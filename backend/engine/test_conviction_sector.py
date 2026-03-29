"""Tests for sector falsifier D_f integration in the conviction pipeline (v4).

Covers the five illustrative scenarios from plan_v4.md:
  1. Clean — no falsifiers triggered
  2. Theory minor only
  3. Theory minor + sector medium (triggered AND relevant)
  4. Theory major + sector medium (triggered AND relevant) → floor
  5. Sector medium triggered but NOT relevant → no discount
"""

from backend.engine.conviction import score_conviction
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
# Scenario 1: Clean — no falsifiers triggered
# RAW = 0.80 * 10 = 8.0, D_f = 1.00, SCORE = 8.0
# ---------------------------------------------------------------------------

def test_clean_no_falsifiers():
    result = score_conviction(_base_input())
    assert abs(result.stage1.raw - 8.0) < 1e-6
    assert result.stage2.soft_falsifier_discount == 1.0
    assert result.stage2.sector_falsifier_discount == 1.0
    assert abs(result.stage2.adjusted - 8.0) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 2: Theory minor only
# D_f = 0.90, SCORE = 8.0 * 0.90 = 7.2
# ---------------------------------------------------------------------------

def test_theory_minor_only():
    result = score_conviction(_base_input(
        triggered_soft_falsifiers=[{"severity": "minor"}],
    ))
    assert abs(result.stage1.raw - 8.0) < 1e-6
    assert abs(result.stage2.soft_falsifier_discount - 0.90) < 1e-6
    assert result.stage2.sector_falsifier_discount == 1.0
    assert abs(result.stage2.adjusted - 7.2) < 1e-6


# ---------------------------------------------------------------------------
# Scenario 3: Theory minor + sector medium (triggered AND relevant)
# Theory D_f = 0.90, sector = 0.75, combined = 0.675
# SCORE = 8.0 * 0.675 = 5.4
# ---------------------------------------------------------------------------

def test_theory_minor_plus_sector_medium_relevant():
    result = score_conviction(_base_input(
        triggered_soft_falsifiers=[{"severity": "minor"}],
        sector_falsifier_audit=[{
            "hypothesis_id": "test-h1",
            "falsifier_id": "tech_sf_01",
            "triggered": "YES",
            "relevant": "YES",
            "severity_applied": "medium",
            "reasoning": "Attacks the hypothesis mechanism",
        }],
    ))
    assert abs(result.stage1.raw - 8.0) < 1e-6
    # Combined D_f includes both theory and sector
    assert abs(result.stage2.soft_falsifier_discount - 0.675) < 1e-6
    assert abs(result.stage2.sector_falsifier_discount - 0.75) < 1e-6
    assert abs(result.stage2.adjusted - 5.4) < 1e-6
    # Sector entry recorded in audit
    assert len(result.stage2.sector_falsifier_entries) == 1


# ---------------------------------------------------------------------------
# Scenario 4: Theory major + sector medium (triggered AND relevant)
# RAW = 0.75 * 10 = 7.5, D_f = 0.55 * 0.75 = 0.4125
# SCORE = 7.5 * 0.4125 = 3.09375 → rounds to 3 → floor to 5
# ---------------------------------------------------------------------------

def test_theory_major_plus_sector_medium_floor():
    result = score_conviction(_base_input(
        support_strength=0.75,
        evidence_quality=0.75,
        convergence=0.75,
        falsifier_clarity=0.75,
        triggered_soft_falsifiers=[{"severity": "major"}],
        sector_falsifier_audit=[{
            "hypothesis_id": "test-h1",
            "falsifier_id": "financials_sf_01",
            "triggered": "YES",
            "relevant": "YES",
            "severity_applied": "medium",
            "reasoning": "CRE delinquency attacks the bank earnings thesis",
        }],
    ))
    assert abs(result.stage1.raw - 7.5) < 1e-6
    assert abs(result.stage2.soft_falsifier_discount - 0.4125) < 1e-9
    # Score = 7.5 * 0.4125 = 3.09375 → after Stage 3, floor kicks in
    assert result.stage3.floor_killed is True
    # Floor raises the kill flag but the final score is the rounded value
    assert result.stage3.final <= 5.0


