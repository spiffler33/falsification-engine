# test_pipeline_e2e.py -- Phase 6: End-to-end pipeline test with mock data.
# Simulates: FRED + Yahoo + Web -> BriefingPacket -> Validation -> Activation
# Verifies the full data flow without live API calls.
from datetime import datetime, timezone

import pytest

from backend.engine.activation import (
    score_all_theories,
    score_theory,
    ActivationTier,
)
from backend.engine.validation_agent import validate_briefing
from backend.schemas.briefing import BriefingPacket, MarketData, WebSourcedData
from backend.schemas.theory import (
    ActivationPhase,
    ActivationTier,
    Direction,
    Indicator,
    TheoryModule,
)


# ---------------------------------------------------------------------------
# Realistic mock data — simulates full pipeline output
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc).isoformat()


def _realistic_briefing() -> BriefingPacket:
    """Construct a BriefingPacket that matches real pipeline output.

    All values are plausible macro data as of early 2026.
    Includes FRED sections, computed metrics, market data, and web-sourced data.
    """
    return BriefingPacket(
        timestamp=_NOW,
        staleness_hours=0.5,
        growth={
            "gdp_latest": 29_350,
            "real_gdp": 2.3,
            "unemployment": 4.1,
            "initial_claims": 225_000,
            "ism_proxy": 48.0,  # MANEMP-derived, says contraction
            "nonfarm_payrolls": 180,
        },
        inflation={
            "cpi_yoy": 3.1,
            "core_pce": 2.7,
            "breakeven_5y": 2.35,
            "breakeven_10y": 2.20,
        },
        rates={
            "fed_funds": 4.50,
            "treasury_2y": 4.20,
            "treasury_10y": 4.40,
            "treasury_30y": 4.55,
            "treasury_3m": 4.52,
            "curve_2s10s": 0.20,
            "curve_3m10y": -0.12,
        },
        liquidity={
            "fed_balance_sheet": 6_800_000,
            "tga": 720_000,
            "reverse_repo": 180_000,
            "m2": 21_200,
        },
        credit={
            "hy_spread": 340,
            "ig_spread": 92,
            "sloos_tightening_ci": 4.8,
        },
        sentiment={
            "consumer_sentiment": 63.5,
        },
        computed={
            "net_liquidity": 5_900_000,  # BS - TGA - RRP
            "equity_risk_premium": 2.1,
            "vix_vs_realized": 2.8,
            "spy_drawdown_from_52w_high": -5.2,
            "qqq_iwm_ratio": 3.1,
            "federal_debt_to_gdp": 123.5,
            "interest_receipts_ratio": 21.5,
            "buffett_indicator": 1.92,
            "deficit_pace_annualized": 2_800,
            "fed_bs_gdp_ratio": 23.2,
            "corporate_profits_gdp_ratio": 9.8,
            "net_liquidity_30d_change": -45_000,
            "foreign_treasury_holdings_pct": 29.5,
            "interest_exceeds_defense": 1,
            "sloos_net_tightening": 4.8,
        },
        markets={
            "^VIX": MarketData(price=19.2, return_1m=-0.05, return_3m=0.12, return_12m=-0.08),
            "SPY": MarketData(price=520.0, return_1m=-0.02, return_3m=0.04, return_12m=0.12),
            "TLT": MarketData(price=88.0, return_1m=0.01, return_3m=-0.03, return_12m=-0.08),
            "GLD": MarketData(price=245.0, return_1m=0.03, return_3m=0.08, return_12m=0.25),
            "DXY": MarketData(price=104.5, return_1m=0.01, return_3m=-0.02, return_12m=0.03),
            "HYG": MarketData(price=78.0, return_1m=0.00, return_3m=0.02, return_12m=0.05),
        },
        web_sourced={
            "shiller_cape": WebSourcedData(value=37.9, source="multpl.com", fetched_at=_NOW, confidence="high"),
            "ism_pmi": WebSourcedData(value=52.7, source="investing.com", fetched_at=_NOW, confidence="medium"),
            "total_debt_to_gdp": WebSourcedData(value=256.7, source="FRED Z.1", fetched_at=_NOW, confidence="high"),
            "top10_wealth_share": WebSourcedData(value=68.1, source="FRED DFA", fetched_at=_NOW, confidence="high"),
            "deficit_pct_gdp": WebSourcedData(value=11.7, source="FRED MTSDS", fetched_at=_NOW, confidence="high"),
            "weighted_avg_interest_rate": WebSourcedData(value=3.36, source="Treasury", fetched_at=_NOW, confidence="high"),
            "usdcny": WebSourcedData(value=6.89, source="er-api.com", fetched_at=_NOW, confidence="high"),
            "finra_margin_debt": WebSourcedData(value=1253.0, source="FINRA", fetched_at=_NOW, confidence="high"),
            "china_credit_impulse": WebSourcedData(value=3.5, source="FRED BIS", fetched_at=_NOW, confidence="high"),
            "consumer_confidence": WebSourcedData(value=98.9, source="FRED OECD", fetched_at=_NOW, confidence="medium"),
            "insider_sell_buy_ratio": WebSourcedData(value=2.57, source="openinsider", fetched_at=_NOW, confidence="medium"),
            "sp500_net_margin": WebSourcedData(value=8.9, source="estimated", fetched_at=_NOW, confidence="low"),
            "passive_fund_share": WebSourcedData(value=59.0, source="estimate", fetched_at=_NOW, confidence="low"),
            "cb_gold_purchases": WebSourcedData(value=1037.0, source="WGC", fetched_at=_NOW, confidence="low"),
            "em_dm_pe_gap": WebSourcedData(value=11.3, source="multpl+est", fetched_at=_NOW, confidence="low"),
            "rmb_swift_share": WebSourcedData(value=3.89, source="SWIFT", fetched_at=_NOW, confidence="low"),
        },
    )


