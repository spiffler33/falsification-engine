# prompt_builder.py -- Build generation and elimination prompts.
# Depends on: schemas/theory.py, schemas/briefing.py, engine/theory_parser.py, engine/activation.py
# Depended on by: api/pipeline.py
#
# The prompts are the interface between the mechanical system and the LLM.
# They include full theory module text (not just structured data), the briefing
# packet, and queued inbox items. Output specifies the exact JSON schema the
# output_parser expects.
from __future__ import annotations

import json
from typing import Any

from backend.schemas.theory import ActivationResult, ActivationTier, TheoryModule


THEORY_LABEL_MAP = {
    "valuation_mean_reversion": "Valuation Mean Reversion",
    "debt_cycle_short": "Debt Cycle (Short)",
    "debt_cycle_long": "Debt Cycle (Long)",
    "structural_fragility": "Structural Fragility",
    "fiscal_dominance_liquidity": "Fiscal Dom. (Liquidity)",
    "fiscal_dominance_arithmetic": "Fiscal Dom. (Arithmetic)",
    "capital_flows": "Capital Flows",
    "monetary_architecture": "Monetary Architecture",
}


def build_generation_prompt(
    theories: list[TheoryModule],
    activation_results: list[ActivationResult],
    briefing: dict[str, Any],
    inbox_items: list[dict[str, Any]],
    max_adjacent: int = 1,
    active_regime_flags: list[dict[str, Any]] | None = None,
) -> str:
    """Build the generation prompt for Pass 2.

    Includes Active theories (full markdown), up to 1 Adjacent wildcard,
    the briefing packet, and queued inbox items.
    """
    active_theories = []
    adjacent_theories = []
    activation_map = {}

    for ar in activation_results:
        tier = ar.tier if not ar.is_two_phase else ar.effective_tier
        activation_map[ar.theory_id] = ar
        if tier == ActivationTier.ACTIVE:
            active_theories.append(ar.theory_id)
        elif tier == ActivationTier.ADJACENT:
            adjacent_theories.append(ar.theory_id)

    # Build theory lookup
    theory_map = {t.theory_id: t for t in theories}

    # --- System instructions ---
    parts = []
    parts.append(_generation_system_instructions())

    # --- Active theories ---
    parts.append("\n\n## ACTIVE THEORIES\n")
    for tid in active_theories:
        t = theory_map.get(tid)
        ar = activation_map.get(tid)
        if t:
            score = ar.score if ar and not ar.is_two_phase else None
            phase = ar.effective_phase if ar and ar.is_two_phase else None
            phase_score = None
            if ar and ar.is_two_phase and ar.phase_scores and phase:
                phase_score = ar.phase_scores.get(phase)
            label = THEORY_LABEL_MAP.get(tid, tid)
            score_display = phase_score if phase_score is not None else (score if score is not None else 0)
            phase_display = f" (Phase: {phase})" if phase else ""
            parts.append(f"\n### {label}{phase_display} -- Activation: {score_display:.0%}\n")
            parts.append(t.raw_markdown[:8000] if t.raw_markdown else f"[Theory module text for {tid}]")

    # --- Adjacent wildcard ---
    if adjacent_theories:
        selected = adjacent_theories[:max_adjacent]
        parts.append("\n\n## ADJACENT THEORY (WILDCARD -- use at most 1)\n")
        for tid in selected:
            t = theory_map.get(tid)
            ar = activation_map.get(tid)
            if t:
                label = THEORY_LABEL_MAP.get(tid, tid)
                parts.append(f"\n### {label}\n")
                parts.append(t.raw_markdown[:4000] if t.raw_markdown else f"[Theory module text for {tid}]")

    # --- Inbox items ---
    if inbox_items:
        parts.append("\n\n## INBOX ITEMS (new since last run)\n")
        for item in inbox_items:
            date = item.get("date", "")
            content = item.get("content", "")
            source = item.get("source", "")
            theories_tagged = item.get("theories", [])
            tags = f" [{', '.join(theories_tagged)}]" if theories_tagged else ""
            parts.append(f"- [{date}] {content}")
            if source:
                parts.append(f"  Source: {source}")
            if tags:
                parts.append(f"  Tags: {tags}")
            parts.append("")

    # --- Regime flags (Pass 1.5 context) ---
    if active_regime_flags:
        active_or_adjacent = set(active_theories + adjacent_theories[:max_adjacent])
        parts.append("\n\n## REGIME FLAGS\n")
        parts.append(
            "The following regime flags are active based on current theory activation states.\n"
            "Use the channel context below when constructing hypotheses for the affected theories.\n"
        )
        for flag in active_regime_flags:
            parts.append(f"REGIME FLAG: {flag['flag_id']}")
            parts.append(f"Triggered by: {flag['flag_id'].replace('_active', '').replace('_', ' ')} is Active\n")
            parts.append("Channel context for affected theories:")
            for module_id, context in flag.get("channel_context", {}).items():
                if module_id in active_or_adjacent:
                    label = THEORY_LABEL_MAP.get(module_id, module_id)
                    parts.append(f"  - {label}: {context}")
            parts.append("")

    # --- Resolution channel requirement ---
    parts.append("\n\n## RESOLUTION CHANNEL REQUIREMENT\n")
    parts.append(_resolution_channel_instructions())

    # --- Data briefing ---
    parts.append("\n\n## DATA BRIEFING\n")
    parts.append("```json")
    parts.append(json.dumps(briefing, indent=2, default=str))
    parts.append("```")

    # --- Output schema ---
    parts.append("\n\n## OUTPUT FORMAT\n")
    parts.append(_generation_output_schema())

    return "\n".join(parts)


