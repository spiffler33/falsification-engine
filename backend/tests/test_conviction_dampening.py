# test_conviction_dampening.py — Tests for conviction dampening + hysteresis floor.
#
# Tests the compute_effective_conviction() governance function which:
# 1. Blends new score with prior for CONFIRM/UPDATE (reduces volatility)
# 2. Raises resurrection floor from 5 to 6 for previously-KILLED hypotheses
from __future__ import annotations

import pytest

from backend.api.pipeline import compute_effective_conviction


class TestConvictionDampening:
    """Dampening blends new score with prior for CONFIRM/UPDATE hypotheses."""

    def test_dampening_saves_from_kill(self):
        """CONFIRM with prior=6, raw=4 -> effective=5 (0.7*4+0.3*6=4.6 -> round=5), survives."""
        eff, floor, killed = compute_effective_conviction(4.0, "CONFIRM", 6.0, False)
        assert eff == 5.0
        assert floor == 5.0
        assert killed is False

    def test_dampening_not_enough(self):
        """UPDATE with prior=7, raw=3 -> effective=4 (0.7*3+0.3*7=4.2 -> round=4), killed."""
        eff, floor, killed = compute_effective_conviction(3.0, "UPDATE", 7.0, False)
        assert eff == 4.0
        assert floor == 5.0
        assert killed is True

    def test_no_dampening_for_new(self):
        """NEW hypotheses get no dampening (no prior)."""
        eff, floor, killed = compute_effective_conviction(4.0, "NEW", None, False)
        assert eff == 4.0
        assert floor == 5.0
        assert killed is True

    def test_no_dampening_for_renew(self):
        """RENEW hypotheses get no dampening (new economic content)."""
        eff, floor, killed = compute_effective_conviction(4.0, "RENEW", 6.0, False)
        assert eff == 4.0
        assert floor == 5.0
        assert killed is True

    def test_no_dampening_when_no_prior_conviction(self):
        """CONFIRM with prior_conviction=None (first run) gets no dampening."""
        eff, floor, killed = compute_effective_conviction(4.0, "CONFIRM", None, False)
        assert eff == 4.0
        assert killed is True

    def test_dampening_clamps_to_10(self):
        """Effective score cannot exceed 10."""
        eff, floor, killed = compute_effective_conviction(10.0, "CONFIRM", 10.0, False)
        assert eff == 10.0
        assert killed is False

    def test_dampening_clamps_to_0(self):
        """Effective score cannot go below 0."""
        eff, floor, killed = compute_effective_conviction(0.0, "CONFIRM", 0.0, False)
        assert eff == 0.0
        # 0 is not floor_killed (special case: 0 means not scored)
        assert killed is False

    def test_dampening_preserves_strong_score(self):
        """CONFIRM with prior=7, raw=8 -> effective=8 (0.7*8+0.3*7=7.7 -> round=8)."""
        eff, floor, killed = compute_effective_conviction(8.0, "CONFIRM", 7.0, False)
        assert eff == 8.0
        assert killed is False


class TestConvictionHysteresis:
    """Hysteresis raises the floor from 5 to 6 for previously-KILLED hypotheses."""

    def test_hysteresis_blocks_weak_resurrection(self):
        """Prior KILLED + raw=5, prior=4 -> eff=5 (0.7*5+0.3*4=4.7->5), floor=6, killed."""
        eff, floor, killed = compute_effective_conviction(5.0, "CONFIRM", 4.0, True)
        assert eff == 5.0
        assert floor == 6.0
        assert killed is True

    def test_hysteresis_allows_strong_resurrection(self):
        """Prior KILLED + raw=7, prior=4 -> eff=6 (0.7*7+0.3*4=6.1->6), floor=6, survives."""
        eff, floor, killed = compute_effective_conviction(7.0, "CONFIRM", 4.0, True)
        assert eff == 6.0
        assert floor == 6.0
        assert killed is False

    def test_hysteresis_without_dampening_for_new(self):
        """NEW hypothesis with prior_was_killed=True still uses floor=6."""
        eff, floor, killed = compute_effective_conviction(5.0, "NEW", None, True)
        assert eff == 5.0
        assert floor == 6.0
        assert killed is True

    def test_standard_floor_when_not_prior_killed(self):
        """Prior SURVIVED uses standard floor=5."""
        eff, floor, killed = compute_effective_conviction(5.0, "CONFIRM", 6.0, False)
        assert floor == 5.0
        assert killed is False

    def test_hysteresis_at_exact_boundary(self):
        """Score exactly at hysteresis floor (6) survives."""
        eff, floor, killed = compute_effective_conviction(6.0, "NEW", None, True)
        assert eff == 6.0
        assert floor == 6.0
        assert killed is False


class TestConvictionDampeningEdgeCases:
    """Edge cases and interaction between dampening and hysteresis."""

    def test_dampening_plus_hysteresis_combined(self):
        """CONFIRM + prior KILLED: dampening AND hysteresis both apply.
        raw=6, prior=3 -> eff=round(0.7*6+0.3*3)=round(5.1)=5, floor=6 -> killed.
        """
        eff, floor, killed = compute_effective_conviction(6.0, "CONFIRM", 3.0, True)
        assert eff == 5.0
        assert floor == 6.0
        assert killed is True

    def test_lifecycle_action_none(self):
        """None lifecycle_action gets no dampening (same as NEW)."""
        eff, floor, killed = compute_effective_conviction(4.0, None, 6.0, False)
        assert eff == 4.0
        assert killed is True

    def test_score_of_1_is_killed(self):
        """Score of 1 is above 0 and below floor, so killed."""
        eff, floor, killed = compute_effective_conviction(1.0, "NEW", None, False)
        assert eff == 1.0
        assert killed is True
