# V9 Phase 4: Theory Approval Results

**Date:** 2026-04-07
**Scope:** Approve remaining DRAFT theories, update correctness harness, document legacy path disposition

---

## 1. Approval Decisions

### APPROVED (3 theories, 6 total now on compiled path)

| Theory | Prior Status | New Status | Tier Change | Justification |
|--------|-------------|-----------|-------------|---------------|
| fiscal_dominance_liquidity | DRAFT/legacy | APPROVED/compiled | Active -> Active (no change) | All 5 diffs are temporal exclusion. 2 evaluable indicators match legacy exactly. |
| debt_cycle_short | DRAFT/legacy | APPROVED/compiled | Adjacent(Contraction) -> Active(Expansion) | Contraction 0.300->0.000: Sahm BUG-03 + Fed funds wiring bug fixed. Expansion 1.000->0.833: 3 temporal excluded, Fed funds field_comparison now evaluable. |
| monetary_architecture | DRAFT/legacy | APPROVED/compiled | Active -> Inactive | All 3 shared indicators temporal. Compiled adds 2 new indicators (1 BLOCKED/excluded, 1 evaluable scalar). |

### NOT APPROVED (2 theories, remain on legacy path)

| Theory | Issue | What Blocks Approval |
|--------|-------|---------------------|
| structural_fragility | Missing indicator + UNRESOLVED | Compiled artifact has `capex_revenue_mismatch` (UNRESOLVED) but is missing `implied-realized vol gap` that legacy parses. This is a compiler issue -- the indicator set doesn't match. |
| capital_flows | Weight discrepancies | Accumulation phase has all 4 weights at 0.10 in compiled vs 0.33/0.27/0.20/0.20 in legacy. Total Accumulation weight = 0.40 (should sum to ~1.00). Compiler appears to have defaulted to equal weights. |

---

## 2. Routing Table (Final State)

| # | Theory | Path | Artifact Status | Compiled Score | Compiled Tier |
|---|--------|------|-----------------|---------------|---------------|
| 1 | valuation_mean_reversion | **compiled** | APPROVED (Phase 3) | 0.7857 | Active |
| 2 | debt_cycle_short | **compiled** | APPROVED (Phase 4) | Exp 0.833 / Con 0.000 | Active (Expansion) |
| 3 | debt_cycle_long | **compiled** | APPROVED (Phase 3) | 0.7647 | Active |
| 4 | structural_fragility | legacy | DRAFT | -- | Adjacent (Building) |
| 5 | fiscal_dominance_liquidity | **compiled** | APPROVED (Phase 4) | 1.0000 | Active |
| 6 | fiscal_dominance_arithmetic | **compiled** | APPROVED (Phase 3) | 1.0000 | Active |
| 7 | capital_flows | legacy | DRAFT | -- | Adjacent (Rotation) |
| 8 | monetary_architecture | **compiled** | APPROVED (Phase 4) | 0.0000 | Inactive |

**Compiled: 6/8 theories. Legacy: 2/8 theories.**

---

## 3. Correctness Harness Changes

### fiscal_dominance_liquidity

| Indicator | Change | Category |
|-----------|--------|----------|
| Net liquidity expanding | True -> excluded (data_unavailable) | temporal_exclusion (persistence) |
| Rate hikes not producing recession | True -> excluded (data_unavailable) | temporal_exclusion (compound ALL + persistence) |
| RRP draining toward zero | evaluated(False) -> excluded (data_unavailable) | temporal_exclusion (compound ALL + trend_state) |
| Fed balance sheet inconsistent | threshold_not_evaluable -> data_unavailable | temporal_exclusion (compound ANY, all temporal) |
| TGA behavior | evaluated(False) -> excluded (data_unavailable) | temporal_exclusion (compound ANY + delta_change) |
| Deficit pace | No change | -- |
| Hard assets outperforming | No change | -- |

**Score:** 0.7778 -> 1.0000 (Active in both). Coverage: 6 eval / 1 excl -> 2 eval / 5 excl.

### debt_cycle_short

