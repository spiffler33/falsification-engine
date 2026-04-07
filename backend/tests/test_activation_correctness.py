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
# 1. valuation_mean_reversion -- Score: 0.833333 (Active)
#    v9 Phase 3: COMPILED PATH. OR condition for profit_margins now evaluable.
#    3 indicators excluded (time-series / missing data), denominator shrinks.
#    Score: 0.50 / 0.60 = 0.833333.
# -----------------------------------------------------------------------

VALUATION_MR_INDICATORS = {
    "Equity risk premium compressed": {
        "triggered": True, "value": 0.19, "metric_field": "equity_risk_premium",
        "weight": 0.25, "direction": "below",
        # weight_correction: ACTIVATION.md is source of truth (0.25),
        # compile_all.py had transcription error (0.20). See V9_PHASE3_5
    },
    "Shiller CAPE elevated": {
        "triggered": True, "value": 37.94, "metric_field": "shiller_cape",
        "weight": 0.20, "direction": "above",
    },
    "Buffett Indicator extreme": {
        # Was skipped by legacy; compiled includes in results as excluded
        "triggered": False, "value": None, "metric_field": "buffett_indicator",
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Short-term cash yield exceeds equity earnings yield": {
        "triggered": False, "value": -0.86, "metric_field": "cash_exceeds_equity_yield",
        "weight": 0.15, "direction": "above",
        # weight_correction: ACTIVATION.md is source of truth (0.15),
        # compile_all.py had transcription error (0.10). See V9_PHASE3_5
        # display_name: Haiku uses full ACTIVATION.md name
    },
    "Corporate profit margins at cycle highs": {
        # justified_improvement: OR condition (margin > 12% OR profits/GDP > 10%)
        # now evaluable via compiled path, see V9_PHASE2_SEMANTIC_DIFF.md
        # display_name: Haiku uses full ACTIVATION.md name
        "triggered": True, "value": None, "metric_field": "sp500_net_margin",
        "weight": 0.10, "direction": "above",
    },
    "Market breadth narrow": {
        # Excluded: historical_extreme requires series store
        "triggered": False, "value": None, "metric_field": "qqq_iwm_ratio",
        "weight": 0.10, "reason": "data_unavailable",
    },
    "Insider selling elevated": {
        # Excluded: persistence requires series store
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.05, "reason": "data_unavailable",
        # weight_correction: ACTIVATION.md is source of truth (0.05),
        # compile_all.py had transcription error (0.15). See V9_PHASE3_5
    },
}

VALUATION_MR_COVERAGE = {
    # 7 indicators in results, 3 skipped (Buffett + breadth + insider)
    # 4 evaluated, 3 excluded, 3 triggered
    # weight_correction: evaluated/triggered/excluded weights updated for
    # ACTIVATION.md weights. See V9_PHASE3_6
    "total_in_results": 7, "skipped_web_qualitative": 3,
    "evaluated": 4, "excluded": 3, "triggered": 3,
    "evaluated_weight": 0.7000, "triggered_weight": 0.5500, "excluded_weight": 0.3000,
}


# -----------------------------------------------------------------------
# 2. debt_cycle_short -- Contraction: 0.000 (Inactive), Expansion: 0.833333 (Active)
#    v9 Phase 4: COMPILED PATH.
#    Contraction: all indicators temporal except SLOOS (not triggered). Score 0.000.
#    Legacy Contraction was 0.300 from BUG-03 (Sahm) + field wiring (Fed funds).
#    Expansion: 5 evaluable, 4 triggered, 3 excluded (temporal).
#    Fed funds below GDP now evaluable as field_comparison (justified_improvement).
#    Effective: Active (Expansion) -- was Adjacent (Contraction) in legacy.
# -----------------------------------------------------------------------

