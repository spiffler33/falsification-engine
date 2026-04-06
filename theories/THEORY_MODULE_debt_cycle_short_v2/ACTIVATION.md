# debt_cycle_short — ACTIVATION.md

*State Detection Spec*
*Last updated: April 2026*

---

## phases

Two mutually exclusive phases:

- **Phase A: Expansion** — credit expanding, economic activity accelerating or steady, risk appetite healthy.
- **Phase B: Contraction** — credit contracting, economic activity decelerating or declining, risk appetite collapsing.

---

## transition_logic

1. **Check Phase B first.** If Phase B scores Active (≥0.60), Phase A is by definition Inactive. Stop. The expansion has ended.

2. **If Phase B is Inactive,** score Phase A.

3. **Late-cycle transition state:** The most operationally valuable state is Phase B scoring Adjacent (0.30–0.59) while Phase A remains Active (≥0.60). This is late cycle — expansion intact, contraction indicators emerging. This is NOT a separate phase; it is the overlap where both scorers return meaningful results. The clean rule: late cycle = Expansion still Active, Contraction Adjacent.

4. **Phase B has absolute precedence.** Once Phase B is Active, the system stops calling it late cycle, regardless of what Phase A indicators show. Some Phase A indicators (e.g., unemployment still low in absolute terms) may still read as "expansion" for weeks or months after Phase B activates — this is expected lag, not contradiction.

5. **Sequencing after contraction:** Phase B deactivates when its indicators fall below Active threshold AND Phase A re-scores at Adjacent or higher. The cycle has restarted.

---

## activation_table — Phase A: Expansion

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| ISM proxy above contraction | `growth.ism_proxy` (MANEMP) | mechanical | Above 50 | above | 0.15 | Most reliable single coincident indicator of manufacturing expansion. Above 50 = expansion. Has led GDP turning points by 2–4 months in every post-war cycle. Calibration: the 50 threshold is the index's design boundary (above = expanding, below = contracting). Not subject to recalibration. |
| Unemployment low or falling | `growth.unemployment` | mechanical | Below 5.0% OR declining for 3+ months | below or falling | 0.15 | Lagging indicator — confirms the cycle rather than predicting it. Below 5.0% is consistent with output at or above potential. Direction matters: stable-to-declining confirms expansion; rising even from low levels warns of phase transition. Calibration: 5.0% threshold reflects post-2000 NAIRU estimates. Recalibrate if NAIRU shifts structurally. |
| Credit spreads tight or tightening | `credit.hy_spread` | mechanical | Below 450bp AND not widening for 3+ consecutive months | below and stable/tightening | 0.15 | Credit market's verdict on default risk. Below 450bp = low distress probability. Below 300bp = fragility signal (that is `structural_fragility`'s domain, not this indicator's). Calibration: 450bp is approximately the 35th percentile of historical HY spreads. Recalibrate if the composition of the HY index shifts materially. |
| Yield curve not deeply inverted | `rates.curve_2s10s` | mechanical | Above -0.50% (inversion shallower than 50bp, or positive slope) | above | 0.10 | Deep inversion has preceded every post-war recession by 6–18 months. But the curve can remain inverted for 12–24 months before contraction begins — inversion alone does not trigger Phase B, it warns the expansion is late. Calibration: -0.50% threshold distinguishes "shallow/technical" inversion from "deep/predictive" inversion. Based on the observation that inversions shallower than 50bp have produced false positives. |
| Initial claims low | `growth.initial_claims` | mechanical | Below 250K (4-week average) | below | 0.10 | Fastest-updating labor market indicator. Below 250K = very few layoffs, consistent with active hiring. Claims typically rise 3–6 months before unemployment does. Calibration: 250K threshold is scaled to current labor force size (~160M). Recalibrate proportionally if labor force grows substantially. |
| Fed funds below nominal GDP growth | `rates.fed_funds` vs. `growth.gdp_latest` (annualized nominal) | computed-mechanical | Fed funds rate below nominal GDP growth rate | below | 0.10 | Monetary policy is accommodative when the policy rate is below the economy's nominal growth rate. This condition sustains credit expansion. **Dependencies:** `rates.fed_funds` (FRED: FEDFUNDS) + `growth.gdp_latest` (FRED: GDP, annualized nominal). Both must be current for the computation to be valid. |
| Net credit growth positive | web search: Fed Senior Loan Officer Survey (SLOOS), bank lending data | web-search | Banks reporting steady or loosening lending standards AND loan growth positive YoY | above | 0.15 | Credit is the fuel of the short-term cycle. SLOOS tightening has led every recession by 3–6 quarters. Preferred source: Federal Reserve SLOOS (published quarterly, January/April/July/October). Calibration: binary (tightening vs. steady/easing across multiple loan categories). The threshold is qualitative-binary, but the data source is a specific published survey. |
| Consumer/business confidence | web search: Conference Board Consumer Confidence, CEO Confidence Survey | web-search | Consumer confidence above 90 AND not declining for 3+ months | above and stable/rising | 0.10 | Confidence drives spending and investment decisions. Below 80 with declining trajectory has preceded every recession since 1970. Preferred source: Conference Board (monthly). Calibration: 90 threshold is approximately the historical median. Recalibrate if the index methodology changes. |

