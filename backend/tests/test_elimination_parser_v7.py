# test_elimination_parser_v7.py — Tests for v7 elimination output parser fields.
# Verifies: staleness_classification/staleness_reasoning carry-through on
# per-falsifier items, emergent_risk extraction and flattening, null/missing
# emergent_risk handling, STALE status acceptance, backward compatibility.
from __future__ import annotations

import json

import pytest

from backend.engine.output_parser import parse_elimination_output


# ---------------------------------------------------------------------------
# Helpers — minimal hypothesis dicts that mirror what import_elimination sends
# ---------------------------------------------------------------------------


def _hyp(
    hyp_id: str = "H-20260403-120000-01",
    short_name: str = "Gold rises on fiscal stress",
    soft_falsifiers: list | None = None,
) -> dict:
    return {
        "id": hyp_id,
        "short_name": short_name,
        "source_theory": "fiscal_dominance_liquidity",
        "status": "SURVIVED",
        "soft_falsifiers": json.dumps(soft_falsifiers or []),
        "predicted_assets": json.dumps(["GLD"]),
    }


def _sf(name: str, severity: str = "minor", status: str = "CLEAR") -> dict:
    return {"name": name, "condition": name, "severity": severity, "status": status}


# ---------------------------------------------------------------------------
# Staleness fields — list-format soft falsifiers
# ---------------------------------------------------------------------------


class TestStalenessFieldsCarryThrough:
    """v7: staleness_classification and staleness_reasoning flow from
    evaluator output into the persisted soft_falsifiers JSON."""

    def test_stale_with_classification_carried_through(self):
        existing = [_hyp(soft_falsifiers=[
            _sf("real rates rise above 2%", "medium"),
            _sf("dollar index strengthens sharply", "minor"),
        ])]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "WOUNDED",
            "elimination_notes": "Staleness concern.",
            "soft_falsifiers": [
                {
                    "name": "real rates rise above 2%",
                    "status": "STALE",
                    "staleness_classification": "TRIGGERED_BY_PASSAGE",
                    "staleness_reasoning": "Real rates data is 45 days old and directional drift favors triggering.",
                },
                {
                    "name": "dollar index strengthens sharply",
                    "status": "CLEAR",
                },
            ],
        }])
        result = parse_elimination_output(elim_json, existing)
        sf = json.loads(result[0]["soft_falsifiers"])

        assert sf[0]["status"] == "STALE"
        assert sf[0]["staleness_classification"] == "TRIGGERED_BY_PASSAGE"
        assert "45 days" in sf[0]["staleness_reasoning"]
        # Second falsifier: CLEAR, no staleness fields
        assert sf[1]["status"] == "CLEAR"
        assert "staleness_classification" not in sf[1]

    def test_stale_without_triggered_by_passage(self):
        """STALE + staleness_classification='STALE' = benign staleness."""
        existing = [_hyp(soft_falsifiers=[_sf("CPI exceeds 4%", "major")])]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "SURVIVED",
            "elimination_notes": "All clear.",
            "soft_falsifiers": [{
                "name": "CPI exceeds 4%",
                "status": "STALE",
                "staleness_classification": "STALE",
                "staleness_reasoning": None,
            }],
        }])
        result = parse_elimination_output(elim_json, existing)
        sf = json.loads(result[0]["soft_falsifiers"])
        assert sf[0]["status"] == "STALE"
        assert sf[0]["staleness_classification"] == "STALE"
        assert "staleness_reasoning" not in sf[0]  # null suppressed

    def test_staleness_on_triggered_falsifier(self):
        """A TRIGGERED falsifier can also carry staleness metadata."""
        existing = [_hyp(soft_falsifiers=[_sf("yield curve uninverts", "medium")])]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "WOUNDED",
            "elimination_notes": "Active trigger.",
            "soft_falsifiers": [{
                "name": "yield curve uninverts",
                "status": "TRIGGERED",
                "staleness_classification": "TRIGGERED_BY_PASSAGE",
                "staleness_reasoning": "3-month inversion deepened further since last data.",
            }],
        }])
        result = parse_elimination_output(elim_json, existing)
        sf = json.loads(result[0]["soft_falsifiers"])
        assert sf[0]["status"] == "TRIGGERED"
        assert sf[0]["staleness_classification"] == "TRIGGERED_BY_PASSAGE"

    def test_triggered_takes_precedence_over_stale(self):
        """If a falsifier was already TRIGGERED by a prior match, STALE cannot overwrite it."""
        existing = [_hyp(soft_falsifiers=[_sf("inflation exceeds target", "major")])]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "WOUNDED",
            "elimination_notes": "Double match test.",
            "soft_falsifiers": [
                {"name": "inflation exceeds target", "status": "TRIGGERED"},
                {"name": "inflation exceeds target", "status": "STALE",
                 "staleness_classification": "STALE"},
            ],
        }])
        result = parse_elimination_output(elim_json, existing)
        sf = json.loads(result[0]["soft_falsifiers"])
        # TRIGGERED wins — the second STALE match is blocked by precedence
        assert sf[0]["status"] == "TRIGGERED"

    def test_no_staleness_fields_backward_compat(self):
        """Pre-v7 evaluator output with no staleness fields still works."""
        existing = [_hyp(soft_falsifiers=[
            _sf("spreads widen", "minor"),
            _sf("VIX spikes", "medium"),
        ])]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "WOUNDED",
            "elimination_notes": "One triggered.",
            "soft_falsifiers": [
                {"name": "spreads widen", "status": "TRIGGERED"},
                {"name": "VIX spikes", "status": "UNTESTABLE"},
            ],
        }])
        result = parse_elimination_output(elim_json, existing)
        sf = json.loads(result[0]["soft_falsifiers"])
        assert sf[0]["status"] == "TRIGGERED"
        assert sf[1]["status"] == "UNTESTABLE"
        assert "staleness_classification" not in sf[0]
        assert "staleness_classification" not in sf[1]


