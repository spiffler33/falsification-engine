#!/usr/bin/env python
"""v8_equivalence_check.py -- Final validation for v8 migration.

Restores old theory_parser.py and old_format/ theory files from git history,
runs activation scoring through both old and new loaders on multiple briefing
packets, and prints comparison tables for human review.

Addresses two plan_v8.md checklist items:
  1. "Run activation equivalence on at least 2 different briefing packets"
  2. "2-3 comparison runs vs. old loader show substantive equivalence"

Usage:
    python -m scripts.v8_equivalence_check
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Ensure project root is importable.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.engine import activation
from backend.engine.theory_loader import load_all_theory_packages
from backend.schemas.briefing import BriefingPacket

# Commit just before Component 16 deleted old_format/ and theory_parser.py
OLD_CODE_COMMIT = "d7f3767"

# Classification from Layer 1 automated tests (test_activation_equivalence.py).
EXACT_MATCH = {"debt_cycle_short", "fiscal_dominance_liquidity", "structural_fragility"}
TIER_MATCH = {"debt_cycle_long", "monetary_architecture"}
KNOWN_DIVERGED = {
    "capital_flows", "fiscal_dominance_arithmetic", "valuation_mean_reversion",
}


# ---------------------------------------------------------------------------
# Git extraction
# ---------------------------------------------------------------------------

def _git_show_file(commit: str, path: str, dest: Path) -> None:
    """Extract a single file from git history."""
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True, cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git show failed for {path}: {result.stderr.decode()}")
    dest.write_bytes(result.stdout)


def restore_old_files(tmp_dir: Path) -> tuple[Path, Path]:
    """Extract old theory_parser.py and old_format/ theory files from git.

    Returns (parser_path, old_theories_dir).
    """
    # Extract theory_parser.py
    parser_path = tmp_dir / "theory_parser.py"
    _git_show_file(OLD_CODE_COMMIT, "backend/engine/theory_parser.py", parser_path)

    # Extract old_format/ theory files
    theories_dir = tmp_dir / "old_format"
    theories_dir.mkdir()

    result = subprocess.run(
        ["git", "ls-tree", "--name-only", OLD_CODE_COMMIT, "theories/old_format/"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            filename = Path(line).name
            dest = theories_dir / filename
            _git_show_file(OLD_CODE_COMMIT, line.strip(), dest)

    return parser_path, theories_dir


def load_old_parser(parser_path: Path):
    """Dynamically import the old theory_parser module."""
    spec = importlib.util.spec_from_file_location("old_theory_parser", parser_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Briefing packets
# ---------------------------------------------------------------------------

def load_real_briefing() -> dict:
    """Load the real briefing packet from data/."""
    path = PROJECT_ROOT / "data" / "briefing_packet.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_stress_briefing(base: dict) -> dict:
    """Build a synthetic stress-scenario briefing packet.

    Simulates a late-cycle recessionary environment with:
    - Slowing growth, rising unemployment
    - Elevated inflation (stagflation-adjacent)
    - Inverted yield curve
    - Tight credit conditions, wide spreads
    - Risk-off in equities, flight to bonds/gold
    """
    import copy
    stress = copy.deepcopy(base)

    stress["timestamp"] = "2026-04-06T00:00:00+00:00"

    # Growth: recessionary
    stress["growth"]["real_gdp"] = -0.3
    stress["growth"]["unemployment"] = 5.8
    stress["growth"]["initial_claims"] = 340000.0
    stress["growth"]["ism_proxy"] = 46.2
    stress["growth"]["nonfarm_payrolls"] = -45.0

    # Inflation: sticky-high
    stress["inflation"]["cpi_yoy"] = 4.1
    stress["inflation"]["core_pce"] = 3.9
    stress["inflation"]["breakeven_5y"] = 3.2
    stress["inflation"]["breakeven_10y"] = 2.9

    # Rates: inverted curve, fed on hold
    stress["rates"]["fed_funds"] = 5.25
    stress["rates"]["treasury_2y"] = 4.8
    stress["rates"]["treasury_10y"] = 4.2
    stress["rates"]["treasury_30y"] = 4.5
    stress["rates"]["treasury_3m"] = 5.1
    stress["rates"]["curve_2s10s"] = -0.60
    stress["rates"]["curve_3m10y"] = -0.90

    # Liquidity: tighter
    stress["liquidity"]["reverse_repo"] = 50.0
    stress["liquidity"]["tga"] = 600000.0

    # Credit: stressed
    stress["credit"]["hy_spread"] = 620.0
    stress["credit"]["ig_spread"] = 175.0

    # Computed: stress values
    stress["computed"]["real_10y"] = 0.1
    stress["computed"]["equity_risk_premium"] = -0.8
    stress["computed"]["net_liquidity_30d_change"] = -200000.0
    stress["computed"]["vix_vs_realized"] = 12.5
    stress["computed"]["spy_drawdown_from_52w_high"] = -18.5
    stress["computed"]["qqq_iwm_ratio"] = 2.6
    stress["computed"]["real_fed_funds"] = 1.35
    stress["computed"]["deficit_pace_annualized"] = 4200.0

    # Markets: risk-off
    stress["markets"]["SPY"]["price"] = 480.0
    stress["markets"]["SPY"]["return_3m"] = -22.0
    stress["markets"]["^VIX"]["price"] = 38.5
    stress["markets"]["^VIX"]["return_3m"] = 120.0
    stress["markets"]["TLT"]["return_3m"] = 8.5
    stress["markets"]["GLD"]["return_3m"] = 15.0
    stress["markets"]["HYG"]["return_3m"] = -12.0

    return stress


def build_recovery_briefing(base: dict) -> dict:
    """Build a synthetic early-recovery scenario briefing.

    Simulates a post-recession rebound with:
    - Accelerating growth off a low base
    - Falling inflation
    - Steep yield curve (fed cutting)
    - Tightening credit spreads
    - Risk-on rotation into small caps and EM
    """
    import copy
    recovery = copy.deepcopy(base)

    recovery["timestamp"] = "2026-04-06T00:00:01+00:00"

    # Growth: accelerating
    recovery["growth"]["real_gdp"] = 3.2
    recovery["growth"]["unemployment"] = 4.8
    recovery["growth"]["initial_claims"] = 220000.0
    recovery["growth"]["ism_proxy"] = 55.8
    recovery["growth"]["nonfarm_payrolls"] = 280.0

    # Inflation: falling
    recovery["inflation"]["cpi_yoy"] = 2.1
    recovery["inflation"]["core_pce"] = 2.3
    recovery["inflation"]["breakeven_5y"] = 2.2
    recovery["inflation"]["breakeven_10y"] = 2.1

    # Rates: steep curve, fed cutting
    recovery["rates"]["fed_funds"] = 3.0
    recovery["rates"]["treasury_2y"] = 3.2
    recovery["rates"]["treasury_10y"] = 4.1
    recovery["rates"]["treasury_30y"] = 4.6
    recovery["rates"]["treasury_3m"] = 3.1
    recovery["rates"]["curve_2s10s"] = 0.90
    recovery["rates"]["curve_3m10y"] = 1.00

    # Liquidity: improving
    recovery["liquidity"]["reverse_repo"] = 150.0

    # Credit: normalizing
    recovery["credit"]["hy_spread"] = 280.0
    recovery["credit"]["ig_spread"] = 75.0

    # Computed
    recovery["computed"]["real_10y"] = 2.0
    recovery["computed"]["equity_risk_premium"] = 1.2
    recovery["computed"]["net_liquidity_30d_change"] = 180000.0
    recovery["computed"]["vix_vs_realized"] = 2.0
    recovery["computed"]["spy_drawdown_from_52w_high"] = -2.5
    recovery["computed"]["qqq_iwm_ratio"] = 1.9
    recovery["computed"]["real_fed_funds"] = 0.9

    # Markets: risk-on, small cap / EM outperformance
    recovery["markets"]["SPY"]["return_3m"] = 12.0
    recovery["markets"]["IWM"]["return_3m"] = 18.0
    recovery["markets"]["EEM"]["return_3m"] = 15.0
    recovery["markets"]["^VIX"]["price"] = 14.5
    recovery["markets"]["^VIX"]["return_3m"] = -40.0
    recovery["markets"]["TLT"]["return_3m"] = 3.0
    recovery["markets"]["HYG"]["return_3m"] = 5.0

    return recovery


# ---------------------------------------------------------------------------
# Scoring + comparison
# ---------------------------------------------------------------------------

def _effective_score(ar) -> float | None:
    if ar.is_two_phase:
        if ar.phase_scores and ar.effective_phase:
            return ar.phase_scores.get(ar.effective_phase)
        return None
    return ar.score


def _effective_tier(ar) -> str:
    tier = ar.effective_tier if ar.is_two_phase else ar.tier
    return tier.value if hasattr(tier, "value") else str(tier)


def _effective_phase(ar) -> str:
    if ar.is_two_phase and ar.effective_phase:
        return ar.effective_phase
    return ""


def run_comparison(
    label: str,
    briefing_data: dict,
    old_parser_mod,
    old_theories_dir: Path,
) -> list[dict]:
    """Run old and new activation scoring on one briefing packet.

    Returns list of per-theory comparison rows.
    """
    briefing = BriefingPacket(**briefing_data)

    # Old loader
    old_theories = old_parser_mod.load_all_theories(old_theories_dir)
    old_results = activation.score_all_theories(old_theories, briefing)

    # New loader (v8 packages)
    packages = load_all_theory_packages()
    new_results = activation.score_all_packages(packages, briefing)

    old_map = {ar.theory_id: ar for ar in old_results}
    new_map = {ar.theory_id: ar for ar in new_results}

    rows = []
    for tid in sorted(set(old_map) | set(new_map)):
        old_ar = old_map.get(tid)
        new_ar = new_map.get(tid)

        old_score = _effective_score(old_ar) if old_ar else None
        new_score = _effective_score(new_ar) if new_ar else None
        old_tier = _effective_tier(old_ar) if old_ar else "N/A"
        new_tier = _effective_tier(new_ar) if new_ar else "N/A"
        old_phase = _effective_phase(old_ar) if old_ar else ""
        new_phase = _effective_phase(new_ar) if new_ar else ""

        if tid in EXACT_MATCH:
            expected = "EXACT"
        elif tid in TIER_MATCH:
            expected = "TIER"
        else:
            expected = "DIVERGED"

        score_match = (
            old_score is not None
            and new_score is not None
            and abs(old_score - new_score) < 0.001
        )
        tier_match = old_tier == new_tier

        if score_match:
            actual = "EXACT"
        elif tier_match:
            actual = "TIER"
        else:
            actual = "DIVERGED"

        ok = (
            (expected == "EXACT" and actual == "EXACT")
            or (expected == "TIER" and actual in ("EXACT", "TIER"))
            or (expected == "DIVERGED")
        )

        rows.append({
            "theory_id": tid,
            "old_score": old_score,
            "new_score": new_score,
            "old_tier": old_tier,
            "new_tier": new_tier,
            "old_phase": old_phase,
            "new_phase": new_phase,
            "expected": expected,
            "actual": actual,
            "pass": ok,
        })

    return rows


def print_comparison(label: str, rows: list[dict]) -> bool:
    """Print a comparison table. Returns True if all pass."""
    print(f"\n{'=' * 80}")
    print(f"  {label}")
    print(f"{'=' * 80}")

    hdr = (
        f"  {'Theory':<32} {'Old':>7} {'New':>7}  "
        f"{'OldTier':<10} {'NewTier':<10} {'Expect':<9} {'Actual':<9} {'Phase'}"
    )
    print(hdr)
    print("  " + "-" * 78)

    all_pass = True
    for r in rows:
        os = f"{r['old_score']:.3f}" if r["old_score"] is not None else "  N/A"
        ns = f"{r['new_score']:.3f}" if r["new_score"] is not None else "  N/A"
        mark = "OK" if r["pass"] else "**FAIL**"
        if not r["pass"]:
            all_pass = False

        phase_info = ""
        if r["old_phase"] or r["new_phase"]:
            if r["old_phase"] == r["new_phase"]:
                phase_info = r["old_phase"]
            else:
                phase_info = f"{r['old_phase']} -> {r['new_phase']}"

        print(
            f"  {r['theory_id']:<32} {os:>7} {ns:>7}  "
            f"{r['old_tier']:<10} {r['new_tier']:<10} "
            f"{r['expected']:<9} {r['actual']:<9} {phase_info}  {mark}"
        )

    status = "ALL PASS" if all_pass else "FAILURES DETECTED"
    print(f"\n  Result: {status}")
    return all_pass


def print_v8_standalone(label: str, briefing_data: dict) -> None:
    """Print v8-only activation results (no old loader comparison).

    Useful for verifying that the new scoring produces sensible results
    on synthetic data even where old-vs-new comparison isn't meaningful.
    """
    briefing = BriefingPacket(**briefing_data)
    packages = load_all_theory_packages()
    results = activation.score_all_packages(packages, briefing)

    print(f"\n{'=' * 80}")
    print(f"  {label} (v8 standalone)")
    print(f"{'=' * 80}")

    hdr = f"  {'Theory':<32} {'Score':>7}  {'Tier':<10} {'Phase'}"
    print(hdr)
    print("  " + "-" * 60)

    for ar in sorted(results, key=lambda x: x.theory_id):
        score = _effective_score(ar)
        tier = _effective_tier(ar)
        phase = _effective_phase(ar)
        ss = f"{score:.3f}" if score is not None else "  N/A"
        print(f"  {ar.theory_id:<32} {ss:>7}  {tier:<10} {phase}")

    active = [ar for ar in results if _effective_tier(ar) == "Active"]
    adjacent = [ar for ar in results if _effective_tier(ar) == "Adjacent"]
    inactive = [ar for ar in results if _effective_tier(ar) == "Inactive"]
    print(f"\n  Active: {len(active)}  Adjacent: {len(adjacent)}  Inactive: {len(inactive)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("v8 Equivalence Check")
    print("=" * 80)
    print(f"Restoring old code from git commit {OLD_CODE_COMMIT}...")

    tmp_dir = Path(tempfile.mkdtemp(prefix="v8_equiv_"))

    try:
        parser_path, old_theories_dir = restore_old_files(tmp_dir)
        old_count = len(list(old_theories_dir.glob("*.md")))
        print(f"  Restored theory_parser.py + {old_count} old-format theory files")

        old_parser = load_old_parser(parser_path)
        print(f"  Old parser loaded successfully")

        # Load briefing packets
        real_data = load_real_briefing()
        stress_data = build_stress_briefing(real_data)
        recovery_data = build_recovery_briefing(real_data)

        # Run 1: Real briefing (same as automated tests used)
        rows1 = run_comparison("Run 1: Real Briefing (2026-04-03)", real_data, old_parser, old_theories_dir)
        pass1 = print_comparison("Run 1: Real Briefing (2026-04-03)", rows1)

        # Run 2: Stress scenario
        rows2 = run_comparison("Run 2: Stress Scenario (synthetic)", stress_data, old_parser, old_theories_dir)
        pass2 = print_comparison("Run 2: Stress Scenario (synthetic)", rows2)

        # Run 3: Recovery scenario
        rows3 = run_comparison("Run 3: Recovery Scenario (synthetic)", recovery_data, old_parser, old_theories_dir)
        pass3 = print_comparison("Run 3: Recovery Scenario (synthetic)", rows3)

        # Standalone v8 views (so human can eyeball whether the tier
        # assignments make economic sense for each regime)
        print_v8_standalone("Run 2: Stress Scenario", stress_data)
        print_v8_standalone("Run 3: Recovery Scenario", recovery_data)

        # Summary
        print(f"\n{'=' * 80}")
        print("  SUMMARY")
        print(f"{'=' * 80}")
        print(f"  Run 1 (Real):     {'PASS' if pass1 else 'FAIL'}")
        print(f"  Run 2 (Stress):   {'PASS' if pass2 else 'FAIL'}")
        print(f"  Run 3 (Recovery): {'PASS' if pass3 else 'FAIL'}")
        all_pass = pass1 and pass2 and pass3
        print(f"\n  Overall: {'ALL PASS -- safe to check off plan_v8.md items' if all_pass else 'FAILURES -- investigate before sign-off'}")

        return 0 if all_pass else 1

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"\n  Cleaned up temp dir: {tmp_dir}")


if __name__ == "__main__":
    sys.exit(main())
