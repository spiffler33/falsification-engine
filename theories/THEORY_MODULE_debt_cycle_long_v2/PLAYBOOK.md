# debt_cycle_long — PLAYBOOK.md

*Operational Run-Time Instructions — updated as engine evolves*

---

## generator_guidance

When this theory is Active, its primary role is as a **structural modifier** of other theories' predictions. It does not produce standalone monthly trade ideas.

1. **Always state the MP classification.** When generating hypotheses, specify the current position in the MP1→MP2→MP3 framework (see TACTICAL.md `current_theme_specifics` for current assessment). The MP classification provides the structural context for every other prediction.

2. **Modify short-term cycle predictions.** If `debt_cycle_short` is also Active, generate hypotheses about HOW the late long-term cycle changes short-cycle behaviour: faster policy response, shorter recessions, more inflationary recoveries, less reliable traditional indicators. Do NOT simply repeat short-cycle predictions without the long-cycle modification.

3. **Specify the resolution scenario.** The theory has two possible resolution paths: orderly financial repression (1940s template) and Japan-style stagnation (1990s template). The generator should assess which is more likely given current conditions and explain why. Default assumption: orderly financial repression (base case) with Japan-style stagnation as the primary alternative.

4. **Use this theory to justify structural positions, not tactical trades.** When referencing gold as a long-term holding, the long-term cycle provides the structural justification. This framing changes how the position is sized and managed — core holding maintained for the duration of the late cycle, not traded around.

5. **Connect to fiscal dominance modules when both are Active.** The long-term cycle explains WHY fiscal dominance is structural (MP1/MP2 exhausted, political system converged on fiscal expansion). The fiscal dominance modules provide the operational detail. The generator should reference the long-cycle context when invoking fiscal dominance predictions. See INTERACTION_MATRIX.md for the authoritative pairwise logic.

---

## generator_prohibitions

1. **Do NOT use this theory to predict near-term market direction.** It does not predict what happens next quarter. It predicts the structural environment within which next quarter's events occur.
2. **Do NOT claim specific resolution timing.** Historical resolutions took 9-16 years. Japan is 30+ years with no resolution. The timeline is genuinely uncertain.
3. **Do NOT assume the 1940s template is the only resolution.** The Japan scenario (S2, major severity) is a genuine alternative where the theory is correct but asset-price predictions substantially miss. Every hypothesis must address this alternative.
4. **Do NOT double-count with `fiscal_dominance_arithmetic`.** The long-term cycle contextualises the fiscal arithmetic — explains WHY it is untenable. The specific numbers (interest/receipts ratio, deficit pace) belong to the arithmetic module. This module provides the structural "why"; that module provides the quantitative "how bad." See INTERACTION_MATRIX.md Shared Upstream Cause Warnings.
5. **Do NOT generate hypotheses where debt_cycle_long is the sole theory invoked.** This theory is a modifier and contextualiser, not a standalone signal source. Every hypothesis must connect to at least one other theory's mechanism for its near-term or medium-term prediction.

---

## evaluator_priority_checks

1. **Modifier vs. standalone check.** Is the generator using this theory as a modifier of other theories' predictions, or as a standalone signal? A hypothesis that says "long-term cycle is late, therefore buy gold" without connecting to another theory's mechanism is structurally incomplete. The long-term cycle provides the backdrop; other theories provide the mechanism.

2. **Japan alternative check.** Did the generator address the Japan scenario? Any hypothesis that assumes the 1940s financial repression template without acknowledging Japan-style stagnation is incomplete. The evaluator should require: "The base case is orderly financial repression because [specific reasons]. The Japan scenario is less likely because [specific differences]." If the generator cannot articulate why Japan is less likely, discount conviction.

3. **MP classification consistency.** Is the stated MP classification (MP1 / MP2 / MP3 / transitioning) consistent with observed data? If the generator claims "we're still in MP1" while the Fed's balance sheet is 26% of GDP and fiscal deficits exceed $2T during non-recession, the classification is wrong. Verify against ACTIVATION.md indicators.

4. **Short-cycle modification check.** When this theory is Active alongside `debt_cycle_short`, did the generator produce modified short-cycle predictions? Standard short-cycle predictions (e.g., "recession lasts 18-24 months with gradual recovery") without late-long-cycle modification (shorter recession, faster policy response, more inflationary recovery) are using the wrong playbook.

5. **Double-counting check.** If both this theory and a fiscal dominance module are invoked, did the generator treat them as independent confirmation or as the same structural condition observed through different lenses? The long cycle explains WHY fiscal dominance exists; the fiscal dominance modules describe HOW it operates. Simultaneous activation is expected — it is NOT two independent signals. See INTERACTION_MATRIX.md Shared Upstream Cause Warnings.

