# Post-v8 Task 5: Single Regression Command Results

**Date:** 2026-04-06
**Baseline:** `docs/POST_V8_TASK4_CORRECTNESS_HARNESS_RESULTS.md` (937 tests passing)

---

## 1. Canonical command

```
python -m scripts.regression_check
```

One command. Offline. Deterministic. No arguments required.

---

## 2. Stages

| Stage | What it runs | Test count | What it catches |
|-------|-------------|------------|-----------------|
| 1 | `backend/tests/test_activation_correctness.py` | 70 | Semantic drift in field resolution, threshold parsing, trigger states, scoring, denominator policy |
| 2 | `backend/tests/` (full suite) | 937 | Parser regressions, lifecycle bugs, prompt builder changes, pipeline integrity, all other backend tests |

Stage 1 is a strict subset of Stage 2 but runs first as the explicit semantic gate. If Stage 1 fails, Stage 2 still runs -- both results are reported.

---

## 3. Sample output (passing)

```
============================================================
  REGRESSION CHECK
  Stages: 2
============================================================

------------------------------------------------------------
  Stage 1: Correctness harness
  Frozen expected-output gate (all 8 theories)
------------------------------------------------------------

  Stage 1: Correctness harness ... PASS  (1.6s)

------------------------------------------------------------
  Stage 2: Broader backend suite
  Full backend test suite
------------------------------------------------------------

  Stage 2: Broader backend suite ... PASS  (6.8s)

============================================================
  RESULTS
============================================================
  Stage 1: Correctness harness ... PASS
  Stage 2: Broader backend suite ... PASS
------------------------------------------------------------
  REGRESSION CHECK PASSED
============================================================
```

---

## 4. Exit-code behavior

| Condition | Exit code |
|-----------|-----------|
| All stages pass | 0 |
| Any stage fails | 1 |

**Proof of failure propagation:** A temporary deliberate-fail test injected into `backend/tests/` produced exit code 1. The temp file was removed immediately after verification.

---

## 5. Design decisions

**Two stages, not three.** The plan mentioned equivalence/comparison scripts, but `v8_equivalence_check.py` restores old parsers from git history -- it is a migration-era tool. The correctness harness (Task 4) subsumes its regression-detection role for ongoing use. Including it would add non-determinism (git history dependency) and latency without improving the regression surface.

**Stage 1 runs redundantly inside Stage 2.** This is deliberate. Stage 1 gives an early, focused signal on the semantic gate before the full suite runs. The ~0.25s overhead is negligible.

**Subprocess output is not suppressed.** On failure, the operator sees full pytest output including assertion details, not just a PASS/FAIL label.

---

## 6. What NOT to do

- Do not add `--quiet` or `-q` flags to suppress pytest output. Failures must be visible.
- Do not add stages that fetch live data or regenerate fixtures.
- Do not auto-update expected outputs inside the regression script.
- Do not use the regression command as a substitute for reading the diff after a semantic change.

---

## 7. Residual issues deferred to Task 6 / v9

| Issue | Disposition |
|-------|------------|
| v8_equivalence_check.py still exists in scripts/ | Task 6 can archive or document as migration artifact |
| No CI integration | Out of scope; operator runs locally |
| Stage timing varies by machine | Informational only; not gated |

---

## 8. Files changed

| File | Change |
|------|--------|
| `scripts/regression_check.py` | New file: canonical regression entrypoint (2 stages) |
| `docs/POST_V8_TASK5_REGRESSION_COMMAND_RESULTS.md` | This file |

---

*Frozen at Task 5 completion. Task 6 (cleanup, closure, v9 boundary) is next.*
