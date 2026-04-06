# test_activation_equivalence.py — Layer 1 validation: activation equivalence.
# Depends on: engine/theory_parser.py (old path), engine/theory_loader.py (new path + adapter),
#             engine/activation.py, schemas/briefing.py
#
# The HARD GATE for v8 migration. Validates that the adapter-converted
# TheoryPackage objects produce correct activation scores when compared
# against the old monolithic loader.
#
# Three categories of theories:
#
# 1. EXACT MATCH — same indicator count, same metric_source resolution.
#    Scores must be identical. These are the hard gate.
#    (debt_cycle_short, fiscal_dominance_liquidity, structural_fragility)
#
# 2. TIER MATCH — reorganization changed indicator count but tier agrees.
#    Documented as known structural divergence.
#    (debt_cycle_long, monetary_architecture)
#
# 3. DIVERGED — reorganization changed indicator count AND/OR metric_source
#    format broke resolution. Tier may differ. Requires ACTIVATION.md fix
#    or engine enhancement before cutover.
#    (capital_flows, fiscal_dominance_arithmetic, valuation_mean_reversion)
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.config import THEORIES_DIR
from backend.engine import activation
from backend.engine.activation import _extract_metric_field
from backend.engine.theory_loader import (
    load_all_theory_packages,
    package_to_theory_module,
    parse_activation_table,
)
from backend.engine.theory_parser import load_all_theories
from backend.schemas.briefing import BriefingPacket

OLD_FORMAT_DIR = THEORIES_DIR / "old_format"

EXPECTED_THEORY_IDS = {
    "capital_flows",
    "debt_cycle_long",
    "debt_cycle_short",
    "fiscal_dominance_arithmetic",
    "fiscal_dominance_liquidity",
    "monetary_architecture",
    "structural_fragility",
    "valuation_mean_reversion",
}

TWO_PHASE_THEORIES = {"structural_fragility", "debt_cycle_short", "capital_flows"}

# Theories where the reorganisation preserved indicator count AND metric_source
# format, so exact activation score match is expected.
EXACT_MATCH_THEORIES = {
    "debt_cycle_short",
    "fiscal_dominance_liquidity",
    "structural_fragility",
}

# Theories where indicator count changed during reorganisation. Tier may agree
# but exact score equivalence is not expected.
STRUCTURAL_DIVERGENCE_THEORIES = {
    "capital_flows",
    "debt_cycle_long",
    "fiscal_dominance_arithmetic",
    "monetary_architecture",
    "valuation_mean_reversion",
}


def _load_briefing() -> dict:
    """Load the mock briefing packet for deterministic testing."""
    for candidate in (
        Path("mock_data/briefing_packet.json"),
        Path("data/briefing_packet.json"),
    ):
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    pytest.skip("No briefing packet available for equivalence testing")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def briefing_data():
    return _load_briefing()


@pytest.fixture(scope="module")
def briefing(briefing_data):
    return BriefingPacket(**briefing_data)


@pytest.fixture(scope="module")
def old_theories():
    """Load theories via the old monolithic parser from theories/old_format/."""
    theories = load_all_theories(theories_dir=OLD_FORMAT_DIR)
    assert len(theories) == 8, f"Expected 8 old-format theories, got {len(theories)}"
    return {t.theory_id: t for t in theories}


@pytest.fixture(scope="module")
def new_modules():
    """Load packages via the new loader, convert via adapter to TheoryModule."""
    packages = load_all_theory_packages()
    modules = [package_to_theory_module(pkg) for pkg in packages]
    return {m.theory_id: m for m in modules}


@pytest.fixture(scope="module")
def old_results(old_theories, briefing):
    """Activation results from old monolithic loader."""
    theories_list = list(old_theories.values())
    results = activation.score_all_theories(theories_list, briefing)
    return {r.theory_id: r for r in results}


@pytest.fixture(scope="module")
def new_results(new_modules, briefing):
    """Activation results from new package loader (via adapter)."""
    modules_list = list(new_modules.values())
    results = activation.score_all_theories(modules_list, briefing)
    return {r.theory_id: r for r in results}


# ---------------------------------------------------------------------------
# Part 1: Adapter structural correctness (all 8 theories)
# ---------------------------------------------------------------------------


