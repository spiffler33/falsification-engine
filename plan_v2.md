# plan_v2.md — Falsification Engine v2 Implementation Plan

## What Exists (v1 + v2 — all complete)

The following pipeline is built and working end-to-end:

- 8 theory modules parsed and scored mechanically (activation engine)
- Data agent fetching FRED + Yahoo Finance into structured briefing packets
- Generation prompt producing 7-9 hypotheses per run
- Elimination prompt with mechanical falsifier audit (CLEAR / TRIGGERED / UNTESTABLE)
- Three-stage conviction scoring: mechanical Stage 1 inputs (support_strength, evidence_quality, convergence, falsifier_clarity) → Stage 2 discounts (soft falsifier, UNTESTABLE, theory-aware overlap) → Stage 3 gates (horizon alignment from timeframe parsing, expression efficiency from ETF liquidity tiers)
- Conviction floor at 5/10
- Consolidation check preventing redundant hypotheses
- React frontend: Research, Observatory, Pipeline, Trades views (+ About via header link)
- Hermes Editorial design system (Cormorant Garamond / EB Garamond / JetBrains Mono, cream/brick/olive/gold) with night mode
- GitHub Pages static publishing: snapshot endpoint bakes all hypotheses (across all runs) into window.__SNAPSHOT__, publish script deploys to gh-pages branch via temp directory with cache-busting query params. Read-only mode auto-detected by frontend (HashRouter, API interception from snapshot). Human-readable timestamp on static banner.
- About page: 12-step pipeline description grouped into 5 sections with architectural premise, continuous CSS counter
- Mobile-responsive CSS: nav horizontal scroll, tighter padding, table scroll wrappers, collapsed grids, reduced whitespace on small screens

### v2 Features — All Complete

1. **Mechanized Horizon Alignment + Expression Efficiency (Feature 3):** Entire conviction pipeline is zero-LLM. Horizon alignment parsed from timeframe strings (30-90 day ideal window). Expression efficiency from ETF universe coverage and liquidity tiers.

2. **Trade Tracker (Feature 1):** Full trade lifecycle — open from hypothesis, track P&L with live Yahoo Finance prices, close with reason. Backend stores primitives only; frontend computes all derived values (P&L, days held, notional, win rate, avg return by conviction tier). Trades linked to hypotheses, visible in both Trades view and Hypothesis Detail overlay.

3. **About Page (Feature 4):** 12-bullet mechanical pipeline description with architectural premise. Cormorant Garamond display, EB Garamond body, JetBrains Mono numbered steps. Header link, not a nav tab.

4. **Newsletter Prompt Builder (Feature 2):** One-click prompt assembly from survived hypotheses (conviction >= 6). System + user prompt sections with copy buttons. Copy-paste into Claude.ai for newsletter generation. No API calls, no storage.

5. **Newsletter Import + Archive (Feature 5):** Full paste-back workflow for newsletter output. Claude appends a `<TRADES>` JSON block to the newsletter text; frontend strips it before display and sends structured trade recommendations to backend. Newsletters stored with date and run context. Archive view shows all newsletters with click-to-expand full text.

6. **Navigation Restructure (Feature 6):** Collapsed from 5 tabs to 4: Research (newsletter workflow + research inbox) | Observatory (theory cards + hypothesis ledger + data briefing) | Pipeline | Trades. Ledger absorbed into Observatory. Briefing absorbed into Observatory. `/briefing` redirects to `/observatory`.

7. **Auto-Managed Trades via Newsletter (Feature 7):** Newsletter import diffs trade recommendations against open positions using desired-state reconciliation. Generates PENDING trade actions (OPEN / CLOSE / REDUCE) sized by conviction ($10k base allocation * conviction/10). Manual signoff required — user reviews pending actions on Trades tab, approves/rejects individually, executes at live Yahoo Finance prices. REDUCE uses close-and-reopen pattern for complete P&L audit trail.

### Infrastructure Improvements

- **Snapshot parity fix:** Snapshot endpoint now includes all hypotheses across all runs, matching the local ledger view (was previously filtered to latest run only).
- **Cache-busting:** Publish script appends `?v=<unix_timestamp>` to snapshot.js script tag, preventing GitHub Pages CDN from serving stale data.
- **Mobile tightening:** Comprehensive `@media (max-width: 768px)` block covering all views — header, nav, controls, modals, pipeline, about, briefing, trades (horizontal scroll wrappers), journal, inbox, audit, newsletter.
- **Lightweight DB migration:** `_migrate()` in database.py handles ALTER TABLE for adding columns to existing tables (e.g., `newsletter_id` on trades). Runs on every startup, idempotent.

