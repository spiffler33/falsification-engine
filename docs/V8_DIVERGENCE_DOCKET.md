# V8 Migration Divergence Docket

**Date:** 2026-04-06
**Subject:** Three theories produce materially different activation scores under v8 theory packages vs. v1 monolithic format
**Severity:** Two are bugs (broken field resolution). One is a structural change with a secondary bug.
**Affected theories:** `valuation_mean_reversion`, `fiscal_dominance_arithmetic`, `capital_flows`

---

## Executive Summary

During the v8 migration (monolithic theory files to four-file packages), the ACTIVATION.md files for three theories were rewritten from machine-parseable metric_source strings to human-readable descriptions. The activation scoring engine (`activation.py`) depends on specific formatting conventions -- backtick-wrapped field names and "Web search:" prefixes -- to resolve metric_source strings to briefing packet fields. The rewrite broke that resolution.

The result: indicators that successfully resolved to data in v1 now resolve to `None` in v8. They are counted in the scoring denominator but can never trigger, permanently depressing scores.

| Theory | v1 Score | v8 Score | v1 Tier | v8 Tier | Broken Indicators | Broken Weight |
|--------|----------|----------|---------|---------|-------------------|---------------|
| `valuation_mean_reversion` | 0.882 | 0.294 | **Active** | Inactive | 3 of 7 | 0.50 / 1.00 |
| `fiscal_dominance_arithmetic` | 0.556 | 0.056 | Adjacent | Inactive | 3 of 6 | 0.55 / 0.90 |
| `capital_flows` | 0.450 | N/A | Adjacent | Inactive | 7 of 10 | ~0.82 across phases |

**Root cause in all three cases:** metric_source strings in v2 ACTIVATION.md lack the formatting that `_extract_metric_field()` needs to resolve them to briefing packet fields.

---

## How Field Resolution Works

The activation scoring engine resolves each indicator's `metric_source` string to a briefing packet field name via `_extract_metric_field()` in `backend/engine/activation.py` (lines 257-291). It uses three strategies, tried in order:

### Strategy 1: Web-search lookup
If the string contains `"web search"`, the engine searches `WEB_FIELD_MAP` (a list of keyword-to-field mappings). Example: `"web search: Shiller CAPE ratio"` matches keyword `"shiller cape ratio"` and resolves to field `shiller_cape`.

**Prerequisite:** The `_entry_to_indicator()` function (lines 410-433) re-injects the `"web search: "` prefix for indicators whose `data_ownership` is `"web-search"`, but only if the metric_source doesn't already contain it.