DEBT_SHORT_INDICATORS = {
    # -- Contraction phase (6 of 7 temporal, only SLOOS evaluable) --
    "ISM proxy below contraction": {
        # temporal_exclusion: compound ALL has trend_state sub-clause.
        "triggered": False, "value": None, "metric_field": "growth.ism_proxy",
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Unemployment rising (Sahm Rule)": {
        # temporal_exclusion: named_pattern requires SeriesStore.
        # Legacy BUG-03 fixed: no longer extracts "3" from "3-month".
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.20, "reason": "data_unavailable",
    },
    "Credit spreads widening sharply": {
        # temporal_exclusion: compound ANY, nested ALL has trend, scalar False.
        "triggered": False, "value": None, "metric_field": "credit.hy_spread",
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Yield curve re-steepening from deep inversion": {
        # temporal_exclusion: named_pattern requires SeriesStore.
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Initial claims rising": {
        # temporal_exclusion: compound ALL has trend_state sub-clause.
        "triggered": False, "value": None, "metric_field": "growth.initial_claims",
        "weight": 0.10, "reason": "data_unavailable",
    },
    "Fed funds above nominal GDP growth": {
        # temporal_exclusion: persistence wrapping field_comparison.
        # Legacy wiring bug fixed: no longer compares GDP level ($B) trivially.
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.10, "reason": "data_unavailable",
    },
    "SLOOS showing broad tightening": {
        # Only evaluable Contraction indicator. sloos_net_tightening = 0.0 > 0 = False.
        "triggered": False, "value": 0.0, "metric_field": "sloos_net_tightening",
        "weight": 0.15, "direction": "above",
    },
    # -- Expansion phase (5 evaluable, 3 temporal) --
    "ISM proxy above contraction": {
        "triggered": True, "value": 52.7, "metric_field": "growth.ism_proxy",
        "weight": 0.15, "direction": "above",
    },
    "Unemployment low or falling": {
        # justified_improvement: compound OR, first scalar clause (unemployment < 5%)
        # evaluates to True. Value is None because compound doesn't propagate sub-values.
        "triggered": True, "value": None, "metric_field": "growth.unemployment",
        "weight": 0.15, "direction": "below",
    },
    "Credit spreads tight or tightening": {
        # temporal_exclusion: compound ALL has trend_state sub-clause.
        "triggered": False, "value": None, "metric_field": "credit.hy_spread",
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Yield curve not deeply inverted": {
        "triggered": True, "value": 0.52, "metric_field": "rates.curve_2s10s",
        "weight": 0.10, "direction": "above",
    },
    "Initial claims low": {
        # K-suffix scaling preserved: 202000 < 250000 = True.
        "triggered": True, "value": 202000.0, "metric_field": "growth.initial_claims",
        "weight": 0.10, "direction": "below",
    },
    "Fed funds below nominal GDP growth": {
        # justified_improvement: field_comparison now evaluable via derived function.
        # fed_funds (3.64) < nominal_gdp_growth (3.31) = False.
        # Legacy couldn't evaluate this (threshold_not_evaluable).
        "triggered": False, "value": 3.64, "metric_field": "rates.fed_funds",
        "weight": 0.10, "direction": "below",
    },
    "Net credit growth positive": {
        # temporal_exclusion: compound ALL has delta_change sub-clause.
        "triggered": False, "value": None, "metric_field": "credit.sloos_tightening_ci",
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Consumer/business confidence": {
        # temporal_exclusion: compound ALL has trend_state sub-clause.
        "triggered": False, "value": None, "metric_field": "sentiment.consumer_sentiment",
        "weight": 0.10, "reason": "data_unavailable",
    },
}

DEBT_SHORT_COVERAGE = {
    # v9 Phase 4: 6 evaluated (5 Expansion + 1 Contraction SLOOS), 9 excluded (temporal)
    "total_in_results": 15, "skipped_web_qualitative": 9,
    "evaluated": 6, "excluded": 9, "triggered": 4,
    "evaluated_weight": 0.7500, "triggered_weight": 0.5000, "excluded_weight": 1.2500,
}


# -----------------------------------------------------------------------
# 3. debt_cycle_long -- Score: 0.647059 (Active)
#    v9 Phase 3: COMPILED PATH. Key fixes:
#    - wealth_inequality: correct 70% threshold (False, not True)
#      justified_improvement, see V9_PHASE2_SEMANTIC_DIFF.md
#    - fiscal_deficit_primary_driver: uses correct field deficit_pct_gdp
#      coincidental_parity: was True for wrong field, still True for right field
#    - rates_near_elb: excluded (historical_extreme needs series store)
#    Score: 0.55 / 0.85 = 0.647059
# -----------------------------------------------------------------------

DEBT_LONG_INDICATORS = {
    "Total debt / GDP above historical warning level": {
        "triggered": True, "value": 256.7205, "metric_field": "total_debt_to_gdp",
        "weight": 0.25, "direction": "above",
        # weight_correction: ACTIVATION.md is source of truth (0.25),
        # compile_all.py had transcription error (0.20). See V9_PHASE3_5
        # display_name: Haiku uses full ACTIVATION.md name
    },
    "Fed balance sheet / GDP elevated": {
        "triggered": True, "value": 21.2, "metric_field": "fed_bs_gdp_ratio",
        "weight": 0.25, "direction": "above",
        # weight_correction: ACTIVATION.md is source of truth (0.25),
        # compile_all.py had transcription error (0.15). See V9_PHASE3_5
        # display_name: Haiku uses full ACTIVATION.md name
    },
    "Rates at or near effective lower bound within recent memory": {
        # Excluded: historical_extreme requires series store
        "triggered": False, "value": None, "metric_field": "rates.fed_funds",
        "weight": 0.15, "reason": "data_unavailable",
        # display_name: Haiku uses full ACTIVATION.md name
    },
    "Fiscal deficit as primary growth driver": {
        # coincidental_parity: compiled uses correct field deficit_pct_gdp (11.74 > 5.0).
        # Haiku simplified compound (removed UNRESOLVED private_credit_growth clause).
        "triggered": True, "value": 11.7358, "metric_field": "deficit_pct_gdp",
        "weight": 0.15, "direction": "above",
        # weight_correction: ACTIVATION.md is source of truth (0.15),
        # compile_all.py had transcription error (0.20). See V9_PHASE3_5
    },
    "Wealth inequality at cycle-characteristic extremes": {
        # justified_improvement: compiled uses correct 70% threshold.
        # 68.1 < 70 = False (correct). Haiku simplified compound
        # (removed UNRESOLVED top_1_income_share clause).
        "triggered": False, "value": 68.1, "metric_field": "top10_wealth_share",
        "weight": 0.10, "direction": "above",
        # weight_correction: ACTIVATION.md is source of truth (0.10),
        # compile_all.py had transcription error (0.15). See V9_PHASE3_5
        # display_name: Haiku uses full ACTIVATION.md name
    },
    "Negative real rates during expansion": {
        "triggered": False, "value": 0.98, "metric_field": "real_fed_funds_rate",
        "weight": 0.10, "direction": "below",
        # weight_correction: ACTIVATION.md is source of truth (0.10),
        # compile_all.py had transcription error (0.15). See V9_PHASE3_5
    },
}

