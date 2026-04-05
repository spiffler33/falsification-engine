# test_prompt_builder_v8.py — Tests for v8 prompt composition (Unit 9+).
# Verifies that build_generation_prompt_v8 composes from TheoryPackage files
# and includes interaction matrix / context flags sections correctly.
from __future__ import annotations

import json

import pytest

from backend.engine.prompt_builder import (
    THEORY_LABEL_MAP,
    _format_context_flags,
    _format_interaction_matrix_for_generation,
    build_generation_prompt_v8,
)
from backend.schemas.theory import (
    ActivationResult,
    ActivationTier,
    ContextFlag,
    TheoryPackage,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_package(
    theory_id: str,
    core: str = "# CORE content",
    tactical: str = "# TACTICAL content",
    playbook: str = "# PLAYBOOK content",
    context_flags: list | None = None,
) -> TheoryPackage:
    return TheoryPackage(
        theory_id=theory_id,
        core=core,
        activation="# ACTIVATION content",
        tactical=tactical,
        playbook=playbook,
        context_flags=context_flags or [],
    )


def _make_activation(
    theory_id: str,
    tier: ActivationTier,
    score: float = 0.70,
    is_two_phase: bool = False,
    effective_phase: str | None = None,
    phase_scores: dict | None = None,
) -> ActivationResult:
    return ActivationResult(
        theory_id=theory_id,
        is_two_phase=is_two_phase,
        score=None if is_two_phase else score,
        tier=None if is_two_phase else tier,
        effective_tier=tier if is_two_phase else None,
        effective_phase=effective_phase,
        phase_scores=phase_scores,
    )


def _basic_briefing() -> dict:
    return {"growth": {"gdp_yoy": 2.1}, "rates": {"fed_funds": 5.25}}


# ---------------------------------------------------------------------------
# _format_context_flags
# ---------------------------------------------------------------------------


class TestFormatContextFlags:

    def test_formats_pydantic_objects(self):
        flags = [
            ContextFlag(
                flag_name="Political risk",
                source="web-search",
                data_ownership="qualitative",
                description="Monitor election rhetoric",
                usage="Generator context",
            ),
        ]
        result = _format_context_flags(flags)
        assert "Political risk" in result
        assert "Monitor election rhetoric" in result
        assert "qualitative -- not scored" in result

    def test_formats_dict_objects(self):
        flags = [
            {"flag_name": "Liquidity stress", "description": "Watch for repo spikes"},
        ]
        result = _format_context_flags(flags)
        assert "Liquidity stress" in result
        assert "Watch for repo spikes" in result

    def test_empty_flags_returns_header_only(self):
        result = _format_context_flags([])
        assert "Context Flags" in result


# ---------------------------------------------------------------------------
# _format_interaction_matrix_for_generation
# ---------------------------------------------------------------------------


class TestFormatInteractionMatrixForGeneration:

    def test_formats_pairwise_entries(self):
        matrix = {
            "pairwise": [
                {
                    "theory_a": "structural_fragility",
                    "theory_b": "fiscal_dominance_liquidity",
                    "relationship": "A triggers B",
                    "invariant_logic": "Fragility resolution forces liquidity response",
                    "expression_detail_location": "TACTICAL.md",
                },
            ],
            "shared_upstream_warnings": [],
        }
        result = _format_interaction_matrix_for_generation(matrix)
        assert "COMPOSITION GUIDANCE" in result
        assert "Structural Fragility" in result
        assert "Fiscal Dom. (Liquidity)" in result
        assert "A triggers B" in result
        assert "Fragility resolution" in result

    def test_formats_shared_upstream_warnings(self):
        matrix = {
            "pairwise": [],
            "shared_upstream_warnings": [
                {
                    "shared_cause": "Fed balance sheet",
                    "theories_affected": [
                        "fiscal_dominance_liquidity",
                        "monetary_architecture",
                    ],
                    "discounting_note": "Discount convergence",
                },
            ],
        }
        result = _format_interaction_matrix_for_generation(matrix)
        assert "Shared Upstream Cause Warnings" in result
        assert "Fed balance sheet" in result
        assert "Discount convergence" in result

    def test_empty_matrix_returns_empty_string(self):
        result = _format_interaction_matrix_for_generation(
            {"pairwise": [], "shared_upstream_warnings": []}
        )
        assert result == ""

    def test_unknown_theory_id_falls_back_to_raw_id(self):
        matrix = {
            "pairwise": [
                {
                    "theory_a": "unknown_theory",
                    "theory_b": "structural_fragility",
                    "relationship": "related",
                    "invariant_logic": "logic",
                    "expression_detail_location": "",
                },
            ],
            "shared_upstream_warnings": [],
        }
        result = _format_interaction_matrix_for_generation(matrix)
        assert "unknown_theory" in result


# ---------------------------------------------------------------------------
# build_generation_prompt_v8 — file inclusion
# ---------------------------------------------------------------------------


class TestGenerationPromptV8FileInclusion:

    def test_active_theory_includes_core_tactical_playbook(self):
        pkg = _make_package("structural_fragility", core="CORE_SF", tactical="TAC_SF", playbook="PLAY_SF")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "--- CORE.md ---" in prompt
        assert "CORE_SF" in prompt
        assert "--- TACTICAL.md ---" in prompt
        assert "TAC_SF" in prompt
        assert "--- PLAYBOOK.md ---" in prompt
        assert "PLAY_SF" in prompt

    def test_activation_md_not_in_generation_prompt(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "--- ACTIVATION.md ---" not in prompt

    def test_adjacent_theory_includes_same_files(self):
        pkg = _make_package("capital_flows", core="CORE_CF", tactical="TAC_CF", playbook="PLAY_CF")
        ar = _make_activation("capital_flows", ActivationTier.ADJACENT, score=0.45)
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "ADJACENT THEORY" in prompt
        assert "CORE_CF" in prompt
        assert "TAC_CF" in prompt
        assert "PLAY_CF" in prompt

    def test_inactive_theory_excluded(self):
        pkg_active = _make_package("structural_fragility", core="CORE_SF")
        pkg_inactive = _make_package("debt_cycle_long", core="CORE_DCL_SHOULD_NOT_APPEAR")
        ar_active = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        ar_inactive = _make_activation("debt_cycle_long", ActivationTier.INACTIVE, score=0.15)
        prompt = build_generation_prompt_v8(
            [pkg_active, pkg_inactive],
            [ar_active, ar_inactive],
            _basic_briefing(),
            [],
        )
        assert "CORE_SF" in prompt
        assert "CORE_DCL_SHOULD_NOT_APPEAR" not in prompt

    def test_max_adjacent_respected(self):
        pkgs = [
            _make_package("T1", core="CORE_T1"),
            _make_package("T2", core="CORE_T2"),
            _make_package("T3", core="CORE_T3"),
        ]
        ars = [
            _make_activation("T1", ActivationTier.ACTIVE),
            _make_activation("T2", ActivationTier.ADJACENT, score=0.50),
            _make_activation("T3", ActivationTier.ADJACENT, score=0.40),
        ]
        prompt = build_generation_prompt_v8(pkgs, ars, _basic_briefing(), [], max_adjacent=1)
        # Only first adjacent should appear
        assert "CORE_T2" in prompt
        assert "CORE_T3" not in prompt


# ---------------------------------------------------------------------------
# build_generation_prompt_v8 — interaction matrix
# ---------------------------------------------------------------------------


class TestGenerationPromptV8InteractionMatrix:

    def test_interaction_matrix_included_when_provided(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        matrix = {
            "pairwise": [
                {
                    "theory_a": "structural_fragility",
                    "theory_b": "fiscal_dominance_liquidity",
                    "relationship": "A triggers B",
                    "invariant_logic": "Fragility forces response",
                    "expression_detail_location": "",
                },
            ],
            "shared_upstream_warnings": [],
        }
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [], interaction_matrix=matrix)
        assert "COMPOSITION GUIDANCE" in prompt
        assert "A triggers B" in prompt

    def test_no_matrix_no_section(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "COMPOSITION GUIDANCE" not in prompt

    def test_empty_matrix_no_section(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        matrix = {"pairwise": [], "shared_upstream_warnings": []}
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [], interaction_matrix=matrix)
        assert "COMPOSITION GUIDANCE" not in prompt


# ---------------------------------------------------------------------------
# build_generation_prompt_v8 — context flags
# ---------------------------------------------------------------------------


class TestGenerationPromptV8ContextFlags:

    def test_context_flags_included_per_theory(self):
        flags = [
            ContextFlag(
                flag_name="Election rhetoric",
                source="web-search",
                data_ownership="qualitative",
                description="Monitor political risk signals",
                usage="Generator context",
            ),
        ]
        pkg = _make_package("structural_fragility", context_flags=flags)
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "Context Flags" in prompt
        assert "Election rhetoric" in prompt
        assert "Monitor political risk signals" in prompt

    def test_no_flags_no_section(self):
        pkg = _make_package("structural_fragility", context_flags=[])
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "Context Flags" not in prompt


# ---------------------------------------------------------------------------
# build_generation_prompt_v8 — preserved sections
# ---------------------------------------------------------------------------


class TestGenerationPromptV8PreservedSections:

    def test_system_instructions_present(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "SYSTEM:" in prompt
        assert "Generation Pass" in prompt

    def test_briefing_packet_included(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        briefing = {"growth": {"gdp_yoy": 2.1}}
        prompt = build_generation_prompt_v8([pkg], [ar], briefing, [])
        assert "DATA BRIEFING" in prompt
        assert "gdp_yoy" in prompt

    def test_output_format_present(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "OUTPUT FORMAT" in prompt

    def test_inbox_items_included(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        inbox = [{"date": "2026-04-01", "content": "Fed minutes hawkish", "source": "FOMC"}]
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), inbox)
        assert "INBOX ITEMS" in prompt
        assert "Fed minutes hawkish" in prompt

    def test_regime_flags_included(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        flags = [
            {
                "flag_id": "structural_fragility_active",
                "channel_context": {"structural_fragility": "Watch credit spreads"},
            },
        ]
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [], active_regime_flags=flags)
        assert "REGIME FLAGS" in prompt
        assert "Watch credit spreads" in prompt

    def test_resolution_channel_present(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "RESOLUTION CHANNEL REQUIREMENT" in prompt

    def test_thread_context_when_threads_provided(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        threads = [{"source_theory": "structural_fragility", "short_name": "Credit stress rising"}]
        prompt = build_generation_prompt_v8(
            [pkg], [ar], _basic_briefing(), [],
            active_threads=threads,
        )
        assert "ACTIVE THREADS" in prompt
        assert "LIFECYCLE CONTRACT" in prompt

    def test_legacy_prior_hypotheses_when_no_threads(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        prior = [{"theory_id": "structural_fragility", "short_name": "Old hypothesis"}]
        prompt = build_generation_prompt_v8(
            [pkg], [ar], _basic_briefing(), [],
            prior_hypotheses=prior,
        )
        assert "PRIOR HYPOTHESES" in prompt
        assert "CONTINUATION CONTRACT" in prompt


# ---------------------------------------------------------------------------
# build_generation_prompt_v8 — two-phase theory handling
# ---------------------------------------------------------------------------


class TestGenerationPromptV8TwoPhase:

    def test_two_phase_shows_phase_and_score(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation(
            "structural_fragility",
            ActivationTier.ACTIVE,
            is_two_phase=True,
            effective_phase="Resolving",
            phase_scores={"Building": 0.30, "Resolving": 0.75},
        )
        prompt = build_generation_prompt_v8([pkg], [ar], _basic_briefing(), [])
        assert "(Phase: Resolving)" in prompt
        assert "75%" in prompt
