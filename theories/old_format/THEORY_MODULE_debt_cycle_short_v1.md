# Theory Module: Short-Term Debt Cycle

*Version 1.0 — March 2026*
*Status: Prototype — thresholds calibrated against post-war US business cycles (1945-2025), with emphasis on the 2001, 2007-09, 2020, and 2022-present episodes. Pending live testing.*

---

## theory_id

`debt_cycle_short`

---

## activation_conditions

This theory has two distinct activation phases. The system must determine which phase is operative — they have opposite investment implications.

### Phase A: Expansion

Credit is expanding. Economic activity is accelerating or steady. Risk appetite is healthy. The implication is constructive: equities and credit outperform cash and duration. The expansion phase itself has early, mid, and late sub-stages — the four-quadrant regime overlay (see below) provides the finer-grained positioning.

| Indicator | Metric Source | Threshold | Direction | Weight | Rationale |
|-----------|--------------|-----------|-----------|--------|-----------|
| ISM proxy above contraction | `growth.ism_proxy` (MANEMP) | Above 50 | above | 0.15 | The most reliable single coincident indicator of whether the manufacturing economy is expanding. Above 50 = expansion. The level matters less than the direction for cycle positioning, but above 50 is the minimum threshold for confirming expansion phase. ISM has led GDP turning points by 2-4 months in every post-war cycle. |
| Unemployment low or falling | `growth.unemployment` | Below 5.0% OR declining for 3+ months | below or falling | 0.15 | Labor market confirms expansion. Unemployment is a lagging indicator — it confirms the cycle rather than predicting it. Below 5.0% is consistent with an economy operating at or above potential. The direction matters: stable-to-declining unemployment confirms expansion; rising unemployment even from low levels warns of phase transition. |
| Credit spreads tight or tightening | `credit.hy_spread` | Below 450bp AND not widening for 3+ consecutive months | below and stable/tightening | 0.15 | The credit market's verdict on default risk. Below 450bp = market pricing low probability of corporate distress. Tightening spreads = risk appetite improving. HY spreads below 300bp don't mean "more expansion" — they mean fragility is building (that's `structural_fragility`'s domain). This indicator confirms expansion is underway, not that it's healthy. |
| Yield curve not deeply inverted | `rates.curve_2s10s` | Above -0.50% (i.e., inversion shallower than 50bp, or positively sloped) | above | 0.10 | A deeply inverted curve has preceded every post-war recession by 6-18 months. Shallow inversion or positive slope is consistent with expansion continuing. CRITICAL CAVEAT: the curve can be inverted for 12-24 months before contraction begins. Inversion alone does not trigger Phase B — it warns that the expansion is late. |
| Initial claims low | `growth.initial_claims` | Below 250K (4-week average) | below | 0.10 | Real-time labor market health. Below 250K = very few layoffs, consistent with active hiring. Claims are the fastest-updating labor indicator and typically rise 3-6 months before unemployment does. They are the early warning within the expansion phase that contraction may be approaching. |
| Fed funds below nominal GDP growth | `rates.fed_funds` vs. `growth.gdp_latest` (annualized nominal) | Fed funds rate below nominal GDP growth rate | below | 0.10 | Monetary policy is accommodative in REAL economic terms when the policy rate is below the economy's nominal growth rate. Money is cheap relative to the return on economic activity. This is the condition that sustains credit expansion. When Fed funds exceeds nominal GDP, policy is genuinely restrictive and the expansion is under pressure. |
| Net credit growth positive | web search: Fed Senior Loan Officer Survey (SLOOS), bank lending data | Banks reporting steady or loosening lending standards AND loan growth positive YoY | positive | 0.15 | Credit is the fuel of the short-term cycle. When banks are lending and standards are steady or easing, credit creation amplifies economic activity. When banks tighten (SLOOS shows tightening across multiple loan categories for 2+ quarters), the credit engine is sputtering even if other indicators still look healthy. SLOOS tightening has led every recession by 3-6 quarters. |
| Consumer/business confidence | web search: Conference Board Consumer Confidence, CEO Confidence Survey | Consumer confidence above 90 AND not declining for 3+ months | above and stable/rising | 0.10 | Confidence drives spending and investment decisions. Forward-looking: confident consumers borrow and spend, confident businesses invest. Below 80 with declining trajectory has preceded every recession since 1970. Not a hard signal — it confirms the weight of evidence from other indicators. |

**Activation scoring for Phase A:**
- Weighted score ≥ 0.60 → **Active (Expansion)**
- Weighted score 0.30–0.59 → **Adjacent (Expansion)**
- Weighted score < 0.30 → **Inactive**

### Phase B: Contraction

