# Theory Module: Structural Fragility (Minsky Dynamics)

*Version 1.0 — March 2026*
*Status: Prototype — thresholds calibrated against historical episodes, pending live testing*

---

## theory_id

`structural_fragility`

---

## scope_limits

This theory diagnoses the **presence and severity** of structural fragility. It does **not** predict timing.

| Scope | In / Out | Rationale |
|-------|----------|-----------|
| Severity of break conditional on catalyst | **In scope** | The theory quantifies how bad the break will be given the fragility level (concentration, leverage, passive share, capex/revenue mismatch). Higher fragility = larger drawdown magnitude. |
| Identification of potential catalysts | **In scope** | The theory identifies which fragility vectors are loaded (which names, which instruments, which mismatches). Combined with other theories, this narrows the set of plausible catalysts. |
| Timing of the break | **Out of scope — hard limit** | Fragility building does NOT predict when the break occurs. Fragility can compound for 2-3 years beyond the point where all Phase A indicators are active. Being early is indistinguishable from being wrong. Any hypothesis that invokes this theory to make a timing claim (e.g., "the break will happen in Q3") is exceeding the theory's scope and should be rejected by the evaluator. The theory supports "IF a catalyst arrives, THEN the severity is X" — not "a catalyst will arrive at time T." |
| Post-break opportunity identification | **In scope** | Phase B diagnoses whether forced selling is exhausted and what is mispriced. This is a separate activation with its own indicators. |

---

## activation_conditions

This theory has two distinct activation phases. The system must determine which phase is operative — they have opposite investment implications.

### Phase A: Fragility Building

The mechanism is accumulating. Stability is breeding instability. Markets appear calm but structural risk is compounding. The implication is defensive: reduce exposure to concentrated/fragile assets, increase optionality.

| Indicator | Metric Source | Threshold | Direction | Weight | Rationale |
|-----------|--------------|-----------|-----------|--------|-----------|
| VIX level | `^VIX` | Below 14 | below | 0.10 | Extreme complacency. Sub-14 VIX has preceded every major drawdown since 2000 by 6-18 months. |
| VIX-realized vol gap | computed: `VIX - 20d_realized_vol` | Above 5 points | above | 0.10 | Market pricing more implied vol than is materializing. Paradoxically bearish: sellers of vol are harvesting premium, compressing realized, creating reflexive calm. |
| HY spread | `credit.hy_spread` | Below 300bp | below | 0.15 | Market pricing near-zero default risk. Historically, sub-300bp HY spreads have preceded every widening event by 6-24 months. The tighter the spread, the more violent the reversal. |
| Top 10 concentration | computed: `top_10_sp500_weight` | Above 30% | above | 0.20 | Passive amplification loop is active. Index beta is becoming the beta of a handful of names. Effective diversification declining. This is the single most important fragility indicator because it determines the severity of the eventual unwind. |
| Capex/revenue mismatch | web search required | Dominant theme capex exceeding identifiable revenue by 3x+ | above | 0.15 | Current application: AI infrastructure. Hyperscaler capex committed ($200B+/year) vs. identifiable AI revenue outside of hyperscalers themselves. When the gap between spending and revenue generation exceeds 3x, cliff risk is present: capex is someone's revenue today, but the revenue justifying the capex is 3-5 years away. |
| Margin debt | web search: FINRA margin statistics | At or within 10% of record highs | above | 0.10 | Leverage amplifies both directions. Record margin debt doesn't cause the break but determines its severity. Forced liquidation from margin calls is the transmission mechanism that converts a decline into a cascade. |
| QQQ/IWM ratio | computed: `qqq_iwm_ratio` | Above 2-year high | above | 0.10 | Proxy for narrow leadership. When large-cap growth dominance over small-cap value is at extremes, the market is pricing perfection in a narrow set of names and distress in everything else. Mean reversion in this ratio has historically coincided with broader market stress. |
| Passive fund share | web search: ICI or Morningstar data | Above 50% of US equity AUM | above | 0.10 | Structural parameter, not cyclical. Once passive exceeds 50%, the reflexive loop (price rise → weight increase → passive inflow → price rise) dominates marginal price-setting. This doesn't trigger the break but determines the mechanism of the break: mechanical, correlated, non-linear. |

