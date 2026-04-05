# TACTICAL.md — Fiscal Dominance: Net Liquidity Transmission

*Theory Package: `fiscal_dominance_liquidity`*
*Last updated: April 2026*

---

## directional_predictions

Core directional predictions when the theory is Active. Each traces to a specific step in the causal mechanism defined in CORE.md.

| Asset | Direction | Magnitude Range | Timeframe | Mechanism (CORE.md Reference) |
|-------|-----------|----------------|-----------|-------------------------------|
| SPY | Rally, but lag hard assets in real terms | +5% to +15% per year nominal | Rolling 12 months | Step 7: net liquidity expansion supports all asset prices via the reserve/credit channel. Equities benefit but face two headwinds: high rates compress multiples and inflation erodes real returns. Nominal positive, real returns mediocre. |
| GLD | Outperform | +10% to +25% per year | Rolling 12 months | Steps 7–8: gold benefits from both the liquidity channel (more reserves chasing finite gold supply) and the debasement channel (markets pricing eventual dollar value erosion). Double tailwind. Central bank buying provides structural floor. This is the canonical hard-asset expression. |
| TLT | Underperform in real terms | −5% to −15% total return (nominal) OR flat nominal but negative real | Rolling 12 months | Step 2 + Step 8: nominal bonds are the victim of fiscal dominance. Higher deficits mean more issuance (supply pressure on the long end). Inflation from fiscal spending erodes coupon value. Rising term premium is the market pricing this in. |
| TIP | Outperform nominal bonds | TIPS outperform TLT by +5% to +15% | Rolling 12 months | Step 8: TIPS protect against the inflation that fiscal dominance generates. The breakeven spread (nominal minus TIPS yield) should widen as the market prices higher sustained inflation from fiscal spending. |
| SHY | Positive carry but losing to hard assets | +4% to +5.5% total return | Rolling 12 months | Step 8: short-duration cash earns high yield because the Fed rate is elevated by the fiscal inflation dynamic. Cash is a fine holding relative to TLT. But cash loses to gold, commodities, and equities in nominal terms because net liquidity is expanding. Cash wins only during brief liquidity contractions. |
| DBC | Outperform bonds | +5% to +15% per year | Rolling 12 months | Step 7: commodities benefit from the same liquidity + debasement dynamic as gold, with additional demand-side support from fiscal spending (infrastructure, defense, energy subsidies). Less pure than gold but broader exposure. |

---

## etf_mappings

| Expression | Primary ETF | Alternatives | Notes |
|------------|-------------|--------------|-------|
| Net liquidity up → equities up | SPY | QQQ, IWM | SPY is the broadest expression. QQQ adds concentration risk. IWM adds small-cap beta. |
| Hard-asset outperformance (gold) | GLD | IAU, SGOL | GLD is the canonical expression. Physically backed. Most liquid. |
| Hard-asset outperformance (commodities) | DBC | GSG, PDBC | DBC is broad commodity basket. PDBC is the K-1-free version. |
| Long-end bond underperformance | TLT (short or underweight) | TMF (inverse position), TBT (inverse ETF) | Short TLT or underweight relative to benchmark. TMF/TBT are leveraged inverse — higher risk. |
| Inflation protection | TIP | VTIP (short-duration TIPS) | TIP for full-duration TIPS. VTIP for those wanting inflation protection without long-duration interest rate risk. |
| Cash / short duration | SHY | BIL, SGOV | SHY is 1–3 year Treasury. BIL and SGOV are T-bill proxies — even shorter duration. |

---

## relative_value_expressions

