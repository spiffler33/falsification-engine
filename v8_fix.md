# v8_fix.md — V8 Remediation Plan

## Status

**Date:** 2026-04-06  
**Scope:** Eliminate all confirmed v8 correctness bugs and all identified high-risk implicit-contract fragilities in theory package loading, activation scoring, and related markdown parsing paths.  
**Source inputs:** `V8_IMPLICIT_CONTRACT_AUDIT.md`, `V8_DIVERGENCE_DOCKET.md`, existing v8 codebase, theory package markdown, v1/v8 equivalence harness.  
**Execution mode:** One task per Claude Code session after context clear.  
**Success standard:** No silent parser fallbacks on machine-critical paths; all known score regressions explained or fixed; load-time validation catches malformed package inputs before scoring.

---

## 0. Why this fix exists

The v8 migration exposed a mismatch between the system's intellectual architecture and its implementation discipline.

The falsification engine is built on a simple premise: **do not let narrative softness override auditable structure.** The model is used to generate and attack hypotheses; the scoring and decision surface must remain explicit, mechanical, and inspectable.

The v8 bugs violated that spirit at the infrastructure layer. Human-readable markdown prose was being treated as machine-readable identifiers. When formatting changed, the system often did not fail loudly; it continued with silent fallbacks, `None` resolutions, or default behaviors that preserved plausible output while weakening correctness.

This remediation fixes that mismatch.

### Governing principle

**Anything the machine depends on must be explicit, validated, and loud on failure.**

That means:
- prose may explain, but it must not secretly identify
- parser heuristics may assist migration, but they must not silently define the contract
- malformed theory packages must fail validation before scoring
- equivalence must be traced causally, never assumed

### Novice explanation of the approach

We are turning the theory package system from “documents the engine sort of knows how to read” into “documents with explicit, validated machine contracts.” The fix is not just to patch wrong scores; it is to make the system reject ambiguous inputs instead of quietly guessing.

---

## 1. What must be fixed

### A. Confirmed correctness bugs

These change current behavior and must be fixed fully.

1. **BUG-01 — broken `metric_source` field resolution in 3 theories**  
2. **BUG-02 — non-standard direction strings silently default to `above`**  
3. **BUG-03 — `RISING` / `FALLING` treated as simple threshold comparisons**  
4. **BUG-04 — `_normalize_computed_field()` generic fallback produces invalid field names**  
5. **BUG-05 — `_extract_number()` strips unit suffixes without structured scaling / mishandles some prose thresholds**  
6. **BUG-06 — `data_ownership` parse fallback can silently yield invalid ownership values**

### B. High-risk fragilities

These may work today but must be hardened so future edits cannot silently corrupt runtime behavior.

1. **FRAGILITY-01 — exact underscore section-header dependencies**  
2. **FRAGILITY-02 — activation table parser assumes fixed column positions**  
3. **FRAGILITY-03 — phase naming depends on exact `Phase A:` / `Phase B:` forms**  
4. **FRAGILITY-04 — context flags default silently to `qualitative` when ownership column absent**  
5. **FRAGILITY-05 — falsifier severity inferred from free text beyond designated severity column**  
6. **FRAGILITY-06 — falsifier ID extraction searches all cells as fallback**  
7. **FRAGILITY-07 — `_extract_metric_field()` passthrough fallback returns whole strings**  
8. **FRAGILITY-08 — non-numeric weights silently drop indicators**  
9. **FRAGILITY-09 — short rows silently dropped**  
10. **FRAGILITY-10 — `theory_id` extraction depends on narrow markdown patterns**  
11. **FRAGILITY-11 — mixed two-phase activation table formats remain tolerated but under-validated**

---

## 2. Remediation philosophy

### 2.1 What we are doing

We are applying four layers of remediation, in this order:

**Layer 0 — Freeze the bad baseline**  
Record the currently broken behavior as an artifact so every later fix is diffed against a known reference, not memory.

**Layer 1 — Restore correctness now**  
Patch live bugs so the system produces correct scores and correct parser outputs on current theory packages.

**Layer 2 — Remove silent failure modes**  
Replace permissive fallbacks with explicit validation errors on machine-critical paths.

**Layer 3 — Formalize the contract**  
Add load-time validation so theory package markdown is treated as structured input with a testable schema.

### 2.2 What we are not doing

