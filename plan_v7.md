# plan_v7.md — Falsification Engine v7 Implementation Plan

## Enhancement 5: Hypothesis Lifecycle Management

### Design Principle

**Gain continuity without losing adversarial pressure.**

A macro PM does not re-derive their view book from scratch every morning. They walk in with existing positions, review overnight developments, ask "has anything changed?", and adjust incrementally. The view book changes when the regime changes — not every session.

The Falsification Engine currently generates a nearly complete new set of hypotheses every run, even when the macro regime has not changed. This is wrong — but the fix must not turn the system into a confirmation engine that rubber-stamps its own prior output.

v7 gives hypotheses persistence, continuity, and age-appropriate evolution across runs, while strengthening — not weakening — the adversarial pressure on persistent hypotheses. Hypothesis continuity is paired with falsifier lifecycle management: staleness gates, emergent risk injection, and UNTESTABLE escalation provide new ammunition for the elimination pass with every cycle. Persistence does not buy easier treatment.

### Prerequisite

**v6 (Expression-Level Realization Engine) must be working before v7 is implemented.** Hypothesis continuity depends on realization data. Without `expression_return`, freshness labels, and payoff band tracking, the LLM has no signal about whether to CONFIRM, UPDATE, RENEW, or RETIRE. v6 Phase 1 (realization primitives) and Phase 2 (generation prompt: payoff bands) are the minimum prerequisites.

---

## What Exists (v1 through v6 — all complete or in build)

The full pipeline through v6:

```
Pass 1:   Activation scoring — 8 modules scored independently → Active / Adjacent / Inactive
Pass 1.5: Regime annotation — compute_regime_flags() from activation results → active flags list
Pass 2:   LLM generation — active theories + regime context + channel tags
            + prior hypothesis realization context
            + structured payoff band output requirement
            + continuation lineage output requirement
            → 7-9 hypotheses with channel tags, payoff bands, optional continuation links
Pass 3:   LLM elimination — adversarial attack + sector falsifier appendices + channel verification
            → SURVIVED / WOUNDED / KILLED + corrected channels + sector audit trail
Pass 4:   Mechanical conviction scoring (zero-LLM):
            Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
            Stage 2: DISCOUNTED = RAW × D_f × D_u × D_r + overlap_adjustment
            Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap, realization_cap) → max(FINAL, 5.0)
Pass 4.5: Realization overlay (zero-LLM, post-conviction):
            compute_expression_return() from entry prices + current prices
            compute_realization_ratios() against payoff band
            compute_time_elapsed_pct()
            compute_freshness_label() from primitives → [CALIBRATION] policy
            compute_realization_cap() from freshness label → feeds back into Stage 3
Pass 5:   Human decision layer — system never recommends trades or sizes
```

v6 adds: structured payoff bands, continuation lineage model, expression-level realization primitives, freshness labels, realization caps. See plan_v6.md for full specification.

**Empirical state (7 runs, 53 hypotheses):** Near-total hypothesis turnover every run (2 exact matches across 6 transitions). Declining kill rate (71% → 0% → 11%). Carry-forward infrastructure exists but is inert (`continuation_of = NULL` across all 53 hypotheses). Falsifiers regenerated fresh each run.

---

## What v7 Adds

Seven components, in dependency order:

| # | Component | Type | Pass |
|---|-----------|------|------|
| 1 | Thread + Instance identity model | Data architecture | All |
| 2 | Mechanical staleness gate | Zero-LLM computation | Pre-Pass 2 |
| 3 | CONFIRM / UPDATE / RENEW / RETIRE / NEW taxonomy | Generation prompt contract | Pass 2 |
| 4 | Falsifier lifecycle in elimination | Elimination prompt contract | Pass 3 |
| 5 | Emergent risk slot | Elimination prompt addition | Pass 3 |
| 6 | ESCALATED_UNTESTABLE | Mechanical computation | Pass 4 |
| 7 | Thread-centered frontend | Display | All views |

---

## Component 1: Thread + Instance Identity Model

### The Problem

The system currently generates IDs as `H-{run_ts}-{seq}` — fresh every run. There is no concept of "the same hypothesis across runs." The user sees a stream of changing IDs even when the underlying macro thesis is stable. The system appears to have no memory.

### Two-Level Identity

v7 introduces two levels of identity:

**Thread ID** — the stable, user-facing object. Created once when a hypothesis is first generated (via NEW). Persists as long as the hypothesis is CONFIRMed or UPDATEd. Format: `T-{first_run_ts}-{seq:02d}`.

**Instance ID** — the per-run database record. Created fresh each run for every hypothesis (including CONFIRMed ones). Carries per-run conviction scores, falsifier audits, realization snapshots, price data. Format: `H-{run_ts}-{seq:02d}`.

The thread is the first-class object in the UI. The instance chain is the audit trail within the thread.

### Thread Lifecycle

```
NEW hypothesis → creates Thread T-xxx-01 + Instance H-xxx-01
  │
  ├── CONFIRM → same Thread T-xxx-01 + new Instance H-yyy-01 (inherits thread)
  ├── UPDATE  → same Thread T-xxx-01 + new Instance H-yyy-02 (inherits thread)
  ├── RENEW   → creates NEW Thread T-yyy-03 + Instance H-yyy-03
  │              with `renewed_from = T-xxx-01` (thread-level link)
  │              old thread T-xxx-01 is RETIRED
  └── RETIRE  → Thread T-xxx-01 status = RETIRED
                 final instance is the archive record
```

### Thread Data Model

```typescript
interface HypothesisThread {
  // Identity
  thread_id: string;                  // T-{first_run_ts}-{seq:02d} — stable, user-facing
  status: "ACTIVE" | "RETIRED";       // ACTIVE while hypothesis is live

  // Realization anchor (pinned to originating instance)
  originating_instance_id: string;    // H-xxx from the first instance in this thread
  originating_run_id: string;         // run that created this thread
  entry_prices: Record<string, number>;  // from originating run's price snapshot
  payoff_band_lower: number;          // from originating instance
  payoff_band_upper: number;          // from originating instance
  timeframe_end_date: string;         // from originating instance (may be updated via UPDATE)

  // Lineage
  renewed_from: string | null;        // thread_id of parent thread (if created via RENEW)

  // Provenance
  source_theory: string;              // theory_id
  created_date: string;               // ISO date of first generation

  // Thread-level accumulators
  confirmation_count: number;         // how many consecutive CONFIRMs (resets on UPDATE)
  total_instances: number;            // total instances in the chain
}
```

### Instance Data Model (extends existing Hypothesis)