def build_elimination_prompt(
    hypotheses: list[dict[str, Any]],
    theories: list[TheoryModule],
    activation_results: list[ActivationResult],
    briefing: dict[str, Any],
    has_channel_tags: bool = False,
    sector_appendices: list[dict[str, Any]] | None = None,
) -> str:
    """Build the elimination prompt for Pass 3.

    Includes the generated hypotheses, theory modules they invoke,
    and the current briefing packet.  When *sector_appendices* is a
    non-empty list the sector falsifier section and structured audit
    output format are appended; when empty or None they are omitted
    entirely — the prompt is unchanged from v3.
    """
    theory_map = {t.theory_id: t for t in theories}

    parts = []
    parts.append(_elimination_system_instructions())

    # --- Hypotheses to attack ---
    parts.append("\n\n## HYPOTHESES TO ATTACK\n")
    parts.append("```json")
    parts.append(json.dumps(hypotheses, indent=2, default=str))
    parts.append("```")

    # --- Relevant theory modules ---
    invoked_theories = set()
    for h in hypotheses:
        invoked_theories.add(h.get("source_theory", ""))
        for st in h.get("source_theories", []):
            invoked_theories.add(st)
    invoked_theories.discard("")

    parts.append("\n\n## THEORY MODULES (for falsifier reference)\n")
    for tid in sorted(invoked_theories):
        t = theory_map.get(tid)
        if t:
            label = THEORY_LABEL_MAP.get(tid, tid)
            parts.append(f"\n### {label}\n")
            # Include falsifier sections specifically
            parts.append(_extract_falsifier_section(t))

    # --- Activation state for cross-theory attacks ---
    parts.append("\n\n## CURRENT ACTIVATION STATE\n")
    for ar in activation_results:
        tier = ar.tier if not ar.is_two_phase else ar.effective_tier
        label = THEORY_LABEL_MAP.get(ar.theory_id, ar.theory_id)
        phase = f" ({ar.effective_phase})" if ar.is_two_phase and ar.effective_phase else ""
        parts.append(f"- {label}{phase}: {tier.value if tier else 'Unknown'}")

    # --- Data briefing ---
    parts.append("\n\n## DATA BRIEFING\n")
    parts.append("```json")
    parts.append(json.dumps(briefing, indent=2, default=str))
    parts.append("```")

    # --- Channel verification (when hypotheses have channel tags) ---
    if has_channel_tags:
        parts.append("\n\n## CHANNEL VERIFICATION\n")
        parts.append(_channel_verification_instructions())

    # --- Sector falsifier appendices (v4 — conditional on ticker match) ---
    if sector_appendices:
        parts.append("\n\n" + _format_sector_appendices_section(sector_appendices))

    # --- Output schema ---
    parts.append("\n\n## OUTPUT FORMAT\n")
    parts.append(_elimination_output_schema(
        has_channel_tags=has_channel_tags,
        has_sector_appendices=bool(sector_appendices),
    ))

    return "\n".join(parts)