# ---------------------------------------------------------------------------
# Emergent risk extraction
# ---------------------------------------------------------------------------


class TestEmergentRiskExtraction:
    """v7: emergent_risk object is extracted from each elimination item
    and flattened onto the hypothesis dict."""

    def test_emergent_risk_extracted_and_flattened(self):
        existing = [_hyp()]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "WOUNDED",
            "elimination_notes": "Tariff risk emerged.",
            "soft_falsifiers": [],
            "emergent_risk": {
                "condition": "April 2 reciprocal tariff announcement",
                "severity": "major",
                "causal_chain": "Tariffs raise input costs for gold miners, compressing margins despite gold price rise.",
            },
        }])
        result = parse_elimination_output(elim_json, existing)
        h = result[0]
        assert h["emergent_risk_condition"] == "April 2 reciprocal tariff announcement"
        assert h["emergent_risk_severity"] == "major"
        assert "gold miners" in h["emergent_risk_causal_chain"]

    def test_null_emergent_risk_no_keys_set(self):
        """emergent_risk: null should not add keys to the hypothesis dict."""
        existing = [_hyp()]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "SURVIVED",
            "elimination_notes": "Clean pass.",
            "soft_falsifiers": [],
            "emergent_risk": None,
        }])
        result = parse_elimination_output(elim_json, existing)
        h = result[0]
        assert "emergent_risk_condition" not in h
        assert "emergent_risk_severity" not in h
        assert "emergent_risk_causal_chain" not in h

    def test_missing_emergent_risk_key_backward_compat(self):
        """Pre-v7 output with no emergent_risk key at all."""
        existing = [_hyp()]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "SURVIVED",
            "elimination_notes": "Legacy output.",
            "soft_falsifiers": [],
        }])
        result = parse_elimination_output(elim_json, existing)
        h = result[0]
        assert "emergent_risk_condition" not in h

    def test_emergent_risk_minor_severity(self):
        existing = [_hyp()]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "SURVIVED",
            "elimination_notes": "Minor risk noted.",
            "soft_falsifiers": [],
            "emergent_risk": {
                "condition": "ECB rate pause speculation",
                "severity": "minor",
                "causal_chain": "EUR strength could dampen dollar-denominated gold demand marginally.",
            },
        }])
        result = parse_elimination_output(elim_json, existing)
        assert result[0]["emergent_risk_severity"] == "minor"

    def test_emergent_risk_with_staleness_combined(self):
        """Both staleness on falsifiers and emergent risk on hypothesis."""
        existing = [_hyp(soft_falsifiers=[_sf("credit spreads widen", "medium")])]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "WOUNDED",
            "elimination_notes": "Stale data + new risk.",
            "soft_falsifiers": [{
                "name": "credit spreads widen",
                "status": "STALE",
                "staleness_classification": "TRIGGERED_BY_PASSAGE",
                "staleness_reasoning": "Spread data 30 days old, direction uncertain.",
            }],
            "emergent_risk": {
                "condition": "PBOC surprise devaluation April 1",
                "severity": "medium",
                "causal_chain": "Capital outflows from EM compress carry returns, undermining thesis.",
            },
        }])
        result = parse_elimination_output(elim_json, existing)
        h = result[0]
        # Staleness on falsifier
        sf = json.loads(h["soft_falsifiers"])
        assert sf[0]["staleness_classification"] == "TRIGGERED_BY_PASSAGE"
        # Emergent risk on hypothesis
        assert h["emergent_risk_condition"] == "PBOC surprise devaluation April 1"
        assert h["emergent_risk_severity"] == "medium"


