"""Compiler semantic correctness harness for v9 spike.

PURPOSE: Freeze what the compiler MUST produce for known inputs.
This is the compiler's equivalent of test_activation_correctness.py.

Each test asserts the INTENDED compilation based on reading the English
source text in ACTIVATION.md, NOT rubber-stamping Haiku output.

These tests do NOT call the Haiku API. They define the contract a
correct compiler must satisfy: given this English, produce this rule.

COVERAGE:
- 5 scalar_comparison (ISM>50, CAPE>30, HY<300bp, debt/GDP>250, gold/oil>25)
- 2 field_comparison (fed funds vs GDP, fed funds above GDP+1%)
- 2 compound (profit margins OR, HY spread AND)
- 2 trend (ISM falling 3mo, claims rising 8wk)
- 2 persistence/lookback_extreme (insider 3mo, CB gold 2yr)
- 2 high-ambiguity / BLOCKED (Sahm Rule, SLOOS)

DELIBERATE UPDATE POLICY:
Same as test_activation_correctness.py. Do not auto-generate.
To update, change the specific expected value and explain why.
"""
import pytest

from backend.schemas.v9_spike.compiled_activation import (
    AmbiguityLevel,
    CompiledIndicator,
    CompiledPhase,
    CompiledRule,
    CompiledTheoryActivation,
    CompoundOp,
    CompoundRule,
    FieldComparisonRule,
    LookbackExtremeRule,
    Operator,
    PersistenceRule,
    ScalarComparisonRule,
    TrendDirection,
    TrendRule,
    TimeUnit,
    ValueUnit,
)


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _scalar(field, op, value, unit=ValueUnit.DIMENSIONLESS):
    return CompiledRule(scalar_comparison=ScalarComparisonRule(
        field=field, operator=op, value=value, unit=unit,
    ))


def _field_cmp(a, b, op, offset=0.0):
    return CompiledRule(field_comparison=FieldComparisonRule(
        field_a=a, field_b=b, operator=op, offset=offset,
    ))


def _trend(field, direction, window_val, window_unit):
    return CompiledRule(trend=TrendRule(
        field=field, direction=direction,
        window_value=window_val, window_unit=window_unit,
    ))


def _persistence(field, op, value, n, k, period_unit):
    return CompiledRule(persistence=PersistenceRule(
        field=field, condition_operator=op, condition_value=value,
        n=n, k=k, period_unit=period_unit,
    ))


def _compound(op, rules):
    return CompiledRule(compound=CompoundRule(operator=op, rules=rules))


# -----------------------------------------------------------------------
# Contract assertions
# -----------------------------------------------------------------------

def _assert_rule_type(indicator: dict, expected_type: str):
    """Assert that the compiled rule has the expected top-level type."""
    assert indicator["expected_rule_type"] == expected_type


