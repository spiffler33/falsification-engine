"""Deterministic compiled evaluator for v9 spike.

Loads compiled artifacts, resolves fields from the briefing packet,
computes deterministic primitives, evaluates compiled rules, and
produces indicator trigger outputs comparable to the legacy activation engine.
"""
from __future__ import annotations

from backend.schemas.briefing import BriefingPacket
from backend.schemas.v9_spike.compiled_activation import (
    AmbiguityLevel,
    CompiledIndicator,
    CompiledPhase,
    CompiledTheoryActivation,
)
from backend.engine.v9_spike.series_primitives import (
    EvalResult,
    eval_rule,
    resolve_field,
)


ACTIVE_THRESHOLD = 0.60
ADJACENT_THRESHOLD = 0.30


class IndicatorEvalResult:
    """Result of evaluating one compiled indicator."""
    def __init__(
        self,
        indicator_name: str,
        triggered: bool | None,  # None = not evaluable
        value: float | None,
        eval_result: EvalResult,
        detail: dict,
        weight: float,
        field_refs: list[str],
        requires_time_series: bool = False,
    ):
        self.indicator_name = indicator_name
        self.triggered = triggered
        self.value = value
        self.eval_result = eval_result
        self.detail = detail
        self.weight = weight
        self.field_refs = field_refs
        self.requires_time_series = requires_time_series


class PhaseEvalResult:
    """Result of evaluating all indicators in one phase."""
    def __init__(
        self,
        phase_name: str,
        phase_label: str,
        score: float,
        tier: str,
        indicator_results: list[IndicatorEvalResult],
    ):
        self.phase_name = phase_name
        self.phase_label = phase_label
        self.score = score
        self.tier = tier
        self.indicator_results = indicator_results


class TheoryEvalResult:
    """Full evaluation result for a compiled theory."""
    def __init__(
        self,
        theory_id: str,
        is_two_phase: bool,
        phase_results: list[PhaseEvalResult],
        effective_tier: str,
        effective_phase: str | None,
    ):
        self.theory_id = theory_id
        self.is_two_phase = is_two_phase
        self.phase_results = phase_results
        self.effective_tier = effective_tier
        self.effective_phase = effective_phase


def _score_to_tier(score: float) -> str:
    if score >= ACTIVE_THRESHOLD:
        return "Active"
    elif score >= ADJACENT_THRESHOLD:
        return "Adjacent"
    return "Inactive"


def evaluate_indicator(
    ind: CompiledIndicator,
    briefing: BriefingPacket,
    time_series: dict[str, list[float]] | None = None,
) -> IndicatorEvalResult:
    """Evaluate a single compiled indicator against a briefing packet."""
    # Resolve primary field value for reporting
    primary_field = ind.field_refs[0] if ind.field_refs else None
    value = resolve_field(briefing, primary_field) if primary_field else None

    # Evaluate the compiled rule
    result, detail = eval_rule(ind.rule, briefing, time_series)

    if result == EvalResult.NOT_EVALUABLE:
        triggered = None
    else:
        triggered = result == EvalResult.TRUE

    return IndicatorEvalResult(
        indicator_name=ind.indicator_name,
        triggered=triggered,
        value=value,
        eval_result=result,
        detail=detail,
        weight=ind.weight,
        field_refs=ind.field_refs,
        requires_time_series=ind.requires_time_series,
    )


def evaluate_phase(
    phase: CompiledPhase,
    briefing: BriefingPacket,
    time_series: dict[str, list[float]] | None = None,
) -> PhaseEvalResult:
    """Evaluate all indicators in a compiled phase.

    Scoring policy matches the legacy engine:
    - Evaluable indicators contribute to denominator
    - NOT_EVALUABLE indicators are excluded from denominator
    - Score = triggered_weight / total_evaluable_weight
    """
    indicator_results = []
    total_weight = 0.0
    triggered_weight = 0.0

    for ind in phase.indicators:
        ir = evaluate_indicator(ind, briefing, time_series)
        indicator_results.append(ir)

        if ir.triggered is not None:
            # Evaluable — include in denominator
            total_weight += ir.weight
            if ir.triggered:
                triggered_weight += ir.weight

    score = triggered_weight / total_weight if total_weight > 0 else 0.0
    tier = _score_to_tier(score)

    return PhaseEvalResult(
        phase_name=phase.phase_name,
        phase_label=phase.phase_label,
        score=score,
        tier=tier,
        indicator_results=indicator_results,
    )


def evaluate_theory(
    artifact: CompiledTheoryActivation,
    briefing: BriefingPacket,
    time_series: dict[str, list[float]] | None = None,
) -> TheoryEvalResult:
    """Evaluate a complete compiled theory against a briefing packet.

    Two-phase logic mirrors legacy: Phase B checked first; if Active, Phase A inactive.
    """
    phase_results = []
    for phase in artifact.phases:
        pr = evaluate_phase(phase, briefing, time_series)
        phase_results.append(pr)

    if artifact.is_two_phase:
        # Find phase_a and phase_b results
        phase_a = next((p for p in phase_results if p.phase_name == "phase_a"), None)
        phase_b = next((p for p in phase_results if p.phase_name == "phase_b"), None)

        effective_tier = "Inactive"
        effective_phase = None

        if phase_b and phase_b.tier == "Active":
            effective_tier = "Active"
            effective_phase = phase_b.phase_label
        elif phase_b and phase_b.tier == "Adjacent":
            effective_tier = "Adjacent"
            effective_phase = phase_b.phase_label
        elif phase_a:
            effective_tier = phase_a.tier
            if phase_a.tier != "Inactive":
                effective_phase = phase_a.phase_label
    else:
        effective_tier = phase_results[0].tier if phase_results else "Inactive"
        effective_phase = phase_results[0].phase_label if phase_results and phase_results[0].tier != "Inactive" else None

    return TheoryEvalResult(
        theory_id=artifact.theory_id,
        is_two_phase=artifact.is_two_phase,
        phase_results=phase_results,
        effective_tier=effective_tier,
        effective_phase=effective_phase,
    )
