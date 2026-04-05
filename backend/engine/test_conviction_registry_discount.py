"""Tests for v8 conviction scoring source change (Unit 11).

The conviction engine now prefers the `discount` field from FalsifierEntry
registry objects over the SEVERITY_WEIGHTS lookup from the severity string.
Pipeline helpers resolve discounts from the registry before passing them
to the conviction engine.

Part A — Conviction engine: discount field preference
  1. discount field present → used directly
  2. discount field absent → fallback to SEVERITY_WEIGHTS[severity]
  3. discount=0.0 → respected as zero (not treated as falsy None)
  4. Both discount and severity present → discount wins
  5. D_f compounding with registry discounts matches severity-derived D_f
  6. Mixed: some entries have discount, some don't → each resolved independently

Part B — Pipeline helpers: registry lookup and matching
  7. _build_registry_discount_lookup returns soft entries only
  8. _resolve_registry_entry exact condition match
  9. _resolve_registry_entry exact name match
  10. _resolve_registry_entry substring match
  11. _resolve_registry_entry no match returns None
  12. _resolve_registry_entry skips short strings in substring phase

Part C — Untestable path: registry severity used for UNTESTABLE_WEIGHTS
  13. Untestable with registry severity → UNTESTABLE_WEIGHTS applied
  14. Untestable without match → hypothesis severity used (existing behavior)

Part D — Emergent risk: no registry lookup (hypothesis-only)
  15. Emergent risk entry has no discount field → severity fallback works
"""

import pytest

