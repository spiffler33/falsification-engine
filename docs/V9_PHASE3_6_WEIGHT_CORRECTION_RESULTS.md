# V9 Phase 3.6: Weight Correction + Artifact Re-Approval Results

*Date: 2026-04-07*
*Status: COMPLETE*

---

## 1. qqq_iwm_ratio Investigation

### Finding

The qqq_iwm_ratio validation error is a **genuine illegal comparison**, not a type system bug.

**Root cause:** Haiku generated a `field_comparison` rule where:
- Left operand: `qqq_iwm_ratio` (semantic_type=ratio, ComparisonClass=ratio_like)
- Right operand: `rsp_spy_12m_relative` (semantic_type=relative_performance, ComparisonClass=relative)

These are different economic quantities:
- A price ratio (QQQ price / IWM price = 3.5x) is a level relationship
- A return differential (RSP 12m return - SPY 12m return = -5%) is a return relationship

The validator correctly flags this as an illegal comparison across ComparisonClasses.

**Structural cause:** The ACTIVATION.md threshold says:
> "QQQ/IWM ratio above 2-year high AND RSP underperforming SPY by 5%+ over 12 months"

These are two **independent conditions** joined by AND. Haiku incorrectly merged them into a single `field_comparison` instead of keeping them as separate compound clauses. The RSP/SPY field doesn't exist in the registry anyway.

### Fix

Post-compilation fixup: extract the evaluable `historical_extreme(qqq_iwm_ratio, high, 2 years)` clause and discard the unevaluable `field_comparison` clause. The RSP/SPY field has no data source, so this simplification has no scoring impact.

**ComparisonClass definitions:** No changes needed. The type system is correct.

---

## 2. New Scores for 3 APPROVED Theories

### valuation_mean_reversion

| Metric | Old (Phase 3) | New (Phase 3.6) | Change |
|--------|--------------|-----------------|--------|
| Score | 0.833333 | **0.785714** | -0.0476 |
| Tier | Active | Active | unchanged |

| Indicator | Old Weight | New Weight | Source |
|-----------|-----------|-----------|--------|
| Equity risk premium | 0.20 | **0.25** | ACTIVATION.md |
| Shiller CAPE | 0.20 | 0.20 | same |
| Buffett Indicator | 0.15 | 0.15 | same |
| Cash yield exceeds equity | 0.10 | **0.15** | ACTIVATION.md |
| Profit margins | 0.10 | 0.10 | same |
| Market breadth | 0.10 | 0.10 | same |
| Insider selling | 0.15 | **0.05** | ACTIVATION.md |

Score decreased because the cash yield indicator (not triggered, weight 0.10 -> 0.15) gained weight in the denominator without contributing to the numerator.

### debt_cycle_long

| Metric | Old (Phase 3) | New (Phase 3.6) | Change |
|--------|--------------|-----------------|--------|
| Score | 0.647059 | **0.764706** | +0.1176 |
| Tier | Active | Active | unchanged |

| Indicator | Old Weight | New Weight | Source |
|-----------|-----------|-----------|--------|
| Total debt/GDP | 0.20 | **0.25** | ACTIVATION.md |
| Fed BS/GDP | 0.15 | **0.25** | ACTIVATION.md |
| Rates near ELB | 0.15 | 0.15 | same |
| Fiscal deficit | 0.20 | **0.15** | ACTIVATION.md |
| Wealth inequality | 0.15 | **0.10** | ACTIVATION.md |
| Negative real rates | 0.15 | **0.10** | ACTIVATION.md |

Score increased because the two triggered indicators (total_debt, fed_bs) gained more weight in both numerator and denominator, while the two non-triggered indicators (wealth_inequality, real_rates) lost weight.

Additional fixes:
- Fiscal deficit compound rule: removed UNRESOLVED `private_sector_credit_growth` clause
- Wealth inequality compound rule: removed UNRESOLVED `top_1_income_share` clause
- Wealth inequality field: corrected from `top_10_sp500_weight` (S&P 500 index concentration) to `top10_wealth_share` (household wealth inequality)

### fiscal_dominance_arithmetic

| Metric | Old (Phase 3) | New (Phase 3.6) | Change |
|--------|--------------|-----------------|--------|
| Score | 1.000000 | **1.000000** | 0.0000 |
| Tier | Active | Active | unchanged |

