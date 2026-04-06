# test_activation_web_integration.py -- Phase 6: Tests for WEB_FIELD_MAP resolution,
# web-enriched activation scoring, and ISM proxy override.
#
# Verifies that the data enrichment work (Phases 1-5) actually wires through
# to activation scoring: previously-skipped web-search indicators now score
# when web_sourced data is present, and scores remain stable when it's absent.
import pytest

from backend.engine.activation import (
    WEB_FIELD_MAP,
    _check_threshold,
    _extract_metric_field,
    _normalize_computed_field,
    _resolve_web_field,
    _score_phase,
    _score_to_tier,
    score_theory,
    ACTIVE_THRESHOLD,
    ADJACENT_THRESHOLD,
)
from backend.schemas.briefing import BriefingPacket, MarketData, WebSourcedData
from backend.schemas.theory import (
    ActivationPhase,
    ActivationTier,
    Direction,
    Indicator,
    TheoryModule,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_briefing(**overrides) -> BriefingPacket:
    """Minimal briefing packet for activation tests."""
    base = dict(
        growth={"real_gdp": 2.5, "unemployment": 3.8, "ism_proxy": 52.0},
        inflation={"cpi_yoy": 3.2, "core_pce": 2.8, "breakeven_5y": 2.4},
        rates={"fed_funds": 4.50, "treasury_10y": 4.35, "curve_2s10s": 0.10},
        liquidity={"fed_balance_sheet": 7_000_000, "tga": 750_000, "reverse_repo": 200_000},
        credit={"hy_spread": 350, "ig_spread": 95},
        sentiment={"consumer_sentiment": 65.0},
        computed={"net_liquidity": 6_050_000, "equity_risk_premium": 2.5,
                  "vix_vs_realized": 3.0, "buffett_indicator": 1.95,
                  "interest_receipts_ratio": 22.0},
        markets={"^VIX": MarketData(price=18.5)},
        web_sourced={},
    )
    base.update(overrides)
    return BriefingPacket(**base)


def _make_indicator(name: str, source: str, threshold: str,
                    direction: Direction = Direction.ABOVE,
                    weight: float = 0.20,
                    requires_web_search: bool = False) -> Indicator:
    return Indicator(
        name=name,
        metric_source=source,
        threshold=threshold,
        direction=direction,
        weight=weight,
        requires_web_search=requires_web_search,
    )


# ---------------------------------------------------------------------------
# _resolve_web_field tests
# ---------------------------------------------------------------------------


class TestResolveWebField:
    def test_shiller_cape_match(self):
        result = _resolve_web_field("web search: Shiller CAPE ratio from Yale")
        assert result == "shiller_cape"

    def test_finra_margin_match(self):
        result = _resolve_web_field("web search: FINRA margin statistics")
        assert result == "finra_margin_debt"

    def test_china_credit_impulse_match(self):
        result = _resolve_web_field("web search: China credit impulse (BIS)")
        assert result == "china_credit_impulse"

    def test_total_social_financing_alias(self):
        result = _resolve_web_field("web search: total social financing data from PBoC")
        assert result == "china_credit_impulse"

    def test_swift_rmb_match(self):
        result = _resolve_web_field("web search: SWIFT RMB share of global payments")
        assert result == "rmb_swift_share"

    def test_treasury_refunding_match(self):
        result = _resolve_web_field("web search: Treasury refunding data on bid-to-cover")
        assert result == "weighted_avg_interest_rate"

    def test_no_match_returns_none(self):
        result = _resolve_web_field("web search: some completely unknown indicator")
        assert result is None

    def test_case_insensitive(self):
        result = _resolve_web_field("WEB SEARCH: SHILLER CAPE RATIO")
        assert result == "shiller_cape"


class TestWebFieldMapCompleteness:
    def test_map_has_entries(self):
        assert len(WEB_FIELD_MAP) >= 30

    def test_all_entries_are_tuples(self):
        for entry in WEB_FIELD_MAP:
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            keyword, field = entry
            assert isinstance(keyword, str)
            assert isinstance(field, str)

    def test_keywords_are_lowercase(self):
        """WEB_FIELD_MAP keywords should be lowercase for matching."""
        for keyword, _ in WEB_FIELD_MAP:
            assert keyword == keyword.lower(), f"Keyword '{keyword}' not lowercase"


# ---------------------------------------------------------------------------
# _extract_metric_field tests — web-search branch
# ---------------------------------------------------------------------------


class TestExtractMetricFieldWeb:
    def test_web_search_with_known_keyword(self):
        result = _extract_metric_field("web search: Shiller CAPE ratio")
        assert result == "shiller_cape"

    def test_web_search_with_unknown_keyword(self):
        result = _extract_metric_field("web search: mystery data")
        assert result is None

    def test_backtick_field(self):
        result = _extract_metric_field("`credit.hy_spread`")
        assert result == "credit.hy_spread"

    def test_computed_expression(self):
        result = _extract_metric_field("computed: `VIX - 20d_realized_vol`")
        assert result == "vix_vs_realized"


class TestNormalizeComputedField:
    def test_vix_realized(self):
        assert _normalize_computed_field("VIX - 20d_realized_vol") == "vix_vs_realized"

    def test_qqq_iwm(self):
        assert _normalize_computed_field("QQQ / IWM price ratio") == "qqq_iwm_ratio"


# ---------------------------------------------------------------------------
# _score_phase with web-sourced indicators
# ---------------------------------------------------------------------------


class TestScorePhaseWebIntegration:
    def test_web_indicator_scored_when_data_present(self):
        """A web-search indicator with data available should be scored."""
        indicators = [
            _make_indicator("CAPE Valuation", "web search: Shiller CAPE ratio",
                            "35", Direction.ABOVE, 0.30, requires_web_search=True),
            _make_indicator("GDP Growth", "`growth.real_gdp`",
                            "2.0", Direction.ABOVE, 0.70),
        ]
        phase = ActivationPhase(
            phase_name="single", phase_label="Active", indicators=indicators,
        )
        # CAPE at 38 > 35 triggers. GDP at 2.5 > 2.0 triggers.
        bp = _make_briefing(web_sourced={
            "shiller_cape": WebSourcedData(value=38.0, source="test"),
        })
        score, results, skipped = _score_phase(phase, bp)
        assert "CAPE Valuation" in results
        assert results["CAPE Valuation"]["triggered"] is True
        assert score == pytest.approx(1.0)  # both triggered, full weight

    def test_web_indicator_skipped_when_no_data(self):
        """Without web data, web-search indicator excluded from denominator."""
        indicators = [
            _make_indicator("CAPE Valuation", "web search: Shiller CAPE ratio",
                            "35", Direction.ABOVE, 0.30, requires_web_search=True),
            _make_indicator("GDP Growth", "`growth.real_gdp`",
                            "2.0", Direction.ABOVE, 0.70),
        ]
        phase = ActivationPhase(
            phase_name="single", phase_label="Active", indicators=indicators,
        )
        bp = _make_briefing()  # no web_sourced
        score, results, skipped = _score_phase(phase, bp)
        # CAPE skipped, only GDP scored (0.70/0.70 = 1.0)
        assert any("CAPE" in s for s in skipped)
        assert "CAPE Valuation" not in results
        assert score == pytest.approx(1.0)

    def test_web_indicator_not_triggered_when_below_threshold(self):
        """Web data present but doesn't meet threshold."""
        indicators = [
            _make_indicator("CAPE Valuation", "web search: Shiller CAPE ratio",
                            "35", Direction.ABOVE, 0.50, requires_web_search=True),
            _make_indicator("GDP Growth", "`growth.real_gdp`",
                            "2.0", Direction.ABOVE, 0.50),
        ]
        phase = ActivationPhase(
            phase_name="single", phase_label="Active", indicators=indicators,
        )
        bp = _make_briefing(web_sourced={
            "shiller_cape": WebSourcedData(value=30.0, source="test"),  # below 35
        })
        score, results, skipped = _score_phase(phase, bp)
        assert results["CAPE Valuation"]["triggered"] is False
        assert score == pytest.approx(0.50)  # only GDP triggers

    def test_score_stability_without_web_data(self):
        """Pre-enrichment behavior: web indicators excluded, score same."""
        # Theory with 3 non-web + 2 web indicators
        indicators = [
            _make_indicator("A", "`growth.real_gdp`", "2.0", Direction.ABOVE, 0.30),
            _make_indicator("B", "`rates.fed_funds`", "3.0", Direction.ABOVE, 0.30),
            _make_indicator("C", "`inflation.cpi_yoy`", "2.5", Direction.ABOVE, 0.20),
            _make_indicator("D", "web search: Shiller CAPE ratio", "35",
                            Direction.ABOVE, 0.10, requires_web_search=True),
            _make_indicator("E", "web search: FINRA margin statistics", "800",
                            Direction.ABOVE, 0.10, requires_web_search=True),
        ]
        phase = ActivationPhase(
            phase_name="single", phase_label="Active", indicators=indicators,
        )
        bp = _make_briefing()  # no web data

        score, results, skipped = _score_phase(phase, bp)
        # D and E skipped. A triggers (2.5>2), B triggers (4.5>3), C triggers (3.2>2.5)
        # Score = 0.80 / 0.80 = 1.0 (denominator excludes web)
        assert score == pytest.approx(1.0)
        assert len(skipped) == 2


# ---------------------------------------------------------------------------
# ISM proxy override via get_field
# ---------------------------------------------------------------------------


class TestIsmProxyOverride:
    def test_override_when_web_ism_present(self):
        bp = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(value=52.7, source="test"),
        })
        bp.growth["ism_proxy"] = 48.0  # MANEMP proxy says contraction
        # get_field("growth.ism_proxy") should return 52.7 (web), not 48.0
        assert bp.get_field("growth.ism_proxy") == 52.7

    def test_no_override_without_web_ism(self):
        bp = _make_briefing()
        bp.growth["ism_proxy"] = 48.0
        assert bp.get_field("growth.ism_proxy") == 48.0

    def test_override_changes_activation(self):
        """ISM indicator should use actual PMI when available."""
        indicators = [
            _make_indicator("ISM PMI", "`growth.ism_proxy`", "50",
                            Direction.ABOVE, 1.0),
        ]
        phase = ActivationPhase(
            phase_name="single", phase_label="Active", indicators=indicators,
        )
        bp_proxy_only = _make_briefing()
        bp_proxy_only.growth["ism_proxy"] = 48.0  # below 50 -> not triggered

        bp_with_web = _make_briefing(web_sourced={
            "ism_pmi": WebSourcedData(value=52.7, source="test"),
        })
        bp_with_web.growth["ism_proxy"] = 48.0

        score_proxy, _, _ = _score_phase(phase, bp_proxy_only)
        score_web, _, _ = _score_phase(phase, bp_with_web)

        assert score_proxy == 0.0  # proxy says contraction
        assert score_web == 1.0  # actual ISM says expansion