# ---------------------------------------------------------------------------
# Scenario 5: Sector medium triggered but NOT relevant → NO discount
# D_f = 1.00, SCORE = 8.0
# ---------------------------------------------------------------------------

def test_sector_triggered_but_not_relevant():
    result = score_conviction(_base_input(
        sector_falsifier_audit=[{
            "hypothesis_id": "test-h1",
            "falsifier_id": "tech_sf_01",
            "triggered": "YES",
            "relevant": "NO",
            "severity_applied": "medium",
            "reasoning": "Semiconductor inventory does not attack liquidity mechanism",
        }],
    ))
    assert abs(result.stage1.raw - 8.0) < 1e-6
    assert result.stage2.soft_falsifier_discount == 1.0
    assert result.stage2.sector_falsifier_discount == 1.0
    assert abs(result.stage2.adjusted - 8.0) < 1e-6
    # No sector entries should have been applied
    assert len(result.stage2.sector_falsifier_entries) == 0


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

def test_sector_not_triggered():
    """triggered == NO → no discount regardless of other fields."""
    result = score_conviction(_base_input(
        sector_falsifier_audit=[{
            "hypothesis_id": "test-h1",
            "falsifier_id": "energy_sf_01",
            "triggered": "NO",
            "relevant": "N/A",
            "severity_applied": "NONE",
            "reasoning": "Threshold not breached",
        }],
    ))
    assert result.stage2.soft_falsifier_discount == 1.0
    assert result.stage2.sector_falsifier_discount == 1.0
    assert len(result.stage2.sector_falsifier_entries) == 0


def test_multiple_sector_falsifiers_compound():
    """Two triggered+relevant sector falsifiers compound multiplicatively."""
    result = score_conviction(_base_input(
        sector_falsifier_audit=[
            {
                "hypothesis_id": "test-h1",
                "falsifier_id": "tech_sf_01",
                "triggered": "YES",
                "relevant": "YES",
                "severity_applied": "medium",
                "reasoning": "Attacks mechanism A",
            },
            {
                "hypothesis_id": "test-h1",
                "falsifier_id": "tech_sf_02",
                "triggered": "YES",
                "relevant": "YES",
                "severity_applied": "minor",
                "reasoning": "Attacks mechanism B",
            },
        ],
    ))
    # sector_d_f = 0.75 * 0.90 = 0.675
    assert abs(result.stage2.sector_falsifier_discount - 0.675) < 1e-9
    # Combined D_f = 1.0 (no theory) * 0.675 = 0.675
    assert abs(result.stage2.soft_falsifier_discount - 0.675) < 1e-9
    assert len(result.stage2.sector_falsifier_entries) == 2


def test_mixed_relevant_and_not_relevant():
    """Only triggered+relevant entries produce discounts; others are ignored."""
    result = score_conviction(_base_input(
        sector_falsifier_audit=[
            {
                "hypothesis_id": "test-h1",
                "falsifier_id": "tech_sf_01",
                "triggered": "YES",
                "relevant": "YES",
                "severity_applied": "medium",
                "reasoning": "Relevant attack",
            },
            {
                "hypothesis_id": "test-h1",
                "falsifier_id": "tech_sf_02",
                "triggered": "YES",
                "relevant": "NO",
                "severity_applied": "major",
                "reasoning": "Not relevant to this mechanism",
            },
        ],
    ))
    # Only the medium one applies: sector_d_f = 0.75
    assert abs(result.stage2.sector_falsifier_discount - 0.75) < 1e-9
    assert len(result.stage2.sector_falsifier_entries) == 1
