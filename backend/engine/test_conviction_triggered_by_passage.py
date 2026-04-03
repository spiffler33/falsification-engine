"""Tests for TRIGGERED_BY_PASSAGE D_f integration in the conviction pipeline (v7 Task 11).

Covers:
  Part A — Conviction engine: TRIGGERED_BY_PASSAGE entries in triggered_soft_falsifiers
    produce correct D_f values (same math as TRIGGERED, routed differently).
  Part B — Pipeline assembly: staleness_classification=="TRIGGERED_BY_PASSAGE" on
    soft falsifiers is correctly routed into triggered_sf.

  Key plan checklist items:
    - TRIGGERED_BY_PASSAGE treated as TRIGGERED in D_f at registered severity
    - 3 STALE (classified STALE, not TRIGGERED_BY_PASSAGE) → no D_f penalty
    - 1 TRIGGERED_BY_PASSAGE (medium) + 1 emergent risk (major) → D_f = 0.4125
"""

import json

from backend.engine.conviction import score_conviction, SEVERITY_WEIGHTS
from backend.schemas.scoring import ConvictionInput


def _base_input(**overrides) -> ConvictionInput:
    """Strong baseline: RAW ~0.80 on 0-1 scale = 8.0 on 0-10.

    Horizon and expression gates are set high enough to not interfere.
    """
    defaults = dict(
        hypothesis_id="test-h1",
        support_strength=0.80,
        evidence_quality=0.80,
        convergence=0.80,
        falsifier_clarity=0.80,
        triggered_soft_falsifiers=[],
        untestable_soft_falsifiers=[],
        same_theory_overlap=0,
        diff_theory_overlap=0,
        resolution_channel="",
        active_regime_flags=[],
        sector_falsifier_audit=[],
        horizon_alignment=0.60,
        expression_efficiency=0.50,
    )
    defaults.update(overrides)
    return ConvictionInput(**defaults)


# ===========================================================================
# Part A: Engine-level — TRIGGERED_BY_PASSAGE entries in D_f
# ===========================================================================
# conviction.py treats all entries in triggered_soft_falsifiers identically
# (severity → weight → multiplicative compounding). These tests confirm the
# math and provide explicit coverage for TRIGGERED_BY_PASSAGE scenarios.

# ---------------------------------------------------------------------------
# Scenario 1: TRIGGERED_BY_PASSAGE medium → D_f = 0.75
# ---------------------------------------------------------------------------

def test_triggered_by_passage_medium_df():
    """Single TRIGGERED_BY_PASSAGE at medium severity → D_f = 1 - 0.25 = 0.75."""
    ci = _base_input(
        triggered_soft_falsifiers=[{"severity": "medium"}],
    )
    result = score_conviction(ci)
    expected_df = 1.0 - SEVERITY_WEIGHTS["medium"]
    assert abs(result.stage2.soft_falsifier_discount - expected_df) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 2: TRIGGERED_BY_PASSAGE + regular TRIGGERED compound
# ---------------------------------------------------------------------------

def test_triggered_by_passage_compounds_with_triggered():
    """TRIGGERED minor + TRIGGERED_BY_PASSAGE major → D_f = 0.90 * 0.55 = 0.495."""
    ci = _base_input(
        triggered_soft_falsifiers=[
            {"severity": "minor"},   # regular TRIGGERED
            {"severity": "major"},   # TRIGGERED_BY_PASSAGE (routed by pipeline)
        ],
    )
    result = score_conviction(ci)
    expected_df = (1.0 - 0.10) * (1.0 - 0.45)
    assert abs(result.stage2.soft_falsifier_discount - expected_df) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 3: TRIGGERED_BY_PASSAGE + emergent risk compound
# ---------------------------------------------------------------------------

def test_triggered_by_passage_compounds_with_emergent_risk():
    """TRIGGERED_BY_PASSAGE medium + emergent major → D_f = 0.75 * 0.55 = 0.4125.

    This is the exact plan checklist scenario:
      D_f = (1-0.25) x (1-0.45) = 0.4125
    """
    ci = _base_input(
        triggered_soft_falsifiers=[
            {"severity": "medium"},  # TRIGGERED_BY_PASSAGE
            {"severity": "major"},   # emergent risk
        ],
    )
    result = score_conviction(ci)
    expected_df = (1.0 - 0.25) * (1.0 - 0.45)
    assert abs(expected_df - 0.4125) < 1e-6  # confirm the plan's arithmetic
    assert abs(result.stage2.soft_falsifier_discount - expected_df) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 4: TRIGGERED_BY_PASSAGE alone (no other falsifiers triggered)
# ---------------------------------------------------------------------------

def test_triggered_by_passage_alone():
    """No regular TRIGGERED, no emergent — only TRIGGERED_BY_PASSAGE minor → D_f = 0.90."""
    ci = _base_input(
        triggered_soft_falsifiers=[{"severity": "minor"}],
    )
    result = score_conviction(ci)
    expected_df = 1.0 - 0.10
    assert abs(result.stage2.soft_falsifier_discount - expected_df) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 5: TRIGGERED_BY_PASSAGE lowers final conviction