- We are **not** rewriting the entire theory system into YAML/JSON immediately.
- We are **not** preserving brittle heuristics out of convenience when they mask ambiguity.
- We are **not** classifying behavior differences as “structural reorganisation” unless the causal path is traced and proven.
- We are **not** tolerating “works by coincidence” on scoring-critical code.
- We are **not** creating unnecessary parallel sources of truth when a stricter validator can enforce the contract directly.

### 2.3 Design standard

For any parser or scorer change, prefer this order of outcomes:

1. explicit structured interpretation
2. tightly constrained normalization
3. loud validation error
4. never silent guesswork on critical paths

### 2.4 Immediate architectural stance on Task 1

For the live `metric_source` breakage, the chosen remediation path is:

- **restore explicit backtick field-bearing strings in the affected `ACTIVATION.md` files now**
- **remove the dangerous passthrough fallback in code now**
- **do not introduce a broad new `COMPUTED_FIELD_MAP` in Task 1 unless a narrow explicit bridge is strictly required for current-package correctness**
- **let Task 7's validator become the durable protection layer**

Reasoning:
- restoring the known-good field-bearing strings is the fastest way to recover correctness without inventing a second authority
- a broad computed-field mapping layer would duplicate machine identity in code and markdown, increasing drift risk
- once passthrough is killed and validation exists, future editors cannot silently break the contract the way v8 did

If, during implementation, a tiny explicit bridge is required to keep one current package working while preserving loudness, it must be documented as transitional and scheduled for removal or formalization by Task 7.

---

## 3. Work sequencing

Each task below is intended to be executed in a separate Claude Code session after context clear.

### Task 0 — Freeze baseline artifacts before remediation

**Goal:** Create a fixed known-bad reference point so every later task can diff against recorded evidence rather than memory.

**Required work:**
1. Run the current equivalence / comparison tooling against the existing broken v8 state.
2. Capture the results in a durable artifact inside the repo.
3. Record at minimum:
   - current scores / tiers for the known broken theories
   - current divergence classifications
   - any failing or suspicious indicators already identified by the docket / audit
4. Ensure this artifact is committed before Task 1 begins.

**Acceptance criteria:**
- There is a committed baseline artifact for the broken pre-fix state.
- Later sessions can point to a file, not a memory, when asking “what changed?”
- The artifact is clearly labeled as pre-remediation baseline.

**Validation required:**
- run the equivalence script or nearest deterministic comparison harness
- confirm the artifact reproduces the known broken state described in the docket/audit

**Update status:**
- [x] Task 0 complete

#### Completion note -- 2026-04-06
- Summary: Created `docs/V8_PREREMEDIATION_BASELINE.md` capturing the full broken v8 state: equivalence check output (3 runs: real, stress, recovery), per-indicator breakdowns for all 8 theories, bug/fragility inventory, briefing field reference values, and test suite state (675/675 passing).
- Files changed: `docs/V8_PREREMEDIATION_BASELINE.md` (new)
- Validation run: `python -m scripts.v8_equivalence_check` (3 scenarios), `python -m pytest backend/tests/ -v` (675 tests), per-indicator detail extraction via `activation.score_all_packages()`
- Result: Artifact reproduces all known broken scores from docket: valuation_mean_reversion 0.882->0.294, fiscal_dominance_arithmetic 0.556->0.056, capital_flows 0.450->N/A. All 13 broken indicators documented with resolved field names and failure reasons.
- Residual risk: None. This is a recording task only.

---

### Task 1 — Fix live `metric_source` score breakage and remove silent passthrough

**Goal:** Eliminate the current wrong-score bug on the 3 affected theories and prevent silent recurrence.

**Includes:**
- Fix BUG-01
- Fix FRAGILITY-07
- Review BUG-04 if touched naturally by the same code path

**Implementation decision (settled):**
- Restore explicit backtick field-bearing strings in the affected `ACTIVATION.md` files.
- Kill `_extract_metric_field()` whole-string passthrough on machine-critical paths.
- Do **not** add a broad `COMPUTED_FIELD_MAP` in this task unless a narrow transitional bridge is strictly unavoidable.
- If any transitional bridge is added, it must be explicitly documented in the completion note with a justification and future disposition.