```typescript
interface HypothesisInstance {
  // Existing fields (all preserved)
  id: string;                         // H-{run_ts}-{seq:02d} — per-run, fresh each cycle
  run_id: string;
  short_name: string;
  full_statement: string;
  source_theory: string;
  status: "SURVIVED" | "WOUNDED" | "KILLED";
  conviction: number;
  predicted_assets: string[];
  asset_direction: Record<string, "LONG" | "SHORT">;
  timeframe: string;
  resolution_channel: string;
  // ... all existing v1-v6 fields preserved ...

  // v7 additions
  thread_id: string;                  // FK to HypothesisThread — REQUIRED
  lifecycle_action: "CONFIRM" | "UPDATE" | "RENEW" | "RETIRE" | "NEW";
  lifecycle_reasoning: string;        // LLM's stated reason for the action

  // Falsifier lifecycle fields (per-instance, per-falsifier)
  soft_falsifiers: {
    name: string;
    severity: "minor" | "medium" | "major";
    status: "CLEAR" | "TRIGGERED" | "UNTESTABLE" | "STALE" | "ESCALATED_UNTESTABLE";
    metric: string;
    threshold: string;
    staleness_flag: "STALE" | "TRIGGERED_BY_PASSAGE" | null;  // from staleness gate
    untestable_consecutive: number;    // thread-accumulated counter
    generation_market_value: number | null;  // market value when falsifier was first written
  }[];

  // Emergent risk slot
  emergent_risk: {
    condition: string;
    severity: "minor" | "medium" | "major";
    causal_chain: string;             // how it threatens the load-bearing mechanism
  } | null;                           // null = empty (default)
}
```

### Realization Anchor Rules

Realization is **thread-anchored**. The realization engine tracks the original call:

| Action | Entry prices | Payoff band | Realization | Thread |
|--------|-------------|-------------|-------------|--------|
| NEW | Current run snapshot | From generation | Starts | New thread created |
| CONFIRM | Originating instance | Originating instance | Continues | Same thread |
| UPDATE | Originating instance | Originating (timeframe may adjust) | Continues | Same thread |
| RENEW | Current run snapshot | From new generation | Restarts | New thread, `renewed_from` link |
| RETIRE | Frozen | Frozen | Stops | Thread status = RETIRED |

**Timeframe adjustment on UPDATE:** An UPDATE may revise `timeframe_end_date` on the thread when the LLM judges the timeline has shifted without changing the economic content of the call. The thread's `timeframe_end_date` is updated; `payoff_band_lower` and `payoff_band_upper` remain pinned to the originating instance. The realization engine uses the updated `timeframe_end_date` for `compute_time_elapsed_pct()`.

### What Defines UPDATE vs. RENEW

This is a judgment call made by the LLM, with the following contract:

**UPDATE** = same mechanism, same expression (tickers + directions), same magnitude band, same realization anchor. Only the following may change: framing, falsifier wording, modest timing refinement. The hypothesis is the same economic call from the same entry point.

**RENEW** = any change that alters the economic content of the call. Specifically:
- Magnitude band revision (the expected move has changed)
- Expression change (different tickers, or direction flip on a leg)
- Mechanism shift (the causal chain has materially changed)

**Timeframe-only revision** is usually UPDATE. But if the timeframe change materially alters the horizon regime or economic meaning of the call (e.g., a 2-month hypothesis extended to 9 months), it should be RENEW. The LLM states its reasoning; the human reviews.

The prompt contract makes this distinction explicit. The LLM must state which action it is taking and why. The system does not mechanically enforce the boundary — it relies on the LLM's contextual judgment, which is the LLM's native work.

---

## Component 2: Mechanical Staleness Gate

### The Problem

Hypothesis-level falsifiers are generated by the LLM at hypothesis creation and reference point-in-time market levels. A falsifier written when VIX = 14 setting "VIX below 18" as a test condition becomes meaningless when VIX = 32. The threshold was calibrated to a point-in-time market state, not to the mechanism being tested.

### Pipeline Placement

The staleness gate runs **pre-generation (before Pass 2)**, not at elimination time. The continuity decision (CONFIRM / UPDATE / RENEW / RETIRE) needs to know which falsifiers have gone stale. A hypothesis with 2 of 3 soft falsifiers STALE is a strong signal toward RENEW.

The elimination pass gets **second-look authority on consequence only** — it can upgrade STALE to TRIGGERED_BY_PASSAGE but cannot downgrade STALE back to CLEAR. This asymmetry prevents narrative rescue.

### The 2x Rule (Mechanical, Zero-LLM)

```python
def compute_staleness_flags(
    falsifier: dict,
    generation_market_value: float,   # market value when falsifier was first written
    current_market_value: float,      # current market value from briefing packet
) -> str | None:
    """
    Mechanical staleness detection for a single falsifier.

    If the market has moved more than 2x the distance between
    the generation-time value and the threshold, the falsifier is stale.

    Returns "STALE" or None.
    """
    threshold = _parse_threshold_value(falsifier["threshold"])
    if threshold is None or generation_market_value is None or current_market_value is None:
        return None

    distance_at_generation = abs(threshold - generation_market_value)
    if distance_at_generation <= 0:
        return None  # threshold was at market level — degenerate case

    distance_current_from_threshold = abs(current_market_value - threshold)

    if distance_current_from_threshold > 2.0 * distance_at_generation:
        return "STALE"

    return None
```

### What Gets Stored

Each soft falsifier on the instance records:
- `generation_market_value`: the market level for the falsifier's metric at the time the falsifier was first generated. For a CONFIRMed hypothesis, this is inherited from the originating instance (the falsifier's creation point, not the current run).
- `staleness_flag`: `"STALE"` | `"TRIGGERED_BY_PASSAGE"` | `null`.

### When Generation Market Values Are Captured

At hypothesis creation (NEW or RENEW), the system captures the current market value for each soft falsifier's metric from the briefing packet. These values are stored on the instance's falsifier records.

When a hypothesis is CONFIRMed or UPDATEd, the new instance inherits `generation_market_value` from the prior instance's falsifiers (because the falsifiers were created at the prior point in time).

### Staleness Gate Execution Flow

```
Pass 1:   Activation scoring
Pass 1.5: Regime annotation
 ↓
STALENESS GATE (new — mechanical, pre-generation):
  For each active thread:
    For each soft falsifier:
      1. Look up generation_market_value (from originating instance)
      2. Look up current_market_value (from current briefing packet)
      3. Apply 2x rule → flag as STALE or leave unflagged
    Attach staleness flags to the thread's falsifier summary
 ↓
Pass 2:   Generation (LLM sees staleness flags on prior threads)
```

### Evaluator Interpretation (Pass 3 — Tightly Bounded)

During elimination, the evaluator receives any STALE-flagged falsifiers and may classify the consequence:

| Evaluator classification | Meaning | Allowed? |
|-------------------------|---------|----------|
| **STALE** | Threshold is structurally irrelevant. No credit, no penalty. | Yes (default) |
| **TRIGGERED_BY_PASSAGE** | The market has blown past this threshold; the passage itself constitutes falsification of the load-bearing mechanism. | Yes (upgrade) |
| **CLEAR** | The threshold is still conceptually relevant despite market movement. | **No** (downgrade blocked) |

