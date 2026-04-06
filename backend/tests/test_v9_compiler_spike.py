"""Tests for the v9 compiler spike.

Tests are organized into:
1. Schema/validator tests (offline, no API calls)
2. Compiler output shape tests (requires saved artifacts or mocks)
3. Deterministic evaluator tests (offline)
4. Compiled-vs-legacy comparison tests (offline, uses pre-compiled fixtures)

Tests marked with @pytest.mark.api require the Anthropic API key and make
real API calls. Run them explicitly with: pytest -m api
"""
import json
import os
import pytest
from pathlib import Path

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
from backend.engine.v9_spike.validator import validate_compiled_theory, ValidationReport
from backend.engine.v9_spike.series_primitives import (
    EvalResult,
    eval_rule,
    resolve_field,
    compare_values,
)
from backend.engine.v9_spike.evaluator import (
    evaluate_indicator,
    evaluate_phase,
    evaluate_theory,
)
from backend.schemas.briefing import BriefingPacket


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

BRIEFING_PATH = Path(__file__).resolve().parents[2] / "mock_data" / "briefing_packet.json"


@pytest.fixture(scope="module")
def briefing():
    """Load the frozen Task-0 briefing packet."""
    with open(BRIEFING_PATH) as f:
        return BriefingPacket(**json.load(f))


def _make_scalar_indicator(name, field, op, value, weight=0.10, unit="dimensionless"):
    """Helper to create a simple scalar indicator."""
    return CompiledIndicator(
        indicator_name=name,
        source_text=f"{field} {op} {value}",
        rule=CompiledRule(scalar_comparison=ScalarComparisonRule(
            field=field, operator=Operator(op), value=value,
            unit=ValueUnit(unit),
        )),
        weight=weight,
        direction_label="above" if op == "gt" else "below",
        field_refs=[field],
        unit=ValueUnit(unit),
    )


def _make_field_comparison_indicator(name, field_a, field_b, op, offset=0.0, weight=0.10):
    return CompiledIndicator(
        indicator_name=name,
        source_text=f"{field_a} {op} {field_b}",
        rule=CompiledRule(field_comparison=FieldComparisonRule(
            field_a=field_a, field_b=field_b,
            operator=Operator(op), offset=offset,
        )),
        weight=weight,
        direction_label="above" if op == "gt" else "below",
        field_refs=[field_a, field_b],
    )


def _make_compound_indicator(name, sub_rules, compound_op="all", weight=0.10):
    return CompiledIndicator(
        indicator_name=name,
        source_text=f"compound({compound_op})",
        rule=CompiledRule(compound=CompoundRule(
            operator=CompoundOp(compound_op),
            rules=sub_rules,
        )),
        weight=weight,
        direction_label="compound",
        field_refs=[],
    )


# -----------------------------------------------------------------------
# 1. Schema tests
# -----------------------------------------------------------------------

