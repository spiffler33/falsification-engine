# ECONOMIC THEORIES — Interface Contract for Architecture Thread

*This document is produced by the Economic Theories design thread. It specifies what the theories component delivers, what it requires, and how it interfaces with the rest of the Falsification Engine. The architecture thread should design around this contract.*

*Version: 2.0 — April 2026*
*Changelog: v2.0 — Replaced monolithic single-file module schema with four-file package structure. Added FalsifierEntry, IndicatorOwnership, and ContextFlag schemas. Added INTERACTION_MATRIX contract. Replaces downstream_implications and conditional predictions with registry-level pairwise interaction table. Data ownership classification now required for every indicator. Context flags separated from scored indicators.*
*Supersedes: v1.1 (March 2026). The v1.1 contract assumed a single-file theory module. That structure is archived alongside the monolithic modules.*

---

## What This Component Is

The economic theories component is a **registry of causal mechanism modules** that serve as the intellectual foundation of the Falsification Engine. Each module describes a macro-economic mechanism — not an opinion, not a persona, not a heuristic — with enough structure that the system can generate testable hypotheses from it and evaluate those hypotheses against empirical evidence.

The theories are what make hypotheses **falsifiable**. Without them, the system degenerates into an LLM producing plausible narratives without testable structure. Every hypothesis the system generates must trace back to a specific mechanism in a specific theory module, and every evaluation must reference the failure conditions that theory specifies.

---

## Current Theory Registry

The registry contains 8 theory modules across 6 intellectual domains. Two domains — debt cycles and fiscal dominance — are split into separate modules because their sub-mechanisms have distinct activation conditions, time horizons, and falsifiers. The architecture must support N modules, not assume 8. New theories can be added when they describe a causal mechanism (not just a heuristic), produce testable predictions, and are orthogonal to existing theories.

| # | Theory ID | Two-Phase? | Domain | Primary Mechanism | Stability Class |
|---|-----------|-----------|--------|-------------------|-----------------|
| 1 | `valuation_mean_reversion` | No | Valuation & Margin of Safety | Equity risk premium compression → capital reallocation → drawdown | cyclical |
| 2 | `debt_cycle_short` | **Yes** (Expansion / Contraction) | Debt Cycle Mechanics | 5-8 year credit expansion/contraction, controlled by rate policy | cyclical |
| 3 | `debt_cycle_long` | No | Debt Cycle Mechanics | 50-75 year debt accumulation, MP1→MP2→MP3 escalation | persistent |
| 4 | `structural_fragility` | **Yes** (Building / Resolving) | Minsky Dynamics | Stability → progressive risk-taking → concentration + leverage + non-linear break | cyclical |
| 5 | `fiscal_dominance_liquidity` | No | Fiscal Dominance | Net liquidity transmission: deficit → reserve injection → asset price correlation | persistent |
| 6 | `fiscal_dominance_arithmetic` | No | Fiscal Dominance | Interest expense trajectory → devaluation arithmetic → hard asset outperformance | persistent |
| 7 | `capital_flows` | **Yes** (Accumulation / Rotation) | Capital Flow Dynamics | Dollar gravity, EM mean reversion, China credit impulse | cyclical |
| 8 | `monetary_architecture` | No | Monetary System Architecture | Treasury-to-commodity collateral substitution; plumbing stress as leading indicator | persistent |

**Two-phase modules:** Three modules have distinct phases with opposite practical implications. Phases are mutually exclusive — the "resolving/contraction/rotation" phase is checked first; if Active, the "building/expansion/accumulation" phase is by definition Inactive. Each phase has its own activation conditions, predictions, and implications. The activation scoring layer must handle per-phase scoring.

**Stability classes:** Each theory's CORE.md declares a stability class that governs expected toggle frequency:
- **persistent** — unlikely to toggle within 5 years. The mechanism is structural.
- **cyclical** — toggles on multi-year cycles. The mechanism is recurring.
- **tactical** — can toggle quarter to quarter. The mechanism is responsive to near-term conditions.

---

## Theory Package Structure

Each theory is a directory containing four files. This is the canonical format — the monolithic single-file module is retired.

