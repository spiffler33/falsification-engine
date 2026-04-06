# test_prompt_thread_context.py — Tests for v7 thread context in generation prompt.
# Verifies: thread context injection, lifecycle contract, output schema routing,
# backward compatibility (no threads -> legacy path), staleness flag display,
# NEW hypothesis section for unrepresented theories.
from __future__ import annotations

import json
from typing import Optional

import pytest

from backend.engine.prompt_builder import (
    THEORY_LABEL_MAP,
    _new_hypothesis_section,
    _thread_context_section,
    _thread_lifecycle_contract,
    build_generation_prompt_v8,
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


def _make_thread(
    thread_id: str = "T-20260402-120000-01",
    short_name: str = "Gold rises on fiscal stress",
    source_theory: str = "fiscal_dominance_liquidity",
    total_instances: int = 3,
    created_date: str = "2026-03-15",
    asset_direction: dict | None = None,
    payoff_band_lower: float = 0.10,
    payoff_band_upper: float = 0.25,
    timeframe_end_date: str = "2026-09-30",
    expression_return: float = 0.08,
    realization_vs_lower: float = 0.80,
    realization_vs_upper: float = 0.32,
    time_elapsed_pct: float = 0.40,
    freshness_label: str = "WORKING",
    hard_falsifiers: list | None = None,
    soft_falsifiers: list | None = None,
) -> dict:
    return {
        "thread_id": thread_id,
        "short_name": short_name,
        "source_theory": source_theory,
        "total_instances": total_instances,
        "created_date": created_date,
        "asset_direction": asset_direction or {"GLD": "LONG", "TLT": "SHORT"},
        "payoff_band_lower": payoff_band_lower,
        "payoff_band_upper": payoff_band_upper,
        "timeframe_end_date": timeframe_end_date,
        "expression_return": expression_return,
        "realization_vs_lower": realization_vs_lower,
        "realization_vs_upper": realization_vs_upper,
        "time_elapsed_pct": time_elapsed_pct,
        "freshness_label": freshness_label,
        "hard_falsifiers": hard_falsifiers or [],
        "soft_falsifiers": soft_falsifiers or [],
    }


# ===================================================================
# _thread_context_section
# ===================================================================


class TestThreadContextSection:
    def test_single_thread_basic(self):
        """Single thread renders all core fields."""
        t = _make_thread()
        result = _thread_context_section([t])

        assert "1 active hypothesis thread" in result
        assert 'T-20260402-120000-01' in result
        assert '"Gold rises on fiscal stress"' in result
        assert "Fiscal Dom. (Liquidity)" in result
        assert "3 runs" in result
        assert "first generated 2026-03-15" in result
        assert "LONG GLD" in result
        assert "SHORT TLT" in result
        assert "10-25%" in result
        assert "through 2026-09-30" in result
        assert "+8.0%" in result
        assert "0.80x lower bound" in result
        assert "0.32x upper bound" in result
        assert "40% of time elapsed" in result
        assert "WORKING" in result
        assert "ACTION REQUIRED" in result

    def test_multiple_threads(self):
        """Multiple threads get listed with correct count."""
        t1 = _make_thread(thread_id="T-01", short_name="Thread A")
        t2 = _make_thread(thread_id="T-02", short_name="Thread B")
        result = _thread_context_section([t1, t2])

        assert "2 active hypothesis threads" in result
        assert "T-01" in result
        assert "T-02" in result

    def test_staleness_flag_displayed(self):
        """STALE falsifiers show staleness warning."""
        sf = {
            "name": "VIX spike",
            "severity": "major",
            "status": "CLEAR",
            "metric": "vix",
            "threshold": "VIX above 30",
            "staleness_flag": "STALE",
            "current_market_value": 22.5,
        }
        t = _make_thread(soft_falsifiers=[sf])
        result = _thread_context_section([t])

        assert "STALE" in result
        assert "2x threshold distance" in result

    def test_escalated_untestable_displayed(self):
        """ESCALATED_UNTESTABLE falsifiers show escalation warning."""
        sf = {
            "name": "China credit impulse",
            "severity": "medium",
            "status": "UNTESTABLE",
            "metric": "china_credit_impulse",
            "threshold": "below 5",
            "escalated_status": "ESCALATED_UNTESTABLE",
            "untestable_consecutive": 4,
        }
        t = _make_thread(soft_falsifiers=[sf])
        result = _thread_context_section([t])

        assert "ESCALATED" in result
        assert "4 consecutive passes" in result

    def test_hard_falsifier_counts(self):
        """Hard falsifier passed/failed counts are displayed."""
        hf = [
            {"condition": "GDP falls", "status": "CLEAR"},
            {"condition": "Fed cuts", "status": "FAILED"},
        ]
        t = _make_thread(hard_falsifiers=hf)
        result = _thread_context_section([t])

        assert "1 passed" in result
        assert "1 FAILED" in result

    def test_no_realization_data(self):
        """Thread without realization data still renders without error."""
        t = _make_thread(expression_return=None, realization_vs_lower=None, realization_vs_upper=None)
        result = _thread_context_section([t])

        assert "T-20260402-120000-01" in result
        # Should not crash, just skip realization lines

    def test_single_run_age(self):
        """Single-instance thread shows '1 run' (singular)."""
        t = _make_thread(total_instances=1)
        result = _thread_context_section([t])
        assert "1 run " in result

    def test_default_action_instructions(self):
        """Section includes instructions about CONFIRM being default."""
        result = _thread_context_section([_make_thread()])
        assert "CONFIRM is the default action" in result
        assert "Do not UPDATE" in result
        assert "Do not RENEW" in result


# ===================================================================
# _thread_lifecycle_contract
# ===================================================================


class TestThreadLifecycleContract:
    def test_contains_all_actions(self):
        """Contract mentions all 4 lifecycle actions."""
        result = _thread_lifecycle_contract()
        for action in ["CONFIRM", "UPDATE", "RENEW", "RETIRE"]:
            assert action in result

    def test_contains_output_format(self):
        """Contract includes the expected output format with thread_actions."""
        result = _thread_lifecycle_contract()
        assert "thread_actions" in result
        assert "lifecycle_action" in result
        assert "lifecycle_reasoning" in result

    def test_renew_requires_full_hypothesis(self):
        """RENEW requires renewed_hypothesis with full specification."""
        result = _thread_lifecycle_contract()
        assert "renewed_hypothesis" in result

    def test_confirm_default_emphasis(self):
        """Emphasizes CONFIRM as default action."""
        result = _thread_lifecycle_contract()
        assert "CONFIRM is the expectation" in result


# ===================================================================
# _new_hypothesis_section
# ===================================================================


class TestNewHypothesisSection:
    def test_shows_unrepresented_theories(self):
        """Lists active theories not covered by threads."""
        result = _new_hypothesis_section(
            active_theories=["fiscal_dominance_liquidity", "valuation_mean_reversion"],
            active_scores={"fiscal_dominance_liquidity": 0.75, "valuation_mean_reversion": 0.68},
            represented_theories={"fiscal_dominance_liquidity"},
        )
        assert "Valuation Mean Reversion" in result
        assert "Unrepresented" in result
        assert "68%" in result

    def test_shows_represented_theories(self):
        """Lists theories already represented with note."""
        result = _new_hypothesis_section(
            active_theories=["fiscal_dominance_liquidity", "valuation_mean_reversion"],
            active_scores={},
            represented_theories={"fiscal_dominance_liquidity"},
        )
        assert "Already represented" in result
        assert "Fiscal Dom. (Liquidity)" in result

    def test_shows_adjacent_theories(self):
        """Adjacent theories shown as optional wildcard."""
        result = _new_hypothesis_section(
            active_theories=["fiscal_dominance_liquidity"],
            active_scores={},
            represented_theories={"fiscal_dominance_liquidity"},
            adjacent_theories=["capital_flows"],
        )
        assert "Adjacent" in result
        assert "Capital Flows" in result

    def test_target_count(self):
        """Always includes the 7-9 target."""
        result = _new_hypothesis_section(
            active_theories=[],
            active_scores={},
            represented_theories=set(),
        )
        assert "7-9" in result


# ===================================================================
# build_generation_prompt_v8 — integration with thread context
# ===================================================================


class TestBuildGenerationPromptWithThreads:
    """Test the full prompt assembly with active_threads parameter."""

    def _build_prompt(self, active_threads=None, prior_hypotheses=None):
        packages = [
            _make_package("fiscal_dominance_liquidity"),
            _make_package("valuation_mean_reversion"),
        ]
        activations = [
            _make_activation("fiscal_dominance_liquidity", ActivationTier.ACTIVE, 0.75),
            _make_activation("valuation_mean_reversion", ActivationTier.ACTIVE, 0.68),
        ]
        briefing = {"growth": {"gdp_now": 2.1}, "timestamp": "2026-04-03"}
        return build_generation_prompt_v8(
            packages=packages,
            activation_results=activations,
            briefing=briefing,
            inbox_items=[],
            active_threads=active_threads,
            prior_hypotheses=prior_hypotheses,
        )

    def test_v7_path_with_threads(self):
        """When active_threads provided, uses thread context + lifecycle contract."""
        threads = [_make_thread(source_theory="fiscal_dominance_liquidity")]
        prompt = self._build_prompt(active_threads=threads)

        # Thread context present
        assert "ACTIVE THREADS (from prior run)" in prompt
        assert "LIFECYCLE CONTRACT" in prompt
        assert "thread_actions" in prompt

        # Legacy path absent
        assert "PRIOR HYPOTHESES" not in prompt
        assert "CONTINUATION CONTRACT" not in prompt

    def test_v7_path_includes_new_section(self):
        """Thread path includes NEW HYPOTHESIS GENERATION section."""
        threads = [_make_thread(source_theory="fiscal_dominance_liquidity")]
        prompt = self._build_prompt(active_threads=threads)

        assert "NEW HYPOTHESIS GENERATION" in prompt
        # valuation_mean_reversion is not represented in threads
        assert "Valuation Mean Reversion" in prompt
        assert "Unrepresented" in prompt

    def test_v7_output_schema(self):
        """Thread path uses v7 output schema with thread_actions + new_hypotheses."""
        threads = [_make_thread()]
        prompt = self._build_prompt(active_threads=threads)

        assert '"thread_actions"' in prompt
        assert '"new_hypotheses"' in prompt
        assert "lifecycle_action" in prompt

    def test_legacy_path_no_threads(self):
        """When no threads, falls back to legacy path."""
        prior = [{
            "id": "H-20260315-01",
            "short_name": "Legacy hypothesis",
            "predicted_assets": ["SPY"],
            "asset_direction": {"SPY": "LONG"},
            "predicted_magnitude_lower": 0.10,
            "predicted_magnitude_upper": 0.20,
            "timeframe_end_date": "2026-09-30",
            "expression_return": 0.05,
            "realization_vs_lower": 0.50,
            "realization_vs_upper": 0.25,
            "time_elapsed_pct": 0.30,
            "status": "SURVIVED",
            "continuation_generation": 1,
            "continuation_of": None,
        }]
        prompt = self._build_prompt(prior_hypotheses=prior)

        # Legacy path present
        assert "PRIOR HYPOTHESES" in prompt
        assert "CONTINUATION CONTRACT" in prompt

        # Thread path absent
        assert "ACTIVE THREADS" not in prompt
        assert "LIFECYCLE CONTRACT" not in prompt

    def test_first_run_no_threads_no_prior(self):
        """First run: no threads, no prior hypotheses — clean generation."""
        prompt = self._build_prompt()

        # Neither thread nor legacy prior sections
        assert "ACTIVE THREADS" not in prompt
        assert "PRIOR HYPOTHESES" not in prompt
        assert "LIFECYCLE CONTRACT" not in prompt
        assert "CONTINUATION CONTRACT" not in prompt

        # Core sections still present
        assert "ACTIVE THEORIES" in prompt
        assert "DATA BRIEFING" in prompt
        assert "OUTPUT FORMAT" in prompt

    def test_system_instructions_thread_aware(self):
        """When threads present, system instructions mention continuation run."""
        threads = [_make_thread()]
        prompt = self._build_prompt(active_threads=threads)
        assert "CONTINUATION RUN" in prompt

    def test_system_instructions_first_run(self):
        """Without threads, system instructions are standard."""
        prompt = self._build_prompt()
        assert "CONTINUATION RUN" not in prompt
        assert "Generate 2-4 hypotheses per Active theory" in prompt

    def test_threads_override_prior_hypotheses(self):
        """When both threads and prior_hypotheses provided, threads take precedence."""
        threads = [_make_thread()]
        prior = [{"id": "H-old", "short_name": "Should not appear"}]
        prompt = self._build_prompt(active_threads=threads, prior_hypotheses=prior)

        assert "ACTIVE THREADS" in prompt
        assert "PRIOR HYPOTHESES" not in prompt

    def test_resolution_channel_always_present(self):
        """Resolution channel requirement appears in all modes."""
        for kwargs in [
            {},
            {"active_threads": [_make_thread()]},
            {"prior_hypotheses": [{"id": "H-01", "short_name": "test", "predicted_assets": [], "asset_direction": {}, "status": "SURVIVED", "continuation_generation": 1, "continuation_of": None}]},
        ]:
            prompt = self._build_prompt(**kwargs)
            assert "RESOLUTION CHANNEL" in prompt

    def test_briefing_always_present(self):
        """Data briefing appears in all modes."""
        prompt = self._build_prompt(active_threads=[_make_thread()])
        assert "DATA BRIEFING" in prompt
        assert "gdp_now" in prompt

    def test_staleness_flag_reaches_prompt(self):
        """Staleness flags on falsifiers survive through to prompt text."""
        sf = {
            "name": "HY spread blowout",
            "severity": "major",
            "status": "CLEAR",
            "metric": "hy_spread",
            "threshold": "spread above 500bps",
            "staleness_flag": "STALE",
            "current_market_value": 380.0,
        }
        threads = [_make_thread(soft_falsifiers=[sf])]
        prompt = self._build_prompt(active_threads=threads)

        assert "STALE" in prompt
        assert "HY spread blowout" in prompt
