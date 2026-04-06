# ACTIVATION.md — Valuation Mean Reversion & Margin of Safety

*theory_id: `valuation_mean_reversion`*

---

## phases

**Single-phase theory.** When active, equity valuations are stretched beyond levels the arithmetic of future returns can support. There is no "resolving" phase — resolution is diagnosed by the scored indicators falling below activation thresholds (ERP widening, CAPE declining, etc.), at which point the theory becomes Inactive or Adjacent.

---

## transition_logic

Single-phase: Active → Adjacent → Inactive, determined solely by the weighted activation score.

- Weighted score ≥ 0.60 → **Active**
- Weighted score 0.30–0.59 → **Adjacent**
- Weighted score < 0.30 → **Inactive**

No sequencing rules. No mutual exclusivity with other phases.

---

## activation_table

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| Equity risk premium compressed | Computed: `equity_risk_premium` (SPY earnings yield minus 10Y Treasury yield) | `computed-mechanical` · Dependencies: SPY price, SPY trailing earnings, 10Y yield — all API-accessible | Below 1.0% | below | 0.25 | The single most important valuation metric for an allocator. Below 1.0% means equities offer negligible compensation for equity risk vs. risk-free. Below 0% means investors PAY for the privilege of bearing risk. ERP was negative in 1999–2000 (−1.2% at peak) and briefly negative in late 2021. Both preceded major drawdowns. Recalibrate if the structural risk-free rate (r*) changes materially — a world with permanently lower r* might justify a tighter ERP threshold (e.g., 0.5%). |
| Shiller CAPE elevated | Web source: Shiller CAPE ratio (multpl.com, Barclays, or equivalent) | `web-search` · Preferred source: multpl.com/shiller-pe. Updated monthly. | Above 30 | above | 0.20 | CAPE above 30 has occurred only four times: 1929 (32), 1999–2000 (44), 2021 (38), 2024–present (36+). Forward 10-year real returns from CAPE above 30 have averaged approximately 1–3% annualized vs. long-term average of 6–7%. Historical average CAPE is 17. Above 30 is nearly 2x the average. Recalibrate if evidence accumulates that the equilibrium CAPE has shifted (e.g., structural shift in index composition toward higher-margin businesses). |
| Buffett Indicator extreme | Web source: total US market cap / GDP (Wilshire 5000 / GDP) | `web-search` · Preferred source: FRED (Wilshire 5000 index + GDP). Quarterly lag on GDP. | Above 1.5x | above | 0.15 | Market cap / GDP approximates price-to-sales for the entire economy. Above 1.5x implies either permanently elevated margins OR speculative pricing of unrealized growth. Occurred only in 1999–2000 (1.6x), 2021 (2.0x), 2024–present (1.8x+). Recalibrate if GDP measurement changes materially (e.g., major methodology revision) or if market composition diverges sharply from GDP composition (tech revenue increasingly international while GDP is domestic). |
| Short-term cash yield exceeds equity earnings yield | Computed: `cash_exceeds_equity_yield` (fed funds rate minus estimated SPY earnings yield) | `computed-mechanical` · Dependencies: fed funds rate (FRED), equity risk premium (computed), 10Y yield (FRED). cash_exceeds = fed_funds - (equity_risk_premium + treasury_10y) | Above 0 (positive = cash yield exceeds equity earnings yield) | above | 0.15 | Binary threshold: when cash pays more than equities yield, the opportunity cost argument for equities collapses. No margin of safety when the risk-free alternative pays more. Recalibrate: this indicator auto-adjusts with rate changes — no manual recalibration needed. |
| Corporate profit margins at cycle highs | Web source: S&P 500 net profit margin; FRED corporate profits / GDP | `web-search` · Preferred sources: FactSet or S&P Global for margins; FRED series A446RC1Q027SBEA/GDP for profits/GDP | Net margins above 12% OR corporate profits / GDP above 10% | above | 0.10 | Multiples applied to above-average margins produce double overvaluation: high PE on elevated earnings. When margins revert, effective PE on normalized earnings is much higher than reported PE. Historical average net margin ~8–9%; current cycle highs ~12–13%. Recalibrate if evidence supports a permanent structural margin shift (e.g., tech platform economics durably raising the index-level margin floor). |
| Market breadth narrow | Computed: `qqq_iwm_ratio` + RSP vs. SPY relative performance | `computed-mechanical` · Dependencies: QQQ price, IWM price (for ratio), RSP price, SPY price (for relative performance) — all API-accessible. 2-year lookback for ratio high. | QQQ/IWM ratio above 2-year high AND RSP underperforming SPY by 5%+ over 12 months | above | 0.10 | Narrow breadth means index-level valuation is driven by a small number of stocks. The "market" PE is really the PE of 7–10 mega-cap names. The average stock is cheaper. Matters because: (a) index is more fragile (concentrated names declining has outsized impact), (b) sector rotation may offer value even when aggregate is expensive. Recalibrate if index construction methodology changes or if passive share reaches levels that structurally suppress breadth measures. |
| Insider selling elevated | Web source: SEC insider transactions, insider buy/sell ratio | `web-search` · Preferred source: OpenInsider, SEC EDGAR Form 4 filings. 3-month rolling window. | Insider sell/buy ratio above 5:1 sustained for 3+ months | above | 0.05 | Confirming, not standalone. Insiders sell for many reasons (diversification, taxes, planned programs). But systematic selling at elevated ratios across multiple companies is informative — insiders collectively expressing the view that prices exceed intrinsic value. Recalibrate: threshold is already conservative (5:1 for 3+ months). Adjust only if structural changes to insider reporting (e.g., 10b5-1 plan reforms) change the signal-to-noise ratio. |

