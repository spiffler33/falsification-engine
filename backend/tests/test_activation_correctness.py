# test_activation_correctness.py -- Task 4: Frozen expected-output correctness harness
#
# PURPOSE: Permanent semantic regression gate for the activation scoring engine.
# Freezes the post-Task-3 behavior so any future change that alters field
# resolution, threshold parsing, trigger states, scoring, or denominator
# policy fails loudly.
#
# INPUT: mock_data/briefing_packet.json (frozen at Task 0, 2026-04-06)
# SOURCE: All 8 theory packages in theories/THEORY_MODULE_*_v2/
#
# DELIBERATE UPDATE POLICY:
# - Do NOT auto-regenerate these fixtures.
# - To update, manually change the specific fixture value that moved
#   and document why in the commit message.
# - If a test fails, investigate the cause before updating the fixture.
#   A failing test means either:
#   (a) intended behavior changed (update fixture deliberately), or
#   (b) unintended semantic drift (fix the code).
#
# COVERAGE: All 8 theories, all scored indicators, all exclusion states,
#           all coverage/denominator metrics, ceiling-hit visibility.

import json
import pytest
from pathlib import Path

from backend.engine.theory_loader import load_all_theory_packages
from backend.engine.activation import score_all_packages, _extract_number
from backend.schemas.briefing import BriefingPacket


# -----------------------------------------------------------------------
# Frozen briefing fixture
# -----------------------------------------------------------------------

BRIEFING_PATH = Path(__file__).resolve().parents[2] / "mock_data" / "briefing_packet.json"


@pytest.fixture(scope="module")
def briefing():
    """Load the frozen Task-0 briefing packet."""
    with open(BRIEFING_PATH) as f:
        return BriefingPacket(**json.load(f))


@pytest.fixture(scope="module")
def all_results(briefing):
    """Score all 8 theories against the frozen briefing, keyed by theory_id."""
    packages = load_all_theory_packages()
    return {r.theory_id: r for r in score_all_packages(packages, briefing)}


# -----------------------------------------------------------------------
# Coverage computation helper
# -----------------------------------------------------------------------

def _compute_coverage(result):
    """Compute coverage metrics from an ActivationResult.

    Returns a dict with:
      total_in_results:       number of entries in indicator_results
      skipped_web_qualitative: len(skipped_indicators)
      evaluated:              indicators scored in the denominator
      excluded:               indicators excluded from denominator (data_unavailable / threshold_not_evaluable)
      triggered:              evaluated indicators that triggered
      evaluated_weight:       sum of weights of evaluated indicators
      triggered_weight:       sum of weights of triggered indicators
      excluded_weight:        sum of weights of excluded indicators
    """
    total = len(result.indicator_results)
    skipped_count = len(result.skipped_indicators)

    evaluated = 0
    excluded = 0
    triggered_count = 0
    triggered_weight = 0.0
    evaluated_weight = 0.0
    excluded_weight = 0.0

    for name, info in result.indicator_results.items():
        reason = info.get("reason", "")
        if reason in ("data_unavailable", "threshold_not_evaluable"):
            excluded += 1
            excluded_weight += info["weight"]
        else:
            evaluated += 1
            evaluated_weight += info["weight"]
            if info["triggered"]:
                triggered_count += 1
                triggered_weight += info["weight"]

    return {
        "total_in_results": total,
        "skipped_web_qualitative": skipped_count,
        "evaluated": evaluated,
        "excluded": excluded,
        "triggered": triggered_count,
        "evaluated_weight": round(evaluated_weight, 4),
        "triggered_weight": round(triggered_weight, 4),
        "excluded_weight": round(excluded_weight, 4),
    }


# -----------------------------------------------------------------------
# Assertion helpers
# -----------------------------------------------------------------------

def _assert_indicator(actual: dict, expected: dict, indicator_name: str, theory_id: str):
    """Assert all frozen fields of a single indicator match expectations.

    Provides descriptive failure messages so the operator knows exactly
    what moved: field resolution, trigger state, value, etc.
    """
    prefix = f"[{theory_id}] {indicator_name}"

    assert actual["triggered"] == expected["triggered"], (
        f"{prefix}: triggered={actual['triggered']}, expected={expected['triggered']}"
    )
    assert actual["metric_field"] == expected["metric_field"], (
        f"{prefix}: metric_field={actual['metric_field']!r}, expected={expected['metric_field']!r}"
    )
    assert actual["weight"] == pytest.approx(expected["weight"], abs=1e-6), (
        f"{prefix}: weight={actual['weight']}, expected={expected['weight']}"
    )

    # Value comparison (None-safe)
    if expected["value"] is None:
        assert actual["value"] is None, (
            f"{prefix}: value={actual['value']}, expected=None"
        )
    else:
        assert actual["value"] == pytest.approx(expected["value"], abs=1e-2), (
            f"{prefix}: value={actual['value']}, expected={expected['value']}"
        )

    # Direction: only present for evaluated (non-excluded) indicators
    if "direction" in expected:
        assert actual.get("direction") == expected["direction"], (
            f"{prefix}: direction={actual.get('direction')!r}, expected={expected['direction']!r}"
        )

    # Reason: only present for excluded indicators
    if "reason" in expected:
        assert actual.get("reason") == expected["reason"], (
            f"{prefix}: reason={actual.get('reason')!r}, expected={expected['reason']!r}"
        )


# =======================================================================
# FROZEN EXPECTED OUTPUTS
#
# Each dict below encodes the exact post-Task-3 intended behavior.
# To update, change the specific value and explain why in the commit.
# =======================================================================


