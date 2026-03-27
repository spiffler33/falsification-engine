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
from backend.schemas.briefing import BriefingPacket, MarketData

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
) -> dict[str, Optional[float]]:
    """Derive computed metrics from raw FRED + Yahoo data.

    These field names must match what theory modules reference as computed metrics.
    """
    computed: dict[str, Optional[float]] = {}

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

    # --- Equity risk premium (SPY earnings yield - 10Y) ---
    # SPY earnings yield ≈ 1/PE. S&P 500 PE ~22 → earnings yield ~4.5%
    # For v1, use a rough approximation. Precise PE data requires web search.
    spy = market_data.get("SPY")
    if spy and spy.price and t10y is not None:
        # Rough estimate: SPY earnings yield ≈ 4.5% (updated when we get PE data)
        # For now, store the 10Y component and flag this as approximate
        estimated_earnings_yield = 4.5  # placeholder — would need S&P PE ratio
        computed["equity_risk_premium"] = round(estimated_earnings_yield - t10y, 2)

    # --- Net liquidity (Fed BS - TGA - RRP) ---
    fed_bs = fred_data.get("liquidity.fed_balance_sheet")
    tga = fred_data.get("liquidity.tga")
    rrp = fred_data.get("liquidity.reverse_repo")
    if fed_bs is not None and tga is not None and rrp is not None:
        net_liq = fed_bs - tga - rrp
        computed["net_liquidity"] = round(net_liq, 0)
        # 30d change would need historical data — store current value for now
        # Will be computed when we have time-series caching
        computed["net_liquidity_30d_change"] = None

    # --- Gold/Oil ratio (GLD price / USO price) ---
    gld = market_data.get("GLD")
    uso = market_data.get("USO")
    if gld and uso and gld.price and uso.price and uso.price > 0:
        computed["gold_oil_ratio"] = round(gld.price / uso.price, 2)

    # --- EM/US relative (EEM return - SPY return) ---
    eem = market_data.get("EEM")
    spy_data = market_data.get("SPY")
    if eem and spy_data:
        if eem.return_3m is not None and spy_data.return_3m is not None:
            computed["em_us_relative_3m"] = round(eem.return_3m - spy_data.return_3m, 2)
            computed["eem_spy_3m_relative"] = computed["em_us_relative_3m"]
        if eem.return_12m is not None and spy_data.return_12m is not None:
            computed["em_us_relative_12m"] = round(eem.return_12m - spy_data.return_12m, 2)

    # --- EEM/SPY 3-year relative (would need 3Y data, approximate with 12M) ---
    if eem and spy_data and eem.return_12m is not None and spy_data.return_12m is not None:
        computed["eem_spy_3y_relative"] = computed.get("em_us_relative_12m")  # best proxy

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
    if vix and vix.price is not None and spy_data:
        # Realized vol would need daily returns series
        # For v1: VIX level is the primary indicator, realized gap is approximate
        # Store VIX level; compute gap when we have daily returns
        computed["vix_vs_realized"] = None  # needs daily SPY returns for 20d realized

    # --- Hard assets vs nominal bonds (12M) ---
    # Hard assets: GLD, SLV, DBC average returns
    # Nominal bonds: TLT, IEF, AGG average returns
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
    if spy_data and spy_data.price:
        # We'd need the 52-week high. Approximate using 12M return.
        # If 12M return is positive, drawdown is likely small.
        # For precise value, we'd need the max price in the last year.
        # For v1, store None — will compute from price series if available.
        computed["spy_drawdown_from_52w_high"] = None

    # --- Top 10 S&P 500 weight (requires external data — web search) ---
    computed["top_10_sp500_weight"] = None  # web search required

    # --- Commodity index 3M change (DBC return) ---
    dbc = market_data.get("DBC")
    if dbc and dbc.return_3m is not None:
        computed["commodity_index_3m_change"] = dbc.return_3m

    # --- Real fed funds rate (fed funds - CPI YoY) ---
    ff = fred_data.get("rates.fed_funds")
    cpi = fred_data.get("inflation.cpi_yoy")
    if ff is not None and cpi is not None:
        computed["real_fed_funds"] = round(ff - cpi, 2)

    return computed


