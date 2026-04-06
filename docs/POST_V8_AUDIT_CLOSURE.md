# Post-v8 Audit Closure

**Date:** 2026-04-06
**Scope:** Semantic remediation of field wiring, unit alignment, data-gap scoring policy, threshold extraction, correctness harness, and regression command -- following the v8 parser remediation.
**Plan:** `post_v8_audit_implementation_plan_v2.md` (Tasks 0-6)
**Baseline:** `docs/POST_V8_SEMANTIC_BASELINE.md` (frozen 2026-04-06, commit 86a45f5)
**Predecessor:** `docs/V8_REMEDIATION_CLOSURE.md` (v8 parser/syntax remediation, 9 tasks)

---

## 1. Context

v8 repaired the **syntax contract**: the parser reads what theory packages declare and refuses to guess. The post-v8 audit found that the **semantic contract** was still broken: some declared fields were wrong proxies, wrong units, wrong wiring, or scored unfairly when data was structurally absent.

This phase fixed the concrete semantic bugs without redesigning the parser architecture.

---

## 2. What was resolved (Tasks 0-5)

### Task 0 -- Frozen semantic baseline (commit 86a45f5)
Regenerated briefing packet with live data agent. Created frozen baseline capturing all 8 theory scores, per-indicator state, and audited field values. All later tasks diff against this artifact.

### Task 1 -- Field wiring and unit alignment (commit 9c96399)
8 fixes across 5 ACTIVATION.md files and data_agent.py:

| Fix | Audit | What changed |
|-----|-------|-------------|
| gold_oil_ratio | A-01 | GLD/USO ETF proxy replaced with GC=F/CL=F commodity futures |
| DXY resolution | A-07 | Added `dxy_index` computed field; capital_flows indicators now resolve |
| fed_bs_gdp_ratio | C-01 | debt_cycle_long wired to pre-computed ratio instead of raw millions |
| deficit_pace | B-01 | Threshold text aligned to native $B units (both fiscal_dominance theories) |
| monetary_architecture backticks | D-03 | `gold_oil_ratio` and `foreign_treasury_holdings_pct` backtick refs added |

**Tier changes:** monetary_architecture Adjacent->Active, capital_flows/Accumulation Inactive->Adjacent.

### Task 2 -- Data-gap scoring policy (commit fa8bef8)
5 indicators across 4 theories excluded from the scoring denominator:
- 1 with no data source (`top_10_sp500_weight`)
- 4 with pure-prose thresholds that `_extract_number()` cannot parse

**No tier changes.** All score increases within same tier.

### Task 3 -- K-suffix scaling in `_extract_number()` (commit f032702)
Rewrote `_extract_number()` from destructive global `.replace()` to targeted regex. Added K suffix scaling (x1000). Fixed 2 `initial_claims` indicators in `debt_cycle_short` that compared raw counts (202000) against unscaled "250K" (was parsed as 250).

**No tier changes.** Both score deltas causally traceable to initial_claims K-suffix fix.

### Task 4 -- Frozen correctness harness
70 tests in `backend/tests/test_activation_correctness.py`. Freezes per-theory scores, per-indicator trigger states, field resolution, threshold parsing, coverage metrics, and ceiling-hit visibility. All 8 theories covered.

### Task 5 -- Canonical regression command
`python -m scripts.regression_check` -- two-stage offline deterministic gate:
- Stage 1: Correctness harness (semantic gate)
- Stage 2: Full backend suite

---

## 3. What is frozen as current intended behavior

These are known imperfections that are explicitly frozen in the correctness harness. They produce correct results today under current market conditions but would fail under different conditions. The harness will catch if their behavior changes unexpectedly; v9 is the resolution boundary.

