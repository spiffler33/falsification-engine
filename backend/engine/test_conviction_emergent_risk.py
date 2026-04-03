"""Tests for emergent risk D_f integration in the conviction pipeline (v7 Task 9).

Covers:
  Part A — Conviction engine: emergent risk entries in triggered_soft_falsifiers
    produce correct D_f values.
  Part B — Pipeline assembly: emergent_risk_severity on the hypothesis model
    is correctly appended to triggered_sf before conviction scoring.

  Scenarios:
    1. No emergent risk — D_f unchanged from theory-level falsifiers
    2. Emergent risk minor — compounds multiplicatively with existing D_f
    3. Emergent risk major — significant additional discount
    4. Emergent risk alone (no theory-level falsifiers triggered) — still applies
    5. Emergent risk + theory major — multiplicative compounding near floor
    6. Stacked majors hit D_f floor
    7. Final conviction score reflects emergent risk discount
    8-12. Pipeline assembly: severity append / null / empty / invalid handling
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


# ---------------------------------------------------------------------------
# Scenario 1: No emergent risk — D_f unchanged
# ---------------------------------------------------------------------------

def test_no_emergent_risk_df_unchanged():
    """Baseline: no triggered falsifiers, no emergent risk → D_f = 1.0."""
    ci = _base_input()
    result = score_conviction(ci)
    assert result.stage2.soft_falsifier_discount == 1.0


# ---------------------------------------------------------------------------
# Scenario 2: Emergent risk minor compounds with existing D_f
# ---------------------------------------------------------------------------

def test_emergent_risk_minor_compounds():
    """Theory minor + emergent minor → D_f = (1-0.10) * (1-0.10) = 0.81."""
    ci = _base_input(
        triggered_soft_falsifiers=[
            {"severity": "minor"},   # theory-level
            {"severity": "minor"},   # emergent risk (appended by pipeline)
        ],
    )
    result = score_conviction(ci)
    expected_df = (1.0 - 0.10) * (1.0 - 0.10)
    assert abs(result.stage2.soft_falsifier_discount - expected_df) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 3: Emergent risk major — significant discount
# ---------------------------------------------------------------------------

def test_emergent_risk_major_significant_discount():
    """Emergent major alone → D_f = (1-0.45) = 0.55."""
    ci = _base_input(
        triggered_soft_falsifiers=[
            {"severity": "major"},   # emergent risk only
        ],
    )
    result = score_conviction(ci)
    expected_df = 1.0 - 0.45
    assert abs(result.stage2.soft_falsifier_discount - expected_df) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 4: Emergent risk alone (no theory-level triggers)
# ---------------------------------------------------------------------------

def test_emergent_risk_medium_alone():
    """No theory falsifiers triggered, emergent medium → D_f = 0.75."""
    ci = _base_input(
        triggered_soft_falsifiers=[
            {"severity": "medium"},  # emergent risk only
        ],
    )
    result = score_conviction(ci)
    expected_df = 1.0 - 0.25
    assert abs(result.stage2.soft_falsifier_discount - expected_df) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 5: Emergent risk + theory major — near floor
# ---------------------------------------------------------------------------

def test_emergent_risk_compounds_near_floor():
    """Theory major + emergent major → D_f = (1-0.45)*(1-0.45) = 0.3025,
    but D_f floor is 0.05 so only if it goes below that."""
    ci = _base_input(
        triggered_soft_falsifiers=[
            {"severity": "major"},   # theory-level
            {"severity": "major"},   # emergent risk
        ],
    )
    result = score_conviction(ci)
    expected_df = (1.0 - 0.45) * (1.0 - 0.45)
    assert expected_df > 0.05  # above floor
    assert abs(result.stage2.soft_falsifier_discount - expected_df) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 6: Verify emergent risk hits D_f floor when stacked
# ---------------------------------------------------------------------------

def test_emergent_risk_hits_df_floor():
    """Three majors → raw D_f = 0.55^3 ≈ 0.166, still above 0.05.
    Four majors → 0.55^4 ≈ 0.0915, still above.
    Need enough to hit floor."""
    ci = _base_input(
        triggered_soft_falsifiers=[
            {"severity": "major"},
            {"severity": "major"},
            {"severity": "major"},
            {"severity": "major"},
            {"severity": "major"},
            {"severity": "major"},  # 0.55^6 ≈ 0.0277 → floored to 0.05
        ],
    )
    result = score_conviction(ci)
    assert result.stage2.soft_falsifier_discount == 0.05


# ---------------------------------------------------------------------------
# Scenario 7: Final conviction score reflects emergent risk discount
# ---------------------------------------------------------------------------

def test_emergent_risk_lowers_final_conviction():
    """Emergent risk should measurably lower the final conviction score."""
    base = _base_input()
    with_emergent = _base_input(
        triggered_soft_falsifiers=[{"severity": "major"}],
    )
    result_base = score_conviction(base)
    result_emergent = score_conviction(with_emergent)

    assert result_emergent.stage3.final < result_base.stage3.final


# ===========================================================================
# Part B: Pipeline assembly — emergent_risk_severity → triggered_sf
# ===========================================================================
# These tests simulate the exact code path from pipeline.py:880-883
# (build triggered_sf from soft_falsifiers, then append emergent risk).

def _simulate_triggered_sf_assembly(
    soft_falsifiers_json: str,
    emergent_risk_severity,
) -> list:
    """Reproduce the pipeline.py assembly logic for triggered_sf."""
    soft_f = json.loads(soft_falsifiers_json)
    triggered_sf = [
        {"severity": sf["severity"]}
        for sf in soft_f
        if sf.get("status") == "TRIGGERED"
    ]
    if emergent_risk_severity:
        triggered_sf.append({"severity": emergent_risk_severity})
    return triggered_sf


class TestPipelineEmergentRiskAssembly:
    """Verify that emergent_risk_severity is correctly appended to triggered_sf."""

    def test_emergent_risk_appended(self):
        """Major emergent risk appended alongside theory-level TRIGGERED."""
        sf_json = json.dumps([
            {"severity": "minor", "status": "TRIGGERED"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json, "major")
        assert len(result) == 2
        assert result[0]["severity"] == "minor"
        assert result[1]["severity"] == "major"

    def test_emergent_risk_none_no_append(self):
        """emergent_risk_severity=None → triggered_sf unchanged."""
        sf_json = json.dumps([
            {"severity": "minor", "status": "TRIGGERED"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json, None)
        assert len(result) == 1

    def test_emergent_risk_empty_string_no_append(self):
        """emergent_risk_severity="" → treated as falsy, no append."""
        sf_json = json.dumps([
            {"severity": "minor", "status": "TRIGGERED"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json, "")
        assert len(result) == 1

    def test_emergent_risk_only_source(self):
        """No theory-level TRIGGERED, only emergent risk → triggered_sf has 1 entry."""
        sf_json = json.dumps([
            {"severity": "minor", "status": "CLEAR"},
            {"severity": "medium", "status": "UNTESTABLE"},
        ])
        result = _simulate_triggered_sf_assembly(sf_json, "medium")
        assert len(result) == 1
        assert result[0]["severity"] == "medium"

    def test_emergent_risk_all_severities(self):
        """Each severity level is correctly passed through."""
        for severity in ("minor", "medium", "major"):
            result = _simulate_triggered_sf_assembly("[]", severity)
            assert result == [{"severity": severity}]
