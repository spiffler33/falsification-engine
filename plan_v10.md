# v10: Three-Pass Generation Split

## Problem

The v7 thread lifecycle crowded out fresh idea generation. The single generation prompt (239 KB, ~61K tokens) tried to do two jobs at once: review existing threads AND generate new hypotheses. With a "7-9 total" cap and "CONFIRM is the default" culture, threads consumed the entire budget and new ideas got squeezed to 0-1 per run. Gold at conviction 9 disappeared because the generator simply didn't include it.

## Solution

Split the single generation prompt into two separate LLM passes with independent mandates. The pipeline goes from 5 steps (2 human-in-loop) to 6 steps (3 human-in-loop).

## Pipeline (6 steps)

| Step | Label | Type | What it does |
|------|-------|------|-------------|
| 1 | Data Briefing | Automated | Refresh FRED + Yahoo data |
| 2 | Activation Scoring | Automated | Score all theories against briefing |
| 3 | **Thread Review** | Human-in-loop | Review existing threads: CONFIRM / UPDATE / RENEW / RETIRE |
| 4 | **Fresh Generation** | Human-in-loop | Generate NEW hypotheses from active theories |
| 5 | Elimination Pass | Human-in-loop | Adversarially attack all hypotheses |
| 6 | Conviction Scoring | Automated | Mechanical scoring pipeline |

## Pass 2A: Thread Review (~30 KB)

Focused solely on lifecycle management. No theory packages needed -- thread context carries the mechanism summary.

**Input:** Active threads (full context with realization, falsifiers, staleness), briefing data, activation score summary.

**Thread health indicators** (new in v10):
- INERTIA WARNING: 3+ consecutive CONFIRMs with no revision
- CONVICTION FLAT/DECLINING: trend across last 3 instances
- FALSIFIER EXHAUSTION: 50%+ soft falsifiers STALE or ESCALATED_UNTESTABLE

**Stronger RETIRE guidance:**
- "A portfolio that never retires anything is not disciplined -- it is stale."
- Explicit RETIRE signals: health flags, hard falsifier FAILED, expression delivered, mechanism unsupported

**Output:** `{"thread_actions": [...]}`

**Does NOT:** Generate new hypotheses.

## Pass 2B: Fresh Generation (~200 KB)

Focused solely on generating NEW hypotheses. The generator's only job.

