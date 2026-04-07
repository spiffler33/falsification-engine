"""FRED historical series fetcher for SeriesStore population.

Fetches full time series from FRED API and applies per-observation
transforms so the stored values match what the compiled rules expect.

Unlike data_agent.py which fetches the *latest* transformed value,
this module fetches the *full history* as a list of (date, value) pairs
that can be loaded directly into InMemorySeriesStore.

Caching: each series is cached as a CSV in data/series_cache/ to avoid
repeated API calls during development and testing.
"""
from __future__ import annotations

import csv
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from backend.config import DATA_DIR, settings

logger = logging.getLogger(__name__)

CACHE_DIR = DATA_DIR / "series_cache"
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds


# ---------------------------------------------------------------------------
# Per-observation transforms
# ---------------------------------------------------------------------------
# These match the transforms in data_agent.py but apply to every observation
# in the series, not just the latest value.

def _transform_level(value: float) -> float:
    """Identity — store raw value."""
    return value


def _transform_pct_to_bps(value: float) -> float:
    """BAML OAS: percentage points -> basis points."""
    return round(value * 100, 0)


def _transform_billions_to_millions(value: float) -> float:
    """FRED reports in billions, we store in millions."""
    return round(value * 1000, 0)


def _transform_millions(value: float) -> float:
    """Already in millions, just round."""
    return round(value, 0)


_TRANSFORMS = {
    "level": _transform_level,
    "pct_to_bps": _transform_pct_to_bps,
    "billions_to_millions": _transform_billions_to_millions,
    "millions": _transform_millions,
}


def _transform_ism_from_employment(values: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Manufacturing employment -> ISM proxy (needs rolling window).

    MANEMP is in thousands. 3-month change maps to ISM:
    50 + (change_3m / 10). Clamped to [30, 70].
    """
    if len(values) < 4:
        return []
    result = []
    for i in range(3, len(values)):
        current = values[i][1]
        three_ago = values[i - 3][1]
        change = current - three_ago
        proxy = 50 + (change / 10)
        proxy = max(30, min(70, proxy))
        result.append((values[i][0], round(proxy, 1)))
    return result


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def _cache_path(series_id: str) -> Path:
    """Path for cached CSV file."""
    safe_name = series_id.replace("=", "_").replace("^", "_").replace(".", "_")
    return CACHE_DIR / f"fred_{safe_name}.csv"


def _read_cache(series_id: str, max_age_hours: float = 24.0) -> Optional[list[tuple[str, float]]]:
    """Read cached series if fresh enough."""
    path = _cache_path(series_id)
    if not path.exists():
        return None

    # Check freshness
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age_hours = (datetime.now() - mtime).total_seconds() / 3600
    if age_hours > max_age_hours:
        logger.debug(f"Cache expired for {series_id} ({age_hours:.1f}h old)")
        return None

    try:
        rows = []
        with open(path) as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                rows.append((row[0], float(row[1])))
        logger.debug(f"Cache hit for {series_id}: {len(rows)} observations")
        return rows
    except Exception as e:
        logger.warning(f"Cache read failed for {series_id}: {e}")
        return None


def _write_cache(series_id: str, data: list[tuple[str, float]]) -> None:
    """Write series data to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(series_id)
    try:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "value"])
            for date_str, value in data:
                writer.writerow([date_str, value])
        logger.debug(f"Cached {series_id}: {len(data)} observations")
    except Exception as e:
        logger.warning(f"Cache write failed for {series_id}: {e}")


# ---------------------------------------------------------------------------
# FRED API fetch
# ---------------------------------------------------------------------------

def fetch_fred_series(
    series_id: str,
    transform: str = "level",
    lookback_years: int = 3,
    use_cache: bool = True,
    cache_max_age_hours: float = 24.0,
) -> Optional[list[tuple[str, float]]]:
    """Fetch a FRED series as (date, transformed_value) pairs.

    Args:
        series_id: FRED series identifier (e.g., "UNRATE", "FEDFUNDS")
        transform: per-observation transform to apply
        lookback_years: how many years of history to fetch
        use_cache: whether to check/write cache
        cache_max_age_hours: max cache age before refetching

    Returns:
        List of (YYYY-MM-DD, float) pairs sorted oldest-first,
        or None on failure.
    """
    cache_key = f"{series_id}_{transform}"

    if use_cache:
        cached = _read_cache(cache_key, cache_max_age_hours)
        if cached is not None:
            return cached

    if not settings.fred_api_key:
        logger.error("FRED_API_KEY not set — cannot fetch %s", series_id)
        return None

    from fredapi import Fred
    fred = Fred(api_key=settings.fred_api_key)

    start_date = (date.today() - timedelta(days=lookback_years * 365)).isoformat()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = fred.get_series(series_id, observation_start=start_date)
            if raw is None or len(raw) == 0:
                logger.warning(f"FRED {series_id}: empty response")
                return None

            raw = raw.dropna()
            if len(raw) == 0:
                logger.warning(f"FRED {series_id}: all NaN after dropna")
                return None

            # Convert to (date_str, value) pairs
            pairs = [
                (idx.strftime("%Y-%m-%d"), float(val))
                for idx, val in raw.items()
            ]

            # Apply per-observation transform
            if transform == "ism_from_employment":
                pairs = _transform_ism_from_employment(pairs)
            else:
                fn = _TRANSFORMS.get(transform, _transform_level)
                pairs = [(d, fn(v)) for d, v in pairs]

            if use_cache:
                _write_cache(cache_key, pairs)

            logger.info(f"FRED {series_id}: {len(pairs)} observations ({pairs[0][0]} to {pairs[-1][0]})")
            return pairs

        except Exception as e:
            logger.warning(f"FRED {series_id} attempt {attempt}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    logger.error(f"FRED {series_id}: all {MAX_RETRIES} attempts failed")
    return None


def fetch_all_fred_series(
    series_map: dict[str, tuple[str, int]],
    use_cache: bool = True,
) -> dict[str, list[tuple[str, float]]]:
    """Fetch multiple FRED series.

    Args:
        series_map: {fred_series_id: (transform, lookback_years)}
        use_cache: whether to use caching

    Returns:
        {fred_series_id: [(date, value), ...]} for successful fetches.
    """
    results = {}
    for series_id, (transform, years) in series_map.items():
        data = fetch_fred_series(series_id, transform, years, use_cache)
        if data:
            results[series_id] = data
        else:
            logger.warning(f"Skipping {series_id} (fetch failed)")
    return results