```
/theories/THEORY_MODULE_{theory_id}_v2/
  CORE.md          — invariant theory (audited by reading, thinking, markets)
  ACTIVATION.md    — state detection spec (audited by data pipeline tests)
  TACTICAL.md      — market expression appendix (updated as themes evolve)
  PLAYBOOK.md      — run-time system instructions (updated as engine evolves)
```

Registry-level files (not per-theory):

```
/theories/
  INTERACTION_MATRIX.md   — single source of truth for all cross-theory relationships
```

### Why Four Files

These layers change at different rates, are audited by different processes, and serve different consumers:

| File | Primary Consumer | Change Frequency | Audited By |
|------|-----------------|------------------|-----------|
| CORE.md | Human reader, generator (theory context) | Rarely (quarterly reread, multi-year revision) | Reading, thinking, market observation |
| ACTIVATION.md | Pass 1 activation layer, Pass 4 conviction scoring | Quarterly (threshold recalibration) | Data pipeline tests |
| TACTICAL.md | Generator (expression options), human (portfolio decisions) | Frequently (themes evolve, new ETFs) | Portfolio behavior |
| PLAYBOOK.md | Generator (behavioral guidance), evaluator (check criteria) | As engine evolves | Prompt effectiveness |

### Per-Pass File Consumption

| Pipeline Pass | Files Read |
|---------------|-----------|
| Pass 1: Activation (mechanical) | ACTIVATION.md only |
| Pass 2: Generation (LLM) | CORE.md + TACTICAL.md + PLAYBOOK.md |
| Pass 3: Elimination (LLM) | CORE.md + ACTIVATION.md + PLAYBOOK.md + INTERACTION_MATRIX.md |
| Pass 4: Conviction Scoring (mechanical) | ACTIVATION.md only (severity assignments) |

---

## A. CORE.md — Invariant Theory

The durable claim about how the world works. Readable in 10 minutes. Auditable against books, papers, and market observation without touching thresholds or ETFs.

### Required Fields

| Field | Content |
|-------|---------|
| `theory_id` | Stable identifier. Example: `structural_fragility` |
| `core_claim` | 2-4 sentence statement of what the theory asserts. No hedging. No "may" or "could." State the claim. |
| `causal_mechanism` | The chain of cause and effect. Prose or numbered steps. For two-phase theories, the mechanism is stated per phase. No thresholds, no tickers, no ETFs. Pure economics. |
| `scope_limits` | Enumerated list (3-5 items). What the theory CANNOT do. Examples: "Does not predict timing." "Applies to US fiscal conditions only." |
| `key_assumptions` | What must be true for the theory to hold. These are the load-bearing premises. If one breaks, the theory needs revision. |
| `deep_falsifiers` | Conditions that would kill the theory ITSELF, not a hypothesis derived from it. Each has an ID (H1, H2, ...), a condition, and the logic. Severity is NOT assigned here — severity is a scoring parameter that belongs in ACTIVATION.md. |
| `stability_class` | One of: `persistent`, `cyclical`, `tactical`. |
| `revision_triggers` | What would constitute a genuine revision to the invariant theory (not a threshold recalibration, not a tactical update). |

### Prohibited Content in CORE.md

- Thresholds, weights, scoring parameters
- Ticker symbols, ETF names, asset class expressions
- Generator or evaluator instructions
- Current-theme implementation details (e.g., "AI capex cycle")
- Severity assignments on falsifiers
- Conditional predictions with other theories (these go in INTERACTION_MATRIX.md)

### Quality Test

If you can read CORE.md in 2027 without updating it, it is written correctly. If it references a specific market condition that might change, that content belongs elsewhere.

---

## B. ACTIVATION.md — State Detection Spec

Machine-facing detection layer. Tells Pass 1 how to score activation. Every input is classified by data ownership. Every threshold has calibration rationale separated from the operational spec.

### Required Fields

| Field | Content |
|-------|---------|
| `phases` | List of phases/states (e.g., Phase A: Building, Phase B: Resolving). Single-phase theories state "single-phase." |
| `transition_logic` | Rules for moving between phases. Mutual exclusivity rules. Sequencing (check Phase B first, then Phase A). Precedence. |
| `activation_table` | Per-phase table of scored indicators (see format below). |
| `activation_thresholds` | Score cutoffs for Active / Adjacent / Inactive per phase. |
| `context_flags` | Supplementary qualitative flags that are NOT scored but are surfaced to the generator. Clearly separated from scored indicators. |
| `falsifier_severity_assignments` | The severity classification (major / medium / minor) and corresponding discount (0.45 / 0.25 / 0.10) for each deep falsifier from CORE.md, plus any state-level falsifiers. Hard falsifiers override activation to Inactive. |
| `state_falsifiers` | Conditions that would force a state transition or challenge the activation determination (distinct from theory-level falsifiers in CORE.md). Include severity. |

