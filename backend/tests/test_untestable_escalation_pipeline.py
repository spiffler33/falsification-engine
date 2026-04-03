# test_untestable_escalation_pipeline.py — Task 8 integration tests.
# Verifies: UNTESTABLE escalation runs post-elimination in the pipeline,
# counters persist through JSON round-trips, ESCALATED_UNTESTABLE feeds
# into conviction scoring, counter inheritance across simulated runs.
from __future__ import annotations

import json

import pytest

from backend.lifecycle import apply_untestable_escalation, ESCALATION_THRESHOLD


# ---------------------------------------------------------------------------
# Helpers — simulate the JSON round-trip that import_elimination performs
# ---------------------------------------------------------------------------

def _sf(
    name: str,
    severity: str = "minor",
    status: str = "CLEAR",
    untestable_consecutive: int = 0,
) -> dict:
    return {
        "name": name,
        "condition": name,
        "severity": severity,
        "status": status,
        "untestable_consecutive": untestable_consecutive,
    }


def _pipeline_escalation_roundtrip(soft_falsifiers_json: str) -> str:
    """Simulate the exact code path in import_elimination:
    parse JSON -> apply_untestable_escalation -> dump JSON.
    """
    sf_list = json.loads(soft_falsifiers_json)
    if sf_list:
        sf_list = apply_untestable_escalation(sf_list)
    return json.dumps(sf_list)


def _collect_untestable_sf(soft_falsifiers_json: str) -> list[dict]:
    """Simulate the conviction scoring collection in import_elimination:
    collect falsifiers with status in (UNTESTABLE, ESCALATED_UNTESTABLE).
    """
    soft_f = json.loads(soft_falsifiers_json)
    return [
        {"severity": sf["severity"]}
        for sf in soft_f
        if sf.get("status") in ("UNTESTABLE", "ESCALATED_UNTESTABLE")
    ]


# ===================================================================
# Post-elimination escalation: JSON round-trip
# ===================================================================

class TestPipelineEscalationRoundTrip:
    """The pipeline stores soft_falsifiers as a JSON string.
    Verify that parsing -> escalation -> serialization is lossless."""

    def test_first_untestable_pass(self):
        """First UNTESTABLE after elimination: counter goes 0->1, stays UNTESTABLE."""
        sf_json = json.dumps([_sf("real rates drop", "medium", "UNTESTABLE", 0)])
        result = _pipeline_escalation_roundtrip(sf_json)
        sf = json.loads(result)
        assert sf[0]["status"] == "UNTESTABLE"
        assert sf[0]["untestable_consecutive"] == 1

    def test_second_untestable_pass(self):
        """Second consecutive UNTESTABLE: counter 1->2, stays UNTESTABLE."""
        sf_json = json.dumps([_sf("real rates drop", "medium", "UNTESTABLE", 1)])
        result = _pipeline_escalation_roundtrip(sf_json)
        sf = json.loads(result)
        assert sf[0]["status"] == "UNTESTABLE"
        assert sf[0]["untestable_consecutive"] == 2

    def test_third_untestable_escalates(self):
        """Third consecutive UNTESTABLE: counter 2->3, status -> ESCALATED_UNTESTABLE."""
        sf_json = json.dumps([_sf("real rates drop", "medium", "UNTESTABLE", 2)])
        result = _pipeline_escalation_roundtrip(sf_json)
        sf = json.loads(result)
        assert sf[0]["status"] == "ESCALATED_UNTESTABLE"
        assert sf[0]["untestable_consecutive"] == 3

    def test_clear_resets_counter(self):
        """Falsifier becomes CLEAR after elimination: counter resets to 0."""
        sf_json = json.dumps([_sf("VIX below 18", "minor", "CLEAR", 2)])
        result = _pipeline_escalation_roundtrip(sf_json)
        sf = json.loads(result)
        assert sf[0]["status"] == "CLEAR"
        assert sf[0]["untestable_consecutive"] == 0

    def test_triggered_resets_counter(self):
        """Falsifier becomes TRIGGERED: counter resets regardless of prior count."""
        sf_json = json.dumps([_sf("spread widens", "major", "TRIGGERED", 4)])
        result = _pipeline_escalation_roundtrip(sf_json)
        sf = json.loads(result)
        assert sf[0]["status"] == "TRIGGERED"
        assert sf[0]["untestable_consecutive"] == 0

    def test_empty_json_array(self):
        """Empty soft_falsifiers: no-op."""
        assert _pipeline_escalation_roundtrip("[]") == "[]"

    def test_preserves_all_fields(self):
        """All falsifier fields survive the round-trip."""
        sf_json = json.dumps([{
            "name": "GDP contracts",
            "condition": "GDP contracts",
            "severity": "major",
            "status": "UNTESTABLE",
            "untestable_consecutive": 1,
            "metric": "real_gdp",
            "threshold": "below 0",
            "generation_market_value": 2.1,
            "staleness_flag": None,
        }])
        result = _pipeline_escalation_roundtrip(sf_json)
        sf = json.loads(result)
        assert sf[0]["name"] == "GDP contracts"
        assert sf[0]["metric"] == "real_gdp"
        assert sf[0]["generation_market_value"] == 2.1
        assert sf[0]["staleness_flag"] is None
        assert sf[0]["untestable_consecutive"] == 2