def _make_theory_valuation() -> TheoryModule:
    """Simplified valuation_mean_reversion theory for E2E testing."""
    return TheoryModule(
        theory_id="valuation_mean_reversion",
        title="Valuation Mean Reversion",
        is_two_phase=False,
        phases=[ActivationPhase(
            phase_name="single",
            phase_label="Active",
            indicators=[
                Indicator(name="Shiller CAPE", metric_source="web search: Shiller CAPE ratio",
                          threshold="30", direction=Direction.ABOVE, weight=0.25,
                          requires_web_search=True),
                Indicator(name="Buffett Indicator", metric_source="web search: total US market cap / GDP",
                          threshold="1.5", direction=Direction.ABOVE, weight=0.15,
                          requires_web_search=True),
                Indicator(name="Equity Risk Premium", metric_source="`equity_risk_premium`",
                          threshold="3.0", direction=Direction.BELOW, weight=0.20),
                Indicator(name="VIX", metric_source="`^VIX`",
                          threshold="14", direction=Direction.ABOVE, weight=0.15),
                Indicator(name="Insider Sell/Buy", metric_source="web search: insider transactions ratio",
                          threshold="2.0", direction=Direction.ABOVE, weight=0.10,
                          requires_web_search=True),
                Indicator(name="Profit Margins", metric_source="web search: S&P 500 net profit margin",
                          threshold="12", direction=Direction.BELOW, weight=0.10,
                          requires_web_search=True),
                Indicator(name="Passive Fund Share", metric_source="web search: ICI or Morningstar passive share",
                          threshold="50", direction=Direction.ABOVE, weight=0.05,
                          requires_web_search=True),
            ],
        )],
    )


