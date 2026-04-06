# test_compare_loaders.py -- Layer 4 validation: comparison harness runs end-to-end.
# Depends on: scripts/compare_loaders.py, engine/theory_parser.py, engine/theory_loader.py,
#             engine/prompt_builder.py, engine/activation.py, schemas/briefing.py
#
# Validates that the Layer 4 comparison harness executes without error and
# produces the expected report structure.  These are structural tests --
# they verify the harness runs, not the human-judgment comparison itself.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.compare_loaders import (
    build_synthetic_hypotheses,
    compare_activation,
    load_briefing,
    prompt_metrics,
    run_comparison,
)

from backend.config import THEORIES_DIR
from backend.engine import activation, theory_parser
from backend.engine.theory_loader import load_all_theory_packages, package_to_theory_module
from backend.schemas.briefing import BriefingPacket


OLD_FORMAT_DIR = THEORIES_DIR / "old_format"


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestLoadBriefing:
    """Briefing loader finds and parses the packet."""

    def test_loads_successfully(self):
        briefing = load_briefing()
        assert isinstance(briefing, dict)
        assert len(briefing) > 0

    def test_has_expected_sections(self):
        briefing = load_briefing()
        # The briefing packet should have at least some of the core sections
        expected_keys = {"growth", "inflation", "rates", "markets"}
        assert expected_keys & set(briefing.keys()), (
            f"Briefing missing expected sections. Keys: {sorted(briefing.keys())}"
        )


class TestPromptMetrics:
    """prompt_metrics extracts correct structural data."""

    def test_basic_metrics(self):
        text = "## Section A\nline1\nline2\n## Section B\nline3"
        m = prompt_metrics(text)
        assert m["length_chars"] == len(text)
        assert m["length_lines"] == 5
        assert m["section_count"] == 2
        assert m["sections"] == ["## Section A", "## Section B"]

    def test_empty_string(self):
        m = prompt_metrics("")
        assert m["length_chars"] == 0
        assert m["section_count"] == 0


class TestCompareActivation:
    """Activation comparison classifies theories correctly."""

    def test_all_eight_theories_present(self):
        briefing_data = load_briefing()
        briefing = BriefingPacket(**briefing_data)

        old_theories = theory_parser.load_all_theories(OLD_FORMAT_DIR)
        packages = load_all_theory_packages()
        adapted = [package_to_theory_module(pkg) for pkg in packages]

        old_results = activation.score_all_theories(old_theories, briefing)
        new_results = activation.score_all_theories(adapted, briefing)

        rows = compare_activation(old_results, new_results)
        theory_ids = {r["theory_id"] for r in rows}

        assert len(rows) == 8
        assert "debt_cycle_short" in theory_ids
        assert "fiscal_dominance_liquidity" in theory_ids

    def test_exact_match_theories_pass(self):
        """The three EXACT-classified theories must actually match exactly."""
        briefing_data = load_briefing()
        briefing = BriefingPacket(**briefing_data)

        old_theories = theory_parser.load_all_theories(OLD_FORMAT_DIR)
        packages = load_all_theory_packages()
        adapted = [package_to_theory_module(pkg) for pkg in packages]

        old_results = activation.score_all_theories(old_theories, briefing)
        new_results = activation.score_all_theories(adapted, briefing)

        rows = compare_activation(old_results, new_results)
        exact_rows = [r for r in rows if r["expected"] == "EXACT"]

        for row in exact_rows:
            assert row["actual"] == "EXACT", (
                f"{row['theory_id']}: expected EXACT match but got {row['actual']} "
                f"(old={row['old_score']}, new={row['new_score']})"
            )
            assert row["pass"] is True

    def test_all_rows_have_required_fields(self):
        briefing_data = load_briefing()
        briefing = BriefingPacket(**briefing_data)

        old_theories = theory_parser.load_all_theories(OLD_FORMAT_DIR)
        packages = load_all_theory_packages()
        adapted = [package_to_theory_module(pkg) for pkg in packages]

        old_results = activation.score_all_theories(old_theories, briefing)
        new_results = activation.score_all_theories(adapted, briefing)

        rows = compare_activation(old_results, new_results)
        required = {"theory_id", "old_score", "new_score", "old_tier", "new_tier",
                     "expected", "actual", "pass"}
        for row in rows:
            assert required <= set(row.keys()), f"Missing fields in {row['theory_id']}"


