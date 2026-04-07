"""v9 Phase 1: Runtime substrate tests."""
from __future__ import annotations
import pytest

from backend.schemas.briefing import BriefingPacket, MarketData
from backend.schemas.v9.compiled_activation import (
    ArtifactStatus,
    CompiledActivationArtifact,
    CompiledIndicator,
    CompiledPhase,
    CompilationStatus,
    CompilerMetadata,
    ExclusionPolicy,
    PhaseModel,
    SourcePackageRef,
)
from backend.schemas.v9.errors import ErrorCode, Severity
from backend.schemas.v9.field_registry import FieldEntry, FieldKind, FieldRegistry, FieldSource
from backend.schemas.v9.rules import (
    Comparator,
    CompoundOperator,
    CompoundRule,
    DeltaChangeRule,
    DeltaMode,
    DerivedOperand,
    ExtremeType,
    FieldComparisonRule,
    FieldOperand,
    HistoricalExtremeRule,
    LiteralOperand,
    NamedPatternRule,
    PersistenceMode,
    PersistenceRule,
    ScalarComparisonRule,
    TrendDirection,
    TrendStateRule,
)
from backend.schemas.v9.units import (
    ComparisonClass,
    SemanticType,
    TimeUnit,
    TimeWindow,
    ValueUnit,
    can_convert,
    convert_value,
    normalize_to_common_unit,
)
from backend.engine.v9.compiled_evaluator import (
    ActivationTier,
    CompiledActivationEvaluator,
)
from backend.engine.v9.derived_functions import evaluate_derived, is_registered
from backend.engine.v9.registry_builder import build_full_registry
from backend.engine.v9.rule_evaluator import RuleEvaluator, RuleOutcome
from backend.engine.v9.series_engine import BriefingSeriesEngine
from backend.engine.v9.series_interface import (
    PrimitiveResultStatus,
    SeriesData,
    SeriesStore,
)
from backend.engine.v9.validator import ArtifactValidator


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def full_registry():
    """Build the full Phase 1 field registry."""
    return build_full_registry()


@pytest.fixture
def sample_briefing():
    """A minimal but realistic briefing packet for testing."""
    return BriefingPacket(
        timestamp="2026-04-07T12:00:00Z",
        growth={
            "gdp_latest": 31442.0,      # $B nominal GDP
            "real_gdp": 2.1,            # %
            "unemployment": 4.3,         # %
            "initial_claims": 202000.0,  # raw count
            "ism_proxy": 52.3,          # index points
        },
        inflation={
            "cpi_yoy": 3.2,            # %
            "core_pce": 2.8,           # %
            "breakeven_5y": 2.3,       # %
            "breakeven_10y": 2.4,      # %
        },
        rates={
            "fed_funds": 5.33,         # %
            "treasury_2y": 4.25,       # %
            "treasury_10y": 4.40,      # %
            "treasury_30y": 4.55,      # %
            "treasury_3m": 5.30,       # %
            "curve_2s10s": 0.15,       # %
        },
        liquidity={
            "fed_balance_sheet": 7500000.0,  # $M
            "tga": 847718.0,                 # $M
            "reverse_repo": 150000.0,        # $M
        },
        credit={
            "hy_spread": 380.0,        # basis points
            "ig_spread": 120.0,        # basis points
        },
        sentiment={
            "consumer_sentiment": 67.5,  # index
        },
        computed={
            "equity_risk_premium": -0.52,
            "shiller_cape": 35.2,
            "gold_oil_ratio": 42.3,
            "net_liquidity": 6502282.0,    # $M
            "eem_spy_3y_relative": 9.5,    # % (positive = EM outperforms)
            "eem_spy_3m_relative": -2.1,
            "em_us_relative_12m": 9.5,
            "real_fed_funds_rate": 2.13,
            "deficit_pace_annualized": 1800.0,  # $B
            "buffett_indicator": 1.85,
            "interest_receipts_ratio": 22.5,
            "interest_exceeds_defense": 120.0,  # $B
            "vix_vs_realized": 4.86,
            "qqq_iwm_ratio": 2.35,
            "dxy_index": 104.5,
            "spy_drawdown_from_52w_high": -3.2,
            "hard_vs_nominal_12m": 15.3,
        },
        markets={
            "^VIX": MarketData(price=23.87),
        },
    )


class MockSeriesStore:
    """A mock series store for testing."""

    def __init__(self, data: dict[str, list[float]] | None = None):
        self._data = data or {}

    def get_series(self, field_id: str, window: TimeWindow):
        values = self._data.get(field_id)
        if values is None:
            return None
        return SeriesData(field_id=field_id, values=values)

    def has_series(self, field_id: str) -> bool:
        return field_id in self._data


# ===================================================================
# 1. Field Registry Population Sanity
# ===================================================================

