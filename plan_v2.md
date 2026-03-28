# plan_v2.md — Falsification Engine v2 Implementation Plan

## What Exists (v1 — complete)

The following pipeline is built and working end-to-end:

- 8 theory modules parsed and scored mechanically (activation engine)
- Data agent fetching FRED + Yahoo Finance into structured briefing packets
- Generation prompt producing 7-9 hypotheses per run
- Elimination prompt with mechanical falsifier audit (CLEAR / TRIGGERED / UNTESTABLE)
- Three-stage conviction scoring: mechanical Stage 1 inputs (support_strength, evidence_quality, convergence, falsifier_clarity) → Stage 2 discounts (soft falsifier, UNTESTABLE, theory-aware overlap) → Stage 3 gates
- Conviction floor at 5/10
- Consolidation check preventing redundant hypotheses
- React frontend: Ledger, Hypothesis Detail, Trades, Observatory, Pipeline, Briefing, About views
- Hermes Editorial design system (Cormorant Garamond / EB Garamond / JetBrains Mono, cream/brick/olive/gold)
- GitHub Pages static publishing: snapshot endpoint bakes all data into window.__SNAPSHOT__, publish script deploys to gh-pages branch via temp directory. Read-only mode auto-detected by frontend (HashRouter, API interception from snapshot).
- About page: 12-step pipeline description grouped into 5 sections with architectural premise, continuous CSS counter

**Current output quality:** 4 survived, 3 killed (all by horizon gate, not weak raw scores). Conviction range 6-8 for survivors. Horizon gate is dominant kill mechanism — debt_cycle_long hypotheses with 9-12 month timeframes capped at 2-4/10 despite raw scores of 6.5-8.5. Stage 2 inputs serialized losslessly. Mechanical scores producing 4.5x wider differentiation than LLM self-evaluation.

---

## v2 Scope — Four Features

### Feature 1: Trade Tracker

**Goal:** Record live trades linked to hypotheses, track P&L, and see how conviction level correlates with actual performance over time.

**This is NOT a portfolio optimizer.** It tracks individual trades in isolation — entry, exit, and which hypothesis justified the trade. The user decides sizing and timing. The system tracks outcomes.

**Design principle:** Backend stores primitives only. All derived values (P&L, days held, notional, performance stats) are computed at render time by the frontend. The backend has no concept of "current price" — it only knows what you paid and what you sold for.

#### Data Model (primitives only)

```python
class Trade(Base):
    __tablename__ = "trades"

    id: str                          # "T-2026-001"
    hypothesis_id: str               # FK to hypothesis that justified this trade
    run_id: str                      # which pipeline run was current at entry

    # Primitives
    ticker: str                      # e.g., "GLD"
    direction: str                   # "LONG" or "SHORT"
    entry_date: str                  # ISO date
    entry_price: float               # price at entry
    shares: float                    # number of shares/units
    conviction_at_entry: float       # conviction score when trade was opened

    # Exit (null until closed)
    exit_date: str | None
    exit_price: float | None
    exit_reason: str | None          # "hypothesis_killed" | "target_reached" | "stop_hit" | "manual" | "expired"

    # Status
    status: str                      # "OPEN" | "CLOSED"

    # Hypothesis snapshot at entry (denormalized for historical record)
    hypothesis_short_name: str
    hypothesis_theory: str
    hypothesis_status_at_entry: str  # SURVIVED / WOUNDED
```

#### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/trades` | All trades. Query: `status=OPEN\|CLOSED`, `ticker`, `hypothesis_id` |
| POST | `/api/trades` | Open a new trade. Requires: ticker, direction, entry_price, shares, hypothesis_id |
| PATCH | `/api/trades/{id}` | Close trade (sets exit_price, exit_date, exit_reason, status=CLOSED). No P&L computation. |
| GET | `/api/prices?tickers=GLD,SPY` | Fetch current prices via Yahoo Finance. Returns `{ticker: price}` dict. Stores nothing. |

No `/api/trades/refresh` — the frontend calls `/api/prices` directly and computes P&L.
No `/api/trades/performance` — the frontend computes win rate, avg return, etc. from the trade list.

#### Frontend — Trade View (all computation client-side)

New tab in NavBar: **TRADES** -- insert between LEDGER and OBSERVATORY. Final nav order: LEDGER | TRADES | OBSERVATORY | PIPELINE | BRIEFING.

