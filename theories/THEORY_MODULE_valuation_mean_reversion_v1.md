# Theory Module: Valuation Mean Reversion & Margin of Safety

*Version 1.0 — March 2026*
*Status: Prototype — thresholds calibrated against every major US equity valuation cycle since 1900, with primary emphasis on 1929, 1968-72, 1999-2000, 2007, and 2021-present. Pending live testing.*

---

## theory_id

`valuation_mean_reversion`

---

## activation_conditions

This is a single-phase theory. When active, equity valuations are stretched beyond levels that the arithmetic of future returns can support. The mechanism is mathematical: paying a high multiple borrows returns from the future. The implication is NOT "sell everything now" — it is "forward real returns are poor, opportunity cost of equity exposure is high, and the magnitude of any drawdown triggered by OTHER mechanisms will be amplified."

This theory does NOT predict WHEN the correction happens. It predicts the MAGNITUDE conditional on a catalyst arriving, and the OPPORTUNITY COST of holding equities versus alternatives in the interim.

| Indicator | Metric Source | Threshold | Direction | Weight | Rationale |
|-----------|--------------|-----------|-----------|--------|-----------|
| Equity risk premium compressed | computed: `equity_risk_premium` (SPY earnings yield − 10Y yield) | Below 1.0% | below | 0.25 | The single most important valuation metric for an allocator. When the earnings yield on equities barely exceeds the risk-free rate, equities offer negligible compensation for bearing equity risk. Below 1.0% = the marginal rational allocator has almost no incentive to hold equities over Treasuries. Below 0% = equities offer NEGATIVE premium, meaning you are PAYING for the privilege of bearing equity risk. Historical precedent: ERP was negative in 1999-2000 (−1.2% at the peak) and in late 2021 (briefly negative). Both preceded major drawdowns. The 2024-2025 ERP has been near zero. |
| Shiller CAPE elevated | web search: Shiller CAPE ratio | Above 30 | above | 0.20 | The cyclically adjusted price-to-earnings ratio smooths earnings over 10 years, removing cyclical distortion. CAPE above 30 has occurred only four times: 1929 (32), 1999-2000 (44), 2021 (38), and 2024-present (36+). Forward 10-year real returns from CAPE above 30 have averaged approximately 1-3% annualized — not negative, but dramatically below the long-term average of 6-7%. The historical average CAPE is 17. Above 30 is nearly 2x the average. |
| Buffett Indicator extreme | web search: total US market cap / GDP | Above 1.5x | above | 0.15 | Market cap relative to GDP measures aggregate equity pricing against economic output. Above 1.5x has occurred only in 1999-2000 (1.6x), 2021 (2.0x), and 2024-present (1.8x+). The mechanism: GDP is a rough proxy for aggregate revenue. Market cap / GDP therefore approximates a price-to-sales ratio for the entire economy. Above 1.5x implies either permanently elevated profit margins OR speculative pricing of growth that doesn't yet exist in revenue. |
| Short-term cash yield exceeds earnings yield | `rates.fed_funds` or SHY yield vs. SPY earnings yield | SHY yield > SPY earnings yield (1/PE) | above | 0.15 | When cash pays more than equities YIELD, the opportunity cost argument for equities collapses. You earn more per year from SHY than from SPY's earnings yield, without equity risk. This is the simplest expression of the margin of safety concept: there is no margin of safety when the risk-free alternative pays more. Threshold is binary: when cash yield exceeds earnings yield, this indicator is triggered. |
| Corporate profit margins at cycle highs | web search: S&P 500 net profit margin, FRED corporate profits / GDP | Net margins above 12% OR corporate profits / GDP above 10% | above | 0.10 | Profit margins mean-revert. Current cycle highs (~12-13% net margins for S&P 500) are well above the historical average (~8-9%). Multiples applied to above-average margins produce DOUBLE overvaluation: you are paying a high multiple on earnings that are themselves elevated. When margins revert, the effective PE ratio on normalized earnings is much higher than the reported PE. This is the valuation trap — reported PE looks 22x but normalized PE is 28-30x. |
| Market breadth narrow | computed: `qqq_iwm_ratio` + RSP vs SPY relative performance | QQQ/IWM ratio above 2-year high AND RSP underperforming SPY by 5%+ over 12 months | diverging | 0.10 | Narrow breadth means the index-level valuation is driven by a small number of stocks. The "market" PE is really the PE of 7-10 mega-cap names. The average stock is cheaper. This matters because: (a) the index is more fragile — concentrated names declining has outsized index impact (connecting to `structural_fragility`), and (b) sector rotation may offer value even when the aggregate is expensive. This indicator activates the sectoral depth analysis below. |
| Insider selling elevated | web search: SEC insider transactions, insider buy/sell ratio | Insider sell/buy ratio above 5:1 sustained for 3+ months | above | 0.05 | Corporate insiders have the best information about their own companies. When insiders are systematically selling at elevated ratios, they are expressing the view that current prices exceed their assessment of intrinsic value. Not a strong standalone signal (insiders sell for many reasons — diversification, taxes, planned programs) but confirming evidence when combined with other valuation indicators. |

