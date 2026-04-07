"""v9 Phase 2: Parallel comparison — legacy vs compiled scoring side by side.

Runs both the legacy activation engine and the Phase 1 compiled evaluator
on the same frozen briefing packet, then produces a structured comparison
at theory, phase, and indicator levels.

Depends on: activation.py (legacy), compiled_evaluator.py (v9), compiler.py
Depended on by: semantic_diff.py, scripts/v9_phase2_compile.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.schemas.briefing import BriefingPacket
from backend.schemas.theory import ActivationResult, ActivationTier as LegacyTier
from backend.schemas.v9.compiled_activation import CompiledActivationArtifact, PhaseModel
from backend.engine.v9.compiled_evaluator import (
    ActivationTier as CompiledTier,
    CompiledActivationEvaluator,
    CompiledEvaluationResult,
    IndicatorResult,
    PhaseResult,
)
from backend.engine.v9.registry_builder import build_full_registry
from backend.engine.v9.rule_evaluator import RuleOutcome


# ---------------------------------------------------------------------------
# Comparison data structures
# ---------------------------------------------------------------------------

@dataclass
class IndicatorComparison:
    """Side-by-side result for a single indicator."""
    indicator_id: str
    display_name: str
    phase_id: str
    # Compiled side
    compiled_triggered: Optional[bool] = None   # True/False/None (not evaluable)
    compiled_outcome: str = ""                   # RuleOutcome value
    compiled_value: Optional[float] = None
    compiled_threshold: Optional[float] = None
    compiled_detail: str = ""
    compiled_in_denominator: bool = True
    # Legacy side
    legacy_triggered: Optional[bool] = None
    legacy_value: Optional[float] = None
    legacy_threshold: Optional[float] = None
    legacy_skipped: bool = False
    # Comparison
    status: str = ""      # MATCH, MISMATCH, NOT_EVALUABLE, NOT_IN_LEGACY, LEGACY_SKIPPED


@dataclass
class PhaseComparison:
    """Side-by-side result for a single phase."""
    phase_id: str
    phase_label: str
    compiled_score: float = 0.0
    legacy_score: float = 0.0
    compiled_tier: str = ""
    legacy_tier: str = ""
    tier_match: bool = True
    score_delta: float = 0.0
    indicators: list[IndicatorComparison] = field(default_factory=list)
    match_count: int = 0
    mismatch_count: int = 0
    not_evaluable_count: int = 0
    not_in_legacy_count: int = 0
    legacy_skipped_count: int = 0


@dataclass
class TheoryComparison:
    """Full comparison result for one theory."""
    theory_id: str
    compiled_effective_tier: str = ""
    legacy_effective_tier: str = ""
    tier_match: bool = True
    phases: list[PhaseComparison] = field(default_factory=list)
    total_matches: int = 0
    total_mismatches: int = 0
    total_not_evaluable: int = 0


# ---------------------------------------------------------------------------
# Comparison engine
# ---------------------------------------------------------------------------

class ParallelComparisonEngine:
    """Runs legacy and compiled scoring side by side.

    Usage:
        engine = ParallelComparisonEngine(briefing)
        comparison = engine.compare(artifact, legacy_result)
    """

    def __init__(self, briefing: BriefingPacket):
        self._briefing = briefing
        self._registry = build_full_registry()
        self._evaluator = CompiledActivationEvaluator(
            briefing, registry=self._registry,
        )

    def compare(
        self,
        artifact: CompiledActivationArtifact,
        legacy_result: ActivationResult,
    ) -> TheoryComparison:
        """Compare compiled artifact evaluation against legacy result."""
        theory_id = artifact.source.theory_id
        compiled_result = self._evaluator.evaluate(artifact)

        tc = TheoryComparison(theory_id=theory_id)

        # Map legacy indicator results for lookup
        legacy_indicators = legacy_result.indicator_results or {}
        legacy_skipped = set(legacy_result.skipped_indicators or [])

        # Compare each phase
        for phase in artifact.phases:
            phase_id = phase.phase_id
            compiled_phase = compiled_result.phase_results.get(phase_id)
            if not compiled_phase:
                continue

            # Get legacy scores for this phase
            if legacy_result.is_two_phase:
                legacy_score = (legacy_result.phase_scores or {}).get(
                    phase.phase_label, 0.0
                )
                legacy_tier_val = (legacy_result.phase_tiers or {}).get(
                    phase.phase_label
                )
                legacy_tier = legacy_tier_val.value if legacy_tier_val else "inactive"
            else:
                legacy_score = legacy_result.score or 0.0
                legacy_tier = legacy_result.tier.value if legacy_result.tier else "inactive"

            pc = PhaseComparison(
                phase_id=phase_id,
                phase_label=phase.phase_label,
                compiled_score=round(compiled_phase.score, 4),
                legacy_score=round(legacy_score, 4),
                compiled_tier=compiled_phase.tier.value,
                legacy_tier=legacy_tier.lower() if isinstance(legacy_tier, str) else legacy_tier,
                tier_match=(compiled_phase.tier.value == (legacy_tier.lower() if isinstance(legacy_tier, str) else legacy_tier)),
                score_delta=round(compiled_phase.score - legacy_score, 4),
            )

            # Compare each indicator
            for ind_result in compiled_phase.indicators:
                ic = self._compare_indicator(
                    ind_result, phase_id, legacy_indicators, legacy_skipped,
                )
                pc.indicators.append(ic)

                if ic.status == "MATCH":
                    pc.match_count += 1
                elif ic.status == "MISMATCH":
                    pc.mismatch_count += 1
                elif ic.status == "NOT_EVALUABLE":
                    pc.not_evaluable_count += 1
                elif ic.status == "NOT_IN_LEGACY":
                    pc.not_in_legacy_count += 1
                elif ic.status == "LEGACY_SKIPPED":
                    pc.legacy_skipped_count += 1

            tc.phases.append(pc)

        # Effective tier comparison
        tc.compiled_effective_tier = compiled_result.effective_tier.value
        if legacy_result.is_two_phase:
            raw = (legacy_result.effective_tier.value
                   if legacy_result.effective_tier else "inactive")
        else:
            raw = (legacy_result.tier.value if legacy_result.tier else "inactive")
        tc.legacy_effective_tier = raw.lower() if isinstance(raw, str) else raw
        tc.tier_match = (tc.compiled_effective_tier == tc.legacy_effective_tier)
        tc.total_matches = sum(p.match_count for p in tc.phases)
        tc.total_mismatches = sum(p.mismatch_count for p in tc.phases)
        tc.total_not_evaluable = sum(p.not_evaluable_count for p in tc.phases)

        return tc

    def _compare_indicator(
        self,
        ind_result: IndicatorResult,
        phase_id: str,
        legacy_indicators: dict,
        legacy_skipped: set,
    ) -> IndicatorComparison:
        """Compare a single indicator's compiled vs legacy result."""
        ic = IndicatorComparison(
            indicator_id=ind_result.indicator_id,
            display_name=ind_result.display_name,
            phase_id=phase_id,
            compiled_outcome=ind_result.outcome.value,
            compiled_value=ind_result.value,
            compiled_threshold=ind_result.threshold,
            compiled_detail=ind_result.detail,
            compiled_in_denominator=ind_result.in_denominator,
        )

        # Determine compiled trigger state
        if ind_result.outcome in (RuleOutcome.NOT_EVALUABLE, RuleOutcome.ERROR):
            ic.compiled_triggered = None
        else:
            ic.compiled_triggered = ind_result.triggered

        # Find legacy match — try display_name first, then indicator_id
        legacy = legacy_indicators.get(ind_result.display_name)
        if legacy is None:
            legacy = legacy_indicators.get(ind_result.indicator_id)

        # Also try fuzzy matching on indicator names
        if legacy is None:
            for leg_name, leg_data in legacy_indicators.items():
                if _names_match(ind_result.display_name, leg_name):
                    legacy = leg_data
                    break

        if legacy is None:
            if ind_result.display_name in legacy_skipped or ind_result.indicator_id in legacy_skipped:
                ic.legacy_skipped = True
                ic.status = "LEGACY_SKIPPED"
            else:
                ic.status = "NOT_IN_LEGACY"
            return ic

        ic.legacy_triggered = legacy.get("triggered", False)
        ic.legacy_value = legacy.get("value")
        ic.legacy_threshold = legacy.get("threshold")

        # Compare
        if ic.compiled_triggered is None:
            ic.status = "NOT_EVALUABLE"
        elif ic.compiled_triggered == ic.legacy_triggered:
            ic.status = "MATCH"
        else:
            ic.status = "MISMATCH"

        return ic


def _names_match(name_a: str, name_b: str) -> bool:
    """Fuzzy match indicator names (case-insensitive, ignore punctuation)."""
    import re
    def normalize(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())
    return normalize(name_a) == normalize(name_b)


# ---------------------------------------------------------------------------
# Convenience: run full parallel comparison for all theories
# ---------------------------------------------------------------------------

def run_parallel_comparison(
    artifacts: dict[str, CompiledActivationArtifact],
    briefing: BriefingPacket,
    legacy_results: dict[str, ActivationResult],
) -> dict[str, TheoryComparison]:
    """Run parallel comparison for all theories."""
    engine = ParallelComparisonEngine(briefing)
    comparisons = {}
    for theory_id, artifact in artifacts.items():
        legacy = legacy_results.get(theory_id)
        if legacy is None:
            continue
        comparisons[theory_id] = engine.compare(artifact, legacy)
    return comparisons