| Trade | Long Leg | Short Leg | Mechanism | When Most Effective |
|-------|----------|-----------|-----------|---------------------|
| Hard vs. nominal | GLD | TLT | Hard assets benefit from debasement; nominal bonds are victimized by supply and inflation. This is the cleanest single expression of fiscal dominance. | When the theory is Active and SF3 (dollar strengthening) is NOT triggered. Dollar weakness amplifies this trade. |
| TIPS vs. nominals | TIP | TLT | Breakeven widening trade. Rising inflation expectations from fiscal spending benefit inflation-linked bonds at the expense of nominal bonds. | When the theory is Active and inflation expectations are rising (breakeven widening). |
| Equities vs. bonds | SPY | TLT | In fiscal dominance, equities get the liquidity bid while bonds get the supply headwind. Equities win on both legs. | When the theory is Active and SF2 (decorrelation) is NOT triggered. |

---

## current_theme_specifics

*Explicitly ephemeral. This section captures implementation details tied to the current macro moment. CORE.md remains valid if this section is emptied.*

**RRP buffer exhaustion (2024–2026 episode):** The RRP facility drained from a peak of ~$2.5T toward zero. This was a one-time tailwind — reserves re-entering circulation from money market fund reallocation. Once fully drained, this component of net liquidity expansion is permanently removed. The theory's mechanism persists, but the RRP amplifier is spent.

**Interest expense acceleration (2024–2026 episode):** Federal interest expense exceeding $1T annually, driven by higher rates applied to the existing debt stock as maturing low-coupon debt is refinanced at current rates. This is currently the fastest-growing component of the deficit and the most direct embodiment of the paradoxical-stimulus loop (CORE.md step 8).

**Contested expression — Bitcoin (IBIT):** Bitcoin as a fiscal dominance proxy — outside government debasement ability, finite supply, increasingly held by institutions. Higher beta to net liquidity than gold. This expression is contested: it requires continued institutional adoption narrative and does not have the same mechanistic link to fiscal dominance as gold. It has not been tested through a full fiscal dominance cycle and its correlation to net liquidity may be coincidental rather than causal. If used, treat as a satellite position, not a core expression.

---

## sector_depth

Not applicable as a standalone section. Fiscal dominance is a cross-asset macro theory operating at the asset-class level (equities vs. bonds vs. hard assets vs. cash), not at the sector level. Sector implications emerge through interaction with other theories (e.g., `valuation_mean_reversion` for sector rotation within equities, `structural_fragility` for sector-level concentration risk).

---

## regional_sequencing

Not directly applicable as a standalone prediction. Regional implications (particularly EM outperformance) are interaction-dependent, driven by the dollar-direction channel. See INTERACTION_MATRIX.md for the `fiscal_dominance_liquidity` × `capital_flows` interaction.

Within the US-centric scope of this theory: no regional sequencing. The net liquidity mechanism applies uniformly to US-listed assets.

---

## expression_monitors

Short-horizon operational checks on whether the trade is working. These are NOT theory falsifiers — they monitor implementation, not mechanism.

| Monitor | Metric | Check Frequency | What to Watch For |
|---------|--------|-----------------|-------------------|
| Net liquidity direction | `net_liquidity_30d_change` | Weekly | Is net liquidity still expanding? If it reverses for 2+ weeks, directional predictions are temporarily suspended until the trend re-establishes. |
| SPY–net liquidity tracking | SPY 20-day return vs. net liquidity 20-day change | Weekly | Are equities tracking liquidity? Short-term divergences (1–2 weeks) are noise. Persistent divergence (4+ weeks) warrants checking state falsifier SF2. |
| GLD–TLT spread direction | GLD 30-day return minus TLT 30-day return | Weekly | Is the hard-vs-nominal trade working? If TLT is outperforming GLD for 4+ weeks while the theory is Active, check for flight-to-quality override or risk-off event. |
| TGA trajectory | `liquidity.tga` level and 30-day change | Weekly | Is TGA building (draining liquidity) or spending (injecting liquidity)? Large TGA builds ($100B+ over 30 days) can temporarily pause the directional predictions. Tax deadlines (April, June, September, December) cause predictable seasonal TGA spikes. |
| Breakeven direction | 10Y breakeven inflation rate | Monthly | Are inflation expectations consistent with the debasement channel? If breakevens are declining while the theory is Active, the TIP vs. TLT trade may be impaired. |

---
