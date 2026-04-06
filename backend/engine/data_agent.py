# data_agent.py — Phase 2: Data Agent for FRED + Yahoo Finance.
# Depends on: config.py, schemas/briefing.py
# Depended on by: scripts/run_data.py, api/briefing.py
#
# Fetches macro data from FRED API and market data from Yahoo Finance.
# Computes derived metrics. Produces a BriefingPacket.
#
# Design principles:
# - Transform FRED data at fetch time (never downstream)
# - Use direct Yahoo v8 chart API (not yfinance library — gets rate-limited)
# - Cache with staleness tracking
# - All field names must match theory module metric_source references
from __future__ import annotations

import json
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fredapi import Fred

from backend.config import DATA_DIR, MOCK_DATA_DIR, settings
from backend.schemas.briefing import BriefingPacket, MarketData, WebSourcedData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FRED Series Registry
# ---------------------------------------------------------------------------
# Each entry: series_id → (briefing_field_path, transform)
# Transforms applied at fetch time per feedback_fred_transforms.md

FRED_SERIES: dict[str, dict] = {
    # Growth
    "GDP": {
        "field": "growth.gdp_latest",
        "transform": "level",  # GDP in billions, latest value
    },
    "GDPC1": {
        "field": "growth.real_gdp",
        "transform": "pct_change_annualized",  # real GDP growth rate
    },
    "UNRATE": {
        "field": "growth.unemployment",
        "transform": "level",  # already in percent
    },
    "ICSA": {
        "field": "growth.initial_claims",
        "transform": "level",  # weekly claims count (thousands)
    },
    "MANEMP": {
        "field": "growth.ism_proxy",
        "transform": "ism_from_employment",  # manufacturing employment → ISM proxy
    },
    "PAYEMS": {
        "field": "growth.nonfarm_payrolls",
        "transform": "mom_change",  # month-over-month change in thousands
    },
    # Inflation
    "CPIAUCSL": {
        "field": "inflation.cpi_yoy",
        "transform": "yoy_pct",  # CPI index → YoY %
    },
    "PCEPILFE": {
        "field": "inflation.core_pce",
        "transform": "yoy_pct",  # core PCE index → YoY %
    },
    "T5YIE": {
        "field": "inflation.breakeven_5y",
        "transform": "level",  # already in percent
    },
    "T10YIE": {
        "field": "inflation.breakeven_10y",
        "transform": "level",  # already in percent
    },
    # Rates
    "FEDFUNDS": {
        "field": "rates.fed_funds",
        "transform": "level",  # already in percent
    },
    "DGS2": {
        "field": "rates.treasury_2y",
        "transform": "level",  # already in percent
    },
    "DGS10": {
        "field": "rates.treasury_10y",
        "transform": "level",  # already in percent
    },
    "DGS30": {
        "field": "rates.treasury_30y",
        "transform": "level",  # already in percent
    },
    "DGS3MO": {
        "field": "rates.treasury_3m",
        "transform": "level",  # already in percent
    },
    # Liquidity
    "WALCL": {
        "field": "liquidity.fed_balance_sheet",
        "transform": "millions",  # FRED reports in millions
    },
    "WTREGEN": {
        "field": "liquidity.tga",
        "transform": "millions",  # Treasury General Account, in millions
    },
    "RRPONTSYD": {
        "field": "liquidity.reverse_repo",
        "transform": "billions_to_millions",  # ON RRP, FRED in billions
    },
    "M2SL": {
        "field": "liquidity.m2",
        "transform": "level",  # M2 in billions
    },
    # Credit
    "BAMLH0A0HYM2": {
        "field": "credit.hy_spread",
        "transform": "pct_to_bps",  # BAML HY OAS: percentage points → basis points
    },
    "BAMLC0A0CM": {
        "field": "credit.ig_spread",
        "transform": "pct_to_bps",  # BAML IG OAS: percentage points → basis points
    },
    # Credit — SLOOS (Senior Loan Officer Opinion Survey)
    "DRTSCLCC": {
        "field": "credit.sloos_tightening_ci",
        "transform": "level",  # net % of banks tightening C&I lending standards
    },
    # Sentiment
    "UMCSENT": {
        "field": "sentiment.consumer_sentiment",
        "transform": "level",  # University of Michigan Consumer Sentiment Index
    },
    # Fiscal / Debt — used by debt_cycle_long, fiscal_dominance_arithmetic, monetary_architecture
    "GFDEGDQ188S": {
        "field": "computed_fred.federal_debt_to_gdp",
        "transform": "level",  # Federal Debt: Total Public Debt as % of GDP (quarterly)
    },
    "TCMDODNS": {
        "field": "computed_fred.total_credit_debt",
        "transform": "level",  # Total Credit Market Debt by Domestic Nonfinancial Sectors ($B)
    },
    "GFDEBTN": {
        "field": "computed_fred.total_public_debt",
        "transform": "level",  # Total Public Debt Outstanding ($M)
    },
    "FDHBFIN": {
        "field": "computed_fred.foreign_treasury_holdings",
        "transform": "level",  # Foreign Holdings of US Treasury Securities ($B)
    },
    "A091RC1Q027SBEA": {
        "field": "computed_fred.federal_interest_payments",
        "transform": "level",  # Federal Gov Interest Payments, annualized rate ($B)
    },
    "W006RC1Q027SBEA": {
        "field": "computed_fred.federal_tax_receipts",
        "transform": "level",  # Federal Gov Current Tax Receipts, annualized rate ($B)
    },
    "CP": {
        "field": "computed_fred.corporate_profits",
        "transform": "level",  # Corporate Profits After Tax ($B)
    },
    "WILL5000INDFC": {
        "field": "computed_fred.wilshire_5000",
        "transform": "level",  # Wilshire 5000 Full Cap Index (for Buffett Indicator)
    },
    "MTSDS133FMS": {
        "field": "computed_fred.monthly_treasury_deficit",
        "transform": "level",  # Monthly Treasury Statement: deficit ($M, negative = deficit)
    },
}


