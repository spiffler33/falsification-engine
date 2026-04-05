# Theory Registry Reorganisation Spec

*Version 1.0 — April 2026*
*Status: Approved instruction set. Apply theory by theory. First theory sets the template.*

---

## Problem

Each theory module currently mixes four distinct layers into one file:

1. Invariant worldview (what the theory says about the world)
2. State/activation logic (how the system detects it)
3. Tactical market playbook (what to buy/sell/watch)
4. Run-time prompt instructions (how generator and evaluator use it)

These layers change at different rates, are audited by different processes, and serve different consumers. Mixing them makes every theory simultaneously too long to audit, too fragile to edit, and too tangled to extend.

---

## Target Architecture

### Per-Theory Package

Each theory becomes a directory with four files:

```
/theories/{theory_id}/
  CORE.md          — invariant theory (audited by reading, thinking, markets)
  ACTIVATION.md    — state detection spec (audited by data pipeline tests)
  TACTICAL.md      — market expression appendix (updated as themes evolve)
  PLAYBOOK.md      — run-time system instructions (updated as engine evolves)
```

### Registry-Level Files

```
/theories/
  INTERACTION_MATRIX.md   — single source of truth for all cross-theory relationships
  REGISTRY_INDEX.md       — summary table of all theories with stability class and status
```

---

## A. CORE.md — Invariant Theory

**Purpose:** The durable claim about how the world works. Readable in 10 minutes. Auditable against books, papers, market observation, and Substack without touching thresholds or ETFs.

**Required fields:**

| Field | Content |
|-------|---------|
| `theory_id` | Stable identifier |
| `core_claim` | 2-4 sentence statement of what the theory asserts. No hedging. No "may" or "could." State the claim. |
| `causal_mechanism` | The chain of cause and effect. Prose or numbered steps. No thresholds, no tickers, no ETFs. Pure economics. |
| `scope_limits` | Enumerated list (3-5 items). What the theory CANNOT do. Examples: "Does not predict timing." "Predicts magnitude conditional on catalyst from another theory." "Applies to US fiscal conditions only." |
| `key_assumptions` | What must be true for the theory to hold. These are the load-bearing premises. If one breaks, the theory needs revision. |
| `deep_falsifiers` | Conditions that would kill the theory ITSELF, not a hypothesis derived from it. State the condition and the logic. Do NOT assign severity here — severity is a scoring parameter, not a theory property. |
| `stability_class` | One of: **persistent** (unlikely to toggle within 5 years), **cyclical** (toggles on multi-year cycles), **tactical** (can toggle quarter to quarter). |
| `revision_triggers` | What would constitute a genuine revision to the invariant theory (not a threshold recalibration, not a tactical update — a real change to the core claim or mechanism). |

**Prohibited content in CORE.md:**
- Thresholds, weights, scoring parameters
- Ticker symbols, ETF names, asset class expressions
- Generator or evaluator instructions
- Current-theme implementation details (e.g., "AI capex cycle")
- Severity assignments on falsifiers
- Conditional predictions with other theories (these go in INTERACTION_MATRIX.md)

**Quality test:** If you can read CORE.md in 2027 without updating it, it's written correctly. If it references a specific market condition that might change, that content belongs elsewhere.

---

## B. ACTIVATION.md — State Detection Spec

**Purpose:** Machine-facing detection layer. Tells Pass 1 how to score activation. Every input is classified by data ownership. Every threshold has calibration rationale separated from the operational spec.

**Required fields:**

| Field | Content |
|-------|---------|
| `phases` | List of phases/states (e.g., Phase A: Building, Phase B: Resolving). Single-phase theories state "single-phase." |
| `transition_logic` | Rules for moving between phases. Mutual exclusivity rules. Sequencing (check Phase B first, then Phase A). Precedence. |
| `activation_table` | Per-phase table of scored indicators (see format below). |
| `activation_thresholds` | Score cutoffs for Active / Adjacent / Inactive per phase. |
| `context_flags` | Supplementary qualitative flags that are NOT scored but are surfaced to the generator. Clearly separated from scored indicators. |
| `falsifier_severity_assignments` | The severity classification (major / medium / minor) for each falsifier defined in CORE.md plus any state-level falsifiers. These are scoring pipeline parameters. |
| `state_falsifiers` | Conditions that would force a state transition or challenge the activation determination (distinct from theory-level falsifiers in CORE.md). Include severity. |

### Activation Table Format

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| ... | ... | ... | ... | ... | ... | ... |

### Data Ownership Categories

| Category | Definition | Implication |
|----------|-----------|-------------|
| `mechanical` | Single data feed, API-accessible, no human judgment | Fully automatable. Freshness = single source check. |
| `computed-mechanical` | Derived from 2+ mechanical feeds via arithmetic | Fully automatable BUT requires freshness checks on ALL inputs. If one feed is stale, the computation is silently wrong. List all dependencies explicitly. |
| `web-search` | Requires web search to obtain. Value changes with source quality. | Semi-automatable. The DATA AGENT fetches it, but the value may require interpretation. State the preferred source. |
| `qualitative` | Requires human or LLM judgment. No stable numeric source. | NOT mechanically scorable. Must be flagged as context, not scored as indicator. If currently scored, either find a mechanical proxy or move to context flags. |

