# plan_v3.md — Falsification Engine v3 Implementation Plan

## Design Principle (governs all v3 changes)

**Do not suppress detection. Do not mechanize interpretation too early. Mechanize the scoring of interpretations afterward.**

Pass 1 detects facts mechanically. Pass 1.5 annotates regime mechanically. Pass 2–3 let the LLM reason about channel, composition, and attack. Pass 4 mechanically penalizes channel/regime mismatch.

The system must never talk itself out of valid warnings. Regime context changes what KIND of warning the system produces — not WHETHER it produces one.

---

## What Exists (v1 + v2 — all complete)

The following pipeline is built and working end-to-end:

- 8 theory modules parsed and scored mechanically (activation engine)
- Data agent fetching FRED + Yahoo Finance into structured briefing packets
- Generation prompt producing 7-9 hypotheses per run
- Elimination prompt with mechanical falsifier audit (CLEAR / TRIGGERED / UNTESTABLE)
- Three-stage conviction scoring: mechanical Stage 1 inputs (support_strength, evidence_quality, convergence, falsifier_clarity) → Stage 2 discounts (soft falsifier, UNTESTABLE, theory-aware overlap) → Stage 3 gates (horizon alignment from timeframe parsing, expression efficiency from ETF liquidity tiers)
- Conviction floor at 5/10
- Consolidation check preventing redundant hypotheses
- React frontend: Research, Observatory, Pipeline, Trades views (+ About via header link)
- Hermes Editorial design system (Cormorant Garamond / EB Garamond / JetBrains Mono, cream/brick/olive/gold) with night mode
- GitHub Pages static publishing with cache-busting
- Trade tracker with full lifecycle (open, track, close)
- Newsletter prompt builder + import + archive
- Auto-managed trades via newsletter (desired-state reconciliation, pending actions, manual signoff)
- Mobile-responsive CSS

**Current output quality:** Two completed runs with 13 total hypotheses. Conviction range 5-8 for survivors. Horizon gate is dominant kill mechanism.

---

## v3 Enhancement: Regime-Conditional Channel Scoring

### Overview

v3 adds three components to the pipeline:

1. **Pass 1.5 — Regime Annotation:** After all eight theory modules score independently, a mechanical post-pass computes regime flags from the activation results. No activation scores change. No thresholds change. The flags are annotations, not modifiers.

2. **Resolution Channel Tagging:** Each hypothesis generated in Pass 2 is tagged with exactly one resolution channel from a fixed enumeration. The evaluator in Pass 3 verifies the tag. This is a new structured field on the hypothesis object.

3. **Channel-Regime Alignment Scoring:** Pass 4 gains a new multiplicative discount. When a regime flag is active, the scorer checks the hypothesis's channel tag against the flag's alignment table and applies a multiplier. This sits in Stage 2 of the conviction pipeline alongside existing soft falsifier and overlap discounts.

### What This Does NOT Do

- Does NOT change any theory module's activation thresholds
- Does NOT suppress or delay activation of any theory
- Does NOT add LLM involvement to the scoring pipeline
- Does NOT change the existing conviction formula structure (additive Stage 1, multiplicative Stage 2, gate Stage 3)
- Does NOT require API integration or new data sources

---

## Component 1: Regime Flag Schema

### Data Structure