**Required work:**
1. Restore correct field resolution for the 3 affected theories:
   - `valuation_mean_reversion`
   - `fiscal_dominance_arithmetic`
   - `capital_flows`
2. Reconfirm the repaired markdown strings actually resolve to the intended briefing fields.
3. Remove the dangerous `_extract_metric_field()` whole-string passthrough for machine-critical resolution.
4. Ensure unresolved `metric_source` cases now fail loudly or are captured by validation scaffolding rather than silently returning `None` and remaining in the denominator.
5. Review `_normalize_computed_field()` and either:
   - eliminate generic garbage normalization on scoring-critical paths, or
   - constrain it to explicit known mappings only.

**Acceptance criteria:**
- The 3 affected theories no longer show the known broken v8 scores from the divergence docket.
- Any unresolved machine-critical `metric_source` now throws or is surfaced as a validation error.
- No current theory package depends on whole-string passthrough.
- Equivalence / comparison tests show the previous regression removed or precisely explained.

**Validation required:**
- run targeted tests on affected theories
- run v1 vs v8 equivalence script
- add or update unit tests for metric resolution
- demonstrate one synthetic malformed case now fails loudly
- diff results against the Task 0 baseline artifact

**Update status:**
- [x] Task 1 complete

#### Completion note — 2026-04-06
- Summary: Restored backtick-wrapped field names in 3 ACTIVATION.md files (10 indicators across valuation_mean_reversion, fiscal_dominance_arithmetic, capital_flows). Removed _extract_metric_field() whole-string passthrough (FRAGILITY-07). Removed _normalize_computed_field() generic garbage fallback (BUG-04). Updated equivalence script classifications: capital_flows and fiscal_dominance_arithmetic promoted from KNOWN_DIVERGED to EXACT_MATCH.
- Files changed: `theories/THEORY_MODULE_valuation_mean_reversion_v2/ACTIVATION.md`, `theories/THEORY_MODULE_fiscal_dominance_arithmatic_v2/ACTIVATION.md`, `theories/THEORY_MODULE_capital_flows_v2/ACTIVATION.md`, `backend/engine/activation.py`, `scripts/v8_equivalence_check.py`, `backend/tests/test_activation_web_integration.py`
- Validation run: `python -m pytest backend/tests/ -x -q` (702 passed), `python -m scripts.v8_equivalence_check` (ALL PASS, 3 runs), per-indicator trace for all 3 theories confirming field resolution
- Result: fiscal_dominance_arithmetic 0.056→0.556 (EXACT v1 match), capital_flows N/A→0.450 Rotation (EXACT v1 match), valuation_mean_reversion 0.294→0.706 Active (TIER match — remaining gap is BUG-05 cash yield threshold, Task 2 scope). No regressions on 5 unaffected theories.
- Residual risk: valuation_mean_reversion cash yield indicator resolves correctly (rates.fed_funds=3.64) but its v2 threshold text "SHY yield > SPY earnings yield" has no extractable number (v1 had "(1/PE)" → extracted "1"). This is BUG-05, Task 2 scope. DXY indicators in capital_flows remain pre-existing failures (failed in v1 too).

---

### Task 2 — Fix direction semantics and threshold interpretation bugs

**Goal:** Remove semantically wrong comparisons that currently work by accident or default.

**Includes:**
- Fix BUG-02
- Fix BUG-05
- document or sharply bound BUG-03

**Required work:**
1. Audit all direction strings in current v2 packages.
2. Convert non-canonical direction strings to a canonical representation or add explicit parser support.
3. Remove the fallback that defaults unknown directions to `above`.
4. Make unrecognized direction values fail validation.
5. Fix threshold extraction for prose thresholds that are currently parsed incorrectly, especially `interest_exceeds_defense`.
6. For `RISING` / `FALLING`:
   - do not pretend the engine has temporal trend data if it does not
   - formalize them as explicitly provisional threshold proxies **or** a clearly bounded known limitation path
   - document the limitation in code and in validation notes
   - do not let this block the rest of the remediation

**Acceptance criteria:**
- No active direction string in current theory packages relies on accidental `above` fallback.
- At least the known semantically wrong indicators now parse correctly.
- Bad direction inputs fail loudly.
- Threshold parsing for current packages is correct and tested.
- The status of `RISING` / `FALLING` is explicit, documented, and non-misleading.