DEBT_LONG_COVERAGE = {
    # 6 indicators in results, 1 excluded (rates_near_elb), 5 evaluated, 3 triggered
    # weight_correction: triggered_weight updated for ACTIVATION.md weights. See V9_PHASE3_6
    "total_in_results": 6, "skipped_web_qualitative": 1,
    "evaluated": 5, "excluded": 1, "triggered": 3,
    "evaluated_weight": 0.8500, "triggered_weight": 0.6500, "excluded_weight": 0.1500,
}


# -----------------------------------------------------------------------
# 4. structural_fragility -- Resolving: 0.000 (Inactive), Building: 0.222222 (Inactive)
#    v9 Phase 4B: COMPILED PATH. Building: 4 evaluable + 4 excluded (2 temporal,
#    1 UNRESOLVED capex, 1 data_unavailable top_10). Only passive_fund triggers.
#    Resolving: 4 evaluable, none trigger. Effective: Inactive.
#    NOTE: display_name collisions ("Implied vol level", "High-yield spread")
#    between phases — Resolving entry overwrites Building in merged dict.
#    This doesn't affect per-phase scoring.
# -----------------------------------------------------------------------

STRUCTURAL_FRAG_INDICATORS = {
    # -- Merged indicators (Resolving overwrites Building for shared names) --
    "Implied vol level": {
        # display_name collision: Building (^VIX < 14, w=0.10) overwritten by
        # Resolving (^VIX > 35, w=0.20). Both evaluate to False for value 23.87.
        "triggered": False, "value": 23.87, "metric_field": "^VIX",
        "weight": 0.20, "direction": "above",
    },
    "High-yield spread": {
        # display_name collision: Building (< 300bp, w=0.15) overwritten by
        # Resolving (> 600bp, w=0.20). Both evaluate to False for value 317.
        "triggered": False, "value": 317.0, "metric_field": "credit.hy_spread",
        "weight": 0.20, "direction": "above",
    },
    # -- Building phase (non-colliding) --
    "Implied-realized vol gap": {
        # Injected by repair (Haiku systematically drops this computed indicator).
        # vix_vs_realized (4.86) > 5 = False. Matches legacy exactly.
        "triggered": False, "value": 4.86, "metric_field": "vix_vs_realized",
        "weight": 0.10, "direction": "above",
    },
    "Top-10 index concentration": {
        # Data unavailable: no data source implemented. Same as legacy.
        "triggered": False, "value": None, "metric_field": "top_10_sp500_weight",
        "weight": 0.20, "reason": "data_unavailable",
    },
    "Capex/revenue mismatch": {
        # new_indicator: UNRESOLVED field, excluded from scoring.
        # Legacy didn't include this (web-search, no field mapping).
        "triggered": False, "value": None, "metric_field": "UNRESOLVED:dominant_theme_capex_to_revenue_ratio",
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Margin debt": {
        # temporal_exclusion: historical_extreme requires SeriesStore.
        # Legacy triggered via BUG-03 (extracted "10" from "10% of record").
        "triggered": False, "value": None, "metric_field": "finra_margin_debt",
        "weight": 0.10, "reason": "data_unavailable",
    },
    "Large-cap/small-cap divergence": {
        # temporal_exclusion: historical_extreme requires SeriesStore.
        # Legacy triggered via BUG-03 (extracted "2" from "2-year high").
        "triggered": False, "value": None, "metric_field": "qqq_iwm_ratio",
        "weight": 0.10, "reason": "data_unavailable",
    },
    "Passive fund share": {
        "triggered": True, "value": 59.0, "metric_field": "passive_fund_share",
        "weight": 0.10, "direction": "above",
    },
    # -- Resolving phase (non-colliding) --
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
    # v9 Phase 4B: 10 indicators total (8 Building + 4 Resolving - 2 collisions)
    # 6 evaluable, 4 excluded (top_10, capex, margin_debt, large_cap)
    "total_in_results": 10, "skipped_web_qualitative": 4,
    "evaluated": 6, "excluded": 4, "triggered": 1,
    "evaluated_weight": 0.9500, "triggered_weight": 0.1000, "excluded_weight": 0.5500,
}


# -----------------------------------------------------------------------
# 5. fiscal_dominance_liquidity -- Score: 1.000000 (Active)
#    v9 Phase 4: COMPILED PATH. 5 temporal indicators excluded (persistence,
#    trend_state, delta_change without SeriesStore). 2 evaluable, both trigger.
#    Score: 0.35 / 0.35 = 1.000. Tier MATCH with legacy (Active).
# -----------------------------------------------------------------------