**Activation scoring:**
- Weighted score ≥ 0.60 → **Active**
- Weighted score 0.30–0.59 → **Adjacent**
- Weighted score < 0.30 → **Inactive**

**Supplementary flags (qualitative — not scored mechanically):**

| Flag | Source | What to look for |
|------|--------|------------------|
| "New paradigm" narratives dominant | Web search: financial media, investment commentary | Widespread arguments that traditional valuation metrics "don't apply" due to structural changes (AI productivity, platform monopolies, intangible assets). Every valuation extreme in history has been accompanied by compelling-sounding arguments for why this time is different. The narratives are always partially true — and always insufficient to justify the multiple. |
| Retail participation surging | Web search: brokerage account openings, options volume, meme stock activity | Retail investors entering late in the cycle tend to be the least price-sensitive and the most momentum-driven buyers. Their participation elevates valuations further AND creates a pool of weak holders who sell at the first sign of trouble. |
| Berkshire cash position extreme | Web search: Berkshire Hathaway cash holdings, latest 10-Q | Buffett's cash position is itself a valuation indicator. When Berkshire cash exceeds $200B and Buffett is a net seller of equities, the most disciplined capital allocator in history is telling you the market is expensive. As of early 2026, Berkshire cash exceeds $300B. |

---

## core_mechanism

### Causal Chain

```
1. Asset prices rise over an extended period, driven by some combination of:
   earnings growth, multiple expansion, passive inflows, momentum,
   and narrative (currently: AI productivity revolution).
   ↓
2. The PRICE of the asset detaches from the CASH FLOW it generates.
   Measured by: PE expansion, CAPE rising above 30, ERP compressing
   toward zero, Buffett Indicator exceeding 1.5x.
   This is not a mystery — it is arithmetic:
   price = earnings × multiple. If price rises faster than earnings,
   the multiple expands. A higher multiple means you are paying more
   per dollar of earnings. More dollars paid per dollar of earnings =
   lower forward returns, mechanically.
   ↓
3. The opportunity cost of equity ownership becomes measurable:
   When SHY yields 4.5-5% and the S&P earnings yield is 4.0-4.5%,
   the RISK-FREE alternative pays as much or more than the RISKY asset.
   A rational allocator allocating fresh capital should prefer SHY.
   The only argument for equities at this point is GROWTH — equities
   will grow earnings and cash will not. But: the growth must be
   sufficient to compensate for the valuation premium. At CAPE 36,
   the implied real equity return is ~2.8% (1/36). If risk-free
   real return is 2%+ (10Y yield minus breakevens), equities
   offer <1% premium for substantially more risk.
   ↓
4. This state CAN PERSIST FOR YEARS. The mechanism does not predict
   timing. Valuations were extreme from 1997-2000 (3 years before
   resolution). Valuations were extreme from 2020-present (5+ years
   and counting). The persistence is driven by:
   (a) momentum and passive inflows creating buyer regardless of price
   (b) FOMO — career risk of being out of the market when it rises
   (c) narratives justifying the multiple ("AI will transform everything")
   (d) fiscal liquidity (connecting to fiscal_dominance_liquidity) providing
       a continuous bid under assets regardless of valuation
   ↓
5. Resolution arrives through one of three channels:

   (a) PRICE DECLINE (most common):
       A catalyst (recession, credit event, earnings miss, exogenous shock)
       causes repricing. The drawdown magnitude is proportional to the
       valuation excess: from CAPE 36, a reversion to CAPE 25 = -30%.
       To CAPE 20 = -44%. To CAPE 17 (historical average) = -53%.
       The catalyst determines WHEN. The valuation determines HOW FAR.

   (b) EARNINGS GROWTH (the soft landing):
       Earnings grow fast enough that the multiple normalizes without
       price decline. At CAPE 36, earnings must grow ~70% to bring
       CAPE to 21 without any price decline. This requires either
       a productivity revolution or substantial inflation (nominal
       earnings grow but real multiple compression happens via
       inflation — the 1970s outcome). Takes 5-10 years.

   (c) INFLATIONARY GRIND (the fiscal dominance resolution):
       Nominal prices tread water or rise slowly while inflation
       erodes real value. The multiple compresses in REAL terms
       without a nominal crash. Forward real returns are 0-2%
       for a decade. Investors don't "lose money" nominally but
       lose purchasing power. This is the resolution predicted
       when fiscal_dominance_liquidity is also Active.
   ↓
6. Post-resolution, the equity risk premium is restored:
   Either through lower prices (channel a), higher earnings (b),
   or lower real values (c). The ERP widens back to 3-5%,
   CAPE falls to 15-22, and forward returns are attractive again.
   This is the DEPLOYMENT signal — when the mechanism resolves,
   Buffett deploys cash. March 2020 (CAPE briefly at 24) is the template.
```

