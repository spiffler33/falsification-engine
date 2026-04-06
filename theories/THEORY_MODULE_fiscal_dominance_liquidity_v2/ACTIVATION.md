# ACTIVATION.md — Fiscal Dominance: Net Liquidity Transmission

*Theory Package: `fiscal_dominance_liquidity`*
*Last updated: April 2026*

---

## phases

Single-phase theory. When active, fiscal deficit spending is injecting reserves into the financial system faster than the central bank can drain them. Net liquidity is the dominant driver of asset prices and monetary policy is subordinate. There is no distinct "resolving" phase — the theory is either operative or it is not.

---

## transition_logic

Single-phase: no phase transitions to manage. The theory transitions between Active, Adjacent, and Inactive based on the weighted activation score below.

- **Active → Inactive:** Requires either (a) activation score falling below 0.30, or (b) a state falsifier triggering forced deactivation (SF1).
- **Active → Adjacent:** Activation score falls between 0.30 and 0.59. Mechanism may still be partially operative but is attenuated.
- **Inactive → Active:** Activation score rises to 0.60 or above.

No mutual exclusivity with other theories. This theory can be simultaneously Active with any other theory in the registry, including `fiscal_dominance_arithmetic`.

---

## activation_table

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| Net liquidity expanding | `net_liquidity_30d_change` (computed: WALCL − WTREGEN − RRPONTSYD, 30-day change) | `computed-mechanical` · Dependencies: `liquidity.fed_balance_sheet` (WALCL), `liquidity.tga` (WTREGEN), `liquidity.reverse_repo` (RRPONTSYD) | Positive for 2+ of last 3 months | above | 0.20 | The direct test. If net liquidity is expanding despite QT, the fiscal channel is overwhelming the monetary channel. This is the single most important indicator — it IS the mechanism in real-time. All three input feeds must be fresh; if any one is stale, the computation is silently wrong. |
| Deficit pace | US Treasury monthly budget statements | `web-search` · Preferred source: US Treasury Monthly Treasury Statement, CBO Monthly Budget Review | Above 1500 annualized (in $B) | above | 0.20 | The fuel. Below $1,500B ($1.5T), the fiscal impulse is insufficient to overpower QT at current balance sheet runoff rates (~$60B/month = ~$720B/year). The $1,500B threshold is calibrated to the approximate equilibrium point where fiscal injection = QT extraction at 2024-2025 QT pace. Recalibrate if QT pace changes materially. |
| Rate hikes not producing recession | `growth.unemployment` + `growth.ism_proxy` | `computed-mechanical` · Dependencies: `growth.unemployment`, `growth.ism_proxy` | Unemployment below 5% AND ISM proxy above 45 after 12+ months of Fed funds above 4% | above | 0.15 | The paradox test. In monetary dominance, rates above 4% for a year produce visible economic contraction. If the economy absorbs 5%+ rates without contracting, something is overriding monetary transmission. This indicator identifies the symptom (monetary policy impotence), not the mechanism. |
| Hard assets outperforming nominal bonds | `hard_vs_nominal_12m` (computed: average 12M return of hard assets minus average 12M return of nominal bonds) | `computed-mechanical` · Dependencies: GLD, SLV, DBC 12M returns; TLT, IEF 12M returns | Above +10% | above | 0.15 | The asset-price confirmation. When the fiscal channel dominates, inflation/debasement implications favor assets with replacement cost or scarcity value over fixed-income promises. Below +5% divergence is inconclusive. Above +10% is a clear signal. |
| RRP draining toward zero | `liquidity.reverse_repo` (RRPONTSYD) | `mechanical` | Below $250B and declining | below | 0.10 | Reserve buffer indicator. As the RRP drains, those reserves re-enter the financial system. Below $250B, the buffer is nearly exhausted. Once drained, the Fed faces a choice between allowing reserve scarcity (risking a repo spike) or ending QT early (capitulating). Either outcome confirms the thesis. |
| Fed balance sheet direction inconsistent with stated policy | `liquidity.fed_balance_sheet` (WALCL) direction vs. stated QT pace | `computed-mechanical` · Dependencies: `liquidity.fed_balance_sheet` rate of change; stated QT pace requires `web-search` (FOMC statements) | Fed BS declining slower than announced QT pace, OR flat, OR expanding despite no announced policy change | rising or flat | 0.10 | The stealth-capitulation indicator. If the balance sheet stops shrinking or starts growing (via discount window lending, emergency facilities, or other interventions), the central bank is de facto accommodating fiscal dominance. March 2023 (SVB response: ~$400B expansion in two weeks while officially doing QT) is the template. Note: stated QT pace is a web-search dependency — must be refreshed after every FOMC meeting. |
| TGA behavior consistent with spending | `liquidity.tga` (WTREGEN) | `mechanical` | TGA below $500B OR declining by $100B+ over 60 days | below or falling | 0.10 | Treasury is spending its cash buffer, releasing reserves into the system. When TGA is high and building, it temporarily drains liquidity. When TGA drains, reserves flood back. Captures periods where Treasury is actively deploying cash. |

---

## activation_thresholds

| Score Range | Status | Implication |
|-------------|--------|-------------|
| ≥ 0.60 | **Active** | Fiscal dominance operative. Net liquidity is the dominant asset-price driver. Full directional predictions apply. |
| 0.30–0.59 | **Adjacent** | Mechanism may be partially operative or approaching activation. Directional predictions apply at reduced confidence. Monitor closely for threshold crossings. |
| < 0.30 | **Inactive** | Fiscal dominance not operative. Standard monetary-dominance framework applies. |