# -----------------------------------------------------------------------
# 1. valuation_mean_reversion -- Score: 0.705882 (Active)
# -----------------------------------------------------------------------

VALUATION_MR_INDICATORS = {
    "Equity risk premium compressed": {
        "triggered": True, "value": 0.19, "metric_field": "equity_risk_premium",
        "weight": 0.25, "direction": "below",
    },
    "Shiller CAPE elevated": {
        "triggered": True, "value": 37.94, "metric_field": "shiller_cape",
        "weight": 0.20, "direction": "above",
    },
    "Short-term cash yield exceeds equity earnings yield": {
        "triggered": False, "value": -0.86, "metric_field": "cash_exceeds_equity_yield",
        "weight": 0.15, "direction": "above",
    },
    "Corporate profit margins at cycle highs": {
        "triggered": False, "value": 8.8621, "metric_field": "sp500_net_margin",
        "weight": 0.10, "direction": "above",
    },
    "Market breadth narrow": {
        "triggered": True, "value": 2.3279, "metric_field": "qqq_iwm_ratio",
        "weight": 0.10, "direction": "above",
    },
    "Insider selling elevated": {
        "triggered": True, "value": 19.0, "metric_field": "insider_sell_buy_ratio",
        "weight": 0.05, "direction": "above",
    },
}

VALUATION_MR_COVERAGE = {
    "total_in_results": 6, "skipped_web_qualitative": 1,
    "evaluated": 6, "excluded": 0, "triggered": 4,
    "evaluated_weight": 0.8500, "triggered_weight": 0.6000, "excluded_weight": 0.0,
}


# -----------------------------------------------------------------------
# 2. debt_cycle_short -- Contraction: 0.300 (Adjacent), Expansion: 1.000 (Active)
#    CEILING HIT: Expansion scores 1.000 with shrunken denominator.
#    2 indicators excluded (threshold_not_evaluable), all 6 remaining trigger.
# -----------------------------------------------------------------------

DEBT_SHORT_INDICATORS = {
    # -- Contraction phase --
    "ISM proxy below contraction": {
        "triggered": False, "value": 52.7, "metric_field": "growth.ism_proxy",
        "weight": 0.15, "direction": "below",
    },
    "Unemployment rising (Sahm Rule)": {
        # BUG-03: extracts "3" from "3-month moving average"; 4.3 > 3 triggers.
        "triggered": True, "value": 4.3, "metric_field": "growth.unemployment",
        "weight": 0.20, "direction": "rising",
    },
    "Credit spreads widening sharply": {
        "triggered": False, "value": 317.0, "metric_field": "credit.hy_spread",
        "weight": 0.15, "direction": "above",
    },
    "Yield curve re-steepening from deep inversion": {
        "triggered": False, "value": 0.52, "metric_field": "rates.curve_2s10s",
        "weight": 0.15, "direction": "rising",
    },
    "Initial claims rising": {
        # Task 3 K-suffix fix: 202000 < 280000, correctly NOT triggered.
        "triggered": False, "value": 202000.0, "metric_field": "growth.initial_claims",
        "weight": 0.10, "direction": "above",
    },
    "Fed funds above nominal GDP growth": {
        # Known field wiring issue: value is GDP level ($B), not rate comparison.
        # 31442.483 > 1 triggers trivially. Current frozen behavior.
        "triggered": True, "value": 31442.483, "metric_field": "growth.gdp_latest",
        "weight": 0.10, "direction": "above",
    },
    "SLOOS showing broad tightening": {
        "triggered": False, "value": 0.0, "metric_field": "sloos_net_tightening",
        "weight": 0.15, "direction": "above",
    },
    # -- Expansion phase --
    "ISM proxy above contraction": {
        "triggered": True, "value": 52.7, "metric_field": "growth.ism_proxy",
        "weight": 0.15, "direction": "above",
    },
    "Unemployment low or falling": {
        "triggered": True, "value": 4.3, "metric_field": "growth.unemployment",
        "weight": 0.15, "direction": "below",
    },
    "Credit spreads tight or tightening": {
        "triggered": True, "value": 317.0, "metric_field": "credit.hy_spread",
        "weight": 0.15, "direction": "below",
    },
    "Yield curve not deeply inverted": {
        "triggered": True, "value": 0.52, "metric_field": "rates.curve_2s10s",
        "weight": 0.10, "direction": "above",
    },
    "Initial claims low": {
        # Task 3 K-suffix fix: 202000 < 250000, correctly triggered.
        "triggered": True, "value": 202000.0, "metric_field": "growth.initial_claims",
        "weight": 0.10, "direction": "below",
    },
    "Consumer/business confidence": {
        "triggered": True, "value": 98.913, "metric_field": "consumer_confidence",
        "weight": 0.10, "direction": "above",
    },
    # -- Expansion phase: excluded indicators --
    "Fed funds below nominal GDP growth": {
        "triggered": False, "value": 31442.483, "metric_field": "growth.gdp_latest",
        "weight": 0.10, "reason": "threshold_not_evaluable",
    },
    "Net credit growth positive": {
        "triggered": False, "value": 0.0, "metric_field": "sloos_net_tightening",
        "weight": 0.15, "reason": "threshold_not_evaluable",
    },
}

DEBT_SHORT_COVERAGE = {
    "total_in_results": 15, "skipped_web_qualitative": 2,
    "evaluated": 13, "excluded": 2, "triggered": 8,
    "evaluated_weight": 1.7500, "triggered_weight": 1.0500, "excluded_weight": 0.2500,
}


