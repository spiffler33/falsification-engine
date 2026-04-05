# debt_cycle_short — CORE.md

*Invariant Theory*
*stability_class: cyclical*
*Last updated: April 2026*

---

## theory_id

`debt_cycle_short`

---

## core_claim

The economy oscillates on a 5–8 year credit cycle. Credit creation amplifies activity through a positive feedback loop (borrowing → spending → income → more borrowing); the cycle terminates when debt service costs outgrow income, triggering a negative feedback loop (tightening → reduced spending → reduced income → defaults → more tightening). The central bank's interest rate policy is the primary control mechanism. The cycle operates on two axes — growth (expanding/contracting) and inflation (rising/falling) — producing four distinct regimes (Goldilocks, Reflation, Stagflation, Deflation) with different asset-class implications in each.

---

## causal_mechanism

### Phase A: Expansion

1. **Credit conditions are accommodative.** The policy rate is below the economy's nominal growth rate. Banks are lending. Bond markets price low default risk. The cost of capital is below the return on economic activity — borrowing is profitable at the margin.

2. **Credit creation amplifies activity.** Businesses borrow to invest (capital expenditure, hiring, inventory). Consumers borrow to spend (mortgages, auto loans, credit cards). Spending by borrowers becomes income for others. Income growth supports further borrowing. This positive feedback loop IS the expansion.

3. **Employment tightens.** Hiring exceeds separations. Unemployment declines. Wages begin to rise — initially below inflation, then matching, then potentially exceeding, depending on the inflation regime.

4. **Asset prices rise.** Equities benefit from earnings growth (revenue expansion plus margin improvement). Credit benefits from declining default risk (spreads tighten). Real estate benefits from low rates and rising incomes. The wealth effect reinforces spending: rising portfolios make consumers more confident, businesses more willing to invest.

5. **The expansion generates its own termination** through one or more channels:

   (a) INFLATION CHANNEL — tight labor and rising wages push input costs up. Companies pass costs through to prices. The central bank tightens. The cost of credit rises. Credit creation slows.

   (b) CREDIT QUALITY CHANNEL — late in the cycle, lending standards loosen to sustain growth. Lower-quality borrowers access credit. Defaults rise. Banks tighten in response. Credit contraction begins.

   (c) ASSET PRICE CHANNEL — rising asset prices become untethered from cash flows. The equity risk premium compresses. Any catalyst produces a larger correction.

   (d) EXOGENOUS SHOCK — pandemic, war, energy crisis, financial accident. The cycle was going to end anyway; the shock determines when.

6. **Late-cycle characteristics emerge.** The yield curve flattens then inverts. Manufacturing activity plateaus then starts declining. Initial jobless claims stop falling. Bank lending standards begin to tighten. Profit margins peak. These are warning signals, not contraction signals. The expansion can persist 6–24 months after late-cycle signs appear.

### Phase B: Contraction

1. **A trigger arrives.** Rate tightening reaches critical level, a credit event erupts, an external shock hits, or earnings disappoint. The specific trigger is less important than the vulnerability: the system was ready to contract because of the termination channels described above.

2. **Credit creation reverses.** Banks tighten lending. Borrowers reduce demand for credit (investment projects no longer clear the higher hurdle rate, consumers pull back). Net credit growth turns negative.

3. **The positive feedback loop reverses.** Reduced lending → reduced spending → reduced income → reduced ability to service existing debt → rising defaults → banks tighten further. This negative feedback loop IS the contraction.

4. **Employment deteriorates.** Hiring freezes give way to layoffs. Unemployment rises. Consumer confidence collapses. Spending contracts further.

5. **Asset prices decline.** Equities reprice for lower earnings (revenue decline plus margin compression). Credit spreads widen (default risk rising). The wealth effect reverses. Forced selling (margin calls, redemptions, systematic deleveraging) amplifies the decline beyond what fundamentals justify.

6. **The central bank responds.** Rate cuts begin. If insufficient, balance sheet expansion follows. If still insufficient, fiscal-monetary coordination. The speed and magnitude of the response determines the depth and duration of the contraction.

