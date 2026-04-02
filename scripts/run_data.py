#!/usr/bin/env python3
"""CLI script: Fetch FRED + Yahoo + web data, produce briefing_packet.json.

Usage:
    python -m scripts.run_data              # fetch with cache
    python -m scripts.run_data --fresh      # force fresh fetch
    python -m scripts.run_data --skip-web   # FRED+Yahoo only (no web scraping)
    python -m scripts.run_data --summary    # print summary of latest briefing
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engine.data_agent import build_briefing, save_briefing_json
from backend.config import MOCK_DATA_DIR, DATA_DIR


def main():
    parser = argparse.ArgumentParser(description="Falsification Engine — Data Agent")
    parser.add_argument("--fresh", action="store_true", help="Force fresh fetch (ignore cache)")
    parser.add_argument("--skip-web", action="store_true", help="Skip web data agent (FRED+Yahoo only)")
    parser.add_argument("--summary", action="store_true", help="Print summary of briefing")
    parser.add_argument("--output", type=str, default=None, help="Output directory (default: mock_data/)")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 60)
    print("  FALSIFICATION ENGINE — DATA AGENT")
    print("=" * 60)
    print()

    # Build briefing
    briefing = build_briefing(use_cache=not args.fresh, skip_web=args.skip_web)

    # Save to file
    output_dir = Path(args.output) if args.output else None
    output_path = save_briefing_json(briefing, output_dir)

    # Also save to data/ for production use
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data_path = DATA_DIR / "briefing_packet.json"
    data_path.write_text(briefing.model_dump_json(indent=2))

    print()
    print(f"Briefing saved to: {output_path}")
    print(f"Also saved to:     {data_path}")
    print(f"Timestamp:         {briefing.timestamp}")
    print()

    # Print summary
    if args.summary or True:  # always print summary
        _print_summary(briefing)


def _print_summary(briefing):
    """Print a human-readable summary of the briefing packet."""
    print("-" * 60)
    print("  MACRO SUMMARY")
    print("-" * 60)

    # Growth
    print("\n  GROWTH")
    for k, v in sorted(briefing.growth.items()):
        print(f"    {k:30s} {_fmt(v)}")

    # Inflation
    print("\n  INFLATION")
    for k, v in sorted(briefing.inflation.items()):
        print(f"    {k:30s} {_fmt(v)}")

    # Rates
    print("\n  RATES")
    for k, v in sorted(briefing.rates.items()):
        print(f"    {k:30s} {_fmt(v)}")

    # Liquidity
    print("\n  LIQUIDITY")
    for k, v in sorted(briefing.liquidity.items()):
        print(f"    {k:30s} {_fmt(v)}")

    # Credit
    print("\n  CREDIT")
    for k, v in sorted(briefing.credit.items()):
        print(f"    {k:30s} {_fmt(v)}")

    # Computed
    print("\n  COMPUTED METRICS")
    for k, v in sorted(briefing.computed.items()):
        print(f"    {k:30s} {_fmt(v)}")

    # Web-sourced data
    if briefing.web_sourced:
        print("\n  WEB-SOURCED DATA")
        for k, ws in sorted(briefing.web_sourced.items()):
            conf = f"[{ws.confidence}]" if ws.confidence else ""
            print(f"    {k:30s} {_fmt(ws.value):>12s}  {conf}")
        print(f"\n    ({len(briefing.web_sourced)}/16 fields populated)")
    else:
        print("\n  WEB-SOURCED DATA")
        print("    (skipped or unavailable)")

    # Market summary (top movers)
    print("\n  MARKETS (selected)")
    key_tickers = ["SPY", "QQQ", "IWM", "TLT", "GLD", "^VIX", "DX-Y.NYB",
                   "EEM", "HYG", "DBC", "IBIT", "UUP"]
    for ticker in key_tickers:
        if ticker in briefing.markets:
            m = briefing.markets[ticker]
            price_str = f"${m.price:>10.2f}" if m.price else "       N/A"
            r1m = f"{m.return_1m:>+7.1f}%" if m.return_1m is not None else "     N/A"
            r3m = f"{m.return_3m:>+7.1f}%" if m.return_3m is not None else "     N/A"
            r12m = f"{m.return_12m:>+7.1f}%" if m.return_12m is not None else "     N/A"
            print(f"    {ticker:12s} {price_str}   1M:{r1m}  3M:{r3m}  12M:{r12m}")

    total_tickers = len(briefing.markets)
    print(f"\n    ({total_tickers} total tickers in universe)")

    print()
    print("=" * 60)


def _fmt(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if abs(v) > 1000:
            return f"{v:,.0f}"
        return f"{v:.2f}"
    return str(v)


if __name__ == "__main__":
    main()