---

## evaluator_rejection_criteria

1. **Reject** any hypothesis that uses debt_cycle_long as its only theoretical basis without connecting to at least one other theory's mechanism for a specific directional prediction.
2. **Reject** any hypothesis that predicts near-term market direction (1-3 months) based solely on long-cycle positioning.
3. **Reject** any hypothesis that assumes orderly financial repression as the resolution path without addressing the Japan alternative and stating why it is less likely.
4. **Reject** any hypothesis that claims simultaneous activation of debt_cycle_long and fiscal_dominance modules constitutes independent confirmation of the same directional prediction.

---

## composition_rules

Authoritative pairwise logic is in INTERACTION_MATRIX.md. Summary of composition quality:

**High-value compositions:**

| Paired Theory | Composition Value | What the Composition Should Produce |
|--------------|-------------------|-------------------------------------|
| `debt_cycle_short` | Highest value in the registry | Modified short-cycle predictions: shorter recessions, faster policy response, more inflationary recoveries, less reliable traditional indicators. The combination should produce a DIFFERENT prediction than standard short-cycle analysis alone. |
| `fiscal_dominance_liquidity` | High | Elevates fiscal dominance from "temporary policy choice" to "structural feature of this era." The combination extends the predicted persistence of fiscal liquidity injection through multiple short-term cycles. |
| `structural_fragility` | High | Modifies fragility resolution — authorities intervene to truncate drawdowns (policy floor at -20% to -30%), but each intervention compounds fragility for the next cycle. Changes magnitude estimates: shallower drawdown, faster recovery, more inflationary aftermath. |
| `monetary_architecture` | High | Extends the time horizon of the gold position from monetary_architecture's 5-15 years to the full 10-20 year late-cycle resolution period. Justifies structurally larger gold allocation as a core holding. |

**Low-value or prohibited compositions:**

| Composition | Issue |
|------------|-------|
| debt_cycle_long alone | No value as standalone. Must modify another theory to produce actionable predictions. |
| debt_cycle_long + fiscal_dominance_arithmetic (as independent signals) | These share upstream causes (deficit spending, MP3 dynamics). Simultaneous activation is one observation through two lenses. See Shared Upstream Cause Warnings. |
| debt_cycle_long + fiscal_dominance_liquidity + fiscal_dominance_arithmetic (triple count) | All three are manifestations of the same late-cycle condition. The long cycle provides context; liquidity provides the flow mechanism; arithmetic provides the stock diagnosis. Do not add conviction for each — add conviction for the DISTINCT prediction each makes. |

---

## common_failure_modes

### Generator failure modes

1. **Oracle mode.** Using the long cycle as an oracle rather than a modifier — producing standalone "buy gold because late cycle" without connecting to another theory's mechanism. The theory provides structural context; it needs a mechanism partner for any actionable prediction.
2. **Japan blindness.** Ignoring the Japan alternative — treating orderly financial repression as the only outcome. The Japan scenario is a major-severity soft falsifier specifically because it represents the most important alternative resolution where the diagnosis is correct but the trade expressions are wrong.
3. **Temporal overreach.** Predicting near-term market moves from a 10-30 year structural thesis. The theory does not tell you what happens next month. It tells you the structural environment is different from what the textbooks describe.
4. **Fiscal dominance double-count.** Treating debt_cycle_long activation alongside fiscal dominance activation as independent confirmation. These are the same structural condition observed from different vantage points.
5. **Resolution certainty.** Overstating certainty about which resolution path (orderly repression vs. Japan stagnation vs. disorderly crisis) or when resolution occurs. The theory identifies the structural condition; it does not determine the resolution timeline or channel.

### Evaluator failure modes

1. **Penalising structural breadth.** Discounting the theory for lack of near-term predictive specificity. The theory's value is structural context, not tactical signals. A well-formed hypothesis that uses debt_cycle_long to MODIFY another theory's prediction is doing what the theory is designed to do.
2. **Confusing S2 with falsification.** Treating the Japan scenario as evidence that the theory is wrong. S2 is a major-severity soft falsifier — it changes the consequences, not the diagnosis. The late cycle is still real in the Japan outcome; the asset-price predictions change.
3. **Missing modification check.** Failing to verify that short-cycle predictions are modified when both theories are Active. Standard short-cycle analysis without late-long-cycle modification is the most common composition failure.
4. **Over-penalising shared causes.** Discounting the entire prediction when shared upstream causes are present, rather than discounting only the shared component. The distinct predictions each theory makes beyond the shared cause should still be evaluated independently.