def _apply_fred_transform(series_data, transform: str) -> Optional[float]:
    """Apply a transform to a FRED pandas Series at fetch time.

    Returns the transformed value, or None if the series is empty.
    """
    if series_data is None or len(series_data) == 0:
        return None

    # Drop NaN values
    series_data = series_data.dropna()
    if len(series_data) == 0:
        return None

    if transform == "level":
        return float(series_data.iloc[-1])

    elif transform == "yoy_pct":
        # Year-over-year percentage change from index
        if len(series_data) < 13:
            return None
        current = float(series_data.iloc[-1])
        year_ago = float(series_data.iloc[-13])  # ~12 months ago
        if year_ago == 0:
            return None
        return round(((current - year_ago) / year_ago) * 100, 2)

    elif transform == "mom_change":
        # Month-over-month change (for payrolls: in thousands)
        if len(series_data) < 2:
            return None
        return round(float(series_data.iloc[-1]) - float(series_data.iloc[-2]), 1)

    elif transform == "pct_change_annualized":
        # Quarter-over-quarter annualized (for GDP)
        if len(series_data) < 2:
            return None
        current = float(series_data.iloc[-1])
        previous = float(series_data.iloc[-2])
        if previous == 0:
            return None
        qoq = (current - previous) / previous
        return round(((1 + qoq) ** 4 - 1) * 100, 2)

    elif transform == "ism_from_employment":
        # Manufacturing employment → ISM proxy
        # MANEMP is in thousands. 3-month change direction maps to expansion/contraction.
        if len(series_data) < 4:
            return None
        current = float(series_data.iloc[-1])
        three_months_ago = float(series_data.iloc[-4])
        # Positive change → above 50, negative → below 50
        # Scale: rough mapping where ±100K jobs ≈ ±10 ISM points
        change = current - three_months_ago
        proxy = 50 + (change / 10)  # 10K jobs per ISM point
        return round(max(30, min(70, proxy)), 1)

    elif transform == "millions":
        # Already in millions from FRED
        return round(float(series_data.iloc[-1]), 0)

    elif transform == "billions_to_millions":
        # FRED reports some series in billions, we want millions
        return round(float(series_data.iloc[-1]) * 1000, 0)

    elif transform == "pct_to_bps":
        # BAML OAS indices: percentage points → basis points
        return round(float(series_data.iloc[-1]) * 100, 0)

    else:
        logger.warning(f"Unknown transform: {transform}")
        return float(series_data.iloc[-1])


# ---------------------------------------------------------------------------
# Yahoo Finance — via curl subprocess
# ---------------------------------------------------------------------------
# Do NOT use yfinance library or Python HTTP libs (httpx/requests).
# Yahoo uses TLS fingerprinting to block programmatic clients.
# Curl uses the system TLS stack which matches real browsers.

YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

# Full ETF universe + special tickers
ETF_UNIVERSE = [
    # US Equity
    "SPY", "QQQ", "IWM", "DIA", "RSP", "MDY",
    # International
    "EFA", "EEM", "FXI", "KWEB", "EWJ", "EWZ", "INDA", "VGK",
    "EWG", "EWU", "EWA", "EWT", "EWY", "EIDO", "THD", "VWO",
    # Bonds
    "TLT", "IEF", "SHY", "HYG", "LQD", "TIP", "EMB", "AGG",
    "BND", "BNDX", "BWX", "GOVT", "STIP", "VTIP",
    # Commodities
    "GLD", "SLV", "DBC", "USO", "UNG", "PDBC", "COPX", "PPLT",
    "WEAT", "CORN", "DBA",
    # Sectors
    "XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "XLU", "XLRE",
    "XLB", "XLC", "XLY", "SMH", "XBI", "KBE", "KRE", "XOP",
    "OIH", "ITB", "XHB", "JETS", "XME",
    # Currency / Alt
    "UUP", "FXE", "FXY", "FXB", "IBIT", "BITO",
    # REITs
    "VNQ", "VNQI", "IYR", "REM",
]

# Special tickers for VIX and FX (Yahoo format)
SPECIAL_TICKERS = {
    "^VIX": "^VIX",
    "DX-Y.NYB": "DX-Y.NYB",      # DXY Dollar Index
    "CNYUSD=X": "CNYUSD=X",
    "EURUSD=X": "EURUSD=X",
    "JPYUSD=X": "JPYUSD=X",
}