**Validation required:**
- add/update unit tests for direction parsing and threshold extraction
- run activation tests across all theories
- confirm no tier changes remain unexplained
- diff results against the Task 0 baseline artifact where relevant

**Update status:**
- [x] Task 2 complete

#### Completion note — 2026-04-06
- Summary: Fixed BUG-02 (11 non-canonical direction strings across 6 ACTIVATION.md files replaced with canonical values; `_parse_direction()` fallback removed, now raises ValueError). Fixed BUG-05 (threshold for `interest_exceeds_defense` changed to "Above 0" since field stores surplus; added 2 new computed fields `cash_exceeds_equity_yield` and `real_fed_funds_rate` in data_agent.py to make previously untestable prose thresholds mechanically checkable). Documented BUG-03 (RISING/FALLING explicitly marked as provisional threshold proxies in code comments).
- Files changed: `theories/THEORY_MODULE_valuation_mean_reversion_v2/ACTIVATION.md`, `theories/THEORY_MODULE_fiscal_dominance_arithmatic_v2/ACTIVATION.md`, `theories/THEORY_MODULE_capital_flows_v2/ACTIVATION.md`, `theories/THEORY_MODULE_debt_cycle_long_v2/ACTIVATION.md`, `theories/THEORY_MODULE_debt_cycle_short_v2/ACTIVATION.md`, `theories/THEORY_MODULE_monetary_architecture_v2/ACTIVATION.md`, `backend/engine/activation.py`, `backend/engine/data_agent.py`, `scripts/v8_equivalence_check.py`, `backend/tests/test_activation_web_integration.py`
- Validation run: `python -m pytest backend/tests/ -v` (734 passed, +32 new tests), `python -m scripts.v8_equivalence_check` (ALL PASS, 3 runs)
- Result: fiscal_dominance_arithmetic 0.556→0.722 (Adjacent→Active, intentional improvement: interest_exceeds_defense now correctly triggers). valuation_mean_reversion stable at 0.706 Active (cash yield indicator correctly does not trigger via new computed comparison field). debt_cycle_long stable at 0.900 Active (real_fed_funds_rate=0.98, correctly not triggered below 0). capital_flows stable at 0.450 Adjacent Rotation (Phase A China credit direction fix has no effect on effective score). All other theories unchanged.
- Residual risk: (1) RISING/FALLING directions remain provisional threshold proxies (no temporal trend data). (2) Unit-suffix stripping in `_extract_number()` does not scale ("$1.5T" extracts 1.5 not 1500) — currently produces correct results by coincidence for all active indicators, but not architecturally sound. Both are candidates for later remediation tasks.

---

### Task 3 — Add parser hardening for table rows, weights, ownership, and malformed inputs

**Goal:** Stop silent data loss in activation table parsing.

**Includes:**
- Fix BUG-06
- Fix FRAGILITY-08
- Fix FRAGILITY-09
- address FRAGILITY-04 where appropriate

**Required work:**
1. Validate `data_ownership` against the canonical set.
2. Reject invalid ownership values loudly.
3. Reject non-numeric weights loudly.
4. Reject malformed or short activation table rows loudly rather than silently skipping them.
5. Review `context_flags` ownership behavior and decide whether:
   - missing ownership column is allowed only by explicit rule, or
   - it must be present always
6. Make the rule explicit and validated.

**Acceptance criteria:**
- No silent row dropping on machine-critical tables.
- No invalid ownership values propagate into scoring.
- No non-numeric weights silently disappear.
- Any allowed default behavior is documented, deliberate, and tested.

**Validation required:**
- unit tests for malformed rows, bad ownership, bad weights
- full parser test across all theory packages
- synthetic failure cases must raise predictable errors

**Update status:**
- [x] Task 3 complete

