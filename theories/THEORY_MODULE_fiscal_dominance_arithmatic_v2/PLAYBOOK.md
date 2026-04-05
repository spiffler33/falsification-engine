# PLAYBOOK.md — Fiscal Dominance: Devaluation Arithmetic

*Theory: fiscal_dominance_arithmetic*
*Last updated: April 2026*

---

## generator_guidance

When this theory is Active or Adjacent, the generator should produce hypotheses about:

1. **The specific arithmetic.** State the current numbers: total debt, annual interest expense, tax receipts, interest/receipts ratio, defense spending comparison, weighted average coupon vs. market rate. The strength of this theory is its mathematical specificity — every claim should be grounded in numbers, not narrative. The numbers are available via web search (Treasury monthly statements, CBO reports) and the current_theme_specifics in TACTICAL.md. Update numbers before generating.

2. **Which resolution channel is most likely and at what speed.** Devaluation is the central prediction, but speed matters for portfolio construction. Slow devaluation (2–4% sustained inflation) favors patient hard-asset positions. Fast devaluation (6–10% inflation spike) favors larger hard-asset allocation plus commodity exposure. Speed depends on whether the central bank accommodates or fights — generate hypotheses about central bank behavior.

3. **The rollover arithmetic.** Compute what interest expense will be when all existing debt has rolled into current market rates. This is deterministic given the maturity profile and current rates. It tells you where the arithmetic is GOING, not just where it is now. The trajectory is as important as the current level.

4. **Rate sensitivity.** The arithmetic is highly rate-sensitive. If the Fed is cutting (or expected to cut), the generator must adjust the arithmetic accordingly. "Interest expense will reach $1.6T" assumes rates stay at current levels — state the rate assumption explicitly and model the alternative.

5. **Time horizon framing.** This theory produces STRUCTURAL positioning hypotheses (hard assets over nominal bonds over multi-year horizons), not tactical ones. Frame hypotheses as "gold is structurally undervalued relative to the fiscal trajectory" — a positioning claim, not a timing claim.

When Adjacent, the generator should flag which specific indicators are not yet triggered and what would change the activation status. Adjacent is a monitoring state, not a positioning state.

---

## generator_prohibitions

Explicit "what NOT to claim" list:

1. **Do NOT predict a dollar collapse or hyperinflation.** The theory predicts GRADUAL devaluation, not a crisis event. The dollar retains reserve status throughout — it just buys less over time. Hyperinflation predictions are not supported by this framework (the US has too many institutional buffers).

2. **Do NOT claim this theory predicts TIMING of devaluation acceleration.** The arithmetic is deterministic but the market's recognition of the arithmetic is not. Gold can lag for years before the market prices the trajectory. The theory supports structural positioning, not tactical timing.

3. **Do NOT confuse this with `fiscal_dominance_liquidity`.** If the hypothesis is about quarterly net liquidity changes and asset price correlation, the generator is using the wrong module. This module is about the multi-year trajectory of debt sustainability. Check which module the claim actually derives from.

4. **Do NOT ignore rate sensitivity.** "Interest expense is unsustainable" is only true at CURRENT rates — if rates fall, the claim weakens (soft falsifier S2 is major severity). Every devaluation hypothesis must state its rate assumption.

5. **Do NOT claim the theory specifies the best vehicle.** "Gold will rally" is a tactical claim that belongs in TACTICAL.md context, not an invariant-theory claim. The generator should frame the hypothesis around the devaluation mechanism and its magnitude, not around a specific instrument's performance.

6. **Do NOT double-count with fiscal_dominance_liquidity.** Both theories share an upstream cause (deficit spending). If both are Active, state that they cross-confirm — but do NOT treat simultaneous activation as independent confirmation that doubles conviction. See Shared Upstream Cause Warnings in INTERACTION_MATRIX.md.

---

## evaluator_priority_checks