**Activation scoring for Phase A:**
- Weighted score ≥ 0.60 → **Active (Building)**
- Weighted score 0.30–0.59 → **Adjacent (Building)**
- Weighted score < 0.30 → **Inactive**

### Phase B: Fragility Resolving

The mechanism has triggered. The Minsky moment is underway or has recently occurred. The implication is opportunistic: forced selling creates prices disconnected from fundamentals. The question shifts from "when does it break" to "what is mispriced in the wreckage."

**Mechanical indicators (scored):**

| Indicator | Metric Source | Threshold | Direction | Weight | Rationale |
|-----------|--------------|-----------|-----------|--------|-----------|
| VIX level | `^VIX` | Above 35 | above | 0.20 | Panic-level implied vol. Historically, VIX above 35 has coincided with forced-selling events where prices overshoot fundamentals to the downside. |
| HY spread | `credit.hy_spread` | Above 600bp | above | 0.20 | Credit market pricing meaningful default risk. Forced selling by constrained institutions (insurance, pensions with rating mandates) creates mechanical selling disconnected from fundamental analysis. |
| Drawdown depth | computed: `spy_drawdown_from_52w_high` | Below -20% | below | 0.20 | Bear market territory. The depth matters because it determines which forced-selling mechanisms have activated: -10% gets retail margin calls, -20% gets institutional risk limits, -30% gets systematic deleveraging. |
| CAPE level | web search: Shiller CAPE | Below 20 | below | 0.15 | Valuations have compressed to levels that historically offer strong forward returns. Below 20 CAPE, the arithmetic favors equity ownership regardless of narrative. |

**Activation scoring for Phase B (mechanical indicators only):**
- Weighted score ≥ 0.60 → **Active (Resolving)**
- Weighted score 0.30–0.59 → **Adjacent (Resolving)**
- Weighted score < 0.30 → **Inactive**

**Supplementary adjunct flags (qualitative — not scored mechanically, used for evaluation context only):**

These flags provide qualitative confirmation that forced selling is active or exhausted. They inform the evaluator's assessment of Phase B hypotheses but do NOT contribute to the mechanical activation score. This separation prevents narrative-driven qualitative judgments from contaminating an otherwise quantitative activation threshold.

| Flag | Source | What to look for | Usage |
|------|--------|-------------------|-------|
| Narrative shift | Web search: financial media sentiment | "Buy the dip" replaced by "this time is different (to the downside)." Capitulation sentiment. When the dominant narrative shifts from opportunity to permanent impairment, forced sellers are usually exhausted. | Confirms Phase B is mature (forced selling near exhaustion). If Phase B is mechanically Active AND this flag is present, conviction in post-break positioning increases. If Phase B is mechanically Active but this flag is absent, forced selling may still be accelerating — caution on timing of opportunistic entry. |
| Fund liquidation evidence | Web search: financial news, SEC filings | Visible fund closures, redemption gates, or forced position unwinds. Archegos (2021), LTCM (1998), and the quant deleveraging (August 2007) all produced visible liquidation before the broader market found its bottom. | Direct evidence that the forced-selling mechanism is active or recently exhausted. Presence during Phase B confirms the Minsky mechanism is operative (not just a sentiment-driven selloff). Absence during a drawdown suggests the decline may be orderly rather than forced — weakens the Phase B thesis. |

**Important:** Phases A and B are mutually exclusive in practice. If Phase B is Active, Phase A is by definition Inactive (the fragility has already resolved into the break). The activation layer should check Phase B first — if Active, skip Phase A scoring.

---

## core_mechanism

### Causal Chain (Phase A: Fragility Building)