class TestSchema:
    def test_scalar_comparison_rule(self):
        rule = ScalarComparisonRule(
            field="growth.unemployment", operator=Operator.LT,
            value=5.0, unit=ValueUnit.PERCENT,
        )
        assert rule.rule_type == "scalar_comparison"
        assert rule.field == "growth.unemployment"
        assert rule.value == 5.0

    def test_field_comparison_rule(self):
        rule = FieldComparisonRule(
            field_a="rates.fed_funds", field_b="growth.gdp_latest",
            operator=Operator.LT, offset=0.0,
        )
        assert rule.rule_type == "field_comparison"

    def test_trend_rule(self):
        rule = TrendRule(
            field="growth.ism_proxy", direction=TrendDirection.FALLING,
            window_value=3, window_unit=TimeUnit.MONTHS,
        )
        assert rule.rule_type == "trend"
        assert rule.direction == TrendDirection.FALLING

    def test_persistence_rule(self):
        rule = PersistenceRule(
            field="insider_sell_buy_ratio",
            condition_operator=Operator.GT, condition_value=5.0,
            n=3, k=3, period_unit=TimeUnit.MONTHS,
        )
        assert rule.n == 3
        assert rule.k == 3

    def test_lookback_extreme_rule(self):
        rule = LookbackExtremeRule(
            field="qqq_iwm_ratio", extreme_type="high",
            lookback_value=2, lookback_unit=TimeUnit.YEARS,
            operator=Operator.GT,
        )
        assert rule.extreme_type == "high"

    def test_compound_rule(self):
        sub = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="credit.hy_spread", operator=Operator.LT, value=450.0,
        ))
        compound = CompoundRule(operator=CompoundOp.ALL, rules=[sub])
        assert len(compound.rules) == 1

    def test_compiled_rule_active_rule(self):
        cr = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="x", operator=Operator.GT, value=1.0,
        ))
        assert cr.active_rule() is not None
        assert cr.rule_type == "scalar_comparison"

    def test_compiled_rule_empty(self):
        cr = CompiledRule()
        assert cr.active_rule() is None
        assert cr.rule_type == "empty"

    def test_compiled_theory_artifact(self):
        ind = _make_scalar_indicator("test", "growth.unemployment", "lt", 5.0)
        phase = CompiledPhase(
            phase_name="single", phase_label="Active", indicators=[ind],
        )
        art = CompiledTheoryActivation(
            theory_id="test_theory", is_two_phase=False, phases=[phase],
        )
        assert art.theory_id == "test_theory"
        assert len(art.phases) == 1
        assert len(art.phases[0].indicators) == 1


# -----------------------------------------------------------------------
# 2. Validator tests
# -----------------------------------------------------------------------

class TestValidator:
    def test_valid_scalar_passes(self):
        ind = _make_scalar_indicator("test", "growth.unemployment", "lt", 5.0)
        phase = CompiledPhase(phase_name="single", phase_label="Active", indicators=[ind])
        art = CompiledTheoryActivation(
            theory_id="test", is_two_phase=False, phases=[phase],
        )
        report = validate_compiled_theory(art)
        assert report.passed
        assert report.error_count == 0

    def test_unresolved_field_fails(self):
        ind = CompiledIndicator(
            indicator_name="bad",
            source_text="test",
            rule=CompiledRule(scalar_comparison=ScalarComparisonRule(
                field="UNRESOLVED:missing_field", operator=Operator.GT, value=0,
            )),
            weight=0.10,
            direction_label="above",
            field_refs=["UNRESOLVED:missing_field"],
        )
        phase = CompiledPhase(phase_name="single", phase_label="Active", indicators=[ind])
        art = CompiledTheoryActivation(theory_id="test", is_two_phase=False, phases=[phase])
        report = validate_compiled_theory(art)
        assert not report.passed
        assert report.error_count >= 1

    def test_empty_rule_fails(self):
        ind = CompiledIndicator(
            indicator_name="empty",
            source_text="test",
            rule=CompiledRule(),
            weight=0.10,
            direction_label="above",
            field_refs=[],
        )
        phase = CompiledPhase(phase_name="single", phase_label="Active", indicators=[ind])
        art = CompiledTheoryActivation(theory_id="test", is_two_phase=False, phases=[phase])
        report = validate_compiled_theory(art)
        assert not report.passed

    def test_high_ambiguity_warning(self):
        ind = _make_scalar_indicator("amb", "growth.unemployment", "lt", 5.0)
        ind.ambiguity = AmbiguityLevel.HIGH
        ind.ambiguity_notes = "very ambiguous"
        phase = CompiledPhase(phase_name="single", phase_label="Active", indicators=[ind])
        art = CompiledTheoryActivation(theory_id="test", is_two_phase=False, phases=[phase])
        report = validate_compiled_theory(art)
        assert report.passed  # warnings don't fail
        assert report.warning_count >= 1

    def test_persistence_n_gt_k_fails(self):
        ind = CompiledIndicator(
            indicator_name="bad_persist",
            source_text="test",
            rule=CompiledRule(persistence=PersistenceRule(
                field="growth.unemployment",
                condition_operator=Operator.GT, condition_value=0.5,
                n=5, k=3, period_unit=TimeUnit.MONTHS,
            )),
            weight=0.10, direction_label="rising", field_refs=["growth.unemployment"],
        )
        phase = CompiledPhase(phase_name="single", phase_label="Active", indicators=[ind])
        art = CompiledTheoryActivation(theory_id="test", is_two_phase=False, phases=[phase])
        report = validate_compiled_theory(art)
        assert not report.passed

    def test_no_phases_fails(self):
        art = CompiledTheoryActivation(theory_id="test", is_two_phase=False, phases=[])
        report = validate_compiled_theory(art)
        assert not report.passed