---

## context_flags

Supplementary qualitative flags. NOT scored mechanically. Surfaced to the generator as context only.

| Flag | Source | Data Ownership | What to Look For |
|------|--------|----------------|------------------|
| "New paradigm" narratives dominant | Financial media, investment commentary | `qualitative` | Widespread arguments that traditional valuation metrics "don't apply" due to structural changes. Every valuation extreme in history has been accompanied by compelling-sounding arguments for why this time is different. The narratives are always partially true and always insufficient to justify the multiple. |
| Retail participation surging | Brokerage account openings, options volume, meme stock activity | `web-search` | Retail investors entering late in the cycle tend to be the least price-sensitive and the most momentum-driven buyers. Their participation elevates valuations further and creates a pool of weak holders who sell at the first sign of trouble. |
| Berkshire cash position extreme | Berkshire Hathaway cash holdings, latest 10-Q | `web-search` | Buffett's cash position is itself a valuation indicator. When Berkshire cash exceeds $200B and Buffett is a net seller of equities, the most disciplined capital allocator in history is expressing the view that the market is expensive. |

---

## falsifier_severity_assignments

Severity assignments for all falsifiers defined in CORE.md (deep_falsifiers) and for state-level falsifiers below.

### Theory-level falsifiers (from CORE.md)

| Falsifier | Severity | Rationale |
|-----------|----------|-----------|
| H1 — Forward 10-year returns from CAPE 30+ exceed 7% real | **theory-killing** | Not a discount — the theory is wrong. Binary: if this occurs, the core mechanism has failed. Cannot be observed in real-time (requires 10-year lookback). |
| H2 — ERP below zero for 10+ years without >20% drawdown | **theory-killing** | Not a discount — the ERP framework is not the correct pricing model. Cannot be observed in real-time (requires 10-year lookback). |
| H3 — Margins do not revert through a full recession | **theory-killing** | Not a discount — the margin mean-reversion assumption is wrong. Observable within a business cycle (requires recession + margin data). |

### State-level falsifier severity

See state_falsifiers table below for severity assignments on S1–S5.

---

## state_falsifiers

Conditions that would challenge the activation determination or force reassessment of the active state. These test whether the ACTIVATION STATE is correct, not whether the THEORY is correct.

| # | Condition | Metric | Data Ownership | Threshold | Severity | Implication |
|---|-----------|--------|----------------|-----------|----------|-------------|
| S1 | Rates decline substantially, improving ERP from denominator | 10Y Treasury yield | `mechanical` | 10Y yield falls below 3.0% without equity price decline | **major** (0.45) | ERP improves because the risk-free comparator declined, not because equities got cheaper. Removes the primary catalyst — cash yield exceeding equity yield — that drives capital reallocation away from equities. Theory's magnitude prediction remains but the trigger mechanism is impaired. |
| S2 | Earnings growth exceeds 15% annualized for 3+ years | S&P 500 forward operating earnings trajectory | `web-search` · Preferred source: FactSet or S&P Global earnings estimates | Forward operating earnings grow 15%+ per year for 3 consecutive years | **major** (0.45) | Earnings growing into the multiple. At 15% growth for 3 years, earnings increase ~52%. CAPE normalizes without price decline. Directly caps predicted drawdown magnitude — correction from CAPE 24 is -29% to reach CAPE 17, vs. -53% from CAPE 36. |
| S3 | Financial repression — cash is a losing proposition in real terms | Fed funds rate vs. CPI YoY | `computed-mechanical` · Dependencies: fed funds rate (API), CPI YoY (API) | Real short-term rate (fed funds minus CPI) below −2% for 12+ months | **medium** (0.25) | "Hold cash and wait" destroys purchasing power. Does not make equities cheap — makes everything expensive in real terms. Practical expression shifts from "hold cash" to "hold the least expensive real asset." Mechanism intact but primary trade expression impaired. |
| S4 | Market broadening reduces concentration-driven overvaluation | QQQ/IWM ratio + RSP vs. SPY relative performance | `computed-mechanical` · Dependencies: QQQ, IWM, RSP, SPY prices (all API) | QQQ/IWM ratio declining for 12+ months AND RSP outperforming SPY by 5%+ | **minor** (0.10) | Index-level overvaluation was concentrated, not broad. Equal-weighted PE (less extreme) becomes more representative. Reduces index-level drawdown prediction without changing the mechanism. Sector rotation within equities may be more appropriate than blanket underweight. |
| S5 | International valuations converge upward, not US down | EFA, VGK P/E ratios | `web-search` · Preferred source: MSCI index factsheets, Yardeni Research | EAFE P/E rises above 18x while US stays at 22x+ | **minor** (0.10) | US premium narrows because international gets more expensive, not because US gets cheaper. Absolute return concern persists for both markets. Changes trade expression (less relative value in international rotation) without affecting the absolute forward-return prediction. |

---