### Sectoral Valuation Depth

The market-level valuation filter is necessary but insufficient. Even in expensive markets, individual sectors rotate through periods of temporary distress. The margin of safety framework applies at the sector level:

**Financials (XLF, KBE, KRE):**
- Primary metric: Price-to-Tangible-Book Value (P/TBV)
- Threshold: Below 1.0x P/TBV = interesting. Below 0.8x in a non-systemic crisis = compelling.
- Mechanism: Banks are leveraged balance sheets with spread income. TBV is the liquidation value floor. Below 1.0x means the market is pricing loan losses that exceed tangible equity — either justified (systemic risk) or overreaction (temporary credit stress).
- Key diagnostic: Is the crisis temporary (credit losses that normalize in 2-3 years) or permanent (business model impairment from regulation or technology)? Regional bank stress in 2023 (KRE -35%) was temporary. Money-center bank stress in 2008 was systemic.
- Current relevance: If rates stay elevated, bank net interest margins expand, supporting TBV. KRE below 0.8x TBV during a non-systemic stress event = high conviction buy.

**Energy (XLE, XOP):**
- Primary metric: EV/EBITDA relative to replacement cost of reserves, sector weight in S&P 500
- Threshold: XLE at or below 4% of S&P 500 weight = historically extreme underweight. EV/EBITDA below 5x = below replacement cost.
- Mechanism: Energy is cyclical but essential. Oil is not going away on any relevant investment horizon. At minimum S&P weight + below replacement cost, you are buying productive assets for less than it would cost to build them. Cash flows are real and current, not hypothetical future revenue.
- Key diagnostic: Is the underweight cyclical (oil price downturn) or structural (energy transition permanently reducing fossil fuel value)? Current view: cyclical underweight within a structural transition that will take decades, not years.

**Healthcare (XLV, XBI):**
- Primary metric: P/E relative to S&P 500 average, P/E relative to own 10-year average
- Threshold: XLV P/E discount to SPY exceeding 30%. XBI below 0.6x its 5-year average P/S.
- Mechanism: Aging demographics provide structural revenue tailwind. Political risk (drug pricing legislation) creates temporary discounts that overshoot because the legislation is typically narrower than feared. Biotech specifically: after pipeline failures or regulatory crackdowns create indiscriminate selling, the sector trades below the value of approved drugs alone (optionality on pipeline is priced at zero).

**Consumer Staples (XLP):**
- Primary metric: P/E, dividend yield
- Threshold: P/E below 18 with dividend yield above 2.8% = fair value. P/E below 15 = rare and attractive.
- Mechanism: Durable moats, predictable cash flows, pricing power over inflation. Rarely cheap enough to be exciting — the market correctly prices stability. Interesting primarily as a safe harbor when everything else is expensive. XLP at 15x when SPY is at 24x = meaningful relative value.

**Small Caps (IWM, MDY):**
- Primary metric: IWM P/E discount to SPY, Russell 2000 P/B ratio
- Threshold: IWM P/E discount to SPY exceeding 30% = historical extreme. Russell 2000 P/B below 1.8x = attractive on asset basis.
- Mechanism: Small caps are more exposed to the domestic economy and credit conditions. They benefit disproportionately from rate cuts (more floating-rate debt). When the valuation gap to large caps is at extremes, mean reversion is likely — but requires a catalyst (rate cuts, credit easing, or large-cap correction).