# ---------------------------------------------------------------------------
# Briefing Packet Assembly
# ---------------------------------------------------------------------------

def _build_briefing_from_data(
    fred_data: dict[str, Optional[float]],
    market_data: dict[str, MarketData],
    computed: dict[str, Optional[float]],
    fetch_timestamp: str,
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

def fetch_fred_data() -> dict[str, Optional[float]]:
    """Fetch all FRED series and return as {field_path: transformed_value}."""
    if not settings.fred_api_key:
        logger.error("FRED_API_KEY not set — skipping FRED fetch")
        return {}

    fred = Fred(api_key=settings.fred_api_key)
    results: dict[str, Optional[float]] = {}

    for series_id, config in FRED_SERIES.items():
        field = config["field"]
        transform = config["transform"]
        try:
            # Fetch last 2 years for transforms that need history
            data = fred.get_series(series_id, observation_start="2023-01-01")
            value = _apply_fred_transform(data, transform)
            results[field] = value
            logger.debug(f"FRED {series_id} → {field} = {value}")
        except Exception as e:
            logger.warning(f"FRED {series_id} failed: {e}")
            results[field] = None

    return results


def fetch_yahoo_data() -> dict[str, MarketData]:
    """Fetch market data for full ETF universe + special tickers.

    Uses concurrent curl subprocess calls to bypass Yahoo TLS fingerprinting.
    """
    all_tickers = ETF_UNIVERSE + list(SPECIAL_TICKERS.keys())
    market_data: dict[str, MarketData] = {}
    failed: list[str] = []

    with ThreadPoolExecutor(max_workers=YAHOO_CONCURRENCY) as executor:
        futures = {
            executor.submit(_fetch_yahoo_ticker_curl, ticker): ticker
            for ticker in all_tickers
        }

        for future in as_completed(futures):
            ticker = futures[future]
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

    if failed:
        logger.warning(f"Failed tickers ({len(failed)}): {', '.join(sorted(failed))}")

    return market_data


def _compute_spy_drawdown_curl() -> Optional[float]:
    """Compute SPY drawdown from 52-week high using curl."""
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
        high_52w = max(valid_closes)
        current = valid_closes[-1]
        if high_52w == 0:
            return None
        return round(((current - high_52w) / high_52w) * 100, 2)
    except Exception as e:
        logger.warning(f"SPY drawdown calc failed: {e}")
        return None


def build_briefing(use_cache: bool = True) -> BriefingPacket:
    """Main entry point: fetch all data and build a BriefingPacket.

    If use_cache is True and a fresh cache exists, returns cached data.
    """
    # Check cache
    if use_cache:
        cached = _load_cache()
        if cached:
            try:
                return BriefingPacket.model_validate_json(json.dumps(cached))
            except Exception:
                # If cache is malformed, proceed with fresh fetch
                pass

    logger.info("Fetching fresh data...")
    fetch_timestamp = datetime.now(timezone.utc).isoformat()

    # Fetch FRED
    logger.info("Fetching FRED data (%d series)...", len(FRED_SERIES))
    fred_data = fetch_fred_data()
    logger.info("FRED: %d/%d series fetched", sum(1 for v in fred_data.values() if v is not None), len(FRED_SERIES))

    # Fetch Yahoo
    total_tickers = len(ETF_UNIVERSE) + len(SPECIAL_TICKERS)
    logger.info("Fetching Yahoo data (%d tickers)...", total_tickers)
    market_data = fetch_yahoo_data()
    logger.info("Yahoo: %d/%d tickers fetched", len(market_data), total_tickers)

    # Compute SPY drawdown
    spy_dd = _compute_spy_drawdown_curl()

    # Compute derived metrics
    computed = _compute_metrics(fred_data, market_data)

    # Patch in SPY drawdown if we got it
    if spy_dd is not None:
        computed["spy_drawdown_from_52w_high"] = spy_dd

    # Assemble briefing
    briefing = _build_briefing_from_data(fred_data, market_data, computed, fetch_timestamp)

    # Cache result
    _save_cache(briefing)

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
