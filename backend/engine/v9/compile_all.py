"""v9 Phase 2: Compile all 8 theories into Phase 0 schema artifacts.

Constructs CompiledActivationArtifact objects for every theory based on
the spike compilation results and the Phase 0/1 contract analysis.

Each indicator maps to a specific Phase 0 Rule type with proper
FieldOperand/LiteralOperand types, unit declarations, and ambiguity records.

The artifacts are deterministic — no API calls needed. When the user wants
to re-compile via Haiku (e.g., after editing a theory module), they run
the compiler adapter separately.

Depends on: compiler.py (builder helpers), Phase 0 schemas
Depended on by: scripts/v9_phase2_compile.py, parallel_compare.py
"""
from __future__ import annotations

from backend.schemas.v9.compiled_activation import (
    AmbiguityLevel,
    AmbiguityRecord,
    CompilationStatus,
    CompiledActivationArtifact,
    ExclusionPolicy,
    PhaseModel,
)
from backend.schemas.v9.units import SemanticType, TimeUnit, ValueUnit
from backend.engine.v9.compiler import (
    compound_all,
    compound_any,
    delta_change,
    field_cmp,
    historical_extreme,
    make_artifact,
    make_indicator,
    make_phase,
    named_pattern,
    persistence,
    save_artifact,
    scalar,
    trend,
)


# Shorthand helpers for ambiguity records
def _amb(level: str, desc: str, suggestion: str = "") -> AmbiguityRecord:
    return AmbiguityRecord(level=AmbiguityLevel(level), description=desc, suggestion=suggestion)


# ---------------------------------------------------------------------------
# 1. valuation_mean_reversion (7 indicators, single-phase)
# ---------------------------------------------------------------------------

def _build_valuation_mean_reversion() -> CompiledActivationArtifact:
    indicators = [
        make_indicator(
            "erp_compressed", "Equity risk premium compressed",
            "Equity risk premium below 1.0%",
            scalar("equity_risk_premium", "lt", 1.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.SPREAD),
            "equity_risk_premium", weight=0.20,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.SPREAD,
        ),
        make_indicator(
            "cape_elevated", "Shiller CAPE elevated",
            "CAPE above 30",
            scalar("shiller_cape", "gt", 30.0,
                   ValueUnit.RATIO, ValueUnit.RATIO, SemanticType.RATIO),
            "shiller_cape", weight=0.20,
            field_unit=ValueUnit.RATIO, field_semantic_type=SemanticType.RATIO,
        ),
        make_indicator(
            "buffett_extreme", "Buffett Indicator extreme",
            "Total market cap / GDP above 1.5x",
            scalar("buffett_indicator", "gt", 1.5,
                   ValueUnit.RATIO, ValueUnit.RATIO, SemanticType.RATIO),
            "buffett_indicator", weight=0.15,
            field_unit=ValueUnit.RATIO, field_semantic_type=SemanticType.RATIO,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Web-sourced field, may not be in briefing")],
        ),
        make_indicator(
            "cash_yield_exceeds_equity", "Cash yield exceeds equity yield",
            "Cash yield exceeds equity yield (spread > 0)",
            scalar("cash_exceeds_equity_yield", "gt", 0.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.SPREAD),
            "cash_exceeds_equity_yield", weight=0.10,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.SPREAD,
        ),
        make_indicator(
            "profit_margins_elevated", "Corporate profit margins elevated",
            "Net margins above 12% OR corporate profits/GDP above 10%",
            compound_any(
                scalar("sp500_net_margin", "gt", 12.0,
                       ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATE),
                scalar("corporate_profits_gdp_ratio", "gt", 10.0,
                       ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATIO),
            ),
            "sp500_net_margin", weight=0.10,
            field_dependencies=["corporate_profits_gdp_ratio"],
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATE,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "OR condition: legacy only checks first sub-condition")],
            paraphrase="Net margins > 12% OR profits/GDP > 10%",
        ),
        make_indicator(
            "breadth_narrow", "Market breadth narrow",
            "QQQ/IWM ratio at 2-year high, broad market divergence",
            historical_extreme("qqq_iwm_ratio", "high", 24, TimeUnit.MONTHS),
            "qqq_iwm_ratio", weight=0.10,
            field_unit=ValueUnit.RATIO, field_semantic_type=SemanticType.RATIO,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "RSP/SPY relative component has no data source")],
            warnings=["RSP/SPY relative performance field not available"],
        ),
        make_indicator(
            "insider_selling", "Insider selling elevated",
            "Insider sell/buy ratio elevated for 3+ months",
            persistence(
                scalar("insider_sell_buy_ratio", "gt", 5.0,
                       ValueUnit.RATIO, ValueUnit.RATIO, SemanticType.RATIO),
                n=3, k=3, window_val=3, window_unit=TimeUnit.MONTHS,
            ),
            "insider_sell_buy_ratio", weight=0.15,
            field_unit=ValueUnit.RATIO, field_semantic_type=SemanticType.RATIO,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Monthly granularity assumption for persistence window")],
        ),
    ]

    return make_artifact(
        "valuation_mean_reversion",
        PhaseModel.SINGLE_PHASE,
        [make_phase("single", "Active", indicators)],
    )