**International Value (EFA, VGK):**
- Primary metric: Relative P/E (MSCI EAFE P/E vs. S&P 500 P/E), US premium as percentage
- Threshold: US P/E premium over EAFE exceeding 50% (e.g., SPY at 22x, EFA at 14x) = extreme.
- Mechanism: The US premium reflects genuine quality differences (higher margins, more tech exposure, better governance) but overshoots. At 50%+ premium, the arithmetic of lower starting multiples favors international. Europe (VGK) at 12-13x when US is at 22-24x = the forward return gap is 3-5% annualized in international's favor, purely from multiple normalization.

### Time Horizon

**This is the longest-horizon theory in the registry.**

- **Forward return prediction:** 7-12 years. CAPE is a poor 1-year predictor but an excellent 10-year predictor. R² of CAPE vs. forward 10-year real return is approximately 0.80 historically.
- **Drawdown magnitude prediction:** Conditional on catalyst. When the catalyst arrives (from another theory), valuation determines the depth. This can be immediately relevant.
- **Sectoral rotation:** 1-3 years. Sector-level valuations mean-revert faster than market-level because catalysts are more frequent (earnings cycles, regulatory changes, oil price moves).
- **Opportunity cost:** Continuous. As long as ERP is compressed, the opportunity cost of equity exposure versus cash/short duration is quantifiable and ongoing.

**Critical implication:** This theory should NOT produce hypotheses about what happens next quarter. It produces hypotheses about the risk/reward of current equity positioning and the magnitude of any correction that other theories might predict.

---

## predictions_when_active

### Directional

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| SPY | Forward real returns poor | +0% to +4% annualized real return | Next 7-10 years | The arithmetic of high CAPE. From CAPE 36, the implied forward real return is approximately 2.8% (1/CAPE). This is well below the historical average of 6-7%. Not a timing call — a RETURN EXPECTATION call. |
| SPY | Drawdown magnitude elevated when catalyst arrives | -25% to -50% peak-to-trough | Conditional on catalyst from another theory | The valuation excess determines the distance from current price to "fair value." From CAPE 36 to CAPE 22 (still above average) = -39%. From current ERP near 0% to ERP of 3% (adequate) requires either price decline, rate decline, or earnings surge. Price decline is the fastest adjustment mechanism. |
| SHY | Outperform SPY on risk-adjusted basis | +4% to +5.5% annualized, zero drawdown risk | While ERP is below 1% | When cash yields more than the equity earnings yield, cash is the superior risk-adjusted holding. Not forever — only while the ERP is compressed. Buffett's cash position IS this trade: earn 5% risk-free while waiting for valuations to normalize. |
| TLT | Conditional on resolution channel | Varies — see conditional predictions | — | If resolution is deflationary crash: TLT rallies +20-30%. If resolution is inflationary grind: TLT declines further. Valuation theory alone does NOT predict the resolution channel — that depends on the interaction with fiscal dominance and debt cycle theories. |
| GLD | Benefits from inflationary resolution channel | +10% to +25% per year if resolution is inflationary | 3-10 years | If valuation excess resolves through inflation (channel c in causal chain), gold benefits as the real value of equities and bonds erodes. Gold preserves purchasing power when nominal assets deliver negative real returns. |
| Sector-level opportunities | Outperform broad index | +5% to +15% annualized relative to SPY | 1-3 years | Even in expensive markets, sectors at relative valuation extremes offer rotation alpha. The specific sectors depend on current conditions — see sectoral depth section. This is the practical edge of valuation theory: you don't have to sit entirely in cash. You can rotate from expensive sectors to cheap sectors within equities. |
| EFA, VGK | Outperform SPY on relative basis | +3% to +7% annualized relative over 5 years | When US premium exceeds 50% | Multiple compression in the US + multiple stability or expansion internationally = international outperformance. Doesn't require international economies to be strong — just requires the US premium to normalize partially. |
| IWM | Outperform QQQ on relative basis | +5% to +10% annualized relative | When IWM P/E discount to SPY exceeds 30% | Valuation gap mean reversion. Requires a catalyst (rate cuts, credit easing, large-cap disappointment). The gap is the setup; the catalyst comes from other theories. |

### Conditional (interaction with other theories)

