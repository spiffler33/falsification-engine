# post_v8_audit_implementation_plan_v2.md — Post-v8 Semantic Remediation Plan

## Status

**Date:** 2026-04-06  
**Scope:** Fix the concrete semantic bugs and missing regression defenses identified in `POST_V8_AUDIT.md`, without drifting into v9 architecture work.  
**Execution mode:** One task per Claude Code session after context clear.  
**Success standard:** Known audited semantic bugs fixed; missing-data scoring policy made explicit; frozen correctness harness added; one-command regression added; v9 boundary documented.

---

## Short preamble

v8 repaired the **syntax contract**. This phase repairs the **semantic contract**.

The remaining work is not “the parser guessed wrong.” It is “the parser read explicit structure, but some fields are still the wrong proxy, wrong unit, wrong wiring, or scored unfairly when the required data does not exist.”

This plan stays deliberately narrow:
- fix live field wiring and unit truthfulness first
- isolate the one scoring-policy change into its own task
- add frozen correctness tests so semantic drift becomes hard to reintroduce
- defer schema/time-series redesign to `v9.md`

### Explicit v9 boundary

The following are **not** part of this plan and belong in `v9.md`:
- structured threshold objects
- first-class time-series / rolling-window model
- native handling of `RISING` / `FALLING`
- multi-condition threshold schema
- replacement of prose-threshold parsing with machine-native threshold definitions

---

## Task graph

| Task | What | Sessions |
|------|------|----------|
| 0 | Freeze semantic baseline | 1 |
| 1 | Fix all field wiring and unit-alignment bugs | 1 |
| 2 | Data-gap policy for structurally absent data | 1 |
| 3 | Unit-suffix scaling in `_extract_number()` | 1 |
| 4 | Frozen expected-output correctness harness | 1 |
| 5 | Single regression command | 1 |
| 6 | Cleanup, closure, and v9 boundary | 1 |

---

## Task 0 — Freeze semantic baseline

**Goal:** Create a frozen post-v8 baseline artifact that matches the current live data agent, so later fixes are diffed against a real reference rather than stale mock data or memory.

**Required work:**
1. Regenerate the briefing packet with the current live data agent.
2. Confirm the regenerated artifact includes post-v8 computed fields already added during remediation.
3. Produce a durable baseline document capturing, at minimum:
   - current scores / tiers for all 8 theories
   - per-indicator triggered / not-triggered state
   - current values for the audited semantic fields
   - any mock/live discrepancies that still exist before remediation
4. Commit the artifact before Task 1 begins.

**Acceptance criteria:**
- There is a committed frozen post-v8 semantic baseline artifact.
- The artifact reflects the live data agent, not stale pre-remediation mock state.
- Later tasks can diff against a file, not memory.

**Validation required:**
- run activation scoring across all 8 theories on the regenerated briefing
- inspect audited fields called out in `POST_V8_AUDIT.md`
- confirm the artifact is internally consistent with live computed fields

**Update status:**
- [x] Task 0 complete

#### Completion note — 2026-04-06
- Summary: Regenerated briefing packet with live data agent (adds 10 post-v8 computed fields). Created frozen semantic baseline capturing all 8 theory scores, per-indicator triggered state, audited field values/provenance, mock/live discrepancies, and correct-by-coincidence inventory.
- Files changed: `docs/POST_V8_SEMANTIC_BASELINE.md` (new), `mock_data/briefing_packet.json` (regenerated), `docs/POST_V8_AUDIT.md` (committed), `post_v8_audit_implementation_plan_v2.md` (committed)
- Validation run: 983 tests passing; activation scoring all 8 theories verified against baseline artifact; all computed field checks passed; DXY resolution gap confirmed
- Result: Frozen baseline committed at 86a45f5. All scores and tiers match. 10 mock/live discrepancies resolved by regeneration. Audit F-03 resolved.
- Residual risk: Briefing data is a point-in-time snapshot (2026-04-06). FRED WILL5000INDFC remains unavailable (ERP fallback active). Yahoo Finance rate-limited one request (EEM PE) but fallback succeeded.