# ===================================================================
# Conviction scoring collection: ESCALATED_UNTESTABLE inclusion
# ===================================================================

class TestConvictionScoringCollection:
    """Verify that both UNTESTABLE and ESCALATED_UNTESTABLE are collected
    for the D_u discount in conviction scoring."""

    def test_untestable_collected(self):
        """Regular UNTESTABLE falsifiers feed into D_u."""
        sf_json = json.dumps([_sf("f1", "minor", "UNTESTABLE", 1)])
        result = _collect_untestable_sf(sf_json)
        assert len(result) == 1
        assert result[0]["severity"] == "minor"

    def test_escalated_untestable_collected(self):
        """ESCALATED_UNTESTABLE falsifiers also feed into D_u."""
        sf_json = json.dumps([_sf("f1", "major", "ESCALATED_UNTESTABLE", 3)])
        result = _collect_untestable_sf(sf_json)
        assert len(result) == 1
        assert result[0]["severity"] == "major"

    def test_clear_not_collected(self):
        """CLEAR falsifiers excluded from D_u."""
        sf_json = json.dumps([_sf("f1", "minor", "CLEAR", 0)])
        assert _collect_untestable_sf(sf_json) == []

    def test_triggered_not_collected(self):
        """TRIGGERED falsifiers excluded from D_u (they go to D_f)."""
        sf_json = json.dumps([_sf("f1", "minor", "TRIGGERED", 0)])
        assert _collect_untestable_sf(sf_json) == []

    def test_stale_not_collected(self):
        """STALE falsifiers excluded from D_u."""
        sf_json = json.dumps([_sf("f1", "minor", "STALE", 0)])
        assert _collect_untestable_sf(sf_json) == []

    def test_mixed_statuses(self):
        """Only UNTESTABLE and ESCALATED_UNTESTABLE collected from a mixed set."""
        sf_json = json.dumps([
            _sf("f1", "minor", "CLEAR", 0),
            _sf("f2", "medium", "UNTESTABLE", 1),
            _sf("f3", "major", "ESCALATED_UNTESTABLE", 4),
            _sf("f4", "minor", "TRIGGERED", 0),
        ])
        result = _collect_untestable_sf(sf_json)
        assert len(result) == 2
        assert result[0]["severity"] == "medium"
        assert result[1]["severity"] == "major"


# ===================================================================
# Multi-run simulation: counter accumulation across runs
# ===================================================================

