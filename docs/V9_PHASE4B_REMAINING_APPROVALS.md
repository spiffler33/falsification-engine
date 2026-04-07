# V9 Phase 4B: Remaining Theory Approvals

**Date:** 2026-04-07
**Scope:** Fix compilation issues for structural_fragility and capital_flows, approve both, achieve 8/8 compiled

---

## 1. Root Causes and Fixes

### capital_flows — Weight Extraction Bug

**Root cause:** The ACTIVATION.md Accumulation phase uses weight annotations like `0.33 \`[CALIBRATION]\``. The activation parser (`activation_parser.py`) passed these raw strings to Haiku. The compilation script's fallback `float()` call failed on `"0.33 \`[CALIBRATION]\`"` and defaulted to `w = 0.1` for all 4 Accumulation indicators.

**Fix:** Added `_clean_weight()` function to `activation_parser.py` that strips non-numeric annotations from weight cells using regex `([\d.]+)`. Now `"0.33 \`[CALIBRATION]\`"` correctly parses to `"0.33"`.

**Why Rotation was unaffected:** Rotation phase weights don't have `[CALIBRATION]` tags — they compiled correctly the first time.

**Fix type:** Parser fix (deterministic, upstream of compilation).

### structural_fragility — Missing Indicator

**Root cause:** Haiku systematically drops the "Implied-realized vol gap" indicator during compilation. The indicator's metric source (`computed: VIX - 20d_realized_vol(SPY)`) is a derived formula that confuses Haiku — it cannot map it to a registry field_id. Confirmed across 3 separate compilation attempts: Haiku always produces 7/8 Building indicators, omitting this one.

**Fix:** Added `repair_missing_indicators()` function to `compiler_repairs.py` (Repair 3). This repair:
1. Compares parsed indicator names from ACTIVATION.md to compiled indicator display_names
2. For known-missing cases (registered in `_KNOWN_MISSING` dict), injects a deterministic CompiledIndicator
3. For the vol gap specifically: injects a `scalar_comparison` rule on `vix_vs_realized > 5.0`
4. Sets `compilation_status: warning` with documented ambiguity

Integrated into `scripts/v9_compile_theories.py` after the existing Repair 1-2 pass.

**Fix type:** Post-compilation repair (deterministic, auditable).

---

## 2. Recompilation Results

| Theory | Recompilation | Additional Repair | Result |
|--------|--------------|-------------------|--------|
| capital_flows | Yes (Haiku API) | None needed — parser fix was sufficient | 10 indicators, correct weights |
| structural_fragility | Yes (Haiku API) | Repair 3: inject missing vol gap | 12 indicators (8 Building + 4 Resolving) |

---

## 3. Semantic Diff Summary

### structural_fragility

| Indicator | Compiled | Legacy | Classification |
|-----------|----------|--------|---------------|
| Implied vol level | False (23.87, w=0.10) | False (23.87, w=0.10) | expected_parity |
| Implied-realized vol gap | False (4.86, w=0.10) | False (4.86, w=0.10) | expected_parity (injected) |
| High-yield spread | False (317.0, w=0.15) | False (317.0, w=0.15) | expected_parity |
| Top-10 concentration | excluded (data_unavailable) | excluded (data_unavailable) | expected_parity |
| Capex/revenue mismatch | excluded (UNRESOLVED) | N/A (skipped) | new_indicator |
| Margin debt | excluded (historical_extreme) | True (1253, BUG-03) | temporal_exclusion |
| Large-cap divergence | excluded (historical_extreme) | True (2.33, BUG-03) | temporal_exclusion |
| Passive fund share | True (59.0, w=0.10) | True (59.0, w=0.10) | expected_parity |
| Drawdown depth | False (-5.7, w=0.20) | False (-5.7, w=0.20) | expected_parity |
| Valuation compression | False (37.94, w=0.15) | False (37.94, w=0.15) | expected_parity |

**Building:** 0.2222 (Inactive) vs legacy 0.4615 (Adjacent). Tier downgrade from temporal exclusion + BUG-03 fixes.
**Resolving:** 0.0000 (Inactive) = match.
**0 unexplained mismatches.**

### capital_flows

