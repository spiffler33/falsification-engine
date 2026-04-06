# Post-v8 Task 2: Data-Gap Scoring Policy Results

**Date:** 2026-04-06
**Baseline:** `docs/POST_V8_TASK1_FIELD_WIRING_RESULTS.md` (frozen after Task 1)
**Test suite:** 850 tests passing (843 + 7 new data-gap policy tests)

---

## 1. Policy change

**Problem:** Indicators that cannot be mechanically scored under the current architecture stay in the scoring denominator, silently depressing theory activation scores. This penalizes theories for data gaps they have no control over.

**Fix:** Two categories of non-scoreable indicators are now excluded from the denominator in `_score_phase()`:

| Category | Detection | Label in results | Example |
|----------|-----------|-----------------|---------|
| Data unavailable | Non-web indicator, value=None | `data_unavailable` | `top_10_sp500_weight` (no data source) |
| Threshold not evaluable | Value resolves, `_extract_number(threshold)` returns None | `threshold_not_evaluable` | "Weighted average rate rising AND below current market rates..." |

Both categories are recorded in `indicator_results` (with reason, value, weight, field) and in the `skipped_indicators` list. Downstream consumers can inspect the reason field to distinguish them from normal non-triggers and from web-search skips.

**What did NOT change:**
- Web-search indicators: still skip when data unavailable (existing behavior, unchanged)
- Valid resolved non-triggers: still counted in denominator (correct behavior)
- RISING/FALLING with extractable number: still scored via BUG-03 proxy (Task 3 scope)
- No temporal logic faked
- No threshold values changed

---

## 2. Affected indicator inventory

### A. Data unavailable (value=None, non-web)

| # | Theory | Phase | Indicator | Weight | Field | Why structural | Disposition |
|---|--------|-------|-----------|--------|-------|---------------|-------------|
| 1 | structural_fragility | Building | Top-10 index concentration | 0.20 | `top_10_sp500_weight` | No data source implemented. Requires index provider constituent weights. | Excluded from denominator |

### B. Threshold not evaluable (value resolves, no extractable number)

| # | Theory | Phase | Indicator | Weight | Value | Threshold (summary) | Why structural | Disposition |
|---|--------|-------|-----------|--------|-------|---------------------|---------------|-------------|
| 2 | debt_cycle_short | Expansion | Fed funds below nominal GDP growth | 0.10 | 31442.5 | "Fed funds rate below nominal GDP growth rate" | Compound rate comparison; no single numeric threshold expressible in current schema | Excluded from denominator |
| 3 | debt_cycle_short | Expansion | Net credit growth positive | 0.15 | 0.0 | "Banks reporting steady or loosening lending standards AND loan growth positive" | Multi-source qualitative assessment | Excluded from denominator |
| 4 | fiscal_dominance_arithmetic | Active | Debt rollover at higher rates | 0.15 | 3.355 | "Weighted average rate rising AND below current market rates" | Temporal trend + compound comparison | Excluded from denominator |
| 5 | fiscal_dominance_liquidity | Active | Fed BS direction inconsistent with stated policy | 0.10 | 6675344.0 | "Fed BS declining slower than QT pace, OR flat, OR expanding" | Comparison against external reference + temporal direction | Excluded from denominator |

### C. NOT affected (already handled or different class)

| Indicator | Current handling | Why not Task 2 |
|-----------|-----------------|----------------|
| Capex/revenue mismatch (structural_fragility) | SKIP_WEB (web-search, no field mapping) | Already excluded from denominator |
| Cross-currency basis swap stress (monetary_architecture) | SKIP_WEB | Already excluded |
| Non-dollar trade settlement growing (monetary_architecture) | SKIP_WEB | Already excluded |
| Buffett Indicator extreme (valuation_mean_reversion) | SKIP_WEB | Already excluded |
| Dollar weakening (capital_flows) | BUG-03 proxy: thresh extracts "3" from "3+ months" | Has extractable number; Task 3 scope |
| RMB strengthening (capital_flows) | BUG-03 proxy: thresh extracts "3" from "3+ months" | Has extractable number; Task 3 scope |
| Foreign Treasury holdings declining (monetary_architecture) | BUG-03 proxy: thresh extracts "3" from "3+ years" | Has extractable number; Task 3 scope |
| Unemployment rising / Sahm Rule (debt_cycle_short) | BUG-03 proxy: thresh extracts "3" from "3-month MA" | Has extractable number; Task 3 scope |

---

