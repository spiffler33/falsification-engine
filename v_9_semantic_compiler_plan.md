# v9 Semantic Compiler Plan

**Status:** Draft for implementation
**Date:** 2026-04-06
**Purpose:** Replace regex-over-prose semantic parsing in Pass 1 activation scoring with a compiled, human-auditable semantic contract.

---

## 1. Why v9 exists

The post-v8 phase closed the immediate semantic bugs without redesigning the architecture. That was the right boundary. The current system is now stable enough to trust as a regression baseline, but the semantic contract is still represented in the wrong form: English prose plus runtime regex extraction.

That architecture is now the bottleneck.

v9 exists to replace:
- number extraction from prose thresholds
- backtick hunting for metric fields
- implicit direction inference from English phrases
- accidental scoring via coincidental numbers inside narrative text

with:
- **compile-time semantic extraction from English**
- **deterministic, validated machine-readable artifacts**
- **runtime scoring that is fully deterministic and does not call an LLM**

---

## 2. v9 design boundary

### v9 DOES
- move semantic interpretation upstream into a compiler layer
- keep runtime scoring deterministic
- preserve human-auditability of theory logic
- surface ambiguity explicitly instead of guessing through it
- support incremental migration theory by theory
- preserve the meaning of the existing correctness harness and regression command

### v9 DOES NOT
- put an LLM in the live scoring loop
- turn activation scoring into a probabilistic or narrative process
- rely on “better regex” as the core solution
- auto-regenerate expected outputs silently
- redesign Pass 2/3 reasoning in this phase
- ask Haiku to do deep macro interpretation; that remains a human / high-end-model design activity upstream

---

## 3. Core architectural principle

Use each component for the thing it is structurally best at.

### Haiku compiler layer
Use Haiku for:
- parsing messy English activation text
- separating level conditions from trend conditions
- separating field references from narrative rationale
- distinguishing units, windows, comparators, and boolean structure
- extracting ambiguity when English cannot be compiled cleanly
- compiling theory docs into structured artifacts

### Deterministic Python runtime
Use deterministic code for:
- field resolution
- unit normalization
- time-series primitive computation
- boolean evaluation
- phase transitions
- scoring
- denominator policy
- validation
- testing
- loud failure on contract violations

### Human / heavy-reasoning layer
Use a human or a stronger model only for:
- theory design
- theory revision
- deciding what the activation text should mean
- resolving real ambiguity that should not be guessed through

---

## 4. The key v9 move

The new architecture is:

**English theory package -> semantic compiler -> compiled artifact -> deterministic runtime evaluation**

The runtime engine no longer interprets prose.
It evaluates compiled rules.

The source of truth becomes two-layered:

1. **Human source** = theory package written in English
2. **Machine contract** = compiled artifact checked into the repo and validated before runtime

That is the central v9 contract.

---

## 5. Why Haiku is sufficient for the compiler

The compiler problem is mostly an **English-to-structure** problem, not a deep inference problem.

We are not asking the model to:
- invent theory
- decide if the economics is correct
- assess conviction
- improvise around missing semantics

We are asking it to do the narrower job of schema compilation:
- identify the condition being expressed
- identify the fields involved
- identify the comparison type
- identify the window or persistence rule
- identify the units
- identify whether the statement is directly compilable, partially compilable, or ambiguous

That is exactly the kind of cheap, repeatable, upstream transformation Haiku is good enough for.

---

## 6. The missing layer: deterministic series semantics

The current parser fails especially badly on time-series language:
- “rising for 3 months”
- “above 2-year high”
- “re-steepening from deep inversion”
- “positive for 2 of last 3 months”
- “falling, then stabilizing”

These are not scalar-threshold problems.
They are **series semantics** problems.

v9 solves this by separating the problem into two parts:

1. **Stats layer computes primitives from time series**
2. **Compiler maps English onto those primitives**

This is the correct place to combine stats + LLM.

The LLM should not evaluate raw series at runtime.
The LLM should compile English like “rising for 3 months” into an explicit operator over deterministic series primitives.

---

## 7. Canonical series primitives

The runtime engine should expose a closed set of deterministic series primitives. These are the building blocks the compiler is allowed to target.

### Level / point-in-time
- `latest_value(series)`
- `value_at_offset(series, offset)`

