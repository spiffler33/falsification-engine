# Post-v8 Semantic Baseline

**Frozen:** 2026-04-06
**Briefing timestamp:** 2026-04-06T07:06:30.033323+00:00
**Data agent:** live (FRED + Yahoo Finance + web scraping, --fresh)
**Test suite at freeze:** 983 tests passing
**Purpose:** Frozen reference for post-v8 semantic remediation. All later tasks diff against this file.

---

## 1. Theory scores and tiers

| # | theory_id | Two-phase? | Score | Tier | Phase (if applicable) |
|---|-----------|-----------|-------|------|-----------------------|
| 1 | valuation_mean_reversion | No | 0.706 | Active | -- |
| 2 | debt_cycle_short | Yes | 0.400 / 0.650 | Adjacent / Active | Effective: Contraction (Adjacent) |
| 3 | debt_cycle_long | No | 0.900 | Active | -- |
| 4 | structural_fragility | Yes | 0.000 / 0.353 | Inactive / Adjacent | Effective: Fragility Building (Adjacent) |
| 5 | fiscal_dominance_liquidity | No | 0.700 | Active | -- |
| 6 | fiscal_dominance_arithmetic | No | 0.722 | Active | -- |
| 7 | capital_flows | Yes | 0.450 / 0.270 | Adjacent / Inactive | Effective: Rotation (Adjacent) |
| 8 | monetary_architecture | No | 0.408 | Adjacent | -- |

### Summary by tier

- **Active (>=0.60):** valuation_mean_reversion (0.706), debt_cycle_long (0.900), fiscal_dominance_liquidity (0.700), fiscal_dominance_arithmetic (0.722)
- **Adjacent (0.30-0.59):** debt_cycle_short/Contraction (0.400), structural_fragility/Building (0.353), capital_flows/Rotation (0.450), monetary_architecture (0.408)
- **Inactive (<0.30):** structural_fragility/Resolving (0.000), capital_flows/Accumulation (0.270)

---

## 2. Per-indicator triggered state

### valuation_mean_reversion -- Score: 0.706 (Active)

| Triggered | Weight | Indicator | Value | Threshold | Direction | Notes |
|-----------|--------|-----------|-------|-----------|-----------|-------|
| . | 0.10 | Corporate profit margins at cycle highs | 8.86 | "Net margins above 12% OR corporate profits / GDP above 10%" | above | Not triggered: 8.86 < 12 |
| T | 0.25 | Equity risk premium compressed | 0.19 | "Below 1.0%" | below | AUDIT A-02: uses fallback 4.5% constant |
| T | 0.05 | Insider selling elevated | 19.0 | "Insider sell/buy ratio above 5:1 sustained for 3+ months" | above | |
| T | 0.10 | Market breadth narrow | 2.33 | "QQQ/IWM ratio above 2-year high..." | above | AUDIT B-03: threshold extracts "2" from "2-year high" |
| T | 0.20 | Shiller CAPE elevated | 37.94 | "Above 30" | above | |
| . | 0.15 | Short-term cash yield exceeds equity earnings yield | -0.86 | "Above 0" | above | AUDIT A-03: inherits degraded ERP |
| -- | 0.15 | Buffett Indicator extreme | skipped | -- | -- | web data unavailable (WILL5000INDFC) |

### debt_cycle_short -- Phase Contraction: 0.400 (Adjacent), Phase Expansion: 0.650 (Active)

