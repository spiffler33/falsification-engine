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
- React frontend: Ledger, Hypothesis Detail, Journal, Observatory, Pipeline, Briefing views
- Hermes Editorial design system (Cormorant Garamond / EB Garamond / JetBrains Mono, cream/brick/olive/gold)

**Current output quality:** Conviction range 5-7 with 2-point spread, mechanical scores producing 4.5x wider differentiation than LLM self-evaluation, UNTESTABLE classification working, overlap penalty differentiating redundancy from convergence.

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

New tab in NavBar: **TRADES** (between JOURNAL and OBSERVATORY).

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

### Feature 2: Newsletter Generator

**Goal:** One-click generation of a single A4 page newsletter showing highest-conviction trades and their justification. Uses the Anthropic API (claude-sonnet-4-20250514) to produce crisp prose from structured hypothesis data.

#### Architecture

```
[GENERATE NEWSLETTER] button on Ledger view
        ↓
Frontend collects: all SURVIVED hypotheses with conviction ≥ 6,
    their conviction_math, falsifier health, predicted assets
        ↓
POST /api/newsletter/generate
        ↓
Backend constructs prompt with structured data + style instructions
        ↓
Calls Anthropic API (claude-sonnet-4-20250514, max_tokens 1500)
        ↓
Returns formatted newsletter text
        ↓
Frontend renders in a print-ready overlay (A4 proportions)
    with [COPY] and [PRINT] buttons
```

#### Newsletter Format (strict — exactly this structure)

```
MERIDIAN MACRO WEEKLY                                    28 March 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HIGHEST CONVICTION: [trade name]                    Conviction: [X]/10
  ▸ THESIS: [2-3 sentences: what the mechanism is, why now]
  ▸ EXPRESSION: [ticker(s) and direction]
  ▸ WHAT BREAKS IT: [the 2 most important falsifiers, current status]

[Repeat for each hypothesis with conviction ≥ 6, max 4 entries]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGIME CONTEXT
  ▸ Active theories: [list with activation %]
  ▸ Key data: [3-4 most relevant data points from briefing]
  ▸ What we're watching: [top UNTESTABLE falsifiers awaiting data]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM: Falsification Engine v2 | 8 theory modules | Mechanical scoring
This is not investment advice. These are hypotheses that survived
systematic falsification. What the system found ≠ what you should do.
```

#### API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/newsletter/generate` | Generate newsletter from current hypothesis ledger |
| GET | `/api/newsletter/latest` | Retrieve most recently generated newsletter |
| GET | `/api/newsletter/history` | List of past newsletters with dates |

#### Prompt Construction (backend builds this, sends to Anthropic API)

System prompt:
```
You are a macro strategist writing a weekly newsletter. Your style is:
- Terse, declarative sentences. No hedging language.
- Lead with the trade, then the mechanism, then the risk.
- Every sentence must be load-bearing. No filler, no "in conclusion."
- Use the structured data provided. Do not add analysis beyond what the data supports.
- The newsletter must fit on one A4 page when printed in 11pt type.
- Maximum 4 trade ideas. Only include hypotheses with conviction ≥ 6.
- For "WHAT BREAKS IT": pick the 2 falsifiers closest to triggering or the 2 with highest severity. State the condition and the current data value.
```

User prompt: the full hypothesis objects for all survivors with conviction ≥ 6, including conviction_math, falsifier arrays, and the current briefing packet summary.

#### Frontend

- **Button:** "GENERATE NEWSLETTER" on Ledger view header, right side. Only enabled when at least 1 hypothesis has conviction ≥ 6.
- **Overlay:** Full-screen overlay with A4-proportioned content area (595px × 842px at 72dpi, scaled). Hermes Editorial typography. Monospace for data values.
- **Actions:** [COPY TO CLIPBOARD] [PRINT] [CLOSE]
- **Loading state:** "Generating..." with the Meridian compass mark.
- **Caching:** Store generated newsletter in DB. If hypothesis ledger hasn't changed since last generation, serve cached version with "Generated [timestamp]" note.

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
    activation score, evidence quality from data coverage ratio, convergence
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
| 4 | Feature 2: Newsletter Generator | 2.5 | Anthropic API key in .env |

**Total: ~7.5 hours**

Feature 3 goes first because it completes the mechanical pipeline — everything after it can reference "zero-LLM conviction scoring" as a fact. Feature 1 is the most user-facing value. Feature 4 is trivial once the pipeline is finalized. Feature 2 is last because it requires API integration and prompt tuning.

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