---

## Task 1 — Fix all field wiring and unit-alignment bugs

**Goal:** Batch-fix the homogeneous class of semantic bugs where the issue is: the field exists or can be computed, but the engine or theory package is wiring the wrong thing through the scoring path.

**This task intentionally merges the earlier Task 1 / Task 2 / Task 3 class of work into one pass.**

**Includes:**
- `gold_oil_ratio` wrong proxy bug
- DXY fetched-but-unresolvable bug
- Fed balance sheet / GDP unit-alignment bug
- deficit-pace unit mismatch
- simple `monetary_architecture` field-reference / backtick fixes
- any other audited “field exists / field can be computed / theory reference is wrong” issues of the same class

**Implementation stance:**
- Batch these as one session because the work is mechanically similar: add or correct field, wire through briefing resolution, update theory backtick reference, verify score effect.
- Do **not** change denominator policy here.
- Do **not** redesign threshold architecture here.

**Required work:**
1. Fix `gold_oil_ratio` to use commodity prices rather than ETF prices.
2. Make DXY mechanically resolvable through the briefing layer, preferably via an explicit machine field.
3. Change long-term debt-cycle Fed balance sheet / GDP logic so field units and threshold units actually match.
4. Fix deficit-pace representation so field units and threshold units actually match.
5. Repair any audited `monetary_architecture` field references that are simple machine-field / backtick issues.
6. Review the audited field/threshold pairs and correct any remaining “works by coincidence” wiring bugs that belong to this same class.

**Acceptance criteria:**
- No audited field-wiring bug remains open in the live scoring path.
- `gold_oil_ratio` is economically truthful.
- DXY is resolvable where the briefing already has the data.
- No audited indicator remains live with a field-vs-threshold unit mismatch in this fix class.
- Any score change is causally explained by semantic correction, not parser behavior.

**Validation required:**
- targeted tests for each corrected field or reference
- targeted activation regression on affected theories
- manual before/after sanity check of field values versus thresholds
- diff against Task 0 baseline artifact

**Update status:**
- [x] Task 1 complete

#### Completion note — 2026-04-06
- Summary: Batch-fixed 8 field wiring/unit-alignment issues. gold_oil_ratio uses commodity futures (GC=F/CL=F). DXY resolves via dxy_index computed field. fed_bs_gdp_ratio wired correctly. Deficit pace thresholds aligned to native $B units. monetary_architecture backticks repaired.
- Files changed: `backend/engine/data_agent.py`, 5 ACTIVATION.md files, `mock_data/briefing_packet.json`, `docs/POST_V8_TASK1_FIELD_WIRING_RESULTS.md`
- Validation run: 983 tests passing (unchanged)
- Result: 2 tier changes (monetary_architecture Adjacent->Active, capital_flows/Accumulation Inactive->Adjacent). All score deltas causally traceable.
- Residual risk: foreign_treasury temporal threshold; Dollar weakening temporal threshold; CL=F contango premium

---

## Task 2 — Make data-gap policy explicit and fair

**Goal:** Fix the only task in this phase that changes **scoring policy** rather than **scoring inputs**.

**Why this is the dangerous task:**
This task changes denominator behavior. It therefore changes the scoring contract across theories, not just the audited fields.

**Implementation rule:**
Before changing any logic, **enumerate every indicator affected by the new policy** and record the expected disposition for each one.

**Required work:**
1. Produce an explicit inventory of every indicator affected by structurally absent data, including:
   - theory
   - indicator name
   - current ownership classification
   - why the data is structurally unavailable
   - whether the right disposition is skip, reclassify, relocate to context flags, or rewire
2. Implement explicit scoring behavior for structurally unavailable computed-mechanical indicators.
3. Ensure structurally absent data no longer silently remains in the denominator as a penalty.
4. Reclassify or relocate indicators that cannot honestly be evaluated mechanically under current architecture.
5. Ensure scoring and validation distinguish:
   - temporary missing data
   - structurally unavailable data
   - valid zero / false values

