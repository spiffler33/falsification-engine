# V9 Phase 3: Dual-Path Activation Engine Results

*Date: 2026-04-07*
*Status: PASS*

---

## 1. What Was Built

Phase 3 approves compiled artifacts for scalar-evaluable theories, builds a dual-path activation engine that selects compiled or legacy scoring per theory, and updates the correctness harness to match.

### Files Created

| File | Purpose |
|------|---------|
| `backend/engine/v9/dual_path.py` | Dual-path routing + CompiledEvaluationResult-to-ActivationResult adapter |
| `scripts/v9_approve_artifacts.py` | Artifact approval script (DRAFT -> APPROVED with justification) |
| `docs/V9_PHASE3_DUAL_PATH_RESULTS.md` | This document |

### Files Modified

| File | Change |
|------|--------|
| `backend/engine/activation.py` | `score_all_packages()` now routes to compiled path for APPROVED theories |
| `backend/schemas/v9/compiled_activation.py` | Added `approval_timestamp` and `approval_justification` fields |
| `backend/tests/test_activation_correctness.py` | Updated fixtures for 3 switched theories |
| `backend/tests/test_v9_phase2_compilation.py` | Updated mismatch count (3 -> 1, 2 resolved by switchover) |
| `artifacts/v9/valuation_mean_reversion.compiled.json` | DRAFT -> APPROVED |
| `artifacts/v9/debt_cycle_long.compiled.json` | DRAFT -> APPROVED |
| `artifacts/v9/fiscal_dominance_arithmetic.compiled.json` | DRAFT -> APPROVED |

### Files NOT Modified (per constraints)

- Phase 0 contracts (`backend/schemas/v9/`)
- Phase 1 runtime (`backend/engine/v9/rule_evaluator.py`, `series_interface.py`, `registry_builder.py`)
- `backend/engine/v9/compile_all.py`

---

## 2. Artifact Approval

| Theory | Old Status | New Status | Justification |
|--------|-----------|-----------|---------------|
| valuation_mean_reversion | DRAFT | APPROVED | 2 expected_parity, 1 justified_improvement (OR condition), 4 data_infra. Zero unexplained mismatches. |
| debt_cycle_long | DRAFT | APPROVED | 3 expected_parity, 1 justified_improvement (wealth_inequality), 1 coincidental_parity (fiscal_deficit), 1 data_infra. Zero unexplained mismatches. |
| fiscal_dominance_arithmetic | DRAFT | APPROVED | 2 expected_parity, 4 data_infra. Score parity 1.000. Zero mismatches. |
| debt_cycle_short | DRAFT | DRAFT | Contraction tier mismatch (inactive vs adjacent). Needs time-series. |
| structural_fragility | DRAFT | DRAFT | Building tier mismatch (adjacent vs inactive). Needs time-series. |
| capital_flows | DRAFT | DRAFT | Accumulation + Rotation tier mismatches. Needs time-series. |
| monetary_architecture | DRAFT | DRAFT | Tier mismatch (inactive vs active). Nearly all indicators temporal. |
| fiscal_dominance_liquidity | DRAFT | DRAFT | No tier mismatch, but score difference. Conservative: wait for time-series. |

---

## 3. Dual-Path Routing

### Architecture

```
score_all_packages(packages, briefing)
  |
  +-- for each theory:
  |     Is theory_id in APPROVED artifacts?
  |       YES -> score_compiled(theory_id, briefing)
  |                 |-> CompiledActivationEvaluator.evaluate(artifact)
  |                 |-> compiled_to_activation_result() adapter
  |                 |-> ActivationResult (identical format)
  |       NO  -> score_package(pkg, briefing)  (legacy path)
  |                 |-> _score_phase() regex evaluation
  |                 |-> ActivationResult
  |
  +-- returns: list[ActivationResult]  (uniform format)
```

### Current Routing

| Theory | Path | Score | Tier |
|--------|------|-------|------|
| valuation_mean_reversion | **compiled** | 0.8333 | Active |
| debt_cycle_long | **compiled** | 0.6471 | Active |
| fiscal_dominance_arithmetic | **compiled** | 1.0000 | Active |
| debt_cycle_short | legacy | 0.3000 (Contraction) | Adjacent |
| structural_fragility | legacy | 0.4615 (Building) | Adjacent |
| fiscal_dominance_liquidity | legacy | 0.7778 | Active |
| capital_flows | legacy | 0.4500 (Rotation) | Adjacent |
| monetary_architecture | legacy | 0.6620 | Active |

