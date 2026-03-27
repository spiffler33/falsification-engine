# Theory Module: Fiscal Dominance — Net Liquidity Transmission

*Version 1.0 — March 2026*
*Status: Prototype — thresholds calibrated against 2020-2026 fiscal expansion episode, with cross-reference to 1940s financial repression. Pending live testing.*

---

## theory_id

`fiscal_dominance_liquidity`

---

## activation_conditions

This is a single-phase theory. When active, fiscal deficit spending is injecting reserves into the financial system faster than the Fed can drain them. Net liquidity is the dominant driver of asset prices, and monetary policy is subordinate.

| Indicator | Metric Source | Threshold | Direction | Weight | Rationale |
|-----------|--------------|-----------|-----------|--------|-----------|
| Net liquidity expanding | computed: `net_liquidity_30d_change` | Positive for 2+ of last 3 months | above | 0.20 | The direct test. Net liquidity (Fed BS − TGA − RRP) captures actual reserves in the financial system. If it's expanding despite the Fed running QT, the fiscal channel is overwhelming the monetary channel. This is the single most important indicator — it IS the mechanism in real-time. |
| Deficit pace | web search: US Treasury monthly budget statements | Above $1.5T annualized | above | 0.20 | The fuel. Deficit spending creates deposits and reserves. Below $1.5T, the fiscal impulse is insufficient to overpower QT at current balance sheet runoff rates (~$60B/month = ~$720B/year). Above $1.5T, the deficit is injecting reserves faster than QT drains them. The $1.5T threshold is calibrated to the approximate equilibrium point where fiscal injection ≈ QT extraction. |
| Rate hikes not producing recession | `growth.unemployment` + `growth.ism_proxy` | Unemployment below 5% AND ISM proxy above 45 after 12+ months of Fed funds above 4% | above | 0.15 | The paradox test. In monetary dominance, rates above 4% for a year produce visible economic contraction (rising unemployment, ISM deeply below 50). If the economy absorbs 5%+ rates without contracting, something is overriding monetary transmission. That something is fiscal spending. This indicator does not identify the mechanism — it identifies the symptom (monetary policy impotence). |
| Hard assets outperforming nominal bonds | computed: `hard_vs_nominal_12m` | Above +10% (i.e., average hard asset 12M return exceeds average nominal bond 12M return by 10%+) | above | 0.15 | The asset price confirmation. When the fiscal channel dominates, the inflation/debasement implications favor assets with replacement cost or scarcity value over fixed-income promises. GLD, SLV, DBC outperforming TLT, IEF is the asset market's verdict that fiscal dominance is operative. Below +5% divergence is inconclusive. Above +10% is a clear signal. |
| RRP draining toward zero | `liquidity.reverse_repo` | Below $250B and declining | below | 0.10 | Reserve buffer indicator. The RRP facility was a reservoir of $2.5T at its peak — money market funds parking cash at the Fed. As it drains, those reserves re-enter the financial system, boosting net liquidity. Below $250B, the buffer is nearly exhausted. This matters because it changes WHAT HAPPENS NEXT: once drained, the Fed faces a choice between allowing reserve scarcity (risking a Sept 2019-style repo spike) or ending QT early (capitulating to fiscal dominance). Either outcome confirms the thesis. |
| Fed balance sheet direction inconsistent with stated policy | `liquidity.fed_balance_sheet` direction vs. stated QT pace | Fed BS declining slower than announced QT pace, OR flat, OR expanding despite no announced policy change | rising or flat | 0.10 | The stealth capitulation indicator. The Fed may not formally end QT, but if the balance sheet stops shrinking or starts growing (via discount window lending, BTFP-style facilities, or other interventions), the central bank is de facto accommodating fiscal dominance. March 2023 (SVB response: ~$400B balance sheet expansion in two weeks while officially still doing QT) is the template. |
| TGA behavior consistent with spending | `liquidity.tga` | TGA below $500B OR declining by $100B+ over 60 days | below or falling | 0.10 | Treasury is spending its cash buffer, which releases reserves into the system. When TGA is high and building, it temporarily drains liquidity (Treasury accumulating cash from issuance without spending it). When TGA drains, reserves flood back. The threshold captures periods where Treasury is actively deploying cash, which directly boosts net liquidity regardless of Fed policy. |