```python
# New file: regime_flags.py

REGIME_FLAGS = {
    "schema_version": 1,
    "flags": [
        {
            "flag_id": "fiscal_dominance_active",

            # TRIGGER — mechanical, computed from Pass 1 activation results
            # Reads the activation status of fiscal_dominance_liquidity
            # Binary: the flag fires or it does not
            "trigger": {
                "module": "fiscal_dominance_liquidity",
                "condition": "Active"
                # No graduated trigger. Adjacent does NOT fire the flag.
                # If fiscal_dominance_liquidity is Adjacent, the generator
                # already receives it as a wildcard module. The regime flag
                # is specifically about mechanical downstream effects.
            },

            # SCOPE — which modules this flag annotates
            # Explicit and closed. Adding a module requires a design decision.
            "affects": [
                "valuation_mean_reversion",
                "structural_fragility",
                "debt_cycle_short"
            ],

            # DIRECTION — enforces DAG constraint
            # fiscal_dominance_liquidity is UPSTREAM. Affected modules never
            # feed back into fiscal_dominance_liquidity's activation.
            # This must be one-directional. No cycles.
            "dependency_direction": "fiscal_dominance_liquidity -> affected modules",

            # CHANNEL CONTEXT — prose, injected into Pass 2 generation prompt
            # These guide the LLM's hypothesis construction.
            # They are NOT scoring inputs.
            "channel_context": {
                "valuation_mean_reversion": (
                    "Resolution channel shifts from nominal price decline toward "
                    "inflationary grind. ERP comparator (risk-free rate) is itself "
                    "being debased. Equity overvaluation resolves through real return "
                    "erosion rather than nominal crash. GLD outperforms SPY in real "
                    "terms even without nominal correction."
                ),
                "structural_fragility": (
                    "Fiscal liquidity extends the fragility-building phase. The bid "
                    "under risk assets delays the Minsky moment. Magnitude of eventual "
                    "break is unchanged or amplified — the delay compounds the fragility, "
                    "it does not resolve it. Do not reduce severity estimates because of "
                    "the fiscal backdrop."
                ),
                "debt_cycle_short": (
                    "Fiscal spending offsets monetary tightening, delaying contraction. "
                    "Late-cycle indicators may fire without triggering recession because "
                    "the fiscal channel provides a floor. The cycle is extended, not "
                    "cancelled — the eventual contraction arrives from a more leveraged "
                    "starting point."
                )
            },

            # CHANNEL-REGIME ALIGNMENT TABLE — mechanical, used by Pass 4
            # Maps resolution channels to alignment classification
            "channel_alignment": {
                "nominal_price_decline":     "mismatch",
                "inflationary_grind":        "aligned",
                "real_asset_outperformance": "aligned",
                "sector_rotation":           "neutral",
                "broad_credit_contraction":  "mismatch",
                "sector_credit_stress":      "neutral"
            }
        }
    ]
}
```

### Execution Logic (Pass 1.5)

```python
def compute_regime_flags(activation_results: dict) -> list[dict]:
    """
    Called AFTER all 8 theory modules have been scored in Pass 1.
    Reads activation_results, checks each flag's trigger condition,
    returns list of active regime flags.

    Input:  {"fiscal_dominance_liquidity": "Active", "valuation_mean_reversion": "Active", ...}
    Output: [{"flag_id": "fiscal_dominance_active", "channel_context": {...}, "channel_alignment": {...}}]
    """
    active_flags = []
    for flag in REGIME_FLAGS["flags"]:
        module = flag["trigger"]["module"]
        required_status = flag["trigger"]["condition"]
        if activation_results.get(module) == required_status:
            active_flags.append({
                "flag_id": flag["flag_id"],
                "affects": flag["affects"],
                "channel_context": flag["channel_context"],
                "channel_alignment": flag["channel_alignment"]
            })
    return active_flags
```

### Schema Extension Rules

- New flags added only when live pipeline output reveals a cross-theory interaction that the LLM consistently fails to capture — meaning the interaction needs to be mechanized because the interpretive layer isn't reliably handling it.
- A second flag should be earned by failure evidence, not by conceptual elegance.
- All flags must maintain the DAG constraint: no module may appear in both a flag's trigger and another flag's affects list in a way that creates a cycle.
- The schema supports N flags. v3 ships with one.

---

## Component 2: Resolution Channel Enumeration

### Channel Definitions

```python
RESOLUTION_CHANNELS = {
    "nominal_price_decline": {
        "description": (
            "Asset prices fall in nominal terms. The hypothesis depends on a "
            "repricing event — sellers overwhelm buyers, multiples compress, "
            "nominal prices drop 15%+."
        ),
        "example": "SPY declines 30% as CAPE reverts from 36 to 25"
    },

    "inflationary_grind": {
        "description": (
            "Nominal prices flat or slowly rising while inflation erodes real "
            "value. The hypothesis depends on purchasing power loss, not nominal "
            "loss. Forward real returns are poor even if nominal returns are "
            "slightly positive."
        ),
        "example": "SPY returns 2% nominal annualized for 5 years while CPI runs 4-5%"
    },

    "real_asset_outperformance": {
        "description": (
            "Hard assets (gold, commodities) outperform financial assets. The "
            "hypothesis depends on debasement, inflation expectations, or "
            "structural demand (central bank buying, collateral substitution) "
            "repricing the relative value of scarce vs. nominal claims."
        ),
        "example": "GLD outperforms SPY by 15%+ over 12 months"
    },

    "sector_rotation": {
        "description": (
            "Capital moves between sectors or geographies without a broad market "
            "decline. The hypothesis depends on relative value convergence, not "
            "absolute repricing."
        ),
        "example": "RSP outperforms SPY by 8% as breadth broadens; or EEM outperforms SPY by 12%"
    },

    "broad_credit_contraction": {
        "description": (
            "Generalized deleveraging across the credit system. The hypothesis "
            "depends on a self-reinforcing cycle: tightening lending standards, "
            "rising defaults, falling asset prices, further tightening."
        ),
        "example": "HY spreads widen to 700bp+, bank lending contracts YoY, unemployment rises 2%+"
    },

    "sector_credit_stress": {
        "description": (
            "Credit stress concentrated in a specific segment without broad "
            "contagion. The hypothesis depends on idiosyncratic distress in one "
            "pocket while the broader credit system functions."
        ),
        "example": "CRE delinquencies hit 8%, KRE falls 25%, but XLF ex-regionals is flat"
    }
}
```

