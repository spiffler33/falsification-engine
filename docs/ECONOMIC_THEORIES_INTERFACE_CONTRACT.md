# ECONOMIC THEORIES — Interface Contract for Architecture Thread

*This document is produced by the Economic Theories design thread. It specifies what the theories component delivers, what it requires, and how it interfaces with the rest of the Falsification Engine. The architecture thread should design around this contract.*

*Version: 1.1 — March 2026*
*Changelog: v1.1 — Updated registry from 6 domains to 8 modules (debt_cycle and fiscal_dominance split). Added severity field to soft falsifiers for conviction scoring pipeline.*

---

## What This Component Is

The economic theories component is a **registry of causal mechanism modules** that serve as the intellectual foundation of the Falsification Engine. Each module describes a macro-economic mechanism — not an opinion, not a persona, not a heuristic — with enough structure that the system can generate testable hypotheses from it and evaluate those hypotheses against empirical evidence.

The theories are what make hypotheses **falsifiable**. Without them, the system degenerates into an LLM producing plausible narratives without testable structure. Every hypothesis the system generates must trace back to a specific mechanism in a specific theory module, and every evaluation must reference the failure conditions that theory specifies.

---

## Current Theory Registry

The registry starts with 8 theory modules across 6 intellectual domains. Two domains — debt cycles and fiscal dominance — are split into separate modules because their sub-mechanisms have distinct activation conditions, time horizons, and falsifiers. The architecture must support N modules, not assume 8. New theories can be added when they describe a causal mechanism (not just a heuristic), produce testable predictions, and are orthogonal to existing theories.

| # | Theory ID | Two-Phase? | Domain | Primary Mechanism |
|---|-----------|-----------|--------|-------------------|
| 1 | `valuation_mean_reversion` | No | Valuation & Margin of Safety | Equity risk premium compression → capital reallocation → drawdown |
| 2 | `debt_cycle_short` | **Yes** (Expansion / Contraction) | Debt Cycle Mechanics | 5-8 year credit expansion/contraction, controlled by rate policy |
| 3 | `debt_cycle_long` | No | Debt Cycle Mechanics | 50-75 year debt accumulation, MP1→MP2→MP3 escalation |
| 4 | `structural_fragility` | **Yes** (Building / Resolving) | Minsky Dynamics | Stability → progressive risk-taking → concentration + leverage + non-linear break |
| 5 | `fiscal_dominance_liquidity` | No | Fiscal Dominance | Net liquidity transmission: deficit → reserve injection → asset price correlation |
| 6 | `fiscal_dominance_arithmetic` | No | Fiscal Dominance | Interest expense trajectory → devaluation arithmetic → hard asset outperformance |
| 7 | `capital_flows` | **Yes** (Accumulation / Rotation) | Capital Flow Dynamics | Dollar gravity, EM mean reversion, China credit impulse |
| 8 | `monetary_architecture` | No | Monetary System Architecture | Treasury-to-commodity collateral substitution; plumbing stress as leading indicator |

**Two-phase modules:** Three modules have distinct phases with opposite practical implications. Phases are mutually exclusive — the "resolving/contraction/rotation" phase is checked first; if Active, the "building/expansion/accumulation" phase is by definition Inactive. Each phase has its own activation conditions, predictions, and implications. The activation scoring layer must handle per-phase scoring.

---

## Theory Module Interface

Each theory module is a structured object with the following fields. This is the contract — the generator, evaluator, and activation-scoring layer all depend on this shape.

