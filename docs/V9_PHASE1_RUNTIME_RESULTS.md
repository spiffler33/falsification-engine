# V9 Phase 1: Deterministic Runtime Substrate Results

*Date: 2026-04-07*
*Status: PASS*

---

## 1. What Was Built

Phase 1 implements the deterministic runtime substrate that makes the Phase 0 contracts executable in pure Python, without any model calls.

### Files Created

| File | Purpose |
|------|---------|
| `backend/engine/v9/registry_builder.py` | Full field registry population from FRED, Yahoo, computed, web-sourced fields (80+ fields) |
| `backend/engine/v9/series_engine.py` | Concrete `SeriesPrimitiveEngine` implementation: 19 primitives + 2 named pattern evaluators |
| `backend/engine/v9/rule_evaluator.py` | Deterministic rule evaluator: dispatches on 8 rule types with unit normalization |
| `backend/engine/v9/compiled_evaluator.py` | Compiled activation evaluator: loads artifacts, evaluates rules, computes phase scores |
| `backend/engine/v9/validator.py` | Artifact validator using Phase 0 error taxonomy (25 error codes) |
| `backend/engine/v9/derived_functions.py` | Derived function registry for `DerivedOperand` resolution (e.g., `nominal_gdp_growth`) |
| `backend/tests/test_v9_phase1_runtime.py` | 65 focused tests: registry, normalization, legality, series, rules, evaluator, validator, regressions |
| `docs/V9_PHASE1_RUNTIME_RESULTS.md` | This document |

### Files Changed

None. All production code is untouched. Phase 0 contracts are unmodified.

---

## 2. Field Registry Coverage

The full field registry (`build_full_registry()`) contains 80+ fields across 5 source categories:

| Category | Count | Examples |
|----------|-------|---------|
| FRED-backed | 23 | growth.gdp_latest, rates.fed_funds, credit.hy_spread |
| FRED-computed intermediate | 9 | computed_fred.federal_debt_to_gdp, computed_fred.corporate_profits |
| Computed (derived) | 30 | equity_risk_premium, net_liquidity, eem_spy_3y_relative, buffett_indicator |
| Ticker/market | 2 | ^VIX, DX-Y.NYB |
| Web-sourced | 16 | shiller_cape, cb_gold_purchases, china_credit_impulse, rmb_swift_share |

Every field carries: field_id, display_name, description, unit (ValueUnit), semantic_type (SemanticType), source, frequency, and dependency metadata where applicable.

---

## 3. eem_spy_3y_relative Investigation Result

**Classification: Legacy threshold extraction bug.**

### Evidence

1. **Field computation** (`data_agent.py:538-540`): `eem_spy_3y_relative = em_us_relative_12m = eem.return_12m - spy.return_12m`

2. **Sign convention is correct**: negative = EM underperformance, positive = EM outperformance. A value of 9.5 means EM outperformed SPY by 9.5% over the measurement period.

3. **Compiled rule is correct**: `eem_spy_3y_relative lt -30.0` means "EM has underperformed by more than 30%." With value 9.5: `9.5 < -30.0 = False`. Correct: EM is outperforming, not underperforming by 30%+.

4. **Legacy result is wrong**: The regex extracts unsigned "30" from the threshold text (which says something like "underperformance exceeding 30%"). It then checks `9.5 < 30 = True`, incorrectly triggering the indicator.

5. **Root cause**: The legacy threshold extraction regex (`_extract_number()`) strips sign semantics from the threshold. It cannot represent "the field must be below negative thirty" -- it only extracts the magnitude "30".

### Additional note

`eem_spy_3y_relative` uses a 12-month return proxy for a 3-year cumulative metric. This is a known data infrastructure limitation documented in `docs/POST_V8_AUDIT_CLOSURE.md` (item 7). The sign convention and field metadata are correct; only the time horizon is approximate.

### What this is NOT

- NOT a data/sign bug in the briefing computation
- NOT a compiler bug (the compiled rule is correct)
- NOT a field metadata bug (semantic type and unit are correct)
- NOT a briefing computation bug

---