Credit is contracting. Economic activity is decelerating materially or declining. Risk appetite is collapsing. The implication is defensive: duration (if deflationary) or cash/gold (if inflationary) outperforms equities and credit.

| Indicator | Metric Source | Threshold | Direction | Weight | Rationale |
|-----------|--------------|-----------|-----------|--------|-----------|
| ISM proxy below contraction | `growth.ism_proxy` (MANEMP) | Below 48 AND declining for 3+ months | below and falling | 0.15 | Below 50 is contraction. Below 48 and falling is accelerating contraction. The "and falling" qualifier avoids false signals from manufacturing hovering at 49 for months (which may reflect sector rotation rather than broad contraction). Sustained decline below 48 has coincided with every recession since 1960. |
| Unemployment rising | `growth.unemployment` | Rising 0.5%+ from cycle trough (Sahm Rule equivalent) | rising | 0.20 | The Sahm Rule: when the 3-month moving average of unemployment rises 0.50 percentage points above its 12-month low, a recession has begun — without exception in post-war history. This is the single most reliable real-time recession indicator. Weight reflects its near-perfect track record. |
| Credit spreads widening sharply | `credit.hy_spread` | Above 500bp AND widening for 2+ months, OR any move above 600bp | above and widening | 0.15 | Credit market pricing rising default risk. Above 500bp with widening trajectory = credit cycle has turned. A spike above 600bp from any level indicates acute stress — institutional selling (insurance companies, pensions with rating mandates) is forced and mechanical. The speed of the widening matters as much as the level: 100bp in a month is more significant than 200bp over a year. |
| Yield curve re-steepening from deep inversion | `rates.curve_2s10s` | Curve was inverted by 50bp+ AND has re-steepened by 75bp+ from the maximum inversion | rising sharply | 0.15 | The most dangerous signal in fixed income. The curve inverts during late expansion (short rates rise above long rates). It RE-STEEPENS when the market prices in rate cuts — which happens because the market sees recession coming. The re-steepening from inversion, not the inversion itself, is the proximate recession signal. Every post-war recession has been preceded by this sequence: deep inversion → rapid re-steepening → recession within 0-6 months. |
| Initial claims rising | `growth.initial_claims` | 4-week average above 280K AND rising for 8+ weeks | above and rising | 0.10 | Claims are the canary. Sustained rise above 280K with an 8-week trend of increases means layoffs are broadening across industries. The 280K threshold is calibrated to the current labor force size — it represents approximately the level at which new hires can no longer offset layoffs, and aggregate employment begins to decline. |
| Fed funds above nominal GDP growth | `rates.fed_funds` vs. `growth.gdp_latest` | Fed funds exceeds nominal GDP growth by 1%+ for 6+ months | above | 0.10 | Monetary policy is genuinely restrictive — the cost of money exceeds the return on economic activity. Credit contraction follows because borrowing is unprofitable at the margin. The 6-month duration qualifier avoids false signals from brief inversions. Historically, this condition has preceded every recession where monetary policy was the proximate cause (as opposed to exogenous shocks like COVID). |
| SLOOS showing broad tightening | web search: Fed Senior Loan Officer Survey | Net % of banks tightening standards positive across 3+ loan categories for 2+ consecutive quarters | tightening | 0.15 | The credit channel is closing. Banks respond to rising defaults and deteriorating economic outlook by tightening lending standards. This reduces credit availability, which reduces spending, which worsens the outlook, which causes more tightening. The reflexive contraction loop is the core Dalio mechanism. 2+ quarters of broad tightening has preceded every credit-driven recession. |

**Activation scoring for Phase B:**
- Weighted score ≥ 0.60 → **Active (Contraction)**
- Weighted score 0.30–0.59 → **Adjacent (Contraction)**
- Weighted score < 0.30 → **Inactive**

**Important:** Phases A and B are mutually exclusive. If Phase B is Active, Phase A is by definition Inactive (the expansion has ended). The activation layer should check Phase B first — if Active, skip Phase A scoring. If Phase B is Inactive, score Phase A.

**Transitional logic:** The most valuable state for the generator is Adjacent (Contraction) while Expansion is still technically Active by score. This is the LATE CYCLE — the expansion is intact but contraction indicators are emerging. The generator should produce hypotheses about both continuation and turn risk in this state.

---

### Four-Quadrant Regime Overlay

The short-term cycle does not oscillate on a single axis. It operates in a two-dimensional space: Growth (expanding/contracting) × Inflation (rising/falling). This creates four regimes, each with distinct optimal asset allocation. The quadrant is determined by the activation phase PLUS inflation direction.