def _generation_system_instructions() -> str:
    return """SYSTEM: You are the Generation Pass of a Falsification Engine for global macro analysis.

Your job is to generate testable hypotheses from the Active theory modules below, grounded in the current data briefing. Each hypothesis must trace to a specific causal mechanism in a specific theory module.

RULES:
1. Generate 2-4 hypotheses per Active theory.
2. You may generate 0-1 hypotheses from the Adjacent wildcard theory (if provided).
3. You may combine mechanisms from multiple Active theories into composite hypotheses -- but ONLY if the combination NARROWS the prediction and makes it MORE falsifiable.
4. Do NOT rank hypotheses by importance or recommend actions.
5. Do NOT produce hypotheses from theories not listed below.
6. Each prediction must be specific: include magnitude range, timeframe, and named ETF instruments.
7. Hard falsifiers must be specific enough to check against data.
8. Soft falsifiers must include severity (minor/medium/major) inherited from the source theory module.
9. Each hypothesis MUST include a PAYOFF_BAND block with magnitude_lower, magnitude_upper, and end_date (see OUTPUT FORMAT).

PAYOFF BAND RULES:
- magnitude_lower and magnitude_upper are the expected EXPRESSION-LEVEL return range, stated as positive decimals (e.g. 0.15 for 15%).
- For pair/spread hypotheses: the magnitude is the spread return, NOT a single-leg prediction. Example: "DBC outperforms QQQ by 15-30%" -> magnitude_lower: 0.15, magnitude_upper: 0.30.
- For single-leg hypotheses: the magnitude is the asset return, which equals the expression return. Example: "GLD +10-20%" -> magnitude_lower: 0.10, magnitude_upper: 0.20.
- Direction is already captured in asset_direction. Magnitudes are always POSITIVE -- they represent expected profitable return on the expression regardless of SHORT legs.
- magnitude_upper must not exceed 1.0 (100%). No liquid ETF hypothesis should predict a double within the holding window.
- end_date is YYYY-MM-DD format, must be in the future, within 12 months.

CONSOLIDATION CHECK: Before finalizing, review all generated hypotheses grouped by their primary SHORT or LONG asset. If 3+ hypotheses share the same directional bet on the same asset:
1. Identify whether they represent genuinely independent mechanisms or variations of the same view.
2. If variations: keep only the hypothesis with the most specific, falsifiable prediction and the clearest causal chain. Merge supporting evidence from the others into the survivor's rationale.
3. If genuinely independent: keep all but note the convergence explicitly.

The goal is that each surviving hypothesis represents a DISTINCT bet the operator could take or leave independently. If killing hypothesis A would not change your conviction on hypothesis B, they are independent. If it would, they are variations and should be consolidated."""