# Concurrency: how many curl processes to run in parallel
YAHOO_CONCURRENCY = 5
YAHOO_DELAY = 0.3  # seconds between batches


def _fetch_yahoo_ticker_curl(ticker: str) -> Optional[dict]:
    """Fetch price data for a single ticker via curl subprocess.

    Returns dict with 'price', 'return_1m', 'return_3m', 'return_12m'
    or None on failure.
    """
    url = f"{YAHOO_BASE_URL}/{ticker}?range=1y&interval=1d&includePrePost=false"

    try:
        result = subprocess.run(
            [
                "curl", "-s", "--max-time", "10",
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                url,
            ],
            capture_output=True, text=True, timeout=15,
        )

        if result.returncode != 0 or not result.stdout:
            logger.warning(f"Yahoo {ticker}: curl failed (rc={result.returncode})")
            return None

        data = json.loads(result.stdout)
        chart_result = data.get("chart", {}).get("result")
        if not chart_result:
            error = data.get("chart", {}).get("error", {})
            logger.warning(f"Yahoo {ticker}: {error.get('description', 'no result')}")
            return None

        indicators = chart_result[0].get("indicators", {})
        quotes = indicators.get("quote", [{}])[0]
        closes = quotes.get("close", [])
        timestamps = chart_result[0].get("timestamp", [])

        if not closes or not timestamps:
            logger.warning(f"Yahoo {ticker}: no price data")
            return None

        # Filter out None values and pair with timestamps
        valid = [(t, c) for t, c in zip(timestamps, closes) if c is not None]
        if not valid:
            return None

        current_price = valid[-1][1]

        # Calculate returns
        return_1m = _calc_return(valid, current_price, days=21)
        return_3m = _calc_return(valid, current_price, days=63)
        return_12m = _calc_return(valid, current_price, days=252)

        return {
            "price": round(current_price, 4),
            "return_1m": return_1m,
            "return_3m": return_3m,
            "return_12m": return_12m,
        }

    except subprocess.TimeoutExpired:
        logger.warning(f"Yahoo {ticker}: timeout")
        return None
    except json.JSONDecodeError:
        logger.warning(f"Yahoo {ticker}: invalid JSON response")
        return None
    except Exception as e:
        logger.warning(f"Yahoo {ticker}: {e}")
        return None


def _calc_return(
    valid_data: list[tuple[int, float]],
    current_price: float,
    days: int,
) -> Optional[float]:
    """Calculate return over approximately `days` trading days."""
    if len(valid_data) < days:
        # Use oldest available if we don't have enough history
        if len(valid_data) > 1:
            old_price = valid_data[0][1]
            if old_price > 0:
                return round(((current_price - old_price) / old_price) * 100, 2)
        return None

    old_price = valid_data[-(days + 1)][1] if len(valid_data) > days else valid_data[0][1]
    if old_price is None or old_price == 0:
        return None
    return round(((current_price - old_price) / old_price) * 100, 2)


# ---------------------------------------------------------------------------
# Computed Metrics
# ---------------------------------------------------------------------------