FISCAL_LIQ_INDICATORS = {
    "Net liquidity expanding": {
        # temporal_exclusion: persistence rule requires SeriesStore.
        # Legacy had BUG-03 (extracted "2" from "2+ of last 3 months").
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.20, "reason": "data_unavailable",
    },
    "Deficit pace": {
        # Scalar comparison: 3690 > 1500 = True. Matches legacy.
        "triggered": True, "value": 3690.0, "metric_field": "deficit_pace_annualized",
        "weight": 0.20, "direction": "above",
    },
    "Rate hikes not producing recession": {
        # temporal_exclusion: compound ALL has persistence sub-clause
        # (fed_funds > 4% for 12+ months). Whole indicator NOT_EVALUABLE.
        "triggered": False, "value": None, "metric_field": "growth.unemployment",
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Hard assets outperforming nominal bonds": {
        # Scalar comparison: 73.09 > 10 = True. Matches legacy.
        "triggered": True, "value": 73.09, "metric_field": "hard_vs_nominal_12m",
        "weight": 0.15, "direction": "above",
    },
    "RRP draining toward zero": {
        # temporal_exclusion: compound ALL has trend_state sub-clause.
        "triggered": False, "value": None, "metric_field": "liquidity.reverse_repo",
        "weight": 0.10, "reason": "data_unavailable",
    },
    "Fed balance sheet direction inconsistent with stated policy": {
        # temporal_exclusion: compound ANY, all 3 clauses are temporal
        # (delta_change, trend_state). Previously threshold_not_evaluable.
        "triggered": False, "value": None, "metric_field": "liquidity.fed_balance_sheet",
        "weight": 0.10, "reason": "data_unavailable",
    },
    "TGA behavior consistent with spending": {
        # temporal_exclusion: compound ANY, scalar clause False (847718 > 500000),
        # delta_change clause NOT_EVALUABLE. OR: all evaluable false, 1 not evaluable.
        "triggered": False, "value": None, "metric_field": "liquidity.tga",
        "weight": 0.10, "reason": "data_unavailable",
    },
}

FISCAL_LIQ_COVERAGE = {
    # v9 Phase 4: 2 evaluable (deficit_pace + hard_assets), 5 excluded (all temporal)
    "total_in_results": 7, "skipped_web_qualitative": 5,
    "evaluated": 2, "excluded": 5, "triggered": 2,
    "evaluated_weight": 0.3500, "triggered_weight": 0.3500, "excluded_weight": 0.6500,
}


# -----------------------------------------------------------------------
# 6. fiscal_dominance_arithmetic -- Score: 1.000 (Active)
#    v9 Phase 3: COMPILED PATH. Score parity at 1.000.
#    CEILING HIT: 2 indicators excluded (time-series), all 4 remaining trigger.
#    Score = 0.70 / 0.70 = 1.000 (shrunken denominator).
# -----------------------------------------------------------------------

FISCAL_ARITH_INDICATORS = {
    "Interest expense / tax receipts ratio": {
        "triggered": True, "value": 34.0, "metric_field": "interest_receipts_ratio",
        "weight": 0.25, "direction": "above",
        # weight_correction: ACTIVATION.md is source of truth (0.25),
        # compile_all.py had transcription error (0.20). See V9_PHASE3_5
        # display_name: Haiku uses full ACTIVATION.md name
    },
    "Interest expense exceeds major discretionary category": {
        "triggered": True, "value": 287.0, "metric_field": "interest_exceeds_defense",
        "weight": 0.15, "direction": "above",
        # display_name: Haiku uses full ACTIVATION.md name
    },
    "Deficit pace outside recession": {
        # Compound rule: deficit > 1500 AND unemployment < 5% (not in recession)
        "triggered": True, "value": None, "metric_field": "deficit_pace_annualized",
        "weight": 0.20, "direction": "above",
        # display_name: Haiku uses full ACTIVATION.md name
    },
    "Debt rollover at higher rates": {
        # Excluded: trend requires series store
        "triggered": False, "value": None, "metric_field": "weighted_avg_interest_rate",
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Gold/oil ratio elevated": {
        "triggered": True, "value": 42.3, "metric_field": "gold_oil_ratio",
        "weight": 0.10, "direction": "above",
        # weight_correction: ACTIVATION.md is source of truth (0.10),
        # compile_all.py had transcription error (0.15). See V9_PHASE3_5
    },
    "Central bank gold purchases sustained": {
        # Excluded: persistence requires series store
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.05, "reason": "data_unavailable",
        # weight_correction: ACTIVATION.md is source of truth (0.05),
        # compile_all.py had transcription error (0.15). See V9_PHASE3_5
    },
}

FISCAL_ARITH_COVERAGE = {
    # 6 indicators in results, 2 excluded (debt_rollover + cb_gold),
    # 4 evaluated, all 4 triggered
    # weight_correction: weights updated for ACTIVATION.md. See V9_PHASE3_6
    "total_in_results": 6, "skipped_web_qualitative": 2,
    "evaluated": 4, "excluded": 2, "triggered": 4,
    "evaluated_weight": 0.7000, "triggered_weight": 0.7000, "excluded_weight": 0.2000,
}


