"""v9 Phase 2: Semantic diff — classify every mismatch between compiled and legacy.

This is the key Phase 2 deliverable. Every difference between compiled and legacy
scoring is classified into one of:
  - expected_parity: both agree, as expected
  - justified_improvement: compiled is correct where legacy was wrong
  - compiler_issue: the compiler made an error
  - field_metadata_issue: field registration or unit metadata problem
  - data_infra_limitation: briefing packet lacks required data
  - needs_human_review: cannot be auto-classified

The known mismatch inventory from spike/Phase 1 docs is explicitly handled:
  - valuation_mean_reversion OR-condition improvement
  - initial_claims count vs thousands normalization
  - fed_funds vs GDP field-comparison issue
  - debt_cycle_long wealth inequality legacy extraction bug
  - structural_fragility VIX field-resolution issue
  - capital_flows eem_spy_3y_relative legacy sign bug
  - monetary_architecture missing-data / time-series structure

Depends on: parallel_compare.py
Depended on by: scripts/v9_phase2_compile.py, docs/V9_PHASE2_SEMANTIC_DIFF.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from backend.engine.v9.parallel_compare import (
    IndicatorComparison,
    PhaseComparison,
    TheoryComparison,
)


# ---------------------------------------------------------------------------
# Classification taxonomy
# ---------------------------------------------------------------------------

class MismatchClass(str, Enum):
    """Classification of a compiled-vs-legacy difference."""
    EXPECTED_PARITY = "expected_parity"
    COINCIDENTAL_PARITY = "coincidental_parity"  # same boolean, but legacy is right for wrong reason
    JUSTIFIED_IMPROVEMENT = "justified_improvement"
    COMPILER_ISSUE = "compiler_issue"
    FIELD_METADATA_ISSUE = "field_metadata_issue"
    DATA_INFRA_LIMITATION = "data_infra_limitation"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


# ---------------------------------------------------------------------------
# Diff entry
# ---------------------------------------------------------------------------

@dataclass
class SemanticDiffEntry:
    """A single classified difference between compiled and legacy."""
    theory_id: str
    phase_id: str
    indicator_id: str
    display_name: str
    status: str              # MATCH, MISMATCH, NOT_EVALUABLE, etc.
    classification: MismatchClass = MismatchClass.NEEDS_HUMAN_REVIEW
    compiled_triggered: Optional[bool] = None
    legacy_triggered: Optional[bool] = None
    compiled_value: Optional[float] = None
    legacy_value: Optional[float] = None
    explanation: str = ""
    spike_reference: str = ""  # link to spike doc finding if known


@dataclass
class TheoryDiffReport:
    """Semantic diff report for one theory."""
    theory_id: str
    entries: list[SemanticDiffEntry] = field(default_factory=list)
    compiled_tier: str = ""
    legacy_tier: str = ""
    tier_match: bool = True
    # Phase-level summaries
    phase_diffs: dict[str, dict] = field(default_factory=dict)

    @property
    def mismatch_count(self) -> int:
        return sum(1 for e in self.entries if e.status == "MISMATCH")

    @property
    def justified_count(self) -> int:
        return sum(1 for e in self.entries
                   if e.classification == MismatchClass.JUSTIFIED_IMPROVEMENT)

    @property
    def needs_review_count(self) -> int:
        return sum(1 for e in self.entries
                   if e.classification == MismatchClass.NEEDS_HUMAN_REVIEW)


@dataclass
class FullSemanticDiff:
    """Complete semantic diff across all theories."""
    theories: dict[str, TheoryDiffReport] = field(default_factory=dict)

    @property
    def total_indicators(self) -> int:
        return sum(len(r.entries) for r in self.theories.values())

    @property
    def total_mismatches(self) -> int:
        return sum(r.mismatch_count for r in self.theories.values())

    @property
    def total_coincidental(self) -> int:
        return sum(
            sum(1 for e in r.entries if e.classification == MismatchClass.COINCIDENTAL_PARITY)
            for r in self.theories.values()
        )

    @property
    def total_justified(self) -> int:
        return sum(r.justified_count for r in self.theories.values())

    @property
    def total_needs_review(self) -> int:
        return sum(r.needs_review_count for r in self.theories.values())

    @property
    def tier_matches(self) -> int:
        count = 0
        for r in self.theories.values():
            for pd in r.phase_diffs.values():
                if pd.get("tier_match"):
                    count += 1
        return count

    @property
    def tier_total(self) -> int:
        return sum(len(r.phase_diffs) for r in self.theories.values())


# ---------------------------------------------------------------------------
# Known mismatch rules — from spike and Phase 1 docs
# ---------------------------------------------------------------------------

# These rules auto-classify known mismatches. Keyed by
# (theory_id, indicator_id) or (theory_id, indicator_id_pattern).
KNOWN_CLASSIFICATIONS: dict[tuple[str, str], tuple[MismatchClass, str, str]] = {
    # valuation_mean_reversion: OR condition
    ("valuation_mean_reversion", "profit_margins_elevated"): (
        MismatchClass.JUSTIFIED_IMPROVEMENT,
        "Compiled correctly handles OR condition (net margin > 12% OR profits/GDP > 10%); "
        "legacy only checks first sub-condition",
        "V9_HAIKU_COMPILER_SPIKE_RESULTS.md Section 5",
    ),

    # debt_cycle_short: initial_claims unit normalization
    ("debt_cycle_short", "exp_initial_claims_low"): (
        MismatchClass.JUSTIFIED_IMPROVEMENT,
        "Compiled declares unit=THOUSANDS for threshold, field=COUNT for briefing value. "
        "Phase 1 runtime normalizes correctly (250K = 250000). Legacy compares raw 202000 < 250.",
        "V9_HAIKU_COMPILER_SPIKE_RESULTS.md Section 4, Change 1",
    ),

    # debt_cycle_short: fed funds vs GDP field comparison
    ("debt_cycle_short", "exp_fed_funds_below_gdp"): (
        MismatchClass.JUSTIFIED_IMPROVEMENT,
        "Compiled correctly identifies as field_comparison (fed_funds vs nominal_gdp_growth). "
        "Legacy treats as scalar and extracts garbage number from GDP level ($31442B).",
        "V9_HAIKU_COMPILER_SPIKE_RESULTS.md Section 5",
    ),

    # debt_cycle_short: contraction fed funds above GDP
    ("debt_cycle_short", "con_fed_funds_above_gdp"): (
        MismatchClass.JUSTIFIED_IMPROVEMENT,
        "Compiled correctly uses field_comparison + persistence. Legacy extracts GDP level "
        "as threshold (31442 > 1), trivially triggering.",
        "V9_HAIKU_COMPILER_SPIKE_RESULTS.md Section 5",
    ),

    # debt_cycle_long: wealth inequality
    ("debt_cycle_long", "wealth_inequality_extreme"): (
        MismatchClass.JUSTIFIED_IMPROVEMENT,
        "Compiled uses correct threshold (top10_wealth_share > 70%). Legacy extracts '10' "
        "from prose, checking 68.1 > 10 = True (wrong).",
        "V9_SPIKE_FULL_COMPILATION_RESULTS.md Section 2",
    ),

    # structural_fragility: VIX field resolution
    ("structural_fragility", "bld_vix_low"): (
        MismatchClass.JUSTIFIED_IMPROVEMENT,
        "Phase 2 correctly maps to ^VIX (23.87); spike incorrectly mapped to "
        "vix_vs_realized (4.86). Fixed VIX field resolution gap.",
        "V9_SPIKE_FULL_COMPILATION_RESULTS.md Finding 1",
    ),

    # capital_flows: eem_spy_3y_relative sign bug
    ("capital_flows", "acc_em_3yr_underperformance"): (
        MismatchClass.JUSTIFIED_IMPROVEMENT,
        "Compiled correctly checks eem_spy_3y_relative < -30 (EM must underperform by 30%+). "
        "Value 9.5 > -30 = False (correct: EM is outperforming). Legacy strips sign from "
        "threshold, checking 9.5 < 30 = True (wrong).",
        "V9_PHASE1_RUNTIME_RESULTS.md Section 3",
    ),

    # debt_cycle_short: net credit growth blocked
    ("debt_cycle_short", "exp_net_credit_growth"): (
        MismatchClass.DATA_INFRA_LIMITATION,
        "loan_growth_yoy field not available in briefing packet.",
        "V9_HAIKU_COMPILER_SPIKE_RESULTS.md Section 3",
    ),

    # structural_fragility: capex/revenue blocked
    ("structural_fragility", "bld_capex_mismatch"): (
        MismatchClass.DATA_INFRA_LIMITATION,
        "Qualitative/thematic indicator; no mechanical threshold possible.",
        "V9_SPIKE_FULL_COMPILATION_RESULTS.md Section 5",
    ),

    # monetary_architecture: CCBS blocked
    ("monetary_architecture", "ccbs_stress"): (
        MismatchClass.DATA_INFRA_LIMITATION,
        "4 cross-currency basis swap fields not in briefing packet.",
        "V9_SPIKE_FULL_COMPILATION_RESULTS.md Finding 5",
    ),

    # monetary_architecture: non-dollar settlement partially blocked
    ("monetary_architecture", "non_dollar_settlement"): (
        MismatchClass.DATA_INFRA_LIMITATION,
        "non_dollar_energy_settlement_volume not in briefing; "
        "rmb_swift_share branch evaluable.",
        "V9_SPIKE_FULL_COMPILATION_RESULTS.md Section 5",
    ),

    # Resolving VIX — same fix as building
    ("structural_fragility", "res_vix_elevated"): (
        MismatchClass.COINCIDENTAL_PARITY,
        "Both False, but legacy uses BUILDING threshold (Below 14) for RESOLVING indicator. "
        "Compiled correctly uses resolving threshold (Above 30). "
        "Coincidence: 23.87 fails both checks.",
        "V9_SPIKE_FULL_COMPILATION_RESULTS.md Finding 1",
    ),

    # structural_fragility resolving HY spread — wrong-phase threshold
    ("structural_fragility", "res_hy_spread_wide"): (
        MismatchClass.COINCIDENTAL_PARITY,
        "Both False, but legacy uses BUILDING threshold (Below 300bp) for RESOLVING indicator. "
        "Compiled correctly uses resolving threshold (Above 600bp). "
        "Coincidence: 317bp fails both checks.",
        "",
    ),

    # debt_cycle_long: fiscal deficit resolves to wrong field
    ("debt_cycle_long", "fiscal_deficit_primary_driver"): (
        MismatchClass.COINCIDENTAL_PARITY,
        "Both True, but legacy resolves to interest_exceeds_defense (287.0) instead of "
        "deficit_pct_gdp (11.74). Legacy checks 287 > extracted '5' = True. "
        "Compiled checks deficit_pct_gdp(11.74) > 5.0 AND unemployment(4.3) < 7.0 = True. "
        "Right answer for wrong field.",
        "",
    ),

    # debt_cycle_short: fed funds below GDP — legacy can't evaluate, defaults to False
    ("debt_cycle_short", "exp_fed_funds_below_gdp"): (
        MismatchClass.COINCIDENTAL_PARITY,
        "Both False, but legacy cannot mechanically evaluate field comparison "
        "(value=31442 = GDP level, not growth rate). Legacy defaults to False. "
        "Compiled correctly computes: fed_funds(3.64) lt nominal_gdp_growth(3.31) = False.",
        "V9_HAIKU_COMPILER_SPIKE_RESULTS.md Section 5",
    ),
}


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify_comparison(
    comparison: TheoryComparison,
) -> TheoryDiffReport:
    """Classify all indicator comparisons for a single theory."""
    report = TheoryDiffReport(
        theory_id=comparison.theory_id,
        compiled_tier=comparison.compiled_effective_tier,
        legacy_tier=comparison.legacy_effective_tier,
        tier_match=comparison.tier_match,
    )

    for phase in comparison.phases:
        report.phase_diffs[phase.phase_id] = {
            "phase_label": phase.phase_label,
            "compiled_score": phase.compiled_score,
            "legacy_score": phase.legacy_score,
            "compiled_tier": phase.compiled_tier,
            "legacy_tier": phase.legacy_tier,
            "tier_match": phase.tier_match,
            "score_delta": phase.score_delta,
        }

        for ic in phase.indicators:
            entry = _classify_indicator(
                comparison.theory_id, phase.phase_id, ic,
            )
            report.entries.append(entry)

    return report


def _classify_indicator(
    theory_id: str,
    phase_id: str,
    ic: IndicatorComparison,
) -> SemanticDiffEntry:
    """Classify a single indicator comparison."""
    entry = SemanticDiffEntry(
        theory_id=theory_id,
        phase_id=phase_id,
        indicator_id=ic.indicator_id,
        display_name=ic.display_name,
        status=ic.status,
        compiled_triggered=ic.compiled_triggered,
        legacy_triggered=ic.legacy_triggered,
        compiled_value=ic.compiled_value,
        legacy_value=ic.legacy_value,
    )

    # Check known classifications first
    key = (theory_id, ic.indicator_id)
    if key in KNOWN_CLASSIFICATIONS:
        cls, explanation, ref = KNOWN_CLASSIFICATIONS[key]
        entry.classification = cls
        entry.explanation = explanation
        entry.spike_reference = ref
        return entry

    # Auto-classify based on status
    if ic.status == "MATCH":
        entry.classification = MismatchClass.EXPECTED_PARITY
        entry.explanation = "Both agree on trigger state"
    elif ic.status == "NOT_EVALUABLE":
        # Check if it's time-series related
        if "series" in (ic.compiled_detail or "").lower() or \
           "time" in (ic.compiled_detail or "").lower() or \
           "trend" in (ic.compiled_detail or "").lower() or \
           "persistence" in (ic.compiled_detail or "").lower():
            entry.classification = MismatchClass.DATA_INFRA_LIMITATION
            entry.explanation = (
                "Requires time-series data not available in snapshot briefing"
            )
        else:
            entry.classification = MismatchClass.DATA_INFRA_LIMITATION
            entry.explanation = f"Not evaluable: {ic.compiled_detail}"
    elif ic.status == "NOT_IN_LEGACY":
        entry.classification = MismatchClass.DATA_INFRA_LIMITATION
        entry.explanation = "Indicator not scored by legacy engine"
    elif ic.status == "LEGACY_SKIPPED":
        entry.classification = MismatchClass.DATA_INFRA_LIMITATION
        entry.explanation = "Legacy engine skipped this indicator (web-search or qualitative)"
    elif ic.status == "MISMATCH":
        # Try to auto-classify known patterns
        entry.classification = _auto_classify_mismatch(theory_id, ic)
        if entry.classification == MismatchClass.NEEDS_HUMAN_REVIEW:
            entry.explanation = (
                f"Trigger disagreement: compiled={ic.compiled_triggered}, "
                f"legacy={ic.legacy_triggered}. Needs manual review."
            )
    else:
        entry.classification = MismatchClass.NEEDS_HUMAN_REVIEW

    return entry


def _auto_classify_mismatch(
    theory_id: str,
    ic: IndicatorComparison,
) -> MismatchClass:
    """Try to auto-classify an unknown mismatch."""
    # If compiled has UNRESOLVED field, it's a field metadata issue
    if ic.indicator_id and "UNRESOLVED" in ic.indicator_id:
        return MismatchClass.FIELD_METADATA_ISSUE

    # If compiled triggered and legacy didn't, check for OR/compound improvements
    if ic.compiled_triggered and not ic.legacy_triggered:
        # Could be a genuine improvement (e.g., OR condition now evaluable)
        return MismatchClass.NEEDS_HUMAN_REVIEW

    # If legacy triggered and compiled didn't, could be legacy extraction bug
    if not ic.compiled_triggered and ic.legacy_triggered:
        return MismatchClass.NEEDS_HUMAN_REVIEW

    return MismatchClass.NEEDS_HUMAN_REVIEW


# ---------------------------------------------------------------------------
# Full diff report
# ---------------------------------------------------------------------------

def generate_full_diff(
    comparisons: dict[str, TheoryComparison],
) -> FullSemanticDiff:
    """Generate the complete semantic diff across all theories."""
    diff = FullSemanticDiff()
    for theory_id, comparison in comparisons.items():
        diff.theories[theory_id] = classify_comparison(comparison)
    return diff


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_diff_report(diff: FullSemanticDiff) -> str:
    """Render the semantic diff as a reviewable markdown report."""
    lines = [
        "# V9 Phase 2: Semantic Diff Report",
        "",
        f"*Total indicators: {diff.total_indicators}*",
        f"*Mismatches: {diff.total_mismatches}*",
        f"*Justified improvements: {diff.total_justified}*",
        f"*Needs human review: {diff.total_needs_review}*",
        f"*Phase/tier matches: {diff.tier_matches}/{diff.tier_total}*",
        "",
        "---",
        "",
    ]

    for theory_id, report in diff.theories.items():
        lines.append(f"## {theory_id}")
        lines.append("")
        lines.append(f"**Effective tier:** compiled={report.compiled_tier}, "
                      f"legacy={report.legacy_tier} "
                      f"({'MATCH' if report.tier_match else 'MISMATCH'})")
        lines.append("")

        # Phase summaries
        for phase_id, pd in report.phase_diffs.items():
            lines.append(f"### {pd['phase_label']} ({phase_id})")
            lines.append("")
            lines.append(f"| Metric | Compiled | Legacy | Delta |")
            lines.append(f"|--------|----------|--------|-------|")
            lines.append(f"| Score | {pd['compiled_score']:.4f} | "
                          f"{pd['legacy_score']:.4f} | "
                          f"{pd['score_delta']:+.4f} |")
            lines.append(f"| Tier | {pd['compiled_tier']} | "
                          f"{pd['legacy_tier']} | "
                          f"{'MATCH' if pd['tier_match'] else 'MISMATCH'} |")
            lines.append("")

        # Indicator details
        lines.append("### Indicator Details")
        lines.append("")
        lines.append("| Indicator | Status | Classification | Compiled | Legacy | Explanation |")
        lines.append("|-----------|--------|----------------|----------|--------|-------------|")

        for entry in report.entries:
            c_str = str(entry.compiled_triggered) if entry.compiled_triggered is not None else "N/A"
            l_str = str(entry.legacy_triggered) if entry.legacy_triggered is not None else "N/A"
            expl = entry.explanation[:80] + "..." if len(entry.explanation) > 80 else entry.explanation
            lines.append(
                f"| {entry.display_name} | {entry.status} | "
                f"{entry.classification.value} | {c_str} | {l_str} | {expl} |"
            )

        lines.append("")
        lines.append("---")
        lines.append("")

    # Summary: items needing human review
    review_items = []
    for report in diff.theories.values():
        for entry in report.entries:
            if entry.classification == MismatchClass.NEEDS_HUMAN_REVIEW:
                review_items.append(entry)

    if review_items:
        lines.append("## Items Requiring Human Review")
        lines.append("")
        for item in review_items:
            lines.append(f"- **{item.theory_id}/{item.indicator_id}**: "
                          f"{item.explanation}")
        lines.append("")

    # Summary: coincidental parity (right answer, wrong reason)
    coincidental = []
    for report in diff.theories.values():
        for entry in report.entries:
            if entry.classification == MismatchClass.COINCIDENTAL_PARITY:
                coincidental.append(entry)

    if coincidental:
        lines.append("## Coincidental Parity (Right Answer, Wrong Reason)")
        lines.append("")
        lines.append("These indicators show the same boolean result but the legacy path")
        lines.append("arrives at it by accident (wrong field, wrong threshold, or default).")
        lines.append("")
        for item in coincidental:
            lines.append(f"- **{item.theory_id}/{item.indicator_id}**: "
                          f"{item.explanation}")
        lines.append("")

    # Summary: justified improvements
    justified = []
    for report in diff.theories.values():
        for entry in report.entries:
            if entry.classification == MismatchClass.JUSTIFIED_IMPROVEMENT:
                justified.append(entry)

    if justified:
        lines.append("## Justified Improvements Over Legacy")
        lines.append("")
        for item in justified:
            lines.append(f"- **{item.theory_id}/{item.indicator_id}**: "
                          f"{item.explanation}")
        lines.append("")

    return "\n".join(lines)
