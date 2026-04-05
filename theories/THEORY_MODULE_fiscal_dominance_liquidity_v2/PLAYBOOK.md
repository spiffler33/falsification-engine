# PLAYBOOK.md — Fiscal Dominance: Net Liquidity Transmission

*Theory Package: `fiscal_dominance_liquidity`*
*Last updated: April 2026*

---

## generator_guidance

When this theory is **Active**, generate hypotheses about:

1. **The current net liquidity trajectory.** What is each component doing? Is the Fed balance sheet shrinking on schedule? Is the TGA building or draining? Is RRP still declining? Compute the NET and compare to 30/60/90-day-ago levels. If net liquidity is expanding, state by how much and at what pace. This is the empirical foundation — every other hypothesis rests on it.

2. **Which asset classes are confirming the transmission.** Check the hard-versus-nominal spread. Check gold versus long bonds relative performance. Check equity correlation with net liquidity. If the assets are following the liquidity, the mechanism is working. If divergences appear, interrogate them: is the divergence temporary (positioning, news event) or structural (transmission weakening)?

3. **Whether the Fed is stealth-capitulating.** Look for balance sheet behavior inconsistent with stated QT policy. Discount window borrowing, new facilities, slowing the QT pace — all are forms of capitulation that expand net liquidity. Flag these as confirming evidence, not neutral events.

4. **The interaction with the debt cycle.** Is fiscal liquidity preventing the recession that debt-cycle theory predicts? If late-cycle indicators are firing (ISM below 50, claims rising, curve inverted) BUT unemployment stays low and GDP stays positive, the most likely explanation is fiscal dominance extending the cycle. State this explicitly and note that the extension makes the eventual contraction worse. See INTERACTION_MATRIX.md for the authoritative pairwise logic.

When this theory is **Adjacent**, hypotheses should focus on whether the mechanism is strengthening toward activation or weakening away from it. Do not generate full directional predictions from an Adjacent reading — the mechanism may not be operative.

---

## generator_prohibitions

1. **Do NOT make timing claims.** Net liquidity predicts direction, not inflection points. A net-liquidity-driven rally can pause or dip 5–8% on any given month's TGA build or short-term noise. Any hypothesis specifying "X% move by Q[N]" is exceeding the theory's scope.

2. **Do NOT predict the end of fiscal dominance.** That is an exogenous political event. The theory tells you what happens while fiscal dominance is active, not when it ends.

3. **Do NOT confuse this theory with `fiscal_dominance_arithmetic`.** This module is about the FLOW (net liquidity this quarter). The arithmetic module is about the STOCK (cumulative debt trajectory over years). They can have different activation statuses. A hypothesis that invokes multi-year devaluation arithmetic while citing net-liquidity evidence is mixing modules.

4. **Do NOT claim fiscal dominance prevents all drawdowns.** Net liquidity expansion supports asset prices directionally, but a sufficiently sharp credit contraction, geopolitical shock, or narrative shift can overwhelm the liquidity bid temporarily. The theory predicts shallower and shorter drawdowns relative to non-fiscal-dominance episodes — not immunity from drawdowns.

5. **Do NOT present net-liquidity bullishness as a substitute for mechanism identification.** Many things can cause equities to rally. A hypothesis invoking this theory must identify the specific mechanism (deficit → reserves → asset prices) and the specific evidence (net liquidity computation, hard-versus-nominal divergence, monetary policy impotence). If the hypothesis reads like generic bullishness, it is not using the theory — it is using the theory as decoration.

---

## evaluator_priority_checks

Check in this order:

1. **Is net liquidity actually expanding?** The generator may invoke this theory based on deficit data alone. Check the NET computation. If net liquidity is contracting (TGA build exceeding fiscal injection, or QT pace increasing), the theory's predictions do not apply regardless of the deficit level. The MECHANISM, not the precondition, must be operative.

2. **Is the asset-price correlation holding?** Check whether state falsifier SF2 (decorrelation) is triggered. If the SPY–net liquidity rolling correlation has fallen below 0.30, the theory is unreliable for directional asset-price claims even if net liquidity is expanding. The generator tends to assume the correlation holds — make it prove it with current data.

3. **Is the generator making a timing claim?** Reject any hypothesis specifying a percentage move in a specific quarter. The theory supports directional claims ("supported while expanding"), not point predictions.

4. **Has the generator distinguished this from a simple risk-on call?** The hypothesis must contain the specific fiscal-dominance mechanism and evidence. Generic bullishness dressed in fiscal-dominance language fails this check.

5. **Composition quality check.** When combined with other theories, the composite hypothesis must be MORE specific and MORE falsifiable than the component theories. "Fiscal dominance is extending the debt cycle and compounding fragility" is valid if it produces a specific magnitude estimate, timeline adjustment, and failure condition. "Fiscal dominance plus fragility plus late cycle means something bad is coming eventually" is unfalsifiable narrative padding. Kill it.

---

## evaluator_rejection_criteria

Reject a hypothesis invoking this theory if:

1. Net liquidity is contracting (regardless of deficit level).
2. The hypothesis makes a specific timing or magnitude claim beyond the ranges in TACTICAL.md.
3. The hypothesis invokes multi-year devaluation logic that belongs to `fiscal_dominance_arithmetic`.
4. The hypothesis cannot state a falsifiable condition under which the claim would be wrong.
5. State falsifier SF2 (decorrelation) is active AND the hypothesis makes directional asset-price predictions that depend on the net-liquidity-to-asset-price transmission.

---

## composition_rules

See INTERACTION_MATRIX.md for authoritative pairwise logic. Summary guidance for the generator and evaluator:

**Composes well with:**

- `debt_cycle_short` — Fiscal dominance extending the short-term debt cycle is the most operationally important composition in the registry. The combined prediction is more specific: attenuated contraction severity, longer cycle duration, larger eventual correction.
- `structural_fragility (Building)` — Fiscal liquidity extending the fragility-building phase. Combined prediction: longer calm period, larger eventual break. The magnitude adjustment (+12–24 months to fragility timeline, upper end of break severity) is the key composition output.
- `fiscal_dominance_arithmetic` — The two fiscal dominance modules reinforce each other. Flow (liquidity) confirms stock (arithmetic) and vice versa. Combined expression: hard-asset allocation at the upper end of both theories' ranges.
- `monetary_architecture` — Plumbing stress within a fiscal dominance regime is a buying opportunity, not a regime change. The Fed's plumbing interventions are net-additive to liquidity.

**Low-value or prohibited compositions:**

- Do NOT compose with `capital_flows` to make direct EM predictions from this theory alone. The EM channel is interaction-dependent (dollar direction determines EM performance), not a direct fiscal-dominance prediction. Let the interaction matrix handle it.
- Do NOT compose three or more theories into a single unfalsifiable narrative. Each added theory must produce a specific incremental prediction with its own failure condition. "Everything confirms everything" is not a composition — it is correlation masquerading as conviction.

---

## escalation_rules

**SF2 → DF3 escalation (decorrelation to hard falsifier):**

If state falsifier SF2 (SPY–net liquidity decorrelation below 0.30) persists for 18+ months across varied market conditions — meaning the decorrelation is not explained by a single dominant override factor (e.g., a tech earnings supercycle or a geopolitical shock) but holds across a rate-hiking period AND a cutting period, or a risk-on phase AND a risk-off phase — then escalate to deep falsifier DF3. At that point, the theory's core asset-price transmission mechanism is unreliable and hypotheses invoking directional predictions from this theory should be disconfirmed.

The evaluator is responsible for tracking the duration and conditions under which SF2 has been active. The 18-month clock resets if correlation rises back above 0.30 for 3+ consecutive months.

---

## common_failure_modes

### Generator failure modes

1. **Deficit-as-proxy-for-mechanism.** The generator cites a large deficit and concludes fiscal dominance is operative without checking whether net liquidity is actually expanding. The deficit is the fuel; net liquidity is the fire. The fuel can exist without the fire (if TGA is hoarding, QT is aggressive, or RRP is re-expanding).

2. **Treating net liquidity as omniscient.** Net liquidity is the strongest single-variable predictor of risk-asset direction since 2020. It is not the only variable. The generator overweights the liquidity signal and underweights temporary overrides (earnings shocks, geopolitical events, positioning unwinds) that can dominate for weeks or months.

3. **Module confusion with fiscal_dominance_arithmetic.** The generator invokes multi-year debt sustainability arguments while citing monthly net liquidity data, or vice versa. The two modules share a common upstream cause (deficit spending) but make different predictions on different timeframes. The discipline: fiscal_dominance_liquidity = flow mechanism and near-term transmission; fiscal_dominance_arithmetic = stock trajectory and multi-year sustainability/devaluation path.

4. **Inflation timing overconfidence.** The generator claims fiscal dominance will produce inflation on a specific timeline. The debasement channel operates on an uncertain lag — markets may take years to price in the inflation implications. The theory supports "hard assets outperform bonds" as a relative prediction, not "CPI will reach X% by date Y."

### Evaluator failure modes

1. **Dismissing the theory because rates are high.** High rates are not evidence against fiscal dominance — they are evidence FOR it (the paradoxical stimulus mechanism). The evaluator may reflexively associate high rates with tight policy. In a fiscal dominance regime, high rates are loose policy in disguise.

2. **Over-penalizing temporary decorrelation.** The SPY–net liquidity correlation broke briefly in late 2022 and re-established in 2023. Single-factor overrides (rate hike panic, AI narrative dominance) cause temporary decorrelation. The evaluator should not escalate SF2 to DF3 prematurely — the 18-month / varied-conditions threshold exists for this reason.

3. **Under-weighting the RRP exhaustion constraint.** Once the RRP is fully drained, the one-time tailwind is gone. The theory still operates (deficit → reserves → asset prices), but one amplifier is permanently removed. The evaluator should flag this when the generator fails to adjust magnitude ranges downward post-RRP-exhaustion.

---
