# debt_cycle_long — ACTIVATION.md

*State Detection Spec — audited by data pipeline tests*

---

## phases

**Single-phase.** When active, the economy is in the late stage of a multi-decade debt accumulation cycle — the stage where conventional monetary policy tools are exhausted or approaching exhaustion, forcing escalation to unconventional tools. The theory does not have distinct sub-phases; it is either Active (late-cycle conditions met), Adjacent (approaching late-cycle), or Inactive (early-to-mid cycle).

---

## transition_logic

Not applicable for intra-theory transitions. This theory has a single phase.

Activation state transitions:
- **Inactive → Active:** Weighted activation score crosses above 0.60. In practice, this transition occurred around 2008-2009 for the US (ZLB first hit, QE first deployed) and has not reversed.
- **Active → Inactive:** Only via deep falsifiers H1, H2, or H3 — representing genuine resolution of the long-term cycle. This is a multi-decade transition, not a quarterly toggle.
- **Precedence:** Check deep falsifiers FIRST. If any H1/H2/H3 condition is met, theory is Inactive regardless of activation score.

---

## activation_table

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| Total debt / GDP above historical warning level | Federal Reserve Z.1 Financial Accounts, BIS global credit | `web-search` (preferred source: FRED Z.1 non-financial debt aggregates) | Total US non-financial debt / GDP above 250% | above | 0.25 | At 250%+ debt/GDP, debt service costs materially constrain growth and force policy to prioritise debt sustainability over price stability. The US crossed 250% around 2008 and currently sits at ~260-270%. Japan crossed 250% in the mid-1990s. For context: ~130% in the early 1980s, ~180% by 2000, ~240% by 2008. Each short-term cycle leaves total debt higher — the ratchet. |
| Fed balance sheet / GDP elevated | `fed_bs_gdp_ratio` (WALCL / nominal GDP, as percentage) | `computed-mechanical` — dependencies: `liquidity.fed_balance_sheet`, nominal GDP from FRED. Pre-computed ratio field: `fed_bs_gdp_ratio` | Above 20 | above | 0.25 | Direct evidence of MP2 deployment. The balance sheet was ~6% of GDP before 2008, rose to ~25% after 2008 QE, hit 36% after COVID QE, currently ~26% despite QT. Above 20% means MP2 has been substantially deployed and the balance sheet cannot easily return to pre-2008 levels without destabilising the system. |
| Rates at or near effective lower bound within recent memory | `rates.fed_funds` (historical lookback) | `mechanical` | Fed funds rate was at 0-0.25% within the last 10 years | above | 0.15 | Evidence that MP1 was exhausted in recent history. ZLB was hit in 2008-2015 and again in 2020-2022. The speed of return in each crisis (2008: 15 months; 2020: 2 weeks) demonstrates gravitational pull. Even if rates are currently elevated, the lookback window captures that MP1 was exhausted recently. |
| Fiscal deficit as primary growth driver | CBO budget data, BEA GDP components | `web-search` (preferred source: CBO Monthly Budget Review, BEA NIPA tables) | Federal deficit exceeds 5% of GDP during non-recession AND private sector credit growth below 3% | above | 0.15 | The defining characteristic of MP3. When government is the primary source of demand growth rather than private-sector credit, the economy has transitioned to fiscal dominance — the culmination of the long-term cycle. The dual threshold captures the specific condition where fiscal is primary while private credit is secondary. |
| Wealth inequality at cycle-characteristic extremes | Fed Distributional Financial Accounts, World Inequality Database | `web-search` (preferred source: Fed DFA, updated quarterly) | Top 10% wealth share above 70% OR top 1% income share above 20% | above | 0.10 | Both symptom and cause of late-cycle dynamics. Symptom: decades of asset price inflation (fuelled by successive MP2/MP3 interventions) disproportionately benefit asset owners. Cause: inequality generates political pressure for populist fiscal policy — which IS MP3. The inequality → populism → fiscal expansion causal chain is the political transmission mechanism of the late long-term cycle. |
| Negative real rates during expansion | Computed: `real_fed_funds_rate` (fed funds rate minus CPI YoY inflation) | `computed-mechanical` — dependencies: `rates.fed_funds`, `inflation.cpi_yoy` | Below 0 (negative real rate = financial repression signature) | below | 0.10 | Sustained negative real rates are the financial repression signature. In the early-to-mid cycle (1980s-2000s), real rates were typically positive (2-4%). The US had negative real rates for most of 2009-2022 (~13 of 14 years). Even at current positive real rates, the long-term cycle's structural pull is toward lower real rates. |

**Weight redistribution note:** Indicator #7 from v1 ("Each successive crisis requires larger intervention," weight 0.10) has been reclassified as a context flag (see below). Its weight has been redistributed: +0.05 to total debt/GDP (now 0.25) and +0.05 to Fed BS/GDP (now 0.25). Rationale: these are the two most directly testable measures of the long cycle's structural state. The escalation thesis remains testable via deep falsifier H3 in CORE.md.

---

## activation_thresholds

| Status | Score Range |
|--------|------------|
| **Active** | ≥ 0.60 |
| **Adjacent** | 0.30 – 0.59 |
| **Inactive** | < 0.30 |

