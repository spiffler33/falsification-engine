# TACTICAL.md — Valuation Mean Reversion & Margin of Safety

*theory_id: `valuation_mean_reversion`*

---

## directional_predictions

When Active, this theory produces the following asset-level predictions. These are return expectations, not timing calls.

| Asset | Direction | Magnitude Range | Timeframe | Mechanism |
|-------|-----------|----------------|-----------|-----------|
| SPY | Forward real returns poor | +0% to +4% annualized real | Next 7–10 years | Arithmetic of high CAPE. From CAPE 36, implied forward real return is approximately 2.8% (1/CAPE), well below the historical average of 6–7%. |
| SPY | Drawdown magnitude elevated when catalyst arrives | -25% to -50% peak-to-trough | Conditional on catalyst from another theory | Valuation excess determines distance from current price to fair value. CAPE 36 to CAPE 22 (still above average) = -39%. CAPE 36 to CAPE 17 (historical average) = -53%. |
| SHY | Outperform SPY on risk-adjusted basis | +4% to +5.5% annualized, zero drawdown risk | While ERP is below 1% | Cash yields more than equity earnings yield. Superior risk-adjusted holding while ERP compressed. |
| TLT | Conditional on resolution channel | Varies by channel | — | Deflationary crash → TLT rallies +20–30%. Inflationary grind → TLT declines further. Valuation theory alone does not predict the channel — depends on interaction with fiscal dominance and debt cycle theories. |
| GLD | Benefits from inflationary resolution channel | +10% to +25% per year if resolution is inflationary | 3–10 years | If valuation excess resolves through inflation (channel c), gold benefits as real value of equities and bonds erodes. Preserves purchasing power when nominal assets deliver negative real returns. |
| EFA, VGK | Outperform SPY on relative basis | +3% to +7% annualized relative over 5 years | When US premium exceeds 50% | Multiple compression in the US + multiple stability or expansion internationally = international outperformance. Does not require international economies to be strong — only requires US premium to partially normalize. |
| IWM | Outperform QQQ on relative basis | +5% to +10% annualized relative | When IWM PE discount to SPY exceeds 30% | Valuation gap mean reversion. Requires catalyst (rate cuts, credit easing, large-cap disappointment). Gap is the setup; catalyst comes from other theories. |
| Sector-level opportunities | Outperform broad index | +5% to +15% annualized relative to SPY | 1–3 years | Sectors at relative valuation extremes offer rotation alpha. Specific sectors depend on current conditions — see sector depth section below. |

---

## etf_mappings

| Expression | Primary ETFs | Alternatives |
|-----------|-------------|-------------|
| Broad US equity underweight | SPY, QQQ (reduce) | VOO, VTI |
| Cash / short duration overweight | SHY, BIL | SGOV, USFR |
| Duration (conditional on channel) | TLT (deflationary crash) | IEF, ZROZ |
| Gold / real assets | GLD | IAU, SGOL, GDX (miners for leverage) |
| International developed | EFA, VGK | IEFA, VEA, EWG, EWU |
| Emerging markets | EEM | VWO, FXI, INDA |
| Small cap value | IWM | IWN, VBR, MDY |
| Financials | XLF | KBE (banks), KRE (regionals) |
| Energy | XLE | XOP (E&P), OIH (services) |
| Healthcare | XLV | XBI (biotech) |
| Consumer staples | XLP | — |

---

## sector_depth

Sector-level valuation analysis. Even in expensive markets, individual sectors rotate through temporary distress. These are the specific sector opportunities this theory monitors.

### Financials (XLF, KBE, KRE)

- **Primary metric:** Price-to-Tangible-Book Value (P/TBV)
- **Threshold:** Below 1.0x P/TBV = interesting. Below 0.8x in a non-systemic crisis = compelling.
- **Mechanism:** Banks are leveraged balance sheets with spread income. TBV is the liquidation value floor. Below 1.0x means the market is pricing loan losses that exceed tangible equity — either justified (systemic risk) or overreaction (temporary credit stress).
- **Key diagnostic:** Is the crisis temporary (credit losses that normalize in 2–3 years) or permanent (business model impairment from regulation or technology)? Regional bank stress in 2023 (KRE -35%) was temporary. Money-center bank stress in 2008 was systemic.