| # | Issue | Theory | What happens | Why frozen |
|---|-------|--------|-------------|-----------|
| 1 | BUG-03: Temporal phrase extraction | ~6 indicators | "3+ months" extracts 3, "2-year high" extracts 2 | Needs time-series model (v9) |
| 2 | TGA $M/$B latent mismatch | fiscal_dom_liq | Field 847718 ($M) vs threshold 500 ($B). Same result by coincidence. | Context-free T/B/M scaling would break other aligned thresholds (v9) |
| 3 | Rates at ELB trivially true | debt_cycle_long | Any positive rate > 0 triggers C-02 | Historical lookback needs temporal data (v9) |
| 4 | Wealth inequality threshold | debt_cycle_long | Extracts "10" from "top 10% wealth share above 70%" | Prose threshold parsing (v9) |
| 5 | Fed funds vs GDP level comparison | debt_cycle_short | GDP level in $B vs rate threshold | Compound rate comparison (v9) |
| 6 | ERP fallback to 4.5% constant | valuation_mr | WILL5000INDFC unavailable from FRED | External data dependency |
| 7 | eem_spy_3y_relative uses 12-month proxy | capital_flows | 12-month return as 3-year proxy | Data infrastructure (v9) |
| 8 | fiscal_dom_arith at 1.000 ceiling | fiscal_dom_arith | 16.7% of weight excluded from denominator | Visible in harness; monitor |
| 9 | debt_cycle_short/Expansion at 1.000 | debt_cycle_short | 25% of weight excluded from denominator | Visible in harness; monitor |
| 10 | top_10_sp500_weight has no data source | structural_fragility | Excluded from denominator | Needs index provider data (v9) |

---

## 4. What is deferred to v9

### Architecture changes

| # | What | Why v9 |
|---|------|--------|
| 1 | Structured threshold objects | Replace prose-as-contract with machine-native threshold definitions (type, value, unit, comparator) |
| 2 | T/B/M suffix scaling | Requires structured thresholds with explicit unit declarations; context-free scaling breaks aligned thresholds |
| 3 | Time-series / rolling-window model | RISING/FALLING, "3+ months", Sahm Rule MA all need temporal data |
| 4 | Compound threshold parsing | "Above 500bp AND widening for 2+ months" needs AND/OR schema |
| 5 | top_10_sp500_weight data source | Needs index provider constituent weights |
| 6 | Native RISING/FALLING direction handling | Currently proxied via BUG-03 temporal number extraction |

### Semantic architecture boundary

v9 is where **semantic parsing moves away from regex-over-prose**. The current architecture extracts meaning from markdown prose using regex patterns (`_extract_number()`, `_extract_metric_field()`, direction inference). This works for simple "Above X" thresholds but fails structurally for:
- compound conditions (A AND B)
- temporal trends (rising for N months)
- unit-aware comparisons ($M vs $B)
- relative comparisons (rate A < rate B)

**Likely v9 direction:** A compiler layer that transforms prose theory modules into structured semantic schema. This could be:
- A local SLM (small language model) that reads prose and outputs structured JSON threshold objects
- A cheap schema-compilation API call (e.g., Haiku-class model) run once per theory edit, not per scoring run
- The compiled schema becomes the machine contract; the prose remains the human-readable source

**What v9 replaces:**
- `_extract_number()` regex parsing of prose thresholds
- `_extract_metric_field()` backtick-hunting in prose
- Direction inference from prose strings
- The implicit assumption that prose and machine meaning are the same string

**What v9 preserves:**
- The five-pass architecture (activation, generation, elimination, conviction, human)
- Mechanical activation scoring (no LLM in Pass 1)
- The theory module registry pattern (N modules, not hardcoded 8)
- The correctness harness pattern (frozen expected outputs)
- The regression command pattern (one command, offline, deterministic)

This is a handoff note. No v9 implementation work was done in Task 6.

---

## 5. Migration-era artifact disposition

