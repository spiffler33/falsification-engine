# test_continuation_lineage.py — Tests for continuation lineage model (v6 Phase 3).
import json

import pytest

from backend.engine.output_parser import parse_generation_output
from backend.engine.prompt_builder import build_generation_prompt_v8, _prior_hypotheses_section
from backend.schemas.theory import TheoryPackage


def _make_generation_json(hypotheses: list[dict]) -> str:
    """Helper: wrap hypothesis dicts into the JSON string the parser expects."""
    return json.dumps(hypotheses)


def _base_hypothesis(**overrides) -> dict:
    """Minimal valid hypothesis with all required fields."""
    h = {
        "theory_id": "valuation_mean_reversion",
        "short_name": "Test hypothesis for continuation",
        "full_statement": "Testing continuation lineage extraction.",
        "predicted_assets": ["SPY"],
        "asset_direction": {"SPY": "LONG"},
        "timeframe": "Through Q3 2026",
        "hard_falsifiers": [],
        "soft_falsifiers": [],
        "payoff_band": {
            "magnitude_lower": 0.10,
            "magnitude_upper": 0.25,
            "end_date": "2026-09-30",
        },
        "conviction_inputs": {
            "support_strength": 0.5, "evidence_quality": 0.5,
            "convergence": 0.5, "falsifier_clarity": 0.5,
            "horizon_alignment": 0.5, "expression_efficiency": 0.5,
        },
    }
    h.update(overrides)
    return h


class TestContinuationFieldExtraction:
    """Test that parse_generation_output extracts continuation fields correctly."""

    def test_original_hypothesis_defaults(self):
        """Original hypothesis: continuation_of=None, generation=1, justification=None."""
        h = _base_hypothesis()
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert len(result) == 1
        assert result[0]["continuation_of"] is None
        assert result[0]["continuation_generation"] == 1
        assert result[0]["continuation_justification"] is None

    def test_continuation_flat_fields(self):
        """LLM puts continuation fields at top level."""
        h = _base_hypothesis(
            continuation_of="H-20260315-03",
            continuation_generation=2,
            continuation_justification="New employment data released showing acceleration",
        )
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["continuation_of"] == "H-20260315-03"
        assert result[0]["continuation_generation"] == 2
        assert result[0]["continuation_justification"] == "New employment data released showing acceleration"

    def test_continuation_nested_object(self):
        """LLM nests continuation fields under a 'continuation' key."""
        h = _base_hypothesis(continuation={
            "continuation_of": "H-20260315-03",
            "continuation_generation": 3,
            "continuation_justification": "Second-order credit tightening now manifesting",
        })
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["continuation_of"] == "H-20260315-03"
        assert result[0]["continuation_generation"] == 3
        assert result[0]["continuation_justification"] == "Second-order credit tightening now manifesting"

    def test_continuation_nested_with_aliases(self):
        """LLM uses alternative field names inside nested object."""
        h = _base_hypothesis(continuation={
            "parent_id": "H-20260315-03",
            "generation": 2,
            "justification": "Changed expression: shifted from DBC/QQQ to XLE/QQQ",
        })
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["continuation_of"] == "H-20260315-03"
        assert result[0]["continuation_generation"] == 2
        assert result[0]["continuation_justification"] == "Changed expression: shifted from DBC/QQQ to XLE/QQQ"

    def test_continuation_field_aliases(self):
        """LLM uses aliased field names at top level."""
        h = _base_hypothesis(
            parent_id="H-20260315-03",
            generation=2,
            justification="New trade deficit data reverses prior trend",
        )
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["continuation_of"] == "H-20260315-03"
        assert result[0]["continuation_generation"] == 2
        assert result[0]["continuation_justification"] == "New trade deficit data reverses prior trend"

    def test_string_generation_converted(self):
        """LLM outputs generation as string instead of int -> converted."""
        h = _base_hypothesis(
            continuation_of="H-20260315-03",
            continuation_generation="2",
            continuation_justification="Test",
        )
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["continuation_generation"] == 2

    def test_mixed_originals_and_continuations(self):
        """Array with both original and continuation hypotheses."""
        h1 = _base_hypothesis(short_name="Original hypothesis A")
        h2 = _base_hypothesis(
            short_name="Continuation of A from current levels",
            continuation_of="H-20260315-03",
            continuation_generation=2,
            continuation_justification="CPI print diverged from forecast, new regime signal",
        )
        h3 = _base_hypothesis(short_name="Original hypothesis B")

        raw = _make_generation_json([h1, h2, h3])
        result = parse_generation_output(raw, "R-20260401-001")

        assert len(result) == 3

        # First and third are originals
        assert result[0]["continuation_of"] is None
        assert result[0]["continuation_generation"] == 1
        assert result[2]["continuation_of"] is None
        assert result[2]["continuation_generation"] == 1

        # Second is a continuation
        assert result[1]["continuation_of"] == "H-20260315-03"
        assert result[1]["continuation_generation"] == 2
        assert "CPI print" in result[1]["continuation_justification"]

    def test_null_continuation_fields_explicit(self):
        """LLM explicitly sets continuation fields to null."""
        h = _base_hypothesis(
            continuation_of=None,
            continuation_generation=1,
            continuation_justification=None,
        )
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["continuation_of"] is None
        assert result[0]["continuation_generation"] == 1
        assert result[0]["continuation_justification"] is None

    def test_empty_string_continuation_treated_as_none(self):
        """Empty string continuation_of treated as None (not a valid parent link)."""
        h = _base_hypothesis(
            continuation_of="",
            continuation_justification="",
        )
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["continuation_of"] is None
        assert result[0]["continuation_justification"] is None


