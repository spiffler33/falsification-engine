# Post-v8 Task 4: Frozen Expected-Output Correctness Harness Results

**Date:** 2026-04-06
**Baseline:** `docs/POST_V8_TASK3_UNIT_SCALING_RESULTS.md` (frozen after Task 3)
**Test suite:** 937 tests passing (867 + 70 new correctness harness tests)

---

## 1. What the harness freezes

The harness (`backend/tests/test_activation_correctness.py`) is the permanent semantic regression gate. It scores all 8 theories against the frozen briefing (`mock_data/briefing_packet.json`, Task 0 artifact) and asserts exact expected outputs.

**Per theory:**
- Score and tier (single-phase) or phase scores/tiers + effective phase (two-phase)
- Indicator count and exact indicator name set

**Per indicator:**
- Triggered state (True/False)
- Resolved field value (with tolerance)
- Metric field path (field resolution)
- Weight
- Direction (for evaluated indicators)
- Exclusion reason (for excluded indicators: `data_unavailable` / `threshold_not_evaluable`)

**Per theory coverage:**
- Total indicators in results
- Skipped count (web-search / qualitative)
- Evaluated count (in denominator)
- Excluded count (removed from denominator)
- Triggered count
- Evaluated weight, triggered weight, excluded weight

**Threshold parsing (22 frozen extractions):**
- 18 specific threshold strings with expected numeric output
- 4 threshold strings that must return None (not evaluable)
- Includes K-suffix scaling (Task 3), bp/% stripping, BUG-03 temporal extractions

---

## 2. Theory coverage summary

| # | Theory | Two-phase | Score | Tier | Indicators | Evaluated | Excluded | Triggered | Tests |
|---|--------|-----------|-------|------|------------|-----------|----------|-----------|-------|
| 1 | valuation_mean_reversion | No | 0.7059 | Active | 6 | 6 | 0 | 4 | 5 |
| 2 | debt_cycle_short | Yes | 0.300/1.000 | Adj/Active | 15 | 13 | 2 | 8 | 7 |
| 3 | debt_cycle_long | No | 0.9000 | Active | 6 | 6 | 0 | 5 | 5 |
| 4 | structural_fragility | Yes | 0.000/0.462 | Inact/Adj | 9 | 8 | 1 | 3 | 6 |
| 5 | fiscal_dominance_liquidity | No | 0.7778 | Active | 7 | 6 | 1 | 4 | 5 |
| 6 | fiscal_dominance_arithmetic | No | 1.0000 | Active | 6 | 5 | 1 | 5 | 5 |
| 7 | capital_flows | Yes | 0.450/0.470 | Adj/Adj | 10 | 10 | 0 | 5 | 6 |
| 8 | monetary_architecture | No | 0.6620 | Active | 3 | 3 | 0 | 2 | 6 |
| -- | **Meta + threshold** | -- | -- | -- | -- | -- | -- | -- | 25 |
| -- | **Total** | -- | -- | -- | **62** | **57** | **5** | **36** | **70** |

---

## 3. Ceiling-hit visibility

### fiscal_dominance_arithmetic: 1.000

| Metric | Value |
|--------|-------|
| Total indicators | 6 |
| Evaluated (denominator) | 5 |
| Excluded | 1 (Debt rollover, w=0.15, threshold_not_evaluable) |
| Triggered | 5 of 5 |
| Evaluated weight | 0.75 |
| Triggered weight | 0.75 |
| Excluded weight | 0.15 |
| **Denominator shrinkage** | **16.7% of total possible weight excluded** |
| **If excluded became evaluable and untriggered** | **Score would be 0.833** |

Harness test: `TestFiscalDominanceArithmetic::test_ceiling_hit_visibility`

### debt_cycle_short / Expansion: 1.000

| Metric | Value |
|--------|-------|
| Total indicators (Expansion phase) | 8 |
| Evaluated (denominator) | 6 |
| Excluded | 2 (Fed funds below GDP w=0.10, Net credit growth w=0.15) |
| Triggered | 6 of 6 |
| Evaluated weight | 0.75 |
| Triggered weight | 0.75 |
| Excluded weight | 0.25 |
| **Denominator shrinkage** | **25% of total possible weight excluded** |
| **If excluded became evaluable and untriggered** | **Score would be 0.750** |