# ---------------------------------------------------------------------------
# BriefingPacket.get_field resolution order
# ---------------------------------------------------------------------------


class TestGetFieldResolution:
    def test_dotted_path(self):
        bp = _make_briefing()
        assert bp.get_field("credit.hy_spread") == 350

    def test_computed_field(self):
        bp = _make_briefing()
        assert bp.get_field("net_liquidity") == 6_050_000

    def test_web_sourced_field(self):
        bp = _make_briefing(web_sourced={
            "china_credit_impulse": WebSourcedData(value=3.5, source="test"),
        })
        assert bp.get_field("china_credit_impulse") == 3.5

    def test_ticker_field(self):
        bp = _make_briefing()
        assert bp.get_field("^VIX") == 18.5

    def test_fallback_scan(self):
        bp = _make_briefing()
        # "real_gdp" without section prefix should be found by fallback scan
        assert bp.get_field("real_gdp") == 2.5

    def test_missing_field_returns_none(self):
        bp = _make_briefing()
        assert bp.get_field("nonexistent_field") is None


# ---------------------------------------------------------------------------
# Tier thresholds
# ---------------------------------------------------------------------------


class TestTierThresholds:
    def test_active_at_060(self):
        assert _score_to_tier(0.60) == ActivationTier.ACTIVE

    def test_adjacent_at_030(self):
        assert _score_to_tier(0.30) == ActivationTier.ADJACENT

    def test_inactive_below_030(self):
        assert _score_to_tier(0.29) == ActivationTier.INACTIVE

    def test_full_score(self):
        assert _score_to_tier(1.0) == ActivationTier.ACTIVE


