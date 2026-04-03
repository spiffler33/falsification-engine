# test_lifecycle.py — Tests for falsifier lifecycle pure functions (v7).
# Component 2: Mechanical staleness gate (2x rule)
# Component 6: UNTESTABLE escalation (N=3 step function)
import pytest

from backend.lifecycle import (
    _parse_threshold_value,
    compute_staleness_flag,
    compute_thread_staleness,
    compute_untestable_escalation,
    apply_untestable_escalation,
    STALENESS_MULTIPLIER,
    ESCALATION_THRESHOLD,
)


# ===================================================================
# _parse_threshold_value
# ===================================================================

class TestParseThresholdValue:
    def test_simple_number(self):
        assert _parse_threshold_value("18") == 18.0

    def test_below_format(self):
        """'VIX below 18' -> 18.0"""
        assert _parse_threshold_value("VIX below 18") == 18.0

    def test_above_format(self):
        """'spread above 2.5%' -> 2.5"""
        assert _parse_threshold_value("spread above 2.5%") == 2.5

    def test_greater_than(self):
        assert _parse_threshold_value("> 3.0") == 3.0

    def test_negative_value(self):
        assert _parse_threshold_value("falls below -0.5") == -0.5

    def test_decimal_value(self):
        assert _parse_threshold_value("exceeds 1.25") == 1.25

    def test_multiple_numbers_takes_last(self):
        """When multiple numbers present, take the last (the threshold)."""
        assert _parse_threshold_value("10Y-2Y spread below 0.50") == 0.50

    def test_none_input(self):
        assert _parse_threshold_value(None) is None

    def test_no_number(self):
        assert _parse_threshold_value("no numeric value here") is None

    def test_empty_string(self):
        assert _parse_threshold_value("") is None


# ===================================================================
# compute_staleness_flag — The 2x Rule
# ===================================================================