| Artifact | Disposition | Status |
|----------|------------|--------|
| `scripts/v8_equivalence_check.py` | Deprecated (header added) | Migration-era tool; not in regression surface. Superseded by correctness harness. |
| `theories/old_format/` (9 files) | Historical artifact (README updated) | v1 theory files for archaeological reference. Not read at runtime. |
| `v8_fix.md` | Historical artifact | v8 parser remediation plan. Complete. |
| `plan_v8.md` | Historical artifact | v8 migration design record. |
| `post_v8_audit_implementation_plan_v2.md` | Historical artifact | This plan. Complete. |
| `docs/V8_DIVERGENCE_DOCKET.md` | Historical artifact | Migration forensics. |
| `docs/V8_IMPLICIT_CONTRACT_AUDIT.md` | Historical artifact | Pre-remediation audit. |
| `docs/V8_PREREMEDIATION_BASELINE.md` | Historical artifact | v8 fix baseline. |
| `docs/V8_REMEDIATION_CLOSURE.md` | Historical artifact | v8 parser remediation closure. |
| `docs/POST_V8_AUDIT.md` | Historical artifact | Audit that spawned this plan. |
| `docs/POST_V8_SEMANTIC_BASELINE.md` | Historical artifact | Task 0 frozen baseline. Referenced by correctness harness. |
| `docs/POST_V8_TASK[1-5]_RESULTS.md` | Historical artifact | Per-task result records. |
| `backend/tests/test_prompt_builder_v8.py` | Active code | Tests current prompt builder. The "v8" is the version, not migration debt. |

---

## 6. Canonical operator entrypoints

**Regression gate:**
```
python -m scripts.regression_check
```

**Data refresh:**
```
python -m scripts.run_data --fresh
```

**Full pipeline:** See `CLAUDE.md` execution model.

---

## 7. Final score state (post-remediation)

| # | Theory | Baseline (Task 0) | Final (Task 3) | Net delta | Tier change |
|---|--------|-------------------|----------------|-----------|-------------|
| 1 | valuation_mean_reversion | 0.706 | 0.706 | 0.000 | -- |
| 2 | debt_cycle_short (Contraction) | 0.400 | 0.300 | -0.100 | -- |
| 2 | debt_cycle_short (Expansion) | 0.650 | 1.000 | +0.350 | -- |
| 3 | debt_cycle_long | 0.900 | 0.900 | 0.000 | -- |
| 4 | structural_fragility (Resolving) | 0.000 | 0.000 | 0.000 | -- |
| 4 | structural_fragility (Building) | 0.353 | 0.462 | +0.109 | -- |
| 5 | fiscal_dominance_liquidity | 0.700 | 0.778 | +0.078 | -- |
| 6 | fiscal_dominance_arithmetic | 0.722 | 1.000 | +0.278 | -- |
| 7 | capital_flows (Rotation) | 0.450 | 0.450 | 0.000 | -- |
| 7 | capital_flows (Accumulation) | 0.270 | 0.470 | +0.200 | Inactive -> Adjacent |
| 8 | monetary_architecture | 0.408 | 0.662 | +0.254 | Adjacent -> Active |

**2 tier changes**, both caused by field wiring fixes (Task 1):
- monetary_architecture: Adjacent -> Active (gold_oil_ratio commodity fix + backtick wiring)
- capital_flows/Accumulation: Inactive -> Adjacent (DXY resolution fix)

All score deltas are causally traceable to specific semantic corrections. No unexplained movement.

---

## 8. Test suite

937 tests passing via `python -m scripts.regression_check`.

| Suite | Tests | What it covers |
|-------|-------|---------------|
| Correctness harness | 70 | Frozen expected outputs for all 8 theories |
| Data-gap policy | 7 | Denominator exclusion paths |
| Unit-suffix scaling | 17 | K scaling, bp/% stripping, word preservation |
| Parser / lifecycle / prompt | ~843 | Full backend regression surface |

---

*This phase is complete. The post-v8 audit is closed. v9 begins from this boundary.*
