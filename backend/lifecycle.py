# lifecycle.py — Falsifier lifecycle computation (v7 Component 2 + Component 6).
# Pure functions, no side effects, no DB access.
# Depends on: nothing
# Depended on by: api/pipeline.py (staleness gate pre-generation),
#                 engine/conviction.py (ESCALATED_UNTESTABLE in D_u)
from __future__ import annotations

import re


# ============================================================
# PROVISIONAL POLICY CONFIGURATION — ALL THRESHOLDS ARE [CALIBRATION]
# Change these values based on live run evidence.
# They are configuration, not architecture.
# ============================================================

# [CALIBRATION] Staleness multiplier — how far current market must be
# from the threshold, relative to the generation-time distance,
# before the falsifier is flagged STALE.
STALENESS_MULTIPLIER = 2.0

# [CALIBRATION] Consecutive UNTESTABLE passes before escalation.
ESCALATION_THRESHOLD = 3


# ---------------------------------------------------------------------------
# Threshold parsing
# ---------------------------------------------------------------------------

def _parse_threshold_value(threshold_str: str) -> float | None:
    """
    Extract a numeric value from a falsifier threshold string.

    Handles formats like:
      "VIX below 18"         -> 18.0
      "spread above 2.5%"    -> 2.5
      "> 3.0"                -> 3.0
      "18"                   -> 18.0
      "falls below -0.5"     -> -0.5

    Returns None if no numeric value can be extracted.
    """
    if threshold_str is None:
        return None

    # Find all numbers (including negative and decimal)
    matches = re.findall(r"-?\d+\.?\d*", str(threshold_str))
    if not matches:
        return None

    # Take the last numeric value — threshold strings typically end with
    # the number (e.g., "VIX below 18", "spread exceeds 2.5%")
    try:
        return float(matches[-1])
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Component 2: Mechanical Staleness Gate (2x Rule)
# ---------------------------------------------------------------------------

def compute_staleness_flag(
    falsifier: dict,
    generation_market_value: float | None,
    current_market_value: float | None,
) -> str | None:
    """
    Mechanical staleness detection for a single falsifier.

    If the market has moved more than 2x the distance between
    the generation-time value and the threshold, the falsifier is stale.

    The logic:
      distance_at_generation = |threshold - generation_market_value|
      distance_current       = |current_market_value - threshold|
      if distance_current > STALENESS_MULTIPLIER * distance_at_generation: STALE

    Returns "STALE" or None.
    """
    threshold = _parse_threshold_value(falsifier.get("threshold"))
    if threshold is None or generation_market_value is None or current_market_value is None:
        return None

    distance_at_generation = abs(threshold - generation_market_value)
    if distance_at_generation <= 0:
        return None  # threshold was at market level — degenerate case

    distance_current_from_threshold = abs(current_market_value - threshold)

    if distance_current_from_threshold > STALENESS_MULTIPLIER * distance_at_generation:
        return "STALE"

    return None


# ---------------------------------------------------------------------------
# Thread-level staleness: run across all falsifiers for an active thread
# ---------------------------------------------------------------------------

def compute_thread_staleness(
    soft_falsifiers: list[dict],
    current_market_values: dict[str, float],
) -> list[dict]:
    """
    Run the staleness gate across all soft falsifiers for a thread.

    For each falsifier, looks up:
      - generation_market_value: stored on the falsifier dict
      - current_market_value: looked up from current_market_values by falsifier metric

    Returns a new list of falsifier dicts with staleness_flag set.
    Does NOT mutate the input list.

    Args:
        soft_falsifiers: list of falsifier dicts, each with at least:
            - metric: str (briefing packet field name)
            - threshold: str (human-readable threshold)
            - generation_market_value: float | None
            - status: str (current status)
        current_market_values: dict mapping metric names to current values
            from the briefing packet

    Returns:
        New list of falsifier dicts with staleness_flag field set.
    """
    result = []
    for f in soft_falsifiers:
        updated = dict(f)  # shallow copy

        generation_val = f.get("generation_market_value")
        metric = f.get("metric", "")
        current_val = current_market_values.get(metric)

        flag = compute_staleness_flag(f, generation_val, current_val)
        updated["staleness_flag"] = flag

        result.append(updated)

    return result


# ---------------------------------------------------------------------------
# Component 6: ESCALATED_UNTESTABLE Step Function
# ---------------------------------------------------------------------------

def compute_untestable_escalation(
    current_status: str,
    untestable_consecutive: int,
    escalation_threshold: int = ESCALATION_THRESHOLD,
) -> tuple[str, int]:
    """
    Track consecutive UNTESTABLE passes and escalate at threshold.

    When a falsifier is UNTESTABLE for N consecutive passes (default N=3),
    it becomes ESCALATED_UNTESTABLE. This flags vacuous survivorship:
    the hypothesis survived because we couldn't test it, not because
    it passed tests.

    Args:
        current_status: the falsifier's status after elimination pass audit.
            One of: CLEAR, TRIGGERED, UNTESTABLE, STALE, TRIGGERED_BY_PASSAGE
        untestable_consecutive: inherited from prior instance (0 for new falsifiers)
        escalation_threshold: [CALIBRATION] consecutive passes before escalation

    Returns:
        (final_status, updated_consecutive_count)
        - If escalated: ("ESCALATED_UNTESTABLE", count)
        - If still UNTESTABLE but below threshold: ("UNTESTABLE", count)
        - If status changed to anything else: (current_status, 0)
    """
    if current_status == "UNTESTABLE":
        new_count = untestable_consecutive + 1
        if new_count >= escalation_threshold:
            return ("ESCALATED_UNTESTABLE", new_count)
        return ("UNTESTABLE", new_count)
    else:
        # Falsifier became CLEAR, TRIGGERED, STALE, or TRIGGERED_BY_PASSAGE
        # — counter resets
        return (current_status, 0)


# ---------------------------------------------------------------------------
# Thread-level UNTESTABLE escalation: run across all falsifiers
# ---------------------------------------------------------------------------

def apply_untestable_escalation(
    soft_falsifiers: list[dict],
    escalation_threshold: int = ESCALATION_THRESHOLD,
) -> list[dict]:
    """
    Run UNTESTABLE escalation across all soft falsifiers for a thread instance.

    Each falsifier dict must have:
        - status: str (post-elimination status)
        - untestable_consecutive: int (inherited from prior instance, 0 if new)

    Returns a new list of falsifier dicts with updated status and
    untestable_consecutive fields. Does NOT mutate the input list.
    """
    result = []
    for f in soft_falsifiers:
        updated = dict(f)  # shallow copy

        current_status = f.get("status", "UNTESTABLE")
        consecutive = f.get("untestable_consecutive", 0)

        new_status, new_count = compute_untestable_escalation(
            current_status, consecutive, escalation_threshold
        )

        updated["status"] = new_status
        updated["untestable_consecutive"] = new_count

        result.append(updated)

    return result
