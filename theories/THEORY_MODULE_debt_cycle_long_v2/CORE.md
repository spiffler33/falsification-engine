# debt_cycle_long — CORE.md

*Invariant Theory — audited by reading, thinking, markets*
*Stability class: persistent*

---

## theory_id

`debt_cycle_long`

---

## core_claim

The economy accumulates debt across successive short-term credit cycles, with each cycle's trough requiring lower interest rates and each recovery starting from a higher debt base. When total debt relative to income reaches levels where conventional monetary policy (rate cuts) is exhausted, authorities must escalate to unconventional tools — first quantitative easing (MP2), then fiscal-monetary coordination (MP3). This escalation is a one-way ratchet: each tool, once deployed at scale, cannot be fully withdrawn without destabilising the system that has grown to depend on it. The late stage of this cycle changes the rules governing recessions, recoveries, bond markets, and inflation — dynamics learned during the early-to-mid cycle no longer apply.

---

## causal_mechanism

The mechanism operates through seven linked steps:

1. **The ratchet.** Each short-term debt cycle ends with total debt higher than before. Recoveries work by creating more credit, not by deleveraging. The new cycle begins from a higher base. Debt/GDP rose from ~130% in the early 1980s to ~180% by 2000 to ~240% by 2008 to ~270% by 2025.

2. **The rate floor descends.** Each cycle's trough interest rate is lower than the previous one because more debt requires lower rates to make debt service manageable. The 1982 trough was ~6%; the 1992 trough was ~3%; the 2003 trough was ~1%; the 2009 and 2020 troughs were 0%. The trend is deterministic: more debt requires lower rates. When rates hit zero, the primary tool (MP1: rate adjustment) is exhausted.

3. **MP1 exhaustion forces MP2.** At the zero lower bound, the central bank escalates from changing the price of money to changing its quantity. Quantitative easing — purchasing bonds to inject reserves — lowers long-term rates through term premium compression, forces investors into risk assets through portfolio balance effects, and signals aggressive accommodation. MP2 works but with diminishing effectiveness: each successive QE programme must be larger to produce the same marginal impact because the starting balance sheet is larger.

4. **MP2 limitations force MP3.** Balance sheet expansion injects reserves into the financial system but does not reliably transmit to the real economy — the "pushing on a string" problem. Asset prices inflate while consumer spending, wages, and real GDP growth remain sluggish. The gap between asset price inflation and real-economy stagnation widens wealth inequality and generates political pressure for direct fiscal spending.

5. **MP3 arrives.** The government borrows and spends directly into the economy while the central bank accommodates — keeping rates low enough that the government can finance the spending without a bond market crisis. MP3 works: it produces real-economy stimulus, real-economy inflation, and real-economy growth. Its problem is sustainability — it creates the fiscal dominance dynamics captured by other modules in this registry.

6. **MP3 creates the endgame tension.** Once deployed at scale, the central bank faces a dilemma: fight inflation (raise rates, which worsens fiscal arithmetic through higher interest expense — paradoxically stimulative) or accommodate inflation (hold rates below inflation, enabling financial repression — real wealth transfer from savers/bondholders to government/debtors). Both paths lead to real devaluation; the question is speed.

7. **Resolution.** Long-term debt cycles have historically resolved through one of two paths: (a) orderly financial repression — sustained negative real rates for 10-15 years, inflation 3-8% with rates capped at 2-3%, debt/GDP gradually declines, painful for bondholders but manageable for society; or (b) disorderly crisis — authorities fail to deploy tools fast enough, deflationary deleveraging cascades, eventually resolved by large-scale fiscal intervention and currency devaluation.

---

## scope_limits