# -----------------------------------------------------------------------
# 7. capital_flows -- Rotation: 0.000 (Inactive), Accumulation: 0.200 (Inactive)
#    v9 Phase 4B: COMPILED PATH.
#    Accumulation: 4 evaluable, 1 triggered (Dollar strong). EM 3y sign fix:
#    compiled correctly uses lt -30 (9.5 < -30 = False). Weights corrected
#    from parser [CALIBRATION] tag fix (0.33/0.27/0.20/0.20 = 1.00).
#    Rotation: 5/6 temporal, Chinese equities now scalar (evaluable, False).
#    Effective: Inactive.
# -----------------------------------------------------------------------

CAPITAL_FLOWS_INDICATORS = {
    # -- Rotation phase (5 temporal, 1 evaluable) --
    "Dollar weakening": {
        # temporal_exclusion: compound ALL with trend_state + historical_extreme.
        "triggered": False, "value": None, "metric_field": "dxy_index",
        "weight": 0.25, "reason": "data_unavailable",
    },
    "China credit impulse positive and accelerating": {
        # temporal_exclusion: compound ALL, all sub-rules temporal.
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.20, "reason": "data_unavailable",
    },
    "RMB strengthening": {
        # temporal_exclusion: trend_state requires SeriesStore.
        "triggered": False, "value": None, "metric_field": "usdcny",
        "weight": 0.20, "reason": "data_unavailable",
    },
    "EM outperforming DM on relative basis": {
        # temporal_exclusion: persistence requires SeriesStore.
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.15, "reason": "data_unavailable",
    },
    "Commodity prices rising": {
        # temporal_exclusion: persistence requires SeriesStore.
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.10, "reason": "data_unavailable",
    },
    "Chinese equities leading": {
        # Simplified to scalar (fxi_3m_return > 15). -7.13 > 15 = False.
        # Previous compilation had compound with historical_extreme (needed series).
        "triggered": False, "value": -7.13, "metric_field": "fxi_3m_return",
        "weight": 0.10, "direction": "above",
    },
    # -- Accumulation phase (4 evaluable, correct weights) --
    "EM vs. DM PE gap at extremes": {
        "triggered": False, "value": 11.284, "metric_field": "em_dm_pe_gap",
        "weight": 0.33, "direction": "above",
    },
    "EM rolling 3-year underperformance": {
        # justified_improvement: compiled correctly uses lt -30.0.
        # 9.5 < -30 = False. Legacy stripped sign (9.5 < 30 = True, wrong).
        "triggered": False, "value": 9.5, "metric_field": "eem_spy_3y_relative",
        "weight": 0.27, "direction": "below",
    },
    "Dollar strong or sideways": {
        # compound OR: first clause dxy_index > 100 evaluable and True (100.08 > 100).
        # Value is None because compound doesn't propagate sub-values.
        "triggered": True, "value": None, "metric_field": "dxy_index",
        "weight": 0.20, "direction": "above",
    },
    "China credit impulse flat or negative": {
        "triggered": False, "value": 3.5, "metric_field": "china_credit_impulse",
        "weight": 0.20, "direction": "below",
    },
}

CAPITAL_FLOWS_COVERAGE = {
    # v9 Phase 4B: 5 evaluable (4 Accumulation + 1 Rotation Chinese equities)
    # 5 excluded (all Rotation temporal)
    "total_in_results": 10, "skipped_web_qualitative": 5,
    "evaluated": 5, "excluded": 5, "triggered": 1,
    "evaluated_weight": 1.1000, "triggered_weight": 0.2000, "excluded_weight": 0.9000,
}


# -----------------------------------------------------------------------
# 8. monetary_architecture -- Score: 0.000000 (Inactive)
#    v9 Phase 4: COMPILED PATH. All 3 legacy-shared indicators are temporal
#    (persistence, trend_state). Compiled adds 2 new: CCBS (BLOCKED/excluded),
#    non-dollar settlement (evaluable scalar, False at 3.89 < 4.0).
#    Score: 0.00 / 0.17 = 0.000. Tier downgrade Active->Inactive is honest.
# -----------------------------------------------------------------------

MONETARY_ARCH_INDICATORS = {
    "Central bank gold purchases sustained at elevated levels": {
        # temporal_exclusion: persistence rule requires SeriesStore.
        # Legacy triggered at 1037 > 800 (correct value, wrong evaluation method).
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.29, "reason": "data_unavailable",
    },
    "Foreign official Treasury holdings declining as share of outstanding": {
        # temporal_exclusion: trend_state requires SeriesStore.
        # Legacy had BUG-03 (extracted "3" from "3+ years").
        "triggered": False, "value": None, "metric_field": "foreign_treasury_holdings_pct",
        "weight": 0.24, "reason": "data_unavailable",
    },
    "Gold/oil ratio elevated and rising": {
        # temporal_exclusion: compound ALL has trend_state sub-clause.
        # Scalar clause (42.3 > 25) is True but trend is NOT_EVALUABLE.
        "triggered": False, "value": None, "metric_field": "gold_oil_ratio",
        "weight": 0.18, "reason": "data_unavailable",
    },
    "Cross-currency basis swap stress episodic": {
        # new_indicator: BLOCKED, empty compound after repair pass
        # (all UNRESOLVED clauses pruned). Excluded from scoring.
        "triggered": False, "value": None, "metric_field": None,
        "weight": 0.12, "reason": "data_unavailable",
    },
    "Non-dollar trade settlement growing": {
        # new_indicator: scalar comparison, rmb_swift_share (3.89) > 4.0 = False.
        # Only evaluable indicator. Legacy skipped this (no field mapping).
        "triggered": False, "value": 3.89, "metric_field": "rmb_swift_share",
        "weight": 0.17, "direction": "above",
    },
}