# -----------------------------------------------------------------------
# 3. debt_cycle_long -- Score: 0.900 (Active)
# -----------------------------------------------------------------------

DEBT_LONG_INDICATORS = {
    "Total debt / GDP above historical warning level": {
        "triggered": True, "value": 256.7205, "metric_field": "total_debt_to_gdp",
        "weight": 0.25, "direction": "above",
    },
    "Fed balance sheet / GDP elevated": {
        # Task 1 fix: uses fed_bs_gdp_ratio (21.2%) not raw fed_balance_sheet.
        "triggered": True, "value": 21.2, "metric_field": "fed_bs_gdp_ratio",
        "weight": 0.25, "direction": "above",
    },
    "Rates at or near effective lower bound within recent memory": {
        # C-02: threshold extracts "0" from "0-0.25%"; 3.64 > 0 trivially true.
        "triggered": True, "value": 3.64, "metric_field": "rates.fed_funds",
        "weight": 0.15, "direction": "above",
    },
    "Fiscal deficit as primary growth driver": {
        # Uses interest_exceeds_defense (287.0) against threshold extracting "5".
        "triggered": True, "value": 287.0, "metric_field": "interest_exceeds_defense",
        "weight": 0.15, "direction": "above",
    },
    "Wealth inequality at cycle-characteristic extremes": {
        # Threshold "Top 10% wealth share above 70%" extracts "10" not "70".
        # 68.1 > 10 triggers. Known extraction limitation.
        "triggered": True, "value": 68.1, "metric_field": "top10_wealth_share",
        "weight": 0.10, "direction": "above",
    },
    "Negative real rates during expansion": {
        "triggered": False, "value": 0.98, "metric_field": "real_fed_funds_rate",
        "weight": 0.10, "direction": "below",
    },
}

DEBT_LONG_COVERAGE = {
    "total_in_results": 6, "skipped_web_qualitative": 0,
    "evaluated": 6, "excluded": 0, "triggered": 5,
    "evaluated_weight": 1.0000, "triggered_weight": 0.9000, "excluded_weight": 0.0,
}


# -----------------------------------------------------------------------
# 4. structural_fragility -- Resolving: 0.000 (Inactive), Building: 0.461538 (Adjacent)
# -----------------------------------------------------------------------

STRUCTURAL_FRAG_INDICATORS = {
    # -- Building phase --
    "Implied vol level": {
        "triggered": False, "value": 23.87, "metric_field": "^VIX",
        "weight": 0.10, "direction": "below",
    },
    "High-yield spread": {
        "triggered": False, "value": 317.0, "metric_field": "credit.hy_spread",
        "weight": 0.15, "direction": "below",
    },
    "Implied-realized vol gap": {
        "triggered": False, "value": 4.86, "metric_field": "vix_vs_realized",
        "weight": 0.10, "direction": "above",
    },
    "Top-10 index concentration": {
        # Data unavailable: no data source implemented. Excluded from denominator.
        "triggered": False, "value": None, "metric_field": "top_10_sp500_weight",
        "weight": 0.20, "reason": "data_unavailable",
    },
    "Margin debt": {
        "triggered": True, "value": 1253.192, "metric_field": "finra_margin_debt",
        "weight": 0.10, "direction": "above",
    },
    "Large-cap/small-cap divergence": {
        # B-03: threshold extracts "2" from "2-year high". 2.3279 > 2 triggers.
        "triggered": True, "value": 2.3279, "metric_field": "qqq_iwm_ratio",
        "weight": 0.10, "direction": "above",
    },
    "Passive fund share": {
        "triggered": True, "value": 59.0, "metric_field": "passive_fund_share",
        "weight": 0.10, "direction": "above",
    },
    # -- Resolving phase --
    "Drawdown depth": {
        "triggered": False, "value": -5.7, "metric_field": "spy_drawdown_from_52w_high",
        "weight": 0.20, "direction": "below",
    },
    "Valuation compression": {
        "triggered": False, "value": 37.94, "metric_field": "shiller_cape",
        "weight": 0.15, "direction": "below",
    },
}

STRUCTURAL_FRAG_COVERAGE = {
    "total_in_results": 9, "skipped_web_qualitative": 2,
    "evaluated": 8, "excluded": 1, "triggered": 3,
    "evaluated_weight": 1.0000, "triggered_weight": 0.3000, "excluded_weight": 0.2000,
}


# -----------------------------------------------------------------------
# 5. fiscal_dominance_liquidity -- Score: 0.777778 (Active)
# -----------------------------------------------------------------------

FISCAL_LIQ_INDICATORS = {
    "Net liquidity expanding": {
        # BUG-03: threshold extracts "2" from "2+ of last 3 months".
        # 101440 > 2 triggers. Current frozen behavior.
        "triggered": True, "value": 101440.0, "metric_field": "net_liquidity_30d_change",
        "weight": 0.20, "direction": "above",
    },
    "Deficit pace": {
        # Task 1: threshold aligned to "Above 1500 annualized (in $B)".
        "triggered": True, "value": 3690.0, "metric_field": "deficit_pace_annualized",
        "weight": 0.20, "direction": "above",
    },
    "Rate hikes not producing recession": {
        # Threshold extracts "5" from "5%". Uses ISM proxy (52.7 via override).
        "triggered": True, "value": 52.7, "metric_field": "growth.ism_proxy",
        "weight": 0.15, "direction": "above",
    },
    "Hard assets outperforming nominal bonds": {
        "triggered": True, "value": 73.09, "metric_field": "hard_vs_nominal_12m",
        "weight": 0.15, "direction": "above",
    },
    "RRP draining toward zero": {
        "triggered": False, "value": 327.0, "metric_field": "liquidity.reverse_repo",
        "weight": 0.10, "direction": "below",
    },
    "Fed balance sheet direction inconsistent with stated policy": {
        # Threshold not evaluable: compound prose threshold.
        "triggered": False, "value": 6675344.0, "metric_field": "liquidity.fed_balance_sheet",
        "weight": 0.10, "reason": "threshold_not_evaluable",
    },
    "TGA behavior consistent with spending": {
        # Latent unit mismatch: TGA in $M (847718), threshold says "$500B" extracts 500.
        # 847718 < 500 = False. Correct result by coincidence.
        "triggered": False, "value": 847718.0, "metric_field": "liquidity.tga",
        "weight": 0.10, "direction": "below",
    },
}

