# V8 Pre-Remediation Baseline Artifact

**Generated:** 2026-04-06
**Purpose:** Frozen record of the broken v8 state BEFORE any remediation task begins. All later tasks diff against this artifact, not memory.
**Briefing packet:** `data/briefing_packet.json` timestamped 2026-04-03T14:14:56+00:00
**Equivalence script:** `scripts/v8_equivalence_check.py` (restores v1 parser from commit `d7f3767`)
**Test suite:** 675/675 passing (`backend/tests/`)

---

## 1. Equivalence Check Summary (3 runs)

All three runs classify the same 3 theories as DIVERGED. The script reports "ALL PASS" because the diverged theories are in the `KNOWN_DIVERGED` set -- the script was designed to accept the divergence, not to flag it as a bug.

### Classification

| Theory | Classification | Notes |
|--------|---------------|-------|
| `debt_cycle_short` | EXACT MATCH | Scores identical across all 3 runs |
| `fiscal_dominance_liquidity` | EXACT MATCH | Scores identical across all 3 runs |
| `structural_fragility` | EXACT MATCH | Scores identical across all 3 runs |
| `debt_cycle_long` | TIER MATCH | 0.889 vs 0.900 (both Active) |
| `monetary_architecture` | TIER MATCH | 0.455 vs 0.408 (both Adjacent) |
| `valuation_mean_reversion` | **DIVERGED** | 0.882 Active --> 0.294 Inactive |
| `fiscal_dominance_arithmetic` | **DIVERGED** | 0.556 Adjacent --> 0.056 Inactive |
| `capital_flows` | **DIVERGED** | 0.450 Adjacent --> N/A Inactive |

### Run 1: Real Briefing (2026-04-03)

| Theory | v1 Score | v8 Score | v1 Tier | v8 Tier | Phase |
|--------|----------|----------|---------|---------|-------|
| `capital_flows` | 0.450 | N/A | Adjacent | Inactive | Rotation -> (lost) |
| `debt_cycle_long` | 0.889 | 0.900 | Active | Active | |
| `debt_cycle_short` | 0.471 | 0.471 | Adjacent | Adjacent | Contraction |
| `fiscal_dominance_arithmetic` | 0.556 | 0.056 | Adjacent | Inactive | |
| `fiscal_dominance_liquidity` | 0.700 | 0.700 | Active | Active | |
| `monetary_architecture` | 0.455 | 0.408 | Adjacent | Adjacent | |
| `structural_fragility` | 0.353 | 0.353 | Adjacent | Adjacent | Fragility Building |
| `valuation_mean_reversion` | 0.882 | 0.294 | Active | Inactive | |

### Run 2: Stress Scenario (synthetic)

| Theory | v1 Score | v8 Score | v1 Tier | v8 Tier |
|--------|----------|----------|---------|---------|
| `capital_flows` | 0.450 | N/A | Adjacent | Inactive |
| `debt_cycle_long` | 1.000 | 1.000 | Active | Active |
| `debt_cycle_short` | 0.647 | 0.647 | Active | Active |
| `fiscal_dominance_arithmetic` | 0.556 | 0.056 | Adjacent | Inactive |
| `fiscal_dominance_liquidity` | 0.600 | 0.600 | Active | Active |
| `monetary_architecture` | 0.455 | 0.408 | Adjacent | Adjacent |
| `structural_fragility` | 0.533 | 0.533 | Adjacent | Adjacent |
| `valuation_mean_reversion` | 0.882 | 0.294 | Active | Inactive |

### Run 3: Recovery Scenario (synthetic)

| Theory | v1 Score | v8 Score | v1 Tier | v8 Tier |
|--------|----------|----------|---------|---------|
| `capital_flows` | 0.450 | N/A | Adjacent | Inactive |
| `debt_cycle_long` | 0.889 | 0.900 | Active | Active |
| `debt_cycle_short` | 0.471 | 0.471 | Adjacent | Adjacent |
| `fiscal_dominance_arithmetic` | 0.556 | 0.056 | Adjacent | Inactive |
| `fiscal_dominance_liquidity` | 0.800 | 0.800 | Active | Active |
| `monetary_architecture` | 0.455 | 0.408 | Adjacent | Adjacent |
| `structural_fragility` | 0.412 | 0.412 | Adjacent | Adjacent |
| `valuation_mean_reversion` | 0.471 | 0.294 | Adjacent | Inactive |

---

## 2. v8 Per-Indicator Breakdown: Broken Theories (Real Briefing)

### 2.1 `valuation_mean_reversion` -- v8 score: 0.294, Tier: Inactive