| Triggered | Weight | Indicator | Value | Threshold extracted | Direction | Phase |
|-----------|--------|-----------|-------|---------------------|-----------|-------|
| T | 0.10 | Consumer/business confidence | 98.91 | above 90 | above | Expansion |
| T | 0.15 | Credit spreads tight or tightening | 317.0 | below 450 | below | Expansion |
| . | 0.15 | Credit spreads widening sharply | 317.0 | above 500 | above | Contraction |
| T | 0.10 | Fed funds above nominal GDP growth | 31442.5 | above 5 | above | Contraction -- AUDIT: value is GDP level in $B, not growth rate comparison |
| . | 0.10 | Fed funds below nominal GDP growth | 31442.5 | below 5 | below | Expansion |
| T | 0.15 | ISM proxy above contraction | 52.7 | above 50 | above | Expansion |
| . | 0.15 | ISM proxy below contraction | 52.7 | below 48 | below | Contraction |
| . | 0.10 | Initial claims low | 202000 | below 250000 | below | Expansion -- AUDIT: 202000 < 250000 is true but direction says "below" |
| T | 0.10 | Initial claims rising | 202000 | above 280000 | above | Contraction -- AUDIT: 202K < 280K, should NOT trigger; check parse |
| . | 0.15 | Net credit growth positive | 0.0 | above (prose) | above | Expansion |
| . | 0.15 | SLOOS showing broad tightening | 0.0 | above (prose) | above | Contraction |
| T | 0.15 | Unemployment low or falling | 4.3 | below 5.0 | below | Expansion |
| T | 0.20 | Unemployment rising (Sahm Rule) | 4.3 | rising 0.50%+ | rising | Contraction -- AUDIT B-02: temporal threshold extracts "3" |
| T | 0.10 | Yield curve not deeply inverted | 0.52 | above -0.50 | above | Expansion |
| . | 0.15 | Yield curve re-steepening | 0.52 | rising (prose) | rising | Contraction |

### debt_cycle_long -- Score: 0.900 (Active)

| Triggered | Weight | Indicator | Value | Threshold extracted | Direction | Notes |
|-----------|--------|-----------|-------|---------------------|-----------|-------|
| T | 0.25 | Fed balance sheet / GDP elevated | 6675344 | 20 | above | AUDIT C-01: compares millions to %; correct by accident |
| T | 0.15 | Fiscal deficit as primary growth driver | 287.0 | above (prose) | above | |
| . | 0.10 | Negative real rates during expansion | 0.98 | below 0 | below | Correct: real rate positive |
| T | 0.15 | Rates at/near ELB within recent memory | 3.64 | 0 | above | AUDIT C-02: trivially always true (any rate > 0) |
| T | 0.25 | Total debt / GDP above warning level | 256.72 | above 250 | above | |
| T | 0.10 | Wealth inequality at extremes | 68.1 | above 70 | above | Note: 68.1 < 70, should NOT trigger; check threshold extraction |

### structural_fragility -- Phase Resolving: 0.000 (Inactive), Phase Building: 0.353 (Adjacent)

| Triggered | Weight | Indicator | Value | Threshold extracted | Direction | Phase |
|-----------|--------|-----------|-------|---------------------|-----------|-------|
| . | 0.20 | Drawdown depth | -5.7 | below -20 | below | Resolving |
| . | 0.15 | High-yield spread | 317.0 | below 300 | below | Building |
| . | 0.10 | Implied vol level | 23.87 | below 14 | below | Building |
| . | 0.10 | Implied-realized vol gap | 4.86 | above 5 | above | Building |
| T | 0.10 | Large-cap/small-cap divergence | 2.33 | 2 | above | Building -- AUDIT B-03: "2-year high" -> threshold 2 |
| T | 0.10 | Margin debt | 1253.2 | above (prose) | above | Building |
| T | 0.10 | Passive fund share | 59.0 | above 50 | above | Building |
| . | 0.00 | Top-10 index concentration | None | above 30 | ? | Building -- AUDIT C-03/A-08: w=0.00 (skipped?), no data source |
| . | 0.15 | Valuation compression | 37.94 | below 20 | below | Resolving |
| -- | -- | Capex/revenue mismatch | skipped | -- | -- | Building -- no field mapping |

### fiscal_dominance_liquidity -- Score: 0.700 (Active)

