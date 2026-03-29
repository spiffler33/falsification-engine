# plan_v4.md — Falsification Engine v4 Implementation Plan

## Enhancement 2: Sector Falsifier Appendices

### Design Principle (inherited from v3, extended)

**Do not suppress detection. Do not mechanize interpretation too early. Mechanize the scoring of interpretations afterward.**

v4 extension: **Tighten the falsifier mesh at the expression level without bloating the generation layer.** Sector appendices are evaluator weapons — they enter the pipeline at Pass 3 to attack hypotheses with sector-specific falsifiers that are tighter and more testable than theory-level falsifiers alone. They do not enter Pass 2. The generator's job is theory-driven hypothesis construction; sector data does not shape what gets generated, it shapes what survives.

---

## What Exists (v1 + v2 + v3 — all complete or in build)

The full pipeline through v3:

```
Pass 1:   Activation scoring — 8 modules scored independently → Active / Adjacent / Inactive
Pass 1.5: Regime annotation — compute_regime_flags() from activation results → active flags list
Pass 2:   LLM generation — active theories + regime flag context + channel requirement → 7-9 hypotheses with channel tags
Pass 3:   LLM elimination — adversarial attack + channel verification → SURVIVED / WOUNDED / KILLED + corrected channels
Pass 4:   Mechanical conviction scoring (zero-LLM):
            Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
            Stage 2: DISCOUNTED = RAW × D_f × D_o × D_r  →  SCORE = DISCOUNTED × 10
            Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap)  →  max(FINAL, 5.0)
Pass 5:   Human decision layer — system never recommends trades or sizes
```

v3 adds regime flags (Pass 1.5), resolution channel tagging (Pass 2–3), and channel-regime alignment scoring (D_r in Pass 4 Stage 2). See plan_v3.md for full specification.

---

## The Problem v4 Solves

Theory-level falsifiers are necessary but insufficient. They attack the economic theory; they do not attack the specific trade expression derived from that theory.

Example: A hypothesis says "RSP outperforms SPY over 2 months as breadth rotation continues." The theory-level falsifier is "CAPE falls below 22." That falsifier attacks the *valuation mean reversion theory* — it does not attack the *breadth rotation mechanism* that the hypothesis depends on.

A tighter falsifier: "If Mag 7 earnings growth re-accelerates above 25% YoY while rest-of-S&P is flat, concentration is justified by fundamentals, not passive flows — the breadth rotation thesis loses its catalyst."

Sector falsifier appendices close this gap. They provide the evaluator with sector-specific, threshold-based falsification conditions and qualitative attack vectors that directly target the hypothesis's load-bearing mechanism at the expression level.

---

## What v4 Adds

### 1. Sector Appendix Documents

Three standalone reference documents, one per sector. These are NOT theory modules. They have no activation conditions, no causal chains, no predictions. They are structured attack ammunition for the evaluator.

### 2. Conditional Injection into Pass 3

After Pass 2 generates hypotheses, the system scans the hypothesis set for sector-relevant ETF tickers. Only appendices whose tickers appear in the generated hypotheses are injected into the Pass 3 elimination prompt. Appendices for sectors not touched by any hypothesis are excluded entirely.

### 3. Structured Sector Falsifier Audit Trail

The evaluator produces a structured output for each sector falsifier it checks, including the data lookup result, the triggered/not-triggered determination, and — critically — a stated relevance determination with reasoning for whether the triggered falsifier actually attacks the specific hypothesis under evaluation.

### 4. Sector Falsifier Discounts in D_f

Triggered AND relevant sector falsifiers compound into the existing soft falsifier discount pipeline (D_f) using the same severity mechanics (minor = 0.10, medium = 0.25, major = 0.45). No separate sector-confidence dimension.

---

## Component 1: Sector Appendix Schema

Each sector appendix is a structured document with the following interface:

```python
SECTOR_APPENDIX = {
    "sector_id": "tech_ai",          # Unique identifier
    "display_name": "Technology / AI Concentration",
    "version": 1,
    "last_updated": "2026-03-29",
    "update_cadence": "quarterly (post-earnings) + event-driven",

    # TICKER TRIGGERS — which ETF tickers cause this appendix to load
    # When any hypothesis from Pass 2 mentions one of these tickers
    # (in its expression, prediction, or asset field), the appendix
    # is injected into the Pass 3 elimination prompt.
    "ticker_triggers": ["QQQ", "SMH", "XLK", "SOXX"],

    # MECHANICAL FALSIFIERS — structured, severity-tagged, threshold-based
    # The evaluator looks up the data and compares to the threshold.
    # The severity is pre-registered at design time — the evaluator
    # does not adjust it. The evaluator DOES determine relevance
    # to each specific hypothesis (see Evaluator Output Contract below).
    "mechanical_falsifiers": [
        {
            "falsifier_id": "tech_sf_01",
            "condition": (
                "Semiconductor inventory-to-sales ratio rises above 1.5x, "
                "indicating cyclical overshoot in the AI infrastructure buildout"
            ),
            "metric": "Semiconductor inventory-to-sales ratio (SIA or WSTS data)",
            "threshold": 1.5,
            "direction": "above",
            "severity": "medium",    # 0.25 discount if triggered AND relevant
            "data_source": "web_search"
        }
        # ... additional falsifiers
    ],

    # EVALUATOR ATTACK VECTORS — qualitative, prose-based
    # The evaluator investigates these during Pass 3.
    # They inform the evaluator's judgment on SURVIVED / WOUNDED / KILLED
    # but do NOT produce numeric severity discounts.
    # They may cause the evaluator to change a hypothesis status
    # from SURVIVED to WOUNDED, or to flag concerns in the audit trail,
    # but they do not feed into D_f.
    "evaluator_attack_vectors": [
        {
            "vector_id": "tech_av_01",
            "question": (
                "Is Mag 7 earnings growth driven by revenue growth or by "
                "cost-cutting and buybacks? If the latter, the concentration "
                "justification is fragile — earnings quality is low."
            ),
            "what_to_search": (
                "Latest quarterly earnings for MSFT, GOOGL, AMZN, META, AAPL, "
                "NVDA, TSLA — revenue growth vs. earnings growth, buyback programs"
            ),
            "kill_condition": (
                "If 4+ of the Mag 7 show earnings growth exceeding revenue growth "
                "by 10%+ and buyback yield exceeds 3%, the earnings quality concern "
                "is material — flag as WOUNDED with reasoning"
            )
        }
        # ... additional vectors
    ],

    # METADATA
    "metadata": {
        "parent_theories": [
            "structural_fragility",
            "valuation_mean_reversion"
        ],
        "notes": (
            "This appendix targets hypotheses about tech concentration, "
            "AI infrastructure buildout, and narrow market breadth. "
            "It is most relevant when structural_fragility Phase A is "
            "Active and the hypothesis expression involves QQQ, SMH, or XLK."
        )
    }
}
```

### Schema Rules

1. **Ticker triggers are exhaustive and closed.** If a ticker is not in the list, the appendix does not load for hypotheses involving that ticker. Adding a ticker requires a deliberate decision.

2. **Mechanical falsifiers must have numeric thresholds.** If you cannot write `if X > Y then severity = Z`, it is not a mechanical falsifier — it belongs in evaluator attack vectors. No exceptions.

3. **Severity tags are fixed at design time.** The evaluator does not adjust severity. It determines (a) whether the threshold is breached (triggered) and (b) whether the triggered falsifier is relevant to the specific hypothesis. It does not second-guess the severity classification.

4. **Evaluator attack vectors do not produce numeric scores.** They inform the evaluator's qualitative judgment (SURVIVED / WOUNDED / KILLED) but they do not flow into D_f. They are weapons, not scorecards.

5. **Data source is declared honestly.** Most sector metrics require web search. The `data_source` field distinguishes between `data_agent` (available in the FRED/Yahoo briefing packet) and `web_search` (the evaluator must look it up during Pass 3). This informs the evaluator prompt about what to search for.

---

## Component 2: Appendix Injection Logic

### When Appendices Load

After Pass 2 generates 7-9 hypotheses, the system scans for sector-relevant tickers:

```python
def select_sector_appendices(hypotheses: list[dict], appendices: list[dict]) -> list[dict]:
    """
    Scan generated hypotheses for ETF tickers that match sector appendix triggers.
    Return only the appendices whose tickers appear in the hypothesis set.

    A hypothesis "mentions" a ticker if the ticker appears in any of:
      - hypothesis.expression (e.g., "LONG QQQ, SHORT SPY")
      - hypothesis.assets (if structured)
      - hypothesis.prediction text (e.g., "SMH declines 20%")

    Input:  hypotheses from Pass 2, all registered sector appendices
    Output: list of appendices to inject into Pass 3 prompt
    """
    # Collect all tickers mentioned across all hypotheses
    mentioned_tickers = set()
    for h in hypotheses:
        mentioned_tickers.update(extract_tickers(h))

    # Match against appendix trigger lists
    selected = []
    for appendix in appendices:
        if mentioned_tickers.intersection(set(appendix["ticker_triggers"])):
            selected.append(appendix)

    return selected
```

### What Gets Injected

The Pass 3 elimination prompt receives the selected appendices as an additional section. The injection is conditional — if no sector appendices are selected, the section is omitted entirely.