class TestMultiRunCounterAccumulation:
    """Simulate the full lifecycle across multiple runs:
    inherit counter -> elimination sets status -> escalation updates counter.

    This exercises the same logic that _inherit_falsifier_counters (generation import)
    and apply_untestable_escalation (elimination import) perform in sequence."""

    def _simulate_run(
        self,
        prior_sf: list[dict],
        elimination_statuses: dict[str, str],
        lifecycle_action: str = "CONFIRM",
    ) -> list[dict]:
        """Simulate one run: inherit -> elimination -> escalation.

        Args:
            prior_sf: soft falsifiers from the prior instance (with counters)
            elimination_statuses: mapping of falsifier name -> post-elimination status
            lifecycle_action: CONFIRM/UPDATE inherit counters; NEW/RENEW reset
        """
        # Step 1: Inherit counters (what _inherit_falsifier_counters does)
        current_sf = []
        for sf in prior_sf:
            new_sf = dict(sf)
            if lifecycle_action in ("NEW", "RENEW"):
                new_sf["untestable_consecutive"] = 0
            # CONFIRM/UPDATE: counter carries forward as-is
            # Set the post-elimination status
            name = sf["name"]
            if name in elimination_statuses:
                new_sf["status"] = elimination_statuses[name]
            current_sf.append(new_sf)

        # Step 2: Apply escalation (what import_elimination does)
        sf_json = json.dumps(current_sf)
        result_json = _pipeline_escalation_roundtrip(sf_json)
        return json.loads(result_json)

    def test_three_consecutive_untestable_runs_escalates(self):
        """Falsifier that is UNTESTABLE for 3 consecutive runs -> ESCALATED."""
        sf = [_sf("GDP contracts", "major", "CLEAR", 0)]

        # Run 1: elimination says UNTESTABLE
        sf = self._simulate_run(sf, {"GDP contracts": "UNTESTABLE"})
        assert sf[0]["status"] == "UNTESTABLE"
        assert sf[0]["untestable_consecutive"] == 1

        # Run 2: still UNTESTABLE
        sf = self._simulate_run(sf, {"GDP contracts": "UNTESTABLE"})
        assert sf[0]["status"] == "UNTESTABLE"
        assert sf[0]["untestable_consecutive"] == 2

        # Run 3: still UNTESTABLE -> ESCALATED
        sf = self._simulate_run(sf, {"GDP contracts": "UNTESTABLE"})
        assert sf[0]["status"] == "ESCALATED_UNTESTABLE"
        assert sf[0]["untestable_consecutive"] == 3

    def test_counter_resets_on_clear(self):
        """Counter resets when falsifier becomes testable again."""
        sf = [_sf("GDP contracts", "major", "UNTESTABLE", 2)]

        # Run: elimination says CLEAR this time
        sf = self._simulate_run(sf, {"GDP contracts": "CLEAR"})
        assert sf[0]["status"] == "CLEAR"
        assert sf[0]["untestable_consecutive"] == 0

    def test_counter_resets_then_restarts(self):
        """Counter resets to 0 on CLEAR, then starts climbing again."""
        sf = [_sf("f1", "medium", "UNTESTABLE", 2)]

        # Run 1: CLEAR -> reset
        sf = self._simulate_run(sf, {"f1": "CLEAR"})
        assert sf[0]["untestable_consecutive"] == 0

        # Run 2: UNTESTABLE again -> count from 0
        sf = self._simulate_run(sf, {"f1": "UNTESTABLE"})
        assert sf[0]["untestable_consecutive"] == 1
        assert sf[0]["status"] == "UNTESTABLE"

    def test_renew_resets_counter(self):
        """RENEW resets counter to 0 regardless of prior accumulation."""
        sf = [_sf("f1", "major", "UNTESTABLE", 2)]

        # RENEW: new thread, counter resets
        sf = self._simulate_run(sf, {"f1": "UNTESTABLE"}, lifecycle_action="RENEW")
        assert sf[0]["untestable_consecutive"] == 1  # 0 (reset) + 1 (this run)
        assert sf[0]["status"] == "UNTESTABLE"

    def test_new_starts_at_zero(self):
        """NEW hypothesis starts with counter=0."""
        sf = [_sf("f1", "minor", "UNTESTABLE", 0)]
        sf = self._simulate_run(sf, {"f1": "UNTESTABLE"}, lifecycle_action="NEW")
        assert sf[0]["untestable_consecutive"] == 1
        assert sf[0]["status"] == "UNTESTABLE"

    def test_stays_escalated_beyond_threshold(self):
        """Once escalated, additional UNTESTABLE passes keep the status."""
        sf = [_sf("f1", "major", "ESCALATED_UNTESTABLE", 3)]

        # Run 4: still UNTESTABLE
        sf = self._simulate_run(sf, {"f1": "UNTESTABLE"})
        assert sf[0]["status"] == "ESCALATED_UNTESTABLE"
        assert sf[0]["untestable_consecutive"] == 4

    def test_escalated_can_recover(self):
        """Even ESCALATED_UNTESTABLE resets if data becomes testable."""
        sf = [_sf("f1", "major", "ESCALATED_UNTESTABLE", 5)]

        # Data becomes available: elimination says TRIGGERED
        sf = self._simulate_run(sf, {"f1": "TRIGGERED"})
        assert sf[0]["status"] == "TRIGGERED"
        assert sf[0]["untestable_consecutive"] == 0

    def test_mixed_falsifiers_independent_counters(self):
        """Each falsifier tracks its own counter independently."""
        sf = [
            _sf("f1", "minor", "UNTESTABLE", 2),
            _sf("f2", "major", "CLEAR", 0),
            _sf("f3", "medium", "UNTESTABLE", 1),
        ]

        # Run: f1 still UNTESTABLE (->escalate), f2 becomes UNTESTABLE, f3 becomes CLEAR
        sf = self._simulate_run(sf, {
            "f1": "UNTESTABLE",
            "f2": "UNTESTABLE",
            "f3": "CLEAR",
        })

        assert sf[0]["status"] == "ESCALATED_UNTESTABLE"
        assert sf[0]["untestable_consecutive"] == 3

        assert sf[1]["status"] == "UNTESTABLE"
        assert sf[1]["untestable_consecutive"] == 1

        assert sf[2]["status"] == "CLEAR"
        assert sf[2]["untestable_consecutive"] == 0


