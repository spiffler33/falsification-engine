"""v9 SeriesStore: synthetic test harness.

Tests the InMemorySeriesStore and validates that temporal primitives
produce correct results when backed by synthetic series data.

Test categories:
  1. InMemorySeriesStore basics (load, slice, has_series)
  2. Trend primitives via BriefingSeriesEngine
  3. Persistence primitives (consecutive, n_of_last_k)
  4. Historical extreme primitives
  5. Delta change primitives (absolute + percent)
  6. Named pattern primitives (sahm_rule, resteepened_after_inversion)
  7. End-to-end: monetary_architecture compiled artifact evaluation
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from backend.engine.v9.series_store import InMemorySeriesStore
from backend.engine.v9.series_engine import BriefingSeriesEngine
from backend.engine.v9.series_interface import (
    PrimitiveResult,
    PrimitiveResultStatus,
    SeriesData,
)
from backend.schemas.v9.units import TimeUnit, TimeWindow


# ===================================================================
# Synthetic data builders
# ===================================================================

def _monthly_dates(n: int, end: str = "2026-03-01") -> list[str]:
    """Generate n monthly date strings ending at `end`, oldest first."""
    end_date = date.fromisoformat(end)
    dates = []
    for i in range(n - 1, -1, -1):
        d = end_date - timedelta(days=30 * i)
        dates.append(d.isoformat())
    return dates


def _rising_series(n: int, start: float = 10.0, step: float = 1.0) -> list[float]:
    """Monotonically rising series."""
    return [start + step * i for i in range(n)]


def _falling_series(n: int, start: float = 100.0, step: float = 2.0) -> list[float]:
    """Monotonically falling series."""
    return [start - step * i for i in range(n)]


def _flat_series(n: int, value: float = 50.0) -> list[float]:
    """Constant series."""
    return [value] * n


def _oscillating_series(n: int, low: float = 30.0, high: float = 70.0) -> list[float]:
    """Alternating low/high values."""
    return [low if i % 2 == 0 else high for i in range(n)]


# ===================================================================
# 1. InMemorySeriesStore basics
# ===================================================================

class TestInMemorySeriesStoreBasics:
    """Tests for the data container itself."""

    def test_empty_store_has_no_series(self):
        store = InMemorySeriesStore()
        assert not store.has_series("growth.unemployment")
        assert store.get_series("growth.unemployment", TimeWindow(value=3, unit=TimeUnit.MONTHS)) is None

    def test_add_and_retrieve_series(self):
        store = InMemorySeriesStore()
        dates = _monthly_dates(6)
        values = _rising_series(6)
        store.add_series("growth.unemployment", dates, values)

        assert store.has_series("growth.unemployment")
        assert store.series_length("growth.unemployment") == 6

        series = store.get_series("growth.unemployment", TimeWindow(value=12, unit=TimeUnit.MONTHS))
        assert series is not None
        assert series.field_id == "growth.unemployment"
        assert len(series.values) == 6

    def test_window_slicing(self):
        """Requesting a 3-month window from a 12-month series returns ~3 months."""
        store = InMemorySeriesStore()
        dates = _monthly_dates(12)
        values = _rising_series(12)
        store.add_series("test.field", dates, values)

        series = store.get_series("test.field", TimeWindow(value=3, unit=TimeUnit.MONTHS))
        assert series is not None
        # 3 months = ~90 days. With ~30-day spacing, expect ~3 points
        assert 2 <= len(series.values) <= 4

    def test_load_from_dict(self):
        store = InMemorySeriesStore()
        data = {
            "field_a": {"2026-01-01": 10.0, "2026-02-01": 20.0, "2026-03-01": 30.0},
            "field_b": {"2026-01-01": 100.0, "2026-02-01": 90.0},
        }
        store.load_from_dict(data)

        assert store.has_series("field_a")
        assert store.has_series("field_b")
        assert store.series_length("field_a") == 3
        assert store.series_length("field_b") == 2

    def test_add_series_sorts_oldest_first(self):
        store = InMemorySeriesStore()
        # Add in reverse order
        store.add_series("f", ["2026-03-01", "2026-01-01", "2026-02-01"], [30.0, 10.0, 20.0])

        series = store.get_series("f", TimeWindow(value=12, unit=TimeUnit.MONTHS))
        assert series.values == [10.0, 20.0, 30.0]

    def test_add_series_length_mismatch_raises(self):
        store = InMemorySeriesStore()
        with pytest.raises(ValueError, match="same length"):
            store.add_series("f", ["2026-01-01", "2026-02-01"], [1.0])

    def test_field_ids_property(self):
        store = InMemorySeriesStore()
        store.load_from_dict({
            "z.field": {"2026-01-01": 1.0},
            "a.field": {"2026-01-01": 2.0},
        })
        assert store.field_ids == ["a.field", "z.field"]

    def test_replace_series_on_second_add(self):
        store = InMemorySeriesStore()
        store.add_series("f", ["2026-01-01"], [10.0])
        store.add_series("f", ["2026-01-01", "2026-02-01"], [20.0, 30.0])
        assert store.series_length("f") == 2


# ===================================================================
# Fixtures for primitive tests
# ===================================================================

@pytest.fixture
def rising_store():
    """Store with a 24-month rising series for several fields."""
    store = InMemorySeriesStore()
    dates = _monthly_dates(24)
    store.add_series("growth.unemployment", dates, _rising_series(24, start=3.5, step=0.1))
    store.add_series("credit.hy_spread", dates, _rising_series(24, start=200, step=20))
    store.add_series("rates.fed_funds", dates, _rising_series(24, start=0.25, step=0.2))
    store.add_series("dxy_index", dates, _rising_series(24, start=95, step=0.5))
    return store


@pytest.fixture
def falling_store():
    """Store with a 24-month falling series."""
    store = InMemorySeriesStore()
    dates = _monthly_dates(24)
    store.add_series("foreign_treasury_holdings_pct", dates, _falling_series(24, start=30.0, step=0.5))
    store.add_series("liquidity.reverse_repo", dates, _falling_series(24, start=2000000, step=80000))
    store.add_series("usdcny", dates, _falling_series(24, start=7.2, step=0.05))
    return store


@pytest.fixture
def persistence_store():
    """Store with series designed to test persistence patterns."""
    store = InMemorySeriesStore()
    dates = _monthly_dates(12)
    # Fed funds consistently above 4.0 for last 6 months
    store.add_series("rates.fed_funds", dates,
                     [2.0, 2.5, 3.0, 3.5, 3.8, 3.9, 5.0, 5.25, 5.33, 5.33, 5.33, 5.33])
    # Net liquidity: positive in 2 of last 3
    store.add_series("net_liquidity_30d_change", dates,
                     [10, -5, 20, -30, 15, -10, 25, -8, 12, 30, -5, 20])
    # CB gold purchases: above 800 for last 3 years (but we only have 12 months)
    store.add_series("cb_gold_purchases", dates,
                     [850, 860, 870, 880, 890, 900, 910, 920, 930, 940, 950, 960])
    # Insider sell/buy: above 2.0 for last 3 consecutive months
    store.add_series("insider_sell_buy_ratio", dates,
                     [1.5, 1.8, 1.6, 1.9, 1.7, 2.0, 1.8, 2.1, 2.3, 2.5, 2.4, 2.6])
    return store


@pytest.fixture
def extreme_store():
    """Store with series at historical extremes."""
    store = InMemorySeriesStore()
    dates = _monthly_dates(36)
    # QQQ/IWM ratio: rising to new 24-month high at end
    qqq_iwm = _rising_series(36, start=1.5, step=0.03)
    store.add_series("qqq_iwm_ratio", dates, qqq_iwm)
    # FINRA margin debt: at 20-year high (we approximate with 36 months)
    margin = _flat_series(34, value=500) + [600, 650]  # spike at end
    store.add_series("finra_margin_debt", dates, margin)
    # Fed funds near ELB (historical low)
    fed_low = [0.25] * 30 + _rising_series(6, start=0.5, step=0.5)
    store.add_series("rates.fed_funds", dates, fed_low)
    return store


# ===================================================================
# 2. Trend primitives
# ===================================================================

class TestTrendPrimitives:
    """Tests for trend_direction via BriefingSeriesEngine."""

    def test_rising_trend_detected(self, rising_store):
        engine = BriefingSeriesEngine(rising_store)
        result = engine.trend_direction("growth.unemployment", TimeWindow(value=6, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.OK
        assert result.detail == "rising"

    def test_falling_trend_detected(self, falling_store):
        engine = BriefingSeriesEngine(falling_store)
        result = engine.trend_direction("foreign_treasury_holdings_pct", TimeWindow(value=12, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.OK
        assert result.detail == "falling"

    def test_flat_series_is_stable(self):
        store = InMemorySeriesStore()
        dates = _monthly_dates(12)
        store.add_series("flat", dates, _flat_series(12, value=50.0))
        engine = BriefingSeriesEngine(store)
        result = engine.trend_direction("flat", TimeWindow(value=6, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.OK
        assert result.detail == "stable"

    def test_missing_field_returns_not_found(self, rising_store):
        engine = BriefingSeriesEngine(rising_store)
        result = engine.trend_direction("nonexistent.field", TimeWindow(value=3, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.FIELD_NOT_FOUND

    def test_slope_positive_for_rising(self, rising_store):
        engine = BriefingSeriesEngine(rising_store)
        result = engine.slope("rates.fed_funds", TimeWindow(value=6, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.OK
        assert result.value > 0

    def test_slope_negative_for_falling(self, falling_store):
        engine = BriefingSeriesEngine(falling_store)
        result = engine.slope("usdcny", TimeWindow(value=6, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.OK
        assert result.value < 0


# ===================================================================
# 3. Persistence primitives
# ===================================================================

class TestPersistencePrimitives:
    """Tests for consecutive_true and n_of_last_k."""

    def test_consecutive_true_positive(self, persistence_store):
        """Fed funds above 4.0 for last 6 consecutive months."""
        engine = BriefingSeriesEngine(persistence_store)
        result = engine.consecutive_true("rates.fed_funds", "gt", 4.0, 6)
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is True

    def test_consecutive_true_negative(self, persistence_store):
        """Fed funds NOT above 4.0 for 12 consecutive months."""
        engine = BriefingSeriesEngine(persistence_store)
        result = engine.consecutive_true("rates.fed_funds", "gt", 4.0, 12)
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is False

    def test_n_of_last_k_positive(self, persistence_store):
        """Net liquidity positive in 2 of last 3 months."""
        engine = BriefingSeriesEngine(persistence_store)
        result = engine.n_of_last_k("net_liquidity_30d_change", "gt", 0, 2, 3)
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is True

    def test_n_of_last_k_negative(self, persistence_store):
        """Net liquidity NOT positive in 3 of last 3."""
        engine = BriefingSeriesEngine(persistence_store)
        result = engine.n_of_last_k("net_liquidity_30d_change", "gt", 0, 3, 3)
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is False

    def test_count_true(self, persistence_store):
        """Count months where gold purchases > 800."""
        engine = BriefingSeriesEngine(persistence_store)
        window = TimeWindow(value=12, unit=TimeUnit.MONTHS)
        result = engine.count_true("cb_gold_purchases", "gt", 800, window)
        assert result.status == PrimitiveResultStatus.OK
        assert result.value >= 10  # all 12 months above 800

    def test_persistence_missing_field(self, persistence_store):
        engine = BriefingSeriesEngine(persistence_store)
        result = engine.consecutive_true("nonexistent", "gt", 0, 3)
        assert result.status == PrimitiveResultStatus.FIELD_NOT_FOUND


# ===================================================================
# 4. Historical extreme primitives
# ===================================================================

class TestHistoricalExtremePrimitives:
    """Tests for is_at_extreme and related."""

    def test_at_high_extreme(self, extreme_store):
        """QQQ/IWM ratio at 24-month high."""
        engine = BriefingSeriesEngine(extreme_store)
        result = engine.is_at_extreme(
            "qqq_iwm_ratio", "high",
            TimeWindow(value=24, unit=TimeUnit.MONTHS),
        )
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is True

    def test_not_at_low_extreme(self, extreme_store):
        """QQQ/IWM ratio NOT at 24-month low (it's at the high)."""
        engine = BriefingSeriesEngine(extreme_store)
        result = engine.is_at_extreme(
            "qqq_iwm_ratio", "low",
            TimeWindow(value=24, unit=TimeUnit.MONTHS),
        )
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is False

    def test_near_high_with_margin(self, extreme_store):
        """FINRA margin debt within 10% of 36-month high."""
        engine = BriefingSeriesEngine(extreme_store)
        result = engine.is_at_extreme(
            "finra_margin_debt", "high",
            TimeWindow(value=36, unit=TimeUnit.MONTHS),
            margin=0.10,
        )
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is True

    def test_percentile_rank_high(self, extreme_store):
        """QQQ/IWM ratio should have high percentile rank."""
        engine = BriefingSeriesEngine(extreme_store)
        result = engine.percentile_rank(
            "qqq_iwm_ratio",
            TimeWindow(value=24, unit=TimeUnit.MONTHS),
        )
        assert result.status == PrimitiveResultStatus.OK
        assert result.value > 0.9  # near top


# ===================================================================
# 5. Delta change primitives
# ===================================================================

class TestDeltaChangePrimitives:
    """Tests for absolute_change and percent_change."""

    def test_absolute_change_rising(self, rising_store):
        engine = BriefingSeriesEngine(rising_store)
        result = engine.absolute_change("rates.fed_funds", TimeWindow(value=6, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.OK
        assert result.value > 0

    def test_absolute_change_falling(self, falling_store):
        engine = BriefingSeriesEngine(falling_store)
        result = engine.absolute_change("liquidity.reverse_repo", TimeWindow(value=3, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.OK
        assert result.value < 0

    def test_percent_change_rising(self, rising_store):
        engine = BriefingSeriesEngine(rising_store)
        result = engine.percent_change("rates.fed_funds", TimeWindow(value=12, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.OK
        assert result.value > 0

    def test_percent_change_flat(self):
        store = InMemorySeriesStore()
        dates = _monthly_dates(6)
        store.add_series("flat", dates, _flat_series(6, 100.0))
        engine = BriefingSeriesEngine(store)
        result = engine.percent_change("flat", TimeWindow(value=3, unit=TimeUnit.MONTHS))
        assert result.status == PrimitiveResultStatus.OK
        assert result.value == 0.0


# ===================================================================
# 6. Named pattern primitives
# ===================================================================

class TestNamedPatternPrimitives:
    """Tests for Sahm Rule and resteepened_after_inversion."""

    def test_sahm_rule_triggered(self):
        """Unemployment rising sharply -> Sahm Rule triggers."""
        store = InMemorySeriesStore()
        dates = _monthly_dates(18)
        # Low unemployment, then sharp rise in last 3 months
        values = [3.5] * 12 + [3.6, 3.7, 3.8, 4.0, 4.2, 4.5]
        store.add_series("growth.unemployment", dates, values)

        engine = BriefingSeriesEngine(store)
        result = engine.evaluate_named_pattern("sahm_rule", {
            "field": "growth.unemployment",
            "threshold": 0.50,
        })
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is True
        assert result.value >= 0.50

    def test_sahm_rule_not_triggered(self):
        """Stable unemployment -> Sahm Rule does not trigger."""
        store = InMemorySeriesStore()
        dates = _monthly_dates(18)
        values = _flat_series(18, value=3.5)
        store.add_series("growth.unemployment", dates, values)

        engine = BriefingSeriesEngine(store)
        result = engine.evaluate_named_pattern("sahm_rule", {
            "field": "growth.unemployment",
            "threshold": 0.50,
        })
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is False

    def test_resteepened_after_inversion_triggered(self):
        """Deep inversion then recovery -> pattern triggers."""
        store = InMemorySeriesStore()
        dates = _monthly_dates(24)
        # Normal -> deep inversion -> recovery
        values = (
            [0.5, 0.3, 0.0, -0.2, -0.5, -0.8, -1.0, -0.9]  # inversion
            + [-0.7, -0.4, -0.1, 0.1, 0.3, 0.5, 0.7, 0.8]  # recovery
            + [0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]      # steep positive
        )
        store.add_series("rates.curve_2s10s", dates, values)

        engine = BriefingSeriesEngine(store)
        result = engine.evaluate_named_pattern("resteepened_after_inversion", {
            "field": "rates.curve_2s10s",
            "inversion_threshold": -0.50,
            "resteepen_delta": 0.75,
        })
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is True

    def test_resteepened_not_triggered_no_inversion(self):
        """Positive curve throughout -> pattern does not trigger."""
        store = InMemorySeriesStore()
        dates = _monthly_dates(24)
        values = _flat_series(24, value=1.0)
        store.add_series("rates.curve_2s10s", dates, values)

        engine = BriefingSeriesEngine(store)
        result = engine.evaluate_named_pattern("resteepened_after_inversion", {
            "field": "rates.curve_2s10s",
            "inversion_threshold": -0.50,
            "resteepen_delta": 0.75,
        })
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is False

    def test_unknown_pattern_returns_error(self):
        store = InMemorySeriesStore()
        engine = BriefingSeriesEngine(store)
        result = engine.evaluate_named_pattern("nonexistent_pattern", {})
        assert result.status == PrimitiveResultStatus.ERROR


# ===================================================================
# 7. Rule evaluator integration with InMemorySeriesStore
# ===================================================================

class TestRuleEvaluatorWithSeriesStore:
    """Tests that the rule evaluator correctly dispatches temporal rules
    to the series engine when backed by InMemorySeriesStore."""

    def test_trend_rule_evaluable_with_store(self, falling_store):
        from backend.engine.v9.rule_evaluator import RuleEvaluator, RuleOutcome
        from backend.schemas.v9.rules import TrendStateRule, TrendDirection, FieldOperand
        from backend.schemas.v9.units import ValueUnit, SemanticType
        from backend.schemas.briefing import BriefingPacket

        briefing = BriefingPacket(timestamp="2026-03-01T00:00:00Z")
        evaluator = RuleEvaluator(briefing, series_store=falling_store)

        rule = TrendStateRule(
            field=FieldOperand(field_id="foreign_treasury_holdings_pct", unit=ValueUnit.PERCENT, semantic_type=SemanticType.SHARE_OF_TOTAL),
            direction=TrendDirection.FALLING,
            window=TimeWindow(value=12, unit=TimeUnit.MONTHS),
        )
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.TRUE

    def test_trend_rule_not_evaluable_without_store(self):
        from backend.engine.v9.rule_evaluator import RuleEvaluator, RuleOutcome
        from backend.schemas.v9.rules import TrendStateRule, TrendDirection, FieldOperand
        from backend.schemas.v9.units import ValueUnit, SemanticType
        from backend.schemas.briefing import BriefingPacket

        briefing = BriefingPacket(timestamp="2026-03-01T00:00:00Z")
        evaluator = RuleEvaluator(briefing, series_store=None)

        rule = TrendStateRule(
            field=FieldOperand(field_id="foreign_treasury_holdings_pct", unit=ValueUnit.PERCENT, semantic_type=SemanticType.SHARE_OF_TOTAL),
            direction=TrendDirection.FALLING,
            window=TimeWindow(value=12, unit=TimeUnit.MONTHS),
        )
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.NOT_EVALUABLE

    def test_persistence_rule_evaluable_with_store(self, persistence_store):
        from backend.engine.v9.rule_evaluator import RuleEvaluator, RuleOutcome
        from backend.schemas.v9.rules import (
            PersistenceRule, PersistenceMode,
            ScalarComparisonRule, Comparator, FieldOperand, LiteralOperand,
        )
        from backend.schemas.v9.units import ValueUnit, SemanticType
        from backend.schemas.briefing import BriefingPacket

        briefing = BriefingPacket(timestamp="2026-03-01T00:00:00Z")
        evaluator = RuleEvaluator(briefing, series_store=persistence_store)

        rule = PersistenceRule(
            condition=ScalarComparisonRule(
                field=FieldOperand(field_id="rates.fed_funds", unit=ValueUnit.PERCENT, semantic_type=SemanticType.RATE),
                comparator=Comparator.GT,
                threshold=LiteralOperand(value=4.0, unit=ValueUnit.PERCENT),
            ),
            mode=PersistenceMode.CONSECUTIVE,
            n=6,
            window=TimeWindow(value=6, unit=TimeUnit.MONTHS),
        )
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.TRUE

    def test_delta_change_rule_evaluable_with_store(self, falling_store):
        from backend.engine.v9.rule_evaluator import RuleEvaluator, RuleOutcome
        from backend.schemas.v9.rules import (
            DeltaChangeRule, DeltaMode, TrendDirection,
            FieldOperand, LiteralOperand,
        )
        from backend.schemas.v9.units import ValueUnit, SemanticType
        from backend.schemas.briefing import BriefingPacket

        briefing = BriefingPacket(timestamp="2026-03-01T00:00:00Z")
        evaluator = RuleEvaluator(briefing, series_store=falling_store)

        rule = DeltaChangeRule(
            field=FieldOperand(field_id="liquidity.reverse_repo", unit=ValueUnit.USD_MILLIONS, semantic_type=SemanticType.BALANCE),
            direction=TrendDirection.FALLING,
            magnitude=LiteralOperand(value=100000, unit=ValueUnit.USD_MILLIONS),
            mode=DeltaMode.ABSOLUTE,
            window=TimeWindow(value=3, unit=TimeUnit.MONTHS),
        )
        result = evaluator.evaluate(rule)
        assert result.outcome in (RuleOutcome.TRUE, RuleOutcome.FALSE)
        assert result.outcome != RuleOutcome.NOT_EVALUABLE

    def test_historical_extreme_rule_evaluable_with_store(self, extreme_store):
        from backend.engine.v9.rule_evaluator import RuleEvaluator, RuleOutcome
        from backend.schemas.v9.rules import (
            HistoricalExtremeRule, ExtremeType, Comparator,
            FieldOperand,
        )
        from backend.schemas.v9.units import ValueUnit, SemanticType
        from backend.schemas.briefing import BriefingPacket

        briefing = BriefingPacket(timestamp="2026-03-01T00:00:00Z")
        evaluator = RuleEvaluator(briefing, series_store=extreme_store)

        rule = HistoricalExtremeRule(
            field=FieldOperand(field_id="qqq_iwm_ratio", unit=ValueUnit.RATIO, semantic_type=SemanticType.RATIO),
            extreme=ExtremeType.HIGH,
            lookback=TimeWindow(value=24, unit=TimeUnit.MONTHS),
            comparator=Comparator.GT,
        )
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.TRUE


# ===================================================================
# 8. End-to-end: monetary_architecture compiled artifact
# ===================================================================

class TestMonetaryArchitectureEndToEnd:
    """Load the actual compiled artifact for monetary_architecture and
    evaluate it with InMemorySeriesStore populated with synthetic data.

    monetary_architecture has 3 temporal indicators (all shared):
      - cb_gold_purchases_elevated (persistence, consecutive)
      - foreign_treasury_holdings_declining (trend_state, falling)
      - gold_oil_ratio_elevated_rising (compound with trend_state)
    Plus 1 blocked (ccbs) and 1 evaluable scalar (non_dollar_settlement).

    With SeriesStore populated, the 3 temporal indicators should
    produce results (not NOT_EVALUABLE).
    """

    @pytest.fixture
    def monetary_artifact(self):
        from backend.schemas.v9.compiled_activation import CompiledActivationArtifact
        import json
        from pathlib import Path

        path = Path("artifacts/v9/monetary_architecture.compiled.json")
        data = json.loads(path.read_text())
        return CompiledActivationArtifact(**data)

    @pytest.fixture
    def monetary_briefing(self):
        """Briefing with scalar fields that monetary_architecture needs."""
        from backend.schemas.briefing import BriefingPacket
        return BriefingPacket(
            timestamp="2026-03-01T00:00:00Z",
            computed={
                "gold_oil_ratio": 42.3,
                "rmb_swift_share": 3.89,
            },
        )

    @pytest.fixture
    def monetary_series_store(self):
        """SeriesStore with synthetic data for monetary_architecture's temporal fields."""
        store = InMemorySeriesStore()
        dates_36 = _monthly_dates(36)

        # cb_gold_purchases: above 800 tons for 2+ consecutive years
        store.add_series("cb_gold_purchases", dates_36,
                         [850 + i * 5 for i in range(36)])

        # foreign_treasury_holdings_pct: declining for 3+ years
        store.add_series("foreign_treasury_holdings_pct", dates_36,
                         _falling_series(36, start=28.0, step=0.3))

        # gold_oil_ratio: rising for 12 months
        store.add_series("gold_oil_ratio", dates_36,
                         _rising_series(36, start=25.0, step=0.5))

        return store

    def test_without_series_store_temporal_not_evaluable(self, monetary_artifact, monetary_briefing):
        """Without SeriesStore, temporal indicators are NOT_EVALUABLE."""
        from backend.engine.v9.compiled_evaluator import CompiledActivationEvaluator
        from backend.engine.v9.rule_evaluator import RuleOutcome

        evaluator = CompiledActivationEvaluator(monetary_briefing)
        result = evaluator.evaluate(monetary_artifact)

        phase = result.phase_results.get("single")
        assert phase is not None

        temporal_ids = {"cb_gold_purchases_elevated", "foreign_treasury_holdings_declining", "gold_oil_ratio_elevated_rising"}
        for ind in phase.indicators:
            if ind.indicator_id in temporal_ids:
                assert ind.outcome == RuleOutcome.NOT_EVALUABLE, (
                    f"{ind.indicator_id} should be NOT_EVALUABLE without store, got {ind.outcome}"
                )

    def test_with_series_store_temporal_evaluable(
        self, monetary_artifact, monetary_briefing, monetary_series_store,
    ):
        """With SeriesStore, temporal indicators produce actual results."""
        from backend.engine.v9.compiled_evaluator import CompiledActivationEvaluator
        from backend.engine.v9.rule_evaluator import RuleOutcome

        evaluator = CompiledActivationEvaluator(
            monetary_briefing,
            series_store=monetary_series_store,
        )
        result = evaluator.evaluate(monetary_artifact)

        phase = result.phase_results.get("single")
        assert phase is not None

        temporal_ids = {"cb_gold_purchases_elevated", "foreign_treasury_holdings_declining", "gold_oil_ratio_elevated_rising"}
        for ind in phase.indicators:
            if ind.indicator_id in temporal_ids:
                assert ind.outcome != RuleOutcome.NOT_EVALUABLE, (
                    f"{ind.indicator_id} should be evaluable with store, got {ind.outcome} ({ind.detail})"
                )

    def test_score_improves_with_series_store(
        self, monetary_artifact, monetary_briefing, monetary_series_store,
    ):
        """Score should be higher (or at least different) with SeriesStore
        because more indicators are in the denominator."""
        from backend.engine.v9.compiled_evaluator import CompiledActivationEvaluator

        without = CompiledActivationEvaluator(monetary_briefing)
        with_store = CompiledActivationEvaluator(
            monetary_briefing,
            series_store=monetary_series_store,
        )

        result_without = without.evaluate(monetary_artifact)
        result_with = with_store.evaluate(monetary_artifact)

        phase_without = result_without.phase_results["single"]
        phase_with = result_with.phase_results["single"]

        # With store, more indicators are in the denominator
        assert phase_with.total_weight > phase_without.total_weight, (
            f"total_weight should increase: {phase_without.total_weight} -> {phase_with.total_weight}"
        )

    def test_blocked_indicator_stays_excluded(self, monetary_artifact, monetary_briefing, monetary_series_store):
        """The blocked CCBS indicator should remain excluded even with store."""
        from backend.engine.v9.compiled_evaluator import CompiledActivationEvaluator
        from backend.engine.v9.rule_evaluator import RuleOutcome

        evaluator = CompiledActivationEvaluator(
            monetary_briefing,
            series_store=monetary_series_store,
        )
        result = evaluator.evaluate(monetary_artifact)
        phase = result.phase_results["single"]

        for ind in phase.indicators:
            if ind.indicator_id == "ccbs_stress_episodic":
                # Blocked indicators have no rule clauses, should be excluded
                assert not ind.in_denominator or ind.outcome in (
                    RuleOutcome.NOT_EVALUABLE, RuleOutcome.ERROR,
                ), f"Blocked CCBS should not be in scoring: {ind.outcome}"