class TestFieldRegistryPopulation:
    """Tests that the full registry is populated correctly."""

    def test_registry_has_fields(self, full_registry):
        """Registry should have a substantial number of fields."""
        assert full_registry.field_count() >= 60

    def test_fred_fields_present(self, full_registry):
        """All primary FRED fields should be registered."""
        fred_fields = [
            "growth.gdp_latest", "growth.real_gdp", "growth.unemployment",
            "growth.initial_claims", "growth.ism_proxy",
            "rates.fed_funds", "rates.treasury_10y", "rates.curve_2s10s",
            "credit.hy_spread", "credit.ig_spread",
            "liquidity.fed_balance_sheet", "liquidity.tga", "liquidity.reverse_repo",
        ]
        for fid in fred_fields:
            assert full_registry.has_field(fid), f"Missing FRED field: {fid}"

    def test_computed_fields_present(self, full_registry):
        """All computed fields should be registered."""
        computed_fields = [
            "equity_risk_premium", "gold_oil_ratio", "net_liquidity",
            "qqq_iwm_ratio", "vix_vs_realized", "buffett_indicator",
            "eem_spy_3y_relative", "deficit_pace_annualized",
            "interest_receipts_ratio", "real_fed_funds_rate",
        ]
        for fid in computed_fields:
            assert full_registry.has_field(fid), f"Missing computed field: {fid}"

    def test_web_fields_present(self, full_registry):
        """All web-sourced fields should be registered."""
        web_fields = [
            "shiller_cape", "consumer_confidence", "cb_gold_purchases",
            "china_credit_impulse", "em_dm_pe_gap", "rmb_swift_share",
        ]
        for fid in web_fields:
            assert full_registry.has_field(fid), f"Missing web field: {fid}"

    def test_ticker_fields_present(self, full_registry):
        """Ticker fields should be registered."""
        assert full_registry.has_field("^VIX")

    def test_initial_claims_unit_is_count(self, full_registry):
        """Regression: initial_claims must be COUNT (raw number), not THOUSANDS."""
        entry = full_registry.get_field("growth.initial_claims")
        assert entry is not None
        assert entry.unit == ValueUnit.COUNT

    def test_eem_spy_3y_relative_metadata(self, full_registry):
        """Regression: eem_spy_3y_relative must have correct metadata."""
        entry = full_registry.get_field("eem_spy_3y_relative")
        assert entry is not None
        assert entry.unit == ValueUnit.PERCENT
        assert entry.semantic_type == SemanticType.RELATIVE_PERFORMANCE
        assert entry.is_computed
        assert "12-month" in entry.description.lower() or "12m" in entry.description.lower()

    def test_fed_funds_semantic_type(self, full_registry):
        """fed_funds should be RATE, not LEVEL."""
        entry = full_registry.get_field("rates.fed_funds")
        assert entry is not None
        assert entry.semantic_type == SemanticType.RATE

    def test_gdp_latest_semantic_type(self, full_registry):
        """gdp_latest should be LEVEL."""
        entry = full_registry.get_field("growth.gdp_latest")
        assert entry is not None
        assert entry.semantic_type == SemanticType.LEVEL


# ===================================================================
# 2. Unit Normalization Correctness
# ===================================================================

class TestUnitNormalization:
    """Tests unit conversion and normalization."""

    def test_count_to_thousands(self):
        """COUNT -> THOUSANDS conversion."""
        result = convert_value(202000.0, ValueUnit.COUNT, ValueUnit.THOUSANDS)
        assert result == 202.0

    def test_thousands_to_count(self):
        """THOUSANDS -> COUNT conversion."""
        result = convert_value(250.0, ValueUnit.THOUSANDS, ValueUnit.COUNT)
        assert result == 250000.0

    def test_percent_to_basis_points(self):
        """PERCENT -> BASIS_POINTS conversion."""
        result = convert_value(3.5, ValueUnit.PERCENT, ValueUnit.BASIS_POINTS)
        assert result == 350.0

    def test_basis_points_to_percent(self):
        """BASIS_POINTS -> PERCENT conversion."""
        result = convert_value(450.0, ValueUnit.BASIS_POINTS, ValueUnit.PERCENT)
        assert result == 4.5

    def test_normalize_count_vs_thousands(self):
        """Normalize COUNT and THOUSANDS to common unit."""
        a, b, unit = normalize_to_common_unit(
            202000.0, ValueUnit.COUNT,
            250.0, ValueUnit.THOUSANDS,
        )
        # Should normalize to COUNT (a's unit preferred)
        assert unit == ValueUnit.COUNT
        assert a == 202000.0
        assert b == 250000.0

    def test_incompatible_units_fail(self):
        """Units with no conversion should raise."""
        with pytest.raises(ValueError):
            normalize_to_common_unit(
                100.0, ValueUnit.PERCENT,
                50.0, ValueUnit.USD_BILLIONS,
            )