### Change / return
- `absolute_change(series, window)`
- `percent_change(series, window)`
- `annualized_change(series, window)`

### Rolling statistics
- `rolling_mean(series, window)`
- `rolling_sum(series, window)`
- `rolling_max(series, window)`
- `rolling_min(series, window)`
- `rolling_std(series, window)`
- `zscore(series, window)`

### Rank / historical context
- `percentile_rank(series, lookback)`
- `is_new_high(series, lookback)`
- `is_new_low(series, lookback)`
- `distance_from_high(series, lookback)`
- `distance_from_low(series, lookback)`

### Trend / slope
- `slope(series, window)`
- `trend_direction(series, window)`
- `is_rising(series, window)`
- `is_falling(series, window)`
- `acceleration(series, window)`

### Crossover / relative conditions
- `crossed_above(series_a, series_b, window)`
- `crossed_below(series_a, series_b, window)`
- `above_moving_average(series, ma_window)`
- `below_moving_average(series, ma_window)`

### Persistence / counting
- `count_true(condition, lookback)`
- `n_of_last_k(condition, n, k)`
- `consecutive_true(condition, n)`

### Sequence / state patterns
- `transitioned_from_to(state_a, state_b, window)`
- `breakout_after_range(series, range_window, breakout_window)`
- `resteepened_after_inversion(curve_series, inversion_threshold, min_inversion_duration, resteepening_amount)`

### Field-to-field comparisons
- `compare_series_or_scalar(lhs, rhs, comparator)`

These primitives should be explicit, closed, and versioned.
If a theory phrase cannot be expressed with them, the compiler must flag that fact.

---

## 8. Compiler output model

The compiler does not output “best effort JSON.”
It outputs a structured intermediate representation with provenance and ambiguity metadata.

### Top-level artifact shape

```yaml
schema_version: 1
artifact_type: activation_semantics
artifact_status: approved

theory_id: debt_cycle_short
source_package:
  package_version: 1
  source_hash: ...
  compiled_at: ...

compiler:
  engine: haiku
  model: ...
  compile_mode: canonical

ambiguities: []
warnings: []

activation:
  phase_model: two_phase
  phases: [...]
  transition_logic: ...
  thresholds:
    active: 0.60
    adjacent: 0.30
  indicators: [...]
  context_flags: [...]
  state_falsifiers: [...]
```

### Per-indicator shape

```yaml
- indicator_id: expansion_ism_above_contraction
  display_name: ISM proxy above contraction
  source_span:
    file: ACTIVATION.md
    section: Phase A
    line_range: 12-18
  source_text: "ISM proxy above contraction | growth.ism_proxy | Above 50"
  normalized_paraphrase: "Trigger when ISM proxy is above 50."
  metric_dependencies:
    primary_fields:
      - growth.ism_proxy
    derived_series: []
  data_ownership: mechanical
  rule:
    type: compare
    comparator: gt
    left:
      type: field
      value: growth.ism_proxy
    right:
      type: literal
      value: 50
      unit: index_points
  weight: 0.15
  exclusion_policy: score_if_evaluable
  notes: []
```

---

## 9. Rule schema

The runtime should evaluate a typed rule AST, not free text.

### Rule types

#### A. Scalar comparison
```yaml
rule:
  type: compare
  comparator: gt | gte | lt | lte | eq
  left: <operand>
  right: <operand>
```

#### B. Range check
```yaml
rule:
  type: between
  subject: <operand>
  lower: <operand>
  upper: <operand>
  inclusive: true
```

#### C. Boolean compound
```yaml
rule:
  type: compound
  operator: all | any
  clauses:
    - <rule>
    - <rule>
```

#### D. Trend / persistence
```yaml
rule:
  type: persistence
  condition:
    type: compare
    ...
  requirement:
    mode: consecutive | n_of_last_k
    n: 3
    k: 3
  lookback:
    value: 3
    unit: months
```

#### E. Historical extreme
```yaml
rule:
  type: historical_extreme
  subject:
    type: field
    value: qqq_iwm_ratio
  extreme: high | low
  lookback:
    value: 24
    unit: months
  comparator: at_or_above
```

#### F. Trend state
```yaml
rule:
  type: trend_state
  subject:
    type: field
    value: dxy_index
  state: rising | falling | flat
  lookback:
    value: 3
    unit: months
```