The evaluator must state reasoning for any TRIGGERED_BY_PASSAGE classification. A TRIGGERED_BY_PASSAGE falsifier is treated as a TRIGGERED soft falsifier for scoring purposes (feeds into D_f at its registered severity).

**Example:**
- VIX falsifier set at "below 18" when VIX was 14. VIX now 32.
- Staleness gate: STALE (distance 14 > 2 × distance 4).
- Evaluator judgment: TRIGGERED_BY_PASSAGE — "VIX has moved 18 points past the generation level, indicating a volatility regime shift that directly undermines the low-volatility-supportive environment this hypothesis requires."
- Scoring consequence: treated as TRIGGERED at the falsifier's registered severity.

---

## Component 3: CONFIRM / UPDATE / RENEW / RETIRE / NEW Taxonomy

### Generation Prompt Contract

The generation prompt receives active threads from the prior run. For each thread, the LLM must state exactly one action with reasoning.

**Action taxonomy:**

| Action | When | What happens to the thread | What happens to realization |
|--------|------|---------------------------|-----------------------------|
| **CONFIRM** | Mechanism unchanged, data consistent, falsifiers intact | Same thread, new instance. Same ID, same payoff band. | Continues from originating entry |
| **UPDATE** | Mechanism intact but framing, falsifier wording, or modest timing needs adjustment | Same thread, new instance. Narrative may change. Timeframe may shift. Magnitude band stays. | Continues from originating entry |
| **RENEW** | Economic content of the call has changed: magnitude, expression, or mechanism materially revised | Old thread RETIRED. New thread created with `renewed_from` link. New payoff band, new entry prices. | Restarts from current levels |
| **RETIRE** | Mechanism weakened, falsifier triggered, thesis no longer supported by data, or expression fully delivered | Thread status = RETIRED. Final instance is archive record. | Stops |
| **NEW** | Active theory not adequately represented in carried-forward set, or genuinely novel opportunity | New thread created. Fresh payoff band, fresh falsifiers. | Starts from current levels |

**Target: 7-9 total hypotheses (carried forward + new).**

**Default action is CONFIRM.** The LLM should not UPDATE unless it can state specifically what changed and why. The LLM should not RENEW unless it can state specifically what economic content changed. CONFIRM is the expectation in a stable regime. A run that is 5 CONFIRMs + 1 UPDATE + 1 NEW reflects a real macro PM's daily workflow. A run that is 0 CONFIRMs + 7 NEWs should only happen when the regime genuinely shifts.

### Generation Prompt Structure

```
--- ACTIVE THREADS (from prior run) ---

You are reviewing {N} active hypothesis threads from the prior run.
For each thread, you MUST state exactly one action: CONFIRM, UPDATE, RENEW, or RETIRE.
After processing all threads, you may generate NEW hypotheses for active theories
not adequately represented. Target: 7-9 total hypotheses (carried forward + new).

CONFIRM is the default action. Do not UPDATE unless you can state specifically what changed.
Do not RENEW unless the economic content of the call (magnitude, expression, mechanism) has changed.
If the expression should change (different tickers, same mechanism): that is RENEW, not UPDATE.

Thread T-{id}: "{short_name}"
  Source theory: {theory_id}
  Age: {N} runs (first generated {date})
  Expression: {LONG/SHORT tickers}
  Payoff band: {lower}-{upper}% through {end_date}
  Realization: {expression_return}% expression return
    {realization_vs_lower}x lower bound, {realization_vs_upper}x upper bound
    {time_elapsed_pct}% of time elapsed
  Freshness: {freshness_label}
  Falsifier status:
    Hard: {N} passed, {N} FAILED
    Soft:
      - "{name}" [{severity}]: {status} (metric: {value}, threshold: {threshold})
        {if STALE: "⚠ STALE — market moved past 2x threshold distance from generation level"}
        {if ESCALATED_UNTESTABLE: "⚠ ESCALATED — untestable for {N} consecutive passes"}
      - ...

  ACTION REQUIRED: State CONFIRM, UPDATE, RENEW, or RETIRE with reasoning.

  Output format:
    lifecycle_action: CONFIRM | UPDATE | RENEW | RETIRE
    lifecycle_reasoning: "[specific reason — what changed or didn't change]"
    {if UPDATE: state what changed in framing/timing}
    {if RENEW: provide full new hypothesis with new payoff band, new falsifiers}
    {if RETIRE: state which mechanism weakened or which falsifier was triggered}

---

{repeat for each active thread}

--- NEW HYPOTHESIS GENERATION ---

Active theories: {list with activation scores}
Adjacent theories (max 1 wildcard): {list}

After processing the threads above, generate NEW hypotheses ONLY for:
  - Active theories not represented in the carried-forward set
  - Theories where conditions have materially changed since the prior run

Each NEW hypothesis requires all standard fields including:
  - thread_id: (system assigns — leave blank)
  - lifecycle_action: NEW
  - full hypothesis specification (statement, assets, direction, falsifiers, payoff band)

Target: 7-9 total hypotheses across carried-forward + new.
```

### Output Schema for Generation Pass

```typescript
interface GenerationOutput {
  // For each prior thread:
  thread_actions: {
    thread_id: string;
    lifecycle_action: "CONFIRM" | "UPDATE" | "RENEW" | "RETIRE";
    lifecycle_reasoning: string;
    // If UPDATE — optional revised fields:
    revised_timeframe_end_date?: string;    // only if timing changed
    revised_short_name?: string;            // only if framing changed
    revised_full_statement?: string;        // only if framing changed
    // If RENEW — full new hypothesis:
    renewed_hypothesis?: NewHypothesis;     // complete specification
    // If RETIRE — no additional fields needed
  }[];

  // New hypotheses:
  new_hypotheses: NewHypothesis[];
}

interface NewHypothesis {
  // Standard generation fields (same as v6)
  short_name: string;
  full_statement: string;
  source_theory: string;
  predicted_assets: string[];
  asset_direction: Record<string, "LONG" | "SHORT">;
  resolution_channel: string;
  timeframe: string;
  hard_falsifiers: { condition: string }[];
  soft_falsifiers: {
    name: string;
    severity: "minor" | "medium" | "major";
    metric: string;
    threshold: string;
  }[];
  predicted_magnitude_lower: number;
  predicted_magnitude_upper: number;
  timeframe_end_date: string;
}
```

---

## Component 4: Falsifier Lifecycle in Elimination

### The Problem

The elimination pass currently audits each hypothesis's falsifiers against current data. With hypothesis continuity, the same falsifiers persist across runs. Three failure modes:

1. **Stale thresholds** — addressed by Component 2 (staleness gate)
2. **Missing attack surfaces** — addressed by Component 5 (emergent risk slot)
3. **UNTESTABLE accumulation** — addressed by Component 6 (ESCALATED_UNTESTABLE)

### Elimination Pass: Full Weight for All Hypotheses

All hypotheses face the full elimination pass, regardless of lifecycle action. There is no lighter review track for CONFIRMed hypotheses. The elimination prompt receives all hypotheses (carried-forward and new) and attacks each with equal rigor.

The elimination pass gains three new sources of ammunition for persistent hypotheses:

1. **Staleness flags** — already computed pre-generation. The evaluator sees STALE flags and interprets consequence (STALE or TRIGGERED_BY_PASSAGE).
2. **Emergent risk slot** — the evaluator fills one slot per hypothesis if a specific post-generation adverse development threatens the load-bearing mechanism.
3. **UNTESTABLE counters** — the evaluator sees how many consecutive passes each falsifier has been UNTESTABLE. High counters signal weak falsification coverage.

### Elimination Prompt Additions

```
--- FALSIFIER LIFECYCLE INSTRUCTIONS ---

For each hypothesis, you receive the falsifier set with lifecycle metadata.
In addition to the standard falsifier audit, apply these checks:

STALENESS INTERPRETATION:
  Falsifiers flagged ⚠ STALE by the mechanical staleness gate have had
  the market move more than 2x past their threshold distance from the
  generation-time level. For each STALE falsifier, classify the consequence:

  - STALE: The threshold is structurally irrelevant. Treat as UNTESTABLE
    for scoring (no credit for passing, no penalty for failing).
  - TRIGGERED_BY_PASSAGE: The market has blown past this threshold in a way
    that directly undermines the hypothesis's load-bearing mechanism.
    State the specific causal chain. Treat as TRIGGERED at registered severity.

  You may NOT classify a mechanically STALE falsifier as CLEAR. The mechanical
  detection is authoritative on whether the threshold has become irrelevant.
  Your judgment is on the consequence: irrelevant (STALE) or adversely
  significant (TRIGGERED_BY_PASSAGE).

EMERGENT RISK ASSESSMENT:
  For each hypothesis, assess whether a SPECIFIC adverse development has
  emerged since the hypothesis was generated (or last evaluated) that
  threatens its load-bearing mechanism.

  The emergent risk slot is EMPTY by default. Fill it ONLY if you can name:
    1. The specific development (a dated, named event or data release — not
       "trade war risks" or "geopolitical uncertainty")
    2. The causal chain to the load-bearing mechanism (how this development
       specifically threatens the channel through which this hypothesis resolves)
    3. A severity assessment (minor / medium / major)

  If you cannot name a specific development AND trace its causal chain,
  leave the slot empty. An empty slot is the correct outcome for most
  hypotheses in most runs.

  Output format:
    emergent_risk: {
      condition: "[specific named development]",
      severity: "minor" | "medium" | "major",
      causal_chain: "[how it threatens the load-bearing mechanism]"
    }
    OR
    emergent_risk: null

UNTESTABLE COUNTERS:
  Falsifiers marked with untestable_consecutive > 0 have been UNTESTABLE
  for that many consecutive passes. This is informational for your audit.
  At count >= 3, the system will mechanically escalate the falsifier.
  Consider whether a hypothesis with multiple high-count UNTESTABLE
  falsifiers has genuinely survived adversarial testing, or has survived
  vacuously because it could not be tested.

--- END FALSIFIER LIFECYCLE INSTRUCTIONS ---
```

### Evaluator Output Schema Additions

```typescript
interface EliminationOutput {
  // Existing fields (preserved)
  id: string;
  status: "SURVIVED" | "WOUNDED" | "KILLED";
  elimination_notes: string;

  // v7 additions per falsifier
  soft_falsifiers: {
    name: string;
    severity: "minor" | "medium" | "major";
    status: "CLEAR" | "TRIGGERED" | "UNTESTABLE" | "STALE";
    staleness_classification: "STALE" | "TRIGGERED_BY_PASSAGE" | null;
    staleness_reasoning: string | null;  // required if TRIGGERED_BY_PASSAGE
    metric: string;
    threshold: string;
  }[];

  // Emergent risk slot
  emergent_risk: {
    condition: string;
    severity: "minor" | "medium" | "major";
    causal_chain: string;
  } | null;
}
```

---

## Component 5: Emergent Risk Slot

### Design

One soft falsifier position per hypothesis is reserved for unmodeled adverse developments that emerge after generation. The elimination pass evaluator defines the condition at each cycle.

### Rules

1. **Empty by default.** The slot starts null each pass. The evaluator fills it only when warranted.
2. **Specific and named.** The evaluator must name a specific, dated development — not ambient risk. "April 2 tariff announcement" is valid. "Geopolitical uncertainty" is not.
3. **Causal chain required.** The evaluator must trace how the development threatens the hypothesis's load-bearing mechanism. If the causal chain cannot be stated, the slot stays empty.
4. **Variable severity.** The evaluator assigns severity (minor / medium / major) based on how directly the development threatens the mechanism. Uses the same severity framework as theory-level soft falsifiers.
5. **Resets each pass.** The emergent risk slot is a per-cycle attack surface, not a persistent thread property. If the same risk persists next pass, the evaluator re-enters it fresh with fresh reasoning. The persistence lives in the audit trail (the instance chain), not in the live slot.
6. **Scores through D_f.** A filled emergent risk slot is treated as an additional soft falsifier at the stated severity for the purpose of computing the soft falsifier discount D_f. It compounds multiplicatively with other falsifier discounts.

### Conviction Pipeline Integration

```python
# In compute_soft_falsifier_discount():
# Existing logic: for each TRIGGERED soft falsifier, apply severity discount
# v7 addition: if emergent_risk is not null, treat as additional TRIGGERED
# soft falsifier at emergent_risk.severity

SOFT_FALSIFIER_SEVERITY_DISCOUNTS = {
    "minor":  0.10,
    "medium": 0.25,
    "major":  0.45,
}

def compute_soft_falsifier_discount(soft_falsifiers, emergent_risk=None):
    """
    Multiplicative discount from triggered soft falsifiers.
    v7: emergent risk slot compounds into the same discount.
    """
    discount = 1.0

    for f in soft_falsifiers:
        if f["status"] == "TRIGGERED":
            discount *= (1.0 - SOFT_FALSIFIER_SEVERITY_DISCOUNTS[f["severity"]])
        # STALE falsifiers classified as TRIGGERED_BY_PASSAGE
        # are treated as TRIGGERED at their registered severity
        if f.get("staleness_classification") == "TRIGGERED_BY_PASSAGE":
            discount *= (1.0 - SOFT_FALSIFIER_SEVERITY_DISCOUNTS[f["severity"]])

    # Emergent risk slot
    if emergent_risk is not None:
        discount *= (1.0 - SOFT_FALSIFIER_SEVERITY_DISCOUNTS[emergent_risk["severity"]])

    return discount
```