| Quadrant | Growth | Inflation | Defining Condition | Historical Examples |
|----------|--------|-----------|-------------------|-------------------|
| **Goldilocks** | Expanding | Falling or stable-low | Phase A active + CPI YoY declining or below 2.5% + Core PCE below 2.5% | 2013-2019 (most of it), 1995-1998, mid-2023 to early-2024 |
| **Reflation** | Expanding | Rising | Phase A active + CPI YoY rising above 3% + commodities rising + breakevens widening | 2021 (first half), 2003-2006, late 2024 |
| **Stagflation** | Contracting | Rising | Phase B active (or adjacent) + CPI YoY above 3% AND rising or sticky + growth decelerating | 1973-1974, 1979-1980, possibly 2025-? (contested) |
| **Deflation** | Contracting | Falling | Phase B active + CPI YoY declining rapidly + credit spreads blowing out + commodities declining | 2008-2009, March 2020 (briefly), 1930-1933 |

**Quadrant determination inputs:**
- Growth axis: Phase A vs. Phase B activation status
- Inflation axis: `inflation.cpi_yoy` direction + `inflation.core_pce_yoy` level + `inflation.breakeven_5y` direction

**The quadrant matters more than the phase for trade expression.** Phase A + Goldilocks and Phase A + Reflation are both "expansion," but they have very different optimal portfolios. The generator MUST specify the quadrant, not just the phase.

---

## core_mechanism

### Causal Chain (Phase A: Expansion)

```
1. Credit conditions are accommodative:
   policy rate is below nominal GDP growth,
   banks are lending, SLOOS shows steady/easing standards,
   bond markets are pricing low default risk (tight spreads).
   ↓
2. Credit creation amplifies activity:
   Businesses borrow to invest (capex, hiring, inventory).
   Consumers borrow to spend (mortgages, auto loans, credit cards).
   Spending by borrowers becomes income for others.
   Income growth supports further borrowing.
   POSITIVE FEEDBACK LOOP — this IS the expansion.
   ↓
3. Employment tightens:
   Hiring exceeds separations. Unemployment declines.
   Wages begin to rise (initially below inflation, then matching,
   then potentially exceeding — depending on the quadrant).
   ↓
4. Asset prices rise:
   Equities benefit from earnings growth (revenue + margins expanding).
   Credit benefits from declining default risk (spreads tighten).
   Real estate benefits from low rates + rising incomes.
   The wealth effect reinforces spending: rising portfolios
   make consumers more confident, businesses more willing to invest.
   ↓
5. The expansion generates its own eventual termination through one
   or more of these channels:
   
   (a) INFLATION CHANNEL: tight labor + rising wages → input costs rise →
       companies pass through to prices → CPI rises → central bank tightens →
       cost of credit rises → credit creation slows → spending slows
   
   (b) CREDIT QUALITY CHANNEL: late in the cycle, lending standards loosen
       to sustain growth. Lower-quality borrowers access credit.
       Default rates begin to rise. Banks tighten in response.
       Credit contraction begins — triggering Phase B.
   
   (c) ASSET PRICE CHANNEL: rising asset prices become untethered from
       cash flows. Equity risk premium compresses. Bond risk premium
       compresses. The buildup of overvaluation means any catalyst
       produces a larger correction — connecting to structural_fragility.
   
   (d) EXOGENOUS SHOCK: pandemic, war, energy crisis, financial accident.
       The cycle was going to end anyway, but the shock determines WHEN.
   ↓
6. Late-cycle characteristics emerge:
   Yield curve flattens then inverts (market pricing in eventual rate cuts).
   ISM plateaus then starts declining. Initial claims stop falling.
   SLOOS begins to tighten. Profit margins peak.
   These are WARNING signals, not contraction signals.
   The expansion can persist 6-24 months after late-cycle signs appear.
```

### Causal Chain (Phase B: Contraction)

```
1. A trigger arrives (rate tightening reaching critical level,
   credit event, external shock, earnings disappointment).
   The specific trigger is less important than the vulnerability:
   the system was READY to contract because of the channels
   described in step 5 above.
   ↓
2. Credit creation reverses:
   Banks tighten lending (SLOOS turns sharply negative).
   Borrowers reduce demand for credit (investment projects
   no longer clear the higher hurdle rate, consumers pull back).
   Net credit growth turns negative.
   ↓
3. The positive feedback loop reverses:
   Reduced lending → reduced spending → reduced income for someone else →
   reduced ability to service existing debt → rising defaults →
   banks tighten further → NEGATIVE FEEDBACK LOOP.
   ↓
4. Employment deteriorates:
   Hiring freezes → layoffs begin → unemployment rises.
   The Sahm Rule triggers (0.5% rise from trough).
   Consumer confidence collapses. Spending contracts further.
   ↓
5. Asset prices decline:
   Equities reprice for lower earnings (revenue decline + margin compression).
   Credit spreads widen (default risk rising).
   The wealth effect reverses: falling portfolios reduce confidence and spending.
   Forced selling (margin calls, redemptions, systematic deleveraging) amplifies
   the decline beyond what fundamentals justify — connecting to structural_fragility.
   ↓
6. Central bank responds:
   Rate cuts begin (MP1). If insufficient, balance sheet expansion (MP2).
   If still insufficient, fiscal-monetary coordination (MP3).
   The SPEED and MAGNITUDE of the response determines the depth
   and duration of the contraction — connecting to debt_cycle_long
   (how much room does the central bank have?).
   ↓
7. Policy response eventually gains traction:
   Lower rates improve credit conditions. Fiscal spending supports demand.
   Credit creation restarts. The cycle begins again from step 1 of Phase A.
   Each restart leaves total debt higher than before — this is the ratchet
   mechanism of the long-term debt cycle.
```

