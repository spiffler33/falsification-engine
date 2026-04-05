# debt_cycle_short — PLAYBOOK.md

*Operational Run-Time Instructions*
*Last updated: April 2026*

---

## generator_guidance

### When Phase A (Expansion) is Active

1. **Determine the quadrant first.** Every expansion-phase hypothesis MUST specify whether the economy is in Goldilocks or Reflation. A hypothesis that says "equities outperform during expansion" without specifying the quadrant is not testable — QQQ outperforms in Goldilocks and underperforms in Reflation. Cite the quadrant determination inputs (CPI YoY direction, Core PCE level, breakeven direction) to support the classification.

2. **Assess cycle maturity.** Early cycle (ISM rising from below 50, unemployment starting to decline, spreads tightening from wide levels) has different risk/reward than late cycle (ISM peaking, unemployment at cycle lows, spreads at cycle tights). The Phase A activation table does not distinguish early from late — use trajectory (direction of change) to assess maturity. Cite specific indicator trajectories.

3. **Monitor late-cycle warning signs even during active expansion.** Curve flattening/inversion, SLOOS tightening, ISM rolling over, initial claims inflecting upward. These do not mean "contraction imminent" — they mean "the expansion is aging." Produce contingent hypotheses: "if ISM falls below 48 in the next 3 months, Phase B probability increases."

4. **Address the fiscal dominance interaction.** If `fiscal_dominance_liquidity` is also Active, explicitly address whether the expansion is self-sustaining (credit-driven) or fiscally sustained (deficit-driven). This distinction matters: credit-driven expansions end through the credit cycle mechanism (this theory works normally); fiscally-sustained expansions can extend beyond normal duration (timing becomes unreliable, but directional predictions still hold when the turn eventually arrives). See INTERACTION_MATRIX.md for the resolution criteria.

5. **Produce quadrant-transition hypotheses, not just current-quadrant hypotheses.** The economy can move from Goldilocks to Reflation within a quarter. Produce hypotheses about the transition mechanism and its portfolio implications.

### When Phase B (Contraction) is Active or Adjacent

1. **Determine the quadrant: Deflation or Stagflation.** This distinction is the most important single determination in the theory. It determines whether duration assets (TLT) are your best friend or your enemy. Cite inflation data to support the classification.

2. **Estimate magnitude conditional on starting conditions.** Reference starting valuations (from `valuation_mean_reversion`), fragility level (from `structural_fragility`), and long-cycle positioning (from `debt_cycle_long`) to narrow the magnitude range. Do not produce generic "-20% to -40%" estimates when cross-theory information can narrow the band.

3. **Produce recovery-leadership hypotheses.** The contraction phase is not just about the decline — it is about where leadership rotates during recovery. Reference `capital_flows` for international rotation, `valuation_mean_reversion` for sector rotation, and TACTICAL.md for the IWM/SPY recovery pattern.

### When in Late-Cycle Transition (Expansion Active, Contraction Adjacent)

This is the most operationally valuable state. Produce BOTH:

- **Continuation hypotheses:** Why the expansion may persist despite late-cycle signals. What would need to happen for the cycle to extend further. What the fiscal dominance explanation implies for positioning.
- **Turn-risk hypotheses:** What specific catalyst could trigger the phase transition. What the magnitude range would be conditional on the turn happening. What positioning should be established before the turn is confirmed.

---

## generator_prohibitions

1. **Do NOT predict the specific month of cycle turn.** The theory identifies late-cycle conditions, not the precise inflection. "Recession begins in Q3" is overspecified. "Late-cycle indicators suggest elevated recession risk over the next 6–18 months" is the appropriate level of precision.

2. **Do NOT assume the quadrant is static.** Quadrant transitions can happen within a single quarter.

3. **Do NOT ignore the fiscal dominance interaction.** A "recession is imminent" hypothesis while `fiscal_dominance_liquidity` is Active implicitly claims fiscal dominance is failing. State that explicitly and provide evidence. See INTERACTION_MATRIX.md for what constitutes evidence that fiscal dominance is losing the fight (unemployment rising AND net liquidity expanding).

4. **Do NOT produce contraction hypotheses based solely on yield curve inversion.** Inversion is a warning signal, not a contraction signal. The curve can be inverted for 12–24 months before contraction. The re-steepening from inversion — not the inversion itself — is the proximate signal.

5. **Do NOT conflate late-cycle with contraction.** Late cycle = Expansion still Active, Contraction Adjacent. The system is warning, not contracting. Positioning for late cycle is different from positioning for confirmed contraction.

---

## evaluator_priority_checks

1. **Did the generator specify the quadrant?** Reject any expansion-phase hypothesis that does not identify Goldilocks, Reflation, Stagflation, or Deflation. "Equities go up in expansion" is not a testable hypothesis — it needs quadrant context.

2. **Is the phase determination mechanically correct?** Check whether Phase B indicators are actually triggered. The generator may claim "expansion" because GDP is positive, while ISM is below 48, claims are rising, and SLOOS is tightening. The activation layer exists precisely to prevent indicator cherry-picking.

