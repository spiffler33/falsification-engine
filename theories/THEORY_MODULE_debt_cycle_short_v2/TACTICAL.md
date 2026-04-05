# debt_cycle_short — TACTICAL.md

*Market Expression Appendix*
*Last updated: April 2026*

---

## directional_predictions — Phase A: Expansion

Predictions vary by quadrant. The phase alone does not determine positioning — the inflation axis matters as much as the growth axis.

### Goldilocks (Expansion + Falling/Stable Inflation)

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| SPY | Rally | +8% to +20% annualized | During expansion | Earnings growth plus risk appetite. Goldilocks delivers higher multiple expansion than Reflation. |
| QQQ | Outperform SPY | +3% to +8% relative | During Goldilocks | Low/falling rates favor long-duration growth equities. In Reflation, QQQ underperforms as rising rates compress growth multiples. |
| TLT | Flat to modestly declining | -2% to +2% | During Goldilocks | Rates stable or slowly rising. Duration not rewarded. Not punished either. |
| SHY | Underperform equities | +3% to +5% total | During Goldilocks | Cash earns its yield but lags risk assets. Opportunity cost of safety. |
| HYG | Outperform investment grade | +2% to +5% relative to LQD | Early/mid expansion | Spread compression benefits high yield more than investment grade. Diminishes in late cycle as asymmetry shifts to downside. |
| GLD | Underperform equities | Flat to +5% | During Goldilocks | No yield. Struggles when real rates are positive and equities offer strong returns. High opportunity cost. |

### Reflation (Expansion + Rising Inflation)

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| SPY | Rally | +8% to +20% annualized | During expansion | Earnings growth, but higher nominal than real. Compressed multiples offset by higher nominal earnings. |
| QQQ | Underperform SPY | -3% to flat relative | During Reflation | Rising rates compress growth multiples. Value and cyclicals outperform growth. |
| XLE, DBC | Outperform | +10% to +30% annualized | During Reflation | Rising inflation plus strong growth = commodity demand surge. Energy is the purest play. Neutral at best in Goldilocks. |
| TLT | Decline sharply | -5% to -15% | During Reflation | Rising inflation forces rates higher. Duration is toxic. Longer maturity = worse loss. |
| TIP | Outperform TLT | +3% to +10% relative | During Reflation | Breakevens widen as market prices sustained inflation. TIPS benefit, nominals suffer. |
| EEM | Outperform conditionally | +5% to +15% relative to SPY | During Reflation + dollar weakening | EM benefits from commodity demand (Reflation) and capital flows (dollar weakening). In Goldilocks with strong dollar, EM lags. Conditional on capital flow dynamics — see INTERACTION_MATRIX.md for `capital_flows` interaction. |
| GLD | Outperform equities | +10% to +25% | Late Reflation especially | Rising inflation with policy uncertainty. Gold benefits from inflation-hedge demand plus the expectation that the central bank will fall behind the curve. |

---

## directional_predictions — Phase B: Contraction

### Deflation (Contraction + Falling Inflation)

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| SPY | Decline | -20% to -40% peak-to-trough | 6–18 months | Earnings contract, multiples compress, forced selling amplifies. Magnitude depends on starting valuation and fragility level — see INTERACTION_MATRIX.md. |
| TLT | Rally sharply | +15% to +30% | During Deflation contraction | Flight to quality plus rate cut expectations plus deflation pricing. The premier deflation hedge. This is the critical quadrant distinction — TLT is the best asset in Deflation and the worst in Stagflation. |
| HYG | Sharp underperformance | -10% to -25% total return | During contraction | Default risk reprices. Spreads widen 200–500bp from cycle tights. Forced selling by rating-mandated institutions amplifies. Both symptom and accelerant of contraction. |
| IWM | Underperform SPY initially, outperform in recovery | -25% to -45% initially, then +20% to +40% relative in first 12M of recovery | Decline: 6–12 months. Recovery: subsequent 12–18 months | Small caps are more leveraged to domestic economy and credit conditions. Decline more in contraction, recover more aggressively as credit reopens. IWM/SPY relative ratio trough typically coincides with cycle trough. |
| SHY | Outperform risk assets | +3% to +5% total, positive real return | During Deflation | Cash preserves capital. In Deflation, real return is positive (falling prices). |

### Stagflation (Contraction + Rising/Sticky Inflation)

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| SPY | Decline | -20% to -40% peak-to-trough | 6–18 months | Same earnings/multiples mechanism as Deflation. Magnitude similar. |
| TLT | Decline or flat | -5% to +3% | During Stagflation contraction | Inflation prevents full flight-to-quality rally. The central bank is constrained — cannot cut aggressively because inflation is elevated. Bonds offer no hedge. Worst environment for traditional 60/40. |
| GLD | Rally | +15% to +40% | During Stagflation contraction | Only reliable hedge when both equities and duration assets fail. 1973–74 and 1979–80 are the templates. In Deflation, gold is neutral to slightly positive (less compelling than TLT). |
| SHY | Outperform risk assets | +3% to +5% total, but real return uncertain | During Stagflation | Nominal return positive but real return may be negative (inflation erodes purchasing power). Cash is the default haven when quadrant is uncertain. |

---

## etf_mappings