# -----------------------------------------------------------------------
# 3. Series primitives / evaluator tests
# -----------------------------------------------------------------------

class TestSeriesPrimitives:
    def test_compare_values(self):
        assert compare_values(5.0, Operator.GT, 3.0) is True
        assert compare_values(5.0, Operator.LT, 3.0) is False
        assert compare_values(5.0, Operator.GTE, 5.0) is True
        assert compare_values(5.0, Operator.LTE, 5.0) is True
        assert compare_values(5.0, Operator.EQ, 5.0) is True
        assert compare_values(5.0, Operator.EQ, 5.1) is False

    def test_resolve_field_dotted(self, briefing):
        val = resolve_field(briefing, "growth.unemployment")
        assert val == pytest.approx(4.3)

    def test_resolve_field_computed(self, briefing):
        val = resolve_field(briefing, "equity_risk_premium")
        assert val == pytest.approx(0.19)

    def test_resolve_field_unresolved(self, briefing):
        val = resolve_field(briefing, "UNRESOLVED:foo")
        assert val is None

    def test_resolve_field_missing(self, briefing):
        val = resolve_field(briefing, "nonexistent.field.path")
        assert val is None

    def test_eval_scalar_true(self, briefing):
        rule = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="growth.unemployment", operator=Operator.LT, value=5.0,
        ))
        result, detail = eval_rule(rule, briefing)
        assert result == EvalResult.TRUE

    def test_eval_scalar_false(self, briefing):
        rule = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="growth.unemployment", operator=Operator.LT, value=3.0,
        ))
        result, detail = eval_rule(rule, briefing)
        assert result == EvalResult.FALSE

    def test_eval_field_comparison(self, briefing):
        # fed_funds (3.64) < gdp_latest (31442.483) → True
        rule = CompiledRule(field_comparison=FieldComparisonRule(
            field_a="rates.fed_funds", field_b="growth.gdp_latest",
            operator=Operator.LT,
        ))
        result, detail = eval_rule(rule, briefing)
        assert result == EvalResult.TRUE

    def test_eval_field_comparison_with_offset(self, briefing):
        # fed_funds (3.64) > gdp_latest (31442.483) + 1.0 → False
        rule = CompiledRule(field_comparison=FieldComparisonRule(
            field_a="rates.fed_funds", field_b="growth.gdp_latest",
            operator=Operator.GT, offset=1.0,
        ))
        result, detail = eval_rule(rule, briefing)
        assert result == EvalResult.FALSE

    def test_eval_trend_no_series(self, briefing):
        rule = CompiledRule(trend=TrendRule(
            field="growth.unemployment", direction=TrendDirection.FALLING,
            window_value=3, window_unit=TimeUnit.MONTHS,
        ))
        result, detail = eval_rule(rule, briefing)
        assert result == EvalResult.NOT_EVALUABLE

    def test_eval_trend_with_series(self, briefing):
        rule = CompiledRule(trend=TrendRule(
            field="growth.unemployment", direction=TrendDirection.FALLING,
            window_value=3, window_unit=TimeUnit.MONTHS,
        ))
        series = {"growth.unemployment": [4.5, 4.4, 4.3]}
        result, detail = eval_rule(rule, briefing, series)
        assert result == EvalResult.TRUE

    def test_eval_persistence_no_series(self, briefing):
        rule = CompiledRule(persistence=PersistenceRule(
            field="growth.unemployment",
            condition_operator=Operator.LT, condition_value=5.0,
            n=2, k=3, period_unit=TimeUnit.MONTHS,
        ))
        result, detail = eval_rule(rule, briefing)
        assert result == EvalResult.NOT_EVALUABLE

    def test_eval_persistence_with_series(self, briefing):
        rule = CompiledRule(persistence=PersistenceRule(
            field="growth.unemployment",
            condition_operator=Operator.LT, condition_value=5.0,
            n=2, k=3, period_unit=TimeUnit.MONTHS,
        ))
        series = {"growth.unemployment": [4.5, 5.1, 4.3]}
        result, detail = eval_rule(rule, briefing, series)
        assert result == EvalResult.TRUE  # 2 of 3 < 5.0

    def test_eval_compound_all(self, briefing):
        sub1 = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="growth.unemployment", operator=Operator.LT, value=5.0,
        ))
        sub2 = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="credit.hy_spread", operator=Operator.LT, value=450.0,
        ))
        rule = CompiledRule(compound=CompoundRule(
            operator=CompoundOp.ALL, rules=[sub1, sub2],
        ))
        result, detail = eval_rule(rule, briefing)
        assert result == EvalResult.TRUE  # 4.3 < 5.0 AND 317 < 450

    def test_eval_compound_any(self, briefing):
        sub1 = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="growth.unemployment", operator=Operator.GT, value=5.0,  # False
        ))
        sub2 = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="credit.hy_spread", operator=Operator.LT, value=450.0,  # True
        ))
        rule = CompiledRule(compound=CompoundRule(
            operator=CompoundOp.ANY, rules=[sub1, sub2],
        ))
        result, detail = eval_rule(rule, briefing)
        assert result == EvalResult.TRUE

    def test_eval_empty_rule(self, briefing):
        rule = CompiledRule()
        result, detail = eval_rule(rule, briefing)
        assert result == EvalResult.NOT_EVALUABLE