### Hypothesis Schema Addition

Each hypothesis object gains one new required field:

```python
# Added to the hypothesis data model
resolution_channel: str  # One of the six keys in RESOLUTION_CHANNELS
```

This is assigned by the LLM during Pass 2 generation and verified by the LLM during Pass 3 evaluation.

### Generation Prompt Addition

Append to the existing generation prompt when regime flags are active:

```
--- REGIME FLAGS ---

The following regime flags are active based on current theory activation states.
Use the channel context below when constructing hypotheses for the affected theories.

{for each active flag:}
REGIME FLAG: {flag_id}
Triggered by: {trigger module} is Active

Channel context for affected theories:
{for each affected module that is Active or Adjacent:}
  - {module_id}: {channel_context prose}

--- RESOLUTION CHANNEL REQUIREMENT ---

For each hypothesis, assign exactly one resolution_channel from this list:
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

Format: include "resolution_channel": "<channel>" in each hypothesis output.
```

### Evaluator Prompt Addition

Append to the existing elimination prompt:

```
--- CHANNEL VERIFICATION ---

For each hypothesis, verify the resolution_channel tag:
1. Does the predicted magnitude match the channel? A 30%+ nominal decline
   tagged as "inflationary_grind" is a misclassification.
2. Does the predicted timeline match the channel? An "inflationary_grind"
   hypothesis with a 2-month timeline is suspect — grinds take years.
3. Does the load-bearing mechanism match the channel? If removing the
   channel's mechanism would kill the hypothesis, the tag is correct.
   If the hypothesis would survive without that mechanism, the tag is wrong.

If you identify a channel misclassification, state:
  - The assigned channel
  - The correct channel
  - Why the reassignment is warranted

The corrected channel will be used for scoring. The original assignment
is preserved in the audit trail.
```

---

## Component 3: Channel-Regime Alignment Scoring

### Conviction Pipeline Integration

Channel-regime alignment is a new multiplicative discount in Stage 2 of the conviction pipeline. It sits alongside the existing soft falsifier discount (D_f) and overlap discount (D_o).

```
Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)           [unchanged]
Stage 2: DISCOUNTED = RAW × D_f × D_o × D_r  →  SCORE = DISCOUNTED × 10
Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap)  →  max(FINAL, 5.0)   [unchanged]
```

Where D_r is the regime alignment discount:

### Multiplier Values (PROVISIONAL — calibration-ready)

```python
# These values are provisional. They are chosen to be:
#   - strong enough to matter in the conviction score
#   - not so strong that they suppress warnings
#   - consistent with the design principle: penalize, do not kill
#
# Recalibrate after 5+ pipeline runs with regime flags active.
# The implementation should read these from a config constant,
# not hardcode them inline, so recalibration is a single edit.

REGIME_ALIGNMENT_MULTIPLIERS = {
    "mismatch": 0.75,   # Hypothesis depends on a mechanism the regime works against
    "aligned":  1.00,   # No bonus — alignment is expected, not rewarded
    "neutral":  1.00    # Regime flag has no opinion on this channel
}
```

### Scoring Logic

```python
def compute_regime_discount(hypothesis_channel: str, active_flags: list[dict]) -> float:
    """
    Compute the regime alignment discount for a hypothesis.

    If multiple regime flags are active (future extensibility), take
    the MINIMUM multiplier across all active flags — worst-case mismatch
    dominates. For v3 with one flag, this is a simple lookup.

    Returns a float between 0.0 and 1.0 to multiply into Stage 2.
    """
    if not active_flags:
        return 1.0

    multipliers = []
    for flag in active_flags:
        alignment = flag["channel_alignment"].get(hypothesis_channel, "neutral")
        multipliers.append(REGIME_ALIGNMENT_MULTIPLIERS[alignment])

    return min(multipliers)  # worst-case mismatch dominates
```