```
--- SECTOR FALSIFIER APPENDICES ---

The following sector-specific falsifiers are available for hypotheses
that involve the listed ETFs. For each hypothesis that touches a sector,
you MUST:

1. Look up the current value of each mechanical falsifier's metric
2. Determine if the threshold is breached (TRIGGERED or NOT TRIGGERED)
3. If TRIGGERED: determine if the falsifier is RELEVANT to this specific
   hypothesis — does it attack the hypothesis's load-bearing mechanism?
4. State your reasoning for the relevance determination
5. Report the result in the structured format specified below

You must also investigate the evaluator attack vectors and incorporate
your findings into your qualitative assessment of the hypothesis.

{for each selected appendix:}

SECTOR: {display_name}
Applies to hypotheses involving: {ticker_triggers}

MECHANICAL FALSIFIERS:
{for each falsifier:}
  [{falsifier_id}] {condition}
  Metric: {metric}
  Threshold: {threshold} ({direction})
  Severity if triggered AND relevant: {severity}
  Data source: {data_source}

EVALUATOR ATTACK VECTORS:
{for each vector:}
  [{vector_id}] {question}
  Search for: {what_to_search}
  Kill condition: {kill_condition}

--- END SECTOR APPENDICES ---
```

---

## Component 3: Evaluator Output Contract for Sector Falsifiers

This is the critical addition. The evaluator must produce structured output for each sector falsifier check. This output is the audit trail that the scorer reads.

### Structured Output Format

For each hypothesis that touches a sector with an active appendix, the evaluator reports:

```
SECTOR FALSIFIER AUDIT: {hypothesis_id}
Sector: {sector_id}

  [{falsifier_id}]
  Metric value found: {current value from web search}
  Triggered: YES | NO
  Relevant to this hypothesis: YES | NO | N/A (if not triggered)
  Reasoning: {1-2 sentences explaining WHY this falsifier does or does
              not attack the hypothesis's load-bearing mechanism}
  Severity applied: {severity} | NONE

  [{falsifier_id}]
  ...

ATTACK VECTOR FINDINGS: {hypothesis_id}
  [{vector_id}] {summary of what was found, 1-2 sentences}
  Impact on hypothesis: {how this finding affects the SURVIVED/WOUNDED/KILLED determination}
```

### Definition of Relevance

A triggered sector falsifier is **relevant** to a hypothesis if and only if:

> **The falsifier is adverse to the hypothesis's load-bearing mechanism** — meaning the condition identified by the falsifier, if true, would weaken, undermine, or contradict the specific causal pathway that the hypothesis depends on for its predicted outcome.

The test is directional and specific:

- The evaluator asks: "If this falsifier condition is true, does it attack the mechanism THIS hypothesis needs to work?"
- If the hypothesis predicts "RSP outperforms SPY via breadth rotation" and the triggered falsifier is "semiconductor inventory overshoot," the evaluator must determine whether semiconductor inventory conditions actually threaten the breadth rotation mechanism — not just whether they are bad for the tech sector in general.
- A triggered falsifier that is bad for the sector but does not attack the specific hypothesis mechanism is NOT relevant. Example: high semiconductor inventory is bad for SMH, but if the hypothesis is "QQQ declines because fiscal liquidity is withdrawn" (a liquidity hypothesis using a tech ETF), the semiconductor inventory falsifier does not attack the liquidity withdrawal mechanism. It is triggered but not relevant.

### What the Scorer Reads

The mechanical conviction scorer in Pass 4 reads the structured audit output. It applies the pre-registered severity discount if and only if BOTH conditions are met:

```python
def apply_sector_falsifier_discounts(
    hypothesis_id: str,
    sector_audit: list[dict],
    current_d_f: float
) -> float:
    """
    Read the evaluator's sector falsifier audit for this hypothesis.
    Apply severity discounts for falsifiers that are BOTH triggered AND relevant.
    Compound multiplicatively with existing D_f (theory-level soft falsifiers).

    Returns updated D_f.
    """
    for entry in sector_audit:
        if entry["triggered"] == "YES" and entry["relevant"] == "YES":
            severity = entry["severity_applied"]
            discount = SEVERITY_DISCOUNTS[severity]  # minor=0.10, medium=0.25, major=0.45
            current_d_f *= (1.0 - discount)

    return current_d_f
```

The scorer does NOT read attack vector findings. Those are qualitative inputs that the evaluator uses to determine SURVIVED / WOUNDED / KILLED status, but they do not produce numeric discounts.

### Four Non-Negotiable Requirements

1. **Structured evaluator output.** The sector falsifier audit is a first-class structured output, not prose buried in the evaluation narrative. It uses the format specified above. The scorer parses it mechanically.