**Activation scoring:**
- Weighted score ≥ 0.60 → **Active**
- Weighted score 0.30–0.59 → **Adjacent**
- Weighted score < 0.30 → **Inactive**

**Supplementary flags (qualitative — not scored mechanically):**

| Flag | Source | What to look for |
|------|--------|------------------|
| Bipartisan fiscal expansion | Web search: Congressional Budget Office, fiscal policy news | Neither party campaigning on deficit reduction. Both parties proposing new spending or tax cuts. This is the political precondition for sustained fiscal dominance — it means NO policy correction is forthcoming. |
| Fed officials acknowledging fiscal offset | Web search: FOMC minutes, Fed speeches | Language like "fiscal policy is offsetting monetary tightening" or "the neutral rate may be higher than estimated" — coded acknowledgment that rate hikes aren't working as expected. |
| Treasury issuance composition shifting to bills | Web search: Treasury refunding announcements | Heavy bill issuance (short-dated) rather than coupon issuance. Bills are more easily absorbed by money market funds and don't create duration risk. This signals Treasury is managing around the fiscal dominance constraints — accommodating it rather than challenging it. |

---

## core_mechanism

### Causal Chain

```
1. Government runs fiscal deficit above $1.5T annualized
   (spending exceeds tax receipts by this amount on a run-rate basis).
   This is the EXOGENOUS FORCE. It is a political outcome, not a market outcome.
   The central bank does not control it.
   ↓
2. To fund the deficit, Treasury issues bonds.
   Bond proceeds go into the TGA (Treasury's checking account at the Fed).
   This step temporarily DRAINS reserves from the banking system
   (cash moves from bank reserves to the TGA).
   ↓
3. Treasury SPENDS the proceeds — paying contractors, transfer payments,
   interest on existing debt, federal salaries.
   This step INJECTS reserves back into the banking system
   (money moves from TGA into recipient bank accounts at the Fed).
   NET EFFECT of steps 2+3: reserves in the banking system INCREASE
   by approximately the deficit amount, because the spending exceeds
   tax receipts by definition of deficit.
   ↓
4. Simultaneously, the Fed is running QT — allowing bonds to mature
   without reinvesting, shrinking its balance sheet.
   This DRAINS reserves at ~$60B/month (~$720B/year at 2024-2025 pace).
   ↓
5. THE CRITICAL ARITHMETIC:
   If deficit pace ($1.5T+) exceeds QT drainage (~$720B),
   net reserves in the system EXPAND despite QT.
   This is fiscal dominance in its simplest form:
   the fiscal channel overwhelms the monetary channel.
   ↓
6. Net liquidity (Fed BS − TGA − RRP) rises.
   This captures the actual usable reserves in the financial system
   after subtracting reserves locked in TGA (not yet spent)
   and RRP (parked at Fed by money market funds).
   ↓
7. Rising net liquidity flows into asset prices.
   The transmission: banks and financial institutions with excess reserves
   seek yield → buy risk assets, extend credit, fund levered positions.
   The correlation between net liquidity and SPY/risk assets
   has been tighter than any other macro variable since 2020.
   ↓
8. Rate hikes become PARADOXICALLY STIMULATIVE:
   Higher rates → higher interest expense on $35T+ federal debt →
   larger deficit → more Treasury issuance → more reserves injected
   when spent → higher net liquidity → higher asset prices.
   The central bank is running on a treadmill that speeds up as it runs faster.
   ↓
9. The feedback loop:
   Higher asset prices → higher capital gains tax receipts
   (partially offsetting the deficit, but not enough) →
   wealth effect → stronger consumption → economy doesn't slow →
   Fed can't cut rates → interest expense stays high → deficit stays wide.
   The loop sustains itself until an exogenous shock breaks it
   (genuine fiscal consolidation, productivity boom, or deflation shock).
```

### What Net Liquidity Actually Measures

Net liquidity is not a theoretical construct — it is an accounting identity:

**Net Liquidity = Federal Reserve Balance Sheet − Treasury General Account − Reverse Repo Facility**

