"""Field-to-source mapping for time-series data.

Maps each field_id that temporal indicators reference to its upstream
data source: FRED series ID, Yahoo Finance ticker, or derivation recipe.

This mapping is consumed by the series loader to fetch historical data
and populate InMemorySeriesStore. The data_agent.py FRED_SERIES dict
maps FRED IDs to briefing field paths; this module maps field_ids to
the FRED IDs (and Yahoo tickers) needed for historical series.

Categories:
  - fred_direct: FRED series, applied directly (level or simple transform)
  - fred_transformed: FRED series needing a per-observation transform
  - yahoo_price: single Yahoo ticker close price
  - yahoo_ratio: ratio of two Yahoo tickers
  - computed_from_fred: derived from multiple FRED series
  - web_sourced: from web scraping / APIs (no historical series available)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SourceType(str, Enum):
    FRED_DIRECT = "fred_direct"
    FRED_TRANSFORMED = "fred_transformed"
    YAHOO_PRICE = "yahoo_price"
    YAHOO_RATIO = "yahoo_ratio"
    COMPUTED_FROM_FRED = "computed_from_fred"
    COMPUTED_FROM_YAHOO = "computed_from_yahoo"
    COMPUTED_MIXED = "computed_mixed"
    WEB_SOURCED = "web_sourced"


@dataclass
class FieldSource:
    """How to get historical series for one field_id."""
    field_id: str
    source_type: SourceType
    fred_series: Optional[str] = None        # FRED series ID (e.g., "UNRATE")
    fred_transform: str = "level"            # transform to apply per observation
    yahoo_tickers: list[str] = field(default_factory=list)  # Yahoo ticker(s)
    derivation: str = ""                     # human-readable derivation formula
    upstream_fields: list[str] = field(default_factory=list)  # field_ids this derives from
    lookback_years: int = 3                  # how many years of history to fetch
    note: str = ""                           # flags for human decision


# ---------------------------------------------------------------------------
# The 26 field_ids needed by temporal indicators
# ---------------------------------------------------------------------------

FIELD_SOURCES: dict[str, FieldSource] = {

    # ===== FRED DIRECT (level transform — store as-is) =====

    "growth.unemployment": FieldSource(
        field_id="growth.unemployment",
        source_type=SourceType.FRED_DIRECT,
        fred_series="UNRATE",
        fred_transform="level",
        lookback_years=3,
    ),
    "rates.fed_funds": FieldSource(
        field_id="rates.fed_funds",
        source_type=SourceType.FRED_DIRECT,
        fred_series="FEDFUNDS",
        fred_transform="level",
        lookback_years=12,  # ELB check needs 10 years
    ),
    "growth.initial_claims": FieldSource(
        field_id="growth.initial_claims",
        source_type=SourceType.FRED_DIRECT,
        fred_series="ICSA",
        fred_transform="level",
        lookback_years=3,
    ),
    "sentiment.consumer_sentiment": FieldSource(
        field_id="sentiment.consumer_sentiment",
        source_type=SourceType.FRED_DIRECT,
        fred_series="UMCSENT",
        fred_transform="level",
        lookback_years=3,
    ),
    "credit.sloos_tightening_ci": FieldSource(
        field_id="credit.sloos_tightening_ci",
        source_type=SourceType.FRED_DIRECT,
        fred_series="DRTSCLCC",
        fred_transform="level",
        lookback_years=3,
    ),

    # ===== FRED TRANSFORMED (need per-observation transform) =====

    "credit.hy_spread": FieldSource(
        field_id="credit.hy_spread",
        source_type=SourceType.FRED_TRANSFORMED,
        fred_series="BAMLH0A0HYM2",
        fred_transform="pct_to_bps",  # FRED reports in pct points, we store in bps
        lookback_years=3,
    ),
    "growth.ism_proxy": FieldSource(
        field_id="growth.ism_proxy",
        source_type=SourceType.FRED_TRANSFORMED,
        fred_series="MANEMP",
        fred_transform="ism_from_employment",
        lookback_years=3,
    ),

    # ===== FRED DIRECT — liquidity series =====

    "liquidity.fed_balance_sheet": FieldSource(
        field_id="liquidity.fed_balance_sheet",
        source_type=SourceType.FRED_DIRECT,
        fred_series="WALCL",
        fred_transform="millions",  # already in millions
        lookback_years=3,
    ),
    "liquidity.reverse_repo": FieldSource(
        field_id="liquidity.reverse_repo",
        source_type=SourceType.FRED_DIRECT,
        fred_series="RRPONTSYD",
        fred_transform="billions_to_millions",
        lookback_years=3,
    ),
    "liquidity.tga": FieldSource(
        field_id="liquidity.tga",
        source_type=SourceType.FRED_DIRECT,
        fred_series="WTREGEN",
        fred_transform="millions",
        lookback_years=3,
    ),

    # ===== YAHOO PRICE (single ticker close) =====

    "dxy_index": FieldSource(
        field_id="dxy_index",
        source_type=SourceType.YAHOO_PRICE,
        yahoo_tickers=["DX-Y.NYB"],
        lookback_years=3,
    ),
    "usdcny": FieldSource(
        field_id="usdcny",
        source_type=SourceType.YAHOO_PRICE,
        yahoo_tickers=["CNYUSD=X"],
        lookback_years=3,
        note="CNYUSD=X gives CNY per USD. Inverted from Yahoo convention.",
    ),

    # ===== YAHOO RATIO (price_a / price_b) =====

    "qqq_iwm_ratio": FieldSource(
        field_id="qqq_iwm_ratio",
        source_type=SourceType.YAHOO_RATIO,
        yahoo_tickers=["QQQ", "IWM"],
        derivation="QQQ.close / IWM.close",
        lookback_years=3,
    ),
    "gold_oil_ratio": FieldSource(
        field_id="gold_oil_ratio",
        source_type=SourceType.YAHOO_RATIO,
        yahoo_tickers=["GC=F", "CL=F"],
        derivation="GC=F.close / CL=F.close",
        lookback_years=3,
    ),

    # ===== COMPUTED FROM YAHOO (returns, relative performance) =====

    "eem_spy_3m_relative": FieldSource(
        field_id="eem_spy_3m_relative",
        source_type=SourceType.COMPUTED_FROM_YAHOO,
        yahoo_tickers=["EEM", "SPY"],
        derivation="rolling_3m_return(EEM) - rolling_3m_return(SPY)",
        lookback_years=3,
    ),
    "commodity_index_3m_change": FieldSource(
        field_id="commodity_index_3m_change",
        source_type=SourceType.COMPUTED_FROM_YAHOO,
        yahoo_tickers=["DBC"],
        derivation="rolling_3m_pct_change(DBC)",
        lookback_years=3,
    ),

    # ===== COMPUTED FROM FRED (multi-series derivations) =====

    "rates.curve_2s10s": FieldSource(
        field_id="rates.curve_2s10s",
        source_type=SourceType.COMPUTED_FROM_FRED,
        upstream_fields=["rates.treasury_10y", "rates.treasury_2y"],
        derivation="DGS10 - DGS2",
        lookback_years=3,
    ),
    "net_liquidity_30d_change": FieldSource(
        field_id="net_liquidity_30d_change",
        source_type=SourceType.COMPUTED_FROM_FRED,
        upstream_fields=["liquidity.fed_balance_sheet", "liquidity.tga", "liquidity.reverse_repo"],
        derivation="30d_change(WALCL - WTREGEN - RRPONTSYD)",
        lookback_years=3,
    ),
    "foreign_treasury_holdings_pct": FieldSource(
        field_id="foreign_treasury_holdings_pct",
        source_type=SourceType.COMPUTED_FROM_FRED,
        fred_series=None,
        upstream_fields=["computed_fred.foreign_treasury_holdings", "computed_fred.total_public_debt"],
        derivation="(FDHBFIN / (GFDEBTN / 1000)) * 100",
        lookback_years=5,
    ),
    "sloos_net_tightening": FieldSource(
        field_id="sloos_net_tightening",
        source_type=SourceType.COMPUTED_FROM_FRED,
        upstream_fields=["credit.sloos_tightening_ci"],
        derivation="passthrough from DRTSCLCC",
        lookback_years=3,
    ),

    # ===== WEB SOURCED (no reliable historical series API) =====

    "cb_gold_purchases": FieldSource(
        field_id="cb_gold_purchases",
        source_type=SourceType.WEB_SOURCED,
        lookback_years=5,
        note="Annual data from WGC Goldhub. No API for historical series. "
             "Hardcode known annual values: 2022=1082, 2023=1037, 2024=1045, 2025=TBD.",
    ),
    "china_credit_impulse": FieldSource(
        field_id="china_credit_impulse",
        source_type=SourceType.FRED_DIRECT,
        fred_series="QCNPAM770A",
        fred_transform="level",
        lookback_years=3,
        note="FRED series QCNPAM770A — may be discontinued or laggy.",
    ),
    "finra_margin_debt": FieldSource(
        field_id="finra_margin_debt",
        source_type=SourceType.WEB_SOURCED,
        lookback_years=5,
        note="FINRA Excel download. Historical monthly data available but requires "
             "scraping. Flag for manual CSV import.",
    ),
    "insider_sell_buy_ratio": FieldSource(
        field_id="insider_sell_buy_ratio",
        source_type=SourceType.WEB_SOURCED,
        lookback_years=3,
        note="openinsider.com scraping. No historical series API. "
             "Flag for manual CSV import or accept NOT_EVALUABLE.",
    ),
    "rmb_swift_share": FieldSource(
        field_id="rmb_swift_share",
        source_type=SourceType.WEB_SOURCED,
        lookback_years=3,
        note="SWIFT.com monthly reports. No API. "
             "Low priority — used by scalar comparison, not temporal.",
    ),
    "weighted_avg_interest_rate": FieldSource(
        field_id="weighted_avg_interest_rate",
        source_type=SourceType.WEB_SOURCED,
        lookback_years=3,
        note="Treasury Fiscal Data API. Quarterly. Could be fetched via HTTP but "
             "need to build custom parser. Flag for later.",
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_fred_fields() -> list[FieldSource]:
    """All fields that need FRED API fetches."""
    return [
        fs for fs in FIELD_SOURCES.values()
        if fs.source_type in (SourceType.FRED_DIRECT, SourceType.FRED_TRANSFORMED)
    ]


def get_yahoo_fields() -> list[FieldSource]:
    """All fields that need Yahoo Finance fetches."""
    return [
        fs for fs in FIELD_SOURCES.values()
        if fs.source_type in (SourceType.YAHOO_PRICE, SourceType.YAHOO_RATIO,
                              SourceType.COMPUTED_FROM_YAHOO)
    ]


def get_computed_fields() -> list[FieldSource]:
    """All fields computed from other fetched series."""
    return [
        fs for fs in FIELD_SOURCES.values()
        if fs.source_type in (SourceType.COMPUTED_FROM_FRED, SourceType.COMPUTED_FROM_YAHOO,
                              SourceType.COMPUTED_MIXED)
    ]


def get_web_sourced_fields() -> list[FieldSource]:
    """Fields from web scraping with no reliable historical API."""
    return [
        fs for fs in FIELD_SOURCES.values()
        if fs.source_type == SourceType.WEB_SOURCED
    ]


def get_all_required_fred_series() -> dict[str, int]:
    """All unique FRED series IDs needed, with max lookback years."""
    series: dict[str, int] = {}
    for fs in FIELD_SOURCES.values():
        if fs.fred_series:
            existing = series.get(fs.fred_series, 0)
            series[fs.fred_series] = max(existing, fs.lookback_years)
    # Add upstream FRED series for computed fields
    _UPSTREAM_FRED = {
        "rates.treasury_10y": ("DGS10", 3),
        "rates.treasury_2y": ("DGS2", 3),
        "computed_fred.foreign_treasury_holdings": ("FDHBFIN", 5),
        "computed_fred.total_public_debt": ("GFDEBTN", 5),
    }
    for field_id, (fred_id, years) in _UPSTREAM_FRED.items():
        existing = series.get(fred_id, 0)
        series[fred_id] = max(existing, years)
    return series


def get_all_required_yahoo_tickers() -> set[str]:
    """All unique Yahoo tickers needed."""
    tickers: set[str] = set()
    for fs in FIELD_SOURCES.values():
        tickers.update(fs.yahoo_tickers)
    return tickers