### Activation Table Format

Each phase has its own table. Indicator weights within a phase should sum to 1.00 (or less, if some indicators are context flags rather than scored indicators).

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| ... | ... | ... | ... | ... | ... | ... |

Column definitions:
- **Indicator:** Human-readable name.
- **Metric Source:** The data briefing field name, market ticker, or computation. Must match data briefing packet fields for mechanical indicators.
- **Data Ownership:** One of `mechanical`, `computed-mechanical`, `web-search`, `qualitative`. See IndicatorOwnership schema below.
- **Threshold:** Numeric value or descriptive condition. Kept as string (may be numeric or descriptive).
- **Direction:** One of `above`, `below`, `rising`, `falling`, `between`.
- **Weight:** 0.0 to 1.0. Per-phase weights should sum to 1.00.
- **Calibration Rationale:** Non-operational. Explains WHY the threshold is set where it is. Historical episodes referenced. What would cause recalibration. Travels with the spec, is not the spec.

### Prohibited Content in ACTIVATION.md

- Asset expressions, ETF mappings
- Generator or evaluator instructions
- Economic theory exposition (that is CORE.md)
- Cross-theory interaction logic (that is INTERACTION_MATRIX.md)

### Quality Test

A developer building the data pipeline should be able to implement Pass 1 scoring from ACTIVATION.md alone, without reading any other file.

---

## C. TACTICAL.md — Market Expression Appendix

What the theory means for portfolio construction. This is the layer that evolves most frequently as themes change, new ETFs launch, sectors rotate, and the current macro environment shifts.

### Required Fields

| Field | Content |
|-------|---------|
| `directional_predictions` | Per-phase table of asset direction, magnitude range, timeframe, and mechanism. |
| `etf_mappings` | Specific instruments for each expression. |
| `sector_depth` | Sector-level analysis where relevant (e.g., P/TBV for banks, replacement cost for energy). |
| `regional_sequencing` | Where applicable: which countries/regions lead, which lag, what determines the sequence. |
| `relative_value_expressions` | Pair trades, spread trades, ratio trades. |
| `current_theme_specifics` | Implementation details tied to the current macro moment. Explicitly labeled as ephemeral. Its presence is NEVER required for CORE.md to remain valid. May be empty. |
| `expression_monitors` | Short-horizon operational checks on trade expressions. These are NOT theory falsifiers — they monitor whether the trade is working, not whether the theory is true. |

### Prohibited Content in TACTICAL.md

- Core economic theory (that is CORE.md)
- Activation thresholds or scoring parameters (that is ACTIVATION.md)
- Generator/evaluator instructions (that is PLAYBOOK.md)

### Quality Test

If the macro regime changes (e.g., a dominant investment theme ends, a new one emerges), TACTICAL.md gets updated. CORE.md and ACTIVATION.md do not.

---

## D. PLAYBOOK.md — Operational Run-Time Instructions

How the generator and evaluator use this theory inside the falsification engine. This is system instruction, not economic theory.

### Required Fields

| Field | Content |
|-------|---------|
| `generator_guidance` | What to produce when this theory is Active/Adjacent. What data to cite. What structure to use. |
| `generator_prohibitions` | Explicit "What NOT to claim" list. Common overclaims to avoid. |
| `evaluator_priority_checks` | Numbered list of what the evaluator checks first, second, third. |
| `evaluator_rejection_criteria` | Specific conditions under which the evaluator should reject a hypothesis invoking this theory. |
| `composition_rules` | Which theories this theory composes well with and how. Which compositions are prohibited or low-value. Pointer to INTERACTION_MATRIX.md for the authoritative pairwise logic. |
| `common_failure_modes` | Known ways the generator misuses this theory. Known ways the evaluator over- or under-penalizes. |

### Prohibited Content in PLAYBOOK.md