---

## Component 6: ESCALATED_UNTESTABLE

### The Problem

Hypotheses whose soft falsifiers reference lagging data (quarterly earnings, GDP) mechanically survive because they cannot be tested. A hypothesis with 3/3 UNTESTABLE soft falsifiers has survived vacuously — it survived because we could not test it, not because it passed tests. Over time this creates survivorship bias toward hypotheses with lagging indicators.

### Mechanism: Step Function at N=3

```python
def compute_untestable_escalation(
    current_status: str,
    untestable_consecutive: int,
    ESCALATION_THRESHOLD: int = 3,  # [CALIBRATION]
) -> tuple[str, int]:
    """
    Track consecutive UNTESTABLE passes and escalate at threshold.

    Args:
        current_status: the falsifier's status after elimination pass audit
        untestable_consecutive: inherited from prior instance (0 for new falsifiers)

    Returns:
        (final_status, updated_consecutive_count)
    """
    if current_status == "UNTESTABLE":
        new_count = untestable_consecutive + 1
        if new_count >= ESCALATION_THRESHOLD:
            return ("ESCALATED_UNTESTABLE", new_count)
        return ("UNTESTABLE", new_count)
    else:
        # Falsifier became CLEAR or TRIGGERED — counter resets
        return (current_status, 0)
```

### ESCALATED_UNTESTABLE vs. STALE

These are **distinct states** with different meanings and different origins:

| State | Origin | Meaning | Scoring treatment |
|-------|--------|---------|-------------------|
| `STALE` | Mechanical staleness gate (2x rule) | Threshold is structurally irrelevant — market moved too far | No credit, no penalty (same as UNTESTABLE) |
| `ESCALATED_UNTESTABLE` | UNTESTABLE counter reaching N=3 | Falsifier has been untestable for 3+ consecutive passes — survivorship is vacuous | No credit, no penalty, PLUS progressive D_u penalty |
| `TRIGGERED_BY_PASSAGE` | Evaluator upgrade of STALE | Market passage constitutes falsification | Treated as TRIGGERED at registered severity |

Both STALE and ESCALATED_UNTESTABLE flag the hypothesis for human review. The distinction matters because the appropriate response is different:

- STALE threshold → the hypothesis likely needs RENEW (new falsifiers calibrated to current levels)
- ESCALATED_UNTESTABLE → the hypothesis may be fundamentally untestable with available data, or it may be waiting for a known data release

### Counter Inheritance

The `untestable_consecutive` counter is a thread-level accumulation carried through instances:

- **NEW / RENEW**: counter starts at 0 for all falsifiers
- **CONFIRM / UPDATE**: new instance inherits prior instance's counters per-falsifier (matched by falsifier name)
- If a falsifier flips from UNTESTABLE to CLEAR or TRIGGERED, counter resets to 0
- If a falsifier is newly added (on UPDATE), counter starts at 0

### Conviction Pipeline Integration

ESCALATED_UNTESTABLE compounds into D_u (the existing UNTESTABLE discount):

```python
# Existing D_u computation:
# Per UNTESTABLE falsifier: minor=0.05, medium=0.10, major=0.15

# v7 addition: ESCALATED_UNTESTABLE applies an additional penalty
# on top of the base UNTESTABLE discount

UNTESTABLE_ESCALATION_PENALTY = 0.05  # [CALIBRATION] additional per-pass penalty

def compute_untestable_discount(soft_falsifiers):
    """
    Multiplicative discount from UNTESTABLE and ESCALATED_UNTESTABLE falsifiers.
    """
    discount = 1.0

    UNTESTABLE_SEVERITY_DISCOUNTS = {
        "minor":  0.05,
        "medium": 0.10,
        "major":  0.15,
    }

    for f in soft_falsifiers:
        if f["status"] in ("UNTESTABLE", "ESCALATED_UNTESTABLE"):
            base = UNTESTABLE_SEVERITY_DISCOUNTS[f["severity"]]
            discount *= (1.0 - base)

        if f["status"] == "ESCALATED_UNTESTABLE":
            # Additional penalty for prolonged untestability
            # Compounds once at escalation (not per-pass after escalation)
            discount *= (1.0 - UNTESTABLE_ESCALATION_PENALTY)

    return discount
```

### Human Review Flag

When any falsifier reaches ESCALATED_UNTESTABLE, the hypothesis instance is flagged for human review in the Pipeline Audit view. The flag shows:

- Which falsifier(s) are escalated
- How many consecutive passes they have been UNTESTABLE
- Whether the falsifier references data with a known reporting schedule (informational note — the system does not track schedules mechanically in v7, but the human can recognize "this is waiting for Q2 GDP")

---

## Conviction Pipeline Reference (v7)

```
Pass 1:   Activation scoring — 8 modules scored independently → Active / Adjacent / Inactive
Pass 1.5: Regime annotation — compute_regime_flags() from activation results → active flags list

STALENESS GATE (new — mechanical, zero-LLM):
  For each active thread's soft falsifiers:
    Apply 2x rule → flag STALE or leave unflagged
  Attach staleness flags to thread context for generation prompt

Pass 2:   LLM generation — active theories + regime context + channel tags
            + prior thread context with realization data + staleness flags
            + CONFIRM / UPDATE / RENEW / RETIRE / NEW taxonomy
            → thread actions + new hypotheses

Pass 3:   LLM elimination — full adversarial attack on ALL hypotheses (no lighter track)
            + staleness interpretation (STALE → STALE or TRIGGERED_BY_PASSAGE, never CLEAR)
            + emergent risk slot (empty by default, specific development required)
            + sector falsifier appendices (unchanged from v4)
            + channel verification (unchanged from v3)
            → SURVIVED / WOUNDED / KILLED + falsifier audit trail + emergent risk

Pass 4:   Mechanical conviction scoring (zero-LLM):
            Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)    [unchanged]
            Stage 2: DISCOUNTED = RAW × D_f × D_u × D_r
                     D_f includes: triggered soft falsifiers + TRIGGERED_BY_PASSAGE
                                   + emergent risk slot (if filled)        [v7]
                     D_u includes: UNTESTABLE + ESCALATED_UNTESTABLE penalty [v7]
                     + overlap_adjustment
                     SCORE = DISCOUNTED × 10
            Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap, realization_cap)
                     → max(FINAL, 5.0)

Pass 4.5: Realization overlay (zero-LLM, post-conviction):
            Computed against thread's realization anchor (originating entry prices + payoff band)
            compute_expression_return()
            compute_realization_ratios()
            compute_time_elapsed_pct()  — uses thread's timeframe_end_date (may have been updated)
            compute_freshness_label()
            compute_realization_cap()

Pass 4.75: UNTESTABLE escalation (new — mechanical, zero-LLM):    [v7]
            For each soft falsifier on each instance:
              Inherit untestable_consecutive from prior instance
              If status == UNTESTABLE: increment counter
              If counter >= 3: reclassify as ESCALATED_UNTESTABLE
              If status == CLEAR or TRIGGERED: reset counter to 0
            Recompute D_u with escalation penalty
            Update conviction score if D_u changed

Pass 5:   Human decision layer — system never recommends trades or sizes
```