#### Completion note — 2026-04-06
- Summary: Hardened activation table parser with 3 parse-time validations + 1 documented default. BUG-06: added `_VALID_ACTIVATION_OWNERSHIP` canonical set, validated after ownership extraction. FRAGILITY-08: non-numeric weight on data row raises ValueError (was silent skip). FRAGILITY-09: short rows (< 6 cells) after header raise ValueError (was silent drop). FRAGILITY-04: missing ownership column in context_flags allowed only when all flags are qualitative; explicit validation constraint added. Updated existing test for qualitative-in-activation-table error message.
- Files changed: `backend/engine/theory_loader.py`, `backend/tests/test_theory_loader.py`, `backend/tests/test_activation_web_integration.py` (1 existing test message updated)
- Validation run: `python -m pytest backend/tests/ -x -q` (750 passed, +16 new tests), `python -m scripts.v8_equivalence_check` (ALL PASS, 3 runs)
- Result: No score changes (these are validation additions, not behavioral changes). All 8 current theory packages parse clean under new validation. Synthetic malformed inputs raise predictable errors in 4 test classes.
- Residual risk: (1) data_ownership first-token fallback still exists for cosmetic variation, but its output is now validated against the canonical set — cannot silently produce garbage. (2) Short rows before the activation table header are still silently skipped (intentional: may be formatting notes). (3) valuation_mean_reversion 0.706 vs v1 0.882 gap is CLOSED — v1 was inflated by accidental threshold extraction; v8 is correct.

---

### Task 4 — Remove brittle header and table-order dependencies

**Goal:** Make theory markdown readable and editable without depending on exact cosmetic formatting.

**Includes:**
- Fix FRAGILITY-01
- Fix FRAGILITY-02
- improve FRAGILITY-10 where touched

**Required work:**
1. Normalize section header matching so underscore/space/case differences do not break expected section detection where reasonable.
2. Convert activation table parsing from positional-column assumptions to header-name mapping.
3. Review `theory_id` extraction and accept safe format variants where appropriate.
4. Add validation that all required sections are actually found.

**Acceptance criteria:**
- Cosmetic header normalization no longer breaks parsing for supported variants.
- Activation tables are parsed by column meaning, not raw position.
- Missing required sections still fail loudly.
- `theory_id` extraction is robust but not vague.

**Validation required:**
- unit tests using variant header spacing / capitalization
- unit tests with reordered activation columns
- regression test that current packages still parse identically

**Update status:**
- [ ] Task 4 not started
- [ ] Task 4 in progress
- [ ] Task 4 complete

---

### Task 5 — Tighten falsifier parsing to designated columns only

**Goal:** Prevent narrative text from being mistaken for falsifier metadata.

**Includes:**
- Fix FRAGILITY-05
- Fix FRAGILITY-06

**Required work:**
1. Restrict severity extraction to the actual Severity column.
2. Restrict falsifier ID extraction to the designated ID column.
3. Reject malformed falsifier rows loudly instead of searching narrative text for rescue signals.
4. Confirm all current theory packages still build correct falsifier registries.

**Acceptance criteria:**
- Free-text narrative cells can no longer accidentally set severity or ID.
- Malformed falsifier rows fail validation.
- Current falsifier registries remain 1:1 and correct.

**Validation required:**
- unit tests for malformed severity/ID rows
- full falsifier registry tests across all packages

**Update status:**
- [ ] Task 5 not started
- [ ] Task 5 in progress
- [ ] Task 5 complete

---

### Task 6 — Standardize and validate phase structure

**Goal:** Make two-phase theory handling explicit and resistant to format drift.

**Includes:**
- Fix FRAGILITY-03
- Fix FRAGILITY-11

**Required work:**
1. Choose one supported phase representation model and document it.
2. Either normalize both existing patterns into the same internal model with explicit validation, or migrate packages to one canonical pattern.
3. Validate:
   - two-phase theories have exactly two phases
   - phases map deterministically to internal phase names
   - phase precedence logic remains correct
4. Remove reliance on exact cosmetic phase labels where possible.

**Acceptance criteria:**
- All two-phase theories parse deterministically.
- Mixed or malformed phase layouts fail validation.
- Phase precedence in scoring remains unchanged except for intended fixes.

**Validation required:**
- tests for all two-phase theories
- tests for malformed phase structures
- full activation regression tests

**Update status:**
- [ ] Task 6 not started
- [ ] Task 6 in progress
- [ ] Task 6 complete

---

### Task 7 — Add a dedicated theory-package validation pass

**Goal:** Make validation a first-class pre-flight gate rather than an emergent property of downstream failures.

**This is the most important architectural task.**

**Required work:**
1. Implement a validation layer that runs before activation scoring and checks theory packages against an explicit machine contract.
2. The validator must check, at minimum:
   - required sections exist
   - all indicators have valid ownership
   - all indicators have valid directions
   - weights are numeric
   - thresholds are parseable
   - metric resolution succeeds or is explicitly allowed
   - falsifier rows are well-formed
   - phase structure is valid