- Core economic theory
- Activation thresholds
- Asset expressions (reference TACTICAL.md if needed)

### Quality Test

If the engine's prompt structure changes (e.g., Pass 3 elimination prompt is redesigned), PLAYBOOK.md gets updated. Nothing else does.

---

## FalsifierEntry Schema

The FalsifierEntry is a **pre-joined object** that combines data from two files: the condition and logic from CORE.md's `deep_falsifiers` section, and the classification and severity from ACTIVATION.md's `falsifier_severity_assignments` section. Downstream consumers (the evaluator, the conviction scoring pipeline) receive FalsifierEntry objects and do not need to know about the two-file split.

```
FalsifierEntry:
│
├── falsifier_id (string)
│   Unique identifier within a theory. Format: "H1", "H2" for hard; "S1", "S2" for soft.
│
├── condition (string)
│   What would need to be true. From CORE.md deep_falsifiers.
│   Example: "Market concentration declining organically (without preceding drawdown)"
│
├── logic (string)
│   Why this condition kills or wounds the theory. From CORE.md deep_falsifiers.
│   Example: "If passive reflexivity is unwinding without stress, the core
│   amplification mechanism is not operative."
│
├── classification ("hard" | "soft")
│   From ACTIVATION.md falsifier_severity_assignments.
│   Hard: if triggered, override activation to Inactive. The theory mechanism
│         is disconfirmed.
│   Soft: discount the conviction score but do not disqualify the theory.
│
├── severity (optional: "minor" | "medium" | "major")
│   For soft falsifiers only. None for hard.
│   From ACTIVATION.md falsifier_severity_assignments.
│   minor  = extends timeline or changes expression, mechanism unchanged
│   medium = weakens mechanism without removing it
│   major  = directly caps predicted magnitude or removes primary catalyst
│
└── discount (optional: float)
    For soft falsifiers only. None for hard.
    Derived mechanically from severity:
      minor  → 0.10
      medium → 0.25
      major  → 0.45
    Used in the conviction scoring formula:
      D_f = max(0.05, 1 - Σ(discount_i) for each triggered soft falsifier)
```

### Source Split

| Field | Source File | Source Section |
|-------|------------|---------------|
| `falsifier_id` | CORE.md | `deep_falsifiers` (ID assigned at theory level) |
| `condition` | CORE.md | `deep_falsifiers` |
| `logic` | CORE.md | `deep_falsifiers` |
| `classification` | ACTIVATION.md | `falsifier_severity_assignments` |
| `severity` | ACTIVATION.md | `falsifier_severity_assignments` |
| `discount` | Derived | `severity → {minor: 0.10, medium: 0.25, major: 0.45}` |

### Why the Split

CORE.md defines what would disprove the theory (a durable intellectual claim). ACTIVATION.md assigns how much that disproval costs in the scoring pipeline (an operational parameter that may be recalibrated). This separation means you can adjust the scoring impact of a falsifier without touching the theory itself.

---

## IndicatorOwnership Schema

Every scored indicator in ACTIVATION.md must declare its data ownership classification. This is not optional. The classification determines what the activation scoring layer can automate and where it must surface data quality warnings.

```
IndicatorOwnership:
│
├── indicator_name (string)
│   Human-readable name matching the ACTIVATION.md table.
│
├── metric_source (string)
│   The data field, ticker, or computation expression.
│
├── data_ownership ("mechanical" | "computed-mechanical" | "web-search" | "qualitative")
│   How the data reaches the system and what freshness guarantees it carries.
│
└── dependencies (optional: list[string])
    For computed-mechanical only. Lists all upstream data feeds.
    If ANY dependency is stale, the computation is silently wrong.
```

### Data Ownership Categories

| Category | Definition | Implication |
|----------|-----------|-------------|
| `mechanical` | Single data feed, API-accessible, no human judgment. | Fully automatable. Freshness = single source check. |
| `computed-mechanical` | Derived from 2+ mechanical feeds via arithmetic. | Fully automatable BUT requires freshness checks on ALL inputs. List all dependencies explicitly. |
| `web-search` | Requires web search to obtain. Value changes with source quality. | Semi-automatable. The data agent fetches it, but the value may require interpretation. State the preferred source. |
| `qualitative` | Requires human or LLM judgment. No stable numeric source. | NOT mechanically scorable. Must be classified as a context flag, not scored as an indicator. If currently scored, either find a mechanical proxy or move to context flags. |