FISCAL_LIQ_COVERAGE = {
    "total_in_results": 7, "skipped_web_qualitative": 1,
    "evaluated": 6, "excluded": 1, "triggered": 4,
    "evaluated_weight": 0.9000, "triggered_weight": 0.7000, "excluded_weight": 0.1000,
}


# -----------------------------------------------------------------------
# 6. fiscal_dominance_arithmetic -- Score: 1.000 (Active)
#    CEILING HIT: 1 indicator excluded, all 5 remaining trigger.
#    Score = 0.75 / 0.75 = 1.000 (shrunken denominator).
# -----------------------------------------------------------------------

FISCAL_ARITH_INDICATORS = {
    "Interest expense / tax receipts ratio": {
        "triggered": True, "value": 34.0, "metric_field": "interest_receipts_ratio",
        "weight": 0.25, "direction": "above",
    },
    "Interest expense exceeds major discretionary category": {
        "triggered": True, "value": 287.0, "metric_field": "interest_exceeds_defense",
        "weight": 0.15, "direction": "above",
    },
    "Deficit pace outside recession": {
        # Task 1: threshold "Deficit above 1500 annualized (in $B)".
        "triggered": True, "value": 3690.0, "metric_field": "deficit_pace_annualized",
        "weight": 0.20, "direction": "above",
    },
    "Debt rollover at higher rates": {
        # Threshold not evaluable: "Weighted average rate rising AND below current..."
        "triggered": False, "value": 3.355, "metric_field": "weighted_avg_interest_rate",
        "weight": 0.15, "reason": "threshold_not_evaluable",
    },
    "Gold/oil ratio elevated": {
        # Task 1: commodity-based ratio (42.3), not ETF proxy.
        "triggered": True, "value": 42.3, "metric_field": "gold_oil_ratio",
        "weight": 0.10, "direction": "above",
    },
    "Central bank gold purchases sustained": {
        "triggered": True, "value": 1037.0, "metric_field": "cb_gold_purchases",
        "weight": 0.05, "direction": "above",
    },
}

FISCAL_ARITH_COVERAGE = {
    "total_in_results": 6, "skipped_web_qualitative": 1,
    "evaluated": 5, "excluded": 1, "triggered": 5,
    "evaluated_weight": 0.7500, "triggered_weight": 0.7500, "excluded_weight": 0.1500,
}


# -----------------------------------------------------------------------
# 7. capital_flows -- Rotation: 0.450 (Adjacent), Accumulation: 0.470 (Adjacent)
# -----------------------------------------------------------------------

CAPITAL_FLOWS_INDICATORS = {
    # -- Rotation phase (Phase B, checked first) --
    "Dollar weakening": {
        # BUG-03: threshold extracts "3" from "3+ months"; 100.08 < 3 = False.
        "triggered": False, "value": 100.08, "metric_field": "dxy_index",
        "weight": 0.25, "direction": "below",
    },
    "China credit impulse positive and accelerating": {
        "triggered": True, "value": 3.5, "metric_field": "china_credit_impulse",
        "weight": 0.20, "direction": "above",
    },
    "RMB strengthening": {
        # BUG-03: threshold extracts "3" from "3+ months"; 6.89 < 3 = False.
        "triggered": False, "value": 6.8922, "metric_field": "usdcny",
        "weight": 0.20, "direction": "falling",
    },
    "EM outperforming DM on relative basis": {
        "triggered": True, "value": 7.27, "metric_field": "eem_spy_3m_relative",
        "weight": 0.15, "direction": "above",
    },
    "Commodity prices rising": {
        # BUG-03: threshold extracts "3" from "3+ months"; 31.17 > 3 triggers.
        "triggered": True, "value": 31.17, "metric_field": "commodity_index_3m_change",
        "weight": 0.10, "direction": "above",
    },
    "Chinese equities leading": {
        "triggered": False, "value": -7.13, "metric_field": "fxi_3m_return",
        "weight": 0.10, "direction": "above",
    },
    # -- Accumulation phase (Phase A) --
    "EM vs. DM PE gap at extremes": {
        "triggered": False, "value": 11.284, "metric_field": "em_dm_pe_gap",
        "weight": 0.33, "direction": "above",
    },
    "EM rolling 3-year underperformance": {
        # A-04: 12-month proxy for 3-year. Threshold "30%+" extracts 30.
        # 9.5 < 30 = True (direction=below). Known proxy limitation.
        "triggered": True, "value": 9.5, "metric_field": "eem_spy_3y_relative",
        "weight": 0.27, "direction": "below",
    },
    "Dollar strong or sideways": {
        # Task 1: dxy_index now resolves. 100.08 > 100 triggers.
        "triggered": True, "value": 100.08, "metric_field": "dxy_index",
        "weight": 0.20, "direction": "above",
    },
    "China credit impulse flat or negative": {
        "triggered": False, "value": 3.5, "metric_field": "china_credit_impulse",
        "weight": 0.20, "direction": "below",
    },
}