- **Fed Balance Sheet (WALCL):** Total assets held by the Fed. When it buys bonds (QE), this rises and reserves increase. When bonds mature without reinvestment (QT), this falls and reserves decrease.
- **TGA (WTREGEN):** Treasury's cash balance at the Fed. When Treasury issues bonds and hasn't yet spent the proceeds, cash sits here — draining reserves from banks. When Treasury spends, cash moves from TGA to bank reserves.
- **RRP (RRPONTSYD):** Cash parked at the Fed by money market funds, earning the RRP rate. These are reserves that exist but are not circulating in the financial system. As RRP drains (money market funds redirect to T-bills or other assets), reserves re-enter circulation.

The formula captures reserves that are actually available to the financial system — not locked in government accounts or parked at the Fed. It is the best single-variable predictor of broad risk asset direction since 2020.

### Time Horizon

**Primary:** 1-6 months. Net liquidity changes transmit to asset prices with a lag of days to weeks, not months. This is the most tactically relevant theory in the registry.

**Secondary:** The CONDITIONS that sustain fiscal dominance (deficit pace, political unwillingness to cut, demographic spending pressures) operate on a 3-10 year horizon. But the asset price transmission is fast. Think of it as: the structural conditions are slow-moving, but the flow-through to markets is rapid.

---

## predictions_when_active

