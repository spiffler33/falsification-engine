# activation.py — Pass 1: Mechanical activation scoring.
# Depends on: schemas/theory.py, schemas/briefing.py
# Depended on by: api/theories.py, api/pipeline.py, engine/prompt_builder.py
#
# Takes parsed theory modules + a data briefing packet.
# For each theory, checks each indicator against the briefing.
# Computes weighted activation score. Returns Active/Adjacent/Inactive.
# Two-phase logic: check Phase B first; if Active, Phase A is Inactive.
from __future__ import annotations

import re

from backend.schemas.briefing import BriefingPacket
from backend.schemas.theory import (
    ActivationPhase,
    ActivationResult,
    ActivationTier,
    Direction,
    Indicator,
    TheoryModule,
)

# Tier thresholds from CLAUDE.md
ACTIVE_THRESHOLD = 0.60
ADJACENT_THRESHOLD = 0.30


def score_all_theories(
    theories: list[TheoryModule],
    briefing: BriefingPacket,
) -> list[ActivationResult]:
    """Score activation for all theory modules against a briefing packet."""
    return [score_theory(t, briefing) for t in theories]


def score_theory(theory: TheoryModule, briefing: BriefingPacket) -> ActivationResult:
    """Score activation for a single theory module."""
    if theory.is_two_phase:
        return _score_two_phase(theory, briefing)
    else:
        return _score_single_phase(theory, briefing)


def _score_single_phase(theory: TheoryModule, briefing: BriefingPacket) -> ActivationResult:
    """Score a single-phase theory."""
    if not theory.phases:
        return ActivationResult(theory_id=theory.theory_id, score=0.0, tier=ActivationTier.INACTIVE)

    phase = theory.phases[0]
    score, indicator_results, skipped = _score_phase(phase, briefing)
    tier = _score_to_tier(score)

    return ActivationResult(
        theory_id=theory.theory_id,
        is_two_phase=False,
        score=score,
        tier=tier,
        indicator_results=indicator_results,
        skipped_indicators=skipped,
    )


def _score_two_phase(theory: TheoryModule, briefing: BriefingPacket) -> ActivationResult:
    """Score a two-phase theory. Phase B checked first per spec."""
    phase_a = None
    phase_b = None
    for p in theory.phases:
        if p.phase_name == "phase_a":
            phase_a = p
        elif p.phase_name == "phase_b":
            phase_b = p

    phase_scores: dict[str, float] = {}
    phase_tiers: dict[str, ActivationTier] = {}
    all_indicator_results: dict[str, dict] = {}
    all_skipped: list[str] = []

    # Score Phase B first
    if phase_b:
        score_b, results_b, skipped_b = _score_phase(phase_b, briefing)
        phase_scores[phase_b.phase_label] = score_b
        phase_tiers[phase_b.phase_label] = _score_to_tier(score_b)
        all_indicator_results.update(results_b)
        all_skipped.extend(skipped_b)

    # Score Phase A
    if phase_a:
        score_a, results_a, skipped_a = _score_phase(phase_a, briefing)
        phase_scores[phase_a.phase_label] = score_a
        phase_tiers[phase_a.phase_label] = _score_to_tier(score_a)
        all_indicator_results.update(results_a)
        all_skipped.extend(skipped_a)

    # Determine effective tier: Phase B takes priority
    effective_tier = ActivationTier.INACTIVE
    effective_phase = None

    if phase_b and phase_tiers.get(phase_b.phase_label) == ActivationTier.ACTIVE:
        effective_tier = ActivationTier.ACTIVE
        effective_phase = phase_b.phase_label
        # Phase A is Inactive by definition when Phase B is Active
        if phase_a:
            phase_tiers[phase_a.phase_label] = ActivationTier.INACTIVE
    elif phase_b and phase_tiers.get(phase_b.phase_label) == ActivationTier.ADJACENT:
        effective_tier = ActivationTier.ADJACENT
        effective_phase = phase_b.phase_label
    elif phase_a:
        phase_a_tier = phase_tiers.get(phase_a.phase_label, ActivationTier.INACTIVE)
        effective_tier = phase_a_tier
        if phase_a_tier != ActivationTier.INACTIVE:
            effective_phase = phase_a.phase_label

    return ActivationResult(
        theory_id=theory.theory_id,
        is_two_phase=True,
        phase_scores=phase_scores,
        phase_tiers=phase_tiers,
        effective_tier=effective_tier,
        effective_phase=effective_phase,
        indicator_results=all_indicator_results,
        skipped_indicators=all_skipped,
    )