def _make_theory_fiscal_arith() -> TheoryModule:
    """Simplified fiscal_dominance_arithmetic theory for E2E testing."""
    return TheoryModule(
        theory_id="fiscal_dominance_arithmetic",
        title="Fiscal Dominance: Arithmetic",
        is_two_phase=False,
        phases=[ActivationPhase(
            phase_name="single",
            phase_label="Active",
            indicators=[
                Indicator(name="Interest/Receipts", metric_source="web search: CBO projections interest vs receipts",
                          threshold="15", direction=Direction.ABOVE, weight=0.25,
                          requires_web_search=True),
                Indicator(name="Avg Interest Rate", metric_source="web search: weighted average interest rate on debt",
                          threshold="3.0", direction=Direction.ABOVE, weight=0.20,
                          requires_web_search=True),
                Indicator(name="Deficit/GDP", metric_source="`deficit_pace_annualized`",
                          threshold="1500", direction=Direction.ABOVE, weight=0.20),
                Indicator(name="Debt/GDP", metric_source="`federal_debt_to_gdp`",
                          threshold="100", direction=Direction.ABOVE, weight=0.20),
                Indicator(name="Fed Funds", metric_source="`rates.fed_funds`",
                          threshold="3.5", direction=Direction.ABOVE, weight=0.15),
            ],
        )],
    )