# -----------------------------------------------------------------------
# 4. Evaluator tests
# -----------------------------------------------------------------------

class TestEvaluator:
    def test_evaluate_single_indicator(self, briefing):
        ind = _make_scalar_indicator("test", "equity_risk_premium", "lt", 1.0, weight=0.25)
        result = evaluate_indicator(ind, briefing)
        assert result.triggered is True
        assert result.value == pytest.approx(0.19)

    def test_evaluate_phase_scoring(self, briefing):
        """Test that phase scoring computes correctly."""
        indicators = [
            _make_scalar_indicator("erp", "equity_risk_premium", "lt", 1.0, weight=0.25),
            _make_scalar_indicator("cape", "shiller_cape", "gt", 30.0, weight=0.20),
            _make_scalar_indicator("cash", "cash_exceeds_equity_yield", "gt", 0.0, weight=0.15),
        ]
        phase = CompiledPhase(
            phase_name="single", phase_label="Active", indicators=indicators,
        )
        result = evaluate_phase(phase, briefing)
        # ERP (0.19 < 1.0): triggered, CAPE (37.94 > 30): triggered, cash (-0.86 > 0): not
        # triggered_weight = 0.25 + 0.20 = 0.45
        # total_weight = 0.25 + 0.20 + 0.15 = 0.60
        # score = 0.45 / 0.60 = 0.75
        assert result.score == pytest.approx(0.75)
        assert result.tier == "Active"

    def test_evaluate_theory_single_phase(self, briefing):
        ind = _make_scalar_indicator("erp", "equity_risk_premium", "lt", 1.0, weight=1.0)
        phase = CompiledPhase(phase_name="single", phase_label="Active", indicators=[ind])
        art = CompiledTheoryActivation(
            theory_id="test", is_two_phase=False, phases=[phase],
        )
        result = evaluate_theory(art, briefing)
        assert result.effective_tier == "Active"

    def test_evaluate_not_evaluable_excluded_from_denominator(self, briefing):
        """NOT_EVALUABLE indicators should be excluded from the denominator."""
        good = _make_scalar_indicator("good", "equity_risk_premium", "lt", 1.0, weight=0.50)
        # Trend rule without time series → NOT_EVALUABLE
        bad = CompiledIndicator(
            indicator_name="bad",
            source_text="test",
            rule=CompiledRule(trend=TrendRule(
                field="growth.unemployment", direction=TrendDirection.FALLING,
                window_value=3, window_unit=TimeUnit.MONTHS,
            )),
            weight=0.50, direction_label="falling",
            field_refs=["growth.unemployment"],
            requires_time_series=True,
        )
        phase = CompiledPhase(
            phase_name="single", phase_label="Active", indicators=[good, bad],
        )
        result = evaluate_phase(phase, briefing)
        # Only 'good' counts: 0.50 triggered / 0.50 total = 1.0
        assert result.score == pytest.approx(1.0)

    def test_two_phase_phase_b_priority(self, briefing):
        """Phase B Active should take precedence."""
        phase_a = CompiledPhase(
            phase_name="phase_a", phase_label="Expansion",
            indicators=[_make_scalar_indicator("x", "equity_risk_premium", "lt", 1.0, weight=1.0)],
        )
        phase_b = CompiledPhase(
            phase_name="phase_b", phase_label="Contraction",
            indicators=[_make_scalar_indicator("y", "growth.unemployment", "lt", 5.0, weight=1.0)],
        )
        art = CompiledTheoryActivation(
            theory_id="test", is_two_phase=True, phases=[phase_a, phase_b],
        )
        result = evaluate_theory(art, briefing)
        assert result.effective_tier == "Active"
        assert result.effective_phase == "Contraction"