2. **Stated reasoning for relevance.** Every relevance determination (YES or NO) includes 1-2 sentences explaining why the triggered falsifier does or does not attack the hypothesis's load-bearing mechanism. This is the audit trail. Without it, the relevance determination is a black box.

3. **Relevance defined as adverse to the load-bearing mechanism.** The evaluator does not ask "is this bad for the sector?" It asks "does this attack the specific causal pathway this hypothesis depends on?" The definition is precise: the falsifier must be adverse to the hypothesis's load-bearing mechanism.

4. **Scorer acts only on triggered=YES AND relevant=YES.** Neither condition alone produces a discount. A falsifier that is triggered but not relevant to the hypothesis is reported but not scored. A falsifier that is relevant but not triggered is not scored. Both gates must pass.

---

## Component 4: Sector Appendix Content — Technology / AI Concentration

**sector_id:** `tech_ai`
**ticker_triggers:** `["QQQ", "SMH", "XLK", "SOXX"]`
**update_cadence:** Quarterly (post-earnings for Mag 7 and TSMC) + event-driven (major AI policy, chip export controls)

### Mechanical Falsifiers

| ID | Condition | Metric | Threshold | Dir | Severity | Source |
|----|-----------|--------|-----------|-----|----------|--------|
| `tech_sf_01` | Semiconductor inventory-to-sales ratio indicates cyclical overshoot in AI infrastructure buildout | SIA or WSTS semiconductor inventory-to-sales ratio | 1.5x | above | medium | web_search |
| `tech_sf_02` | Mag 7 collective earnings growth re-accelerates, justifying concentration by fundamentals rather than passive flows | Mag 7 aggregate YoY earnings growth (latest quarter) | 25% YoY | above | major | web_search |
| `tech_sf_03` | Hyperscaler capex-to-identifiable-AI-revenue ratio shows spending is justified, not speculative | Combined capex of MSFT+GOOGL+AMZN+META vs. identifiable AI revenue outside hyperscalers | 5x | below | major | web_search |
| `tech_sf_04` | AI revenue outside hyperscalers reaches critical mass, resolving the capex/revenue mismatch fragility | Annualized AI-related revenue outside hyperscalers (enterprise SaaS AI, AI infrastructure companies ex-hyperscalers) | $150B | above | major | web_search |
| `tech_sf_05` | TSMC monthly revenue growth decelerates, indicating semiconductor demand peak | TSMC monthly revenue YoY growth (3-month trailing average) | Below 10% | below | minor | web_search |

**Note on tech_sf_02:** This falsifier fires when Mag 7 earnings growth is STRONG (above 25%). It is a falsifier of BEARISH tech hypotheses — the ones that predict concentration unwinding or tech underperformance. If Mag 7 earnings justify the premium, the fragility thesis is weakened. The evaluator must assess relevance directionally: this falsifier attacks hypotheses predicting tech weakness, not hypotheses predicting tech strength.

**Note on tech_sf_03 and tech_sf_04:** These two falsifiers address the same underlying fragility (capex/revenue mismatch) from opposite directions. tech_sf_03 triggers when the ratio contracts (spending justified), tech_sf_04 triggers when absolute AI revenue reaches critical mass. Both are major severity because the capex/revenue mismatch is the primary fragility vector for AI concentration hypotheses.

### Evaluator Attack Vectors

| ID | Question | What to Search | Kill Condition |
|----|----------|---------------|----------------|
| `tech_av_01` | Is Mag 7 earnings growth driven by revenue growth or by cost-cutting and buybacks? If the latter, concentration justification is fragile. | Latest quarterly earnings for Mag 7 — revenue growth vs. EPS growth, buyback programs, cost restructuring | If 4+ of Mag 7 show EPS growth exceeding revenue growth by 10%+ and buyback yield above 3%, earnings quality concern is material — flag WOUNDED |
| `tech_av_02` | Are chip export restrictions escalating in ways that compress semiconductor demand outside China while benefiting domestic substitution? | Latest US-China chip export controls, TSMC/Samsung/Intel capacity allocation, China domestic chip production data | If new export restrictions materially reduce TAM for leading-edge chips, the semiconductor demand thesis shifts — assess impact on SMH-specific hypotheses |
| `tech_av_03` | Is the QQQ/IWM ratio compressing or expanding? Direction matters for breadth rotation hypotheses. | QQQ vs IWM relative performance over 1M, 3M, 6M; RSP vs SPY relative performance | If QQQ/IWM ratio is expanding (large-cap outperformance accelerating), breadth rotation hypotheses are swimming upstream — flag WOUNDED |

---

## Component 5: Sector Appendix Content — Energy

**sector_id:** `energy`
**ticker_triggers:** `["XLE", "XOP", "OIH", "USO", "DBC"]`
**update_cadence:** Monthly (EIA data, rig counts) + quarterly (earnings) + event-driven (OPEC+ decisions, geopolitical)

