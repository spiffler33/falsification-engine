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
    prior_hypotheses: list[dict[str, Any]] | None = None,
    active_threads: list[dict[str, Any]] | None = None,
) -> str:
    """Build the generation prompt for Pass 2.

    Includes Active theories (full markdown), up to 1 Adjacent wildcard,
    the briefing packet, and queued inbox items.

    v7: When active_threads is provided, injects thread context with lifecycle
    taxonomy (CONFIRM/UPDATE/RENEW/RETIRE) and NEW hypothesis section.
    Falls back to legacy prior_hypotheses + continuation contract when no threads.
    """
    has_threads = bool(active_threads)

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
    parts.append(_generation_system_instructions(has_threads=has_threads))

    # --- v7 Thread context (replaces prior_hypotheses + continuation contract) ---
    if has_threads:
        parts.append("\n\n## ACTIVE THREADS (from prior run)\n")
        parts.append(_thread_context_section(active_threads))
        parts.append("\n\n## LIFECYCLE CONTRACT\n")
        parts.append(_thread_lifecycle_contract())

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

    # --- v7 NEW hypothesis section (for theories not in carried-forward threads) ---
    if has_threads:
        represented_theories = {t.get("source_theory") for t in active_threads}
        active_scores = {}
        for tid in active_theories:
            ar = activation_map.get(tid)
            if ar:
                if ar.is_two_phase and ar.phase_scores and ar.effective_phase:
                    active_scores[tid] = ar.phase_scores.get(ar.effective_phase, 0.0)
                else:
                    active_scores[tid] = ar.score if ar.score is not None else 0.0
        parts.append("\n\n## NEW HYPOTHESIS GENERATION\n")
        parts.append(_new_hypothesis_section(
            active_theories=active_theories,
            active_scores=active_scores,
            represented_theories=represented_theories,
            adjacent_theories=adjacent_theories[:max_adjacent] if adjacent_theories else None,
        ))

    # --- Legacy: Prior hypotheses with realization data (pre-v7 backward compat) ---
    if not has_threads and prior_hypotheses:
        parts.append("\n\n## PRIOR HYPOTHESES (from previous runs)\n")
        parts.append(_prior_hypotheses_section(prior_hypotheses))
        parts.append("\n\n## CONTINUATION CONTRACT\n")
        parts.append(_continuation_contract_instructions())

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
    if has_threads:
        parts.append(_generation_output_schema_v7())
    else:
        parts.append(_generation_output_schema_legacy())

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


def _generation_system_instructions(has_threads: bool = False) -> str:
    base = """SYSTEM: You are the Generation Pass of a Falsification Engine for global macro analysis.

Your job is to generate testable hypotheses from the Active theory modules below, grounded in the current data briefing. Each hypothesis must trace to a specific causal mechanism in a specific theory module."""

    if has_threads:
        base += """

THIS IS A CONTINUATION RUN. Active hypothesis threads from the prior run are listed below.
Your PRIMARY job is to review each thread and assign a lifecycle action (CONFIRM, UPDATE, RENEW, or RETIRE).
Your SECONDARY job is to generate NEW hypotheses for active theories not adequately represented.

RULES:
1. For each active thread: state exactly one lifecycle action with reasoning.
2. CONFIRM is the default. Do not change what does not need changing.
3. After processing all threads, generate NEW hypotheses ONLY for active theories not represented in the carried-forward set, or where conditions have materially changed.
4. Target: 7-9 total hypotheses (carried forward + new).
5. You may generate 0-1 NEW hypotheses from the Adjacent wildcard theory (if provided).
6. Do NOT rank hypotheses by importance or recommend actions.
7. Do NOT produce hypotheses from theories not listed below.
8. Each NEW prediction must be specific: include magnitude range, timeframe, and named ETF instruments.
9. Hard falsifiers must be specific enough to check against data.
10. Soft falsifiers must include severity (minor/medium/major) inherited from the source theory module.
11. Each NEW hypothesis MUST include a PAYOFF_BAND block with magnitude_lower, magnitude_upper, and end_date."""
    else:
        base += """

RULES:
1. Generate 2-4 hypotheses per Active theory.
2. You may generate 0-1 hypotheses from the Adjacent wildcard theory (if provided).
3. You may combine mechanisms from multiple Active theories into composite hypotheses -- but ONLY if the combination NARROWS the prediction and makes it MORE falsifiable.
4. Do NOT rank hypotheses by importance or recommend actions.
5. Do NOT produce hypotheses from theories not listed below.
6. Each prediction must be specific: include magnitude range, timeframe, and named ETF instruments.
7. Hard falsifiers must be specific enough to check against data.
8. Soft falsifiers must include severity (minor/medium/major) inherited from the source theory module.
9. Each hypothesis MUST include a PAYOFF_BAND block with magnitude_lower, magnitude_upper, and end_date (see OUTPUT FORMAT)."""

    base += """

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

    return base


def _generation_output_schema_v7() -> str:
    """Output schema when active threads are present — lifecycle-aware format."""
    return """Output a single JSON object with two top-level keys: "thread_actions" and "new_hypotheses".