def _compute_metrics(
    fred_data: dict[str, Optional[float]],
    market_data: dict[str, MarketData],
    fred_timeseries: Optional[dict[str, object]] = None,
    spy_daily: Optional[list[float]] = None,
) -> dict[str, Optional[float]]:
    """Derive computed metrics from raw FRED + Yahoo data.

    These field names must match what theory modules reference as computed metrics.

    Returns:
        (computed, provenance) tuple. provenance tracks derivation quality for
        metrics that have fallback paths or hardcoded dependencies. Absence from
        provenance dict means "primary" — the intended data source was used.

    Args:
        fred_data: Transformed FRED values keyed by field path.
        market_data: Yahoo market data keyed by ticker.
        fred_timeseries: Raw pandas Series for WALCL/WTREGEN/RRPONTSYD (for 30d change).
        spy_daily: SPY daily closes for drawdown + realized vol.
    """
    from backend.schemas.briefing import FieldProvenance

    computed: dict[str, Optional[float]] = {}
    provenance: dict[str, FieldProvenance] = {}
    if fred_timeseries is None:
        fred_timeseries = {}

    # --- Yield curves ---
    t2y = fred_data.get("rates.treasury_2y")
    t10y = fred_data.get("rates.treasury_10y")
    t3m = fred_data.get("rates.treasury_3m")

    if t2y is not None and t10y is not None:
        computed["rates.curve_2s10s"] = round(t10y - t2y, 2)
    if t3m is not None and t10y is not None:
        computed["rates.curve_3m10y"] = round(t10y - t3m, 2)

    # --- Real 10Y yield (10Y nominal - 10Y breakeven) ---
    be10y = fred_data.get("inflation.breakeven_10y")
    if t10y is not None and be10y is not None:
        computed["real_10y"] = round(t10y - be10y, 2)

    # --- Equity risk premium ---
    # Improved: use corporate profits for earnings yield estimate if available.
    # CP (after-tax corporate profits, annualized) / approx S&P market cap.
    # Will be replaced by Shiller earnings yield in Phase 2 (web agent).
    spy_data = market_data.get("SPY")
    cp = fred_data.get("computed_fred.corporate_profits")
    gdp = fred_data.get("growth.gdp_latest")
    if cp is not None and gdp is not None and gdp > 0 and t10y is not None:
        # S&P 500 is ~80% of total market cap; Wilshire 5000 / GDP gives Buffett ratio
        # Earnings yield ≈ CP / (GDP * Buffett ratio) — rough but better than 4.5% constant
        wilshire = fred_data.get("computed_fred.wilshire_5000")
        if wilshire is not None and wilshire > 0:
            # Wilshire 5000 index: approx conversion to market cap ($T)
            # As of 2024-2025, Wilshire 5000 ~45000 ≈ $50T market cap
            approx_market_cap_T = wilshire / 900  # rough scalar
            if approx_market_cap_T > 0:
                earnings_yield = (cp / 1000) / approx_market_cap_T * 100  # CP is $B
                computed["equity_risk_premium"] = round(earnings_yield - t10y, 2)
                provenance["equity_risk_premium"] = FieldProvenance(
                    method="primary",
                    detail="CP/Wilshire5000 earnings yield - 10Y yield",
                )
            else:
                computed["equity_risk_premium"] = round(4.5 - t10y, 2)
                provenance["equity_risk_premium"] = FieldProvenance(
                    method="fallback",
                    detail="4.5% constant - 10Y yield (Wilshire5000 index <= 0)",
                )
        else:
            computed["equity_risk_premium"] = round(4.5 - t10y, 2)
            provenance["equity_risk_premium"] = FieldProvenance(
                method="fallback",
                detail="4.5% constant - 10Y yield (WILL5000INDFC FRED series unavailable)",
            )
    elif spy_data and spy_data.price and t10y is not None:
        computed["equity_risk_premium"] = round(4.5 - t10y, 2)
        provenance["equity_risk_premium"] = FieldProvenance(
            method="fallback",
            detail="4.5% constant - 10Y yield (corporate profits data unavailable)",
        )

    # --- Cash yield vs equity earnings yield (valuation_mean_reversion) ---
    # Positive = cash (fed funds) pays more than equities yield.
    # SPY earnings yield ≈ equity_risk_premium + 10Y yield.
    fed_funds = fred_data.get("rates.fed_funds")
    erp = computed.get("equity_risk_premium")
    if fed_funds is not None and erp is not None and t10y is not None:
        spy_earnings_yield = erp + t10y
        computed["cash_exceeds_equity_yield"] = round(fed_funds - spy_earnings_yield, 2)
        provenance["cash_exceeds_equity_yield"] = FieldProvenance(
            method="primary",
            detail=f"fed_funds ({fed_funds}) - (ERP ({erp}) + 10Y ({t10y}))",
        )

    # --- Real fed funds rate (debt_cycle_long) ---
    # Negative real rate = financial repression signature.
    cpi_yoy = fred_data.get("inflation.cpi_yoy")
    if fed_funds is not None and cpi_yoy is not None:
        computed["real_fed_funds_rate"] = round(fed_funds - cpi_yoy, 2)
        provenance["real_fed_funds_rate"] = FieldProvenance(
            method="primary",
            detail=f"fed_funds ({fed_funds}) - CPI YoY ({cpi_yoy})",
        )

    # --- Net liquidity (Fed BS - TGA - RRP) ---
    fed_bs = fred_data.get("liquidity.fed_balance_sheet")
    tga = fred_data.get("liquidity.tga")
    rrp = fred_data.get("liquidity.reverse_repo")
    if fed_bs is not None and tga is not None and rrp is not None:
        net_liq = fed_bs - tga - rrp
        computed["net_liquidity"] = round(net_liq, 0)

    # --- Net liquidity 30d change (from FRED time series) ---
    computed["net_liquidity_30d_change"] = _compute_net_liq_30d_change(fred_timeseries)

    # --- Gold/Oil ratio (GLD price / USO price) ---
    gld = market_data.get("GLD")
    uso = market_data.get("USO")
    if gld and uso and gld.price and uso.price and uso.price > 0:
        computed["gold_oil_ratio"] = round(gld.price / uso.price, 2)

    # --- EM/US relative (EEM return - SPY return) ---
    eem = market_data.get("EEM")
    if eem and spy_data:
        if eem.return_3m is not None and spy_data.return_3m is not None:
            computed["em_us_relative_3m"] = round(eem.return_3m - spy_data.return_3m, 2)
            computed["eem_spy_3m_relative"] = computed["em_us_relative_3m"]
        if eem.return_12m is not None and spy_data.return_12m is not None:
            computed["em_us_relative_12m"] = round(eem.return_12m - spy_data.return_12m, 2)

    # --- EEM/SPY 3-year relative (approximate with 12M) ---
    if eem and spy_data and eem.return_12m is not None and spy_data.return_12m is not None:
        computed["eem_spy_3y_relative"] = computed.get("em_us_relative_12m")

    # --- FXI and KWEB 3M returns (direct from market data) ---
    fxi = market_data.get("FXI")
    kweb = market_data.get("KWEB")
    if fxi and fxi.return_3m is not None:
        computed["fxi_3m_return"] = fxi.return_3m
    if kweb and kweb.return_3m is not None:
        computed["kweb_3m_return"] = kweb.return_3m

    # --- QQQ/IWM ratio (concentration proxy) ---
    qqq = market_data.get("QQQ")
    iwm = market_data.get("IWM")
    if qqq and iwm and qqq.price and iwm.price and iwm.price > 0:
        computed["qqq_iwm_ratio"] = round(qqq.price / iwm.price, 4)

    # --- VIX vs realized vol ---
    vix = market_data.get("^VIX")
    if vix and vix.price is not None and spy_daily:
        realized = _compute_realized_vol(spy_daily)
        if realized is not None:
            computed["vix_vs_realized"] = round(vix.price - realized, 2)
        else:
            computed["vix_vs_realized"] = None
    else:
        computed["vix_vs_realized"] = None

    # --- Hard assets vs nominal bonds (12M) ---
    hard_tickers = ["GLD", "SLV", "DBC"]
    bond_tickers = ["TLT", "IEF", "AGG"]

    hard_returns = [
        market_data[t].return_12m for t in hard_tickers
        if t in market_data and market_data[t].return_12m is not None
    ]
    bond_returns = [
        market_data[t].return_12m for t in bond_tickers
        if t in market_data and market_data[t].return_12m is not None
    ]

    if hard_returns and bond_returns:
        avg_hard = sum(hard_returns) / len(hard_returns)
        avg_bond = sum(bond_returns) / len(bond_returns)
        computed["hard_vs_nominal_12m"] = round(avg_hard - avg_bond, 2)

    # --- SPY drawdown from 52-week high ---
    if spy_daily:
        computed["spy_drawdown_from_52w_high"] = _compute_spy_drawdown(spy_daily)
    else:
        computed["spy_drawdown_from_52w_high"] = None

    # --- Top 10 S&P 500 weight (Phase 2: web agent) ---
    computed["top_10_sp500_weight"] = None

    # --- Commodity index 3M change (DBC return) ---
    dbc = market_data.get("DBC")
    if dbc and dbc.return_3m is not None:
        computed["commodity_index_3m_change"] = dbc.return_3m

    # --- Real fed funds rate (fed funds - CPI YoY) ---
    ff = fred_data.get("rates.fed_funds")
    cpi = fred_data.get("inflation.cpi_yoy")
    if ff is not None and cpi is not None:
        computed["real_fed_funds"] = round(ff - cpi, 2)

    # -----------------------------------------------------------------------
    # NEW: Derived metrics from expanded FRED series
    # -----------------------------------------------------------------------

    # --- Interest expense / tax receipts ratio (fiscal_dominance_arithmetic) ---
    interest = fred_data.get("computed_fred.federal_interest_payments")
    receipts = fred_data.get("computed_fred.federal_tax_receipts")
    if interest is not None and receipts is not None and receipts > 0:
        computed["interest_receipts_ratio"] = round((interest / receipts) * 100, 1)

    # --- Fed BS / GDP (debt_cycle_long) ---
    if fed_bs is not None and gdp is not None and gdp > 0:
        fed_bs_billions = fed_bs / 1000  # WALCL is in millions
        computed["fed_bs_gdp_ratio"] = round((fed_bs_billions / gdp) * 100, 1)

    # --- Federal debt to GDP (debt_cycle_long) ---
    debt_gdp = fred_data.get("computed_fred.federal_debt_to_gdp")
    if debt_gdp is not None:
        computed["federal_debt_to_gdp"] = round(debt_gdp, 1)

    # --- SLOOS net tightening (debt_cycle_short) ---
    sloos = fred_data.get("credit.sloos_tightening_ci")
    if sloos is not None:
        computed["sloos_net_tightening"] = round(sloos, 1)

    # --- Deficit pace annualized (fiscal_dominance_liquidity) ---
    monthly_deficit = fred_data.get("computed_fred.monthly_treasury_deficit")
    if monthly_deficit is not None:
        # MTSDS133FMS is in millions; negative = deficit. Annualize and convert to $B.
        computed["deficit_pace_annualized"] = round(abs(monthly_deficit) * 12 / 1000, 1)

    # --- Buffett indicator: total market cap / GDP (valuation_mean_reversion) ---
    wilshire = fred_data.get("computed_fred.wilshire_5000")
    if wilshire is not None and gdp is not None and gdp > 0:
        # Wilshire 5000 index: rough conversion to market cap in $T
        # Historical calibration: Wilshire ~45000 ≈ $50T (factor ≈ 1/900)
        approx_market_cap_T = wilshire / 900
        gdp_T = gdp / 1000  # GDP is in billions
        if gdp_T > 0:
            computed["buffett_indicator"] = round(approx_market_cap_T / gdp_T, 2)
    else:
        provenance["buffett_indicator"] = FieldProvenance(
            method="missing",
            detail="Cannot compute: WILL5000INDFC unavailable" if gdp is not None
                   else "Cannot compute: GDP and/or WILL5000INDFC unavailable",
        )

    # --- Foreign treasury holdings % of total outstanding (monetary_architecture) ---
    foreign_holdings = fred_data.get("computed_fred.foreign_treasury_holdings")
    total_debt = fred_data.get("computed_fred.total_public_debt")
    if foreign_holdings is not None and total_debt is not None and total_debt > 0:
        # foreign_holdings is in $B, total_debt is in $M — normalize
        total_debt_B = total_debt / 1000
        if total_debt_B > 0:
            computed["foreign_treasury_holdings_pct"] = round(
                (foreign_holdings / total_debt_B) * 100, 1
            )

    # --- Corporate profits / GDP (valuation_mean_reversion) ---
    if cp is not None and gdp is not None and gdp > 0:
        computed["corporate_profits_gdp_ratio"] = round((cp / gdp) * 100, 1)

    # --- Interest expense exceeds defense spending (fiscal_dominance_arithmetic) ---
    # Defense spending ~$886B in FY2024, ~3%/yr growth → ~$940B by FY2026
    # Stored as surplus: positive = interest exceeds defense
    if interest is not None:
        computed["interest_exceeds_defense"] = round(interest - 940, 0)
        provenance["interest_exceeds_defense"] = FieldProvenance(
            method="hardcoded",
            detail="Interest - $940B defense (FY2026 estimate, ~3%/yr from FY2024 $886B)",
        )

    # --- Top 10 S&P 500 weight (no data source wired) ---
    # Already set to None above; record provenance so validation surfaces it.
    provenance["top_10_sp500_weight"] = FieldProvenance(
        method="missing",
        detail="No data source implemented (placeholder since v1)",
    )

    return computed, provenance