| Triggered | Weight | Indicator | Value | Threshold extracted | Direction | Notes |
|-----------|--------|-----------|-------|---------------------|-----------|-------|
| T | 0.20 | Deficit pace | 3690.0 | 1.5 | above | AUDIT B-01: "$1.5T" strips to 1.5, field in billions |
| . | 0.10 | Fed BS direction inconsistent | 6675344 | rising (prose) | rising | |
| T | 0.15 | Hard assets outperforming nominal bonds | 73.09 | above 10 | above | |
| T | 0.20 | Net liquidity expanding | 101440 | above (prose) | above | |
| . | 0.10 | RRP draining toward zero | 327.0 | below 250 | below | |
| T | 0.15 | Rate hikes not producing recession | 52.7 | above 5 | above | AUDIT B-04: compound threshold, extracts "5" from "5%" |
| . | 0.10 | TGA behavior consistent with spending | 847718 | below 500 | below | |

### fiscal_dominance_arithmetic -- Score: 0.722 (Active)

| Triggered | Weight | Indicator | Value | Threshold extracted | Direction | Notes |
|-----------|--------|-----------|-------|---------------------|-----------|-------|
| T | 0.05 | CB gold purchases sustained | 1037.0 | above 800 | above | |
| . | 0.15 | Debt rollover at higher rates | 3.355 | rising (prose) | rising | |
| T | 0.20 | Deficit pace outside recession | 3690.0 | 1.5 | above | AUDIT B-01: "$1.5T" strips to 1.5 |
| . | 0.10 | Gold/oil ratio elevated | 3.11 | above 25 | above | AUDIT A-01: ETF ratio, not commodity ratio |
| T | 0.25 | Interest expense / tax receipts | 34.0 | above 20 | above | |
| T | 0.15 | Interest exceeds defense | 287.0 | above 0 | above | AUDIT A-05: uses $940B hardcoded defense |

### capital_flows -- Phase Rotation: 0.450 (Adjacent), Phase Accumulation: 0.270 (Inactive)

| Triggered | Weight | Indicator | Value | Threshold extracted | Direction | Phase |
|-----------|--------|-----------|-------|---------------------|-----------|-------|
| . | 0.20 | China credit impulse flat/negative | 3.5 | below 0 | below | Rotation |
| T | 0.20 | China credit impulse positive | 3.5 | above 0 | above | Accumulation |
| . | 0.10 | Chinese equities leading | -7.13 | above 15 | above | Accumulation |
| T | 0.10 | Commodity prices rising | 31.17 | above 3 | above | Accumulation -- AUDIT B-02: "3+ months" extracts 3 |
| . | 0.00 | Dollar strong or sideways | None | above 100 | ? | Rotation -- AUDIT A-07: DXY unresolvable, w=0.00 |
| . | 0.00 | Dollar weakening | None | declining 3+ months | ? | Accumulation -- AUDIT A-07: DXY unresolvable, w=0.00 |
| T | 0.15 | EM outperforming DM | 7.27 | above (prose) | above | Accumulation |
| T | 0.27 | EM rolling 3-year underperformance | 9.5 | below -30 | below | Rotation -- AUDIT A-04: 12-month proxy for 3-year |
| . | 0.33 | EM vs. DM PE gap at extremes | 11.28 | above 40 | above | Rotation |
| . | 0.20 | RMB strengthening | 6.89 | falling (prose) | falling | Accumulation |

### monetary_architecture -- Score: 0.408 (Adjacent)

| Triggered | Weight | Indicator | Value | Threshold extracted | Direction | Notes |
|-----------|--------|-----------|-------|---------------------|-----------|-------|
| T | 0.29 | CB gold purchases sustained | 1037.0 | above 800 | above | |
| . | 0.00 | Foreign Treasury holdings declining | None | declining (prose) | ? | AUDIT D-03: field exists but no backtick ref |
| . | 0.00 | Gold/oil ratio elevated and rising | None | above 25 | ? | AUDIT D-03: field exists but no backtick ref |
| -- | -- | Cross-currency basis swap stress | skipped | -- | -- | No field mapping |
| -- | -- | Non-dollar trade settlement growing | skipped | -- | -- | No field mapping |

