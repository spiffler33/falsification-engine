# Structural Fragility — PLAYBOOK.md

*Theory Package: structural_fragility*
*Reorganised: April 2026*
*Layer: Operational run-time instructions — updated as engine evolves*

---

## generator_guidance

### When Active (Building) — Phase A

Generate hypotheses about:

1. **What specific fragilities are compounding.** Identify which names are driving concentration, which instruments carry the leverage, which markets exhibit complacency. Be specific — "fragility is building" is not a hypothesis; "top-10 concentration at 35% driven by 5 semiconductor names, with margin debt at record highs and VIX at 12" is a hypothesis.

2. **What catalysts could trigger the break.** Draw from other Active theories — a debt cycle turn, an earnings miss in the dominant investment theme, a fiscal consolidation shock, a plumbing event. Catalysts come from OUTSIDE this theory. Do not invent timing.

3. **What the mechanism-chain looks like.** Combine with other Active theories to produce specific predictions about break type: deflationary, inflationary, or stagflationary. The break type determines which assets are defensive. See INTERACTION_MATRIX.md for valid combinations.

4. **What the severity estimate is conditional on a catalyst arriving.** Use concentration level, leverage, passive share to calibrate the magnitude range. Produce a range, not a point estimate. Reference the directional predictions in TACTICAL.md for the mapping.

### When Active (Resolving) — Phase B

Generate hypotheses about:

1. **Whether forced selling is exhausted.** Check Phase B context flags (narrative shift, fund liquidation evidence), margin debt trajectory, and VIX term structure (backwardation → contango transition signals panic subsiding).

2. **What is mispriced in the wreckage.** Broad-market-level and sector-level. Mechanical selling does not discriminate by quality — identify where quality is cheapest.

3. **What recovery leadership looks like.** Draw from INTERACTION_MATRIX.md: capital_flows theory for international rotation, valuation_mean_reversion for sector rotation.

### When Adjacent

Generate monitoring hypotheses: "If [indicator X] crosses [threshold Y], fragility moves from Adjacent to Active." Useful for pre-positioning or watchlist construction.

---

## generator_prohibitions

1. **No timing claims.** This theory does NOT predict when the break occurs. Any hypothesis of the form "the break will happen in [quarter/month/year]" is a scope violation. The generator may estimate proximity using other theories' cycle positioning (via INTERACTION_MATRIX.md), but timing precision is outside this module's scope.

2. **No vague fragility claims.** "Everything is fragile" is not a hypothesis. The generator must specify WHICH fragility vectors are loaded, to WHAT degree, and what the conditional severity estimate is.

3. **No standalone fragility hypotheses without catalyst specification.** A fragility hypothesis must either (a) specify which catalyst class could trigger the break (drawn from other Active theories) or (b) explicitly state "severity estimate conditional on an unspecified catalyst" and accept the lower conviction that implies.

4. **No Phase B claims when Phase A is Active.** Do not generate "buy the dip" hypotheses when the mechanical indicators show fragility building, not resolving. Phase mismatch is the most common generator error with this theory.

5. **No conflation of mechanism interactions with asset-expression consequences.** A mechanism interaction modifies the break itself (type, magnitude, duration). An asset-expression consequence describes where capital flows after the break without modifying the break mechanism. These produce different kinds of predictions at different confidence levels.

---

## evaluator_priority_checks

1. **Phase verification.** Is the theory legitimately in the phase the generator invoked? Do not let the generator claim "resolving" when implied vol is 12 and there has been no drawdown. Check Phase B indicators mechanically.

2. **Hard falsifier check.** Are any of H1–H4 triggered? Pay special attention to H2 in the current environment — the capex/revenue mismatch is the most likely falsifier to trigger if the dominant theme delivers revenue. Check the expression monitor in TACTICAL.md for current status.

3. **Scope compliance — timing.** Is the generator making a timing claim? This is a hard scope violation. The theory predicts severity conditional on catalyst, not timing. If the hypothesis says "the break will happen in Q3," reject the timing claim.

4. **Combination quality.** If the generator combined this theory with others, did the combination NARROW the prediction? A "fragility + fiscal dominance + late debt cycle" hypothesis should produce a SPECIFIC prediction about break type and magnitude, not a vague "everything is fragile." Check against INTERACTION_MATRIX.md for valid combinations and expected specificity gains.

5. **Mechanism vs. expression distinction.** Did the generator correctly distinguish mechanism interactions from asset-expression consequences? A mechanism interaction modifies the break itself. An asset-expression consequence describes post-break capital flows. Conflating them produces false precision.

