# Structural Fragility — TACTICAL.md

*Theory Package: structural_fragility*
*Reorganised: April 2026*
*Layer: Market expression appendix — updated as themes evolve*

---

## directional_predictions

### Phase A: Fragility Building

When Phase A is Active, the following directional predictions apply. All predictions are conditional on a catalyst arriving — this theory does NOT predict timing (see CORE.md `scope_limits`).

| Asset | Ticker(s) | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|-----------|----------------|-----------|-----------|
| US broad equity | SPY | Vulnerable to drawdown | -25% to -40% from peak | 12–24 months from catalyst | Passive outflows + margin calls + systematic deleveraging. Magnitude depends on concentration level at time of break. |
| US large-cap growth | QQQ | Underperforms broad index during break | -30% to -50% from peak | 12–24 months from catalyst | Higher concentration, higher beta, more systematic/momentum exposure. The reflexive loop that drove outperformance drives underperformance in reverse. |
| US small-cap | IWM | Declines with index initially, recovers faster | -20% to -35% initially, then outperforms by 15–25% | Decline: first 3–6 months. Outperformance: following 12 months. | Less owned by passive (lower index weight), less exposed to forced systematic selling. Recovery leadership historically rotates to small-cap. |
| Short-duration Treasury | SHY | Outperforms during break | +2% to +5% total return | During break period | Cash is the anti-fragility asset. Return is certain; everything else is repricing. |
| Long-duration Treasury | TLT | Conditional on break type | See interaction matrix | See interaction matrix | Depends on whether the break is deflationary (TLT rallies) or inflationary (TLT declines). Break type determined by interaction with fiscal dominance and debt cycle theories. |
| Gold | GLD | Conditional on break type | See interaction matrix | See interaction matrix | Depends on whether the break triggers flight-to-safety (GLD rallies) or liquidity liquidation (GLD sells off initially, then rallies). |
| Implied vol | VIX / VXX | Spikes | 35 to 80+ | First 2–4 weeks of acute phase | Mechanical: gamma hedging by market makers amplifies moves. Magnitude depends on starting VIX level — lower start = bigger spike. |

### Phase B: Fragility Resolving

When Phase B is Active, directional predictions shift to opportunistic positioning. See CORE.md Phase B mechanism for the logic.

| Asset | Ticker(s) | Direction | Mechanism |
|-------|-----------|-----------|-----------|
| US broad equity | SPY | Recovery | Forced selling exhausted; prices below intrinsic value for a meaningful subset. |
| US small-cap | IWM | Outperforms broad index | Less damaged by the break (lower passive exposure); benefits disproportionately from recovery broadening. |
| International equity | EFA, EEM | Potential outperformance | If break was US-centric, capital rotates to better-valued markets. See INTERACTION_MATRIX.md for capital_flows interaction. |

---

## etf_mappings

| Expression | Primary ETF | Alternatives | Notes |
|------------|------------|-------------|-------|
| US broad equity exposure | SPY | VOO, IVV | Proxy for the concentrated index. During Phase A, this IS the fragility. |
| US large-cap growth | QQQ | — | Highest concentration exposure. Maximum Phase A fragility. |
| US small-cap | IWM | VTWO | Recovery leadership proxy. Phase B outperformance vehicle. |
| Short-duration Treasury | SHY | BIL, SGOV | Anti-fragility. Cash-equivalent during break. |
| Long-duration Treasury | TLT | VGLT | Conditional — only defensive if break is deflationary. |
| Gold | GLD | IAU, GLDM | Conditional — flight-to-safety bid during break, but may sell off in acute liquidity stress before rallying. |
| Implied vol | VIX (index) | VXX, UVXY (short-term products) | Phase A monitoring + Phase B confirmation. VIX products have negative carry — not a hold, a signal. |
| Equal-weight S&P 500 | RSP | — | S3 soft falsifier monitor. RSP outperforming SPY signals broadening. |

---

## sector_depth

Structural fragility operates primarily at the index level (concentration + passive amplification), not sector level. However, the dominant investment theme that drives the capex/revenue mismatch connects to specific sectors (see `current_theme_specifics` below).

During Phase B, sector rotation is relevant:

| Sector | Phase B Behavior | Mechanism |
|--------|-----------------|-----------|
| Financials (XLF, KBE) | Hardest hit during credit-driven breaks; first to recover if crisis is contained | Leverage on leverage — banks are leveraged to borrowers who are leveraged. But if credit losses prove temporary, P/TBV compression creates deep value. |
| Energy (XLE) | Less correlated to passive concentration dynamics | Tangible assets, essential product. If break is inflationary, energy is defensive. If deflationary, energy declines but from lower starting valuations. |
| Technology | Most exposed during Phase A break | Highest concentration, highest passive weight, most exposed to capex/revenue mismatch. During Phase B, select tech names with real cash flows recover fastest. |