def _make_theory_two_phase() -> TheoryModule:
    """Simplified two-phase structural_fragility theory."""
    return TheoryModule(
        theory_id="structural_fragility",
        is_two_phase=True,
        phases=[
            ActivationPhase(
                phase_name="phase_a",
                phase_label="Building",
                indicators=[
                    Indicator(name="VIX Low", metric_source="`^VIX`",
                              threshold="20", direction=Direction.BELOW, weight=0.40),
                    Indicator(name="CAPE High", metric_source="web search: Shiller CAPE ratio",
                              threshold="30", direction=Direction.ABOVE, weight=0.30,
                              requires_web_search=True),
                    Indicator(name="Margin Debt", metric_source="web search: FINRA margin statistics",
                              threshold="800", direction=Direction.ABOVE, weight=0.30,
                              requires_web_search=True),
                ],
            ),
            ActivationPhase(
                phase_name="phase_b",
                phase_label="Resolving",
                indicators=[
                    Indicator(name="VIX Spike", metric_source="`^VIX`",
                              threshold="25", direction=Direction.ABOVE, weight=0.50),
                    Indicator(name="HY Spread Wide", metric_source="`credit.hy_spread`",
                              threshold="400", direction=Direction.ABOVE, weight=0.50),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------


class TestPipelineE2E:
    """Full pipeline flow: Briefing -> Validation -> Activation."""

    def test_validation_on_realistic_briefing(self):
        bp = _realistic_briefing()
        report = validate_briefing(bp)

        assert report.overall_quality in ("good", "degraded")
        # ISM cross-source: proxy=48 vs actual=52.7 -> error
        cross = [c for c in report.checks if c.check_type == "cross_source"]
        assert len(cross) >= 1

    def test_ism_override_in_realistic_briefing(self):
        bp = _realistic_briefing()
        # ISM proxy=48, web ISM=52.7. Override should return 52.7
        assert bp.get_field("growth.ism_proxy") == 52.7

    def test_web_sourced_fields_resolve(self):
        bp = _realistic_briefing()
        assert bp.get_field("shiller_cape") == 37.9
        assert bp.get_field("china_credit_impulse") == 3.5
        assert bp.get_field("usdcny") == 6.89
        assert bp.get_field("finra_margin_debt") == 1253.0

    def test_activation_valuation_all_web_indicators_scored(self):
        bp = _realistic_briefing()
        theory = _make_theory_valuation()
        result = score_theory(theory, bp)

        # All 7 indicators should be scored (none skipped) because
        # we have web data for all web-search fields
        assert len(result.skipped_indicators) == 0
        assert len(result.indicator_results) == 7

    def test_activation_valuation_score_plausible(self):
        bp = _realistic_briefing()
        theory = _make_theory_valuation()
        result = score_theory(theory, bp)

        # CAPE=37.9>30 yes, Buffett=1.92>1.5 yes, ERP=2.1<3 yes,
        # VIX=19.2>14 yes, Insider=2.57>2 yes,
        # Margins=8.9<12 yes, Passive=59>50 yes -- all trigger
        assert result.score > 0.8
        assert result.tier == ActivationTier.ACTIVE

    def test_activation_fiscal_arith_web_enriched(self):
        bp = _realistic_briefing()
        theory = _make_theory_fiscal_arith()
        result = score_theory(theory, bp)

        # Interest/Receipts=21.5>15 yes, AvgRate=3.36>3 yes,
        # Deficit=2800>1500 yes, Debt/GDP=123.5>100 yes, FF=4.5>3.5 yes
        assert result.score == pytest.approx(1.0)
        assert result.tier == ActivationTier.ACTIVE
        assert len(result.skipped_indicators) == 0

    def test_activation_two_phase_building(self):
        """Phase B not triggered, Phase A active with web data."""
        bp = _realistic_briefing()
        theory = _make_theory_two_phase()
        result = score_theory(theory, bp)

        # Phase B: VIX=19.2<25 no, HY=340<400 no -> inactive
        # Phase A: VIX=19.2<20 yes, CAPE=37.9>30 yes, Margin=1253>800 yes
        assert result.phase_tiers["Resolving"] == ActivationTier.INACTIVE
        assert result.phase_tiers["Building"] == ActivationTier.ACTIVE
        assert result.effective_tier == ActivationTier.ACTIVE
        assert result.effective_phase == "Building"

    def test_activation_without_web_data_fewer_indicators(self):
        """Without web data, web indicators skipped but scores still valid."""
        bp = _realistic_briefing()
        bp.web_sourced = {}  # strip web data

        theory = _make_theory_valuation()
        result = score_theory(theory, bp)

        # 4 web indicators skipped (CAPE, Insider, Margins, Passive).
        # Buffett Indicator resolves to computed.buffett_indicator via WEB_FIELD_MAP.
        # ERP, VIX, and Buffett scored = 3 indicators.
        assert len(result.skipped_indicators) == 4
        assert len(result.indicator_results) == 3

    def test_score_all_theories(self):
        bp = _realistic_briefing()
        theories = [
            _make_theory_valuation(),
            _make_theory_fiscal_arith(),
            _make_theory_two_phase(),
        ]
        results = score_all_theories(theories, bp)
        assert len(results) == 3
        assert all(r.theory_id for r in results)

    def test_validation_then_activation_full_pipeline(self):
        """Complete pipeline: build -> validate -> score -> check coverage."""
        bp = _realistic_briefing()

        # Step 1: Validate
        report = validate_briefing(bp)
        bp.data_quality = report.model_dump()

        # Step 2: Score all theories
        theories = [
            _make_theory_valuation(),
            _make_theory_fiscal_arith(),
            _make_theory_two_phase(),
        ]
        results = score_all_theories(theories, bp)

        # Step 3: Coverage report
        total_indicators = 0
        scored_indicators = 0
        skipped_indicators = 0
        for r in results:
            scored_indicators += len(r.indicator_results)
            skipped_indicators += len(r.skipped_indicators)
            total_indicators += scored_indicators + skipped_indicators

        # With web data, all indicators should be scored
        assert skipped_indicators == 0
        assert scored_indicators > 0

        # Verify data_quality was stored
        assert bp.data_quality.get("overall_quality") in ("good", "degraded", "poor")

    def test_net_liquidity_consistency_check(self):
        """Validation catches net_liq != BS - TGA - RRP."""
        bp = _realistic_briefing()
        # Our realistic briefing: BS=6.8M, TGA=720K, RRP=180K
        # Expected: 6,800,000 - 720,000 - 180,000 = 5,900,000
        # We set net_liq to 5,900,000 which is correct
        report = validate_briefing(bp)
        consistency_errors = [c for c in report.checks
                              if c.check_type == "consistency" and c.field == "net_liquidity"]
        assert len(consistency_errors) == 0