## 4. Unit Normalization Protections

The runtime now prevents these comparison errors:

| Error Class | Example | Mechanism |
|-------------|---------|-----------|
| Scale mismatch | initial_claims (202000 COUNT) vs threshold (250 THOUSANDS) | Unit conversion: 250 THOUSANDS -> 250000 COUNT |
| Rate vs level | fed_funds (RATE) vs gdp_latest (LEVEL) | ComparisonClass mismatch: RATE_LIKE != LEVEL_LIKE |
| Count vs index | initial_claims (COUNT) vs ism_proxy (INDEX) | ComparisonClass mismatch: COUNT_LIKE != INDEX_LIKE |
| Basis points vs percent | HY spread (380 BP) vs threshold (4.5%) | Unit conversion: 4.5 PERCENT -> 450 BASIS_POINTS |

The normalization chain:
1. Rule evaluator gets field unit from registry (authoritative)
2. Normalizes field and threshold to common unit via `normalize_to_common_unit()`
3. Applies comparison operator on normalized values
4. Returns detailed normalization trace in result

---

## 5. Named Patterns: Stubbed vs Implemented

| Pattern | Status | Notes |
|---------|--------|-------|
| `sahm_rule` | **Implemented** | 3-month MA vs 12-month low, configurable threshold (default 0.50) |
| `resteepened_after_inversion` | **Implemented** | Checks deep inversion + delta rise from trough |
| `breakout_after_range` | **Stubbed** (registered in Phase 0, no evaluator) | Needs price consolidation detection; deferred to Phase 2 |

---

## 6. What Remains for Phase 2

| Item | Why Deferred |
|------|-------------|
| Haiku compilation of all 8 theories | Phase 2 scope |
| Production switchover from regex to compiled | Phase 2 scope |
| Compiled artifact file storage (JSON checked into repo) | Phase 2 |
| Parallel scoring (legacy + compiled side by side) | Phase 2 |
| `breakout_after_range` named pattern evaluator | Needs price consolidation logic |
| SeriesStore backed by actual FRED time-series data | Current data agent returns snapshots; needs historical series extension |
| Full dependency validation for all computed fields | Registry declares deps but not all upstream chains are verified |
| Denomination policy engine for denominator management | Scaffold built; full policy testing is Phase 2 |

---

## 7. Test Results

### Phase 1 tests
```
backend/tests/test_v9_phase1_runtime.py: 65 passed in 0.23s
```

### Phase 0 tests
```
backend/tests/test_v9_phase0_contracts.py: 91 passed in 0.21s
```

### Regression gate
```
Stage 1: Correctness harness ... PASS
Stage 2: Broader backend suite ... PASS (1156 passed, 2 skipped)
REGRESSION CHECK PASSED
```

---

## 8. Recommended Next Prompt: Phase 2 Compilation + Parallel Runtime

```
You are working inside the falsification-engine repo.

Your job is to execute Phase 2 from:
  v9_semantic_compiler_plan.md

Phases 0-1 are complete. The contract package and runtime substrate are frozen:
  backend/schemas/v9/          (units, rules, compiled_activation, field_registry, errors)
  backend/engine/v9/           (series_interface, registry_builder, series_engine,
                                rule_evaluator, compiled_evaluator, validator, derived_functions)
  backend/tests/test_v9_phase0_contracts.py  (91 tests)
  backend/tests/test_v9_phase1_runtime.py    (65 tests)

Results docs:
  docs/V9_PHASE0_CONTRACT_RESULTS.md
  docs/V9_PHASE1_RUNTIME_RESULTS.md

Phase 2 deliverables:
  1. Run Haiku compilation on all 8 theories
  2. Store compiled artifacts as JSON files (one per theory)
  3. Validate all artifacts using the Phase 1 validator
  4. Build parallel scoring: legacy + compiled running side by side
  5. Compare results on a frozen briefing packet
  6. Freeze compiled artifacts as the new regression baseline

Do not:
  - Modify Phase 0 or Phase 1 files
  - Switch production to compiled-only mode
  - Break the regression gate

Start now.
```