| Condition | Prediction | Specificity Gain |
|-----------|-----------|-----------------|
| If `structural_fragility` is Active (Building) | Valuation excess + fragility buildup = the MAGNITUDE of the eventual drawdown is at the maximum end of the range (-35% to -50%). Fragility determines the mechanism of the break (forced selling, passive unwind, leverage cascade). Valuation determines the distance to travel (CAPE 36 to CAPE 18 = -50%). Combined: the break is both DEEP and VIOLENT. Expression: maximum defensive positioning — SHY overweight, GLD as tail hedge, reduce concentrated equity exposure (QQQ underweight). | Narrows the magnitude estimate. Valuation theory alone says -25% to -50% (wide range). Adding fragility says the break mechanism will be amplified (forced selling overshoots fundamental fair value). The combined estimate tightens to -35% to -50%. |
| If `fiscal_dominance_liquidity` is Active | Valuation mean reversion is DELAYED because fiscal liquidity injection provides a continuous bid under equities. The mechanism: net liquidity expansion → excess reserves → bid for risk assets → equities stay expensive longer than pure valuation theory predicts. Prediction: ERP stays compressed for 2-5 additional years beyond what valuation timing models suggest. But: the resolution channel shifts from (a) price decline to (c) inflationary grind — nominal prices tread water while inflation erodes real value. GLD outperforms SPY on a real basis even without a nominal crash. | The critical insight: fiscal dominance doesn't invalidate valuation theory — it changes the CHANNEL of resolution. Instead of "wait for the crash, then deploy cash," the prediction becomes "real returns will be poor for years while nominal prices stay elevated." This changes the TRADE: from SHY (waiting for crash) to GLD/TIP (protecting against real value erosion). |
| If `debt_cycle_short` is Active (Contraction) | Valuation excess + cycle contraction = the correction arrives via price decline (channel a). The cycle provides the CATALYST (earnings decline, credit tightening). Valuations determine the MAGNITUDE (-30% to -50% from CAPE 36). The combination is the classic Buffett deployment setup: wait for the cycle to turn, wait for valuations to compress, then deploy cash into the resulting dislocation. Prediction: CAPE falls to 18-25 during the contraction. At CAPE 20, forward 10-year real returns exceed 5% — Buffett-level deployment signal. | Provides the specific TRIGGER + MAGNITUDE pairing that neither theory produces alone. Cycle theory says "recession coming." Valuation theory says "when it comes, the drawdown will be 30-50%." Combined: "recession triggers 30-50% drawdown, producing CAPE below 22, which is the deployment signal for the cash position." This is the full Buffett playbook as a testable hypothesis. |
| If `capital_flows` is Active (Accumulation or Rotation) | When US valuations are extreme and EM valuations are depressed (PE gap at historical extremes), the capital rotation trade reinforces the valuation thesis. Prediction: EM outperformance vs. US is driven by BOTH valuation convergence (EM multiples expand, US multiples contract) AND growth convergence (EM growth accelerates, US growth decelerates). Expression: fund the GLD/EM position by reducing QQQ/SPY exposure. The valuation arithmetic favors EM (EEM at 12x vs. SPY at 22x) on any reasonable forward earnings assumptions. | Connects the domestic valuation call (US expensive) to the international rotation call (EM cheap). The combination creates a portfolio-level expression: underweight US (expensive, poor forward returns), overweight EM (cheap, strong forward returns), hedge with GLD (benefits from both dollar weakness and debasement). |

---

## downstream_implications

### affects[]

| Target Theory | Relationship | Description |
|--------------|-------------|-------------|
| `structural_fragility` | **amplifies** | Elevated valuations amplify the MAGNITUDE of any fragility-driven break. The fragility theory predicts the mechanism of the break (forced selling, passive unwind). Valuation theory predicts how far prices must fall to reach fair value. At CAPE 36, the distance to historical average (CAPE 17) is 53%. Even a partial normalization to CAPE 25 is -31%. Fragility provides the catalyst; valuation determines the depth. The evaluator should check: when both theories are Active, magnitude estimates should be at the upper end of BOTH ranges. |
| `fiscal_dominance_liquidity` | **contradicts (partially)** | Valuation theory says "equities are overvalued, hold cash." Fiscal dominance liquidity says "cash loses purchasing power in a debasement regime, hold real assets." The contradiction is about CASH — is it a safe haven (valuation theory) or a wasting asset (fiscal dominance)? Resolution: cash is optimal SHORT-TERM (while waiting for the correction), but real assets (GLD) are optimal LONG-TERM (if the correction never arrives because fiscal dominance sustains nominal prices). The time horizon of the question determines which theory dominates. |
| `debt_cycle_short` | **modifies** | Valuation levels modify the debt cycle's predictions about drawdown magnitude. A cycle contraction starting from CAPE 17 produces a -20% to -30% drawdown (2001 was less severe partly because starting valuations were already partially corrected by 2001). A cycle contraction starting from CAPE 36 produces -30% to -50% (2000-2002 was severe partly because starting valuations were extreme). The starting multiple is the rubber band's tension — the cycle turn releases it. |
| `capital_flows` | **reinforces** | Extreme US valuations strengthen the case for international rotation. When the US premium over EM (measured by relative PE) exceeds 50%, the arithmetic of expected returns increasingly favors EM even without a catalyst. Valuation theory provides the QUANTITATIVE foundation for the capital flow rotation thesis: "US at 22x, EM at 12x, the forward return gap is 3-5% annualized just from multiple normalization." |

