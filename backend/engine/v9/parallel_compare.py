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

        # Find legacy match using explicit name mapping, then fallbacks
        legacy = None

        # 1. Try explicit mapping first (authoritative)
        mapped_names = INDICATOR_NAME_MAP.get(ind_result.indicator_id, [])
        for mapped_name in mapped_names:
            legacy = legacy_indicators.get(mapped_name)
            if legacy is not None:
                break

        # 2. Try display_name and indicator_id directly
        if legacy is None:
            legacy = legacy_indicators.get(ind_result.display_name)
        if legacy is None:
            legacy = legacy_indicators.get(ind_result.indicator_id)

        # 3. Try fuzzy matching as last resort
        if legacy is None:
            for leg_name, leg_data in legacy_indicators.items():
                if _names_match(ind_result.display_name, leg_name):
                    legacy = leg_data
                    break

        if legacy is None:
            # Check if skipped — try mapped names + display_name + id
            all_names_to_check = (
                mapped_names
                + [ind_result.display_name, ind_result.indicator_id]
            )
            is_skipped = any(
                any(sn.startswith(n) or n in sn for sn in legacy_skipped)
                for n in all_names_to_check
            )
            if is_skipped:
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
# Explicit indicator name mapping: compiled indicator_id → legacy name(s)
# ---------------------------------------------------------------------------
# The compiled artifacts use clean snake_case indicator_ids.
# The legacy engine uses display names from the theory module markdown.
# These are often different strings, so we need an explicit mapping to
# avoid false NOT_IN_LEGACY classifications.