def _generation_output_schema() -> str:
    return """Output a JSON array of hypothesis objects. Each object must have exactly these fields:

```json
[
  {
    "theory_id": "fiscal_dominance_liquidity",
    "source_theories": ["fiscal_dominance_liquidity"],
    "short_name": "6-12 word summary of the hypothesis",
    "full_statement": "Complete mechanism chain, prediction, and timeframe as a paragraph",
    "mechanism": "The causal chain from the theory module",
    "prediction": "Specific, testable prediction with magnitude and timeframe",
    "predicted_assets": ["GLD", "TLT"],
    "asset_direction": {"GLD": "LONG", "TLT": "SHORT"},
    "resolution_channel": "one of: nominal_price_decline | inflationary_grind | real_asset_outperformance | sector_rotation | broad_credit_contraction | sector_credit_stress",
    "hard_falsifiers": [
      {"condition": "Description of what would kill this hypothesis", "metric": "data field to check", "threshold": "specific number or condition"}
    ],
    "soft_falsifiers": [
      {"name": "Short name", "severity": "minor|medium|major", "condition": "What would wound it", "metric": "data field", "threshold": "value"}
    ],
    "timeframe": "e.g. Through Q3 2026",
    "payoff_band": {
      "magnitude_lower": 0.15,
      "magnitude_upper": 0.30,
      "end_date": "2026-09-30"
    },
    "conviction_inputs": {
      "support_strength": 0.0,
      "evidence_quality": 0.0,
      "convergence": 0.0,
      "falsifier_clarity": 0.0,
      "horizon_alignment": 0.0,
      "expression_efficiency": 0.0
    }
  }
]
```

IMPORTANT: Output ONLY the JSON array. No commentary before or after."""


def _elimination_system_instructions() -> str:
    return """SYSTEM: You are the Elimination Pass of a Falsification Engine for global macro analysis.

Your ONLY job is to mechanically audit each hypothesis against its pre-registered falsifiers, then apply strict kill rules. You are a data checker, not an analyst.

## STAGE A -- FALSIFIER AUDIT (no discretion)

For each hypothesis, evaluate every pre-registered hard and soft falsifier against the current data briefing and your web search findings. For each falsifier, state:
(a) the exact condition
(b) the current data value or observation
(c) TRIGGERED, CLEAR, or UNTESTABLE

Status definitions:
- TRIGGERED: The data meets the stated condition.
- CLEAR: The data exists AND contradicts the stated condition. You must cite a specific current number or observation.
- UNTESTABLE: The data required to evaluate this condition is not available, not yet published, or would require forward-looking information you do not have.

CRITICAL: The default status is UNTESTABLE, not CLEAR. You must cite specific current data to justify a CLEAR status. If you cannot point to a concrete number or observation that contradicts the falsifier condition, the status is UNTESTABLE.

Do not infer CLEAR from price action or market performance unless the falsifier condition specifically references price action. Do not infer CLEAR from "it seems unlikely." Either you have the data or you do not.

## STAGE B -- KILL RULES (mechanical)

Apply these rules in strict order. Do not override with narrative judgment:
- ANY hard falsifier TRIGGERED -> status: KILLED
- 2+ major soft falsifiers TRIGGERED -> status: KILLED
- 3+ soft falsifiers of any severity TRIGGERED -> status: KILLED
- 1+ soft falsifier TRIGGERED AND the hypothesis directional prediction contradicted by trailing 30-day price action -> status: WOUNDED
- Otherwise -> status: SURVIVED

IMPORTANT: Do not rescue a hypothesis by reinterpreting what "triggered" means. If the data meets the stated condition, the falsifier is triggered. Period.

## ADDITIONAL CHECKS (for context, not kill authority)

3. CROSS-THEORY ATTACK: Does another Active theory's mechanism contradict this hypothesis? Report contradictions but do NOT use them to override the kill rules above.

4. EVIDENCE QUALITY ASSESSMENT: Grade the evidence: direct market data > high-quality macro data > proxies > narrative inference.

5. COMPOSITION INTEGRITY (multi-theory hypotheses only): Did combining theories narrow the prediction? If it made the hypothesis broader or harder to kill, status: KILLED as narrative padding.

RULES:
- Do NOT assign conviction scores -- that is the mechanical pipeline's job.
- Do NOT decide whether soft falsifiers are "serious enough" to kill -- severity is pre-registered.
- Do NOT recommend which survivors to act on.
- Do NOT soften your attacks. If it is worth mentioning, state it plainly.
- Every hypothesis gets the full audit. No exceptions."""


