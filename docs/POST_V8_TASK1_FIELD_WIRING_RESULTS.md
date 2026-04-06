# Post-v8 Task 1: Field Wiring Remediation Results

**Date:** 2026-04-06
**Baseline:** `docs/POST_V8_SEMANTIC_BASELINE.md` (frozen 2026-04-06, commit 86a45f5)
**Test suite:** 983 tests passing (unchanged)

---

## 1. Affected indicators -- before/after

| # | Audit | Theory | Indicator | Old field/value | New field/value | Old triggered | New triggered | Reason |
|---|-------|--------|-----------|----------------|-----------------|---------------|---------------|--------|
| 1 | A-01 | fiscal_dom_arith | Gold/oil ratio elevated | gold_oil_ratio=3.11 (GLD/USO ETF) | gold_oil_ratio=42.3 (GC=F/CL=F commodity) | False (3.11 < 25) | True (42.3 > 25) | Commodity futures, not ETF proxy |
| 2 | A-01+D-03 | monetary_arch | Gold/oil ratio elevated and rising | None (no backtick ref + ETF proxy) | gold_oil_ratio=42.3 | Dead (unresolvable) | True (42.3 > 25) | Backtick `gold_oil_ratio` + commodity fix |
| 3 | C-01 | debt_cycle_long | Fed BS / GDP elevated | liquidity.fed_balance_sheet=6,675,344 vs 20 | fed_bs_gdp_ratio=21.2 vs 20 | True (by accident: 6.6M >> 20) | True (correct: 21.2% > 20%) | Field wiring to pre-computed ratio |
| 4 | A-07 | capital_flows (A) | Dollar strong or sideways | None (DXY unresolvable) | dxy_index=100.08 | Dead (unresolvable) | True (100.08 > 100) | New `dxy_index` computed field |
| 5 | A-07 | capital_flows (B) | Dollar weakening | None (DXY unresolvable) | dxy_index=100.08 | Dead (unresolvable) | False (temporal thresh) | Field resolves; temporal threshold is B-02 class |
| 6 | D-03 | monetary_arch | Foreign Treasury holdings declining | None (no backtick ref) | foreign_treasury_holdings_pct=24.0 | Dead (unresolvable) | False (temporal thresh) | Backtick `foreign_treasury_holdings_pct` |
| 7 | B-01 | fiscal_dom_liq | Deficit pace | deficit_pace_annualized=3690 vs 1.5 | deficit_pace_annualized=3690 vs 1500 | True (by accident: 3690 >> 1.5) | True (correct: 3690 > 1500) | Threshold text fixed to match native $B unit |
| 8 | B-01 | fiscal_dom_arith | Deficit pace outside recession | deficit_pace_annualized=3690 vs 1.5 | deficit_pace_annualized=3690 vs 1500 | True (by accident) | True (correct) | Same threshold fix |

---

## 2. Theory score deltas

| Theory | Baseline score | New score | Delta | Tier change | Cause |
|--------|---------------|-----------|-------|-------------|-------|
| fiscal_dominance_arithmetic | 0.722 (Active) | 0.833 (Active) | +0.111 | No | gold_oil_ratio now triggers (w=0.10) |
| monetary_architecture | 0.408 (Adjacent) | 0.662 (Active) | +0.254 | Adjacent -> Active | gold_oil_ratio triggers (w=0.18) + foreign_treasury resolves |
| capital_flows / Accumulation | 0.270 (Inactive) | 0.470 (Adjacent) | +0.200 | Inactive -> Adjacent | DXY "Dollar strong" triggers (w=0.20) |
| capital_flows / Rotation | 0.450 (Adjacent) | 0.450 (Adjacent) | 0.000 | No | DXY resolves but "Dollar weakening" doesn't trigger |
| debt_cycle_long | 0.900 (Active) | 0.900 (Active) | 0.000 | No | fed_bs_gdp_ratio: same trigger, correct reason |
| fiscal_dominance_liquidity | 0.700 (Active) | 0.700 (Active) | 0.000 | No | deficit_pace: same trigger, correct reason |
| valuation_mean_reversion | 0.706 (Active) | 0.706 (Active) | 0.000 | No | Not affected |
| debt_cycle_short | 0.400/0.650 | 0.400/0.650 | 0.000 | No | Not affected |
| structural_fragility | 0.000/0.353 | 0.000/0.353 | 0.000 | No | Not affected |