---

## 3. Audited field values and provenance

These are the specific fields called out in `POST_V8_AUDIT.md` as semantically risky.

| Field | Value | Provenance method | Provenance detail | Audit finding |
|-------|-------|-------------------|-------------------|---------------|
| `gold_oil_ratio` | 3.11 | (none) | -- | A-01 BUG: uses GLD/USO ETF prices, not commodity. Real ratio ~66 |
| `equity_risk_premium` | 0.19 | fallback | 4.5% constant - 10Y yield (WILL5000INDFC unavailable) | A-02: hardcoded 4.5% earnings yield constant |
| `cash_exceeds_equity_yield` | -0.86 | primary | fed_funds (3.64) - (ERP (0.19) + 10Y (4.31)) | A-03: inherits degraded ERP |
| `eem_spy_3y_relative` | 9.5 | (none) | -- | A-04: 12-month return used as 3-year proxy |
| `interest_exceeds_defense` | 287.0 | hardcoded | Interest - $940B defense (FY2026 estimate) | A-05: acceptable, surplus large enough |
| `real_fed_funds` | 0.98 | (none) | -- | A-06: duplicate of `real_fed_funds_rate` |
| `real_fed_funds_rate` | 0.98 | primary | fed_funds (3.64) - CPI YoY (2.66) | A-06: canonical field, matches theory backtick |
| `fed_bs_gdp_ratio` | 21.2 | (none) | -- | C-01: field EXISTS but debt_cycle_long uses raw `liquidity.fed_balance_sheet` instead |
| `deficit_pace_annualized` | 3690.0 | (none) | -- | B-01: value in billions; threshold "$1.5T" extracts as 1.5 |
| `top_10_sp500_weight` | None | missing | No data source implemented (placeholder since v1) | A-08/C-03: stays in denominator as dead weight |
| `foreign_treasury_holdings_pct` | 24.0 | (none) | -- | D-03: field exists but monetary_architecture ACTIVATION.md lacks backtick ref |
| `federal_debt_to_gdp` | 122.5 | (none) | -- | New post-v8 computed field |
| `interest_receipts_ratio` | 34.0 | (none) | -- | New post-v8 computed field |
| `sloos_net_tightening` | 0.0 | (none) | -- | New post-v8 computed field |

### DXY resolution gap

DX-Y.NYB is fetched and present in `markets`:
- price: 100.083
- return_1m: +0.77%
- return_3m: +1.69%
- return_12m: -3.1%

But `BriefingPacket.get_field("DX-Y.NYB")` returns None because the ticker format is not recognized by the get_field resolution path (only `^` and `$` prefixed tickers are checked in market data). **Audit A-07.**

---

## 4. Mock/live discrepancies resolved by this regeneration

The previous frozen briefing (2026-04-03, committed to git) was missing these computed fields that the live data agent produces:

| Field | Value in regenerated briefing | Status |
|-------|-------------------------------|--------|
| `cash_exceeds_equity_yield` | -0.86 | Added by v8 remediation Task 2 |
| `real_fed_funds_rate` | 0.98 | Added by v8 remediation Task 2 |
| `fed_bs_gdp_ratio` | 21.2 | Added during v8 data enrichment |
| `deficit_pace_annualized` | 3690.0 | Added during v8 data enrichment |
| `interest_exceeds_defense` | 287.0 | Added during v8 data enrichment |
| `interest_receipts_ratio` | 34.0 | Added during v8 data enrichment |
| `foreign_treasury_holdings_pct` | 24.0 | Added during v8 data enrichment |
| `federal_debt_to_gdp` | 122.5 | Added during v8 data enrichment |
| `corporate_profits_gdp_ratio` | 11.4 | Added during v8 data enrichment |
| `sloos_net_tightening` | 0.0 | Added during v8 data enrichment |