### Mechanical Falsifiers

| ID | Condition | Metric | Threshold | Dir | Severity | Source |
|----|-----------|--------|-----------|-----|----------|--------|
| `energy_sf_01` | US crude oil inventories build significantly above seasonal norms, indicating demand weakness or oversupply | EIA weekly crude oil inventory vs. 5-year seasonal average | 20% above seasonal average for 4+ consecutive weeks | above | medium | web_search |
| `energy_sf_02` | US oil rig count rises sharply, indicating capex discipline is breaking and supply response is underway | Baker Hughes US oil rig count | Above 600 AND rising for 8+ weeks | above | medium | web_search |
| `energy_sf_03` | Energy sector capex/cash flow ratio rises, indicating the capex discipline thesis (bullish for energy equities) is weakening | Aggregate capex-to-operating-cash-flow ratio for top 10 US E&P companies | 0.60x | above | medium | web_search |
| `energy_sf_04` | Crack spreads collapse, indicating refining margin compression that weakens integrated energy equity earnings | 3-2-1 crack spread (RBOB gasoline + ULSD minus 3x WTI) | Below $15/bbl sustained for 4+ weeks | below | minor | web_search |
| `energy_sf_05` | WTI crude falls to a level that challenges the economics of marginal US production | WTI crude oil spot price | $50/bbl | below | major | web_search |

### Evaluator Attack Vectors

| ID | Question | What to Search | Kill Condition |
|----|----------|---------------|----------------|
| `energy_av_01` | Is OPEC+ cohesion holding or are members cheating on quotas? Quota violations above 500K bpd indicate the cartel's pricing power is eroding. | Latest OPEC+ production data vs. agreed quotas, compliance rates by member, any scheduled meeting outcomes | If aggregate overproduction exceeds 500K bpd for 2+ months, supply discipline thesis is wounded |
| `energy_av_02` | Is US strategic petroleum reserve being refilled or drained? SPR policy affects both supply/demand balance and government fiscal position. | SPR inventory levels, announced purchase/sale plans, current fill rate | SPR drawdowns of 10M+ barrels in a quarter shift near-term supply dynamics |
| `energy_av_03` | Is natural gas pricing divergence (US HH vs. international LNG) creating or destroying value for US LNG exporters? | Henry Hub spot vs. JKM/TTF LNG pricing, US LNG export capacity utilization | Sustained HH-international convergence weakens the US energy export advantage thesis |

---

## Component 6: Sector Appendix Content — Financials

**sector_id:** `financials`
**ticker_triggers:** `["XLF", "KRE", "KBE"]`
**update_cadence:** Quarterly (bank earnings, FDIC data, SLOOS) + event-driven (regulatory changes, bank failures)

### Mechanical Falsifiers

| ID | Condition | Metric | Threshold | Dir | Severity | Source |
|----|-----------|--------|-----------|-----|----------|--------|
| `financials_sf_01` | CRE delinquency rate rises to levels indicating systemic stress in regional bank portfolios | FDIC quarterly CRE delinquency rate (all commercial banks) | 6% | above | major | web_search |
| `financials_sf_02` | Net interest margins compress to levels that challenge bank profitability across the sector | FDIC aggregate net interest margin (all FDIC-insured institutions) | 2.5% | below | medium | web_search |
| `financials_sf_03` | Major bank loan loss provisions surge, indicating expected credit deterioration | Aggregate quarterly loan loss provisions for top 6 US banks (JPM, BAC, WFC, C, GS, MS) | Provisions increase 50%+ QoQ | above | medium | web_search |
| `financials_sf_04` | Regional bank deposit outflows accelerate, indicating renewed flight-to-quality or structural deposit migration | KRE constituent aggregate deposit change (quarterly) | Deposits declining 3%+ QoQ for 2+ consecutive quarters | below | major | web_search |
| `financials_sf_05` | Bank P/TBV for money-center banks rises above historical average, removing the valuation discount thesis | Aggregate P/TBV for top 6 US banks | 1.3x | above | major | web_search |

**Note on financials_sf_05:** This falsifier fires when bank valuations are NOT cheap. It attacks bullish financial sector hypotheses that depend on the "banks are undervalued" thesis. If P/TBV is above 1.3x, the valuation discount that drives `valuation_mean_reversion` sector rotation hypotheses toward financials has closed.

### Evaluator Attack Vectors