**What each component does natively:**

| Component | Does | Does NOT do |
|-----------|------|-------------|
| **LLM** | CONFIRM/UPDATE/RENEW/RETIRE decisions, adversarial attack, emergent risk identification, staleness consequence interpretation, falsifier generation | Scoring, threshold classification, kill rules, staleness detection, UNTESTABLE counting |
| **Math** | Activation, regime flags, staleness gate (2x rule), conviction scoring, D_f/D_u/D_r computation, realization primitives, freshness labels, UNTESTABLE escalation, caps | Contextual judgment, narrative, hypothesis generation |
| **Human** | Execution decisions, final review of ESCALATED_UNTESTABLE flags, thread review, override authority | Mechanical scoring, data fetching |

---

## Component 7: Thread-Centered Frontend

### Design Principle

The user experiences **one continuing thesis thread**, not a stream of changing IDs. The thread is the first-class object in every view. Instances are the audit trail inside the thread.

### Ledger View Changes

**Rows are threads, not instances.** Each row shows:

| Field | Source |
|-------|--------|
| Thread ID | `thread_id` (e.g., T-2026-090-01) |
| Short name | Latest instance's `short_name` |
| Source theory | Thread's `source_theory` |
| Status | Latest instance's `status` (SURVIVED / WOUNDED / KILLED) |
| Conviction | Latest instance's `conviction` score |
| Conviction delta | Current vs. prior instance's conviction |
| Freshness | Latest instance's freshness label |
| Thread age | Days since thread creation |
| Confirmation count | Thread's `confirmation_count` |
| Last action | Latest instance's `lifecycle_action` |
| Flags | Badges for STALE falsifiers, ESCALATED_UNTESTABLE, emergent risk filled |

**RETIRED threads** are shown with reduced opacity (0.55) below the active threads, unless the user toggles them off.

**Thread age** is displayed as a subtle badge: "3 runs" or "12 days". Long-lived threads are visually distinct from new ones.

### Thread Detail View (replaces Hypothesis Detail)

Opens as overlay (unchanged interaction pattern). Shows:

**Current state (default view):**
- Full hypothesis statement (from latest instance)
- Expression and direction
- Payoff band with realization progress bar (v6)
- Conviction score with full Stage 1-2-3 math breakdown
- All falsifiers with lifecycle metadata:
  - Status badges: CLEAR, TRIGGERED, UNTESTABLE, STALE, ESCALATED_UNTESTABLE
  - Staleness flag indicator (⚠ with reason)
  - UNTESTABLE consecutive counter
  - TRIGGERED_BY_PASSAGE indicator with evaluator reasoning
- Emergent risk slot (if filled): condition, severity, causal chain
- Elimination notes from latest pass

**Lineage panel (collapsible):**
- Timeline of all instances in the thread, newest first
- Each instance shows: run date, lifecycle action taken, conviction score, falsifier audit summary
- Instances are clickable to expand full detail
- RENEW links show the `renewed_from` thread for navigating lineage across thread boundaries

### Pipeline Run View Changes

The run output summary shows actions taken on threads:

```
Run R8 — April 4, 2026

Thread Actions:
  5 CONFIRM  |  1 UPDATE  |  0 RENEW  |  1 RETIRE  |  2 NEW

Threads:
  T-2026-090-01  "Breadth rotation RSP>QQQ"          CONFIRM    8/10  →  8/10
  T-2026-090-02  "Gold debasement hedge GLD>SPY"      CONFIRM    7/10  →  7/10
  T-2026-090-03  "Bear steepener SHY>TLT"             CONFIRM    6/10  →  6/10
  T-2026-091-01  "Energy-tech rotation XLE>XLK"        CONFIRM    7/10  →  7/10
  T-2026-091-02  "EM flows stall EEM<SPY"              CONFIRM    6/10  →  6/10
  T-2026-092-01  "Fiscal dom bear steepening STIP"     UPDATE     6/10  →  7/10
  T-2026-088-01  "Cash beats equities SHY>SPY"         RETIRE     5/10  →  —
  T-2026-092-02  "Oil shock energy outperformance"     NEW        —     →  7/10
  T-2026-092-03  "Debasement sustains gold miners"     NEW        —     →  6/10
```

### Pipeline Audit View Changes

The Audit Mode gains a new column in the walk-forward panel:

| Column | Source |
|--------|--------|
| Thread age | Days since thread creation |
| Lifecycle action | CONFIRM / UPDATE / RENEW / RETIRE / NEW |
| STALE count | Number of STALE-flagged falsifiers |
| ESCALATED count | Number of ESCALATED_UNTESTABLE falsifiers |
| Emergent risk | Filled / Empty |

---

## Data Model Changes

### New Table: `hypothesis_threads`

```sql
CREATE TABLE hypothesis_threads (
    thread_id TEXT PRIMARY KEY,           -- T-{first_run_ts}-{seq:02d}
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE | RETIRED
    originating_instance_id TEXT NOT NULL, -- FK to hypotheses
    originating_run_id TEXT NOT NULL,      -- FK to runs
    source_theory TEXT NOT NULL,
    created_date TEXT NOT NULL,            -- ISO date
    renewed_from TEXT,                     -- FK to hypothesis_threads (thread-level link)
    confirmation_count INTEGER NOT NULL DEFAULT 0,
    total_instances INTEGER NOT NULL DEFAULT 1,
    -- Realization anchor (copied from originating instance at thread creation)
    payoff_band_lower REAL,
    payoff_band_upper REAL,
    timeframe_end_date TEXT                -- may be updated by UPDATE action
);
```

### Hypothesis Table Additions (Migration 7)

```sql
ALTER TABLE hypotheses ADD COLUMN thread_id TEXT;              -- FK to hypothesis_threads
ALTER TABLE hypotheses ADD COLUMN lifecycle_action TEXT;        -- CONFIRM|UPDATE|RENEW|RETIRE|NEW
ALTER TABLE hypotheses ADD COLUMN lifecycle_reasoning TEXT;
ALTER TABLE hypotheses ADD COLUMN emergent_risk_condition TEXT;
ALTER TABLE hypotheses ADD COLUMN emergent_risk_severity TEXT;
ALTER TABLE hypotheses ADD COLUMN emergent_risk_causal_chain TEXT;
```