### Strategy 2: Backtick extraction
If no web-search match, the engine looks for backtick-wrapped field names via regex `` `([^`]+)` ``. Example: `` computed: `equity_risk_premium` (SPY earnings yield) `` extracts `equity_risk_premium`.

### Strategy 3: Plain string passthrough
If no backticks found and the string doesn't start with `"web"`, the entire string is returned as-is and passed to `briefing.get_field()`. This almost always returns `None` because no briefing field is named `"Computed: SPY earnings yield (1/PE) minus 10Y Treasury yield"`.

**The bug:** The v2 ACTIVATION.md files use Strategy 3 for indicators that previously used Strategy 1 or 2. The human-readable descriptions pass through as literal field names and fail to resolve.

---

## Case 1: `valuation_mean_reversion`

**Score change:** 0.882 (Active) --> 0.294 (Inactive)

### Broken Indicators

Three `computed-mechanical` indicators lost their backtick-wrapped field names in the v2 rewrite:

#### 1. Equity Risk Premium Compressed (weight: 0.25)

| | v1 metric_source | v2 metric_source |
|--|--|--|
| **String** | `` computed: `equity_risk_premium` (SPY earnings yield - 10Y yield) `` | `Computed: SPY earnings yield (1/PE) minus 10Y Treasury yield` |
| **Resolution strategy** | Strategy 2: backtick extraction --> `equity_risk_premium` | Strategy 3: passthrough --> whole string |
| **Resolved field** | `equity_risk_premium` | `Computed: SPY earnings yield (1/PE) minus 10Y Treasury yield` |
| **Value from briefing** | `0.17` (from `computed` section) | `None` (field doesn't exist) |
| **Threshold check** | 0.17 < 1.0 --> **TRIGGERED** | Cannot check (None) --> untriggered |

#### 2. Short-term Cash Yield Exceeds Equity Earnings Yield (weight: 0.15)

| | v1 metric_source | v2 metric_source |
|--|--|--|
| **String** | `` `rates.fed_funds` or SHY yield vs. SPY earnings yield `` | `Computed: SHY yield (or fed funds rate) vs. SPY earnings yield (1/PE)` |
| **Resolution strategy** | Strategy 2: backtick extraction --> `rates.fed_funds` | Strategy 3: passthrough --> whole string |
| **Resolved field** | `rates.fed_funds` | `Computed: SHY yield (or fed funds rate)...` |
| **Value from briefing** | `3.64` (from `rates` section) | `None` |
| **Threshold check** | 3.64 > 1.0 --> **TRIGGERED** | Cannot check --> untriggered |

#### 3. Market Breadth Narrow (weight: 0.10)

| | v1 metric_source | v2 metric_source |
|--|--|--|
| **String** | `` computed: `qqq_iwm_ratio` + RSP vs SPY relative performance `` | `Computed: QQQ/IWM ratio + RSP vs. SPY relative performance` |
| **Resolution strategy** | Strategy 2: backtick extraction --> `qqq_iwm_ratio` | Strategy 3: passthrough --> whole string |
| **Resolved field** | `qqq_iwm_ratio` | `Computed: QQQ/IWM ratio + RSP vs. SPY...` |
| **Value from briefing** | `2.3279` (from `computed` section) | `None` |
| **Threshold check** | 2.3279 > 2.0 --> **TRIGGERED** | Cannot check --> untriggered |

### Scoring Math

**v1 (old loader):**
- Buffett Indicator: SKIPPED (web-search, data unavailable). Not counted in denominator.
- Total mechanical weight: 1.00 - 0.15 (skipped) = **0.85**
- Triggered weight: 0.25 (ERP) + 0.20 (CAPE) + 0.15 (cash yield) + 0.10 (breadth) + 0.05 (insider) = **0.75**
- Score: **0.75 / 0.85 = 0.882 (Active)**

**v8 (new loader):**
- Buffett Indicator: SKIPPED (web-search, data unavailable). Not counted.
- Total mechanical weight: 1.00 - 0.15 (skipped) = **0.85** (same denominator)
- Triggered weight: 0.20 (CAPE) + 0.05 (insider) = **0.25**
- Lost triggers: 0.25 (ERP) + 0.15 (cash yield) + 0.10 (breadth) = 0.50
- Score: **0.25 / 0.85 = 0.294 (Inactive)**

### Indicators That Work Correctly in v8

| Indicator | Weight | Resolves? | Triggered? |
|-----------|--------|-----------|------------|
| Shiller CAPE elevated | 0.20 | Yes (`web-search` --> WEB_FIELD_MAP --> `shiller_cape`) | Yes (37.94 > 30) |
| Buffett Indicator extreme | 0.15 | Yes (same path --> `buffett_indicator`) | Skipped (data unavailable) |
| Corporate profit margins | 0.10 | Yes (same path --> `sp500_net_margin`) | No (8.86 < 12) |
| Insider selling elevated | 0.05 | Yes (same path --> `insider_sell_buy_ratio`) | Yes (10.11 > 5) |

All `web-search` indicators work because `_entry_to_indicator()` re-injects the `"web search: "` prefix based on `data_ownership`. The three broken indicators are all `computed-mechanical` -- this data_ownership category has no equivalent prefix re-injection.

---

## Case 2: `fiscal_dominance_arithmetic`

**Score change:** 0.556 (Adjacent) --> 0.056 (Inactive)

### Broken Indicators

Three indicators fail. Two changed `data_ownership` from `web-search` to `computed-mechanical`, losing the web-search resolution path. One lost its backtick field name.

#### 1. Interest Expense / Tax Receipts Ratio (weight: 0.25)

| | v1 metric_source | v2 metric_source |
|--|--|--|
| **String** | `Web search: US Treasury Monthly Statement, CBO projections` | `FRED: FYOINT (federal interest outlays), FGRECPT (federal receipts)` |
| **v1 data_ownership** | `web-search` (implicit from "Web search:" prefix) | -- |
| **v2 data_ownership** | -- | `computed-mechanical` |
| **Resolution** | Strategy 1: "treasury monthly statement" matches WEB_FIELD_MAP --> `interest_receipts_ratio` | Strategy 3: passthrough --> whole FRED string |
| **Value** | `34.0` | `None` |
| **Result** | 34.0 > 20 --> **TRIGGERED** | Untriggered (None) |

**What changed:** The v2 ACTIVATION.md reclassified this indicator from `web-search` to `computed-mechanical` (because the underlying FRED series FYOINT/FGRECPT are API-accessible). This is semantically correct -- the data IS computable from FRED. But it broke the resolution path: `_entry_to_indicator()` only re-injects `"web search: "` when `data_ownership == "web-search"`. With `computed-mechanical`, no prefix is added, and the FRED series names don't match any WEB_FIELD_MAP entry or backtick pattern.

#### 2. Deficit Pace Outside Recession (weight: 0.20)

| | v1 metric_source | v2 metric_source |
|--|--|--|
| **String** | `Web search: US Treasury monthly budget statements + NBER recession dating` | `FRED: FYFSD (federal surplus/deficit), USREC (recession indicator); trailing annualized computation` |
| **v1 data_ownership** | `web-search` | -- |
| **v2 data_ownership** | -- | `computed-mechanical` |
| **Resolution** | Strategy 1: "treasury monthly budget statements + nber" matches WEB_FIELD_MAP --> `deficit_pace_annualized` | Strategy 3: passthrough --> whole FRED string |
| **Value** | `3690.0` | `None` |
| **Result** | 3690.0 > 1.5 --> **TRIGGERED** | Untriggered (None) |

Same pattern: reclassified from `web-search` to `computed-mechanical`, broke the WEB_FIELD_MAP lookup.

#### 3. Gold/Oil Ratio Elevated (weight: 0.10)

| | v1 metric_source | v2 metric_source |
|--|--|--|
| **String** | `` computed: `gold_oil_ratio` `` | `Computed: gold price / oil price (Yahoo Finance)` |
| **Resolution** | Strategy 2: backtick --> `gold_oil_ratio` | Strategy 3: passthrough --> whole string |
| **Value** | `3.11` (from `computed` section) | `None` |
| **Result** | 3.11 < 25 --> not triggered (but resolvable) | Untriggered (None) |

Same class as the valuation_mean_reversion bugs: backtick field name removed.

### Scoring Math

**v1 (old loader):**
- "No credible deficit reduction plan" (0.10): SKIPPED (web-search, no WEB_FIELD_MAP match). Not counted.
- Total mechanical weight: 1.00 - 0.10 = **0.90**
- Triggered: 0.25 (interest/receipts) + 0.20 (deficit pace) + 0.05 (CB gold) = **0.50**
- Score: **0.50 / 0.90 = 0.556 (Adjacent)**

**v8 (new loader):**
- "No credible deficit reduction plan" moved to context_flags (intentional, correct). Weight removed from table.
- Total mechanical weight: **0.90**
- Triggered: 0.05 (CB gold) = **0.05**
- Lost triggers: 0.25 (interest/receipts) + 0.20 (deficit pace) = 0.45 (gold/oil was already not triggered in v1)
- Score: **0.05 / 0.90 = 0.056 (Inactive)**

### Indicators That Work Correctly in v8

| Indicator | Weight | Resolves? | Triggered? |
|-----------|--------|-----------|------------|
| Interest exceeds discretionary | 0.15 | Yes (`web-search` --> `interest_exceeds_defense`) | No (threshold parsing issue, pre-existing) |
| Debt rollover at higher rates | 0.15 | Yes (`web-search` --> `weighted_avg_interest_rate`) | No (3.355 not rising by threshold logic) |
| CB gold purchases | 0.05 | Yes (`web-search` --> `cb_gold_purchases`) | Yes (1037 > 800) |

---

## Case 3: `capital_flows`

**Score change:** 0.450 (Adjacent, Rotation phase) --> Inactive (both phases below 0.30)

This theory has TWO issues:
1. **Intentional:** Two qualitative indicators (0.25 total weight) moved from Phase A activation_table to context_flags. This is correct per the data_ownership spec.
2. **Bug:** Multiple indicators across both phases lost backtick field names and "Web search:" prefixes, breaking field resolution.

### Phase A: Accumulation

| # | Indicator | Weight | v1 metric_source | v1 Resolves To | v2 metric_source | v2 Resolves To | Bug? |
|---|-----------|--------|------------------|---------------|------------------|---------------|------|
| 1 | EM vs. DM PE gap | 0.25 (v1) / 0.33 (v2) | `Web search: MSCI EM PE vs. MSCI World PE, or EEM PE vs. SPY PE` | `em_dm_pe_gap` | `MSCI EM PE vs. MSCI World PE, or broad EM vs. broad DM PE ratios` | `em_dm_pe_gap` (via web-search re-injection) | No |
| 2 | EM 3-year underperformance | 0.20 / 0.27 | `` computed: `eem_spy_3y_relative` `` | `eem_spy_3y_relative` --> 9.5 | `EEM vs. SPY cumulative rolling 3-year relative return` | whole string --> None | **Yes** |
| 3 | Dollar strong or sideways | 0.15 / 0.20 | `` `DX-Y.NYB` (DXY) or `UUP` `` | `UUP` --> None (no market data by ticker) | `DXY index` | whole string --> None | **Yes** (but v1 also failed to resolve) |
| 4 | China credit impulse | 0.15 / 0.20 | `Web search: China credit impulse data, total social financing` | `china_credit_impulse` --> 3.5 | `China total social financing growth, credit impulse calculation` | `china_credit_impulse` (via web-search) | No |
| 5 | No EM-positive catalysts | 0.15 / -- | `Composite qualitative check` | whole string --> None | *Moved to context_flags* | -- | N/A (intentional) |
| 6 | Geopolitical risk | 0.10 / -- | `Web search: US-China relations...` | None (no WEB_FIELD_MAP match) | *Moved to context_flags* | -- | N/A (intentional) |

**Phase A v1 score:** 0.35 (triggered) / 0.90 (total minus skipped) = 0.389 (Adjacent)
**Phase A v8 score:** 0.20 (China credit only) / 1.00 = 0.200 (Inactive)

### Phase B: Rotation

| # | Indicator | Weight | v1 metric_source | v1 Resolves To | v2 metric_source | v2 Resolves To | Bug? |
|---|-----------|--------|------------------|---------------|------------------|---------------|------|
| 1 | Dollar weakening | 0.25 | `` `DX-Y.NYB` (DXY) or `UUP` `` | `UUP` --> None | `DXY index` | whole string --> None | **Yes** (but v1 also failed) |
| 2 | China credit impulse+ | 0.20 | `Web search: China credit impulse, total social financing growth` | `china_credit_impulse` --> 3.5 | `China total social financing, credit impulse` | `china_credit_impulse` (via web-search) | No |
| 3 | RMB strengthening | 0.20 | `Web search: USD/CNY spot rate, CNH offshore rate` | `usdcny` --> 6.8947 | `USD/CNY spot rate` | whole string --> None | **Yes** |
| 4 | EM outperforming DM | 0.15 | `` computed: `eem_spy_3m_relative` `` | `eem_spy_3m_relative` --> 7.27 | `EEM vs. SPY 3-month relative return` | whole string --> None | **Yes** |
| 5 | Commodity prices rising | 0.10 | `` `DBC` or computed: `commodity_index_3m_change` `` | `commodity_index_3m_change` --> 31.17 | `Broad commodity index (DBC or equivalent)` | whole string --> None | **Yes** |
| 6 | Chinese equities leading | 0.10 | `` computed: `fxi_3m_return` or `kweb_3m_return` `` | `kweb_3m_return` --> -17.5 | `FXI 3-month return from low` | whole string --> None | **Yes** |

**Phase B v1 score:** 0.45 / 1.00 = 0.450 (Adjacent) <-- effective score, Phase B takes priority
**Phase B v8 score:** 0.20 / 1.00 = 0.200 (Inactive)

### Notable: RMB Strengthening (Phase B, indicator #3)

This indicator changed `data_ownership` from `web-search` to `mechanical`. In v1, the "Web search:" prefix triggered WEB_FIELD_MAP lookup, which matched `"usd/cny"` --> `usdcny`. In v2, ownership is `mechanical` so no prefix is re-injected, and the plain string `"USD/CNY spot rate"` has no backticks and doesn't match anything.

This is the same class of bug as `fiscal_dominance_arithmetic` indicators 1 and 2: a correct data_ownership reclassification broke the resolution path that the old ownership accidentally enabled.

---

## Common Root Cause

All three theories exhibit the same failure pattern:

```
v1 metric_source format               -->  Resolution strategy  -->  Result
------------------------------------       -------------------       ------
computed: `field_name` (description)       Backtick extraction       field_name
Web search: descriptive keywords           WEB_FIELD_MAP lookup      mapped_field
`ticker` or `field`                        Backtick extraction       field_name

