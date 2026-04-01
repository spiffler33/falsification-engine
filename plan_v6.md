# plan_v6.md — Falsification Engine v6 Implementation Plan

## Enhancement 4: Expression-Level Realization Engine

### Design Principle

**The payoff band is for audit, not automatic liquidation.**

The realization engine exists to prevent the system from presenting already-delivered trades as fresh opportunities. It is a new kind of falsification — not "the thesis is wrong" but "the thesis is right and the trade is done."

The system must keep three layers separate:

- **Hypothesis** = the causal mechanism claim (attacked by falsifiers in Pass 3)
- **Expression** = the ETF spread/pair chosen to represent it (tracked by the realization engine)
- **Execution** = sizing, stops, entry/exit timing (human Pass 5 decision, never mechanized)

The realization engine operates at the expression layer. It does not kill hypotheses, does not recommend exits, and does not become a portfolio optimizer.

### Architectural Separation: Primitives vs. Policy

v6 enforces a strict two-layer separation:

**Layer 1 — Realization Primitives.** Mechanical, zero-LLM, zero-policy. Computed fields that answer factual questions: how much of the predicted move has been delivered, how much of the holding window has elapsed, what is the lineage of this hypothesis. These are architectural. They do not change under recalibration.

**Layer 2 — Provisional Policy.** Configurable rules that consume primitives and produce freshness labels and optional conviction caps. Every threshold, label boundary, and cap value in this layer is explicitly marked `[CALIBRATION]` and is expected to be tuned from live runs. The policy layer is a starting configuration, not settled truth.

---

## What Exists (v1 through v5 — all complete)

The full pipeline through v5:

```
Pass 1:   Activation scoring — 8 modules scored independently → Active / Adjacent / Inactive
Pass 1.5: Regime annotation — compute_regime_flags() from activation results → active flags list
Pass 2:   LLM generation — active theories + regime context + channel tags → 7-9 hypotheses
Pass 3:   LLM elimination — adversarial attack + sector falsifier appendices + channel verification
            → SURVIVED / WOUNDED / KILLED + corrected channels + sector audit trail
Pass 4:   Mechanical conviction scoring (zero-LLM):
            Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
            Stage 2: DISCOUNTED = RAW × D_f × D_o × D_r  →  SCORE = DISCOUNTED × 10
            Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap)  →  max(FINAL, 5.0)
Pass 5:   Human decision layer — system never recommends trades or sizes
```

v5 adds: briefing packet snapshots per run, market price snapshots per run (`run_price_snapshots`), outcome tracking (CORRECT / INCORRECT / PARTIAL / EXPIRED), Run Archive panel, Walk-Forward panel with direction-aware deltas, outcome badges on Ledger.

---

## The Problem v6 Solves

The pipeline has no concept of "how much of the predicted move has already been delivered." This creates a systematic momentum-chasing bias:

- **Generation pass** sets magnitude predictions cumulative from hypothesis inception. Once the move has happened, the residual expected return approaches zero, but the generation pass does not re-baseline.
- **Elimination pass** checks "is the thesis dead?" — none of the falsifiers ask "has the predicted move already been delivered?"
- **Conviction scoring** actively makes this worse. Stage 1 dimensions (support_strength, evidence_quality, convergence) all score higher when the trade is working, because confirming price action looks like strong evidence. The system assigns peak conviction to exhausted trades.

Live example: DBC/QQQ spread up ~36 points in 3 months against a 15-30% prediction. System scored it as "strongest-performing hypothesis" with 10/10 conviction. The trade was already delivered. Meanwhile STIP/TLT at +2.6% against a 5-12% prediction — the trade with actual residual expected value — scored lower.

---

## What v6 Adds

### Layer 1: Realization Primitives

Six computed primitives. All mechanical, all zero-LLM, all stored as fields on the hypothesis data model.

### Layer 2: Provisional Policy

Freshness labels and realization caps computed from primitives. All thresholds marked `[CALIBRATION]`.

### Generation Prompt Changes

Structured payoff band fields at generation time. Prior-hypothesis realization data passed to generation prompt. Continuation lineage model.

### Frontend Surfacing

Realization primitives, freshness overlay, continuation lineage, and payoff band progress visible in Ledger, Hypothesis Detail, and Pipeline Audit views.

---

## Component 1: Expression-Level Realization Computation

### The Core Function