# ===================================================================
# 3. Illegal Comparison Rejection
# ===================================================================

class TestComparisonLegality:
    """Tests semantic comparison legality checks."""

    def test_rate_vs_level_illegal(self, full_registry):
        """Regression: fed_funds (rate) vs gdp_latest (level) must be illegal."""
        ok, reason = full_registry.check_comparison_legality(
            "rates.fed_funds", "growth.gdp_latest",
        )
        assert not ok
        assert "mismatch" in reason.lower()

    def test_rate_vs_growth_rate_legal(self, full_registry):
        """fed_funds (rate) vs real_gdp (growth_rate) should be legal (both RATE_LIKE)."""
        ok, reason = full_registry.check_comparison_legality(
            "rates.fed_funds", "growth.real_gdp",
        )
        assert ok

    def test_spread_vs_spread_legal(self, full_registry):
        """hy_spread vs ig_spread should be legal (both RATE_LIKE)."""
        ok, reason = full_registry.check_comparison_legality(
            "credit.hy_spread", "credit.ig_spread",
        )
        assert ok

    def test_ratio_vs_share_legal(self, full_registry):
        """shiller_cape (ratio) vs passive_fund_share (share) should be legal (both RATIO_LIKE)."""
        ok, reason = full_registry.check_comparison_legality(
            "shiller_cape", "passive_fund_share",
        )
        assert ok

    def test_count_vs_index_illegal(self, full_registry):
        """initial_claims (count) vs ism_proxy (index) should be illegal."""
        ok, reason = full_registry.check_comparison_legality(
            "growth.initial_claims", "growth.ism_proxy",
        )
        assert not ok

    def test_unit_compatibility_count_vs_thousands(self, full_registry):
        """initial_claims (COUNT) should be compatible with THOUSANDS literal."""
        ok, reason = full_registry.check_unit_compatibility(
            "growth.initial_claims", ValueUnit.THOUSANDS,
        )
        assert ok
        assert "convertible" in reason.lower()


# ===================================================================
# 4. Series Primitive Behavior
# ===================================================================

class TestSeriesPrimitives:
    """Tests the concrete series primitive engine."""

    def test_latest_value(self):
        store = MockSeriesStore({"growth.unemployment": [4.1, 4.2, 4.3]})
        engine = BriefingSeriesEngine(store)
        result = engine.latest_value("growth.unemployment")
        assert result.status == PrimitiveResultStatus.OK
        assert result.value == 4.3

    def test_missing_field(self):
        store = MockSeriesStore({})
        engine = BriefingSeriesEngine(store)
        result = engine.latest_value("nonexistent")
        assert result.status == PrimitiveResultStatus.FIELD_NOT_FOUND

    def test_trend_rising(self):
        store = MockSeriesStore({"field": [10.0, 12.0, 14.0, 16.0, 18.0]})
        engine = BriefingSeriesEngine(store)
        window = TimeWindow(value=5, unit=TimeUnit.MONTHS)
        result = engine.trend_direction("field", window)
        assert result.status == PrimitiveResultStatus.OK
        assert result.detail == "rising"

    def test_trend_falling(self):
        store = MockSeriesStore({"field": [18.0, 16.0, 14.0, 12.0, 10.0]})
        engine = BriefingSeriesEngine(store)
        window = TimeWindow(value=5, unit=TimeUnit.MONTHS)
        result = engine.trend_direction("field", window)
        assert result.status == PrimitiveResultStatus.OK
        assert result.detail == "falling"

    def test_n_of_last_k(self):
        store = MockSeriesStore({"field": [5.0, 1.0, 6.0, 2.0, 7.0]})
        engine = BriefingSeriesEngine(store)
        # 3 of last 5 values > 4.0 (5, 6, 7) = True for n=2
        result = engine.n_of_last_k("field", "gt", 4.0, 2, 5)
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is True

    def test_consecutive_true(self):
        store = MockSeriesStore({"field": [5.0, 6.0, 7.0, 8.0]})
        engine = BriefingSeriesEngine(store)
        # Last 3 values > 4.0 consecutively
        result = engine.consecutive_true("field", "gt", 4.0, 3)
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is True

    def test_rolling_max(self):
        store = MockSeriesStore({"field": [10.0, 25.0, 15.0, 20.0]})
        engine = BriefingSeriesEngine(store)
        window = TimeWindow(value=4, unit=TimeUnit.MONTHS)
        result = engine.rolling_max("field", window)
        assert result.status == PrimitiveResultStatus.OK
        assert result.value == 25.0

    def test_is_at_extreme_high(self):
        store = MockSeriesStore({"field": [10.0, 20.0, 15.0, 20.0]})
        engine = BriefingSeriesEngine(store)
        window = TimeWindow(value=4, unit=TimeUnit.MONTHS)
        result = engine.is_at_extreme("field", "high", window)
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is True

    def test_absolute_change(self):
        store = MockSeriesStore({"field": [100.0, 120.0, 130.0]})
        engine = BriefingSeriesEngine(store)
        window = TimeWindow(value=3, unit=TimeUnit.MONTHS)
        result = engine.absolute_change("field", window)
        assert result.status == PrimitiveResultStatus.OK
        assert result.value == 30.0

    def test_percent_change(self):
        store = MockSeriesStore({"field": [100.0, 120.0, 150.0]})
        engine = BriefingSeriesEngine(store)
        window = TimeWindow(value=3, unit=TimeUnit.MONTHS)
        result = engine.percent_change("field", window)
        assert result.status == PrimitiveResultStatus.OK
        assert result.value == 50.0