The "thread_actions" array contains one entry per active thread listed above.
The "new_hypotheses" array contains any genuinely new hypotheses.

See OUTPUT FORMAT FOR THREAD ACTIONS above for thread_actions structure.

Each NEW hypothesis in "new_hypotheses" must have exactly these fields:

```json
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
  "lifecycle_action": "NEW",
  "conviction_inputs": {
    "support_strength": 0.0,
    "evidence_quality": 0.0,
    "convergence": 0.0,
    "falsifier_clarity": 0.0,
    "horizon_alignment": 0.0,
    "expression_efficiency": 0.0
  }
}
```

IMPORTANT: Output ONLY the JSON object. No commentary before or after."""


def _generation_output_schema_legacy() -> str:
    """Output schema for first-run (no threads) — flat array format, backward compatible."""
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
    "lifecycle_action": "NEW",
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


def _prior_hypotheses_section(prior_hypotheses: list[dict[str, Any]]) -> str:
    """Format prior hypotheses with realization data for the generation prompt.

    Each prior hypothesis is displayed with its expression, payoff band,
    realization primitives, and status so the LLM can decide whether to
    regenerate, continue, or move to other mechanisms.

    NOTE: This is the v6 legacy path, used when no active threads exist
    (e.g., runs before v7 migration). The v7 path uses _thread_context_section.
    """
    lines = []
    lines.append(
        "The following hypotheses survived previous pipeline runs and have "
        "realization data. Review each before generating new hypotheses on "
        "the same expression or mechanism.\n"
    )

    for h in prior_hypotheses:
        h_id = h.get("id", "?")
        lines.append(f"PRIOR HYPOTHESIS: {h_id}")

        # Expression: direction + assets
        asset_dir = h.get("asset_direction", {})
        if asset_dir:
            legs = []
            for ticker, direction in asset_dir.items():
                legs.append(f"{direction} {ticker}")
            lines.append(f"  Expression: {' / '.join(legs)}")
        else:
            assets = h.get("predicted_assets", [])
            if assets:
                lines.append(f"  Assets: {', '.join(assets)}")

        # Payoff band
        mag_lower = h.get("predicted_magnitude_lower")
        mag_upper = h.get("predicted_magnitude_upper")
        end_date = h.get("timeframe_end_date")
        if mag_lower is not None and mag_upper is not None:
            band_str = f"{mag_lower*100:.0f}-{mag_upper*100:.0f}%"
            if end_date:
                band_str += f" through {end_date}"
            lines.append(f"  Payoff band: {band_str}")

        # Realization primitives
        expr_return = h.get("expression_return")
        if expr_return is not None:
            lines.append(f"  Expression return since inception: {expr_return:+.1%}")

        real_lower = h.get("realization_vs_lower")
        if real_lower is not None:
            lines.append(
                f"  Realization vs lower bound: {real_lower:.2f}  "
                f"({real_lower*100:.0f}% of lower bound delivered)"
            )

        real_upper = h.get("realization_vs_upper")
        if real_upper is not None:
            lines.append(
                f"  Realization vs upper bound: {real_upper:.2f}  "
                f"({real_upper*100:.0f}% of upper bound delivered)"
            )

        time_elapsed = h.get("time_elapsed_pct")
        if time_elapsed is not None:
            lines.append(f"  Time elapsed: {time_elapsed:.0%} of holding window")

        lines.append(f"  Status: {h.get('status', 'SURVIVED')}")

        # Continuation lineage
        cont_gen = h.get("continuation_generation", 1)
        if cont_gen > 1:
            lines.append(f"  Continuation: Gen {cont_gen} of {h.get('continuation_of', '?')}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# v7 Thread-Based Context — replaces prior_hypotheses + continuation contract
# ---------------------------------------------------------------------------


def _thread_context_section(active_threads: list[dict[str, Any]]) -> str:
    """Format active hypothesis threads with realization + staleness for generation prompt.

    Each thread is displayed with its identity, expression, payoff band,
    realization data, freshness, and falsifier status (including staleness
    flags from the mechanical staleness gate). The LLM must assign exactly
    one lifecycle action per thread.
    """
    n = len(active_threads)
    lines = []
    lines.append(
        f"You are reviewing {n} active hypothesis thread{'s' if n != 1 else ''} "
        f"from the prior run.\n"
        "For each thread, you MUST state exactly one action: CONFIRM, UPDATE, RENEW, or RETIRE.\n"
        "After processing all threads, you may generate NEW hypotheses for active theories\n"
        "not adequately represented. Target: 7-9 total hypotheses (carried forward + new).\n"
    )
    lines.append(
        "CONFIRM is the default action. Do not UPDATE unless you can state specifically what changed.\n"
        "Do not RENEW unless the economic content of the call (magnitude, expression, mechanism) has changed.\n"
        "If the expression should change (different tickers, same mechanism): that is RENEW, not UPDATE.\n"
    )

    for t in active_threads:
        tid = t.get("thread_id", "?")
        short_name = t.get("short_name", "?")
        lines.append(f'Thread {tid}: "{short_name}"')

        # Source theory
        source_theory = t.get("source_theory", "?")
        label = THEORY_LABEL_MAP.get(source_theory, source_theory)
        lines.append(f"  Source theory: {label}")

        # Age
        total_instances = t.get("total_instances", 1)
        created_date = t.get("created_date", "?")
        lines.append(f"  Age: {total_instances} run{'s' if total_instances != 1 else ''} (first generated {created_date})")

        # Expression: direction + assets
        asset_dir = t.get("asset_direction", {})
        if asset_dir:
            legs = [f"{direction} {ticker}" for ticker, direction in asset_dir.items()]
            lines.append(f"  Expression: {' / '.join(legs)}")

        # Payoff band
        band_lower = t.get("payoff_band_lower")
        band_upper = t.get("payoff_band_upper")
        end_date = t.get("timeframe_end_date")
        if band_lower is not None and band_upper is not None:
            band_str = f"{band_lower*100:.0f}-{band_upper*100:.0f}%"
            if end_date:
                band_str += f" through {end_date}"
            lines.append(f"  Payoff band: {band_str}")

        # Realization data
        expr_return = t.get("expression_return")
        if expr_return is not None:
            lines.append(f"  Realization: {expr_return:+.1%} expression return")

            real_lower = t.get("realization_vs_lower")
            real_upper = t.get("realization_vs_upper")
            if real_lower is not None and real_upper is not None:
                lines.append(f"    {real_lower:.2f}x lower bound, {real_upper:.2f}x upper bound")

            time_elapsed = t.get("time_elapsed_pct")
            if time_elapsed is not None:
                lines.append(f"    {time_elapsed:.0%} of time elapsed")

        # Freshness label
        freshness = t.get("freshness_label")
        if freshness:
            lines.append(f"  Freshness: {freshness}")

        # Falsifier status
        hard_falsifiers = t.get("hard_falsifiers", [])
        soft_falsifiers = t.get("soft_falsifiers", [])

        if hard_falsifiers:
            passed = sum(1 for f in hard_falsifiers if f.get("status") != "FAILED")
            failed = sum(1 for f in hard_falsifiers if f.get("status") == "FAILED")
            lines.append(f"  Falsifier status:")
            lines.append(f"    Hard: {passed} passed, {failed} FAILED")

        if soft_falsifiers:
            if not hard_falsifiers:
                lines.append(f"  Falsifier status:")
            lines.append(f"    Soft:")
            for sf in soft_falsifiers:
                name = sf.get("name", "?")
                severity = sf.get("severity", "?")
                status = sf.get("status", "UNTESTABLE")
                metric = sf.get("metric", "?")
                current_val = sf.get("current_market_value")
                threshold = sf.get("threshold", "?")

                val_str = f"{current_val}" if current_val is not None else "N/A"
                lines.append(f'      - "{name}" [{severity}]: {status} (metric: {val_str}, threshold: {threshold})')

                # Staleness flag
                staleness = sf.get("staleness_flag")
                if staleness == "STALE":
                    lines.append(f"        >> STALE -- market moved past 2x threshold distance from generation level")

                # ESCALATED_UNTESTABLE flag
                esc_status = sf.get("escalated_status")
                esc_count = sf.get("untestable_consecutive", 0)
                if esc_status == "ESCALATED_UNTESTABLE":
                    lines.append(f"        >> ESCALATED -- untestable for {esc_count} consecutive passes")

        lines.append("")
        lines.append(f"  ACTION REQUIRED: State CONFIRM, UPDATE, RENEW, or RETIRE with reasoning.")
        lines.append("")

    return "\n".join(lines)


def _thread_lifecycle_contract() -> str:
    """Lifecycle action taxonomy and output format for thread actions.

    Injected after the thread context section. Defines what each action means
    and the exact output format expected per thread.
    """
    return """## LIFECYCLE ACTION TAXONOMY