> **Design note:** Journal removed from navigation. Its audit trail function is redundant -- Hypothesis Detail shows per-hypothesis lifecycle events, Pipeline Run shows per-run operational logs. No user workflow requires a cross-hypothesis activity feed as a separate view.

On mount: fetch trades via GET `/api/trades`, then call GET `/api/prices` with all OPEN trade tickers.

**Computed per-trade at render time:**
- `notional = entry_price * shares`
- `unrealized_pnl = (current_price - entry_price) * shares * direction_sign`
- `unrealized_pct = (current_price - entry_price) / entry_price * direction_sign`
- `days_held = today - entry_date` (or exit_date - entry_date for closed)
- For CLOSED trades: same math using exit_price instead of current_price

**Performance summary** (computed client-side): open P&L, total notional, win rate, W/L, avg return by conviction tier.

**REFRESH PRICES button** just re-calls `/api/prices` and re-renders. No backend writes.

**Layout:**

```
┌──────────────────────────────────────────────────────────────────┐
│  OPEN TRADES                       [REFRESH PRICES] [+ NEW TRADE] │
├──────────────────────────────────────────────────────────────────┤
│  Ticker  Dir   Entry    Current   P&L      %      Days  Conv  Hyp │
│  GLD     LONG  $295.40  $298.10   +$810   +0.91%   3    7    H-05 │
│  RSP     LONG  $168.20  $169.50   +$390   +0.77%   3    6    H-03 │
│  SPY     SHORT $641.00  $638.20   +$840   +0.44%   3    6    H-03 │
│  SHY     LONG  $82.15   $82.30    +$75    +0.18%   3    5    H-02 │
├──────────────────────────────────────────────────────────────────┤
│  CLOSED TRADES                                                    │
│  [empty — no closed trades yet]                                   │
├──────────────────────────────────────────────────────────────────┤
│  PERFORMANCE                                                      │
│  Open P&L: +$2,115  |  Win Rate: —  |  Avg by Conv 7: —  |  6: — │
└──────────────────────────────────────────────────────────────────┘
```

**New Trade form** (modal):
- Hypothesis selector (dropdown of active survived/wounded hypotheses)
- Auto-populates: ticker options (from hypothesis predicted_assets), direction
- User enters: entry_price, shares
- System records: conviction_at_entry, hypothesis snapshot

**Hypothesis Detail integration:** Add a "TRADES" section at the bottom of the hypothesis detail overlay showing all trades linked to that hypothesis. For OPEN trades, shows "Use Trades view to refresh prices" since live prices are only fetched on the Trades view.

---

### Feature 2: Newsletter Prompt Builder

**Goal:** One-click assembly of a structured prompt for newsletter generation. The user copies the prompt into Claude.ai, gets the newsletter there, and can iterate conversationally.

**Design note:** Newsletter follows the same operational pattern as the rest of the pipeline: backend assembles the prompt, frontend presents it for copy-paste into Claude chat. No API calls from the backend. This keeps the system as a prompt engine, not an inference engine, and lets the user leverage their Claude Max subscription (free, with web search) instead of paying per API call.

#### Architecture

```
[GENERATE NEWSLETTER] button on Ledger view
        ↓
GET /api/newsletter/prompt
        ↓
Backend assembles system_prompt + user_prompt from:
  - SURVIVED hypotheses with conviction >= 6 from latest run
  - Active theory names + activation scores
  - Briefing summary from latest run
  - UNTESTABLE falsifiers across qualifying hypotheses
        ↓
Frontend displays two-section overlay with [COPY] buttons
        ↓
User pastes system prompt into Claude project instructions,
    user prompt as a message, iterates in Claude chat
```

#### API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/newsletter/prompt` | Assemble system + user prompts from latest run |

Returns:
```json
{
  "system_prompt": "...",
  "user_prompt": "..."
}
```

Returns 400 if no hypotheses meet conviction >= 6 threshold.

No Newsletter DB model. No storage. No caching. No history. Every click regenerates from the latest run data.

#### Frontend