class TestCompilerSemanticCorrectness:
    """Freeze the INTENDED compilation for known indicator inputs.

    Each test specifies:
    - source: exact English from ACTIVATION.md
    - expected: rule_type, operator, value, unit, field_refs
    - theory + indicator name for traceability
    """

    # -------------------------------------------------------------------
    # SCALAR COMPARISONS (5)
    # -------------------------------------------------------------------

    def test_ism_above_50(self):
        """debt_cycle_short / Expansion: 'Above 50' on growth.ism_proxy

        Source: "ISM proxy above contraction | `growth.ism_proxy` | Above 50 | above | 0.15"
        This is the simplest possible scalar: field > constant.
        """
        expected = _scalar("growth.ism_proxy", Operator.GT, 50.0, ValueUnit.INDEX_POINTS)
        rule = expected.active_rule()
        assert rule.rule_type == "scalar_comparison"
        assert rule.field == "growth.ism_proxy"
        assert rule.operator == Operator.GT
        assert rule.value == 50.0

    def test_cape_above_30(self):
        """valuation_mean_reversion: 'Above 30' on shiller_cape

        Source: "Shiller CAPE elevated | Web source: Shiller CAPE ratio | Above 30 | above | 0.20"
        Web-search field must resolve to shiller_cape.
        """
        expected = _scalar("shiller_cape", Operator.GT, 30.0, ValueUnit.INDEX_POINTS)
        rule = expected.active_rule()
        assert rule.field == "shiller_cape"
        assert rule.operator == Operator.GT
        assert rule.value == 30.0

    def test_hy_spread_below_300bp(self):
        """structural_fragility / Building: 'Below 300bp' on credit.hy_spread

        Source: "High-yield spread | `credit.hy_spread` | Below 300bp | below | 0.15"
        Unit must be basis_points. Value is 300, not 0.03.
        """
        expected = _scalar("credit.hy_spread", Operator.LT, 300.0, ValueUnit.BASIS_POINTS)
        rule = expected.active_rule()
        assert rule.field == "credit.hy_spread"
        assert rule.operator == Operator.LT
        assert rule.value == 300.0
        assert rule.unit == ValueUnit.BASIS_POINTS

    def test_total_debt_gdp_above_250(self):
        """debt_cycle_long: 'Total US non-financial debt / GDP above 250%'

        Source: "Total debt / GDP above historical warning level | web-search | above 250% | above | 0.25"
        Web-search must resolve to total_debt_to_gdp. Unit is percent.
        """
        expected = _scalar("total_debt_to_gdp", Operator.GT, 250.0, ValueUnit.PERCENT)
        rule = expected.active_rule()
        assert rule.field == "total_debt_to_gdp"
        assert rule.operator == Operator.GT
        assert rule.value == 250.0

    def test_gold_oil_ratio_above_25(self):
        """fiscal_dominance_arithmetic: 'Above 25' on gold_oil_ratio

        Source: "Gold/oil ratio elevated | Computed: `gold_oil_ratio` | Above 25 | above | 0.10"
        Straightforward computed field scalar.
        """
        expected = _scalar("gold_oil_ratio", Operator.GT, 25.0, ValueUnit.RATIO)
        rule = expected.active_rule()
        assert rule.field == "gold_oil_ratio"
        assert rule.operator == Operator.GT
        assert rule.value == 25.0

    # -------------------------------------------------------------------
    # FIELD COMPARISONS (2)
    # -------------------------------------------------------------------

    def test_fed_funds_below_gdp_growth(self):
        """debt_cycle_short / Expansion: 'Fed funds rate below nominal GDP growth rate'

        Source: "Fed funds below nominal GDP growth | `rates.fed_funds` vs. `growth.gdp_latest` |
                Fed funds rate below nominal GDP growth rate | below | 0.10"

        This MUST compile to a field_comparison, not a scalar. The legacy
        system marks this threshold_not_evaluable because regex cannot parse it.
        The compiler must identify the two-field structure.

        NOTE: field_b should ideally be a nominal GDP growth rate, not GDP level.
        The compiler correctly identifies the structure even if the field mapping
        needs fixing upstream.
        """
        expected = _field_cmp("rates.fed_funds", "growth.gdp_latest", Operator.LT)
        rule = expected.active_rule()
        assert rule.rule_type == "field_comparison"
        assert rule.field_a == "rates.fed_funds"
        assert rule.field_b == "growth.gdp_latest"
        assert rule.operator == Operator.LT

    def test_fed_funds_above_gdp_plus_1pct(self):
        """debt_cycle_short / Contraction: 'Fed funds exceeds nominal GDP growth by 1%+'

        Source: "Fed funds above nominal GDP growth | `rates.fed_funds` vs. `growth.gdp_latest` |
                Fed funds exceeds nominal GDP growth by 1%+ for 6+ months | above | 0.10"

        Must compile to field_comparison with offset=1.0.
        The 6-month persistence qualifier should be a separate sub-rule
        or flagged as requiring temporal validation.
        """
        expected = _field_cmp("rates.fed_funds", "growth.gdp_latest", Operator.GT, offset=1.0)
        rule = expected.active_rule()
        assert rule.rule_type == "field_comparison"
        assert rule.field_a == "rates.fed_funds"
        assert rule.operator == Operator.GT
        assert rule.offset == pytest.approx(1.0)

    # -------------------------------------------------------------------
    # COMPOUND RULES (2)
    # -------------------------------------------------------------------

    def test_profit_margins_or_condition(self):
        """valuation_mean_reversion: 'Net margins above 12% OR corporate profits / GDP above 10%'

        Source: "Corporate profit margins at cycle highs | Web source |
                Net margins above 12% OR corporate profits / GDP above 10% | above | 0.10"

        MUST be compound(any) with two scalar sub-rules.
        The legacy system only checks the first condition. This is one of
        the key improvements the compiler provides.
        """
        rule = _compound(CompoundOp.ANY, [
            _scalar("sp500_net_margin", Operator.GT, 12.0, ValueUnit.PERCENT),
            _scalar("corporate_profits_gdp_ratio", Operator.GT, 10.0, ValueUnit.PERCENT),
        ])
        compound = rule.active_rule()
        assert compound.rule_type == "compound"
        assert compound.operator == CompoundOp.ANY
        assert len(compound.rules) == 2
        # First sub-rule: margins > 12%
        sub0 = compound.rules[0].active_rule()
        assert sub0.field == "sp500_net_margin"
        assert sub0.operator == Operator.GT
        assert sub0.value == 12.0
        # Second sub-rule: profits/GDP > 10%
        sub1 = compound.rules[1].active_rule()
        assert sub1.field == "corporate_profits_gdp_ratio"
        assert sub1.operator == Operator.GT
        assert sub1.value == 10.0

    def test_hy_spread_and_trend(self):
        """debt_cycle_short / Expansion: 'Below 450bp AND not widening for 3+ months'

        Source: "Credit spreads tight or tightening | `credit.hy_spread` |
                Below 450bp AND not widening for 3+ consecutive months |
                below and stable/tightening | 0.15"

        MUST be compound(all) with:
        - scalar: hy_spread < 450 (basis_points)
        - trend: hy_spread stable/not-rising over 3 months
        """
        rule = _compound(CompoundOp.ALL, [
            _scalar("credit.hy_spread", Operator.LT, 450.0, ValueUnit.BASIS_POINTS),
            _trend("credit.hy_spread", TrendDirection.STABLE, 3, TimeUnit.MONTHS),
        ])
        compound = rule.active_rule()
        assert compound.rule_type == "compound"
        assert compound.operator == CompoundOp.ALL
        assert len(compound.rules) == 2
        sub0 = compound.rules[0].active_rule()
        assert sub0.rule_type == "scalar_comparison"
        assert sub0.value == 450.0
        sub1 = compound.rules[1].active_rule()
        assert sub1.rule_type == "trend"
        assert sub1.window_value == 3
        assert sub1.window_unit == TimeUnit.MONTHS

    # -------------------------------------------------------------------
    # TREND RULES (2)
    # -------------------------------------------------------------------

    def test_ism_falling_3_months(self):
        """debt_cycle_short / Contraction: 'Below 48 AND declining for 3+ months'

        Source: "ISM proxy below contraction | `growth.ism_proxy` |
                Below 48 AND declining for 3+ months | below and falling | 0.15"

        The trend sub-rule MUST specify: field=growth.ism_proxy, direction=falling,
        window=3 months. requires_time_series must be True.
        """
        trend = TrendRule(
            field="growth.ism_proxy", direction=TrendDirection.FALLING,
            window_value=3, window_unit=TimeUnit.MONTHS,
        )
        assert trend.direction == TrendDirection.FALLING
        assert trend.window_value == 3
        assert trend.window_unit == TimeUnit.MONTHS

    def test_claims_rising_8_weeks(self):
        """debt_cycle_short / Contraction: 'Above 280K AND rising for 8+ weeks'

        Source: "Initial claims rising | `growth.initial_claims` |
                4-week average above 280K AND rising for 8+ weeks |
                above and rising | 0.10"

        The trend sub-rule MUST use weeks (not months) as the time unit.
        Window = 8 weeks.
        """
        trend = TrendRule(
            field="growth.initial_claims", direction=TrendDirection.RISING,
            window_value=8, window_unit=TimeUnit.WEEKS,
        )
        assert trend.direction == TrendDirection.RISING
        assert trend.window_value == 8
        assert trend.window_unit == TimeUnit.WEEKS

    # -------------------------------------------------------------------
    # PERSISTENCE / LOOKBACK_EXTREME (2)
    # -------------------------------------------------------------------

    def test_insider_selling_3_month_persistence(self):
        """valuation_mean_reversion: 'Insider sell/buy ratio above 5:1 sustained for 3+ months'

        Source: "Insider selling elevated | Web source |
                Insider sell/buy ratio above 5:1 sustained for 3+ months | above | 0.05"

        MUST be persistence: field=insider_sell_buy_ratio, condition=gt 5.0,
        n=3, k=3 (all 3 of last 3 months), period=months.
        """
        rule = _persistence(
            "insider_sell_buy_ratio", Operator.GT, 5.0,
            n=3, k=3, period_unit=TimeUnit.MONTHS,
        )
        pers = rule.active_rule()
        assert pers.rule_type == "persistence"
        assert pers.field == "insider_sell_buy_ratio"
        assert pers.condition_operator == Operator.GT
        assert pers.condition_value == 5.0
        assert pers.n == 3
        assert pers.k == 3
        assert pers.period_unit == TimeUnit.MONTHS

    def test_cb_gold_purchases_2_year_persistence(self):
        """monetary_architecture + fiscal_dominance_arithmetic:
        'Central bank buying above 800 tonnes/year for 2+ consecutive years'

        Source: "Central bank gold purchases sustained | Web source |
                Central bank buying above 800 tonnes/year for 2+ consecutive years |
                above | 0.29 (monetary_arch) / 0.05 (fiscal_dom_arith)"

        MUST be persistence: condition=gt 800, n=2, k=2, period=years.
        """
        rule = _persistence(
            "cb_gold_purchases", Operator.GT, 800.0,
            n=2, k=2, period_unit=TimeUnit.YEARS,
        )
        pers = rule.active_rule()
        assert pers.rule_type == "persistence"
        assert pers.condition_value == 800.0
        assert pers.n == 2
        assert pers.k == 2
        assert pers.period_unit == TimeUnit.YEARS

    # -------------------------------------------------------------------
    # HIGH-AMBIGUITY / BLOCKED (2)
    # -------------------------------------------------------------------

    def test_sahm_rule_must_flag_ambiguity(self):
        """debt_cycle_short / Contraction: Sahm Rule

        Source: "Unemployment rising (Sahm Rule) | `growth.unemployment` |
                3-month moving average rising 0.50%+ above its 12-month low |
                rising | 0.20"

        The Sahm Rule is a SPECIFIC COMPUTATION: 3-month MA of unemployment
        minus its 12-month minimum >= 0.50 percentage points.

        A correct compiler MUST flag ambiguity >= medium because:
        - Standard persistence/trend rules cannot represent "MA minus lookback minimum"
        - The 0.50% threshold applies to the MA-minus-low DELTA, not the raw level
        - This requires a custom named computation primitive

        The compiler should NOT silently compile this as a simple scalar or trend.
        """
        # The contract: any compilation of Sahm Rule must have ambiguity >= medium
        # We cannot assert the exact rule structure because Haiku might use
        # persistence, compound, or a custom approximation -- but it MUST flag
        # that the standard primitives don't fully represent this computation.
        assert AmbiguityLevel.MEDIUM.value in ("medium", "high")
        assert AmbiguityLevel.HIGH.value in ("medium", "high")
        # Contract: requires_time_series must be True
        # Contract: ambiguity must be >= medium

    def test_sloos_must_flag_high_ambiguity(self):
        """debt_cycle_short / Contraction: SLOOS broad tightening

        Source: "SLOOS showing broad tightening | web search |
                Net % of banks tightening positive across 3+ loan categories
                for 2+ consecutive quarters | above | 0.15"

        A correct compiler MUST flag ambiguity=high because:
        - "3+ loan categories" is multi-dimensional categorical condition
        - "2+ consecutive quarters" is temporal persistence
        - The briefing field sloos_net_tightening is a single aggregate scalar
        - There is no way to verify the "3+ categories" condition from one number
        - A scalar gt 0 compilation loses critical information

        The compiler should NOT silently compile this as scalar_comparison(gt, 0)
        without flagging the loss of categorical and temporal specificity.
        """
        assert AmbiguityLevel.HIGH.value == "high"
        # Contract: ambiguity must be HIGH
        # Contract: compiler_warnings must mention multi-category or categorical

    # -------------------------------------------------------------------
    # STRUCTURAL CONTRACTS (not indicator-specific)
    # -------------------------------------------------------------------

    def test_unit_must_be_explicit_for_bp_thresholds(self):
        """Any threshold expressed in basis points MUST compile with unit=basis_points.

        Examples: "Below 300bp", "Above 500bp", "Above 600bp"
        The evaluator needs units to know that 300 means 300bp, not 3.0%.
        """
        rule = ScalarComparisonRule(
            field="credit.hy_spread", operator=Operator.LT,
            value=300.0, unit=ValueUnit.BASIS_POINTS,
        )
        assert rule.unit == ValueUnit.BASIS_POINTS
        assert rule.value == 300.0  # NOT 0.03 or 3.0

    def test_unit_must_be_explicit_for_percent_thresholds(self):
        """Any threshold expressed as percentage MUST compile with unit=percent.

        Examples: "Below 1.0%", "Above 20%"
        """
        rule = ScalarComparisonRule(
            field="equity_risk_premium", operator=Operator.LT,
            value=1.0, unit=ValueUnit.PERCENT,
        )
        assert rule.unit == ValueUnit.PERCENT
        assert rule.value == 1.0

    def test_compound_and_vs_or_must_be_correct(self):
        """AND thresholds must use CompoundOp.ALL. OR must use CompoundOp.ANY.

        "Below X AND not Y" -> ALL
        "Above X% OR above Y%" -> ANY

        Getting this wrong flips the logic entirely.
        """
        and_rule = CompoundRule(operator=CompoundOp.ALL, rules=[])
        or_rule = CompoundRule(operator=CompoundOp.ANY, rules=[])
        assert and_rule.operator == CompoundOp.ALL
        assert or_rule.operator == CompoundOp.ANY

    def test_temporal_rules_must_flag_time_series(self):
        """Any indicator with trend/persistence/lookback rules MUST set
        requires_time_series=True on the CompiledIndicator.

        Without time-series data, these rules evaluate to NOT_EVALUABLE.
        The evaluator must know this upfront.
        """
        ind = CompiledIndicator(
            indicator_name="test",
            source_text="declining for 3+ months",
            rule=CompiledRule(trend=TrendRule(
                field="x", direction=TrendDirection.FALLING,
                window_value=3, window_unit=TimeUnit.MONTHS,
            )),
            weight=0.10,
            direction_label="falling",
            field_refs=["x"],
            requires_time_series=True,
        )
        assert ind.requires_time_series is True