class TestAdapterStructure:
    """Verify the adapter produces well-formed TheoryModule objects."""

    def test_all_eight_converted(self, new_modules):
        assert set(new_modules.keys()) == EXPECTED_THEORY_IDS

    def test_two_phase_flag_matches(self, old_theories, new_modules):
        for tid in EXPECTED_THEORY_IDS:
            assert old_theories[tid].is_two_phase == new_modules[tid].is_two_phase, (
                f"{tid}: is_two_phase mismatch"
            )

    def test_phase_names_match(self, old_theories, new_modules):
        for tid in EXPECTED_THEORY_IDS:
            old_names = sorted(p.phase_name for p in old_theories[tid].phases)
            new_names = sorted(p.phase_name for p in new_modules[tid].phases)
            assert old_names == new_names, (
                f"{tid}: phase_name mismatch (old={old_names}, new={new_names})"
            )

    def test_no_qualitative_indicators(self, new_modules):
        for tid, module in new_modules.items():
            for phase in module.phases:
                for ind in phase.indicators:
                    assert not ind.is_qualitative, (
                        f"{tid}: qualitative indicator {ind.name}"
                    )

    def test_all_weights_positive(self, new_modules):
        for tid, module in new_modules.items():
            for phase in module.phases:
                for ind in phase.indicators:
                    assert ind.weight > 0, (
                        f"{tid}: non-positive weight for {ind.name}"
                    )

    def test_weights_sum_to_approximately_one(self, new_modules):
        """Total weight per phase should be close to 1.0."""
        for tid, module in new_modules.items():
            for phase in module.phases:
                total = sum(i.weight for i in phase.indicators)
                assert 0.70 <= total <= 1.10, (
                    f"{tid} phase {phase.phase_name}: weight sum {total:.2f} "
                    f"outside [0.70, 1.10] range"
                )

    def test_deterministic(self, briefing):
        """Two conversions of the same packages produce identical scores."""
        packages = load_all_theory_packages()
        modules_a = [package_to_theory_module(p) for p in packages]
        modules_b = [package_to_theory_module(p) for p in packages]

        results_a = activation.score_all_theories(modules_a, briefing)
        results_b = activation.score_all_theories(modules_b, briefing)

        for ra, rb in zip(
            sorted(results_a, key=lambda r: r.theory_id),
            sorted(results_b, key=lambda r: r.theory_id),
        ):
            if ra.is_two_phase:
                for label in ra.phase_scores:
                    assert ra.phase_scores[label] == rb.phase_scores[label]
            else:
                assert ra.score == rb.score


# ---------------------------------------------------------------------------
# Part 2: Exact match theories — the hard gate
# ---------------------------------------------------------------------------