### Activation thresholds — Phase A

- Weighted score ≥ 0.60 → **Active (Expansion)**
- Weighted score 0.30–0.59 → **Adjacent (Expansion)**
- Weighted score < 0.30 → **Inactive**

---

## activation_table — Phase B: Contraction

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| ISM proxy below contraction | `growth.ism_proxy` (MANEMP) | mechanical | Below 48 AND declining for 3+ months | below and falling | 0.15 | Below 48 and falling is accelerating contraction. The "and falling" qualifier avoids false signals from manufacturing hovering near 49 (sector rotation, not broad contraction). Calibration: 48 rather than 50 because sustained readings at 49 have not reliably preceded recession. |
| Unemployment rising (Sahm Rule) | `growth.unemployment` | computed-mechanical | 3-month moving average rising 0.50%+ above its 12-month low | rising | 0.20 | Near-perfect post-war track record — without exception, this condition has coincided with the onset of recession. Weight reflects reliability. **Dependencies:** `growth.unemployment` (FRED: UNRATE), requires 12 months of history for trough calculation. |
| Credit spreads widening sharply | `credit.hy_spread` | mechanical | Above 500bp AND widening for 2+ months, OR any move above 600bp | above and widening | 0.15 | Above 500bp with widening trajectory = credit cycle has turned. Above 600bp from any level = acute stress with forced institutional selling (rating mandates). Speed matters as much as level: 100bp in a month is more significant than 200bp over a year. Calibration: 500bp is approximately the 65th percentile historically; 600bp marks the onset of the forced-selling regime. |
| Yield curve re-steepening from deep inversion | `rates.curve_2s10s` | computed-mechanical | Curve was inverted by 50bp+ AND has re-steepened by 75bp+ from maximum inversion | rising sharply | 0.15 | The re-steepening — not the inversion itself — is the proximate recession signal. The curve re-steepens when the market prices in rate cuts because it sees recession coming. Every post-war recession has been preceded by this sequence: deep inversion → rapid re-steepening → recession within 0–6 months. **Dependencies:** `rates.curve_2s10s` (FRED: T10Y2Y), requires tracking of inversion depth and subsequent re-steepening magnitude. |
| Initial claims rising | `growth.initial_claims` | mechanical | 4-week average above 280K AND rising for 8+ weeks | above and rising | 0.10 | Sustained rise above 280K with 8-week upward trend = layoffs broadening across industries. 280K approximates the level where new hires no longer offset layoffs. Calibration: scaled to current labor force size. Recalibrate proportionally. |
| Fed funds above nominal GDP growth | `rates.fed_funds` vs. `growth.gdp_latest` | computed-mechanical | Fed funds exceeds nominal GDP growth by 1%+ for 6+ months | above | 0.10 | Policy is genuinely restrictive — the cost of money exceeds the return on economic activity. 6-month duration qualifier avoids false signals from brief inversions. **Dependencies:** same as Phase A (FEDFUNDS + nominal GDP). |
| SLOOS showing broad tightening | web search: Fed Senior Loan Officer Survey | web-search | Net % of banks tightening positive across 3+ loan categories for 2+ consecutive quarters | above | 0.15 | Credit channel closing. The reflexive tightening loop — tightening → reduced credit → weaker economy → more tightening — is the core Dalio contraction mechanism. 2+ quarters of broad tightening has preceded every credit-driven recession. Preferred source: Federal Reserve SLOOS (quarterly). |

### Activation thresholds — Phase B

- Weighted score ≥ 0.60 → **Active (Contraction)**
- Weighted score 0.30–0.59 → **Adjacent (Contraction)**
- Weighted score < 0.30 → **Inactive**

---

## quadrant_classification — Second-Tier Determination

After determining the phase (Expansion or Contraction), classify the inflation axis to establish the quadrant. This is a secondary classification layer, not a separate activation score.

### Quadrant Determination Inputs

| Indicator | Metric Source | Data Ownership | Threshold | Usage |
|-----------|--------------|----------------|-----------|-------|
| CPI YoY direction | `inflation.cpi_yoy` | mechanical | Above 3% and rising = inflationary axis. Below 2.5% and falling = disinflationary axis. | Primary inflation signal. |
| Core PCE YoY level | `inflation.core_pce_yoy` | mechanical | Above 2.5% = elevated. Below 2.5% = contained. | Confirms CPI signal, filters volatile components. |
| 5-year breakeven direction | `inflation.breakeven_5y` | mechanical | Widening for 3+ months = market pricing in sustained inflation. Narrowing = market pricing disinflation. | Forward-looking market confirmation of the inflation regime. |