# ===================================================================
# 5. Rule Evaluator Correctness
# ===================================================================

class TestRuleEvaluator:
    """Tests deterministic rule evaluation."""

    def test_scalar_comparison_true(self, sample_briefing, full_registry):
        """ISM proxy > 50 should be True (52.3 > 50)."""
        rule = ScalarComparisonRule(
            field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS,
                               semantic_type=SemanticType.INDEX),
            comparator=Comparator.GT,
            threshold=LiteralOperand(value=50.0, unit=ValueUnit.INDEX_POINTS),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.TRUE

    def test_scalar_comparison_false(self, sample_briefing, full_registry):
        """CAPE > 40 should be False (35.2 < 40)."""
        rule = ScalarComparisonRule(
            field=FieldOperand(field_id="shiller_cape", unit=ValueUnit.RATIO,
                               semantic_type=SemanticType.RATIO),
            comparator=Comparator.GT,
            threshold=LiteralOperand(value=40.0, unit=ValueUnit.RATIO),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.FALSE

    def test_scalar_with_unit_normalization(self, sample_briefing, full_registry):
        """Regression: initial_claims (COUNT) < 250 (THOUSANDS) should normalize correctly."""
        rule = ScalarComparisonRule(
            field=FieldOperand(field_id="growth.initial_claims", unit=ValueUnit.COUNT,
                               semantic_type=SemanticType.COUNT),
            comparator=Comparator.LT,
            threshold=LiteralOperand(value=250.0, unit=ValueUnit.THOUSANDS),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        # 202000 COUNT < 250000 COUNT (250 THOUSANDS converted) -> True
        assert result.outcome == RuleOutcome.TRUE

    def test_field_comparison_with_derived(self, sample_briefing, full_registry):
        """fed_funds < nominal_gdp_growth should use derived function."""
        rule = FieldComparisonRule(
            left=FieldOperand(field_id="rates.fed_funds", unit=ValueUnit.PERCENT,
                              semantic_type=SemanticType.RATE),
            comparator=Comparator.LT,
            right=DerivedOperand(
                function_name="nominal_gdp_growth",
                arguments=["growth.real_gdp", "inflation.cpi_yoy"],
                unit=ValueUnit.PERCENT,
                semantic_type=SemanticType.GROWTH_RATE,
            ),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        # fed_funds=5.33, nominal_gdp_growth=2.1+3.2=5.3 -> 5.33 < 5.3 -> False
        assert result.outcome == RuleOutcome.FALSE

    def test_compound_all_true(self, sample_briefing, full_registry):
        """Compound ALL: both sub-rules true -> True."""
        rule = CompoundRule(
            operator=CompoundOperator.ALL,
            clauses=[
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=50.0, unit=ValueUnit.INDEX_POINTS),
                ),
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.unemployment", unit=ValueUnit.PERCENT),
                    comparator=Comparator.LT,
                    threshold=LiteralOperand(value=5.0, unit=ValueUnit.PERCENT),
                ),
            ],
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.TRUE

    def test_compound_any_one_true(self, sample_briefing, full_registry):
        """Compound ANY: one sub-rule true -> True."""
        rule = CompoundRule(
            operator=CompoundOperator.ANY,
            clauses=[
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=60.0, unit=ValueUnit.INDEX_POINTS),
                ),  # False
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.unemployment", unit=ValueUnit.PERCENT),
                    comparator=Comparator.LT,
                    threshold=LiteralOperand(value=5.0, unit=ValueUnit.PERCENT),
                ),  # True
            ],
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.TRUE

    def test_missing_field_not_evaluable(self, sample_briefing, full_registry):
        """Missing field should return NOT_EVALUABLE."""
        rule = ScalarComparisonRule(
            field=FieldOperand(field_id="nonexistent_field"),
            comparator=Comparator.GT,
            threshold=LiteralOperand(value=50.0),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.NOT_EVALUABLE

    def test_trend_without_series_not_evaluable(self, sample_briefing, full_registry):
        """Trend rule without series store -> NOT_EVALUABLE."""
        rule = TrendStateRule(
            field=FieldOperand(field_id="growth.ism_proxy"),
            direction=TrendDirection.FALLING,
            window=TimeWindow(value=3, unit=TimeUnit.MONTHS),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.NOT_EVALUABLE

    def test_trend_with_series(self, sample_briefing, full_registry):
        """Trend rule with series data should evaluate."""
        store = MockSeriesStore({
            "growth.ism_proxy": [54.0, 53.0, 52.0, 51.0, 50.0],
        })
        rule = TrendStateRule(
            field=FieldOperand(field_id="growth.ism_proxy"),
            direction=TrendDirection.FALLING,
            window=TimeWindow(value=5, unit=TimeUnit.MONTHS),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry, series_store=store)
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.TRUE

    def test_persistence_with_series(self, sample_briefing, full_registry):
        """Persistence rule with series should evaluate."""
        store = MockSeriesStore({
            "net_liquidity": [100.0, 50.0, 150.0],
        })
        rule = PersistenceRule(
            condition=ScalarComparisonRule(
                field=FieldOperand(field_id="net_liquidity"),
                comparator=Comparator.GT,
                threshold=LiteralOperand(value=0.0),
            ),
            mode=PersistenceMode.N_OF_LAST_K,
            n=2,
            k=3,
            window=TimeWindow(value=3, unit=TimeUnit.MONTHS),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry, series_store=store)
        result = evaluator.evaluate(rule)
        # 2 of 3 values > 0 (100, 150) = True for n=2
        assert result.outcome == RuleOutcome.TRUE

    def test_named_pattern_without_series(self, sample_briefing, full_registry):
        """Named pattern without series store -> NOT_EVALUABLE."""
        rule = NamedPatternRule(
            name="sahm_rule",
            params={"field": "growth.unemployment"},
            field_dependencies=["growth.unemployment"],
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.NOT_EVALUABLE

    def test_delta_change_with_series(self, sample_briefing, full_registry):
        """Delta change rule should evaluate with series data."""
        store = MockSeriesStore({
            "liquidity.tga": [900000.0, 850000.0, 780000.0],
        })
        rule = DeltaChangeRule(
            field=FieldOperand(field_id="liquidity.tga", unit=ValueUnit.USD_MILLIONS),
            direction=TrendDirection.FALLING,
            magnitude=LiteralOperand(value=100000.0, unit=ValueUnit.USD_MILLIONS),
            mode=DeltaMode.ABSOLUTE,
            window=TimeWindow(value=60, unit=TimeUnit.DAYS),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry, series_store=store)
        result = evaluator.evaluate(rule)
        # Change: 780000 - 900000 = -120000, magnitude check: -120000 <= -100000 -> True
        assert result.outcome == RuleOutcome.TRUE


# ===================================================================
# 6. Named Pattern Hooks
# ===================================================================

class TestNamedPatterns:
    """Tests named pattern evaluation."""

    def test_sahm_rule_triggered(self):
        """Sahm Rule should trigger when unemployment rises sharply."""
        # 12 months of slowly rising unemployment
        values = [3.5, 3.5, 3.6, 3.6, 3.7, 3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.5, 4.8, 5.0]
        store = MockSeriesStore({"growth.unemployment": values})
        engine = BriefingSeriesEngine(store)
        result = engine.evaluate_named_pattern("sahm_rule", {
            "field": "growth.unemployment",
            "threshold": 0.50,
        })
        assert result.status == PrimitiveResultStatus.OK
        # The 3-month MA has risen significantly above the 12-month low
        assert result.boolean is True

    def test_sahm_rule_not_triggered(self):
        """Sahm Rule should not trigger with stable unemployment."""
        values = [3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5]
        store = MockSeriesStore({"growth.unemployment": values})
        engine = BriefingSeriesEngine(store)
        result = engine.evaluate_named_pattern("sahm_rule", {
            "field": "growth.unemployment",
        })
        assert result.status == PrimitiveResultStatus.OK
        assert result.boolean is False

    def test_unknown_pattern_error(self):
        """Unknown named pattern should return ERROR."""
        store = MockSeriesStore({})
        engine = BriefingSeriesEngine(store)
        result = engine.evaluate_named_pattern("nonexistent_pattern", {})
        assert result.status == PrimitiveResultStatus.ERROR


# ===================================================================
# 7. Compiled Activation Evaluator
# ===================================================================

def _make_artifact(
    theory_id: str,
    phases: list[CompiledPhase],
    phase_model: PhaseModel = PhaseModel.SINGLE_PHASE,
) -> CompiledActivationArtifact:
    """Helper: create a test artifact."""
    return CompiledActivationArtifact(
        source=SourcePackageRef(theory_id=theory_id),
        phase_model=phase_model,
        phases=phases,
        total_indicators=sum(len(p.indicators) for p in phases),
    )


def _make_indicator(
    indicator_id: str,
    rule: "Rule",
    weight: float = 0.15,
    primary_field: str = "",
    exclusion_policy: ExclusionPolicy = ExclusionPolicy.SCORE_IF_EVALUABLE,
) -> CompiledIndicator:
    """Helper: create a test indicator."""
    return CompiledIndicator(
        indicator_id=indicator_id,
        display_name=indicator_id.replace("_", " ").title(),
        source_text="test",
        rule=rule,
        primary_field=primary_field,
        weight=weight,
        exclusion_policy=exclusion_policy,
    )


class TestCompiledEvaluator:
    """Tests the compiled activation evaluator scaffold."""

    def test_single_phase_active(self, sample_briefing, full_registry):
        """A single-phase artifact with most indicators triggered -> Active."""
        indicators = [
            _make_indicator(
                "ism_above_50",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=50.0, unit=ValueUnit.INDEX_POINTS),
                ),
                weight=0.20,
                primary_field="growth.ism_proxy",
            ),
            _make_indicator(
                "unemployment_low",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.unemployment", unit=ValueUnit.PERCENT),
                    comparator=Comparator.LT,
                    threshold=LiteralOperand(value=5.0, unit=ValueUnit.PERCENT),
                ),
                weight=0.20,
                primary_field="growth.unemployment",
            ),
            _make_indicator(
                "hy_spread_tight",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="credit.hy_spread", unit=ValueUnit.BASIS_POINTS),
                    comparator=Comparator.LT,
                    threshold=LiteralOperand(value=450.0, unit=ValueUnit.BASIS_POINTS),
                ),
                weight=0.20,
                primary_field="credit.hy_spread",
            ),
        ]
        artifact = _make_artifact(
            "test_theory",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        evaluator = CompiledActivationEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(artifact)
        assert result.effective_tier == ActivationTier.ACTIVE
        assert result.effective_score == pytest.approx(1.0)

    def test_exclusion_policy_removes_from_denominator(self, sample_briefing, full_registry):
        """EXCLUDE_FROM_SCORING indicators should not affect the score."""
        indicators = [
            _make_indicator(
                "triggered",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=50.0, unit=ValueUnit.INDEX_POINTS),
                ),
                weight=0.50,
                primary_field="growth.ism_proxy",
            ),
            _make_indicator(
                "excluded_context",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=99.0, unit=ValueUnit.INDEX_POINTS),
                ),
                weight=0.50,
                primary_field="growth.ism_proxy",
                exclusion_policy=ExclusionPolicy.EXCLUDE_FROM_SCORING,
            ),
        ]
        artifact = _make_artifact(
            "test_exclusion",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        evaluator = CompiledActivationEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(artifact)
        # Only the first indicator counts: 0.50/0.50 = 1.0
        assert result.effective_score == pytest.approx(1.0)

    def test_two_phase_b_priority(self, sample_briefing, full_registry):
        """Two-phase: if Phase B is Active, Phase A is forced Inactive."""
        phase_a_indicators = [
            _make_indicator(
                "phase_a_ind",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=50.0, unit=ValueUnit.INDEX_POINTS),
                ),
                weight=1.0,
            ),
        ]
        phase_b_indicators = [
            _make_indicator(
                "phase_b_ind",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.unemployment", unit=ValueUnit.PERCENT),
                    comparator=Comparator.LT,
                    threshold=LiteralOperand(value=5.0, unit=ValueUnit.PERCENT),
                ),
                weight=1.0,
            ),
        ]
        artifact = _make_artifact(
            "test_two_phase",
            [
                CompiledPhase(phase_id="expansion", phase_label="Expansion",
                              indicators=phase_a_indicators),
                CompiledPhase(phase_id="contraction", phase_label="Contraction",
                              indicators=phase_b_indicators),
            ],
            phase_model=PhaseModel.TWO_PHASE,
        )
        evaluator = CompiledActivationEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(artifact)
        # Phase B (contraction) is Active -> it takes priority
        assert result.effective_tier == ActivationTier.ACTIVE
        assert result.effective_phase == "contraction"