Harness test: `TestDebtCycleShort::test_expansion_ceiling_hit_visibility`

---

## 4. Tests added

| Test class | Tests | What it freezes |
|-----------|-------|-----------------|
| TestValuationMeanReversion | 5 | Score, tier, 6 indicators, coverage, Buffett skip |
| TestDebtCycleShort | 7 | Phase scores/tiers, effective phase, 15 indicators, coverage, ceiling hit, K-suffix regression |
| TestDebtCycleLong | 5 | Score, tier, 6 indicators, coverage, zero exclusions |
| TestStructuralFragility | 6 | Phase scores/tiers, effective phase, 9 indicators, coverage, top_10 exclusion |
| TestFiscalDominanceLiquidity | 5 | Score, tier, 7 indicators, coverage, TGA mismatch frozen |
| TestFiscalDominanceArithmetic | 5 | Score, tier, 6 indicators, coverage, ceiling-hit visibility |
| TestCapitalFlows | 6 | Phase scores/tiers, effective phase, 10 indicators, coverage, DXY resolution |
| TestMonetaryArchitecture | 6 | Score, tier, 3 indicators, coverage, web skips, gold/oil commodity fix |
| TestHarnessCompleteness | 3 | All 8 theories scored, 8 test classes present, no unexpected theories |
| TestThresholdParsing | 22 | 18 numeric extractions, 4 not-evaluable extractions |
| **Total** | **70** | |

---

## 5. Failure-path proof

Three deliberate perturbations proved the harness catches semantic drift:

**Perturbation 1 -- Value change (hy_spread 317 -> 250):**
- `structural_fragility/Building "High-yield spread"` flips from not-triggered to triggered
- Score moves 0.462 -> 0.692
- Harness would fail on: trigger state, score, coverage metrics

**Perturbation 2 -- Field removal (delete gold_oil_ratio):**
- `monetary_architecture "Gold/oil ratio elevated and rising"` becomes data_unavailable
- Score drops 0.662 -> 0.547
- Harness would fail on: trigger state, reason field, score, coverage

**Perturbation 3 -- K-suffix regression:**
- If `_extract_number("Below 250K")` returned 250 instead of 250000:
- `debt_cycle_short/Expansion "Initial claims low"` would stop triggering
- Expansion score would drop below 1.000
- Harness would fail on: trigger state, phase score, threshold parsing test

---

## 6. Deliberate update policy

The harness is designed to be **hard to update casually**:

1. All expected values are explicit constants in the test file -- no auto-generation.
2. Each indicator has a named dict entry with frozen trigger state, value, field, weight, and direction.
3. Coverage metrics are explicit per-theory constants, not computed from expectations.
4. Comments on contentious indicators document why the current behavior is frozen (known bugs, known proxies, known coincidences).

To update: change the specific fixture value in `test_activation_correctness.py` and explain the change in the commit message. A reviewer should be able to see exactly what moved and why.

---

## 7. Residual issues deferred to v9

| Issue | Class | Why not fixed here |
|-------|-------|-------------------|
| BUG-03 temporal phrase extraction | Architecture | Harness freezes current proxy behavior ("3+ months" -> 3) |
| TGA $M/$B latent mismatch | Field wiring | Harness freezes current correct-by-coincidence state |
| Wealth inequality threshold extraction | Parsing | Extracts "10" from "10% wealth share above 70%"; frozen as-is |
| Rates at ELB trivially true (any rate > 0) | Threshold design | C-02 known; frozen as-is |
| Fed funds vs GDP level comparison | Field wiring | GDP level ($B) vs rate threshold; frozen as-is |
| T/B/M suffix scaling | Architecture | Deferred to v9 structured thresholds |

---

## 8. Files changed

| File | Change |
|------|--------|
| `backend/tests/test_activation_correctness.py` | New file: 70 tests, frozen expected-output correctness harness for all 8 theories |
| `docs/POST_V8_TASK4_CORRECTNESS_HARNESS_RESULTS.md` | This file |

---

*Frozen at Task 4 completion. Task 5 (single regression command) is next.*
