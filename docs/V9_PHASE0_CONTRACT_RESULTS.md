# V9 Phase 0: Contract-Hardening Results

*Date: 2026-04-07*
*Status: PASS*

---

## 1. What Was Built

Phase 0 froze the machine contract for the v9 semantic compiler. Six contract packages were created, none of which modify production code or the existing regression surface.

### Files Created

| File | Purpose |
|------|---------|
| `backend/schemas/v9/__init__.py` | Package init |
| `backend/schemas/v9/units.py` | ValueUnit enum, SemanticType enum, ComparisonClass, unit conversion, normalization, UnitValue, TimeWindow |
| `backend/schemas/v9/rules.py` | Rule AST: 8 rule types as discriminated union, operand types, comparators, named pattern registry |
| `backend/schemas/v9/compiled_activation.py` | Top-level artifact schema: indicator, phase, artifact, compiler metadata, source provenance, validation summary |
| `backend/schemas/v9/field_registry.py` | FieldEntry, FieldRegistry with comparison legality, unit compatibility, dependency validation, seed builder |
| `backend/schemas/v9/errors.py` | ErrorCode enum (25 codes), Severity, ValidationFinding, ValidationReport |
| `backend/engine/v9/__init__.py` | Package init |
| `backend/engine/v9/series_interface.py` | SeriesPrimitiveEngine ABC, SeriesData, SeriesStore protocol, primitive catalogue (19 primitives) |
| `backend/tests/test_v9_phase0_contracts.py` | 91 focused tests across all 6 contract packages |
| `docs/V9_PHASE0_CONTRACT_RESULTS.md` | This document |

### Files Changed

None. All production code is untouched.

---

## 2. Contract Decisions

### 2.1 Unit Model

Three-layer design:

1. **ValueUnit** (21 members): the dimensional unit of a number (percent, basis_points, count, thousands, usd_billions, etc.)
2. **SemanticType** (16 members): the economic meaning (rate, level, growth_rate, spread, ratio, count, index, etc.)
3. **ComparisonClass** (9 members): groups of semantic types that can legally be compared

Key contract: two operands can only be compared if they share a ComparisonClass. This catches:
- `fed_funds` (rate) vs `gdp_latest` (level) -- ILLEGAL, different comparison classes
- `fed_funds` (rate) vs `real_gdp` (growth_rate) -- LEGAL, both RATE_LIKE
- `initial_claims` (count) vs threshold 250 (thousands) -- LEGAL with conversion

Conversion table covers 30+ (from, to) pairs for scale conversions (count<->thousands, percent<->basis_points, usd_billions<->usd_millions, etc.).

### 2.2 Rule AST

