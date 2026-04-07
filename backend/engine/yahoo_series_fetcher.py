"""Yahoo Finance historical series fetcher for SeriesStore population.

Fetches daily close prices via curl subprocess (same TLS-fingerprinting
strategy as data_agent.py) and returns (date, price) pairs for loading
into InMemorySeriesStore.

Supports:
  - Single ticker prices (e.g., DX-Y.NYB -> dxy_index)
  - Ratio tickers (e.g., QQQ/IWM -> qqq_iwm_ratio)
  - Rolling return computations (e.g., EEM-SPY 3M relative)
"""
from __future__ import annotations

import csv
import json
import logging
import subprocess
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from backend.config import DATA_DIR

logger = logging.getLogger(__name__)

CACHE_DIR = DATA_DIR / "series_cache"
YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
MAX_RETRIES = 3
RETRY_DELAY = 2.0


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def _cache_path(ticker: str) -> Path:
    safe = ticker.replace("=", "_").replace("^", "_").replace(".", "_").replace("-", "_")
    return CACHE_DIR / f"yahoo_{safe}.csv"


def _read_cache(ticker: str, max_age_hours: float = 24.0) -> Optional[list[tuple[str, float]]]:
    path = _cache_path(ticker)
    if not path.exists():
        return None
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age_hours = (datetime.now() - mtime).total_seconds() / 3600
    if age_hours > max_age_hours:
        return None
    try:
        rows = []
        with open(path) as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                rows.append((row[0], float(row[1])))
        logger.debug(f"Yahoo cache hit for {ticker}: {len(rows)} observations")
        return rows
    except Exception:
        return None


def _write_cache(ticker: str, data: list[tuple[str, float]]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(ticker)
    try:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "value"])
            for d, v in data:
                writer.writerow([d, v])
    except Exception as e:
        logger.warning(f"Yahoo cache write failed for {ticker}: {e}")


# ---------------------------------------------------------------------------
# Yahoo fetch via curl
# ---------------------------------------------------------------------------

