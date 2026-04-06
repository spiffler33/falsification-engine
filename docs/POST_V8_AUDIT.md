# Post-v8 Audit

**Date:** 2026-04-06
**Auditor:** Claude Opus (post-v8 deep audit)
**Scope:** Semantic correctness, data truthfulness, threshold integrity, downstream fragility, and regression harness adequacy after v8 remediation
**Method:** Code inspection, causal tracing, frozen-artifact cross-reference, concrete examples
**Test suite at time of audit:** 983 tests passing

---

## 1. Executive summary

### What v8 truly solved

v8 eliminated **parser-level contract violations** between theory packages and the activation engine. Before v8, the engine silently guessed at field names, silently defaulted unknown directions to "above," silently dropped malformed rows, and silently accepted any string as a valid data ownership value. After v8:

- Field resolution fails loudly when backtick field names are missing (FRAGILITY-07 killed)
- Direction parsing rejects unrecognized strings (BUG-02 killed)
- Validation runs as a pre-flight gate before scoring (Task 7)
- All 11 fragilities are either fixed or explicitly documented

v8 restored the **syntax contract**: the engine now reads what the theory packages explicitly declare, and refuses to guess when declarations are ambiguous.

### What remains most risky now

v8 did NOT fix the **semantic contract**: whether the declared fields, thresholds, and comparison logic actually measure what the economic theory intends. The most dangerous remaining issues are:

1. **Proxy mismatches**: computed fields that use wrong units or wrong instruments (gold_oil_ratio uses ETF prices, not commodity prices; eem_spy_3y_relative uses 12-month data as a 3-year proxy)
2. **Threshold extraction from prose**: `_extract_number()` pulls coincidental numbers from prose thresholds ("2-year high" becomes threshold 2, "3-month MA" becomes threshold 3)
3. **Unit mismatches**: several indicators compare field values in one unit system against thresholds extracted in another (millions vs. percentages, billions vs. trillions)
4. **Data gap policy inconsistency**: computed-mechanical indicators with permanently unavailable data stay in the scoring denominator, silently depressing scores

### Recommended next move

**`post_v8_audit.md` targeted remediation first, then `v9.md` architectural redesign.**

The semantic bugs are concrete and fixable without architectural redesign. The architectural issues (structured thresholds, temporal data, correctness harness) need design work that should not block the semantic fixes.

---

## 2. Findings by area

### Area A -- Briefing packet and computed fields

---

#### A-01: gold_oil_ratio uses ETF prices, not commodity prices

- **Classification:** BUG
- **File/function/field:** `backend/engine/data_agent.py:508-510`, field `gold_oil_ratio`
- **Why it matters:** The theory modules (`fiscal_dominance_arithmetic`, `monetary_architecture`) define the gold/oil ratio as "gold spot price / WTI crude oil price." The `fiscal_dominance_arithmetic` ACTIVATION.md line 28 explicitly documents the dependencies as "gold spot price (GC=F or equivalent), WTI crude (CL=F or equivalent). Ratio = gold / oil." But the code computes `GLD.price / USO.price` -- ETF prices, not commodity prices.
- **Concrete example:**
  - GLD = $429.41 (roughly 0.093 oz gold; implies gold spot ~$4,618/oz)
  - USO = $137.92 (oil futures ETF, post-reverse-split; not convertible to oil price)
  - `gold_oil_ratio` = 429.41 / 137.92 = **3.11**
  - Actual gold/oil ratio at ~$4,618 gold / ~$70 oil = **~66**
  - Theory threshold: "Above 25 (vs. historical average ~16-20)"
  - ETF ratio (3.11) can **never** reach 25. Indicator is permanently dormant.
  - Actual ratio (66) would easily trigger. The real world says this indicator should be Active.
- **Impact:** Two theories lose this indicator permanently. fiscal_dominance_arithmetic loses 0.10 weight; monetary_architecture loses 0.18 weight. Both theories are scored lower than economic reality warrants.
- **Recommended next move:** Compute from actual commodity data. DX-Y.NYB is already fetched via SPECIAL_TICKERS. Add gold futures (GC=F) and oil futures (CL=F) to SPECIAL_TICKERS, then compute `gold_price / oil_price` directly. Fallback: use GLD price / 0.093 as a gold spot estimate, and USO is NOT usable as an oil price proxy.

---

#### A-02: equity_risk_premium uses hardcoded 4.5% constant as fallback

- **Classification:** SEMANTIC WEAKNESS
- **File/function/field:** `backend/engine/data_agent.py:459-464`, field `equity_risk_premium`
- **Why it matters:** When WILL5000INDFC (Wilshire 5000) is unavailable from FRED -- which it currently IS -- the ERP calculation falls back to `4.5 - 10Y_yield`. This hardcoded 4.5% "earnings yield" is a static constant that does not track actual market earnings.
- **Concrete example:**
  - `field_provenance["equity_risk_premium"]` = `{method: "fallback", detail: "4.5% constant - 10Y yield"}`
  - ERP = 4.5 - 4.33 = **0.17%**
  - Theory threshold (valuation_mean_reversion): "Below 1.0%"
  - 0.17 < 1.0 --> triggers. But ERP is measuring "are 10Y yields above 3.5%?" not "is the equity risk premium compressed?"
  - With real earnings data, if earnings yield were ~7% (more realistic), ERP = 7.0 - 4.33 = 2.67% and would NOT trigger.
- **Impact:** valuation_mean_reversion indicator (weight 0.25) triggers based on a stale constant, not actual market data. The provenance system correctly flags this as "fallback," but no downstream consumer acts on that flag.
- **Recommended next move:** Wire the web_data_agent to fetch actual S&P 500 earnings yield (or trailing PE from multpl.com, which is already scraped for CAPE). Replace the 4.5% constant. Short-term: consider demoting this indicator's confidence when provenance is "fallback."