# ---------------------------------------------------------------------------
# 2. debt_cycle_short (15 indicators, two-phase)
# ---------------------------------------------------------------------------

def _build_debt_cycle_short() -> CompiledActivationArtifact:
    expansion = [
        make_indicator(
            "exp_ism_above_contraction", "ISM above contraction threshold",
            "ISM proxy above 50",
            scalar("growth.ism_proxy", "gt", 50.0,
                   ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS, SemanticType.INDEX),
            "growth.ism_proxy", weight=0.15,
            field_unit=ValueUnit.INDEX_POINTS, field_semantic_type=SemanticType.INDEX,
        ),
        make_indicator(
            "exp_unemployment_low", "Unemployment low or falling",
            "Below 5.0% OR declining",
            compound_any(
                scalar("growth.unemployment", "lt", 5.0,
                       ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATE),
                trend("growth.unemployment", "falling", 3, TimeUnit.MONTHS,
                      ValueUnit.PERCENT),
            ),
            "growth.unemployment", weight=0.10,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATE,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "OR decomposition of 'low or falling'")],
        ),
        make_indicator(
            "exp_credit_spreads_tight", "Credit spreads tight",
            "HY spread below 450bp AND not widening for 3+ months",
            compound_all(
                scalar("credit.hy_spread", "lt", 450.0,
                       ValueUnit.BASIS_POINTS, ValueUnit.BASIS_POINTS, SemanticType.SPREAD),
                trend("credit.hy_spread", "stable", 3, TimeUnit.MONTHS,
                      ValueUnit.BASIS_POINTS),
            ),
            "credit.hy_spread", weight=0.15,
            field_unit=ValueUnit.BASIS_POINTS, field_semantic_type=SemanticType.SPREAD,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "'Not widening' approximated as trend(stable)")],
        ),
        make_indicator(
            "exp_curve_not_inverted", "Yield curve not inverted",
            "2s10s curve above -0.50%",
            scalar("rates.curve_2s10s", "gt", -0.50,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.SPREAD),
            "rates.curve_2s10s", weight=0.10,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.SPREAD,
        ),
        make_indicator(
            "exp_initial_claims_low", "Initial claims low",
            "Initial claims below 250K",
            scalar("growth.initial_claims", "lt", 250.0,
                   ValueUnit.COUNT, ValueUnit.THOUSANDS, SemanticType.COUNT),
            "growth.initial_claims", weight=0.10,
            field_unit=ValueUnit.COUNT, field_semantic_type=SemanticType.COUNT,
            paraphrase="Weekly initial claims below 250,000 (threshold in thousands, field in raw count)",
        ),
        make_indicator(
            "exp_fed_funds_below_gdp", "Fed funds below nominal GDP growth",
            "Fed funds rate below nominal GDP growth rate",
            field_cmp("rates.fed_funds", "lt", derived_fn="nominal_gdp_growth",
                      left_unit=ValueUnit.PERCENT, right_unit=ValueUnit.PERCENT,
                      left_st=SemanticType.RATE, right_st=SemanticType.GROWTH_RATE),
            "rates.fed_funds", weight=0.10,
            field_dependencies=["growth.real_gdp", "inflation.cpi_yoy"],
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATE,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Uses derived nominal_gdp_growth = real_gdp + cpi_yoy")],
        ),
        make_indicator(
            "exp_net_credit_growth", "Net credit growth positive",
            "Bank loan growth YoY positive",
            scalar("UNRESOLVED:loan_growth_yoy", "gt", 0.0),
            "UNRESOLVED:loan_growth_yoy", weight=0.15,
            compilation_status=CompilationStatus.BLOCKED,
            warnings=["loan_growth_yoy field not available in briefing packet"],
        ),
        make_indicator(
            "exp_consumer_confidence", "Consumer confidence stable/rising",
            "Consumer confidence above 90 AND stable or rising",
            compound_all(
                scalar("consumer_confidence", "gt", 90.0,
                       ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS, SemanticType.INDEX),
                trend("consumer_confidence", "stable", 3, TimeUnit.MONTHS,
                      ValueUnit.INDEX_POINTS),
            ),
            "consumer_confidence", weight=0.15,
            field_unit=ValueUnit.INDEX_POINTS, field_semantic_type=SemanticType.INDEX,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "CEO confidence survey component unresolved")],
        ),
    ]

    contraction = [
        make_indicator(
            "con_ism_below_contraction", "ISM below contraction AND falling",
            "ISM proxy below 48 AND declining for 3+ months",
            compound_all(
                scalar("growth.ism_proxy", "lt", 48.0,
                       ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS, SemanticType.INDEX),
                trend("growth.ism_proxy", "falling", 3, TimeUnit.MONTHS,
                      ValueUnit.INDEX_POINTS),
            ),
            "growth.ism_proxy", weight=0.20,
            field_unit=ValueUnit.INDEX_POINTS, field_semantic_type=SemanticType.INDEX,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Compound: scalar + 3-month falling trend")],
        ),
        make_indicator(
            "con_sahm_rule", "Unemployment rising (Sahm Rule)",
            "Sahm Rule triggered: 3-month MA of unemployment rising 0.50%+ above 12-month low",
            named_pattern("sahm_rule",
                          params={"field": "growth.unemployment", "threshold": 0.50},
                          deps=["growth.unemployment"]),
            "growth.unemployment", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATE,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Custom 3mo-MA-vs-12mo-low computation required")],
        ),
        make_indicator(
            "con_credit_spreads_widening", "Credit spreads widening rapidly",
            "(HY > 500bp AND rising for 2 months) OR HY > 600bp",
            compound_any(
                compound_all(
                    scalar("credit.hy_spread", "gt", 500.0,
                           ValueUnit.BASIS_POINTS, ValueUnit.BASIS_POINTS, SemanticType.SPREAD),
                    trend("credit.hy_spread", "rising", 2, TimeUnit.MONTHS,
                          ValueUnit.BASIS_POINTS),
                ),
                scalar("credit.hy_spread", "gt", 600.0,
                       ValueUnit.BASIS_POINTS, ValueUnit.BASIS_POINTS, SemanticType.SPREAD),
            ),
            "credit.hy_spread", weight=0.15,
            field_unit=ValueUnit.BASIS_POINTS, field_semantic_type=SemanticType.SPREAD,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Three-level nesting: OR(AND(scalar, trend), scalar)")],
        ),
        make_indicator(
            "con_curve_resteepening", "Yield curve re-steepening after inversion",
            "Curve re-steepened from deep inversion",
            named_pattern("resteepened_after_inversion",
                          params={"curve_field": "rates.curve_2s10s",
                                  "inversion_threshold": -0.75, "delta_rise": 0.75},
                          deps=["rates.curve_2s10s"]),
            "rates.curve_2s10s", weight=0.10,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.SPREAD,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "75bp delta rise from trough needs lookback")],
        ),
        make_indicator(
            "con_initial_claims_rising", "Initial claims rising",
            "Initial claims above 280K AND rising for 8+ weeks",
            compound_all(
                scalar("growth.initial_claims", "gt", 280.0,
                       ValueUnit.COUNT, ValueUnit.THOUSANDS, SemanticType.COUNT),
                trend("growth.initial_claims", "rising", 8, TimeUnit.WEEKS,
                      ValueUnit.COUNT),
            ),
            "growth.initial_claims", weight=0.10,
            field_unit=ValueUnit.COUNT, field_semantic_type=SemanticType.COUNT,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "8-week window for weekly data")],
        ),
        make_indicator(
            "con_fed_funds_above_gdp", "Fed funds above nominal GDP growth",
            "Fed funds > nominal GDP growth + 1% AND sustained for 6+ months",
            compound_all(
                field_cmp("rates.fed_funds", "gt", derived_fn="nominal_gdp_growth",
                          left_unit=ValueUnit.PERCENT, right_unit=ValueUnit.PERCENT,
                          left_st=SemanticType.RATE, right_st=SemanticType.GROWTH_RATE),
                persistence(
                    scalar("rates.fed_funds", "gt", 4.0,
                           ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATE),
                    n=6, k=6, window_val=6, window_unit=TimeUnit.MONTHS,
                    mode="consecutive",
                ),
            ),
            "rates.fed_funds", weight=0.15,
            field_dependencies=["growth.real_gdp", "inflation.cpi_yoy"],
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATE,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Compound: field comparison + persistence; offset +1% implicit")],
        ),
        make_indicator(
            "con_sloos_tightening", "SLOOS broad tightening",
            "Senior Loan Officer Survey showing net tightening",
            scalar("sloos_net_tightening", "gt", 0.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.INDEX),
            "sloos_net_tightening", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.INDEX,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("high", "Multi-categorical survey collapsed to single metric > 0")],
        ),
    ]

    return make_artifact(
        "debt_cycle_short",
        PhaseModel.TWO_PHASE,
        [
            make_phase("expansion", "Expansion", expansion),
            make_phase("contraction", "Contraction", contraction),
        ],
    )


