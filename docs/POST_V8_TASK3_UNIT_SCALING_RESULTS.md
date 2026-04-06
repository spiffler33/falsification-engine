# Post-v8 Task 3: Unit-Suffix Scaling Results

**Date:** 2026-04-06
**Baseline:** `docs/POST_V8_TASK2_DATA_GAP_POLICY_RESULTS.md` (frozen after Task 2)
**Test suite:** 867 tests passing (850 + 17 new unit-suffix scaling tests)

---

## 1. What changed

**Problem:** `_extract_number()` stripped unit-suffix characters (T, B, M, bp, %, $, x) globally from the entire string without applying scale factors. "250K" parsed to 250 instead of 250000, producing wrong comparisons against raw-count fields like `growth.initial_claims` (202000).

**Fix:** Rewrote `_extract_number()` to use targeted regex patterns instead of destructive global `.replace()`. Added K suffix scaling (x1000). Preserved existing behavior for bp, %, $, T, B, M, x (strip only, no scaling).

**Why only K scales:**

| Suffix | Scaling | Why |
|--------|---------|-----|
| K/k | x1000 | Only field using K thresholds (`initial_claims`) stores raw counts |
| bp | none | `credit.hy_spread` already stores basis points |
| % | none | Percentage fields already store percentages |
| T, B, M | none | Monetary field units are inconsistent ($M vs $B); context-free scaling would break Task 1's aligned thresholds |
| x | none | Ratio marker only |

---

## 2. Affected indicator inventory

### A. Indicators whose parsed threshold CHANGED (K suffix fix)

| # | Theory | Phase | Indicator | Threshold text | Old parsed | New parsed | Field | Field value | Old triggered | New triggered |
|---|--------|-------|-----------|---------------|-----------|-----------|-------|-------------|---------------|---------------|
| 1 | debt_cycle_short | Expansion | Initial claims low | "Below 250K (4-week average)" | 250 | **250000** | initial_claims | 202000 | FALSE (202000 > 250) | **TRUE** (202000 < 250000) |
| 2 | debt_cycle_short | Contraction | Initial claims rising | "above 280K AND rising for 8+ weeks" | 280 | **280000** | initial_claims | 202000 | TRUE (202000 > 280) | **FALSE** (202000 < 280000) |

Both were previously **correct by coincidence** in opposite ways:
- Expansion: claims of 202K ARE below 250K, but the indicator was NOT triggering (comparing raw count 202000 against unscaled 250)
- Contraction: claims of 202K are NOT above 280K, but the indicator WAS triggering (comparing 202000 against unscaled 280)

### B. Indicators with unit suffixes that are CORRECTLY unchanged

| # | Theory | Indicator | Threshold | Parsed | Field unit | Why correct |
|---|--------|-----------|-----------|--------|------------|-------------|
| 3 | debt_cycle_short/Expansion | Credit spreads tight | "Below 450bp" | 450 | bp | Field hy_spread=317 in bp; 317<450 correct |
| 4 | debt_cycle_short/Contraction | Credit spreads widening | "Above 500bp" | 500 | bp | 317>500 correct |
| 5 | structural_fragility/Building | HY spread tight | "Below 300bp" | 300 | bp | 317<300 correct |
| 6 | structural_fragility/Resolving | HY spread wide | "Above 600bp" | 600 | bp | 317>600 correct |
| 7 | structural_fragility/Resolving | Drawdown depth | "Below -20%" | -20 | % | -5.7<-20 correct |
| 8 | fiscal_dom_liq | Deficit pace | "Above 1500 (in $B)" | 1500 | $B | 3690>1500 correct (Task 1 aligned) |
| 9 | fiscal_dom_liq | Hard assets | "Above +10%" | 10 | % | 73.09>10 correct |
| 10 | fiscal_dom_liq | RRP draining | "Below $250B" | 250 | $B | 327<250 correct |
| 11 | fiscal_dom_arith | Interest/receipts | "Above 20%" | 20 | % | 34>20 correct |
| 12 | fiscal_dom_arith | Deficit pace | "Above 1500 (in $B)" | 1500 | $B | 3690>1500 correct |
| 13 | valuation_mr | ERP | "Below 1.0%" | 1.0 | % | 0.19<1.0 correct |

### C. Latent field-unit mismatch (not affecting current scores)

| # | Theory | Indicator | Threshold | Parsed | Field unit | Issue |
|---|--------|-----------|-----------|--------|------------|-------|
| 14 | fiscal_dom_liq | TGA spending | "TGA below $500B" | 500 | $M (847718) | Threshold says $B, field stores $M. Comparison 847718<500 is FALSE; correct answer ($847.7B > $500B) is also FALSE. Same result by coincidence. Would fail if TGA drops below $500B (engine would not detect until TGA drops below $0.5M). |

**Disposition:** Not fixed in Task 3 because context-free T/B/M scaling would break other aligned thresholds. Documented for v9 structured threshold schema.

### D. BUG-03 temporal phrases (NOT fixed, NOT claimed as fixed)

| # | Theory | Indicator | Threshold | Extracts | Status |
|---|--------|-----------|-----------|----------|--------|
| T1 | debt_cycle_short/Contraction | Sahm Rule | "3-month MA rising 0.50%+" | 3 | Temporal; deferred to v9 |
| T2 | capital_flows/Rotation | Dollar weakening | "DXY declining for 3+ months" | 3 | Temporal; deferred to v9 |
| T3 | capital_flows/Rotation | RMB strengthening | "USD/CNY declining for 3+ months" | 3 | Temporal; deferred to v9 |
| T4 | monetary_architecture | Foreign Treasury | "declining for 3+ years" | 3 | Temporal; deferred to v9 |
| T5 | fiscal_dom_liq | Net liquidity | "Positive for 2+ of last 3 months" | 2 | Temporal; deferred to v9 |
| T6 | debt_cycle_short/Contraction | Curve re-steepening | "50bp+ AND re-steepened by 75bp+" | 50 | Compound temporal; deferred to v9 |