def _fetch_yahoo_daily(
    ticker: str,
    lookback_years: int = 3,
) -> Optional[list[tuple[str, float]]]:
    """Fetch daily close prices for a single ticker.

    Returns list of (YYYY-MM-DD, close_price) sorted oldest-first,
    or None on failure.
    """
    # Yahoo v8 API: range parameter for multi-year data
    range_str = f"{lookback_years}y"
    url = f"{YAHOO_BASE_URL}/{ticker}?range={range_str}&interval=1d&includePrePost=false"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = subprocess.run(
                [
                    "curl", "-s", "--max-time", "15",
                    "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    url,
                ],
                capture_output=True, text=True, timeout=20,
            )

            if result.returncode != 0 or not result.stdout:
                logger.warning(f"Yahoo {ticker} attempt {attempt}: curl failed")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                continue

            data = json.loads(result.stdout)
            chart_result = data.get("chart", {}).get("result")
            if not chart_result:
                error = data.get("chart", {}).get("error", {})
                logger.warning(f"Yahoo {ticker}: {error.get('description', 'no result')}")
                return None

            timestamps = chart_result[0].get("timestamp", [])
            quotes = chart_result[0].get("indicators", {}).get("quote", [{}])[0]
            closes = quotes.get("close", [])

            if not timestamps or not closes:
                logger.warning(f"Yahoo {ticker}: no data")
                return None

            # Pair timestamps with closes, skip None
            pairs = []
            for ts, close in zip(timestamps, closes):
                if close is not None:
                    dt = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                    pairs.append((dt, round(close, 4)))

            if not pairs:
                return None

            logger.info(f"Yahoo {ticker}: {len(pairs)} daily observations ({pairs[0][0]} to {pairs[-1][0]})")
            return pairs

        except subprocess.TimeoutExpired:
            logger.warning(f"Yahoo {ticker} attempt {attempt}: timeout")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
        except json.JSONDecodeError:
            logger.warning(f"Yahoo {ticker}: invalid JSON")
            return None
        except Exception as e:
            logger.warning(f"Yahoo {ticker} attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    logger.error(f"Yahoo {ticker}: all {MAX_RETRIES} attempts failed")
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_yahoo_series(
    ticker: str,
    lookback_years: int = 3,
    use_cache: bool = True,
    cache_max_age_hours: float = 24.0,
) -> Optional[list[tuple[str, float]]]:
    """Fetch daily close prices for a single Yahoo ticker.

    Returns:
        List of (YYYY-MM-DD, close_price) pairs sorted oldest-first.
    """
    if use_cache:
        cached = _read_cache(ticker, cache_max_age_hours)
        if cached is not None:
            return cached

    data = _fetch_yahoo_daily(ticker, lookback_years)
    if data and use_cache:
        _write_cache(ticker, data)
    return data


def fetch_yahoo_ratio(
    ticker_a: str,
    ticker_b: str,
    lookback_years: int = 3,
    use_cache: bool = True,
) -> Optional[list[tuple[str, float]]]:
    """Compute price ratio series: ticker_a / ticker_b.

    Aligns on common dates and computes the ratio per day.
    """
    cache_key = f"{ticker_a}_div_{ticker_b}"
    if use_cache:
        cached = _read_cache(cache_key)
        if cached is not None:
            return cached

    series_a = fetch_yahoo_series(ticker_a, lookback_years, use_cache)
    series_b = fetch_yahoo_series(ticker_b, lookback_years, use_cache)

    if not series_a or not series_b:
        return None

    # Build date -> price maps
    map_a = dict(series_a)
    map_b = dict(series_b)

    # Intersect dates
    common_dates = sorted(set(map_a.keys()) & set(map_b.keys()))
    if not common_dates:
        return None

    ratios = []
    for d in common_dates:
        if map_b[d] > 0:
            ratios.append((d, round(map_a[d] / map_b[d], 4)))

    if ratios and use_cache:
        _write_cache(cache_key, ratios)

    logger.info(f"Yahoo ratio {ticker_a}/{ticker_b}: {len(ratios)} observations")
    return ratios


def fetch_yahoo_rolling_return_diff(
    ticker_a: str,
    ticker_b: str,
    window_days: int = 63,
    lookback_years: int = 3,
    use_cache: bool = True,
) -> Optional[list[tuple[str, float]]]:
    """Compute rolling return difference: return(A) - return(B) over window.

    Used for eem_spy_3m_relative (EEM 3M return - SPY 3M return).
    Returns a monthly-sampled series of return differences.
    """
    cache_key = f"{ticker_a}_minus_{ticker_b}_{window_days}d"
    if use_cache:
        cached = _read_cache(cache_key)
        if cached is not None:
            return cached

    series_a = fetch_yahoo_series(ticker_a, lookback_years, use_cache)
    series_b = fetch_yahoo_series(ticker_b, lookback_years, use_cache)

    if not series_a or not series_b:
        return None

    map_a = dict(series_a)
    map_b = dict(series_b)
    common_dates = sorted(set(map_a.keys()) & set(map_b.keys()))

    if len(common_dates) < window_days + 1:
        return None

    # Compute rolling returns at monthly intervals (~21 trading days)
    result = []
    step = 21  # sample monthly
    for i in range(window_days, len(common_dates), step):
        d = common_dates[i]
        d_past = common_dates[i - window_days]

        pa_now, pa_past = map_a[d], map_a[d_past]
        pb_now, pb_past = map_b[d], map_b[d_past]

        if pa_past > 0 and pb_past > 0:
            ret_a = ((pa_now - pa_past) / pa_past) * 100
            ret_b = ((pb_now - pb_past) / pb_past) * 100
            result.append((d, round(ret_a - ret_b, 2)))

    if result and use_cache:
        _write_cache(cache_key, result)

    logger.info(f"Yahoo rolling diff {ticker_a}-{ticker_b}: {len(result)} monthly observations")
    return result


def fetch_yahoo_rolling_return(
    ticker: str,
    window_days: int = 63,
    lookback_years: int = 3,
    use_cache: bool = True,
) -> Optional[list[tuple[str, float]]]:
    """Compute rolling percent return for a single ticker.

    Used for commodity_index_3m_change (DBC 3M pct change).
    Returns a monthly-sampled series.
    """
    cache_key = f"{ticker}_{window_days}d_return"
    if use_cache:
        cached = _read_cache(cache_key)
        if cached is not None:
            return cached

    series = fetch_yahoo_series(ticker, lookback_years, use_cache)
    if not series or len(series) < window_days + 1:
        return None

    result = []
    step = 21
    for i in range(window_days, len(series), step):
        d = series[i][0]
        price_now = series[i][1]
        price_past = series[i - window_days][1]
        if price_past > 0:
            ret = ((price_now - price_past) / price_past) * 100
            result.append((d, round(ret, 2)))

    if result and use_cache:
        _write_cache(cache_key, result)

    logger.info(f"Yahoo rolling return {ticker}: {len(result)} monthly observations")
    return result