CAPITAL_FLOWS_COVERAGE = {
    "total_in_results": 10, "skipped_web_qualitative": 0,
    "evaluated": 10, "excluded": 0, "triggered": 5,
    "evaluated_weight": 2.0000, "triggered_weight": 0.9200, "excluded_weight": 0.0,
}


# -----------------------------------------------------------------------
# 8. monetary_architecture -- Score: 0.661972 (Active)
# -----------------------------------------------------------------------

MONETARY_ARCH_INDICATORS = {
    "Central bank gold purchases sustained at elevated levels": {
        "triggered": True, "value": 1037.0, "metric_field": "cb_gold_purchases",
        "weight": 0.29, "direction": "above",
    },
    "Foreign official Treasury holdings declining as share of outstanding": {
        # BUG-03: threshold extracts "3" from "3+ years"; 24.0 < 3 = False.
        "triggered": False, "value": 24.0, "metric_field": "foreign_treasury_holdings_pct",
        "weight": 0.24, "direction": "below",
    },
    "Gold/oil ratio elevated and rising": {
        # Task 1: commodity ratio (42.3) resolves. 42.3 > 25 triggers.
        "triggered": True, "value": 42.3, "metric_field": "gold_oil_ratio",
        "weight": 0.18, "direction": "above",
    },
}

MONETARY_ARCH_COVERAGE = {
    "total_in_results": 3, "skipped_web_qualitative": 2,
    "evaluated": 3, "excluded": 0, "triggered": 2,
    "evaluated_weight": 0.7100, "triggered_weight": 0.4700, "excluded_weight": 0.0,
}


# =======================================================================
# TEST CLASSES
# =======================================================================


class TestValuationMeanReversion:
    """valuation_mean_reversion: single-phase, Active, 0.705882"""

    def test_score_and_tier(self, all_results):
        r = all_results["valuation_mean_reversion"]
        assert r.is_two_phase is False
        assert r.score == pytest.approx(0.705882, abs=1e-4)
        assert r.tier.value == "Active"

    def test_indicator_count(self, all_results):
        r = all_results["valuation_mean_reversion"]
        assert len(r.indicator_results) == 6
        assert set(r.indicator_results.keys()) == set(VALUATION_MR_INDICATORS.keys())

    def test_each_indicator(self, all_results):
        r = all_results["valuation_mean_reversion"]
        for name, expected in VALUATION_MR_INDICATORS.items():
            _assert_indicator(r.indicator_results[name], expected, name, "valuation_mean_reversion")

    def test_coverage(self, all_results):
        r = all_results["valuation_mean_reversion"]
        actual = _compute_coverage(r)
        for key, expected_val in VALUATION_MR_COVERAGE.items():
            assert actual[key] == pytest.approx(expected_val, abs=1e-4), (
                f"valuation_mean_reversion coverage.{key}: "
                f"actual={actual[key]}, expected={expected_val}"
            )

    def test_skipped_buffett(self, all_results):
        """Buffett Indicator skipped because WILL5000INDFC unavailable."""
        r = all_results["valuation_mean_reversion"]
        assert len(r.skipped_indicators) == 1
        assert "Buffett Indicator" in r.skipped_indicators[0]


class TestDebtCycleShort:
    """debt_cycle_short: two-phase, Contraction 0.300 / Expansion 1.000
    CEILING HIT on Expansion: shrunken denominator, all remaining trigger."""

    def test_phase_scores_and_tiers(self, all_results):
        r = all_results["debt_cycle_short"]
        assert r.is_two_phase is True
        assert r.phase_scores["Contraction"] == pytest.approx(0.300, abs=1e-4)
        assert r.phase_scores["Expansion"] == pytest.approx(1.000, abs=1e-4)
        assert r.phase_tiers["Contraction"].value == "Adjacent"
        assert r.phase_tiers["Expansion"].value == "Active"

    def test_effective_phase(self, all_results):
        r = all_results["debt_cycle_short"]
        assert r.effective_tier.value == "Adjacent"
        assert r.effective_phase == "Contraction"

    def test_indicator_count(self, all_results):
        r = all_results["debt_cycle_short"]
        assert len(r.indicator_results) == 15
        assert set(r.indicator_results.keys()) == set(DEBT_SHORT_INDICATORS.keys())

    def test_each_indicator(self, all_results):
        r = all_results["debt_cycle_short"]
        for name, expected in DEBT_SHORT_INDICATORS.items():
            _assert_indicator(r.indicator_results[name], expected, name, "debt_cycle_short")

    def test_coverage(self, all_results):
        r = all_results["debt_cycle_short"]
        actual = _compute_coverage(r)
        for key, expected_val in DEBT_SHORT_COVERAGE.items():
            assert actual[key] == pytest.approx(expected_val, abs=1e-4), (
                f"debt_cycle_short coverage.{key}: "
                f"actual={actual[key]}, expected={expected_val}"
            )

    def test_expansion_ceiling_hit_visibility(self, all_results):
        """Expansion scores 1.000 via shrunken denominator.
        Make visible: 6 evaluated indicators all trigger, 2 excluded."""
        r = all_results["debt_cycle_short"]

        # Identify excluded Expansion indicators
        excluded = {
            name: info for name, info in r.indicator_results.items()
            if info.get("reason") in ("data_unavailable", "threshold_not_evaluable")
        }
        assert len(excluded) == 2, (
            f"Expected 2 excluded indicators in Expansion, got {len(excluded)}: "
            f"{list(excluded.keys())}"
        )
        assert "Fed funds below nominal GDP growth" in excluded
        assert "Net credit growth positive" in excluded

        # Denominator shrinkage: 0.25 of total possible weight excluded
        excluded_weight = sum(info["weight"] for info in excluded.values())
        assert excluded_weight == pytest.approx(0.25, abs=1e-4)

    def test_k_suffix_initial_claims(self, all_results):
        """Task 3 regression: K-suffix scaling must hold for initial_claims."""
        r = all_results["debt_cycle_short"]
        # Expansion: claims low (202K < 250K -> triggered)
        assert r.indicator_results["Initial claims low"]["triggered"] is True
        # Contraction: claims rising (202K < 280K -> NOT triggered)
        assert r.indicator_results["Initial claims rising"]["triggered"] is False


