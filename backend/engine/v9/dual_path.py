"""v9 Phase 3: Dual-path activation engine.

Converts CompiledEvaluationResult into ActivationResult so the rest of
the pipeline (prompt builder, conviction scorer, frontend) sees a single
format regardless of whether the theory was scored via legacy or compiled.

Selection rule:
  - If an APPROVED compiled artifact exists for a theory, use compiled mode.
  - Otherwise, use legacy mode.

Depends on: compiled_evaluator.py, compiler.py, schemas/theory.py
Depended on by: activation.py (score_all_packages)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from backend.schemas.briefing import BriefingPacket
from backend.schemas.theory import ActivationResult, ActivationTier as LegacyTier
from backend.schemas.v9.compiled_activation import (
    ArtifactStatus,
    CompiledActivationArtifact,
    PhaseModel,
)
from backend.schemas.v9.rules import (
    Comparator,
    CompoundRule,
    FieldComparisonRule,
    ScalarComparisonRule,
)
from backend.engine.v9.compiled_evaluator import (
    ActivationTier as CompiledTier,
    CompiledActivationEvaluator,
    CompiledEvaluationResult,
    IndicatorResult,
    PhaseResult,
)
from backend.engine.v9.registry_builder import build_full_registry
from backend.engine.v9.rule_evaluator import RuleOutcome


# ---------------------------------------------------------------------------
# Approved artifact cache (loaded once per process)
# ---------------------------------------------------------------------------

_approved_cache: dict[str, CompiledActivationArtifact] | None = None


def _load_approved_artifacts() -> dict[str, CompiledActivationArtifact]:
    """Load all APPROVED compiled artifacts. Cached on first call."""
    global _approved_cache
    if _approved_cache is not None:
        return _approved_cache

    from backend.engine.v9.compiler import load_all_artifacts
    all_arts = load_all_artifacts()
    _approved_cache = {
        tid: art for tid, art in all_arts.items()
        if art.artifact_status == ArtifactStatus.APPROVED
    }
    return _approved_cache


def clear_artifact_cache() -> None:
    """Clear the approved artifact cache (for testing)."""
    global _approved_cache
    _approved_cache = None


def get_approved_theory_ids() -> set[str]:
    """Return the set of theory_ids that have APPROVED compiled artifacts."""
    return set(_load_approved_artifacts().keys())


# ---------------------------------------------------------------------------
# Tier mapping
# ---------------------------------------------------------------------------

_TIER_MAP = {
    CompiledTier.ACTIVE: LegacyTier.ACTIVE,
    CompiledTier.ADJACENT: LegacyTier.ADJACENT,
    CompiledTier.INACTIVE: LegacyTier.INACTIVE,
}


def _map_tier(compiled_tier: CompiledTier) -> LegacyTier:
    return _TIER_MAP[compiled_tier]


# ---------------------------------------------------------------------------
# Direction extraction from rule
# ---------------------------------------------------------------------------

_CMP_TO_DIR = {
    Comparator.GT: "above",
    Comparator.GTE: "above",
    Comparator.LT: "below",
    Comparator.LTE: "below",
    Comparator.EQ: "at",
}


def _extract_direction(indicator_result: IndicatorResult, rule) -> Optional[str]:
    """Extract a direction string from the compiled rule for legacy compat."""
    if rule is None:
        return None
    if hasattr(rule, "comparator"):
        return _CMP_TO_DIR.get(rule.comparator, "above")
    if hasattr(rule, "operator"):
        # Compound rule — use first clause's comparator
        if rule.clauses:
            return _extract_direction(indicator_result, rule.clauses[0])
    return None


def _extract_metric_field(rule) -> Optional[str]:
    """Extract the primary field_id from a compiled rule for legacy compat."""
    if rule is None:
        return None
    if hasattr(rule, "field") and hasattr(rule.field, "field_id"):
        return rule.field.field_id
    if hasattr(rule, "left") and hasattr(rule.left, "field_id"):
        return rule.left.field_id
    if hasattr(rule, "clauses") and rule.clauses:
        return _extract_metric_field(rule.clauses[0])
    return None


# ---------------------------------------------------------------------------
# Adapter: CompiledEvaluationResult -> ActivationResult
# ---------------------------------------------------------------------------

def _build_indicator_dict(
    ind: IndicatorResult,
    rule,
) -> dict:
    """Convert a CompiledIndicatorResult into a legacy indicator_results dict entry."""
    entry: dict = {
        "triggered": ind.triggered,
        "value": ind.value,
        "threshold": ind.threshold,
        "weight": ind.weight,
        "metric_field": _extract_metric_field(rule),
    }

    if not ind.in_denominator:
        # Excluded indicator — use legacy-compatible reason codes so
        # _compute_coverage() and downstream consumers handle them identically.
        if ind.value is None:
            entry["reason"] = "data_unavailable"
        else:
            entry["reason"] = "threshold_not_evaluable"
    else:
        # Evaluated indicator — add direction
        direction = _extract_direction(ind, rule)
        if direction:
            entry["direction"] = direction

    return entry


def compiled_to_activation_result(
    compiled: CompiledEvaluationResult,
    artifact: CompiledActivationArtifact,
) -> ActivationResult:
    """Convert a CompiledEvaluationResult to an ActivationResult.

    The output is indistinguishable from a legacy ActivationResult for
    downstream consumers (prompt builder, conviction scorer, frontend).
    """
    is_two_phase = artifact.phase_model == PhaseModel.TWO_PHASE

    # Build indicator_results and skipped lists
    indicator_results: dict[str, dict] = {}
    skipped: list[str] = []

    # Build a lookup from indicator_id to the rule in the artifact
    rule_lookup: dict[str, object] = {}
    for phase in artifact.phases:
        for ci in phase.indicators:
            rule_lookup[ci.indicator_id] = ci.rule

    for _phase_id, pr in compiled.phase_results.items():
        for ind in pr.indicators:
            rule = rule_lookup.get(ind.indicator_id)
            entry = _build_indicator_dict(ind, rule)
            indicator_results[ind.display_name] = entry

            if not ind.in_denominator:
                skipped.append(f"{ind.display_name} ({ind.detail})")

    if is_two_phase:
        # Build phase_scores and phase_tiers keyed by phase_label
        phase_scores: dict[str, float] = {}
        phase_tiers: dict[str, LegacyTier] = {}

        for phase in artifact.phases:
            pr = compiled.phase_results.get(phase.phase_id)
            if pr:
                phase_scores[phase.phase_label] = pr.score
                phase_tiers[phase.phase_label] = _map_tier(pr.tier)

        return ActivationResult(
            theory_id=compiled.theory_id,
            is_two_phase=True,
            phase_scores=phase_scores,
            phase_tiers=phase_tiers,
            effective_tier=_map_tier(compiled.effective_tier),
            effective_phase=compiled.effective_phase,
            indicator_results=indicator_results,
            skipped_indicators=skipped,
        )
    else:
        return ActivationResult(
            theory_id=compiled.theory_id,
            is_two_phase=False,
            score=compiled.effective_score,
            tier=_map_tier(compiled.effective_tier),
            indicator_results=indicator_results,
            skipped_indicators=skipped,
        )


# ---------------------------------------------------------------------------
# Score a single theory via compiled path
# ---------------------------------------------------------------------------

_evaluator_cache: dict[int, CompiledActivationEvaluator] = {}


def score_compiled(
    theory_id: str,
    briefing: BriefingPacket,
) -> ActivationResult:
    """Score a theory via the compiled activation path.

    Requires an APPROVED artifact. Raises KeyError if not found.
    """
    approved = _load_approved_artifacts()
    artifact = approved[theory_id]

    # Cache evaluator per briefing object identity
    bp_id = id(briefing)
    if bp_id not in _evaluator_cache:
        registry = build_full_registry()
        _evaluator_cache[bp_id] = CompiledActivationEvaluator(
            briefing, registry=registry,
        )
    evaluator = _evaluator_cache[bp_id]

    compiled_result = evaluator.evaluate(artifact)
    return compiled_to_activation_result(compiled_result, artifact)
