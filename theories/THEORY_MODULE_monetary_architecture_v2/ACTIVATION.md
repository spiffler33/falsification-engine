# monetary_architecture — ACTIVATION.md

*State Detection Spec — Audited by data pipeline tests*

---

## phases

**Single-phase theory.** When active, the global monetary system's foundational plumbing — collateral structures, reserve composition, and settlement mechanisms — is undergoing a structural transition.

This theory does not toggle on and off. It describes a multi-decade structural transition. It has been Active since approximately 2022 (the Russia sanctions marked the structural break) and is unlikely to become Inactive without a fundamental reversal of geopolitical and fiscal trends.

---

## transition_logic

Not applicable for single-phase theories.

**Activation persistence note:** Once Active, this theory remains Active unless one or more hard falsifiers (H1–H4) are triggered. Short-term fluctuations in individual indicators (e.g., a quarter of lower CB gold buying) do not warrant status change. The structural break (2022 sanctions) cannot be undone — the knowledge that reserves can be frozen is permanent even if specific sanctions are reversed.

---

## activation_table

Two indicators from the original module have been reclassified from scored to context flags because they are qualitative and cannot be mechanically scored:
- "Sanctions weaponization continuing or expanding" (originally 0.10 weight) → moved to context_flags
- "Pozsar/Gromen thesis gaining institutional adoption" (originally 0.05 weight) → moved to context_flags

Remaining scored indicators have been proportionally reweighted from a 0.85 base to sum to 1.00. Activation thresholds (0.60 / 0.30) are unchanged.

| Indicator | Metric Source | Data Ownership | Threshold | Direction | Weight | Calibration Rationale |
|-----------|--------------|----------------|-----------|-----------|--------|-----------------------|
| Central bank gold purchases sustained at elevated levels | World Gold Council quarterly reports, IMF IFS data | **web-search** — quarterly publication, no real-time API. Preferred source: WGC quarterly demand trends report. Cross-check: IMF IFS reserve data (monthly, lagged). | Central bank gold buying above 800 tonnes/year for 2+ consecutive years | above | 0.29 | Pre-2022 baseline was 400–600 tonnes/year. In 2022 and 2023, buying exceeded 1,000 tonnes/year. If sustained above 800 tonnes, this is structural reserve reallocation, not a one-time adjustment. The buying is concentrated among non-allied central banks with the strongest sanctions-diversification incentive. Each tonne purchased is permanently removed from the tradeable float — the supply/demand impact is cumulative. |
| Foreign official Treasury holdings declining as share of outstanding | Treasury International Capital (TIC) data, FRED series for total marketable debt outstanding | **computed-mechanical** — Dependencies: (1) FRED series `FDHBFIN` (foreign holdings of Treasury securities) or TIC monthly data; (2) FRED series `MVMTD027MNFRBDAL` or Treasury total marketable debt outstanding. Computation: foreign official holdings / total outstanding. | Foreign official holdings as % of total outstanding declining for 3+ years | declining share | 0.24 | The mirror of gold buying. The metric is share-of-outstanding, not dollar amount — total outstanding is growing rapidly (fiscal deficits), so flat dollar holdings = declining share. Declining share means the domestic private sector must absorb more issuance, requiring higher term premium. This reinforces the fiscal arithmetic thesis (less foreign demand → higher yields → higher interest expense). |
| Gold/oil ratio elevated and rising | Computed from gold spot price and crude oil price | **computed-mechanical** — Dependencies: (1) Gold spot price (Yahoo Finance, FRED `GOLDAMGBD228NLBM`, or equivalent); (2) WTI crude oil price (Yahoo Finance, FRED `DCOILWTICO`, or equivalent). Computation: gold price / oil price. **Cross-reference note:** This indicator is also scored in `fiscal_dominance_arithmetic`. See INTERACTION_MATRIX.md Shared Upstream Cause Warning "Gold/monetary-premium indicators." The indicator legitimately appears in both modules but with different causal interpretations — monetary_architecture interprets it as evidence of collateral substitution; fiscal_dominance_arithmetic interprets it as evidence of debasement recognition. The double-counting discount is applied at the composition layer, not the scoring layer. | Ratio above 25 (vs. historical average ~16–20) AND rising on trailing 12-month basis | above and rising | 0.18 | The gold/oil ratio measures the monetary premium on gold above its commodity value. When gold buys more barrels of oil than the historical average, the market is assigning reserve-asset status beyond what physical supply/demand justifies. Rising ratio means the monetary premium is expanding — more participants are treating gold as a monetary reserve, not just a commodity. |
| Cross-currency basis swap stress episodic | EUR/USD and JPY/USD 3-month cross-currency basis | **web-search** — Requires Bloomberg terminal or specialized data provider. No freely available real-time API. Preferred source: Bloomberg `EURUSD3M XCCY` and `JPYUSD3M XCCY`. Alternative: central bank financial stability reports (lagged). This is the most technically demanding indicator in the registry. | 3-month EUR/USD or JPY/USD basis more negative than -30bp during non-crisis periods, OR episodic spikes to -50bp+ | widening (more negative) | 0.12 | The basis measures the cost of obtaining dollars via FX swaps. Deeply negative basis = dollar scarcity in global plumbing. Persistent or episodic widening during non-crisis periods indicates structural tightness (not 2008-style systemic panic but architectural strain). Each plumbing episode forces Fed intervention, which temporarily resolves the stress but adds to the evidence that the current architecture is fragile. |
| Non-dollar trade settlement growing | SWIFT RMB Tracker, bilateral trade settlement data | **web-search** — SWIFT publishes its RMB Tracker monthly. Bilateral settlement volumes require news/research sources and central bank reports. Preferred sources: SWIFT monthly reports, PBOC cross-border RMB reports, bilateral trade agreement announcements. | RMB share of global payments above 4% AND/OR non-dollar energy settlement visible and growing in volume | rising | 0.17 | The settlement layer of the transition. Bilateral agreements (China-Saudi, China-Brazil, India-Russia, UAE-India) enable trade outside the dollar system — volumes are harder to measure but directionally growing. Each transaction that bypasses the dollar is a small reduction in structural dollar demand. This indicator is specific to monetary_architecture — not shared with other theories' activation tables. |

