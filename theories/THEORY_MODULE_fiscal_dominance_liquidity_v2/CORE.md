# CORE.md — Fiscal Dominance: Net Liquidity Transmission

*Theory Package: `fiscal_dominance_liquidity`*
*Stability Class: cyclical*
*Last updated: April 2026*

---

## theory_id

`fiscal_dominance_liquidity`

---

## core_claim

When fiscal deficit spending injects reserves into the financial system faster than the central bank can drain them, net liquidity becomes the dominant driver of asset prices and monetary policy becomes subordinate. The fiscal channel overwhelms the monetary channel: rate hikes become paradoxically stimulative because higher interest expense on existing government debt widens the deficit, which injects more reserves, which supports asset prices. This condition persists until an exogenous shock breaks it — genuine fiscal consolidation, a productivity boom, or a deflation shock.

---

## causal_mechanism

1. The government runs a fiscal deficit large enough to exceed the central bank's reserve-draining pace. This is an exogenous political outcome. The central bank does not control it.

2. To fund the deficit, Treasury issues bonds. Bond proceeds flow into the Treasury General Account (TGA) at the Fed. This step temporarily drains reserves from the banking system.

3. Treasury spends the proceeds — paying contractors, transfer payments, interest on existing debt, federal salaries. This step injects reserves back into the banking system. The net effect of issuance plus spending: reserves increase by approximately the deficit amount, because spending exceeds tax receipts by definition of deficit.

4. Simultaneously, the central bank runs quantitative tightening — allowing bonds to mature without reinvesting, shrinking its balance sheet. This drains reserves.

5. The critical arithmetic: if the deficit pace exceeds the QT drainage rate, net reserves in the system expand despite QT. This is fiscal dominance in its simplest form — the fiscal channel overwhelms the monetary channel.

6. Net liquidity rises. Net liquidity (Fed balance sheet minus TGA minus reverse repo facility) captures the actual usable reserves in the financial system after subtracting reserves locked in government accounts or parked at the Fed.

7. Rising net liquidity flows into asset prices. Banks and financial institutions with excess reserves seek yield — buying risk assets, extending credit, funding levered positions. The transmission is mechanical: more reserves chasing a finite set of assets.

8. Rate hikes become paradoxically stimulative: higher rates increase interest expense on outstanding government debt, which widens the deficit, which increases Treasury issuance, which injects more reserves when spent, which raises net liquidity, which supports asset prices. The central bank is running on a treadmill that accelerates as it runs faster. *Note: this module describes the interest-expense feedback only insofar as it sustains near-term reserve injection and net liquidity transmission. The standalone debt-sustainability question, interest-to-receipts arithmetic, and multi-year devaluation trajectory belong to `fiscal_dominance_arithmetic`.*

9. The feedback loop: higher asset prices generate higher capital gains tax receipts (partially offsetting the deficit, but not enough), produce a wealth effect that supports consumption, and prevent the economic slowdown that would allow rate cuts. Interest expense stays high. The deficit stays wide. The loop sustains itself until an exogenous shock breaks it.

### What net liquidity actually measures

Net liquidity is an accounting identity, not a theoretical construct:

**Net Liquidity = Federal Reserve Balance Sheet − Treasury General Account − Reverse Repo Facility**

Each component captures a distinct reserve pool: the Fed balance sheet measures total reserves created, the TGA measures reserves temporarily locked in government cash holdings, and the reverse repo facility measures reserves voluntarily parked at the Fed by money market funds. The formula captures reserves actually available to the financial system — not those locked away. It has been the strongest single-variable predictor of broad risk-asset direction since 2020.

### Time horizon

**Primary:** 1–6 months. Net liquidity changes transmit to asset prices with a lag of days to weeks. This is the most tactically relevant theory in the registry.

**Secondary:** The conditions that sustain fiscal dominance (deficit pace, political unwillingness to consolidate, demographic spending pressures) operate on a 3–10 year horizon. The structural conditions are slow-moving; the flow-through to markets is rapid.

---

## scope_limits

1. This module covers the flow mechanism and near-term asset-price transmission of fiscal dominance. The standalone debt-sustainability question, interest-to-receipts arithmetic, and multi-year devaluation trajectory belong to `fiscal_dominance_arithmetic`. The two modules can have different activation statuses — the liquidity transmission can be inactive (temporary fiscal consolidation) while the arithmetic trajectory remains untenable.

2. Net liquidity predicts direction, not timing. A net-liquidity-driven rally can pause or dip on any given month's TGA build or short-term noise. This theory supports "asset prices are directionally supported while net liquidity expands" — not a specific percentage move in a specific quarter.

3. This theory does not predict the end of fiscal dominance. That is an exogenous political event. The theory tells you what happens while fiscal dominance is active, not when it ends.

4. The RRP drain from its peak toward zero is a one-time tailwind that cannot repeat. Once the RRP buffer is exhausted, one component of the net liquidity expansion formula is permanently removed. The theory's transmission mechanism persists, but one amplifier is spent.

