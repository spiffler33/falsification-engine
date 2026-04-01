# realization.py — Expression-level realization computation (v6 Phases 1 + 4).
# Pure functions, no side effects, no DB access.
# Depends on: nothing
# Depended on by: api/hypotheses.py (realization endpoint), api/pipeline.py (walk-forward),
#                 engine/conviction.py (realization cap in Stage 3)
from __future__ import annotations

from datetime import date, timedelta


# ============================================================
# PROVISIONAL POLICY CONFIGURATION — ALL THRESHOLDS ARE [CALIBRATION]
# Change these values based on live run evidence.
# They are configuration, not architecture.
# ============================================================

# [CALIBRATION] Time axis threshold — fraction of holding window
# Below this = "early", at or above = "late"
TIME_THRESHOLD = 0.50

# [CALIBRATION] Conviction caps per freshness label (None = no cap)
REALIZATION_CAPS = {
    "FRESH":            None,
    "WORKING":          None,
    "ACCELERATING":     None,
    "UNDERPERFORMING":  None,
    "MATURE":           7.0,
    "EXPRESSED":        5.0,
    "INDETERMINATE":    None,
}


def compute_expression_return(
    predicted_assets: list[str],
    asset_direction: dict[str, str],
    entry_prices: dict[str, float],
    current_prices: dict[str, float],
) -> float | None:
    """
    Compute the expression-level return as the equal-weight mean
    of direction-adjusted leg returns.

    For a LONG leg:  leg_return = (current - entry) / entry
    For a SHORT leg: leg_return = (entry - current) / entry
        (equivalently: -1 * raw_return)

    Expression return = mean(all leg returns)

    Returns None if any ticker is missing from entry_prices or current_prices,
    or if any entry price is zero/negative.
    """
    if not predicted_assets:
        return None

    leg_returns: list[float] = []
    for ticker in predicted_assets:
        if ticker not in entry_prices or ticker not in current_prices:
            return None

        entry = entry_prices[ticker]
        current = current_prices[ticker]

        if entry <= 0:
            return None

        raw_return = (current - entry) / entry

        direction = asset_direction.get(ticker, "LONG")
        if direction == "SHORT":
            raw_return = -raw_return

        leg_returns.append(raw_return)

    return sum(leg_returns) / len(leg_returns)


def compute_realization_ratios(
    expression_return: float,
    predicted_magnitude_lower: float,
    predicted_magnitude_upper: float,
) -> dict:
    """
    Compare expression return against the payoff band.

    Returns:
        realization_vs_lower: expression_return / predicted_magnitude_lower
        realization_vs_upper: expression_return / predicted_magnitude_upper

    Both are ratios. Below 1.0 = hasn't reached the bound. Above 1.0 = has passed it.

    If either magnitude bound is zero or negative (data error), returns None for that ratio.
    """
    result = {}

    if predicted_magnitude_lower and predicted_magnitude_lower > 0:
        result["realization_vs_lower"] = expression_return / predicted_magnitude_lower
    else:
        result["realization_vs_lower"] = None

    if predicted_magnitude_upper and predicted_magnitude_upper > 0:
        result["realization_vs_upper"] = expression_return / predicted_magnitude_upper
    else:
        result["realization_vs_upper"] = None

    return result


def compute_time_elapsed_pct(
    entry_date: str,
    timeframe_end_date: str,
    as_of_date: str | None = None,
) -> float:
    """
    Fraction of the holding window consumed.

    Returns a float clamped to [0.0, 1.0].
    At 0.0 the window just opened. At 1.0 the window has expired.
    """
    entry = date.fromisoformat(entry_date)
    end = date.fromisoformat(timeframe_end_date)
    now = date.fromisoformat(as_of_date) if as_of_date else date.today()

    window = (end - entry).days
    if window <= 0:
        return 1.0

    elapsed = (now - entry).days
    return max(0.0, min(1.0, elapsed / window))


def validate_payoff_band(
    predicted_magnitude_lower: float,
    predicted_magnitude_upper: float,
    timeframe_end_date: str,
    as_of_date: str | None = None,
) -> list[str]:
    """
    Validate payoff band fields. Returns list of error messages (empty if valid).

    Constraints (from plan_v6.md Component 2):
    - Both bounds must be positive
    - Lower must be strictly less than upper (band has width)
    - Upper bound capped at 1.0 (100%) -- no liquid ETF hypothesis should
      predict more than a double within the holding window
    - timeframe_end_date must be a valid ISO date in the future, within 12 months
    """
    errors = []

    if predicted_magnitude_lower <= 0:
        errors.append("predicted_magnitude_lower must be positive")
    if predicted_magnitude_upper <= 0:
        errors.append("predicted_magnitude_upper must be positive")

    if predicted_magnitude_lower >= predicted_magnitude_upper:
        errors.append("predicted_magnitude_lower must be less than predicted_magnitude_upper")

    if predicted_magnitude_upper > 1.0:
        errors.append("predicted_magnitude_upper exceeds 1.0 (100%) ceiling")

    today = date.fromisoformat(as_of_date) if as_of_date else date.today()
    try:
        end = date.fromisoformat(timeframe_end_date)
        if end <= today:
            errors.append("timeframe_end_date must be in the future")
        if (end - today).days > 365:
            errors.append("timeframe_end_date must be within 12 months")
    except (ValueError, TypeError):
        errors.append("timeframe_end_date is not a valid ISO date")

    return errors


# ---------------------------------------------------------------------------
# Provisional Policy Layer (v6 Phase 4)
# ---------------------------------------------------------------------------

def compute_freshness_label(
    realization_vs_lower: float | None,
    realization_vs_upper: float | None,
    time_elapsed_pct: float,
) -> str:
    """
    Compute the freshness label from realization primitives.

    Two axes:
      Magnitude: R < L (below lower) | L <= R < U (within band) | R >= U (above upper)
      Time:      early (< TIME_THRESHOLD) | late (>= TIME_THRESHOLD)

    Matrix (6 cells):
      Below lower + early  = FRESH
      Below lower + late   = UNDERPERFORMING
      Within band + early  = WORKING
      Within band + late   = MATURE
      Above upper + early  = ACCELERATING
      Above upper + late   = EXPRESSED

    If realization ratios are None (missing payoff band data), returns INDETERMINATE.
    """
    if realization_vs_lower is None or realization_vs_upper is None:
        return "INDETERMINATE"

    late = time_elapsed_pct >= TIME_THRESHOLD

    if realization_vs_upper >= 1.0:
        return "EXPRESSED" if late else "ACCELERATING"
    elif realization_vs_lower >= 1.0:
        return "MATURE" if late else "WORKING"
    else:
        return "UNDERPERFORMING" if late else "FRESH"


def compute_realization_cap(freshness_label: str) -> float | None:
    """
    Return the conviction cap for the given freshness label, or None if no cap applies.

    This cap is applied in Stage 3 alongside horizon_cap and expression_cap:
        FINAL = min(SCORE, horizon_cap, expression_cap, realization_cap)
    """
    return REALIZATION_CAPS.get(freshness_label, None)