### Effect on Conviction Scores (illustrative)

With a single mismatch flag active and D_r = 0.75:

| Scenario | RAW | D_f | D_o | D_r | SCORE | FINAL |
|----------|-----|-----|-----|-----|-------|-------|
| Strong thesis, no mismatch | 0.80 | 0.90 | 1.00 | 1.00 | 7.2 | 7 |
| Strong thesis, mismatch | 0.80 | 0.90 | 1.00 | 0.75 | 5.4 | 5 |
| Medium thesis, no mismatch | 0.65 | 0.85 | 0.90 | 1.00 | 5.0 | 5 |
| Medium thesis, mismatch | 0.65 | 0.85 | 0.90 | 0.75 | 3.7 | 5 (floor) |

Note: the conviction floor at 5 catches medium-thesis mismatches. A mismatch hypothesis needs strong raw evidence to score above the floor. This is the intended behavior — the system says "this thesis is swimming against the regime current; it needs exceptional evidence to warrant conviction."

---

## Component 4: Threshold Adjustments (DEFERRED)

### Status: Explicitly Not In v3

Two narrow threshold adjustments were identified as potentially warranted:

1. **ERP threshold:** When fiscal_dominance_liquidity is Active AND real short rates are negative (fed funds minus CPI below zero), adjust ERP threshold from "below 1.0%" to "below 0.0%" — because the risk-free comparator is itself being debased.

2. **Real cash yield:** The cash-yield-exceeds-earnings-yield indicator on valuation_mean_reversion adjusts to trigger only when REAL cash yield exceeds earnings yield, not just nominal.

**Why deferred:** Threshold adjustments act directly on activation and can suppress detection. The regime-conditional channel scoring (Components 1-3) provides the primary mechanism for regime sensitivity without touching activation. Threshold adjustments should only be added when live output demonstrates that the channel scoring alone is insufficient — when the system is producing hypotheses with correct channel tags and correct alignment penalties, but the activation layer is still generating noise by treating a debased risk-free rate as a genuine risk-free rate.

**Implementation note for future:** If threshold adjustments are added, they must be implemented as post-pass modifications in Pass 1.5, AFTER all modules have scored independently. The base activation code must remain single-theory. Threshold modifications are annotations applied to activation results, not changes to module definitions.

---

## Data Model Changes

### Hypothesis (additions to existing model)

```python
# New field on hypothesis object
resolution_channel: str         # One of 6 channel keys — required
resolution_channel_original: str | None  # If evaluator corrected the tag, preserve the original
```

### Pipeline Run (additions to existing model)

```python
# New field on run metadata
regime_flags_active: str        # JSON array of active flag_ids at run time, e.g. '["fiscal_dominance_active"]'
```

### New Configuration Constants

```python
# regime_config.py — or equivalent config location
# All regime-related constants in one place for easy recalibration

REGIME_FLAGS = { ... }              # Full schema as defined above
RESOLUTION_CHANNELS = { ... }      # Full enumeration as defined above
REGIME_ALIGNMENT_MULTIPLIERS = {    # Provisional — recalibrate after 5+ runs
    "mismatch": 0.75,
    "aligned":  1.00,
    "neutral":  1.00
}
```

---

## Build Order

**STATUS: v3 COMPLETE. All 8 priorities done. 20 tests passing. GitHub Pages should be republished after the next pipeline run (first run with channel tags + potential regime flags).**

| Priority | Component | Description | Status |
|----------|-----------|-------------|--------|
| 1 | Regime flag schema | `regime_config.py` with REGIME_FLAGS, RESOLUTION_CHANNELS, REGIME_ALIGNMENT_MULTIPLIERS | DONE |
| 2 | Regime scoring functions | `regime.py` with `compute_regime_flags()` + `compute_regime_discount()` (12 tests passing) | DONE |
| 3 | Generation prompt update | Inject regime flag context + channel requirement into Pass 2 prompt | DONE |
| 4 | Evaluator prompt update | Add channel verification check to Pass 3 prompt | DONE |
| 5 | Channel-regime alignment scoring | `compute_regime_discount()` integrated into Stage 2 of conviction pipeline | DONE |
| 6 | Data model migration | Add `resolution_channel`, `resolution_channel_original` to hypothesis; `regime_flags_active` to run | DONE |
| 7 | Frontend: regime flag display | TheoryCard annotated with "FISCAL DOMINANCE" label when flag affects theory; theories API + snapshot enriched with regime_flags | DONE |
| 8 | Frontend: channel tag display | Conditional Channel column in HypothesisTable with compact labels + correction indicator; hypothesis API returns resolution_channel fields | DONE |