| Indicator | Compiled | Legacy | Classification |
|-----------|----------|--------|---------------|
| EM vs DM PE gap | False (11.28, w=0.33) | False (11.28, w=0.33) | expected_parity |
| EM 3y underperformance | False (9.5, w=0.27) | True (9.5, w=0.27) | justified_improvement (sign fix) |
| Dollar strong/sideways | True (OR, w=0.20) | True (100.08, w=0.20) | expected_parity |
| China credit flat | False (3.5, w=0.20) | False (3.5, w=0.20) | expected_parity |
| Dollar weakening | excluded (temporal) | False (BUG-03) | temporal_exclusion |
| China credit positive | excluded (temporal) | True | temporal_exclusion |
| RMB strengthening | excluded (temporal) | False (BUG-03) | temporal_exclusion |
| EM outperforming | excluded (temporal) | True | temporal_exclusion |
| Commodity prices | excluded (temporal) | True (BUG-03) | temporal_exclusion |
| Chinese equities | False (-7.13, w=0.10) | False (-7.13, w=0.10) | expected_parity |

**Accumulation:** 0.2000 (Inactive) vs legacy 0.4700 (Adjacent). Tier downgrade from EM 3y sign fix.
**Rotation:** 0.0000 (Inactive) vs legacy 0.4500 (Adjacent). Tier downgrade from temporal exclusion.
**0 unexplained mismatches.**

---

## 4. Updated Routing Table (Final — 8/8 Compiled)

| # | Theory | Path | Artifact Status | Score | Tier |
|---|--------|------|-----------------|-------|------|
| 1 | valuation_mean_reversion | compiled | APPROVED (Phase 3) | 0.7857 | Active |
| 2 | debt_cycle_short | compiled | APPROVED (Phase 4) | Exp 0.833 / Con 0.000 | Active (Expansion) |
| 3 | debt_cycle_long | compiled | APPROVED (Phase 3) | 0.7647 | Active |
| 4 | structural_fragility | compiled | APPROVED (Phase 4B) | Bld 0.222 / Res 0.000 | Inactive |
| 5 | fiscal_dominance_liquidity | compiled | APPROVED (Phase 4) | 1.0000 | Active |
| 6 | fiscal_dominance_arithmetic | compiled | APPROVED (Phase 3) | 1.0000 | Active |
| 7 | capital_flows | compiled | APPROVED (Phase 4B) | Acc 0.200 / Rot 0.000 | Inactive |
| 8 | monetary_architecture | compiled | APPROVED (Phase 4B*) | 0.0000 | Inactive |

**8/8 theories on compiled path. 0 on legacy path. Legacy path is now dormant.**

---

## 5. Regression Gate

```
backend/tests/ — 1204 passed, 2 skipped, 0 failed
test_activation_correctness.py — 72 passed (all 8 theories)
test_v9_phase2_compilation.py — updated: 0 mismatches expected (all compiled)
```

---

## 6. Files Modified

| File | Change |
|------|--------|
| `backend/engine/v9/activation_parser.py` | Added `_clean_weight()` to strip `[CALIBRATION]` tags from weight cells |
| `backend/engine/v9/compiler_repairs.py` | Added Repair 3: `repair_missing_indicators()` with `_KNOWN_MISSING` registry |
| `scripts/v9_compile_theories.py` | Integrated Repair 3 into compilation pipeline |
| `artifacts/v9/structural_fragility.compiled.json` | Recompiled + approved (12 indicators) |
| `artifacts/v9/capital_flows.compiled.json` | Recompiled + approved (correct weights) |
| `backend/tests/test_activation_correctness.py` | Updated harness for both theories |
| `backend/tests/test_v9_phase2_compilation.py` | Updated mismatch count: 1 -> 0 |

---

## 7. Legacy Path Disposition

**The legacy activation path is now dormant.** All 8 theories route through the compiled path. The legacy code in `activation.py` (`score_package`, `_score_phase`, etc.) remains as fallback infrastructure but is no longer exercised during normal operation.

**Path to full removal:** The legacy path can be removed once:
1. SeriesStore is implemented (makes temporal indicators evaluable)
2. A full run with live data confirms compiled-only mode works end-to-end
3. The legacy code is deleted and `dual_path.py` simplified to compiled-only
