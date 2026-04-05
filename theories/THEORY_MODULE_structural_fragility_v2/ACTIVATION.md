# Structural Fragility — ACTIVATION.md

*Theory Package: structural_fragility*
*Reorganised: April 2026*
*Layer: State detection spec — audited by data pipeline tests*

---

## phases

- **Phase A: Fragility Building** — The mechanism is accumulating. Stability is breeding instability. Markets appear calm but structural risk is compounding. Investment implication: defensive.
- **Phase B: Fragility Resolving** — The mechanism has triggered. Forced selling is active or recently exhausted. Prices are disconnected from fundamentals due to mechanical selling. Investment implication: opportunistic.

---

## transition_logic

1. Phases A and B are **mutually exclusive**. If Phase B is Active, Phase A is by definition Inactive — the fragility has resolved into the break.
2. **Check Phase B first.** If Phase B scores Active, skip Phase A scoring entirely.
3. If Phase B is Inactive, score Phase A.
4. If both score Inactive, theory is Inactive.
5. **Transition A → B:** Occurs when a catalyst triggers non-linear decline. Phase B indicators (implied vol spike, spread widening, drawdown) will mechanically activate — no manual override needed.
6. **Transition B → A:** Occurs when forced selling exhausts, prices stabilize, and fragility begins rebuilding. Phase B indicators deactivate; over subsequent quarters, Phase A indicators begin reactivating as a new building phase starts.

---

## activation_table

### Phase A: Fragility Building

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| Implied vol level | `^VIX` | `mechanical` | Below 14 | below | 0.10 | Extreme complacency. Sub-14 has preceded every major drawdown since 2000 by 6–18 months. Recalibrate if vol regime structurally shifts (e.g., 0DTE options permanently alter VIX dynamics). |
| Implied-realized vol gap | computed: `VIX - 20d_realized_vol(SPY)` | `computed-mechanical` — inputs: `^VIX`, `SPY` 20-day realized vol | Above 5 points | above | 0.10 | Market pricing more implied vol than is materializing. Vol sellers harvesting premium, compressing realized, creating reflexive calm. Threshold calibrated to 2017–2019 and 2023–2024 calm periods. |
| High-yield spread | `credit.hy_spread` | `mechanical` | Below 300bp | below | 0.15 | Near-zero default risk pricing. Sub-300bp has preceded every widening event by 6–24 months. The tighter the spread, the more violent the reversal. |
| Top-10 index concentration | computed: `top_10_sp500_weight` | `computed-mechanical` — inputs: individual S&P 500 constituent weights from index provider | Above 30% | above | 0.20 | Passive amplification loop is active. Index beta is becoming the beta of a handful of names. Single most important fragility indicator — determines severity of eventual unwind. 30% threshold set above 2000 peak (~27%) to account for structurally higher passive share today. |
| Capex/revenue mismatch | dominant investment theme capex vs. identifiable revenue | `web-search` — preferred source: company earnings reports, industry analyst aggregations. Theme identification defined in TACTICAL.md `current_theme_specifics`. | Dominant theme capex exceeding identifiable revenue by 3x+ | above | 0.15 | Tests whether speculative/Ponzi financing is present in the dominant investment theme. When the gap between spending and revenue generation exceeds 3x, cliff risk is present: capex is someone's revenue today, but the revenue justifying it is years away. |
| Margin debt | FINRA margin statistics | `web-search` — preferred source: FINRA monthly margin statistics report | At or within 10% of record highs | above | 0.10 | Leverage amplifies both directions. Record margin debt does not cause the break but determines its severity via forced liquidation cascade. |
| Large-cap/small-cap divergence | computed: `QQQ / IWM` price ratio | `computed-mechanical` — inputs: QQQ price, IWM price | Above 2-year high | above | 0.10 | Proxy for narrow leadership. When large-cap growth dominance over small-cap value is at extremes, market is pricing perfection in narrow set and distress elsewhere. Mean reversion historically coincided with broader stress. |
| Passive fund share | ICI or Morningstar passive share data | `web-search` — preferred source: ICI quarterly factsheet or Morningstar passive share report. Structural parameter, quarterly refresh sufficient. | Above 50% of US equity AUM | above | 0.10 | Once passive exceeds 50%, the reflexive loop dominates marginal price-setting. Does not trigger the break but determines its mechanism: mechanical, correlated, non-linear. Slow-moving — recalibrate only if passive share structurally reverses. |

**Total weight: 1.00**

### Phase B: Fragility Resolving

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| Implied vol level | `^VIX` | `mechanical` | Above 35 | above | 0.20 | Panic-level implied vol. Above 35 has coincided with forced-selling events where prices overshoot fundamentals to the downside. Calibrated to 2008 (80+), 2020 (82), 2011 (48). Recalibrate if 0DTE options structurally change VIX behavior. |
| High-yield spread | `credit.hy_spread` | `mechanical` | Above 600bp | above | 0.20 | Credit market pricing meaningful default risk. Forced selling by constrained institutions (insurance, pensions with rating mandates) creates mechanical selling disconnected from fundamental analysis. |
| Drawdown depth | computed: `SPY_price / SPY_52w_high - 1` | `computed-mechanical` — inputs: SPY current price, SPY 52-week high | Below -20% | below | 0.20 | Bear market territory. -10% triggers retail margin calls, -20% triggers institutional risk limits, -30% triggers systematic deleveraging. Depth determines which forced-selling mechanisms have activated. |
| Valuation compression | Shiller CAPE ratio | `web-search` — preferred source: multpl.com or Robert Shiller's data page | Below 20 | below | 0.15 | Valuations compressed to levels historically offering strong forward returns. Below 20 CAPE, the arithmetic favors equity ownership regardless of narrative. Confirms opportunity, not the break itself. Calibrated to 2009 (13), 2011 (20), 2020 (24 briefly). |