# ---------------------------------------------------------------------------
# Two-phase scoring
# ---------------------------------------------------------------------------


class TestTwoPhaseScoring:
    def test_phase_b_priority(self):
        """Phase B active -> Phase A forced inactive."""
        theory = TheoryModule(
            theory_id="test_two_phase",
            is_two_phase=True,
            phases=[
                ActivationPhase(
                    phase_name="phase_a", phase_label="Building",
                    indicators=[
                        _make_indicator("A1", "`growth.real_gdp`", "2.0",
                                        Direction.ABOVE, 1.0),
                    ],
                ),
                ActivationPhase(
                    phase_name="phase_b", phase_label="Resolving",
                    indicators=[
                        _make_indicator("B1", "`credit.hy_spread`", "300",
                                        Direction.ABOVE, 1.0),
                    ],
                ),
            ],
        )
        bp = _make_briefing()  # GDP=2.5>2.0, HY=350>300 -- both would trigger
        result = score_theory(theory, bp)
        assert result.effective_tier == ActivationTier.ACTIVE
        assert result.effective_phase == "Resolving"
        assert result.phase_tiers["Building"] == ActivationTier.INACTIVE


# ---------------------------------------------------------------------------
# v8 remediation Task 1: metric_source resolution fixes
# ---------------------------------------------------------------------------