class TestDebtCycleLong:
    """debt_cycle_long: single-phase, Active, 0.900"""

    def test_score_and_tier(self, all_results):
        r = all_results["debt_cycle_long"]
        assert r.is_two_phase is False
        assert r.score == pytest.approx(0.900, abs=1e-4)
        assert r.tier.value == "Active"

    def test_indicator_count(self, all_results):
        r = all_results["debt_cycle_long"]
        assert len(r.indicator_results) == 6
        assert set(r.indicator_results.keys()) == set(DEBT_LONG_INDICATORS.keys())

    def test_each_indicator(self, all_results):
        r = all_results["debt_cycle_long"]
        for name, expected in DEBT_LONG_INDICATORS.items():
            _assert_indicator(r.indicator_results[name], expected, name, "debt_cycle_long")

    def test_coverage(self, all_results):
        r = all_results["debt_cycle_long"]
        actual = _compute_coverage(r)
        for key, expected_val in DEBT_LONG_COVERAGE.items():
            assert actual[key] == pytest.approx(expected_val, abs=1e-4), (
                f"debt_cycle_long coverage.{key}: "
                f"actual={actual[key]}, expected={expected_val}"
            )

    def test_no_exclusions(self, all_results):
        """debt_cycle_long has zero excluded indicators."""
        r = all_results["debt_cycle_long"]
        assert len(r.skipped_indicators) == 0
        for name, info in r.indicator_results.items():
            assert "reason" not in info, (
                f"Unexpected exclusion: {name} ({info.get('reason')})"
            )


class TestStructuralFragility:
    """structural_fragility: two-phase, Resolving 0.000 / Building 0.461538"""

    def test_phase_scores_and_tiers(self, all_results):
        r = all_results["structural_fragility"]
        assert r.is_two_phase is True
        assert r.phase_scores["Fragility Resolving"] == pytest.approx(0.000, abs=1e-4)
        assert r.phase_scores["Fragility Building"] == pytest.approx(0.461538, abs=1e-4)
        assert r.phase_tiers["Fragility Resolving"].value == "Inactive"
        assert r.phase_tiers["Fragility Building"].value == "Adjacent"

    def test_effective_phase(self, all_results):
        r = all_results["structural_fragility"]
        assert r.effective_tier.value == "Adjacent"
        assert r.effective_phase == "Fragility Building"

    def test_indicator_count(self, all_results):
        r = all_results["structural_fragility"]
        assert len(r.indicator_results) == 9
        assert set(r.indicator_results.keys()) == set(STRUCTURAL_FRAG_INDICATORS.keys())

    def test_each_indicator(self, all_results):
        r = all_results["structural_fragility"]
        for name, expected in STRUCTURAL_FRAG_INDICATORS.items():
            _assert_indicator(r.indicator_results[name], expected, name, "structural_fragility")

    def test_coverage(self, all_results):
        r = all_results["structural_fragility"]
        actual = _compute_coverage(r)
        for key, expected_val in STRUCTURAL_FRAG_COVERAGE.items():
            assert actual[key] == pytest.approx(expected_val, abs=1e-4), (
                f"structural_fragility coverage.{key}: "
                f"actual={actual[key]}, expected={expected_val}"
            )

    def test_top10_excluded(self, all_results):
        """Top-10 concentration excluded because no data source exists."""
        r = all_results["structural_fragility"]
        info = r.indicator_results["Top-10 index concentration"]
        assert info["reason"] == "data_unavailable"
        assert info["value"] is None


class TestFiscalDominanceLiquidity:
    """fiscal_dominance_liquidity: single-phase, Active, 0.777778"""

    def test_score_and_tier(self, all_results):
        r = all_results["fiscal_dominance_liquidity"]
        assert r.is_two_phase is False
        assert r.score == pytest.approx(0.777778, abs=1e-4)
        assert r.tier.value == "Active"

    def test_indicator_count(self, all_results):
        r = all_results["fiscal_dominance_liquidity"]
        assert len(r.indicator_results) == 7
        assert set(r.indicator_results.keys()) == set(FISCAL_LIQ_INDICATORS.keys())

    def test_each_indicator(self, all_results):
        r = all_results["fiscal_dominance_liquidity"]
        for name, expected in FISCAL_LIQ_INDICATORS.items():
            _assert_indicator(r.indicator_results[name], expected, name, "fiscal_dominance_liquidity")

    def test_coverage(self, all_results):
        r = all_results["fiscal_dominance_liquidity"]
        actual = _compute_coverage(r)
        for key, expected_val in FISCAL_LIQ_COVERAGE.items():
            assert actual[key] == pytest.approx(expected_val, abs=1e-4), (
                f"fiscal_dominance_liquidity coverage.{key}: "
                f"actual={actual[key]}, expected={expected_val}"
            )

    def test_tga_latent_mismatch_frozen(self, all_results):
        """TGA comparison is correct by coincidence (field $M, threshold $B).
        Freeze the current state: 847718 < 500 = False."""
        r = all_results["fiscal_dominance_liquidity"]
        tga = r.indicator_results["TGA behavior consistent with spending"]
        assert tga["triggered"] is False
        assert tga["value"] == pytest.approx(847718.0, abs=1)