1. **Does not predict timing of resolution.** Historical resolutions took 9-16 years. Japan has been in the late stage for 30+ years with no resolution. The timeline is genuinely uncertain.
2. **Does not produce near-term trade signals.** Operates on a 10-30 year horizon. Its value is as a structural modifier of other theories' predictions, not as a standalone source of monthly positioning.
3. **Calibrated primarily to the US long-term debt cycle.** Cross-referenced with UK (1940s-1970s), Japan (1990s-present), and select EM episodes, but thresholds are US-specific and may not transfer cleanly to other sovereign contexts.
4. **Does not predict the specific resolution path.** Both orderly repression and Japan-style stagnation are consistent with late-cycle diagnosis. The theory identifies structural conditions; it does not determine which resolution materialises.
5. **Does not replace fiscal dominance modules.** The long cycle explains WHY fiscal dominance emerges (MP1/MP2 exhaustion forces MP3). The fiscal dominance modules quantify HOW it operates (liquidity flows, arithmetic constraints). This module provides structural context; it does not duplicate operational detail.

---

## key_assumptions

1. **Debt ratchet is irreversible absent extraordinary events.** Voluntary deleveraging from debt/GDP above 250% has no historical precedent in a major economy. The ratchet holds because the political cost of austerity exceeds the political cost of further borrowing.
2. **Policy tools escalate but do not reverse.** Once MP2 is deployed at scale, the balance sheet cannot return to pre-deployment levels without destabilising the financial system. Once MP3 is deployed, the political constituency for deficit spending prevents consolidation.
3. **Rate sensitivity increases with debt level.** As total debt/GDP rises, the economy becomes more sensitive to interest rate changes — small rate increases produce large changes in aggregate debt service, constraining the central bank's ability to fight inflation without causing fiscal distress.
4. **The zero lower bound is gravitational.** In the late long-term cycle, rates may be temporarily elevated, but each crisis pulls them back toward zero with increasing speed. The speed of return to ZLB is evidence that MP1's capacity is structurally limited.
5. **Political systems converge on fiscal expansion in the late cycle.** Wealth inequality generated by decades of asset price inflation creates political pressure for fiscal redistribution from both left-populist and right-populist directions. The fiscal expansion is politically determined, not merely a policy choice.

---

## deep_falsifiers

These conditions would kill the theory itself — not a hypothesis derived from it. Severity assignments are in ACTIVATION.md.

| # | Condition | Logic |
|---|-----------|-------|
| H1 | Total debt/GDP declines below 200% through organic deleveraging — actual debt reduction or GDP growth, not inflation reducing real debt — sustained for 4+ quarters | If the economy genuinely deleverages, the late-cycle dynamics ease. Below 200%, conventional monetary policy has more room to operate and the escalation ratchet reverses. No precedent for voluntary achievement at current debt levels in any major economy. |
| H2 | Real GDP growth above 4% sustained for 5+ years (20+ consecutive quarters) | A genuine productivity revolution changes the denominator fast enough to improve debt/GDP organically — the economy grows out of the debt rather than inflating it away. MP1 becomes sufficient again because income generation exceeds debt service at normal rates. The US has not achieved this since the 1960s. |
| H3 | Next recession is resolved by MP1 alone — rate cuts only, no QE restart or balance sheet expansion, no fiscal stimulus exceeding $500B, economy recovers within 18 months | The escalation thesis predicts each successive crisis requires larger intervention. If the next recession resolves cleanly with rate cuts alone, the escalation pattern is broken and MP1 still works at current debt levels. |

---

## stability_class

**persistent** — The late-stage long-term debt cycle is a multi-decade structural condition. The US has been above 250% debt/GDP since 2008 and above 200% since the early 2000s. Toggling to Inactive would require resolution of the debt overhang, which historically takes 10-20 years. Unlikely to change within 5 years.

---

## revision_triggers

1. A genuinely novel monetary transmission mechanism (e.g., CBDC-enabled direct stimulus) that changes the MP1→MP2→MP3 escalation logic by creating effective intermediate tools between rate policy and fiscal coordination.
2. Evidence that the debt ratchet has reversed in a major economy without crisis — voluntary, sustained deleveraging through growth or austerity without financial system instability.
3. A theoretical framework that explains the post-2008 period equally well without reference to long-term debt accumulation dynamics — an alternative explanation for why policy tools escalated, why rates gravitate toward zero, and why each intervention is larger than the last.
