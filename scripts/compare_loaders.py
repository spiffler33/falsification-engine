#!/usr/bin/env python
"""compare_loaders.py -- Layer 4 comparison harness for v8 migration.

Run the full pipeline (activation + prompt construction) through both
the old monolithic loader and the new v8 package loader, on the same
briefing packet.  Produces:

  1. Activation score comparison table (automated, printed to stdout)
  2. Generation prompt files for human diff
  3. Elimination prompt files for human diff
  4. Structured comparison report (JSON)

Usage:
    python -m scripts.compare_loaders [--output-dir DIR]

Output goes to data/comparison/<timestamp>/ by default.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on the path for imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import DATA_DIR, MOCK_DATA_DIR, THEORIES_DIR
from backend.engine import activation, regime, theory_parser
from backend.engine.prompt_builder import (
    build_elimination_prompt,
    build_elimination_prompt_v8,
    build_generation_prompt,
    build_generation_prompt_v8,
)
from backend.engine.theory_loader import (
    build_falsifier_registry,
    filter_interaction_matrix,
    load_all_theory_packages,
    package_to_theory_module,
    parse_interaction_matrix,
)
from backend.schemas.briefing import BriefingPacket
from backend.schemas.theory import ActivationTier


OLD_FORMAT_DIR = THEORIES_DIR / "old_format"
INTERACTION_MATRIX_PATH = THEORIES_DIR / "INTERACTION_MATRIX.md"

# Classification from Layer 1 (test_activation_equivalence.py).
EXACT_MATCH_THEORIES = {
    "debt_cycle_short",
    "fiscal_dominance_liquidity",
    "structural_fragility",
}
TIER_MATCH_THEORIES = {
    "debt_cycle_long",
    "monetary_architecture",
}
KNOWN_DIVERGED = {
    "capital_flows",
    "fiscal_dominance_arithmetic",
    "valuation_mean_reversion",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_briefing() -> dict:
    """Load the latest briefing packet (real first, then mock)."""
    for path in [DATA_DIR / "briefing_packet.json", MOCK_DATA_DIR / "briefing_packet.json"]:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("No briefing packet found in data/ or mock_data/")


def _effective_score(ar) -> float | None:
    """Extract the display score from an ActivationResult."""
    if ar.is_two_phase:
        if ar.phase_scores and ar.effective_phase:
            return ar.phase_scores.get(ar.effective_phase)
        return None
    return ar.score


def _effective_tier(ar) -> str | None:
    """Extract tier string from an ActivationResult."""
    tier = ar.effective_tier if ar.is_two_phase else ar.tier
    if tier is None:
        return None
    return tier.value if hasattr(tier, "value") else str(tier)


def compare_activation(old_results, new_results) -> list[dict]:
    """Compare activation results from both loaders, row per theory."""
    old_map = {ar.theory_id: ar for ar in old_results}
    new_map = {ar.theory_id: ar for ar in new_results}

    rows = []
    for tid in sorted(set(old_map) | set(new_map)):
        old_ar = old_map.get(tid)
        new_ar = new_map.get(tid)

        old_score = _effective_score(old_ar) if old_ar else None
        new_score = _effective_score(new_ar) if new_ar else None
        old_tier = _effective_tier(old_ar) if old_ar else None
        new_tier = _effective_tier(new_ar) if new_ar else None

        # Expected classification from Layer 1
        if tid in EXACT_MATCH_THEORIES:
            expected = "EXACT"
        elif tid in TIER_MATCH_THEORIES:
            expected = "TIER"
        else:
            expected = "DIVERGED"

        score_match = (
            old_score is not None
            and new_score is not None
            and abs(old_score - new_score) < 0.001
        )
        tier_match = old_tier == new_tier

        actual = "EXACT" if score_match else ("TIER" if tier_match else "DIVERGED")

        ok = (
            (expected == "EXACT" and actual == "EXACT")
            or (expected == "TIER" and actual in ("EXACT", "TIER"))
            or (expected == "DIVERGED")  # known; not a gate
        )

        rows.append({
            "theory_id": tid,
            "old_score": old_score,
            "new_score": new_score,
            "old_tier": old_tier,
            "new_tier": new_tier,
            "expected": expected,
            "actual": actual,
            "pass": ok,
        })

    return rows


def build_synthetic_hypotheses(activation_results) -> list[dict]:
    """Minimal synthetic hypotheses from active theories for elimination comparison.

    These exercise the elimination prompt path without needing real LLM output.
    Each references one active theory so the elimination builder pulls in that
    theory's content — enough to compare old vs. new content injection.
    """
    hypotheses = []
    for ar in activation_results:
        tier = ar.effective_tier if ar.is_two_phase else ar.tier
        if tier == ActivationTier.ACTIVE:
            hypotheses.append({
                "id": f"synthetic_{ar.theory_id}",
                "theory_id": ar.theory_id,
                "source_theory": ar.theory_id,
                "source_theories": [ar.theory_id],
                "short_name": f"Synthetic hypothesis ({ar.theory_id})",
                "full_statement": f"Synthetic hypothesis exercising {ar.theory_id} elimination path.",
                "predicted_assets": ["SPY"],
                "asset_direction": {"SPY": "SHORT"},
                "hard_falsifiers": [{"condition": "SPY exceeds all-time high"}],
                "soft_falsifiers": [
                    {"name": "test_soft", "condition": "Test condition", "severity": "minor"},
                ],
                "timeframe": "3 months",
                "resolution_channel": "",
            })
    return hypotheses


def prompt_metrics(prompt: str) -> dict:
    """Basic structural metrics for a prompt string."""
    lines = prompt.split("\n")
    sections = [ln.strip() for ln in lines if ln.startswith("## ")]
    return {
        "length_chars": len(prompt),
        "length_lines": len(lines),
        "section_count": len(sections),
        "sections": sections,
    }


def _tier_str(ar) -> str:
    tier = ar.effective_tier if ar.is_two_phase else ar.tier
    return tier.value if tier else "N/A"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_comparison(output_dir: Path | None = None) -> dict:
    """Execute the full comparison and return the structured report.

    Separated from main() so tests can call it directly without argparse.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = (output_dir or Path("data/comparison")) / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Layer 4 Comparison Harness -- {timestamp}")
    print("=" * 60)

    # ---- 1. Briefing ----
    print("\n1. Loading briefing packet...")
    briefing_data = load_briefing()
    briefing = BriefingPacket(**briefing_data)
    gen_at = briefing_data.get("metadata", {}).get("generated_at", "unknown")
    print(f"   Briefing loaded ({gen_at})")

    # ---- 2. Theories ----
    print("\n2. Loading theories...")
    old_theories = theory_parser.load_all_theories(OLD_FORMAT_DIR)
    print(f"   Old loader:  {len(old_theories)} theories from old_format/")

    packages = load_all_theory_packages()
    print(f"   New loader:  {len(packages)} packages from _v2/ directories")

    adapted = [package_to_theory_module(pkg) for pkg in packages]
    print(f"   Adapter:     {len(adapted)} TheoryModule objects via adapter")

    # ---- 3. Activation ----
    print("\n3. Running activation scoring...")
    old_activation = activation.score_all_theories(old_theories, briefing)
    new_activation = activation.score_all_theories(adapted, briefing)

    # ---- 4. Activation comparison ----
    print("\n4. Activation comparison:")
    comparison = compare_activation(old_activation, new_activation)

    hdr = (
        f"   {'Theory':<35} {'Old':>7} {'New':>7} "
        f"{'OldTier':<10} {'NewTier':<10} {'Expect':<10} {'Actual':<10} OK"
    )
    print(hdr)
    print("   " + "-" * (len(hdr) - 3))

    all_pass = True
    for row in comparison:
        os = f"{row['old_score']:.3f}" if row["old_score"] is not None else "  N/A"
        ns = f"{row['new_score']:.3f}" if row["new_score"] is not None else "  N/A"
        mark = "OK" if row["pass"] else "FAIL"
        if not row["pass"]:
            all_pass = False
        print(
            f"   {row['theory_id']:<35} {os:>7} {ns:>7} "
            f"{(row['old_tier'] or 'N/A'):<10} {(row['new_tier'] or 'N/A'):<10} "
            f"{row['expected']:<10} {row['actual']:<10} {mark}"
        )

    status = "ALL PASS" if all_pass else "FAILURES DETECTED"
    print(f"\n   Activation comparison: {status}")

    # ---- 5. Regime flags ----
    old_status_map = {ar.theory_id: _tier_str(ar) for ar in old_activation}
    new_status_map = {ar.theory_id: _tier_str(ar) for ar in new_activation}
    old_flags = regime.compute_regime_flags(old_status_map)
    new_flags = regime.compute_regime_flags(new_status_map)

    # ---- 6. Generation prompts ----
    print("\n5. Building generation prompts...")
    gen_old = build_generation_prompt(
        theories=old_theories,
        activation_results=old_activation,
        briefing=briefing_data,
        inbox_items=[],
        active_regime_flags=old_flags,
    )

    # Load interaction matrix for the v8 path.
    interaction_matrix = None
    if INTERACTION_MATRIX_PATH.exists():
        matrix_text = INTERACTION_MATRIX_PATH.read_text(encoding="utf-8")
        known_ids = {pkg.theory_id for pkg in packages}
        interaction_matrix = parse_interaction_matrix(matrix_text, known_ids)
        active_ids = {
            ar.theory_id
            for ar in new_activation
            if (ar.effective_tier if ar.is_two_phase else ar.tier) == ActivationTier.ACTIVE
        }
        interaction_matrix = filter_interaction_matrix(interaction_matrix, active_ids)

    gen_new = build_generation_prompt_v8(
        packages=packages,
        activation_results=new_activation,
        briefing=briefing_data,
        inbox_items=[],
        interaction_matrix=interaction_matrix,
        active_regime_flags=new_flags,
    )

    gen_old_m = prompt_metrics(gen_old)
    gen_new_m = prompt_metrics(gen_new)
    print(
        f"   Old: {gen_old_m['length_chars']:,} chars, "
        f"{gen_old_m['length_lines']} lines, {gen_old_m['section_count']} sections"
    )
    print(
        f"   New: {gen_new_m['length_chars']:,} chars, "
        f"{gen_new_m['length_lines']} lines, {gen_new_m['section_count']} sections"
    )

    old_secs = set(gen_old_m["sections"])
    new_secs = set(gen_new_m["sections"])
    only_old = sorted(old_secs - new_secs)
    only_new = sorted(new_secs - old_secs)
    if only_old:
        print(f"   Sections only in old: {only_old}")
    if only_new:
        print(f"   Sections only in new: {only_new}")
    if not only_old and not only_new:
        print("   Section headers: identical")

    # ---- 7. Elimination prompts ----
    print("\n6. Building elimination prompts...")
    synthetic_hyps = build_synthetic_hypotheses(new_activation)
    print(f"   Synthetic hypotheses: {len(synthetic_hyps)} (from active theories)")

    elim_old = build_elimination_prompt(
        hypotheses=synthetic_hyps,
        theories=old_theories,
        activation_results=old_activation,
        briefing=briefing_data,
    )

    # Ensure falsifier registries are populated for v8 elimination.
    for pkg in packages:
        if not pkg.falsifier_registry:
            pkg.falsifier_registry = build_falsifier_registry(pkg.core, pkg.activation)

    elim_new = build_elimination_prompt_v8(
        hypotheses=synthetic_hyps,
        packages=packages,
        activation_results=new_activation,
        briefing=briefing_data,
        interaction_matrix=interaction_matrix,
    )

    elim_old_m = prompt_metrics(elim_old)
    elim_new_m = prompt_metrics(elim_new)
    print(
        f"   Old: {elim_old_m['length_chars']:,} chars, "
        f"{elim_old_m['length_lines']} lines, {elim_old_m['section_count']} sections"
    )
    print(
        f"   New: {elim_new_m['length_chars']:,} chars, "
        f"{elim_new_m['length_lines']} lines, {elim_new_m['section_count']} sections"
    )

    # ---- 8. Write output files ----
    print(f"\n7. Writing output files to {out_dir}/")

    (out_dir / "generation_old.txt").write_text(gen_old, encoding="utf-8")
    (out_dir / "generation_new.txt").write_text(gen_new, encoding="utf-8")
    (out_dir / "elimination_old.txt").write_text(elim_old, encoding="utf-8")
    (out_dir / "elimination_new.txt").write_text(elim_new, encoding="utf-8")

    report = {
        "timestamp": timestamp,
        "briefing_generated_at": gen_at,
        "theory_counts": {
            "old_loader": len(old_theories),
            "new_loader": len(packages),
            "adapter": len(adapted),
        },
        "activation_comparison": comparison,
        "activation_all_pass": all_pass,
        "regime_flags": {
            "old": [f["flag_id"] for f in old_flags],
            "new": [f["flag_id"] for f in new_flags],
        },
        "generation_prompt": {
            "old": gen_old_m,
            "new": gen_new_m,
            "sections_only_in_old": only_old,
            "sections_only_in_new": only_new,
        },
        "elimination_prompt": {
            "old": elim_old_m,
            "new": elim_new_m,
            "synthetic_hypothesis_count": len(synthetic_hyps),
        },
    }
    (out_dir / "comparison_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )

    for name in [
        "generation_old.txt",
        "generation_new.txt",
        "elimination_old.txt",
        "elimination_new.txt",
        "comparison_report.json",
    ]:
        print(f"   {name}")

    print(f"\n{'=' * 60}")
    print("Layer 4 comparison complete.")
    print(f"Review: diff {out_dir}/generation_old.txt {out_dir}/generation_new.txt")
    print(f"        diff {out_dir}/elimination_old.txt {out_dir}/elimination_new.txt")

    return report


def main():
    parser = argparse.ArgumentParser(description="Layer 4: Compare old and v8 loaders")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/comparison"),
        help="Directory for output files (default: data/comparison)",
    )
    args = parser.parse_args()
    report = run_comparison(output_dir=args.output_dir)
    return 0 if report.get("activation_all_pass") else 1


if __name__ == "__main__":
    sys.exit(main())