# ---------------------------------------------------------------------------

def test_triggered_by_passage_lowers_final_conviction():
    """TRIGGERED_BY_PASSAGE should measurably lower the final conviction score."""
    base = _base_input()
    with_passage = _base_input(
        triggered_soft_falsifiers=[{"severity": "major"}],
    )
    result_base = score_conviction(base)
    result_passage = score_conviction(with_passage)

    assert result_passage.stage3.final < result_base.stage3.final


# ===========================================================================
# Part B: Pipeline assembly — staleness_classification routing
# ===========================================================================
# These tests simulate the exact code path from pipeline.py:880
# (build triggered_sf from soft_falsifiers including TRIGGERED_BY_PASSAGE).

def _simulate_triggered_sf_assembly(
    soft_falsifiers_json: str,
    emergent_risk_severity=None,
) -> list:
    """Reproduce the pipeline.py assembly logic for triggered_sf.

    Matches pipeline.py:880-883 after the TRIGGERED_BY_PASSAGE addition.
    """
    soft_f = json.loads(soft_falsifiers_json)
    triggered_sf = [
        {"severity": sf["severity"]}
        for sf in soft_f
        if sf.get("status") == "TRIGGERED"
        or sf.get("staleness_classification") == "TRIGGERED_BY_PASSAGE"
    ]
    if emergent_risk_severity:
        triggered_sf.append({"severity": emergent_risk_severity})
    return triggered_sf


class TestPipelineTriggeredByPassageAssembly:
    """Verify staleness_classification routing into triggered_sf."""

    def test_triggered_by_passage_collected(self):
        """STALE + staleness_classification=TRIGGERED_BY_PASSAGE → in triggered_sf."""
        sf_json = json.dumps([
            {"severity": "medium", "status": "STALE",
             "staleness_classification": "TRIGGERED_BY_PASSAGE"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json)
        assert len(result) == 1
        assert result[0]["severity"] == "medium"

    def test_stale_without_passage_not_collected(self):
        """STALE + staleness_classification=STALE → NOT in triggered_sf."""
        sf_json = json.dumps([
            {"severity": "medium", "status": "STALE",
             "staleness_classification": "STALE"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json)
        assert len(result) == 0

    def test_stale_no_classification_not_collected(self):
        """STALE without staleness_classification → NOT in triggered_sf."""
        sf_json = json.dumps([
            {"severity": "medium", "status": "STALE"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json)
        assert len(result) == 0

    def test_three_stale_all_benign_no_df_penalty(self):
        """Plan checklist: 3 STALE falsifiers (all classified STALE) → no D_f penalty.

        triggered_sf should be empty → D_f remains 1.0.
        """
        sf_json = json.dumps([
            {"severity": "minor", "status": "STALE",
             "staleness_classification": "STALE"},
            {"severity": "medium", "status": "STALE",
             "staleness_classification": "STALE"},
            {"severity": "major", "status": "STALE",
             "staleness_classification": "STALE"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json)
        assert len(result) == 0
        # Confirm D_f = 1.0 through the engine
        ci = _base_input(triggered_soft_falsifiers=result)
        engine_result = score_conviction(ci)
        assert engine_result.stage2.soft_falsifier_discount == 1.0

    def test_triggered_by_passage_alongside_triggered(self):
        """Both regular TRIGGERED and TRIGGERED_BY_PASSAGE collected."""
        sf_json = json.dumps([
            {"severity": "minor", "status": "TRIGGERED"},
            {"severity": "major", "status": "STALE",
             "staleness_classification": "TRIGGERED_BY_PASSAGE"},
            {"severity": "medium", "status": "CLEAR"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json)
        assert len(result) == 2
        assert result[0]["severity"] == "minor"   # regular TRIGGERED
        assert result[1]["severity"] == "major"    # TRIGGERED_BY_PASSAGE

    def test_triggered_by_passage_plus_emergent_risk(self):
        """TRIGGERED_BY_PASSAGE + emergent risk severity → both collected."""
        sf_json = json.dumps([
            {"severity": "medium", "status": "STALE",
             "staleness_classification": "TRIGGERED_BY_PASSAGE"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json, "major")
        assert len(result) == 2
        assert result[0]["severity"] == "medium"   # TRIGGERED_BY_PASSAGE
        assert result[1]["severity"] == "major"     # emergent risk

    def test_full_mix_all_sources(self):
        """All three D_f sources: TRIGGERED + TRIGGERED_BY_PASSAGE + emergent risk."""
        sf_json = json.dumps([
            {"severity": "minor", "status": "TRIGGERED"},
            {"severity": "medium", "status": "STALE",
             "staleness_classification": "TRIGGERED_BY_PASSAGE"},
            {"severity": "major", "status": "STALE",
             "staleness_classification": "STALE"},
            {"severity": "minor", "status": "CLEAR"},
            {"severity": "medium", "status": "UNTESTABLE"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json, "major")
        assert len(result) == 3
        severities = [r["severity"] for r in result]
        assert severities == ["minor", "medium", "major"]