```
1. Extended period of low volatility + easy credit + rising asset prices
   ↓
2. Market participants shift from hedge financing (income covers debt service)
   to speculative financing (must refinance to survive)
   to Ponzi financing (depend on asset appreciation to service debt)
   ↓
3. This progression is invisible in aggregate statistics —
   standard risk metrics (VaR, correlations, default rates) look benign
   BECAUSE the stability itself suppresses measured risk
   ↓
4. Concentration amplifies through passive flows:
   Rising price → higher index weight → more passive inflows → higher price
   (reflexive loop, documented: ~50% of US equity AUM now passive)
   ↓
5. Effective diversification declines:
   When top 10 names are 30%+ of index, "the market" IS those names.
   Investors who think they own a diversified index actually own a concentrated bet.
   Risk models underestimate because they use backward-looking correlations
   from the calm period — precisely the correlations that will break.
   ↓
6. Liquidity is illusory:
   High daily volume during calm ≠ available liquidity during stress.
   Market makers widen spreads, systematic strategies withdraw, bid evaporates.
   The order book that existed yesterday doesn't exist during the event.
   ↓
7. A catalyst arrives (recession, credit event, earnings miss in dominant theme,
   exogenous shock). The specific catalyst is unpredictable.
   What IS predictable: the SEVERITY of the response given the fragility level.
   ↓
8. Non-linear decline:
   Passive outflows are mechanical (correlated, forced, not discretionary).
   Margin calls force liquidation.
   Systematic strategies hit stop-losses simultaneously.
   VIX spikes → vol-targeting funds deleverage → selling begets selling.
   ↓
9. Resolution: prices overshoot fair value to the downside
   because the selling is mechanical, not fundamental.
   This creates the opportunity described in Phase B.
```

### Causal Chain (Phase B: Fragility Resolving)

```
1. The break has occurred. Forced selling is active or recently exhausted.
   ↓
2. Prices are below intrinsic value for a meaningful subset of assets
   because mechanical selling does not discriminate by quality.
   ↓
3. The opportunity: assets with intact cash flows and business models
   priced at levels implying permanent impairment.
   ↓
4. The risk: catching a falling knife — the forced selling may not be over.
   The diagnostic: are the forced sellers exhausted?
   Check: fund liquidation evidence, margin debt declining, VIX term structure
   (backwardation → contango transition signals panic subsiding).
   ↓
5. Recovery leadership: what led during the fragility-building phase
   typically does NOT lead during recovery. Narrow leadership gives way
   to broad-based recovery. Small caps, value, and international
   historically outperform during post-Minsky recoveries.
```

### Time Horizon

- **Phase A (building):** Months to years. Fragility can compound for 2-3 years before resolving. This is the hardest part — being early is indistinguishable from being wrong, and the cost of positioning too early is significant (opportunity cost of underperformance while fragility builds further).
- **Phase B (resolving):** Weeks to months. The break itself is fast (the 2008 crash took 18 months peak-to-trough but the acute phase was 8 weeks). The opportunity window after forced selling exhausts is typically 3-6 months before institutional buyers reprice assets.

---

## predictions_when_active

### Directional (Phase A — Fragility Building)

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| SPY | Vulnerable to drawdown | -25% to -40% from peak | 12-24 months from catalyst | Passive outflows + margin calls + systematic deleveraging. Magnitude depends on concentration level at the time of break. |
| QQQ | Underperforms SPY during break | -30% to -50% from peak | 12-24 months | Higher concentration, higher beta, more systematic/momentum exposure. The reflexive loop that drove outperformance drives underperformance in reverse. |
| IWM | Declines WITH index initially, recovers faster | -20% to -35% initially, then outperforms by 15-25% | Decline: first 3-6 months. Outperformance: following 12 months | Small caps are less owned by passive (lower index weight), less exposed to forced systematic selling. |
| SHY | Outperforms during break | +2% to +5% total return | During break period | Cash is the anti-fragility asset. Its return is certain; everything else is repricing. |
| TLT | Conditional — see below | — | — | Depends on whether the break is deflationary or inflationary. |
| GLD | Conditional — see below | — | — | Depends on whether the break triggers a flight-to-safety or a liquidity liquidation. |
| VIX | Spikes | 35 to 80+ | First 2-4 weeks of acute phase | Mechanical: gamma hedging by market makers amplifies moves. Magnitude depends on starting VIX level (lower start = bigger spike). |