1. **Did the generator state the specific numbers?** This theory is mathematical. Reject any hypothesis that claims "the fiscal situation is unsustainable" without citing the current interest/receipts ratio, deficit pace, and rollover math. Vague fiscal doom is not a testable hypothesis.

2. **Did the generator distinguish this from the liquidity module?** If the hypothesis is about quarterly asset price direction driven by net liquidity, it belongs under `fiscal_dominance_liquidity`, not this module. This module produces STRUCTURAL positioning hypotheses, not TACTICAL ones.

3. **Did the generator address the rate path?** The arithmetic is highly rate-sensitive. A hypothesis that claims "interest expense will reach $1.6T" assumes rates stay at current levels. If the Fed is cutting (or expected to cut), the generator must adjust the arithmetic accordingly. Check that the interest expense projection is consistent with the rate assumptions.

4. **Is the generator claiming timing?** This theory does not predict WHEN the market fully prices devaluation. A hypothesis that claims "gold will rally 30% in Q3" is overspecified on timing. The theory supports positioning claims, not timing claims.

5. **Is the expression bounded by expression monitors?** Check EM1 in TACTICAL.md. If gold has underperformed cash for an extended period while the arithmetic indicators are triggered, flag the trade expression as suspect and prompt the generator to consider alternative vehicles — while separately assessing whether the underlying arithmetic diagnosis remains valid.

6. **Is the generator double-counting shared upstream causes?** If both `fiscal_dominance_arithmetic` and `fiscal_dominance_liquidity` are Active, check whether the hypothesis treats them as independent confirmation. They share the same upstream cause (deficit spending). Conviction should be additive only for the DISTINCT predictions each theory makes.

---

## evaluator_rejection_criteria

Reject a hypothesis invoking this theory if:

1. It cannot cite the current interest/receipts ratio and deficit pace. Specificity is the minimum bar.
2. It predicts timing (quarter or specific month) for devaluation acceleration. The theory does not support timing claims.
3. It predicts dollar collapse or hyperinflation. The theory predicts gradual erosion within a functioning system.
4. It is actually a `fiscal_dominance_liquidity` hypothesis (quarterly asset price direction from net liquidity changes) mis-labeled as arithmetic.
5. It does not state its rate assumption. Rate sensitivity is the theory's key uncertainty — ignoring it is a specification failure.
6. It claims specific vehicle outperformance as a theory-level conclusion rather than a tactical expression.

---

## composition_rules

This theory composes with other theories as specified in INTERACTION_MATRIX.md. Key compositions and their value:

| Composition Partner | Value Added | What to Check |
|--------------------|------------|---------------|
| `fiscal_dominance_liquidity` | Cross-confirms the devaluation timeline. Liquidity active = deficit is currently large and transmitting to asset prices. Arithmetic active = cumulative result is untenable. Both together = devaluation is both HAPPENING (in slow motion) and INEVITABLE (the math forces it). Expression sizing at the upper end of both theories' ranges. | CRITICAL: these share an upstream cause (deficit spending). Simultaneous activation is NOT independent confirmation. Conviction is additive only for DISTINCT predictions: liquidity predicts near-term direction (1–6 months); arithmetic predicts structural trajectory (3–10 years). |
| `debt_cycle_short` (Contraction) | Recession WORSENS the fiscal arithmetic. Tax receipts fall, automatic stabilizers increase spending, deficit widens. Interest/receipts ratio spikes. GLD is the better recession hedge than TLT when fiscal arithmetic is untenable — TLT rally is capped and short-lived because recession-driven deficit widening is permanent. | The generator should flag the GLD > TLT preference during recession as a specific insight from this composition. The stagflationary variant is the highest-impact combined scenario. |
| `valuation_mean_reversion` | Resolves the apparent contradiction: valuation says "hold cash," arithmetic says "cash loses purchasing power." Resolution is by TIME HORIZON: cash for the 1–3 year horizon (earn risk-free while waiting for the valuation correction); gold for the 3–10 year horizon (protect against devaluation). Portfolio construction: split the defensive allocation between cash and gold. | The generator must specify the time horizon when presenting this composition. Without time horizon, the two theories appear contradictory. |
| `monetary_architecture` | Central bank buying provides a structural floor under gold that makes the gold position lower-risk than the arithmetic alone justifies. The downside for gold is structurally limited by CB buying. Changes position sizing calculus — larger gold position justified when both theories are Active. | Both theories predict gold outperformance via related but distinct mechanisms. The distinct split: arithmetic = debasement demand; monetary architecture = reserve-composition demand. See Shared Upstream Cause Warnings. |