- **Button:** "GENERATE NEWSLETTER" on Ledger view header, right side of controls bar. `--accent-brick` background, cream text, JetBrains Mono 11px uppercase. Only visible when at least 1 SURVIVED hypothesis has conviction >= 6.
- **Overlay:** Full-screen modal (720px max-width), same backdrop pattern as HypothesisDetail.
- **Section 1: SYSTEM PROMPT** — label in Cormorant Garamond 14px, content in JetBrains Mono 11px `--text-secondary`, scrollable pre block, own [COPY] button.
- **Section 2: USER PROMPT** — same layout, `--text-primary`, own [COPY] button.
- **Top bar:** [COPY ALL] copies both sections as one block, [CLOSE] closes overlay.
- **States:** Loading ("Assembling prompt..."), Error (accent-negative), Success (two prompt sections).
- No print button. No storage. No caching. No history.

---

### Feature 3: Mechanize Horizon Alignment + Expression Efficiency

**Goal:** Remove the last two LLM-assigned values from the conviction pipeline. After this, the entire scoring system is zero-LLM.

#### 3A. Horizon Alignment (H)

**What it measures:** Does the hypothesis timeframe match the 1-3 month holding period?

**Computation:**

```python
def compute_horizon_alignment(hypothesis_timeframe: str) -> float:
    """
    Parse the hypothesis timeframe string and compute overlap
    with the ideal 30-90 day holding window.
    
    Returns 0.0 - 1.0
    """
    # Parse timeframe to approximate days
    # Patterns: "Through Q3 2026", "Next 6-8 weeks", "1-3 months", 
    #           "By June 2026", "Within 30 days"
    
    end_date = parse_timeframe(hypothesis_timeframe)
    hypothesis_days = (end_date - today).days
    
    # Ideal window: 30-90 days
    IDEAL_MIN = 30
    IDEAL_MAX = 90
    
    if IDEAL_MIN <= hypothesis_days <= IDEAL_MAX:
        return 1.0  # Perfect fit
    elif hypothesis_days < IDEAL_MIN:
        return hypothesis_days / IDEAL_MIN  # Too short — wastes holding period
    else:
        # Too long — diminishing returns past 90 days
        return IDEAL_MAX / hypothesis_days  # 180 days → 0.50, 360 days → 0.25
```

**Hardcode the 30-90 day window.** This is a personal system with a known investment style.

#### 3B. Expression Efficiency (E)

**What it measures:** Can this hypothesis be traded cleanly through liquid ETFs?

**Computation:**

```python
# ETF liquidity tiers (hardcoded)
TIER_1 = {"SPY", "QQQ", "GLD", "TLT", "SHY", "IEF", "HYG", "LQD", 
           "EEM", "VWO", "DBC", "XLE", "XLF", "IWM", "TIP", "UUP"}  # >$500M daily volume
TIER_2 = {"RSP", "XLU", "XLP", "XLY", "XLK", "EWZ", "EWY", "FXI", 
           "STIP", "XOP", "MDY", "JETS", "ITB", "VEA"}               # >$50M daily volume
TIER_3 = set()  # everything else in ETF_UNIVERSE

def compute_expression_efficiency(predicted_assets: list[dict]) -> float:
    """
    Score based on:
    1. Coverage: what fraction of assets are in our ETF universe
    2. Liquidity: weighted by tier
    3. Directness: fewer assets = cleaner expression
    """
    tickers = [a["ticker"] for a in predicted_assets]
    n = len(tickers)
    
    # Coverage: all in universe?
    in_universe = sum(1 for t in tickers if t in ETF_UNIVERSE)
    coverage = in_universe / n if n > 0 else 0
    
    # Liquidity weighting
    tier_scores = []
    for t in tickers:
        if t in TIER_1: tier_scores.append(1.0)
        elif t in TIER_2: tier_scores.append(0.75)
        elif t in ETF_UNIVERSE: tier_scores.append(0.50)
        else: tier_scores.append(0.0)
    liquidity = sum(tier_scores) / n if n > 0 else 0
    
    # Directness: 1/sqrt(n) — 1 asset=1.0, 2=0.71, 4=0.50
    directness = 1.0 / (n ** 0.5) if n > 0 else 0
    
    # Weighted combination
    return coverage * 0.30 + liquidity * 0.40 + directness * 0.30
```

#### Integration

- Both functions go in `conviction.py` alongside `compute_mechanical_conviction_inputs()`
- Stage 3 gates use these mechanical values instead of LLM-assigned H and E
- Gate thresholds remain: H < 0.40 caps conviction at 4, E < 0.30 caps at 3
- Store LLM values as `llm_horizon_alignment` and `llm_expression_efficiency` for audit comparison

