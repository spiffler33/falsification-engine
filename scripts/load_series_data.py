#!/usr/bin/env python3
"""Load time-series data into InMemorySeriesStore.

Orchestrates:
  1. Fetch raw FRED + Yahoo series (or read from cache)
  2. Compute derived series (curve_2s10s, net_liquidity, etc.)
  3. Populate InMemorySeriesStore
  4. Report loaded/failed/missing fields

Usage:
  python -m scripts.load_series_data              # fetch live, cache results
  python -m scripts.load_series_data --cached      # use cached data only
  python -m scripts.load_series_data --report      # just report what's available

The populated store can be used by the compiled evaluator:
  store = load_series_store()
  evaluator = CompiledActivationEvaluator(briefing, registry, series_store=store)
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engine.v9.series_store import InMemorySeriesStore
from backend.engine.field_source_mapping import (
    FIELD_SOURCES,
    SourceType,
    get_all_required_fred_series,
    get_all_required_yahoo_tickers,
)
from backend.engine.fred_series_fetcher import fetch_fred_series
from backend.engine.yahoo_series_fetcher import (
    fetch_yahoo_series,
    fetch_yahoo_ratio,
    fetch_yahoo_rolling_return,
    fetch_yahoo_rolling_return_diff,
)

logger = logging.getLogger(__name__)

# Known annual values for web-sourced fields without historical APIs
_CB_GOLD_PURCHASES_ANNUAL = {
    "2020-12-31": 255,
    "2021-12-31": 463,
    "2022-12-31": 1082,
    "2023-12-31": 1037,
    "2024-12-31": 1045,
}


# ---------------------------------------------------------------------------
# Computed series derivation
# ---------------------------------------------------------------------------

def _compute_curve_2s10s(
    fred_raw: dict[str, list[tuple[str, float]]],
) -> list[tuple[str, float]] | None:
    """Compute 2s10s yield curve spread from DGS10 - DGS2."""
    dgs10 = fred_raw.get("DGS10")
    dgs2 = fred_raw.get("DGS2")
    if not dgs10 or not dgs2:
        return None

    map_10 = dict(dgs10)
    map_2 = dict(dgs2)
    common = sorted(set(map_10.keys()) & set(map_2.keys()))
    return [(d, round(map_10[d] - map_2[d], 2)) for d in common]


def _compute_net_liquidity_30d_change(
    store: InMemorySeriesStore,
) -> list[tuple[str, float]] | None:
    """Compute 30d change in net liquidity (Fed BS - TGA - RRP).

    Uses already-loaded series from the store.
    """
    if not all(store.has_series(f) for f in
               ["liquidity.fed_balance_sheet", "liquidity.tga", "liquidity.reverse_repo"]):
        return None

    from backend.schemas.v9.units import TimeUnit, TimeWindow
    # Get full series
    bs = store.get_series("liquidity.fed_balance_sheet", TimeWindow(value=5, unit=TimeUnit.YEARS))
    tga = store.get_series("liquidity.tga", TimeWindow(value=5, unit=TimeUnit.YEARS))
    rrp = store.get_series("liquidity.reverse_repo", TimeWindow(value=5, unit=TimeUnit.YEARS))

    if not bs or not tga or not rrp:
        return None

    # Build date-aligned maps
    map_bs = dict(zip(bs.timestamps, bs.values))
    map_tga = dict(zip(tga.timestamps, tga.values))
    map_rrp = dict(zip(rrp.timestamps, rrp.values))

    common = sorted(set(map_bs.keys()) & set(map_tga.keys()) & set(map_rrp.keys()))
    if len(common) < 2:
        return None

    # Net liquidity series
    net_liq = [(d, map_bs[d] - map_tga[d] - map_rrp[d]) for d in common]

    # 30d change: for each point, subtract the value ~30 days earlier
    result = []
    for i, (d, val) in enumerate(net_liq):
        # Find point ~30 days back
        target = date.fromisoformat(d) - timedelta(days=30)
        target_str = target.isoformat()
        # Find nearest earlier date
        past_val = None
        for j in range(i - 1, -1, -1):
            if net_liq[j][0] <= target_str:
                past_val = net_liq[j][1]
                break
        if past_val is not None:
            result.append((d, round(val - past_val, 0)))

    return result


def _compute_foreign_treasury_pct(
    fred_raw: dict[str, list[tuple[str, float]]],
) -> list[tuple[str, float]] | None:
    """Compute foreign treasury holdings as % of total outstanding.

    FDHBFIN ($B) / (GFDEBTN ($M) / 1000) * 100
    """
    fdhbfin = fred_raw.get("FDHBFIN")
    gfdebtn = fred_raw.get("GFDEBTN")
    if not fdhbfin or not gfdebtn:
        return None

    map_fh = dict(fdhbfin)
    map_td = dict(gfdebtn)
    common = sorted(set(map_fh.keys()) & set(map_td.keys()))
    result = []
    for d in common:
        total_B = map_td[d] / 1000  # $M -> $B
        if total_B > 0:
            result.append((d, round((map_fh[d] / total_B) * 100, 1)))
    return result


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load_series_store(
    use_cache: bool = True,
    cache_max_age_hours: float = 168.0,  # 1 week default for series
) -> tuple[InMemorySeriesStore, dict]:
    """Load all available time-series data into an InMemorySeriesStore.

    Returns:
        (store, report) where report has keys:
          loaded: list of field_ids successfully loaded
          failed: list of (field_id, reason) for failures
          skipped: list of (field_id, reason) for web-sourced fields
    """
    store = InMemorySeriesStore()
    report = {"loaded": [], "failed": [], "skipped": []}

    # --- Phase 1: Fetch raw FRED series ---
    fred_raw: dict[str, list[tuple[str, float]]] = {}
    all_fred = get_all_required_fred_series()

    for series_id, lookback_years in all_fred.items():
        # Find the transform for this series
        transform = "level"
        for fs in FIELD_SOURCES.values():
            if fs.fred_series == series_id:
                transform = fs.fred_transform
                break

        data = fetch_fred_series(
            series_id, transform, lookback_years,
            use_cache=use_cache,
            cache_max_age_hours=cache_max_age_hours,
        )
        if data:
            fred_raw[series_id] = data

    # --- Phase 2: Fetch raw Yahoo series ---
    yahoo_raw: dict[str, list[tuple[str, float]]] = {}
    all_yahoo = get_all_required_yahoo_tickers()

    for ticker in sorted(all_yahoo):
        data = fetch_yahoo_series(
            ticker, lookback_years=3,
            use_cache=use_cache,
            cache_max_age_hours=cache_max_age_hours,
        )
        if data:
            yahoo_raw[ticker] = data

    # --- Phase 3: Populate store from field mapping ---
    for field_id, fs in FIELD_SOURCES.items():

        if fs.source_type in (SourceType.FRED_DIRECT, SourceType.FRED_TRANSFORMED):
            if fs.fred_series and fs.fred_series in fred_raw:
                data = fred_raw[fs.fred_series]
                store.add_series(field_id, [d for d, _ in data], [v for _, v in data])
                report["loaded"].append(field_id)
            else:
                report["failed"].append((field_id, f"FRED {fs.fred_series} not available"))

        elif fs.source_type == SourceType.YAHOO_PRICE:
            ticker = fs.yahoo_tickers[0] if fs.yahoo_tickers else None
            if ticker and ticker in yahoo_raw:
                data = yahoo_raw[ticker]
                store.add_series(field_id, [d for d, _ in data], [v for _, v in data])
                report["loaded"].append(field_id)
            else:
                report["failed"].append((field_id, f"Yahoo {ticker} not available"))

        elif fs.source_type == SourceType.YAHOO_RATIO:
            if len(fs.yahoo_tickers) >= 2:
                data = fetch_yahoo_ratio(
                    fs.yahoo_tickers[0], fs.yahoo_tickers[1],
                    use_cache=use_cache,
                )
                if data:
                    store.add_series(field_id, [d for d, _ in data], [v for _, v in data])
                    report["loaded"].append(field_id)
                else:
                    report["failed"].append((field_id, f"Yahoo ratio {fs.yahoo_tickers} failed"))
            else:
                report["failed"].append((field_id, "Not enough tickers for ratio"))

        elif fs.source_type == SourceType.COMPUTED_FROM_YAHOO:
            if field_id == "eem_spy_3m_relative":
                data = fetch_yahoo_rolling_return_diff(
                    "EEM", "SPY", window_days=63,
                    use_cache=use_cache,
                )
            elif field_id == "commodity_index_3m_change":
                data = fetch_yahoo_rolling_return(
                    "DBC", window_days=63,
                    use_cache=use_cache,
                )
            else:
                data = None

            if data:
                store.add_series(field_id, [d for d, _ in data], [v for _, v in data])
                report["loaded"].append(field_id)
            else:
                report["failed"].append((field_id, "Yahoo computed series failed"))

        elif fs.source_type == SourceType.COMPUTED_FROM_FRED:
            # Defer — handled in Phase 4
            pass

        elif fs.source_type == SourceType.WEB_SOURCED:
            if field_id == "cb_gold_purchases":
                dates = sorted(_CB_GOLD_PURCHASES_ANNUAL.keys())
                values = [_CB_GOLD_PURCHASES_ANNUAL[d] for d in dates]
                store.add_series(field_id, dates, values)
                report["loaded"].append(field_id)
            else:
                report["skipped"].append((field_id, f"Web-sourced, no historical API ({fs.note})"))

    # --- Phase 4: Compute derived series ---

    # rates.curve_2s10s
    curve = _compute_curve_2s10s(fred_raw)
    if curve:
        store.add_series("rates.curve_2s10s",
                         [d for d, _ in curve], [v for _, v in curve])
        report["loaded"].append("rates.curve_2s10s")
    else:
        report["failed"].append(("rates.curve_2s10s", "Missing DGS10 or DGS2"))

    # sloos_net_tightening (passthrough from credit.sloos_tightening_ci)
    if store.has_series("credit.sloos_tightening_ci"):
        from backend.schemas.v9.units import TimeUnit, TimeWindow
        sloos = store.get_series("credit.sloos_tightening_ci", TimeWindow(value=5, unit=TimeUnit.YEARS))
        if sloos:
            store.add_series("sloos_net_tightening", sloos.timestamps, sloos.values)
            report["loaded"].append("sloos_net_tightening")
    else:
        report["failed"].append(("sloos_net_tightening", "Missing credit.sloos_tightening_ci"))

    # net_liquidity_30d_change
    net_liq = _compute_net_liquidity_30d_change(store)
    if net_liq:
        store.add_series("net_liquidity_30d_change",
                         [d for d, _ in net_liq], [v for _, v in net_liq])
        report["loaded"].append("net_liquidity_30d_change")
    else:
        report["failed"].append(("net_liquidity_30d_change", "Missing liquidity components"))

    # foreign_treasury_holdings_pct
    ftp = _compute_foreign_treasury_pct(fred_raw)
    if ftp:
        store.add_series("foreign_treasury_holdings_pct",
                         [d for d, _ in ftp], [v for _, v in ftp])
        report["loaded"].append("foreign_treasury_holdings_pct")
    else:
        report["failed"].append(("foreign_treasury_holdings_pct", "Missing FDHBFIN or GFDEBTN"))

    return store, report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_report(report: dict, store: InMemorySeriesStore) -> None:
    """Print human-readable report."""
    print("\n" + "=" * 60)
    print("  SERIES DATA LOAD REPORT")
    print("=" * 60)

    print(f"\n  Loaded: {len(report['loaded'])} fields")
    for fid in sorted(report["loaded"]):
        n = store.series_length(fid)
        print(f"    {fid}: {n} observations")

    if report["failed"]:
        print(f"\n  Failed: {len(report['failed'])} fields")
        for fid, reason in sorted(report["failed"]):
            print(f"    {fid}: {reason}")

    if report["skipped"]:
        print(f"\n  Skipped (web-sourced): {len(report['skipped'])} fields")
        for fid, reason in sorted(report["skipped"]):
            print(f"    {fid}: {reason}")

    total = len(FIELD_SOURCES)
    loaded = len(report["loaded"])
    print(f"\n  Coverage: {loaded}/{total} fields ({loaded/total*100:.0f}%)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Load series data into InMemorySeriesStore")
    parser.add_argument("--cached", action="store_true",
                        help="Use only cached data (no API calls)")
    parser.add_argument("--report", action="store_true",
                        help="Just report what cached data is available")
    parser.add_argument("--max-age", type=float, default=168.0,
                        help="Max cache age in hours (default: 168 = 1 week)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.cached:
        # Force very large max_age so we use whatever is cached
        cache_hours = 999999.0
    else:
        cache_hours = args.max_age

    store, report = load_series_store(
        use_cache=True,
        cache_max_age_hours=cache_hours,
    )

    _print_report(report, store)


if __name__ == "__main__":
    main()