INDICATOR_NAME_MAP: dict[str, list[str]] = {
    # --- valuation_mean_reversion ---
    "erp_compressed": ["Equity risk premium compressed"],
    "cape_elevated": ["Shiller CAPE elevated"],
    "buffett_extreme": ["Buffett Indicator extreme"],
    "cash_yield_exceeds_equity": [
        "Short-term cash yield exceeds equity earnings yield",
        "Cash yield exceeds equity yield",
    ],
    "profit_margins_elevated": [
        "Corporate profit margins at cycle highs",
        "Corporate profit margins elevated",
    ],
    "breadth_narrow": ["Market breadth narrow"],
    "insider_selling": ["Insider selling elevated"],

    # --- debt_cycle_short (expansion) ---
    "exp_ism_above_contraction": ["ISM proxy above contraction"],
    "exp_unemployment_low": ["Unemployment low or falling"],
    "exp_credit_spreads_tight": ["Credit spreads tight or tightening"],
    "exp_curve_not_inverted": [
        "Yield curve not deeply inverted",
        "Yield curve not inverted",
    ],
    "exp_initial_claims_low": ["Initial claims low"],
    "exp_fed_funds_below_gdp": ["Fed funds below nominal GDP growth"],
    "exp_net_credit_growth": ["Net credit growth positive"],
    "exp_consumer_confidence": [
        "Consumer/business confidence",
        "Consumer confidence",
    ],

    # --- debt_cycle_short (contraction) ---
    "con_ism_below_contraction": ["ISM proxy below contraction"],
    "con_sahm_rule": ["Unemployment rising (Sahm Rule)"],
    "con_credit_spreads_widening": ["Credit spreads widening sharply"],
    "con_curve_resteepening": [
        "Yield curve re-steepening from deep inversion",
        "Yield curve re-steepening",
    ],
    "con_initial_claims_rising": ["Initial claims rising"],
    "con_fed_funds_above_gdp": ["Fed funds above nominal GDP growth"],
    "con_sloos_tightening": ["SLOOS showing broad tightening"],

    # --- debt_cycle_long ---
    "total_debt_gdp_elevated": [
        "Total debt / GDP above historical warning level",
        "Total debt/GDP above warning level",
    ],
    "fed_bs_gdp_elevated": [
        "Fed balance sheet / GDP elevated",
        "Fed balance sheet/GDP elevated",
    ],
    "rates_near_elb": [
        "Rates at or near effective lower bound within recent memory",
        "Rates at/near effective lower bound in recent memory",
        "Rates at/near ELB",
    ],
    "fiscal_deficit_primary_driver": [
        "Fiscal deficit as primary growth driver",
        "Deficit as primary growth driver",
    ],
    "wealth_inequality_extreme": [
        "Wealth inequality at cycle-characteristic extremes",
        "Wealth inequality at extremes",
    ],
    "negative_real_rates": [
        "Negative real rates during expansion",
        "Negative real rates",
    ],

    # --- structural_fragility (building) ---
    "bld_vix_low": ["Implied vol level"],
    "bld_vol_gap": ["Implied-realized vol gap"],
    "bld_hy_spread_tight": ["High-yield spread"],
    "bld_top10_concentration": ["Top-10 index concentration"],
    "bld_capex_mismatch": ["Capex/revenue mismatch"],
    "bld_margin_debt_high": ["Margin debt"],
    "bld_large_small_divergence": ["Large-cap/small-cap divergence"],
    "bld_passive_share": ["Passive fund share"],

    # --- structural_fragility (resolving) ---
    "res_vix_elevated": ["Implied vol level"],
    "res_hy_spread_wide": ["High-yield spread"],
    "res_drawdown_deep": ["Drawdown depth"],
    "res_cape_compressed": ["Valuation compression"],

    # --- fiscal_dominance_arithmetic ---
    "interest_receipts_ratio": ["Interest expense / tax receipts ratio"],
    "interest_exceeds_defense": [
        "Interest expense exceeds major discretionary category",
    ],
    "deficit_pace_outside_recession": ["Deficit pace outside recession"],
    "debt_rollover_higher_rates": ["Debt rollover at higher rates"],
    "gold_oil_ratio_elevated": ["Gold/oil ratio elevated"],
    "cb_gold_purchases": ["Central bank gold purchases sustained"],

    # --- fiscal_dominance_liquidity ---
    "net_liquidity_expanding": ["Net liquidity expanding"],
    "deficit_pace_elevated": ["Deficit pace"],
    "rate_hikes_no_recession": [
        "Rate hikes not producing recession",
        "Rate hikes without recession",
    ],
    "hard_assets_outperforming": [
        "Hard assets outperforming nominal bonds",
        "Hard assets outperforming",
    ],
    "rrp_draining": [
        "RRP draining toward zero",
        "RRP draining",
    ],
    "fed_bs_inconsistent": [
        "Fed balance sheet direction inconsistent with stated policy",
        "Fed BS inconsistent with announced QT pace",
    ],
    "tga_spending": [
        "TGA behavior consistent with spending",
        "TGA spending behavior",
    ],

    # --- capital_flows (accumulation) ---
    "acc_em_dm_pe_gap": [
        "EM vs. DM PE gap at extremes",
        "EM vs. DM valuation gap",
    ],
    "acc_em_3yr_underperformance": [
        "EM rolling 3-year underperformance",
        "EM 3-year cumulative underperformance",
    ],
    "acc_dollar_strong": [
        "Dollar strong or sideways",
        "Dollar strength/stability",
    ],
    "acc_china_credit_flat": [
        "China credit impulse flat or negative",
        "China credit impulse flat/negative",
    ],

    # --- capital_flows (rotation) ---
    "rot_dollar_weakening": ["Dollar weakening"],
    "rot_china_credit_positive": [
        "China credit impulse positive and accelerating",
        "China credit impulse positive and rising",
    ],
    "rot_rmb_strengthening": [
        "RMB strengthening",
        "RMB/CNH strengthening vs USD",
    ],
    "rot_em_outperforming": [
        "EM outperforming DM on relative basis",
        "EM outperforming DM",
    ],
    "rot_commodity_prices_rising": [
        "Commodity prices rising",
        "Broad commodity prices rising",
    ],
    "rot_chinese_equities_leading": [
        "Chinese equities leading",
        "Chinese equities leading rotation",
    ],

    # --- monetary_architecture ---
    "cb_gold_sustained": [
        "Central bank gold purchases sustained at elevated levels",
        "Central bank gold purchases sustained",
    ],
    "foreign_treasury_declining": [
        "Foreign official Treasury holdings declining as share of outstanding",
        "Foreign official Treasury holdings declining",
    ],
    "gold_oil_elevated_rising": [
        "Gold/oil ratio elevated and rising",
        "Gold/oil elevated and rising",
    ],
    "ccbs_stress": [
        "Cross-currency basis swap stress",
        "Cross-border funding stress",
    ],
    "non_dollar_settlement": [
        "Non-dollar trade settlement rising",
        "Non-dollar settlement share rising",
    ],
}


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