```python
def compute_expression_return(
    predicted_assets: list[str],
    asset_direction: dict[str, str],       # {"DBC": "LONG", "QQQ": "SHORT"}
    entry_prices: dict[str, float],        # from run_price_snapshots of originating run
    current_prices: dict[str, float],      # from walk-forward price fetch
) -> float | None:
    """
    Compute the expression-level return as the equal-weight mean
    of direction-adjusted leg returns.

    For a LONG leg:  leg_return = (current - entry) / entry
    For a SHORT leg: leg_return = (entry - current) / entry
        (equivalently: -1 * raw_return)

    Expression return = mean(all leg returns)

    Returns None if any ticker is missing from entry_prices or current_prices.
    """
    if not predicted_assets:
        return None

    leg_returns = []
    for ticker in predicted_assets:
        if ticker not in entry_prices or ticker not in current_prices:
            return None

        entry = entry_prices[ticker]
        current = current_prices[ticker]

        if entry <= 0:
            return None

        raw_return = (current - entry) / entry

        direction = asset_direction.get(ticker, "LONG")
        if direction == "SHORT":
            raw_return = -raw_return

        leg_returns.append(raw_return)

    return sum(leg_returns) / len(leg_returns)
```

### Design Decisions (settled)

1. **Equal-weight across legs.** The hypothesis expresses a view on relative performance, not a sized trade. Dollar-weighting is an execution (Pass 5) decision. Equal-weight is the correct abstraction for the hypothesis layer.

2. **Entry prices from the originating run.** The `run_price_snapshots` table (v5) captures ticker prices at run time. The realization engine uses the snapshot from the **first run** that generated the hypothesis — the price at hypothesis inception. If a hypothesis survives across multiple runs, the entry price stays pinned to the original run.

3. **Current prices from walk-forward machinery.** Reuse the existing `_fetch_current_price()` from trades.py (Yahoo v8 chart API via curl). No separate pricing path. Prices are fetched on demand when the realization computation is invoked (at run time and when the walk-forward endpoint is called).

4. **The formula already exists in v5.** The walk-forward delta computation does direction-aware returns per-leg. The expression-level return is the mean across legs of those same per-leg deltas. This is aggregation, not reinvention.

### Realization Ratios

```python
def compute_realization_ratios(
    expression_return: float,
    predicted_magnitude_lower: float,
    predicted_magnitude_upper: float,
) -> dict:
    """
    Compare expression return against the payoff band.

    Returns:
        realization_vs_lower: expression_return / predicted_magnitude_lower
        realization_vs_upper: expression_return / predicted_magnitude_upper

    Both are ratios. Below 1.0 = hasn't reached the bound. Above 1.0 = has passed it.

    If either magnitude bound is zero or negative (data error), returns None for that ratio.
    """
    result = {}

    if predicted_magnitude_lower and predicted_magnitude_lower > 0:
        result["realization_vs_lower"] = expression_return / predicted_magnitude_lower
    else:
        result["realization_vs_lower"] = None

    if predicted_magnitude_upper and predicted_magnitude_upper > 0:
        result["realization_vs_upper"] = expression_return / predicted_magnitude_upper
    else:
        result["realization_vs_upper"] = None

    return result
```

### Time Elapsed

```python
def compute_time_elapsed_pct(
    entry_date: str,           # ISO date from originating run
    timeframe_end_date: str,   # ISO date from payoff band
    as_of_date: str = None,    # ISO date, defaults to today
) -> float:
    """
    Fraction of the holding window consumed.

    Returns a float clamped to [0.0, 1.0].
    At 0.0 the window just opened. At 1.0 the window has expired.
    """
    from datetime import date

    entry = date.fromisoformat(entry_date)
    end = date.fromisoformat(timeframe_end_date)
    now = date.fromisoformat(as_of_date) if as_of_date else date.today()

    window = (end - entry).days
    if window <= 0:
        return 1.0

    elapsed = (now - entry).days
    return max(0.0, min(1.0, elapsed / window))
```

### Where Entry Prices Come From

The originating run is determined by `run_id` on the hypothesis. That run's `run_price_snapshots` provide entry prices for each ticker in `predicted_assets`.

If a hypothesis appears across multiple runs (same `id` carried forward), the entry prices are always from the **earliest** run — the run that first generated it. This answers "has the original call been delivered?" which is the question the realization engine exists to answer.

If a later run produces a **continuation** hypothesis (new ID, `continuation_of` pointing to the parent), the continuation gets its own entry prices from its own originating run. The parent and continuation are tracked independently.

---

## Component 2: Structured Payoff Band Fields

### New Fields at Generation Time

The generation prompt must produce three structured fields alongside the existing prose prediction:

```python
# New fields on Hypothesis — required at generation time
predicted_magnitude_lower: float    # e.g., 0.15 (15%), always positive
predicted_magnitude_upper: float    # e.g., 0.30 (30%), always positive
timeframe_end_date: str             # ISO date, e.g., "2026-09-30"
```

### Framing: Payoff Band, Not Oracle Prediction

These fields are a **falsifiability scaffold**, not a precision forecast. Their role:

- Make the hypothesis auditable and non-slippery (the LLM cannot silently shift goalposts)
- Enable mechanical comparison of delivered return vs. expected return
- Feed the freshness/maturity overlay so the system can distinguish fresh opportunities from exhausted trades

What they are NOT:

- Not a stop-loss. Missing the band does not automatically trigger exit.
- Not automatic falsification. Underperformance is a review signal, not a death sentence.
- Not a price target for execution. The human decides entry, exit, and sizing.

### Constraints Enforced at Ingestion

```python
def validate_payoff_band(
    predicted_magnitude_lower: float,
    predicted_magnitude_upper: float,
    timeframe_end_date: str,
) -> list[str]:
    """
    Validate payoff band fields. Returns list of error messages (empty if valid).
    """
    errors = []

    # Both bounds must be positive
    if predicted_magnitude_lower <= 0:
        errors.append("predicted_magnitude_lower must be positive")
    if predicted_magnitude_upper <= 0:
        errors.append("predicted_magnitude_upper must be positive")

    # Lower < Upper (band has width)
    if predicted_magnitude_lower >= predicted_magnitude_upper:
        errors.append("predicted_magnitude_lower must be less than predicted_magnitude_upper")

    # Upper bound capped at 1.0 (100%) — no hypothesis should predict
    # more than a double within the holding window for liquid ETFs
    if predicted_magnitude_upper > 1.0:
        errors.append("predicted_magnitude_upper exceeds 1.0 (100%) ceiling")

    # Timeframe must be valid future date, no more than 12 months out
    from datetime import date
    try:
        end = date.fromisoformat(timeframe_end_date)
        today = date.today()
        if end <= today:
            errors.append("timeframe_end_date must be in the future")
        if (end - today).days > 365:
            errors.append("timeframe_end_date must be within 12 months")
    except ValueError:
        errors.append("timeframe_end_date is not a valid ISO date")

    return errors
```

### Magnitude Bounds Are Expression-Level

The magnitude prediction must be stated in the same units as the expression return.

- **Pair hypothesis:** "LONG DBC / SHORT QQQ, spread delivers 15-30%" — the 15-30% is the expected expression return (the spread), not a single-leg prediction.
- **Single-leg hypothesis:** "LONG GLD, +10-20%" — the 10-20% is the asset return, which equals the expression return for a single-leg expression.

The generation prompt must enforce this. A prediction that says "DBC rises 20-30%" on a DBC/QQQ pair hypothesis is malformed — it states a single-leg prediction on a multi-leg expression. The correct form is "DBC outperforms QQQ by 15-30%."

### Magnitude Bounds Are Always Positive

Direction is already captured in `asset_direction`. The magnitude bounds represent expected **profitable** return on the expression, regardless of whether the expression involves short legs.

- "SHORT SPY, expected 10-20% decline" → `predicted_magnitude_lower: 0.10, predicted_magnitude_upper: 0.20`. The expression return will be positive (via direction adjustment) if SPY falls.

### Existing Fields Preserved

The existing `timeframe: string` field (e.g., "Through Q3 2026") stays for display. The new `timeframe_end_date` is for computation. Both are populated by the generation prompt.

### Generation Prompt Addition

The generation prompt gains an additional structured output requirement. After each hypothesis, the LLM must produce:

```
PAYOFF_BAND:
  magnitude_lower: [float, 0.0-1.0]
  magnitude_upper: [float, 0.0-1.0, must exceed magnitude_lower]
  end_date: [YYYY-MM-DD, within 12 months]
```

This sits alongside the existing structured fields (predicted_assets, asset_direction, timeframe, etc.) in the hypothesis output block.

---

## Component 3: Continuation Lineage Model

### The Problem

When a hypothesis reaches MATURE or EXPRESSED realization, the generation prompt in a subsequent run may see that the same macro mechanism is still Active and produce a new hypothesis on the same expression from current levels. This must be handled as a **continuation**, not a silent revision of the original.

### Two Questions, Two Hypothesis Objects

- **Original-call realization:** has the original hypothesis, from its original entry point and original payoff band, already largely delivered? → Tracked on the original hypothesis object.
- **Continuation opportunity:** from current levels, is there a fresh residual move worth expressing? → A new hypothesis object with explicit parent linkage.

These must never be silently merged. The original hypothesis keeps its original entry prices and payoff band forever. A continuation is a new hypothesis with its own entry prices, its own payoff band, and its own conviction score.

### New Fields on Hypothesis

```python
# Continuation lineage — null for original hypotheses
continuation_of: str | None           # hypothesis ID of the parent
continuation_generation: int          # 1 = original, 2 = first continuation, etc.
continuation_justification: str | None  # required for continuations: what is genuinely new
```

### Generation Prompt Contract for Continuations

When the generation prompt receives realization data showing a prior hypothesis with high realization (realization_vs_upper approaching or exceeding 1.0), it has three options:

1. **Decline to regenerate.** The mechanism is spent. Generate hypotheses on other mechanisms instead.