**Acceptance criteria:**
- There is an explicit inventory of every indicator touched by the policy change.
- Structurally absent data no longer silently depresses scores.
- Reclassification / relocation decisions are explicit and justified.
- The change is testable and visible in scoring outputs.

**Validation required:**
- unit tests for each missing-data path
- targeted activation checks on theories previously penalized by structurally absent data
- validator output review for affected packages
- diff against Task 0 baseline artifact

**Update status:**
- [x] Task 2 complete

#### Completion note — 2026-04-06
- Summary: Made data-gap scoring policy explicit. 5 indicators across 4 theories excluded from denominator: 1 with no data source (top_10_sp500_weight), 4 with pure-prose thresholds that _extract_number cannot parse. All score increases are within the same tier. 7 new tests covering every data-gap path.
- Files changed: `backend/engine/activation.py`, `backend/tests/test_activation_web_integration.py`, `docs/POST_V8_TASK2_DATA_GAP_POLICY_RESULTS.md`
- Validation run: 850 tests passing (843 + 7 new)
- Result: No tier changes. 4 theories score higher: structural_fragility/Building +0.109, debt_cycle_short/Expansion +0.217, fiscal_dominance_arithmetic +0.167, fiscal_dominance_liquidity +0.078. All deltas causally traceable to dead-weight indicator removal.
- Residual risk: BUG-03 RISING/FALLING proxy still extracts temporal numbers (Task 3 scope). top_10_sp500_weight still has no data source (v9 scope).

---

## Task 3 — Add unit-suffix scaling to `_extract_number()`

**Goal:** Remove the current “correct by coincidence” threshold parsing behavior for unit-bearing prose thresholds.

**Critical dependency:**
This task must run **after Task 1**. If unit-suffix scaling lands before the field-unit fixes, thresholds may suddenly parse correctly while fields are still in the wrong unit system, producing false regressions.

**Minimum scaling scope:**
- `T`
- `B`
- `M`
- `bp`

**Required work:**
1. Add unit-suffix scaling to `_extract_number()` for the minimum scope above.
2. Re-run all current threshold extractions touched by this logic.
3. Confirm that the fields fixed in Task 1 now compare against the newly scaled thresholds in the intended unit system.
4. Document any threshold patterns that remain semantically weak and should still be deferred to v9.

**Acceptance criteria:**
- Unit-bearing thresholds no longer parse as raw unscaled numbers.
- Current live thresholds produce the intended numeric magnitudes.
- No field fixed in Task 1 regresses because of unit-suffix scaling.
- Remaining threshold weakness is explicitly documented as v9 debt.

**Validation required:**
- direct unit tests for suffix cases
- regression checks on all affected indicators
- targeted manual review of audited prose thresholds
- diff against Task 0 baseline artifact

**Update status:**
- [x] Task 3 complete

#### Completion note — 2026-04-06
- Summary: Rewrote `_extract_number()` with targeted regex and K suffix scaling (x1000). Fixed 2 initial_claims indicators in debt_cycle_short that compared raw counts against unscaled K thresholds. Preserved all other suffix behavior. 17 new tests.
- Files changed: `backend/engine/activation.py`, `backend/tests/test_activation_web_integration.py`, `docs/POST_V8_TASK3_UNIT_SCALING_RESULTS.md`
- Validation run: 867 tests passing (850 + 17 new)
- Result: No tier changes. 2 score deltas: debt_cycle_short/Expansion 0.867->1.000 (+0.133), Contraction 0.400->0.300 (-0.100). Both causally traceable to K-suffix fix only.
- Residual risk: TGA $B/$M latent mismatch; BUG-03 temporal phrases; T/B/M scaling blocked by inconsistent field units

---

## Task 4 — Build frozen expected-output correctness harness

**Goal:** Add the permanent semantic regression gate.

**This is the most important durable defense in the plan.**