### Implementation Notes for Claude Code

- **Priority 1-2 are pure data/config.** No UI, no prompt changes. Just Python constants and a scoring function with tests.
- **Priority 3-4 are prompt text changes.** The generation and elimination prompts are text files or string constants. The additions are appended conditionally when regime flags are active.
- **Priority 5 is a single multiplication** inserted into the existing conviction scoring pipeline between D_o and the ×10 scaling. The function signature and return type match the existing discount pattern.
- **Priority 6 is a DB migration.** Same pattern as the v2 `_migrate()` — ALTER TABLE to add columns, idempotent.
- **Priority 7-8 are display-only frontend changes.** No new views. Regime flags appear as annotations on existing theory cards. Channel tags appear as a new field on hypothesis cards.

### Testing Checklist

- [x] `compute_regime_flags()` returns empty list when no flags trigger
- [x] `compute_regime_flags()` returns the fiscal_dominance_active flag when fiscal_dominance_liquidity is Active
- [x] `compute_regime_flags()` does NOT fire when fiscal_dominance_liquidity is Adjacent
- [x] `compute_regime_discount()` returns 1.0 when no flags active
- [x] `compute_regime_discount()` returns 0.75 for mismatch channels when flag active
- [x] `compute_regime_discount()` returns 1.0 for aligned and neutral channels
- [x] Conviction pipeline produces correct FINAL scores with D_r integrated (verify against illustrative table above)
- [x] Conviction floor at 5 still applies after regime discount
- [x] Generation prompt includes regime flag context only when flags are active
- [x] Generation prompt omits regime flag section entirely when no flags active
- [x] Evaluator prompt includes channel verification section when hypotheses have channel tags
- [x] Hypothesis channel tag persists through elimination (survived hypotheses retain their tag)
- [x] Channel correction by evaluator preserves original tag in `resolution_channel_original`
- [x] Run metadata records which regime flags were active

---

## What v3 Does NOT Include (explicit exclusions)

1. **No threshold adjustments to any theory module.** Activation conditions are unchanged. ERP threshold stays at 1.0%. CAPE threshold stays at 30. All detection remains at default sensitivity.

2. **No second regime flag.** The schema supports N flags but v3 ships with one. A second flag requires failure evidence from live output.

3. **No sector falsifier appendices.** Enhancement 2 from the design brief is deferred to a future version. The resolution channel enumeration partially addresses the sector-level specificity gap by distinguishing `sector_credit_stress` from `broad_credit_contraction` and `sector_rotation` from `nominal_price_decline`, but full sector falsifier appendices are a separate design thread.

4. **No changes to the copy-paste execution model.** Everything works within a single Claude chat context window. The regime flag computation happens in the backend between Pass 1 and Pass 2. The prompt additions are text injected into the existing generation and elimination prompts.

---

## Conviction Pipeline Reference (v3)

```
Pass 1:   Activation scoring — 8 modules scored independently → Active / Adjacent / Inactive
Pass 1.5: Regime annotation — compute_regime_flags() from activation results → active flags list
Pass 2:   LLM generation — active theories + regime flag context + channel requirement → 7-9 hypotheses with channel tags
Pass 3:   LLM elimination — adversarial attack + channel verification → SURVIVED / WOUNDED / KILLED + corrected channels
Pass 4:   Mechanical conviction scoring (zero-LLM):
            Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
            Stage 2: DISCOUNTED = RAW × D_f × D_o × D_r  →  SCORE = DISCOUNTED × 10
            Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap)  →  max(FINAL, 5.0)
Pass 5:   Human decision layer — system never recommends trades or sizes
```

LLM does: generate hypotheses with channel tags, attack hypotheses and verify channels, check falsifiers against data
Math does: activation scoring, regime flag computation, conviction scoring (all dimensions including regime alignment), overlap penalty, UNTESTABLE discount, gates, floor
