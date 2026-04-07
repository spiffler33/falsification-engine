"""v9 Phase 1: Compiled activation evaluator scaffold.

Loads a CompiledActivationArtifact (hand-authored or compiler-produced),
resolves fields from a briefing packet, evaluates rules deterministically,
and computes per-phase activation scores.

This is the runtime path for compiled artifacts. It replaces the regex-based
activation scoring for theories that have approved compiled artifacts.

Design decisions:
  - Indicator scoring follows the same weighted-average formula as
    the legacy activation.py, but with unit-aware comparison.
  - ExclusionPolicy controls denominator handling:
    * SCORE_IF_EVALUABLE: include in denominator only if the rule
      can be evaluated (missing data -> excluded)
    * ALWAYS_INCLUDE: always in denominator (missing -> False)
    * EXCLUDE_FROM_SCORING: context flag, never in denominator
  - Two-phase logic: check Phase B first. If Active, Phase A is
    forced Inactive (same as legacy).
  - The evaluator does NOT validate artifacts. Call the validator
    separately before evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from backend.schemas.briefing import BriefingPacket
from backend.schemas.v9.compiled_activation import (
    CompiledActivationArtifact,
    CompiledIndicator,
    CompiledPhase,
    ExclusionPolicy,
    PhaseModel,
)
from backend.schemas.v9.field_registry import FieldRegistry
from backend.engine.v9.rule_evaluator import RuleEvaluator, RuleOutcome, RuleResult
from backend.engine.v9.series_interface import SeriesStore


# ---------------------------------------------------------------------------
# Tier classification (mirrors activation.py constants)
# ---------------------------------------------------------------------------

ACTIVE_THRESHOLD = 0.60
ADJACENT_THRESHOLD = 0.30


class ActivationTier(str, Enum):
    ACTIVE = "active"
    ADJACENT = "adjacent"
    INACTIVE = "inactive"


def _score_to_tier(score: float) -> ActivationTier:
    if score >= ACTIVE_THRESHOLD:
        return ActivationTier.ACTIVE
    elif score >= ADJACENT_THRESHOLD:
        return ActivationTier.ADJACENT
    return ActivationTier.INACTIVE


# ---------------------------------------------------------------------------
# Evaluation results
# ---------------------------------------------------------------------------

@dataclass
class IndicatorResult:
    """Result of evaluating a single compiled indicator."""
    indicator_id: str
    display_name: str
    outcome: RuleOutcome
    triggered: bool
    value: Optional[float] = None
    threshold: Optional[float] = None
    weight: float = 0.0
    detail: str = ""
    exclusion_policy: str = "score_if_evaluable"
    in_denominator: bool = True
    in_numerator: bool = False


@dataclass
class PhaseResult:
    """Result of evaluating a compiled phase."""
    phase_id: str
    phase_label: str
    score: float = 0.0
    tier: ActivationTier = ActivationTier.INACTIVE
    total_weight: float = 0.0
    triggered_weight: float = 0.0
    indicators: list[IndicatorResult] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


@dataclass
class CompiledEvaluationResult:
    """Full result of evaluating a compiled activation artifact."""
    theory_id: str
    phase_model: str
    effective_tier: ActivationTier = ActivationTier.INACTIVE
    effective_phase: Optional[str] = None
    effective_score: float = 0.0
    phase_results: dict[str, PhaseResult] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class CompiledActivationEvaluator:
    """Evaluates a compiled activation artifact against a briefing packet.

    Usage:
        registry = build_full_registry()
        evaluator = CompiledActivationEvaluator(briefing, registry)
        result = evaluator.evaluate(artifact)
    """

    def __init__(
        self,
        briefing: BriefingPacket,
        registry: Optional[FieldRegistry] = None,
        series_store: Optional[SeriesStore] = None,
    ):
        self._briefing = briefing
        self._registry = registry
        self._rule_evaluator = RuleEvaluator(
            briefing=briefing,
            registry=registry,
            series_store=series_store,
        )

    def evaluate(
        self, artifact: CompiledActivationArtifact,
    ) -> CompiledEvaluationResult:
        """Evaluate a compiled activation artifact.

        Returns CompiledEvaluationResult with per-phase scores and tiers.
        For two-phase artifacts, applies Phase B priority rule.
        """
        theory_id = artifact.source.theory_id

        result = CompiledEvaluationResult(
            theory_id=theory_id,
            phase_model=artifact.phase_model.value,
        )

        # Evaluate each phase
        for phase in artifact.phases:
            phase_result = self._evaluate_phase(phase)
            result.phase_results[phase.phase_id] = phase_result

        # Determine effective tier
        if artifact.phase_model == PhaseModel.SINGLE_PHASE:
            if artifact.phases:
                pr = result.phase_results.get(artifact.phases[0].phase_id)
                if pr:
                    result.effective_tier = pr.tier
                    result.effective_phase = pr.phase_id
                    result.effective_score = pr.score
        elif artifact.phase_model == PhaseModel.TWO_PHASE:
            result = self._apply_two_phase_priority(result, artifact)

        return result

    def _evaluate_phase(self, phase: CompiledPhase) -> PhaseResult:
        """Evaluate all indicators in a phase and compute the weighted score."""
        pr = PhaseResult(
            phase_id=phase.phase_id,
            phase_label=phase.phase_label,
        )

        for indicator in phase.indicators:
            ind_result = self._evaluate_indicator(indicator)
            pr.indicators.append(ind_result)

            if not ind_result.in_denominator:
                pr.skipped.append(
                    f"{indicator.indicator_id} ({ind_result.detail})"
                )
                continue

            pr.total_weight += indicator.weight
            if ind_result.in_numerator:
                pr.triggered_weight += indicator.weight

        # Compute score
        if pr.total_weight > 0:
            pr.score = pr.triggered_weight / pr.total_weight
        else:
            pr.score = 0.0

        pr.tier = _score_to_tier(pr.score)
        return pr

    def _evaluate_indicator(self, indicator: CompiledIndicator) -> IndicatorResult:
        """Evaluate a single compiled indicator."""
        # Check exclusion policy
        if indicator.exclusion_policy == ExclusionPolicy.EXCLUDE_FROM_SCORING:
            return IndicatorResult(
                indicator_id=indicator.indicator_id,
                display_name=indicator.display_name,
                outcome=RuleOutcome.NOT_EVALUABLE,
                triggered=False,
                weight=indicator.weight,
                detail="excluded from scoring by policy",
                exclusion_policy=indicator.exclusion_policy.value,
                in_denominator=False,
                in_numerator=False,
            )

        # Evaluate the rule
        rule_result = self._rule_evaluator.evaluate(indicator.rule)

        # Apply exclusion policy
        in_denominator = True
        in_numerator = False

        if rule_result.outcome == RuleOutcome.NOT_EVALUABLE:
            if indicator.exclusion_policy == ExclusionPolicy.SCORE_IF_EVALUABLE:
                in_denominator = False
            elif indicator.exclusion_policy == ExclusionPolicy.ALWAYS_INCLUDE:
                in_denominator = True
                in_numerator = False  # missing = not triggered
        elif rule_result.outcome == RuleOutcome.ERROR:
            in_denominator = False
        else:
            in_numerator = rule_result.triggered

        return IndicatorResult(
            indicator_id=indicator.indicator_id,
            display_name=indicator.display_name,
            outcome=rule_result.outcome,
            triggered=rule_result.triggered,
            value=rule_result.value,
            threshold=rule_result.threshold,
            weight=indicator.weight,
            detail=rule_result.detail,
            exclusion_policy=indicator.exclusion_policy.value,
            in_denominator=in_denominator,
            in_numerator=in_numerator,
        )

    def _apply_two_phase_priority(
        self,
        result: CompiledEvaluationResult,
        artifact: CompiledActivationArtifact,
    ) -> CompiledEvaluationResult:
        """Apply two-phase priority rule: Phase B checked first.

        Phase naming convention:
          - Phase A = building/expansion/accumulation (first listed)
          - Phase B = resolving/contraction/rotation (second listed)

        If Phase B is Active, Phase A is forced Inactive.
        """
        phases = artifact.phases
        if len(phases) < 2:
            # Degenerate: only one phase in a two-phase artifact
            if phases:
                pr = result.phase_results.get(phases[0].phase_id)
                if pr:
                    result.effective_tier = pr.tier
                    result.effective_phase = pr.phase_id
                    result.effective_score = pr.score
            return result

        phase_a_id = phases[0].phase_id
        phase_b_id = phases[1].phase_id

        pr_a = result.phase_results.get(phase_a_id)
        pr_b = result.phase_results.get(phase_b_id)

        if pr_b and pr_b.tier == ActivationTier.ACTIVE:
            result.effective_tier = ActivationTier.ACTIVE
            result.effective_phase = phase_b_id
            result.effective_score = pr_b.score
            # Force Phase A Inactive
            if pr_a:
                pr_a.tier = ActivationTier.INACTIVE
        elif pr_b and pr_b.tier == ActivationTier.ADJACENT:
            result.effective_tier = ActivationTier.ADJACENT
            result.effective_phase = phase_b_id
            result.effective_score = pr_b.score
        elif pr_a:
            result.effective_tier = pr_a.tier
            if pr_a.tier != ActivationTier.INACTIVE:
                result.effective_phase = phase_a_id
            result.effective_score = pr_a.score

        return result