3. **Is the fiscal dominance interaction addressed?** In the current macro environment, any contraction hypothesis that does not address fiscal dominance is incomplete. If late-cycle indicators are firing but no recession is materializing, the most likely explanation is fiscal override. The generator must state this and explain why it believes the cycle will turn anyway (or acknowledge extension).

4. **Are magnitude estimates quadrant-appropriate?** Deflationary contraction: equities decline, TLT rallies sharply. Stagflationary contraction: equities decline, TLT declines or flat. These are opposite duration predictions. A hypothesis predicting both equity decline and TLT rally in a Stagflation scenario is internally inconsistent. Flag it.

5. **Does the cross-theory composition narrow the prediction?** If the hypothesis invokes both `debt_cycle_short` and `structural_fragility`, the combined prediction must be MORE specific than either alone. "Late cycle + fragility = bad" is not a valid composition. "Late-cycle indicators + elevated fragility = drawdown at upper end of range (-35% to -45%) with recovery leadership in small caps and EM" IS valid because it narrows magnitude and identifies recovery leadership.

---

## evaluator_rejection_criteria

Reject a hypothesis invoking this theory if:

1. Hard falsifier H1, H2, or H3 is currently triggered.
2. The hypothesis invokes a phase that the activation layer scores as Inactive.
3. The hypothesis predicts contraction without specifying Deflation or Stagflation quadrant.
4. The hypothesis predicts expansion without specifying Goldilocks or Reflation quadrant.
5. The hypothesis predicts contraction while `fiscal_dominance_liquidity` is Active, without providing evidence that fiscal dominance is failing (unemployment rising despite net liquidity expansion).
6. The hypothesis invokes this theory in composition with another theory but produces no specificity gain over either theory alone.

---

## composition_rules

See INTERACTION_MATRIX.md for the authoritative pairwise logic. Summary:

### Good Compositions

| Partner Theory | Value of Composition |
|---------------|---------------------|
| `structural_fragility` (Building) | Narrows magnitude estimate. Late cycle + elevated fragility = upper end of drawdown range. Recovery leadership shifts to small caps and EM. |
| `fiscal_dominance_liquidity` | Resolves the "why isn't the recession here?" question. The testable contradiction between cycle turn and fiscal override is the most important current interaction. |
| `fiscal_dominance_arithmetic` | In Stagflation quadrant: identifies worst-case scenario for traditional portfolios (equities down, bonds down, only gold and cash work). |
| `debt_cycle_long` | In Deflation quadrant: predicts the policy response escalation (MP1 → MP2 → MP3) and the sequencing trade (TLT at contraction onset → rotate to GLD/TIPS when policy response generates inflation). |
| `valuation_mean_reversion` | Modifies timing: early/mid expansion → stretched valuations can persist (earnings catch-up). Late expansion → stretched valuations meet declining earnings power, reversion through price, not earnings. |

### Prohibited or Low-Value Compositions

| Pattern | Why It Fails |
|---------|-------------|
| `debt_cycle_short` contraction + `fiscal_dominance_liquidity` Active, without resolution | This IS a contradiction. The generator must resolve it with evidence, not paper over it with narrative. |
| `debt_cycle_short` alone without quadrant | Produces untestable predictions. The quadrant is the minimum necessary context. |
| `debt_cycle_short` + `capital_flows` without specifying which EM phase is operative | Capital flow rotation is conditional on EM being in Accumulation or Rotation phase. If EM is also contracting, no rotation occurs. |

---

## common_failure_modes

### Generator Failure Modes

1. **Timing overclaim.** The generator treats late-cycle indicators as contraction signals and produces "recession in 3 months" hypotheses. The theory supports 6–18 month probability windows, not month-specific predictions.

2. **Quadrant omission.** The generator says "buy equities because we're in expansion" without specifying whether Goldilocks or Reflation is operative. This produces the wrong ETF selection half the time.

3. **Fiscal dominance dodge.** The generator produces a contraction hypothesis in a fiscal dominance environment without addressing why fiscal override will fail this time. The resulting hypothesis is unfalsifiable because it doesn't specify what evidence would confirm or deny the fiscal dominance interaction.

4. **Duration assumption.** The generator defaults to TLT as the contraction hedge without checking the inflation axis. In Stagflation, TLT is a liability, not a hedge. This is the single most expensive error the generator can make.

### Evaluator Failure Modes

1. **Over-weighting the yield curve.** The evaluator flags a contraction hypothesis as well-supported because the curve is inverted. Inversion is necessary context, not sufficient evidence. The re-steepening, not the inversion, is the signal.

2. **Under-weighting SLOOS.** SLOOS is published quarterly with a lag, making it feel "stale" compared to daily indicators. The evaluator may discount it relative to market-priced indicators (spreads, claims). But SLOOS has the best lead time of any recession indicator (3–6 quarters). Do not under-weight because of frequency.

3. **Letting the generator double-count.** If the generator invokes this theory plus `structural_fragility` plus `fiscal_dominance_liquidity`, the evaluator must check whether the indicators flagged are actually independent. Some indicators (like credit spreads) are used across multiple theories. The same observation should not be counted as confirmation of multiple theories independently. See Shared Upstream Cause Warnings in INTERACTION_MATRIX.md.

---
