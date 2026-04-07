# V9 SeriesStore Design

## Purpose

The SeriesStore is the runtime data provider that feeds time-series values to the
compiled evaluator's temporal primitives (trend, persistence, historical_extreme,
delta_change, named_pattern). Without it, 33 indicators across all 8 theories return
NOT_EVALUABLE, and the compound cascade makes this worse: a compound rule with 3
scalar clauses and 1 trend clause returns NOT_EVALUABLE for the whole thing.

## Temporal Indicator Inventory

**33 indicators require time-series data**, distributed across 5 primitive types:

| Primitive Type     | Pure | In Compound | Total Uses | Engine Method(s)           |
|--------------------|------|-------------|------------|----------------------------|
| trend_state        | 3    | 14          | 17         | trend_direction            |
| persistence        | 7    | 2           | 9          | consecutive_true, n_of_last_k |
| historical_extreme | 3    | 2           | 5          | is_at_extreme              |
| delta_change       | 0    | 4           | 4          | absolute_change, percent_change |
| named_pattern      | 2    | 0           | 2          | evaluate_named_pattern     |

**All 5 primitive types are already implemented** in `series_engine.py`.
The gap is purely the data provider: no concrete `SeriesStore` exists.

**26 unique field IDs** need series data. Most theories need 3-5 fields.
Two fields are shared across theories: `cb_gold_purchases` (fiscal_dominance_arithmetic
+ monetary_architecture) and `growth.unemployment` (debt_cycle_short +
fiscal_dominance_liquidity).

### Impact by Theory

| Theory                       | Temporal Indicators | Theories Affected If Unblocked |
|------------------------------|--------------------:|-------------------------------|
| debt_cycle_short             | 10                  | Both phases                   |
| capital_flows                | 5                   | Rotation phase goes evaluable |
| fiscal_dominance_liquidity   | 5                   | 5 of 8 indicators             |
| monetary_architecture        | 3 (+ 1 shared)     | All 3 shared indicators       |
| structural_fragility         | 2                   | 2 Building-phase indicators   |
| valuation_mean_reversion     | 2                   | 2 of 8 indicators             |
| fiscal_dominance_arithmetic  | 1 (+ 1 shared)     | gold_purchases indicator      |
| debt_cycle_long              | 1                   | ELB indicator                 |

## Data Model

### InMemorySeriesStore

A concrete implementation of the `SeriesStore` protocol that stores time-series
data in memory as `{field_id: [(timestamp, value), ...]}` sorted oldest-to-newest.

```
class InMemorySeriesStore:
    """Concrete SeriesStore backed by in-memory dict.

    Implements the SeriesStore protocol from series_interface.py.
    Data is loaded via add_series() or bulk load_from_dict().

    Storage: dict[str, list[tuple[str, float]]]
      key = field_id (e.g., "growth.unemployment")
      value = list of (ISO date string, float value), sorted oldest-first
    """

    def get_series(field_id, window) -> SeriesData | None
    def has_series(field_id) -> bool
    def add_series(field_id, timestamps, values) -> None
    def load_from_dict(data: dict[str, dict[str, float]]) -> None
```

### Why In-Memory (Not SQLite)

1. The activation pass runs once per briefing cycle (not real-time)
2. 26 fields x ~240 monthly observations = ~6,240 data points = negligible memory
3. SQLite adds complexity (schema migration, file locking) with zero benefit at this scale
4. Future: if live data wiring adds 1000+ daily-frequency fields, reconsider

### Window-to-Slice Logic

`get_series(field_id, window)` converts the `TimeWindow` to a date cutoff:
- Compute `cutoff = latest_timestamp - window_to_days(window)`
- Filter stored points to `[cutoff, latest]`
- Return as `SeriesData(field_id, values, timestamps)`

This reuses the existing `_window_to_periods()` logic from `series_engine.py`
but operates on actual dates rather than period counts, making it calendar-aware.

## Interface Contract

The `InMemorySeriesStore` implements the `SeriesStore` protocol defined in
`series_interface.py` (lines 65-77):

```python
class SeriesStore(Protocol):
    def get_series(self, field_id: str, window: TimeWindow) -> Optional[SeriesData]: ...
    def has_series(self, field_id: str) -> bool: ...
```

### Wiring into the Evaluator

The `RuleEvaluator.__init__()` already accepts `series_store: Optional[SeriesStore]`.
When provided, it wraps it in a `BriefingSeriesEngine`. No changes to rule_evaluator.py
or series_engine.py are needed.

```python
# Existing code in rule_evaluator.py:
store = InMemorySeriesStore()
store.load_from_dict(historical_data)
evaluator = RuleEvaluator(briefing, registry=registry, series_store=store)
```

## Freshness Policy (HUMAN DECISION REQUIRED)

**Question:** How stale can time-series data be before Pass 1 refuses to score a
temporal indicator?

Options:
- **Strict (recommended for v1):** If the latest data point for a field is older
  than 2x the field's natural frequency (e.g., >60 days for monthly data),
  return INSUFFICIENT_DATA. This prevents scoring on dangerously stale data.
- **Permissive:** Score with whatever is available, annotate staleness in the
  result detail. Trust the human to notice.
- **Configurable:** Accept a staleness_policy parameter. Default to strict.

**Current implementation:** No staleness check. The InMemorySeriesStore returns
whatever data it has. This is the simplest starting point for synthetic testing.
Staleness policy should be added when live data wiring happens.

## Resolution and Frequency

Different indicators need different time resolutions:

| Window Range     | Fields (examples)               | Resolution Needed |
|------------------|---------------------------------|-------------------|
| 1-3 months       | TGA, RRP, Fed BS                | Daily/weekly      |
| 3-12 months      | Unemployment, ISM, spreads      | Monthly           |
| 1-3 years        | Gold purchases, DXY             | Monthly           |
| 10-20 years      | Fed funds ELB, margin debt      | Monthly           |

**Decision:** Store at monthly resolution for v1. The `_window_to_periods()` helper
already handles conversion. Daily resolution can be added later for short-window
fields without changing the interface.

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `backend/engine/v9/series_store.py` | CREATE | InMemorySeriesStore implementation |
| `backend/tests/test_v9_series_store.py` | CREATE | Synthetic fixtures + primitive tests |
| `docs/V9_SERIESSTORE_DESIGN.md` | CREATE | This document |

No modifications to existing files. The store plugs into the existing
`RuleEvaluator(series_store=...)` parameter.