---

## falsifiers

### Hard Falsifiers

These conditions, if met, indicate that the valuation mean reversion mechanism is NOT operative or its core predictions are wrong.

| # | Condition | Metric | Threshold | Rationale |
|---|-----------|--------|-----------|-----------|
| H1 | Forward 10-year returns from CAPE 30+ exceed 7% real | Post-hoc: S&P 500 10-year real annualized return from entry at CAPE 30+ | >7% real return over 10 years | If investors who bought at CAPE 30+ earn above-average real returns, the entire theory is wrong. High multiples would NOT be borrowing from the future. This has NEVER occurred in the historical record (since 1900). The highest 10-year real return from CAPE 28+ entry was approximately 5% (entering in 1997, benefiting from the 2009-2019 bull). If a period starting from CAPE 36 delivers 7%+ real, the mechanism has failed. |
| H2 | Equity risk premium below zero for 10+ years without a drawdown exceeding 20% | computed: `equity_risk_premium` + SPY drawdown | ERP negative or below 0.5% continuously for 10 years, max drawdown <20% | If equities deliver adequate total returns despite offering no risk premium over cash for a decade, the ERP framework is not the right pricing model. Possible explanation: equities are priced for growth that cash cannot replicate, and the growth actually materializes decade after decade. This would represent a genuine structural change in how equity risk is priced. |
| H3 | Profit margins do NOT revert over a full business cycle | Web search: S&P 500 net profit margins | Net margins stay above 11% through a full recession without declining below 10% | Margin mean reversion is a key component of the valuation argument (reported PE understates normalized PE because margins are elevated). If margins are structurally permanently higher — due to technology, monopoly power, globalization, or industry mix — then reported PEs are closer to "true" PEs and the overvaluation is smaller than the theory claims. The threshold requires surviving a recession without margin compression — the strongest possible test. |

### Soft Falsifiers

| # | Condition | Metric | Threshold | Implication | Severity |
|---|-----------|--------|-----------|-------------|----------|
| S1 | Rates decline substantially, improving ERP from denominator | `rates.yield_10y` | 10Y yield falls below 3.8% | ERP improves because the "risk-free" comparator declined, not because equities got cheaper. Valuations are still stretched in absolute terms (CAPE still elevated) but the RELATIVE attractiveness of equities vs. bonds improves. The "hold cash" recommendation weakens because cash yields less. Theory is still correct about forward returns being poor, but the catalyst (opportunity cost of equities vs. cash) diminishes. | **major** — removes the primary catalyst (cash yield exceeding equity yield) that drives capital reallocation away from equities. The theory's magnitude prediction remains, but the TRIGGER mechanism is impaired. |
| S2 | Earnings growth exceeds 15% annualized for 3+ years | Web search: S&P 500 operating earnings trajectory | Forward operating earnings revised up 5%+ in a single quarter, with broad-based revenue beats beyond hyperscalers | Earnings growing into the multiple. At 15% annual growth for 3 years, earnings increase ~52%. CAPE falls from 36 to ~24 without any price decline. This would be a genuine productivity-driven bull market (AI delivering). Valuation theory becomes wrong about magnitude (the starting point is expensive but the destination is justifiable) though still correct about mechanism (prices DO need earnings support to be sustained). | **medium** — a single quarter of strong revisions wounds the magnitude prediction but does not confirm sustained earnings growth into the multiple. If earnings are growing fast enough to normalize the multiple, the distance from current price to fair value shrinks dramatically. A correction from CAPE 24 is -29% to reach CAPE 17, vs. -53% from CAPE 36. |
| S3 | Financial repression makes cash a losing proposition in real terms | `rates.fed_funds` vs. `inflation.cpi_yoy` | Real short-term rate (fed funds - CPI) below -1% for the trailing 2 months | When cash yields less than inflation by 2%+, the "hold cash and wait" recommendation destroys purchasing power. The theory's comparative framework (equities vs. cash) breaks when cash is guaranteed to lose real value. This doesn't make equities cheap — it makes EVERYTHING expensive in real terms. The optimal response shifts from "hold cash" to "hold the least expensive real asset" (GLD, TIPS, cheap sector equities). | **medium** — weakens the "hold cash" trade recommendation without changing the valuation diagnosis. Equities are still expensive; cash just stops being the alternative. The mechanism is intact but the practical expression changes. |
| S4 | Market broadening reduces concentration-driven overvaluation | computed: `qqq_iwm_ratio` + RSP vs. SPY | QQQ/IWM ratio declining for 2+ months AND RSP outperforming SPY by 2%+ trailing 1 month | The market-cap-weighted index was expensive partly because a few mega-cap names drove the index PE. If breadth improves, the equal-weighted PE (which was less extreme) becomes more representative. The "market" is less expensive than the index suggested. Valuation excess was concentrated, not broad. Reduces the index-level drawdown prediction (the average stock has less to fall). | **minor** — extends the timeline or changes the expression. The mechanism is unchanged (expensive names should revert), but the INDEX-level expression softens because the index becomes less dependent on the overvalued names. Sector rotation within equities may be more appropriate than blanket underweight. |
| S5 | International valuations converge upward rather than US converging down | EFA, VGK P/E ratios | EAFE P/E rises above 16x while US stays above 21x (gap narrows from international re-rating, not US de-rating) | The US premium narrows not because US gets cheaper but because international gets more expensive. The "overweight EM/EAFE vs. US" trade works on relative returns but the absolute valuation concern remains — both markets are expensive. The prediction about poor forward absolute returns persists for BOTH markets. | **minor** — changes the trade expression (less relative value in EM/EAFE rotation) without affecting the absolute return prediction. The mechanism (high multiples → poor forward returns) applies equally to both markets if both are expensive. |