class TestComputeStalenessFlag:
    """
    The 2x rule: if market has moved > 2x the original distance
    from threshold to generation value, the falsifier is STALE.

    Example from plan: VIX falsifier at "below 18" when VIX was 14.
    distance_at_generation = |18 - 14| = 4
    If VIX now 32: distance_current = |32 - 18| = 14 > 2*4 = 8 -> STALE
    """

    def test_plan_example_vix_stale(self):
        """VIX at 14, threshold 18, now 32 -> STALE (14 > 8)."""
        f = {"threshold": "VIX below 18", "metric": "vix"}
        result = compute_staleness_flag(f, generation_market_value=14.0, current_market_value=32.0)
        assert result == "STALE"

    def test_not_stale_within_range(self):
        """VIX at 14, threshold 18, now 20 -> not stale (2 < 8)."""
        f = {"threshold": "VIX below 18", "metric": "vix"}
        result = compute_staleness_flag(f, generation_market_value=14.0, current_market_value=20.0)
        assert result is None

    def test_exactly_at_2x_boundary_not_stale(self):
        """At exactly 2x, not stale (requires strictly greater than)."""
        # distance_at_gen = |18 - 14| = 4, 2x = 8
        # current must be > 8 from threshold to be stale
        # threshold=18, so current must be > 26 or < 10
        f = {"threshold": "below 18", "metric": "vix"}
        result = compute_staleness_flag(f, generation_market_value=14.0, current_market_value=26.0)
        assert result is None  # |26-18| = 8 = 2*4, not strictly greater

    def test_just_past_2x_boundary_stale(self):
        """Just past 2x -> STALE."""
        f = {"threshold": "below 18", "metric": "vix"}
        result = compute_staleness_flag(f, generation_market_value=14.0, current_market_value=26.01)
        assert result == "STALE"

    def test_market_moved_opposite_direction(self):
        """Market moved away from threshold in opposite direction -> can be STALE."""
        # Gen value 14, threshold 18. Market drops to 1.
        # distance_at_gen = 4, distance_current = |1 - 18| = 17 > 8 -> STALE
        f = {"threshold": "below 18", "metric": "vix"}
        result = compute_staleness_flag(f, generation_market_value=14.0, current_market_value=1.0)
        assert result == "STALE"

    def test_spread_above_threshold(self):
        """Spread was 1.5, threshold 'above 2.5%', now 8.0 -> STALE."""
        f = {"threshold": "spread above 2.5%", "metric": "credit_spread"}
        # distance_at_gen = |2.5 - 1.5| = 1.0, 2x = 2.0
        # distance_current = |8.0 - 2.5| = 5.5 > 2.0 -> STALE
        result = compute_staleness_flag(f, generation_market_value=1.5, current_market_value=8.0)
        assert result == "STALE"

    def test_missing_generation_value(self):
        """No generation_market_value -> None (cannot compute)."""
        f = {"threshold": "below 18", "metric": "vix"}
        result = compute_staleness_flag(f, generation_market_value=None, current_market_value=32.0)
        assert result is None

    def test_missing_current_value(self):
        """No current_market_value -> None (cannot compute)."""
        f = {"threshold": "below 18", "metric": "vix"}
        result = compute_staleness_flag(f, generation_market_value=14.0, current_market_value=None)
        assert result is None

    def test_unparseable_threshold(self):
        """Threshold with no number -> None."""
        f = {"threshold": "qualitative assessment only", "metric": "sentiment"}
        result = compute_staleness_flag(f, generation_market_value=14.0, current_market_value=32.0)
        assert result is None

    def test_threshold_at_generation_value(self):
        """Degenerate case: threshold == generation value -> distance 0 -> None."""
        f = {"threshold": "below 14", "metric": "vix"}
        result = compute_staleness_flag(f, generation_market_value=14.0, current_market_value=50.0)
        assert result is None

    def test_negative_threshold(self):
        """Negative threshold value (e.g., real rates below -0.5)."""
        f = {"threshold": "falls below -0.5", "metric": "real_rate"}
        # Gen value 0.5, threshold -0.5, distance = 1.0, 2x = 2.0
        # Current -3.0: distance = |-3.0 - (-0.5)| = 2.5 > 2.0 -> STALE
        result = compute_staleness_flag(f, generation_market_value=0.5, current_market_value=-3.0)
        assert result == "STALE"

    def test_missing_threshold_key(self):
        """Falsifier dict missing threshold key -> None."""
        f = {"metric": "vix"}
        result = compute_staleness_flag(f, generation_market_value=14.0, current_market_value=32.0)
        assert result is None


# ===================================================================
# compute_thread_staleness — batch across falsifiers
# ===================================================================

class TestComputeThreadStaleness:
    def test_mixed_stale_and_fresh(self):
        """Two falsifiers: one goes stale, one stays fresh."""
        falsifiers = [
            {
                "name": "VIX calm",
                "metric": "vix",
                "threshold": "below 18",
                "generation_market_value": 14.0,
                "status": "CLEAR",
            },
            {
                "name": "Spread narrow",
                "metric": "credit_spread",
                "threshold": "below 2.0",
                "generation_market_value": 1.5,
                "status": "UNTESTABLE",
            },
        ]
        current = {"vix": 32.0, "credit_spread": 1.8}

        result = compute_thread_staleness(falsifiers, current)

        assert len(result) == 2
        assert result[0]["staleness_flag"] == "STALE"  # VIX moved too far
        assert result[1]["staleness_flag"] is None       # spread still in range

    def test_does_not_mutate_input(self):
        """Input list must not be modified."""
        falsifiers = [
            {
                "name": "VIX calm",
                "metric": "vix",
                "threshold": "below 18",
                "generation_market_value": 14.0,
                "status": "CLEAR",
            },
        ]
        original_copy = [dict(f) for f in falsifiers]
        compute_thread_staleness(falsifiers, {"vix": 32.0})
        assert falsifiers == original_copy

    def test_missing_metric_in_current_values(self):
        """Metric not in briefing packet -> staleness_flag is None."""
        falsifiers = [
            {
                "name": "VIX calm",
                "metric": "vix",
                "threshold": "below 18",
                "generation_market_value": 14.0,
                "status": "CLEAR",
            },
        ]
        result = compute_thread_staleness(falsifiers, {})  # no vix in current
        assert result[0]["staleness_flag"] is None

    def test_empty_falsifiers(self):
        """Empty list -> empty result."""
        result = compute_thread_staleness([], {"vix": 20.0})
        assert result == []

    def test_preserves_existing_fields(self):
        """All original fields preserved in output."""
        falsifiers = [
            {
                "name": "VIX calm",
                "metric": "vix",
                "threshold": "below 18",
                "severity": "medium",
                "generation_market_value": 14.0,
                "status": "UNTESTABLE",
                "untestable_consecutive": 2,
            },
        ]
        result = compute_thread_staleness(falsifiers, {"vix": 15.0})
        assert result[0]["name"] == "VIX calm"
        assert result[0]["severity"] == "medium"
        assert result[0]["status"] == "UNTESTABLE"
        assert result[0]["untestable_consecutive"] == 2