---

## regional_sequencing

This theory is primarily US-centric (US passive share, US index concentration, US margin debt). International implications are derivative:

1. **During Phase A break:** US-centric forced selling spills over to global markets via correlation, systematic strategy deleveraging, and dollar liquidity withdrawal. International markets decline in sympathy but typically less than US (lower concentration, lower passive share).
2. **During Phase B recovery:** If the break resolves the US premium (see INTERACTION_MATRIX.md, capital_flows interaction), recovery leadership may rotate internationally — particularly to EM and international value.

---

## relative_value_expressions

| Expression | Trade Structure | Mechanism | Monitor |
|------------|---------------|-----------|---------|
| Narrow → broad rotation | Long IWM / Short QQQ | Mean reversion in leadership divergence. When QQQ/IWM ratio is at 2-year highs, the ratio reverts during stress or broadening. | QQQ/IWM ratio declining for 3+ months. |
| Equal-weight vs. cap-weight | Long RSP / Short SPY | Concentration premium unwind. RSP outperformance = market broadening, reducing fragility severity. | RSP/SPY ratio sustained above 6-month average. |
| Vol expansion | Long VIX calls (or VIX call spreads) during Phase A | Low implied vol = cheap optionality. The complacency itself is the mispricing. | VIX below 14 with term structure in contango. |

---

## current_theme_specifics

*Explicitly ephemeral. This section captures the dominant investment theme driving the capex/revenue mismatch indicator in ACTIVATION.md. It will need updating when the dominant theme changes. Its presence is NEVER required for CORE.md to remain valid.*

### Current Theme: AI Infrastructure (as of April 2026)

**The mismatch:** Hyperscaler capex committed ($200B+/year aggregate across major cloud providers) vs. identifiable AI revenue outside of hyperscalers themselves. The companies spending the capital are generating some AI revenue (cloud services, advertising optimization), but the ecosystem beyond the hyperscalers — enterprise software companies, startups, application-layer businesses — has yet to demonstrate revenue commensurate with the infrastructure investment.

**Capex/revenue test (current application):** Revenue-to-capex ratio for hyperscaler AI spend. Currently well below 0.5x when measured across the full AI value chain (not just the hyperscalers' own cloud revenue). The 3x+ mismatch threshold in ACTIVATION.md is met.

**Why this is Minsky:** The hyperscaler capex IS revenue for semiconductor companies, data center builders, energy providers, and cooling infrastructure firms. These downstream beneficiaries are priced for continued capex growth. If the capex cycle disappoints — because AI revenue doesn't materialize at scale, because compute costs decline faster than expected, or because one or more hyperscalers blink — the revenue cliff affects the entire supply chain simultaneously.

**AI-specific expression monitor:** Aggregate AI-related revenue across the investable universe (not just hyperscalers). If growing 40%+ YoY broadly, S2 soft falsifier triggers. If revenue-to-capex ratio exceeds 0.5x within 18 months, H2 hard falsifier triggers (general form — see CORE.md).

**When this section becomes stale:** If the dominant capex/investment theme shifts away from AI (to fusion, to quantum, to reshoring, to defense, or to something not yet visible), this section should be rewritten for the new theme. The CORE.md mechanism and ACTIVATION.md indicator remain unchanged — only the theme-specific content here updates.

---

## expression_monitors

These are short-horizon operational checks on trade expressions. They are NOT theory falsifiers — they monitor whether the trade is working, not whether the theory is true.

| Monitor | Metric | What It Checks | Action if Triggered |
|---------|--------|---------------|-------------------|
| AI revenue trajectory | Quarterly earnings: aggregate AI-related revenue across investable universe | Whether S2 state falsifier is approaching | If AI revenue growing 40%+ YoY broadly, flag S2. Narrow the capex/revenue mismatch indicator contribution. |
| AI capex commitment changes | Hyperscaler capex guidance on quarterly calls | Whether capex cycle is accelerating, steady, or decelerating | Deceleration = potential mismatch catalyst approaching. Acceleration = extends timeline but compounds eventual cliff. |
| QQQ/IWM ratio trajectory | `QQQ / IWM` price ratio, 3-month trend | Whether narrow leadership is intensifying or reversing | Intensifying = Phase A fragility compounding. Reversing for 6+ months = S3 soft falsifier may trigger. |
| Margin debt trajectory | FINRA monthly margin statistics | Whether leverage is building further or unwinding | Building = Phase A indicator reinforced. Unwinding from highs without market decline = unusual, flag for H4 review. |
| VIX regime | `^VIX` level and 20-day realized vol | Whether complacency is deepening or dissipating | VIX sustained above 20 with market rising for 6+ months = flag for H3 review. |

---