### Energy (XLE, XOP)

- **Primary metric:** EV/EBITDA relative to replacement cost of reserves; sector weight in S&P 500.
- **Threshold:** XLE at or below 4% of S&P 500 weight = historically extreme underweight. EV/EBITDA below 5x = below replacement cost.
- **Mechanism:** Energy is cyclical but essential. At minimum S&P weight + below replacement cost, you are buying productive assets for less than it would cost to build them. Cash flows are real and current, not hypothetical future revenue.
- **Key diagnostic:** Is the underweight cyclical (oil price downturn) or structural (energy transition permanently reducing fossil fuel value)? Current view: cyclical underweight within a structural transition that will take decades, not years.

### Healthcare (XLV, XBI)

- **Primary metric:** P/E relative to S&P 500 average; P/E relative to own 10-year average.
- **Threshold:** XLV PE discount to SPY exceeding 30%. XBI below 0.6x its 5-year average P/S.
- **Mechanism:** Aging demographics provide structural revenue tailwind. Political risk (drug pricing legislation) creates temporary discounts that overshoot because legislation is typically narrower than feared. Biotech after pipeline failures or regulatory crackdowns: sector trades below value of approved drugs alone (pipeline optionality priced at zero).

### Consumer Staples (XLP)

- **Primary metric:** P/E, dividend yield.
- **Threshold:** PE below 18 with dividend yield above 2.8% = fair value. PE below 15 = rare and attractive.
- **Mechanism:** Durable moats, predictable cash flows, pricing power over inflation. Rarely cheap enough to be exciting — primarily a safe harbor when everything else is expensive. XLP at 15x when SPY is at 24x = meaningful relative value.

### Small Caps (IWM, MDY)

- **Primary metric:** IWM PE discount to SPY; Russell 2000 P/B ratio.
- **Threshold:** IWM PE discount to SPY exceeding 30% = historical extreme. Russell 2000 P/B below 1.8x = attractive on asset basis.
- **Mechanism:** More exposed to domestic economy and credit conditions. Benefit disproportionately from rate cuts (more floating-rate debt). When valuation gap to large caps is at extremes, mean reversion is likely — but requires a catalyst (rate cuts, credit easing, large-cap correction).

### International Value (EFA, VGK)

- **Primary metric:** Relative P/E (MSCI EAFE PE vs. S&P 500 PE); US premium as percentage.
- **Threshold:** US PE premium over EAFE exceeding 50% (e.g., SPY at 22x, EFA at 14x) = extreme.
- **Mechanism:** The US premium reflects genuine quality differences (higher margins, more tech exposure, better governance) but overshoots. At 50%+ premium, the arithmetic of lower starting multiples favors international. Forward return gap is 3–5% annualized in international's favor, purely from multiple normalization.

---

## regional_sequencing

When the US valuation premium is extreme (>50% over EAFE):

1. **Europe (VGK)** tends to lead the relative outperformance — deepest discount, most liquid, least geopolitical risk.
2. **Japan (EWJ)** follows — structural governance improvements (TSE reforms) providing a catalyst for re-rating.
3. **EM broadly (EEM)** participates when the US dollar weakens — currency is the primary gating factor for EM relative performance.
4. **Sector rotation within US** (IWM, XLF, XLE) runs in parallel — the same valuation discipline applied domestically.

---

## relative_value_expressions