# ---------------------------------------------------------------------------
# 3. debt_cycle_long (6 indicators, single-phase)
# ---------------------------------------------------------------------------

def _build_debt_cycle_long() -> CompiledActivationArtifact:
    indicators = [
        make_indicator(
            "total_debt_gdp_elevated", "Total debt/GDP above warning level",
            "Total debt to GDP above 250%",
            scalar("total_debt_to_gdp", "gt", 250.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATIO),
            "total_debt_to_gdp", weight=0.20,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATIO,
        ),
        make_indicator(
            "fed_bs_gdp_elevated", "Fed balance sheet/GDP elevated",
            "Fed BS as % of GDP above 20%",
            scalar("fed_bs_gdp_ratio", "gt", 20.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATIO),
            "fed_bs_gdp_ratio", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATIO,
        ),
        make_indicator(
            "rates_near_elb", "Rates at/near effective lower bound in recent memory",
            "Fed funds at or near 10-year low",
            historical_extreme("rates.fed_funds", "low", 120, TimeUnit.MONTHS, "lt"),
            "rates.fed_funds", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATE,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "10-year lookback for ELB proximity")],
        ),
        make_indicator(
            "fiscal_deficit_primary_driver", "Fiscal deficit as primary growth driver",
            "Deficit > 5% GDP + non-recession + private credit < 3%",
            compound_all(
                scalar("deficit_pct_gdp", "gt", 5.0,
                       ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATIO),
                scalar("growth.unemployment", "lt", 7.0,
                       ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATE),
            ),
            "deficit_pct_gdp", weight=0.20,
            field_dependencies=["growth.unemployment"],
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATIO,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("high", "Private credit growth field not available; "
                              "non-recession proxied by unemployment < 7%")],
            warnings=["private_credit_growth field not in briefing; partial compilation"],
        ),
        make_indicator(
            "wealth_inequality_extreme", "Wealth inequality at extremes",
            "Top 10% wealth share > 70%",
            scalar("top10_wealth_share", "gt", 70.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.SHARE_OF_TOTAL),
            "top10_wealth_share", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.SHARE_OF_TOTAL,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "OR condition with top1_income_share > 20% "
                              "dropped (field not available)")],
            warnings=["top_1_percent_income_share not in briefing; simplified to single metric"],
        ),
        make_indicator(
            "negative_real_rates", "Negative real rates during expansion",
            "Real fed funds rate below 0%",
            scalar("real_fed_funds_rate", "lt", 0.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATE),
            "real_fed_funds_rate", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATE,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "'During expansion' qualifier not encoded in rule")],
        ),
    ]

    return make_artifact(
        "debt_cycle_long",
        PhaseModel.SINGLE_PHASE,
        [make_phase("single", "Active", indicators)],
    )


