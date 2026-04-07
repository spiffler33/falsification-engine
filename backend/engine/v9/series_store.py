"""v9 SeriesStore: concrete in-memory time-series data provider.

Implements the SeriesStore protocol from series_interface.py.
Stores (field_id -> sorted list of (date, value) tuples) in memory.

The compiled evaluator's temporal primitives (trend, persistence,
historical_extreme, delta_change, named_pattern) all route through
BriefingSeriesEngine, which delegates data retrieval to this store.

This module is purely a data container. It does NOT compute primitives --
that's series_engine.py. It does NOT decide what data to fetch --
that's the data agent's job (future live wiring phase).

Usage:
    store = InMemorySeriesStore()
    store.add_series("growth.unemployment", dates, values)
    evaluator = RuleEvaluator(briefing, registry=reg, series_store=store)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from backend.engine.v9.series_interface import SeriesData, SeriesStore
from backend.schemas.v9.units import TimeUnit, TimeWindow


# ---------------------------------------------------------------------------
# Window conversion helpers
# ---------------------------------------------------------------------------

_UNIT_TO_DAYS: dict[TimeUnit, int] = {
    TimeUnit.DAYS: 1,
    TimeUnit.WEEKS: 7,
    TimeUnit.MONTHS: 30,
    TimeUnit.QUARTERS: 90,
    TimeUnit.YEARS: 365,
}


def _window_to_days(window: TimeWindow) -> int:
    """Convert a TimeWindow to approximate number of calendar days."""
    return window.value * _UNIT_TO_DAYS.get(window.unit, 30)


def _parse_date(s: str) -> date:
    """Parse an ISO date string (YYYY-MM-DD) to a date object."""
    return date.fromisoformat(s)


# ---------------------------------------------------------------------------
# InMemorySeriesStore
# ---------------------------------------------------------------------------

class InMemorySeriesStore:
    """Concrete SeriesStore backed by an in-memory dict.

    Storage format:
        _data[field_id] = [(date_str, value), ...] sorted oldest-first

    Implements the SeriesStore protocol so it can be passed directly
    to RuleEvaluator(series_store=store).
    """

    def __init__(self) -> None:
        self._data: dict[str, list[tuple[str, float]]] = {}

    # -- SeriesStore protocol --

    def get_series(self, field_id: str, window: TimeWindow) -> Optional[SeriesData]:
        """Get historical series for a field over a time window.

        Slices the stored data to the requested window by computing a
        date cutoff from the latest data point. Returns None if no data
        exists for the field.
        """
        raw = self._data.get(field_id)
        if not raw:
            return None

        latest_date = _parse_date(raw[-1][0])
        cutoff = latest_date - timedelta(days=_window_to_days(window))

        filtered = [(ts, v) for ts, v in raw if _parse_date(ts) >= cutoff]
        if not filtered:
            return None

        timestamps = [ts for ts, _ in filtered]
        values = [v for _, v in filtered]
        return SeriesData(field_id=field_id, values=values, timestamps=timestamps)

    def has_series(self, field_id: str) -> bool:
        """Check whether series data is available for a field."""
        return field_id in self._data and len(self._data[field_id]) > 0

    # -- Data loading --

    def add_series(
        self,
        field_id: str,
        timestamps: list[str],
        values: list[float],
    ) -> None:
        """Add a time series for a field.

        timestamps: list of ISO date strings (YYYY-MM-DD)
        values: corresponding float values

        Data is sorted oldest-first. If the field already has data,
        it is replaced entirely.
        """
        if len(timestamps) != len(values):
            raise ValueError(
                f"timestamps ({len(timestamps)}) and values ({len(values)}) "
                f"must have the same length"
            )
        pairs = sorted(zip(timestamps, values), key=lambda p: p[0])
        self._data[field_id] = [(ts, v) for ts, v in pairs]

    def load_from_dict(self, data: dict[str, dict[str, float]]) -> None:
        """Bulk load series data from a nested dict.

        Format:
            {
                "growth.unemployment": {
                    "2024-01-01": 3.7,
                    "2024-02-01": 3.9,
                    ...
                },
                ...
            }

        Each inner dict maps ISO date strings to float values.
        """
        for field_id, date_values in data.items():
            timestamps = list(date_values.keys())
            values = list(date_values.values())
            self.add_series(field_id, timestamps, values)

    # -- Introspection --

    @property
    def field_ids(self) -> list[str]:
        """List all field IDs with data loaded."""
        return sorted(self._data.keys())

    def series_length(self, field_id: str) -> int:
        """Number of data points stored for a field."""
        return len(self._data.get(field_id, []))