| Indicator | Old Weight | New Weight | Source |
|-----------|-----------|-----------|--------|
| Interest/receipts | 0.20 | **0.25** | ACTIVATION.md |
| Interest > defense | 0.15 | 0.15 | same |
| Deficit pace | 0.20 | 0.20 | same |
| Debt rollover | 0.15 | 0.15 | same |
| Gold/oil ratio | 0.15 | **0.10** | ACTIVATION.md |
| CB gold purchases | 0.15 | **0.05** | ACTIVATION.md |

Score unchanged at 1.000 because all evaluable indicators remain triggered regardless of weight distribution.

---

## 3. Correctness Harness Changes

### valuation_mean_reversion

| Field | Old | New | Reason |
|-------|-----|-----|--------|
| Score | 0.833333 | 0.785714 | weight_correction |
| "Equity risk premium" weight | 0.20 | 0.25 | weight_correction |
| "Cash yield exceeds equity yield" name | "Cash yield exceeds equity yield" | "Short-term cash yield exceeds equity earnings yield" | Haiku uses ACTIVATION.md name |
| "Cash yield" weight | 0.10 | 0.15 | weight_correction |
| "Corporate profit margins" name | "Corporate profit margins elevated" | "Corporate profit margins at cycle highs" | Haiku uses ACTIVATION.md name |
| "Insider selling" weight | 0.15 | 0.05 | weight_correction |
| Coverage evaluated_weight | 0.6000 | 0.7000 | weight_correction |
| Coverage triggered_weight | 0.5000 | 0.5500 | weight_correction |
| Coverage excluded_weight | 0.4000 | 0.3000 | weight_correction |

### debt_cycle_long

| Field | Old | New | Reason |
|-------|-----|-----|--------|
| Score | 0.647059 | 0.764706 | weight_correction |
| "Total debt/GDP" name | "Total debt/GDP above warning level" | "Total debt / GDP above historical warning level" | Haiku uses ACTIVATION.md name |
| "Total debt/GDP" weight | 0.20 | 0.25 | weight_correction |
| "Fed BS/GDP" name | "Fed balance sheet/GDP elevated" | "Fed balance sheet / GDP elevated" | Haiku uses ACTIVATION.md name |
| "Fed BS/GDP" weight | 0.15 | 0.25 | weight_correction |
| "Rates near ELB" name | "Rates at/near effective lower bound in recent memory" | "Rates at or near effective lower bound within recent memory" | Haiku uses ACTIVATION.md name |
| "Fiscal deficit" weight | 0.20 | 0.15 | weight_correction |
| "Fiscal deficit" value | None | 11.7358 | Haiku simplified compound to scalar |
| "Wealth inequality" name | "Wealth inequality at extremes" | "Wealth inequality at cycle-characteristic extremes" | Haiku uses ACTIVATION.md name |
| "Wealth inequality" weight | 0.15 | 0.10 | weight_correction |
| "Negative real rates" weight | 0.15 | 0.10 | weight_correction |
| Coverage triggered_weight | 0.5500 | 0.6500 | weight_correction |

### fiscal_dominance_arithmetic

| Field | Old | New | Reason |
|-------|-----|-----|--------|
| "Interest/receipts" name | "Interest/receipts ratio elevated" | "Interest expense / tax receipts ratio" | Haiku uses ACTIVATION.md name |
| "Interest/receipts" weight | 0.20 | 0.25 | weight_correction |
| "Interest > defense" name | "Interest exceeds defense spending" | "Interest expense exceeds major discretionary category" | Haiku uses ACTIVATION.md name |
| "Deficit pace" name | "Deficit pace elevated outside recession" | "Deficit pace outside recession" | Haiku uses ACTIVATION.md name |
| "Gold/oil" weight | 0.15 | 0.10 | weight_correction |
| "CB gold" weight | 0.15 | 0.05 | weight_correction |
| Coverage excluded_weight | 0.3000 | 0.2000 | weight_correction |

---

## 4. Regression Gate

```
Stage 1: Correctness harness ... PASS
Stage 2: Broader backend suite ... PASS
REGRESSION CHECK PASSED
```

Total: 1203 passed, 2 skipped.

---

## 5. Summary

All 3 APPROVED theories now use Haiku-compiled artifacts with correct ACTIVATION.md weights. The weight transcription errors in compile_all.py have been corrected. All tier classifications are preserved (Active for all 3).

| Theory | Old Score | New Score | Tier |
|--------|-----------|-----------|------|
| valuation_mean_reversion | 0.8333 | 0.7857 | Active |
| debt_cycle_long | 0.6471 | 0.7647 | Active |
| fiscal_dominance_arithmetic | 1.0000 | 1.0000 | Active |
