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
) -> str:
    """Build the elimination prompt for Pass 3.

    Includes the generated hypotheses, theory modules they invoke,
    and the current briefing packet.
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

    # --- Output schema ---
    parts.append("\n\n## OUTPUT FORMAT\n")
    parts.append(_elimination_output_schema())

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
    "hard_falsifiers": [
      {"condition": "Description of what would kill this hypothesis", "metric": "data field to check", "threshold": "specific number or condition"}
    ],
    "soft_falsifiers": [
      {"name": "Short name", "severity": "minor|medium|major", "condition": "What would wound it", "metric": "data field", "threshold": "value"}
    ],
    "timeframe": "e.g. Through Q3 2026",
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


def _elimination_output_schema() -> str:
    return """Output a JSON array. For each hypothesis (in the same order as input), provide:

```json
[
  {
    "hypothesis_id": "the id or index from the input",
    "theory_id": "the source theory_id",
    "short_name": "the hypothesis short_name",
    "status": "SURVIVED | WOUNDED | KILLED",
    "hard_falsifier_check": {
      "any_triggered": false,
      "details": "Explanation of each hard falsifier check"
    },
    "soft_falsifier_check": {
      "triggered_count": 0,
      "triggered": ["list of triggered soft falsifier names"],
      "untestable": ["list of soft falsifier names where data is unavailable"],
      "close_to_triggering": ["list approaching threshold"],
      "details": "Explanation"
    },
    "cross_theory_attack": {
      "contradictions_found": false,
      "details": "Explanation of any contradicting mechanisms"
    },
    "evidence_quality": {
      "grade": "strong | moderate | weak",
      "details": "Assessment of evidence supporting each prediction"
    },
    "composition_integrity": {
      "applicable": false,
      "passed": true,
      "details": "Only for multi-theory hypotheses"
    },
    "elimination_notes": "Full reasoning paragraph summarizing the adversarial assessment",
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

IMPORTANT: Output ONLY the JSON array. No commentary before or after.
For KILLED hypotheses, conviction_inputs should all be 0.0.
For WOUNDED hypotheses, reduce the relevant conviction_input dimensions to reflect the wounds."""


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