# ===================================================================
# compute_untestable_escalation — N=3 Step Function
# ===================================================================

class TestComputeUntestableEscalation:
    """
    Counter increments each time a falsifier is UNTESTABLE.
    At N=3 (default), status becomes ESCALATED_UNTESTABLE.
    Any non-UNTESTABLE status resets the counter to 0.
    """

    def test_first_untestable(self):
        """First UNTESTABLE pass: count=1, stays UNTESTABLE."""
        status, count = compute_untestable_escalation("UNTESTABLE", 0)
        assert status == "UNTESTABLE"
        assert count == 1

    def test_second_untestable(self):
        """Second UNTESTABLE pass: count=2, still UNTESTABLE."""
        status, count = compute_untestable_escalation("UNTESTABLE", 1)
        assert status == "UNTESTABLE"
        assert count == 2

    def test_third_untestable_escalates(self):
        """Third consecutive UNTESTABLE -> ESCALATED_UNTESTABLE."""
        status, count = compute_untestable_escalation("UNTESTABLE", 2)
        assert status == "ESCALATED_UNTESTABLE"
        assert count == 3

    def test_fourth_untestable_stays_escalated(self):
        """Beyond threshold: stays ESCALATED_UNTESTABLE, count keeps climbing."""
        status, count = compute_untestable_escalation("UNTESTABLE", 3)
        assert status == "ESCALATED_UNTESTABLE"
        assert count == 4

    def test_clear_resets_counter(self):
        """CLEAR after 2 UNTESTABLE passes -> counter resets to 0."""
        status, count = compute_untestable_escalation("CLEAR", 2)
        assert status == "CLEAR"
        assert count == 0

    def test_triggered_resets_counter(self):
        """TRIGGERED resets counter regardless of prior UNTESTABLE count."""
        status, count = compute_untestable_escalation("TRIGGERED", 5)
        assert status == "TRIGGERED"
        assert count == 0

    def test_stale_resets_counter(self):
        """STALE is not UNTESTABLE -> counter resets."""
        status, count = compute_untestable_escalation("STALE", 2)
        assert status == "STALE"
        assert count == 0

    def test_triggered_by_passage_resets_counter(self):
        """TRIGGERED_BY_PASSAGE resets counter."""
        status, count = compute_untestable_escalation("TRIGGERED_BY_PASSAGE", 3)
        assert status == "TRIGGERED_BY_PASSAGE"
        assert count == 0

    def test_custom_threshold(self):
        """Custom escalation threshold of 5."""
        # At count 4 -> not escalated yet
        status, count = compute_untestable_escalation("UNTESTABLE", 4, escalation_threshold=5)
        assert status == "ESCALATED_UNTESTABLE"
        assert count == 5

    def test_custom_threshold_below(self):
        """Below custom threshold -> stays UNTESTABLE."""
        status, count = compute_untestable_escalation("UNTESTABLE", 3, escalation_threshold=5)
        assert status == "UNTESTABLE"
        assert count == 4

    def test_zero_consecutive_clear(self):
        """CLEAR with 0 consecutive -> stays at 0."""
        status, count = compute_untestable_escalation("CLEAR", 0)
        assert status == "CLEAR"
        assert count == 0