**Input:** Active theory packages (CORE/TACTICAL/PLAYBOOK), briefing, interaction matrix, regime flags, inbox items, compact thread summary (so the generator knows what exists and doesn't duplicate).

**Key rules:**
- Generate hypotheses from every Active theory. At least one per theory. No cap.
- NEW hypotheses may come from theories that already have threads if the mechanism/expression/assets are materially different.
- CONSOLIDATION CHECK still applies (no 3+ on same directional bet).
- 0-1 from adjacent wildcard.

**Output:** Flat JSON array (legacy format). All items are NEW.

**Does NOT:** Review threads, assign lifecycle actions, CONFIRM anything.

## Key Design Decisions

1. **Independent budgets.** Thread review and fresh generation don't compete for the same slot count. The "7-9 total" cap is gone.
2. **No generation cap.** The elimination pass and conviction scoring ARE the filter. Capping generation does the eliminator's job for it.
3. **NEW from represented theories.** A new gold hypothesis is possible even if a gold thread already exists, as long as it proposes a different mechanism or expression.
4. **Thread health indicators.** The LLM never had signal that a thread was being rubber-stamped. Now it does.
5. **First run auto-skip.** When no threads exist, Thread Review auto-completes and Fresh Generation uses the legacy prompt.

## Files Modified

### prompt_builder.py
- `build_thread_review_prompt()` -- new, ~30 KB output
- `build_fresh_generation_prompt()` -- new, ~200 KB output, uncapped generation
- `_get_display_score()` -- new helper
- `_thread_context_section()` -- added thread health indicators (inertia, conviction trend, falsifier exhaustion)
- `_thread_lifecycle_contract()` -- stronger RETIRE guidance, removed "5 CONFIRMs + 1 NEW is ideal"
- `build_generation_prompt_v8()` -- preserved for legacy first-run fallback

### pipeline.py
- `GET /api/pipeline/prompt/thread-review` -- new endpoint
- `POST /api/pipeline/import/thread-review` -- new endpoint, FK-safe hypothesis deletion
- `GET /api/pipeline/prompt/generation` -- modified: uses fresh generation prompt when threads exist, legacy when not
- `POST /api/pipeline/import/generation` -- preserved for both legacy and split flows
- `_get_current_pipeline_state()` -- 6-step state machine
- `_build_thread_summaries_for_prompt()` -- enriched with confirmation_count, conviction_trend, escalated_or_stale_count
- `_build_compact_thread_summary()` -- new helper for fresh generation prompt

### PipelineView.jsx
- STEP_DEFS: 6 steps (was 5)
- Thread Review step at index 2: COPY PROMPT / IMPORT RESULT
- Fresh Generation step at index 3
- Elimination shifted to index 4
- RunSummary checks conviction at index 5

### RunSummary.jsx (also v10)
- STATUS column (KILLED/SURVIVED/WOUNDED)
- Clickable rows -- opens ThreadDetail/HypothesisDetail modal

## Implementation Status

**COMPLETE (2026-04-09).** All changes implemented, tested (1197 pass, 0 regressions), committed, pushed, published to GH Pages. DB cleared for fresh start.

Commits: dcb1820, c222295, 2570a72, c9e9b3a, 441f365, d5e715f

## Bugfix: Scoped Import Deletion (2026-04-11)

**Problem:** `import_generation` (line 927) unconditionally deleted ALL hypotheses for the run, including CONFIRM/UPDATE/RENEW instances created by `import_thread_review`. Thread-review was effectively a no-op -- its results were always destroyed by the generation import that followed.

Root cause: commit `c9e9b3a` reverted split-flow protection to fix legacy-flow UNIQUE constraint violations, using a sledgehammer `DELETE WHERE run_id = X` that nuked both import types.

**Impact on first live run (R-20260410-230800):** Gold threads (conviction 7/10 and 6/10) were correctly CONFIRMed by thread-review, then silently destroyed by generation import. Thread counters were inflated but instances gone. Newsletter NL-2026-002 saw no gold, proposed closing all gold trades.

**Fix (commits d9ae246 + 6f4bfe3):** Three issues fixed:
1. Scoped deletion -- each import only clears its own lifecycle actions. `import_thread_review`: CONFIRM/UPDATE/RENEW only. `import_generation`: auto-detects legacy vs split flow (split: NEW only, legacy: all).
2. ID renumbering -- both imports call the same parser which numbers from -01. Second import offsets past highest existing ID for the run. Prevents UNIQUE constraint violations.
3. FK-safe deletion -- circular FK between `hypothesis.thread_id` and `thread.originating_instance_id`. Nulls `thread_id` before deleting threads on re-import.

Parse moved before delete in generation import (validates before modifying DB).

**Tests:** 13 integration tests in `backend/tests/test_split_pipeline_integration.py`. 1348 total tests pass.

**Bugfix 2: source_theories inheritance (2026-04-11, commit bfc0a82)**

Parser defaults `source_theories` to `'["unknown"]'` for CONFIRM actions missing `theory_id`. `_inherit_field` sentinel check only matched `"unknown"` (plain string), not `'["unknown"]'` (JSON array). All CONFIRMs hit conviction floor scores (support=0.3, evidence=0.2) because the mechanical scorer looked up theory "unknown" in the activation map. Gold went from conviction 7 to 4 (killed). Fixed by adding `'["unknown"]'` to sentinel list.

**Successful run: R-20260411-150952.** 18 hypotheses (11 CONFIRM + 7 NEW). After re-scoring: 12 SURVIVED, 6 KILLED. Gold CONFIRM at conviction 7. Deep audit passed: field inheritance, soft falsifier discounts, elimination notes, overlap, thread state all verified correct.

**Cleanup:** All failed runs (R-20260410, earlier R-20260411 attempts) and NL-2026-002 deleted. Run 1 thread counters rolled back.