---

## 3. Theory score deltas

| Theory | Phase | Task 2 score | Task 3 score | Delta | Tier | Cause |
|--------|-------|-------------|-------------|-------|------|-------|
| debt_cycle_short | Expansion | 0.867 | **1.000** | **+0.133** | Active -> Active | "Initial claims low" now triggers (202K < 250K) |
| debt_cycle_short | Contraction | 0.400 | **0.300** | **-0.100** | Adjacent -> Adjacent | "Initial claims rising" stops falsely triggering (202K < 280K) |
| valuation_mean_reversion | -- | 0.706 | 0.706 | 0.000 | Active | -- |
| debt_cycle_long | -- | 0.900 | 0.900 | 0.000 | Active | -- |
| structural_fragility | Building | 0.462 | 0.462 | 0.000 | Adjacent | -- |
| structural_fragility | Resolving | 0.000 | 0.000 | 0.000 | Inactive | -- |
| fiscal_dominance_arithmetic | -- | 1.000 | 1.000 | 0.000 | Active | -- |
| fiscal_dominance_liquidity | -- | 0.778 | 0.778 | 0.000 | Active | -- |
| capital_flows | Accumulation | 0.470 | 0.470 | 0.000 | Adjacent | -- |
| capital_flows | Rotation | 0.450 | 0.450 | 0.000 | Adjacent | -- |
| monetary_architecture | -- | 0.662 | 0.662 | 0.000 | Active | -- |

**No tier changes.** Both score deltas are causally traceable to the initial_claims K-suffix fix only.

---

## 4. Implementation detail

### Old `_extract_number` (destructive global stripping)

```python
cleaned = s.replace("bp", "").replace("%", "").replace("$", "")
cleaned = cleaned.replace("T", "").replace("B", "").replace("M", "")
cleaned = cleaned.replace("x", "")
numbers = re.findall(r"[-+]?\d*\.?\d+", cleaned)
```

Problems:
- Strips B from "Below", T from words containing T, M from "Monthly" etc.
- No suffix scaling at all
- Works by accident because regex still finds the number after mangling

### New `_extract_number` (targeted regex patterns)

```python
# K/k suffix: multiply by 1000
k_match = re.search(r"([-+]?\d*\.?\d+)\s*[Kk]\b", s)
if k_match:
    return float(k_match.group(1)) * 1000

# Strip suffixes attached to numbers only (not letters in words)
cleaned = re.sub(r"(\d)\s*bp\b", r"\1", s)
cleaned = re.sub(r"(\d)\s*%", r"\1", cleaned)
cleaned = cleaned.replace("$", "")
cleaned = re.sub(r"(\d)\s*[TBM]\b", r"\1", cleaned)
cleaned = re.sub(r"(\d)\s*x\b", r"\1", cleaned)

numbers = re.findall(r"[-+]?\d*\.?\d+", cleaned)
```

Improvements:
- K suffix detected and scaled (x1000)
- Suffix characters only stripped when adjacent to digits
- Words like "Below", "Monthly" preserved intact
- Same behavior for all non-K suffixes (intentional; field units vary)

---

## 5. What remains deferred to v9

| Issue | Class | Why deferred |
|-------|-------|-------------|
| T/B/M suffix scaling | Architecture | Field monetary units are inconsistent ($M vs $B). Context-free scaling would break aligned thresholds. Needs structured threshold schema with explicit unit declarations. |
| TGA field-unit mismatch | Field wiring | TGA is in $M (FRED native), threshold says "$500B". Same result for current values but would fail at lower TGA levels. Fix requires either converting TGA to $B or adding field-aware scaling. |
| BUG-03 temporal phrases | Architecture | "3+ months", "2-year high", "rising 0.50%+" all extract wrong numbers. Needs time-series model and structured threshold objects. |
| Compound threshold parsing | Architecture | "Above 500bp AND widening for 2+months" only checks the numeric part. AND/OR conditions need structured schema. |

---

## 6. Carry-forward note for Task 4

`fiscal_dominance_arithmetic` scores 1.000 (ceiling hit). This was already flagged after Task 2 as a denominator-coverage concern: every scored indicator either triggers or is excluded. The correctness harness (Task 4) should make visible whether 1.000 reflects genuine full coverage or a shrunken denominator. Task 3 did not change this score.

`debt_cycle_short/Expansion` also now scores 1.000 after the K fix. This is genuine: all 6 scored indicators (ISM>50, unemployment<5%, spreads<450bp, curve>-0.50%, claims<250K, confidence>90) trigger against current data. The 2 excluded indicators (Fed funds vs GDP, Net credit growth) have no extractable number and are correctly excluded.

---

## 7. Files changed

| File | Change |
|------|--------|
| `backend/engine/activation.py` | `_extract_number()`: replaced destructive global stripping with targeted regex; added K suffix scaling (x1000) |
| `backend/tests/test_activation_web_integration.py` | Added `TestUnitSuffixScalingTask3` (17 tests): K scaling, bp/% no-scaling, $/T/B/M stripping, plain numerics, temporal phrases unchanged, activation-level trigger checks, non-destructive word preservation |
| `docs/POST_V8_TASK3_UNIT_SCALING_RESULTS.md` | This file |

---

*Frozen at Task 3 completion. Task 4 (frozen expected-output correctness harness) is next.*