**Calibration Rationale column:** Non-operational. Exists for the human auditor. Explains WHY the threshold is set where it is. Historical episodes referenced. What would cause recalibration. Think of it as a code comment — travels with the spec, is not the spec.

**Prohibited content in ACTIVATION.md:**
- Asset expressions, ETF mappings
- Generator or evaluator instructions
- Economic theory exposition (that's CORE.md)
- Cross-theory interaction logic (that's INTERACTION_MATRIX.md)

**Quality test:** A developer building the data pipeline should be able to implement Pass 1 scoring from ACTIVATION.md alone, without reading any other file.

---

## C. TACTICAL.md — Market Expression Appendix

**Purpose:** What the theory means for portfolio construction. This is the layer that evolves most frequently as themes change, new ETFs launch, sectors rotate, and the current macro environment shifts.

**Required fields:**

| Field | Content |
|-------|---------|
| `directional_predictions` | Per-phase or per-quadrant table of asset direction, magnitude range, timeframe, and mechanism. |
| `etf_mappings` | Specific instruments for each expression. |
| `sector_depth` | Sector-level analysis where relevant (e.g., P/TBV for banks, replacement cost for energy). |
| `regional_sequencing` | Where applicable: which countries/regions lead, which lag, what determines the sequence. |
| `relative_value_expressions` | Pair trades, spread trades, ratio trades. |
| `current_theme_specifics` | Implementation details tied to the current macro moment (e.g., "AI capex cycle" for capex/revenue mismatch). Explicitly labeled as current-theme so future updates know what to revise. `current_theme_specifics` is explicitly ephemeral. It may be empty. Its presence must never be required for CORE.md to remain valid.|
| `expression_monitors` | Short-horizon operational checks on trade expressions. These are NOT theory falsifiers — they monitor whether the trade is working, not whether the theory is true. |

**Prohibited content in TACTICAL.md:**
- Core economic theory (that's CORE.md)
- Activation thresholds or scoring parameters (that's ACTIVATION.md)
- Generator/evaluator instructions (that's PLAYBOOK.md)

**Quality test:** If the macro regime changes (e.g., AI capex theme ends, new theme emerges), TACTICAL.md gets updated. CORE.md and ACTIVATION.md do not.

---

## D. PLAYBOOK.md — Operational Run-Time Instructions

**Purpose:** How the generator and evaluator use this theory inside the falsification engine. This is system instruction, not economic theory.

**Required fields:**

| Field | Content |
|-------|---------|
| `generator_guidance` | What to produce when this theory is Active/Adjacent. What data to cite. What structure to use. |
| `generator_prohibitions` | Explicit "What NOT to claim" list. Common overclaims to avoid. |
| `evaluator_priority_checks` | Numbered list of what the evaluator checks first, second, third. |
| `evaluator_rejection_criteria` | Specific conditions under which the evaluator should reject a hypothesis invoking this theory. |
| `composition_rules` | Which theories this theory composes well with and how. Which compositions are prohibited or low-value. Pointer to INTERACTION_MATRIX.md for the authoritative pairwise logic. |
| `common_failure_modes` | Known ways the generator misuses this theory. Known ways the evaluator over- or under-penalizes. |

**Prohibited content in PLAYBOOK.md:**
- Core economic theory
- Activation thresholds
- Asset expressions (reference TACTICAL.md if needed)

**Quality test:** If the engine's prompt structure changes (e.g., Pass 3 elimination prompt is redesigned), PLAYBOOK.md gets updated. Nothing else does.

---

## E. INTERACTION_MATRIX.md — Registry-Level

**Purpose:** Single source of truth for all cross-theory relationships. Replaces the `downstream_implications` and `conditional predictions` sections currently duplicated across 8 theory files.

**Format:**

### Pairwise Interaction Table

| Theory A | Theory B | Relationship | Invariant Logic | Expression Detail Location |
|----------|----------|-------------|-----------------|---------------------------|
| structural_fragility (Building) | debt_cycle_short (Contraction) | A triggers B | Fragility break is a common catalyst for cycle turn. Break provides catalyst; cycle provides context for magnitude. | structural_fragility/TACTICAL.md, debt_cycle_short/TACTICAL.md |
| fiscal_dominance_liquidity | structural_fragility (Building) | A extends B | Net liquidity injection delays fragility resolution. Extends building phase 12-24 months. Amplifies eventual break magnitude. | fiscal_dominance_liquidity/TACTICAL.md |
| ... | ... | ... | ... | ... |

**Rules:**
- Each pair appears ONCE. Not twice.
- Invariant logic column contains the causal relationship that is always true.
- Expression detail column points to the TACTICAL.md file(s) that carry the specific trade implications.
- Relationship types: `reinforces`, `contradicts`, `triggers`, `extends`, `modifies`, `accelerates`.

---

## Reorganisation Process — Per Theory

Execute these steps for each theory. Do not batch.

### Step 1: Extract the invariant claim

Write the shortest serious version of what the theory says about the world. 2-4 sentences. If you can't state the claim in 4 sentences, the theory may be two theories — consider splitting. If a theory contains two distinct causal mechanisms that can activate independently, generate distinct falsifiers, or produce different state machines, flag it for possible split rather than forcing them into one CORE.md.

### Step 2: Classify every section

Go through the existing module line by line. Mark each paragraph, table, or subsection as one of:
- `I` — invariant (→ CORE.md)
- `A` — activation/state (→ ACTIVATION.md)
- `T` — tactical/expression (→ TACTICAL.md)
- `P` — playbook/operational (→ PLAYBOOK.md)
- `M` — interaction/composition (→ INTERACTION_MATRIX.md)
- `D` — duplicate (→ remove or consolidate)

### Step 3: Write the four files

Do not merely relabel sections. Actually reorganise. Tighten prose. Remove redundancy. Sharpen scope limits.

### Step 4: Scope discipline check

Read CORE.md and ask: "Does this theory claim more than it can actually deliver?" If yes, add explicit scope limits. If the module title implies broader scope than the actual mechanism, either tighten the title or define the narrower true core.

### Step 5: Data honesty check

For every indicator in ACTIVATION.md, confirm the data ownership classification is accurate. If an indicator is classified as `mechanical` but actually requires web search, reclassify. If an indicator is classified as `web-search` but is actually qualitative judgment dressed up as data, reclassify.

For every `computed-mechanical` indicator, list all input dependencies explicitly.

### Step 6: Falsifier hygiene check

Separate into three tiers:

| Tier | Location | What It Tests |
|------|----------|--------------|
| Theory-level falsifiers | CORE.md | Would the THEORY be wrong? |
| State-level falsifiers (soft + hard) | ACTIVATION.md | Would the ACTIVATION STATE be wrong? Severity assigned here. |
| Expression monitors | TACTICAL.md | Is the TRADE working? |

If a falsifier is currently testing the trade rather than the theory, move it to TACTICAL.md. If a falsifier is currently testing the theory but assigned a severity, split: condition → CORE.md, severity → ACTIVATION.md.

### Step 7: Interaction extraction

Remove all `downstream_implications`, `conditional predictions`, and `affects[]` sections from the theory file. Migrate the invariant causal logic to INTERACTION_MATRIX.md. Migrate the expression-level detail to the relevant TACTICAL.md file.

### Step 8: Internal consistency check

Verify:
- Every indicator in ACTIVATION.md has a data ownership classification
- Every falsifier in CORE.md has a corresponding severity assignment in ACTIVATION.md
- Every asset mentioned in TACTICAL.md has a mechanism linking it to CORE.md's causal chain
- PLAYBOOK.md's composition rules are consistent with INTERACTION_MATRIX.md
- No economic theory remains in PLAYBOOK.md
- No tickers remain in CORE.md
- No generator/evaluator instructions remain outside PLAYBOOK.md

---

## Downstream Integration Notes

After reorganisation, these engine components must be updated to reference the new file structure:

| Component | What Changes |
|-----------|-------------|
| Pass 1 activation layer | Reads ACTIVATION.md instead of the monolithic module. No change to scoring logic — only to where it finds thresholds and weights. |
| Pass 2 generation prompt | Reads CORE.md for theory context + TACTICAL.md for expression options + PLAYBOOK.md for behavioral guidance. Currently reads one file. |
| Pass 3 elimination prompt | Reads CORE.md for falsifiers + ACTIVATION.md for severity assignments + PLAYBOOK.md for evaluator instructions + INTERACTION_MATRIX.md for composition validation. |
| Pass 4 conviction scoring | Reads ACTIVATION.md for severity assignments (the multiplicative soft falsifier discounts). No change to scoring arithmetic. |
| Frontend / Observatory | Theory Observatory view may need to display CORE.md summary + ACTIVATION.md status. No change to data model — only to which files feed the display. |

**Do not attempt full downstream refactoring during per-theory reorganisation.** However, for each theory, note any immediate compatibility constraints or temporary adapters required so the reorganised package remains mappable to the current engine. After all 8 theories are reorganised, produce one registry-wide downstream integration plan.

---

## Essence preservation test
For each theory, after reorganisation, state:

- what the original theory was fundamentally trying to say
- what was preserved unchanged
- what was only moved, not altered
- what was narrowed for clarity
- what, if anything, was substantively revised

---

## Quality Bar

The reorganised version should feel:
- **Sharper** — each file has one job
- **More auditable** — CORE.md is short enough to reread quarterly
- **More maintainable** — updating a threshold doesn't touch theory; updating theory doesn't touch ETFs
- **More honest** — data ownership is explicit, scope limits are enumerated, falsifiers are properly tiered
- **System-native** — each file maps to a specific engine pass or human process

Without losing the intellectual force of the original theory.

---

## Required per-theory deliverables
For each theory, return:

Reorganisation diagnosis
Proposed directory/file contents
Essence preservation note
Open questions / judgment calls
Immediate downstream compatibility notes
Split recommendation, if any
Confidence in reorganisation quality

---