---

## evaluator_rejection_criteria

Reject a hypothesis invoking this theory if:

1. **Any hard falsifier (H1–H4) is triggered.** The mechanism the hypothesis relies on has been disconfirmed.
2. **Timing claim present.** The hypothesis specifies when the break will occur. This exceeds scope.
3. **Phase mismatch.** The hypothesis invokes Phase B (resolving) when mechanical indicators show Phase A (building), or vice versa.
4. **No catalyst specified and no explicit conditionality.** The hypothesis claims "fragility will cause a drawdown" without specifying a catalyst or stating "conditional on catalyst."
5. **Vague severity.** The hypothesis invokes fragility without a magnitude range or mechanism chain. "The market is fragile" is an observation, not a falsifiable hypothesis.
6. **Invalid theory combination.** The hypothesis combines this theory with another in a way that contradicts INTERACTION_MATRIX.md logic (e.g., claiming a deflationary break while fiscal_dominance_arithmetic is Active, which the matrix says produces stagflationary resolution).

---

## composition_rules

See INTERACTION_MATRIX.md for the authoritative pairwise logic. Summary of composition behavior:

| Combination | Quality | Notes |
|-------------|---------|-------|
| structural_fragility + debt_cycle_short (late/contraction) | **High value** | Narrows break-type to deflationary. Adds duration (TLT) as high-conviction expression. |
| structural_fragility + fiscal_dominance_liquidity | **High value** | Narrows magnitude (shallower) and changes recovery type (inflationary, not deflationary). |
| structural_fragility + fiscal_dominance_arithmetic | **High value** | Narrows break-type to stagflationary. Eliminates bonds as hedge. Cash and gold only defensive assets. |
| structural_fragility + valuation_mean_reversion | **High value** | Narrows magnitude to upper end of range. Extends recovery timeline. |
| structural_fragility + capital_flows | **Moderate value** | Adds post-break rotation prediction (international outperformance). Does not modify the break mechanism. |
| structural_fragility + monetary_architecture | **Moderate value** | Crisis accelerates monetary transition. Adds gold as structural post-break position. |
| structural_fragility + debt_cycle_long | **Context only** | Modifies how authorities respond to the break (intervene vs. allow clearing). Does not change the break itself. |
| structural_fragility alone (no combination) | **Low value** | Without a catalyst theory, the hypothesis is purely conditional: "IF a catalyst arrives, THEN severity is X." Valid but low conviction because it cannot be actioned until the catalyst appears. |

**Prohibited composition:** Fragility (Building) + Fragility (Resolving). Phases are mutually exclusive.

---

## common_failure_modes

### Generator failure modes

| Failure | Description | Fix |
|---------|-------------|-----|
| **Timing oracle** | Generator uses fragility indicators to predict WHEN the break happens. "VIX at 11 and concentration at 34% means crash within 6 months." | Reject timing claim. Fragility predicts severity, not timing. |
| **Vague doom** | Generator produces "everything is fragile, be cautious" without specifying which vectors are loaded, what the magnitude range is, or which catalysts could trigger. | Require specific fragility vector identification and conditional magnitude range. |
| **Phase confusion** | Generator recommends buying the dip (Phase B logic) when Phase A is Active, or recommends defensive positioning (Phase A logic) when Phase B is Active. | Check phase mechanically before evaluating the hypothesis content. |
| **Independence assumption** | Generator treats fragility as an independent signal, ignoring that many fragility indicators share upstream causes with other theories (e.g., low VIX is also a debt_cycle_short expansion indicator). | Check INTERACTION_MATRIX.md. Shared upstream causes should be discounted, not double-counted. |

### Evaluator failure modes

| Failure | Description | Fix |
|---------|-------------|-----|
| **Over-penalizing conditionality** | Evaluator discounts a fragility hypothesis because it "doesn't predict when." Conditionality is a FEATURE, not a weakness — it's honest scope. | Grade conditionality as a strength if the severity estimate is well-specified. |
| **Ignoring partial falsification** | H2 triggers (capex generating revenue) but evaluator disqualifies ALL fragility, not just the capex/revenue channel. | H2 is channel-specific. Other fragility channels (concentration, leverage, passive) remain independently testable. |
| **Conflating soft falsifiers with hard** | Evaluator treats S1 (central bank backstop) as disqualifying the theory rather than discounting magnitude. | Soft falsifiers discount; hard falsifiers disqualify. Apply the correct severity mechanically. |

---