### Quadrant Assignment Rules

| Phase | Inflation Axis | Quadrant |
|-------|---------------|----------|
| Phase A (Expansion) | Falling or stable-low (CPI <2.5%, Core PCE <2.5%) | **Goldilocks** |
| Phase A (Expansion) | Rising (CPI >3% and rising, breakevens widening) | **Reflation** |
| Phase B (Contraction) | Falling (CPI declining, breakevens narrowing) | **Deflation** |
| Phase B (Contraction) | Rising or sticky-high (CPI >3% AND rising or sticky) | **Stagflation** |

### Quadrant Ambiguity Rule

When inflation and growth indicators contradict each other for 3+ months (e.g., ISM rising but CPI also rising sharply, or growth decelerating but inflation falling rapidly), the quadrant is ambiguous. Flag as `QUADRANT_AMBIGUOUS`. This condition corresponds to state falsifier S4.

---

## context_flags

These are NOT scored. They are surfaced to the generator for interpretive context.

| Flag | Source | What to Look For | Usage |
|------|--------|------------------|-------|
| Cycle maturity | Trajectory of Phase A indicators (ISM direction, claims direction, curve slope trend) | ISM peaking/declining, claims inflecting upward, curve flattening/inverting, SLOOS tightening — while Phase A is still Active | Indicates late cycle. Generator should produce both continuation and turn-risk hypotheses. |
| Credit-driven vs. fiscally-sustained expansion | SLOOS + deficit data | If SLOOS shows easing AND deficit is below $1T annualized → credit-driven. If SLOOS shows tightening but GDP positive and deficit above $1.5T → fiscally-sustained. | Critical for interpreting late-cycle signals. Fiscally-sustained expansion makes timing unreliable. See INTERACTION_MATRIX.md for fiscal_dominance_liquidity interaction. |
| Contraction speed | Rate of change in Phase B indicators | Claims rising faster than 10K/week sustained, ISM falling faster than 2 points/month, spreads widening faster than 50bp/month | Fast contraction suggests exogenous shock or fragility break rather than normal credit cycle. Connects to `structural_fragility`. |

---

## state_falsifiers

These test the activation determination, not the theory itself. Severity assigned here.

| # | Severity | Condition | Metric | Threshold | Implication |
|---|----------|-----------|--------|-----------|-------------|
| S1 | **medium** (0.25) | Yield curve signal fails to predict recession within 24 months of deep inversion | `rates.curve_2s10s` | Inversion exceeds -75bp, then re-steepens, but no recession within 24 months of initial inversion | The curve's post-war track record is perfect. A false positive means the indicator needs recalibration — possibly because fiscal dominance has changed the curve's information content. Reduce weight on curve-based indicators; increase weight on SLOOS and claims. |
| S2 | **minor** (0.10) | ISM diverges from GDP for 6+ months | `growth.ism_proxy` vs. GDP | ISM below 48 for 6+ months while GDP growth above 1.5% | Manufacturing and the broad economy are decoupling. ISM may be measuring sectoral rotation, not a broad cycle turn. Shift weight toward services-sector indicators and aggregate employment data. |
| S3 | **major** (0.45) | Central bank pre-emptively cuts before labor market deterioration | `rates.fed_funds` + `growth.unemployment` | Fed cuts 75bp+ while unemployment below 4.5% and stable | Central bank engineering a soft landing. If successful, Phase B may never formally activate — the expansion extends with a growth scare but no recession. Reduces magnitude of contraction-phase predictions. |
| S4 | **minor** (0.10) | Four-quadrant determination is ambiguous | Inflation + growth indicators | Growth and inflation indicators contradict each other for 3+ months | Quadrant overlay requires clear positioning. If data is mixed, optimal positioning is uncertain. Generator should not produce high-conviction quadrant-dependent predictions. |

---

## falsifier_severity_assignments

Consolidated severity assignments for all falsifiers referenced in this theory:

| Falsifier | Location | Severity | Discount |
|-----------|----------|----------|----------|
| H1 (expansion under restrictive policy, no fiscal offset) | CORE.md deep_falsifiers | hard — binary kill | Disconfirm all hypotheses depending on this theory |
| H2 (credit contraction without economic weakness) | CORE.md deep_falsifiers | hard — binary kill | Disconfirm all hypotheses depending on this theory |
| H3 (Phase B triggered, no recession in 18 months) | CORE.md deep_falsifiers | hard — binary kill | Disconfirm all hypotheses depending on this theory |
| S1 (yield curve false positive) | ACTIVATION.md state_falsifiers | medium | 0.25 conviction discount |
| S2 (ISM-GDP divergence) | ACTIVATION.md state_falsifiers | minor | 0.10 conviction discount |
| S3 (pre-emptive soft landing) | ACTIVATION.md state_falsifiers | major | 0.45 conviction discount |
| S4 (quadrant ambiguity) | ACTIVATION.md state_falsifiers | minor | 0.10 conviction discount |

---