from backend.engine.conviction import (
    SEVERITY_WEIGHTS,
    UNTESTABLE_WEIGHTS,
    score_conviction,
)
from backend.schemas.scoring import ConvictionInput
from backend.schemas.theory import FalsifierEntry, Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_input(**overrides) -> ConvictionInput:
    """Strong baseline: RAW ~0.80 on 0-1 scale = 8.0 on 0-10.

    Horizon and expression gates set high to avoid interference.
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


def _make_entry(
    fid: str = "S1",
    condition: str = "test condition",
    severity: str = "minor",
    classification: str = "soft",
) -> FalsifierEntry:
    discount_map = {"minor": 0.10, "medium": 0.25, "major": 0.45}
    return FalsifierEntry(
        falsifier_id=fid,
        condition=condition,
        logic="test logic",
        classification=classification,
        severity=Severity(severity) if classification == "soft" else None,
        discount=discount_map.get(severity) if classification == "soft" else None,
    )


# ---------------------------------------------------------------------------
# Part A — Conviction engine: discount field preference
# ---------------------------------------------------------------------------

class TestDiscountFieldPreference:
    """Verify conviction engine prefers `discount` over SEVERITY_WEIGHTS lookup."""

    def test_discount_field_used_directly(self):
        """When discount is present, it is used as the weight — not SEVERITY_WEIGHTS."""
        ci = _base_input(triggered_soft_falsifiers=[{"discount": 0.25}])
        result = score_conviction(ci)
        # D_f = 1 - 0.25 = 0.75
        assert result.stage2.soft_falsifier_discount == pytest.approx(0.75)

    def test_fallback_to_severity_when_no_discount(self):
        """Without discount field, SEVERITY_WEIGHTS[severity] is used (backwards compat)."""
        ci = _base_input(triggered_soft_falsifiers=[{"severity": "medium"}])
        result = score_conviction(ci)
        # D_f = 1 - 0.25 = 0.75 (SEVERITY_WEIGHTS["medium"] = 0.25)
        assert result.stage2.soft_falsifier_discount == pytest.approx(0.75)

    def test_discount_zero_respected(self):
        """discount=0.0 means zero weight, not fallback to SEVERITY_WEIGHTS."""
        ci = _base_input(
            triggered_soft_falsifiers=[{"severity": "major", "discount": 0.0}],
        )
        result = score_conviction(ci)
        # discount=0.0 → weight=0.0 → D_f = 1.0 * (1 - 0.0) = 1.0
        # If fallback fired, D_f would be 1 - 0.45 = 0.55
        assert result.stage2.soft_falsifier_discount == pytest.approx(1.0)

    def test_discount_wins_over_severity(self):
        """When both discount and severity are present, discount takes precedence."""
        # Provide severity="minor" (0.10) but discount=0.45 (major-equivalent)
        ci = _base_input(
            triggered_soft_falsifiers=[{"severity": "minor", "discount": 0.45}],
        )
        result = score_conviction(ci)
        # D_f = 1 - 0.45 = 0.55 (from discount, not severity)
        assert result.stage2.soft_falsifier_discount == pytest.approx(0.55)

    def test_registry_discount_matches_severity_derived(self):
        """When discount matches SEVERITY_WEIGHTS[severity], results are identical."""
        # Registry path: discount=0.10
        ci_registry = _base_input(
            triggered_soft_falsifiers=[{"severity": "minor", "discount": 0.10}],
        )
        # Old path: severity only
        ci_old = _base_input(
            triggered_soft_falsifiers=[{"severity": "minor"}],
        )
        r1 = score_conviction(ci_registry)
        r2 = score_conviction(ci_old)
        assert r1.stage2.soft_falsifier_discount == r2.stage2.soft_falsifier_discount
        assert r1.stage3.final == r2.stage3.final

    def test_compounding_with_registry_discounts(self):
        """Multiple triggered falsifiers with discount fields compound multiplicatively."""
        ci = _base_input(
            triggered_soft_falsifiers=[
                {"discount": 0.10},  # minor
                {"discount": 0.25},  # medium
            ],
        )
        result = score_conviction(ci)
        expected_df = (1 - 0.10) * (1 - 0.25)  # 0.90 * 0.75 = 0.675
        assert result.stage2.soft_falsifier_discount == pytest.approx(expected_df)

    def test_mixed_discount_and_severity(self):
        """Some entries have discount (registry), some have only severity (unmatched)."""
        ci = _base_input(
            triggered_soft_falsifiers=[
                {"discount": 0.25},                 # from registry
                {"severity": "major"},               # no registry match, fallback
            ],
        )
        result = score_conviction(ci)
        expected_df = (1 - 0.25) * (1 - 0.45)  # 0.75 * 0.55 = 0.4125
        assert result.stage2.soft_falsifier_discount == pytest.approx(expected_df)

    def test_discount_none_triggers_fallback(self):
        """Explicit discount=None falls back to SEVERITY_WEIGHTS."""
        ci = _base_input(
            triggered_soft_falsifiers=[{"severity": "medium", "discount": None}],
        )
        result = score_conviction(ci)
        assert result.stage2.soft_falsifier_discount == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Part B — Pipeline helpers: registry lookup and matching
# ---------------------------------------------------------------------------

class TestRegistryLookupHelpers:
    """Test _build_registry_discount_lookup and _resolve_registry_entry."""

    def test_build_lookup_returns_soft_only(self):
        """_build_registry_discount_lookup filters to soft entries (those with discount)."""
        from backend.api.pipeline import _build_registry_discount_lookup
        lookup = _build_registry_discount_lookup()

        for theory_id, entries in lookup.items():
            for entry in entries:
                assert entry.classification == "soft", (
                    f"{theory_id}: hard entry {entry.falsifier_id} in soft-only lookup"
                )
                assert entry.discount is not None, (
                    f"{theory_id}: {entry.falsifier_id} has no discount"
                )

    def test_build_lookup_covers_all_theories(self):
        """Every theory directory produces at least one soft falsifier entry."""
        from backend.api.pipeline import _build_registry_discount_lookup
        lookup = _build_registry_discount_lookup()
        assert len(lookup) >= 8, f"Expected >= 8 theories, got {len(lookup)}"
        for theory_id, entries in lookup.items():
            assert len(entries) > 0, f"{theory_id} has no soft falsifier entries"

    def test_resolve_exact_condition_match(self):
        """Exact condition text match returns the entry."""
        from backend.api.pipeline import _resolve_registry_entry
        entries = [_make_entry(condition="Credit spreads widen beyond 600bp")]
        sf = {"condition": "Credit spreads widen beyond 600bp"}
        matched = _resolve_registry_entry(sf, entries)
        assert matched is not None
        assert matched.discount == 0.10

    def test_resolve_exact_name_match(self):
        """Exact name match against entry condition returns the entry."""
        from backend.api.pipeline import _resolve_registry_entry
        entries = [_make_entry(condition="Fed pivot to easing")]
        sf = {"name": "Fed pivot to easing"}
        matched = _resolve_registry_entry(sf, entries)
        assert matched is not None

    def test_resolve_substring_match(self):
        """Substring containment match works for long-enough strings."""
        from backend.api.pipeline import _resolve_registry_entry
        entries = [_make_entry(
            condition="S&P 500 earnings yield rises above 6% through earnings growth rather than price decline",
            severity="major",
        )]
        sf = {"condition": "earnings yield rises above 6% through earnings growth"}
        matched = _resolve_registry_entry(sf, entries)
        assert matched is not None
        assert matched.discount == 0.45

    def test_resolve_no_match_returns_none(self):
        """Completely unrelated text returns None."""
        from backend.api.pipeline import _resolve_registry_entry
        entries = [_make_entry(condition="Credit spreads widen beyond 600bp")]
        sf = {"name": "Bitcoin halving cycle", "condition": "BTC drops below 20k"}
        matched = _resolve_registry_entry(sf, entries)
        assert matched is None

    def test_resolve_skips_short_strings_in_substring(self):
        """Short condition/name strings don't trigger false substring matches."""
        from backend.api.pipeline import _resolve_registry_entry
        entries = [_make_entry(condition="A very long condition about credit spreads")]
        sf = {"name": "credit", "condition": "credit"}  # too short for substring
        matched = _resolve_registry_entry(sf, entries)
        assert matched is None

    def test_resolve_case_insensitive(self):
        """Matching is case-insensitive."""
        from backend.api.pipeline import _resolve_registry_entry
        entries = [_make_entry(condition="Fed Pivot To Easing")]
        sf = {"condition": "fed pivot to easing"}
        matched = _resolve_registry_entry(sf, entries)
        assert matched is not None

    def test_resolve_prefers_exact_over_substring(self):
        """Exact match is tried first, even if substring would also match."""
        from backend.api.pipeline import _resolve_registry_entry
        exact = _make_entry(fid="S1", condition="credit spreads widen", severity="minor")
        substr = _make_entry(fid="S2", condition="credit spreads widen beyond 600bp", severity="major")
        sf = {"condition": "credit spreads widen"}
        matched = _resolve_registry_entry(sf, [exact, substr])
        assert matched is not None
        assert matched.falsifier_id == "S1"