**Total weight: 0.75** (Phase B uses 4 indicators; maximum achievable score is 0.75, so thresholds are set relative to this maximum.)

---

## activation_thresholds

### Phase A: Fragility Building

| Score Range | Status |
|-------------|--------|
| ≥ 0.60 | **Active (Building)** |
| 0.30 – 0.59 | **Adjacent (Building)** |
| < 0.30 | **Inactive** |

### Phase B: Fragility Resolving

| Score Range | Status |
|-------------|--------|
| ≥ 0.60 | **Active (Resolving)** |
| 0.30 – 0.59 | **Adjacent (Resolving)** |
| < 0.30 | **Inactive** |

---

## context_flags

These flags provide qualitative confirmation for Phase B assessment. They inform the generator and evaluator but do NOT contribute to mechanical activation scoring. This separation prevents narrative-driven qualitative judgments from contaminating the quantitative activation threshold.

| Flag | Source | Data Ownership | What to Look For | Usage |
|------|--------|----------------|-------------------|-------|
| Narrative shift | Financial media sentiment | `qualitative` | "Buy the dip" replaced by capitulation sentiment. When the dominant narrative shifts from opportunity to permanent impairment, forced sellers are usually near exhaustion. | Confirms Phase B maturity (forced selling near exhaustion). If Phase B mechanically Active AND flag present → conviction in post-break positioning increases. If Phase B Active but flag absent → forced selling may still be accelerating — caution on timing of opportunistic entry. |
| Fund liquidation evidence | Financial news, SEC filings | `web-search` | Visible fund closures, redemption gates, or forced position unwinds. Historical examples: Archegos (2021), LTCM (1998), quant deleveraging (August 2007). | Direct evidence that forced-selling mechanism is active or recently exhausted. Presence during Phase B confirms Minsky mechanism operative (not just sentiment-driven selloff). Absence during drawdown suggests orderly decline rather than forced selling — weakens Phase B thesis. |

---

## falsifier_severity_assignments

### Theory-level falsifiers (from CORE.md `deep_falsifiers`)

| Falsifier | Severity | Scoring Effect |
|-----------|----------|---------------|
| H1: Concentration declining organically | **Hard** | If triggered → override activation to Inactive. Theory mechanism not operative. |
| H2: Dominant capex theme generating proportional revenue | **Hard** | If triggered → override activation to Inactive for capex/revenue channel. Note: other fragility channels (concentration, leverage, passive) remain independently testable. Partial falsification — reassess overall activation score without capex/revenue indicator contribution. |
| H3: Implied vol sustained above 20 in rising market (6+ months) | **Hard** | If triggered → override activation to Inactive. Minsky complacency mechanism not operative. |
| H4: Leverage declining despite rising prices | **Hard** | If triggered → override activation to Inactive. Progressive risk-taking mechanism not operative. |

### State-level falsifiers

These weaken the activation state's predictions without killing the theory. Severity discounts applied mechanically per the canonical schedule (minor = 0.10, medium = 0.25, major = 0.45).

| # | Severity | Condition | Metric Source | Data Ownership | Threshold | Implication |
|---|----------|-----------|---------------|----------------|-----------|-------------|
| S1 | **Major** (0.45) | Central bank backstop is explicit | Fed policy statements, FOMC minutes | `web-search` | Fed explicitly commits to intervening if markets decline beyond a threshold (formal or informal policy put) | Directly caps predicted magnitude. Does not prevent the break but truncates the downside. Each backstop compounds fragility for next cycle. |
| S2 | **Medium** (0.25) | Dominant investment theme revenue growth strong | Earnings reports for dominant theme companies | `web-search` — theme identification in TACTICAL.md `current_theme_specifics` | Aggregate theme-related revenue growing 40%+ YoY across investable universe (not just the capex spenders themselves) | Narrows capex/revenue mismatch, removing the most likely near-term catalyst (earnings disappointment). Fragility from concentration, leverage, and passive amplification intact — mechanism holds, but one major trigger vector weakened. |
| S3 | **Minor** (0.10) | Market broadening underway | Large-cap/small-cap ratio + equal-weight vs. cap-weight performance | `computed-mechanical` — inputs: QQQ, IWM, RSP, SPY prices | Large-cap/small-cap ratio declining for 6+ months AND equal-weight index outperforming cap-weight index | Concentration unwinding gradually without a break. Changes expression from non-linear crash to gradual rotation. Reduces severity of eventual break but does not eliminate fragility from other channels. |

---