---

## metadata

```json
{
  "theory_id": "valuation_mean_reversion",
  "version": 1,
  "last_updated": "2026-03-26",
  "update_type": "new",
  "confidence_in_specification": "high",
  "notes": "This is the most empirically grounded theory in the registry. CAPE has predicted forward 10-year returns with R² ~0.80 across 120+ years of data. ERP has correctly identified every major overvaluation (1929, 1968, 2000, 2007, 2021). The main uncertainty is not WHETHER the mechanism works but WHEN and HOW the resolution arrives — the theory is deliberately agnostic on timing because it has no predictive power on catalysts. Sectoral depth is new in this version and less historically tested than the aggregate metrics — threshold calibration for sector-level indicators (P/TBV for banks, replacement cost for energy) is based on fewer data points. The interaction with fiscal dominance is the most consequential open question: if fiscal liquidity permanently prevents price corrections, the resolution channel shifts from crash to inflationary grind — the theory's magnitude prediction (drawdown) may not manifest, but its return prediction (poor forward real returns) still holds. Severity classifications on soft falsifiers align with the scoring pipeline: S1 and S2 are major (0.45 discount) because they directly cap magnitude or remove the primary catalyst; S3 is medium (0.25 discount) because it weakens practical expression without changing the diagnosis; S4 and S5 are minor (0.10 discount) because they affect timing or expression only.",
  "historical_episodes_referenced": [
    "1929 peak (CAPE 32, ERP near zero, Buffett Indicator ~1.0x — resolved via price decline: -86% over 3 years. The most extreme resolution in the dataset.)",
    "1968-1972 Nifty Fifty (CAPE 22-24, not as extreme as other episodes but combined with rising inflation. Resolution: -48% nominal decline 1973-74 PLUS inflation eroding remaining real value. The inflationary grind resolution channel in action.)",
    "1999-2000 dot-com (CAPE 44 — highest ever. ERP negative. Buffett Indicator 1.6x. Resolution: -49% SPY, -78% NASDAQ over 2.5 years. Forward 10-year real return from 2000 peak: approximately -1% annualized. The strongest evidence that high CAPE predicts poor forward returns.)",
    "2007 pre-GFC (CAPE 27 — elevated but not extreme. Resolution amplified by credit crisis, -57% peak-to-trough. Demonstrated that even moderately elevated valuations produce severe drawdowns when combined with structural fragility in the credit system.)",
    "March 2009 trough (CAPE 13. ERP above 7%. Forward 10-year real return: ~13% annualized. The deployment signal in action — buying when valuation theory signals 'cheap' has produced exceptional returns every time.)",
    "March 2020 trough (CAPE briefly 24. ERP widened sharply. Forward returns from March 2020 lows were exceptional. However, the window was brief — within months CAPE was back above 30. The V-shaped recovery demonstrated that fiscal/monetary response can cut short the valuation opportunity.)",
    "2021-present (CAPE 36-38. ERP near zero or negative. Buffett Indicator above 1.8x. Resolution channel TBD — this is the live test of the theory. Berkshire cash above $300B is the real-world expression of the theory's recommendation.)"
  ]
}
```