2. **Generate a continuation.** A new hypothesis on the same or similar expression, with:
   - `continuation_of` set to the parent hypothesis ID
   - `continuation_generation` incremented from the parent
   - `continuation_justification` stating what is genuinely new — required, and the following is NOT sufficient justification: "the same macro factors are still active." Acceptable justifications include:
     - New data not available at original generation time
     - A mechanism extension (e.g., a second-order effect now manifesting)
     - A changed expression (same mechanism, different ETF pair from current levels)
   - Its own payoff band calibrated from current levels (not the original's band)

3. **Generate a genuinely different hypothesis** on the same mechanism with a different expression. This is not a continuation — it's a new original hypothesis (`continuation_of = null`, `continuation_generation = 1`).

The generation prompt must NOT silently revise the original hypothesis's payoff band. The original's `predicted_magnitude_lower`, `predicted_magnitude_upper`, and `timeframe_end_date` are immutable after generation.

### What the Prompt Receives

The generation prompt receives, for each surviving prior hypothesis:

```
PRIOR HYPOTHESIS: H-2026-037-01
  Expression: LONG DBC / SHORT QQQ
  Payoff band: 15-30% through 2026-09-30
  Expression return since inception: +24.8%
  Realization vs lower bound: 1.65  (165% of lower bound delivered)
  Realization vs upper bound: 0.83  (83% of upper bound delivered)
  Time elapsed: 38% of holding window
  Status: SURVIVED
  Freshness: WORKING
```

The LLM uses this context to decide whether to regenerate, continue, or move to other mechanisms. This is a contextual judgment — the LLM's native work. The system does not mechanically prevent or force any of the three options.

### Lineage Display

On the Ledger and Hypothesis Detail, continuations display:

- A visible parent link (e.g., "Continuation of H-2026-037-01")
- The generation number (e.g., "Gen 2")
- The continuation justification text

The user can click through to the parent hypothesis to see the original call, its realization state, and how the continuation differs.

---

## Component 4: Provisional Policy Layer

**Everything in this component is marked `[CALIBRATION]` and is expected to be tuned from live runs.** The thresholds, label boundaries, and cap values live in a single configuration block, not scattered across the codebase.

### Freshness Label Computation

```python
# ============================================================
# PROVISIONAL POLICY — ALL THRESHOLDS ARE [CALIBRATION]
# Change these values based on live run evidence.
# They are configuration, not architecture.
# ============================================================

# [CALIBRATION] Time threshold — fraction of holding window
TIME_THRESHOLD = 0.50   # 50% of window elapsed = "late"

# [CALIBRATION] Freshness label logic
def compute_freshness_label(
    realization_vs_lower: float | None,
    realization_vs_upper: float | None,
    time_elapsed_pct: float,
) -> str:
    """
    Compute the freshness label from realization primitives.

    Two axes:
      Magnitude: R < L (below lower) | L <= R < U (within band) | R >= U (above upper)
      Time:      early (< TIME_THRESHOLD) | late (>= TIME_THRESHOLD)

    Returns one of six labels. See action model below.

    If realization ratios are None (missing payoff band data), returns "INDETERMINATE".
    """
    if realization_vs_lower is None or realization_vs_upper is None:
        return "INDETERMINATE"

    late = time_elapsed_pct >= TIME_THRESHOLD

    if realization_vs_upper >= 1.0:
        return "EXPRESSED" if late else "ACCELERATING"
    elif realization_vs_lower >= 1.0:
        return "MATURE" if late else "WORKING"
    else:
        return "UNDERPERFORMING" if late else "FRESH"
```

### Action Model

Each label maps to a distinct human action and an optional mechanical cap:

| Label | Condition | Human Action | Mechanical Cap |
|-------|-----------|--------------|----------------|
| FRESH | Below lower bound, early window | Evaluate for new entry | None |
| WORKING | Within band, early window | Hold, monitor | None |
| ACCELERATING | Above upper bound, early window | Review: best trade or crowded overshoot? | None `[CALIBRATION]` |
| UNDERPERFORMING | Below lower bound, late window | Review: thesis wrong, expression wrong, or timing wrong? | None `[CALIBRATION]` |
| MATURE | Within band, late window | Tighten risk, consider partial exit | 7.0 `[CALIBRATION]` |
| EXPRESSED | Above upper bound, late window | No new entry, exit existing position | 5.0 `[CALIBRATION]` |
| INDETERMINATE | Missing payoff band data | Treat as FRESH (legacy hypotheses without structured bands) | None |

Notes on the action model:

- **ACCELERATING and UNDERPERFORMING are review signals, not mechanical cap states.** They surface in the UI with distinct labels but do not reduce conviction scores. The human investigates. Future calibration may add caps if live runs show the system repeatedly scores accelerating or underperforming hypotheses in misleading ways.
- **MATURE cap at 7.0 `[CALIBRATION]`** reflects reduced residual expected return — the lower bound has been reached, the window is advanced, but the upper bound hasn't been hit. The argument against: reducing conviction on a winning trade is counterintuitive. The argument for: the risk/reward has shifted. Starting value is 7.0; tune from live evidence.
- **EXPRESSED cap at 5.0 `[CALIBRATION]`** puts the hypothesis at the conviction floor. "Thesis alive, trade exhausted, no edge remaining." 5.0 is the existing conviction floor.
- **INDETERMINATE** handles legacy hypotheses generated before v6 that lack structured payoff band fields. They are treated as FRESH — no cap, no label. The system degrades gracefully.

### Realization Cap in Stage 3

```python
# [CALIBRATION] Cap values per freshness label
REALIZATION_CAPS = {
    "FRESH":            None,
    "WORKING":          None,
    "ACCELERATING":     None,
    "UNDERPERFORMING":  None,
    "MATURE":           7.0,
    "EXPRESSED":        5.0,
    "INDETERMINATE":    None,
}

def compute_realization_cap(freshness_label: str) -> float | None:
    """
    Return the conviction cap for the given freshness label, or None if no cap applies.

    This cap is applied in Stage 3 alongside horizon_cap and expression_cap:
        FINAL = min(SCORE, horizon_cap, expression_cap, realization_cap)
        FINAL = max(FINAL, 5.0)
    """
    return REALIZATION_CAPS.get(freshness_label, None)
```

### Updated Stage 3

```
Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap, realization_cap) → max(FINAL, 5.0)
```

The realization cap sits alongside the existing horizon and expression caps. All three are independent gates. The most restrictive cap wins (min). The conviction floor at 5.0 still applies.

### Configuration Block

All `[CALIBRATION]` values live in a single file (e.g., `realization_config.py`):

```python
# realization_config.py
# ============================================================
# PROVISIONAL POLICY CONFIGURATION
# All values in this file are [CALIBRATION] — expected to be
# tuned from live run evidence. Changing these values is a
# config change, not an architectural change.
# ============================================================

# Time axis threshold (fraction of holding window)
TIME_THRESHOLD = 0.50           # [CALIBRATION]

# Conviction caps per freshness label (None = no cap)
REALIZATION_CAPS = {            # [CALIBRATION]
    "FRESH":            None,
    "WORKING":          None,
    "ACCELERATING":     None,
    "UNDERPERFORMING":  None,
    "MATURE":           7.0,
    "EXPRESSED":        5.0,
    "INDETERMINATE":    None,
}

# Payoff band validation constraints
MAGNITUDE_UPPER_CEILING = 1.0   # [CALIBRATION] max predicted return (100%)
TIMEFRAME_MAX_DAYS = 365        # [CALIBRATION] max holding window
```

---

## Component 5: Frontend Surfacing

### Hypothesis Data Shape Additions

```typescript
interface Hypothesis {
  // ... existing fields unchanged ...

  // v6: Payoff Band (structured at generation time)
  predicted_magnitude_lower: number | null;   // e.g., 0.15
  predicted_magnitude_upper: number | null;   // e.g., 0.30
  timeframe_end_date: string | null;          // ISO date

  // v6: Realization Primitives (computed)
  realization: {
    expression_return: number | null;          // e.g., 0.248 (24.8%)
    realization_vs_lower: number | null;       // e.g., 1.65
    realization_vs_upper: number | null;       // e.g., 0.83
    time_elapsed_pct: number | null;           // e.g., 0.38
    as_of_date: string;                        // ISO date of price fetch
  } | null;

  // v6: Freshness Overlay (provisional policy output)
  entry_freshness: string | null;             // FRESH | WORKING | ACCELERATING |
                                               // UNDERPERFORMING | MATURE | EXPRESSED |
                                               // INDETERMINATE

  // v6: Continuation Lineage
  continuation_of: string | null;             // parent hypothesis ID
  continuation_generation: number;            // 1 = original
  continuation_justification: string | null;

  // v6: Updated conviction math
  conviction_math: {
    // ... stage1, stage2 unchanged ...
    stage3: {
      horizon_cap: number | null;
      expression_cap: number | null;
      realization_cap: number | null;          // NEW — null if not binding
      final: number;
    };
  };
}
```

### Ledger View Changes

- **Freshness badge** next to conviction score. Small colored label: FRESH (olive), WORKING (olive), ACCELERATING (gold), UNDERPERFORMING (gold), MATURE (brick, muted), EXPRESSED (brick). Colors follow Hermes Editorial palette.
- **Continuation indicator.** If `continuation_of` is set, show "Gen N" badge with parent link.

### Hypothesis Detail Changes

**New section: Realization (between Falsifiers and Research Notes)**

- Payoff band display: lower bound, upper bound, timeframe end date
- Expression return: current % with direction indicator
- Realization progress bar: visual showing expression return position relative to lower/upper bounds
- Time elapsed: bar or fraction showing % of holding window consumed
- Freshness label: prominently displayed with the action guidance text
- If realization_cap is binding: show "Realization cap: 7.0 (MATURE)" or equivalent, explaining why the final conviction differs from the uncapped score

**Continuation lineage section (only if continuation_of is set):**

- Parent hypothesis link (clickable)
- Continuation justification text
- Generation number

### Pipeline Audit Mode Changes

The conviction math breakdown in the 5-stage audit gains:

- Stage 3 now shows `realization_cap` alongside `horizon_cap` and `expression_cap`
- Walk-forward panel gains a "Realization" column showing expression_return and freshness label

---

## Database Changes

### Altered table: hypotheses

```sql
-- Migration 6 (in database.py _migrate())
-- Payoff band fields
ALTER TABLE hypotheses ADD COLUMN predicted_magnitude_lower REAL;
ALTER TABLE hypotheses ADD COLUMN predicted_magnitude_upper REAL;
ALTER TABLE hypotheses ADD COLUMN timeframe_end_date TEXT;

-- Continuation lineage
ALTER TABLE hypotheses ADD COLUMN continuation_of TEXT;
ALTER TABLE hypotheses ADD COLUMN continuation_generation INTEGER DEFAULT 1;
ALTER TABLE hypotheses ADD COLUMN continuation_justification TEXT;

-- Freshness overlay (computed, stored for display)
ALTER TABLE hypotheses ADD COLUMN entry_freshness TEXT;
ALTER TABLE hypotheses ADD COLUMN expression_return REAL;
ALTER TABLE hypotheses ADD COLUMN realization_vs_lower REAL;
ALTER TABLE hypotheses ADD COLUMN realization_vs_upper REAL;
ALTER TABLE hypotheses ADD COLUMN time_elapsed_pct REAL;
ALTER TABLE hypotheses ADD COLUMN realization_cap REAL;
```

All migrations idempotent (Migration 6 in database.py `_migrate()`).

No new tables. No changes to `run_price_snapshots`, `runs`, or any other existing table.

### Computed Fields vs. Stored Fields

The realization primitives (`expression_return`, `realization_vs_lower`, `realization_vs_upper`, `time_elapsed_pct`) are recomputed whenever prices are fetched (at run time and when walk-forward endpoint is called). They are stored for display purposes but are not authoritative — the authoritative values come from recomputation against current prices.

The payoff band fields and continuation lineage fields are set at generation time and are immutable thereafter.

The freshness label and realization cap are recomputed from the primitives whenever the primitives update.

---

## API Changes

### Updated Endpoints

```
GET /api/runs/{id}/walkforward
```

Response gains per-hypothesis fields:
- `expression_return`: float (the aggregate expression return)
- `realization_vs_lower`: float
- `realization_vs_upper`: float
- `time_elapsed_pct`: float
- `entry_freshness`: string (freshness label)
- `realization_cap`: float | null

### New Endpoint

```
GET /api/hypotheses/{id}/realization
```

Returns the full realization primitive set for a single hypothesis:

```json
{
  "hypothesis_id": "H-2026-037-01",
  "expression_return": 0.248,
  "legs": [
    {"ticker": "DBC", "direction": "LONG", "entry": 23.45, "current": 28.12, "return": 0.199},
    {"ticker": "QQQ", "direction": "SHORT", "entry": 485.20, "current": 462.30, "return": 0.047}
  ],
  "realization_vs_lower": 1.65,
  "realization_vs_upper": 0.83,
  "time_elapsed_pct": 0.38,
  "payoff_band": {
    "lower": 0.15,
    "upper": 0.30,
    "end_date": "2026-09-30"
  },
  "entry_freshness": "WORKING",
  "realization_cap": null,
  "as_of_date": "2026-04-01",
  "continuation_of": null,
  "continuation_generation": 1
}
```

---

## Generation Prompt Changes

### Structured Output Additions

The generation prompt's hypothesis output block gains:

```
For each hypothesis, you MUST provide:
  ... (existing fields: short_name, full_statement, predicted_assets, asset_direction, timeframe, etc.)

  PAYOFF_BAND:
    magnitude_lower: [positive float, e.g. 0.15 for 15%]
    magnitude_upper: [positive float, must exceed magnitude_lower, max 1.0]
    end_date: [YYYY-MM-DD, must be future date within 12 months]

  Rules for the payoff band:
  - The magnitude bounds represent the expected EXPRESSION-LEVEL return, not a single-leg return.
  - For pair/spread hypotheses (LONG X / SHORT Y), state the expected spread return.
  - For single-leg hypotheses (LONG X), state the expected asset return.
  - Both bounds are always POSITIVE — they represent profitable return on the expression.
    Direction is already captured in asset_direction.
  - The band is an auditable range for tracking realization, not a stop-loss or precision forecast.
```

### Prior Hypothesis Realization Context

When prior hypotheses exist with computed realization data, the generation prompt receives a new context section:

```
PRIOR HYPOTHESIS REALIZATION (for awareness — do not regenerate exhausted trades):

  H-2026-037-01: LONG DBC / SHORT QQQ
    Payoff band: 15-30% through 2026-09-30
    Expression return: +24.8%
    Realization: 165% of lower bound, 83% of upper bound
    Time elapsed: 38% of window
    Freshness: WORKING

  H-2026-037-04: LONG XLE / SHORT XLK
    Payoff band: 10-25% through 2026-09-30
    Expression return: +31.2%
    Realization: 312% of lower bound, 125% of upper bound
    Time elapsed: 38% of window
    Freshness: ACCELERATING

  INSTRUCTION: Do not reissue hypotheses whose original predicted move has been substantially
  delivered (realization_vs_upper >= 1.0) unless you can justify a CONTINUATION with genuinely
  new evidence or mechanism extension. If generating a continuation, you MUST provide:
    continuation_of: [parent hypothesis ID]
    continuation_justification: [what is genuinely new — "same factors still active" is NOT sufficient]
```

### Elimination Prompt: No Changes

The elimination pass attacks thesis validity. Realization is orthogonal to falsification. Pass 3 is unchanged by v6.

---

## Build Order

| Priority | Component | Description | Phase |
|----------|-----------|-------------|-------|
| 1 | Expression return computation | `compute_expression_return()`, `compute_realization_ratios()`, `compute_time_elapsed_pct()` in new `realization.py` | Phase 1 |
| 2 | Realization API endpoint | `GET /api/hypotheses/{id}/realization` using walk-forward price infrastructure | Phase 1 |
| 3 | Database migration | Migration 6: add payoff band, continuation, and realization columns to hypotheses | Phase 2 |
| 4 | Payoff band validation | `validate_payoff_band()` in realization.py, called at hypothesis import | Phase 2 |
| 5 | Generation prompt: structured payoff band | Add PAYOFF_BAND output requirement to generation prompt template | Phase 2 |
| 6 | Generation prompt: continuation model | Add PRIOR HYPOTHESIS REALIZATION context section, continuation output fields | Phase 3 |
| 7 | Continuation lineage persistence | Store `continuation_of`, `continuation_generation`, `continuation_justification` at import | Phase 3 |
| 8 | Provisional policy: freshness label | `compute_freshness_label()` in realization_config.py, stored on hypothesis at run time | Phase 4 |
| 9 | Provisional policy: realization cap | `compute_realization_cap()` integrated into Stage 3 of conviction pipeline | Phase 4 |
| 10 | Walk-forward endpoint update | Add realization fields to walk-forward response | Phase 4 |
| 11 | Frontend: Ledger freshness badges | Freshness label badge + continuation indicator on HypothesisTable | Phase 5 |
| 12 | Frontend: Hypothesis Detail realization section | Payoff band, progress bar, realization primitives, freshness label, cap display | Phase 5 |
| 13 | Frontend: Pipeline Audit realization column | Expression return + freshness in walk-forward panel, realization_cap in Stage 3 audit | Phase 5 |
| 14 | Frontend: Continuation lineage display | Parent link, generation number, justification text on Hypothesis Detail | Phase 5 |

### Implementation Notes for Claude Code

- **Priority 1-2 are pure computation + API.** No prompt changes, no UI. New file `backend/realization.py` with pure functions. New endpoint in `backend/api/hypotheses.py`. Reuses `_fetch_current_price()` and `run_price_snapshots` from v5.
- **Priority 3-5 are generation prompt + DB.** Migration follows the same pattern as Migration 5. Payoff band validation runs at hypothesis import time (when the user pastes elimination results). Generation prompt change is a text addition to the prompt template.
- **Priority 6-7 are the continuation model.** Generation prompt receives realization context as an injected section. Continuation fields stored at import.
- **Priority 8-9 are the provisional policy.** Single config file `backend/realization_config.py` with all `[CALIBRATION]` values. Freshness label stored on hypothesis. Realization cap plugged into existing Stage 3 gate logic — same pattern as `horizon_cap` and `expression_cap`, one additional `min()` term.
- **Priority 10 updates the existing walk-forward endpoint** — no new endpoint, just additional fields in the response.
- **Priority 11-14 are display-only frontend changes.** No new views. Freshness badges on existing Ledger. New section in existing Hypothesis Detail overlay. New column in existing Walk-Forward panel.

### Testing Checklist

- [ ] `compute_expression_return()` returns correct value for single-leg LONG hypothesis
- [ ] `compute_expression_return()` returns correct value for single-leg SHORT hypothesis
- [ ] `compute_expression_return()` returns correct value for LONG/SHORT pair (equal-weight mean)
- [ ] `compute_expression_return()` returns None if any ticker missing from prices
- [ ] `compute_realization_ratios()` returns ratios > 1.0 when expression return exceeds bounds
- [ ] `compute_realization_ratios()` handles zero/null magnitude bounds gracefully
- [ ] `compute_time_elapsed_pct()` returns 0.0 at entry date
- [ ] `compute_time_elapsed_pct()` returns 1.0 at or after timeframe_end_date
- [ ] `compute_time_elapsed_pct()` returns 0.5 at midpoint of window
- [ ] `validate_payoff_band()` rejects lower >= upper
- [ ] `validate_payoff_band()` rejects upper > 1.0
- [ ] `validate_payoff_band()` rejects past end dates
- [ ] `validate_payoff_band()` rejects end dates > 12 months out
- [ ] `compute_freshness_label()` returns FRESH for below-lower + early
- [ ] `compute_freshness_label()` returns WORKING for within-band + early
- [ ] `compute_freshness_label()` returns ACCELERATING for above-upper + early
- [ ] `compute_freshness_label()` returns UNDERPERFORMING for below-lower + late
- [ ] `compute_freshness_label()` returns MATURE for within-band + late
- [ ] `compute_freshness_label()` returns EXPRESSED for above-upper + late
- [ ] `compute_freshness_label()` returns INDETERMINATE when ratios are None
- [ ] Realization cap integrates into Stage 3: `min(SCORE, horizon_cap, expression_cap, realization_cap)`
- [ ] Conviction floor at 5.0 still applies after realization cap
- [ ] EXPRESSED hypothesis scores exactly 5.0 (floor) regardless of raw conviction
- [ ] MATURE hypothesis with raw conviction 9.0 scores 7.0 (capped)
- [ ] WORKING hypothesis with raw conviction 9.0 scores 9.0 (no cap)
- [ ] Continuation fields stored correctly at import
- [ ] Continuation hypothesis has its own entry prices (not the parent's)
- [ ] Walk-forward endpoint includes realization fields
- [ ] Legacy hypotheses (no payoff band) get INDETERMINATE freshness and no cap

---

## What v6 Does NOT Do

1. **Does not kill hypotheses.** Freshness labels and caps are overlays, not status changes. SURVIVED / WOUNDED / KILLED remains a thesis validity assessment independent of trade realization.

2. **Does not make execution decisions.** "EXPRESSED, cap 5.0" means "the system scores this at the floor." The human decides whether to exit.

3. **Does not modify the elimination pass.** Pass 3 attacks thesis validity. Realization is orthogonal to falsification.

4. **Does not cross-compare expressions.** The system does not answer "your mechanism was right but another ETF pair would have been better." That's optimizer logic. v6 tracks one expression against its own payoff band.

5. **Does not enforce hard gates on continuations.** No automatic penalty for continuations. No "no same expression within N runs" rule. The generation prompt must justify continuations with genuinely new evidence; the human judges whether the justification is real. Automatic gates may be added in future versions if live runs show repeated recycling.

6. **Does not treat the provisional policy as settled.** All `[CALIBRATION]` thresholds are starting values. The 50% time split, the 7.0 MATURE cap, the 5.0 EXPRESSED cap, and the label boundaries are all expected to be tuned after live run evidence accumulates.

7. **Does not auto-resolve realization.** Realization primitives are recomputed from market prices; freshness labels follow mechanically. But the human interprets them. UNDERPERFORMING does not mean "sell." ACCELERATING does not mean "take profit." EXPRESSED does not mean "exit now."

8. **Does not change theory modules, sector appendices, or activation scoring.** All Pass 1 / Pass 1.5 infrastructure is unchanged.

---

## Conviction Pipeline Reference (v6)

```
Pass 1:   Activation scoring — 8 modules scored independently → Active / Adjacent / Inactive
Pass 1.5: Regime annotation — compute_regime_flags() from activation results → active flags list
Pass 2:   LLM generation — active theories + regime context + channel tags
            + prior hypothesis realization context
            + structured payoff band output requirement
            + continuation lineage output requirement
            → 7-9 hypotheses with channel tags, payoff bands, optional continuation links
Pass 3:   LLM elimination — adversarial attack + sector falsifier appendices + channel verification
            → SURVIVED / WOUNDED / KILLED (unchanged from v5)
Pass 4:   Mechanical conviction scoring (zero-LLM):
            Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
            Stage 2: DISCOUNTED = RAW × D_f × D_o × D_r  →  SCORE = DISCOUNTED × 10
            Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap, realization_cap) → max(FINAL, 5.0)
Pass 4.5: Realization overlay (zero-LLM, post-conviction):
            compute_expression_return() from entry prices + current prices
            compute_realization_ratios() against payoff band
            compute_time_elapsed_pct()
            compute_freshness_label() from primitives → [CALIBRATION] policy
            compute_realization_cap() from freshness label → feeds back into Stage 3
Pass 5:   Human decision layer — system never recommends trades or sizes
```

LLM does: generate hypotheses with payoff bands + continuation reasoning, attack hypotheses
Math does: activation, regime flags, conviction scoring, realization primitives, freshness labels, caps
Human does: execution decisions, continuation judgment, realization interpretation

---

## Status: DESIGN COMPLETE — Ready for implementation (2026-04-01)
