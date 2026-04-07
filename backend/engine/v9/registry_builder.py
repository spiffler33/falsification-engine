"""v9 Phase 1: Full field registry builder.

Populates the FieldRegistry from the actual data layer:
  - FRED-backed fields (from data_agent.FRED_SERIES)
  - Yahoo-backed ticker fields (^VIX, DX-Y.NYB)
  - Computed fields (from data_agent._compute_metrics)
  - Web-sourced fields (from web_data_agent)

Every field the v9 compiler can reference must be registered here.
Unknown field references are compilation errors, not runtime surprises.

Design decisions:
  - Units reflect what is STORED in the briefing packet, not what
    the upstream source (FRED, Yahoo) delivers before transformation.
  - Semantic types enable cross-field comparison legality checks.
  - Computed fields declare their dependencies so the validator can
    trace upstream availability.
  - Ticker fields use the briefing resolution path (^VIX resolves
    via BriefingPacket.get_field() -> markets['^VIX'].price).
"""
from __future__ import annotations

from backend.schemas.v9.field_registry import (
    AllowedOperators,
    DataFrequency,
    FieldEntry,
    FieldKind,
    FieldRegistry,
    FieldSource,
)
from backend.schemas.v9.units import SemanticType, ValueUnit


def build_full_registry() -> FieldRegistry:
    """Build the complete Phase 1 field registry from the data layer.

    Returns a FieldRegistry with every field that the briefing packet
    can produce, annotated with unit, semantic type, source, and
    dependency metadata.
    """
    registry = FieldRegistry()

    for entry in _ALL_FIELDS:
        registry.register(entry)

    return registry


# ---------------------------------------------------------------------------
# FRED-backed fields
# ---------------------------------------------------------------------------
# These are populated by data_agent.py from FRED API.
# Units reflect the value AFTER the FRED transform is applied.