**Total weight: 1.00** (0.29 + 0.24 + 0.18 + 0.12 + 0.17 = 1.00)

---

## activation_thresholds

| Status | Score Range | Interpretation |
|--------|------------|----------------|
| **Active** | ≥ 0.60 | The collateral regime transition is underway with clear, sustained empirical evidence across multiple indicators. |
| **Adjacent** | 0.30–0.59 | Some indicators suggest transition dynamics but evidence is partial, mixed, or too early to confirm. |
| **Inactive** | < 0.30 | No meaningful evidence of collateral regime transition. The existing Treasury-centric architecture is stable and unchallenged. |

---

## context_flags

Supplementary qualitative flags. NOT scored mechanically. Surfaced to the generator for contextual enrichment.

| Flag | Source | Data Ownership | What to Look For |
|------|--------|----------------|------------------|
| Sanctions weaponization | Web search: US/EU sanctions developments | **qualitative** | New sanctions involving reserve asset freezes applied to sovereign entities within the trailing 24 months. Each new episode reinforces diversification incentive. If sanctions contract or are reversed, diversification pressure eases. *Reclassified from scored indicator (original weight 0.10) because no mechanical data feed exists — requires editorial judgment on whether new sanctions are "escalation."* |
| Institutional thesis adoption | Web search: BIS papers, IMF reserve reports, large asset manager research | **qualitative** | Major institutional research explicitly discussing collateral regime transition, gold's reserve role, or "Bretton Woods III" framework. Recognition by reserve managers accelerates the transition (reflexive loop: recognition → allocation → buying → price impact → further recognition). *Reclassified from scored indicator (original weight 0.05) because the threshold is inherently judgment-based.* |
| Gold repatriation activity | Web search: central bank gold repatriation announcements | **qualitative** | Central banks moving physical gold from London/New York vaults to domestic vaults. The strongest possible signal of distrust in the existing custodial arrangement. Each repatriation is a central bank saying: "I don't trust that I can access my gold when stored abroad." |
| BRICS+ payment infrastructure | Web search: BRICS payment system, mBridge, New Development Bank | **qualitative** | Progress on alternative payment infrastructure (mBridge CBDC bridge, BRICS payment network). If an alternative to the dominant settlement network becomes operational with meaningful volume, the monopoly of dollar-denominated settlement infrastructure is directly challenged. Currently pre-operational but under active development. |
| Gold-backed sovereign instruments | Web search: gold bonds, gold-denominated trade instruments | **qualitative** | Any sovereign issuing gold-backed or gold-referenced financial instruments. Would represent formalization of gold's return to the monetary system. Currently hypothetical but consistent with the theory's endpoint prediction. |
| Plumbing state | Cross-currency basis levels, repo rate behaviour, Fed facility usage | **web-search / computed-mechanical** | Binary state: **calm** (no basis events, no repo spikes, no new facilities in trailing 12 months) vs. **stressed** (basis widening, repo volatility, new/expanded Fed facilities). This is NOT a phase — the theory remains single-phase. It is a supplementary state descriptor that informs tactical timing in TACTICAL.md and PLAYBOOK.md. A transition from "calm" to "stressed" is a tactical signal (buying opportunity), not an activation change. |