| Indicator | Triggered | Value | metric_field (resolved) | Reason |
|-----------|-----------|-------|------------------------|--------|
| Equity risk premium compressed | No | null | `Computed: SPY earnings yield (1/PE) minus 10Y Treasury yield` | data not available (passthrough -- no backtick) |
| Shiller CAPE elevated | **Yes** | 37.94 | `shiller_cape` | web-search resolution works |
| Short-term cash yield exceeds equity earnings yield | No | null | `Computed: SHY yield (or fed funds rate) vs. SPY earnings yield (1/PE)` | data not available (passthrough) |
| Corporate profit margins at cycle highs | No | 8.86 | `sp500_net_margin` | web-search works; 8.86 < 12 threshold |
| Market breadth narrow | No | null | `Computed: QQQ/IWM ratio + RSP vs. SPY relative performance` | data not available (passthrough) |
| Insider selling elevated | **Yes** | 10.11 | `insider_sell_buy_ratio` | web-search works |
| Buffett Indicator extreme | SKIPPED | -- | -- | web data not available |

**Broken indicators (3):** Equity risk premium, Cash yield, Market breadth. All `computed-mechanical` with prose metric_source strings. Weight: 0.50/1.00.
**v1 score with same briefing:** 0.882 (Active).

### 2.2 `fiscal_dominance_arithmetic` -- v8 score: 0.056, Tier: Inactive

| Indicator | Triggered | Value | metric_field (resolved) | Reason |
|-----------|-----------|-------|------------------------|--------|
| Interest expense / tax receipts ratio | No | null | `FRED: FYOINT (federal interest outlays), FGRECPT (federal receipts)` | passthrough (ownership changed web-search -> computed-mechanical) |
| Interest expense exceeds major discretionary category | No | 287.0 | `interest_exceeds_defense` | web-search works; but 287 < 886 (BUG-05: extracts wrong number from threshold) |
| Deficit pace outside recession | No | null | `FRED: FYFSD (federal surplus/deficit), USREC...` | passthrough (ownership changed) |
| Debt rollover at higher rates | No | 3.355 | `weighted_avg_interest_rate` | web-search works; RISING direction (BUG-03) |
| Gold/oil ratio elevated | No | null | `Computed: gold price / oil price (Yahoo Finance)` | passthrough (lost backtick) |
| Central bank gold purchases sustained | **Yes** | 1037.0 | `cb_gold_purchases` | web-search works |

**Broken indicators (3):** Interest/receipts ratio, Deficit pace, Gold/oil ratio. Weight: 0.55/0.90.
**Additional pre-existing bugs on working indicators:** BUG-05 (interest_exceeds_defense threshold), BUG-03 (RISING direction).
**v1 score with same briefing:** 0.556 (Adjacent).

### 2.3 `capital_flows` -- v8 score: N/A (both phases Inactive), Effective tier: Inactive

#### Phase A: Accumulation (score: 0.200)

| Indicator | Triggered | Value | metric_field | Reason |
|-----------|-----------|-------|-------------|--------|
| EM vs. DM PE gap at extremes | No | 11.284 | `em_dm_pe_gap` | web-search works; 11.28 below threshold |
| EM rolling 3-year underperformance | No | null | `EEM vs. SPY cumulative rolling 3-year relative return` | passthrough (lost backtick) |
| Dollar strong or sideways | No | null | `DXY index` | passthrough (lost backtick; also failed in v1) |
| China credit impulse flat or negative | **Yes** | 3.5 | `china_credit_impulse` | web-search works; direction "above" (BUG-02 accidental) |

#### Phase B: Rotation (score: 0.200)

| Indicator | Triggered | Value | metric_field | Reason |
|-----------|-----------|-------|-------------|--------|
| Dollar weakening | No | null | `DXY index` | passthrough (lost backtick; also failed in v1) |
| China credit impulse positive and accelerating | **Yes** | 3.5 | `china_credit_impulse` | web-search works |
| RMB strengthening | No | null | `USD/CNY spot rate` | passthrough (ownership changed web-search -> mechanical) |
| EM outperforming DM on relative basis | No | null | `EEM vs. SPY 3-month relative return` | passthrough (lost backtick) |
| Commodity prices rising | No | null | `Broad commodity index (DBC or equivalent)` | passthrough (lost backtick) |
| Chinese equities leading | No | null | `FXI 3-month return from low` | passthrough (lost backtick) |