3. Decide where it runs:
   - load time
   - pre-flight test script
   - or both
4. Add a human-readable validation report so failures are actionable.

**Acceptance criteria:**
- A malformed theory package fails validation before scoring.
- Current packages pass cleanly once all earlier fixes are complete.
- Validation errors name the exact theory, section, row, and field that failed.

**Validation required:**
- tests for validator success on current packages
- tests for representative malformed packages
- full run showing validator passes before scoring

**Update status:**
- [ ] Task 7 not started
- [ ] Task 7 in progress
- [ ] Task 7 complete

---

### Task 8 — Final equivalence, audit closure, and operator explanation

**Goal:** Close the loop formally and explain the final system simply.

**Required work:**
1. Re-run v1 vs v8 equivalence and update the divergence classification honestly.
2. Remove or rewrite any `KNOWN_DIVERGED` language that is no longer true.
3. Produce a short closure note:
   - what was broken
   - what was fixed
   - what remains as an explicit design limitation rather than a bug
4. Produce a 3-5 sentence novice explanation of the final approach.

**Acceptance criteria:**
- Every previously flagged issue is now either fixed or explicitly documented as a deliberate limitation.
- No silent parser-scoring contract issues remain in the audited areas.
- The final explanation is short, clear, and philosophically aligned with the falsification brief.

**Validation required:**
- full test suite relevant to theory loading and activation
- equivalence script
- manual sanity check of key theories
- compare final state to the Task 0 baseline artifact

**Update status:**
- [ ] Task 8 not started
- [ ] Task 8 in progress
- [ ] Task 8 complete

---

## 4. Cross-task rules

These apply to every task.

### 4.1 Root-cause discipline

Do not treat any changed score, tier, registry output, or parser behavior as acceptable until the causal chain is traced:

**markdown input → parser path → internal representation → scoring/registry behavior → output**

### 4.2 Loudness over convenience

When forced to choose, prefer a loud validation error to a permissive heuristic on scoring-critical paths.

### 4.3 Narrow fix, broad test

Each session may target one task, but validation must include:
- direct unit tests for the changed behavior
- nearby regression tests
- whole-package parse or activation checks where relevant

### 4.4 No philosophical drift

The infrastructure must match the engine philosophy:
- explicit where consequence-bearing
- mechanical where scored
- explainable to a novice
- suspicious of hidden narrative softness in machine paths

---

## 5. Required workflow after every task

After completing a task, Claude Code must do **all** of the following before stopping:

1. **Run tests and validations** relevant to that task.
2. **Update this `v8_fix.md` file**:
   - mark the task status accurately
   - add a short dated completion note under the task describing what changed and what validated it
3. **Write a short operator paragraph** for the user to paste into ChatGPT for independent review. This paragraph must include:
   - what was changed
   - what tests passed
   - what residual risk, if any, remains
4. **Update memory / checkpoint context** in whatever project memory pattern Claude Code is using.
5. **Git commit** with a precise message tied to the task.
6. **Push to remote**.
7. **Stop cleanly** and provide a **next-session prompt** that assumes context will be cleared.

### Required completion note format inside `v8_fix.md`

Use this exact pattern under the relevant task:

```md
#### Completion note — YYYY-MM-DD
- Summary:
- Files changed:
- Validation run:
- Result:
- Residual risk:
```

---

## 6. Definition of done

The remediation is done only when all of the following are true:

- all confirmed bugs are fixed
- all high-risk fragilities are either fixed or explicitly downgraded to safe with evidence
- machine-critical parser paths no longer rely on silent fallbacks
- current theory packages pass explicit validation before scoring
- equivalence / divergence classifications are updated honestly
- the final system can be explained simply:
  - humans may write readable theory documents
  - the engine reads explicit validated structure
  - when structure is ambiguous, the system refuses to guess

---

## 7. Master status board

- [x] Task 0 complete
- [x] Task 1 complete
- [x] Task 2 complete
- [x] Task 3 complete
- [ ] Task 4 complete
- [ ] Task 5 complete
- [ ] Task 6 complete
- [ ] Task 7 complete
- [ ] Task 8 complete

**Project status:** NOT COMPLETE