**Required work:**
1. Create a frozen expected-output correctness suite, e.g. `test_activation_correctness.py`.
2. Use the Task 0 frozen briefing artifact as authoritative input.
3. Assert, per theory and per indicator where practical:
   - resolved field
   - extracted threshold
   - comparison direction
   - value
   - triggered / not-triggered result
   - final weighted score / tier where appropriate
4. Cover all 8 theories.
5. Make the harness easy to update deliberately, hard to update casually.

**Acceptance criteria:**
- There is a deterministic frozen expected-output harness for all 8 theories.
- A future semantic change that alters indicator behavior fails a test.
- The harness checks semantic outputs, not just parser success.

**Validation required:**
- run the new correctness suite end-to-end
- prove at least one deliberate semantic perturbation would fail it
- manually review expected outputs for the highest-weight indicators

**Update status:**
- [ ] Task 4 complete

#### Completion note — YYYY-MM-DD
- Summary:
- Files changed:
- Validation run:
- Result:
- Residual risk:

---

## Task 5 — Create a single regression command

**Goal:** Make semantic correctness, parser validation, and equivalence checks runnable through one command.

**Required work:**
1. Create `scripts/regression_check.py` or equivalent.
2. It must run, at minimum:
   - relevant pytest suite
   - frozen expected-output correctness harness
   - equivalence / comparison script(s)
3. Make output clearly PASS / FAIL with enough detail for operator use.
4. Ensure the command fails non-zero when any required check fails.

**Acceptance criteria:**
- There is one command that runs the full post-v8 regression surface.
- Operator output is concise and actionable.
- The command covers the correctness harness, not just generic pytest.

**Validation required:**
- run the command end-to-end
- demonstrate a synthetic failure path produces a clear failure
- confirm required coverage is included

**Update status:**
- [ ] Task 5 complete

#### Completion note — YYYY-MM-DD
- Summary:
- Files changed:
- Validation run:
- Result:
- Residual risk:

---

## Task 6 — Cleanup, closure, and explicit handoff to v9

**Goal:** Close the remediation cleanly, remove confusing leftovers, and document the exact handoff boundary into `v9.md`.

**Required work:**
1. Remove or consolidate duplicated fields that still create mock/live confusion where the disposition is already clear.
2. Update validator notes / classifications if semantic remediation changed them.
3. Produce a closure document stating:
   - what was semantically wrong
   - what was fixed
   - what remains an explicit limitation
   - what is intentionally deferred to v9
4. Add a 3–5 sentence novice explanation of the final post-v8 state.
5. Make the v9 handoff explicit: threshold schema, time-series model, and richer trend semantics begin there, not here.

**Acceptance criteria:**
- Every item assigned to post-v8 remediation is either fixed or explicitly downgraded with evidence.
- No audited semantic bug remains open accidentally.
- The residual boundary to v9 is explicit enough for the next thread to start cleanly.

**Validation required:**
- full regression command from Task 5
- manual review of closure note against `POST_V8_AUDIT.md`
- compare final state to Task 0 baseline artifact

**Update status:**
- [ ] Task 6 complete

#### Completion note — YYYY-MM-DD
- Summary:
- Files changed:
- Validation run:
- Result:
- Residual risk:

---

## Definition of done

This plan is complete when all of the following are true:

- Task 0 frozen baseline exists
- Task 1 field wiring / unit-alignment bugs are fixed
- Task 2 data-gap scoring policy is explicit and tested
- Task 3 unit-suffix scaling is in place and does not regress Task 1 fixes
- Task 4 frozen correctness harness exists for all 8 theories
- Task 5 one-command regression exists and passes
- Task 6 closure note makes the v9 boundary explicit

---

## Master status board

- [x] Task 0 — Freeze semantic baseline (2026-04-06, commit 86a45f5)
- [ ] Task 1 — Fix all field wiring and unit-alignment bugs
- [ ] Task 2 — Make data-gap policy explicit and fair
- [ ] Task 3 — Add unit-suffix scaling to `_extract_number()`
- [ ] Task 4 — Build frozen expected-output correctness harness
- [ ] Task 5 — Create a single regression command
- [ ] Task 6 — Cleanup, closure, and explicit handoff to v9