# ===================================================================
# Edge cases
# ===================================================================

class TestEdgeCases:
    def test_missing_untestable_consecutive_field(self):
        """Falsifier dict without untestable_consecutive defaults to 0."""
        sf_json = json.dumps([{
            "name": "f1",
            "severity": "minor",
            "status": "UNTESTABLE",
            # no untestable_consecutive field
        }])
        result = _pipeline_escalation_roundtrip(sf_json)
        sf = json.loads(result)
        assert sf[0]["untestable_consecutive"] == 1

    def test_stale_status_resets_counter(self):
        """STALE is not UNTESTABLE — counter resets.
        This is correct because STALE is about threshold drift, not data absence."""
        sf_json = json.dumps([_sf("f1", "minor", "STALE", 2)])
        result = _pipeline_escalation_roundtrip(sf_json)
        sf = json.loads(result)
        assert sf[0]["status"] == "STALE"
        assert sf[0]["untestable_consecutive"] == 0

    def test_triggered_by_passage_resets_counter(self):
        """TRIGGERED_BY_PASSAGE resets counter (it's a definitive test result)."""
        sf_json = json.dumps([{
            "name": "f1",
            "severity": "medium",
            "status": "TRIGGERED_BY_PASSAGE",
            "untestable_consecutive": 2,
            "staleness_classification": "TRIGGERED_BY_PASSAGE",
        }])
        result = _pipeline_escalation_roundtrip(sf_json)
        sf = json.loads(result)
        assert sf[0]["status"] == "TRIGGERED_BY_PASSAGE"
        assert sf[0]["untestable_consecutive"] == 0

    def test_escalation_threshold_is_three(self):
        """Verify the calibration constant matches plan spec."""
        assert ESCALATION_THRESHOLD == 3