### Time Horizon

**Full cycle:** 5-8 years peak-to-peak. The post-1980 average is approximately 7 years (1982 trough → 1990 recession → 2001 recession → 2007 recession → 2020 recession, though 2020 was exogenous).

**Expansion phase:** Typically 4-6 years. Can extend to 10+ years in unusual circumstances (1991-2001 expansion: 10 years; 2009-2020 expansion: 11 years, both extended by productivity gains and/or fiscal support).

**Contraction phase:** Typically 6-18 months. Rarely exceeds 2 years unless debt cycle is long-term (1929-1933: 4 years; 2007-2009: 18 months; 2020: 2 months due to massive policy response).

**Lead time of indicators:** Late-cycle warning signs (curve inversion, ISM plateau, SLOOS tightening) appear 6-24 months before the contraction. This is the tradeable window — the late-expansion period where the generator should be producing hypotheses about turn risk.

---

## predictions_when_active

### Directional (Phase A — Expansion)

Predictions vary by quadrant. The phase alone does not determine positioning — the inflation axis matters as much as the growth axis.

| Asset | Direction | Magnitude Range | Timeframe | Condition (Quadrant) |
|-------|-----------|----------------|-----------|---------------------|
| SPY | Rally | +8% to +20% annualized | During expansion | **Goldilocks or Reflation.** Equities benefit from earnings growth + risk appetite. Goldilocks delivers higher multiple expansion; Reflation delivers higher nominal earnings growth but compressed multiples. |
| QQQ | Outperform SPY | +3% to +8% relative | During Goldilocks | **Goldilocks only.** Low/falling rates favor long-duration growth equities. In Reflation, QQQ underperforms as rising rates compress growth multiples. |
| XLE, DBC | Outperform | +10% to +30% annualized | During Reflation | **Reflation only.** Rising inflation + strong growth = commodity demand surge. Energy is the purest play. In Goldilocks, commodities are neutral at best. |
| TLT | Decline modestly or flat | -2% to +2% | During Goldilocks | **Goldilocks.** Rates stable or slowly rising. Duration not rewarded. Not punished either. |
| TLT | Decline sharply | -5% to -15% | During Reflation | **Reflation.** Rising inflation forces rates higher. Duration is toxic. The longer the maturity, the worse the loss. |
| TIP | Outperform TLT | +3% to +10% relative | During Reflation | **Reflation.** Breakevens widen as market prices in sustained inflation. TIPS benefit, nominals suffer. |
| SHY | Underperform equities | Positive carry but +3-5% total | During Goldilocks/Reflation | **Both.** Cash earns its yield but lags risk assets during expansion. Opportunity cost of safety. |
| HYG | Outperform investment grade | +2% to +5% relative to LQD | During early/mid expansion | **Both quadrants, but diminishes late cycle.** Spread compression benefits HY more than IG. Late cycle: spreads stop compressing, asymmetry shifts to downside. |
| EEM | Outperform conditionally | +5% to +15% relative to SPY | During Reflation + dollar weakening | **Reflation only, and only with dollar cooperation.** EM benefits from commodity demand (Reflation) and capital flows (dollar weakening). In Goldilocks with strong dollar, EM lags — connecting to `capital_flows`. |
| GLD | Underperform equities | Flat to +5% | During Goldilocks | **Goldilocks.** Gold has no yield and struggles when real rates are positive and equities offer strong returns. Opportunity cost is high. |
| GLD | Outperform equities | +10% to +25% | During Reflation, especially late | **Reflation.** Rising inflation with policy uncertainty. Gold benefits from inflation hedge demand + eventual expectation that the central bank will fall behind the curve. |

### Directional (Phase B — Contraction)

