# ACTIVATION.md — Fiscal Dominance: Devaluation Arithmetic

*Theory: fiscal_dominance_arithmetic*
*Last updated: April 2026*

---

## phases

**Single-phase theory.** When active, the arithmetic of US federal debt — specifically the trajectory of interest expense relative to tax receipts — has crossed thresholds that historically force resolution via devaluation. There is no secondary phase; the theory either describes the current fiscal trajectory or it does not.

---

## transition_logic

Not applicable. Single-phase theory. Activation is determined by the weighted score of the indicators below. No sequencing or mutual exclusivity to manage.

---

## activation_table

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| Interest expense / tax receipts ratio | Computed: `interest_receipts_ratio` (FRED: FYOINT / FGRECPT annualized) | `computed-mechanical` — Dependencies: FYOINT, FGRECPT. Both API-accessible. Ratio = FYOINT / FGRECPT annualized. Forward projections (CBO) require web-search; current/trailing ratio is fully mechanical. | Above 20% | above | 0.25 | The single most important indicator. When interest expense consumes more than 20% of revenue, the government devotes a fifth of everything it collects to servicing existing debt — before any spending on defense, entitlements, or anything else. Historical precedent: no major sovereign has sustained interest/receipts above 25% without defaulting or devaluing. The 20% threshold marks the zone where the arithmetic becomes self-reinforcing. Recalibrate if: structural changes to revenue composition (e.g., new tax base) alter the relationship. |
| Interest expense exceeds major discretionary category | CBO budget data, defense/entitlement spending comparison | `web-search` — Annual defense and entitlement spending figures require CBO or OMB data, not available via single API feed. | Above 0 (surplus: positive = interest exceeds defense spending, via `interest_exceeds_defense` computed field) | above | 0.15 | A political and psychological threshold. When interest costs more than the entire defense budget, the scale of the problem becomes legible to non-economists. Each successive threshold crossed (defense, then Medicare, then Social Security) reduces the probability of voluntary correction. Recalibrate if: defense spending changes dramatically (e.g., large-scale drawdown), shifting the comparison baseline. |
| Deficit pace outside recession | Computed: `deficit_pace_annualized` (FRED: FYFSD trailing annualized) | `computed-mechanical` — Dependencies: FYFSD (deficit data), USREC (NBER recession dating). Note: NBER declares recessions with a lag (typically 6–12 months). Real-time assessment may require supplementary judgment on whether the economy is in recession. | Deficit above $1.5T annualized while unemployment below 5% | above | 0.20 | Deficits normally widen IN recessions and narrow DURING expansions. Running a $1.5T+ deficit during expansion is historically anomalous — it means the deficit is STRUCTURAL, not cyclical. A structural deficit cannot be resolved by growth alone because it persists even when the economy is strong. This separates "temporary fiscal concerns" from "arithmetic trap." Recalibrate if: the $1.5T threshold becomes obsolete due to inflation (adjust nominally) or structural changes to automatic stabilizers. |
| Debt rollover at higher rates | Treasury refunding data, weighted average interest rate on federal debt | `web-search` — Weighted average coupon on outstanding debt requires Treasury refunding announcements and maturity profile data, not available via single API. | Weighted average rate rising AND below current market rates (rollover still has room to push expense higher) | rising | 0.15 | The delayed fuse. The weighted average coupon on outstanding debt is still below market rate because much debt was issued during prior low-rate periods. As that debt matures and rolls into current rates, interest expense rises MECHANICALLY without any new borrowing. This is the auto-pilot dimension — the arithmetic worsens every month through the passage of time alone. Recalibrate if: Treasury shifts maturity profile dramatically (e.g., heavy short-end issuance that reprices faster, or ultra-long issuance that locks in rates). |
| Gold/oil ratio elevated | Computed: `gold_oil_ratio` (gold price / oil price) | `computed-mechanical` — Dependencies: gold spot price (GC=F or equivalent), WTI crude (CL=F or equivalent). Both API-accessible. Ratio = gold / oil. | Above 25 (vs. historical average ~16–20) | above | 0.10 | The gold/oil ratio measures the monetary premium on gold relative to the most economically essential commodity. When gold buys more barrels of oil than the historical average, the market is assigning a monetary reserve premium to gold above its commodity value. This premium reflects expectations of currency debasement. Note: this indicator is shared with `monetary_architecture`. When both theories are Active, this evidence should not be double-counted — see Shared Upstream Cause Warnings in INTERACTION_MATRIX.md. Recalibrate if: structural changes to oil supply/demand (e.g., energy transition reducing oil's benchmark role) alter the denominator's meaning. |
| Central bank gold purchases sustained | World Gold Council quarterly reports, IMF COFER data | `web-search` — Quarterly publication, not API-accessible. Value requires interpretation of report data. | Central bank buying above 800 tonnes/year for 2+ consecutive years | above | 0.05 | Confirmation that official institutions are voting with their reserves. Sustained buying above 800 tonnes/year (vs. pre-2022 average of ~400–500 tonnes) indicates a structural shift in reserve composition, not a one-time adjustment. Buying is concentrated among non-allied central banks with the strongest incentive to diversify after the 2022 Russia sanctions. Note: this indicator is shared with `monetary_architecture`, which owns the reserve-composition mechanism more directly. Within this theory, it serves as secondary confirmation that the arithmetic is being recognized by reserve managers. See Shared Upstream Cause Warnings in INTERACTION_MATRIX.md. Recalibrate if: a structural reversal in geopolitical alignment eliminates the diversification incentive. |

### Indicator moved to context_flags

**"No credible deficit reduction plan"** was scored in the original module (weight 0.10, binary). Per data ownership classification, this is `qualitative` — no mechanical proxy exists for assessing political will. The spec requires qualitative indicators to be flagged as context, not scored as indicators. Moved to context_flags below. Remaining scored weights sum to 0.90; maximum possible activation score is 0.90 without this indicator.

---

## activation_thresholds

| Status | Score Range |
|--------|------------|
| **Active** | Weighted score ≥ 0.60 |
| **Adjacent** | Weighted score 0.30–0.59 |
| **Inactive** | Weighted score < 0.30 |

Note: With the qualitative "no credible deficit reduction plan" indicator moved to context_flags, the maximum possible mechanical score is 0.90. The Active threshold (0.60) remains achievable from scored indicators alone. No threshold adjustment is needed.

---

## context_flags

Supplementary qualitative flags that are NOT scored but are surfaced to Pass 2 for narrative context. These provide hypothesis-generation context without pretending to be mechanically scorable.

| Flag | Source | Data Ownership | What to Look For |
|------|--------|----------------|------------------|
| No credible deficit reduction plan | Congressional budget proposals, CBO long-term outlook, political analysis | `qualitative` | Neither major party proposing deficit reduction that would bring the deficit below a manageable level within 5 years. Both parties propose tax cuts, spending increases, or both. No credible bipartisan framework exists. The political system has implicitly chosen devaluation. Binary assessment: either a credible plan exists or it does not. |
| Treasury auction deterioration | Treasury auction results, bid-to-cover ratios, dealer takedowns | `web-search` | Declining bid-to-cover ratios, rising dealer takedowns (dealers forced to absorb supply the market won't), tail risk in auctions (clearing above when-issued yield). These are the bond market's real-time verdict on fiscal sustainability. A failed or severely distressed auction would be a regime-change event — extremely unlikely but existential if it occurs. |
| Foreign official Treasury holdings declining | Treasury International Capital (TIC) data, Fed custody holdings | `web-search` | Foreign central bank holdings of Treasuries declining as a percentage of total outstanding. Measured by share-of-outstanding, not dollar amount (total outstanding is growing, so flat holdings = declining share). If the marginal foreign buyer is stepping back, the domestic private market must absorb more supply, requiring higher yields. |
| Petrodollar settlement diversification | Energy trade settlement data, bilateral currency agreements | `web-search` | Oil and gas trade settled in non-dollar currencies. Each transaction that bypasses the dollar reduces structural dollar demand. This is slow-moving but directional. Volume matters more than headlines. Note: this is primarily owned by `monetary_architecture` — surfaced here as context for the secondary accelerant mechanism in CORE.md. |

---

## falsifier_severity_assignments

Severity classifications for all falsifiers. Theory-level falsifiers (from CORE.md) are binary deactivation events. State-level falsifiers (below) are scored as discounts per the canonical severity scale: minor = 0.10 discount, medium = 0.25 discount, major = 0.45 discount.

### Theory-Level Falsifiers (from CORE.md)

| ID | Condition | Classification | Effect |
|----|-----------|---------------|--------|
| H1 | Genuine fiscal consolidation sustained | **Hard — deactivates theory** | If triggered, theory moves to Inactive. The "no political will" assumption is falsified. |
| H2 | Interest/receipts ratio declines to manageable level sustained | **Hard — deactivates theory** | If triggered, the arithmetic pressure that drives the theory has eased to historically manageable levels. Theory moves to Inactive or Adjacent depending on magnitude. |
| H3 | Productivity-driven GDP growth above 4% real sustained for 3+ years | **Hard — deactivates theory** | If triggered, the "grow out of the debt" scenario is operative. Theory moves to Inactive. |

### State-Level Falsifiers

| ID | Condition | Metric | Threshold | Severity | Discount | Implication |
|----|-----------|--------|-----------|----------|----------|-------------|
| S1 | Dollar strengthening despite fiscal deterioration | DXY index or UUP equivalent | DXY rising for 12+ months while interest/receipts above 20% | **medium** | 0.25 | Dollar CAN strengthen even when the arithmetic is terrible (flight to safety, relative weakness elsewhere, US growth exceptionalism). Strong dollar dampens the devaluation transmission: imported goods cheaper, inflation moderates, commodity prices in dollars fall. The devaluation trajectory is unchanged but the timeline extends. Market expression is impaired. |
| S2 | Rates decline substantially (Fed cutting to below 3%) | Federal funds rate | Fed funds below 3% sustained for 6+ months | **major** | 0.45 | Lower rates directly reduce interest expense on floating-rate and short-duration debt. Rollover arithmetic improves — new issuance carries a lower coupon. Interest/receipts ratio declines. The arithmetic pressure eases — not because debt shrank, but because the cost of carrying it declined. However: if rates fell because of recession, receipts also deteriorate, partially offsetting the improvement. The devaluation timeline extends substantially. |
| S3 | Petrodollar system stabilizes or reverses | Energy trade settlement data | Non-dollar energy settlement declines OR major bilateral non-dollar agreements are reversed | **minor** | 0.10 | The petrodollar dimension is SECONDARY to the domestic arithmetic. If diversification stalls, one accelerant is removed but the core domestic mechanism is unaffected. Changes speed, not direction. Note: this falsifier primarily tests the `monetary_architecture` interaction, not the domestic arithmetic itself. |
| S4 | Inflation falls below 2% sustained | CPI YoY | CPI YoY below 2% for 12+ months | **medium** | 0.25 | Low inflation undermines the devaluation channel. If inflation is below the interest rate on debt, real debt burden is NOT declining — it may be increasing. The "inflate away the debt" mechanism requires inflation ABOVE the interest rate. Below-2% inflation means the devaluation is not occurring and the arithmetic worsens in real terms. This is actually the WORST outcome for fiscal sustainability (low inflation + high rates = maximum real interest expense). Weakens the devaluation prediction specifically but may strengthen the broader fiscal crisis thesis — the mechanism is impaired, but the problem persists or worsens. |
| S5 | Tax receipts grow faster than interest expense for 4+ quarters | Treasury receipts vs. interest expense data | Receipts YoY growth exceeds interest expense YoY growth for 4+ consecutive quarters | **minor** | 0.10 | The arithmetic is improving at the margin — the critical ratio stabilizes or declines. Possible drivers: strong economy, bracket creep, capital gains from rising markets. Does not resolve the stock problem (debt is still large) but eases the flow pressure. Timeline extends without changing the structural diagnosis. |

---