---

#### A-03: cash_exceeds_equity_yield inherits degraded ERP

- **Classification:** SEMANTIC WEAKNESS
- **File/function/field:** `backend/engine/data_agent.py:472-483`, field `cash_exceeds_equity_yield`
- **Why it matters:** This field is computed as `fed_funds - (ERP + 10Y)`. When ERP is the fallback constant, the denominator is `4.5% + 10Y` = effectively the constant itself. The comparison becomes `fed_funds - 4.5` rather than `fed_funds - actual_earnings_yield`.
- **Concrete example:**
  - cash_exceeds_equity_yield = 3.64 - (0.17 + 4.33) = **-0.86**
  - Threshold "Above 0" --> does NOT trigger (correct directionally: cash does not exceed equity yield)
  - But the magnitude is wrong. With real earnings yield (~7%), result would be 3.64 - 7.0 = -3.36 (much more negative)
- **Impact:** Currently produces the correct trigger result (negative = doesn't trigger), but the margin of safety is understated. If fed funds rose above 4.5%, this indicator would falsely trigger.
- **Recommended next move:** Fix upstream (A-02). This field automatically corrects when ERP uses real data.

---

#### A-04: eem_spy_3y_relative uses 12-month return as 3-year proxy

- **Classification:** ARCHITECTURAL LIMITATION
- **File/function/field:** `backend/engine/data_agent.py:522-523`, field `eem_spy_3y_relative`
- **Why it matters:** The field is documented as "EEM vs SPY cumulative rolling 3-year relative return." The code sets `eem_spy_3y_relative = em_us_relative_12m`. A 12-month return is not a 3-year cumulative return. The theory threshold is "EEM underperformed SPY by 30%+ cumulative 3-year." A 12-month underperformance of 30% does not imply 3-year underperformance of 30%.
- **Concrete example:**
  - eem_spy_3y_relative = 9.5 (12-month EM outperformance)
  - Theory checks: 9.5 < -30 --> does not trigger (correct directionally -- EM is outperforming)
  - But if EM had -20% 12M relative return, the proxy would show -20 vs threshold -30 --> not triggered. The actual 3-year number could be -45% (triggered) or -15% (not triggered). The proxy gives no information.
- **Impact:** capital_flows Phase A loses one indicator (weight 0.27) to a proxy that can only detect extreme values. Moderate underperformance goes undetected.
- **Recommended next move:** Yahoo Finance 1-year chart data is the limit. For a true 3-year comparison, either: (a) accumulate returns over time in a local store, or (b) fetch 3-year data via a different API. Classify this as a v9 task.

---

#### A-05: interest_exceeds_defense uses hardcoded $940B defense estimate

- **Classification:** ACCEPTABLE CONSTRAINT
- **File/function/field:** `backend/engine/data_agent.py:650-658`, field `interest_exceeds_defense`
- **Why it matters:** Defense spending is hardcoded at $940B (FY2026 estimate). The provenance system correctly marks this as `method: "hardcoded"`. The value drifts ~3%/year.
- **Concrete example:** interest_payments (~$1,227B) - $940B = $287B surplus. Indicator triggers (287 > 0). Correct.
- **Impact:** Low. The surplus is large enough ($287B) that reasonable drift in the defense constant ($940B +/- $50B) does not change the trigger result.
- **Recommended next move:** Add an annual review note. Consider fetching defense spending from CBO or OMB data in the web_data_agent. Not urgent.

---

#### A-06: real_fed_funds / real_fed_funds_rate duplicate fields

- **Classification:** SEMANTIC WEAKNESS
- **File/function/field:** `backend/engine/data_agent.py:489` (`real_fed_funds_rate`) and `data_agent.py:586` (`real_fed_funds`)
- **Why it matters:** Two fields with nearly identical names compute the identical formula (`fed_funds - CPI_YoY`). The theory module (debt_cycle_long line 33) references `real_fed_funds_rate` in backticks. The frozen briefing packet only contains `real_fed_funds` (generated before Task 2 added `real_fed_funds_rate`). A live data agent run produces both, so scoring works at runtime. But the frozen mock data creates a discrepancy.
- **Concrete example:**
  - `computed["real_fed_funds"]` = 0.98 (present in mock data)
  - `computed["real_fed_funds_rate"]` = 0.98 (produced by live data agent, absent from mock data)
  - Theory backtick reference: `real_fed_funds_rate`
  - Against mock data: BriefingPacket.get_field("real_fed_funds_rate") = None (field not in mock)
  - Against live data: BriefingPacket.get_field("real_fed_funds_rate") = 0.98 (field exists)
- **Impact:** Low at runtime (both fields exist). But creates confusion and mock data diverges from live.
- **Recommended next move:** Remove the duplicate `real_fed_funds` (line 586). Keep `real_fed_funds_rate` which matches the theory's backtick reference. Regenerate mock data.

---

#### A-07: DXY data fetched but not resolvable through BriefingPacket.get_field()

- **Classification:** ARCHITECTURAL LIMITATION
- **File/function/field:** `backend/engine/data_agent.py:285` (SPECIAL_TICKERS), `backend/schemas/briefing.py:111-115` (get_field ticker logic)
- **Why it matters:** DX-Y.NYB is in SPECIAL_TICKERS and IS fetched. The mock data shows `markets["DX-Y.NYB"] = {price: 100.092, ...}`. But `BriefingPacket.get_field("DX-Y.NYB")` only checks market data for tickers starting with `^` or `$`. DX-Y.NYB starts with `D`, so it falls through to the computed/web-sourced/fallback scans, all of which fail.
- **Concrete example:**
  - capital_flows references DXY for "Dollar strong or sideways" (weight 0.20) and "Dollar weakening" (weight 0.25)
  - DXY price = 100.092 (in market data, fetched successfully)
  - get_field("DX-Y.NYB") returns None (ticker format not recognized)
  - Both indicators have value=None, stay in denominator, never trigger
  - This failed in v1 too (pre-existing gap), but the data IS now available -- just not wired through
- **Impact:** capital_flows loses 0.45 weight across both phases to an indicator whose data actually exists in the briefing. fiscal_dominance_liquidity and fiscal_dominance_arithmetic also reference DXY in falsifiers.
- **Recommended next move:** Either (a) add a computed field `dxy_index` extracted from `markets["DX-Y.NYB"].price`, or (b) extend get_field to check market data for any ticker, not just ^/$ prefixed ones. Then update capital_flows ACTIVATION.md to reference the new field with backticks.

---

#### A-08: top_10_sp500_weight has no data source

- **Classification:** SEMANTIC WEAKNESS
- **File/function/field:** `backend/engine/data_agent.py:574-575`, field `top_10_sp500_weight`
- **Why it matters:** This field is hardcoded to `None` with provenance `method: "missing"`. It has been a placeholder since v1. The structural_fragility theory uses it as a computed-mechanical indicator with weight 0.20.
- **Concrete example:**
  - Value = None. Stays in denominator. Never triggers.
  - structural_fragility Phase A score is permanently depressed by 0.20 weight.
- **Impact:** Same class as A-07 but worse -- there is no data source at all, not even an unfetched one.
- **Recommended next move:** Either wire a data source (web-scrape from S&P or ETF holdings data) or reclassify the indicator to `web-search` so it is skipped (not penalized) when unavailable. The latter is the honest short-term fix.

---

### Area B -- Threshold semantics and units

---

#### B-01: _extract_number() strips unit suffixes without scaling

- **Classification:** BUG (known, documented as design limitation #2 in closure)
- **File/function/field:** `backend/engine/activation.py:366-381`
- **Why it matters:** The function strips T, B, M, bp, %, $, x characters but does not multiply the resulting number by the appropriate scale factor. "$1.5T" becomes 1.5, not 1,500,000,000,000. This is only safe when the field value happens to be in matching units.
- **Concrete example -- deficit_pace_annualized:**
  - Threshold string: "Deficit above $1.5T annualized while unemployment below 5%"
  - After stripping: "Deficit above 1.5 annualized while unemployment below 5"
  - Extracted number: **1.5** (first number)
  - Field value: `deficit_pace_annualized` = 3690.0 (**billions**)
  - Comparison: 3690 > 1.5 --> True
  - Correct comparison: 3690 > 1500 (both in $B) or 3.69 > 1.5 (both in $T)
  - Result: **Correct by accident.** Threshold is 1000x too small. A $2B deficit (effectively balanced budget) would still trigger (2 > 1.5).
- **Scope:** Affects every threshold containing T, B, or M suffixes. Currently all trigger correctly by accident because field values greatly exceed the stripped numbers.
- **Recommended next move:** For post_v8_audit: add unit-aware threshold parsing for known suffixes (T=1e12, B=1e9, M=1e6, bp=0.01). For v9: structured threshold objects.

---

#### B-02: Temporal thresholds extracted as static numbers

- **Classification:** SEMANTIC WEAKNESS (systemic)
- **File/function/field:** `backend/engine/activation.py:366-381` (extraction), all theories with temporal thresholds
- **Why it matters:** Many thresholds describe temporal conditions ("declining 3+ months," "within last 10 years," "rising 3+ months AND accelerating"). `_extract_number()` extracts the first number as a static threshold, ignoring the temporal semantics.
- **Concrete examples:**

  | Theory | Indicator | Threshold text | Extracted number | Field value | Triggers? | Correct? |
  |--------|-----------|---------------|-----------------|-------------|-----------|----------|
  | debt_cycle_long | Rates at ELB | "0-0.25% within last 10 years" | 0 | fed_funds=3.64 | Yes (3.64>0) | Wrong reason: tests current rate > 0, not historical ELB |
  | debt_cycle_short B | Sahm Rule | "3-month MA rising 0.50%+ above 12-month low" | 3 | unemployment=4.3 | Yes (4.3>3) | Wrong reason: tests unemployment > 3, not Sahm Rule math |
  | capital_flows B | Dollar weakening | "DXY declining 3+ months AND below 12-month MA" | 3 | None (DXY unresolvable) | N/A | N/A (but would be wrong if resolved) |

- **Scope:** At least 8-10 indicators across 5 theories use temporal thresholds that cannot be checked with the current engine's snapshot-based data model.
- **Recommended next move:** For post_v8_audit: classify each temporal threshold as either (a) convertible to a static proxy (document the proxy explicitly) or (b) genuinely requiring temporal data (mark as UNTESTABLE via validator note, consider not scoring). For v9: add prior-period data to briefing for RISING/FALLING and MA-based checks.

---

#### B-03: "2-year high" and similar comparative thresholds parsed as the embedded number

- **Classification:** BUG
- **File/function/field:** `backend/engine/activation.py:366-381`, valuation_mean_reversion market breadth indicator
- **Why it matters:** Thresholds like "Above 2-year high" or "Within 10% of record highs" contain numbers that refer to time periods or percentages, not threshold values. `_extract_number()` extracts them as thresholds.
- **Concrete example -- qqq_iwm_ratio:**
  - Threshold: "QQQ/IWM above 2-year high AND RSP underperforming SPY by 5%+ over 12 months"
  - After stripping %: "QQQ/IWM above 2-year high AND RSP underperforming SPY by 5+ over 12 months"
  - Extracted number: **2** (from "2-year")
  - Field value: `qqq_iwm_ratio` = 2.3279
  - Comparison: 2.3279 > 2 --> True
  - **Correct by coincidence.** The QQQ/IWM ratio historically ranges 1.5-3.0, and 2.0 happens to be a plausible threshold. But the intended check is "above the 2-year high of the ratio" -- a historical comparison requiring time-series data.
- **Impact:** Produces plausible-looking results that are semantically wrong. Future ratio changes could expose the coincidence.
- **Recommended next move:** Explicitly tag these indicators as having UNTESTABLE thresholds. Add a computed field for QQQ/IWM 2-year high if historical data is available, or reclassify as a context flag.

---

#### B-04: Compound AND/OR thresholds reduce to first number

- **Classification:** SEMANTIC WEAKNESS
- **File/function/field:** `backend/engine/activation.py:366-381`, multiple theories
- **Why it matters:** Thresholds like "Unemployment <5% AND ISM >45 after 12+ months FF >4%" contain multiple conditions. Only the first extractable number is used.
- **Concrete example -- fiscal_dominance_liquidity "Rate hikes not producing recession":**
  - Threshold: "Unemployment <5% AND ISM >45 after 12+ months FF >4%"
  - Extracted number: **5** (from "5%")
  - Field value: `growth.unemployment` = 4.3
  - Direction: above --> 4.3 > 5 --> **False**
  - But the INTENDED first condition is "Unemployment < 5%" which should be True (4.3 < 5)
  - The direction/number mismatch: the direction is "above" (from ACTIVATION.md), but the first condition is "below 5%"
- **Impact:** Multi-condition thresholds are reduced to a single condition that may not even be the primary one. Results are unpredictable.
- **Recommended next move:** For v9: introduce structured threshold objects that can represent AND/OR conditions. For post_v8_audit: audit each multi-condition threshold and decide whether to (a) split into multiple indicators, (b) pick the primary condition and document the rest as context, or (c) add computed fields that evaluate the compound condition mechanically.

---

#### B-05: Should v9 introduce structured threshold objects?

- **Classification:** ARCHITECTURAL LIMITATION (systemic)
- **Assessment:** **Yes, emphatically.** The current prose-threshold system has the following failure modes:
  1. Unit suffix stripping without scaling (B-01)
  2. Temporal conditions extracted as static numbers (B-02)
  3. Comparative thresholds parsed as embedded numbers (B-03)
  4. Multi-condition thresholds reduced to first number (B-04)
  5. No validation that the extracted number is semantically related to the threshold's intent

  Of the 43 scored indicators across 8 theories:
  - ~20 have simple "Above/Below X" thresholds that parse correctly
  - ~10 have unit-suffixed thresholds that parse correctly by coincidence
  - ~8 have temporal or comparative thresholds that parse as wrong numbers
  - ~5 have multi-condition thresholds that lose information

  A structured threshold schema would look like:
  ```
  threshold:
    type: simple | range | temporal | compound | comparative
    value: 25
    unit: ratio | percent | billions | basis_points
    conditions:  # for compound type
      - field: growth.unemployment
        operator: below
        value: 5
        unit: percent
  ```

- **Recommended next move:** Design the schema in v9. For post_v8_audit: document each indicator's threshold as one of STRUCTURED_ENOUGH / PROSE_BUT_CORRECT / PROSE_AND_WRONG / UNTESTABLE. Fix the PROSE_AND_WRONG cases with targeted threshold string edits or computed fields.

---

### Area C -- Activation-score semantic correctness

Traced against the frozen briefing packet (`data/briefing_packet.json`, 2026-04-03).

---

#### C-01: debt_cycle_long "Fed BS / GDP" -- comparing millions to percentage threshold

- **Classification:** BUG (correct by accident)
- **File/function/field:** `theories/THEORY_MODULE_debt_cycle_long_v2/ACTIVATION.md:29`, field `liquidity.fed_balance_sheet`
- **Why it matters:** The indicator checks "Fed BS above 20% of GDP." The metric source resolves to `liquidity.fed_balance_sheet` (raw value in millions). The threshold extracts 20. The comparison is 6,675,344 > 20, which is trivially true for any non-zero balance sheet.
- **Traced path:**
  - Metric source: `` `liquidity.fed_balance_sheet` / nominal GDP (FRED) ``
  - Backtick extraction: `liquidity.fed_balance_sheet` (the "/nominal GDP" part is after the backtick, ignored)
  - Resolved value: 6,675,344.0 (millions)
  - Threshold: "Fed BS above 20% of GDP" --> extracts 20
  - Direction: above
  - Result: 6,675,344 > 20 --> **True**
  - Correct result: fed_bs_gdp_ratio (21.2%) > 20% --> True
  - The **correct answer is obtained for the wrong reason.** Any fed balance sheet above $20M would trigger this.
- **Impact:** The computed field `fed_bs_gdp_ratio` (= 21.2%) already exists in the briefing. The theory should reference it instead.
- **Recommended next move:** Change the ACTIVATION.md metric_source backtick to `` `fed_bs_gdp_ratio` ``. Update threshold to "Above 20". This is a one-line markdown edit + one test update.

---

#### C-02: debt_cycle_long "Rates at ELB" -- trivially always true

- **Classification:** SEMANTIC WEAKNESS
- **File/function/field:** `theories/THEORY_MODULE_debt_cycle_long_v2/ACTIVATION.md:30`, field `rates.fed_funds`
- **Why it matters:** The indicator asks "Were rates at 0-0.25% within the last 10 years?" The implementation checks `current_fed_funds > 0`. This is trivially true for any positive fed funds rate. The indicator is permanently activated.
- **Traced path:**
  - Metric source: `` `rates.fed_funds` (historical lookback) ``
  - Resolved value: 3.64
  - Threshold: "Fed funds rate was at 0-0.25% within the last 10 years" --> extracts **0**
  - Direction: above
  - Result: 3.64 > 0 --> **True**
  - Intended check: historical -- "was the rate at 0-0.25% at any point in the last 10 years?"
  - This requires historical data the engine does not have.
- **Impact:** Weight 0.15 is effectively free. The indicator provides no discrimination between scenarios.
- **Recommended next move:** Either (a) create a computed boolean field `elb_within_10y` that the data_agent sets based on known FRED history, or (b) reclassify as a context flag since the engine cannot mechanically evaluate the historical condition. Option (b) is more honest.

---

#### C-03: structural_fragility "Top-10 concentration" -- permanently in denominator with no data

- **Classification:** SEMANTIC WEAKNESS
- **File/function/field:** structural_fragility ACTIVATION.md Phase A, field `top_10_sp500_weight`
- **Why it matters:** The field has provenance `method: "missing"`. It is `computed-mechanical` (not `web-search`), so it is NOT skipped when unavailable. It stays in the scoring denominator (weight 0.20) and can never trigger. This permanently depresses Phase A scores by 0.20 / total_weight.
- **Traced path:**
  - Value: None (no data source implemented)
  - Data ownership: computed-mechanical
  - Handling: counted in denominator, value=None, triggered=False
  - Phase A total weight: ~1.00
  - Without this indicator: triggered/denominator would exclude 0.20 from both
  - With this indicator: denominator includes 0.20, triggered does not
- **Impact:** Phase A score is structurally capped lower than it should be. If 3 other indicators trigger (weights 0.10 + 0.10 + 0.10 = 0.30), score = 0.30/1.00 = 0.30 (barely Adjacent). Without this dead indicator: 0.30/0.80 = 0.375 (solidly Adjacent).
- **Recommended next move:** Reclassify as `web-search` so it is skipped when unavailable. Or wire a data source.

---

#### C-04: gold_oil_ratio permanently dormant in fiscal_dominance_arithmetic and monetary_architecture

- **Classification:** BUG (see A-01 for root cause)
- **Impact trace:**
  - fiscal_dominance_arithmetic: gold_oil_ratio weight 0.10. Current score 0.722 (Active). If gold_oil_ratio triggered, score = 0.822. Tier unchanged but conviction higher.
  - monetary_architecture: gold_oil_ratio weight 0.18. Current score 0.408 (Adjacent). If gold_oil_ratio triggered, score = 0.588 (still Adjacent, but approaching Active). **This could change tier** with other indicators also improving.
- **Recommended next move:** Fix A-01.

---

#### C-05: Indicators correct by coincidence -- full inventory

- **Classification:** SEMANTIC WEAKNESS (systemic)
- **Why it matters:** These indicators trigger correctly today but would give wrong answers under different market conditions.

| Theory | Indicator | Field | Value | Threshold extracted | Intended threshold | Why coincidence holds |
|--------|-----------|-------|-------|--------------------|--------------------|----------------------|
| debt_cycle_long | Fed BS/GDP | liquidity.fed_balance_sheet | 6,675,344 | 20 | 20% of GDP (21.2%) | Millions >> 20 |
| debt_cycle_long | Rates at ELB | rates.fed_funds | 3.64 | 0 | Historical 10y lookback | Any positive rate > 0 |
| fiscal_dom_liq | Deficit pace | deficit_pace_annualized | 3,690 | 1.5 | $1.5T ($1,500B) | Billions >> 1.5 |
| debt_cycle_short B | Sahm Rule | growth.unemployment | 4.3 | 3 | 3mo MA +0.50pp | 4.3 > 3 by luck |
| valuation_mr | Market breadth | qqq_iwm_ratio | 2.33 | 2 | Above 2-year high | Ratio ~2.3 > 2 by luck |

- **Recommended next move:** Fix C-01 (fed_bs_gdp_ratio). Convert debt_cycle_long ELB to context flag or computed boolean. Fix deficit_pace threshold to use matching units. The rest require v9 structured thresholds.

---

### Area D -- Data-gap policy

---

#### D-01: Inconsistent None handling between web-search and computed-mechanical

- **Classification:** POLICY INCONSISTENCY
- **File/function/field:** `backend/engine/activation.py:216-219` (web-search skip) vs `:221-230` (non-web None stays in denominator)
- **Why it matters:** Web-search indicators with `value=None` are **skipped** (removed from both numerator and denominator). Computed-mechanical indicators with `value=None` **stay in the denominator** (counted as untriggered). This distinction makes sense for *temporarily* unavailable web data but is wrong for *structurally* unavailable computed fields.
- **Examples of structurally absent computed-mechanical indicators:**
  - `top_10_sp500_weight` -- no data source exists (provenance: "missing")
  - `DX-Y.NYB` via capital_flows -- data exists but field resolution fails (A-07)
  - `real_fed_funds_rate` in mock data -- field absent from frozen artifacts
- **Impact:** Structurally absent computed-mechanical indicators permanently depress scores. The penalty is invisible (no loud failure) and permanent (not fixable by fetching more data).
- **Recommended next move:** Introduce a third category: "structurally unresolvable." When the validator identifies a computed-mechanical indicator whose metric_source resolves to None (or whose field is in provenance as "missing"), it should either (a) skip that indicator (like web-search), or (b) raise an error-severity finding that blocks scoring.

---

#### D-02: Validator notes used as bounded constraints vs. masking live weakness

- **Classification:** POLICY UNCLEAR
- **File/function/field:** `backend/engine/theory_loader.py:1603-1614` (note-severity threshold), `:1628-1639` (note-severity metric resolution)
- **Why it matters:** The Task 7 validator produces 8 informational notes across the 8 theories. These are classified as `severity="note"` (non-blocking). Some are genuine bounded constraints ("RISING/FALLING is a provisional proxy"). Others mask indicators that are effectively dead weight in the denominator.
- **Classification of current validator notes:**

  | Note | Type | Correct policy? |
  |------|------|----------------|
  | DXY metric resolution in capital_flows | Live weakness (data exists, field unresolvable) | Should be ERROR or SKIP |
  | Prose threshold in debt_cycle_short | Bounded constraint (engine returns False) | Correct as NOTE |
  | Prose threshold in fiscal_dom_arith | Bounded constraint | Correct as NOTE |
  | Prose threshold in fiscal_dom_liq | Bounded constraint | Correct as NOTE |
  | Non-backtick metric in monetary_arch | Live weakness (field won't resolve) | Should be ERROR or SKIP |
  | RISING/FALLING proxy | Bounded constraint (documented) | Correct as NOTE |

- **Recommended next move:** Reclassify the two "live weakness" notes as error-severity findings OR add a "skip" mechanism for indicators whose metric resolution demonstrably fails. The principle: a note should mean "this is known and handled gracefully," not "this indicator is silently dead."

---

#### D-03: monetary_architecture has 2 indicators with no field resolution

- **Classification:** SEMANTIC WEAKNESS
- **File/function/field:** monetary_architecture ACTIVATION.md indicators "Foreign official Treasury holdings declining" and "Gold/oil ratio elevated"
- **Why it matters:** These are `computed-mechanical` indicators. "Foreign Treasury holdings" references `FDHBFIN` from FRED but the metric_source in ACTIVATION.md does not have backtick-wrapped field names that the parser can extract. The field `foreign_treasury_holdings_pct` exists in the briefing (computed at data_agent.py:635-644) but the indicator can't find it.
- **Impact:** monetary_architecture loses 0.24 + 0.18 = 0.42 weight to unresolvable indicators. Current score: 0.408 (Adjacent). Without these dead indicators: the denominator drops by 0.42, and the score of the remaining indicators rises. If CB gold (0.29 weight, triggers) were the only triggering indicator: 0.29 / 0.58 = 0.50 (still Adjacent but higher).
- **Recommended next move:** Add backtick field references to the ACTIVATION.md: `` `foreign_treasury_holdings_pct` `` and `` `gold_oil_ratio` ``. The fields exist -- they just aren't wired.

---

### Area E -- Downstream consumer fragility

---

#### E-01: Prompt builder is safe (pass-through)

- **Classification:** ACCEPTABLE (no action needed)
- **File/function:** `backend/engine/prompt_builder.py` :: `build_generation_prompt_v8()`, `build_elimination_prompt_v8()`
- **Evidence:** CORE.md, TACTICAL.md, and PLAYBOOK.md are injected verbatim into prompts as raw markdown. No parsing, no structural dependencies. If the markdown content changes, the LLM sees the new content. The only hardcoded strings are the section labels ("--- CORE.md ---", etc.).
- **Risk:** Minimal. The section labels are cosmetic (they help the LLM identify sections, not the engine).

---

#### E-02: Pipeline falsifier matching uses fuzzy substring containment

- **Classification:** ARCHITECTURAL LIMITATION
- **File/function:** `backend/api/pipeline.py` :: `_resolve_registry_entry()` (approximately lines 74-94)
- **Why it matters:** When a hypothesis's soft falsifier condition text is matched against the falsifier registry, matching uses case-insensitive substring containment with a minimum 10-character overlap. This is fragile: if the hypothesis generator produces slightly different wording than the registry's condition text, matching fails silently and no discount is applied.
- **Impact:** Conviction scoring may under-discount if falsifier conditions are paraphrased. This is a design choice (fuzzy matching is better than exact matching for LLM-generated text), but it degrades silently.
- **Recommended next move:** Not a post_v8 issue. For v9: consider matching by falsifier ID rather than condition text, which would require the LLM to reference IDs in its output.

---

#### E-03: Severity enum values hardcoded in multiple places

- **Classification:** SEMANTIC WEAKNESS
- **File/function:** `backend/engine/conviction.py` (SEVERITY_WEIGHTS dict), `backend/engine/theory_loader.py` (_classify_severity_text), `backend/schemas/theory.py` (Severity enum)
- **Why it matters:** The severity values ("minor", "medium", "major") and their numeric weights (0.10, 0.25, 0.45) are defined in three separate locations. If one changes without the others, discounts break silently.
- **Impact:** Low (the values are unlikely to change). But it violates the "single source of truth" principle.
- **Recommended next move:** Consolidate to the Severity enum in `schemas/theory.py` with associated weights. Low priority.

---

#### E-04: WEB_FIELD_MAP depends on exact substring matching

- **Classification:** ACCEPTABLE CONSTRAINT
- **File/function:** `backend/engine/activation.py:32-88`
- **Why it matters:** WEB_FIELD_MAP contains 36 keyword-to-field mappings. Each keyword must appear as a substring of the metric_source. If a web-search metric_source is reworded (e.g., "Shiller PE ratio" instead of "Shiller CAPE ratio"), the lookup fails and returns None.
- **Impact:** Low today (all current packages match). Fragile to future edits.
- **Recommended next move:** The validator (Task 7) catches unresolvable web-search metrics. No additional work needed unless false positives appear.

---

### Area F -- Reproducibility and regression harness

---

#### F-01: Equivalence script is a migration harness, not a correctness harness

- **Classification:** ARCHITECTURAL LIMITATION
- **File/function:** `scripts/v8_equivalence_check.py`
- **Why it matters:** The script compares v8 scores against v1 scores. After v8 remediation, v1 is the known-broken baseline. The script can detect regression FROM v1 but cannot detect:
  - Whether v8 scores are economically correct
  - Whether new bugs introduced after remediation produce wrong scores
  - Whether indicators trigger for the right reasons (vs. coincidence)
  - Whether the briefing data is accurate
- **Evidence:** The V8_CORRECTED classification accepts v8 divergence from v1 as "intentional improvement." This is correct for the migration, but post-migration the script's value diminishes.
- **Recommended next move:** Evolve into a correctness harness (see F-02).

---

#### F-02: No frozen expected-output tests exist

- **Classification:** REGRESSION GAP
- **Why it matters:** There is no test that says "given this specific briefing, theory X should produce score Y with these specific indicators triggering/not-triggering and these specific values." The existing tests either (a) use synthetic data with synthetic theories, or (b) compare v8 to v1. Neither checks absolute correctness.
- **What is needed:** A test fixture like:
  ```python
  EXPECTED_RESULTS = {
      "valuation_mean_reversion": {
          "score": 0.706,
          "tier": "Active",
          "indicators": {
              "Equity risk premium compressed": {"triggered": True, "value": 0.17},
              "Market breadth narrow": {"triggered": True, "value": 2.3279},
              ...
          }
      }
  }
  ```
  This should be checked on every test run against the frozen briefing packet.
- **Recommended next move:** Create `test_activation_correctness.py` with per-indicator expected outputs for all 8 theories against the frozen briefing. This is the single most important regression defense post-v8.

---

#### F-03: Frozen briefing does not contain post-Task-2 computed fields

- **Classification:** SEMANTIC WEAKNESS
- **File:** `data/briefing_packet.json` (and `mock_data/briefing_packet.json`)
- **Why it matters:** Both briefing files were generated on 2026-04-03, before Task 2 added `real_fed_funds_rate` and `cash_exceeds_equity_yield`. These fields exist at runtime (data_agent produces them) but are absent from frozen artifacts. Tests that use the frozen briefing will see different behavior than live runs.
- **Recommended next move:** Regenerate the frozen briefing by running the data agent. Commit the result. Update expected-output tests (F-02) to match.

---

#### F-04: Missing "one command" regression answer

- **Classification:** REGRESSION GAP
- **Why it matters:** There is no single command that answers: "did we break parser correctness, score correctness, or validator behavior?" The current answer requires running three separate things:
  1. `python -m pytest backend/` (parser + validator)
  2. `python -m scripts.v8_equivalence_check` (migration regression)
  3. Manual inspection of indicator results (score correctness)
- **Recommended next move:** Create a `scripts/regression_check.py` that runs (1) pytest programmatically, (2) the correctness harness from F-02, and (3) the equivalence check. Output: PASS/FAIL with specific failures named. This becomes the permanent post-v8 regression gate.

---

## 3. Priority ranking

| # | Finding | Severity | Scope | Why now | Phase |
|---|---------|----------|-------|---------|-------|
| 1 | **A-01**: gold_oil_ratio uses ETF prices | BUG | 2 theories, 0.28 weight | Indicator permanently dormant; real data says should trigger | post_v8_audit |
| 2 | **F-02**: No frozen expected-output tests | GAP | All 8 theories | Without this, any future change can break scores silently | post_v8_audit |
| 3 | **C-01**: Fed BS/GDP compares millions to percentage | BUG | 1 theory, 0.25 weight | Correct by accident; trivial fix (use existing computed field) | post_v8_audit |
| 4 | **D-01**: Computed-mechanical None stays in denominator | POLICY | 3+ theories | Silently depresses scores for structurally absent data | post_v8_audit |
| 5 | **A-07**: DXY fetched but not resolvable | ARCH LIMIT | 1 theory, 0.45 weight | Data exists; just needs wiring through get_field | post_v8_audit |
| 6 | **B-01**: _extract_number unit suffix scaling | BUG | ~10 indicators | Correct by accident today; future thresholds may not be | post_v8_audit |
| 7 | **D-03**: monetary_architecture 2 indicators unresolvable | SEM WEAK | 1 theory, 0.42 weight | Fields exist; backtick references missing | post_v8_audit |
| 8 | **B-05**: Structured threshold objects needed | ARCH LIMIT | Systemic | Root cause of B-01 through B-04 | v9 |
| 9 | **A-02**: ERP fallback to 4.5% constant | SEM WEAK | 2 fields | Provenance tracks it; needs better data source | post_v8_audit |
| 10 | **F-04**: No single regression command | GAP | All | Operational gap; blocks automated CI | post_v8_audit |

---

## 4. Proposed next phase

**Choice: `post_v8_audit.md` targeted remediation first, then `v9.md` architectural redesign.**

### Justification

The findings split cleanly:

- **Concrete, fixable now (post_v8_audit):** gold_oil_ratio formula, Fed BS/GDP field reference, DXY wiring, monetary_architecture backtick fixes, data gap policy, frozen expected-output tests, briefing regeneration, unit-suffix scaling
- **Needs design work (v9):** structured threshold schema, temporal data model, multi-condition threshold parsing, correctness validation framework, RISING/FALLING trend detection

The post_v8_audit fixes do not require any architectural changes. They are field-level corrections and test infrastructure. They should take 6-8 focused tasks.

The v9 work requires design decisions (threshold schema format, temporal data storage, computed boolean fields for complex conditions). Starting v9 before fixing the known semantic bugs would mean designing around incorrect data.

### Proposed task list for post_v8_audit.md

**Task 0 -- Freeze current state**
Regenerate briefing packet with current data_agent (adds real_fed_funds_rate, cash_exceeds_equity_yield). Commit as new frozen baseline.

**Task 1 -- Fix gold_oil_ratio computation**
Add GC=F (gold futures) and CL=F (oil futures) to SPECIAL_TICKERS. Compute gold_oil_ratio from spot-equivalent prices instead of GLD/USO. Validate against threshold 25.

**Task 2 -- Wire DXY through briefing resolution**
Create computed field `dxy_index` from `markets["DX-Y.NYB"].price`. Update capital_flows ACTIVATION.md to reference `` `dxy_index` ``. Extend get_field if needed.

**Task 3 -- Fix unit-mismatch indicators**
- Change debt_cycle_long "Fed BS/GDP" metric_source to `` `fed_bs_gdp_ratio` ``
- Fix deficit_pace threshold string to use billions ("Above 1500") or create a computed boolean field
- Fix monetary_architecture missing backtick references (foreign_treasury_holdings_pct, gold_oil_ratio)

**Task 4 -- Data gap policy**
- Reclassify top_10_sp500_weight as web-search (or wire data source)
- Add "structurally unresolvable" handling: when provenance is "missing" and data_ownership is computed-mechanical, skip the indicator (don't penalize)
- Reclassify debt_cycle_long "Rates at ELB" as context flag (cannot be mechanically evaluated)

**Task 5 -- Unit-suffix scaling in _extract_number**
Add T/B/M/bp multipliers. Validate all current thresholds still produce correct results.

**Task 6 -- Create frozen expected-output correctness tests**
Build test_activation_correctness.py with per-indicator expected results for all 8 theories against the frozen briefing. This becomes the permanent regression gate.

**Task 7 -- Create single regression command**
Build scripts/regression_check.py that runs pytest + correctness tests + equivalence check. PASS/FAIL output.

**Task 8 -- Clean up duplicates and update closure**
Remove real_fed_funds duplicate. Update validator note classifications (D-02). Produce closure document. Update memory.

---

## 5. Novice explanation

The v8 remediation fixed the **syntax** of how the engine reads theory modules. Before v8, when a theory document said "check the equity risk premium," the engine sometimes couldn't find the right data field and quietly returned zero instead of loudly failing. v8 fixed that: now the engine either finds the right field or refuses to proceed.

What we are auditing now is the **semantics** -- whether the fields, thresholds, and comparisons actually mean what the economic theory intends. For example, the system computes the gold/oil ratio by dividing the price of a gold ETF by the price of an oil ETF, but the theory's threshold (25) was written for the actual gold-to-oil commodity ratio, which is about 20 times larger. The indicator can never trigger because the proxy uses the wrong scale.

Parser correctness was not the end of the story because a mechanically correct parser can still produce economically wrong scores. "The field resolved correctly" does not mean "the score reflects economic reality." The engine now reads what it's told to read -- but some of what it's told is a poor proxy for what the theory actually means.

The next phase should fix these concrete semantic mismatches (wrong proxies, wrong units, dead indicators) with targeted corrections, then follow with an architectural redesign that introduces structured thresholds and temporal data capabilities.

---

## 6. Appendix

### Files inspected

| File | Lines inspected | Purpose |
|------|----------------|---------|
| `backend/engine/activation.py` | Full (580 lines) | Scoring engine, field resolution, threshold checking |
| `backend/engine/data_agent.py` | 1-740 | FRED transforms, Yahoo fetch, computed metrics, briefing assembly |
| `backend/engine/theory_loader.py` | 1-100, 1515-1714 | Theory loading, validation, TheoryValidationError |
| `backend/schemas/briefing.py` | Full (147 lines) | BriefingPacket model, get_field resolution |
| `backend/engine/prompt_builder.py` | Via agent (full) | Prompt assembly, theory content injection |
| `backend/api/pipeline.py` | Via agent (full) | Pipeline endpoints, falsifier matching |
| `backend/engine/conviction.py` | Via agent (key sections) | Conviction scoring, severity weights |
| `scripts/v8_equivalence_check.py` | Via agent (full, 490 lines) | Migration equivalence harness |
| `theories/THEORY_MODULE_*/ACTIVATION.md` | All 8 files (full) | Indicator definitions, thresholds, directions |
| `data/briefing_packet.json` | Full | Frozen briefing data |
| `mock_data/briefing_packet.json` | Full | Mock briefing (identical to data/) |
| `docs/V8_PREREMEDIATION_BASELINE.md` | Full | Pre-remediation frozen state |
| `docs/V8_REMEDIATION_CLOSURE.md` | Full | Post-remediation closure |
| `docs/V8_DIVERGENCE_DOCKET.md` | Full | Migration divergence analysis |
| `docs/V8_IMPLICIT_CONTRACT_AUDIT.md` | Full | Pre-remediation implicit contract audit |
| `v8_fix.md` | Full (601 lines) | Remediation plan and completion notes |

### Commands run

```
python -m pytest backend/ -x -q          # 983 passed in 5.82s
python3 -c "..." (briefing inspection)   # Verified field presence, provenance, market data
ls -la data/ mock_data/                  # Confirmed identical briefing files
```

### Frozen artifacts relied on

- `data/briefing_packet.json` — 2026-04-03 FRED + Yahoo + web data
- `docs/V8_PREREMEDIATION_BASELINE.md` — Pre-fix broken state
- `docs/V8_REMEDIATION_CLOSURE.md` — Post-fix closure with design limitations
- `docs/V8_DIVERGENCE_DOCKET.md` — Per-indicator migration divergence traces
- `docs/V8_IMPLICIT_CONTRACT_AUDIT.md` — Pre-remediation implicit contract findings