## 3. Theory score deltas

Compared against Task 1 results (which diff against the frozen semantic baseline):

| Theory | Phase | Task 1 score | Task 2 score | Delta | Tier | Indicators excluded |
|--------|-------|-------------|-------------|-------|------|---------------------|
| structural_fragility | Building | 0.353 | 0.462 | +0.109 | Adjacent -> Adjacent | top_10_sp500_weight (w=0.20) |
| debt_cycle_short | Expansion | 0.650 | 0.867 | +0.217 | Active -> Active | Fed funds below GDP (w=0.10), Net credit growth (w=0.15) |
| fiscal_dominance_arithmetic | Active | 0.833 | 1.000 | +0.167 | Active -> Active | Debt rollover (w=0.15) |
| fiscal_dominance_liquidity | Active | 0.700 | 0.778 | +0.078 | Active -> Active | Fed BS direction (w=0.10) |
| valuation_mean_reversion | -- | 0.706 | 0.706 | 0.000 | Active | -- |
| debt_cycle_short | Contraction | 0.400 | 0.400 | 0.000 | Adjacent | -- |
| debt_cycle_long | -- | 0.900 | 0.900 | 0.000 | Active | -- |
| capital_flows | Rotation | 0.450 | 0.450 | 0.000 | Adjacent | -- |
| capital_flows | Accumulation | 0.470 | 0.470 | 0.000 | Adjacent | -- |
| monetary_architecture | -- | 0.662 | 0.662 | 0.000 | Active | -- |

**No tier changes.** All score increases are within the same tier. Every delta is causally traceable to the removal of dead-weight indicators from the denominator.

---

## 4. Per-indicator disposition detail

| # | Theory | Indicator | Prior disposition | New disposition | Prior score effect | New score effect | Why new treatment is more honest |
|---|--------|-----------|-------------------|-----------------|-------------------|-----------------|----------------------------------|
| 1 | structural_fragility | Top-10 index concentration | In denominator (w=0.20), always untriggered, reason="data not available" | Excluded from denominator, reason="data_unavailable" | Depresses Building score by 0.20 dead weight | No effect on score | No data source exists; penalizing for its absence is unfair |
| 2 | debt_cycle_short | Fed funds below nominal GDP growth | In denominator (w=0.10), always untriggered (no number extractable) | Excluded, reason="threshold_not_evaluable" | Depresses Expansion by 0.10 dead weight | No effect | Compound rate comparison cannot be expressed as value > X |
| 3 | debt_cycle_short | Net credit growth positive | In denominator (w=0.15), always untriggered (no number extractable) | Excluded, reason="threshold_not_evaluable" | Depresses Expansion by 0.15 dead weight | No effect | Multi-source qualitative threshold; no number to extract |
| 4 | fiscal_dom_arith | Debt rollover at higher rates | In denominator (w=0.15), always untriggered (no number extractable) | Excluded, reason="threshold_not_evaluable" | Depresses score by 0.15 dead weight | No effect | Requires temporal trend + compound comparison |
| 5 | fiscal_dom_liq | Fed BS direction inconsistent | In denominator (w=0.10), always untriggered (no number extractable) | Excluded, reason="threshold_not_evaluable" | Depresses score by 0.10 dead weight | No effect | Requires comparison against announced QT pace + temporal direction |

---

## 5. Residual issues deferred

| Issue | Class | Deferred to | Note |
|-------|-------|-------------|------|
| BUG-03 RISING/FALLING proxy extracts temporal numbers | Threshold extraction | Task 3 | 6+ indicators affected; extracts "3" from "3+ months" etc. |
| top_10_sp500_weight has no data source | Data infrastructure | v9 | Requires index provider constituent data |
| Compound thresholds (rate A < rate B) | Schema limitation | v9 | Needs structured threshold objects |
| Temporal trend evaluation (rising/falling) | Architecture | v9 | Needs time-series model |

---

## 6. Files changed

| File | Change |
|------|--------|
| `backend/engine/activation.py` | `_score_phase()`: added data-gap policy — data_unavailable and threshold_not_evaluable indicators excluded from denominator with explicit reasons |
| `backend/tests/test_activation_web_integration.py` | Added `TestDataGapPolicy` (7 tests); updated 2 existing score assertions for policy-changed theories |
| `docs/POST_V8_TASK2_DATA_GAP_POLICY_RESULTS.md` | This file |

---

*Frozen at Task 2 completion. Task 3 (unit-suffix scaling) is next.*