MONETARY_ARCH_COVERAGE = {
    # v9 Phase 4: 1 evaluable (non-dollar settlement), 4 excluded (3 temporal + 1 blocked)
    "total_in_results": 5, "skipped_web_qualitative": 4,
    "evaluated": 1, "excluded": 4, "triggered": 0,
    "evaluated_weight": 0.1700, "triggered_weight": 0.0000, "excluded_weight": 0.8300,
}


# =======================================================================
# TEST CLASSES
# =======================================================================


class TestValuationMeanReversion:
    """valuation_mean_reversion: single-phase, Active, 0.785714
    v9 Phase 3.6: Haiku-compiled with corrected ACTIVATION.md weights."""

    def test_score_and_tier(self, all_results):
        r = all_results["valuation_mean_reversion"]
        assert r.is_two_phase is False
        # weight_correction: 0.833333 -> 0.785714. ACTIVATION.md weights differ
        # from compile_all.py (ERP 0.25 not 0.20, cash_yield 0.15 not 0.10,
        # insider 0.05 not 0.15). See V9_PHASE3_6
        assert r.score == pytest.approx(0.785714, abs=1e-4)
        assert r.tier.value == "Active"

    def test_indicator_count(self, all_results):
        r = all_results["valuation_mean_reversion"]
        # Compiled includes Buffett in results (was skipped by legacy)
        assert len(r.indicator_results) == 7
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

    def test_excluded_time_series(self, all_results):
        """3 indicators excluded: Buffett (no data), breadth + insider (time-series)."""
        r = all_results["valuation_mean_reversion"]
        assert len(r.skipped_indicators) == 3
        skip_text = " ".join(r.skipped_indicators)
        assert "Buffett" in skip_text
        assert "breadth" in skip_text.lower() or "Market breadth" in skip_text
        assert "Insider" in skip_text


class TestDebtCycleShort:
    """debt_cycle_short: two-phase, Contraction 0.000 / Expansion 0.833333
    v9 Phase 4: COMPILED PATH. Contraction all-temporal except SLOOS.
    Expansion: 5 evaluable (4 triggered), Fed funds now evaluable.
    Effective: Active (Expansion)."""

    def test_phase_scores_and_tiers(self, all_results):
        r = all_results["debt_cycle_short"]
        assert r.is_two_phase is True
        # v9 Phase 4: Contraction 0.300->0.000 (Sahm BUG-03 + Fed wiring fixed)
        assert r.phase_scores["Contraction"] == pytest.approx(0.000, abs=1e-4)
        # v9 Phase 4: Expansion 1.000->0.833 (3 temporal excluded, Fed funds now evaluable False)
        assert r.phase_scores["Expansion"] == pytest.approx(0.833333, abs=1e-4)
        assert r.phase_tiers["Contraction"].value == "Inactive"
        assert r.phase_tiers["Expansion"].value == "Active"

    def test_effective_phase(self, all_results):
        r = all_results["debt_cycle_short"]
        # v9 Phase 4: effective flips from Adjacent(Contraction) to Active(Expansion)
        # because Contraction is now honestly Inactive (was inflated by bugs).
        assert r.effective_tier.value == "Active"
        assert r.effective_phase == "expansion"

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

    def test_contraction_temporal_exclusion(self, all_results):
        """v9 Phase 4: Contraction has 6 temporal indicators excluded.
        Only SLOOS is evaluable (scalar, not triggered). Score = 0.0/0.15 = 0.000."""
        r = all_results["debt_cycle_short"]
        contraction_excluded = [
            "ISM proxy below contraction",
            "Unemployment rising (Sahm Rule)",
            "Credit spreads widening sharply",
            "Yield curve re-steepening from deep inversion",
            "Initial claims rising",
            "Fed funds above nominal GDP growth",
        ]
        for name in contraction_excluded:
            assert r.indicator_results[name].get("reason") == "data_unavailable", (
                f"{name} should be excluded (temporal)"
            )

    def test_fed_funds_field_comparison(self, all_results):
        """v9 Phase 4 justified_improvement: Expansion 'Fed funds below GDP'
        is now evaluable as field_comparison. Legacy couldn't parse this.
        fed_funds (3.64) < nominal_gdp_growth (3.31) = False."""
        r = all_results["debt_cycle_short"]
        ff = r.indicator_results["Fed funds below nominal GDP growth"]
        assert ff["triggered"] is False
        assert ff["metric_field"] == "rates.fed_funds"
        assert ff["value"] == pytest.approx(3.64, abs=0.1)
        assert "reason" not in ff  # now evaluable, no reason code

    def test_k_suffix_initial_claims(self, all_results):
        """Task 3 regression: K-suffix scaling must hold for initial_claims."""
        r = all_results["debt_cycle_short"]
        # Expansion: claims low (202K < 250K -> triggered)
        assert r.indicator_results["Initial claims low"]["triggered"] is True