**Current output quality:** Two completed runs with 13 total hypotheses. Conviction range 5-8 for survivors. Horizon gate is dominant kill mechanism — debt_cycle_long hypotheses with 9-12 month timeframes capped at 2-4/10 despite raw scores of 6.5-8.5. Stage 2 inputs serialized losslessly. Mechanical scores producing 4.5x wider differentiation than LLM self-evaluation.

---

## Build Order — All Complete

| Priority | Feature | Status |
|----------|---------|--------|
| 1 | Feature 3: Mechanize H + E | COMPLETE |
| 2 | Feature 1: Trade Tracker | COMPLETE |
| 3 | Feature 4: About Page | COMPLETE |
| 4 | Feature 2: Newsletter Prompt Builder | COMPLETE |
| 5 | Feature 5: Newsletter Import + Archive | COMPLETE |
| 6 | Feature 6: Navigation Restructure (5 tabs -> 4) | COMPLETE |
| 7 | Feature 7: Auto-Managed Trades via Newsletter | COMPLETE |
| 8 | Mobile responsive CSS | COMPLETE |
| 9 | Snapshot parity + cache-busting | COMPLETE |

---

## Data Model Reference

### Trade (primitives only)

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

### Newsletter

```python
class Newsletter(Base):
    __tablename__ = "newsletters"
    id: str            # "NL-2026-001"
    date: str          # ISO date of import
    run_id: str        # FK to runs — pipeline run at time of import
    content: str       # full ASCII newsletter text (TRADES block stripped)
    trade_recommendations: str  # JSON array: [{hypothesis_id, ticker, direction, conviction}]
```

### PendingTradeAction

```python
class PendingTradeAction(Base):
    __tablename__ = "pending_trade_actions"
    id: str             # "PTA-001"
    newsletter_id: str  # FK to newsletters
    action_type: str    # "OPEN" | "CLOSE" | "REDUCE"
    hypothesis_id: str  # which hypothesis drives this action
    ticker: str
    direction: str
    conviction: float
    proposed_shares: float
    proposed_price: float   # price at time of newsletter import
    existing_trade_id: str  # for CLOSE/REDUCE: which open trade to modify
    reduce_to_shares: float # for REDUCE: target share count
    status: str         # "PENDING" | "EXECUTED" | "REJECTED"
    executed_at: str
    executed_price: float   # actual price at signoff time
```

### Conviction Pipeline (zero-LLM)

```
Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
Stage 2: DISCOUNTED = RAW * D_f * D_o  →  SCORE = DISCOUNTED * 10
Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap)  →  max(FINAL, 5.0)
```

LLM does: generate hypotheses, attack hypotheses, check falsifiers against data
Math does: activation scoring, conviction scoring (all dimensions), overlap penalty, UNTESTABLE discount, gates, floor

### Post-Implementation Fixes

**Horizon alignment decay: symmetric → asymmetric (2026-03-28)**

Changed from symmetric hyperbolic `90/days` to asymmetric square root `(90/days)^0.5` for hypotheses exceeding the 90-day ideal window. Rationale: above-90 hypotheses describe mechanisms that are active now — the penalty is for dilution of per-period return expectation, not inability to execute. The gate cap (H < 0.40 → max conviction 4) now fires at ~562 days (~19 months) instead of ~135 days (~4.5 months). Below-30 linear penalty unchanged.

**GitHub Pages polish (2026-03-28)**

- Static mode UI stripping: Pipeline tab hidden from nav in static mode. All write-action buttons (GENERATE PROMPT, IMPORT NEWSLETTER, NEW TRADE, CLOSE, REFRESH PRICES, ADD inbox, ADD NOTE) hidden when `isStaticMode()`. Read-only data fully visible.
- Theory detail overlay: Clicking any theory card on Observatory opens a full overlay showing summary, core mechanism (5-step causal chain), activation indicators with thresholds/weights, predictions when active, hard falsifiers, and soft falsifiers with severity. Content embedded in `theoryDescriptions.js` (works on GitHub Pages without backend). All 8 theories covered.
- Night mode button color: `--accent-high` from `#C86B3A` (burnt orange) to `#A08B6E` (warm brass). Consistent with Hermes Editorial.
- README rewrite: Practitioner-facing README with intellectual approach, five-pass pipeline diagram, theory modules, conviction math, tech stack, setup, and GitHub Pages deployment.