class TestPassthroughRemoved:
    """FRAGILITY-07: whole-string passthrough in _extract_metric_field
    must be removed. Prose metric_source strings without backtick field
    names must resolve to None, not to the whole string."""

    def test_prose_without_backtick_returns_none(self):
        """Prose metric_source that formerly passed through the whole string."""
        result = _extract_metric_field(
            "Computed: SPY earnings yield (1/PE) minus 10Y Treasury yield"
        )
        assert result is None

    def test_fred_reference_without_backtick_returns_none(self):
        result = _extract_metric_field(
            "FRED: FYOINT (federal interest outlays), FGRECPT (federal receipts)"
        )
        assert result is None

    def test_ticker_without_backtick_returns_none(self):
        result = _extract_metric_field("DXY index")
        assert result is None

    def test_backtick_field_still_works(self):
        result = _extract_metric_field("Computed: `equity_risk_premium`")
        assert result == "equity_risk_premium"

    def test_backtick_field_with_prose_still_works(self):
        result = _extract_metric_field(
            "`rates.fed_funds` (proxy: fed funds rate vs. SPY earnings yield)"
        )
        assert result == "rates.fed_funds"

    def test_web_search_still_works(self):
        result = _extract_metric_field("web search: Shiller CAPE ratio")
        assert result == "shiller_cape"