| ID | Question | What to Search | Kill Condition |
|----|----------|---------------|----------------|
| `financials_av_01` | Is the divergence between money-center and regional banks widening or narrowing? This determines whether financial sector hypotheses should be expressed via XLF (broad) or KRE/KBE (targeted). | JPM/BAC stock performance vs. KRE index, earnings divergence, deposit flow divergence | If money-center banks are outperforming regionals by 15%+ over 3 months, a broad XLF hypothesis is masking a split sector — flag for expression refinement |
| `financials_av_02` | Are SLOOS lending standards tightening or easing? Direction matters more than level for credit cycle positioning. | Latest Fed Senior Loan Officer Survey results across all loan categories | If SLOOS shows tightening across 3+ categories for 2+ consecutive quarters, credit contraction is underway — assess whether hypothesis accounts for this |
| `financials_av_03` | Are unrealized losses on bank bond portfolios (HTM and AFS) improving or deteriorating? This is the latent risk that drove SVB. | FDIC quarterly data on unrealized losses in bank securities portfolios | If unrealized losses exceed $500B and are concentrated in regional banks with <$100B assets, the KRE-specific risk is elevated regardless of headline NIM data |

---

## Conviction Pipeline Reference (v4)

The pipeline is unchanged from v3 except for the source of D_f inputs:

```
Pass 1:   Activation scoring — 8 modules scored independently → Active / Adjacent / Inactive
Pass 1.5: Regime annotation — compute_regime_flags() from activation results → active flags list
Pass 2:   LLM generation — active theories + regime flag context + channel requirement → 7-9 hypotheses with channel tags
Pass 3:   LLM elimination — adversarial attack + channel verification + SECTOR FALSIFIER AUDIT → SURVIVED / WOUNDED / KILLED + corrected channels + sector audit trail
Pass 4:   Mechanical conviction scoring (zero-LLM):
            Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
            Stage 2: DISCOUNTED = RAW × D_f × D_o × D_r  →  SCORE = DISCOUNTED × 10
            Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap)  →  max(FINAL, 5.0)
Pass 5:   Human decision layer — system never recommends trades or sizes
```

### D_f Computation (v4)

D_f now compounds theory-level AND sector-level soft falsifier discounts:

```python
def compute_d_f(
    theory_soft_falsifiers: list[dict],
    sector_audit: list[dict]
) -> float:
    """
    Compute the total soft falsifier discount for a hypothesis.

    Sources:
    1. Theory-level soft falsifiers (from theory modules, checked in Pass 3)
    2. Sector-level mechanical falsifiers (from sector appendices, checked in Pass 3)

    Both use the same severity scale:
      minor  = 0.10 discount  →  multiplier 0.90
      medium = 0.25 discount  →  multiplier 0.75
      major  = 0.45 discount  →  multiplier 0.55

    Compounding is multiplicative. Order does not matter.
    """
    d_f = 1.0

    # Theory-level discounts (unchanged from v2)
    for f in theory_soft_falsifiers:
        if f["status"] == "TRIGGERED":
            d_f *= (1.0 - SEVERITY_DISCOUNTS[f["severity"]])

    # Sector-level discounts (new in v4)
    # BOTH conditions must be met: triggered AND relevant
    for entry in sector_audit:
        if entry["triggered"] == "YES" and entry["relevant"] == "YES":
            d_f *= (1.0 - SEVERITY_DISCOUNTS[entry["severity_applied"]])

    return d_f
```

### Effect on Conviction Scores (illustrative)

| Scenario | RAW | Theory D_f | Sector D_f | Combined D_f | D_o | D_r | SCORE | FINAL |
|----------|-----|-----------|-----------|-------------|-----|-----|-------|-------|
| Clean — no falsifiers triggered | 0.80 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8.0 | 8 |
| Theory minor only | 0.80 | 0.90 | 1.00 | 0.90 | 1.00 | 1.00 | 7.2 | 7 |
| Theory minor + sector medium | 0.80 | 0.90 | 0.75 | 0.675 | 1.00 | 1.00 | 5.4 | 5 |
| Theory major + sector medium | 0.75 | 0.55 | 0.75 | 0.4125 | 1.00 | 1.00 | 3.1 | 5 (floor) |
| Sector medium, triggered but NOT relevant | 0.80 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 8.0 | 8 |

The last row is critical: a triggered-but-not-relevant sector falsifier produces NO discount. The relevance gate protects hypotheses from false penalization.

---

## Data Model Changes

### Hypothesis (additions to existing model)

```python
# New field on hypothesis object
sector_appendices_applied: str | None   # JSON array of sector_ids checked, e.g. '["tech_ai"]'
```

### Sector Falsifier Audit (new model)

```python
# New table: sector_falsifier_audit
# One row per falsifier check per hypothesis
class SectorFalsifierAudit:
    hypothesis_id: str          # FK to hypothesis
    sector_id: str              # e.g. "tech_ai"
    falsifier_id: str           # e.g. "tech_sf_01"
    metric_value_found: str     # What the evaluator looked up, e.g. "1.6x"
    triggered: str              # "YES" | "NO"
    relevant: str               # "YES" | "NO" | "N/A"
    reasoning: str              # 1-2 sentences: why relevant or not
    severity_applied: str       # "minor" | "medium" | "major" | "NONE"
    run_id: str                 # FK to pipeline run
```

