"""Tests for ESCALATED_UNTESTABLE D_u penalty in conviction pipeline (v7 Task 10).

Covers:
  Part A -- Conviction engine: ESCALATED_UNTESTABLE entries in untestable_soft_falsifiers
    receive heavier D_u discount than regular UNTESTABLE entries.
  Part B -- Boundary and interaction: floor, stacking, final score integration.

  Scenarios:
    1. No untestable falsifiers -- D_u = 1.0 (baseline)
    2. Regular UNTESTABLE minor -- base penalty only
    3. ESCALATED_UNTESTABLE minor -- base penalty + escalation penalty
    4. Regular UNTESTABLE major vs ESCALATED_UNTESTABLE major -- heavier for escalated
    5. Mixed UNTESTABLE + ESCALATED_UNTESTABLE -- both penalties compound
    6. Multiple ESCALATED_UNTESTABLE -- escalation penalty per entry
    7. D_u floor at 0.05 with stacked escalated majors
    8. Final conviction score reflects escalated D_u discount
    9. Backward compatible: entries without status field get base penalty only
"""

from backend.engine.conviction import (
    score_conviction,
    UNTESTABLE_WEIGHTS,
    UNTESTABLE_ESCALATION_PENALTY,
)
from backend.schemas.scoring import ConvictionInput


def _base_input(**overrides) -> ConvictionInput:
    """Strong baseline: RAW ~0.80 on 0-1 scale = 8.0 on 0-10.

    Horizon and expression gates set high enough to not interfere.
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


# ===================================================================
# Part A: D_u values from UNTESTABLE vs ESCALATED_UNTESTABLE
# ===================================================================

class TestEscalatedUntestableDu:
    """Verify that ESCALATED_UNTESTABLE applies a heavier D_u penalty."""

    def test_no_untestable_du_is_one(self):
        """Baseline: no untestable falsifiers, D_u = 1.0."""
        inp = _base_input(untestable_soft_falsifiers=[])
        result = score_conviction(inp)
        assert result.stage2.untestable_discount == 1.0

    def test_regular_untestable_minor_base_only(self):
        """Regular UNTESTABLE minor: D_u = 1 - 0.05 = 0.95."""
        inp = _base_input(untestable_soft_falsifiers=[
            {"severity": "minor", "status": "UNTESTABLE"},
        ])
        result = score_conviction(inp)
        expected = 1.0 - UNTESTABLE_WEIGHTS["minor"]  # 0.95
        assert abs(result.stage2.untestable_discount - expected) < 1e-9

    def test_escalated_untestable_minor_heavier(self):
        """ESCALATED_UNTESTABLE minor: D_u = (1-0.05) * (1-0.05) = 0.9025."""
        inp = _base_input(untestable_soft_falsifiers=[
            {"severity": "minor", "status": "ESCALATED_UNTESTABLE"},
        ])
        result = score_conviction(inp)
        base = 1.0 - UNTESTABLE_WEIGHTS["minor"]  # 0.95
        expected = base * (1.0 - UNTESTABLE_ESCALATION_PENALTY)  # 0.95 * 0.95 = 0.9025
        assert abs(result.stage2.untestable_discount - expected) < 1e-9

    def test_escalated_vs_regular_major(self):
        """ESCALATED_UNTESTABLE major is strictly heavier than regular UNTESTABLE major."""
        regular = _base_input(untestable_soft_falsifiers=[
            {"severity": "major", "status": "UNTESTABLE"},
        ])
        escalated = _base_input(untestable_soft_falsifiers=[
            {"severity": "major", "status": "ESCALATED_UNTESTABLE"},
        ])
        d_u_regular = score_conviction(regular).stage2.untestable_discount
        d_u_escalated = score_conviction(escalated).stage2.untestable_discount

        # Regular: 1 - 0.15 = 0.85
        # Escalated: 0.85 * (1 - 0.05) = 0.8075
        assert d_u_regular > d_u_escalated
        assert abs(d_u_regular - 0.85) < 1e-9
        assert abs(d_u_escalated - (0.85 * 0.95)) < 1e-9

    def test_mixed_untestable_and_escalated(self):
        """One UNTESTABLE + one ESCALATED: both base penalties, only escalated gets extra."""
        inp = _base_input(untestable_soft_falsifiers=[
            {"severity": "minor", "status": "UNTESTABLE"},
            {"severity": "medium", "status": "ESCALATED_UNTESTABLE"},
        ])
        result = score_conviction(inp)
        # minor base: 1 - 0.05 = 0.95
        # medium base: 1 - 0.10 = 0.90
        # medium escalation: 1 - 0.05 = 0.95
        # D_u = 0.95 * 0.90 * 0.95 = 0.81225
        expected = (1.0 - 0.05) * (1.0 - 0.10) * (1.0 - UNTESTABLE_ESCALATION_PENALTY)
        assert abs(result.stage2.untestable_discount - expected) < 1e-9

    def test_multiple_escalated(self):
        """Two ESCALATED_UNTESTABLE: each gets its own base + escalation penalty."""
        inp = _base_input(untestable_soft_falsifiers=[
            {"severity": "minor", "status": "ESCALATED_UNTESTABLE"},
            {"severity": "major", "status": "ESCALATED_UNTESTABLE"},
        ])
        result = score_conviction(inp)
        # minor: (1-0.05) * (1-0.05) = 0.9025
        # major: (1-0.15) * (1-0.05) = 0.8075
        # D_u = 0.9025 * 0.8075
        expected = (0.95 * 0.95) * (0.85 * 0.95)
        assert abs(result.stage2.untestable_discount - expected) < 1e-9


# ===================================================================
# Part B: Boundary and interaction tests
# ===================================================================

class TestEscalatedUntestableBoundary:
    """Floor, stacking, and final score integration."""

    def test_floor_with_stacked_escalated_majors(self):
        """D_u cannot go below 0.05, even with many escalated majors.

        Each escalated major applies (1-0.15)*(1-0.05) = 0.8075.
        Need enough to push below 0.05: 0.8075^14 = ~0.046 < 0.05.
        """
        entries = [{"severity": "major", "status": "ESCALATED_UNTESTABLE"}] * 15
        inp = _base_input(untestable_soft_falsifiers=entries)
        result = score_conviction(inp)
        assert result.stage2.untestable_discount == 0.05

    def test_final_score_reflects_escalation(self):
        """Escalated D_u reduces the final conviction score."""
        regular = _base_input(untestable_soft_falsifiers=[
            {"severity": "medium", "status": "UNTESTABLE"},
        ])
        escalated = _base_input(untestable_soft_falsifiers=[
            {"severity": "medium", "status": "ESCALATED_UNTESTABLE"},
        ])
        score_regular = score_conviction(regular).stage3.final
        score_escalated = score_conviction(escalated).stage3.final
        assert score_regular >= score_escalated

    def test_backward_compatible_no_status(self):
        """Entries without 'status' field get base penalty only (no escalation)."""
        inp = _base_input(untestable_soft_falsifiers=[
            {"severity": "minor"},
        ])
        result = score_conviction(inp)
        expected = 1.0 - UNTESTABLE_WEIGHTS["minor"]  # 0.95
        assert abs(result.stage2.untestable_discount - expected) < 1e-9

    def test_escalation_penalty_constant_value(self):
        """UNTESTABLE_ESCALATION_PENALTY matches the plan spec: 0.05."""
        assert UNTESTABLE_ESCALATION_PENALTY == 0.05