class TestGenericNormalizationRemoved:
    """BUG-04: _normalize_computed_field generic fallback must not produce
    garbage field names from arbitrary expressions."""

    def test_known_mapping_vix_realized(self):
        assert _normalize_computed_field("VIX - 20d_realized_vol") == "vix_vs_realized"

    def test_known_mapping_qqq_iwm(self):
        assert _normalize_computed_field("QQQ / IWM ratio") == "qqq_iwm_ratio"

    def test_known_mapping_spy_52w(self):
        assert _normalize_computed_field("SPY 52w high drawdown") == "spy_drawdown_from_52w_high"

    def test_unknown_expression_returns_none(self):
        """Previously returned a garbage underscore-munged string."""
        result = _normalize_computed_field("SPY earnings yield / PE ratio")
        assert result is None

    def test_another_unknown_returns_none(self):
        result = _normalize_computed_field("gold price / oil price")
        assert result is None


class TestFixedTheoryFieldResolution:
    """BUG-01: The 3 affected theory packages must now resolve
    metric_source fields correctly after backtick restoration."""

    def test_valuation_mean_reversion_erp(self):
        result = _extract_metric_field(
            "Computed: `equity_risk_premium` (SPY earnings yield minus 10Y Treasury yield)"
        )
        assert result == "equity_risk_premium"

    def test_valuation_mean_reversion_cash_yield(self):
        result = _extract_metric_field(
            "`rates.fed_funds` (proxy: fed funds rate vs. SPY earnings yield)"
        )
        assert result == "rates.fed_funds"

    def test_valuation_mean_reversion_breadth(self):
        result = _extract_metric_field(
            "Computed: `qqq_iwm_ratio` + RSP vs. SPY relative performance"
        )
        assert result == "qqq_iwm_ratio"

    def test_fiscal_arithmetic_interest_receipts(self):
        result = _extract_metric_field(
            "Computed: `interest_receipts_ratio` (FRED: FYOINT / FGRECPT annualized)"
        )
        assert result == "interest_receipts_ratio"

    def test_fiscal_arithmetic_deficit_pace(self):
        result = _extract_metric_field(
            "Computed: `deficit_pace_annualized` (FRED: FYFSD trailing annualized)"
        )
        assert result == "deficit_pace_annualized"

    def test_fiscal_arithmetic_gold_oil(self):
        result = _extract_metric_field(
            "Computed: `gold_oil_ratio` (gold price / oil price)"
        )
        assert result == "gold_oil_ratio"

    def test_capital_flows_eem_3y(self):
        result = _extract_metric_field(
            "Computed: `eem_spy_3y_relative` (EEM vs. SPY cumulative rolling 3-year relative return)"
        )
        assert result == "eem_spy_3y_relative"

    def test_capital_flows_usdcny(self):
        result = _extract_metric_field("`usdcny` (USD/CNY spot rate)")
        assert result == "usdcny"

    def test_capital_flows_eem_3m(self):
        result = _extract_metric_field(
            "Computed: `eem_spy_3m_relative` (EEM vs. SPY 3-month relative return)"
        )
        assert result == "eem_spy_3m_relative"

    def test_capital_flows_commodity(self):
        result = _extract_metric_field(
            "`commodity_index_3m_change` (broad commodity index, DBC or equivalent)"
        )
        assert result == "commodity_index_3m_change"

    def test_capital_flows_fxi(self):
        result = _extract_metric_field(
            "`fxi_3m_return` (FXI 3-month return from low)"
        )
        assert result == "fxi_3m_return"