# ---------------------------------------------------------------------------
# 4. structural_fragility (12 indicators, two-phase)
# ---------------------------------------------------------------------------

def _build_structural_fragility() -> CompiledActivationArtifact:
    building = [
        make_indicator(
            "bld_vix_low", "Implied vol level (VIX) low",
            "VIX below 14 — complacency signal",
            scalar("^VIX", "lt", 14.0,
                   ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS, SemanticType.INDEX),
            "^VIX", weight=0.10,
            field_unit=ValueUnit.INDEX_POINTS, field_semantic_type=SemanticType.INDEX,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Spike mapped to vix_vs_realized; corrected to ^VIX")],
            warnings=["Spike had VIX field resolution gap; fixed in Phase 2"],
        ),
        make_indicator(
            "bld_vol_gap", "Implied-realized vol gap wide",
            "VIX vs realized vol gap above 5 points",
            scalar("vix_vs_realized", "gt", 5.0,
                   ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS, SemanticType.SPREAD),
            "vix_vs_realized", weight=0.10,
            field_unit=ValueUnit.INDEX_POINTS, field_semantic_type=SemanticType.SPREAD,
        ),
        make_indicator(
            "bld_hy_spread_tight", "High-yield spreads complacently tight",
            "HY spread below 300bp",
            scalar("credit.hy_spread", "lt", 300.0,
                   ValueUnit.BASIS_POINTS, ValueUnit.BASIS_POINTS, SemanticType.SPREAD),
            "credit.hy_spread", weight=0.15,
            field_unit=ValueUnit.BASIS_POINTS, field_semantic_type=SemanticType.SPREAD,
        ),
        make_indicator(
            "bld_top10_concentration", "Top-10 index concentration elevated",
            "Top 10 S&P 500 weight above 30%",
            scalar("top_10_sp500_weight", "gt", 30.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.SHARE_OF_TOTAL),
            "top_10_sp500_weight", weight=0.10,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.SHARE_OF_TOTAL,
            compilation_status=CompilationStatus.WARNING,
            warnings=["top_10_sp500_weight has no data source (null in briefing)"],
        ),
        make_indicator(
            "bld_capex_mismatch", "Capex/revenue mismatch",
            "Qualitative/thematic indicator — not compilable",
            scalar("UNRESOLVED:capex_revenue_mismatch", "gt", 0.0),
            "UNRESOLVED:capex_revenue_mismatch", weight=0.10,
            compilation_status=CompilationStatus.BLOCKED,
            exclusion_policy=ExclusionPolicy.EXCLUDE_FROM_SCORING,
            ambiguities=[_amb("high", "Qualitative indicator; no mechanical threshold possible")],
            warnings=["Permanently qualitative; should be a context_flag, not activation indicator"],
        ),
        make_indicator(
            "bld_margin_debt_high", "Margin debt at/near record highs",
            "Margin debt within 10% of record high",
            historical_extreme("finra_margin_debt", "high", 12, TimeUnit.MONTHS, "gt", 0.10,
                               ValueUnit.USD_BILLIONS),
            "finra_margin_debt", weight=0.15,
            field_unit=ValueUnit.USD_BILLIONS, field_semantic_type=SemanticType.LEVEL,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "10% margin for 'near record highs'")],
        ),
        make_indicator(
            "bld_large_small_divergence", "Large-cap/small-cap divergence",
            "QQQ/IWM ratio above 2-year high",
            historical_extreme("qqq_iwm_ratio", "high", 24, TimeUnit.MONTHS),
            "qqq_iwm_ratio", weight=0.15,
            field_unit=ValueUnit.RATIO, field_semantic_type=SemanticType.RATIO,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "24-month lookback for 2-year high")],
        ),
        make_indicator(
            "bld_passive_share", "Passive fund share elevated",
            "Passive fund share above 50%",
            scalar("passive_fund_share", "gt", 50.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.SHARE_OF_TOTAL),
            "passive_fund_share", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.SHARE_OF_TOTAL,
        ),
    ]

    resolving = [
        make_indicator(
            "res_vix_elevated", "Implied vol level (VIX) elevated",
            "VIX above 30 — stress signal",
            scalar("^VIX", "gt", 30.0,
                   ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS, SemanticType.INDEX),
            "^VIX", weight=0.25,
            field_unit=ValueUnit.INDEX_POINTS, field_semantic_type=SemanticType.INDEX,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Resolving VIX threshold; spike had field resolution gap")],
        ),
        make_indicator(
            "res_hy_spread_wide", "High-yield spreads blown out",
            "HY spread above 600bp",
            scalar("credit.hy_spread", "gt", 600.0,
                   ValueUnit.BASIS_POINTS, ValueUnit.BASIS_POINTS, SemanticType.SPREAD),
            "credit.hy_spread", weight=0.25,
            field_unit=ValueUnit.BASIS_POINTS, field_semantic_type=SemanticType.SPREAD,
        ),
        make_indicator(
            "res_drawdown_deep", "Drawdown depth significant",
            "SPY drawdown from 52-week high exceeding -20%",
            scalar("spy_drawdown_from_52w_high", "lt", -20.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.GROWTH_RATE),
            "spy_drawdown_from_52w_high", weight=0.25,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.GROWTH_RATE,
        ),
        make_indicator(
            "res_cape_compressed", "Valuation compression (CAPE)",
            "CAPE below 20",
            scalar("shiller_cape", "lt", 20.0,
                   ValueUnit.RATIO, ValueUnit.RATIO, SemanticType.RATIO),
            "shiller_cape", weight=0.25,
            field_unit=ValueUnit.RATIO, field_semantic_type=SemanticType.RATIO,
        ),
    ]

    return make_artifact(
        "structural_fragility",
        PhaseModel.TWO_PHASE,
        [
            make_phase("building", "Building", building),
            make_phase("resolving", "Resolving", resolving),
        ],
    )