### Scoring Rules by Ownership

- `mechanical` and `computed-mechanical` indicators are scored normally by Pass 1.
- `web-search` indicators are scored by Pass 1 when the data agent provides a value. If the value is absent or stale, the indicator is skipped and reported in `skipped_indicators`.
- `qualitative` indicators MUST NOT appear in the activation table. They belong in `context_flags`.

---

## ContextFlag Contract

Context flags are qualitative inputs that inform the generator and evaluator but are **explicitly excluded from mechanical activation scoring**. This separation prevents narrative-driven judgments from contaminating quantitative thresholds.

```
ContextFlag:
│
├── flag_name (string)
│   Descriptive name. Example: "Narrative shift"
│
├── source (string)
│   Where the flag's value comes from. Example: "Sentiment surveys, financial media"
│
├── data_ownership (string)
│   Typically "qualitative" or "web-search".
│
├── description (string)
│   What the flag measures and why it matters to the theory.
│   Example: "When 'buy the dip' sentiment shifts to capitulation — signals
│   that the forced-selling mechanism may be exhausting."
│
└── usage (string)
    How the generator or evaluator should use this flag.
    Example: "Phase B transition signal. If flagged while Phase B indicators
    are approaching thresholds, increases confidence in Phase B activation."
```

### Routing Rules

- Context flags are **surfaced to the generator** in Pass 2 (they provide qualitative context for hypothesis construction).
- Context flags are **surfaced to the evaluator** in Pass 3 (they provide qualitative context for evaluation).
- Context flags are **excluded from** Pass 1 activation scoring and Pass 4 conviction scoring.
- Context flags are carried on the `TheoryPackage.context_flags` field, not in the activation table.

---

## INTERACTION_MATRIX.md — Registry-Level Cross-Theory Relationships

The INTERACTION_MATRIX is the **single source of truth** for all cross-theory relationships. It replaces the `downstream_implications` and `conditional_predictions` sections that were previously duplicated across individual theory modules.

### Pairwise Interaction Table Format

| Column | Content |
|--------|---------|
| Theory A | First theory in the pair (with phase if relevant). |
| Theory B | Second theory in the pair (with phase if relevant). |
| Relationship | Type of interaction. May be compound (e.g., "A triggers B; B modifies A"). |
| Invariant Logic | The causal relationship that is ALWAYS true, regardless of current market conditions. This is permanent, auditable logic. No tickers, no ETFs, no current themes. |
| Expression Detail Location | Pointer to which TACTICAL.md files carry the specific trade implications. |

### Relationship Types

- `reinforces` — A strengthens B's mechanism or predictions.
- `contradicts` — A's mechanism works against B's mechanism.
- `triggers` — A's activation or resolution can initiate B.
- `extends` — A prolongs B's current phase.
- `modifies` — A changes how B's mechanism plays out (resolution type, magnitude, timeline).
- `accelerates` — A speeds up B's mechanism.
- `delays` — A slows B's mechanism.
- `contextualises` — A provides structural backdrop that changes interpretation of B.

Compound types are permitted: "A extends B; partially contradicts B".

### Rules

1. Each pair appears ONCE. Not twice. The directionality is stated in the relationship and invariant logic columns.
2. The invariant logic column contains permanent causal reasoning. If it references a specific market condition, that content belongs in TACTICAL.md.
3. Each entry must be cross-confirmed from both theories' perspectives. The invariant logic must be consistent with both CORE.md files.
4. Pairs with no direct mechanism are omitted. If the connection runs through an intermediary theory, state the intermediary in the Notes section rather than adding a row.

### Shared Upstream Cause Warnings

The INTERACTION_MATRIX includes a **Shared Upstream Cause Warnings** section that flags cases where two or more theories may appear to confirm each other but actually share an upstream cause. The engine must discount shared causes rather than mistaking them for independent confirmation.

Each warning specifies:
- The shared cause.
- The theories affected.
- A discounting note explaining the distinct contribution of each theory (what it adds beyond the shared cause).

These warnings are consumed by the **conviction scoring pipeline** (Pass 4, Stage 1, Convergence dimension) and by the **evaluator** (Pass 3, cross-theory attack). When multiple theories sharing an upstream cause are simultaneously Active, their convergence should be treated as one observation through multiple lenses, not as independent confirmation.