#### After this change: the entire conviction pipeline is zero-LLM.

```
LLM does: generate hypotheses, attack hypotheses, check falsifiers against data
Math does: activation scoring, conviction scoring (all 6 dimensions), overlap penalty, 
           UNTESTABLE discount, gates, floor
```

---

### Feature 4: About Page

**Goal:** A single page in the app showing exactly what the system does mechanically, in 10 bullet points. No philosophy, no "why" — just "what."

**Navigation:** New link in the app header (not a main tab). Small "ABOUT" text link, right-aligned.

**Content (exactly these 10 bullets, rendered in Hermes Editorial typography):**

```
WHAT THIS SYSTEM DOES

 1. Parses 8 economic theory modules into structured activation
    conditions, predictions, and falsifier sets.

 2. Fetches 22+ macro data series (FRED, Yahoo Finance) and computes
    derived metrics (net liquidity, ERP, yield curves, relative performance).

 3. Scores theory activation mechanically: weighted indicator sum against
    current data, producing Active / Adjacent / Inactive per theory.

 4. Generates candidate hypotheses via LLM using only Active theory
    mechanisms and current data. Consolidates redundant hypotheses.

 5. Attacks each hypothesis via LLM falsifier audit: every pre-registered
    hard and soft falsifier checked against data. Status: CLEAR, TRIGGERED,
    or UNTESTABLE.

 6. Applies mechanical kill rules: hard falsifier trigger = killed,
    2+ major soft falsifiers = killed, 3+ any soft falsifiers = killed.

 7. Scores conviction mechanically (zero LLM): support strength from
    activation score, evidence quality from mechanical data coverage ratio
    (excludes qualitative/web-search indicators from denominator), convergence
    from 30-day price alignment, falsifier clarity from verification ratio.

 8. Applies Stage 2 discounts: soft falsifier severity discount (multiplicative),
    UNTESTABLE uncertainty discount, theory-aware overlap penalty (same-theory
    penalized, cross-theory convergence bonused).

 9. Applies Stage 3 gates: horizon alignment from timeframe parsing,
    expression efficiency from ETF universe coverage and liquidity tier.
    Conviction floor at 5/10.

10. Presents surviving hypotheses ranked by conviction with full audit trail:
    every score, every falsifier, every discount visible and traceable.
```

**Design:** Full-width page, generous whitespace, numbered list in EB Garamond 15px, numbers in JetBrains Mono. No graphics, no diagrams. The text is the design.

---

## Build Order

| Priority | Feature | Estimated Hours | Dependencies |
|----------|---------|----------------|--------------|
| 1 | Feature 3: Mechanize H + E | 1.5 | None (pure backend) |
| 2 | Feature 1: Trade Tracker | 3.0 | None |
| 3 | Feature 4: About Page | 0.5 | Feature 3 (content references zero-LLM pipeline) |
| 4 | Feature 2: Newsletter Prompt Builder | 1.0 | None (prompt assembly only) |

**Total: ~7.5 hours**

Feature 3 goes first because it completes the mechanical pipeline — everything after it can reference "zero-LLM conviction scoring" as a fact. Feature 1 is the most user-facing value. Feature 4 is trivial once the pipeline is finalized. Feature 2 is last but trivial — it's just prompt assembly, no API integration needed.

---

## Suggested Initial Trades (from run R-20260328-084910)

To be entered via the Trade Tracker once Feature 1 is built:

| Trade | Ticker | Direction | Hypothesis | Conviction | Sizing Logic |
|-------|--------|-----------|------------|------------|-------------|
| 1 | GLD | LONG | H-05 Gold resumes uptrend | 7 | Largest — highest conviction, zero UNTESTABLE, clean single-asset |
| 2 | RSP | LONG | H-03 RSP outperforms SPY | 6 | Medium — pair leg 1, breadth rotation |
| 3 | SPY | SHORT | H-03 RSP outperforms SPY | 6 | Medium — pair leg 2, hedges beta |
| 4 | SHY | LONG | H-02 SHY beats SPY | 5 | Smallest — cash parking, 2 UNTESTABLE falsifiers |

Entry prices: use next market open. The system does not generate entry signals — the conviction score tells you relative sizing, not timing.