### Pipeline Run (additions to existing model)

```python
# New field on run metadata (in addition to v3's regime_flags_active)
sector_appendices_loaded: str   # JSON array of sector_ids injected into Pass 3, e.g. '["tech_ai", "energy"]'
```

---

## Build Order

| Priority | Component | Description | Status |
|----------|-----------|-------------|--------|
| 1 | Sector appendix schema | Python constants for 3 sector appendices (tech_ai, energy, financials) | DONE |
| 2 | Appendix injection logic | `select_sector_appendices()` — scan hypotheses for tickers, return matching appendices | DONE |
| 3 | Evaluator prompt update | Append sector falsifier section to Pass 3 prompt, conditional on appendices selected | DONE |
| 4 | Evaluator output parser | Parse structured sector falsifier audit from evaluator response into `SectorFalsifierAudit` records | DONE |
| 5 | D_f integration | Update `compute_d_f()` to compound sector falsifier discounts alongside theory-level discounts | DONE |
| 6 | Data model migration | Add `sector_appendices_applied` to hypothesis; create `sector_falsifier_audit` table; add `sector_appendices_loaded` to run | DONE |
| 7 | Frontend: sector audit display | Show sector falsifier audit on hypothesis detail view (triggered/relevant status, reasoning) | DONE |

### Implementation Notes for Claude Code

- **Priority 1 is pure data/config.** Three Python dictionaries following the schema above. No logic, no UI. Just constants.
- **Priority 2 is a pure function.** Input: list of hypotheses + list of appendices. Output: filtered list of appendices. Ticker extraction is string matching against a known set.
- **Priority 3 is a prompt text change.** The sector falsifier section is appended conditionally to the elimination prompt. Same pattern as v3's regime flag injection — text is included only when appendices are selected.
- **Priority 4 is a parser.** The evaluator's structured output (the `SECTOR FALSIFIER AUDIT` block) must be parsed into `SectorFalsifierAudit` records. This is string parsing with known delimiters — same pattern as the existing falsifier status parser.
- **Priority 5 is a single loop** added to the existing `compute_d_f()` function. Same multiplicative compounding pattern. The only new logic is the two-gate check: `triggered == YES` AND `relevant == YES`.
- **Priority 6 is a DB migration.** Same pattern as v2/v3 migrations — ALTER TABLE to add columns, CREATE TABLE for the audit table, idempotent.
- **Priority 7 is display-only.** The sector audit appears as a collapsible section on the hypothesis detail card. Each audit entry shows: falsifier condition, metric value found, triggered status, relevant status, reasoning, severity applied. Green/amber/red color coding for triggered×relevant status.

### Testing Checklist

- [x] `select_sector_appendices()` returns empty list when no hypotheses mention sector tickers
- [x] `select_sector_appendices()` returns tech appendix when a hypothesis mentions QQQ
- [x] `select_sector_appendices()` returns multiple appendices when hypotheses mention tickers from different sectors
- [x] `select_sector_appendices()` does not return an appendix when its tickers are not mentioned
- [x] Evaluator prompt includes sector falsifier section only when appendices are selected
- [x] Evaluator prompt omits sector falsifier section entirely when no appendices selected
- [x] Evaluator produces structured audit output in the specified format (tested via parser round-trip)
- [x] Parser correctly extracts triggered, relevant, severity_applied from audit output
- [x] `compute_d_f()` applies no discount when triggered=YES but relevant=NO
- [x] `compute_d_f()` applies no discount when triggered=NO (regardless of relevance)
- [x] `compute_d_f()` applies correct severity discount when triggered=YES AND relevant=YES
- [x] `compute_d_f()` compounds theory-level and sector-level discounts multiplicatively
- [x] Conviction floor at 5.0 still applies after combined discounts
- [x] `SectorFalsifierAudit` records are persisted with full audit trail
- [x] Run metadata records which sector appendices were loaded
- [x] Hypothesis records which sector appendices were applied

### Post-Implementation Verification (2026-03-29)

Full E2E pipeline test passed: 33 integration checks + 61 unit tests (42 sector appendices + 8 conviction sector + 11 migration).

