# theories/old_format/ — Historical Artifact (DO NOT DELETE)

These are the original v1 monolithic theory modules. They serve as the ground-truth
reference for what the activation scoring engine produced before the v8 migration.

**Status (2026-04-06):** Historical artifact. Not read at runtime. Not part of the
current regression surface. Retained for archaeological reference.

**Why they are retained:**

1. The v8 ACTIVATION.md files for 3 theories (`valuation_mean_reversion`,
   `fiscal_dominance_arithmetic`, `capital_flows`) contained metric_source strings
   that broke field resolution during the reorganisation. The old files are the
   authoritative record of the machine-parseable metric_source format that worked.
   See `docs/V8_DIVERGENCE_DOCKET.md` for the full investigation.

2. They were used by the now-deprecated migration-era equivalence check script
   (`scripts/v8_equivalence_check.py`). That script is no longer part of the
   active regression surface — it was superseded by the frozen correctness harness
   (`backend/tests/test_activation_correctness.py`) and the canonical regression
   command (`python -m scripts.regression_check`).

3. Nothing in the pipeline reads from this directory at runtime. These files are
   reference material only.
