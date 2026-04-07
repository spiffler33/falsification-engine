"""v9 Compiler Spike — main orchestration script.

Compiles pilot theories via Haiku, validates artifacts, evaluates against
frozen briefing, compares to legacy results, and reports findings.

Usage:
    python -m scripts.v9_compile_spike
    python -m scripts.v9_compile_spike --all             # compile all 8 theories
    python -m scripts.v9_compile_spike --repeatability   # run 3x for stability test
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Load .env if available
_env_path = Path(__file__).resolve().parents[1] / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

from backend.engine.theory_loader import load_all_theory_packages, parse_activation_table
from backend.engine.activation import score_all_packages
from backend.schemas.briefing import BriefingPacket
from backend.engine.v9_spike.haiku_compiler import HaikuCompiler
from backend.engine.v9_spike.validator import validate_compiled_theory
from backend.engine.v9_spike.evaluator import evaluate_theory

BRIEFING_PATH = Path(__file__).resolve().parents[1] / "mock_data" / "briefing_packet.json"
PILOT_THEORIES = ["valuation_mean_reversion", "debt_cycle_short"]


def load_briefing() -> BriefingPacket:
    with open(BRIEFING_PATH) as f:
        return BriefingPacket(**json.load(f))


def get_packages(all_theories=False):
    """Load theory packages. If all_theories, return all 8; else only pilots."""
    all_pkgs = load_all_theory_packages()
    if all_theories:
        return all_pkgs
    return [p for p in all_pkgs if p.theory_id in PILOT_THEORIES]


def run_legacy_scoring(packages, briefing):
    """Run the legacy activation engine for comparison baseline."""
    results = score_all_packages(packages, briefing)
    return {r.theory_id: r for r in results}


def compile_and_validate(compiler, pkg):
    """Compile a single theory and validate the artifact."""
    entries = parse_activation_table(pkg.activation)
    artifact = compiler.compile_theory(pkg.theory_id, entries)
    report = validate_compiled_theory(artifact)
    return artifact, report, entries


def compare_results(legacy_result, compiled_eval, theory_id):
    """Compare legacy vs compiled evaluation results."""
    comparisons = []

    # Build legacy indicator lookup
    legacy_indicators = legacy_result.indicator_results

    for phase_result in compiled_eval.phase_results:
        for ir in phase_result.indicator_results:
            legacy = legacy_indicators.get(ir.indicator_name)
            if legacy is None:
                comparisons.append({
                    "indicator": ir.indicator_name,
                    "phase": phase_result.phase_label,
                    "status": "NOT_IN_LEGACY",
                    "compiled_triggered": ir.triggered,
                    "compiled_value": ir.value,
                })
                continue

            legacy_triggered = legacy.get("triggered", False)
            legacy_value = legacy.get("value")

            if ir.triggered is None:
                status = "NOT_EVALUABLE"
            elif ir.triggered == legacy_triggered:
                status = "MATCH"
            else:
                status = "MISMATCH"

            comparisons.append({
                "indicator": ir.indicator_name,
                "phase": phase_result.phase_label,
                "status": status,
                "compiled_triggered": ir.triggered,
                "legacy_triggered": legacy_triggered,
                "compiled_value": ir.value,
                "legacy_value": legacy_value,
                "detail": ir.detail if status == "MISMATCH" else {},
            })

    return comparisons


def print_section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def main():
    repeatability = "--repeatability" in sys.argv
    all_theories = "--all" in sys.argv
    n_runs = 3 if repeatability else 1

    print_section("v9 HAIKU COMPILER SPIKE")
    mode = "ALL 8 theories" if all_theories else f"Pilots: {PILOT_THEORIES}"
    print(f"Mode: {mode}")
    print(f"Briefing: {BRIEFING_PATH}")
    print(f"Repeatability runs: {n_runs}")

    # Load briefing and packages
    briefing = load_briefing()
    packages = get_packages(all_theories=all_theories)
    print(f"Loaded {len(packages)} packages")

    # Run legacy scoring for baseline
    print_section("LEGACY BASELINE")
    legacy_results = run_legacy_scoring(packages, briefing)
    for tid, result in legacy_results.items():
        if result.is_two_phase:
            for label, score in result.phase_scores.items():
                tier = result.phase_tiers.get(label, "?")
                print(f"  {tid}/{label}: {score:.4f} ({tier.value if hasattr(tier, 'value') else tier})")
        else:
            print(f"  {tid}: {result.score:.4f} ({result.tier.value})")

    # Compile and evaluate
    all_run_results = []
    for run_idx in range(n_runs):
        if n_runs > 1:
            print_section(f"COMPILATION RUN {run_idx + 1}/{n_runs}")
        else:
            print_section("HAIKU COMPILATION")

        compiler = HaikuCompiler()
        run_data = {}

        for pkg in packages:
            print(f"\n--- Compiling: {pkg.theory_id} ---")
            artifact, val_report, entries = compile_and_validate(compiler, pkg)

            # Print compilation stats
            print(f"  Total indicators: {artifact.total_indicators}")
            print(f"  Clean: {artifact.clean_count}")
            print(f"  With warnings: {artifact.warning_count}")
            print(f"  Blocked: {artifact.blocked_count}")

            # Print validation
            print(f"\n  Validation: {'PASS' if val_report.passed else 'FAIL'}")
            print(f"  Errors: {val_report.error_count}, Warnings: {val_report.warning_count}, Info: {val_report.info_count}")
            for finding in val_report.findings:
                print(f"    {finding!r}")

            # Evaluate against briefing
            eval_result = evaluate_theory(artifact, briefing)
            print(f"\n  Compiled evaluation:")
            for pr in eval_result.phase_results:
                print(f"    {pr.phase_label}: {pr.score:.4f} ({pr.tier})")
                for ir in pr.indicator_results:
                    status = "TRIGGERED" if ir.triggered else ("NOT_EVAL" if ir.triggered is None else "not triggered")
                    print(f"      {ir.indicator_name}: {status} (value={ir.value})")

            # Compare to legacy
            legacy = legacy_results.get(pkg.theory_id)
            if legacy:
                comparisons = compare_results(legacy, eval_result, pkg.theory_id)
                print(f"\n  Legacy comparison:")
                matches = sum(1 for c in comparisons if c["status"] == "MATCH")
                mismatches = sum(1 for c in comparisons if c["status"] == "MISMATCH")
                not_eval = sum(1 for c in comparisons if c["status"] == "NOT_EVALUABLE")
                print(f"    Matches: {matches}, Mismatches: {mismatches}, Not evaluable: {not_eval}")
                for c in comparisons:
                    if c["status"] != "MATCH":
                        print(f"    [{c['status']}] {c['indicator']}: "
                              f"compiled={c.get('compiled_triggered')}, legacy={c.get('legacy_triggered')}")

            run_data[pkg.theory_id] = {
                "artifact": artifact,
                "validation": val_report,
                "eval_result": eval_result,
                "comparisons": comparisons if legacy else [],
            }

        # Print cost/latency
        cost = compiler.get_cost_estimate()
        print(f"\n  Cost/latency:")
        for k, v in cost.items():
            print(f"    {k}: {v}")

        all_run_results.append(run_data)

    # Repeatability analysis
    if n_runs > 1:
        print_section("REPEATABILITY ANALYSIS")
        for tid in PILOT_THEORIES:
            print(f"\n  {tid}:")
            for run_idx, run_data in enumerate(all_run_results):
                data = run_data.get(tid)
                if data:
                    art = data["artifact"]
                    ev = data["eval_result"]
                    comps = data["comparisons"]
                    matches = sum(1 for c in comps if c["status"] == "MATCH")
                    mismatches = sum(1 for c in comps if c["status"] == "MISMATCH")
                    scores = [f"{pr.phase_label}={pr.score:.4f}" for pr in ev.phase_results]
                    print(f"    Run {run_idx+1}: clean={art.clean_count} warn={art.warning_count} "
                          f"blocked={art.blocked_count} matches={matches} mismatches={mismatches} "
                          f"scores=[{', '.join(scores)}]")

    # Print per-indicator detail of compiled artifacts for the last run
    print_section("DETAILED COMPILED ARTIFACTS (last run)")
    last_run = all_run_results[-1]
    for tid in PILOT_THEORIES:
        data = last_run.get(tid)
        if not data:
            continue
        art = data["artifact"]
        print(f"\n  {tid} (model={art.compilation_model}):")
        for phase in art.phases:
            print(f"    Phase: {phase.phase_label}")
            for ind in phase.indicators:
                rule = ind.rule.active_rule()
                rule_type = rule.rule_type if rule else "empty"
                ts = " [TIME-SERIES]" if ind.requires_time_series else ""
                amb = f" [AMBIGUITY={ind.ambiguity.value}]" if ind.ambiguity != AmbiguityLevel.NONE else ""
                warns = f" WARNS={ind.compiler_warnings}" if ind.compiler_warnings else ""
                print(f"      {ind.indicator_name}: {rule_type}{ts}{amb}{warns}")
                print(f"        fields={ind.field_refs}, unit={ind.unit.value}")
                if hasattr(rule, 'field') and hasattr(rule, 'operator') and hasattr(rule, 'value'):
                    print(f"        rule: {rule.field} {rule.operator.value} {rule.value}")
                elif hasattr(rule, 'field_a'):
                    print(f"        rule: {rule.field_a} {rule.operator.value} {rule.field_b} + {rule.offset}")
                elif hasattr(rule, 'rules'):
                    print(f"        compound ({rule.operator.value}): {len(rule.rules)} sub-rules")
                    for i, sr in enumerate(rule.rules):
                        sub = sr.active_rule()
                        if sub:
                            print(f"          [{i}] {sub.rule_type}: {sub}")

    print_section("SPIKE COMPLETE")
    print("Review output above to assess compilation fidelity.")

    # Return summary data for test consumption
    return all_run_results


# Need this import at module level for the AmbiguityLevel reference in artifact printing
from backend.schemas.v9_spike.compiled_activation import AmbiguityLevel  # noqa: E402

if __name__ == "__main__":
    main()
