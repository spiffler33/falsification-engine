# test_snapshot_shape.py -- Validates that the snapshot builder produces
# data shapes matching the live API endpoints.
#
# Root cause prevention: the snapshot builder in pipeline.py and the live
# API endpoints (theories.py, hypotheses.py, etc.) must produce identical
# shapes. When they diverge, the GitHub Pages static site silently breaks.
# This test catches drift before it reaches production.
import pytest

from backend.api.theories import build_theory_summaries

# Keys the frontend reads from each API response.
# If a key is in this set, the snapshot MUST include it.

THEORY_REQUIRED_KEYS = {
    "theory_id", "name", "is_two_phase", "regime_flags",
    "tier", "activation_score", "active_phase",
}


class TestSnapshotTheoryShape:
    def test_build_theory_summaries_has_required_keys(self):
        """build_theory_summaries() must include all keys the frontend reads."""
        # Pass empty briefing — we're testing shape, not values
        summaries = build_theory_summaries(briefing_data={})
        assert len(summaries) > 0, "No theories found — check theories/ directory"

        for t in summaries:
            missing = THEORY_REQUIRED_KEYS - set(t.keys())
            assert missing == set(), (
                f"Theory '{t.get('theory_id')}' missing keys: {missing}. "
                f"The snapshot builder must match the /api/theories shape."
            )

    def test_tier_is_lowercase_string(self):
        summaries = build_theory_summaries(briefing_data={})
        for t in summaries:
            tier = t.get("tier")
            assert isinstance(tier, str), f"tier must be str, got {type(tier)}"
            assert tier == tier.lower(), f"tier must be lowercase, got '{tier}'"
            assert tier in ("active", "adjacent", "inactive"), f"Unknown tier: '{tier}'"

    def test_activation_score_is_numeric(self):
        summaries = build_theory_summaries(briefing_data={})
        for t in summaries:
            score = t.get("activation_score")
            assert isinstance(score, (int, float)), (
                f"activation_score must be numeric, got {type(score)}"
            )
            assert 0 <= score <= 1.0, f"activation_score {score} outside [0, 1]"

    def test_snapshot_and_endpoint_produce_same_keys(self):
        """The snapshot builder (build_theory_summaries) IS the endpoint now.
        This test ensures no one accidentally re-introduces a separate path."""
        from backend.api.theories import list_theories

        endpoint_result = list_theories()
        snapshot_result = build_theory_summaries()

        assert len(endpoint_result) == len(snapshot_result)

        endpoint_keys = set(endpoint_result[0].keys()) if endpoint_result else set()
        snapshot_keys = set(snapshot_result[0].keys()) if snapshot_result else set()

        assert endpoint_keys == snapshot_keys, (
            f"Key mismatch!\n"
            f"  Endpoint only: {endpoint_keys - snapshot_keys}\n"
            f"  Snapshot only: {snapshot_keys - endpoint_keys}"
        )