def _elimination_output_schema(
    has_channel_tags: bool = False,
    has_sector_appendices: bool = False,
) -> str:
    channel_block = ""
    if has_channel_tags:
        channel_block = (
            '    "channel_verification": {\n'
            '      "assigned_channel": "the resolution_channel from generation",\n'
            '      "correct_channel": "same as assigned, or corrected channel if misclassified",\n'
            '      "correction_reason": "null if no correction, otherwise explanation"\n'
            '    },\n'
        )

    sector_block = ""
    if has_sector_appendices:
        sector_block = (
            '    "sector_falsifier_audit": [\n'
            '      {\n'
            '        "sector_id": "the sector_id from the appendix",\n'
            '        "falsifier_id": "e.g. tech_sf_01",\n'
            '        "metric_value_found": "the current value you looked up",\n'
            '        "triggered": "YES | NO",\n'
            '        "relevant": "YES | NO | N/A",\n'
            '        "reasoning": "1-2 sentences on why this does or does not attack the load-bearing mechanism",\n'
            '        "severity_applied": "minor | medium | major | NONE"\n'
            '      }\n'
            '    ],\n'
            '    "attack_vector_findings": [\n'
            '      {\n'
            '        "vector_id": "e.g. tech_av_01",\n'
            '        "finding": "summary of what was found, 1-2 sentences",\n'
            '        "impact": "how this affects the SURVIVED/WOUNDED/KILLED determination"\n'
            '      }\n'
            '    ],\n'
        )

    return (
        "Output a JSON array. For each hypothesis (in the same order as input), provide:\n\n"
        "```json\n"
        "[\n"
        "  {\n"
        '    "hypothesis_id": "the id or index from the input",\n'
        '    "theory_id": "the source theory_id",\n'
        '    "short_name": "the hypothesis short_name",\n'
        '    "status": "SURVIVED | WOUNDED | KILLED",\n'
        + channel_block +
        '    "hard_falsifier_check": {\n'
        '      "any_triggered": false,\n'
        '      "details": "Explanation of each hard falsifier check"\n'
        '    },\n'
        '    "soft_falsifier_check": {\n'
        '      "triggered_count": 0,\n'
        '      "triggered": ["list of triggered soft falsifier names"],\n'
        '      "untestable": ["list of soft falsifier names where data is unavailable"],\n'
        '      "close_to_triggering": ["list approaching threshold"],\n'
        '      "details": "Explanation"\n'
        '    },\n'
        + sector_block +
        '    "cross_theory_attack": {\n'
        '      "contradictions_found": false,\n'
        '      "details": "Explanation of any contradicting mechanisms"\n'
        '    },\n'
        '    "evidence_quality": {\n'
        '      "grade": "strong | moderate | weak",\n'
        '      "details": "Assessment of evidence supporting each prediction"\n'
        '    },\n'
        '    "composition_integrity": {\n'
        '      "applicable": false,\n'
        '      "passed": true,\n'
        '      "details": "Only for multi-theory hypotheses"\n'
        '    },\n'
        '    "elimination_notes": "Full reasoning paragraph summarizing the adversarial assessment",\n'
        '    "conviction_inputs": {\n'
        '      "support_strength": 0.0,\n'
        '      "evidence_quality": 0.0,\n'
        '      "convergence": 0.0,\n'
        '      "falsifier_clarity": 0.0,\n'
        '      "horizon_alignment": 0.0,\n'
        '      "expression_efficiency": 0.0\n'
        '    }\n'
        '  }\n'
        ']\n'
        "```\n\n"
        "IMPORTANT: Output ONLY the JSON array. No commentary before or after.\n"
        "For KILLED hypotheses, conviction_inputs should all be 0.0.\n"
        "For WOUNDED hypotheses, reduce the relevant conviction_input dimensions to reflect the wounds."
    )