# ---------------------------------------------------------------------------
# 5. fiscal_dominance_arithmetic (6 indicators, single-phase)
# ---------------------------------------------------------------------------

def _build_fiscal_dominance_arithmetic() -> CompiledActivationArtifact:
    indicators = [
        make_indicator(
            "interest_receipts_ratio", "Interest/receipts ratio elevated",
            "Net interest as % of federal receipts above 20%",
            scalar("interest_receipts_ratio", "gt", 20.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATIO),
            "interest_receipts_ratio", weight=0.20,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATIO,
        ),
        make_indicator(
            "interest_exceeds_defense", "Interest exceeds defense spending",
            "Net interest expense exceeds defense budget (spread > 0)",
            scalar("interest_exceeds_defense", "gt", 0.0,
                   ValueUnit.USD_BILLIONS, ValueUnit.USD_BILLIONS, SemanticType.LEVEL),
            "interest_exceeds_defense", weight=0.15,
            field_unit=ValueUnit.USD_BILLIONS, field_semantic_type=SemanticType.LEVEL,
        ),
        make_indicator(
            "deficit_pace_outside_recession", "Deficit pace elevated outside recession",
            "Annualized deficit > $1500B AND unemployment < 5%",
            compound_all(
                scalar("deficit_pace_annualized", "gt", 1500.0,
                       ValueUnit.USD_BILLIONS, ValueUnit.USD_BILLIONS, SemanticType.LEVEL),
                scalar("growth.unemployment", "lt", 5.0,
                       ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATE),
            ),
            "deficit_pace_annualized", weight=0.20,
            field_dependencies=["growth.unemployment"],
            field_unit=ValueUnit.USD_BILLIONS, field_semantic_type=SemanticType.LEVEL,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Non-recession proxied by unemployment < 5%")],
        ),
        make_indicator(
            "debt_rollover_higher_rates", "Debt rollover at higher rates",
            "Weighted average interest rate trending higher",
            trend("weighted_avg_interest_rate", "rising", 6, TimeUnit.MONTHS,
                  ValueUnit.PERCENT),
            "weighted_avg_interest_rate", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATE,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Trend + field comparison; time-series required")],
        ),
        make_indicator(
            "gold_oil_ratio_elevated", "Gold/oil ratio elevated",
            "Gold/oil ratio above 25",
            scalar("gold_oil_ratio", "gt", 25.0,
                   ValueUnit.RATIO, ValueUnit.RATIO, SemanticType.RATIO),
            "gold_oil_ratio", weight=0.15,
            field_unit=ValueUnit.RATIO, field_semantic_type=SemanticType.RATIO,
        ),
        make_indicator(
            "cb_gold_purchases", "Central bank gold purchases sustained",
            "CB gold purchases > 800 tonnes for 2 consecutive years",
            persistence(
                scalar("cb_gold_purchases", "gt", 800.0,
                       ValueUnit.TONS, ValueUnit.TONS, SemanticType.COUNT),
                n=2, k=2, window_val=2, window_unit=TimeUnit.YEARS,
                mode="consecutive",
            ),
            "cb_gold_purchases", weight=0.15,
            field_unit=ValueUnit.TONS, field_semantic_type=SemanticType.COUNT,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Annual data; 2-year persistence window")],
        ),
    ]

    return make_artifact(
        "fiscal_dominance_arithmetic",
        PhaseModel.SINGLE_PHASE,
        [make_phase("single", "Active", indicators)],
    )