```
Theory Module:
│
├── theory_id (string)
│   Unique identifier. Examples: "fiscal_dominance_liquidity", "debt_cycle_short"
│
├── activation_conditions
│   ├── indicators[]
│   │   Each indicator:
│   │     - metric_name (string, matches data briefing field name)
│   │     - threshold (number or range)
│   │     - direction ("above" | "below" | "rising" | "falling" | "between")
│   │     - weight (how much this indicator matters for activation scoring)
│   │   
│   └── activation_score()
│       Mechanical computation: count triggered indicators weighted by importance.
│       Returns: "Active" | "Adjacent" | "Inactive"
│       Rule of thumb: ≥60% weighted indicators triggered → Active.
│       20-59% → Adjacent. <20% → Inactive.
│
├── core_mechanism
│   ├── causal_chain[]
│   │   Ordered sequence of transmission steps.
│   │   Example for fiscal_dominance:
│   │     1. Government runs deficit above $1.5T annualized
│   │     2. Treasury issuance injects reserves into banking system
│   │     3. Net liquidity expands despite QT
│   │     4. Asset prices correlate with net liquidity expansion
│   │     5. Higher rates → higher interest expense → larger deficit → feedback loop
│   │
│   └── time_horizon
│       What timescale this mechanism primarily operates on.
│       Examples: "6-18 months" (debt_cycle_short),
│       "5-15 years" (monetary_architecture)
│
├── predictions_when_active
│   ├── directional[]
│   │   Each prediction:
│   │     - asset (ETF ticker or asset class)
│   │     - direction ("outperform" | "underperform" | "rally" | "decline")
│   │     - magnitude_range (e.g., "15-30% over 12 months")
│   │     - timeframe (e.g., "6-12 months")
│   │
│   └── conditional[]
│       Predictions that depend on interaction with other theories.
│       Each:
│         - condition ("if [theory_id] is also Active")
│         - prediction (what happens when BOTH mechanisms are operative)
│         - specificity_gain (how the combination narrows the prediction)
│
├── downstream_implications
│   └── affects[]
│       Each:
│         - target_theory_id (which other theory is affected)
│         - relationship ("extends" | "accelerates" | "contradicts" | "triggers" | "modifies")
│         - description (how this theory's activation changes the other theory's dynamics)
│       
│       Example: fiscal_dominance_liquidity → debt_cycle_short:
│         relationship: "extends"
│         description: "Fiscal spending prevents the short-term debt cycle from
│         contracting normally. Traditional late-cycle indicators (yield curve
│         inversion, rising unemployment) may not predict recession because fiscal
│         impulse exceeds monetary drag."
│
├── falsifiers
│   ├── hard[]
│   │   Conditions that definitively prove the theory is not operative.
│   │   Must be specific and testable against data.
│   │   Each:
│   │     - condition (what would need to be true)
│   │     - metric (what data field to check)
│   │     - threshold (specific number or duration)
│   │   
│   │   Example: "Deficit falls below $500B annualized through genuine spending cuts
│   │   (not accounting adjustments) sustained for 2+ quarters"
│   │
│   └── soft[]
│       Conditions that weaken the theory without killing it.
│       Each:
│         - condition
│         - metric
│         - threshold
│         - implication (what it means if triggered — theory weakened how?)
│         - severity ("minor" | "medium" | "major")
│           minor  = extends timeline or changes expression, mechanism unchanged
│                    (conviction discount: 0.10)
│           medium = weakens mechanism without removing it
│                    (conviction discount: 0.25)
│           major  = directly caps predicted magnitude or removes primary catalyst
│                    (conviction discount: 0.45)
│           Severity is pre-registered at the theory-module level.
│           The scoring pipeline applies discounts mechanically.
│
└── metadata
    ├── last_updated (ISO date)
    ├── update_type ("refinement" | "extension" | "new")
    ├── version (integer, increments on each update)
    └── confidence_in_specification
        How well-calibrated are the thresholds? "high" = thresholds
        tested against historical episodes. "medium" = reasonable
        estimates. "low" = placeholder, needs refinement.
```

---

## Activation Scoring Layer

**Design decision (settled in theories thread):** Theory inclusion in each generation pass is governed by a thin activation-scoring layer that runs BEFORE the generator. This is consistent with the falsification-engine philosophy — theory inclusion must be earned by current data conditions, not left to the generator's narrative-building tendencies.

### Scoring Tiers

- **Active:** Mechanism's activation conditions are substantially met by current data. The generator SHOULD use this theory.
- **Adjacent:** Some activation conditions met, or conditions are approaching thresholds. The generator MAY use at most one Adjacent theory as a wildcard — this preserves room for non-obvious mechanism chains.
- **Inactive:** Activation conditions are not met. The generator MUST NOT invoke this theory.

### Scoring Mechanics

Each theory module's `activation_conditions.indicators[]` are checked against the current data briefing. This is a mechanical pass — threshold comparisons, not LLM judgment. For two-phase modules, each phase is scored independently; Phase B (resolving/contraction/rotation) is checked first — if Active, Phase A is Inactive by definition. The output is a simple map:

```json
{
  "activation_scores": {
    "valuation_mean_reversion": "Active",
    "debt_cycle_short": { "phase_a_expansion": "Adjacent", "phase_b_contraction": "Inactive", "effective": "Adjacent" },
    "debt_cycle_long": "Active",
    "structural_fragility": { "phase_a_building": "Active", "phase_b_resolving": "Inactive", "effective": "Active (Building)" },
    "fiscal_dominance_liquidity": "Active",
    "fiscal_dominance_arithmetic": "Adjacent",
    "capital_flows": { "phase_a_accumulation": "Adjacent", "phase_b_rotation": "Inactive", "effective": "Adjacent" },
    "monetary_architecture": "Inactive"
  },
  "active_theories": ["valuation_mean_reversion", "debt_cycle_long", "structural_fragility (Building)", "fiscal_dominance_liquidity"],
  "adjacent_theories": ["debt_cycle_short (Expansion)", "fiscal_dominance_arithmetic", "capital_flows (Accumulation)"],
  "inactive_theories": ["monetary_architecture"],
  "generator_receives": "all Active + at most 1 Adjacent"
}
```

### What the Architecture Thread Needs to Build

A lightweight function (not an LLM call) that:
1. Takes the data briefing packet as input
2. Checks each theory module's `activation_conditions.indicators[]` against the data
3. Computes weighted activation scores
4. Returns the tier assignments

This can be a Python function or even a simple rule engine. It does not require intelligence — it requires consistency.

---

## How the Generator Uses Theory Modules

The generator receives:
- The data briefing packet (from the data agent)
- All Active theory modules (full content)
- At most one Adjacent theory module (as wildcard)

It produces hypotheses that:
1. Reference specific mechanisms from the invoked theories (by `theory_id`)
2. Inherit the falsifiers from those theories
3. State predictions that are testable against the data briefing

### Multi-Theory Hypotheses

The generator is permitted — and encouraged — to combine mechanisms from multiple Active theories into composite hypotheses. This is where the strongest macro insights come from: mechanism chains that explain how one dynamic feeds another.

**The composition constraint (critical for the evaluator to enforce):**

A multi-theory hypothesis is valid ONLY when combining theories:
- **Narrows** the prediction (more specific than either theory alone)
- **Sharpens** the causal chain (explains a transmission that neither theory captures independently)
- **Creates a clearer failure condition** (the combination is MORE falsifiable, not less)

If combining theories makes the hypothesis broader, more hedged, or harder to kill, it must be rejected as narrative padding.

**Example of valid composition:**

> "Fiscal dominance [theory 4] is extending the debt cycle [theory 2] beyond its normal expiry, which is amplifying Minsky-style concentration fragility [theory 3] in large-cap US equities. Prediction: when the turn comes, the drawdown will be 35-50% (larger than Minsky alone predicts, because fiscal extension has allowed fragility to compound beyond normal levels). Failure condition: if the deficit falls below $1T annualized OR if top-10 concentration declines below 25% without a drawdown, the compound hypothesis fails."

This is more specific, more testable, and more falsifiable than any of the three theories alone.

**Example of invalid composition:**

> "Valuations are stretched [theory 1], the debt cycle is late [theory 2], fragility is building [theory 3], fiscal spending is unsustainable [theory 4], EM is undervalued [theory 5], and the monetary system is restructuring [theory 6]. Therefore, a major regime change is coming."

This stacks theories to create an unfalsifiable super-narrative. It has no specific prediction, no timeline, and no failure condition. The evaluator should kill it.

---

## How the Evaluator Uses Theory Modules

The evaluator receives:
- The hypotheses (from the generator)
- The theory modules those hypotheses invoke
- The current data briefing

The evaluator checks four things:

1. **Evidence consistency:** Does current data support or contradict the hypothesis's predictions?

2. **Falsifier check:** Are any of the invoked theories' hard falsifiers currently triggered? If yes, any hypothesis depending on that theory is disconfirmed.

3. **Activation legitimacy:** Were the invoked theories legitimately Active or Adjacent at the time of generation? If the generator invoked an Inactive theory, the hypothesis is procedurally invalid.

4. **Composition integrity (for multi-theory hypotheses only):** Did the combination of theories produce a prediction that is more specific and more falsifiable than its components? If not, the hypothesis is rejected as narrative padding regardless of whether the evidence supports it.