### Generator and Evaluator Filtering

The generator and evaluator use the INTERACTION_MATRIX differently:

**Generator (Pass 2):** When constructing multi-theory hypotheses, the generator references composition rules in PLAYBOOK.md (which point back to the INTERACTION_MATRIX). Valid compositions narrow predictions and sharpen falsifiability. The matrix's invariant logic provides the causal chain; the TACTICAL.md files provide the expression detail.

**Evaluator (Pass 3):** The evaluator uses the matrix for two checks:
1. **Composition integrity:** Did the generator's multi-theory hypothesis actually narrow the prediction? The matrix's invariant logic defines what a valid combination looks like.
2. **Cross-theory attack:** Does another Active theory's mechanism contradict this hypothesis? The evaluator checks the `contradicts` relationships in the matrix.

---

## Activation Scoring Layer

Theory inclusion in each generation pass is governed by a thin activation-scoring layer that runs BEFORE the generator. This is consistent with the falsification-engine philosophy — theory inclusion must be earned by current data conditions, not left to the generator's narrative-building tendencies.

### Scoring Tiers

- **Active** (score >= 0.60): Mechanism's activation conditions are substantially met by current data. The generator SHOULD use this theory.
- **Adjacent** (score 0.30-0.59): Some activation conditions met, or conditions are approaching thresholds. The generator MAY use at most one Adjacent theory as a wildcard.
- **Inactive** (score < 0.30): Activation conditions are not met. The generator MUST NOT invoke this theory.

### Scoring Mechanics

Each theory's ACTIVATION.md `activation_table` indicators are checked against the current data briefing. This is a mechanical pass — threshold comparisons, not LLM judgment.

For two-phase modules, each phase is scored independently. Phase B (resolving/contraction/rotation) is checked first — if Active, Phase A is Inactive by definition.

Indicators classified as `web-search` or `qualitative` in data ownership are skipped if no current value is available. Skipped indicators are reported in `skipped_indicators` so downstream consumers can assess data completeness.

### Hard Falsifier Override

If any hard falsifier (classification = "hard" in the FalsifierEntry registry) is currently triggered, the theory's activation is overridden to Inactive regardless of the indicator score.

### Output Shape

```json
{
  "activation_scores": {
    "valuation_mean_reversion": "Active",
    "debt_cycle_short": {
      "phase_a_expansion": "Adjacent",
      "phase_b_contraction": "Inactive",
      "effective": "Adjacent"
    },
    "structural_fragility": {
      "phase_a_building": "Active",
      "phase_b_resolving": "Inactive",
      "effective": "Active (Building)"
    }
  },
  "active_theories": ["valuation_mean_reversion", "structural_fragility (Building)"],
  "adjacent_theories": ["debt_cycle_short (Expansion)"],
  "inactive_theories": ["monetary_architecture"],
  "generator_receives": "all Active + at most 1 Adjacent"
}
```

### What the Architecture Thread Needs to Build

A lightweight function (not an LLM call) that:
1. Takes the data briefing packet as input
2. Reads each theory's ACTIVATION.md (via the parsed TheoryPackage)
3. Checks indicators against the data, respecting data ownership classifications
4. Checks hard falsifier state
5. Computes weighted activation scores
6. Returns the tier assignments

---

## How the Generator Uses Theory Packages

The generator receives:
- The data briefing packet (from the data agent)
- All Active theory packages: CORE.md (theory context) + TACTICAL.md (expression options) + PLAYBOOK.md (behavioral guidance)
- At most one Adjacent theory package (as wildcard)
- Context flags from Active theories (from ACTIVATION.md, surfaced but not scored)

It produces hypotheses that:
1. Reference specific mechanisms from the invoked theories (by `theory_id`)
2. Inherit the falsifiers from those theories (via the FalsifierEntry registry)
3. State predictions that are testable against the data briefing

### Multi-Theory Hypotheses

The generator is permitted — and encouraged — to combine mechanisms from multiple Active theories into composite hypotheses, guided by the `composition_rules` in each theory's PLAYBOOK.md and the INTERACTION_MATRIX.md.

**The composition constraint (critical for the evaluator to enforce):**