### Soft Falsifier Table Additions (or extended JSON)

Per soft falsifier on each instance:

```
staleness_flag TEXT,                -- STALE | TRIGGERED_BY_PASSAGE | null
staleness_reasoning TEXT,           -- evaluator reasoning (if TRIGGERED_BY_PASSAGE)
untestable_consecutive INTEGER DEFAULT 0,
generation_market_value REAL        -- market value at falsifier creation time
```

If soft falsifiers are stored as JSON on the hypothesis row, these fields are added to each falsifier object in the JSON array.

### Entry Prices for Threads

Thread entry prices are derived from `run_price_snapshots` of the originating run. No separate table needed — the thread stores `originating_run_id`, and the realization engine looks up entry prices from `run_price_snapshots WHERE run_id = originating_run_id`.

---

## Build Order

| Priority | Component | Description | Phase |
|----------|-----------|-------------|-------|
| 1 | Thread table + migration | Create `hypothesis_threads` table. Migration 7: add thread_id, lifecycle_action, lifecycle_reasoning, emergent risk fields to hypotheses. | Phase 1 |
| 2 | Thread creation on import | When importing generation results, create threads for NEW hypotheses. Link instances to threads. | Phase 1 |
| 3 | Staleness gate computation | `compute_staleness_flags()` in new `lifecycle.py`. Runs pre-generation on active threads. | Phase 1 |
| 4 | Generation prompt: thread context | Inject active thread summaries with realization + staleness into generation prompt. CONFIRM/UPDATE/RENEW/RETIRE/NEW taxonomy in prompt contract. | Phase 2 |
| 5 | Generation output parser: lifecycle actions | Parse lifecycle_action, lifecycle_reasoning. Handle CONFIRM (link to existing thread), UPDATE (link + update), RENEW (retire old thread + create new), RETIRE (close thread), NEW (create thread). | Phase 2 |
| 6 | Elimination prompt: falsifier lifecycle | Add staleness interpretation, emergent risk slot, UNTESTABLE counter display to elimination prompt. | Phase 3 |
| 7 | Elimination output parser: v7 fields | Parse staleness_classification, emergent_risk, per-falsifier lifecycle metadata. | Phase 3 |
| 8 | UNTESTABLE escalation | `compute_untestable_escalation()` in lifecycle.py. Runs post-elimination, pre-conviction. Counter inheritance logic. | Phase 3 |
| 9 | Conviction pipeline: emergent risk in D_f | Emergent risk slot treated as additional triggered soft falsifier in D_f computation. | Phase 3 |
| 10 | Conviction pipeline: ESCALATED_UNTESTABLE in D_u | ESCALATED_UNTESTABLE adds escalation penalty to D_u computation. | Phase 3 |
| 11 | Conviction pipeline: TRIGGERED_BY_PASSAGE in D_f | TRIGGERED_BY_PASSAGE treated as TRIGGERED at registered severity in D_f. | Phase 3 |
| 12 | Frontend: thread-centered Ledger | Rows = threads. Thread age badge. Last action badge. Retired thread display. | Phase 4 |
| 13 | Frontend: Thread Detail view | Current state + collapsible lineage panel. Falsifier lifecycle badges. Emergent risk display. | Phase 4 |
| 14 | Frontend: Pipeline Run summary | Action summary ("5 CONFIRMs, 1 UPDATE..."). Thread-based run output display. | Phase 4 |
| 15 | Frontend: Pipeline Audit columns | Thread age, lifecycle action, STALE count, ESCALATED count, emergent risk indicator. | Phase 4 |

### Implementation Notes for Claude Code

- **Priority 1-3 are data + computation.** New table, migration, pure functions. No prompt changes, no UI. New file `backend/lifecycle.py` with `compute_staleness_flags()` and `compute_untestable_escalation()`. Thread creation in the import pipeline (`pipeline.py`).
- **Priority 4-5 are generation prompt + parser.** The generation prompt changes are text additions to the prompt template in `prompt_builder.py`. The parser changes are in `output_parser.py` — new fields to extract. The thread-linking logic runs in `pipeline.py` at import time.
- **Priority 6-7 are elimination prompt + parser.** Text additions to the elimination prompt template. Parser gains staleness_classification, emergent_risk, and per-falsifier lifecycle fields.
- **Priority 8-11 are conviction pipeline.** Modifications to `conviction.py` — additional terms in D_f and D_u computation. UNTESTABLE escalation runs post-elimination.
- **Priority 12-15 are display-only frontend changes.** No new views. Thread-centered Ledger replaces instance-centered Ledger. Thread Detail replaces Hypothesis Detail. New columns in Pipeline Audit. New summary in Pipeline Run.

### Phase Boundaries (context-clearable)

| Phase | Components | Context needed |
|-------|-----------|---------------|
| Phase 1 | 1-3 | Database schema, lifecycle.py pure functions |
| Phase 2 | 4-5 | Prompt templates, output parser, import pipeline |
| Phase 3 | 6-11 | Elimination prompt, conviction pipeline |
| Phase 4 | 12-15 | Frontend components only |

Each phase is independently implementable and testable. Context can be cleared between phases.

---

## Testing Checklist

### Thread Identity
- [ ] NEW hypothesis creates a thread with `thread_id` = `T-{run_ts}-{seq}`
- [ ] CONFIRM creates new instance linked to existing thread
- [ ] UPDATE creates new instance linked to existing thread, updates thread's `timeframe_end_date` if revised
- [ ] RENEW retires old thread, creates new thread with `renewed_from` link, creates new instance
- [ ] RETIRE sets thread status = RETIRED
- [ ] Thread's `confirmation_count` increments on CONFIRM, resets on UPDATE
- [ ] Thread's `total_instances` increments on every action except RETIRE

### Realization Anchor
- [ ] CONFIRM: realization computed against originating instance's entry prices and payoff band
- [ ] UPDATE: realization computed against originating instance's entry prices and payoff band
- [ ] UPDATE with timeframe revision: `time_elapsed_pct` uses updated `timeframe_end_date`
- [ ] RENEW: realization computed against new thread's entry prices (current run snapshot)
- [ ] RETIRE: realization frozen at final values

### Staleness Gate
- [ ] 2x rule correctly flags STALE when market moved > 2× threshold distance
- [ ] 2x rule does not flag when market moved < 2× threshold distance
- [ ] STALE flag survives into generation prompt context
- [ ] STALE flag survives into elimination prompt for evaluator interpretation
- [ ] Evaluator can classify STALE as TRIGGERED_BY_PASSAGE
- [ ] Evaluator cannot classify STALE as CLEAR (parser rejects)
- [ ] TRIGGERED_BY_PASSAGE treated as TRIGGERED in D_f at registered severity
- [ ] `generation_market_value` inherited from prior instance on CONFIRM/UPDATE
- [ ] `generation_market_value` set fresh on NEW/RENEW