7. **Policy response gains traction.** Lower rates improve credit conditions. Fiscal spending supports demand. Credit creation restarts. The cycle begins again from step 1 of Phase A. Each restart leaves total debt higher than before — this is the ratchet mechanism that connects the short cycle to the long-term debt cycle.

### The Two-Dimensional Regime Claim

The short-term cycle does not oscillate on a single axis. It operates in a two-dimensional space: Growth (expanding/contracting) × Inflation (rising/falling). This creates four regimes:

| Regime | Growth | Inflation | Defining Condition |
|--------|--------|-----------|-------------------|
| **Goldilocks** | Expanding | Falling or stable-low | Expansion with contained inflation |
| **Reflation** | Expanding | Rising | Expansion with rising inflation |
| **Stagflation** | Contracting | Rising or sticky-high | Contraction with elevated inflation |
| **Deflation** | Contracting | Falling | Contraction with falling inflation |

The regime matters more than the phase alone for practical purposes. Two expansions in different inflation regimes have different optimal positioning. Two contractions in different inflation regimes have opposite implications for duration assets.

### Time Horizon

**Full cycle:** 5–8 years peak-to-peak. Post-1980 average is approximately 7 years.

**Expansion phase:** Typically 4–6 years. Can extend to 10+ years in unusual circumstances (productivity booms, fiscal support).

**Contraction phase:** Typically 6–18 months. Rarely exceeds 2 years unless compounded by long-term debt cycle dynamics.

**Lead time of indicators:** Late-cycle warning signs appear 6–24 months before contraction. This is the operationally valuable window.

---

## scope_limits

1. **Does not predict the timing of cycle turns.** The theory identifies late-cycle conditions and elevated recession probability over a 6–18 month window, not the specific month of inflection.

2. **Does not model the fiscal override mechanism.** Fiscal spending can prevent the credit cycle from contracting despite late-cycle indicators firing. That mechanism belongs to `fiscal_dominance_liquidity`. This theory predicts what happens when the credit cycle operates normally; fiscal dominance describes when and how it is overridden.

3. **The inflation axis is imported, not independently modeled.** Quadrant classification depends on inflation data (CPI, Core PCE, breakevens) that this theory observes but does not causally explain. Inflation dynamics are an input, not an output.

4. **Applies primarily to US credit cycles.** Emerging-market credit cycles involve additional mechanisms (currency, capital account, external debt denomination) that this theory does not capture. Those dynamics belong to `capital_flows`.

5. **Magnitude estimates are conditional on starting conditions.** The theory provides ranges, not point estimates. Actual magnitude depends on starting valuations (from `valuation_mean_reversion`), fragility level (from `structural_fragility`), and long-cycle positioning (from `debt_cycle_long`).

---

## key_assumptions

1. **Credit is the primary growth driver.** Economic activity is amplified by borrowing — spending exceeds income through credit creation, and one agent's spending becomes another's income. If the economy structurally shifts to a non-credit-driven growth model, the cycle mechanism weakens.

2. **Central bank interest rate policy is the primary control mechanism.** Rate changes alter the cost of credit, which controls the pace of credit creation. If fiscal policy permanently replaces monetary policy as the primary cycle driver, the rate transmission mechanism is no longer the binding constraint.

3. **Labor market, credit market, and manufacturing indicators are reliable coincident and leading signals.** The indicator set (unemployment, claims, spreads, ISM, SLOOS, yield curve) has accurately tracked every post-war US cycle. If structural economic shifts decouple these indicators from the cycle, the detection mechanism fails.

4. **Expansions generate their own termination.** Through one or more of the four channels (inflation, credit quality, asset price, exogenous shock), every expansion plants the seeds of its own contraction. If a mechanism exists that sustains expansion indefinitely without accumulating the imbalances that produce contraction, the cycle theory is incomplete.

---

## deep_falsifiers

These conditions would kill the theory itself — not a hypothesis derived from it. Severity is NOT assigned here; severity is a scoring parameter in ACTIVATION.md.