# -----------------------------------------------------------------------
# 5. Compiled-vs-legacy comparison (frozen briefing, offline)
# -----------------------------------------------------------------------

class TestCompiledVsLegacy:
    """Compare known compiled behavior against legacy baseline.

    These tests document the EXPECTED differences between the compiled
    and legacy systems. They serve as evidence for the spike report.
    """

    def test_erp_matches_legacy(self, briefing):
        """ERP: scalar comparison, should match legacy."""
        ind = _make_scalar_indicator("ERP", "equity_risk_premium", "lt", 1.0, weight=0.25)
        result = evaluate_indicator(ind, briefing)
        assert result.triggered is True  # legacy: True (0.19 < 1.0)

    def test_cape_matches_legacy(self, briefing):
        """CAPE: scalar comparison, should match legacy."""
        ind = _make_scalar_indicator("CAPE", "shiller_cape", "gt", 30.0, weight=0.20)
        result = evaluate_indicator(ind, briefing)
        assert result.triggered is True  # legacy: True (37.94 > 30)

    def test_cash_yield_matches_legacy(self, briefing):
        """Cash yield: scalar comparison, should match legacy."""
        ind = _make_scalar_indicator("Cash", "cash_exceeds_equity_yield", "gt", 0.0, weight=0.15)
        result = evaluate_indicator(ind, briefing)
        assert result.triggered is False  # legacy: False (-0.86 < 0)

    def test_profit_margins_compound_improves_on_legacy(self, briefing):
        """Profit margins: legacy checks only one field, compiled checks OR of two.

        Legacy: sp500_net_margin (8.86) > 12 → False
        Compiled: sp500_net_margin > 12 OR corporate_profits_gdp_ratio > 10 → True
        This is a JUSTIFIED IMPROVEMENT: the theory says "Net margins above 12% OR
        corporate profits / GDP above 10%". Legacy regex missed the OR condition.
        """
        sub1 = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="sp500_net_margin", operator=Operator.GT, value=12.0,
        ))
        sub2 = CompiledRule(scalar_comparison=ScalarComparisonRule(
            field="corporate_profits_gdp_ratio", operator=Operator.GT, value=10.0,
        ))
        ind = _make_compound_indicator("Profit margins", [sub1, sub2], "any", weight=0.10)
        result = evaluate_indicator(ind, briefing)
        assert result.triggered is True  # 11.4 > 10 via second condition

    def test_fed_funds_vs_gdp_field_comparison(self, briefing):
        """Fed funds below nominal GDP: compiled correctly identifies field comparison.

        Legacy: threshold_not_evaluable (regex can't parse prose)
        Compiled: field_comparison(fed_funds < gdp_latest) → True

        NOTE: Both are semantically wrong because gdp_latest is GDP level ($B),
        not nominal growth rate (%). But the compiled version at least correctly
        identifies the STRUCTURE of the comparison.
        """
        ind = _make_field_comparison_indicator(
            "Fed funds vs GDP", "rates.fed_funds", "growth.gdp_latest", "lt",
        )
        result = evaluate_indicator(ind, briefing)
        assert result.triggered is True  # 3.64 < 31442.483

    def test_ism_expansion_matches_legacy(self, briefing):
        """ISM > 50: simple scalar, should match."""
        ind = _make_scalar_indicator("ISM", "growth.ism_proxy", "gt", 50.0, weight=0.15)
        result = evaluate_indicator(ind, briefing)
        assert result.triggered is True  # 52.7 > 50

    def test_hy_spread_expansion_matches_legacy(self, briefing):
        """HY spread < 450bp: scalar part should match legacy."""
        ind = _make_scalar_indicator("HY", "credit.hy_spread", "lt", 450.0, weight=0.15)
        result = evaluate_indicator(ind, briefing)
        assert result.triggered is True  # 317 < 450

    def test_curve_expansion_matches_legacy(self, briefing):
        """Yield curve > -0.50: scalar, should match."""
        ind = _make_scalar_indicator("Curve", "rates.curve_2s10s", "gt", -0.50, weight=0.10)
        result = evaluate_indicator(ind, briefing)
        assert result.triggered is True  # 0.52 > -0.50