---

## falsifier_severity_assignments

Severity classifications for all falsifiers defined in CORE.md (deep_falsifiers) and state-level falsifiers defined below. Canonical severity discounts: minor = 0.10, medium = 0.25, major = 0.45.

### Deep Falsifiers (from CORE.md)

| ID | Condition | Classification | Severity | Notes |
|----|-----------|---------------|----------|-------|
| H1 | CB gold buying reverses to sustained net selling 3+ years | **hard** | Theory-killing — forces Inactive | No discount applied. Triggers full deactivation. |
| H2 | US sanctions framework dismantled or credibly constrained | **hard** | Theory-killing — forces Inactive | No discount applied. Triggers full deactivation. |
| H3 | Gold reserve share declines 5+ years through selling | **hard** | Theory-killing — forces Inactive | No discount applied. Triggers full deactivation. |
| H4 | Plumbing stress ceases 5+ years, no new Fed facilities | **hard** | Theory-killing — forces Inactive | No discount applied. Triggers full deactivation. Specifically tests the plumbing-stress sub-thesis. |
| S1 | RMB fails to develop as reserve alternative | **soft** | **minor** (0.10) | Changes endpoint composition but actually concentrates diversification demand on gold. Core gold thesis slightly strengthens. |
| S4 | Digital asset achieves zero-counterparty-risk reserve adoption | **soft** | **minor** (0.10) | Currently entirely hypothetical. No existing or proposed design achieves the required properties. |

### State-Level Falsifiers

These test whether the activation conditions hold at their current strength, distinct from whether the theory itself is correct.

| ID | Condition | Metric | Threshold | Severity | Implication |
|----|-----------|--------|-----------|----------|-------------|
| S3 | US fiscal situation improves substantially | Federal deficit, interest/receipts ratio (web-search: CBO, Treasury data) | Deficit below $800B for 4+ consecutive quarters AND interest/receipts ratio declining | **medium** (0.25) | Removes the DOMESTIC demand source for gold as a debasement hedge. The international demand (CB reserve diversification from monetary_architecture) continues independently, but one of the two structural demand sources weakens. The double-sourced bid becomes a single-sourced bid. |
| S5 | Major geopolitical de-escalation reduces sanctions risk | US-China relations, US-Russia relations, sanctions rollback (web-search: geopolitical developments) | Comprehensive de-escalation sustained for 3+ years, including sanctions rollback | **medium** (0.25) | Reduces the URGENCY of reserve diversification without reversing it. The 2022 precedent cannot be fully un-learned even with de-escalation, but the pace of buying slows. Transition continues at reduced speed. |

---