# ---------------------------------------------------------------------------
# Part C — Untestable path: registry severity for UNTESTABLE_WEIGHTS
# ---------------------------------------------------------------------------

class TestUntestableRegistrySeverity:
    """Untestable falsifiers use registry severity for UNTESTABLE_WEIGHTS lookup."""

    def test_untestable_uses_severity_not_discount(self):
        """UNTESTABLE_WEIGHTS != SEVERITY_WEIGHTS. Discount field is not used for untestable."""
        # UNTESTABLE_WEIGHTS: minor=0.05, medium=0.10, major=0.15
        # SEVERITY_WEIGHTS:   minor=0.10, medium=0.25, major=0.45
        ci = _base_input(
            untestable_soft_falsifiers=[{"severity": "medium", "status": "UNTESTABLE"}],
        )
        result = score_conviction(ci)
        expected_du = 1 - 0.10  # UNTESTABLE_WEIGHTS["medium"] = 0.10
        assert result.stage2.untestable_discount == pytest.approx(expected_du)

    def test_untestable_fallback_severity(self):
        """Without registry match, hypothesis severity still works for untestable."""
        ci = _base_input(
            untestable_soft_falsifiers=[{"severity": "major", "status": "UNTESTABLE"}],
        )
        result = score_conviction(ci)
        expected_du = 1 - 0.15  # UNTESTABLE_WEIGHTS["major"] = 0.15
        assert result.stage2.untestable_discount == pytest.approx(expected_du)


# ---------------------------------------------------------------------------
# Part D — Emergent risk: no registry lookup
# ---------------------------------------------------------------------------

class TestEmergentRiskNoRegistry:
    """Emergent risk entries don't come from the registry — severity fallback works."""

    def test_emergent_risk_severity_only(self):
        """Emergent risk has no discount field — SEVERITY_WEIGHTS[severity] used."""
        ci = _base_input(
            triggered_soft_falsifiers=[{"severity": "medium"}],  # emergent risk entry
        )
        result = score_conviction(ci)
        assert result.stage2.soft_falsifier_discount == pytest.approx(0.75)

    def test_emergent_risk_with_registry_entry(self):
        """Mixed: one registry-resolved + one emergent risk → both compound."""
        ci = _base_input(
            triggered_soft_falsifiers=[
                {"severity": "minor", "discount": 0.10},  # from registry
                {"severity": "major"},                      # emergent risk (no discount)
            ],
        )
        result = score_conviction(ci)
        expected_df = (1 - 0.10) * (1 - 0.45)  # 0.90 * 0.55 = 0.495
        assert result.stage2.soft_falsifier_discount == pytest.approx(expected_df)


# ---------------------------------------------------------------------------
# Part E — Arithmetic invariant: registry path = severity path when aligned
# ---------------------------------------------------------------------------

class TestArithmeticInvariant:
    """The core contract: when registry and hypothesis agree on severity,
    the final conviction score is identical regardless of which path is used."""

    @pytest.mark.parametrize("severity,discount", [
        ("minor", 0.10),
        ("medium", 0.25),
        ("major", 0.45),
    ])
    def test_each_severity_level(self, severity, discount):
        """For each severity level, registry discount == SEVERITY_WEIGHTS."""
        ci_registry = _base_input(
            triggered_soft_falsifiers=[{"severity": severity, "discount": discount}],
        )
        ci_old = _base_input(
            triggered_soft_falsifiers=[{"severity": severity}],
        )
        r1 = score_conviction(ci_registry)
        r2 = score_conviction(ci_old)
        assert r1.stage3.final == r2.stage3.final

    def test_multi_falsifier_arithmetic_invariant(self):
        """Multiple falsifiers: registry vs severity paths produce identical scores."""
        triggered = [
            {"severity": "minor", "discount": 0.10},
            {"severity": "medium", "discount": 0.25},
            {"severity": "major", "discount": 0.45},
        ]
        ci_registry = _base_input(triggered_soft_falsifiers=triggered)

        triggered_old = [
            {"severity": "minor"},
            {"severity": "medium"},
            {"severity": "major"},
        ]
        ci_old = _base_input(triggered_soft_falsifiers=triggered_old)

        r1 = score_conviction(ci_registry)
        r2 = score_conviction(ci_old)
        assert r1.stage2.soft_falsifier_discount == pytest.approx(r2.stage2.soft_falsifier_discount)
        assert r1.stage3.final == r2.stage3.final