### Directional

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| SPY | Rally, but lag hard assets in real terms | +5% to +15% per year in nominal terms | Rolling 12 months | Net liquidity expansion supports ALL asset prices via the reserve/credit channel. Equities benefit but face two headwinds: high rates compress multiples, and inflation erodes real returns. Nominal positive, real returns mediocre. |
| GLD | Outperform | +10% to +25% per year | Rolling 12 months | Gold benefits from both the liquidity channel (more reserves chasing finite gold supply) AND the debasement channel (markets pricing eventual dollar value erosion). Double tailwind. Central bank buying provides structural floor under price. |
| IBIT | Outperform (higher vol) | +15% to +50% per year with ±30% drawdowns | Rolling 12 months | Bitcoin as a fiscal dominance proxy — outside government debasement ability, finite supply, increasingly held by institutions. Higher beta to net liquidity than gold. Contested thesis: requires continued institutional adoption narrative. |
| TLT | Underperform in real terms | -5% to -15% total return (nominal) OR flat nominal but negative real | Rolling 12 months | Nominal bonds are the victim of fiscal dominance. Higher deficits → more issuance → supply pressure on long end. Inflation from fiscal spending erodes coupon value. The term premium rising (Pozsar's indicator) is the market pricing this in. |
| TIP | Outperform nominal bonds | TIPS outperform TLT by +5% to +15% | Rolling 12 months | TIPS protect against the inflation that fiscal dominance generates. The breakeven spread (difference between nominal and TIPS yields) should widen as the market prices in higher sustained inflation from fiscal spending. |
| SHY | Positive carry but losing to hard assets | +4% to +5.5% total return | Rolling 12 months | Short-duration cash earns high yield in this environment (the Fed rate is high because of the fiscal inflation dynamic). Cash is a fine holding relative to TLT. But cash LOSES to gold, commodities, and equities in nominal terms because net liquidity is expanding. Cash wins only during brief liquidity contractions. |
| DBC | Outperform bonds | +5% to +15% per year | Rolling 12 months | Commodities benefit from the same liquidity + debasement dynamic as gold, with additional demand-side support from fiscal spending (infrastructure, defense, energy subsidies). Less pure than gold but broader exposure. |
| EEM | Conditional — see below | — | — | EM benefits from net liquidity expansion via the risk-appetite channel, but dollar direction matters more. If fiscal dominance weakens the dollar, EM benefits doubly. If the dollar stays strong (flight to US assets despite fiscal concerns), EM underperforms. |

### Conditional (interaction with other theories)

| Condition | Prediction | Specificity Gain |
|-----------|-----------|-----------------|
| If `debt_cycle_short` is Active (Contraction phase) | Net liquidity expansion may be **insufficient** to prevent equity drawdown if credit conditions tighten sharply. Prediction: SPY declines -10% to -20%, but the drawdown is shallower and shorter than a non-fiscal-dominance contraction (-25% to -40%). GLD still outperforms. TLT rally is capped because fiscal issuance limits the flight-to-quality bid. | Narrows the "does fiscal dominance prevent recession?" question. Answer: it attenuates the severity but may not prevent it entirely. Converts a binary prediction into a magnitude estimate. |
| If `structural_fragility` is Active (Building phase) | Fiscal liquidity injection **extends the fragility-building phase** beyond its normal duration. The Minsky moment is delayed because net liquidity provides a continuous bid under risk assets. BUT: the eventual break is LARGER because fragility compounds during the extended building phase. Prediction: the duration of calm is longer than fragility theory alone predicts (add 12-24 months to the expected fragility resolution timeline), and the magnitude of the eventual break is at the upper end of fragility's range (-35% to -50% instead of -25% to -40%). | Critical composition insight: fiscal dominance doesn't prevent Minsky dynamics — it extends the building phase and amplifies the eventual resolution. This is the most important interaction in the registry for current conditions. |
| If `fiscal_dominance_arithmetic` is also Active | The two fiscal dominance mechanisms reinforce each other. Liquidity transmission drives NEAR-TERM asset prices; fiscal arithmetic drives STRUCTURAL positioning. Combined prediction: GLD and hard asset overweight should be BOTH tactical (net liquidity) AND strategic (devaluation arithmetic). Sizing should be larger than either theory alone suggests (20-30% portfolio allocation to hard assets vs. 10-15% from either theory independently). | Converts independent signals into a conviction multiplier. When both the flow (liquidity) and the stock (debt arithmetic) are confirming, portfolio expression should be at the upper end of suggested ranges. |
| If `valuation_mean_reversion` is Active (expensive market) | Fiscal liquidity may sustain NOMINAL equity prices even at extreme valuations, delaying the valuation mean reversion. Prediction: the equity risk premium stays compressed longer than valuation theory alone predicts. But REAL returns are poor (inflation eroding nominal gains). The resolution: either a nominal crash eventually (if fiscal impulse falters) or an inflationary grind that delivers negative real returns without a nominal crash (the 1970s outcome). | Narrows the critical question: "does valuation mean reversion happen via price decline or via inflation eroding real values while nominal prices tread water?" Fiscal dominance biases toward the inflationary grind — prices don't crash, but purchasing power erosion is the penalty for overvaluation. |
| If `monetary_architecture` is also Active | The plumbing stress that monetary architecture theory identifies can DISRUPT the net liquidity transmission. If cross-currency basis blows out or repo markets freeze, the smooth transmission from fiscal spending → reserves → asset prices breaks down. Prediction: short-term liquidity disruptions create buying opportunities within the fiscal dominance trend, because the Fed will be forced to intervene (swap lines, new facilities) to restore plumbing, which ADDS to net liquidity. Post-disruption net liquidity is HIGHER than pre-disruption. | Converts a potential contradiction into a buying signal: plumbing stress within a fiscal dominance regime is a buying opportunity, not a regime change. The Fed's plumbing interventions are net-additive to liquidity. |

---

## downstream_implications

### affects[]

| Target Theory | Relationship | Description |
|--------------|-------------|-------------|
| `debt_cycle_short` | **extends** | Fiscal liquidity injection can prevent the short-term debt cycle from contracting normally. Traditional late-cycle indicators (yield curve inversion, ISM below 50, rising claims) may fire without producing recession because the fiscal impulse exceeds the monetary drag on aggregate demand. This doesn't eliminate the cycle — it extends it. When the extension finally ends, the accumulated imbalances from the extended cycle are larger, and the eventual contraction is more severe. The evaluator should treat sustained late-cycle indicators with 18+ months of no recession as evidence that this interaction is operative. |
| `structural_fragility` | **extends (partially contradicts)** | Net liquidity expansion provides a continuous bid under risk assets, dampening volatility and delaying fragility resolution. This creates a false sense of security — the very mechanism that prevents the break in the short run compounds the fragility for the next cycle. The contradiction: fragility theory says "the break is coming" while fiscal liquidity says "not yet, the bid is still there." The resolution: fragility compounds during the extension, making the eventual break larger. Timing is extended; magnitude is amplified. |
| `fiscal_dominance_arithmetic` | **reinforces** | The liquidity transmission and the fiscal arithmetic are two manifestations of the same underlying condition (unsustainable deficit spending). Liquidity transmission is the near-term price driver. Fiscal arithmetic is the structural trajectory. When both are active, they cross-confirm: the flow data (net liquidity expanding) validates the stock concern (debt trajectory unsustainable). |
| `monetary_architecture` | **modifies** | Fiscal liquidity dynamics change what plumbing stress means. In a non-fiscal-dominance regime, plumbing stress is a warning of systemic fragility. In a fiscal dominance regime, plumbing stress triggers Fed interventions that ADD to net liquidity. The Sept 2019 repo spike led to $400B of "not-QE" balance sheet expansion. The March 2023 SVB crisis led to BTFP. Each plumbing event is resolved by MORE reserves, not less. Monetary architecture theory's stress gauges become BUY signals for fiscal dominance positioning. |

---

## falsifiers

### Hard Falsifiers

These conditions, if met, indicate that the fiscal dominance liquidity mechanism is NOT operative. Any hypothesis invoking this theory should be disconfirmed if any hard falsifier is triggered.

| # | Condition | Metric | Threshold | Rationale |
|---|-----------|--------|-----------|-----------|
| H1 | Net liquidity contracts despite large deficit | computed: `net_liquidity_30d_change` + deficit pace from web search | Net liquidity declines for 3+ consecutive months while the deficit remains above $1.5T annualized | This is the core mechanism test. If net liquidity contracts despite fiscal spending, the transmission mechanism is broken. Possible causes: massive TGA build (Treasury hoarding cash), QT accelerating beyond deficit offset, or RRP re-expanding (money market funds parking cash back at the Fed). Whatever the cause, if the mechanism isn't transmitting, the theory's asset price predictions don't hold. |
| H2 | Rate hikes produce recession within 12 months | `growth.unemployment` + `growth.ism_proxy` | Unemployment rises above 5.5% AND ISM below 45 within 12 months of the last rate hike, with deficit above $1.5T | If the economy contracts sharply despite massive fiscal spending, monetary transmission is still dominant. The rate hikes are working — the fiscal impulse is insufficient to override them. This falsifies the core paradox claim (that rate hikes are stimulative via interest expense). The deficit threshold is important: if the deficit is below $1.5T when recession hits, the theory isn't falsified — the fiscal impulse simply wasn't large enough. |
| H3 | Genuine fiscal consolidation | Web search: CBO monthly budget review, Treasury statements | Deficit falls below $800B annualized for 2+ consecutive quarters through actual spending cuts or revenue increases (not accounting adjustments or one-time items) | If the government actually reduces the deficit to below $800B on a sustained basis, the fuel for fiscal dominance is removed. $800B (vs. $720B QT pace) means QT is now draining reserves faster than fiscal injection replenishes them. Net effect flips to tightening. CRITICAL: one-quarter flukes don't count. Tax deadline lump-sum receipts (April/June) temporarily compress the deficit — the threshold requires 2+ consecutive quarters. |

### Soft Falsifiers

These conditions weaken the theory without killing it. They suggest the transmission is operative but attenuated, or that the theory's predictive utility is degraded.

| # | Severity | Condition | Metric | Threshold | Implication |
|---|----------|-----------|--------|-----------|-------------|
| S1 ⚠️ | **Major** | Net liquidity and asset prices decorrelate | computed: `net_liquidity` vs. `SPY` price | 3-month rolling correlation between net liquidity and SPY falls below 0.30 | **Strongest soft falsifier — with escalation clause.** If asset prices stop following net liquidity, the transmission mechanism may be overridden by other forces (AI earnings cycle, geopolitical repricing, credit channel dynamics) or may have been misspecified. While net liquidity is still expanding, the theory's *directional predictions* lose reliability — you cannot claim "net liquidity up therefore assets up" if the correlation has broken. **However, this is a soft rather than hard falsifier because temporary decorrelation is expected during regime transitions, narrative-driven markets, or periods where a single dominant factor (e.g., a tech earnings supercycle or a geopolitical shock) overwhelms the liquidity signal.** The correlation broke briefly in late 2022 (aggressive rate hikes dominated sentiment despite stable net liquidity) and re-established in 2023. **Escalation clause:** If the decorrelation persists for 18+ months across varied market conditions (i.e., not explained by a single dominant override factor), this falsifier should be escalated to a hard falsifier. Sustained decorrelation across multiple macro environments — a rate-hiking period, a cutting period, a risk-on phase, a risk-off phase — would constitute evidence that the net-liquidity-to-asset-price transmission was misspecified rather than merely temporarily overridden. At that point, the theory's core predictive mechanism is unreliable and hypotheses invoking it should be disconfirmed. |
| S2 | **Medium** | Dollar strengthening despite fiscal dominance | `DX-Y.NYB` (DXY) or `UUP` | DXY rises 3%+ over trailing 2 months concurrent with expanding net liquidity | Fiscal dominance should weaken the dollar (more supply of dollar-denominated assets, debasement concerns). If the dollar strengthens anyway (flight-to-safety, relative weakness elsewhere), the theory's GLD/DBC predictions weaken — hard assets perform better in dollar-weakness environments. Net liquidity → equity correlation may still hold, but the inflation/debasement channel (which drives gold/commodities) is impaired. |
| S3 | **Medium** | QT pace accelerating | `liquidity.fed_balance_sheet` rate of change | Fed BS declining faster than announced pace (e.g., $80B+/month vs. announced $60B) | The Fed is fighting harder against fiscal dominance. Doesn't break the theory if the deficit is large enough to offset, but the NET liquidity expansion slows. Asset price support attenuates. Predictions should be revised to the lower end of magnitude ranges. |
| S4 | **Minor** | RRP re-expanding | `liquidity.reverse_repo` | RRP rising above $500B after having declined below $250B | Money market funds parking cash back at the Fed. This removes reserves from circulation and reduces net liquidity. Possible cause: T-bill issuance declining (reducing alternatives for money market funds). Temporarily weakens the liquidity transmission without breaking the theory — the reserves still exist, they're just parked. |
| S5 | **Medium** | Hard assets underperforming despite rising net liquidity | computed: `hard_vs_nominal_12m` | Trailing 2-month hard_vs_nominal return negative while net liquidity expanded in the same period | If net liquidity is rising but gold and commodities aren't responding, the debasement premium isn't being priced. The equity/liquidity correlation may still hold (S&P benefits), but the full fiscal dominance thesis (which predicts hard asset outperformance specifically) is weakened. This may indicate that the market doesn't yet believe in the debasement trajectory — timing revision needed, not thesis revision. |

---

## metadata

```json
{
  "theory_id": "fiscal_dominance_liquidity",
  "version": 1,
  "last_updated": "2026-03-26",
  "update_type": "new",
  "confidence_in_specification": "medium-high",
  "notes": "Thresholds calibrated primarily against the 2020-2026 episode: the only modern period where fiscal deficits were large enough relative to QT to produce sustained fiscal dominance. The 1940s-1950s provide the historical precedent but under different conditions (explicit yield curve control, wartime economy, different financial system structure). The $1.5T deficit threshold is specific to the current QT pace (~$720B/year) and would need recalibration if QT pace changes. Net liquidity correlation with SPY has been exceptionally tight since 2020 but may weaken if other factors (AI earnings cycle, geopolitical shocks) dominate price action. The RRP drain from $2.5T toward zero is a one-time tailwind that cannot repeat — once it hits zero, one component of the net liquidity expansion formula is permanently removed.",
  "historical_episodes_referenced": [
    "2020-2021 COVID fiscal expansion ($5T+ in stimulus, net liquidity surged ~$3T, SPY +68% from March 2020 trough, GLD +25% in 2020)",
    "2022-2023 rate hiking cycle with no recession (Fed funds 0% to 5.25% in 16 months, economy continued growing, unemployment stayed below 4% — strongest evidence of fiscal dominance overriding monetary policy)",
    "March 2023 SVB/regional bank crisis (Fed expanded balance sheet ~$400B in 2 weeks while officially conducting QT — net liquidity surged, SPY rallied from March low through July high, demonstrating that plumbing interventions ADD to fiscal dominance)",
    "September 2019 repo spike (reserves fell below system minimum, Fed forced to inject $400B of 'not-QE' — template for how reserve scarcity forces Fed capitulation, supporting the fiscal dominance feedback loop)",
    "1942-1951 yield curve control (Fed capped long rates at 2.5% while Treasury ran wartime deficits, CPI 8-14%, negative real bond returns for a decade — the most complete historical episode of fiscal dominance with explicit central bank accommodation)"
  ]
}
```

---

## Usage Notes for Generator and Evaluator

### For the Generator

When this theory is Active, generate hypotheses about:

- **The current net liquidity trajectory.** What is each component doing? Is the Fed BS shrinking on schedule? Is the TGA building or draining? Is RRP still declining? Compute the NET and compare to 30/60/90 day ago levels. If net liquidity is expanding, state by how much and at what pace. This is the empirical foundation — every other hypothesis rests on it.

- **Which asset classes are confirming the transmission.** Check hard_vs_nominal_12m. Check GLD vs. TLT relative performance. Check SPY correlation with net liquidity. If the assets are following the liquidity, the mechanism is working. If divergences appear, interrogate them: is the divergence temporary (positioning, news event) or structural (transmission weakening)?

- **Whether the Fed is stealth-capitulating.** Look for balance sheet behavior inconsistent with stated QT policy. Discount window borrowing, new facilities, slowing the QT pace — all are forms of capitulation that EXPAND net liquidity. The generator should flag these as confirming evidence, not neutral events.

- **The interaction with the debt cycle.** This is the critical composition. Is fiscal liquidity preventing the recession that debt cycle theory predicts? If late-cycle indicators are firing (ISM below 50, claims rising, curve inverted) BUT unemployment stays low and GDP stays positive, the most likely explanation is fiscal dominance extending the cycle. State this explicitly and note that the extension makes the eventual contraction worse.

**What NOT to claim:**

- Do NOT claim fiscal dominance predicts equity market TIMING. Net liquidity predicts DIRECTION, not inflection points. A net-liquidity-driven rally can pause or dip 5-8% on any given month's TGA build or short-term noise.
- Do NOT claim this theory alone predicts the end of fiscal dominance. That is an exogenous political event. The theory tells you what happens WHILE fiscal dominance is active, not when it ends.
- Do NOT confuse this theory with `fiscal_dominance_arithmetic`. This module is about the FLOW (net liquidity this quarter). The arithmetic module is about the STOCK (cumulative debt trajectory over years). They can have different activation statuses — it is possible for the liquidity transmission to be inactive (temporary fiscal consolidation) while the arithmetic trajectory remains untenable.

### For the Evaluator

Priority checks:

1. **Is net liquidity actually expanding?** The generator may invoke this theory based on deficit data alone. Check the NET computation. If net liquidity is contracting (TGA build exceeding fiscal injection, or QT pace increasing), the theory's predictions don't apply regardless of the deficit level. The MECHANISM, not the precondition, must be operative.

2. **Is the asset price correlation holding?** Check the SPY-net liquidity correlation. If the decorrelation soft falsifier (S1) is triggered, the theory is unreliable for directional asset price claims even if net liquidity is expanding. The generator tends to assume the correlation holds — make it prove it with current data. If S1 has been active for 18+ months across varied conditions, escalate to hard falsifier status and disconfirm hypotheses invoking this theory's asset price predictions.

3. **Is the generator making a timing claim?** Net liquidity provides direction, not precision timing. If the hypothesis says "SPY will rally 15% in Q2 because net liquidity is expanding," challenge the magnitude and timing specificity. The theory supports "SPY is directionally supported while net liquidity expands" — not a specific percentage in a specific quarter.

4. **Has the generator distinguished this from a simple risk-on call?** Many things can cause SPY to rally. The fiscal dominance hypothesis must identify the SPECIFIC mechanism (deficit → reserves → asset prices) and the SPECIFIC evidence (net liquidity computation, hard vs. nominal asset divergence, monetary policy impotence). If the hypothesis reads like generic bullishness, it's not using the theory — it's using the theory as decoration.

5. **Composition quality check:** When combined with other theories, the composite hypothesis must be MORE specific and MORE falsifiable than the component theories. "Fiscal dominance is extending the debt cycle and compounding fragility" is valid if it produces a specific magnitude estimate, timeline adjustment, and failure condition. "Fiscal dominance plus fragility plus late cycle means something bad is coming eventually" is unfalsifiable narrative padding. Kill it.
