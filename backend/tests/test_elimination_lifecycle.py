# test_elimination_lifecycle.py — Tests for v7 falsifier lifecycle in elimination prompt.
# Verifies: lifecycle instructions injection, output schema v7 fields,
# staleness flags in hypothesis data, untestable counters displayed,
# emergent risk schema, backward compatibility (no lifecycle -> legacy).
from __future__ import annotations

import json

import pytest

from backend.engine.prompt_builder import (
    _elimination_output_schema,
    _falsifier_lifecycle_instructions,
    build_elimination_prompt_v8,
)
from backend.schemas.theory import ActivationResult, ActivationTier, TheoryPackage


# ---------------------------------------------------------------------------
# Fixtures — minimal data for prompt builder
# ---------------------------------------------------------------------------


def _make_package(theory_id: str) -> TheoryPackage:
    return TheoryPackage(
        theory_id=theory_id,
        core="# CORE content",
        activation="# ACTIVATION content",
        tactical="# TACTICAL content",
        playbook="# PLAYBOOK content",
        context_flags=[],
        falsifier_registry=[],
    )


def _make_activation(theory_id: str, tier: ActivationTier, score: float = 0.7) -> ActivationResult:
    return ActivationResult(
        theory_id=theory_id,
        is_two_phase=False,
        score=score,
        tier=tier,
    )


def _make_hypothesis(
    hyp_id: str = "H-20260403-120000-01",
    theory_id: str = "fiscal_dominance_liquidity",
    short_name: str = "Gold rises on fiscal stress",
    soft_falsifiers: list | None = None,
    hard_falsifiers: list | None = None,
) -> dict:
    return {
        "id": hyp_id,
        "theory_id": theory_id,
        "source_theories": [theory_id],
        "short_name": short_name,
        "full_statement": "Test hypothesis statement.",
        "predicted_assets": ["GLD"],
        "asset_direction": {"GLD": "LONG"},
        "hard_falsifiers": hard_falsifiers or [],
        "soft_falsifiers": soft_falsifiers or [],
        "timeframe": "Through Q3 2026",
        "resolution_channel": "real_asset_outperformance",
    }


MINIMAL_BRIEFING = {"growth": {}, "inflation": {}, "rates": {}, "markets": {}}


# ===================================================================
# _falsifier_lifecycle_instructions
# ===================================================================


class TestFalsifierLifecycleInstructions:
    def test_contains_staleness_interpretation(self):
        text = _falsifier_lifecycle_instructions()
        assert "STALENESS INTERPRETATION" in text
        assert "STALE" in text
        assert "TRIGGERED_BY_PASSAGE" in text

    def test_contains_emergent_risk_section(self):
        text = _falsifier_lifecycle_instructions()
        assert "EMERGENT RISK ASSESSMENT" in text
        assert "causal chain" in text
        assert "severity" in text

    def test_contains_untestable_counters(self):
        text = _falsifier_lifecycle_instructions()
        assert "UNTESTABLE COUNTERS" in text
        assert "untestable_consecutive" in text
        assert ">= 3" in text

    def test_stale_cannot_be_classified_clear(self):
        """The instructions forbid re-classifying STALE as CLEAR."""
        text = _falsifier_lifecycle_instructions()
        assert "may NOT classify a mechanically STALE falsifier as CLEAR" in text

    def test_emergent_risk_default_empty(self):
        """The instructions say the slot is EMPTY by default."""
        text = _falsifier_lifecycle_instructions()
        assert "EMPTY by default" in text

    def test_delimiters(self):
        text = _falsifier_lifecycle_instructions()
        assert text.startswith("--- FALSIFIER LIFECYCLE INSTRUCTIONS ---")
        assert text.endswith("--- END FALSIFIER LIFECYCLE INSTRUCTIONS ---")


# ===================================================================
# _elimination_output_schema — v7 additions
# ===================================================================


class TestEliminationOutputSchemaLifecycle:
    def test_legacy_no_lifecycle_fields(self):
        """Without lifecycle flag, schema has no v7 fields."""
        schema = _elimination_output_schema(has_falsifier_lifecycle=False)
        assert "staleness_classification" not in schema
        assert "emergent_risk" not in schema

    def test_lifecycle_adds_staleness_classification(self):
        schema = _elimination_output_schema(has_falsifier_lifecycle=True)
        assert "staleness_classification" in schema
        assert "STALE | TRIGGERED_BY_PASSAGE" in schema

    def test_lifecycle_adds_staleness_reasoning(self):
        schema = _elimination_output_schema(has_falsifier_lifecycle=True)
        assert "staleness_reasoning" in schema

    def test_lifecycle_adds_emergent_risk(self):
        schema = _elimination_output_schema(has_falsifier_lifecycle=True)
        assert "emergent_risk" in schema
        assert "causal_chain" in schema

    def test_lifecycle_adds_soft_falsifiers_structure(self):
        schema = _elimination_output_schema(has_falsifier_lifecycle=True)
        assert '"soft_falsifiers"' in schema
        assert '"name": "falsifier name"' in schema

    def test_lifecycle_with_channels_and_sectors(self):
        """All three conditional blocks can coexist."""
        schema = _elimination_output_schema(
            has_channel_tags=True,
            has_sector_appendices=True,
            has_falsifier_lifecycle=True,
        )
        assert "channel_verification" in schema
        assert "sector_falsifier_audit" in schema
        assert "staleness_classification" in schema
        assert "emergent_risk" in schema

    def test_lifecycle_null_guidance(self):
        """Schema includes guidance about setting emergent_risk to null."""
        schema = _elimination_output_schema(has_falsifier_lifecycle=True)
        assert "null" in schema.lower()


