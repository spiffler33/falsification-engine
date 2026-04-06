# test_prompt_builder_v8.py — Tests for v8 prompt composition (Unit 9+).
# Verifies that build_generation_prompt_v8 composes from TheoryPackage files
# and includes interaction matrix / context flags sections correctly.
from __future__ import annotations

import json

import pytest

from backend.engine.prompt_builder import (
    THEORY_LABEL_MAP,
    _format_context_flags,
    _format_falsifier_registry_block,
    _format_interaction_matrix_for_elimination,
    _format_interaction_matrix_for_generation,
    build_elimination_prompt_v8,
    build_generation_prompt_v8,
)
from backend.engine.activation import _build_phases_from_package
from backend.schemas.theory import (
    ActivationResult,
    ActivationTier,
    ContextFlag,
    FalsifierEntry,
    Severity,
    TheoryPackage,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_package(
    theory_id: str,
    core: str = "# CORE content",
    activation: str = "# ACTIVATION content",
    tactical: str = "# TACTICAL content",
    playbook: str = "# PLAYBOOK content",
    context_flags: list | None = None,
    falsifier_registry: list | None = None,
) -> TheoryPackage:
    return TheoryPackage(
        theory_id=theory_id,
        core=core,
        activation=activation,
        tactical=tactical,
        playbook=playbook,
        context_flags=context_flags or [],
        falsifier_registry=falsifier_registry or [],
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


# ===========================================================================
# build_elimination_prompt_v8 tests (Unit 10)
# ===========================================================================


def _sample_falsifier_registry() -> list[FalsifierEntry]:
    return [
        FalsifierEntry(
            falsifier_id="H1",
            condition="Fed raises rates 75bp+",
            logic="Contractionary shock kills reflation thesis",
            classification="hard",
            severity=None,
            discount=None,
        ),
        FalsifierEntry(
            falsifier_id="S1",
            condition="Credit spreads narrow below 100bp",
            logic="Risk appetite contradicts fragility thesis",
            classification="soft",
            severity=Severity.MEDIUM,
            discount=0.25,
        ),
        FalsifierEntry(
            falsifier_id="S2",
            condition="VIX sustains below 15 for 30 days",
            logic="Volatility collapse weakens positioning",
            classification="soft",
            severity=Severity.MINOR,
            discount=0.10,
        ),
    ]


def _sample_hypotheses(source_theory: str = "structural_fragility") -> list[dict]:
    return [
        {
            "source_theory": source_theory,
            "source_theories": [source_theory],
            "short_name": "Credit stress rising",
            "prediction": "HYG -10% through Q3",
        },
    ]


def _composite_hypotheses() -> list[dict]:
    """Multi-theory hypothesis for composition integrity tests."""
    return [
        {
            "source_theory": "structural_fragility",
            "source_theories": ["structural_fragility", "fiscal_dominance_liquidity"],
            "short_name": "Fragility triggers liquidity repricing",
            "prediction": "TLT +15% as flight to quality",
        },
    ]


# ---------------------------------------------------------------------------
# _format_falsifier_registry_block
# ---------------------------------------------------------------------------


class TestFormatFalsifierRegistryBlock:

    def test_formats_hard_and_soft_falsifiers(self):
        registry = _sample_falsifier_registry()
        result = _format_falsifier_registry_block(registry)
        assert "Falsifier Registry (pre-joined)" in result
        assert "Hard Falsifiers:" in result
        assert "[H1]" in result
        assert "Fed raises rates 75bp+" in result
        assert "Soft Falsifiers:" in result
        assert "[S1]" in result
        assert "(medium)" in result
        assert "Credit spreads narrow below 100bp" in result

    def test_includes_logic_lines(self):
        registry = _sample_falsifier_registry()
        result = _format_falsifier_registry_block(registry)
        assert "Logic: Contractionary shock kills reflation thesis" in result
        assert "Logic: Risk appetite contradicts fragility thesis" in result

    def test_hard_only_registry(self):
        registry = [
            FalsifierEntry(
                falsifier_id="H1", condition="Rate hike", logic="Kills thesis",
                classification="hard", severity=None, discount=None,
            ),
        ]
        result = _format_falsifier_registry_block(registry)
        assert "Hard Falsifiers:" in result
        assert "Soft Falsifiers:" not in result

    def test_soft_only_registry(self):
        registry = [
            FalsifierEntry(
                falsifier_id="S1", condition="Spreads narrow", logic="Weakens",
                classification="soft", severity=Severity.MAJOR, discount=0.45,
            ),
        ]
        result = _format_falsifier_registry_block(registry)
        assert "Soft Falsifiers:" in result
        assert "Hard Falsifiers:" not in result
        assert "(major)" in result

    def test_empty_registry_returns_empty(self):
        result = _format_falsifier_registry_block([])
        assert result == ""

    def test_handles_dict_entries(self):
        registry = [
            {
                "falsifier_id": "H1",
                "condition": "Rate hike",
                "logic": "Kills thesis",
                "classification": "hard",
            },
        ]
        result = _format_falsifier_registry_block(registry)
        assert "[H1]" in result
        assert "Rate hike" in result


# ---------------------------------------------------------------------------
# _format_interaction_matrix_for_elimination
# ---------------------------------------------------------------------------


class TestFormatInteractionMatrixForElimination:

    def test_formats_pairwise_as_composition_validation(self):
        matrix = {
            "pairwise": [
                {
                    "theory_a": "structural_fragility",
                    "theory_b": "fiscal_dominance_liquidity",
                    "relationship": "A triggers B",
                    "invariant_logic": "Fragility forces response",
                    "expression_detail_location": "TACTICAL.md",
                },
            ],
            "shared_upstream_warnings": [],
        }
        result = _format_interaction_matrix_for_elimination(matrix)
        assert "COMPOSITION VALIDATION" in result
        assert "COMPOSITION GUIDANCE" not in result  # That's the generation framing
        assert "Structural Fragility" in result
        assert "A triggers B" in result

    def test_includes_shared_upstream_warnings(self):
        matrix = {
            "pairwise": [],
            "shared_upstream_warnings": [
                {
                    "shared_cause": "Fed balance sheet",
                    "theories_affected": ["fiscal_dominance_liquidity", "monetary_architecture"],
                    "discounting_note": "Discount convergence by 50%",
                },
            ],
        }
        result = _format_interaction_matrix_for_elimination(matrix)
        assert "Shared Upstream Cause Warnings" in result
        assert "Fed balance sheet" in result
        assert "double-counting" in result
        assert "Discount convergence" in result

    def test_empty_matrix_returns_empty(self):
        result = _format_interaction_matrix_for_elimination(
            {"pairwise": [], "shared_upstream_warnings": []}
        )
        assert result == ""


# ---------------------------------------------------------------------------
# build_elimination_prompt_v8 — file inclusion
# ---------------------------------------------------------------------------


class TestEliminationPromptV8FileInclusion:

    def test_invoked_theory_includes_all_four_files(self):
        pkg = _make_package(
            "structural_fragility",
            core="CORE_SF_ELIM",
            activation="ACTIV_SF_ELIM",
            tactical="TAC_SF_ELIM",
            playbook="PLAY_SF_ELIM",
        )
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "--- CORE.md ---" in prompt
        assert "CORE_SF_ELIM" in prompt
        assert "--- ACTIVATION.md ---" in prompt
        assert "ACTIV_SF_ELIM" in prompt
        assert "--- TACTICAL.md ---" in prompt
        assert "TAC_SF_ELIM" in prompt
        assert "--- PLAYBOOK.md ---" in prompt
        assert "PLAY_SF_ELIM" in prompt

    def test_non_invoked_theory_excluded(self):
        pkg_invoked = _make_package("structural_fragility", core="CORE_SF")
        pkg_other = _make_package("debt_cycle_long", core="CORE_DCL_SHOULD_NOT_APPEAR")
        ar_invoked = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        ar_other = _make_activation("debt_cycle_long", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(
            hypotheses, [pkg_invoked, pkg_other], [ar_invoked, ar_other], _basic_briefing(),
        )
        assert "CORE_SF" in prompt
        assert "CORE_DCL_SHOULD_NOT_APPEAR" not in prompt

    def test_composite_hypothesis_includes_both_theories(self):
        pkg_sf = _make_package("structural_fragility", core="CORE_SF_COMP")
        pkg_fdl = _make_package("fiscal_dominance_liquidity", core="CORE_FDL_COMP")
        ar_sf = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        ar_fdl = _make_activation("fiscal_dominance_liquidity", ActivationTier.ACTIVE)
        hypotheses = _composite_hypotheses()
        prompt = build_elimination_prompt_v8(
            hypotheses, [pkg_sf, pkg_fdl], [ar_sf, ar_fdl], _basic_briefing(),
        )
        assert "CORE_SF_COMP" in prompt
        assert "CORE_FDL_COMP" in prompt

    def test_theory_label_used_in_header(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "### Structural Fragility" in prompt


# ---------------------------------------------------------------------------
# build_elimination_prompt_v8 — falsifier registry
# ---------------------------------------------------------------------------


class TestEliminationPromptV8FalsifierRegistry:

    def test_registry_block_included_when_present(self):
        registry = _sample_falsifier_registry()
        pkg = _make_package("structural_fragility", falsifier_registry=registry)
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "Falsifier Registry (pre-joined)" in prompt
        assert "[H1]" in prompt
        assert "[S1]" in prompt
        assert "(medium)" in prompt

    def test_no_registry_no_block(self):
        pkg = _make_package("structural_fragility", falsifier_registry=[])
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "Falsifier Registry" not in prompt


# ---------------------------------------------------------------------------
# build_elimination_prompt_v8 — interaction matrix
# ---------------------------------------------------------------------------


class TestEliminationPromptV8InteractionMatrix:

    def test_matrix_included_as_composition_validation(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
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
        prompt = build_elimination_prompt_v8(
            hypotheses, [pkg], [ar], _basic_briefing(), interaction_matrix=matrix,
        )
        assert "COMPOSITION VALIDATION" in prompt
        assert "A triggers B" in prompt

    def test_no_matrix_no_section(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "COMPOSITION VALIDATION" not in prompt

    def test_empty_matrix_no_section(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        matrix = {"pairwise": [], "shared_upstream_warnings": []}
        prompt = build_elimination_prompt_v8(
            hypotheses, [pkg], [ar], _basic_briefing(), interaction_matrix=matrix,
        )
        assert "COMPOSITION VALIDATION" not in prompt


# ---------------------------------------------------------------------------
# build_elimination_prompt_v8 — preserved sections
# ---------------------------------------------------------------------------


class TestEliminationPromptV8PreservedSections:

    def test_system_instructions_present(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "SYSTEM:" in prompt
        assert "Elimination Pass" in prompt

    def test_hypotheses_included_as_json(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "HYPOTHESES TO ATTACK" in prompt
        assert "Credit stress rising" in prompt

    def test_activation_state_present(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "CURRENT ACTIVATION STATE" in prompt
        assert "Structural Fragility" in prompt
        assert "Active" in prompt

    def test_briefing_packet_included(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        briefing = {"growth": {"gdp_yoy": 2.1}}
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], briefing)
        assert "DATA BRIEFING" in prompt
        assert "gdp_yoy" in prompt

    def test_output_format_present(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "OUTPUT FORMAT" in prompt


# ---------------------------------------------------------------------------
# build_elimination_prompt_v8 — optional sections
# ---------------------------------------------------------------------------


class TestEliminationPromptV8OptionalSections:

    def test_channel_verification_when_enabled(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(
            hypotheses, [pkg], [ar], _basic_briefing(), has_channel_tags=True,
        )
        assert "CHANNEL VERIFICATION" in prompt

    def test_no_channel_verification_when_disabled(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(
            hypotheses, [pkg], [ar], _basic_briefing(), has_channel_tags=False,
        )
        assert "CHANNEL VERIFICATION" not in prompt

    def test_sector_appendices_when_provided(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        appendices = [
            {
                "sector_id": "tech",
                "display_name": "Technology",
                "ticker_triggers": ["QQQ"],
                "mechanical_falsifiers": [
                    {
                        "falsifier_id": "tech_sf_01",
                        "condition": "AI capex growth decelerates",
                        "metric": "tech_capex_growth_yoy",
                        "threshold": "15",
                        "direction": "below",
                        "severity": "medium",
                        "data_source": "earnings reports",
                    },
                ],
                "evaluator_attack_vectors": [
                    {
                        "vector_id": "tech_av_01",
                        "question": "Are margins compressing?",
                        "what_to_search": "tech sector margin data",
                        "kill_condition": "Margins down 500bp+",
                    },
                ],
            },
        ]
        prompt = build_elimination_prompt_v8(
            hypotheses, [pkg], [ar], _basic_briefing(), sector_appendices=appendices,
        )
        assert "SECTOR FALSIFIER APPENDICES" in prompt
        assert "Technology" in prompt

    def test_falsifier_lifecycle_when_enabled(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(
            hypotheses, [pkg], [ar], _basic_briefing(), has_falsifier_lifecycle=True,
        )
        assert "FALSIFIER LIFECYCLE INSTRUCTIONS" in prompt
        assert "STALENESS INTERPRETATION" in prompt
        assert "EMERGENT RISK ASSESSMENT" in prompt

    def test_no_lifecycle_when_disabled(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation("structural_fragility", ActivationTier.ACTIVE)
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(
            hypotheses, [pkg], [ar], _basic_briefing(), has_falsifier_lifecycle=False,
        )
        assert "FALSIFIER LIFECYCLE INSTRUCTIONS" not in prompt


# ---------------------------------------------------------------------------
# build_elimination_prompt_v8 — two-phase theory in activation state
# ---------------------------------------------------------------------------


class TestEliminationPromptV8TwoPhase:

    def test_two_phase_shows_phase_in_activation_state(self):
        pkg = _make_package("structural_fragility")
        ar = _make_activation(
            "structural_fragility",
            ActivationTier.ACTIVE,
            is_two_phase=True,
            effective_phase="Resolving",
            phase_scores={"Building": 0.30, "Resolving": 0.75},
        )
        hypotheses = _sample_hypotheses("structural_fragility")
        prompt = build_elimination_prompt_v8(hypotheses, [pkg], [ar], _basic_briefing())
        assert "(Resolving)" in prompt


# ===========================================================================
# Pass 1 — Activation Data Path (Component 12: Layer 3)
# ===========================================================================
# Pass 1 is mechanical Python, not an LLM prompt. The "prompt assembly"
# test verifies that only ACTIVATION.md content reaches the activation
# scorer via the TheoryPackage → TheoryModule adapter.


_SINGLE_PHASE_ACTIVATION = """\
## activation_table

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|---------------|-----------|-----------|--------|----------------------|
| GDP Growth | fred: gdp_yoy | mechanical | 2.0% | above | 0.25 | Standard threshold |
| Core Inflation | fred: core_cpi_yoy | mechanical | 3.0% | above | 0.35 | Target deviation |
| Fed Funds Rate | fred: fed_funds | mechanical | 5.0% | above | 0.40 | Restriction threshold |
"""

_TWO_PHASE_ACTIVATION = """\
## activation_table

### Phase A: Expansion

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|---------------|-----------|-----------|--------|----------------------|
| Credit Growth | fred: credit_growth | mechanical | 5.0% | above | 0.50 | Credit expansion signal |
| Consumer Confidence | web search: Conference Board | web-search | 100 | above | 0.50 | Sentiment gauge |

### Phase B: Contraction

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|---------------|-----------|-----------|--------|----------------------|
| Credit Spreads | fred: hy_spread | mechanical | 500bp | above | 0.60 | Stress threshold |
| Bank Lending | fred: bank_lending | mechanical | 0% | below | 0.40 | Contraction signal |
"""


class TestActivationDataPathV8:
    """Layer 3 snapshot: Pass 1 reads ACTIVATION.md content exclusively.

    Uses activation._build_phases_from_package() — the package-native path
    that replaced the temporary adapter after v8 cutover.
    """

    def test_extracts_indicators_from_activation_field(self):
        pkg = _make_package("test_theory", activation=_SINGLE_PHASE_ACTIVATION)
        is_two_phase, phases = _build_phases_from_package(pkg)
        assert not is_two_phase
        assert len(phases) == 1
        indicators = phases[0].indicators
        assert len(indicators) == 3
        names = {ind.name for ind in indicators}
        assert "GDP Growth" in names
        assert "Core Inflation" in names
        assert "Fed Funds Rate" in names

    def test_activation_ignores_core_tactical_playbook(self):
        """Changing core/tactical/playbook does not affect activation —
        Pass 1 reads only ACTIVATION.md."""
        pkg_a = _make_package(
            "test_theory",
            core="CORE version A — long essay about causal mechanisms",
            tactical="TACTICAL version A — ETF mappings for equities",
            playbook="PLAYBOOK version A — generator guidance for credit",
            activation=_SINGLE_PHASE_ACTIVATION,
        )
        pkg_b = _make_package(
            "test_theory",
            core="Entirely different CORE content",
            tactical="Entirely different TACTICAL content",
            playbook="Entirely different PLAYBOOK content",
            activation=_SINGLE_PHASE_ACTIVATION,
        )
        _, phases_a = _build_phases_from_package(pkg_a)
        _, phases_b = _build_phases_from_package(pkg_b)
        assert len(phases_a) == len(phases_b)
        for pa, pb in zip(phases_a, phases_b):
            assert pa.phase_name == pb.phase_name
            assert len(pa.indicators) == len(pb.indicators)
            for ind_a, ind_b in zip(pa.indicators, pb.indicators):
                assert ind_a.name == ind_b.name
                assert ind_a.weight == ind_b.weight
                assert ind_a.direction == ind_b.direction

    def test_single_phase_produces_one_activation_phase(self):
        pkg = _make_package("test_theory", activation=_SINGLE_PHASE_ACTIVATION)
        is_two_phase, phases = _build_phases_from_package(pkg)
        assert len(phases) == 1
        assert phases[0].phase_name == "single"
        assert not is_two_phase

    def test_two_phase_produces_two_activation_phases(self):
        pkg = _make_package("debt_cycle_short", activation=_TWO_PHASE_ACTIVATION)
        is_two_phase, phases = _build_phases_from_package(pkg)
        assert is_two_phase
        assert len(phases) == 2
        phase_names = {p.phase_name for p in phases}
        assert "phase_a" in phase_names
        assert "phase_b" in phase_names

    def test_indicator_weights_preserved(self):
        pkg = _make_package("test_theory", activation=_SINGLE_PHASE_ACTIVATION)
        _, phases = _build_phases_from_package(pkg)
        indicators = phases[0].indicators
        weight_map = {ind.name: ind.weight for ind in indicators}
        assert weight_map["GDP Growth"] == 0.25
        assert weight_map["Core Inflation"] == 0.35
        assert weight_map["Fed Funds Rate"] == 0.40

    def test_two_phase_indicators_separated_by_phase(self):
        pkg = _make_package("debt_cycle_short", activation=_TWO_PHASE_ACTIVATION)
        _, phases = _build_phases_from_package(pkg)
        phase_map = {p.phase_name: p for p in phases}
        phase_a_names = {ind.name for ind in phase_map["phase_a"].indicators}
        phase_b_names = {ind.name for ind in phase_map["phase_b"].indicators}
        assert "Credit Growth" in phase_a_names
        assert "Consumer Confidence" in phase_a_names
        assert "Credit Spreads" in phase_b_names
        assert "Bank Lending" in phase_b_names
        # No cross-contamination
        assert phase_a_names.isdisjoint(phase_b_names)

    def test_web_search_prefix_injected_for_web_search_indicators(self):
        """The activation engine re-injects 'web search:' prefix for web-search
        indicators so _extract_metric_field resolves fields via WEB_FIELD_MAP."""
        pkg = _make_package("debt_cycle_short", activation=_TWO_PHASE_ACTIVATION)
        _, phases = _build_phases_from_package(pkg)
        phase_a = next(p for p in phases if p.phase_name == "phase_a")
        conf_ind = next(i for i in phase_a.indicators if i.name == "Consumer Confidence")
        assert conf_ind.requires_web_search is True
        assert conf_ind.metric_source.lower().startswith("web search:")


# ---------------------------------------------------------------------------
# Task 6: Phase structure validation in _build_phases_from_package
# (FRAGILITY-03, FRAGILITY-11)
# ---------------------------------------------------------------------------

_PHASE_TABLE_HEADER = (
    "| Indicator | Metric Source | Data Ownership | Threshold "
    "| Direction | Weight | Rationale |\n"
    "|-----------|--------------|----------------|-----------|"
    "-----------|--------|-----------|\n"
)
_PHASE_ROW_A = "| Ind A | src_a | mechanical | Above 10 | above | 0.50 | Note |\n"
_PHASE_ROW_B = "| Ind B | src_b | mechanical | Below 5 | below | 0.50 | Note |\n"
_PHASE_ROW_C = "| Ind C | src_c | mechanical | Above 20 | above | 0.40 | Note |\n"


class TestBuildPhasesValidation:
    """FRAGILITY-03/FRAGILITY-11: phase structure validation."""

    def test_unrecognized_phase_string_raises(self):
        """Phase strings without 'Phase A' or 'Phase B' are rejected."""
        text = (
            "## activation_table — Expansion\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_A}\n"
            "## activation_table — Contraction\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_B}\n"
        )
        pkg = _make_package("test", activation=text)
        with pytest.raises(ValueError, match="does not contain.*Phase A.*Phase B"):
            _build_phases_from_package(pkg)

    def test_duplicate_phase_a_raises(self):
        """Two phase strings that both map to phase_a are rejected."""
        text = (
            "## activation_table\n\n"
            "### Phase A: Alpha\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_A}\n"
            "### Phase A: Beta\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_B}\n"
        )
        pkg = _make_package("test", activation=text)
        with pytest.raises(ValueError, match="Duplicate phase name.*phase_a"):
            _build_phases_from_package(pkg)

    def test_three_phase_groups_raises(self):
        """Three distinct phase groups are rejected."""
        text = (
            "## activation_table — Phase A: Expansion\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_A}\n"
            "## activation_table — Phase B: Contraction\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_B}\n"
            "## activation_table — Phase A: Late Expansion\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_C}\n"
        )
        pkg = _make_package("test", activation=text)
        with pytest.raises(ValueError, match="3 phase groups.*expected exactly 2"):
            _build_phases_from_package(pkg)

    def test_valid_subsection_format_passes(self):
        """structural_fragility/capital_flows style: ### subsections."""
        pkg = _make_package("test", activation=_TWO_PHASE_ACTIVATION)
        is_two_phase, phases = _build_phases_from_package(pkg)
        assert is_two_phase
        assert len(phases) == 2
        names = {p.phase_name for p in phases}
        assert names == {"phase_a", "phase_b"}

    def test_valid_separate_heading_format_passes(self):
        """debt_cycle_short style: separate ## headings."""
        text = (
            "## activation_table — Phase A: Expansion\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_A}\n"
            "## activation_table — Phase B: Contraction\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_B}\n"
        )
        pkg = _make_package("test", activation=text)
        is_two_phase, phases = _build_phases_from_package(pkg)
        assert is_two_phase
        assert len(phases) == 2
        names = {p.phase_name for p in phases}
        assert names == {"phase_a", "phase_b"}

    def test_phase_labels_extracted(self):
        """Phase labels are extracted from 'Phase A: <label>' format."""
        text = (
            "## activation_table\n\n"
            "### Phase A: Fragility Building\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_A}\n"
            "### Phase B: Fragility Resolving\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_B}\n"
        )
        pkg = _make_package("test", activation=text)
        _, phases = _build_phases_from_package(pkg)
        labels = {p.phase_name: p.phase_label for p in phases}
        assert labels["phase_a"] == "Fragility Building"
        assert labels["phase_b"] == "Fragility Resolving"

    def test_case_insensitive_phase_matching(self):
        """Phase A/B detection is case-insensitive."""
        text = (
            "## activation_table\n\n"
            "### phase a: Alpha\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_A}\n"
            "### phase b: Beta\n\n"
            f"{_PHASE_TABLE_HEADER}"
            f"{_PHASE_ROW_B}\n"
        )
        pkg = _make_package("test", activation=text)
        is_two_phase, phases = _build_phases_from_package(pkg)
        assert is_two_phase
        names = {p.phase_name for p in phases}
        assert names == {"phase_a", "phase_b"}