| Action  | When to use |
|---------|-------------|
| CONFIRM | Mechanism unchanged, data consistent, falsifiers intact. Default action. |
| UPDATE  | Mechanism intact but framing, falsifier wording, or modest timing needs adjustment. |
| RENEW   | Economic content has changed: magnitude, expression, or mechanism materially revised. |
| RETIRE  | Mechanism weakened, falsifier triggered, thesis no longer supported, or expression fully delivered. |

CONFIRM is the expectation in a stable regime. A run that is 5 CONFIRMs + 1 UPDATE + 1 NEW reflects a real macro PM's daily workflow.

Do NOT UPDATE unless you can state specifically what changed and why.
Do NOT RENEW unless you can state specifically what economic content changed.
A run that is 0 CONFIRMs + 7 NEWs should only happen when the regime genuinely shifts.

## OUTPUT FORMAT FOR THREAD ACTIONS

For each active thread above, include one object in the "thread_actions" array:

```json
{
  "thread_actions": [
    {
      "thread_id": "T-...",
      "lifecycle_action": "CONFIRM",
      "lifecycle_reasoning": "Data consistent, mechanism intact, no changes needed."
    },
    {
      "thread_id": "T-...",
      "lifecycle_action": "UPDATE",
      "lifecycle_reasoning": "Timing extended — [specific reason].",
      "revised_timeframe_end_date": "2026-10-31",
      "revised_short_name": "Updated name if framing changed",
      "revised_full_statement": "Updated statement if framing changed"
    },
    {
      "thread_id": "T-...",
      "lifecycle_action": "RENEW",
      "lifecycle_reasoning": "Expression changed — [specific economic content that changed].",
      "renewed_hypothesis": {
        "theory_id": "...",
        "short_name": "...",
        "full_statement": "...",
        "predicted_assets": ["..."],
        "asset_direction": {"...": "LONG"},
        "resolution_channel": "...",
        "timeframe": "...",
        "hard_falsifiers": [{"condition": "...", "metric": "...", "threshold": "..."}],
        "soft_falsifiers": [{"name": "...", "severity": "minor|medium|major", "condition": "...", "metric": "...", "threshold": "..."}],
        "payoff_band": {"magnitude_lower": 0.15, "magnitude_upper": 0.30, "end_date": "YYYY-MM-DD"},
        "conviction_inputs": {"support_strength": 0.0, "evidence_quality": 0.0, "convergence": 0.0, "falsifier_clarity": 0.0, "horizon_alignment": 0.0, "expression_efficiency": 0.0}
      }
    },
    {
      "thread_id": "T-...",
      "lifecycle_action": "RETIRE",
      "lifecycle_reasoning": "Hard falsifier triggered — [which one and why]."
    }
  ],
  "new_hypotheses": [
    ...see NEW HYPOTHESIS FORMAT below...
  ]
}
```