---

## context_flags

Supplementary qualitative flags — NOT scored mechanically. Surfaced to the generator for contextual reasoning.

| Flag | Source | Data Ownership | What to Look For |
|------|--------|----------------|-----------------|
| Political system producing populist fiscal policy | Policy platforms, electoral outcomes | `qualitative` | Both left-populism (social spending, redistribution) and right-populism (tariffs, industrial policy, tax cuts) are expressions of MP3. When BOTH parties compete on fiscal expansion — differing on allocation but not on deficit spending — the political system has converged on MP3 regardless of electoral outcome. |
| Central bank independence under pressure | Political commentary on Fed, proposed legislation | `qualitative` | Proposals to audit, restructure, or politically direct the central bank. Explicit executive-branch criticism of rate policy. In the late long-term cycle, fiscal authorities increasingly need monetary accommodation and political pressure on independence rises. Loss of independence would accelerate the transition to explicit fiscal-monetary coordination. |
| Japan-style dynamics emerging | BOJ policy evolution, yield curve control discussions | `web-search` | Japan has been in the late long-term cycle since the early 1990s — 30+ years. Japan's policy evolution (QE → ZIRP → NIRP → YCC → coordinated fiscal-monetary) provides a roadmap for where the US cycle may go. Any discussion of yield curve control in the US context signals Japanese-style dynamics are being contemplated. |
| Escalation ratchet pattern intact | Historical crisis response comparison | `qualitative` | Each successive crisis response was larger than the prior one (2001: rate cuts only; 2008: QE at ~25% of GDP; 2020: QE + fiscal at ~35% of GDP). This is a historical-pattern assessment, not a live mechanically testable variable. The genuine falsification of this claim exists as deep falsifier H3 ("next recession resolved by MP1 alone"). This flag tracks whether the pattern remains unbroken. |

---

## falsifier_severity_assignments

### Deep falsifier severities (conditions defined in CORE.md)

| Falsifier | Severity | Rationale |
|-----------|----------|-----------|
| H1 — Organic deleveraging below 200% debt/GDP | **Hard falsifier — theory killed** | Would mean the late-cycle condition has genuinely resolved. No precedent for voluntary achievement at current levels. |
| H2 — Sustained 4%+ real GDP growth for 5+ years | **Hard falsifier — theory killed** | Would mean the economy is growing out of the debt organically. Extraordinarily demanding threshold; last achieved in the 1960s. |
| H3 — Next recession resolved by MP1 alone | **Hard falsifier — theory killed** | Would break the escalation pattern that is central to the theory's mechanism. The test is prospective — it can only be evaluated when the next recession occurs. |

### State-level falsifier severities

| # | Condition | Metric | Threshold | Severity | Rationale |
|---|-----------|--------|-----------|----------|-----------|
| S1 | QT completes successfully — Fed balance sheet returns below 15% of GDP without financial market disruption or emergency facility deployment | `liquidity.fed_balance_sheet` / GDP (`computed-mechanical`) | Fed BS below 15% of GDP, no emergency liquidity facilities activated during the drawdown | **medium** (0.25 discount) | Weakens the "MP2 is irreversible" claim without changing the debt/GDP reality. Even if the balance sheet normalises, total debt/GDP remains above 250% and the structural conditions persist. The balance sheet is one indicator of late-cycle dynamics, not the only one. |
| S2 | Japan-style stagnation — low growth, low inflation, stable debt/GDP for 10+ years | Japan comparison metrics: CPI trajectory, GDP growth, debt/GDP trend | US debt/GDP stable (not rising), CPI consistently below 2%, GDP growth 1-2%, no financial crisis for 10+ years | **major** (0.45 discount) | The scenario where the theory's diagnosis is correct (late cycle) but its asset-price predictions are substantially wrong. Instead of inflation, gold outperformance, and bond underperformance, the Japan outcome produces low rates, modest positive bond returns, and flat gold. This does NOT kill the theory — it modifies the consequences. The single most important alternative scenario the generator must address. |
| S3 | Central bank maintains genuine independence through late cycle — sustains positive real rates during fiscal expansion without government override or restructuring | Fed policy independence metrics (`web-search`) | Positive real fed funds rate for 3+ consecutive years during fiscal expansion, no political restructuring of the Fed | **medium** (0.25 discount) | Impairs the financial repression channel. Positive real rates prevent the "inflate away the debt" mechanism. Changes trade expression (less certain about bond underperformance) but increases tail risk of disorderly resolution — the debt must still be resolved, but the orderly path is blocked. |
| S4 | Emerging monetary technology fundamentally changes transmission mechanisms | CBDC deployment, stablecoin regulation, blockchain settlement adoption (`web-search`) | Major central banks deploy CBDCs that bypass traditional banking-system transmission, or non-sovereign digital currency achieves significant settlement volume | **minor** (0.10 discount) | Extends timeline and introduces uncertainty about resolution mechanism without changing current-state diagnosis. The debt exists regardless of payment technology. New tools could change how the cycle resolves but do not change the fact that resolution is needed. |