| Expression | Primary Ticker | Alternatives | Notes |
|------------|---------------|-------------|-------|
| US large cap equity | SPY | VOO, IVV | Broad market. Phase A core position. |
| US growth / tech | QQQ | VGT, XLK | Goldilocks outperformer. Reflation underperformer. |
| US small cap | IWM | VB, SCHA | Cycle-leveraged. Recovery leadership. |
| Commodities broad | DBC | GSG, PDBC | Reflation play. |
| Energy | XLE | VDE, IYE | Purest Reflation expression. |
| Long-duration Treasury | TLT | VGLT, EDV | Deflation hedge. Stagflation liability. |
| TIPS | TIP | VTIP, STIP | Reflation/inflation protection. |
| Short-duration Treasury | SHY | BIL, SGOV | Default haven. Quadrant ambiguity position. |
| High yield credit | HYG | JNK, USHY | Expansion phase, early/mid cycle only. |
| Investment grade credit | LQD | VCIT, IGIB | Less cycle-sensitive than HYG. |
| Gold | GLD | IAU, GLDM | Stagflation hedge. Reflation secondary. |
| Emerging markets | EEM | VWO, IEMG | Conditional on dollar direction and EM cycle. |

---

## relative_value_expressions

| Trade | Long | Short | Regime | Rationale |
|-------|------|-------|--------|-----------|
| Goldilocks growth tilt | QQQ | XLE | Goldilocks | Low rates favor growth over cyclicals. Reverses in Reflation. |
| Reflation value tilt | XLE, DBC | QQQ | Reflation | Rising inflation favors real assets and commodities over long-duration growth. |
| Deflation duration | TLT | HYG | Deflation contraction | Flight to quality widens spreads and compresses yields. Maximum divergence. |
| Stagflation real assets | GLD | TLT | Stagflation contraction | Gold works when bonds don't. The critical quadrant diagnostic trade. |
| Recovery leadership | IWM | SPY | Early recovery from contraction | Small caps recover faster as credit reopens. Best entered when Phase B indicators are peaking. |
| Cycle maturity monitor | HYG/LQD ratio | — | Late expansion | Ratio declining = high yield underperforming investment grade = credit market pricing rising risk. Deterioration from stable levels is a late-cycle warning. |

---

## sector_depth

Not the primary lens for this theory. Sector implications are largely captured by quadrant determination. However:

- **Financials (XLF):** Most credit-cycle-sensitive sector. Outperform in early/mid expansion (net interest margin expanding, loan growth healthy, credit losses low). Underperform sharply in contraction (credit losses rise, loan growth negative, NIM compressed by rate cuts). The Phase B leading indicator: bank stock underperformance often leads the broad market by 3–6 months.

- **Consumer Discretionary (XLY):** Second-most cycle-sensitive. Directly exposed to consumer credit conditions. Outperform in Goldilocks, underperform in Stagflation (consumers face both rising costs and tightening credit).

- **Utilities/Staples (XLU, XLP):** Defensive sectors that outperform in late expansion and early contraction. Underperform in Reflation (rising rates hurt utility valuations).

---

## regional_sequencing

The US credit cycle typically leads the global cycle by 3–6 months. Sequence:

1. US late-cycle signals appear → 2. US contraction begins → 3. Global trade decelerates → 4. Export-dependent economies (Germany, Korea, Japan) follow → 5. EM economies follow (with additional currency/capital-flow dynamics from `capital_flows`).

Exception: China's credit cycle can diverge from the US cycle because it is state-directed. A Chinese credit impulse can offset US contraction effects on EM.

---

## current_theme_specifics

*Explicitly ephemeral. Current as of April 2026.*

- **2022–2025 fiscal dominance override:** The most important current theme is that fiscal spending has prevented the credit cycle from contracting despite late-cycle indicators firing for an extended period. This modifies the confidence in any contraction hypothesis — see INTERACTION_MATRIX.md for the `fiscal_dominance_liquidity` interaction. The practical implication: traditional late-cycle positioning (short equities, long duration) has been wrong for 2+ years because the fiscal impulse has overridden the monetary restraint.

- **Reflation/Stagflation boundary ambiguity:** The current environment sits at the boundary between Reflation and Stagflation. Growth is positive but decelerating, inflation is sticky but not accelerating. This is the state where quadrant classification is least reliable and where state falsifier S4 may be operative.

---

## expression_monitors

These monitor whether the trade expression is working, not whether the theory is true. They are operational checks, not falsifiers.

| Monitor | Metric | Warning Signal | Action |
|---------|--------|---------------|--------|
| Goldilocks QQQ/XLE ratio | QQQ relative to XLE over 1-month rolling window | If ratio declines >5% while Phase A is Active and CPI is not rising → Goldilocks positioning may be wrong | Re-examine quadrant classification. Possible regime transition to Reflation. |
| Deflation TLT/SPY divergence | TLT vs. SPY correlation during Phase B | If TLT and SPY decline together for 2+ weeks during Phase B → Stagflation, not Deflation | Switch from TLT to GLD as primary hedge. |
| Recovery IWM signal | IWM/SPY relative ratio | If ratio fails to turn higher within 3 months of Phase B peak indicators → recovery leadership may not come from small caps | Re-examine whether credit channel is reopening or whether the recovery is fiscally-driven (which favors large caps). |
| Credit cycle confirmation | HYG total return vs. SHY during Phase A | If HYG underperforms SHY for 3+ months during Phase A Active → credit market is not confirming expansion | Late-cycle warning. Cross-reference with SLOOS data. |

---