# ===================================================================
# build_elimination_prompt_v8 — lifecycle integration
# ===================================================================


class TestBuildEliminationPromptLifecycle:
    def _build(self, hypotheses=None, has_falsifier_lifecycle=False):
        packages = [_make_package("fiscal_dominance_liquidity")]
        activation_results = [
            _make_activation("fiscal_dominance_liquidity", ActivationTier.ACTIVE),
        ]
        return build_elimination_prompt_v8(
            hypotheses=hypotheses or [_make_hypothesis()],
            packages=packages,
            activation_results=activation_results,
            briefing=MINIMAL_BRIEFING,
            has_falsifier_lifecycle=has_falsifier_lifecycle,
        )

    def test_legacy_no_lifecycle_section(self):
        """Without lifecycle flag, no lifecycle instructions in prompt."""
        prompt = self._build(has_falsifier_lifecycle=False)
        assert "FALSIFIER LIFECYCLE INSTRUCTIONS" not in prompt

    def test_lifecycle_section_included(self):
        """With lifecycle flag, lifecycle instructions appear in prompt."""
        prompt = self._build(has_falsifier_lifecycle=True)
        assert "--- FALSIFIER LIFECYCLE INSTRUCTIONS ---" in prompt
        assert "--- END FALSIFIER LIFECYCLE INSTRUCTIONS ---" in prompt

    def test_lifecycle_section_before_output_format(self):
        """Lifecycle instructions appear before OUTPUT FORMAT section."""
        prompt = self._build(has_falsifier_lifecycle=True)
        lifecycle_pos = prompt.index("FALSIFIER LIFECYCLE INSTRUCTIONS")
        output_pos = prompt.index("## OUTPUT FORMAT")
        assert lifecycle_pos < output_pos

    def test_lifecycle_section_after_data_briefing(self):
        """Lifecycle instructions appear after DATA BRIEFING section."""
        prompt = self._build(has_falsifier_lifecycle=True)
        briefing_pos = prompt.index("## DATA BRIEFING")
        lifecycle_pos = prompt.index("FALSIFIER LIFECYCLE INSTRUCTIONS")
        assert briefing_pos < lifecycle_pos

    def test_hypothesis_staleness_flags_in_json(self):
        """Hypothesis soft falsifiers with staleness_flag appear in prompt JSON."""
        sf = {
            "name": "VIX spike",
            "severity": "major",
            "status": "CLEAR",
            "metric": "vix",
            "threshold": "VIX above 30",
            "staleness_flag": "STALE",
            "untestable_consecutive": 0,
            "generation_market_value": 18.5,
            "current_market_value": 22.5,
        }
        h = _make_hypothesis(soft_falsifiers=[sf])
        prompt = self._build(hypotheses=[h], has_falsifier_lifecycle=True)

        # The hypothesis JSON dump should contain the lifecycle metadata
        assert '"staleness_flag": "STALE"' in prompt
        assert '"untestable_consecutive": 0' in prompt
        assert '"generation_market_value": 18.5' in prompt

    def test_hypothesis_untestable_counter_in_json(self):
        """High untestable_consecutive counters appear in prompt JSON."""
        sf = {
            "name": "Credit spread widening",
            "severity": "medium",
            "status": "UNTESTABLE",
            "metric": "hy_spread",
            "threshold": "HY spread above 500bps",
            "untestable_consecutive": 4,
        }
        h = _make_hypothesis(soft_falsifiers=[sf])
        prompt = self._build(hypotheses=[h], has_falsifier_lifecycle=True)
        assert '"untestable_consecutive": 4' in prompt

    def test_output_schema_has_lifecycle_fields(self):
        """When lifecycle is on, the output schema includes v7 fields."""
        prompt = self._build(has_falsifier_lifecycle=True)
        assert "staleness_classification" in prompt
        assert "emergent_risk" in prompt

    def test_output_schema_no_lifecycle_fields_when_off(self):
        """When lifecycle is off, the output schema is unchanged."""
        prompt = self._build(has_falsifier_lifecycle=False)
        assert "staleness_classification" not in prompt
        assert "emergent_risk" not in prompt

    def test_all_features_coexist(self):
        """Lifecycle + channels + sectors all render without collision."""
        packages = [_make_package("fiscal_dominance_liquidity")]
        activation_results = [
            _make_activation("fiscal_dominance_liquidity", ActivationTier.ACTIVE),
        ]
        prompt = build_elimination_prompt_v8(
            hypotheses=[_make_hypothesis()],
            packages=packages,
            activation_results=activation_results,
            briefing=MINIMAL_BRIEFING,
            has_channel_tags=True,
            sector_appendices=[{
                "sector_id": "technology",
                "display_name": "Technology",
                "ticker_triggers": ["QQQ"],
                "mechanical_falsifiers": [],
                "evaluator_attack_vectors": [],
            }],
            has_falsifier_lifecycle=True,
        )
        assert "FALSIFIER LIFECYCLE INSTRUCTIONS" in prompt
        assert "CHANNEL VERIFICATION" in prompt
        assert "SECTOR FALSIFIER APPENDICES" in prompt
        assert "staleness_classification" in prompt