class TestDebtCycleLong:
    """debt_cycle_long: single-phase, Active, 0.764706
    v9 Phase 3.6: Haiku-compiled with corrected ACTIVATION.md weights."""

    def test_score_and_tier(self, all_results):
        r = all_results["debt_cycle_long"]
        assert r.is_two_phase is False
        # weight_correction: 0.647059 -> 0.764706. ACTIVATION.md weights differ
        # from compile_all.py (total_debt 0.25 not 0.20, fed_bs 0.25 not 0.15,
        # fiscal_deficit 0.15 not 0.20, wealth/real_rates 0.10 not 0.15). See V9_PHASE3_6
        assert r.score == pytest.approx(0.764706, abs=1e-4)
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

    def test_wealth_inequality_fixed(self, all_results):
        """v9 compiled path: wealth inequality correctly False (68.1 < 70%).
        Legacy extracted '10' from threshold, getting True (wrong).
        v9 Phase 3.6: display name now uses full ACTIVATION.md name."""
        r = all_results["debt_cycle_long"]
        wi = r.indicator_results["Wealth inequality at cycle-characteristic extremes"]
        assert wi["triggered"] is False
        assert wi["value"] == pytest.approx(68.1, abs=0.1)

    def test_rates_excluded(self, all_results):
        """rates_near_elb requires historical_extreme (series store), excluded."""
        r = all_results["debt_cycle_long"]
        assert len(r.skipped_indicators) == 1
        assert "Rates" in r.skipped_indicators[0]


class TestStructuralFragility:
    """structural_fragility: two-phase, Resolving 0.000 / Building 0.222222
    v9 Phase 4B: COMPILED PATH. Building: only passive_fund triggers.
    2 temporal (margin_debt, large_cap), 1 UNRESOLVED (capex), 1 data (top_10)."""

    def test_phase_scores_and_tiers(self, all_results):
        r = all_results["structural_fragility"]
        assert r.is_two_phase is True
        assert r.phase_scores["Resolving"] == pytest.approx(0.000, abs=1e-4)
        # v9 Phase 4B: Building 0.4615->0.2222 (temporal exclusion + BUG fixes)
        assert r.phase_scores["Building"] == pytest.approx(0.222222, abs=1e-4)
        assert r.phase_tiers["Resolving"].value == "Inactive"
        assert r.phase_tiers["Building"].value == "Inactive"

    def test_effective_phase(self, all_results):
        r = all_results["structural_fragility"]
        # v9 Phase 4B: effective Adjacent->Inactive (both phases Inactive)
        assert r.effective_tier.value == "Inactive"

    def test_indicator_count(self, all_results):
        r = all_results["structural_fragility"]
        # v9 Phase 4B: 9->10 (adds capex_revenue_mismatch from compiled)
        assert len(r.indicator_results) == 10
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

    def test_vol_gap_injected(self, all_results):
        """v9 Phase 4B: implied-realized vol gap injected by repair pass.
        Matches legacy exactly: vix_vs_realized (4.86) > 5 = False."""
        r = all_results["structural_fragility"]
        vg = r.indicator_results["Implied-realized vol gap"]
        assert vg["triggered"] is False
        assert vg["value"] == pytest.approx(4.86, abs=0.1)
        assert vg["metric_field"] == "vix_vs_realized"


class TestFiscalDominanceLiquidity:
    """fiscal_dominance_liquidity: single-phase, Active, 1.000000
    v9 Phase 4: COMPILED PATH. 5 temporal indicators excluded,
    2 evaluable both trigger. Score = 0.35/0.35 = 1.000."""

    def test_score_and_tier(self, all_results):
        r = all_results["fiscal_dominance_liquidity"]
        assert r.is_two_phase is False
        # v9 Phase 4: compiled score 1.000 (was legacy 0.778).
        # Denominator shrinkage from temporal exclusion, tier unchanged.
        assert r.score == pytest.approx(1.000000, abs=1e-4)
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

    def test_temporal_exclusion(self, all_results):
        """v9 Phase 4: 5 indicators excluded due to temporal rules (persistence,
        trend_state, delta_change) without SeriesStore. All correctly data_unavailable."""
        r = all_results["fiscal_dominance_liquidity"]
        excluded = {
            name: info for name, info in r.indicator_results.items()
            if info.get("reason") == "data_unavailable"
        }
        assert len(excluded) == 5
        assert "Net liquidity expanding" in excluded
        assert "Rate hikes not producing recession" in excluded
        assert "RRP draining toward zero" in excluded
        assert "Fed balance sheet direction inconsistent with stated policy" in excluded
        assert "TGA behavior consistent with spending" in excluded