# ---------------------------------------------------------------------------
# 6. fiscal_dominance_liquidity (7 indicators, single-phase)
# ---------------------------------------------------------------------------

def _build_fiscal_dominance_liquidity() -> CompiledActivationArtifact:
    indicators = [
        make_indicator(
            "net_liquidity_expanding", "Net liquidity expanding",
            "Net liquidity positive for 2+ of last 3 months",
            persistence(
                scalar("net_liquidity", "gt", 0.0,
                       ValueUnit.USD_BILLIONS, ValueUnit.DIMENSIONLESS, SemanticType.LEVEL),
                n=2, k=3, window_val=3, window_unit=TimeUnit.MONTHS,
            ),
            "net_liquidity", weight=0.15,
            field_unit=ValueUnit.USD_BILLIONS, field_semantic_type=SemanticType.LEVEL,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Persistence on monthly level changes")],
        ),
        make_indicator(
            "deficit_pace_elevated", "Deficit pace elevated",
            "Annualized deficit pace above $1500B",
            scalar("deficit_pace_annualized", "gt", 1500.0,
                   ValueUnit.USD_BILLIONS, ValueUnit.USD_BILLIONS, SemanticType.LEVEL),
            "deficit_pace_annualized", weight=0.15,
            field_unit=ValueUnit.USD_BILLIONS, field_semantic_type=SemanticType.LEVEL,
        ),
        make_indicator(
            "rate_hikes_no_recession", "Rate hikes not producing recession",
            "Unemployment < 5% AND ISM > 45 AND fed funds > 4% for 12+ months",
            compound_all(
                scalar("growth.unemployment", "lt", 5.0,
                       ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATE),
                scalar("growth.ism_proxy", "gt", 45.0,
                       ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS, SemanticType.INDEX),
                persistence(
                    scalar("rates.fed_funds", "gt", 4.0,
                           ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATE),
                    n=12, k=12, window_val=12, window_unit=TimeUnit.MONTHS,
                    mode="consecutive",
                ),
            ),
            "growth.unemployment", weight=0.15,
            field_dependencies=["growth.ism_proxy", "rates.fed_funds"],
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATE,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Complex compound with 12-month persistence")],
        ),
        make_indicator(
            "hard_assets_outperforming", "Hard assets outperforming",
            "Hard assets vs nominal assets 12-month relative > 10%",
            scalar("hard_vs_nominal_12m", "gt", 10.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.GROWTH_RATE),
            "hard_vs_nominal_12m", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.GROWTH_RATE,
        ),
        make_indicator(
            "rrp_draining", "RRP draining toward zero",
            "Reverse repo below $250B AND declining",
            compound_all(
                scalar("liquidity.reverse_repo", "lt", 250.0,
                       ValueUnit.USD_BILLIONS, ValueUnit.USD_BILLIONS, SemanticType.LEVEL),
                trend("liquidity.reverse_repo", "falling", 3, TimeUnit.MONTHS,
                      ValueUnit.USD_BILLIONS),
            ),
            "liquidity.reverse_repo", weight=0.10,
            field_unit=ValueUnit.USD_BILLIONS, field_semantic_type=SemanticType.LEVEL,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "'Declining' decomposed as trend(falling)")],
        ),
        make_indicator(
            "fed_bs_inconsistent", "Fed BS inconsistent with announced QT pace",
            "Fed balance sheet declining slower than announced QT pace",
            trend("liquidity.fed_balance_sheet", "falling", 3, TimeUnit.MONTHS,
                  ValueUnit.USD_BILLIONS),
            "liquidity.fed_balance_sheet", weight=0.15,
            field_unit=ValueUnit.USD_BILLIONS, field_semantic_type=SemanticType.LEVEL,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("high", "Policy-dependent threshold; requires external QT pace metadata; "
                              "fundamentally non-compilable without policy context")],
            warnings=["Requires policy_context extension to briefing packet"],
        ),
        make_indicator(
            "tga_spending", "TGA spending behavior",
            "TGA below $500B OR declining by $100B+ over 60 days",
            compound_any(
                scalar("liquidity.tga", "lt", 500.0,
                       ValueUnit.USD_BILLIONS, ValueUnit.USD_BILLIONS, SemanticType.LEVEL),
                delta_change("liquidity.tga", "falling", 100.0, "absolute",
                             60, TimeUnit.DAYS, ValueUnit.USD_BILLIONS,
                             ValueUnit.USD_BILLIONS),
            ),
            "liquidity.tga", weight=0.15,
            field_unit=ValueUnit.USD_BILLIONS, field_semantic_type=SemanticType.LEVEL,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Delta magnitude pattern: $100B over 60 days")],
        ),
    ]

    return make_artifact(
        "fiscal_dominance_liquidity",
        PhaseModel.SINGLE_PHASE,
        [make_phase("single", "Active", indicators)],
    )


# ---------------------------------------------------------------------------
# 7. capital_flows (10 indicators, two-phase)
# ---------------------------------------------------------------------------