5. This theory applies to the US fiscal and monetary system. The specific transmission mechanism (deficit → Treasury issuance → reserve injection → asset prices) depends on the institutional structure of the Fed, Treasury, and money markets. It does not generalize directly to other sovereign systems without adaptation.

---

## key_assumptions

1. **Deficit spending creates reserves when spent.** The Treasury issuance → TGA → spending → bank reserves transmission chain is mechanical and operates as described by reserve accounting. This is an accounting identity, not a behavioral assumption.

2. **Excess reserves flow into asset prices.** Financial institutions with surplus reserves seek yield by purchasing risk assets, extending credit, and funding leveraged positions. This behavioral assumption rests on the profit motive of banks and financial institutions, which is durable but not universal — reserves can sit idle if risk appetite collapses (the 2008–2010 experience, where excess reserves accumulated without flowing to risk assets because the banking system was impaired).

3. **The fiscal deficit is large enough relative to QT to produce net expansion.** The theory is only operative when the fiscal injection exceeds the monetary drainage. Below that threshold, standard monetary dominance applies.

4. **The central bank cannot or will not offset the fiscal channel.** If the Fed were to accelerate QT or shrink its balance sheet faster than Treasury injects reserves, fiscal dominance would break. The assumption is that political and institutional constraints prevent the Fed from escalating to match the fiscal impulse — and that the interest-expense feedback loop makes escalation self-defeating.

5. **Asset price correlation with net liquidity persists.** The theory assumes the mechanical relationship between rising reserves and rising asset prices continues. If this correlation breaks (see deep falsifiers), the theory's predictive power is lost even if the reserve accounting remains valid.

---

## deep_falsifiers

These conditions would kill the theory itself — not a specific hypothesis derived from it.

| ID | Condition | Logic |
|----|-----------|-------|
| DF1 | Net liquidity contracts for a sustained period despite a deficit large enough to exceed QT drainage | The core mechanism test. If net liquidity contracts even when the fiscal injection arithmetically exceeds monetary drainage, the reserve transmission chain is broken. Possible causes: structural changes in how reserves circulate, TGA behavior permanently diverging from spending patterns, or institutional plumbing changes that trap reserves outside the financial system. If the mechanism does not transmit, the theory's causal chain fails at its most fundamental step. |
| DF2 | Rate hikes produce sharp economic contraction despite sustained fiscal spending at scale | The paradox test. If the economy contracts sharply (rising unemployment, deeply contractionary ISM) despite fiscal spending at a level that arithmetically exceeds QT drainage, then monetary transmission is still dominant. The fiscal impulse is insufficient to override monetary tightening. This falsifies the core claim that the fiscal channel overwhelms the monetary channel. The deficit must be sufficiently large when recession occurs — if the deficit has already shrunk below the dominance threshold, the theory is not falsified; the precondition was simply removed. |
| DF3 | Sustained decorrelation between net liquidity and asset prices across varied market conditions | If net liquidity expands persistently but asset prices do not follow — across multiple macro environments (rate hiking, rate cutting, risk-on, risk-off) — then the transmission from reserves to asset prices is misspecified. The reserve accounting may still be valid, but the theory's predictive claim (net liquidity drives asset prices) is broken. Temporary decorrelation during narrative-driven markets or single-factor overrides does not qualify; sustained decorrelation across varied conditions does. |

---

## stability_class

**Cyclical.** The structural conditions enabling fiscal dominance (high deficit, political unwillingness to consolidate) toggle on multi-year political and economic cycles. The theory can be active for several years and inactive for several years. It is not tactical (the conditions do not change quarter to quarter when operative) and not persistent (fiscal consolidation or structural economic shifts can remove the preconditions).

---

## revision_triggers

These would require revising the invariant theory, not just recalibrating thresholds:

1. **Reserve accounting changes.** If the institutional plumbing changes such that the Net Liquidity = Fed BS − TGA − RRP formula no longer captures usable reserves (e.g., a new facility or institutional structure creates a fourth significant reserve pool), the formula and the mechanism it describes require revision.

2. **Structural change in reserve-to-asset transmission.** If evidence accumulates that excess reserves no longer flow to asset prices even under normal banking conditions (not crisis conditions where the transmission is temporarily impaired, but a durable structural shift), the causal chain from step 6 to step 7 requires revision.

3. **Interest-expense feedback loop breaks.** If higher rates no longer widen the deficit (e.g., because the government issues predominantly floating-rate or very-short-duration debt that matures before interest costs compound, or because tax receipts grow faster than interest expense due to a productivity revolution), the paradoxical stimulation mechanism in step 8 needs revision.

4. **New dominant driver of asset prices.** If a force emerges that persistently overwhelms net liquidity as the primary driver of risk-asset direction (and this is not a temporary override but a structural regime change), the theory's core predictive claim requires revision.

---