### Tier changes

- **monetary_architecture: Adjacent -> Active** -- Gold/oil ratio was permanently dormant (ETF proxy + missing backtick). Now fires correctly with commodity data. This is the single most impactful fix.
- **capital_flows / Accumulation: Inactive -> Adjacent** -- DXY was fetched but unresolvable. Now triggers "Dollar strong" indicator. Phase A is now properly recognized as setup-present.

---

## 3. Score change explanations

**fiscal_dominance_arithmetic (+0.111):** gold_oil_ratio transitions from dormant to triggered. The commodity ratio (42.3) correctly exceeds the threshold (25), adding 0.10 weight to the numerator. Score: 0.75/0.90 = 0.833 (was 0.65/0.90 = 0.722).

**monetary_architecture (+0.254):** Two D-03 backtick fixes plus A-01 commodity fix. gold_oil_ratio resolves and triggers (42.3 > 25, w=0.18). foreign_treasury_holdings_pct resolves (24.0) but has a temporal threshold ("declining for 3+ years") which the snapshot engine cannot evaluate -- stays in denominator, doesn't trigger. Net: (0.29+0.18)/(0.29+0.24+0.18) = 0.47/0.71 = 0.662.

**capital_flows Accumulation (+0.200):** DXY exposed as `dxy_index` computed field. "Dollar strong or sideways" indicator resolves (100.08 > 100, triggers). Adds 0.20 to numerator. Score: 0.47/1.00 = 0.470 (was 0.27/1.00 = 0.270).

---

## 4. Denominator policy

**Unchanged.** Verified:
- Web-search indicators with no data: still skipped (removed from both numerator and denominator)
- Computed-mechanical indicators with None: still stay in denominator (e.g., top_10_sp500_weight)
- No new skip/exclude logic introduced
- Task 2 owns the denominator policy change

---

## 5. Residual issues deferred

| Issue | Class | Deferred to | Why |
|-------|-------|-------------|-----|
| foreign_treasury_holdings_pct temporal threshold | B-02 | Task 3 / v9 | "declining for 3+ years" requires time-series data |
| Dollar weakening temporal threshold | B-02 | Task 3 / v9 | "declining 3+ months AND below 12-month MA" requires time-series |
| CL=F at $110.66 (elevated oil price) | Data quality | Monitor | Commodity futures may have contango premium; ratio still economically valid |
| gold_oil_ratio = 42.3 vs threshold 25 | Economic assessment | None | Ratio is above threshold but below the ~66 the audit predicted (oil higher than expected). Correct behavior. |

---

## 6. Files changed

| File | Change |
|------|--------|
| `backend/engine/data_agent.py` | Added GC=F, CL=F to SPECIAL_TICKERS; rewrote gold_oil_ratio from commodity futures; added `dxy_index` computed field |
| `theories/THEORY_MODULE_debt_cycle_long_v2/ACTIVATION.md` | C-01: backtick changed to `fed_bs_gdp_ratio`, threshold "Above 20" |
| `theories/THEORY_MODULE_capital_flows_v2/ACTIVATION.md` | A-07: backtick `dxy_index` added to both DXY indicators |
| `theories/THEORY_MODULE_monetary_architecture_v2/ACTIVATION.md` | D-03: backticks `foreign_treasury_holdings_pct` and `gold_oil_ratio` added |
| `theories/THEORY_MODULE_fiscal_dominance_liquidity_v2/ACTIVATION.md` | B-01: threshold "Above 1500 annualized (in $B)" |
| `theories/THEORY_MODULE_fiscal_dominance_arithmatic_v2/ACTIVATION.md` | B-01: threshold "Deficit above 1500 annualized (in $B)" |
| `mock_data/briefing_packet.json` | Regenerated with GC=F, CL=F, dxy_index; web-sourced data merged from baseline |
| `docs/POST_V8_TASK1_FIELD_WIRING_RESULTS.md` | This file |

---

*Frozen at Task 1 completion. Task 2 (denominator policy) is next.*