**Broken indicators (7 across both phases):** EM 3-year, Dollar (both phases), RMB, EM outperforming, Commodities, Chinese equities. Weight: ~0.82 across phases.
**Pre-existing failures (2):** Dollar indicators (DXY index) failed in v1 too -- ticker-based field name with no market data.
**v1 score with same briefing:** 0.450 (Adjacent, Rotation phase active).

---

## 3. v8 Per-Indicator Breakdown: Working Theories (Real Briefing)

### 3.1 `debt_cycle_long` -- v8 score: 0.900, Tier: Active

| Indicator | Triggered | Value | Weight | metric_field |
|-----------|-----------|-------|--------|-------------|
| Total debt / GDP above historical warning level | **Yes** | 256.72 | 0.25 | `total_debt_to_gdp` |
| Fed balance sheet / GDP elevated | **Yes** | 6675344.0 | 0.25 | `liquidity.fed_balance_sheet` |
| Rates at or near effective lower bound | **Yes** | 3.64 | 0.15 | `rates.fed_funds` |
| Fiscal deficit as primary growth driver | **Yes** | 287.0 | 0.15 | `interest_exceeds_defense` |
| Wealth inequality at cycle-characteristic extremes | **Yes** | 68.1 | 0.10 | `top10_wealth_share` |
| Negative real rates during expansion | No | 2.66 | 0.10 | `inflation.cpi_yoy` |

**Note:** "Fiscal deficit as primary growth driver" resolves to `interest_exceeds_defense` and triggers because 287 > threshold. The direction strings "negative", "at or near floor recently", "above / below respectively" are all BUG-02 cases that happen to produce acceptable results here by accident.

### 3.2 `debt_cycle_short` -- v8 score: N/A (two-phase), Tier: Adjacent (Contraction)

Phase A (Expansion): score 0.765, tier Active
Phase B (Contraction): score 0.471, tier Adjacent
Effective: Contraction (Adjacent) -- Phase B checked first, is Adjacent (not Active), so Phase A applies... but Phase B takes priority per two-phase logic.

13 total indicators across both phases. All resolve correctly. Skipped: 2 (SLOOS, Net credit growth -- web data not available).

### 3.3 `fiscal_dominance_liquidity` -- v8 score: 0.700, Tier: Active

7 indicators, all resolve correctly. 4 triggered (net liquidity, deficit pace, rate hikes not producing recession, hard assets outperforming). 3 untriggered (RRP, Fed BS direction, TGA).

### 3.4 `monetary_architecture` -- v8 score: 0.408, Tier: Adjacent

| Indicator | Triggered | Value | metric_field | Note |
|-----------|-----------|-------|-------------|------|
| CB gold purchases sustained | **Yes** | 1037.0 | `cb_gold_purchases` | works |
| Foreign official Treasury holdings declining | No | null | (prose passthrough) | BUG-01 class -- data not available |
| Gold/oil ratio elevated and rising | No | null | (prose passthrough) | BUG-01 class -- data not available |

**Note:** `monetary_architecture` has 2 indicators that fail via the same passthrough bug class as the 3 broken theories, but it was classified as TIER MATCH because the v1 loader also could not resolve these (they used "Web search:" keywords that had no WEB_FIELD_MAP entry). The score difference (0.455 vs 0.408) comes from different denominator handling. 2 indicators skipped (cross-currency basis, non-dollar settlement -- no field mapping).

### 3.5 `structural_fragility` -- v8 score: N/A (two-phase), Tier: Adjacent (Fragility Building)

Phase A (Fragility Resolving): score 0.000, tier Inactive
Phase B (Fragility Building): score 0.353, tier Adjacent
Effective: Fragility Building (Adjacent)

9 indicators. 3 triggered in Building phase (margin debt, large/small cap divergence, passive fund share). 1 skipped (capex/revenue mismatch -- no field mapping). 1 unresolved (top-10 index concentration -- no data).

---

## 4. Bug and Fragility Inventory

### 4.1 Confirmed Bugs (from V8_IMPLICIT_CONTRACT_AUDIT.md)

| ID | Description | Severity | Migration-specific? |
|----|-------------|----------|-------------------|
| BUG-01 | metric_source field resolution broken for 3 theories (13 indicators) | Critical | Yes |
| BUG-02 | Non-standard direction strings silently default to "above" (10 indicators, 5 theories) | Medium | Pre-existing |
| BUG-03 | RISING/FALLING treated as simple threshold comparison | Medium | Pre-existing |
| BUG-04 | `_normalize_computed_field()` generic fallback produces garbage field names | Medium | Pre-existing (masked by BUG-01) |
| BUG-05 | `_extract_number()` strips unit suffixes without scaling; mishandles `interest_exceeds_defense` | Low-Medium | Pre-existing |
| BUG-06 | `data_ownership` parse fallback can silently yield invalid values | Low | Pre-existing (not currently triggered) |