def _build_capital_flows() -> CompiledActivationArtifact:
    accumulation = [
        make_indicator(
            "acc_em_dm_pe_gap", "EM vs DM PE gap elevated",
            "EM/DM PE gap above 40%",
            scalar("em_dm_pe_gap", "gt", 40.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.RATIO),
            "em_dm_pe_gap", weight=0.25,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.RATIO,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "PE gap semantics: measures DM premium over EM in %")],
        ),
        make_indicator(
            "acc_em_3yr_underperformance", "EM 3-year underperformance",
            "EM has underperformed SPY by 30%+ over measurement period",
            scalar("eem_spy_3y_relative", "lt", -30.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.GROWTH_RATE),
            "eem_spy_3y_relative", weight=0.25,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.GROWTH_RATE,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Uses 12-month return proxy for 3-year cumulative; "
                              "sign convention: negative = EM underperformance")],
            paraphrase="eem_spy_3y_relative < -30: EM must have underperformed by 30%+",
        ),
        make_indicator(
            "acc_dollar_strong", "Dollar strong or sideways",
            "DXY above 100 OR trending higher/flat",
            compound_any(
                scalar("dxy_index", "gt", 100.0,
                       ValueUnit.INDEX_POINTS, ValueUnit.INDEX_POINTS, SemanticType.INDEX),
                trend("dxy_index", "rising", 3, TimeUnit.MONTHS, ValueUnit.INDEX_POINTS),
                trend("dxy_index", "stable", 3, TimeUnit.MONTHS, ValueUnit.INDEX_POINTS),
            ),
            "dxy_index", weight=0.25,
            field_unit=ValueUnit.INDEX_POINTS, field_semantic_type=SemanticType.INDEX,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "OR of scalar + two trend states")],
        ),
        make_indicator(
            "acc_china_credit_flat", "China credit impulse flat or negative",
            "China credit impulse at or below zero",
            scalar("china_credit_impulse", "lte", 0.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.GROWTH_RATE),
            "china_credit_impulse", weight=0.25,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.GROWTH_RATE,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Credit impulse sign convention: positive = expanding credit")],
        ),
    ]

    rotation = [
        make_indicator(
            "rot_dollar_weakening", "Dollar weakening",
            "DXY trending lower for 3+ months AND below 12-month average",
            compound_all(
                trend("dxy_index", "falling", 3, TimeUnit.MONTHS, ValueUnit.INDEX_POINTS),
                historical_extreme("dxy_index", "low", 12, TimeUnit.MONTHS, "lt"),
            ),
            "dxy_index", weight=0.20,
            field_unit=ValueUnit.INDEX_POINTS, field_semantic_type=SemanticType.INDEX,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Nearly all temporal; below 12mo avg approximated as lookback")],
        ),
        make_indicator(
            "rot_china_credit_positive", "China credit impulse positive and rising",
            "Credit impulse > 0 for 2/3 months AND trending higher",
            compound_all(
                persistence(
                    scalar("china_credit_impulse", "gt", 0.0,
                           ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.GROWTH_RATE),
                    n=2, k=3, window_val=3, window_unit=TimeUnit.MONTHS,
                ),
                trend("china_credit_impulse", "rising", 3, TimeUnit.MONTHS,
                      ValueUnit.PERCENT),
            ),
            "china_credit_impulse", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.GROWTH_RATE,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Persistence + trend compound; fully temporal")],
        ),
        make_indicator(
            "rot_rmb_strengthening", "RMB strengthening",
            "USD/CNY declining for 3+ months (CNY appreciating)",
            trend("usdcny", "falling", 3, TimeUnit.MONTHS, ValueUnit.RATIO),
            "usdcny", weight=0.15,
            field_unit=ValueUnit.RATIO, field_semantic_type=SemanticType.LEVEL,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "USD/CNY falling = CNY strengthening")],
        ),
        make_indicator(
            "rot_em_outperforming", "EM outperforming DM",
            "EEM/SPY 3-month relative trending higher for 3+ months",
            trend("eem_spy_3m_relative", "rising", 3, TimeUnit.MONTHS,
                  ValueUnit.PERCENT),
            "eem_spy_3m_relative", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.GROWTH_RATE,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "3-month relative return trending")],
        ),
        make_indicator(
            "rot_commodity_prices_rising", "Commodity prices rising",
            "Commodity index 3-month change trending higher",
            trend("commodity_index_3m_change", "rising", 3, TimeUnit.MONTHS,
                  ValueUnit.PERCENT),
            "commodity_index_3m_change", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.GROWTH_RATE,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Double-counted temporal window")],
        ),
        make_indicator(
            "rot_chinese_equities_leading", "Chinese equities leading rotation",
            "FXI 3-month return positive and outperforming",
            scalar("fxi_3m_return", "gt", 0.0,
                   ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.GROWTH_RATE),
            "fxi_3m_return", weight=0.20,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.GROWTH_RATE,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Simplified from lookback to scalar; "
                              "spike had field unresolved (now in registry)")],
            warnings=["Field was UNRESOLVED in spike; now available in Phase 1 registry"],
        ),
    ]

    return make_artifact(
        "capital_flows",
        PhaseModel.TWO_PHASE,
        [
            make_phase("accumulation", "Accumulation", accumulation),
            make_phase("rotation", "Rotation", rotation),
        ],
    )