#### G. Field-to-field comparison
```yaml
rule:
  type: compare
  comparator: lt
  left:
    type: field
    value: rates.fed_funds
  right:
    type: derived
    fn: nominal_gdp_growth
    args: [growth.gdp_series]
```
```

#### H. Named pattern
For patterns too common to rewrite each time, allow named deterministic evaluators.

```yaml
rule:
  type: named_pattern
  name: resteepened_after_deep_inversion
  params:
    curve_field: rates.curve_2s10s
    inversion_threshold: -0.50
    min_inversion_duration_months: 3
    resteepening_amount_bp: 75
```

This lets the schema stay readable while keeping evaluation deterministic.

---

## 10. Unit model

One of the main sources of current semantic fragility is the lack of explicit unit contracts.

v9 artifacts must carry units explicitly.

### Canonical unit enum
Examples:
- `percent`
- `basis_points`
- `usd_billions`
- `usd_millions`
- `index_points`
- `ratio`
- `count`
- `tons`
- `months`
- `years`

### Unit rules
- literals must declare units where meaningful
- fields must be resolvable to canonical units
- comparisons across mismatched units are invalid unless an explicit conversion exists
- conversion logic must be deterministic and centralized
- if a threshold phrase does not expose enough information to assign a unit cleanly, compilation fails or requires review

---

## 11. Field registry contract

The compiler must target a deterministic field registry rather than free-form field strings.

### The registry must define
- canonical field id
- path
- description
- unit
- whether scalar or series
- freshness expectations
- dependencies for computed fields
- whether runtime can evaluate it mechanically

### Example
```yaml
field_id: growth.initial_claims
kind: series
unit: count
frequency: weekly
source: fred
```

The compiler can only emit field references that exist in the registry.
Unknown field reference = compile failure.

---

## 12. Ambiguity policy

Ambiguity must be surfaced explicitly, not guessed through.

### Compiler output states
Each indicator compilation attempt must land in one of three buckets:

1. **Compilable**
   - unambiguous
   - maps cleanly to runtime primitives

2. **Compilable with warning**
   - structurally valid
   - but contains a judgment call or fallback normalization that should be reviewed

3. **Blocked / needs review**
   - ambiguous English
   - unsupported semantic pattern
   - unresolved field/unit/window/comparator

### Examples of ambiguity that should block
- “elevated” without threshold or percentile definition
- “historically high” without lookback/window semantics
- “rising” without period or persistence definition where persistence matters
- compound phrases where boolean structure is unclear
- field-vs-field comparison where one side has no deterministic definition yet

The runtime must never see blocked artifacts.

---

## 13. Validator contract

After Haiku emits a draft artifact, deterministic Python validation must decide whether it is admissible.

### Validator checks
- schema validity
- all fields exist in registry
- all units are valid
- all rule types are supported
- all named patterns exist in evaluator registry
- all phase references are consistent
- all weights are present and valid
- transition logic is well-formed
- all ambiguity markers are accounted for
- no unresolved placeholders remain
- no unsupported prose is left in the runtime rule body

### Validator output
```yaml
validation_status: pass | warning | fail
errors: [...]
warnings: [...]
```

Only `pass` artifacts may become runtime-authoritative.

---

## 14. Human audit surface

Compiled artifacts must be easy to read and review.

That means each indicator should carry:
- original source text
- normalized paraphrase
- source location
- resolved fields
- resolved units
- explicit rule AST
- compiler warnings

A human reviewing the artifact should be able to answer:
- What did the English say?
- What did the compiler think it meant?
- What will the runtime actually evaluate?
- Where is the ambiguity, if any?

If that is not obvious from the artifact, the artifact is too machine-native and not auditable enough.

---

## 15. Runtime contract

Runtime scoring must remain deterministic.

### Runtime receives only
- compiled artifact
- briefing packet / field registry values / derived deterministic series

### Runtime does not do
- prose interpretation
- regex number extraction
- backtick scanning
- English trend inference
- model calls of any kind

### Runtime responsibilities
- load compiled artifact
- resolve fields
- compute needed series primitives
- evaluate rule AST
- apply denominator policy
- compute weighted phase scores
- apply phase transitions and activation states
- emit results in current activation result format or compatible successor format

---

## 16. Migration strategy

Migration should be incremental and reversible until fully complete.

### Dual-path mode
For a period, the activation engine supports two modes:

- **legacy mode**: current prose parser
- **compiled mode**: compiled artifact evaluator

Selection rule per theory:
- if approved compiled artifact exists for a theory, use compiled mode
- otherwise use legacy mode

This allows theory-by-theory migration without destabilizing the entire engine.

### Migration order
Recommended pilot sequence:

1. `valuation_mean_reversion`
   - relatively simple
   - good for end-to-end proof of artifact contract

2. `debt_cycle_short`
   - forces the architecture to handle temporal and compound rules properly
   - good stress test for series semantics

3. Remaining theories
   - migrate one at a time

### Per-theory migration steps
1. Freeze current behavior against the existing harness.
2. Compile ACTIVATION.md into v9 artifact.
3. Run validator.
4. Produce semantic diff report:
   - legacy interpretation
   - compiled interpretation
   - changed rule semantics
   - changed outcomes on frozen briefing
5. Human review.
6. Approve artifact and enable compiled mode for that theory.
7. Update tests deliberately where changed behavior is intended.

---

## 17. Correctness harness and regression preservation

The existing regression surface must stay meaningful.

### Preserve
- `backend/tests/test_activation_correctness.py`
- `python -m scripts.regression_check`
- offline deterministic execution
- explicit semantic gate before full suite

### Extend
Add three test classes during migration:

#### A. Artifact validation tests
- schema parses
- validator passes
- no blocked ambiguities
- source hashes match expected source files

#### B. Compiled correctness tests
For migrated theories, assert exact expected outputs against the frozen briefing packet.

#### C. Legacy-vs-compiled comparison tests
Temporary during migration.
Not all differences should fail.
Only unapproved or unexplained differences should fail.

### Test philosophy
- do not auto-regenerate fixtures
- do not let the compiler change runtime behavior silently
- fixture updates must be explicit and justified

The operator experience should remain:

```bash
python -m scripts.regression_check
```

That command must still mean:
- semantic gate first
- full backend suite second
- offline
- deterministic

---

## 18. Required new components

### Compiler components
- `backend/engine/semantic_compiler.py`
- `backend/engine/compiler_adapters/haiku_adapter.py`
- `backend/engine/compiler_normalizer.py`
- `backend/engine/compiler_validator.py`
- `backend/engine/semantic_diff.py`

### Runtime evaluator components
- `backend/engine/compiled_activation.py`
- `backend/engine/rule_evaluator.py`
- `backend/engine/series_primitives.py`
- `backend/engine/field_registry.py`
- `backend/schemas/compiled_activation.py`

### Artifacts / storage
- `theories/<theory_id>/compiled/ACTIVATION.compiled.yaml`
- optional review report per theory during migration

---

## 19. Phased implementation plan

### Phase 0 — contract design [COMPLETE 2026-04-07]
Deliverables:
- artifact schema
- rule schema
- unit enum
- field registry contract
- series primitive catalogue
- validator error taxonomy

Results: 91 tests, regression gate PASS. See docs/V9_PHASE0_CONTRACT_RESULTS.md.
Files: backend/schemas/v9/, backend/engine/v9/, backend/tests/test_v9_phase0_contracts.py

### Phase 1 — deterministic runtime substrate [COMPLETE 2026-04-07]
Deliverables:
- field registry (80+ fields from FRED, Yahoo, computed, web sources)
- series primitive engine (19 primitives + Sahm Rule, resteepening)
- rule evaluator (8 rule types with unit normalization)
- compiled activation evaluator scaffold (exclusion policy, two-phase logic)
- artifact validator (25 error codes from Phase 0 taxonomy)
- derived function registry (nominal_gdp_growth)

Success condition:
- runtime can evaluate hand-authored compiled artifacts without any model use

Results: 65 Phase 1 tests + 91 Phase 0 tests, regression gate PASS. See docs/V9_PHASE1_RUNTIME_RESULTS.md.
Files: backend/engine/v9/{registry_builder,series_engine,rule_evaluator,compiled_evaluator,validator,derived_functions}.py
Investigation: eem_spy_3y_relative mismatch = legacy threshold extraction bug (regex strips sign). Compiled rule correct.

### Phase 2 — Haiku compiler scaffold + parallel comparison [COMPLETE 2026-04-07]
Deliverables:
- Haiku compiler adapter
- compiler prompt / output contract
- normalization layer
- validator integration

Results: All 8 theories compiled (68 indicators: 19 clean, 46 warn, 3 blocked). Parallel comparison with semantic diff. 46 tests. See docs/V9_PHASE2_COMPILATION_RESULTS.md, V9_PHASE2_SEMANTIC_DIFF.md.
Files: backend/engine/v9/{compiler,compile_all,parallel_compare,semantic_diff}.py, artifacts/v9/*.compiled.json

### Phase 3 — dual-path engine + first 3 approvals [COMPLETE 2026-04-07]
Actual scope expanded: combined pilot theories + dual-path engine + Haiku API pipeline + weight corrections + generic repairs.

Sub-phases:
- Phase 3.0: Dual-path engine (score_all_packages auto-routes per artifact_status)
- Phase 3.5: Haiku API pipeline (activation_parser + compiler_prompt + CLI)
- Phase 3.6: Weight correction (ACTIVATION.md is source of truth, compile_all.py had transcription errors)
- Phase 3.7: Generic post-compilation repairs (prune UNRESOLVED + remove illegal field_comparisons)

Results: 3 theories APPROVED (valuation_mean_reversion, debt_cycle_long, fiscal_dominance_arithmetic). 1203 tests. See docs/V9_PHASE3_DUAL_PATH_RESULTS.md, V9_PHASE3_5/3_6/3_7 results docs.
Files: backend/engine/v9/{dual_path,activation_parser,compiler_prompt,compiler_repairs}.py

### Phase 4 — full theory approval + legacy deprecation [COMPLETE 2026-04-07]
Sub-phases:
- Phase 4: Approved 3 more (fiscal_dominance_liquidity, debt_cycle_short, monetary_architecture). 6/8 compiled.
- Phase 4B: Fixed capital_flows weight parsing (CALIBRATION tag stripping), fixed structural_fragility missing indicator (repair_missing_indicators). Approved both. 8/8 compiled.

Results: All 8 theories APPROVED on compiled path. Legacy path dormant. 1204 tests. See docs/V9_PHASE4_APPROVAL_RESULTS.md, V9_PHASE4B_REMAINING_APPROVALS.md.

### Phase 5 — SeriesStore (NEXT)
Deliverables:
- implement SeriesStore with time-series data loading
- make 30+ temporal indicators evaluable (currently NOT_EVALUABLE)
- re-run scoring with full temporal coverage
- update harness with temporal indicator results

### Phase 6 — legacy path removal
Deliverables:
- remove prose extraction from runtime path
- simplify dual_path.py to compiled-only
- deprecate `_extract_number()` for activation semantics
- deprecate backtick-based field extraction in activation runtime
- keep legacy parser only as archival/migration utility if still needed

---

## 20. Definition of done for v9

v9 is complete when all of the following are true:

1. No live activation scoring path depends on regex extraction from prose.
2. All runtime-evaluated activation semantics are loaded from approved compiled artifacts.
3. All migrated theories have human-auditable compiled artifacts checked into the repo.
4. Ambiguous activation language fails compilation or requires review; it is not guessed through.
5. The regression gate remains one command and fully deterministic.
6. The system can express temporal and mixed-series semantics through deterministic primitives rather than prose-number accidents.

---

## 21. Explicit non-goals for this document

This document does not specify:
- changes to Pass 2 generation prompts
- changes to Pass 3 elimination prompts
- broader theory re-authoring beyond what is needed to compile ACTIVATION semantics
- LLM-in-runtime evaluation for series interpretation
- automatic policy inference from prose without human review

Those can come later. v9 is specifically about repairing the semantic contract in Pass 1.

---

## 22. Final summary

The correct v9 architecture is not:
- more regex
- or an LLM sitting inside runtime scoring

It is:

**English activation docs -> Haiku semantic compiler -> validated compiled artifacts -> deterministic series/stat evaluation -> deterministic activation scoring**

That gives the system the right split:
- English interpretation at compile time
- statistics and time-series logic at runtime
- zero ambiguity hidden inside regex
- zero model dependence inside live scoring

That is the v9 contract.