_FRED_FIELDS: list[FieldEntry] = [
    # ---- Growth ----
    FieldEntry(
        field_id="growth.gdp_latest",
        display_name="GDP (nominal, latest)",
        description="Nominal GDP level in billions of dollars (FRED GDP)",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.LEVEL,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="growth.real_gdp",
        display_name="Real GDP Growth Rate",
        description="Real GDP quarter-over-quarter annualized growth rate (FRED GDPC1)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.GROWTH_RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="growth.unemployment",
        display_name="Unemployment Rate",
        description="Civilian unemployment rate (FRED UNRATE)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="growth.initial_claims",
        display_name="Initial Jobless Claims",
        description="Weekly initial unemployment claims, raw count (FRED ICSA)",
        kind=FieldKind.SERIES,
        unit=ValueUnit.COUNT,
        semantic_type=SemanticType.COUNT,
        source=FieldSource.FRED,
        frequency=DataFrequency.WEEKLY,
    ),
    FieldEntry(
        field_id="growth.ism_proxy",
        display_name="ISM Manufacturing PMI (proxy)",
        description="ISM proxy derived from MANEMP manufacturing employment (FRED MANEMP)",
        unit=ValueUnit.INDEX_POINTS,
        semantic_type=SemanticType.INDEX,
        source=FieldSource.FRED,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="growth.nonfarm_payrolls",
        display_name="Nonfarm Payrolls (MoM change)",
        description="Month-over-month change in nonfarm payrolls, thousands (FRED PAYEMS)",
        unit=ValueUnit.THOUSANDS,
        semantic_type=SemanticType.COUNT,
        source=FieldSource.FRED,
        frequency=DataFrequency.MONTHLY,
    ),

    # ---- Inflation ----
    FieldEntry(
        field_id="inflation.cpi_yoy",
        display_name="CPI Year-over-Year",
        description="Consumer Price Index year-over-year percent change (FRED CPIAUCSL)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.GROWTH_RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="inflation.core_pce",
        display_name="Core PCE Year-over-Year",
        description="Core PCE price index year-over-year percent change (FRED PCEPILFE)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.GROWTH_RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="inflation.breakeven_5y",
        display_name="5-Year Breakeven Inflation",
        description="5-year breakeven inflation rate (FRED T5YIE)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="inflation.breakeven_10y",
        display_name="10-Year Breakeven Inflation",
        description="10-year breakeven inflation rate (FRED T10YIE)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),

    # ---- Rates ----
    FieldEntry(
        field_id="rates.fed_funds",
        display_name="Federal Funds Rate",
        description="Effective federal funds rate (FRED FEDFUNDS)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="rates.treasury_2y",
        display_name="2-Year Treasury Yield",
        description="2-year Treasury constant maturity rate (FRED DGS2)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="rates.treasury_10y",
        display_name="10-Year Treasury Yield",
        description="10-year Treasury constant maturity rate (FRED DGS10)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="rates.treasury_30y",
        display_name="30-Year Treasury Yield",
        description="30-year Treasury constant maturity rate (FRED DGS30)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="rates.treasury_3m",
        display_name="3-Month Treasury Yield",
        description="3-month Treasury constant maturity rate (FRED DGS3MO)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),

    # ---- Liquidity ----
    FieldEntry(
        field_id="liquidity.fed_balance_sheet",
        display_name="Fed Balance Sheet",
        description="Federal Reserve total assets in millions (FRED WALCL)",
        kind=FieldKind.SERIES,
        unit=ValueUnit.USD_MILLIONS,
        semantic_type=SemanticType.BALANCE,
        source=FieldSource.FRED,
        frequency=DataFrequency.WEEKLY,
    ),
    FieldEntry(
        field_id="liquidity.tga",
        display_name="Treasury General Account",
        description="Treasury General Account balance in millions (FRED WTREGEN)",
        kind=FieldKind.SERIES,
        unit=ValueUnit.USD_MILLIONS,
        semantic_type=SemanticType.BALANCE,
        source=FieldSource.FRED,
        frequency=DataFrequency.WEEKLY,
    ),
    FieldEntry(
        field_id="liquidity.reverse_repo",
        display_name="Overnight Reverse Repo",
        description="ON RRP facility balance in millions (FRED RRPONTSYD, converted from billions)",
        kind=FieldKind.SERIES,
        unit=ValueUnit.USD_MILLIONS,
        semantic_type=SemanticType.BALANCE,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="liquidity.m2",
        display_name="M2 Money Supply",
        description="M2 money supply in billions (FRED M2SL)",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.BALANCE,
        source=FieldSource.FRED,
        frequency=DataFrequency.MONTHLY,
    ),

    # ---- Credit ----
    FieldEntry(
        field_id="credit.hy_spread",
        display_name="High-Yield Credit Spread",
        description="ICE BofA HY OAS spread in basis points (FRED BAMLH0A0HYM2, pct_to_bps)",
        kind=FieldKind.SERIES,
        unit=ValueUnit.BASIS_POINTS,
        semantic_type=SemanticType.SPREAD,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="credit.ig_spread",
        display_name="Investment-Grade Credit Spread",
        description="ICE BofA IG OAS spread in basis points (FRED BAMLC0A0CM, pct_to_bps)",
        kind=FieldKind.SERIES,
        unit=ValueUnit.BASIS_POINTS,
        semantic_type=SemanticType.SPREAD,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="credit.sloos_tightening_ci",
        display_name="SLOOS C&I Tightening",
        description="Net % of banks tightening C&I lending standards (FRED DRTSCLCC)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.INDEX,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),

    # ---- Sentiment ----
    FieldEntry(
        field_id="sentiment.consumer_sentiment",
        display_name="UMich Consumer Sentiment",
        description="University of Michigan Consumer Sentiment Index (FRED UMCSENT)",
        unit=ValueUnit.INDEX_POINTS,
        semantic_type=SemanticType.INDEX,
        source=FieldSource.FRED,
        frequency=DataFrequency.MONTHLY,
    ),
]


# ---------------------------------------------------------------------------
# FRED-computed intermediate fields
# ---------------------------------------------------------------------------
# These come from FRED but are used as inputs to derived computed metrics.
# Stored in briefing under computed_fred.* prefix (available via get_field fallback).

_FRED_COMPUTED_FIELDS: list[FieldEntry] = [
    FieldEntry(
        field_id="computed_fred.federal_debt_to_gdp",
        display_name="Federal Debt to GDP",
        description="Federal debt as % of GDP (FRED GFDEGDQ188S)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="computed_fred.total_credit_debt",
        display_name="Total Credit Market Debt",
        description="Total credit market debt by domestic nonfinancial sectors, $B (FRED TCMDODNS)",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.LEVEL,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="computed_fred.total_public_debt",
        display_name="Total Public Debt Outstanding",
        description="Total public debt outstanding, $M (FRED GFDEBTN)",
        unit=ValueUnit.USD_MILLIONS,
        semantic_type=SemanticType.LEVEL,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="computed_fred.foreign_treasury_holdings",
        display_name="Foreign Holdings of US Treasuries",
        description="Foreign holdings of US Treasury securities, $B (FRED FDHBFIN)",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.LEVEL,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="computed_fred.federal_interest_payments",
        display_name="Federal Interest Payments",
        description="Federal government interest payments annualized rate, $B (FRED A091RC1Q027SBEA)",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.FLOW,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="computed_fred.federal_tax_receipts",
        display_name="Federal Tax Receipts",
        description="Federal government current tax receipts annualized rate, $B (FRED W006RC1Q027SBEA)",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.FLOW,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="computed_fred.corporate_profits",
        display_name="Corporate Profits After Tax",
        description="Corporate profits after tax, $B (FRED CP)",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.LEVEL,
        source=FieldSource.FRED,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="computed_fred.wilshire_5000",
        display_name="Wilshire 5000 Index",
        description="Wilshire 5000 Full Cap Price Index (FRED WILL5000INDFC)",
        unit=ValueUnit.INDEX_POINTS,
        semantic_type=SemanticType.INDEX,
        source=FieldSource.FRED,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="computed_fred.monthly_treasury_deficit",
        display_name="Monthly Treasury Deficit",
        description="Monthly Treasury statement deficit, $M (FRED MTSDS133FMS, negative=deficit)",
        unit=ValueUnit.USD_MILLIONS,
        semantic_type=SemanticType.FLOW,
        source=FieldSource.FRED,
        frequency=DataFrequency.MONTHLY,
    ),
]


# ---------------------------------------------------------------------------
# Computed fields (derived in data_agent._compute_metrics)
# ---------------------------------------------------------------------------
# These are derived from FRED + Yahoo data.
# Stored in briefing.computed dict, accessed via get_field().

_COMPUTED_FIELDS: list[FieldEntry] = [
    # ---- Yield curves (stored in rates section) ----
    FieldEntry(
        field_id="rates.curve_2s10s",
        display_name="2s10s Yield Curve Spread",
        description="10Y minus 2Y Treasury yield",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SPREAD,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        dependencies=["rates.treasury_2y", "rates.treasury_10y"],
        computation_description="treasury_10y - treasury_2y",
    ),
    FieldEntry(
        field_id="rates.curve_3m10y",
        display_name="3m10y Yield Curve Spread",
        description="10Y minus 3M Treasury yield",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SPREAD,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        dependencies=["rates.treasury_3m", "rates.treasury_10y"],
        computation_description="treasury_10y - treasury_3m",
    ),

    # ---- Valuation ----
    FieldEntry(
        field_id="equity_risk_premium",
        display_name="Equity Risk Premium",
        description="S&P 500 earnings yield minus 10Y Treasury yield",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SPREAD,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        dependencies=["computed_fred.corporate_profits", "computed_fred.wilshire_5000",
                       "rates.treasury_10y"],
        computation_description="(CP/Wilshire5000 earnings yield) - 10Y yield",
    ),
    FieldEntry(
        field_id="cash_exceeds_equity_yield",
        display_name="Cash vs Equity Yield",
        description="Fed funds rate minus S&P 500 earnings yield; positive = cash pays more",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SPREAD,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        dependencies=["rates.fed_funds", "equity_risk_premium", "rates.treasury_10y"],
        computation_description="fed_funds - (ERP + 10Y)",
    ),
    FieldEntry(
        field_id="buffett_indicator",
        display_name="Buffett Indicator",
        description="Total US market cap / GDP ratio",
        unit=ValueUnit.RATIO,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        dependencies=["computed_fred.wilshire_5000", "growth.gdp_latest"],
        computation_description="(Wilshire5000/900) / (GDP/1000)",
    ),
    FieldEntry(
        field_id="corporate_profits_gdp_ratio",
        display_name="Corporate Profits / GDP",
        description="After-tax corporate profits as % of GDP",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.QUARTERLY,
        is_computed=True,
        dependencies=["computed_fred.corporate_profits", "growth.gdp_latest"],
        computation_description="(CP / GDP) * 100",
    ),

    # ---- Rates/real ----
    FieldEntry(
        field_id="real_10y",
        display_name="Real 10-Year Yield",
        description="10Y nominal minus 10Y breakeven inflation",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        dependencies=["rates.treasury_10y", "inflation.breakeven_10y"],
    ),
    FieldEntry(
        field_id="real_fed_funds_rate",
        display_name="Real Federal Funds Rate",
        description="Fed funds minus CPI YoY",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        dependencies=["rates.fed_funds", "inflation.cpi_yoy"],
        computation_description="fed_funds - CPI YoY",
    ),
    FieldEntry(
        field_id="real_fed_funds",
        display_name="Real Federal Funds Rate (alias)",
        description="Alias for real_fed_funds_rate",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        dependencies=["rates.fed_funds", "inflation.cpi_yoy"],
        briefing_path="real_fed_funds",
    ),

    # ---- Liquidity ----
    FieldEntry(
        field_id="net_liquidity",
        display_name="Net Liquidity",
        description="Fed BS - TGA - RRP, in millions",
        kind=FieldKind.SERIES,
        unit=ValueUnit.USD_MILLIONS,
        semantic_type=SemanticType.BALANCE,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.WEEKLY,
        is_computed=True,
        dependencies=["liquidity.fed_balance_sheet", "liquidity.tga", "liquidity.reverse_repo"],
    ),
    FieldEntry(
        field_id="net_liquidity_30d_change",
        display_name="Net Liquidity 30d Change",
        description="30-day change in net liquidity, in millions",
        unit=ValueUnit.USD_MILLIONS,
        semantic_type=SemanticType.FLOW,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.MONTHLY,
        is_computed=True,
        dependencies=["net_liquidity"],
    ),
    FieldEntry(
        field_id="dxy_index",
        display_name="DXY Dollar Index",
        description="DX-Y.NYB exposed as computed field",
        unit=ValueUnit.INDEX_POINTS,
        semantic_type=SemanticType.INDEX,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),

    # ---- Commodity ----
    FieldEntry(
        field_id="gold_oil_ratio",
        display_name="Gold/Oil Price Ratio",
        description="Gold futures / Oil futures (GC=F / CL=F)",
        unit=ValueUnit.RATIO,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),
    FieldEntry(
        field_id="commodity_index_3m_change",
        display_name="Commodity Index 3M Change",
        description="DBC ETF 3-month return",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RETURN,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),

    # ---- Equity metrics ----
    FieldEntry(
        field_id="qqq_iwm_ratio",
        display_name="QQQ/IWM Ratio",
        description="Large-cap/small-cap concentration proxy (QQQ price / IWM price)",
        unit=ValueUnit.RATIO,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),
    FieldEntry(
        field_id="vix_vs_realized",
        display_name="VIX vs Realized Vol Gap",
        description="VIX price minus 20-day realized SPY vol",
        unit=ValueUnit.INDEX_POINTS,
        semantic_type=SemanticType.VOLATILITY,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),
    FieldEntry(
        field_id="spy_drawdown_from_52w_high",
        display_name="SPY Drawdown from 52-Week High",
        description="Current SPY drawdown from 52-week high (negative %)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RETURN,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),
    FieldEntry(
        field_id="top_10_sp500_weight",
        display_name="Top 10 S&P 500 Weight",
        description="Weight of top 10 stocks in S&P 500 (placeholder, no data source wired)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SHARE_OF_TOTAL,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        is_mechanical=False,
    ),
    FieldEntry(
        field_id="hard_vs_nominal_12m",
        display_name="Hard Assets vs Nominal Bonds 12M",
        description="Avg 12M return of hard assets (GLD,SLV,DBC) minus bonds (TLT,IEF,AGG)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RELATIVE_PERFORMANCE,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),

    # ---- EM/International relatives ----
    FieldEntry(
        field_id="em_us_relative_3m",
        display_name="EM vs US 3-Month Relative",
        description="EEM 3M return minus SPY 3M return",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RELATIVE_PERFORMANCE,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),
    FieldEntry(
        field_id="eem_spy_3m_relative",
        display_name="EEM/SPY 3M Relative (alias)",
        description="Alias for em_us_relative_3m",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RELATIVE_PERFORMANCE,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        briefing_path="eem_spy_3m_relative",
    ),
    FieldEntry(
        field_id="em_us_relative_12m",
        display_name="EM vs US 12-Month Relative",
        description="EEM 12M return minus SPY 12M return",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RELATIVE_PERFORMANCE,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),
    FieldEntry(
        field_id="eem_spy_3y_relative",
        display_name="EEM/SPY 3-Year Relative",
        description=(
            "EEM vs SPY 3-year cumulative relative return. "
            "APPROXIMATED with 12-month data (data infrastructure limitation). "
            "Negative = EM underperformance. "
            "Investigation (v9 Phase 1): sign convention is correct. "
            "Legacy mismatch was a threshold extraction bug (regex loses sign)."
        ),
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RELATIVE_PERFORMANCE,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
        dependencies=["em_us_relative_12m"],
        computation_description="Proxy: em_us_relative_12m (12M standing in for 3Y)",
    ),
    FieldEntry(
        field_id="fxi_3m_return",
        display_name="FXI 3-Month Return",
        description="iShares China Large-Cap ETF 3-month return",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RETURN,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),
    FieldEntry(
        field_id="kweb_3m_return",
        display_name="KWEB 3-Month Return",
        description="KraneShares China Internet ETF 3-month return",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RETURN,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.DAILY,
        is_computed=True,
    ),

    # ---- Fiscal / Debt computed ----
    FieldEntry(
        field_id="interest_receipts_ratio",
        display_name="Interest/Receipts Ratio",
        description="Federal interest payments as % of tax receipts",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.QUARTERLY,
        is_computed=True,
        dependencies=["computed_fred.federal_interest_payments",
                       "computed_fred.federal_tax_receipts"],
    ),
    FieldEntry(
        field_id="interest_exceeds_defense",
        display_name="Interest Exceeds Defense",
        description="Interest payments minus ~$940B defense estimate; positive = exceeds",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.FLOW,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.QUARTERLY,
        is_computed=True,
        is_mechanical=False,  # depends on hardcoded defense estimate
        dependencies=["computed_fred.federal_interest_payments"],
    ),
    FieldEntry(
        field_id="fed_bs_gdp_ratio",
        display_name="Fed Balance Sheet / GDP",
        description="Fed balance sheet as % of GDP",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.QUARTERLY,
        is_computed=True,
        dependencies=["liquidity.fed_balance_sheet", "growth.gdp_latest"],
    ),
    FieldEntry(
        field_id="federal_debt_to_gdp",
        display_name="Federal Debt to GDP (computed)",
        description="Passthrough of FRED GFDEGDQ188S (federal debt as % of GDP)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.QUARTERLY,
        is_computed=True,
        dependencies=["computed_fred.federal_debt_to_gdp"],
    ),
    FieldEntry(
        field_id="sloos_net_tightening",
        display_name="SLOOS Net Tightening (computed)",
        description="Passthrough of FRED DRTSCLCC SLOOS C&I tightening",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.INDEX,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.QUARTERLY,
        is_computed=True,
        dependencies=["credit.sloos_tightening_ci"],
    ),
    FieldEntry(
        field_id="deficit_pace_annualized",
        display_name="Annualized Fiscal Deficit Pace",
        description="Monthly treasury deficit annualized, $B",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.FLOW,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.MONTHLY,
        is_computed=True,
        dependencies=["computed_fred.monthly_treasury_deficit"],
    ),
    FieldEntry(
        field_id="foreign_treasury_holdings_pct",
        display_name="Foreign Treasury Holdings %",
        description="Foreign holdings as % of total public debt outstanding",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SHARE_OF_TOTAL,
        source=FieldSource.COMPUTED,
        frequency=DataFrequency.QUARTERLY,
        is_computed=True,
        dependencies=["computed_fred.foreign_treasury_holdings",
                       "computed_fred.total_public_debt"],
    ),
]


# ---------------------------------------------------------------------------
# Ticker/market fields
# ---------------------------------------------------------------------------
# Resolved via BriefingPacket.get_field('^VIX') -> markets['^VIX'].price

_TICKER_FIELDS: list[FieldEntry] = [
    FieldEntry(
        field_id="^VIX",
        display_name="VIX Index",
        description="CBOE Volatility Index (Yahoo ^VIX)",
        unit=ValueUnit.INDEX_POINTS,
        semantic_type=SemanticType.VOLATILITY,
        source=FieldSource.YAHOO,
        frequency=DataFrequency.DAILY,
        briefing_path="^VIX",
    ),
    FieldEntry(
        field_id="DX-Y.NYB",
        display_name="DXY Dollar Index (ticker)",
        description="ICE US Dollar Index (Yahoo DX-Y.NYB)",
        unit=ValueUnit.INDEX_POINTS,
        semantic_type=SemanticType.INDEX,
        source=FieldSource.YAHOO,
        frequency=DataFrequency.DAILY,
        briefing_path="DX-Y.NYB",
    ),
]


# ---------------------------------------------------------------------------
# Web-sourced fields (from web_data_agent.py)
# ---------------------------------------------------------------------------
# Populated by web scraping, stored in briefing.web_sourced dict.

_WEB_FIELDS: list[FieldEntry] = [
    FieldEntry(
        field_id="shiller_cape",
        display_name="Shiller CAPE Ratio",
        description="Cyclically adjusted price-to-earnings ratio (multpl.com)",
        unit=ValueUnit.RATIO,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.WEB,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="ism_pmi",
        display_name="ISM Manufacturing PMI",
        description="Actual ISM PMI (replaces MANEMP proxy when available)",
        unit=ValueUnit.INDEX_POINTS,
        semantic_type=SemanticType.INDEX,
        source=FieldSource.WEB,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="sp500_net_margin",
        display_name="S&P 500 Net Profit Margin",
        description="S&P 500 net profit margin %",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.WEB,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="insider_sell_buy_ratio",
        display_name="Insider Sell/Buy Ratio",
        description="Insider selling / buying ratio (openinsider)",
        unit=ValueUnit.RATIO,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.WEB,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="consumer_confidence",
        display_name="Conference Board Consumer Confidence",
        description="Conference Board Consumer Confidence Index",
        unit=ValueUnit.INDEX_POINTS,
        semantic_type=SemanticType.INDEX,
        source=FieldSource.WEB,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="total_debt_to_gdp",
        display_name="Total Debt to GDP",
        description="All-sector total debt as % of GDP (BIS/Z.1)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.WEB,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="top10_wealth_share",
        display_name="Top 10% Wealth Share",
        description="Top 10% household wealth share (DFA)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SHARE_OF_TOTAL,
        source=FieldSource.WEB,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="deficit_pct_gdp",
        display_name="Deficit as % of GDP",
        description="Federal deficit as percentage of GDP",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATIO,
        source=FieldSource.WEB,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="finra_margin_debt",
        display_name="FINRA Margin Debt",
        description="FINRA margin debt balance, $B",
        unit=ValueUnit.USD_BILLIONS,
        semantic_type=SemanticType.LEVEL,
        source=FieldSource.WEB,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="passive_fund_share",
        display_name="Passive Fund Share",
        description="Passive fund share of US equity market %",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SHARE_OF_TOTAL,
        source=FieldSource.WEB,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="weighted_avg_interest_rate",
        display_name="Weighted Average Interest Rate",
        description="Weighted average interest rate on outstanding US federal debt",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.RATE,
        source=FieldSource.WEB,
        frequency=DataFrequency.QUARTERLY,
    ),
    FieldEntry(
        field_id="cb_gold_purchases",
        display_name="Central Bank Gold Purchases",
        description="Annual central bank gold purchases in metric tons (WGC)",
        unit=ValueUnit.TONS,
        semantic_type=SemanticType.FLOW,
        source=FieldSource.WEB,
        frequency=DataFrequency.ANNUAL,
    ),
    FieldEntry(
        field_id="em_dm_pe_gap",
        display_name="EM vs DM PE Gap",
        description="EM PE discount relative to DM (MSCI EM PE / MSCI World PE - 1) * 100",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SPREAD,
        source=FieldSource.WEB,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="china_credit_impulse",
        display_name="China Credit Impulse",
        description="China total social financing credit impulse (% of GDP change)",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.FLOW,
        source=FieldSource.WEB,
        frequency=DataFrequency.MONTHLY,
    ),
    FieldEntry(
        field_id="usdcny",
        display_name="USD/CNY Exchange Rate",
        description="USD/CNY spot exchange rate",
        unit=ValueUnit.RATIO,
        semantic_type=SemanticType.PRICE,
        source=FieldSource.WEB,
        frequency=DataFrequency.DAILY,
    ),
    FieldEntry(
        field_id="rmb_swift_share",
        display_name="RMB SWIFT Share",
        description="RMB share of SWIFT global payments %",
        unit=ValueUnit.PERCENT,
        semantic_type=SemanticType.SHARE_OF_TOTAL,
        source=FieldSource.WEB,
        frequency=DataFrequency.MONTHLY,
    ),
]


# ---------------------------------------------------------------------------
# Combined field list
# ---------------------------------------------------------------------------

_ALL_FIELDS: list[FieldEntry] = (
    _FRED_FIELDS
    + _FRED_COMPUTED_FIELDS
    + _COMPUTED_FIELDS
    + _TICKER_FIELDS
    + _WEB_FIELDS
)