---

## Usage Notes for Generator and Evaluator

### For the Generator

When this theory is Active, generate hypotheses about:

- **The specific valuation math.** State the CAPE, the ERP, the Buffett Indicator, and SHY yield. Then compute: what forward real return does the current CAPE imply? What is the opportunity cost of equities vs. cash? What drawdown to CAPE 22 (still-elevated fair value) vs. CAPE 17 (historical average)? These are arithmetic, not opinion — compute them explicitly.

- **Which resolution channel is most likely.** Given the other active theories, is the resolution more likely to be (a) price decline, (b) earnings growth, or (c) inflationary grind? If `fiscal_dominance_liquidity` is Active, bias toward channel (c). If `debt_cycle_short` is in Contraction, bias toward channel (a). If neither is clearly signaling, hold all three as possibilities with estimated probabilities.

- **Sectoral opportunities within the expensive market.** Check each sector against its specific valuation threshold. Are financials below 1.0x TBV? Is energy below 4% of S&P weight? Is the IWM/SPY PE discount above 30%? Is international at 50%+ PE discount? Produce specific sector rotation hypotheses even when the market-level view is "expensive."

- **The deployment signal.** Specify what conditions would flip this theory from "defensive" to "deploy." CAPE below 22? ERP above 3%? SPY drawdown of 30%+? The deployment conditions are as important as the warning conditions — they tell you when to STOP being defensive.

**What NOT to claim:**

- Do NOT predict the quarter the correction begins. This theory has zero timing predictive power. It identifies the LEVEL from which the correction starts and the MAGNITUDE of the correction, not the date.
- Do NOT claim "valuations are extreme therefore sell everything." Valuations have been extreme since 2020 and equities have risen substantially. The theory says forward returns are POOR, not that prices can't go higher first. There is a crucial difference between "this is an expensive market" and "this market will crash next month."
- Do NOT ignore the sectoral depth. A hypothesis that says "hold cash, market is expensive" without examining sector-level opportunities is lazy. Buffett doesn't hold 100% cash — he holds cash for the market-level allocation and deploys selectively into sectors with margin of safety. The generator should do the same.
- Do NOT claim this theory alone justifies short positions. The theory identifies magnitude, not timing. Shorting based on "it's expensive" has a terrible track record because expensive can get more expensive for years. Cash (SHY) is the correct expression of the bearish view — not short SPY/QQQ.

### For the Evaluator

Priority checks:

1. **Did the generator state the specific valuation math?** Reject any hypothesis that claims "valuations are stretched" without citing the specific CAPE, ERP, Buffett Indicator values. The theory is QUANTITATIVE — the generator must be quantitative too.

2. **Did the generator make a timing claim?** If the hypothesis says "correction in Q3" or "drawdown within 6 months," challenge it. This theory does not support timing claims. The generator must identify which OTHER theory provides the timing catalyst, and cite it explicitly.

3. **Did the generator address the resolution channel?** If the hypothesis predicts a drawdown but `fiscal_dominance_liquidity` is also Active, the evaluator should challenge whether the price-decline channel is the right prediction or whether the inflationary-grind channel is more likely. The generator cannot invoke valuation theory for the magnitude and ignore fiscal dominance for the channel.

4. **Did the generator examine sector opportunities?** A blanket "hold cash" recommendation from an Active valuation theory is incomplete. Check whether specific sectors are at their identified thresholds. If XLF is at 0.9x TBV, the generator should be producing a sector hypothesis even while the market-level view is defensive.

5. **Is the ERP computation current?** The equity risk premium is the most dynamic valuation metric — it changes daily with rates and SPY price. Ensure the generator used the most recent data, not a stale computation. A hypothesis calibrated to ERP of 0.4% is different from one calibrated to ERP of 1.5% (which might occur if rates fall substantially).

6. **Composition quality check.** The most valuable compositions involve valuation + one other theory providing the timing catalyst: valuation + debt cycle contraction = the classic "what and when" pairing. Valuation + fragility = "how deep." Valuation + fiscal dominance = "which channel." If the composition doesn't narrow the prediction beyond what valuation theory alone provides, it's not adding value.