class TestAffectedTheoryScoring:
    """End-to-end scoring for the 3 theories that were broken by BUG-01.
    Uses the real theory packages and a briefing with known values."""

    @pytest.fixture()
    def briefing(self):
        """Briefing with values that reproduce the baseline test conditions."""
        return BriefingPacket(
            growth={"real_gdp": 0.65, "unemployment": 4.3, "ism_proxy": 51.1},
            inflation={"cpi_yoy": 2.66, "core_pce": 3.06},
            rates={"fed_funds": 3.64, "treasury_10y": 4.33, "treasury_2y": 3.81},
            liquidity={"fed_balance_sheet": 6675344.0, "tga": 847718.0,
                       "reverse_repo": 327.0},
            credit={"hy_spread": 316.0, "ig_spread": 87.0},
            sentiment={},
            computed={
                "equity_risk_premium": 0.17,
                "qqq_iwm_ratio": 2.3279,
                "gold_oil_ratio": 3.11,
                "interest_receipts_ratio": 34.0,
                "deficit_pace_annualized": 3690.0,
                "interest_exceeds_defense": 287.0,
                "eem_spy_3m_relative": 7.27,
                "eem_spy_3y_relative": 9.5,
                "commodity_index_3m_change": 31.17,
                "fxi_3m_return": -7.13,
                "net_liquidity": 5827299.0,
            },
            markets={},
            web_sourced={
                "shiller_cape": WebSourcedData(value=37.94, source="test"),
                "insider_sell_buy_ratio": WebSourcedData(value=10.1111, source="test"),
                "sp500_net_margin": WebSourcedData(value=8.8621, source="test"),
                "cb_gold_purchases": WebSourcedData(value=1037.0, source="test"),
                "weighted_avg_interest_rate": WebSourcedData(value=3.355, source="test"),
                "china_credit_impulse": WebSourcedData(value=3.5, source="test"),
                "em_dm_pe_gap": WebSourcedData(value=11.284, source="test"),
                "usdcny": WebSourcedData(value=6.8947, source="test"),
            },
        )

    @pytest.fixture()
    def packages(self):
        from backend.engine.theory_loader import load_all_theory_packages
        return {p.theory_id: p for p in load_all_theory_packages()}

    def test_valuation_mean_reversion_no_longer_inactive(self, briefing, packages):
        """Was 0.294 Inactive (BUG-01), should be Active after fix."""
        from backend.engine.activation import score_package
        result = score_package(packages["valuation_mean_reversion"], briefing)
        assert result.tier == ActivationTier.ACTIVE, (
            f"Expected Active, got {result.tier} (score={result.score:.3f})"
        )
        # Score should be >0.60 (was 0.294 before fix)
        assert result.score > 0.60

    def test_fiscal_dominance_arithmetic_no_longer_inactive(self, briefing, packages):
        """Was 0.056 Inactive (BUG-01), should be Adjacent (0.556) after fix."""
        from backend.engine.activation import score_package
        result = score_package(packages["fiscal_dominance_arithmetic"], briefing)
        assert result.tier == ActivationTier.ADJACENT, (
            f"Expected Adjacent, got {result.tier} (score={result.score:.3f})"
        )
        assert abs(result.score - 0.556) < 0.01

    def test_capital_flows_no_longer_inactive(self, briefing, packages):
        """Was N/A Inactive (BUG-01), should be Adjacent (Rotation, 0.450) after fix."""
        from backend.engine.activation import score_package
        result = score_package(packages["capital_flows"], briefing)
        assert result.effective_tier == ActivationTier.ADJACENT, (
            f"Expected Adjacent, got {result.effective_tier}"
        )
        assert result.effective_phase == "Rotation"

    def test_valuation_erp_indicator_triggers(self, briefing, packages):
        """equity_risk_premium=0.17 should trigger (below 1.0%)."""
        from backend.engine.activation import score_package
        result = score_package(packages["valuation_mean_reversion"], briefing)
        erp_result = result.indicator_results.get("Equity risk premium compressed")
        assert erp_result is not None, "ERP indicator missing from results"
        assert erp_result["triggered"] is True
        assert erp_result["metric_field"] == "equity_risk_premium"

    def test_fiscal_interest_receipts_triggers(self, briefing, packages):
        """interest_receipts_ratio=34.0 should trigger (above 20%)."""
        from backend.engine.activation import score_package
        result = score_package(packages["fiscal_dominance_arithmetic"], briefing)
        ir_result = result.indicator_results.get("Interest expense / tax receipts ratio")
        assert ir_result is not None
        assert ir_result["triggered"] is True
        assert ir_result["metric_field"] == "interest_receipts_ratio"