# ---------------------------------------------------------------------------
# Multiple hypotheses
# ---------------------------------------------------------------------------


class TestMultipleHypotheses:
    """Verify v7 fields work across multiple hypotheses in one elimination pass."""

    def test_mixed_emergent_risk_across_hypotheses(self):
        existing = [
            _hyp("H-01", "Gold thesis", [_sf("rates rise", "minor")]),
            _hyp("H-02", "Oil thesis", [_sf("OPEC increases supply", "major")]),
        ]
        elim_json = json.dumps([
            {
                "id": "H-01",
                "status": "WOUNDED",
                "elimination_notes": "Risk found.",
                "soft_falsifiers": [{"name": "rates rise", "status": "STALE",
                                     "staleness_classification": "STALE"}],
                "emergent_risk": {
                    "condition": "Fed emergency meeting rumor",
                    "severity": "major",
                    "causal_chain": "Emergency rate hike would crush gold.",
                },
            },
            {
                "id": "H-02",
                "status": "SURVIVED",
                "elimination_notes": "Clean.",
                "soft_falsifiers": [{"name": "OPEC increases supply", "status": "CLEAR"}],
                "emergent_risk": None,
            },
        ])
        result = parse_elimination_output(elim_json, existing)
        # H-01 has emergent risk
        h1 = next(h for h in result if h["id"] == "H-01")
        assert h1["emergent_risk_severity"] == "major"
        # H-02 does not
        h2 = next(h for h in result if h["id"] == "H-02")
        assert "emergent_risk_condition" not in h2


# ---------------------------------------------------------------------------
# Dict-format backward compatibility
# ---------------------------------------------------------------------------


class TestDictFormatUnchanged:
    """Dict-format soft falsifier handling has no staleness fields — verify it
    still works unchanged and doesn't inject unexpected keys."""

    def test_dict_format_triggered_still_works(self):
        existing = [_hyp(soft_falsifiers=[
            _sf("spreads widen", "minor"),
            _sf("VIX spikes", "medium"),
        ])]
        elim_json = json.dumps([{
            "id": "H-20260403-120000-01",
            "status": "WOUNDED",
            "elimination_notes": "One triggered.",
            "soft_falsifiers": {
                "triggered": ["spreads widen"],
                "untestable": ["VIX spikes"],
                "triggered_count": 1,
            },
        }])
        result = parse_elimination_output(elim_json, existing)
        sf = json.loads(result[0]["soft_falsifiers"])
        assert sf[0]["status"] == "TRIGGERED"
        assert sf[1]["status"] == "UNTESTABLE"
        assert "staleness_classification" not in sf[0]
