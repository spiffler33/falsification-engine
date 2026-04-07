"""v9 Phase 2: Full compilation, validation, parallel comparison, and semantic diff.

Usage:
    python -m scripts.v9_phase2_compile                # full run
    python -m scripts.v9_phase2_compile --save         # save artifacts to disk
    python -m scripts.v9_phase2_compile --diff-only    # only print semantic diff

This script:
  1. Builds compiled artifacts for all 8 theories
  2. Validates each artifact using the Phase 1 validator
  3. Runs legacy activation scoring as baseline
  4. Runs compiled evaluation through the Phase 1 substrate
  5. Compares results side by side
  6. Generates the semantic diff report
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Load .env if available
_env_path = Path(__file__).resolve().parents[1] / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            import os
            os.environ.setdefault(key.strip(), val.strip())

from backend.schemas.briefing import BriefingPacket
from backend.engine.theory_loader import load_all_theory_packages
from backend.engine.activation import score_all_packages
from backend.engine.v9.compile_all import compile_all_theories, save_all_artifacts
from backend.engine.v9.compiler import load_all_artifacts, ARTIFACTS_DIR
from backend.engine.v9.registry_builder import build_full_registry
from backend.engine.v9.validator import ArtifactValidator
from backend.engine.v9.parallel_compare import run_parallel_comparison
from backend.engine.v9.semantic_diff import generate_full_diff, render_diff_report

BRIEFING_PATH = Path(__file__).resolve().parents[1] / "mock_data" / "briefing_packet.json"


def _header(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def main():
    save_mode = "--save" in sys.argv
    diff_only = "--diff-only" in sys.argv

    _header("V9 PHASE 2: COMPILATION + PARALLEL COMPARISON")

    # --- Step 1: Build artifacts ---
    _header("STEP 1: BUILD COMPILED ARTIFACTS")
    artifacts = compile_all_theories()
    print(f"Built {len(artifacts)} artifacts:")
    for tid, art in artifacts.items():
        print(f"  {tid}: {art.total_indicators} indicators "
              f"(clean={art.clean_count}, warn={art.warning_count}, blocked={art.blocked_count})")

    total_indicators = sum(a.total_indicators for a in artifacts.values())
    total_clean = sum(a.clean_count for a in artifacts.values())
    total_warn = sum(a.warning_count for a in artifacts.values())
    total_blocked = sum(a.blocked_count for a in artifacts.values())
    print(f"\nTotals: {total_indicators} indicators, "
          f"{total_clean} clean, {total_warn} warnings, {total_blocked} blocked")

    # --- Step 2: Save artifacts ---
    if save_mode:
        _header("STEP 2: SAVE ARTIFACTS")
        paths = save_all_artifacts(artifacts)
        for p in paths:
            print(f"  Saved: {p}")

    # --- Step 3: Validate ---
    _header("STEP 3: VALIDATE ALL ARTIFACTS")
    registry = build_full_registry()
    validator = ArtifactValidator(registry)
    validation_results = {}
    for tid, art in artifacts.items():
        report = validator.validate(art)
        validation_results[tid] = report
        status = "PASS" if report.passed else "FAIL"
        print(f"  {tid}: {status} "
              f"({report.error_count} errors, {report.warning_count} warnings)")
        if not report.passed:
            for f in report.errors():
                print(f"    [ERROR] {f.indicator_id}: [{f.error_code.value}] {f.message}")

    # --- Step 4: Legacy baseline ---
    _header("STEP 4: LEGACY BASELINE")
    with open(BRIEFING_PATH) as f:
        briefing = BriefingPacket(**json.load(f))
    packages = load_all_theory_packages()
    legacy_results = {r.theory_id: r for r in score_all_packages(packages, briefing)}

    for tid, result in legacy_results.items():
        if result.is_two_phase:
            for label, score in (result.phase_scores or {}).items():
                tier = (result.phase_tiers or {}).get(label, "?")
                tier_str = tier.value if hasattr(tier, 'value') else str(tier)
                print(f"  {tid}/{label}: {score:.4f} ({tier_str})")
        else:
            tier_str = result.tier.value if result.tier else "?"
            print(f"  {tid}: {result.score:.4f} ({tier_str})")

    # --- Step 5: Parallel comparison ---
    _header("STEP 5: PARALLEL COMPARISON")
    comparisons = run_parallel_comparison(artifacts, briefing, legacy_results)

    for tid, tc in comparisons.items():
        tier_status = "MATCH" if tc.tier_match else "MISMATCH"
        print(f"\n  {tid}: effective tier={tc.compiled_effective_tier} vs "
              f"legacy={tc.legacy_effective_tier} ({tier_status})")
        for phase in tc.phases:
            ptier = "MATCH" if phase.tier_match else "MISMATCH"
            print(f"    {phase.phase_label}: compiled={phase.compiled_score:.4f} "
                  f"({phase.compiled_tier}) vs legacy={phase.legacy_score:.4f} "
                  f"({phase.legacy_tier}) [{ptier}]")
            print(f"      matches={phase.match_count}, mismatches={phase.mismatch_count}, "
                  f"not_eval={phase.not_evaluable_count}")

    # --- Step 6: Semantic diff ---
    _header("STEP 6: SEMANTIC DIFF")
    diff = generate_full_diff(comparisons)

    print(f"Total indicators: {diff.total_indicators}")
    print(f"Mismatches: {diff.total_mismatches}")
    print(f"Justified improvements: {diff.total_justified}")
    print(f"Needs human review: {diff.total_needs_review}")
    print(f"Phase/tier matches: {diff.tier_matches}/{diff.tier_total}")

    # Print detailed diff
    report_text = render_diff_report(diff)
    if diff_only:
        print(report_text)

    # --- Summary ---
    _header("PHASE 2 SUMMARY")
    all_valid = all(r.passed for r in validation_results.values())
    print(f"Artifacts built: {len(artifacts)}")
    print(f"Artifacts valid: {sum(1 for r in validation_results.values() if r.passed)}/{len(artifacts)}")
    print(f"Validation: {'ALL PASS' if all_valid else 'SOME FAIL'}")
    print(f"Tier agreements: {diff.tier_matches}/{diff.tier_total}")
    print(f"Justified improvements: {diff.total_justified}")
    print(f"Items for human review: {diff.total_needs_review}")
    print(f"\nPhase 2 {'PASS' if diff.total_needs_review == 0 or all_valid else 'PARTIAL'}")

    return {
        "artifacts": artifacts,
        "validation": validation_results,
        "comparisons": comparisons,
        "diff": diff,
        "diff_report": report_text,
    }


if __name__ == "__main__":
    main()