### UNTESTABLE Escalation
- [ ] Counter increments when falsifier remains UNTESTABLE
- [ ] Counter resets when falsifier becomes CLEAR or TRIGGERED
- [ ] Counter inherited from prior instance on CONFIRM/UPDATE
- [ ] Counter starts at 0 on NEW/RENEW
- [ ] At N=3, status becomes ESCALATED_UNTESTABLE
- [ ] ESCALATED_UNTESTABLE applies additional D_u penalty
- [ ] Hypothesis flagged for human review when any falsifier is ESCALATED_UNTESTABLE

### Emergent Risk Slot
- [ ] Slot defaults to null (empty)
- [ ] Filled slot requires condition, severity, and causal_chain (parser validates)
- [ ] Filled slot treated as additional TRIGGERED soft falsifier in D_f
- [ ] Slot resets to null each pass (not inherited from prior instance)
- [ ] Empty slot does not affect D_f

### Conviction Pipeline
- [ ] D_f correctly includes: triggered soft falsifiers + TRIGGERED_BY_PASSAGE + emergent risk
- [ ] D_u correctly includes: UNTESTABLE + ESCALATED_UNTESTABLE penalty
- [ ] Conviction floor at 5.0 still applies after all v7 discounts
- [ ] A hypothesis with 3 STALE falsifiers (all classified STALE, not TRIGGERED_BY_PASSAGE) has no D_f penalty from staleness
- [ ] A hypothesis with 1 TRIGGERED_BY_PASSAGE (medium severity) and 1 emergent risk (major) has D_f = (1-0.25) × (1-0.45) = 0.4125

### Frontend
- [ ] Ledger shows threads, not instances
- [ ] Thread Detail shows latest instance by default
- [ ] Lineage panel shows all instances in thread
- [ ] Pipeline Run view shows action summary
- [ ] RETIRED threads shown at reduced opacity
- [ ] STALE and ESCALATED_UNTESTABLE badges visible in Thread Detail

---

## What v7 Does NOT Do

1. **Does not build reporting-schedule-aware UNTESTABLE tracking.** The simple N=3 step function is sufficient for v7. Schedule-aware logic is a future enhancement if live runs show false positives from cyclically untestable falsifiers.

2. **Does not create a lighter elimination track for persistent hypotheses.** All hypotheses face full adversarial attack regardless of lifecycle action.

3. **Does not modify theory modules or sector appendices.** Theory-level falsifiers remain fixed. Only hypothesis-level falsifiers get lifecycle management.

4. **Does not mechanically enforce UPDATE vs. RENEW boundary.** The LLM makes the judgment; the human reviews. The prompt contract defines the distinction explicitly but does not automate enforcement.

5. **Does not change the copy-paste execution model.** Everything within a single Claude chat context window.

6. **Does not introduce automatic hypothesis retirement.** RETIRE is an LLM judgment, not a timer. A hypothesis is not automatically retired for age, low conviction, or EXPRESSED freshness. The human and LLM decide when a thesis is dead.

7. **Does not treat the UNTESTABLE escalation threshold as settled.** N=3 is marked `[CALIBRATION]` and is expected to be tuned from live run evidence.

8. **Does not collapse STALE and ESCALATED_UNTESTABLE into a single state.** These are distinct states with different origins, different meanings, and potentially different appropriate responses. The schema preserves the distinction.

---

## Implementation Status

### Phase 1: COMPLETE (Tasks 1-3) — 2026-04-03
- Task 1: Thread table + migration 8
- Task 2: Thread creation/linking on generation import (includes Task 5 — output parser lifecycle actions)
- Task 3: Staleness gate + UNTESTABLE escalation in lifecycle.py

### Phase 2: COMPLETE (Tasks 4-5) — 2026-04-03
- Task 4: Generation prompt with thread context + lifecycle taxonomy
- Task 5: Folded into Task 2 (output parser already handles v7 structured format)

### Phase 3: IN PROGRESS (Tasks 6-11)
- Task 6: COMPLETE (2026-04-03) — Elimination prompt falsifier lifecycle
  - `_falsifier_lifecycle_instructions()` in prompt_builder.py: staleness interpretation, emergent risk slot, UNTESTABLE counter instructions
  - `_elimination_output_schema()` gains `has_falsifier_lifecycle` flag: adds staleness_classification, staleness_reasoning per falsifier + emergent_risk per hypothesis
  - `_enrich_elimination_falsifiers()` in pipeline.py: runs staleness gate on hypothesis falsifiers using current briefing data, annotates with staleness_flag + current_market_value
  - Pipeline `get_elimination_prompt()` detects thread presence and auto-enables lifecycle mode
  - 27 new tests in test_elimination_lifecycle.py, 406 total passing
- Task 7: COMPLETE (2026-04-03) — Elimination output parser: v7 fields
  - `parse_elimination_output()` list-format path: accepts STALE status, carries through staleness_classification + staleness_reasoning per falsifier
  - `parse_elimination_output()` extracts emergent_risk object, flattens to emergent_risk_condition/severity/causal_chain on hypothesis dict
  - `import_elimination()` persists emergent_risk_condition/severity/causal_chain to HypothesisModel
  - 12 new tests in test_elimination_parser_v7.py, 418 total passing
- Task 8: COMPLETE (2026-04-03) — UNTESTABLE escalation post-elimination
  - `apply_untestable_escalation()` called in `import_elimination()` after parser sets statuses, before conviction scoring
  - Counters increment per UNTESTABLE pass; at N=3, status becomes ESCALATED_UNTESTABLE
  - ESCALATED_UNTESTABLE included in untestable_sf collection for D_u discount
  - Counter inheritance: CONFIRM/UPDATE carry forward; NEW/RENEW reset to 0 (via _inherit_falsifier_counters)
  - 25 new tests in test_untestable_escalation_pipeline.py, 443 total passing
- Task 9: COMPLETE (2026-04-03) — Conviction pipeline: emergent risk in D_f
  - In `import_elimination()`, after building triggered_sf from soft falsifiers, checks h.emergent_risk_severity — if truthy, appends {"severity": h.emergent_risk_severity} to triggered_sf
  - Compounds multiplicatively into D_f through existing SEVERITY_WEIGHTS (minor=0.10, medium=0.25, major=0.45)
  - No changes to conviction.py or schemas — emergent risk is just another entry in triggered_soft_falsifiers
  - 12 new tests in test_conviction_emergent_risk.py (7 engine + 5 pipeline assembly), 455 total passing
- Task 10: PENDING — Conviction pipeline: ESCALATED_UNTESTABLE in D_u
- Task 11: PENDING — Conviction pipeline: TRIGGERED_BY_PASSAGE in D_f

### Phase 4: PENDING (Tasks 12-15) — Frontend