---

## How the Theory Library Evolves

The theory library is a living system. Three types of changes occur:

### Refinement (most common)
- **What:** Updating an existing theory module — sharpening a mechanism description, adjusting an indicator threshold, adding a historical episode, improving a falsifier's specificity.
- **Trigger:** The user reads something that deepens understanding, or the system's outputs reveal that a theory's thresholds are miscalibrated.
- **Process:** Direct edit to the theory module. Version increments. No structural review needed.
- **Cadence:** Whenever warranted. Expect weekly to monthly.

### Extension (occasional)
- **What:** Adding a new theory module to the registry.
- **Trigger:** The user identifies a causal mechanism that no existing theory captures AND that mechanism would generate hypotheses the system currently cannot produce.
- **Quality gate:** A new theory must (a) describe a causal mechanism with a transmission chain, (b) produce testable predictions, and (c) be orthogonal to existing theories — meaning it generates hypotheses that no existing theory would produce. If it is really a sub-mechanism of an existing theory, it gets nested within that theory, not added as a new entry.
- **Process:** Draft in standard module format → review activation conditions and falsifiers for specificity → add to registry.
- **Cadence:** Rare. Perhaps 1-2 new theories per year.

### Inbox (low-friction capture)
- **What:** A scratchpad for raw intellectual inputs — articles read, podcast insights, emerging ideas — that haven't been processed into theory refinements or extensions yet.
- **Purpose:** Ensures that insights captured on-the-go (phone, Feedly, commute) don't get lost and eventually flow into the formal theory modules.
- **Process:** Tag each item to the relevant theory domain (or flag as "potential new theory"). Periodic review (quarterly) to integrate into modules or recognize new theory candidates.
- **The architecture should support this** as a simple append-only log per theory, reviewable through the frontend.

---

## What This Component Does NOT Do

To be explicit about scope boundaries:

- **Does not generate hypotheses.** That is the generator's job. The theories provide the mechanisms; the generator applies them to current data.
- **Does not evaluate hypotheses.** That is the evaluator's job. The theories provide the failure conditions; the evaluator checks them.
- **Does not produce trade ideas.** That is Layer 4 (action under asymmetry), which is human-governed.
- **Does not include decision heuristics.** Frameworks like Howard Marks's second-level thinking or Pabrai's asymmetric payoff analysis are decision frameworks, not causal mechanisms. They belong in the evaluator or action layer, not in the theory registry.
- **Does not include persona content.** The theories are mechanisms, not characters. The Macro Council's persona elements (Buffett's voice, Dalio's four-quadrant framing) are presentation choices, not analytical content. The architecture may choose to add persona flavor downstream, but the theory modules are persona-free.

---

## Summary for Architecture Design

| Question | Answer |
|----------|--------|
| How many theories? | Starting with 8 modules across 6 domains, extensible to N |
| Fixed or dynamic? | Dynamic registry with quality gate for new entries |
| What shape? | Structured modules with standardized interface (see schema above) |
| Two-phase modules? | 3 of 8 (`structural_fragility`, `debt_cycle_short`, `capital_flows`). Phases mutually exclusive, scored independently. |
| How does the generator get them? | Via activation-scoring layer: Active/Adjacent/Inactive (per-phase for two-phase modules) |
| Can theories combine? | Yes, under strict falsifiability constraint |
| Who enforces composition quality? | The evaluator, checking specificity gain |
| What format? | Structured objects (JSON-serializable) with prose mechanism descriptions |
| Who maintains them? | The user, with system support for inbox capture |
| What's the update cadence? | Refinements: weekly-monthly. Extensions: rare. Core mechanisms: quarterly review. |
| Are failure modes developed? | Yes — hard falsifiers (binary kill) and soft falsifiers (severity-weighted conviction discount: minor=0.10, medium=0.25, major=0.45) |
| What does the evaluator need most? | The `falsifiers` section — hard falsifiers for elimination, soft falsifiers with pre-registered severity for conviction scoring |
| What does the generator need most? | `core_mechanism.causal_chain` + `predictions_when_active` + `downstream_implications` |

---

*This contract will be updated as the theories thread resolves remaining design questions. The interface shape above is stable — field names and structure will not change unless both threads agree.*
