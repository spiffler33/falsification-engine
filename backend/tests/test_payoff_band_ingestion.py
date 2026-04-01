# test_payoff_band_ingestion.py — Tests for payoff band extraction in output_parser (v6 Phase 2).
import json

import pytest

from backend.engine.output_parser import parse_generation_output


def _make_generation_json(hypotheses: list[dict]) -> str:
    """Helper: wrap hypothesis dicts into the JSON string the parser expects."""
    return json.dumps(hypotheses)


def _base_hypothesis(**overrides) -> dict:
    """Minimal valid hypothesis with all required fields."""
    h = {
        "theory_id": "valuation_mean_reversion",
        "short_name": "Test hypothesis for payoff band",
        "full_statement": "Testing payoff band extraction.",
        "predicted_assets": ["SPY"],
        "asset_direction": {"SPY": "LONG"},
        "timeframe": "Through Q3 2026",
        "hard_falsifiers": [],
        "soft_falsifiers": [],
        "conviction_inputs": {
            "support_strength": 0.5, "evidence_quality": 0.5,
            "convergence": 0.5, "falsifier_clarity": 0.5,
            "horizon_alignment": 0.5, "expression_efficiency": 0.5,
        },
    }
    h.update(overrides)
    return h


class TestPayoffBandExtraction:
    """Test that parse_generation_output extracts payoff band from various formats."""

    def test_nested_payoff_band(self):
        """Standard format: payoff_band as a nested object."""
        h = _base_hypothesis(payoff_band={
            "magnitude_lower": 0.10,
            "magnitude_upper": 0.25,
            "end_date": "2026-09-30",
        })
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert len(result) == 1
        assert result[0]["predicted_magnitude_lower"] == pytest.approx(0.10)
        assert result[0]["predicted_magnitude_upper"] == pytest.approx(0.25)
        assert result[0]["timeframe_end_date"] == "2026-09-30"

    def test_flat_fields(self):
        """LLM puts fields at top level instead of nesting."""
        h = _base_hypothesis(
            predicted_magnitude_lower=0.05,
            predicted_magnitude_upper=0.12,
            timeframe_end_date="2026-12-31",
        )
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["predicted_magnitude_lower"] == pytest.approx(0.05)
        assert result[0]["predicted_magnitude_upper"] == pytest.approx(0.12)
        assert result[0]["timeframe_end_date"] == "2026-12-31"

    def test_missing_payoff_band_still_ingested(self):
        """Hypothesis without payoff band is still ingested (tolerant parsing)."""
        h = _base_hypothesis()
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert len(result) == 1
        assert result[0]["predicted_magnitude_lower"] is None
        assert result[0]["predicted_magnitude_upper"] is None
        assert result[0]["timeframe_end_date"] is None

    def test_string_magnitudes_converted(self):
        """LLM outputs magnitude as string instead of float -> converted."""
        h = _base_hypothesis(payoff_band={
            "magnitude_lower": "0.10",
            "magnitude_upper": "0.25",
            "end_date": "2026-09-30",
        })
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["predicted_magnitude_lower"] == pytest.approx(0.10)
        assert result[0]["predicted_magnitude_upper"] == pytest.approx(0.25)

    def test_end_date_in_nested_timeframe_end_date(self):
        """LLM uses timeframe_end_date inside payoff_band instead of end_date."""
        h = _base_hypothesis(payoff_band={
            "magnitude_lower": 0.10,
            "magnitude_upper": 0.25,
            "timeframe_end_date": "2026-09-30",
        })
        raw = _make_generation_json([h])
        result = parse_generation_output(raw, "R-20260401-001")

        assert result[0]["timeframe_end_date"] == "2026-09-30"

    def test_multiple_hypotheses_each_get_payoff_band(self):
        """Each hypothesis in the array gets its own payoff band."""
        h1 = _base_hypothesis(
            short_name="Hypothesis A",
            payoff_band={"magnitude_lower": 0.10, "magnitude_upper": 0.20, "end_date": "2026-06-30"},
        )
        h2 = _base_hypothesis(
            short_name="Hypothesis B",
            payoff_band={"magnitude_lower": 0.05, "magnitude_upper": 0.15, "end_date": "2026-12-31"},
        )
        raw = _make_generation_json([h1, h2])
        result = parse_generation_output(raw, "R-20260401-001")

        assert len(result) == 2
        assert result[0]["predicted_magnitude_lower"] == pytest.approx(0.10)
        assert result[1]["predicted_magnitude_lower"] == pytest.approx(0.05)
        assert result[0]["timeframe_end_date"] == "2026-06-30"
        assert result[1]["timeframe_end_date"] == "2026-12-31"
