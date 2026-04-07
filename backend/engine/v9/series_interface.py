"""v9 series primitive catalogue — interface contract.

This module defines the canonical interface for deterministic series
operations. The runtime evaluator can ONLY perform operations listed here.
If a rule requires an operation not in this catalogue, it must be flagged
at compile/validation time.

Phase 0: Interface definition only.
Phase 1: Implementation against actual time-series data.

The key architectural principle: the compiler maps English onto these
primitives. The primitives are deterministic. The result: English
interpretation happens at compile time, statistics happen at runtime,
and there is zero ambiguity at the boundary.

Primitive categories:
  1. Point-in-time — latest value, value at offset
  2. Change — absolute/percent change over window
  3. Rolling statistics — mean, max, min, std
  4. Historical rank — percentile, new high/low, distance from extreme
  5. Trend — slope, direction, acceleration
  6. Crossover — crossed above/below, relative to moving average
  7. Persistence — count-true, n-of-last-k, consecutive
  8. Named patterns — complex statistical patterns with registered evaluators
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Protocol

from backend.schemas.v9.units import TimeWindow


# ---------------------------------------------------------------------------
# Series data contract — what the runtime receives
# ---------------------------------------------------------------------------

class SeriesData:
    """A time series for one field.

    Wraps a list of (timestamp, value) pairs ordered oldest-to-newest.
    The runtime populates these from the data agent's historical data store.
    Phase 1 will implement the actual data loading; this is the contract.
    """

    def __init__(self, field_id: str, values: list[float], timestamps: list[str] | None = None):
        self.field_id = field_id
        self.values = values
        self.timestamps = timestamps or []

    @property
    def length(self) -> int:
        return len(self.values)

    @property
    def latest(self) -> Optional[float]:
        return self.values[-1] if self.values else None

    @property
    def is_empty(self) -> bool:
        return len(self.values) == 0


class SeriesStore(Protocol):
    """Protocol for the series data provider.

    The runtime evaluator depends on this interface to get time-series data.
    Phase 1 implements this against the data agent's historical store.
    """

    def get_series(self, field_id: str, window: TimeWindow) -> Optional[SeriesData]:
        """Get historical series for a field over a time window.

        Returns None if the field has no series data available.
        """
        ...

    def has_series(self, field_id: str) -> bool:
        """Check whether series data is available for a field."""
        ...


# ---------------------------------------------------------------------------
# Primitive result
# ---------------------------------------------------------------------------

class PrimitiveResultStatus(str, Enum):
    """Outcome of a primitive computation."""
    OK = "ok"                           # computed successfully
    INSUFFICIENT_DATA = "insufficient_data"  # not enough data points
    FIELD_NOT_FOUND = "field_not_found"      # field not in series store
    ERROR = "error"                          # computation error


class PrimitiveResult:
    """Result of a series primitive computation."""

    def __init__(
        self,
        status: PrimitiveResultStatus,
        value: Optional[float] = None,
        boolean: Optional[bool] = None,
        detail: str = "",
    ):
        self.status = status
        self.value = value          # numeric result (for value-returning primitives)
        self.boolean = boolean      # boolean result (for condition-checking primitives)
        self.detail = detail        # human-readable explanation


# ---------------------------------------------------------------------------
# Primitive interface — the catalogue of operations
# ---------------------------------------------------------------------------

class SeriesPrimitiveEngine(ABC):
    """Abstract interface for the series primitive engine.

    The runtime evaluator calls methods on this interface.
    Phase 1 provides the concrete implementation.

    Each method returns a PrimitiveResult, never raises for missing data.
    Missing data -> PrimitiveResult with status != OK.
    """

    # --- Category 1: Point-in-time ---

    @abstractmethod
    def latest_value(self, field_id: str) -> PrimitiveResult:
        """Get the most recent value for a field."""
        ...

    @abstractmethod
    def value_at_offset(self, field_id: str, offset: int) -> PrimitiveResult:
        """Get the value N periods back from the latest."""
        ...

    # --- Category 2: Change ---

    @abstractmethod
    def absolute_change(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        """Compute absolute change: latest - value_at(window_ago)."""
        ...

    @abstractmethod
    def percent_change(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        """Compute percent change over window."""
        ...

    # --- Category 3: Rolling statistics ---

    @abstractmethod
    def rolling_max(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        """Maximum value over the lookback window."""
        ...

    @abstractmethod
    def rolling_min(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        """Minimum value over the lookback window."""
        ...

    @abstractmethod
    def rolling_mean(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        """Mean value over the lookback window."""
        ...

    # --- Category 4: Historical rank ---

    @abstractmethod
    def percentile_rank(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        """Current value's percentile rank within the lookback window.

        Returns value in [0.0, 1.0].
        """
        ...

    @abstractmethod
    def is_at_extreme(
        self, field_id: str, extreme: str, window: TimeWindow,
        margin: float = 0.0,
    ) -> PrimitiveResult:
        """Check if current value is at or near a historical extreme.

        extreme: "high" or "low"
        margin: tolerance (e.g., 0.10 = within 10% of extreme)
        """
        ...

    @abstractmethod
    def distance_from_extreme(
        self, field_id: str, extreme: str, window: TimeWindow,
    ) -> PrimitiveResult:
        """Compute distance from historical extreme as a fraction.

        Returns (current - extreme) / abs(extreme) for high,
        or (extreme - current) / abs(extreme) for low.
        """
        ...

    # --- Category 5: Trend ---

    @abstractmethod
    def trend_direction(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        """Determine trend direction over window.

        Returns boolean=True if trend matches, with detail indicating
        the direction ("rising", "falling", "stable").
        """
        ...

    @abstractmethod
    def slope(self, field_id: str, window: TimeWindow) -> PrimitiveResult:
        """Compute linear regression slope over window."""
        ...

    # --- Category 6: Crossover ---

    @abstractmethod
    def crossed_above(
        self, field_a: str, field_b: str, window: TimeWindow,
    ) -> PrimitiveResult:
        """Check if field_a crossed above field_b within the window."""
        ...

    @abstractmethod
    def crossed_below(
        self, field_a: str, field_b: str, window: TimeWindow,
    ) -> PrimitiveResult:
        """Check if field_a crossed below field_b within the window."""
        ...

    @abstractmethod
    def above_moving_average(
        self, field_id: str, ma_window: TimeWindow,
    ) -> PrimitiveResult:
        """Check if current value is above the moving average."""
        ...

    # --- Category 7: Persistence ---

    @abstractmethod
    def count_true(
        self, field_id: str, condition_fn: str,
        condition_value: float, window: TimeWindow,
    ) -> PrimitiveResult:
        """Count periods where condition is true within window.

        condition_fn: "gt", "lt", "gte", "lte", "eq"
        Returns value = count of true periods.
        """
        ...

    @abstractmethod
    def n_of_last_k(
        self, field_id: str, condition_fn: str,
        condition_value: float, n: int, k: int,
    ) -> PrimitiveResult:
        """Check if condition was true for at least n of last k periods.

        Returns boolean = True if count >= n.
        """
        ...

    @abstractmethod
    def consecutive_true(
        self, field_id: str, condition_fn: str,
        condition_value: float, n: int,
    ) -> PrimitiveResult:
        """Check if condition was true for n consecutive recent periods.

        Returns boolean = True if the last n periods all satisfy the condition.
        """
        ...

    # --- Category 8: Named patterns ---

    @abstractmethod
    def evaluate_named_pattern(
        self, pattern_name: str, params: dict,
    ) -> PrimitiveResult:
        """Evaluate a registered named pattern.

        Named patterns are complex statistical patterns that don't decompose
        cleanly into the primitives above. Each pattern has a registered
        evaluator that takes pattern-specific parameters.

        Known patterns:
          - sahm_rule: 3-month MA of unemployment rising 0.50%+ above 12-month low
          - resteepened_after_inversion: yield curve re-steepened after deep inversion
          - breakout_after_range: price breakout after consolidation range

        Returns PrimitiveResult with status=ERROR if pattern_name is not registered.
        """
        ...


# ---------------------------------------------------------------------------
# Primitive inventory — the closed set of operations
# ---------------------------------------------------------------------------

PRIMITIVE_CATALOGUE: dict[str, str] = {
    # Category 1: Point-in-time
    "latest_value": "Get the most recent value for a field",
    "value_at_offset": "Get the value N periods back",

    # Category 2: Change
    "absolute_change": "Absolute change over window",
    "percent_change": "Percent change over window",

    # Category 3: Rolling statistics
    "rolling_max": "Maximum over lookback window",
    "rolling_min": "Minimum over lookback window",
    "rolling_mean": "Mean over lookback window",

    # Category 4: Historical rank
    "percentile_rank": "Percentile rank within lookback",
    "is_at_extreme": "At or near historical high/low",
    "distance_from_extreme": "Fractional distance from extreme",

    # Category 5: Trend
    "trend_direction": "Rising/falling/stable classification",
    "slope": "Linear regression slope",

    # Category 6: Crossover
    "crossed_above": "Field A crossed above field B",
    "crossed_below": "Field A crossed below field B",
    "above_moving_average": "Current value above MA",

    # Category 7: Persistence
    "count_true": "Count of periods where condition is true",
    "n_of_last_k": "At least n of last k periods satisfy condition",
    "consecutive_true": "Last n periods all satisfy condition",

    # Category 8: Named patterns
    "evaluate_named_pattern": "Complex statistical pattern with registered evaluator",
}

# The set of primitive names — for validation that rules only reference
# operations that exist in the catalogue.
SUPPORTED_PRIMITIVES: frozenset[str] = frozenset(PRIMITIVE_CATALOGUE.keys())
