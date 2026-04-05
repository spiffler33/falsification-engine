# PLAYBOOK.md — Valuation Mean Reversion & Margin of Safety

*theory_id: `valuation_mean_reversion`*

---

## generator_guidance

When this theory is Active or Adjacent, the generator should produce hypotheses about:

1. **The specific valuation math.** State the current CAPE, ERP, Buffett Indicator, and SHY yield. Compute: what forward real return does the current CAPE imply? What is the opportunity cost of equities vs. cash? What drawdown to CAPE 22 (still-elevated fair value) vs. CAPE 17 (historical average)? These are arithmetic, not opinion — compute them explicitly.

2. **Which resolution channel is most likely.** Given the other active theories, assess whether the resolution is more likely to be (a) price decline, (b) earnings growth, or (c) inflationary grind. Cite the specific interaction that drives the channel assessment — do not assert a channel without identifying which other theory provides the basis. See INTERACTION_MATRIX.md for the authoritative pairwise logic.

3. **Sectoral opportunities within the expensive market.** Check each sector against its specific valuation threshold (see TACTICAL.md sector_depth). Are financials below 1.0x TBV? Is energy below 4% of S&P weight? Is the IWM/SPY PE discount above 30%? Is international at 50%+ PE discount? Produce specific sector rotation hypotheses even when the market-level view is defensive.

4. **The deployment signal.** Specify what conditions would flip this theory from "defensive" to "deploy." Produce both the defensive hypothesis (current state) and the deployment hypothesis (what the theory says to do when valuations normalize). The deployment conditions are as important as the warning conditions.

---

## generator_prohibitions

- **Do NOT predict the quarter the correction begins.** This theory has zero timing predictive power. It identifies the level from which the correction starts and the magnitude of the correction, not the date. Any timing claim must cite another theory for the catalyst.

- **Do NOT claim "valuations are extreme therefore sell everything."** Valuations have been extreme since 2020 and equities have risen substantially. The theory says forward returns are poor, not that prices cannot go higher first.

- **Do NOT ignore the sectoral depth.** A hypothesis that says "hold cash, market is expensive" without examining sector-level opportunities is incomplete. Even the most valuation-disciplined investors (Buffett) deploy selectively into sectors with margin of safety while holding cash for market-level allocation.

- **Do NOT claim this theory alone justifies short positions.** The theory identifies magnitude, not timing. Shorting based on "it's expensive" has a terrible track record because expensive can get more expensive for years. Cash (SHY) is the correct expression of the bearish view, not short SPY/QQQ.

- **Do NOT invoke valuation theory for magnitude and ignore fiscal dominance for channel.** If both theories are active, the generator must address the resolution channel explicitly.

---

## evaluator_priority_checks

1. **Did the generator state the specific valuation math?** Reject any hypothesis that claims "valuations are stretched" without citing the specific CAPE, ERP, and Buffett Indicator values. The theory is quantitative — the generator must be quantitative too.

2. **Did the generator make a timing claim?** If the hypothesis says "correction in Q3" or "drawdown within 6 months," challenge it. This theory does not support timing claims. The generator must identify which other theory provides the timing catalyst and cite it explicitly.

3. **Did the generator address the resolution channel?** If the hypothesis predicts a drawdown but fiscal_dominance_liquidity is also Active, challenge whether price decline is the right prediction or whether the inflationary-grind channel is more likely.

4. **Did the generator examine sector opportunities?** A blanket "hold cash" recommendation from an Active valuation theory is incomplete. Check whether specific sectors are at their identified thresholds.

5. **Is the ERP computation current?** The equity risk premium is the most dynamic valuation metric — it changes daily with rates and SPY price. Ensure the generator used the most recent data. A hypothesis calibrated to ERP of 0.4% is different from one calibrated to ERP of 1.5%.

6. **Composition quality check.** The most valuable compositions pair valuation (the "what" and "how far") with another theory providing timing or channel:
   - Valuation + debt cycle contraction = "what and when" (the classic Buffett deployment setup)
   - Valuation + structural fragility = "how deep" (amplified magnitude)
   - Valuation + fiscal dominance = "which channel" (price decline vs. inflationary grind)
   - If the composition does not narrow the prediction beyond what valuation theory alone provides, it is not adding value.

---

## evaluator_rejection_criteria

Reject a hypothesis invoking this theory if:

- It makes a timing claim without citing a catalyst from another theory.
- It claims "sell everything" without examining sector-level opportunities.
- It asserts "valuations are stretched" without providing the specific current CAPE, ERP, and at least one other metric.
- It invokes valuation theory for the magnitude prediction while ignoring the resolution channel when fiscal_dominance_liquidity is also Active.
- It recommends short equity positions (as opposed to cash overweight) based on valuation theory alone.
- It uses stale ERP data (more than 1 month old) for a hypothesis that depends on the cash-vs-equity comparison.

---

## composition_rules

See INTERACTION_MATRIX.md for the authoritative pairwise interaction logic. Summary of composition priorities:

**High-value compositions:**
- `valuation_mean_reversion` + `debt_cycle_short` (Contraction): The full "what, when, and how far" pairing. Valuation provides magnitude; cycle provides timing catalyst. The combined prediction is testable: "recession triggers 30–50% drawdown, producing CAPE below 22, which is the deployment signal."
- `valuation_mean_reversion` + `structural_fragility` (Building): Magnitude amplifier. Both theories point to the same drawdown but through different lenses — fragility determines the mechanism (forced selling), valuation determines the distance to fair value. Combined estimate tightens to the upper end of the magnitude range.
- `valuation_mean_reversion` + `fiscal_dominance_liquidity`: Resolution channel modifier. The composition shifts the prediction from "wait for crash" to "real returns poor for years without nominal crash." Changes the trade expression from SHY to GLD/TIP.
- `valuation_mean_reversion` + `capital_flows`: International rotation amplifier. Quantifies the forward return gap between expensive US and cheaper international markets.

**Low-value or prohibited compositions:**
- `valuation_mean_reversion` alone with a timing claim — the theory has no timing mechanism.
- `valuation_mean_reversion` + `fiscal_dominance_arithmetic` without also referencing `fiscal_dominance_liquidity` — the arithmetic module provides the structural trajectory; the liquidity module provides the near-term channel through which valuation resolution plays out. Referencing arithmetic alone for the resolution channel skips the operative mechanism.

---

## common_failure_modes

**Generator failure modes:**
- **"Market is expensive, hold cash" without sector analysis.** The most common generator failure. Forces evaluator to reject for incompleteness.
- **Timing claims disguised as magnitude claims.** Generator says "expect 30% drawdown within 12 months" — the magnitude (30%) is defensible from valuation theory; the timeframe (12 months) is not. The evaluator must separate the two.
- **Ignoring the resolution channel.** Generator predicts a price crash when fiscal dominance is also Active. The evaluator must challenge whether the crash channel is correct given the fiscal backstop.
- **Stale data.** Generator uses a CAPE or ERP figure from the prior month when the current figure has changed materially (e.g., a 10% equity rally compresses ERP further).

**Evaluator failure modes:**
- **Over-penalizing for lack of timing.** The theory explicitly disclaims timing. The evaluator should not reject a hypothesis simply because it cannot say WHEN — the theory's value is in the MAGNITUDE and RETURN EXPECTATION, not the timing.
- **Under-penalizing a "hold cash" hypothesis that ignores sectors.** A defensible but incomplete hypothesis should be scored lower, not passed through.
- **Failing to check ERP freshness.** The evaluator should confirm that the valuation data is from the current month, not a stale snapshot.

---
