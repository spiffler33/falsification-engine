# Theory Module: Fiscal Dominance — Devaluation Arithmetic

*Version 1.0 — March 2026*
*Status: Prototype — thresholds calibrated against historical sovereign debt trajectories (US 1940s, UK 1940s-1970s, EM precedents), with primary emphasis on the post-2020 US fiscal trajectory. Pending live testing.*

---

## theory_id

`fiscal_dominance_arithmetic`

---

## activation_conditions

This is a single-phase theory. When active, the arithmetic of US federal debt — specifically the trajectory of interest expense relative to tax receipts — has crossed thresholds that historically force one of three resolutions: austerity (politically near-impossible), default (system-destroying), or devaluation (path of least resistance). The implication is structural: hard assets outperform nominal claims on a multi-year basis because the most likely resolution erodes the purchasing power of those nominal claims.

This theory is distinct from `fiscal_dominance_liquidity`. The liquidity module describes the FLOW mechanism — how deficit spending creates reserves and drives asset prices quarter to quarter. This module describes the STOCK problem — the cumulative debt trajectory and the mathematical endpoint it implies. Liquidity can be temporarily inactive (a quarter of deficit narrowing) while the arithmetic remains untenable. The arithmetic is a slower-moving, higher-conviction signal.

| Indicator | Metric Source | Threshold | Direction | Weight | Rationale |
|-----------|--------------|-----------|-----------|--------|-----------|
| Interest expense / tax receipts ratio | Web search: US Treasury Monthly Statement, CBO projections | Above 20% | above | 0.25 | The single most important indicator. When interest expense consumes more than 20% of federal revenue, the government is devoting a fifth of everything it collects just to service existing debt — before a dollar is spent on defense, Medicare, Social Security, or anything else. Historical precedent: no major sovereign has sustained interest/receipts above 25% without either defaulting or devaluing. The US is currently at ~23% and rising because: (a) total debt is $35T+, (b) low-rate debt (~1.5% coupons from 2020-2021 issuance) is rolling into high-rate debt (~4.5% coupons), and (c) deficits add more principal. The arithmetic is self-reinforcing: higher rates → higher interest expense → larger deficit → more debt → even higher interest expense. |
| Interest expense exceeds major discretionary category | Web search: CBO budget data | Annual interest expense > defense spending ($886B in FY2024) | above | 0.15 | A political and psychological threshold. When interest on debt costs more than the entire defense budget, the scale of the problem becomes legible to non-economists. This threshold was crossed in 2024. The next threshold — interest exceeding Medicare or Social Security — would represent a genuine fiscal crisis point. Each successive threshold crossed reduces the probability of voluntary correction and increases the probability of forced resolution. |
| Deficit pace outside recession | Web search: US Treasury monthly budget statements + NBER recession dating | Deficit above $1.5T annualized while unemployment is below 5% | above | 0.20 | Deficits normally widen IN recessions (automatic stabilizers + stimulus) and narrow DURING expansions (higher tax receipts + lower transfer payments). Running a $1.5T+ deficit during economic expansion is historically anomalous — it means the deficit is STRUCTURAL, not cyclical. A structural deficit cannot be resolved by growth alone because the deficit persists even when the economy is strong. This is the condition that separates "temporary fiscal concerns" from "arithmetic trap." |
| No credible deficit reduction plan | Web search: Congressional budget proposals, CBO long-term outlook, political analysis | Neither major party proposing deficit reduction that would bring deficit below $500B within 5 years | qualitative (scored as binary: 0 or triggered) | 0.10 | The political precondition for devaluation. Devaluation becomes the path of least resistance BECAUSE the alternatives (austerity, default) are politically unacceptable. If both parties are proposing tax cuts, spending increases, or both — and no credible bipartisan framework for deficit reduction exists — the political system has implicitly chosen devaluation even if no one says so. This indicator is qualitative but binary: either a credible plan exists or it doesn't. |
| Debt rollover at higher rates | Web search: Treasury refunding data, weighted average interest rate on federal debt | Weighted average interest rate on total federal debt rising AND below current market rates (meaning rollover still has room to push expense higher) | rising | 0.15 | The delayed fuse. The federal government has $35T+ in debt. Not all of it rolls over at once. The weighted average coupon on outstanding debt is still below the current market rate because much debt was issued during 2020-2021 at ultra-low rates. As that debt matures and rolls into current rates (~4.5%), interest expense rises MECHANICALLY even without any new borrowing. This is the auto-pilot dimension of the arithmetic — it gets worse every month without any policy action, simply through the passage of time. |
| Gold/oil ratio elevated | computed: `gold_oil_ratio` | Above 25 (vs. historical average of ~16-20) | above | 0.10 | Gromen's signature metric. The gold/oil ratio measures the monetary premium on gold relative to the most economically essential commodity. When gold buys more barrels of oil than the historical average, the market is assigning a monetary reserve premium to gold above its commodity value. This premium reflects expectations of currency debasement — gold is being priced as an alternative reserve asset, not just a commodity. The ratio was ~15 in the early 2000s (dollar strong, no fiscal concern), ~22 in 2019 (early fiscal concern), and above 28 currently (fiscal arithmetic anxiety). |
| Central bank gold purchases sustained | Web search: World Gold Council, IMF COFER data | Central bank gold buying above 800 tonnes/year for 2+ consecutive years | above | 0.05 | Confirmation that official institutions — the most conservative allocators in the world — are voting with their reserves. Sustained buying above 800 tonnes/year (vs. pre-2022 average of ~400-500 tonnes) indicates a structural shift in reserve composition, not a one-time adjustment. The buying is concentrated among non-allied central banks (China, India, Turkey, Poland, Singapore) who have the strongest incentive to diversify away from Treasuries after the 2022 Russia sanctions. This connects to `monetary_architecture` but confirms the fiscal arithmetic thesis independently: CBs are buying gold BECAUSE they see the arithmetic and don't trust the US to resolve it. |