# ---------------------------------------------------------------------------
# 8. monetary_architecture (5 indicators, single-phase)
# ---------------------------------------------------------------------------

def _build_monetary_architecture() -> CompiledActivationArtifact:
    indicators = [
        make_indicator(
            "cb_gold_sustained", "Central bank gold purchases sustained",
            "CB gold purchases > 800 tonnes for 2 consecutive years",
            persistence(
                scalar("cb_gold_purchases", "gt", 800.0,
                       ValueUnit.TONS, ValueUnit.TONS, SemanticType.COUNT),
                n=2, k=2, window_val=2, window_unit=TimeUnit.YEARS,
                mode="consecutive",
            ),
            "cb_gold_purchases", weight=0.25,
            field_unit=ValueUnit.TONS, field_semantic_type=SemanticType.COUNT,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("medium", "Annual data; same pattern as fiscal_dom_arith")],
        ),
        make_indicator(
            "foreign_treasury_declining", "Foreign treasury holdings declining",
            "Foreign holdings as % of total declining for 3+ years",
            trend("foreign_treasury_holdings_pct", "falling", 36, TimeUnit.MONTHS,
                  ValueUnit.PERCENT),
            "foreign_treasury_holdings_pct", weight=0.20,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.SHARE_OF_TOTAL,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "3-year trend window")],
        ),
        make_indicator(
            "gold_oil_elevated_rising", "Gold/oil ratio elevated and rising",
            "Gold/oil > 25 AND trending higher for 12+ months",
            compound_all(
                scalar("gold_oil_ratio", "gt", 25.0,
                       ValueUnit.RATIO, ValueUnit.RATIO, SemanticType.RATIO),
                trend("gold_oil_ratio", "rising", 12, TimeUnit.MONTHS,
                      ValueUnit.RATIO),
            ),
            "gold_oil_ratio", weight=0.20,
            field_unit=ValueUnit.RATIO, field_semantic_type=SemanticType.RATIO,
            requires_time_series=True,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("low", "Scalar + 12-month trend")],
        ),
        make_indicator(
            "ccbs_stress", "Cross-currency basis swap stress",
            "EUR/USD, JPY/USD 3-month CCBS stress or spike",
            scalar("UNRESOLVED:eur_usd_3m_ccbs", "lt", -30.0,
                   ValueUnit.BASIS_POINTS, ValueUnit.BASIS_POINTS, SemanticType.SPREAD),
            "UNRESOLVED:eur_usd_3m_ccbs", weight=0.20,
            compilation_status=CompilationStatus.BLOCKED,
            ambiguities=[_amb("high", "4 CCBS fields not in briefing packet")],
            warnings=["eur_usd_3m_ccbs, jpy_usd_3m_ccbs, spike variants all UNRESOLVED"],
        ),
        make_indicator(
            "non_dollar_settlement", "Non-dollar trade settlement rising",
            "RMB SWIFT share > 4% OR non-dollar energy settlement rising",
            compound_any(
                scalar("rmb_swift_share", "gt", 4.0,
                       ValueUnit.PERCENT, ValueUnit.PERCENT, SemanticType.SHARE_OF_TOTAL),
                scalar("UNRESOLVED:non_dollar_energy_settlement", "gt", 0.0),
            ),
            "rmb_swift_share", weight=0.15,
            field_unit=ValueUnit.PERCENT, field_semantic_type=SemanticType.SHARE_OF_TOTAL,
            compilation_status=CompilationStatus.WARNING,
            ambiguities=[_amb("high", "Second OR branch (energy settlement) UNRESOLVED")],
            warnings=["non_dollar_energy_settlement_volume field not in briefing"],
        ),
    ]

    return make_artifact(
        "monetary_architecture",
        PhaseModel.SINGLE_PHASE,
        [make_phase("single", "Active", indicators)],
        notes=[
            "Structurally hardest theory to compile — most external-data-dependent",
            "Nearly all indicators require time-series or missing fields",
            "Legacy score of 0.662 achieved via fragile number extraction from prose",
        ],
    )


# ---------------------------------------------------------------------------
# Master compilation function
# ---------------------------------------------------------------------------

ALL_THEORY_BUILDERS = {
    "valuation_mean_reversion": _build_valuation_mean_reversion,
    "debt_cycle_short": _build_debt_cycle_short,
    "debt_cycle_long": _build_debt_cycle_long,
    "structural_fragility": _build_structural_fragility,
    "fiscal_dominance_arithmetic": _build_fiscal_dominance_arithmetic,
    "fiscal_dominance_liquidity": _build_fiscal_dominance_liquidity,
    "capital_flows": _build_capital_flows,
    "monetary_architecture": _build_monetary_architecture,
}


def compile_all_theories() -> dict[str, CompiledActivationArtifact]:
    """Build compiled artifacts for all 8 theories."""
    return {tid: builder() for tid, builder in ALL_THEORY_BUILDERS.items()}


def save_all_artifacts(
    artifacts: dict[str, CompiledActivationArtifact] = None,
) -> list[str]:
    """Build and save all artifacts to disk. Returns list of saved paths."""
    if artifacts is None:
        artifacts = compile_all_theories()
    paths = []
    for theory_id, artifact in artifacts.items():
        path = save_artifact(artifact)
        paths.append(str(path))
    return paths