| Asset | Direction | Magnitude Range | Timeframe | Condition (Quadrant) |
|-------|-----------|----------------|-----------|---------------------|
| SPY | Decline | -20% to -40% peak-to-trough | 6-18 months | **Both Deflation and Stagflation.** Earnings contract, multiples compress, forced selling amplifies. Magnitude depends on starting valuation (connecting to `valuation_mean_reversion`) and fragility level (connecting to `structural_fragility`). |
| TLT | Rally sharply | +15% to +30% | During Deflation contraction | **Deflation ONLY.** Flight to quality + rate cut expectations + deflation pricing. TLT is the premier deflation hedge. This is the most important quadrant distinction — TLT is your best friend in Deflation and your enemy in Stagflation. |
| TLT | Decline or flat | -5% to +3% | During Stagflation contraction | **Stagflation ONLY.** Inflation prevents the full flight-to-quality bond rally. The Fed is constrained — can't cut aggressively because inflation is elevated. Bonds offer no hedge. This is the worst environment for traditional 60/40 portfolios. |
| GLD | Rally | +15% to +40% | During Stagflation contraction | **Stagflation.** Gold is the only reliable hedge when both stocks AND bonds are failing. 1973-74 and 1979-80 are the templates. In Deflation, gold is neutral to slightly positive (less compelling than TLT). |
| SHY | Outperform risk assets | +3% to +5% total, but real return uncertain | During both contraction types | **Both.** Cash preserves capital during drawdowns. In Deflation, real return is positive (falling prices). In Stagflation, nominal return is positive but real return may be negative (inflation erodes purchasing power). Cash is the default haven when you can't determine which quadrant you're in. |
| IWM | Underperform SPY initially, outperform in recovery | -25% to -45% initially, then +20% to +40% relative in first 12M of recovery | Decline: first 6-12 months. Recovery: subsequent 12-18 months | **Both.** Small caps are more leveraged to the domestic economy and credit conditions. They decline more in contraction but recover more aggressively as credit reopens. The IWM/SPY relative ratio is a cycle indicator itself — its trough typically coincides with the cycle trough. |
| HYG | Sharp underperformance | -10% to -25% total return | During contraction | **Both quadrants.** Default risk reprices. Spreads widen 200-500bp from cycle tights. Forced selling by constrained institutions (rating mandates) amplifies the decline. HYG underperformance is both a symptom and an accelerant of contraction. |

### Conditional (interaction with other theories)

| Condition | Prediction | Specificity Gain |
|-----------|-----------|-----------------|
| If `fiscal_dominance_liquidity` is Active during late expansion | The contraction may be **delayed or attenuated**. Fiscal spending provides a demand floor that credit contraction alone cannot break. Prediction: traditional late-cycle indicators (ISM below 50, curve inversion, SLOOS tightening) fire 12-24 months before any recession materializes, if one materializes at all. The expansion phase scoring may show "Adjacent to Contraction" for an extended period — a limbo state where the cycle WANTS to turn but fiscal injection prevents it. Expression: stay cautiously long equities but hedge with GLD rather than TLT (fiscal dominance means inflation, not deflation, on the other side). | This is THE critical interaction for current conditions. It answers the question: "all the late-cycle indicators are flashing — why isn't the recession here?" Fiscal dominance is the answer. The specificity gain: the generator should NOT produce "recession imminent" hypotheses when fiscal dominance is also Active, because the mechanism that would produce the recession is being overridden. |
| If `structural_fragility` is Active (Building) during late expansion | The eventual contraction will be **more severe than the cycle indicators alone suggest**. The combination of late-cycle vulnerability + fragility buildup means that when the turn comes, it will be amplified by forced selling, passive outflows, and leverage unwind. Prediction: drawdown at upper end of range (-30% to -45% instead of -20% to -30%). Recovery also takes longer because damage to credit conditions is deeper. | Narrows the magnitude estimate. Cycle theory alone predicts a "normal" recession drawdown (-20% to -30%). Adding fragility pushes the estimate higher because the turn itself triggers non-linear mechanical selling that overshoots. |
| If contraction is **Stagflationary** AND `fiscal_dominance_arithmetic` is Active | This is the worst case for traditional portfolios. Equities decline because growth is contracting. Bonds decline because inflation prevents rate cuts and fiscal issuance floods the market. Only gold and cash provide defense. Prediction: 60/40 portfolios deliver -15% to -25% over the contraction period. GLD outperforms both SPY and TLT by 20%+ during the episode. Expression: maximum GLD allocation (20-30%), reduce both equities and duration, hold remaining in SHY. | Identifies the specific scenario where ALL conventional safe havens fail simultaneously. The only modern precedent is 1973-74 (SPY -48%, TLT equivalent -15%, GLD +67%). This is the scenario the generator should flag as highest-impact, even if not highest-probability. |
| If contraction is **Deflationary** AND `debt_cycle_long` is Active (late long-term cycle) | The central bank's response will be **more aggressive than normal** because MP1 (rate cuts) may be insufficient if rates are already low. Expect rapid escalation to MP2 (QE) and possibly MP3 (fiscal-monetary coordination). Prediction: initial decline is sharp (-25% to -35%) but recovery is fast (V-shaped within 6-12 months) as authorities deploy overwhelming force. TLT rallies sharply in the initial phase (+20% to +30%) but gives back gains as MP2/MP3 generate inflation. The best trade is TLT at contraction onset, rotating to GLD/TIPS 6-12 months later as policy response generates inflation. | Provides a sequencing recommendation that neither theory alone produces. The deflation-to-reflation sequence is tradeable: long TLT at the break, then rotate to inflation hedges when the policy response arrives. |