class TestFiscalDominanceArithmetic:
    """fiscal_dominance_arithmetic: single-phase, Active, 1.000
    CEILING HIT: 1 indicator excluded, all 5 remaining trigger."""

    def test_score_and_tier(self, all_results):
        r = all_results["fiscal_dominance_arithmetic"]
        assert r.is_two_phase is False
        assert r.score == pytest.approx(1.000, abs=1e-4)
        assert r.tier.value == "Active"

    def test_indicator_count(self, all_results):
        r = all_results["fiscal_dominance_arithmetic"]
        assert len(r.indicator_results) == 6
        assert set(r.indicator_results.keys()) == set(FISCAL_ARITH_INDICATORS.keys())

    def test_each_indicator(self, all_results):
        r = all_results["fiscal_dominance_arithmetic"]
        for name, expected in FISCAL_ARITH_INDICATORS.items():
            _assert_indicator(r.indicator_results[name], expected, name, "fiscal_dominance_arithmetic")

    def test_coverage(self, all_results):
        r = all_results["fiscal_dominance_arithmetic"]
        actual = _compute_coverage(r)
        for key, expected_val in FISCAL_ARITH_COVERAGE.items():
            assert actual[key] == pytest.approx(expected_val, abs=1e-4), (
                f"fiscal_dominance_arithmetic coverage.{key}: "
                f"actual={actual[key]}, expected={expected_val}"
            )

    def test_ceiling_hit_visibility(self, all_results):
        """Score is 1.000 because denominator shrank, not because all indicators fire.

        5 evaluated, all triggered (w=0.75).
        1 excluded: Debt rollover (w=0.15, threshold_not_evaluable).
        Total possible weight if nothing excluded: 0.90.
        Denominator: 0.75 (0.90 - 0.15 excluded).
        Score: 0.75 / 0.75 = 1.000.
        """
        r = all_results["fiscal_dominance_arithmetic"]
        cov = _compute_coverage(r)

        # All evaluated indicators trigger
        assert cov["evaluated"] == 5
        assert cov["triggered"] == 5
        assert cov["triggered_weight"] == cov["evaluated_weight"]

        # Shrunken denominator is visible
        assert cov["excluded"] == 1
        assert cov["excluded_weight"] == pytest.approx(0.15, abs=1e-4)

        # The excluded indicator is specifically "Debt rollover"
        excluded = {
            name: info for name, info in r.indicator_results.items()
            if info.get("reason") in ("data_unavailable", "threshold_not_evaluable")
        }
        assert "Debt rollover at higher rates" in excluded


class TestCapitalFlows:
    """capital_flows: two-phase, Rotation 0.450 / Accumulation 0.470"""

    def test_phase_scores_and_tiers(self, all_results):
        r = all_results["capital_flows"]
        assert r.is_two_phase is True
        assert r.phase_scores["Rotation"] == pytest.approx(0.450, abs=1e-4)
        assert r.phase_scores["Accumulation"] == pytest.approx(0.470, abs=1e-4)
        assert r.phase_tiers["Rotation"].value == "Adjacent"
        assert r.phase_tiers["Accumulation"].value == "Adjacent"

    def test_effective_phase(self, all_results):
        r = all_results["capital_flows"]
        assert r.effective_tier.value == "Adjacent"
        assert r.effective_phase == "Rotation"

    def test_indicator_count(self, all_results):
        r = all_results["capital_flows"]
        assert len(r.indicator_results) == 10
        assert set(r.indicator_results.keys()) == set(CAPITAL_FLOWS_INDICATORS.keys())

    def test_each_indicator(self, all_results):
        r = all_results["capital_flows"]
        for name, expected in CAPITAL_FLOWS_INDICATORS.items():
            _assert_indicator(r.indicator_results[name], expected, name, "capital_flows")

    def test_coverage(self, all_results):
        r = all_results["capital_flows"]
        actual = _compute_coverage(r)
        for key, expected_val in CAPITAL_FLOWS_COVERAGE.items():
            assert actual[key] == pytest.approx(expected_val, abs=1e-4), (
                f"capital_flows coverage.{key}: "
                f"actual={actual[key]}, expected={expected_val}"
            )

    def test_dxy_resolution(self, all_results):
        """Task 1 regression: DXY must resolve via dxy_index computed field."""
        r = all_results["capital_flows"]
        assert r.indicator_results["Dollar strong or sideways"]["metric_field"] == "dxy_index"
        assert r.indicator_results["Dollar weakening"]["metric_field"] == "dxy_index"