### Conditional (interaction with other theories)

| Type | Condition | Prediction | Specificity Gain |
|------|-----------|-----------|-----------------|
| **Mechanism interaction** | If `debt_cycle_short` is also Active (late cycle) | Break is more likely to be **deflationary**. TLT rallies +15-25%. Fed cuts aggressively. Recovery faster because monetary policy still has room. | Narrows the break-type prediction from "could be inflationary or deflationary" to "likely deflationary." Adds TLT as a high-conviction trade. |
| **Mechanism interaction** | If `fiscal_dominance_liquidity` is also Active | Break may be **shallower and faster** because fiscal spending provides a floor under aggregate demand. BUT: recovery is inflationary, not deflationary. TLT does NOT rally. GLD outperforms. | Narrows the magnitude prediction downward (-20% to -30% instead of -30% to -40%) and changes the optimal recovery positioning (hard assets, not bonds). |
| **Mechanism interaction** | If `fiscal_dominance_arithmetic` is also Active | Break is inflationary — the fragility resolves into a **stagflationary episode** where equities decline, bonds decline, and only hard assets protect purchasing power. Worst-case scenario for traditional portfolios. | Narrows the asset-class prediction: bonds are NOT a hedge. Cash (SHY) and gold (GLD) are the only defensive assets. This is the 1970s-style resolution. |
| **Mechanism interaction** | If `valuation_mean_reversion` is also Active (ERP near zero) | The drawdown magnitude is at the **upper end** of the range (-35% to -50%) because valuations provide no cushion. In 2000 and 2007, the combination of extreme valuations + fragility produced the largest drawdowns. | Narrows the magnitude estimate upward. Also extends the recovery timeline (took 5+ years from 2000 peak to recover). |
| **Asset-expression consequence** | If `capital_flows` is also Active (EM undervalued) | Post-break recovery leadership rotates **internationally**. EM and international equities outperform US in the 2-3 years following a US-centric Minsky event, as capital flows to better-valued markets. | Adds a cross-asset prediction that fragility theory alone doesn't produce. The break in US equities becomes the catalyst for the EM rotation trade. This does not modify the break mechanism — it describes where capital flows AFTER the break resolves. |

---

## downstream_implications

### affects[]

| Target Theory | Relationship | Description |
|--------------|-------------|-------------|
| `valuation_mean_reversion` | **accelerates** | A Minsky moment is one of the catalysts that RESOLVES stretched valuations. Fragility theory doesn't predict when — valuation theory provides the "how far to fall" estimate. They interact: higher starting valuations × higher fragility = larger drawdown. |
| `debt_cycle_short` | **triggers** | A fragility break can be the event that tips the short-term debt cycle from expansion to contraction. Credit tightens not because the central bank wills it but because risk appetite collapses and lenders pull back. The fragility break IS the cycle turn. |
| `debt_cycle_long` | **modifies** | In the late long-term cycle, fragility breaks are resolved differently. Instead of allowing the break to clear (1929-style), authorities intervene (2008-style, 2020-style). This interrupts the Minsky moment but compounds fragility for the next cycle. Each intervention leaves the system MORE fragile. |
| `fiscal_dominance_liquidity` | **contradicts (partially)** | Fiscal liquidity injection can dampen or delay a fragility break by maintaining aggregate demand and asset prices. This creates a tension: fragility theory says the break is coming; fiscal dominance says the government won't allow it. The resolution is usually that fiscal dominance extends the building phase but makes the eventual break larger. |
| `fiscal_dominance_arithmetic` | **reinforces** | A fragility break worsens the fiscal arithmetic — tax receipts decline, spending increases (automatic stabilizers + bailouts), deficit widens. The break accelerates the devaluation timeline. |
| `capital_flows` | **triggers** | A US-centric fragility break is the primary catalyst for capital flow rotation toward EM. This is because the US premium (which kept capital in US assets despite higher EM expected returns) evaporates during the break. |
| `monetary_architecture` | **accelerates** | A major financial crisis accelerates monetary system transitions. The 2008 crisis led to massive central bank balance sheet expansion and the beginning of reserve diversification. The next major crisis may accelerate the Treasury-to-gold collateral substitution that monetary architecture theory predicts. |

