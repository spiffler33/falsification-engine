# V9 Phase 3.7: Compiler Repairs Results

*Date: 2026-04-07*
*Status: COMPLETE*

---

## 1. What Was Built

A generic post-compilation repair pass that runs automatically between Haiku compilation and validation.

### Files Created

| File | Purpose |
|------|---------|
| `backend/engine/v9/compiler_repairs.py` | Two generic structural repairs for compound rules |
| `docs/V9_PHASE3_7_COMPILER_REPAIRS_RESULTS.md` | This document |

### Files Modified

| File | Change |
|------|--------|
| `scripts/v9_compile_theories.py` | Integrated repair pass: parse -> compile -> **repair** -> validate -> save |

---

## 2. Repair Pass Design

### Pipeline (updated)

```
Parse ACTIVATION.md -> Call Haiku -> Repair pass -> Validate -> Write artifact
```

### Repair 1: Prune UNRESOLVED compound clauses

For any compound rule, checks each sub-rule's field references recursively. If a sub-rule references a field starting with `UNRESOLVED:` or not present in the field registry, that sub-rule is removed. Single-clause compounds are unwrapped to their inner rule.

### Repair 2: Remove illegal field_comparison clauses

Runs the same semantic type comparison check the validator uses (`are_comparable`) on FieldOperand-vs-FieldOperand comparisons within field_comparison rules. Also checks for unregistered derived functions. Removes clauses that would fail validation.

### Matching validator behavior

The repair checks match the validator exactly:
- Semantic type checks only apply to FieldOperand vs FieldOperand (not DerivedOperand)
- Unregistered derived functions are caught and removed
- Field existence checks use the same FieldRegistry

### What repairs do NOT fix

- **Field misresolution** (category 3): Haiku resolving a field name to the wrong registry entry (e.g., "top 10% wealth share" -> `top_10_sp500_weight` instead of `top10_wealth_share`). This remains a human review item.

---

## 3. Indicators Repaired During Full Recompilation

| Theory | Indicator | Repair | Pruned Clause | Reason |
|--------|-----------|--------|---------------|--------|
| debt_cycle_long | fiscal_deficit_primary_growth | prune_unresolved | scalar_comparison | unresolved:UNRESOLVED:private_sector_credit_growth |
| debt_cycle_long | wealth_inequality_extremes | prune_unresolved | scalar_comparison | unresolved:UNRESOLVED:top_1_income_share |
| monetary_architecture | ccbs_stress_episodic | prune_unresolved | 4 clauses | UNRESOLVED CCBS fields (eur_usd_3m, jpy_usd_3m) |
| monetary_architecture | non_dollar_settlement_growing | prune_unresolved | scalar_comparison | UNRESOLVED:non_dollar_energy_settlement_volume |

Total: 7 clauses pruned across 4 indicators in 2 theories.

**valuation_mean_reversion note:** The qqq_iwm_ratio market_breadth indicator did NOT require repair in this compilation. Haiku produced a clean compilation without the illegal field_comparison clause that appeared in Phase 3.5. (Haiku output can vary slightly across API calls even at temperature=0, likely due to model version updates.)

---

## 4. Recompilation Results

| Theory | Status | Clean | Warn | Blocked | Phase 3.5 Status | Change |
|--------|--------|-------|------|---------|------------------|--------|
| valuation_mean_reversion | WARN | 5 | 2 | 0 | BLOCKED | **Fixed** |
| debt_cycle_short | WARN | 7 | 7 | 1 | WARN | same |
| debt_cycle_long | WARN | 2 | 4 | 0 | BLOCKED | **Fixed** |
| structural_fragility | BLOCKED | 10 | 0 | 1 | BLOCKED | same (capex qualitative) |
| fiscal_dominance_arithmetic | WARN | 4 | 2 | 0 | WARN | same |
| fiscal_dominance_liquidity | WARN | 3 | 4 | 0 | WARN | same |
| capital_flows | WARN | 5 | 5 | 0 | WARN | same |
| monetary_architecture | BLOCKED | 3 | 1 | 1 | BLOCKED | improved (repairs reduced errors) |

Key improvements:
- **valuation_mean_reversion**: BLOCKED -> WARN (no repair needed this time; Haiku compiled cleanly)
- **debt_cycle_long**: BLOCKED -> WARN (2 UNRESOLVED clauses pruned)
- **monetary_architecture**: still BLOCKED (1 indicator fully UNRESOLVED after pruning all clauses), but 5 dead clauses removed

---

## 5. Score Parity for 3 APPROVED Theories

APPROVED artifacts were restored from backup (Phase 3.6 versions with corrected weights). Scores verified:

| Theory | Score | Tier | Matches Phase 3.6? |
|--------|-------|------|---------------------|
| valuation_mean_reversion | 0.785714 | Active | YES |
| debt_cycle_long | 0.764706 | Active | YES |
| fiscal_dominance_arithmetic | 1.000000 | Active | YES |

---

## 6. Regression Gate

```
Stage 1: Correctness harness ... PASS
Stage 2: Broader backend suite ... PASS
REGRESSION CHECK PASSED
```

1203 passed, 2 skipped.

Compiler correctness harness: 19/19 passed.

---

## 7. Known Limitation: Field Misresolution

debt_cycle_long's wealth_inequality indicator: Haiku consistently resolves "Top 10% wealth share" to `top_10_sp500_weight` (S&P 500 index concentration) instead of `top10_wealth_share` (household wealth inequality). This is a Haiku field resolution error (category 3) that the generic repair pass does not fix.

The current APPROVED debt_cycle_long artifact has this field manually corrected (Phase 3.6). Future recompilations will need this manual correction until either:
- The prompt is improved to disambiguate similarly-named fields
- A field-verification post-step is added (checking source text keywords against resolved field descriptions)