def _compute_net_liq_30d_change(fred_timeseries: dict[str, object]) -> Optional[float]:
    """Compute 30-day change in net liquidity from WALCL - WTREGEN - RRPONTSYD.

    Uses raw time series to align dates and compute the delta.
    """
    walcl = fred_timeseries.get("WALCL")
    wtregen = fred_timeseries.get("WTREGEN")
    rrpontsyd = fred_timeseries.get("RRPONTSYD")

    if walcl is None or wtregen is None or rrpontsyd is None:
        return None

    try:
        import pandas as pd

        # Align all three series on their index (dates)
        df = pd.DataFrame({
            "walcl": walcl,
            "wtregen": wtregen,
            "rrpontsyd": rrpontsyd,
        }).dropna()

        if len(df) < 2:
            return None

        # Net liquidity = WALCL - WTREGEN - RRPONTSYD
        df["net_liq"] = df["walcl"] - df["wtregen"] - df["rrpontsyd"]

        current = df["net_liq"].iloc[-1]

        # Find the value closest to 30 days ago
        current_date = df.index[-1]
        target_date = current_date - pd.Timedelta(days=30)
        # Find nearest date at or before target
        mask = df.index <= target_date
        if not mask.any():
            # Less than 30 days of data — use oldest available
            past = df["net_liq"].iloc[0]
        else:
            past = df.loc[mask, "net_liq"].iloc[-1]

        change = current - past
        return round(float(change), 0)
    except Exception as e:
        logger.warning(f"net_liquidity_30d_change computation failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Briefing Packet Assembly
# ---------------------------------------------------------------------------

def _build_briefing_from_data(
    fred_data: dict[str, Optional[float]],
    market_data: dict[str, MarketData],
    computed: dict[str, Optional[float]],
    fetch_timestamp: str,
    web_sourced: Optional[dict[str, WebSourcedData]] = None,
    field_provenance: Optional[dict] = None,
) -> BriefingPacket:
    """Assemble a BriefingPacket from fetched + computed data."""
    # Split fred_data into sections by prefix
    growth: dict[str, Optional[float]] = {}
    inflation: dict[str, Optional[float]] = {}
    rates: dict[str, Optional[float]] = {}
    liquidity: dict[str, Optional[float]] = {}
    credit: dict[str, Optional[float]] = {}
    sentiment: dict[str, Optional[float]] = {}

    section_map = {
        "growth": growth,
        "inflation": inflation,
        "rates": rates,
        "liquidity": liquidity,
        "credit": credit,
        "sentiment": sentiment,
    }

    for field_path, value in fred_data.items():
        if "." in field_path:
            section, field = field_path.split(".", 1)
            if section in section_map:
                section_map[section][field] = value

    # Add yield curve computations to rates
    for key in ("rates.curve_2s10s", "rates.curve_3m10y"):
        if key in computed:
            rates[key.split(".", 1)[1]] = computed[key]

    # Computed metrics (strip section prefix if present)
    computed_clean: dict[str, Optional[float]] = {}
    for k, v in computed.items():
        if k.startswith("rates."):
            continue  # already added to rates section
        computed_clean[k] = v

    return BriefingPacket(
        timestamp=fetch_timestamp,
        staleness_hours=0.0,
        growth=growth,
        inflation=inflation,
        rates=rates,
        liquidity=liquidity,
        credit=credit,
        sentiment=sentiment,
        computed=computed_clean,
        markets=market_data,
        web_sourced=web_sourced or {},
        field_provenance=field_provenance or {},
    )


# ---------------------------------------------------------------------------
# Cache Management
# ---------------------------------------------------------------------------

CACHE_FILE = DATA_DIR / "briefing_cache.json"
CACHE_MAX_AGE_HOURS = 24


def _load_cache() -> Optional[dict]:
    """Load cached briefing data if fresh enough."""
    if not CACHE_FILE.exists():
        return None

    try:
        raw = json.loads(CACHE_FILE.read_text())
        cached_at = datetime.fromisoformat(raw.get("timestamp", ""))
        age = datetime.now(timezone.utc) - cached_at
        if age.total_seconds() / 3600 > CACHE_MAX_AGE_HOURS:
            logger.info("Cache expired (%.1f hours old)", age.total_seconds() / 3600)
            return None
        logger.info("Using cached briefing (%.1f hours old)", age.total_seconds() / 3600)
        return raw
    except Exception as e:
        logger.warning(f"Cache load failed: {e}")
        return None


def _save_cache(briefing: BriefingPacket) -> None:
    """Save briefing to cache."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CACHE_FILE.write_text(briefing.model_dump_json(indent=2))
        logger.info("Briefing cached to %s", CACHE_FILE)
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Series IDs whose raw time series we need for derived computations
# (net_liquidity_30d_change needs historical WALCL, WTREGEN, RRPONTSYD)
_TIMESERIES_SERIES = {"WALCL", "WTREGEN", "RRPONTSYD"}


def fetch_fred_data() -> tuple[dict[str, Optional[float]], dict[str, object]]:
    """Fetch all FRED series and return transformed values + raw time series.

    Returns:
        (field_values, timeseries) where timeseries contains raw pandas Series
        for series in _TIMESERIES_SERIES, keyed by series_id.
    """
    if not settings.fred_api_key:
        logger.error("FRED_API_KEY not set — skipping FRED fetch")
        return {}, {}

    fred = Fred(api_key=settings.fred_api_key)
    results: dict[str, Optional[float]] = {}
    timeseries: dict[str, object] = {}

    for series_id, config in FRED_SERIES.items():
        field = config["field"]
        transform = config["transform"]
        try:
            # Fetch last 2 years for transforms that need history
            data = fred.get_series(series_id, observation_start="2023-01-01")
            value = _apply_fred_transform(data, transform)
            results[field] = value
            logger.debug(f"FRED {series_id} → {field} = {value}")

            # Preserve raw time series for derived computations
            if series_id in _TIMESERIES_SERIES and data is not None:
                timeseries[series_id] = data.dropna()
        except Exception as e:
            logger.warning(f"FRED {series_id} failed: {e}")
            results[field] = None

    return results, timeseries


def fetch_yahoo_data(on_progress=None) -> dict[str, MarketData]:
    """Fetch market data for full ETF universe + special tickers.

    Uses concurrent curl subprocess calls to bypass Yahoo TLS fingerprinting.

    Args:
        on_progress: Optional callback(fetched, total, ticker) called as each ticker completes.
    """
    all_tickers = ETF_UNIVERSE + list(SPECIAL_TICKERS.keys())
    market_data: dict[str, MarketData] = {}
    failed: list[str] = []
    total = len(all_tickers)
    fetched = 0

    with ThreadPoolExecutor(max_workers=YAHOO_CONCURRENCY) as executor:
        futures = {
            executor.submit(_fetch_yahoo_ticker_curl, ticker): ticker
            for ticker in all_tickers
        }

        for future in as_completed(futures):
            ticker = futures[future]
            fetched += 1
            try:
                result = future.result()
                if result:
                    market_data[ticker] = MarketData(
                        price=result["price"],
                        return_1m=result.get("return_1m"),
                        return_3m=result.get("return_3m"),
                        return_12m=result.get("return_12m"),
                    )
                else:
                    failed.append(ticker)
            except Exception as e:
                logger.warning(f"Yahoo {ticker}: {e}")
                failed.append(ticker)

            if on_progress:
                on_progress(fetched, total, ticker)

    if failed:
        logger.warning(f"Failed tickers ({len(failed)}): {', '.join(sorted(failed))}")

    return market_data


def _fetch_spy_daily_data() -> Optional[list[float]]:
    """Fetch SPY 1-year daily closes via curl. Single fetch, multiple uses.

    Returns list of valid daily closing prices (oldest to newest), or None on failure.
    Used for both 52-week drawdown and 20-day realized volatility calculations.
    """
    url = f"{YAHOO_BASE_URL}/SPY?range=1y&interval=1d&includePrePost=false"
    try:
        result = subprocess.run(
            [
                "curl", "-s", "--max-time", "10",
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                url,
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0 or not result.stdout:
            return None

        data = json.loads(result.stdout)
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        valid_closes = [c for c in closes if c is not None]
        if not valid_closes:
            return None
        return valid_closes
    except Exception as e:
        logger.warning(f"SPY daily data fetch failed: {e}")
        return None


def _compute_spy_drawdown(spy_daily: list[float]) -> Optional[float]:
    """Compute SPY drawdown from 52-week high given daily closes."""
    if not spy_daily:
        return None
    high_52w = max(spy_daily)
    current = spy_daily[-1]
    if high_52w == 0:
        return None
    return round(((current - high_52w) / high_52w) * 100, 2)


def _compute_realized_vol(spy_daily: list[float], window: int = 20) -> Optional[float]:
    """Compute annualized realized volatility from SPY daily closes.

    Uses the last `window` trading days of daily log returns,
    annualized by sqrt(252).
    """
    if not spy_daily or len(spy_daily) < window + 1:
        return None
    import math
    returns = [
        (spy_daily[i] - spy_daily[i - 1]) / spy_daily[i - 1]
        for i in range(1, len(spy_daily))
    ]
    recent = returns[-window:]
    mean = sum(recent) / len(recent)
    variance = sum((r - mean) ** 2 for r in recent) / (len(recent) - 1)
    realized = math.sqrt(variance) * math.sqrt(252) * 100
    return round(realized, 2)


def build_briefing(use_cache: bool = True, on_progress=None, skip_web: bool = False) -> BriefingPacket:
    """Main entry point: fetch all data and build a BriefingPacket.

    If use_cache is True and a fresh cache exists, returns cached data.

    Args:
        use_cache: If True, return cached data when available.
        on_progress: Optional callback(stage, detail) for progress reporting.
                     stage: short phase name, detail: human-readable status string.
        skip_web: If True, skip web data agent (faster, FRED+Yahoo only).
    """
    def emit(stage, detail):
        if on_progress:
            on_progress(stage, detail)

    # Check cache
    if use_cache:
        emit("cache", "Checking cache...")
        cached = _load_cache()
        if cached:
            try:
                emit("cache", "Fresh cache found, using cached data")
                return BriefingPacket.model_validate_json(json.dumps(cached))
            except Exception:
                emit("cache", "Cache malformed, fetching fresh data")

    emit("start", "Starting fresh data fetch")
    fetch_timestamp = datetime.now(timezone.utc).isoformat()

    # Fetch FRED (expanded: returns values + time series for net_liq computation)
    emit("fred", f"Fetching FRED data ({len(FRED_SERIES)} series)...")
    fred_data, fred_timeseries = fetch_fred_data()
    fred_ok = sum(1 for v in fred_data.values() if v is not None)
    emit("fred", f"FRED complete: {fred_ok}/{len(FRED_SERIES)} series")

    # Fetch Yahoo
    total_tickers = len(ETF_UNIVERSE) + len(SPECIAL_TICKERS)
    emit("yahoo", f"Fetching Yahoo Finance data ({total_tickers} tickers)...")

    def yahoo_progress(fetched, total, ticker):
        emit("yahoo", f"Yahoo: {fetched}/{total} tickers ({ticker})")

    market_data = fetch_yahoo_data(on_progress=yahoo_progress)
    emit("yahoo", f"Yahoo complete: {len(market_data)}/{total_tickers} tickers")

    # Fetch web-sourced data (ISM, CAPE, margin debt, etc.)
    web_sourced: dict[str, WebSourcedData] = {}
    if not skip_web:
        from backend.engine.web_data_agent import fetch_web_data

        emit("web", "Fetching web-sourced data (16 fields)...")
        web_ok = 0

        def web_progress(field_name: str, status: str):
            nonlocal web_ok
            if status.startswith("ok"):
                web_ok += 1
            emit("web", f"Web: {field_name} — {status}")

        web_sourced = fetch_web_data(fred_data=fred_data, on_progress=web_progress)
        emit("web", f"Web complete: {len(web_sourced)}/16 fields")
    else:
        emit("web", "Web data skipped (--skip-web)")

    # Fetch SPY daily data (single fetch for both drawdown + realized vol)
    spy_daily = _fetch_spy_daily_data()

    # Compute derived metrics (now receives timeseries + spy_daily)
    emit("compute", "Computing derived metrics...")
    computed, field_provenance = _compute_metrics(fred_data, market_data, fred_timeseries, spy_daily)

    # Assemble briefing
    emit("assemble", "Assembling briefing packet...")
    briefing = _build_briefing_from_data(
        fred_data, market_data, computed, fetch_timestamp, web_sourced, field_provenance,
    )

    # Validate briefing data (Phase 4: validation agent)
    from backend.engine.validation_agent import validate_briefing

    emit("validate", "Running validation checks...")

    # Load previous briefing for anomaly detection (raw cache, skip freshness check)
    previous_briefing = None
    if CACHE_FILE.exists():
        try:
            prev_raw = json.loads(CACHE_FILE.read_text())
            previous_briefing = BriefingPacket.model_validate(prev_raw)
        except Exception:
            pass

    report = validate_briefing(briefing, previous_briefing)
    briefing.data_quality = report.model_dump()
    emit("validate", f"Validation: {report.overall_quality} ({report.errors} errors, {report.warnings} warnings)")

    # Cache result
    emit("save", "Saving to cache...")
    _save_cache(briefing)

    emit("done", "Data briefing complete")
    return briefing


def save_briefing_json(briefing: BriefingPacket, output_dir: Optional[Path] = None) -> Path:
    """Save briefing packet as JSON file. Returns the output path."""
    if output_dir is None:
        output_dir = MOCK_DATA_DIR

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "briefing_packet.json"
    output_path.write_text(briefing.model_dump_json(indent=2))
    logger.info("Briefing saved to %s", output_path)
    return output_path