Key verification points:
- QQQ + XLE hypotheses correctly select tech_ai + energy appendices (not financials)
- Elimination prompt includes only matched sector sections
- Parser extracts all 4 audit entries from simulated evaluator output
- D_f compounding: theory minor (0.90) x sector major (0.55) = 0.495 confirmed
- Triggered-but-NOT-relevant falsifier produces zero discount (D_f stays 1.0)
- Conviction floor kills at 2/10 when combined discounts drag score below 5
- Audit records persist to SQLite and round-trip through the API correctly
- GitHub Pages snapshot includes sector audit data via `_model_to_dict()`

### Learnings

1. **Two-gate check is load-bearing.** The triggered-AND-relevant gate prevents over-penalization. Without it, any sector ETF hypothesis would eat discounts from tangentially related conditions (e.g., semiconductor inventory vs. fiscal liquidity thesis using QQQ). The relevance gate delegates contextual judgment to the evaluator while keeping the math mechanical.

2. **Parser dual-path (JSON + text) is resilient.** Supporting both structured JSON and text-block parsing means the system handles both clean LLM output and messy free-text output. JSON takes precedence; text fills gaps. No duplicates on merge.

3. **Multiplicative compounding is severe by design.** A theory minor + sector major yields D_f = 0.495, nearly halving the score. This is intentional -- the system is a falsification engine. Evidence against should bite hard. The conviction floor at 5.0 is the backstop.

4. **Extensibility is trivial.** Adding a new sector requires only a new Python dict in `sector_appendices.py` and adding it to `SECTOR_APPENDICES`. No pipeline, prompt builder, parser, or frontend changes needed -- everything discovers appendices dynamically.

---

## What v4 Does NOT Include (explicit exclusions)

1. **No sector data in Pass 2 generation.** Sector appendices are evaluator weapons. They do not shape hypothesis generation. The generator works from theory modules and regime context only.

2. **No sector-specific activation conditions.** Sectors do not activate or deactivate. The appendices are passive reference documents that load when tickers appear in hypotheses.

3. **No separate sector confidence score.** Sector falsifiers compound into the same D_f pipeline as theory-level falsifiers. There is no new scoring dimension.

4. **No healthcare, real estate, or utilities appendices.** Three sectors for v1 (tech, energy, financials). Additional sectors added when live output demonstrates that the falsifier mesh is too loose for hypotheses touching those sectors.

5. **No changes to the copy-paste execution model.** Sector appendix content is injected into the elimination prompt as text. No API integration, no separate model calls. Everything within a single Claude chat context window.

6. **No evaluator severity adjustment.** The evaluator determines triggered/relevant. It does not adjust severity. Severity is fixed at design time and registered in the appendix definition.

7. **No channel-relevance filtering on sector falsifiers.** The relevance determination is made by the evaluator based on the hypothesis's load-bearing mechanism, not by matching channel tags. A triggered falsifier is relevant if it attacks the hypothesis mechanism, regardless of channel.

---

## Sector Appendix Maintenance

### Update Cadence

| Sector | Primary Trigger | Secondary Trigger | Typical Frequency |
|--------|----------------|-------------------|-------------------|
| Tech / AI | Mag 7 quarterly earnings, TSMC monthly revenue | Chip export policy changes, AI regulation | Quarterly + event-driven |
| Energy | EIA weekly data, Baker Hughes rig count | OPEC+ decisions, geopolitical events | Monthly + event-driven |
| Financials | Major bank quarterly earnings, FDIC quarterly data | SLOOS releases, regulatory changes, bank failures | Quarterly + event-driven |

### What Gets Updated

- **Threshold values** — recalibrate when market structure changes (e.g., if the semiconductor industry's normal inventory-to-sales ratio shifts due to structural demand changes, the 1.5x threshold may need adjustment).
- **Severity classifications** — only when live output demonstrates that a severity level is consistently too harsh or too lenient. This is a calibration decision, not a per-run judgment.
- **New falsifiers** — added when live output reveals a hypothesis attack surface that existing falsifiers don't cover. Same principle as theory module refinement.
- **Retired falsifiers** — removed when the underlying condition becomes permanently irrelevant (e.g., a one-time regulatory event passes).

### What Does NOT Get Updated Per Run

- Severity is not adjusted per run. It is a design-time decision.
- Relevance is not pre-cached. It is determined fresh by the evaluator for each hypothesis in each run.
- Thresholds are not dynamic. They are static between explicit recalibration decisions.

---

## Relationship to Existing Plan Documents

- **plan.md** — original architecture. Superseded by plan_v2.md.
- **plan_v2.md** — the working system (activation, generation, elimination, conviction scoring, frontend). Still the foundation.
- **plan_v3.md** — regime flags, resolution channels, channel-regime alignment scoring. Extends plan_v2.md.
- **plan_v4.md** (this document) — sector falsifier appendices. Extends plan_v3.md. Does not modify any v2 or v3 component except to add sector falsifier inputs to the D_f computation.

All four documents are cumulative. The system implements all of them.