---

## falsifiers

### Hard Falsifiers

These conditions, if met, indicate that the structural fragility mechanism is NOT building meaningfully or that the theory's core predictions are wrong. Any hypothesis invoking this theory should be disconfirmed if any hard falsifier is triggered.

| # | Condition | Metric | Threshold | Rationale |
|---|-----------|--------|-----------|-----------|
| H1 | Market concentration is declining organically | `top_10_sp500_weight` | Below 25% and falling, without a preceding drawdown | If concentration declines without a break, the passive reflexive loop is weakening. The core mechanism (concentration amplifies fragility) is not operative. Note: concentration declining BECAUSE of a drawdown does not falsify the theory — that IS the theory working. |
| H2 | Capex is generating proportional revenue | Web search: AI revenue vs. hyperscaler capex | Revenue-to-capex ratio exceeds 0.5x within 18 months of deployment | If the dominant theme's capex is actually generating revenue at reasonable conversion rates, the capex/revenue mismatch is not present. No cliff risk from disappointed expectations. |
| H3 | VIX sustained above 20 during a rising market | `^VIX` + `SPY` direction | VIX remains 20-30 while SPY makes new highs over 6+ months | This would indicate that the market is pricing risk appropriately — no complacency. The Minsky mechanism requires that measured risk declines during the building phase. If vol stays elevated, participants are not shifting to speculative/Ponzi financing. |
| H4 | Leverage declining despite rising prices | FINRA margin debt | Margin debt declining 15%+ while SPY is flat or rising over 12 months | If participants are reducing leverage voluntarily during an up-market, the progressive risk-taking mechanism is not operative. This has essentially never happened, which is part of why the theory is robust. |

### Soft Falsifiers

These conditions weaken the theory without killing it. They suggest the magnitude may be smaller than predicted, the timeline is uncertain, or the expression may differ from the base case.

| # | Severity | Condition | Metric | Threshold | Implication |
|---|----------|-----------|--------|-----------|-------------|
| S1 | **Major** | Central bank backstop is explicit | Fed policy statements / web search | Fed explicitly commits to intervening if markets decline beyond a threshold (formal or informal "Fed put") | Directly caps the predicted magnitude. Doesn't prevent the break but truncates the downside. Magnitude estimate should be revised downward (-20% to -30% instead of -30% to -40%). However, each backstop compounds fragility for next cycle. |
| S2 | **Medium** | Earnings are actually delivering | Dominant theme (AI) earnings reports | AI-related revenue growing 25%+ YoY in at least 3 sectors beyond hyperscalers in latest quarterly reports | The capex/revenue mismatch narrows, removing the most likely near-term catalyst (earnings disappointment). Fragility is still present from concentration, leverage, and passive amplification — the mechanism is intact, but one major trigger vector is weakened. Other catalysts (credit event, exogenous shock, cycle turn) can still trigger the break. |
| S3 | **Minor** | Market broadening underway | `qqq_iwm_ratio` + equal-weight vs. cap-weight | QQQ/IWM ratio declining for 2+ months AND RSP outperforming SPY trailing 1 month | Concentration is unwinding gradually without a break — changes the expression from non-linear crash to gradual rotation. The fragility mechanism (concentration + passive amplification) still holds, but its resolution may be orderly rather than disorderly. Reduces severity of eventual break but doesn't eliminate it. |
| S4 | **Minor** | Short-term debt cycle is early, not late | `debt_cycle_short` activation status | Short-term cycle in early expansion (ISM rising, unemployment low and stable, credit expanding) | Extends the timeline. The typical catalyst for a Minsky moment — a cyclical downturn that triggers margin calls — is less likely in early cycle. Fragility can still build but the timeline to resolution lengthens. The mechanism is unchanged; only the proximity of the most common catalyst class is reduced. |