v2 metric_source format               -->  Resolution strategy  -->  Result
------------------------------------       -------------------       ------
Computed: human-readable description       Passthrough               whole string --> None
FRED: SERIES_NAME (description)            Passthrough               whole string --> None
Descriptive text without backticks         Passthrough               whole string --> None
```

The v2 ACTIVATION.md files were rewritten to be more readable and to accurately reflect data sources (FRED series names, descriptive computations). This is good documentation. But the engine's field resolution was never updated to parse the new format.

### Why This Wasn't Caught

The v8 migration testing classified these three theories as "KNOWN_DIVERGED" based on automated Layer 1 tests that found the reorganisation changed their indicator count and/or metric_source format. The 5 structurally divergent theories were documented and the divergence was accepted as an expected consequence of the reorganisation. The assumption was that the divergence was intentional. It was not investigated further.

---

## Summary of All Broken Indicators

### Indicators where v2 lost backtick field names (`computed-mechanical`)

| Theory | Indicator | Weight | v1 Field | v2 Field |
|--------|-----------|--------|----------|----------|
| `valuation_mean_reversion` | Equity risk premium compressed | 0.25 | `equity_risk_premium` | None |
| `valuation_mean_reversion` | Short-term cash yield exceeds equity earnings yield | 0.15 | `rates.fed_funds` | None |
| `valuation_mean_reversion` | Market breadth narrow | 0.10 | `qqq_iwm_ratio` | None |
| `fiscal_dominance_arithmetic` | Gold/oil ratio elevated | 0.10 | `gold_oil_ratio` | None |
| `capital_flows` (Phase A) | EM rolling 3-year underperformance | 0.27 | `eem_spy_3y_relative` | None |
| `capital_flows` (Phase B) | EM outperforming DM on relative basis | 0.15 | `eem_spy_3m_relative` | None |
| `capital_flows` (Phase B) | Commodity prices rising | 0.10 | `commodity_index_3m_change` | None |
| `capital_flows` (Phase B) | Chinese equities leading | 0.10 | `kweb_3m_return` | None |

### Indicators where v2 changed data_ownership, breaking resolution path

| Theory | Indicator | Weight | v1 Ownership | v2 Ownership | v1 Resolved Via | v2 Resolved Via |
|--------|-----------|--------|-------------|-------------|-----------------|-----------------|
| `fiscal_dominance_arithmetic` | Interest expense / tax receipts ratio | 0.25 | `web-search` | `computed-mechanical` | WEB_FIELD_MAP --> `interest_receipts_ratio` | Passthrough --> None |
| `fiscal_dominance_arithmetic` | Deficit pace outside recession | 0.20 | `web-search` | `computed-mechanical` | WEB_FIELD_MAP --> `deficit_pace_annualized` | Passthrough --> None |
| `capital_flows` (Phase B) | RMB strengthening | 0.20 | `web-search` | `mechanical` | WEB_FIELD_MAP --> `usdcny` | Passthrough --> None |

### Indicators where v2 lost backtick ticker names (`mechanical`)

| Theory | Indicator | Weight | v1 Field | v2 Field | Note |
|--------|-----------|--------|----------|----------|------|
| `capital_flows` (Phase A) | Dollar strong or sideways | 0.20 | `UUP` (failed in v1 too -- no market data by ticker) | None | Pre-existing issue in both |
| `capital_flows` (Phase B) | Dollar weakening | 0.25 | `UUP` (failed in v1 too) | None | Pre-existing issue in both |

---

## Intentional Changes (Not Bugs)

For completeness, the following changes are intentional and correct:

| Theory | Change | Effect |
|--------|--------|--------|
| `capital_flows` | "No EM-positive catalysts firing yet" (0.15) moved to context_flags | Phase A loses qualitative scoring ballast. Correct per data_ownership spec: this is a composite qualitative check. |
| `capital_flows` | "Geopolitical risk not escalating" (0.10) moved to context_flags | Same rationale. No mechanical threshold exists for geopolitical risk. |
| `fiscal_dominance_arithmetic` | "No credible deficit reduction plan" (0.10) moved to context_flags | Same rationale. Political will is not mechanically scorable. |
| All three | Weight redistribution in remaining indicators | Correct renormalization after indicator removal. |

---

## Appendix: Full Indicator Traces

### How to reproduce

```bash
python -m scripts.v8_equivalence_check
```

This script restores the old `theory_parser.py` and monolithic theory files from git history (commit `d7f3767`), runs both old and new activation scoring on the same briefing packet, and prints comparison tables. It cleans up after itself.

### Briefing packet values referenced

From `data/briefing_packet.json` (2026-04-03):

| Field | Section | Value |
|-------|---------|-------|
| `equity_risk_premium` | `computed` | 0.17 |
| `shiller_cape` | `web_sourced` | 37.94 |
| `rates.fed_funds` | `rates` | 3.64 |
| `qqq_iwm_ratio` | `computed` | 2.3279 |
| `insider_sell_buy_ratio` | `web_sourced` | 10.1111 |
| `sp500_net_margin` | `web_sourced` | 8.8621 |
| `interest_receipts_ratio` | `computed` | 34.0 |
| `deficit_pace_annualized` | `computed` | 3690.0 |
| `gold_oil_ratio` | `computed` | 3.11 |
| `cb_gold_purchases` | `web_sourced` | 1037.0 |
| `weighted_avg_interest_rate` | `web_sourced` | 3.355 |
| `interest_exceeds_defense` | `computed` | 287.0 |
| `china_credit_impulse` | `web_sourced` | 3.5 |
| `em_dm_pe_gap` | `web_sourced` | 11.284 |
| `eem_spy_3m_relative` | `computed` | 7.27 |
| `eem_spy_3y_relative` | `computed` | 9.5 |
| `commodity_index_3m_change` | `computed` | 31.17 |
| `kweb_3m_return` | `computed` | -17.5 |
| `fxi_3m_return` | `computed` | -7.13 |
| `usdcny` | `web_sourced` | 6.8947 |
| `buffett_indicator` | -- | Missing (WILL5000INDFC unavailable) |

---

## Files to Attach

When sending this docket, attach the following files for complete context:

1. **This docket:** `docs/V8_DIVERGENCE_DOCKET.md`

2. **The three v2 ACTIVATION.md files** (the files with the bugs):
   - `theories/THEORY_MODULE_valuation_mean_reversion_v2/ACTIVATION.md`
   - `theories/THEORY_MODULE_fiscal_dominance_arithmatic_v2/ACTIVATION.md`
   - `theories/THEORY_MODULE_capital_flows_v2/ACTIVATION.md`

3. **The field resolution code:**
   - `backend/engine/activation.py` -- particularly `_extract_metric_field()` (lines 257-291), `_entry_to_indicator()` (lines 410-433), and `WEB_FIELD_MAP` (lines 32-88)

4. **The activation table parser:**
   - `backend/engine/theory_loader.py` -- particularly `parse_activation_table()` (line 666+) and `_parse_activation_rows()` (line 584+)

5. **The briefing packet used for testing:**
   - `data/briefing_packet.json`

6. **The equivalence check script** (reproduces all findings):
   - `scripts/v8_equivalence_check.py`

7. **For reference, the old v1 monolithic files** can be retrieved from git:
   ```bash
   git show d7f3767:theories/old_format/THEORY_MODULE_valuation_mean_reversion_v1.md
   git show d7f3767:theories/old_format/THEORY_MODULE_fiscal_dominance_arithmetic_v1.md
   git show d7f3767:theories/old_format/THEORY_MODULE_capital_flows_v1.md
   ```