def _format_sector_appendices_section(appendices: list[dict]) -> str:
    """Format sector appendices into the prompt injection block for Pass 3.

    This produces the full ``--- SECTOR FALSIFIER APPENDICES ---`` section
    exactly as specified in plan_v4.md Component 2, followed by the
    structured output template from Component 3.

    The block is built *only* when appendices is non-empty; the caller
    gates on that condition so this function always receives >= 1 appendix.
    """
    lines: list[str] = []

    # --- Header and instructions ---
    lines.append("--- SECTOR FALSIFIER APPENDICES ---")
    lines.append("")
    lines.append(
        "The following sector-specific falsifiers are available for hypotheses\n"
        "that involve the listed ETFs. For each hypothesis that touches a sector,\n"
        "you MUST:"
    )
    lines.append("")
    lines.append("1. Look up the current value of each mechanical falsifier's metric")
    lines.append("2. Determine if the threshold is breached (TRIGGERED or NOT TRIGGERED)")
    lines.append(
        "3. If TRIGGERED: determine if the falsifier is RELEVANT to this specific\n"
        "   hypothesis -- does it attack the hypothesis's load-bearing mechanism?"
    )
    lines.append("4. State your reasoning for the relevance determination")
    lines.append("5. Report the result in the structured format specified below")
    lines.append("")
    lines.append(
        "You must also investigate the evaluator attack vectors and incorporate\n"
        "your findings into your qualitative assessment of the hypothesis."
    )

    # --- Per-appendix content ---
    for appendix in appendices:
        lines.append("")
        lines.append(f"SECTOR: {appendix['display_name']}")
        lines.append(f"Applies to hypotheses involving: {', '.join(appendix['ticker_triggers'])}")
        lines.append("")
        lines.append("MECHANICAL FALSIFIERS:")
        for f in appendix["mechanical_falsifiers"]:
            lines.append(f"  [{f['falsifier_id']}] {f['condition']}")
            lines.append(f"  Metric: {f['metric']}")
            lines.append(f"  Threshold: {f['threshold']} ({f['direction']})")
            lines.append(f"  Severity if triggered AND relevant: {f['severity']}")
            lines.append(f"  Data source: {f['data_source']}")
            lines.append("")
        lines.append("EVALUATOR ATTACK VECTORS:")
        for v in appendix["evaluator_attack_vectors"]:
            lines.append(f"  [{v['vector_id']}] {v['question']}")
            lines.append(f"  Search for: {v['what_to_search']}")
            lines.append(f"  Kill condition: {v['kill_condition']}")
            lines.append("")

    # --- Structured output template (Component 3) ---
    lines.append("")
    lines.append("SECTOR FALSIFIER AUDIT OUTPUT FORMAT:")
    lines.append("")
    lines.append(
        "For each hypothesis that touches a sector with an active appendix,\n"
        "include the following structured audit in your response:"
    )
    lines.append("")
    lines.append("```")
    lines.append("SECTOR FALSIFIER AUDIT: {hypothesis_id}")
    lines.append("Sector: {sector_id}")
    lines.append("")
    lines.append("  [{falsifier_id}]")
    lines.append("  Metric value found: {current value from web search}")
    lines.append("  Triggered: YES | NO")
    lines.append("  Relevant to this hypothesis: YES | NO | N/A (if not triggered)")
    lines.append("  Reasoning: {1-2 sentences explaining WHY this falsifier does or does")
    lines.append("              not attack the hypothesis's load-bearing mechanism}")
    lines.append("  Severity applied: {severity} | NONE")
    lines.append("")
    lines.append("ATTACK VECTOR FINDINGS: {hypothesis_id}")
    lines.append("  [{vector_id}] {summary of what was found, 1-2 sentences}")
    lines.append("  Impact on hypothesis: {how this finding affects the SURVIVED/WOUNDED/KILLED determination}")
    lines.append("```")
    lines.append("")
    lines.append("DEFINITION OF RELEVANCE:")
    lines.append(
        "A triggered sector falsifier is RELEVANT to a hypothesis if and only if\n"
        "the falsifier is adverse to the hypothesis's load-bearing mechanism --\n"
        "meaning the condition identified by the falsifier, if true, would weaken,\n"
        "undermine, or contradict the specific causal pathway that the hypothesis\n"
        "depends on for its predicted outcome."
    )
    lines.append("")
    lines.append(
        "The test is directional and specific: ask \"If this falsifier condition\n"
        "is true, does it attack the mechanism THIS hypothesis needs to work?\"\n"
        "A triggered falsifier that is bad for the sector but does not attack the\n"
        "specific hypothesis mechanism is NOT relevant."
    )

    lines.append("")
    lines.append("--- END SECTOR APPENDICES ---")

    return "\n".join(lines)


