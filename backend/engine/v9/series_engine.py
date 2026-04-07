"""v9 Phase 1: Concrete series primitive engine.

Implements the SeriesPrimitiveEngine ABC from Phase 0.
Evaluates deterministic series operations against time-series data
stored in a SeriesStore.

Design decisions:
  - All operations return PrimitiveResult, never raise.
  - Missing data / insufficient history -> status != OK.
  - Trend classification uses simple sign-of-slope heuristic.
  - Named patterns dispatched to registered evaluators.
  - Window conversion: TimeWindow -> approximate period count
    based on data frequency.
"""
from __future__ import annotations

import math
from typing import Optional

from backend.engine.v9.series_interface import (
    PrimitiveResult,
    PrimitiveResultStatus,
    SeriesData,
    SeriesPrimitiveEngine,
    SeriesStore,
)
from backend.schemas.v9.units import TimeWindow, TimeUnit


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------

def _window_to_periods(window: TimeWindow, frequency: str = "monthly") -> int:
    """Convert a TimeWindow to approximate number of data periods.

    This is an approximation — exact conversion depends on the data
    frequency and calendar alignment.
    """
    freq_days = {
        "daily": 1,
        "weekly": 7,
        "monthly": 30,
        "quarterly": 90,
    }
    window_days = {
        TimeUnit.DAYS: 1,
        TimeUnit.WEEKS: 7,
        TimeUnit.MONTHS: 30,
        TimeUnit.QUARTERS: 90,
        TimeUnit.YEARS: 365,
    }
    total_days = window.value * window_days.get(window.unit, 30)
    period_days = freq_days.get(frequency, 30)
    return max(1, total_days // period_days)


def _require_series(
    store: SeriesStore, field_id: str, window: TimeWindow,
) -> tuple[Optional[SeriesData], Optional[PrimitiveResult]]:
    """Fetch series data, returning an error PrimitiveResult if unavailable."""
    if not store.has_series(field_id):
        return None, PrimitiveResult(
            status=PrimitiveResultStatus.FIELD_NOT_FOUND,
            detail=f"No series data for {field_id}",
        )
    series = store.get_series(field_id, window)
    if series is None or series.is_empty:
        return None, PrimitiveResult(
            status=PrimitiveResultStatus.INSUFFICIENT_DATA,
            detail=f"Empty series for {field_id}",
        )
    return series, None


# ---------------------------------------------------------------------------
# Named pattern evaluators
# ---------------------------------------------------------------------------

def _eval_sahm_rule(params: dict, store: SeriesStore) -> PrimitiveResult:
    """Sahm Rule: 3-month MA of unemployment rising 0.50%+ above 12-month low.

    Params:
      field: unemployment rate field_id (default: growth.unemployment)
      threshold: trigger threshold (default: 0.50)
    """
    field = params.get("field", "growth.unemployment")
    threshold = params.get("threshold", 0.50)

    window = TimeWindow(value=15, unit=TimeUnit.MONTHS)
    series, err = _require_series(store, field, window)
    if err:
        return err

    values = series.values
    if len(values) < 12:
        return PrimitiveResult(
            status=PrimitiveResultStatus.INSUFFICIENT_DATA,
            detail=f"Need 12+ months for Sahm Rule, have {len(values)}",
        )

    # 3-month moving average of last 3 values
    ma_3 = sum(values[-3:]) / 3.0

    # 12-month low of 3-month MA
    # Compute 3-month MA for each valid point
    mas = []
    for i in range(2, len(values)):
        mas.append(sum(values[i-2:i+1]) / 3.0)

    if not mas:
        return PrimitiveResult(
            status=PrimitiveResultStatus.INSUFFICIENT_DATA,
            detail="Cannot compute 3-month MA series",
        )

    low_12 = min(mas[-12:]) if len(mas) >= 12 else min(mas)
    rise = ma_3 - low_12
    triggered = rise >= threshold

    return PrimitiveResult(
        status=PrimitiveResultStatus.OK,
        value=round(rise, 4),
        boolean=triggered,
        detail=f"Sahm: 3mo MA={ma_3:.2f}, 12mo low={low_12:.2f}, rise={rise:.2f}, threshold={threshold}",
    )


def _eval_resteepened_after_inversion(params: dict, store: SeriesStore) -> PrimitiveResult:
    """Yield curve re-steepening after deep inversion.

    Params:
      field: yield curve spread field_id (default: rates.curve_2s10s)
      inversion_threshold: how negative the curve must have been (default: -0.50)
      resteepen_delta: minimum rise from trough (default: 0.75)
    """
    field = params.get("field", "rates.curve_2s10s")
    inv_thresh = params.get("inversion_threshold", -0.50)
    delta = params.get("resteepen_delta", 0.75)

    window = TimeWindow(value=24, unit=TimeUnit.MONTHS)
    series, err = _require_series(store, field, window)
    if err:
        return err

    values = series.values
    if len(values) < 6:
        return PrimitiveResult(
            status=PrimitiveResultStatus.INSUFFICIENT_DATA,
            detail="Need 6+ months for resteepening check",
        )

    trough = min(values)
    current = values[-1]
    was_inverted = trough < inv_thresh
    resteepened = (current - trough) >= delta

    triggered = was_inverted and resteepened

    return PrimitiveResult(
        status=PrimitiveResultStatus.OK,
        value=round(current - trough, 4),
        boolean=triggered,
        detail=f"Curve: trough={trough:.2f}, current={current:.2f}, delta={current-trough:.2f}",
    )


_NAMED_PATTERN_EVALUATORS: dict[str, callable] = {
    "sahm_rule": _eval_sahm_rule,
    "resteepened_after_inversion": _eval_resteepened_after_inversion,
}


# ---------------------------------------------------------------------------
# Concrete engine
# ---------------------------------------------------------------------------

class BriefingSeriesEngine(SeriesPrimitiveEngine):
    """Concrete series primitive engine backed by a SeriesStore.

    All operations are deterministic. Missing data returns
    PrimitiveResult with status != OK, never raises.
    """

    def __init__(self, store: SeriesStore):
        self._store = store

    # --- Category 1: Point-in-time ---

    def latest_value(self, field_id: str) -> PrimitiveResult:
        if not self._store.has_series(field_id):
            return PrimitiveResult(
                status=PrimitiveResultStatus.FIELD_NOT_FOUND,
                detail=f"No series for {field_id}",
            )
        window = TimeWindow(value=1, unit=TimeUnit.DAYS)
        series = self._store.get_series(field_id, window)
        if series is None or series.is_empty:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail=f"Empty series for {field_id}",
            )
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=series.latest,
        )

    def value_at_offset(self, field_id: str, offset: int) -> PrimitiveResult:
        window = TimeWindow(value=max(offset + 1, 1), unit=TimeUnit.MONTHS)
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err
        if len(series.values) <= offset:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail=f"Need {offset+1} points, have {len(series.values)}",
            )
        idx = -(offset + 1)
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=series.values[idx],
        )

    # --- Category 2: Change ---

    def absolute_change(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err
        if len(series.values) < 2:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail="Need 2+ points for change",
            )
        change = series.values[-1] - series.values[0]
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=round(change, 6),
        )

    def percent_change(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err
        if len(series.values) < 2:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail="Need 2+ points for percent change",
            )
        base = series.values[0]
        if base == 0:
            return PrimitiveResult(
                status=PrimitiveResultStatus.ERROR,
                detail="Base value is zero, cannot compute percent change",
            )
        pct = ((series.values[-1] - base) / abs(base)) * 100
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=round(pct, 4),
        )

    # --- Category 3: Rolling statistics ---

    def rolling_max(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=max(series.values),
        )

    def rolling_min(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=min(series.values),
        )

    def rolling_mean(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err
        mean = sum(series.values) / len(series.values)
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=round(mean, 6),
        )

    # --- Category 4: Historical rank ---

    def percentile_rank(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err
        values = series.values
        if len(values) < 2:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail="Need 2+ points for percentile rank",
            )
        current = values[-1]
        below = sum(1 for v in values[:-1] if v < current)
        rank = below / (len(values) - 1)
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=round(rank, 4),
        )

    def is_at_extreme(
        self, field_id: str, extreme: str, window: TimeWindow,
        margin: float = 0.0,
    ) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err

        current = series.values[-1]
        if extreme == "high":
            extreme_val = max(series.values)
            if margin > 0 and extreme_val != 0:
                threshold = extreme_val * (1 - margin)
                at_extreme = current >= threshold
            else:
                at_extreme = current >= extreme_val
        elif extreme == "low":
            extreme_val = min(series.values)
            if margin > 0 and extreme_val != 0:
                threshold = extreme_val * (1 + margin)
                at_extreme = current <= threshold
            else:
                at_extreme = current <= extreme_val
        else:
            return PrimitiveResult(
                status=PrimitiveResultStatus.ERROR,
                detail=f"Unknown extreme type: {extreme}",
            )

        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=current,
            boolean=at_extreme,
            detail=f"Current={current}, {extreme}={extreme_val}, margin={margin}",
        )

    def distance_from_extreme(
        self, field_id: str, extreme: str, window: TimeWindow,
    ) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err

        current = series.values[-1]
        if extreme == "high":
            extreme_val = max(series.values)
        elif extreme == "low":
            extreme_val = min(series.values)
        else:
            return PrimitiveResult(
                status=PrimitiveResultStatus.ERROR,
                detail=f"Unknown extreme type: {extreme}",
            )

        if extreme_val == 0:
            return PrimitiveResult(
                status=PrimitiveResultStatus.ERROR,
                detail="Extreme value is zero",
            )

        if extreme == "high":
            distance = (current - extreme_val) / abs(extreme_val)
        else:
            distance = (extreme_val - current) / abs(extreme_val)

        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=round(distance, 4),
        )

    # --- Category 5: Trend ---

    def trend_direction(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err

        values = series.values
        if len(values) < 2:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail="Need 2+ points for trend",
            )

        # Simple linear regression slope
        n = len(values)
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))

        if den == 0:
            direction = "stable"
        else:
            slope_val = num / den
            # Normalize slope relative to mean for stability classification
            rel_slope = slope_val / abs(y_mean) if y_mean != 0 else slope_val
            if rel_slope > 0.005:
                direction = "rising"
            elif rel_slope < -0.005:
                direction = "falling"
            else:
                direction = "stable"

        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            boolean=True,  # always returns a classification
            detail=direction,
        )

    def slope(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err

        values = series.values
        if len(values) < 2:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail="Need 2+ points for slope",
            )

        n = len(values)
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))

        slope_val = num / den if den != 0 else 0.0
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=round(slope_val, 6),
        )

    # --- Category 6: Crossover ---

    def crossed_above(
        self, field_a: str, field_b: str, window: TimeWindow,
    ) -> PrimitiveResult:
        series_a, err = _require_series(self._store, field_a, window)
        if err:
            return err
        series_b, err = _require_series(self._store, field_b, window)
        if err:
            return err

        min_len = min(len(series_a.values), len(series_b.values))
        if min_len < 2:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail="Need 2+ points for crossover",
            )

        vals_a = series_a.values[-min_len:]
        vals_b = series_b.values[-min_len:]

        crossed = False
        for i in range(1, len(vals_a)):
            if vals_a[i-1] <= vals_b[i-1] and vals_a[i] > vals_b[i]:
                crossed = True
                break

        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            boolean=crossed,
        )

    def crossed_below(
        self, field_a: str, field_b: str, window: TimeWindow,
    ) -> PrimitiveResult:
        series_a, err = _require_series(self._store, field_a, window)
        if err:
            return err
        series_b, err = _require_series(self._store, field_b, window)
        if err:
            return err

        min_len = min(len(series_a.values), len(series_b.values))
        if min_len < 2:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail="Need 2+ points for crossover",
            )

        vals_a = series_a.values[-min_len:]
        vals_b = series_b.values[-min_len:]

        crossed = False
        for i in range(1, len(vals_a)):
            if vals_a[i-1] >= vals_b[i-1] and vals_a[i] < vals_b[i]:
                crossed = True
                break

        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            boolean=crossed,
        )

    def above_moving_average(
        self, field_id: str, ma_window: TimeWindow,
    ) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, ma_window)
        if err:
            return err

        values = series.values
        if len(values) < 2:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail="Need 2+ points for MA comparison",
            )

        ma = sum(values) / len(values)
        current = values[-1]
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=ma,
            boolean=current > ma,
            detail=f"Current={current}, MA={ma:.4f}",
        )

    # --- Category 7: Persistence ---

    def count_true(
        self, field_id: str, condition_fn: str,
        condition_value: float, window: TimeWindow,
    ) -> PrimitiveResult:
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err

        cmp = _get_comparator(condition_fn)
        if cmp is None:
            return PrimitiveResult(
                status=PrimitiveResultStatus.ERROR,
                detail=f"Unknown condition: {condition_fn}",
            )

        count = sum(1 for v in series.values if cmp(v, condition_value))
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=float(count),
        )

    def n_of_last_k(
        self, field_id: str, condition_fn: str,
        condition_value: float, n: int, k: int,
    ) -> PrimitiveResult:
        window = TimeWindow(value=k, unit=TimeUnit.MONTHS)
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err

        cmp = _get_comparator(condition_fn)
        if cmp is None:
            return PrimitiveResult(
                status=PrimitiveResultStatus.ERROR,
                detail=f"Unknown condition: {condition_fn}",
            )

        # Take last k values (or fewer if not enough data)
        last_k = series.values[-k:] if len(series.values) >= k else series.values
        count = sum(1 for v in last_k if cmp(v, condition_value))
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            value=float(count),
            boolean=count >= n,
            detail=f"{count} of {len(last_k)} satisfy {condition_fn} {condition_value}",
        )

    def consecutive_true(
        self, field_id: str, condition_fn: str,
        condition_value: float, n: int,
    ) -> PrimitiveResult:
        window = TimeWindow(value=n + 2, unit=TimeUnit.MONTHS)
        series, err = _require_series(self._store, field_id, window)
        if err:
            return err

        cmp = _get_comparator(condition_fn)
        if cmp is None:
            return PrimitiveResult(
                status=PrimitiveResultStatus.ERROR,
                detail=f"Unknown condition: {condition_fn}",
            )

        values = series.values
        if len(values) < n:
            return PrimitiveResult(
                status=PrimitiveResultStatus.INSUFFICIENT_DATA,
                detail=f"Need {n} points, have {len(values)}",
            )

        # Check last n values
        all_true = all(cmp(v, condition_value) for v in values[-n:])
        return PrimitiveResult(
            status=PrimitiveResultStatus.OK,
            boolean=all_true,
            detail=f"Last {n} values all {condition_fn} {condition_value}: {all_true}",
        )

    # --- Category 8: Named patterns ---

    def evaluate_named_pattern(
        self, pattern_name: str, params: dict,
    ) -> PrimitiveResult:
        evaluator = _NAMED_PATTERN_EVALUATORS.get(pattern_name)
        if evaluator is None:
            return PrimitiveResult(
                status=PrimitiveResultStatus.ERROR,
                detail=f"Unknown named pattern: {pattern_name}",
            )
        return evaluator(params, self._store)


# ---------------------------------------------------------------------------
# Comparator dispatch
# ---------------------------------------------------------------------------

def _get_comparator(name: str):
    """Get a comparison function by name."""
    return {
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
        "eq": lambda a, b: a == b,
    }.get(name)