# ===================================================================
# 8. Validator Correctness
# ===================================================================

class TestValidator:
    """Tests artifact validation."""

    def test_valid_artifact_passes(self, full_registry):
        """A well-formed artifact should pass validation."""
        indicators = [
            _make_indicator(
                "ism_above_50",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=50.0, unit=ValueUnit.INDEX_POINTS),
                ),
                weight=0.20,
                primary_field="growth.ism_proxy",
            ),
        ]
        artifact = _make_artifact(
            "test_valid",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert report.passed

    def test_unknown_field_fails(self, full_registry):
        """Reference to unknown field should fail validation."""
        indicators = [
            _make_indicator(
                "bad_field",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="nonexistent.field"),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=50.0),
                ),
                weight=0.20,
                primary_field="nonexistent.field",
            ),
        ]
        artifact = _make_artifact(
            "test_unknown_field",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert not report.passed
        assert report.has_code(ErrorCode.F_UNKNOWN_FIELD)

    def test_unresolved_field_fails(self, full_registry):
        """UNRESOLVED: prefix should fail validation."""
        indicators = [
            _make_indicator(
                "unresolved",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="UNRESOLVED:loan_growth"),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=0.0),
                ),
                weight=0.20,
                primary_field="UNRESOLVED:loan_growth",
            ),
        ]
        artifact = _make_artifact(
            "test_unresolved",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert not report.passed
        assert report.has_code(ErrorCode.F_UNRESOLVED_FIELD)

    def test_trivial_placeholder_warning(self, full_registry):
        """Trivial gt 0.0 dimensionless threshold should warn."""
        indicators = [
            _make_indicator(
                "trivial",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.ism_proxy", unit=ValueUnit.INDEX_POINTS),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=0.0, unit=ValueUnit.DIMENSIONLESS),
                ),
                weight=0.20,
                primary_field="growth.ism_proxy",
            ),
        ]
        artifact = _make_artifact(
            "test_trivial",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert report.has_code(ErrorCode.R_TRIVIAL_PLACEHOLDER)

    def test_missing_named_pattern_fails(self, full_registry):
        """Reference to unregistered named pattern should fail."""
        indicators = [
            _make_indicator(
                "bad_pattern",
                NamedPatternRule(name="nonexistent_pattern"),
                weight=0.20,
            ),
        ]
        artifact = _make_artifact(
            "test_bad_pattern",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert not report.passed
        assert report.has_code(ErrorCode.R_MISSING_NAMED_PATTERN)

    def test_empty_compound_fails(self, full_registry):
        """Empty compound rule should fail."""
        indicators = [
            _make_indicator(
                "empty_compound",
                CompoundRule(operator=CompoundOperator.ALL, clauses=[]),
                weight=0.20,
            ),
        ]
        artifact = _make_artifact(
            "test_empty_compound",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert not report.passed
        assert report.has_code(ErrorCode.R_EMPTY_COMPOUND)

    def test_invalid_persistence_fails(self, full_registry):
        """Persistence with n > k should fail."""
        indicators = [
            _make_indicator(
                "bad_persistence",
                PersistenceRule(
                    condition=ScalarComparisonRule(
                        field=FieldOperand(field_id="growth.ism_proxy"),
                        comparator=Comparator.GT,
                        threshold=LiteralOperand(value=50.0),
                    ),
                    mode=PersistenceMode.N_OF_LAST_K,
                    n=5,
                    k=3,
                    window=TimeWindow(value=3, unit=TimeUnit.MONTHS),
                ),
                weight=0.20,
            ),
        ]
        artifact = _make_artifact(
            "test_bad_persistence",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert not report.passed
        assert report.has_code(ErrorCode.R_INVALID_PERSISTENCE)

    def test_phase_model_mismatch_fails(self, full_registry):
        """Declared two_phase with only 1 phase should fail."""
        indicators = [
            _make_indicator(
                "ind",
                ScalarComparisonRule(
                    field=FieldOperand(field_id="growth.ism_proxy"),
                    comparator=Comparator.GT,
                    threshold=LiteralOperand(value=50.0),
                ),
                weight=0.50,
                primary_field="growth.ism_proxy",
            ),
        ]
        artifact = _make_artifact(
            "test_mismatch",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
            phase_model=PhaseModel.TWO_PHASE,
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert not report.passed
        assert report.has_code(ErrorCode.P_PHASE_MODEL_MISMATCH)

    def test_delta_change_stable_direction_fails(self, full_registry):
        """delta_change with stable direction should fail."""
        indicators = [
            _make_indicator(
                "bad_delta",
                DeltaChangeRule(
                    field=FieldOperand(field_id="liquidity.tga"),
                    direction=TrendDirection.STABLE,
                    magnitude=LiteralOperand(value=100.0, unit=ValueUnit.USD_MILLIONS),
                    mode=DeltaMode.ABSOLUTE,
                    window=TimeWindow(value=60, unit=TimeUnit.DAYS),
                ),
                weight=0.20,
                primary_field="liquidity.tga",
            ),
        ]
        artifact = _make_artifact(
            "test_bad_delta",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert not report.passed
        assert report.has_code(ErrorCode.R_INVALID_DELTA_DIRECTION)

    def test_unregistered_derived_function_fails(self, full_registry):
        """Derived function not in registry should fail."""
        indicators = [
            _make_indicator(
                "bad_derived",
                FieldComparisonRule(
                    left=FieldOperand(field_id="rates.fed_funds"),
                    comparator=Comparator.LT,
                    right=DerivedOperand(function_name="nonexistent_function"),
                ),
                weight=0.20,
                primary_field="rates.fed_funds",
            ),
        ]
        artifact = _make_artifact(
            "test_bad_derived",
            [CompiledPhase(phase_id="single", phase_label="Single", indicators=indicators)],
        )
        validator = ArtifactValidator(full_registry)
        report = validator.validate(artifact)
        assert not report.passed
        assert report.has_code(ErrorCode.X_UNRESOLVED_DERIVED)


# ===================================================================
# 9. Regression Cases
# ===================================================================

class TestRegressions:
    """Explicit regression tests for known issues."""

    def test_initial_claims_unit_normalization(self, sample_briefing, full_registry):
        """Regression: initial_claims COUNT vs THOUSANDS must normalize.

        The spike found that initial_claims (202000, COUNT) compared
        to threshold 250 (THOUSANDS) without normalization gave wrong result.
        The runtime must convert: 250 THOUSANDS = 250000 COUNT.
        """
        rule = ScalarComparisonRule(
            field=FieldOperand(field_id="growth.initial_claims", unit=ValueUnit.COUNT,
                               semantic_type=SemanticType.COUNT),
            comparator=Comparator.LT,
            threshold=LiteralOperand(value=250.0, unit=ValueUnit.THOUSANDS),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        assert result.outcome == RuleOutcome.TRUE
        assert result.detail  # should have normalization info

    def test_fed_funds_vs_gdp_illegality(self, full_registry):
        """Regression: fed_funds (RATE) vs gdp_latest (LEVEL) must be illegal.

        The legacy system compares fed_funds (5.33%) to GDP ($31,442B)
        which is a category error. The v9 registry must flag this.
        """
        ok, reason = full_registry.check_comparison_legality(
            "rates.fed_funds", "growth.gdp_latest",
        )
        assert not ok
        assert "rate_like" in reason.lower() or "level_like" in reason.lower()

    def test_eem_spy_3y_relative_sign_convention(self, sample_briefing, full_registry):
        """Regression: eem_spy_3y_relative sign investigation.

        Investigation result: sign convention is CORRECT.
        - Negative = EM underperformance
        - Positive = EM outperformance
        - Value 9.5 means EM outperformed by 9.5%
        - Threshold lt -30.0 means "underperformed by 30%+"
        - 9.5 < -30.0 -> False (correct: EM is not underperforming)
        - Legacy said True (bug: regex extracted unsigned "30", checked 9.5 < 30)
        """
        rule = ScalarComparisonRule(
            field=FieldOperand(field_id="eem_spy_3y_relative", unit=ValueUnit.PERCENT,
                               semantic_type=SemanticType.RELATIVE_PERFORMANCE),
            comparator=Comparator.LT,
            threshold=LiteralOperand(value=-30.0, unit=ValueUnit.PERCENT),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        # 9.5 < -30.0 -> False (EM is outperforming, not underperforming)
        assert result.outcome == RuleOutcome.FALSE

        # Also verify the field is properly typed
        entry = full_registry.get_field("eem_spy_3y_relative")
        assert entry is not None
        assert entry.semantic_type == SemanticType.RELATIVE_PERFORMANCE
        assert entry.unit == ValueUnit.PERCENT

    def test_hy_spread_basis_points(self, sample_briefing, full_registry):
        """HY spread stored in basis points should compare correctly."""
        rule = ScalarComparisonRule(
            field=FieldOperand(field_id="credit.hy_spread", unit=ValueUnit.BASIS_POINTS,
                               semantic_type=SemanticType.SPREAD),
            comparator=Comparator.LT,
            threshold=LiteralOperand(value=450.0, unit=ValueUnit.BASIS_POINTS),
        )
        evaluator = RuleEvaluator(sample_briefing, full_registry)
        result = evaluator.evaluate(rule)
        # 380 < 450 -> True
        assert result.outcome == RuleOutcome.TRUE

    def test_derived_function_nominal_gdp_growth(self, sample_briefing):
        """nominal_gdp_growth should be real_gdp + cpi_yoy."""
        result = evaluate_derived("nominal_gdp_growth", sample_briefing)
        # 2.1 + 3.2 = 5.3
        assert result is not None
        assert result == pytest.approx(5.3)

    def test_derived_function_unknown(self, sample_briefing):
        """Unknown derived function should return None."""
        result = evaluate_derived("nonexistent_function", sample_briefing)
        assert result is None