---

## downstream_implications

### affects[]

| Target Theory | Relationship | Description |
|--------------|-------------|-------------|
| `structural_fragility` | **triggers** | A cycle turn from expansion to contraction is one of the most common catalysts for a Minsky moment. Credit tightening → earnings disappointments → margin calls → forced selling. The fragility was already present (building during the expansion); the cycle turn provides the CATALYST. The evaluator should check: when both theories are Active (short cycle transitioning to contraction + fragility in building phase), the magnitude estimate should be at the upper end of both theories' ranges. |
| `fiscal_dominance_liquidity` | **contradicts (partially)** | The short-term debt cycle says "late-cycle indicators predict recession." Fiscal dominance liquidity says "deficit spending prevents the recession from materializing." This is a genuine, testable contradiction. The data resolves it: if unemployment is rising AND net liquidity is expanding, fiscal dominance is losing the fight (cycle theory wins). If ISM is below 50 but unemployment is stable and GDP positive, fiscal dominance is winning (fiscal theory wins, cycle is extended). The evaluator must not allow the generator to dodge this contradiction by invoking both theories without a resolution. |
| `valuation_mean_reversion` | **modifies** | Cycle positioning changes how valuation mean reversion plays out. In early-to-mid expansion, stretched valuations can PERSIST for years because earnings growth closes the gap from the numerator side. In late expansion, stretched valuations meet declining earnings power — the reversion comes through price decline, not earnings catch-up. The cycle phase modifies valuation theory's TIMING, not its truth. |
| `capital_flows` | **triggers (conditional)** | A US contraction can be the catalyst that initiates the capital flow rotation toward EM — especially if EM is in its own expansion phase. The US recession removes the US growth exceptionalism premium that was keeping capital at home. This interaction is conditional on EM being in Accumulation or Rotation phase (if EM is also contracting, no rotation occurs). |

---

## falsifiers

### Hard Falsifiers

These conditions, if met, indicate that the short-term debt cycle mechanism is NOT the dominant force driving economic outcomes.

| # | Condition | Metric | Threshold | Rationale |
|---|-----------|--------|-----------|-----------|
| H1 | Expansion persists for 24+ months with deeply restrictive monetary policy AND no fiscal offset | `rates.fed_funds` > nominal GDP by 2%+ for 24 months + deficit below $800B annualized + no recession | Multiple: fed_funds, gdp, deficit pace, unemployment | If the economy sustains strong growth with genuinely restrictive monetary policy AND no fiscal offset, the credit cycle mechanism is not operating as described. Something else is driving growth (productivity boom, structural change, external capital inflows). This has never occurred in post-war US history, which is why the theory is robust. |
| H2 | Credit contraction does NOT produce economic weakness | SLOOS showing broad tightening for 4+ quarters + HY spreads above 500bp + bank lending declining YoY, but unemployment stays below 4.5% and GDP growth above 2% for 12+ months | SLOOS, hy_spread, unemployment, gdp | If credit conditions tighten severely but the economy doesn't slow, the credit channel is not the primary growth driver. Possible explanation: the economy has structurally shifted away from credit-sensitive sectors (more services, less manufacturing/housing). This would fundamentally weaken the debt cycle framework. |
| H3 | Phase B indicators all triggered but no recession materializes within 18 months | Phase B activation score ≥ 0.60 sustained for 18 months without NBER recession declaration or GDP contraction | Phase B composite score + GDP + NBER | If the contraction indicators are screaming but no recession arrives within 18 months, either the indicators are miscalibrated or an overriding force (fiscal dominance is the prime candidate) is preventing the mechanism from completing. Note: this falsifier specifically tests the THEORY, not the indicators — it asks whether the debt cycle mechanism is operative. If fiscal dominance is the explanation, this falsifier triggers for the debt cycle while fiscal dominance theory remains Active. Both conclusions are correct simultaneously. |

### Soft Falsifiers