# ===================================================================
# _enrich_elimination_falsifiers (pipeline helper)
# ===================================================================


class TestEnrichEliminationFalsifiers:
    """Test the pipeline helper that adds staleness to elimination hypothesis dicts."""

    def test_staleness_flag_added(self):
        """Soft falsifiers get staleness_flag from staleness gate."""
        from backend.api.pipeline import _enrich_elimination_falsifiers
        from backend.schemas.briefing import BriefingPacket

        sf = {
            "name": "VIX spike",
            "severity": "major",
            "metric": "vix",
            "threshold": "VIX above 30",
            "generation_market_value": 18.0,
        }
        h = _make_hypothesis(soft_falsifiers=[sf])
        # Current VIX at 55 — well past 2x threshold distance from 18
        # Threshold is 30, gen value is 18, distance = 12, 2x = 24
        # Current = 55, distance from gen = 37, > 24 -> STALE
        briefing = BriefingPacket(
            growth={},
            inflation={},
            rates={},
            markets={},
            computed={"vix": 55.0},
        )
        _enrich_elimination_falsifiers([h], briefing)

        enriched_sf = h["soft_falsifiers"][0]
        assert enriched_sf.get("staleness_flag") == "STALE"
        assert enriched_sf.get("current_market_value") == 55.0

    def test_no_staleness_when_within_range(self):
        """Falsifiers within 2x range do not get STALE flag."""
        from backend.api.pipeline import _enrich_elimination_falsifiers
        from backend.schemas.briefing import BriefingPacket

        sf = {
            "name": "VIX spike",
            "severity": "major",
            "metric": "vix",
            "threshold": "VIX above 30",
            "generation_market_value": 25.0,
        }
        h = _make_hypothesis(soft_falsifiers=[sf])
        # Current VIX at 28 — close to threshold, not stale
        briefing = BriefingPacket(
            growth={},
            inflation={},
            rates={},
            markets={},
            computed={"vix": 28.0},
        )
        _enrich_elimination_falsifiers([h], briefing)

        enriched_sf = h["soft_falsifiers"][0]
        assert enriched_sf.get("staleness_flag") is None

    def test_untestable_counter_preserved(self):
        """Existing untestable_consecutive values survive enrichment."""
        from backend.api.pipeline import _enrich_elimination_falsifiers
        from backend.schemas.briefing import BriefingPacket

        sf = {
            "name": "Credit spread",
            "severity": "medium",
            "metric": "hy_spread",
            "threshold": "HY spread above 500",
            "untestable_consecutive": 3,
        }
        h = _make_hypothesis(soft_falsifiers=[sf])
        briefing = BriefingPacket(growth={}, inflation={}, rates={}, markets={})
        _enrich_elimination_falsifiers([h], briefing)

        enriched_sf = h["soft_falsifiers"][0]
        assert enriched_sf["untestable_consecutive"] == 3

    def test_empty_falsifiers_no_error(self):
        """Hypothesis with no soft falsifiers does not crash."""
        from backend.api.pipeline import _enrich_elimination_falsifiers
        from backend.schemas.briefing import BriefingPacket

        h = _make_hypothesis(soft_falsifiers=[])
        briefing = BriefingPacket(growth={}, inflation={}, rates={}, markets={})
        _enrich_elimination_falsifiers([h], briefing)
        assert h["soft_falsifiers"] == []

    def test_multiple_hypotheses_enriched(self):
        """All hypotheses in the list get enriched, not just the first."""
        from backend.api.pipeline import _enrich_elimination_falsifiers
        from backend.schemas.briefing import BriefingPacket

        sf1 = {"name": "A", "severity": "minor", "metric": "vix", "threshold": "VIX above 30", "generation_market_value": 10.0}
        sf2 = {"name": "B", "severity": "major", "metric": "vix", "threshold": "VIX above 30", "generation_market_value": 10.0}
        h1 = _make_hypothesis(hyp_id="H-01", soft_falsifiers=[sf1])
        h2 = _make_hypothesis(hyp_id="H-02", soft_falsifiers=[sf2])

        briefing = BriefingPacket(
            growth={}, inflation={}, rates={}, markets={},
            computed={"vix": 55.0},
        )
        _enrich_elimination_falsifiers([h1, h2], briefing)

        assert h1["soft_falsifiers"][0].get("current_market_value") == 55.0
        assert h2["soft_falsifiers"][0].get("current_market_value") == 55.0