---

## context_flags

Supplementary qualitative flags. NOT scored mechanically. Surfaced to the generator for contextual reasoning only.

| Flag | Data Ownership | Source | What to Look For |
|------|----------------|--------|------------------|
| Bipartisan fiscal expansion | `web-search` | Congressional Budget Office, fiscal policy news | Neither party campaigning on deficit reduction. Both parties proposing new spending or tax cuts. This is the political precondition for sustained fiscal dominance — it means no policy correction is forthcoming. |
| Fed officials acknowledging fiscal offset | `web-search` | FOMC minutes, Fed speeches | Language like "fiscal policy is offsetting monetary tightening" or "the neutral rate may be higher than estimated." Coded acknowledgment that rate hikes are not working as expected. |
| Treasury issuance composition shifting to bills | `web-search` | Treasury refunding announcements | Heavy bill issuance (short-dated) rather than coupon issuance. Bills are more easily absorbed by money market funds and do not create duration risk. Signals Treasury is managing around fiscal dominance constraints rather than challenging them. |

---

## falsifier_severity_assignments

Severity assignments for deep falsifiers defined in CORE.md. These are scoring pipeline parameters.

| Falsifier (from CORE.md) | Severity | Rationale |
|--------------------------|----------|-----------|
| DF1 — Net liquidity contracts despite large deficit | Hard falsifier — disconfirm | Core mechanism broken. No discount — kill hypotheses invoking this theory. |
| DF2 — Rate hikes produce recession despite fiscal spending | Hard falsifier — disconfirm | Core claim falsified. Monetary dominance persists. |
| DF3 — Sustained decorrelation across varied conditions | Hard falsifier — disconfirm | Reserve-to-asset-price transmission misspecified. Note: this is the escalated form of state falsifier SF2 (see below). Escalation criteria defined in PLAYBOOK.md. |

---

## state_falsifiers

Conditions that would force a state transition or challenge the activation determination. Distinct from theory-level falsifiers in CORE.md.

| ID | Severity | Condition | Metric | Data Ownership | Threshold | Implication |
|----|----------|-----------|--------|----------------|-----------|-------------|
| SF1 | State change → Inactive | Genuine fiscal consolidation | Deficit pace from CBO Monthly Budget Review, Treasury statements | `web-search` | Deficit falls below $800B annualized for 2+ consecutive quarters through actual spending cuts or revenue increases (not accounting adjustments or one-time items) | Fuel for fiscal dominance removed. QT drains reserves faster than fiscal injection replenishes them. Net effect flips to tightening. One-quarter flukes do not count — tax-deadline lump-sum receipts (April/June) temporarily compress the deficit. Requires 2+ consecutive quarters. |
| SF2 | **Major** (0.10 discount) | Net liquidity and asset prices decorrelate | Computed: 12-month rolling correlation between `net_liquidity` and SPY price | `computed-mechanical` · Dependencies: `net_liquidity` (computed), SPY daily close | Correlation falls below 0.30 | Strongest soft falsifier. If asset prices stop following net liquidity, the transmission mechanism may be overridden by other forces or may be misspecified. Temporary decorrelation is expected during narrative-driven markets or single-factor overrides (e.g., late 2022 rate-hike sentiment). Directional predictions lose reliability while decorrelation persists. Escalation criteria to hard falsifier (DF3) defined in PLAYBOOK.md. |
| SF3 | **Medium** (0.25 discount) | Dollar strengthening despite fiscal dominance | DXY index | `mechanical` | DXY rising for 6+ months concurrent with expanding net liquidity | Fiscal dominance should weaken the dollar. If the dollar strengthens anyway (flight-to-safety, relative weakness elsewhere), the hard-asset predictions weaken. The equity-liquidity correlation may still hold, but the inflation/debasement channel is impaired. |
| SF4 | **Medium** (0.25 discount) | QT pace accelerating | `liquidity.fed_balance_sheet` rate of change | `mechanical` | Fed BS declining faster than announced pace (e.g., $80B+/month vs. announced $60B) | The Fed is fighting harder against fiscal dominance. Does not break the theory if the deficit is large enough to offset, but net liquidity expansion slows. Asset price support attenuates. Predictions should be revised to the lower end of magnitude ranges. |
| SF5 | **Minor** (0.10 discount) | RRP re-expanding | `liquidity.reverse_repo` | `mechanical` | RRP rising above $500B after having declined below $250B | Money market funds parking cash back at the Fed. Removes reserves from circulation, reduces net liquidity. Possible cause: T-bill issuance declining. Temporarily weakens the liquidity transmission without breaking the theory — the reserves still exist, they are just parked. |
| SF6 | **Medium** (0.25 discount) | Hard assets underperforming despite rising net liquidity | `hard_vs_nominal_12m` (computed) | `computed-mechanical` · Dependencies: GLD, SLV, DBC, TLT, IEF 12M returns | Below 0% for 6+ months while net liquidity is expanding | If net liquidity is rising but hard assets are not responding, the debasement premium is not being priced. The equity-liquidity correlation may still hold, but the full fiscal dominance thesis (which predicts hard-asset outperformance specifically) is weakened. May indicate the market does not yet believe in the debasement trajectory — timing revision needed, not thesis revision. |

---
