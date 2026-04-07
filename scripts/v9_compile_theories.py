#!/usr/bin/env python3
"""v9 Phase 3.5: Compile theory ACTIVATION.md files via Haiku API.

Reads English activation indicator tables from theory modules, sends them
to Claude Haiku for semantic compilation into Phase 0 schema artifacts,
validates the output, and writes artifacts to artifacts/v9/.

This is the canonical compilation entrypoint for the v9 architecture.
It replaces the hand-authored definitions in compile_all.py.

Usage:
    python -m scripts.v9_compile_theories --all
    python -m scripts.v9_compile_theories --theory valuation_mean_reversion
    python -m scripts.v9_compile_theories --all --dry-run
    python -m scripts.v9_compile_theories --all --diff
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Load .env before any other imports that might need it
from dotenv import load_dotenv
load_dotenv()

from backend.engine.v9.activation_parser import (
    ALL_THEORY_IDS,
    TWO_PHASE_THEORIES,
    get_activation_path,
    parse_activation_md,
)
from backend.engine.v9.compiler import (
    _parse_haiku_indicator,
    _parse_phase_key,
    load_artifact,
    make_artifact,
    make_phase,
    save_artifact,
    ARTIFACTS_DIR,
)
from backend.engine.v9.compiler_prompt import (
    build_system_prompt,
    build_user_prompt,
)
from backend.engine.v9.compiler_repairs import repair_indicators, repair_missing_indicators
from backend.engine.v9.registry_builder import build_full_registry
from backend.engine.v9.validator import ArtifactValidator
from backend.schemas.v9.compiled_activation import (
    ArtifactStatus,
    CompilationStatus,
    CompiledActivationArtifact,
    CompilerMetadata,
    PhaseModel,
    SourcePackageRef,
)
from backend.schemas.v9.errors import Severity


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_ID = "claude-haiku-4-5-20251001"
PROMPT_VERSION = "phase3_5_v1"
SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Haiku API caller
# ---------------------------------------------------------------------------

class HaikuCompiler:
    """Calls the Haiku API to compile indicator batches."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Set it in .env or environment."
            )
        self._client = None
        self.stats = {
            "calls": 0, "input_tokens": 0, "output_tokens": 0,
            "latencies": [], "errors": 0,
        }

    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def compile_batch(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> list[dict]:
        """Send a batch to Haiku and return parsed JSON indicators."""
        t0 = time.time()
        try:
            response = self.client.messages.create(
                model=MODEL_ID,
                max_tokens=8192,
                temperature=0.0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            latency = time.time() - t0
            self.stats["calls"] += 1
            self.stats["input_tokens"] += response.usage.input_tokens
            self.stats["output_tokens"] += response.usage.output_tokens
            self.stats["latencies"].append(latency)

            raw = response.content[0].text.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines)

            return json.loads(raw)

        except json.JSONDecodeError as e:
            self.stats["errors"] += 1
            print(f"  JSON parse error: {e}")
            print(f"  Raw response (first 500 chars): {raw[:500]}")
            return []
        except Exception as e:
            self.stats["errors"] += 1
            print(f"  API error: {e}")
            return []


# ---------------------------------------------------------------------------
# Theory compilation
# ---------------------------------------------------------------------------

def compile_theory(
    theory_id: str,
    compiler: HaikuCompiler,
    system_prompt: str,
    registry,
) -> tuple[CompiledActivationArtifact | None, dict]:
    """Compile a single theory via Haiku.

    Returns (artifact, report_dict) where report_dict contains
    compilation status and any issues.
    """
    report = {
        "theory_id": theory_id,
        "status": "unknown",
        "phases": [],
        "total_indicators": 0,
        "clean": 0,
        "warning": 0,
        "blocked": 0,
        "errors": [],
    }

    # Parse ACTIVATION.md
    try:
        filepath = get_activation_path(theory_id)
        parsed = parse_activation_md(filepath)
    except Exception as e:
        report["status"] = "error"
        report["errors"].append(f"Parse error: {e}")
        return None, report

    is_two_phase = parsed["is_two_phase"]
    compiled_phases = []

    for phase_data in parsed["phases"]:
        phase_key = phase_data["phase_key"]
        phase_label = phase_data["phase_label"]
        phase_id = phase_data["phase_id"]
        indicators = phase_data["indicators"]

        print(f"  Compiling {phase_label} ({len(indicators)} indicators)...")

        # Build user prompt
        user_prompt = build_user_prompt(theory_id, phase_key, indicators)

        # Call Haiku
        haiku_output = compiler.compile_batch(system_prompt, user_prompt)

        if not haiku_output:
            report["errors"].append(f"Haiku returned empty for {phase_label}")
            report["status"] = "error"
            return None, report

        # Parse Haiku output into CompiledIndicator objects
        weight_lookup = {}
        for ind in indicators:
            try:
                w = float(ind["weight"])
            except (ValueError, TypeError):
                w = 0.1
            weight_lookup[ind["indicator_name"]] = w

        compiled_indicators = []
        for item in haiku_output:
            try:
                ci = _parse_haiku_indicator(item, weight_lookup)
                compiled_indicators.append(ci)
            except Exception as e:
                report["errors"].append(
                    f"Parse error for {item.get('indicator_id', '?')}: {e}"
                )

        # Repair pass 1-2: prune UNRESOLVED clauses and illegal comparisons
        repair_log = repair_indicators(compiled_indicators, registry)
        if repair_log:
            print(f"    Repairs: {len(repair_log)} clause(s) pruned")
            for entry in repair_log:
                print(f"      {entry['indicator_id']}: {entry['repair']} ({entry['reason']})")
        report.setdefault("repairs", []).extend(repair_log)

        # Repair pass 3: inject missing indicators (Haiku systematic drops)
        missing_log = repair_missing_indicators(
            compiled_indicators, indicators, theory_id, phase_id,
        )
        if missing_log:
            print(f"    Missing indicator repairs: {len(missing_log)}")
            for entry in missing_log:
                print(f"      {entry['indicator_id']}: {entry['repair']} ({entry['reason']})")
        report.setdefault("repairs", []).extend(missing_log)

        compiled_phases.append(make_phase(phase_id, phase_label, compiled_indicators))

        # Count statuses (after repair)
        for ci in compiled_indicators:
            report["total_indicators"] += 1
            if ci.compilation_status == CompilationStatus.CLEAN:
                report["clean"] += 1
            elif ci.compilation_status == CompilationStatus.WARNING:
                report["warning"] += 1
            elif ci.compilation_status == CompilationStatus.BLOCKED:
                report["blocked"] += 1

        report["phases"].append({
            "phase_id": phase_id,
            "phase_label": phase_label,
            "indicator_count": len(compiled_indicators),
            "haiku_returned": len(haiku_output),
        })

    # Build artifact
    phase_model = PhaseModel.TWO_PHASE if is_two_phase else PhaseModel.SINGLE_PHASE
    artifact = make_artifact(
        theory_id, phase_model, compiled_phases,
        source_file=str(filepath),
    )

    # Update compiler metadata
    artifact.compiler = CompilerMetadata(
        compiler_engine="haiku_phase3_5",
        model_id=MODEL_ID,
        schema_version=SCHEMA_VERSION,
        prompt_version=PROMPT_VERSION,
        compiled_at=datetime.now(timezone.utc).isoformat(),
    )

    # Validate
    validator = ArtifactValidator(registry)
    val_report = validator.validate(artifact)

    error_count = sum(
        1 for f in val_report.findings if f.severity == Severity.ERROR
    )
    warn_count = sum(
        1 for f in val_report.findings if f.severity == Severity.WARNING
    )

    if error_count > 0:
        report["status"] = "blocked"
        report["errors"].extend(
            f"Validation: {f.error_code.value}: {f.message}"
            for f in val_report.findings if f.severity == Severity.ERROR
        )
    elif report["blocked"] > 0:
        report["status"] = "warn"
    elif report["warning"] > 0:
        report["status"] = "warn"
    else:
        report["status"] = "clean"

    report["validation_errors"] = error_count
    report["validation_warnings"] = warn_count

    return artifact, report


# ---------------------------------------------------------------------------
# Semantic diff
# ---------------------------------------------------------------------------

def _match_indicators(old_indicators, new_indicators):
    """Match indicators between old and new by primary_field + weight proximity.

    Returns list of (old_ind, new_ind) tuples. Unmatched entries have None.
    """
    matched = []
    used_new = set()

    for oi in old_indicators:
        best = None
        best_score = -1
        for j, ni in enumerate(new_indicators):
            if j in used_new:
                continue
            score = 0
            if oi.primary_field == ni.primary_field:
                score += 2
            if abs(oi.weight - ni.weight) < 0.02:
                score += 1
            if oi.display_name.lower()[:20] == ni.display_name.lower()[:20]:
                score += 1
            if score > best_score:
                best_score = score
                best = j
        if best is not None and best_score >= 2:
            matched.append((oi, new_indicators[best]))
            used_new.add(best)
        else:
            matched.append((oi, None))

    for j, ni in enumerate(new_indicators):
        if j not in used_new:
            matched.append((None, ni))

    return matched


def semantic_diff(old: CompiledActivationArtifact, new: CompiledActivationArtifact) -> list[str]:
    """Compare two artifacts and return a list of differences.

    Matches indicators by primary_field rather than indicator_id,
    since Haiku may generate different IDs than hand-authored artifacts.
    """
    diffs = []

    if len(old.phases) != len(new.phases):
        diffs.append(f"Phase count: {len(old.phases)} -> {len(new.phases)}")

    for old_phase, new_phase in zip(old.phases, new.phases):
        if old_phase.phase_id != new_phase.phase_id:
            diffs.append(
                f"Phase ID: {old_phase.phase_id} -> {new_phase.phase_id}"
            )

        pairs = _match_indicators(old_phase.indicators, new_phase.indicators)

        for oi, ni in pairs:
            if oi is None:
                diffs.append(
                    f"[{new_phase.phase_id}] ADDED: {ni.indicator_id} "
                    f"({ni.display_name})"
                )
                continue
            if ni is None:
                diffs.append(
                    f"[{old_phase.phase_id}] UNMATCHED: {oi.indicator_id} "
                    f"({oi.display_name})"
                )
                continue

            prefix = f"[{old_phase.phase_id}/{oi.primary_field}]"

            if oi.indicator_id != ni.indicator_id:
                diffs.append(
                    f"{prefix} id: {oi.indicator_id} -> {ni.indicator_id}"
                )

            if abs(oi.weight - ni.weight) > 0.001:
                diffs.append(f"{prefix} weight: {oi.weight} -> {ni.weight}")

            if oi.primary_field != ni.primary_field:
                diffs.append(
                    f"{prefix} field: {oi.primary_field} -> {ni.primary_field}"
                )

            old_rt = oi.rule.rule_type if hasattr(oi.rule, 'rule_type') else "?"
            new_rt = ni.rule.rule_type if hasattr(ni.rule, 'rule_type') else "?"
            if old_rt != new_rt:
                diffs.append(f"{prefix} rule_type: {old_rt} -> {new_rt}")

            if oi.compilation_status != ni.compilation_status:
                diffs.append(
                    f"{prefix} status: {oi.compilation_status.value} -> "
                    f"{ni.compilation_status.value}"
                )

            if oi.requires_time_series != ni.requires_time_series:
                diffs.append(
                    f"{prefix} time_series: {oi.requires_time_series} -> "
                    f"{ni.requires_time_series}"
                )

    return diffs


# ---------------------------------------------------------------------------
# Score parity check
# ---------------------------------------------------------------------------

def check_score_parity(
    theory_id: str,
    old_artifact: CompiledActivationArtifact,
    new_artifact: CompiledActivationArtifact,
) -> dict:
    """Check if new artifact produces identical scores to old artifact.

    Uses the frozen briefing packet for evaluation.
    """
    import json as _json
    from backend.engine.v9.compiled_evaluator import CompiledActivationEvaluator
    from backend.schemas.briefing import BriefingPacket

    briefing_path = Path(__file__).resolve().parent / "mock_data" / "briefing_packet.json"
    if not briefing_path.exists():
        # Try from project root
        briefing_path = Path(__file__).resolve().parents[1] / "mock_data" / "briefing_packet.json"
    if not briefing_path.exists():
        return {"parity": "skip", "reason": "No frozen briefing found"}

    briefing = BriefingPacket(**_json.loads(briefing_path.read_text()))
    registry = build_full_registry()

    evaluator = CompiledActivationEvaluator(briefing, registry)

    old_result = evaluator.evaluate(old_artifact)
    new_result = evaluator.evaluate(new_artifact)

    old_scores = {pid: pr.score for pid, pr in old_result.phase_results.items()}
    new_scores = {pid: pr.score for pid, pr in new_result.phase_results.items()}

    mismatches = []
    for phase_id in old_scores:
        if phase_id not in new_scores:
            mismatches.append(f"{phase_id}: missing in new")
            continue
        if abs(old_scores[phase_id] - new_scores[phase_id]) > 0.0001:
            mismatches.append(
                f"{phase_id}: {old_scores[phase_id]:.4f} -> {new_scores[phase_id]:.4f}"
            )

    return {
        "parity": "pass" if not mismatches else "fail",
        "old_scores": old_scores,
        "new_scores": new_scores,
        "mismatches": mismatches,
    }


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compile theory ACTIVATION.md files via Haiku API"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--theory", type=str,
        help="Compile a single theory by ID",
    )
    group.add_argument(
        "--all", action="store_true",
        help="Compile all 8 theories",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compile and validate without overwriting artifacts",
    )
    parser.add_argument(
        "--diff", action="store_true",
        help="Show semantic diff against existing artifacts",
    )
    args = parser.parse_args()

    # Determine theories to compile
    if args.theory:
        if args.theory not in ALL_THEORY_IDS:
            print(f"Unknown theory: {args.theory}")
            print(f"Available: {', '.join(ALL_THEORY_IDS)}")
            sys.exit(1)
        theories = [args.theory]
    else:
        theories = ALL_THEORY_IDS

    # Build registry and prompt
    print("Building field registry...")
    registry = build_full_registry()

    print("Building system prompt...")
    system_prompt = build_system_prompt(registry)

    # Initialize compiler
    compiler = HaikuCompiler()

    # Track results
    results = {}
    all_diffs = {}

    for theory_id in theories:
        print(f"\n{'='*60}")
        print(f"Compiling: {theory_id}")
        print(f"{'='*60}")

        artifact, report = compile_theory(
            theory_id, compiler, system_prompt, registry,
        )
        results[theory_id] = report

        if artifact is None:
            print(f"  FAILED: {report['errors']}")
            continue

        print(
            f"  Result: {report['status']} | "
            f"clean={report['clean']} warn={report['warning']} "
            f"blocked={report['blocked']}"
        )

        if report.get("validation_errors", 0) > 0:
            print(f"  Validation errors: {report['validation_errors']}")
            for err in report.get("errors", []):
                if err.startswith("Validation:"):
                    print(f"    {err}")

        # Semantic diff
        if args.diff or not args.dry_run:
            try:
                existing = load_artifact(theory_id)
                diffs = semantic_diff(existing, artifact)
                all_diffs[theory_id] = diffs
                if diffs:
                    print(f"  Semantic diff ({len(diffs)} differences):")
                    for d in diffs[:10]:
                        print(f"    {d}")
                    if len(diffs) > 10:
                        print(f"    ... and {len(diffs) - 10} more")
                else:
                    print("  Semantic diff: IDENTICAL")
            except Exception:
                print("  No existing artifact for diff")
                all_diffs[theory_id] = ["NEW (no existing artifact)"]

        # Save artifact (unless dry-run)
        if not args.dry_run and artifact:
            path = save_artifact(artifact)
            print(f"  Saved: {path}")
        elif args.dry_run:
            print("  (dry-run: not saved)")

    # Print summary
    print(f"\n{'='*60}")
    print("COMPILATION SUMMARY")
    print(f"{'='*60}")
    for tid, report in results.items():
        status = report["status"].upper()
        total = report["total_indicators"]
        clean = report["clean"]
        warn = report["warning"]
        blocked = report["blocked"]
        print(f"  {tid}: {status} ({clean}/{total} clean, {warn} warn, {blocked} blocked)")

    # API stats
    stats = compiler.stats
    print(f"\nAPI Stats:")
    print(f"  Calls: {stats['calls']}")
    print(f"  Input tokens: {stats['input_tokens']}")
    print(f"  Output tokens: {stats['output_tokens']}")
    if stats["latencies"]:
        avg = sum(stats["latencies"]) / len(stats["latencies"])
        print(f"  Avg latency: {avg:.1f}s")
    if stats["errors"]:
        print(f"  Errors: {stats['errors']}")

    # Score parity check for APPROVED theories
    backup_dir = ARTIFACTS_DIR.parent / "v9_backup_pre_haiku"
    approved = ["valuation_mean_reversion", "debt_cycle_long",
                "fiscal_dominance_arithmetic"]
    if not args.dry_run:
        print(f"\nScore Parity Check (APPROVED theories):")
        for tid in approved:
            if tid not in results or results[tid]["status"] == "error":
                print(f"  {tid}: SKIPPED (compilation failed)")
                continue
            try:
                old = load_artifact(tid, backup_dir / f"{tid}.compiled.json")
            except Exception:
                print(f"  {tid}: SKIPPED (no backup artifact)")
                continue

            new_path = ARTIFACTS_DIR / f"{tid}.compiled.json"
            try:
                new = load_artifact(tid, new_path)
                parity = check_score_parity(tid, old, new)
                if parity["parity"] == "pass":
                    print(f"  {tid}: PASS")
                    print(f"    scores: {parity['new_scores']}")
                elif parity["parity"] == "skip":
                    print(f"  {tid}: SKIP ({parity['reason']})")
                else:
                    print(f"  {tid}: FAIL")
                    for m in parity["mismatches"]:
                        print(f"    {m}")
            except Exception as e:
                print(f"  {tid}: ERROR ({e})")


if __name__ == "__main__":
    main()