| # | Condition | Logic |
|---|-----------|-------|
| H1 | **Expansion persists 24+ months under deeply restrictive monetary policy with no fiscal offset.** The policy rate exceeds nominal GDP growth by 2%+ for 24 months, the fiscal deficit is below $800B annualized, and no recession materializes. | If the economy sustains strong growth with genuinely restrictive monetary policy AND no fiscal offset, the credit cycle mechanism is not operative. Something else is driving growth (productivity boom, structural change, external capital inflows). This has never occurred in post-war US history. |
| H2 | **Credit contraction does not produce economic weakness.** Bank lending standards tighten broadly for 4+ quarters, high-yield spreads exceed 500bp, bank lending declines year-over-year — but unemployment stays below 4.5% and GDP growth remains above 2% for 12+ months. | If credit conditions tighten severely but the economy does not slow, the credit channel is not the primary growth driver. The economy may have structurally shifted away from credit-sensitive sectors. This would fundamentally weaken the debt cycle framework. |
| H3 | **Phase B indicators all triggered but no recession materializes within 18 months.** The contraction activation score reaches Active (≥0.60) and sustains for 18 months without NBER recession or GDP contraction. | If contraction indicators are screaming and no recession arrives within 18 months, either the indicators are miscalibrated or an overriding force is preventing the mechanism from completing. Fiscal dominance is the prime candidate explanation. This falsifier tests the theory, not the indicators — it asks whether the debt cycle mechanism is operative. If fiscal dominance is the explanation, this falsifier triggers for the debt cycle while fiscal dominance theory remains Active. Both conclusions are correct simultaneously. |

---

## revision_triggers

1. **A sustained productivity boom that breaks the link between credit expansion and the cycle.** If growth persists for a full cycle without the characteristic credit-quality deterioration or inflation pressures, the theory's assumption that expansions generate their own termination needs revision.

2. **Permanent structural shift away from credit-sensitive sectors.** If the economy becomes dominated by services, technology, and intellectual property to the degree that bank lending and credit spreads cease to predict the cycle, the indicator framework needs fundamental rethinking — not recalibration, but replacement.

3. **Fiscal policy permanently replaces monetary policy as the primary cycle driver.** If the 2022–2025 non-recession experience (massive rate hikes, no recession due to fiscal override) becomes the new normal rather than an exceptional episode, the theory's core claim about rate policy controlling the cycle needs revision. This is the most likely revision trigger in the current environment.

---

## historical_episodes

These episodes calibrate the theory and illustrate its range of application:

- **2001 recession:** Dot-com bust. Mild contraction. Manufacturing ISM reached 41, unemployment rose from 4.0% to 6.3%. Equity drawdown amplified by starting valuation excess (-49% peak-to-trough over 2.5 years). Duration assets rallied ~20%. Deflation quadrant.

- **2007–2009 Great Recession:** Housing/credit bust. Severe contraction. ISM reached 33, unemployment rose from 4.4% to 10.0%. Credit spreads hit 2000bp. Duration assets rallied ~33%. Deflation quadrant. Required MP2 escalation. The template for credit-quality-channel termination.

- **2020 COVID recession:** Exogenous shock. Ultra-fast contraction (2 months). Unemployment spiked from 3.5% to 14.7%. Fastest drawdown in history (-34% in 23 trading days). Fastest V-shaped recovery due to unprecedented MP3 deployment ($5T+ fiscal plus unlimited QE). The template for exogenous-shock-channel termination.

- **2022–2025 non-recession:** Fed funds rose from 0% to 5.25% in 16 months. Yield curve deeply inverted. ISM below 50 for extended periods. SLOOS showed tightening. No recession materialized. Strongest evidence for fiscal dominance overriding the short-term cycle mechanism. Hard falsifier H3 may be approaching trigger.

- **1973–1974 stagflation recession:** Oil shock plus tight monetary policy. Equities declined ~48%. Duration assets declined ~15%. Gold rallied ~67%. The template for stagflationary contraction where duration assets fail as a hedge.

- **1995 soft landing:** Pre-emptive rate cuts. Unemployment never rose significantly. Expansion extended 6 years. The template for central bank successfully averting the cycle turn.

---