| # | Condition | Metric | Threshold | Severity | Implication |
|---|-----------|--------|-----------|----------|-------------|
| S1 | Yield curve signal fails to predict recession within 24 months of deep inversion | `rates.curve_2s10s` | Curve re-steepens above +25bp for 2+ months while ISM rises above 50 and payrolls stay positive | **medium** | The curve's track record is perfect (post-war). If it produces a false positive, the indicator needs recalibration. Possible explanation: fiscal dominance has changed the curve's information content. Implication: reduce weight on curve-based indicators for cycle timing, increase weight on SLOOS and claims. |
| S2 | ISM diverges from GDP for 6+ months | `growth.ism_proxy` vs. GDP | ISM below 48 for 2+ months while monthly payrolls remain above +100K | **minor** | Manufacturing and the broad economy are decoupling. The ISM may be measuring a sectoral rotation (manufacturing weakness offset by services strength) rather than a broad cycle turn. Implication: ISM becomes less reliable as a cycle indicator; weight should shift to services-sector indicators and aggregate employment data. |
| S3 | Central bank pre-emptively cuts before labor market deterioration | Fed funds trajectory + `growth.unemployment` | Fed cuts 50bp+ while unemployment is below 4.5% and has not risen more than 0.3pp in prior 3 months | **major** | The central bank is trying to engineer a soft landing by cutting pre-emptively. If successful, the "contraction" may be so shallow as to be undetectable in the data. Implication: Phase B may never formally activate — the expansion extends with a growth scare but no recession. Reduces the magnitude of contraction-phase predictions. |
| S4 | The four-quadrant determination is ambiguous | Inflation and growth indicators | Growth and inflation indicators contradict each other for 6+ weeks (e.g., ISM rising but CPI also rising, or ISM falling but CPI also falling) | **minor** | The quadrant overlay requires clear positioning. If the data is mixed (growth mixed, inflation mixed), the optimal asset allocation is uncertain. Implication: the generator should NOT produce high-conviction quadrant-dependent predictions. Cash/SHY is the default in quadrant ambiguity. |

| S5 | Primary predicted asset moves 15%+ against the hypothesis direction within the hypothesis holding window, without a corresponding fundamental falsifier triggering | Price of primary `predicted_assets` ticker(s) | 15% adverse move from hypothesis entry point within stated timeframe | **medium** | The market is pricing information the hypothesis mechanism does not capture. Either the mechanism is wrong, the timeframe is wrong, or an unmodeled force is dominant. Does NOT automatically invalidate the mechanism — forced liquidations, positioning squeezes, and liquidity events can produce temporary adverse moves that reverse. But the hypothesis must explain the adverse move or accept the discount. |

---

## metadata

```json
{
  "theory_id": "debt_cycle_short",
  "version": 1,
  "last_updated": "2026-03-30",
  "update_type": "refinement",
  "confidence_in_specification": "high",
  "notes": "This is the most historically tested theory in the registry. Post-war US has produced 12 complete short-term cycles with recession endpoints. The thresholds are calibrated against all 12, with primary emphasis on the 4 most recent (2001, 2007-09, 2020, 2022-present). Confidence in the expansion/contraction indicators is high — they have worked every time. Confidence in the four-quadrant overlay is medium — Goldilocks and Deflation are clean categories, but the Reflation/Stagflation boundary is fuzzy in real-time (how much inflation = reflation vs. stagflation?). The biggest open question is Hard Falsifier H3: are we currently in a regime where fiscal dominance has broken the debt cycle? The 2022-2025 experience (massive rate hikes, no recession) is the strongest evidence yet that the short-term cycle mechanism can be overridden. If so, this is historically unprecedented. Added price action soft falsifier (medium severity, 0.25 discount) to close the gap where adverse price action was not captured by any pre-registered falsifier, forcing the LLM elimination pass to freelance on status assignment. The 15% threshold is calibrated above normal ETF monthly ranges (3-8%) to avoid triggering on noise.",
  "historical_episodes_referenced": [
    "2001 recession (dot-com bust → mild contraction, ISM to 41, unemployment 4.0% to 6.3%, SPY -49% peak-to-trough over 2.5 years due to valuation excess, TLT equivalent +20%)",
    "2007-2009 Great Recession (housing/credit bust → severe contraction, ISM to 33, unemployment 4.4% to 10.0%, SPY -57%, HY spreads to 2000bp, TLT +33%, deflation quadrant, required MP2 escalation)",
    "2020 COVID recession (exogenous shock → ultra-fast contraction, ISM to 41, unemployment 3.5% to 14.7% in 2 months, SPY -34% in 23 trading days, fastest V-shaped recovery due to unprecedented MP3 deployment — $5T+ fiscal + unlimited QE)",
    "2022-2025 non-recession (Fed funds 0% to 5.25% in 16 months, yield curve deeply inverted, ISM below 50 for extended periods, SLOOS showed tightening — BUT no recession. Strongest evidence for fiscal dominance overriding the short-term cycle mechanism. Hard Falsifier H3 may be approaching trigger.)",
    "1973-1974 stagflation recession (oil shock + tight money, SPY -48%, TLT equivalent -15%, GLD +67% — the template for stagflationary contraction where bonds fail as a hedge)",
    "1995 soft landing (Greenspan pre-emptive cuts, unemployment never rose significantly, expansion extended 6 years — template for Soft Falsifier S3)"
  ]
}
```