| Indicator | Change | Category |
|-----------|--------|----------|
| ISM below contraction | evaluated(False) -> excluded | temporal_exclusion |
| Sahm Rule | True(BUG-03) -> excluded | temporal_exclusion + BUG-03 fixed |
| Credit spreads widening | evaluated(False) -> excluded | temporal_exclusion |
| Yield curve resteepened | evaluated(False) -> excluded | temporal_exclusion |
| Initial claims rising | evaluated(False) -> excluded | temporal_exclusion |
| Fed funds above GDP | True(wiring bug) -> excluded | temporal_exclusion + wiring bug fixed |
| Fed funds below GDP | threshold_not_evaluable -> evaluable(False, 3.64) | justified_improvement (field_comparison) |
| Unemployment low/falling | value 4.3 -> None (compound OR, trigger unchanged) | justified_improvement (compound value not propagated) |
| Credit spreads tight | True -> excluded | temporal_exclusion |
| Consumer confidence | True -> excluded | temporal_exclusion |
| Net credit growth | threshold_not_evaluable -> data_unavailable | temporal_exclusion |
| SLOOS broad tightening | No change | -- |
| ISM above contraction | No change | -- |
| Yield curve not inverted | No change | -- |
| Initial claims low | No change | -- |

**Scores:** Contraction 0.300(Adjacent) -> 0.000(Inactive). Expansion 1.000(Active) -> 0.833(Active).
**Effective:** Adjacent(Contraction) -> Active(Expansion).

### monetary_architecture

| Indicator | Change | Category |
|-----------|--------|----------|
| Central bank gold purchases | True -> excluded (data_unavailable) | temporal_exclusion (persistence) |
| Foreign treasury holdings | evaluated(False) -> excluded (data_unavailable) | temporal_exclusion (trend_state) |
| Gold/oil ratio | True -> excluded (data_unavailable) | temporal_exclusion (compound ALL + trend_state) |
| CCBS stress episodic | NEW: excluded (BLOCKED, empty compound) | new_indicator |
| Non-dollar trade settlement | NEW: evaluable(False, 3.89) | new_indicator (scalar) |

**Score:** 0.662(Active) -> 0.000(Inactive). Indicators: 3 -> 5. Coverage: 3 eval / 0 excl -> 1 eval / 4 excl.

---

## 4. Theories That Could NOT Be Approved

### structural_fragility

**Blockers:**
1. **Missing indicator:** The compiled artifact does not contain `Implied-realized vol gap` (field: `vix_vs_realized`), which the legacy parser finds. Instead, the compiled artifact has `Capex/revenue mismatch` with an UNRESOLVED field (`UNRESOLVED:dominant_theme_capex_to_revenue_ratio`).
2. **Blocked indicator:** `capex_revenue_mismatch` has `compilation_status: blocked` with an unresolvable field.
3. **Consequence:** Building phase loses an evaluable indicator (vol gap, which the legacy evaluates) and gains an unusable one. This is a compiler mapping issue, not a data limitation.

**Path to approval:** Recompile with the corrected ACTIVATION.md mapping. Ensure the implied-realized vol gap indicator appears in the compiled artifact with field `vix_vs_realized`. The capex_revenue_mismatch indicator should also be present (it's in the ACTIVATION.md) but needs a resolvable field or explicit context_flag exclusion.

### capital_flows

**Blockers:**
1. **Weight discrepancies in Accumulation phase:** All 4 Accumulation indicators have weight 0.10 in the compiled artifact, but ACTIVATION.md assigns them differentiated weights. The legacy parser extracted weights correctly (0.33, 0.27, 0.20, 0.20). The compiler appears to have defaulted to equal weights.
2. **Total Accumulation weight = 0.40** (should be ~1.00 as phase weights sum to 1.0).
3. **EM underperformance sign fix is correct** in compiled (lt -30 instead of legacy's unsigned comparison), but can't be approved with wrong weights.

**Path to approval:** Recompile with correct weight extraction from ACTIVATION.md. The Rotation phase weights (0.25, 0.20, 0.20, 0.15, 0.10, 0.10 = 1.00) are correct -- only Accumulation needs fixing.

---

## 5. Regression Gate

```
backend/tests/ -- 1204 passed, 2 skipped, 0 failed
```

- test_activation_correctness.py: 72 passed (all 8 theories, all indicators, all coverage)
- No regressions in broader backend suite

---

## 6. Test Count

| Suite | Passed | Skipped | Failed |
|-------|--------|---------|--------|
| Full backend | 1204 | 2 | 0 |
| Correctness harness | 72 | 0 | 0 |

---

## 7. Summary

- **6/8 theories** now on compiled path (3 from Phase 3, 3 from Phase 4)
- **2/8 theories** remain on legacy path (structural_fragility, capital_flows)
- Both remaining theories have specific, documented compiler issues (not temporal limitations)
- Path to full compiled-only mode requires:
  1. Fix structural_fragility compilation (missing indicator + UNRESOLVED field)
  2. Fix capital_flows Accumulation weight extraction
  3. Recompile and re-run Phase 4 approval for those 2 theories
- No code changes needed in dual_path.py, activation.py, or compiled_evaluator.py -- the routing logic works correctly based on artifact_status
