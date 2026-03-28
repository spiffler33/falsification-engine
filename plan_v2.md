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
- React frontend: Ledger, Trades, Observatory, Pipeline, Briefing, About views
- Hermes Editorial design system (Cormorant Garamond / EB Garamond / JetBrains Mono, cream/brick/olive/gold) with night mode
- GitHub Pages static publishing: snapshot endpoint bakes all hypotheses (across all runs) into window.__SNAPSHOT__, publish script deploys to gh-pages branch via temp directory with cache-busting query params. Read-only mode auto-detected by frontend (HashRouter, API interception from snapshot). Human-readable timestamp on static banner.
- About page: 12-step pipeline description grouped into 5 sections with architectural premise, continuous CSS counter
- Mobile-responsive CSS: nav horizontal scroll, tighter padding, table scroll wrappers, collapsed grids, reduced whitespace on small screens

### v2 Features — All Complete

1. **Mechanized Horizon Alignment + Expression Efficiency (Feature 3):** Entire conviction pipeline is zero-LLM. Horizon alignment parsed from timeframe strings (30-90 day ideal window). Expression efficiency from ETF universe coverage and liquidity tiers.

2. **Trade Tracker (Feature 1):** Full trade lifecycle — open from hypothesis, track P&L with live Yahoo Finance prices, close with reason. Backend stores primitives only; frontend computes all derived values (P&L, days held, notional, win rate, avg return by conviction tier). Trades linked to hypotheses, visible in both Trades view and Hypothesis Detail overlay.

3. **About Page (Feature 4):** 12-bullet mechanical pipeline description with architectural premise. Cormorant Garamond display, EB Garamond body, JetBrains Mono numbered steps. Header link, not a nav tab.

4. **Newsletter Prompt Builder (Feature 2):** One-click prompt assembly from survived hypotheses (conviction >= 6). System + user prompt sections with copy buttons. Copy-paste into Claude.ai for newsletter generation. No API calls, no storage.

### Infrastructure Improvements

- **Snapshot parity fix:** Snapshot endpoint now includes all hypotheses across all runs, matching the local ledger view (was previously filtered to latest run only).
- **Cache-busting:** Publish script appends `?v=<unix_timestamp>` to snapshot.js script tag, preventing GitHub Pages CDN from serving stale data.
- **Mobile tightening:** Comprehensive `@media (max-width: 768px)` block covering all views — header, nav, controls, modals, pipeline, about, briefing, trades (horizontal scroll wrappers), journal, inbox, audit, newsletter.

**Current output quality:** Two completed runs with 13 total hypotheses. Conviction range 5-8 for survivors. Horizon gate is dominant kill mechanism — debt_cycle_long hypotheses with 9-12 month timeframes capped at 2-4/10 despite raw scores of 6.5-8.5. Stage 2 inputs serialized losslessly. Mechanical scores producing 4.5x wider differentiation than LLM self-evaluation.

---

## Build Order — All Complete

| Priority | Feature | Status |
|----------|---------|--------|
| 1 | Feature 3: Mechanize H + E | COMPLETE |
| 2 | Feature 1: Trade Tracker | COMPLETE |
| 3 | Feature 4: About Page | COMPLETE |
| 4 | Feature 2: Newsletter Prompt Builder | COMPLETE |
| 5 | Mobile responsive CSS | COMPLETE |
| 6 | Snapshot parity + cache-busting | COMPLETE |

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

### Conviction Pipeline (zero-LLM)

```
Stage 1: RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
Stage 2: DISCOUNTED = RAW * D_f * D_o  →  SCORE = DISCOUNTED * 10
Stage 3: FINAL = min(SCORE, horizon_cap, expression_cap)  →  max(FINAL, 5.0)
```

LLM does: generate hypotheses, attack hypotheses, check falsifiers against data
Math does: activation scoring, conviction scoring (all dimensions), overlap penalty, UNTESTABLE discount, gates, floor