---

## Usage Notes for Generator and Evaluator

### For the Generator

When Phase A (Expansion) is Active, generate hypotheses about:

- **Which quadrant are we in?** This is the FIRST determination. Goldilocks, Reflation, Stagflation, or Deflation — each produces different positioning. The generator MUST specify the quadrant in every expansion-phase hypothesis. A hypothesis that says "equities outperform during expansion" without specifying the quadrant is useless — QQQ outperforms in Goldilocks and underperforms in Reflation.

- **Where are we in the expansion?** Early cycle (ISM rising from below 50, unemployment starting to decline, spreads tightening from wide) has different risk/reward than late cycle (ISM peaking, unemployment at cycle lows, spreads at cycle tights). The expansion-phase indicators don't distinguish early from late — the generator must use trajectory (direction of change) to assess maturity.

- **What are the late-cycle warning signs?** Even during active expansion, the generator should monitor: curve flattening/inversion, SLOOS starting to tighten, ISM rolling over, initial claims inflecting upward. These don't mean "contraction imminent" — they mean "the expansion is aging." Produce contingent hypotheses: "if ISM falls below 48 in the next 3 months, Phase B probability increases to X."

- **Interaction with fiscal dominance.** If `fiscal_dominance_liquidity` is also Active, the generator should explicitly address whether the expansion is self-sustaining (credit-driven) or fiscally sustained (deficit-driven). This distinction matters because credit-driven expansions end through the credit cycle mechanism (the theory works normally), while fiscally-sustained expansions can extend beyond normal duration (the theory's timing is unreliable but its directional predictions still hold when the turn eventually arrives).

**What NOT to claim:**

- Do NOT predict the specific month of cycle turn. The theory identifies late-cycle conditions, not the precise inflection. A hypothesis that says "recession begins in Q3" is overspecified — the theory supports "late-cycle indicators suggest elevated recession risk over the next 6-18 months."
- Do NOT assume the quadrant is static. The economy can move from Goldilocks to Reflation within a quarter (inflation surprise). The generator should produce hypotheses about quadrant transitions, not just the current quadrant.
- Do NOT ignore the fiscal dominance interaction. If you produce a "recession is imminent" hypothesis while fiscal dominance is Active, you are implicitly claiming that fiscal dominance is failing. State that explicitly and provide the evidence.

### For the Evaluator

Priority checks:

1. **Did the generator specify the quadrant?** Reject any expansion-phase hypothesis that doesn't identify Goldilocks, Reflation, Stagflation, or Deflation. "Equities go up in expansion" is not a testable hypothesis — it needs the quadrant context.

2. **Is the phase determination correct?** Check whether Phase B indicators are actually triggered. The generator may claim "expansion" because GDP is positive, while ISM is below 48, claims are rising, and SLOOS is tightening. Check the mechanical score — the activation layer exists precisely to prevent the generator from cherry-picking indicators.

3. **Is the fiscal dominance interaction addressed?** In the current macro environment (post-2022), any contraction hypothesis that doesn't address fiscal dominance is incomplete. If late-cycle indicators are firing but no recession is materializing, the most likely explanation is fiscal override — the generator must state this and explain why it believes the cycle will turn anyway (or acknowledge that fiscal dominance may extend the expansion further).

4. **Are magnitude estimates quadrant-appropriate?** A Stagflationary contraction has different magnitudes than a Deflationary contraction. Check that the generator's drawdown and recovery estimates match the quadrant. -40% SPY + +30% TLT is a deflation prediction. -40% SPY + -10% TLT is a stagflation prediction. The generator should not claim both simultaneously.

5. **Composition quality with structural_fragility.** If both theories are invoked, the combined hypothesis must produce a MORE specific magnitude or timing estimate than either theory alone. "Late cycle + fragility = bad" is not a valid composition. "Late cycle indicators + elevated fragility (30%+ concentration, VIX below 14) = drawdown at upper end of range (-35% to -45%) with recovery leadership in small caps and EM" IS a valid composition because it narrows magnitude and identifies recovery leadership.