For CONFIRM: only thread_id, lifecycle_action, lifecycle_reasoning required.
For UPDATE: include any revised_* fields that changed. Omit fields that did not change.
For RENEW: include full renewed_hypothesis with complete specification (new payoff band from current levels).
For RETIRE: only thread_id, lifecycle_action, lifecycle_reasoning required."""


def _new_hypothesis_section(
    active_theories: list[str],
    active_scores: dict[str, float],
    represented_theories: set[str],
    adjacent_theories: list[str] | None = None,
) -> str:
    """NEW hypothesis generation section — for theories not represented in carried-forward threads."""
    lines = []
    lines.append("After processing the threads above, generate NEW hypotheses ONLY for:")
    lines.append("  - Active theories not represented in the carried-forward set")
    lines.append("  - Theories where conditions have materially changed since the prior run\n")

    # Show which theories are represented vs. unrepresented
    unrepresented = [t for t in active_theories if t not in represented_theories]
    if unrepresented:
        lines.append("Unrepresented active theories (NEW hypotheses expected):")
        for tid in unrepresented:
            label = THEORY_LABEL_MAP.get(tid, tid)
            score = active_scores.get(tid)
            score_str = f" -- Activation: {score:.0%}" if score is not None else ""
            lines.append(f"  - {label}{score_str}")
        lines.append("")

    represented = [t for t in active_theories if t in represented_theories]
    if represented:
        lines.append("Already represented (generate NEW only if conditions materially changed):")
        for tid in represented:
            label = THEORY_LABEL_MAP.get(tid, tid)
            lines.append(f"  - {label}")
        lines.append("")

    if adjacent_theories:
        lines.append("Adjacent theories (max 1 wildcard, NEW only):")
        for tid in adjacent_theories:
            label = THEORY_LABEL_MAP.get(tid, tid)
            lines.append(f"  - {label}")
        lines.append("")

    lines.append("Target: 7-9 total hypotheses across carried-forward + new.")
    return "\n".join(lines)


def _continuation_contract_instructions() -> str:
    """Instructions for the LLM on how to handle continuations."""
    return """When a prior hypothesis has high realization (realization_vs_upper approaching or exceeding 1.0), you have three options:

1. DECLINE TO REGENERATE. The mechanism is spent. Generate hypotheses on other mechanisms instead.

2. GENERATE A CONTINUATION. A new hypothesis on the same or similar expression, with:
   - continuation_of: set to the prior hypothesis ID
   - continuation_generation: increment from the parent (parent's generation + 1)
   - continuation_justification: REQUIRED. Must state what is genuinely new. The following is NOT sufficient: "the same macro factors are still active."
   Acceptable justifications:
     - New data not available at original generation time
     - A mechanism extension (e.g., a second-order effect now manifesting)
     - A changed expression (same mechanism, different ETF pair from current levels)
   The continuation gets its own payoff band calibrated from current levels, NOT the original's band.

3. GENERATE A GENUINELY DIFFERENT HYPOTHESIS on the same mechanism with a different expression. This is NOT a continuation -- it is a new original hypothesis (continuation_of: null, continuation_generation: 1).

CRITICAL: Do NOT silently revise a prior hypothesis's payoff band. The original's predicted_magnitude_lower, predicted_magnitude_upper, and timeframe_end_date are immutable after generation. If you want to update the view from current levels, generate a continuation."""


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