### Downstream Impact

- Prompt builder: **unaffected** (reads tier/score/effective_phase, all present)
- Conviction scorer: **unaffected** (reads ActivationResult fields only)
- Frontend: **unaffected** (API surface unchanged)
- Pipeline: **unaffected** (score_all_packages return type unchanged)

---

## 4. Correctness Harness Changes

### valuation_mean_reversion

| Metric | Old (legacy) | New (compiled) | Reason |
|--------|-------------|----------------|--------|
| Score | 0.705882 | 0.833333 | OR condition fix + denominator shrink |
| Indicator count | 6 | 7 | Buffett now in results (excluded) |
| Skipped count | 1 | 3 | +breadth (time-series), +insider (time-series) |
| profit_margins triggered | False | True | justified_improvement: OR condition evaluable |
| breadth triggered | True | excluded | data_unavailable: historical_extreme needs series |
| insider triggered | True | excluded | data_unavailable: persistence needs series |
| Weights | legacy weights | compiled weights | Rebalanced across all 7 indicators |

### debt_cycle_long

| Metric | Old (legacy) | New (compiled) | Reason |
|--------|-------------|----------------|--------|
| Score | 0.900000 | 0.647059 | wealth_inequality fix + rates excluded |
| wealth_inequality triggered | True | **False** | justified_improvement: correct 70% threshold |
| fiscal_deficit metric_field | interest_exceeds_defense | deficit_pct_gdp | coincidental_parity: correct field now |
| fiscal_deficit value | 287.0 | None (compound) | Compound rule, no single value |
| rates_near_elb | True (trivial) | excluded | data_unavailable: historical_extreme needs series |

### fiscal_dominance_arithmetic

| Metric | Old (legacy) | New (compiled) | Reason |
|--------|-------------|----------------|--------|
| Score | 1.000000 | 1.000000 | Score parity maintained |
| Excluded count | 1 | 2 | +cb_gold (persistence needs series) |
| cb_gold triggered | True | excluded | data_unavailable: persistence needs series |
| Display names | legacy verbose | compiled normalized | e.g., "Interest expense / tax receipts ratio" -> "Interest/receipts ratio elevated" |

---

## 5. Coincidental Parity Disposition

| # | Theory | Indicator | In Approved? | Disposition |
|---|--------|-----------|-------------|-------------|
| 1 | debt_cycle_long | fiscal_deficit_primary_driver | **YES** | **Silently fixed.** Compiled uses correct field `deficit_pct_gdp` (11.74 > 5.0). Legacy used wrong field `interest_exceeds_defense` (287 > 5). Same answer, now for the right reason. |
| 2 | debt_cycle_short | exp_fed_funds_below_gdp | No | Awaiting switchover. Legacy defaults False by coincidence (extracts GDP level, not growth rate). |
| 3 | structural_fragility | res_vix_elevated | No | Awaiting switchover. Legacy uses wrong-phase threshold (Building "Below 14" for Resolving indicator). |
| 4 | structural_fragility | res_hy_spread_wide | No | Awaiting switchover. Legacy uses wrong-phase threshold (Building "Below 300bp" for Resolving indicator). |

---

## 6. Phase 2 Test Impact

The Phase 2 `test_all_mismatches_are_known_justified` test expected 3 mismatches. After switchover, 2 of those (valuation_mean_reversion/profit_margins, debt_cycle_long/wealth_inequality) disappeared because both sides now use the compiled path. Updated expectation: 1 mismatch (capital_flows/acc_em_3yr_underperformance, still on legacy).

---

## 7. Regression Gate

```
Stage 1: Correctness harness ... PASS
Stage 2: Broader backend suite ... PASS
REGRESSION CHECK PASSED
```

Total tests: 1203 passed, 2 skipped

---

## 8. What Remains for Phase 4

| Item | Reason |
|------|--------|
| Time-series data (SeriesStore) | 30 indicators across 5 theories need trend/persistence/delta evaluation |
| Approve remaining theories | After SeriesStore resolves temporal indicators |
| Full compiled-only mode | After all 8 theories approved, legacy path can be deprecated |
| Artifact recompilation from theory text | Haiku compiler adapter for on-demand recompilation |