### Low-Value or Prohibited Compositions

- **fiscal_dominance_arithmetic × capital_flows:** The connection runs through dollar weakness → EM outperformance, which is already captured by `fiscal_dominance_liquidity` × `capital_flows`. Arithmetic does not add a distinct mechanism for capital flows beyond what liquidity already provides. Do not generate separate capital-flow hypotheses from this theory.
- **fiscal_dominance_arithmetic × debt_cycle_long:** The long cycle provides context for WHY the arithmetic reached this point (decades of debt accumulation, MP escalation) but is not a direct pairwise interaction. Do not generate hypotheses that cite both theories unless the long-cycle positioning adds a specific prediction beyond the arithmetic.

---

## common_failure_modes

### Generator Failure Modes

1. **Vague fiscal doom.** The generator produces "the fiscal situation is unsustainable" without specific numbers. This is not a testable hypothesis — it is commentary. Require the arithmetic.

2. **Module confusion with fiscal_dominance_liquidity.** The generator produces a quarterly asset-price hypothesis (e.g., "SPY will rally because net liquidity is expanding") and attributes it to this module. This is a liquidity hypothesis, not an arithmetic hypothesis. The distinction: liquidity = flow, arithmetic = stock.

3. **Timing claims.** The generator predicts "gold will rally 30% in Q3 because the arithmetic is untenable." The arithmetic is untenable — but the theory does not predict WHEN the market prices it. Structural positioning, not tactical timing.

4. **Ignoring rate sensitivity.** The generator treats the interest expense trajectory as a certainty without acknowledging that rate cuts (soft falsifier S2) would materially alter it. Every arithmetic hypothesis must state its rate assumption.

5. **Hyperinflation escalation.** The generator escalates from "gradual devaluation" to "dollar collapse" without justification. The theory explicitly predicts gradual erosion, not catastrophe. The US has institutional buffers (independent central bank, deep capital markets, rule of law) that prevent hyperinflation.

6. **Double-counting with liquidity.** The generator cites both fiscal_dominance_arithmetic and fiscal_dominance_liquidity as "independent confirmation" of the devaluation thesis. They share an upstream cause. The generator must state the distinct contribution of each.

### Evaluator Failure Modes

1. **Over-penalizing for dollar strength.** Dollar strength (S1) is a medium-severity soft falsifier that impairs the expression, not the theory. The evaluator should not kill an arithmetic hypothesis because the dollar is strong — it should note the expression is impaired and the timeline extends.

2. **Conflating theory falsification with expression failure.** If gold is underperforming (EM1), the evaluator may incorrectly treat this as evidence the arithmetic is wrong. The arithmetic can be correct and gold can still be the wrong vehicle. Separate the assessment.

3. **Ignoring rate sensitivity in the other direction.** If rates are rising, the evaluator should note that the arithmetic is WORSENING (interest expense rising faster) — this strengthens, not weakens, the theory. Rising rates are bad for the expression (gold may underperform in the short term due to higher real rates) but good for the theory (the arithmetic trap deepens).

4. **Under-weighting S2.** Soft falsifier S2 (rate cuts to below 3%) is MAJOR severity — the most consequential soft falsifier. If rates fall substantially, the evaluator must apply the full 0.45 discount. This is the theory's key vulnerability and must not be glossed over.

---