---

## metadata

```json
{
  "theory_id": "structural_fragility",
  "version": 1,
  "last_updated": "2026-03-26",
  "update_type": "new",
  "confidence_in_specification": "medium-high",
  "notes": "Activation condition thresholds calibrated against 2000, 2007-08, and 2020 episodes. Phase B thresholds less tested — fewer historical data points for the resolving phase. Capex/revenue mismatch indicator is domain-specific (currently AI) and will need updating if dominant investment theme changes. Phase B qualitative indicators (narrative shift, fund liquidation evidence) separated into adjunct flags — they inform evaluation but do not contribute to mechanical activation scoring.",
  "historical_episodes_referenced": [
    "1999-2000 dot-com (top 10 concentration ~27%, capex/revenue mismatch in fiber/telecom, NASDAQ -78%)",
    "2007-2008 credit crisis (Minsky mechanism in credit, not equity concentration; structural mismatch in mortgage-backed securities)",
    "1972-73 Nifty Fifty (50 stocks at 40-90x earnings, subsequent decade negative real returns)",
    "2020 COVID crash (VIX to 82, fastest 30% drawdown in history, but V-shaped due to fiscal/monetary response — testing H1 of 'backstop caps downside')",
    "2021 Archegos (single-name concentration + leverage, forced liquidation cascade, contained to specific names)"
  ]
}
```

---

## Usage Notes for Generator and Evaluator

### For the Generator

When this theory is Active (Building), generate hypotheses about:
- **What specific fragilities are compounding** (concentration in which names, leverage through which instruments, complacency in which markets)
- **What catalysts could trigger the break** (draw from other Active theories — a debt cycle turn, an earnings miss in AI, a fiscal consolidation shock, a plumbing event)
- **What the mechanism-chain looks like** (combine with other theories to produce specific predictions about break-type: deflationary, inflationary, or stagflationary)
- **What the severity estimate is conditional on a catalyst arriving** (use concentration level, leverage, passive share to calibrate the magnitude range — do NOT make a timing claim; see scope_limits)

When this theory is Active (Resolving), generate hypotheses about:
- **Whether forced selling is exhausted** (check Phase B adjunct flags: fund liquidation evidence, narrative shift, margin debt trajectory, VIX term structure)
- **What is mispriced in the wreckage** (broad-market-level and sector-level)
- **What recovery leadership looks like** (draw from capital_flows theory for international rotation, from valuation_mean_reversion for sector rotation)

### For the Evaluator

Priority checks:
1. Is the theory legitimately in the phase the generator invoked? (Don't let the generator claim "resolving" when VIX is 12.)
2. Are any hard falsifiers triggered? (Pay special attention to H2 — capex/revenue mismatch is the most likely falsifier to trigger in the current AI-dominated market.)
3. If the generator combined this theory with others, did the combination narrow the prediction? (A "fragility + fiscal dominance + late debt cycle" hypothesis should produce a SPECIFIC prediction about break-type and magnitude, not a vague "everything is fragile.")
4. **Is the generator making a timing claim?** This is a hard scope violation. Per the formal scope_limits section, this theory does NOT predict timing. It predicts severity conditional on a catalyst arriving. If the hypothesis says "the break will happen in Q3," reject the timing claim — the theory doesn't support it. The generator may estimate proximity using other theories' cycle positioning, but timing precision is outside this module's scope.
5. For conditional predictions: did the generator correctly distinguish mechanism interactions from asset-expression consequences? A mechanism interaction modifies the break itself (type, magnitude, duration). An asset-expression consequence describes where capital flows after the break without modifying the break mechanism. Conflating the two produces false precision.