A multi-theory hypothesis is valid ONLY when combining theories:
- **Narrows** the prediction (more specific than either theory alone)
- **Sharpens** the causal chain (explains a transmission that neither theory captures independently)
- **Creates a clearer failure condition** (the combination is MORE falsifiable, not less)

If combining theories makes the hypothesis broader, more hedged, or harder to kill, it must be rejected as narrative padding.

**The generator must NOT:**
- Rank hypotheses by importance
- Recommend actions
- Produce hypotheses from Inactive theories
- Combine theories in ways that broaden rather than narrow predictions
- Ignore generator_prohibitions from PLAYBOOK.md

---

## How the Evaluator Uses Theory Packages

The evaluator receives:
- The hypotheses (from the generator)
- The theory packages for invoked theories: CORE.md (falsifier conditions) + ACTIVATION.md (severity assignments) + PLAYBOOK.md (evaluator instructions)
- The INTERACTION_MATRIX.md
- The current data briefing

The evaluator checks five things:

1. **Hard falsifier check:** Are any of the invoked theories' hard falsifiers (from the FalsifierEntry registry) currently triggered? If yes, any hypothesis depending on that theory is KILLED.

2. **Soft falsifier state:** Which soft falsifiers are triggered? Report count and which ones. Do NOT assess severity — severity is pre-registered in ACTIVATION.md and applied mechanically in Pass 4.

3. **Cross-theory attack:** Does another Active theory's mechanism contradict this hypothesis? Use the INTERACTION_MATRIX to identify contradictions.

4. **Evidence quality assessment:** Is the supporting evidence strong or weak? Grade: direct market data > high-quality macro data > proxies > narrative inference.

5. **Composition integrity (multi-theory hypotheses only):** Did combining theories produce a prediction that is more specific and more falsifiable than its components? If not, KILLED as narrative padding. Use the INTERACTION_MATRIX's invariant logic to validate the combination.

**The evaluator must NOT:**
- Assign conviction scores
- Decide whether soft falsifiers are "serious enough" to kill
- Recommend which survivors to act on
- Soften its attacks

Output per hypothesis: SURVIVED / WOUNDED / KILLED + full reasoning chain.

---

## TheoryPackage Schema

The TheoryPackage is the complete parsed representation of a four-file theory directory. It is the unit that the loader delivers to all downstream consumers.

```
TheoryPackage:
│
├── theory_id (string)
│   Extracted from CORE.md content, not from directory name.
│
├── core (string)
│   Full text of CORE.md.
│
├── activation (string)
│   Full text of ACTIVATION.md.
│
├── tactical (string)
│   Full text of TACTICAL.md.
│
├── playbook (string)
│   Full text of PLAYBOOK.md.
│
├── falsifier_registry (list[FalsifierEntry])
│   Pre-joined falsifiers. Condition/logic from CORE.md, classification/severity
│   from ACTIVATION.md. See FalsifierEntry schema above.
│
├── data_ownership (list[IndicatorOwnership])
│   Data ownership classification for every scored indicator in ACTIVATION.md.
│   See IndicatorOwnership schema above.
│
└── context_flags (list[ContextFlag])
    Qualitative flags from ACTIVATION.md. Routed to generator/evaluator,
    excluded from mechanical scoring. See ContextFlag contract above.
```

### Backward Compatibility

The v1 `TheoryModule` schema (single-file, monolithic) remains available for the legacy monolithic modules. The `TheoryPackage` is the canonical schema for v2 four-file packages. The activation scoring layer, prompt builder, and conviction pipeline accept both schemas during the migration period. After migration is complete, the `TheoryModule` schema is retired.

---

## How the Theory Library Evolves

Three types of changes occur, each scoped to specific files:

### Refinement (most common)
- **What:** Updating an existing theory — sharpening a mechanism, adjusting a threshold, improving a falsifier's specificity.
- **Scope:** Threshold changes → ACTIVATION.md only. Expression changes → TACTICAL.md only. Mechanism clarification → CORE.md. Prompt tuning → PLAYBOOK.md. No single refinement should require touching all four files.
- **Cadence:** Whenever warranted. Expect weekly to monthly.