# -----------------------------------------------------------------------
# 6. API-dependent tests (skipped unless --run-api or marker present)
# -----------------------------------------------------------------------

api = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


@api
class TestHaikuCompilerAPI:
    """Tests that make real Haiku API calls. Run with pytest -m 'not skipif'."""

    def test_compile_single_scalar_indicator(self):
        from backend.engine.v9_spike.haiku_compiler import HaikuCompiler

        compiler = HaikuCompiler()
        indicators = [{
            "indicator_name": "ISM proxy above contraction",
            "metric_source": "`growth.ism_proxy` (MANEMP)",
            "threshold": "Above 50",
            "direction": "above",
            "weight": 0.15,
            "data_ownership": "mechanical",
        }]
        results, stats = compiler.compile_indicators(indicators, "test", "Active")

        assert len(results) == 1
        assert results[0].indicator_name == "ISM proxy above contraction"
        rule = results[0].rule.active_rule()
        assert rule is not None
        # Should be a scalar comparison
        if hasattr(rule, 'field'):
            assert "ism_proxy" in rule.field.lower() or "growth.ism_proxy" in rule.field

    def test_compile_returns_valid_json(self):
        from backend.engine.v9_spike.haiku_compiler import HaikuCompiler

        compiler = HaikuCompiler()
        indicators = [{
            "indicator_name": "Test indicator",
            "metric_source": "`rates.fed_funds`",
            "threshold": "Above 3.0%",
            "direction": "above",
            "weight": 0.10,
            "data_ownership": "mechanical",
        }]
        results, stats = compiler.compile_indicators(indicators, "test", "Active")
        assert "error" not in stats
        assert stats["indicators_received"] == 1