# ===================================================================
# apply_untestable_escalation — batch across falsifiers
# ===================================================================

class TestApplyUntestableEscalation:
    def test_mixed_statuses(self):
        """Three falsifiers with different histories."""
        falsifiers = [
            {"name": "f1", "status": "UNTESTABLE", "untestable_consecutive": 2, "severity": "minor"},
            {"name": "f2", "status": "CLEAR", "untestable_consecutive": 1, "severity": "medium"},
            {"name": "f3", "status": "UNTESTABLE", "untestable_consecutive": 0, "severity": "major"},
        ]
        result = apply_untestable_escalation(falsifiers)

        # f1: 2+1=3 >= 3 -> ESCALATED_UNTESTABLE
        assert result[0]["status"] == "ESCALATED_UNTESTABLE"
        assert result[0]["untestable_consecutive"] == 3

        # f2: CLEAR -> resets to 0
        assert result[1]["status"] == "CLEAR"
        assert result[1]["untestable_consecutive"] == 0

        # f3: 0+1=1 < 3 -> stays UNTESTABLE
        assert result[2]["status"] == "UNTESTABLE"
        assert result[2]["untestable_consecutive"] == 1

    def test_does_not_mutate_input(self):
        """Input list must not be modified."""
        falsifiers = [
            {"name": "f1", "status": "UNTESTABLE", "untestable_consecutive": 2, "severity": "minor"},
        ]
        original_copy = [dict(f) for f in falsifiers]
        apply_untestable_escalation(falsifiers)
        assert falsifiers == original_copy

    def test_defaults_missing_consecutive_to_zero(self):
        """Missing untestable_consecutive defaults to 0."""
        falsifiers = [
            {"name": "f1", "status": "UNTESTABLE", "severity": "minor"},
        ]
        result = apply_untestable_escalation(falsifiers)
        assert result[0]["status"] == "UNTESTABLE"
        assert result[0]["untestable_consecutive"] == 1

    def test_defaults_missing_status_to_untestable(self):
        """Missing status defaults to UNTESTABLE (conservative default from plan)."""
        falsifiers = [
            {"name": "f1", "untestable_consecutive": 2, "severity": "minor"},
        ]
        result = apply_untestable_escalation(falsifiers)
        assert result[0]["status"] == "ESCALATED_UNTESTABLE"
        assert result[0]["untestable_consecutive"] == 3

    def test_preserves_existing_fields(self):
        """All original fields preserved in output."""
        falsifiers = [
            {
                "name": "VIX calm",
                "metric": "vix",
                "threshold": "below 18",
                "severity": "medium",
                "status": "UNTESTABLE",
                "untestable_consecutive": 0,
                "generation_market_value": 14.0,
                "staleness_flag": None,
            },
        ]
        result = apply_untestable_escalation(falsifiers)
        assert result[0]["name"] == "VIX calm"
        assert result[0]["metric"] == "vix"
        assert result[0]["generation_market_value"] == 14.0

    def test_empty_list(self):
        """Empty input -> empty output."""
        assert apply_untestable_escalation([]) == []

    def test_custom_threshold(self):
        """Custom escalation threshold passed through."""
        falsifiers = [
            {"name": "f1", "status": "UNTESTABLE", "untestable_consecutive": 4, "severity": "minor"},
        ]
        result = apply_untestable_escalation(falsifiers, escalation_threshold=5)
        assert result[0]["status"] == "ESCALATED_UNTESTABLE"
        assert result[0]["untestable_consecutive"] == 5


# ===================================================================
# Configuration constants
# ===================================================================

class TestConfigConstants:
    def test_staleness_multiplier(self):
        assert STALENESS_MULTIPLIER == 2.0

    def test_escalation_threshold(self):
        assert ESCALATION_THRESHOLD == 3