### Extension (occasional)
- **What:** Adding a new theory module to the registry.
- **Quality gate:** A new theory must (a) describe a causal mechanism with a transmission chain, (b) produce testable predictions, and (c) be orthogonal to existing theories. If it is really a sub-mechanism of an existing theory, it gets nested within that theory, not added as a new entry.
- **Process:** Draft all four files in standard format → add pairwise interactions to INTERACTION_MATRIX.md → cross-confirm from both directions.
- **Cadence:** Rare. Perhaps 1-2 new theories per year.

### Inbox (low-friction capture)
- **What:** A scratchpad for raw intellectual inputs — articles, podcast insights, emerging ideas — that have not been processed into theory refinements or extensions.
- **Process:** Tag each item to the relevant theory domain (or flag as "potential new theory"). Periodic review to integrate into modules or recognize new theory candidates.
- **The architecture supports this** as a simple append-only log per theory, reviewable through the frontend.

---

## Internal Consistency Requirements

For each theory package, the following invariants must hold:

1. Every indicator in ACTIVATION.md has a data ownership classification.
2. Every deep falsifier in CORE.md has a corresponding severity assignment in ACTIVATION.md.
3. Every asset mentioned in TACTICAL.md has a mechanism linking it to CORE.md's causal chain.
4. PLAYBOOK.md's composition rules are consistent with INTERACTION_MATRIX.md.
5. No economic theory exposition remains in PLAYBOOK.md.
6. No ticker symbols remain in CORE.md.
7. No generator/evaluator instructions remain outside PLAYBOOK.md.
8. Per-phase indicator weights sum to 1.00 (or less, if some indicators were moved to context flags).
9. No `qualitative` data ownership indicators appear in the scored activation table.

---

## What This Component Does NOT Do

- **Does not generate hypotheses.** That is the generator's job. The theories provide the mechanisms; the generator applies them to current data.
- **Does not evaluate hypotheses.** That is the evaluator's job. The theories provide the failure conditions; the evaluator checks them.
- **Does not produce trade ideas.** That is the human decision layer.
- **Does not include decision heuristics.** Frameworks like second-level thinking or asymmetric payoff analysis are decision frameworks, not causal mechanisms. They belong in the evaluator or action layer, not in the theory registry.
- **Does not include persona content.** The theories are mechanisms, not characters. The theory modules are persona-free.

---

## Summary for Architecture Design

| Question | Answer |
|----------|--------|
| How many theories? | Starting with 8 modules across 6 domains, extensible to N |
| Fixed or dynamic? | Dynamic registry with quality gate for new entries |
| What shape? | Four-file packages (CORE, ACTIVATION, TACTICAL, PLAYBOOK) with pre-joined FalsifierEntry registry |
| Two-phase modules? | 3 of 8 (`structural_fragility`, `debt_cycle_short`, `capital_flows`). Phases mutually exclusive, scored independently. |
| How does the generator get them? | Via activation-scoring layer: Active/Adjacent/Inactive. Generator receives CORE + TACTICAL + PLAYBOOK for Active theories. |
| How does the evaluator get them? | Evaluator receives CORE + ACTIVATION + PLAYBOOK + INTERACTION_MATRIX for invoked theories. |
| Can theories combine? | Yes, under strict falsifiability constraint. INTERACTION_MATRIX is the authority. |
| Who enforces composition quality? | The evaluator, checking specificity gain against INTERACTION_MATRIX invariant logic. |
| What format? | Structured markdown parsed into TheoryPackage (Pydantic model). Full text preserved for prompt building. |
| Who maintains them? | The user, with system support for inbox capture. |
| What's the update cadence? | Refinements: weekly-monthly. Extensions: rare. Core mechanisms: quarterly review. |
| Are failure modes developed? | Yes — FalsifierEntry: hard (binary kill, override to Inactive) and soft (severity-weighted conviction discount: minor=0.10, medium=0.25, major=0.45) |
| How is data quality tracked? | IndicatorOwnership schema: mechanical / computed-mechanical / web-search / qualitative |
| How are qualitative inputs handled? | ContextFlag schema: routed to generator/evaluator, excluded from mechanical scoring |
| Where are cross-theory relationships? | INTERACTION_MATRIX.md with pairwise interaction table + shared upstream cause warnings |

---

*This contract will be updated as the engine evolves. The four-file package structure and per-file field requirements are stable. Schema field names will not change unless both the theories thread and architecture thread agree.*