These fields were present at runtime (data agent produced them) but absent from frozen artifacts. Tests using the old frozen briefing saw different behavior than live runs. **Audit F-03 resolved.**

The duplicate field `real_fed_funds` (0.98) is also present -- identical to `real_fed_funds_rate`. **Audit A-06 confirmed: still duplicated.**

---

## 5. Indicators correct by coincidence (from audit C-05)

These indicators trigger correctly today but would give wrong answers under different market conditions:

| Theory | Indicator | Field value | Threshold extracted | Intended threshold | Why coincidence holds |
|--------|-----------|-------------|--------------------|--------------------|----------------------|
| debt_cycle_long | Fed BS/GDP | 6,675,344 (millions) | 20 | 20% of GDP (21.2%) | Millions >> 20 |
| debt_cycle_long | Rates at ELB | 3.64 | 0 | Historical 10y lookback | Any positive rate > 0 |
| fiscal_dom_liq | Deficit pace | 3,690 (billions) | 1.5 | $1.5T ($1,500B) | Billions >> 1.5 |
| debt_cycle_short | Sahm Rule | 4.3 | 3 | 3mo MA +0.50pp | 4.3 > 3 by luck |
| valuation_mr | Market breadth | 2.33 | 2 | Above 2-year high | Ratio ~2.3 > 2 by luck |

---

## 6. Data quality at freeze time

- **Overall quality:** DEGRADED
- **1 error:** Missing critical computed field `buffett_indicator` (WILL5000INDFC unavailable from FRED)
- **3 warnings:**
  - `buffett_indicator`: Cannot compute
  - `equity_risk_premium`: 4.5% constant fallback
  - `top_10_sp500_weight`: No data source implemented
- **1 informational:** `interest_exceeds_defense` uses hardcoded $940B defense estimate

---

## 7. Validation notes from theory package validator

| Theory | Note | Type |
|--------|------|------|
| capital_flows | DXY metric resolution fails | Live weakness (data exists, field unresolvable) |
| debt_cycle_short | Prose threshold (net credit growth) | Bounded constraint |
| fiscal_dominance_arithmetic | Prose threshold (debt rollover) | Bounded constraint |
| fiscal_dominance_liquidity | Prose threshold (multiple) | Bounded constraint |
| monetary_architecture | Non-backtick metric refs (2 indicators) | Live weakness (fields exist, not wired) |
| Multiple | RISING/FALLING provisional proxy | Bounded constraint (documented) |

---

## 8. Semantic bugs inventory (pre-remediation state)

Carried forward from `POST_V8_AUDIT.md` priority ranking. This is what Tasks 1-6 will fix:

| Priority | Finding | Classification | Theories affected | Weight lost |
|----------|---------|---------------|-------------------|-------------|
| 1 | gold_oil_ratio uses ETF prices (A-01) | BUG | fiscal_dom_arith, monetary_arch | 0.10 + 0.18 |
| 2 | No frozen expected-output tests (F-02) | GAP | All 8 | -- |
| 3 | Fed BS/GDP compares millions to % (C-01) | BUG | debt_cycle_long | 0.25 |
| 4 | Computed-mechanical None stays in denominator (D-01) | POLICY | 3+ theories | variable |
| 5 | DXY fetched but not resolvable (A-07) | ARCH LIMIT | capital_flows | 0.45 |
| 6 | Unit suffix scaling missing (B-01) | BUG | ~10 indicators | variable |
| 7 | monetary_architecture 2 indicators unresolvable (D-03) | SEM WEAK | monetary_architecture | 0.42 |
| 8 | ERP fallback to 4.5% constant (A-02) | SEM WEAK | valuation_mr | 0.25 |
| 9 | No single regression command (F-04) | GAP | All | -- |

---

*This file is a frozen artifact. Do not edit it after Task 0 is committed. Later tasks diff against this baseline.*