class TestSyntheticHypotheses:
    """Synthetic hypothesis builder produces valid structures."""

    def test_produces_hypotheses_for_active_theories(self):
        briefing_data = load_briefing()
        briefing = BriefingPacket(**briefing_data)

        packages = load_all_theory_packages()
        adapted = [package_to_theory_module(pkg) for pkg in packages]
        results = activation.score_all_theories(adapted, briefing)

        hyps = build_synthetic_hypotheses(results)
        assert len(hyps) >= 1, "At least one theory should be Active"

        for h in hyps:
            assert h["id"].startswith("synthetic_")
            assert h["source_theory"]
            assert h["source_theories"]
            assert h["predicted_assets"]
            assert h["hard_falsifiers"]
            assert h["soft_falsifiers"]

    def test_only_active_theories_get_hypotheses(self):
        briefing_data = load_briefing()
        briefing = BriefingPacket(**briefing_data)

        packages = load_all_theory_packages()
        adapted = [package_to_theory_module(pkg) for pkg in packages]
        results = activation.score_all_theories(adapted, briefing)

        hyps = build_synthetic_hypotheses(results)
        hyp_theories = {h["source_theory"] for h in hyps}

        # Every hypothesis theory should be Active
        active_theories = set()
        for ar in results:
            tier = ar.effective_tier if ar.is_two_phase else ar.tier
            if tier and tier.value == "Active":
                active_theories.add(ar.theory_id)

        assert hyp_theories <= active_theories


# ---------------------------------------------------------------------------
# Integration test: full comparison harness
# ---------------------------------------------------------------------------


class TestRunComparison:
    """End-to-end test of the comparison harness."""

    def test_produces_valid_report(self, tmp_path):
        report = run_comparison(output_dir=tmp_path)

        # Report structure
        assert "timestamp" in report
        assert "activation_comparison" in report
        assert "activation_all_pass" in report
        assert "generation_prompt" in report
        assert "elimination_prompt" in report
        assert "regime_flags" in report
        assert "theory_counts" in report

        # All 8 theories compared
        assert len(report["activation_comparison"]) == 8

        # Theory counts
        assert report["theory_counts"]["old_loader"] == 8
        assert report["theory_counts"]["new_loader"] == 8
        assert report["theory_counts"]["adapter"] == 8

    def test_writes_all_output_files(self, tmp_path):
        run_comparison(output_dir=tmp_path)

        # Find the timestamped subdirectory
        subdirs = list(tmp_path.iterdir())
        assert len(subdirs) == 1
        out_dir = subdirs[0]

        expected_files = {
            "generation_old.txt",
            "generation_new.txt",
            "elimination_old.txt",
            "elimination_new.txt",
            "comparison_report.json",
        }
        actual_files = {f.name for f in out_dir.iterdir()}
        assert expected_files <= actual_files

        # All text files are non-empty
        for name in expected_files:
            f = out_dir / name
            assert f.stat().st_size > 0, f"{name} is empty"

    def test_comparison_report_json_valid(self, tmp_path):
        run_comparison(output_dir=tmp_path)
        subdirs = list(tmp_path.iterdir())
        report_path = subdirs[0] / "comparison_report.json"
        data = json.loads(report_path.read_text())

        # Validate activation rows
        for row in data["activation_comparison"]:
            assert row["expected"] in ("EXACT", "TIER", "DIVERGED")
            assert row["actual"] in ("EXACT", "TIER", "DIVERGED")
            assert isinstance(row["pass"], bool)

        # Validate prompt metrics
        for key in ("generation_prompt", "elimination_prompt"):
            assert "old" in data[key]
            assert "new" in data[key]
            assert data[key]["old"]["length_chars"] > 0
            assert data[key]["new"]["length_chars"] > 0

    def test_prompts_contain_theory_content(self, tmp_path):
        """Both old and new generation prompts contain active theory names."""
        run_comparison(output_dir=tmp_path)
        subdirs = list(tmp_path.iterdir())
        out_dir = subdirs[0]

        gen_old = (out_dir / "generation_old.txt").read_text()
        gen_new = (out_dir / "generation_new.txt").read_text()

        # At least one Active theory name should appear in both prompts
        assert "ACTIVE THEORIES" in gen_old
        assert "ACTIVE THEORIES" in gen_new

    def test_elimination_prompts_contain_hypotheses(self, tmp_path):
        """Both elimination prompts contain the synthetic hypotheses."""
        run_comparison(output_dir=tmp_path)
        subdirs = list(tmp_path.iterdir())
        out_dir = subdirs[0]

        elim_old = (out_dir / "elimination_old.txt").read_text()
        elim_new = (out_dir / "elimination_new.txt").read_text()

        assert "HYPOTHESES TO ATTACK" in elim_old
        assert "HYPOTHESES TO ATTACK" in elim_new
        assert "synthetic_" in elim_old
        assert "synthetic_" in elim_new