**Activation scoring:**
- Weighted score ≥ 0.60 → **Active**
- Weighted score 0.30–0.59 → **Adjacent**
- Weighted score < 0.30 → **Inactive**

**Supplementary flags (qualitative — not scored mechanically):**

| Flag | Source | What to look for |
|------|--------|------------------|
| Treasury auction deterioration | Web search: Treasury auction results, bid-to-cover ratios, dealer takedowns | Declining bid-to-cover ratios, rising dealer takedowns (dealers forced to absorb supply the market won't), tail risk in auctions (auction clearing above when-issued yield). These are the bond market's real-time verdict on fiscal sustainability. A failed or severely distressed auction would be a regime-change event — extremely unlikely but existential if it occurs. |
| Foreign official Treasury holdings declining | Web search: Treasury International Capital (TIC) data, Fed custody holdings | Foreign central bank holdings of Treasuries declining as a percentage of total outstanding. Not dollar-weighted (total outstanding is growing, so flat holdings = declining share). If the marginal foreign buyer is stepping back, the domestic private market must absorb more supply, requiring higher yields = higher interest expense = the arithmetic worsens faster. |
| Petrodollar settlement diversification | Web search: energy trade settlement data, bilateral currency agreements | Oil and gas trade settled in non-dollar currencies (RMB, rupees, dirham). Each transaction that bypasses the dollar reduces structural dollar demand. This is slow-moving but directional. The 2023 Saudi-China RMB-settled oil sales, the India-Russia rupee-settled energy trade, and the UAE-India trade in rupees are all data points. Volume matters more than headlines. |

---

## core_mechanism

### Causal Chain

```
1. The US federal government has accumulated $35T+ in debt.
   This is the STOCK. It exists. It cannot be wished away.
   It must be serviced — interest payments are legally obligatory,
   senior to all other spending in practice (though not technically
   in statute).
   ↓
2. The weighted average interest rate on this debt is rising:
   Debt issued in 2020-2021 at ~1.5% coupons is maturing and
   rolling into current market rates (~4.5%).
   Each quarter, the effective interest rate on total debt ratchets
   higher as low-rate debt is replaced by high-rate debt.
   This process is AUTOMATIC — no policy action required.
   ↓
3. Interest expense is now $1.1T+ annualized and rising:
   This exceeds defense spending ($886B).
   It represents ~23% of federal tax receipts ($4.8T).
   It is the fastest-growing line item in the federal budget.
   Unlike discretionary spending, it cannot be "cut" without defaulting.
   ↓
4. The deficit is $2T+ annualized, DURING a non-recessionary economy:
   This means the deficit is STRUCTURAL, not cyclical.
   It will not shrink when the economy improves — the economy is
   already performing reasonably. It will WIDEN in a recession
   (automatic stabilizers + stimulus + lower tax receipts).
   ↓
5. Three mathematically possible resolutions exist:

   (a) AUSTERITY — cut spending and/or raise taxes enough to
       reduce the deficit below $500B:
       - Requires cutting $1.5T+ from the budget
       - Politically: would require cutting Social Security, Medicare,
         defense, or raising taxes dramatically
       - Neither party proposes this. Both propose expansions.
       - Historical precedent: no democracy with this debt/GDP ratio
         has voluntarily imposed austerity sufficient to resolve it
       - Probability assessment: <10% in the next decade

   (b) DEFAULT / RESTRUCTURING — fail to make interest payments:
       - Would destroy the Treasury market, the dollar's reserve status,
         and the global financial system that depends on both
       - The US has never defaulted (debt ceiling theatre excluded)
       - Would be catastrophic and irrational when option (c) exists
       - Probability assessment: <2% barring extreme political dysfunction

   (c) DEVALUATION — reduce the real value of the debt by allowing
       inflation to exceed the interest rate on the debt:
       - Every major sovereign in history at comparable debt levels
         has chosen this path
       - It is the path of LEAST political resistance because:
         · No explicit vote to "devalue" is taken
         · Inflation is diffuse — everyone pays a little, no one
           is specifically harmed enough to organize opposition
         · Nominal wages and nominal asset prices rise, masking
           the real wealth transfer from creditors to debtors
         · The government is the largest debtor — it benefits most
       - The mechanism: keep nominal interest rates below nominal GDP
         growth (and below inflation) for an extended period.
         The real debt burden shrinks each year by the gap between
         inflation and interest rates.
       - The 1940s-1950s template: 10 years of negative real rates
         reduced debt/GDP from 120% to 60% without nominal default.
       - Probability assessment: >80% over the next decade
   ↓
6. Devaluation produces specific asset price consequences:
   - Assets denominated in nominal dollars (Treasuries, corporate bonds,
     cash) lose REAL purchasing power even if their NOMINAL value
     is preserved. TLT pays its coupon, but the coupon buys less.
   - Assets with scarcity or replacement cost (gold, commodities,
     real estate, equities with pricing power) maintain or increase
     real value because their prices adjust upward with inflation.
   - The SPEED of devaluation matters:
     · Slow (2-4% sustained inflation, rates held below):
       Gradual real wealth transfer. Bond holders lose 2-3% real/year.
       Gold appreciates 5-10%/year. Equities deliver mediocre real returns
       but positive nominal. Most people don't notice.
     · Fast (6-10% inflation spike):
       Rapid repricing. TLT declines sharply. Gold surges 20-40%.
       Equities volatile (inflation hurts multiples but helps nominal
       earnings). Politically destabilizing — risks overcorrection.
   ↓
7. The petrodollar dimension accelerates the timeline:
   Dollar's reserve status partly rests on oil trade in dollars.
   Non-dollar energy settlement reduces structural dollar demand.
   Reduced demand → weaker dollar → imported inflation → worsens
   fiscal arithmetic (higher costs, possibly lower foreign buying
   of Treasuries). This is a SECONDARY mechanism — slower-moving
   than the domestic arithmetic but directionally reinforcing.
   ↓
8. The feedback loop:
   Devaluation worsens the arithmetic in the short run if rates
   stay high (higher inflation → Fed keeps rates elevated →
   higher interest expense on rolling debt). The loop only closes
   if the Fed ACCOMMODATES — keeps rates below inflation.
   This is the endgame: the Fed is forced to choose between
   fighting inflation (worsening the fiscal arithmetic) and
   accommodating inflation (enabling the devaluation).
   The fiscal arithmetic makes accommodation inevitable
   because the alternative (fighting inflation with higher rates)
   INCREASES the deficit through interest expense.
   This is the trap.
```

### The Arithmetic in Numbers

This section provides the specific math the generator should reference. All numbers are approximate as of early 2026 and will be updated by web search:

| Item | Value | Trajectory |
|------|-------|-----------|
| Total federal debt | ~$35.5T | Growing ~$2T/year |
| Annual interest expense | ~$1.1T | Rising as low-rate debt rolls |
| Annual tax receipts | ~$4.8T | Growing ~3-4%/year nominally |
| Interest / receipts | ~23% | Rising — the critical ratio |
| Defense spending | ~$886B | Growing ~3%/year |
| Social Security + Medicare | ~$2.4T | Growing ~5-6%/year (demographics) |
| Structural deficit | ~$2.0T | Cannot shrink without policy change |
| Weighted avg. interest rate on debt | ~3.3% | Rising toward market rates (~4.5%) |
| Implied interest expense at full rollover | ~$1.6T | If all debt repriced to current rates |

The last row is the delayed fuse: when all existing debt has rolled into current market rates, interest expense reaches ~$1.6T — 33% of current receipts. This is the arithmetic that makes the trajectory untenable even without any additional borrowing.

### Time Horizon

**Primary:** 3-10 years. The arithmetic plays out over the medium term. The rollover of low-rate debt to high-rate debt takes 5-7 years to complete (weighted average maturity of outstanding Treasuries is ~6 years). The devaluation trajectory is measured in years, not quarters.

**Secondary:** The asset price implications (hard assets vs. nominal bonds) begin pricing in immediately once the market recognizes the trajectory. Gold's move from $1,800 (2022) to $2,800+ (2025-2026) partially reflects this pre-pricing. The question is how much is already discounted.

**Distinction from `fiscal_dominance_liquidity`:** The liquidity module operates on 1-6 month horizons (net liquidity changes transmit to asset prices in days to weeks). This module operates on 3-10 year horizons (the debt trajectory determines the structural positioning). They can have different activation statuses: liquidity can be temporarily inactive (one quarter of deficit narrowing) while the arithmetic remains fully active (the stock of debt is unchanged, the rollover continues).

---

## predictions_when_active

### Directional

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| GLD | Structural outperformance | +8% to +20% annualized real | Rolling 3-5 years | Gold is the primary beneficiary of devaluation arithmetic. Three reinforcing channels: (1) inflation hedge as dollar purchasing power erodes, (2) reserve asset substitution as central banks diversify from Treasuries (structural floor under price), (3) monetary premium expansion as the gold/oil ratio rises above historical norms. Gold's outperformance is structural, not tactical — it persists as long as the arithmetic is untenable. |
| SLV | Outperform, lagging gold | +5% to +15% annualized | Rolling 3-5 years | Silver benefits from the same monetary premium channel as gold but with higher volatility and additional industrial demand (electrification, solar). Silver underperforms gold during the early phase of devaluation recognition and outperforms during the acceleration phase (higher beta). The gold/silver ratio is a useful internal indicator: above 80 = silver relatively cheap within the complex. |
| TLT | Structural underperformance in real terms | -2% to -8% annualized real return | Rolling 3-5 years | Long-duration nominal bonds are the primary VICTIM of devaluation. The coupon is fixed in nominal terms. Inflation erodes the real value of both coupon and principal. Additionally: rising term premium (market demanding compensation for holding duration in an uncertain fiscal environment) pressures prices independently of rate moves. TLT can deliver POSITIVE nominal returns if rates fall — but real returns will still be poor if inflation persists above the coupon rate. |
| TIP | Outperform TLT | +3% to +10% annualized relative | Rolling 3-5 years | TIPS protect the principal against CPI inflation. In a devaluation regime, TIPS preserve real value while nominal bonds lose it. The breakeven spread (TIPS yield vs. nominal yield) should widen as the market prices in sustained higher inflation. TIPS are the bond market's expression of the devaluation thesis. |
| DBC | Outperform nominal bonds | +5% to +15% annualized | Rolling 3-5 years | Commodities benefit from both the monetary premium channel (real assets hold value during devaluation) and the demand channel (fiscal spending on infrastructure, defense, energy subsidies supports commodity consumption). Commodities are noisier than gold (subject to supply/demand cycles) but directionally aligned. |
| UUP (Dollar) | Structural decline | -2% to -5% annualized on trade-weighted basis | Rolling 3-5 years | The dollar weakens structurally because: (a) fiscal profligacy reduces confidence in dollar-denominated claims, (b) non-dollar energy settlement reduces structural dollar demand, (c) central bank reserve diversification from Treasuries to gold reduces official dollar holdings. The decline is SLOW — not a crisis, not a collapse, but a persistent grind. The dollar can rally sharply on short-term dynamics (flight to safety, rate differentials) within the structural decline. |
| SPY | Mediocre real returns, positive nominal | +3% to +8% annualized nominal, 0% to +3% real | Rolling 3-5 years | Equities are mixed in a devaluation regime. Nominal earnings rise with inflation (revenue adjusts upward). But multiples compress because real discount rates are uncertain and inflation compresses PE ratios. Net: nominal returns are positive but real returns are mediocre. Equities with pricing power (XLP, XLV) and tangible assets (XLE, XLB) outperform. Long-duration growth equities (QQQ) underperform on a real basis. |
| IBIT | Outperform if adoption thesis holds | +15% to +40% annualized with ±30% drawdowns | Rolling 3-5 years | Bitcoin as devaluation hedge — fixed supply, outside government control, increasingly held by institutions. The thesis is contested: Bitcoin has NOT yet proven itself through a sustained devaluation regime (it didn't exist in the 1940s-1970s). Its correlation with risk assets during 2022 tightening weakened the "inflation hedge" narrative. Include with lower conviction than GLD. |

### Conditional (interaction with other theories)

| Condition | Prediction | Specificity Gain |
|-----------|-----------|-----------------|
| If `fiscal_dominance_liquidity` is also Active | Both the flow (net liquidity expansion) and the stock (debt arithmetic) are confirming simultaneously. Combined prediction: hard asset allocation should be at the UPPER END of suggested ranges (25-30% portfolio in GLD/SLV/DBC) because both the tactical signal (liquidity) and the structural signal (arithmetic) are aligned. The probability of the devaluation channel increases because the liquidity mechanism demonstrates that the fiscal engine is actively running, not just a future projection. | Cross-confirms the devaluation timeline. Liquidity active = the deficit is currently large and transmitting to asset prices. Arithmetic active = the cumulative result is untenable. Both together = the devaluation is both HAPPENING (in slow motion) and INEVITABLE (the math forces it). Sizing should reflect this double confirmation. |
| If `debt_cycle_short` is Active (Contraction) | A recession WORSENS the fiscal arithmetic dramatically. Tax receipts fall 10-15% (2009: receipts fell from $2.5T to $2.1T). Automatic stabilizers increase spending. The deficit widens by $500B-$1T above its structural level. Interest/receipts ratio spikes because the numerator stays constant (interest is obligatory) while the denominator shrinks (lower receipts). Prediction: GLD accelerates during recession (up 25%+ as markets price in the worsened arithmetic). TLT has a BRIEF rally on flight-to-quality (3-6 months) then resumes decline as the market recognizes the fiscal damage. The best trade: long GLD into recession, not long TLT. | The critical insight: recession is NOT good for bondholders in a fiscal dominance regime, despite the historical pattern. In previous recessions, TLT rallied because deficit widening was temporary and credible. In this regime, recession-driven deficit widening is PERMANENT (the structural deficit was already unsustainable). TLT rally is capped and short-lived. GLD is the better recession hedge when fiscal arithmetic is already untenable. |
| If `valuation_mean_reversion` is also Active | Valuation theory says "hold cash." Arithmetic theory says "cash loses purchasing power." The combination resolves by TIME HORIZON: cash (SHY) is correct for the 1-3 year horizon (earn 5% risk-free while waiting for the valuation correction). GLD is correct for the 3-10 year horizon (protect against devaluation). Combined expression: split the defensive allocation between SHY (near-term) and GLD (structural). A 50/50 SHY/GLD barbell captures both theories. | Resolves the apparent contradiction between the two theories by distinguishing time horizons. Produces a specific portfolio construction recommendation (SHY/GLD barbell) that neither theory alone would generate. |
| If `monetary_architecture` is also Active | The collateral substitution thesis (monetary architecture) provides the STRUCTURAL BACKDROP for the fiscal arithmetic. Central banks are buying gold BECAUSE they see the arithmetic. Their buying provides a structural floor under gold prices that makes GLD a lower-risk position than the arithmetic alone would justify. Prediction: GLD downside is limited to -10% to -15% even in adverse scenarios (dollar strengthening, risk-off) because central bank buying absorbs supply. The risk/reward is asymmetric in favor of GLD when both theories are active. | Provides a risk management insight: the downside for GLD is structurally limited by central bank buying. This changes the position sizing calculus — you can hold a larger GLD position with confidence that the floor is higher than a purely speculative gold position. |

---

## downstream_implications

### affects[]

| Target Theory | Relationship | Description |
|--------------|-------------|-------------|
| `fiscal_dominance_liquidity` | **reinforces** | The arithmetic provides the STRUCTURAL reason why the liquidity flow will persist. Deficits won't narrow voluntarily (no political will) and can't narrow through growth alone (structural deficit too large). Therefore the liquidity injection will continue. The arithmetic module gives the liquidity module its staying power — it's not a one-quarter phenomenon but a multi-year structural condition. |
| `debt_cycle_short` | **modifies** | The fiscal arithmetic changes how recessions affect bonds. In a normal debt cycle, recession → TLT rally (flight to quality, rate cut expectations). When the fiscal arithmetic is untenable, recession → fiscal arithmetic WORSENS → TLT rally is capped and short-lived. The evaluator should flag any hypothesis that predicts a sustained multi-year bond bull market during recession when this theory is Active. |
| `monetary_architecture` | **reinforces** | The domestic fiscal arithmetic is the DEMAND-SIDE driver of the collateral substitution that monetary architecture describes. Central banks are diversifying from Treasuries to gold because they see the arithmetic. The US fiscal trajectory is the proximate cause of the Bretton Woods III transition. Without fiscal concerns, the incentive to diversify reserves is much weaker. |
| `valuation_mean_reversion` | **modifies** | The fiscal arithmetic changes the likely resolution channel for valuation mean reversion. Instead of resolution via price crash (the historical default), fiscal dominance biases toward resolution via inflationary grind — nominal prices stay elevated while inflation erodes real value. The evaluator should check: when both theories are active, is the generator predicting the right resolution channel? |

---

## falsifiers

### Hard Falsifiers

These conditions, if met, indicate that the fiscal arithmetic devaluation mechanism is NOT the dominant trajectory.

| # | Condition | Metric | Threshold | Rationale |
|---|-----------|--------|-----------|-----------|
| H1 | Genuine fiscal consolidation sustained | Web search: US Treasury monthly statements, CBO | Deficit falls below $800B annualized for 4+ consecutive quarters through actual spending cuts or tax increases (not one-time items, accounting changes, or April tax-receipt lump sums) | If the government demonstrates sustained ability to reduce the deficit below the level where arithmetic pressure builds, the "no political will" assumption is falsified. The 4-quarter requirement eliminates seasonal noise and one-off adjustments. $800B is the threshold where interest expense growth can plausibly be managed through GDP growth. This has not occurred since the late 1990s surplus (driven by the dot-com boom + defense cuts + capital gains tax windfalls — an unrepeatable combination). |
| H2 | Interest/receipts ratio declines below 15% for 4+ quarters | Web search: CBO, Treasury data | Interest expense as % of tax receipts falls below 15% sustained for 4 quarters | If the critical ratio improves materially — through some combination of lower rates, faster revenue growth, or slower debt accumulation — the arithmetic pressure eases. Below 15% is manageable by historical standards (the ratio was ~10-12% during the 2010s). The improvement must be sustained, not a one-quarter artifact of tax deadline receipts. |
| H3 | Productivity-driven GDP growth above 4% real sustained for 3+ years | `growth.gdp_latest` (real) | Real GDP growth above 4% annualized for 12+ consecutive quarters | If a genuine productivity revolution (AI or otherwise) drives sustained 4%+ real growth, tax receipts grow faster than interest expense, and the arithmetic improves organically. This would be historically extraordinary — the US has not sustained 4%+ real growth for 12 quarters since the 1960s. But it is theoretically possible and would represent the "grow out of the debt" scenario. If it occurs, the devaluation prediction is materially weakened because the denominator (GDP, receipts) is growing fast enough to manage the numerator (debt, interest). |
| H4 | Gold underperforms SHY for 5+ consecutive years while arithmetic indicators are triggered | GLD total return vs. SHY total return | GLD trails SHY for 5+ consecutive calendar years during a period when interest/receipts is above 20% | This is a falsifier of the TRADE EXPRESSION, not of the underlying arithmetic. It tests "is GLD the right implementation?" rather than "is the debt arithmetic problem real?" The arithmetic can be untenable AND gold can still be the wrong vehicle — because the dollar retains reserve status longer than expected, because real rates stay positive and punish zero-yield assets, or because the devaluation transmits through channels that gold doesn't capture. 5 years is sufficient to rule out short-term noise (dollar rallies, positioning, risk-off episodes). If GLD fails to outperform cash over a 5-year window while the arithmetic indicators are clearly triggered, the correct response is to re-examine the expression (perhaps TIPS, commodities, or equities with pricing power are the better vehicle) — not necessarily to abandon the fiscal arithmetic diagnosis. That said, if the theory cannot produce a working trade, its utility for portfolio construction is zero regardless of its intellectual validity. |

### Soft Falsifiers

| # | Condition | Metric | Threshold | Implication | Severity |
|---|-----------|--------|-----------|-------------|----------|
| S1 | Dollar strengthening despite fiscal deterioration | `DX-Y.NYB` (DXY) or `UUP` | DXY rises 3%+ over trailing 2 months while interest/receipts ratio is above 20% | The dollar CAN strengthen even when the arithmetic is terrible — flight to safety, relative weakness in other currencies (Europe and Japan have their own fiscal problems), or US growth exceptionalism. A strong dollar dampens the devaluation transmission: imported goods are cheaper, inflation moderates, commodity prices in dollars fall. The GLD and DBC predictions weaken. The arithmetic is unchanged but the MARKET EXPRESSION is impaired. | **medium** — weakens the market expression (gold, commodities) without changing the underlying arithmetic. The devaluation trajectory is unchanged; the timeline extends because a strong dollar delays the inflation transmission. |
| S2 | Rates decline substantially (Fed cutting to below 3%) | `rates.fed_funds` | Fed funds rate falls below 3.25% OR market-implied terminal rate (18-month OIS) falls below 3.0% | Lower rates directly reduce the interest expense on floating-rate and short-duration debt. The rollover arithmetic improves because new issuance carries a lower coupon. Interest/receipts ratio declines. The arithmetic pressure eases — NOT because the debt shrank, but because the cost of carrying it declined. The devaluation timeline extends. However: if rates fell because of recession, the receipts side also deteriorates, partially offsetting the interest expense improvement. | **major** — directly caps the predicted interest expense trajectory. If rates fall to 3%, the "all debt rolls into 4.5% coupons" scenario doesn't materialize. Interest expense at full rollover drops from $1.6T to ~$1.05T. The arithmetic is still concerning but no longer at the "untenable" threshold. |
| S3 | Petrodollar system stabilizes or reverses | Web search: energy trade settlement data | No new bilateral non-dollar energy settlement agreements announced for 3+ months AND existing non-dollar settlement volume flat or declining per latest data | The petrodollar dimension is SECONDARY to the domestic arithmetic. If petrodollar diversification stalls or reverses, it removes one accelerant but doesn't affect the core domestic mechanism (interest expense trajectory). The dollar weakening prediction loses one source of pressure. Gold's monetary premium from reserve diversification is partially reduced. | **minor** — the petrodollar dimension extends the timeline but is not the primary mechanism. Domestic arithmetic alone is sufficient to sustain the theory. Removing the petrodollar accelerant changes the speed, not the direction. |
| S4 | Inflation falls below 2% sustained | `inflation.cpi_yoy` | Core PCE below 2.0% for 2 consecutive months | Low inflation undermines the devaluation channel. If inflation is below the interest rate on debt, real debt burden is NOT declining — it may even be increasing. The "inflate away the debt" mechanism requires inflation ABOVE the interest rate on the debt. Below-2% inflation means the devaluation is not occurring and the arithmetic continues to worsen in real terms. This is actually the WORST outcome for fiscal sustainability — low inflation + high rates = maximum real interest expense. The devaluation prediction is weakened, but the fiscal crisis prediction may be STRENGTHENED (the non-devaluation path leads to a harder endpoint). | **medium** — weakens the devaluation prediction specifically but may strengthen the broader fiscal crisis thesis. The mechanism (devaluation as resolution) is impaired, but the problem (unsustainable arithmetic) persists or worsens. The trade expression changes: less GLD, more crisis hedges. |
| S5 | Tax receipts grow faster than interest expense for 4+ quarters | Web search: Treasury receipts data vs. interest expense | Monthly Treasury receipts YoY growth exceeds interest expense YoY growth for 2+ consecutive months | The arithmetic is improving at the margin — the critical ratio stabilizes or declines. Possible drivers: strong economy, bracket creep from inflation, capital gains from rising markets. Doesn't resolve the stock problem (debt is still $35T+) but eases the flow pressure. Timeline for devaluation extends. | **minor** — extends the timeline without changing the structural diagnosis. Receipts growing faster than interest expense slows the deterioration but doesn't reverse it unless sustained for many years (connecting to H3). |

| S6 | Primary predicted asset moves 15%+ against the hypothesis direction within the hypothesis holding window, without a corresponding fundamental falsifier triggering | Price of primary `predicted_assets` ticker(s) | 15% adverse move from hypothesis entry point within stated timeframe | The market is pricing information the hypothesis mechanism does not capture. Either the mechanism is wrong, the timeframe is wrong, or an unmodeled force is dominant. Does NOT automatically invalidate the mechanism — forced liquidations, positioning squeezes, and liquidity events can produce temporary adverse moves that reverse. But the hypothesis must explain the adverse move or accept the discount. | **medium** |

---

## metadata

```json
{
  "theory_id": "fiscal_dominance_arithmetic",
  "version": 1,
  "last_updated": "2026-03-30",
  "update_type": "refinement",
  "confidence_in_specification": "medium-high",
  "notes": "The arithmetic is the most mechanically certain component of the entire theory registry — the numbers are public, the trajectory is computable, and the rollover math is deterministic. What is UNCERTAIN is the resolution channel: devaluation is assessed as >80% probability but the timeline, speed, and market expression are genuinely uncertain. The gold/oil ratio indicator is Gromen-specific and less historically tested than the core fiscal metrics. The petrodollar dimension is directionally correct but slow-moving and difficult to measure precisely (non-dollar trade settlement data is incomplete and lagged). The interaction with interest rates is the key sensitivity: if the Fed cuts to 2-3%, the arithmetic pressure eases substantially (soft falsifier S2 is major severity) — but rate cuts typically coincide with recession, which worsens receipts. Severity calibrations: S1 (dollar strength) is medium because the expression is impaired but the arithmetic isn't; S2 (rate cuts) is major because it directly caps the interest expense trajectory; S3 (petrodollar) is minor because it's secondary; S4 (low inflation) is medium because it weakens the devaluation channel specifically; S5 (receipts outgrowing interest) is minor because it extends timeline only. Added price action soft falsifier (medium severity, 0.25 discount) to close the gap where adverse price action was not captured by any pre-registered falsifier, forcing the LLM elimination pass to freelance on status assignment. The 15% threshold is calibrated above normal ETF monthly ranges (3-8%) to avoid triggering on noise.",
  "historical_episodes_referenced": [
    "1942-1951 US financial repression (debt/GDP peaked at 120%, resolved via sustained negative real rates, CPI 8-14% with rates capped at 2.5%. Debt/GDP halved to ~60% by 1960 without nominal default. The template for devaluation as resolution.)",
    "1946-1974 UK post-war fiscal dominance (debt/GDP 250% at peak, resolved via 30 years of sustained negative real rates and periodic sterling devaluations. GBP lost ~75% of purchasing power. Gilt holders suffered decades of negative real returns. The most extended devaluation episode by a major sovereign.)",
    "1970s US stagflation (fiscal deficits + oil shock + loose monetary policy. Federal debt/GDP only ~35% — much lower than today. Gold rose from $35 to $850 (24x). TLT equivalent lost ~40% of real value. Despite much lower debt levels, the fiscal-inflation dynamic produced dramatic hard asset outperformance.)",
    "2020-present US fiscal expansion ($5T COVID stimulus, followed by IRA + CHIPS + infrastructure. Deficit $2T+ during non-recession. Interest expense crossed $1T in 2024, surpassing defense spending. The current episode — the arithmetic trap is actively forming.)",
    "Brazil 1990s-2000s, Turkey 2010s-2020s, Argentina persistent (EM precedents where fiscal arithmetic forced devaluation. More extreme than the US trajectory but same mechanism: interest expense exceeds capacity to service → currency devalues → hard assets outperform nominal claims. The US has more room because of dollar reserve status, but the direction is the same.)"
  ]
}
```

---

## Usage Notes for Generator and Evaluator

### For the Generator

When this theory is Active, generate hypotheses about:

- **The specific arithmetic.** State the current numbers: total debt, annual interest expense, tax receipts, interest/receipts ratio, defense spending comparison, weighted average coupon vs. market rate. The strength of this theory is its mathematical specificity — every claim should be grounded in the numbers, not in narrative. The numbers are available via web search (Treasury monthly statements, CBO reports).

- **Which resolution channel is most likely and at what speed.** Devaluation is the central prediction, but the SPEED matters for portfolio construction. Slow devaluation (2-4% sustained inflation) favors a patient GLD/TIP position. Fast devaluation (6-10% inflation spike) favors larger GLD allocation plus commodity exposure (DBC, XLE). The speed depends on whether the Fed accommodates or fights — generate hypotheses about Fed behavior.

- **The rollover arithmetic.** Compute what interest expense will be when all existing debt has rolled into current market rates. This is deterministic given the maturity profile and current rates. It tells you where the arithmetic is GOING, not just where it is now. The trajectory is as important as the current level.

- **Interaction with the liquidity module.** If `fiscal_dominance_liquidity` is also Active, the flow and stock are both confirming. State this explicitly and explain why the dual confirmation justifies higher conviction and sizing in hard asset positions.

- **The gold/oil ratio.** If the ratio is elevated (above 25), explain what the monetary premium implies. If the ratio is near historical average (16-20), note that the market has NOT yet priced the devaluation thesis — which is either a buying opportunity or evidence that the thesis is wrong.

**What NOT to claim:**

- Do NOT predict a dollar collapse or hyperinflation. The theory predicts GRADUAL devaluation, not a crisis event. The dollar retains reserve status throughout — it just buys less over time. Hyperinflation predictions are not supported by this framework (the US has too many institutional buffers: independent Fed, deep capital markets, rule of law, military power backing reserve status).
- Do NOT claim this theory predicts TIMING of devaluation acceleration. The arithmetic is deterministic but the MARKET'S RECOGNITION of the arithmetic is not. Gold can lag for years before the market prices in the trajectory. The theory supports structural positioning, not tactical timing.
- Do NOT confuse this with `fiscal_dominance_liquidity`. If your hypothesis is about quarterly net liquidity changes and asset price correlation, you're using the wrong module. This module is about the multi-year trajectory of debt sustainability. Check which module your claim actually derives from.
- Do NOT ignore the rate sensitivity. If the Fed cuts to 2-3%, the arithmetic pressure eases substantially (soft falsifier S2). The generator must address the rate path when producing devaluation hypotheses. "Interest expense is unsustainable" is only true at CURRENT rates — if rates fall, the claim weakens.

### For the Evaluator

Priority checks:

1. **Did the generator state the specific numbers?** This theory is mathematical. Reject any hypothesis that claims "the fiscal situation is unsustainable" without citing the current interest/receipts ratio, deficit pace, and rollover math. Vague fiscal doom is not a testable hypothesis.

2. **Did the generator distinguish this from the liquidity module?** If the hypothesis is about quarterly asset price direction driven by net liquidity, it belongs under `fiscal_dominance_liquidity`, not this module. This module produces STRUCTURAL positioning hypotheses (hard assets over nominal bonds over multi-year horizons), not TACTICAL ones.

3. **Did the generator address the rate path?** The arithmetic is highly rate-sensitive. A hypothesis that claims "interest expense will reach $1.6T" assumes rates stay at current levels. If the Fed is cutting (or expected to cut), the generator must adjust the arithmetic accordingly. Check that the interest expense projection is consistent with the rate assumptions.

4. **Is the generator claiming timing?** This theory does not predict WHEN the market fully prices devaluation. It predicts the TRAJECTORY. A hypothesis that claims "gold will rally 30% in Q3 because the arithmetic is untenable" is overspecified on timing. The theory supports "gold is structurally undervalued relative to the fiscal trajectory" — a positioning claim, not a timing claim.

5. **Is the gold prediction bounded?** Check hard falsifier H4. Note that H4 tests whether GLD is the right implementation of the thesis, not whether the arithmetic problem is real. If gold has underperformed SHY for an extended period while the arithmetic indicators are triggered, the evaluator should flag the trade expression as suspect and prompt the generator to consider alternative vehicles (TIP, DBC, XLE) — while separately assessing whether the underlying arithmetic diagnosis remains valid.

6. **Composition quality check.** The most valuable compositions pair this module with `fiscal_dominance_liquidity` (flow + stock confirmation), `valuation_mean_reversion` (resolving the cash vs. gold tension by time horizon), or `debt_cycle_short` contraction (recession worsens the arithmetic, making GLD the preferred recession hedge over TLT). If the composition doesn't produce a more specific sizing, timing, or expression recommendation than this module alone, it's not adding value.