class TestFiscalDominanceArithmetic:
    """fiscal_dominance_arithmetic: single-phase, Active, 1.000
    v9 Phase 3.6: Haiku-compiled with corrected ACTIVATION.md weights.
    CEILING HIT: 2 indicators excluded (time-series), all 4 remaining trigger."""

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

        v9 Phase 3.6 compiled: 4 evaluated, all triggered (w=0.70).
        2 excluded: Debt rollover + CB gold (w=0.20, time-series).
        # weight_correction: excluded_weight 0.30 -> 0.20 because
        # gold_oil dropped from 0.15 to 0.10, cb_gold from 0.15 to 0.05
        Total possible weight if nothing excluded: 0.90.
        Denominator: 0.70 (0.90 - 0.20 excluded).
        Score: 0.70 / 0.70 = 1.000.
        """
        r = all_results["fiscal_dominance_arithmetic"]
        cov = _compute_coverage(r)

        # All evaluated indicators trigger
        assert cov["evaluated"] == 4
        assert cov["triggered"] == 4
        assert cov["triggered_weight"] == cov["evaluated_weight"]

        # Shrunken denominator is visible
        assert cov["excluded"] == 2
        # weight_correction: ACTIVATION.md weights (0.15 + 0.05 = 0.20),
        # compile_all.py had 0.15 + 0.15 = 0.30. See V9_PHASE3_6
        assert cov["excluded_weight"] == pytest.approx(0.20, abs=1e-4)

        # The excluded indicators
        excluded = {
            name: info for name, info in r.indicator_results.items()
            if info.get("reason") in ("data_unavailable", "threshold_not_evaluable")
        }
        assert "Debt rollover at higher rates" in excluded
        assert "Central bank gold purchases sustained" in excluded


class TestCapitalFlows:
    """capital_flows: two-phase, Rotation 0.000 / Accumulation 0.200
    v9 Phase 4B: COMPILED PATH. EM 3y sign fixed. Weights corrected.
    Rotation all temporal except Chinese equities (scalar, False)."""

    def test_phase_scores_and_tiers(self, all_results):
        r = all_results["capital_flows"]
        assert r.is_two_phase is True
        # v9 Phase 4B: Rotation 0.450->0.000 (5/6 temporal, 1 evaluable False)
        assert r.phase_scores["Rotation"] == pytest.approx(0.000, abs=1e-4)
        # v9 Phase 4B: Accumulation 0.470->0.200 (EM 3y sign fix: False not True)
        assert r.phase_scores["Accumulation"] == pytest.approx(0.200, abs=1e-4)
        assert r.phase_tiers["Rotation"].value == "Inactive"
        assert r.phase_tiers["Accumulation"].value == "Inactive"

    def test_effective_phase(self, all_results):
        r = all_results["capital_flows"]
        # v9 Phase 4B: effective Adjacent->Inactive (both phases Inactive)
        assert r.effective_tier.value == "Inactive"

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

    def test_em_underperformance_sign_fix(self, all_results):
        """v9 Phase 4B justified_improvement: EM 3y underperformance now correctly
        checks < -30% (value 9.5 < -30 = False). Legacy stripped sign (9.5 < 30 = True)."""
        r = all_results["capital_flows"]
        em = r.indicator_results["EM rolling 3-year underperformance"]
        assert em["triggered"] is False
        assert em["value"] == pytest.approx(9.5, abs=0.1)
        assert em["weight"] == pytest.approx(0.27, abs=1e-4)


class TestMonetaryArchitecture:
    """monetary_architecture: single-phase, Inactive, 0.000000
    v9 Phase 4: COMPILED PATH. All 3 legacy indicators are temporal.
    2 new indicators from compiled (CCBS blocked, non-dollar evaluable).
    Tier downgrade Active->Inactive is honest temporal exclusion."""

    def test_score_and_tier(self, all_results):
        r = all_results["monetary_architecture"]
        assert r.is_two_phase is False
        # v9 Phase 4: 0.662->0.000. All shared indicators temporal.
        # Only evaluable indicator (non-dollar settlement) is False.
        assert r.score == pytest.approx(0.000000, abs=1e-4)
        assert r.tier.value == "Inactive"

    def test_indicator_count(self, all_results):
        r = all_results["monetary_architecture"]
        # v9 Phase 4: 3->5 indicators (compiled adds CCBS + non-dollar settlement)
        assert len(r.indicator_results) == 5
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

    def test_temporal_exclusion(self, all_results):
        """v9 Phase 4: 3 temporal indicators + 1 blocked = 4 excluded."""
        r = all_results["monetary_architecture"]
        assert len(r.skipped_indicators) == 4
        skip_text = " ".join(r.skipped_indicators)
        assert "gold purchases" in skip_text.lower()
        assert "Treasury" in skip_text
        assert "Gold/oil" in skip_text
        assert "Cross-currency" in skip_text

    def test_non_dollar_settlement_evaluable(self, all_results):
        """v9 Phase 4: non-dollar settlement is the only evaluable indicator.
        rmb_swift_share (3.89) > 4.0 = False. Legacy skipped this entirely."""
        r = all_results["monetary_architecture"]
        nd = r.indicator_results["Non-dollar trade settlement growing"]
        assert nd["triggered"] is False
        assert nd["value"] == pytest.approx(3.89, abs=0.1)
        assert nd["metric_field"] == "rmb_swift_share"


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