def _extract_falsifier_section(theory: TheoryModule) -> str:
    """Extract falsifier information from a theory module for the elimination prompt."""
    lines = []

    if theory.hard_falsifiers:
        lines.append("**Hard Falsifiers:**")
        for hf in theory.hard_falsifiers:
            lines.append(f"- [{hf.id}] {hf.condition}")
            if hf.metric:
                lines.append(f"  Metric: {hf.metric}, Threshold: {hf.threshold}")

    if theory.soft_falsifiers:
        lines.append("\n**Soft Falsifiers:**")
        for sf in theory.soft_falsifiers:
            lines.append(f"- [{sf.id}] ({sf.severity.value}) {sf.condition}")
            if sf.metric:
                lines.append(f"  Metric: {sf.metric}, Threshold: {sf.threshold}")
            if sf.implication:
                lines.append(f"  Implication: {sf.implication}")

    return "\n".join(lines) if lines else "[No falsifiers specified]"


def _resolution_channel_instructions() -> str:
    """Resolution channel requirement for the generation prompt."""
    return """For each hypothesis, assign exactly one resolution_channel from this list:
  - nominal_price_decline
  - inflationary_grind
  - real_asset_outperformance
  - sector_rotation
  - broad_credit_contraction
  - sector_credit_stress

Select the channel that describes the PRIMARY mechanism your hypothesis depends on.
Choose the channel whose failure would most directly kill the hypothesis.

If the hypothesis predicts a 15%+ nominal price decline, the channel is nominal_price_decline
even if there are secondary inflationary dynamics. The channel is the load-bearing mechanism.

Include "resolution_channel": "<channel>" in each hypothesis output."""


def _channel_verification_instructions() -> str:
    """Channel verification section for the elimination prompt."""
    return """For each hypothesis, verify the resolution_channel tag:
1. Does the predicted magnitude match the channel? A 30%+ nominal decline
   tagged as "inflationary_grind" is a misclassification.
2. Does the predicted timeline match the channel? An "inflationary_grind"
   hypothesis with a 2-month timeline is suspect -- grinds take years.
3. Does the load-bearing mechanism match the channel? If removing the
   channel's mechanism would kill the hypothesis, the tag is correct.
   If the hypothesis would survive without that mechanism, the tag is wrong.

If you identify a channel misclassification, include in your output:
  - "channel_verification.assigned_channel": the original channel
  - "channel_verification.correct_channel": the corrected channel
  - "channel_verification.correction_reason": why the reassignment is warranted

The corrected channel will be used for scoring. The original assignment
is preserved in the audit trail."""