class TestMonetaryArchitecture:
    """monetary_architecture: single-phase, Active, 0.661972"""

    def test_score_and_tier(self, all_results):
        r = all_results["monetary_architecture"]
        assert r.is_two_phase is False
        assert r.score == pytest.approx(0.661972, abs=1e-4)
        assert r.tier.value == "Active"

    def test_indicator_count(self, all_results):
        r = all_results["monetary_architecture"]
        assert len(r.indicator_results) == 3
        assert set(r.indicator_results.keys()) == set(MONETARY_ARCH_INDICATORS.keys())

    def test_each_indicator(self, all_results):
        r = all_results["monetary_architecture"]
        for name, expected in MONETARY_ARCH_INDICATORS.items():
            _assert_indicator(r.indicator_results[name], expected, name, "monetary_architecture")

    def test_coverage(self, all_results):
        r = all_results["monetary_architecture"]
        actual = _compute_coverage(r)
        for key, expected_val in MONETARY_ARCH_COVERAGE.items():
            assert actual[key] == pytest.approx(expected_val, abs=1e-4), (
                f"monetary_architecture coverage.{key}: "
                f"actual={actual[key]}, expected={expected_val}"
            )

    def test_web_search_skips(self, all_results):
        """Two web-search indicators skipped: no field mapping."""
        r = all_results["monetary_architecture"]
        assert len(r.skipped_indicators) == 2
        skip_text = " ".join(r.skipped_indicators)
        assert "Cross-currency" in skip_text
        assert "Non-dollar" in skip_text

    def test_gold_oil_commodity_fix(self, all_results):
        """Task 1 regression: gold_oil_ratio must use commodity data (42.3), not ETF."""
        r = all_results["monetary_architecture"]
        gold_oil = r.indicator_results["Gold/oil ratio elevated and rising"]
        assert gold_oil["value"] == pytest.approx(42.3, abs=0.1)
        assert gold_oil["triggered"] is True


# =======================================================================
# META-TESTS: Completeness and structural integrity
# =======================================================================


class TestHarnessCompleteness:
    """Verify the harness covers all 8 theories and catches drift."""

    EXPECTED_THEORY_IDS = {
        "valuation_mean_reversion",
        "debt_cycle_short",
        "debt_cycle_long",
        "structural_fragility",
        "fiscal_dominance_liquidity",
        "fiscal_dominance_arithmetic",
        "capital_flows",
        "monetary_architecture",
    }

    def test_all_8_theories_scored(self, all_results):
        """Every theory in the registry was scored."""
        assert set(all_results.keys()) == self.EXPECTED_THEORY_IDS

    def test_all_8_theories_have_test_classes(self):
        """Every theory has a corresponding test class in this file.
        If a new theory is added to the registry but not to the harness,
        this test fails."""
        import inspect
        import sys
        module = sys.modules[__name__]
        test_classes = {
            name for name, obj in inspect.getmembers(module)
            if inspect.isclass(obj) and name.startswith("Test")
            and name not in ("TestHarnessCompleteness", "TestThresholdParsing")
        }
        # 8 theory test classes expected
        assert len(test_classes) == 8, (
            f"Expected 8 theory test classes, found {len(test_classes)}: {test_classes}"
        )

    def test_no_unexpected_theories(self, all_results):
        """No extra theories appeared that are not covered by the harness."""
        unexpected = set(all_results.keys()) - self.EXPECTED_THEORY_IDS
        assert not unexpected, f"Unexpected theories not in harness: {unexpected}"


class TestThresholdParsing:
    """Freeze threshold parsing for critical indicators.

    These tests verify that _extract_number produces the expected numeric
    threshold for key indicators. If threshold text or parsing logic changes,
    these fail.
    """

    @pytest.mark.parametrize("threshold_text,expected_number", [
        # K-suffix (Task 3)
        ("Below 250K (4-week average)", 250000.0),
        ("above 280K AND rising for 8+ weeks", 280000.0),
        # bp suffix
        ("Below 450bp", 450.0),
        ("Above 500bp AND widening for 2+ months", 500.0),
        ("Below 300bp", 300.0),
        # % suffix
        ("Below 1.0%", 1.0),
        ("Above 20%", 20.0),
        ("Below -20%", -20.0),
        # $ suffix
        ("Above 1500 annualized (in $B)", 1500.0),
        ("TGA below $500B OR declining by $100B+ over 60 days", 500.0),
        # Plain numbers
        ("Above 30", 30.0),
        ("Above 50", 50.0),
        ("Below 5.0% OR declining for 3+ months", 5.0),
        ("Above 0 (positive = cash yield exceeds equity earnings yield)", 0.0),
        # BUG-03 temporal extractions (frozen as current behavior, v9 will fix)
        ("3-month moving average rising 0.50%+ above its 12-month low", 3.0),
        ("DXY declining for 3+ months AND below its 12-month moving average", 3.0),
        ("USD/CNY declining (fewer yuan per dollar) for 3+ months", 3.0),
        ("Positive for 2+ of last 3 months", 2.0),
    ], ids=lambda x: str(x)[:50])
    def test_threshold_extraction(self, threshold_text, expected_number):
        actual = _extract_number(threshold_text)
        assert actual == pytest.approx(expected_number, abs=1e-4), (
            f"_extract_number({threshold_text!r}) = {actual}, expected {expected_number}"
        )

    @pytest.mark.parametrize("threshold_text", [
        "Fed funds rate below nominal GDP growth rate",
        "Banks reporting steady or loosening lending standards AND loan growth positive YoY",
        "Weighted average rate rising AND below current market rates (rollover still has room to push expense higher)",
        "Fed BS declining slower than announced QT pace, OR flat, OR expanding despite no announced policy change",
    ], ids=lambda x: x[:50])
    def test_threshold_not_evaluable(self, threshold_text):
        """These thresholds must return None (not evaluable)."""
        actual = _extract_number(threshold_text)
        assert actual is None, (
            f"_extract_number({threshold_text!r}) = {actual}, expected None"
        )