Discriminated union on `rule_type` field (replaces spike's optional-field wrapper pattern):

| Rule Type | English Pattern | Spike Coverage? |
|-----------|----------------|-----------------|
| `scalar_comparison` | "Above 50", "Below 1.0%" | Yes |
| `field_comparison` | "Fed funds below nominal GDP growth" | Yes |
| `compound` | "Below 450bp AND not widening" | Yes |
| `persistence` | "Positive for 2 of last 3 months" | Yes |
| `trend_state` | "Declining for 3+ months" | Yes |
| `historical_extreme` | "Above 2-year high" | Yes |
| `named_pattern` | "Sahm Rule triggered" | **NEW** (was proposed but not implemented) |
| `delta_change` | "Declining by $100B over 60 days" | **NEW** (identified as gap in full compilation) |

Operand types: `FieldOperand` (with unit + semantic type), `LiteralOperand` (with unit), `DerivedOperand` (named function + arguments).

### 2.3 Compiled Activation Schema

Top-level artifact carries:
- Schema version, artifact status (draft/reviewed/approved/rejected/superseded)
- Source package reference (theory_id, package_version, source_hash)
- Compiler metadata (engine, model, prompt version, timestamp)
- Phase model (single_phase / two_phase)
- Phases, each with indicators
- Validation summary (populated after validation pass)

Per-indicator:
- Source provenance (file, section, line range)
- Normalized paraphrase
- Rule (typed)
- Field metadata (primary field, dependencies, unit, semantic type)
- Weight, exclusion policy
- Compilation status (clean/warning/blocked)
- Structured ambiguity records

### 2.4 Field Registry

FieldEntry declares: field_id, display_name, kind (scalar/series), unit, semantic_type, source, frequency, is_computed, dependencies, allowed_operators.

FieldRegistry provides:
- `check_comparison_legality(field_a, field_b)` -- prevents rate vs level errors
- `check_unit_compatibility(field, literal_unit)` -- catches count vs thousands mismatches
- `validate_dependencies(field_id)` -- ensures computed fields have upstream deps available

Seed registry has 20 representative fields for testing. Phase 1 will populate the full registry from data_agent.py.

### 2.5 Series Primitive Interface

19 primitives across 8 categories:
- Point-in-time (2): latest_value, value_at_offset
- Change (2): absolute_change, percent_change
- Rolling statistics (3): rolling_max, rolling_min, rolling_mean
- Historical rank (3): percentile_rank, is_at_extreme, distance_from_extreme
- Trend (2): trend_direction, slope
- Crossover (3): crossed_above, crossed_below, above_moving_average
- Persistence (3): count_true, n_of_last_k, consecutive_true
- Named patterns (1): evaluate_named_pattern

ABC interface (`SeriesPrimitiveEngine`) and protocol (`SeriesStore`) defined. Phase 1 implements.

### 2.6 Validator Error Taxonomy

25 error codes across 5 categories:

| Category | Prefix | Count | Examples |
|----------|--------|-------|----------|
| Schema | S_ | 5 | empty_artifact, invalid_weight |
| Field | F_ | 4 | unknown_field, unresolved_field |
| Unit | U_ | 4 | unit_mismatch, scale_mismatch |
| Rule | R_ | 7 | unsupported_rule_type, trivial_placeholder, missing_named_pattern |
| Phase | P_ | 4 | phase_model_mismatch, duplicate_phase_id |
| Semantic | X_ | 6 | illegal_comparison, ambiguous_threshold, blocked_by_missing_series |

Every finding carries: error_code, severity (error/warning/info), indicator_id, phase_id, message, structured detail dict.

---

## 3. Intentionally Deferred to Phase 1

| Item | Reason |
|------|--------|
| Full field registry population | Phase 1 will build from data_agent.py's FRED/Yahoo/web registries |
| Series primitive implementation | Phase 1 will implement against actual time-series data |
| Rule evaluator | Phase 1 deterministic runtime substrate |
| Compiled activation evaluator | Phase 1 runtime that loads and evaluates artifacts |
| Validator implementation | Phase 1 will implement the full validator using the error taxonomy |
| Derived function registry | Phase 1 will define nominal_gdp_growth and other derived functions |
| Two-phase transition logic | Phase 1 will formalize the "check resolving first" rule |
| Denominator policy engine | Phase 1 will implement the exclusion_policy contract |

---

## 4. Open Design Decisions

### 4.1 `SHARE` vs `PERCENT` semantic boundary
`SHARE` (0.35 = 35%) and `PERCENT` (35.0 = 35%) are separate ValueUnit members with a conversion factor. This is correct but means the compiler must consistently choose one. Recommendation: the compiler should emit PERCENT for human-readable thresholds and the normalizer handles conversion.

### 4.2 Named pattern parameter schema
Named patterns use `dict[str, Any]` for params. Phase 1 could tighten this with per-pattern Pydantic models. Not blocking.

### 4.3 `DerivedOperand` function registry
The DerivedOperand references functions by name (e.g., "nominal_gdp_growth") but the function registry doesn't exist yet. Phase 1 must create it. The interface is clean; only the implementation is missing.

---

## 5. Test Results

### Phase 0 contract tests
```
backend/tests/test_v9_phase0_contracts.py: 91 passed in 0.21s
```

### Regression gate
```
Stage 1: Correctness harness ... PASS (70 tests)
Stage 2: Broader backend suite ... PASS (full suite)
REGRESSION CHECK PASSED
```

---

## 6. Recommended Next Prompt: Phase 1 Deterministic Runtime Substrate

```
You are working inside the falsification-engine repo.

Your job is to execute Phase 1 from:
  v_9_semantic_compiler_plan.md

Phase 0 is complete. The contract package is frozen at:
  backend/schemas/v9/    (units, rules, compiled_activation, field_registry, errors)
  backend/engine/v9/     (series_interface)
  backend/tests/test_v9_phase0_contracts.py (91 tests, all passing)

Results doc: docs/V9_PHASE0_CONTRACT_RESULTS.md

Read first:
  1. v_9_semantic_compiler_plan.md (Sections 7, 9, 11, 13, 15)
  2. docs/V9_PHASE0_CONTRACT_RESULTS.md
  3. backend/schemas/v9/   (all 5 contract files)
  4. backend/engine/v9/series_interface.py

Phase 1 deliverables:
  1. Full field registry — populate from data_agent.py FRED_SERIES, YAHOO_TICKERS, web-sourced fields
  2. Series primitive engine — implement SeriesPrimitiveEngine against actual time-series data
  3. Rule evaluator — deterministic evaluator that dispatches on rule_type
  4. Compiled activation evaluator scaffold — loads artifact, resolves fields, evaluates rules, computes scores
  5. Validator implementation — uses the Phase 0 error taxonomy to validate artifacts

Success condition:
  - Runtime can evaluate hand-authored compiled artifacts without any model use
  - 91 Phase 0 tests still pass
  - Regression gate still passes
  - New Phase 1 tests cover evaluator correctness

Do not:
  - Modify Phase 0 contract files (they are frozen)
  - Switch production activation to compiled mode
  - Run Haiku compilations
  - Break regression

Start now.
```