class TestPriorHypothesesSection:
    """Test the prior hypotheses prompt section formatting."""

    def test_basic_prior_hypothesis(self):
        """Prior hypothesis with full realization data formats correctly."""
        priors = [{
            "id": "H-20260315-03",
            "short_name": "DBC outperforms QQQ on commodity supercycle",
            "predicted_assets": ["DBC", "QQQ"],
            "asset_direction": {"DBC": "LONG", "QQQ": "SHORT"},
            "predicted_magnitude_lower": 0.15,
            "predicted_magnitude_upper": 0.30,
            "timeframe_end_date": "2026-09-30",
            "expression_return": 0.248,
            "realization_vs_lower": 1.65,
            "realization_vs_upper": 0.83,
            "time_elapsed_pct": 0.38,
            "status": "SURVIVED",
            "continuation_generation": 1,
            "continuation_of": None,
        }]

        section = _prior_hypotheses_section(priors)

        assert "H-20260315-03" in section
        assert "LONG DBC / SHORT QQQ" in section
        assert "15-30%" in section
        assert "2026-09-30" in section
        assert "+24.8%" in section
        assert "1.65" in section
        assert "0.83" in section
        assert "38%" in section
        assert "SURVIVED" in section

    def test_prior_with_continuation_lineage(self):
        """Prior hypothesis that is itself a continuation shows lineage info."""
        priors = [{
            "id": "H-20260401-02",
            "short_name": "DBC/QQQ continuation from current levels",
            "predicted_assets": ["DBC", "QQQ"],
            "asset_direction": {"DBC": "LONG", "QQQ": "SHORT"},
            "predicted_magnitude_lower": 0.08,
            "predicted_magnitude_upper": 0.18,
            "timeframe_end_date": "2026-12-31",
            "expression_return": 0.03,
            "realization_vs_lower": 0.38,
            "realization_vs_upper": 0.17,
            "time_elapsed_pct": 0.05,
            "status": "SURVIVED",
            "continuation_generation": 2,
            "continuation_of": "H-20260315-03",
        }]

        section = _prior_hypotheses_section(priors)

        assert "Gen 2" in section
        assert "H-20260315-03" in section

    def test_prior_without_realization(self):
        """Prior hypothesis with payoff band but no computed realization."""
        priors = [{
            "id": "H-20260315-05",
            "short_name": "STIP outperforms TLT",
            "predicted_assets": ["STIP", "TLT"],
            "asset_direction": {"STIP": "LONG", "TLT": "SHORT"},
            "predicted_magnitude_lower": 0.05,
            "predicted_magnitude_upper": 0.12,
            "timeframe_end_date": "2026-09-30",
            "expression_return": None,
            "realization_vs_lower": None,
            "realization_vs_upper": None,
            "time_elapsed_pct": None,
            "status": "SURVIVED",
            "continuation_generation": 1,
            "continuation_of": None,
        }]

        section = _prior_hypotheses_section(priors)

        assert "H-20260315-05" in section
        assert "5-12%" in section
        # Should not contain realization lines
        assert "Expression return since inception" not in section
        assert "Realization vs lower" not in section

    def test_prompt_includes_prior_section_when_provided(self):
        """build_generation_prompt_v8 includes PRIOR HYPOTHESES section when priors exist."""
        priors = [{
            "id": "H-20260315-03",
            "short_name": "Test prior",
            "predicted_assets": ["SPY"],
            "asset_direction": {"SPY": "LONG"},
            "predicted_magnitude_lower": 0.10,
            "predicted_magnitude_upper": 0.20,
            "timeframe_end_date": "2026-09-30",
            "expression_return": 0.15,
            "realization_vs_lower": 1.5,
            "realization_vs_upper": 0.75,
            "time_elapsed_pct": 0.40,
            "status": "SURVIVED",
            "continuation_generation": 1,
            "continuation_of": None,
        }]

        prompt = build_generation_prompt_v8(
            packages=[],
            activation_results=[],
            briefing={"growth": {}},
            inbox_items=[],
            prior_hypotheses=priors,
        )

        assert "## PRIOR HYPOTHESES" in prompt
        assert "## CONTINUATION CONTRACT" in prompt
        assert "H-20260315-03" in prompt
        assert "DECLINE TO REGENERATE" in prompt
        assert "GENERATE A CONTINUATION" in prompt

    def test_prompt_omits_prior_section_when_none(self):
        """build_generation_prompt_v8 omits PRIOR HYPOTHESES section when no priors."""
        prompt = build_generation_prompt_v8(
            packages=[],
            activation_results=[],
            briefing={"growth": {}},
            inbox_items=[],
            prior_hypotheses=None,
        )

        assert "## PRIOR HYPOTHESES" not in prompt
        assert "## CONTINUATION CONTRACT" not in prompt