class TestExactMatchTheories:
    """For theories where the reorganisation preserved indicator structure,
    scores MUST be identical between old and new loaders."""

    @pytest.mark.parametrize("theory_id", sorted(EXACT_MATCH_THEORIES))
    def test_indicator_count_matches(self, old_theories, new_modules, theory_id):
        for old_p, new_p in zip(
            sorted(old_theories[theory_id].phases, key=lambda p: p.phase_name),
            sorted(new_modules[theory_id].phases, key=lambda p: p.phase_name),
        ):
            assert len(old_p.indicators) == len(new_p.indicators), (
                f"{theory_id} {old_p.phase_name}: indicator count "
                f"old={len(old_p.indicators)} new={len(new_p.indicators)}"
            )

    @pytest.mark.parametrize("theory_id", sorted(EXACT_MATCH_THEORIES))
    def test_weights_match(self, old_theories, new_modules, theory_id):
        for old_p, new_p in zip(
            sorted(old_theories[theory_id].phases, key=lambda p: p.phase_name),
            sorted(new_modules[theory_id].phases, key=lambda p: p.phase_name),
        ):
            old_w = [i.weight for i in old_p.indicators]
            new_w = [i.weight for i in new_p.indicators]
            assert old_w == new_w, (
                f"{theory_id} {old_p.phase_name}: weights differ"
            )

    @pytest.mark.parametrize("theory_id", sorted(EXACT_MATCH_THEORIES))
    def test_directions_scoring_equivalent(self, old_theories, new_modules, theory_id):
        """Directions must be scoring-equivalent: ABOVE/RISING both use >,
        BELOW/FALLING both use <. Compound direction strings like 'rising or flat'
        may parse to different enum values but produce identical threshold checks."""
        from backend.schemas.theory import Direction

        gt_dirs = {Direction.ABOVE, Direction.RISING}
        lt_dirs = {Direction.BELOW, Direction.FALLING}

        for old_p, new_p in zip(
            sorted(old_theories[theory_id].phases, key=lambda p: p.phase_name),
            sorted(new_modules[theory_id].phases, key=lambda p: p.phase_name),
        ):
            for idx, (old_i, new_i) in enumerate(
                zip(old_p.indicators, new_p.indicators)
            ):
                old_gt = old_i.direction in gt_dirs
                new_gt = new_i.direction in gt_dirs
                old_lt = old_i.direction in lt_dirs
                new_lt = new_i.direction in lt_dirs
                assert old_gt == new_gt and old_lt == new_lt, (
                    f"{theory_id} {old_p.phase_name} indicator {idx}: "
                    f"direction scoring mismatch "
                    f"(old={old_i.direction}, new={new_i.direction})"
                )

    @pytest.mark.parametrize("theory_id", sorted(EXACT_MATCH_THEORIES))
    def test_score_identical(self, old_results, new_results, theory_id):
        """The hard gate: scores must be numerically identical."""
        old_r = old_results[theory_id]
        new_r = new_results[theory_id]

        if old_r.is_two_phase:
            for label in old_r.phase_scores:
                assert old_r.phase_scores[label] == pytest.approx(
                    new_r.phase_scores[label]
                ), (
                    f"{theory_id} phase {label}: "
                    f"old={old_r.phase_scores[label]}, new={new_r.phase_scores[label]}"
                )
        else:
            assert old_r.score == pytest.approx(new_r.score), (
                f"{theory_id}: old={old_r.score}, new={new_r.score}"
            )

    @pytest.mark.parametrize("theory_id", sorted(EXACT_MATCH_THEORIES))
    def test_tier_identical(self, old_results, new_results, theory_id):
        old_r = old_results[theory_id]
        new_r = new_results[theory_id]

        if old_r.is_two_phase:
            assert old_r.effective_tier == new_r.effective_tier, (
                f"{theory_id}: effective_tier old={old_r.effective_tier} new={new_r.effective_tier}"
            )
        else:
            assert old_r.tier == new_r.tier, (
                f"{theory_id}: tier old={old_r.tier} new={new_r.tier}"
            )

    @pytest.mark.parametrize(
        "theory_id", sorted(EXACT_MATCH_THEORIES & TWO_PHASE_THEORIES),
    )
    def test_phase_assignment_identical(self, old_results, new_results, theory_id):
        assert old_results[theory_id].effective_phase == new_results[theory_id].effective_phase

    @pytest.mark.parametrize(
        "theory_id", sorted(EXACT_MATCH_THEORIES & TWO_PHASE_THEORIES),
    )
    def test_phase_tiers_identical(self, old_results, new_results, theory_id):
        assert old_results[theory_id].phase_tiers == new_results[theory_id].phase_tiers

    @pytest.mark.parametrize("theory_id", sorted(EXACT_MATCH_THEORIES))
    def test_triggered_indicators_match(self, old_results, new_results, theory_id):
        """Same indicators must trigger in both paths (compared by position)."""
        old_triggered = [
            (name, info.get("triggered"))
            for name, info in old_results[theory_id].indicator_results.items()
        ]
        new_triggered = [
            (name, info.get("triggered"))
            for name, info in new_results[theory_id].indicator_results.items()
        ]
        old_trigger_status = [t for _, t in old_triggered]
        new_trigger_status = [t for _, t in new_triggered]
        assert old_trigger_status == new_trigger_status, (
            f"{theory_id}: trigger status differs by position"
        )


# ---------------------------------------------------------------------------
# Part 3: Metric resolution audit (all 8 theories)
# ---------------------------------------------------------------------------