def _score_phase(
    phase: ActivationPhase,
    briefing: BriefingPacket,
) -> tuple[float, dict[str, dict], list[str]]:
    """Score a single activation phase against the briefing.

    Returns (score, indicator_results, skipped_indicators).
    Score is weighted sum of triggered mechanical indicators,
    normalized by total mechanical weight.
    """
    total_mechanical_weight = 0.0
    triggered_weight = 0.0
    indicator_results: dict[str, dict] = {}
    skipped: list[str] = []

    for ind in phase.indicators:
        # Skip qualitative indicators
        if ind.is_qualitative or ind.weight < 0:
            skipped.append(f"{ind.name} (qualitative)")
            continue

        # Skip web-search-required indicators for v1
        if ind.requires_web_search:
            skipped.append(f"{ind.name} (web-search required)")
            continue

        total_mechanical_weight += ind.weight

        # Resolve metric from briefing
        metric_field = _extract_metric_field(ind.metric_source)
        value = briefing.get_field(metric_field) if metric_field else None

        if value is None:
            indicator_results[ind.name] = {
                "triggered": False,
                "value": None,
                "threshold": ind.threshold,
                "metric_field": metric_field,
                "reason": "data not available",
            }
            continue

        # Check threshold
        triggered = _check_threshold(value, ind)

        if triggered:
            triggered_weight += ind.weight

        indicator_results[ind.name] = {
            "triggered": triggered,
            "value": value,
            "threshold": ind.threshold,
            "direction": ind.direction.value,
            "weight": ind.weight,
            "metric_field": metric_field,
        }

    # Normalize score by total mechanical weight
    if total_mechanical_weight > 0:
        score = triggered_weight / total_mechanical_weight
    else:
        score = 0.0

    return score, indicator_results, skipped


def _extract_metric_field(metric_source: str) -> str | None:
    """Extract the briefing packet field name from a metric_source string.

    Examples:
        '`^VIX`' → '^VIX'
        '`credit.hy_spread`' → 'credit.hy_spread'
        'computed: `qqq_iwm_ratio`' → 'qqq_iwm_ratio'
        'computed: `VIX - 20d_realized_vol`' → 'vix_realized_gap'
        'web search required' → None
        'web search: FINRA margin statistics' → None
    """
    source = metric_source.strip()

    # Skip web-search sources
    if "web search" in source.lower():
        return None

    # Extract backtick-wrapped field names
    backtick_match = re.findall(r"`([^`]+)`", source)
    if backtick_match:
        field = backtick_match[-1]  # take the last backtick match

        # Handle computed expressions like "VIX - 20d_realized_vol"
        if " - " in field or " + " in field or " / " in field:
            # These are computed metrics — map to a normalized field name
            return _normalize_computed_field(field)

        return field

    # Handle plain metric names
    if source and not source.startswith("web"):
        return source

    return None


def _normalize_computed_field(expr: str) -> str:
    """Normalize a computed expression to a briefing field name."""
    expr_lower = expr.lower().strip()

    # Known computed field mappings
    if "vix" in expr_lower and "realized" in expr_lower:
        return "vix_vs_realized"
    if "qqq" in expr_lower and "iwm" in expr_lower:
        return "qqq_iwm_ratio"

    # Generic normalization: replace operators with underscores
    normalized = re.sub(r"[^a-z0-9]", "_", expr_lower)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def _check_threshold(value: float, indicator: Indicator) -> bool:
    """Check if a value triggers an indicator's threshold condition."""
    threshold_str = indicator.threshold.strip()

    # Extract numeric threshold from the description
    threshold_num = _extract_number(threshold_str)

    if threshold_num is None:
        # Cannot mechanically check — descriptive threshold
        return False

    if indicator.direction == Direction.ABOVE:
        return value > threshold_num
    elif indicator.direction == Direction.BELOW:
        return value < threshold_num
    elif indicator.direction == Direction.RISING:
        # For rising/falling, we'd need historical data. For v1, check against threshold.
        return value > threshold_num
    elif indicator.direction == Direction.FALLING:
        return value < threshold_num
    elif indicator.direction == Direction.BETWEEN:
        # Try to extract a range
        numbers = re.findall(r"[-+]?\d*\.?\d+", threshold_str)
        if len(numbers) >= 2:
            low, high = float(numbers[0]), float(numbers[1])
            return low <= value <= high
        return False

    return False


def _extract_number(s: str) -> float | None:
    """Extract the first meaningful number from a threshold string.

    Handles: 'Below 14', 'Above 300bp', '-20%', '$1.5T', '0.5x', etc.
    """
    # Remove common suffixes
    cleaned = s.replace("bp", "").replace("%", "").replace("$", "")
    cleaned = cleaned.replace("T", "").replace("B", "").replace("M", "")
    cleaned = cleaned.replace("x", "")

    # Find numbers
    numbers = re.findall(r"[-+]?\d*\.?\d+", cleaned)
    if numbers:
        return float(numbers[0])

    return None


def _score_to_tier(score: float) -> ActivationTier:
    """Convert a numeric score to an activation tier."""
    if score >= ACTIVE_THRESHOLD:
        return ActivationTier.ACTIVE
    elif score >= ADJACENT_THRESHOLD:
        return ActivationTier.ADJACENT
    else:
        return ActivationTier.INACTIVE