### 4.2 High-Risk Fragilities

| ID | Description | Currently triggered? |
|----|-------------|---------------------|
| FRAGILITY-01 | Section headers require exact underscore format | No |
| FRAGILITY-02 | Activation table assumes fixed column positions | No |
| FRAGILITY-03 | Phase naming requires exact `Phase A:` / `Phase B:` | No |
| FRAGILITY-04 | Context flags default to `qualitative` when ownership column absent | No (1 theory omits column, correctly all qualitative) |
| FRAGILITY-05 | Falsifier severity inferred from free text in any cell | No |
| FRAGILITY-06 | Falsifier ID extraction searches all cells as fallback | No |
| FRAGILITY-07 | `_extract_metric_field()` passthrough returns whole strings | **YES** -- root cause of BUG-01 |
| FRAGILITY-08 | Non-numeric weights silently drop indicators | No |
| FRAGILITY-09 | Short rows silently dropped | No |
| FRAGILITY-10 | `theory_id` extraction depends on narrow markdown patterns | No |
| FRAGILITY-11 | Mixed two-phase activation table formats tolerated | No |

---

## 5. Test Suite State

**675 tests passing** in `backend/tests/` as of 2026-04-06.

The tests accept the current broken state because:
- The v8 equivalence script classifies `valuation_mean_reversion`, `fiscal_dominance_arithmetic`, and `capital_flows` as `KNOWN_DIVERGED` and marks them as "OK"
- The test infrastructure tests the parser and scorer in isolation, not the end-to-end field resolution for these specific theories
- No test asserts "valuation_mean_reversion should score 0.882" -- the scoring math tests use synthetic inputs, not the actual theory packages

---

## 6. Equivalence Script Raw Output (abbreviated)

```
Run 1: Real Briefing (2026-04-03)
  capital_flows                      0.450     N/A  Adjacent   Inactive   DIVERGED  DIVERGED  Rotation ->   OK
  debt_cycle_long                    0.889   0.900  Active     Active     TIER      TIER        OK
  debt_cycle_short                   0.471   0.471  Adjacent   Adjacent   EXACT     EXACT     Contraction  OK
  fiscal_dominance_arithmetic        0.556   0.056  Adjacent   Inactive   DIVERGED  DIVERGED    OK
  fiscal_dominance_liquidity         0.700   0.700  Active     Active     EXACT     EXACT       OK
  monetary_architecture              0.455   0.408  Adjacent   Adjacent   TIER      TIER        OK
  structural_fragility               0.353   0.353  Adjacent   Adjacent   EXACT     EXACT     Fragility Building  OK
  valuation_mean_reversion           0.882   0.294  Active     Inactive   DIVERGED  DIVERGED    OK

Overall: ALL PASS -- safe to check off plan_v8.md items
```

The "ALL PASS" is misleading: it means "all divergences match the expected classification," not "all scores are correct." This is the artifact the remediation will fix.

---

## 7. Key Reference Fields from Briefing Packet

These are the briefing values used in the indicator checks above, for reproducibility:

| Field | Section | Value |
|-------|---------|-------|
| `equity_risk_premium` | computed | 0.17 |
| `shiller_cape` | web_sourced | 37.94 |
| `rates.fed_funds` | rates | 3.64 |
| `qqq_iwm_ratio` | computed | 2.3279 |
| `insider_sell_buy_ratio` | web_sourced | 10.1111 |
| `sp500_net_margin` | web_sourced | 8.8621 |
| `interest_receipts_ratio` | computed | 34.0 |
| `deficit_pace_annualized` | computed | 3690.0 |
| `gold_oil_ratio` | computed | 3.11 |
| `cb_gold_purchases` | web_sourced | 1037.0 |
| `weighted_avg_interest_rate` | web_sourced | 3.355 |
| `interest_exceeds_defense` | computed | 287.0 |
| `china_credit_impulse` | web_sourced | 3.5 |
| `em_dm_pe_gap` | web_sourced | 11.284 |
| `eem_spy_3m_relative` | computed | 7.27 |
| `eem_spy_3y_relative` | computed | 9.5 |
| `commodity_index_3m_change` | computed | 31.17 |
| `kweb_3m_return` | computed | -17.5 |
| `fxi_3m_return` | computed | -7.13 |
| `usdcny` | web_sourced | 6.8947 |
| `buffett_indicator` | -- | Missing |