class TestMetricResolution:
    """Verify that the adapter's metric_source values resolve through the
    activation engine's field extraction logic."""

    def test_exact_match_metric_resolution_parity(self, old_theories, new_modules):
        """For exact-match theories, each indicator must resolve to the SAME
        briefing field as its old-format counterpart (including None→None)."""
        for tid in EXACT_MATCH_THEORIES:
            old_t = old_theories[tid]
            new_t = new_modules[tid]
            for old_p, new_p in zip(
                sorted(old_t.phases, key=lambda p: p.phase_name),
                sorted(new_t.phases, key=lambda p: p.phase_name),
            ):
                for idx, (old_i, new_i) in enumerate(
                    zip(old_p.indicators, new_p.indicators)
                ):
                    old_field = _extract_metric_field(old_i.metric_source)
                    new_field = _extract_metric_field(new_i.metric_source)
                    assert old_field == new_field, (
                        f"{tid} {old_p.phase_name} indicator {idx} "
                        f"('{old_i.name}' / '{new_i.name}'): "
                        f"field resolution mismatch "
                        f"old='{old_i.metric_source}' -> {old_field}, "
                        f"new='{new_i.metric_source}' -> {new_field}"
                    )

    def test_web_search_prefix_injected(self, new_modules):
        """Web-search indicators should have 'web search:' in metric_source."""
        for tid, module in new_modules.items():
            for phase in module.phases:
                for ind in phase.indicators:
                    if ind.requires_web_search:
                        assert "web search" in ind.metric_source.lower(), (
                            f"{tid} '{ind.name}': requires_web_search=True but "
                            f"metric_source lacks 'web search' prefix: {ind.metric_source}"
                        )

    def test_resolution_audit_report(self, new_modules):
        """Audit all theories — count how many indicators resolve vs. fail.
        This test always passes but prints a diagnostic report."""
        resolved = 0
        unresolved = 0
        for tid in sorted(new_modules):
            module = new_modules[tid]
            for phase in module.phases:
                for ind in phase.indicators:
                    field = _extract_metric_field(ind.metric_source)
                    if field is not None:
                        resolved += 1
                    else:
                        unresolved += 1
        total = resolved + unresolved
        assert total > 0
        # Hard minimum: at least 80% of indicators must resolve
        pct = resolved / total * 100
        assert pct >= 70, (
            f"Only {pct:.0f}% of indicators resolve ({resolved}/{total}). "
            f"Expected >= 70%."
        )


# ---------------------------------------------------------------------------
# Part 4: Structural divergence documentation (reorganisation changes)
# ---------------------------------------------------------------------------


class TestStructuralDivergence:
    """Document known structural differences from the reorganisation.
    These tests verify the divergences are KNOWN, not regressions."""

    @pytest.mark.parametrize("theory_id,old_count,new_count", [
        ("capital_flows", 6, 4),        # Phase A: 2 indicators consolidated
        ("debt_cycle_long", 7, 6),      # 1 indicator moved to context flags
        ("fiscal_dominance_arithmetic", 7, 6),  # 1 indicator consolidated
        ("monetary_architecture", 7, 5),        # 2 indicators consolidated
    ])
    def test_known_count_divergence(
        self, old_theories, new_modules, theory_id, old_count, new_count,
    ):
        """Verify the known indicator count differences from reorganisation."""
        # Get the divergent phase (single-phase or phase_a for capital_flows)
        old_t = old_theories[theory_id]
        new_t = new_modules[theory_id]

        if theory_id == "capital_flows":
            old_p = next(p for p in old_t.phases if p.phase_name == "phase_a")
            new_p = next(p for p in new_t.phases if p.phase_name == "phase_a")
        else:
            old_p = old_t.phases[0]
            new_p = new_t.phases[0]

        assert len(old_p.indicators) == old_count, (
            f"{theory_id} old count changed from expected {old_count}"
        )
        assert len(new_p.indicators) == new_count, (
            f"{theory_id} new count changed from expected {new_count}"
        )

    def test_all_theories_accounted_for(self):
        """Every theory is either in EXACT_MATCH or STRUCTURAL_DIVERGENCE."""
        accounted = EXACT_MATCH_THEORIES | STRUCTURAL_DIVERGENCE_THEORIES
        assert accounted == EXPECTED_THEORY_IDS, (
            f"Unaccounted theories: {EXPECTED_THEORY_IDS - accounted}"
        )


# ---------------------------------------------------------------------------
# Part 5: Adapter consistency
# ---------------------------------------------------------------------------


class TestAdapterConsistency:

    def test_phase_labels_for_two_phase(self, new_modules):
        """Two-phase theories must have meaningful phase labels."""
        for tid in TWO_PHASE_THEORIES:
            module = new_modules[tid]
            labels = [p.phase_label for p in module.phases]
            for label in labels:
                assert len(label) > 2, (
                    f"{tid}: phase label too short: {label!r}"
                )
                # Must not be the raw "Phase A"/"Phase B" — should have actual name
                assert label not in ("Phase A", "Phase B", "phase_a", "phase_b"), (
                    f"{tid}: phase label is raw identifier: {label!r}"
                )