| Long | Short / Underweight | Thesis | Timeframe |
|------|---------------------|--------|-----------|
| SHY | SPY | Cash yields more than equity earnings yield while ERP < 1% | While ERP compressed |
| EFA/VGK | QQQ | International at 50%+ PE discount to US | 3–5 years |
| IWM | QQQ | Small cap PE discount at historical extreme (>30%) | 1–3 years, catalyst-dependent |
| RSP | SPY | Equal-weight vs. cap-weight when breadth is narrow | 1–2 years |
| XLF (below 1.0x TBV) | SPY | Banks below liquidation value in non-systemic stress | 1–2 years |
| GLD | SPY | If resolution channel is inflationary grind | 3–10 years |

---

## current_theme_specifics

*This section is explicitly ephemeral. Update as the macro environment evolves.*

**As of early 2026:**

- CAPE at 36+. ERP near zero. Buffett Indicator above 1.8x.
- Berkshire cash exceeds $300B — the real-world expression of the theory's recommendation.
- Primary narrative justifying the multiple: AI productivity revolution. The narrative is partially true (AI is producing genuine productivity gains in some sectors) and insufficient to justify the aggregate multiple (the productivity gains would need to be 3–5x larger and more broadly distributed than current evidence supports).
- Resolution channel TBD — this is the live test of the theory. If fiscal dominance sustains nominal prices, resolution is inflationary grind. If a cyclical downturn arrives, resolution is price decline.
- Sector opportunities as of current conditions: KRE remains interesting if it re-tests stress levels from 2023 (below 0.8x TBV during non-systemic stress). Energy (XLE) at approximately 4% of S&P weight — near the threshold but not yet triggering. International (VGK at ~13x) vs. US (~22x) gap is at extremes.

---

## expression_monitors

Short-horizon operational checks on trade expressions. These monitor whether the TRADE is working, not whether the THEORY is true.

| Monitor | What It Tracks | Action If Triggered |
|---------|---------------|---------------------|
| SHY yield declining toward equity earnings yield | Fed cutting rates, reducing cash yield advantage | If SHY yield drops below SPY earnings yield, the cash-overweight expression loses its rationale. Reassess: either move to GLD (real assets) or re-enter equities if CAPE has normalized. |
| Sector rotation trades underperforming for 6+ months | Cheap sectors staying cheap or getting cheaper | Review whether "temporary distress" diagnosis is correct. May be permanent impairment. Do not add to losing sector positions without re-examining the thesis. |
| International relative performance stalling despite PE gap | EFA/VGK not outperforming despite 50%+ PE discount | Dollar strength or European macro deterioration overriding the valuation signal. The PE gap is a necessary but insufficient condition — currency and growth matter for timing. |
| Breadth narrowing further despite "expensive" signal | QQQ/IWM ratio making new highs, concentration increasing | Market can get MORE expensive and MORE concentrated. This is not a falsifier — it confirms the theory. But it means the RSP-vs-SPY expression is premature. Timing is from another theory. |

---

## time_horizon

- **Forward return prediction:** 7–12 years. CAPE is a poor 1-year predictor but an excellent 10-year predictor. R² of CAPE vs. forward 10-year real return is approximately 0.80 historically.
- **Drawdown magnitude prediction:** Conditional on catalyst. When the catalyst arrives (from another theory), valuation determines the depth. Can be immediately relevant.
- **Sectoral rotation:** 1–3 years. Sector-level valuations mean-revert faster than market-level because catalysts are more frequent (earnings cycles, regulatory changes, commodity price moves).
- **Opportunity cost:** Continuous. As long as ERP is compressed, the opportunity cost of equity exposure versus cash/short duration is quantifiable and ongoing.

---

## deployment_signal

The theory's forward-return prediction works in both directions. When valuations reach historically cheap levels, the theory signals aggressive deployment:

- CAPE below 22 → forward 10-year real returns historically exceed 5% annualized
- ERP above 3% → equities offer meaningful compensation for risk
- SPY drawdown of 30%+ from recent peak → valuation gap partially closed
- March 2009 (CAPE 13, ERP >7%) and March 2020 (CAPE briefly 24, ERP widening sharply) are the templates. The deployment signal is as important as the warning signal.

---
