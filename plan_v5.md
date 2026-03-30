# plan_v5.md — Falsification Engine v5 Implementation Plan

## Enhancement 3: Walk-Forward Run Archive + Outcome Tracking

### Design Principle

**The system must be accountable to itself.** A hypothesis engine that cannot answer "was it right?" is incomplete. Walk-forward analysis requires three things the system lacked: what the system *saw* (briefing snapshot), what the market *was* (price snapshot), and whether it was *right* (outcomes). All three are append-only. Outcomes are manual -- the system does NOT auto-resolve, because "was it right?" is a judgment call that belongs to the human.

---

## What Exists (v1 + v2 + v3 + v4 — all complete)

The full pipeline through v4:

```
Pass 1:   Activation scoring — 8 modules scored independently
Pass 1.5: Regime annotation — compute_regime_flags() from activation results
Pass 2:   LLM generation — active theories + regime context + channel tags
Pass 3:   LLM elimination — adversarial attack + sector falsifier appendices + channel verification
Pass 4:   Mechanical conviction scoring (zero-LLM, 3-stage: raw -> discounts -> gates)
Pass 5:   Human decision layer
```

Missing: No historical record of what the briefing data looked like at run time. No capture of asset prices at the moment the system spoke. No structured way to record whether hypotheses were correct. No archive view across runs.

---

## The Problem v5 Solves

After 8+ pipeline runs over 2 months, the user needs to look back and answer:

1. **What did the system detect?** (activation scores, hypothesis generation)
2. **What hypotheses survived?** (conviction scoring results)
3. **What were asset prices when the system spoke?** (entry prices for walk-forward comparison)
4. **Was it right?** (outcome tracking -- CORRECT / INCORRECT / PARTIAL / EXPIRED)

Without briefing snapshots, FRED data revisions erase what the system actually saw. Without price snapshots, the user must manually look up historical prices. Without outcomes, there is no feedback loop.

---

## What v5 Adds

### 1. Briefing Packet Snapshot Per Run

The complete briefing packet (all FRED + Yahoo Finance data + computed metrics) is saved as a JSON column on the run record when a new pipeline run is created. This captures the ground truth for "what data was available when this run happened."

**Implementation:** `_get_or_create_active_run()` in pipeline.py saves `briefing_snapshot` on the Run model.

### 2. Market Price Snapshot at Run Time

After conviction scoring completes, the system captures the current closing price for every ticker mentioned across ALL hypotheses in the run (SURVIVED, WOUNDED, and KILLED -- all of them, for completeness).

**Implementation:**
- New table: `run_price_snapshots` (composite PK: run_id + ticker)
- `_capture_price_snapshots()` called in `import_elimination()` after conviction scoring, before status = "complete"
- Uses existing `_fetch_current_price()` from trades.py (Yahoo v8 chart API via curl)

### 3. Outcome Tracking on Hypotheses

Four new fields on the hypothesis model:
- `outcome_status`: NULL (pending) | CORRECT | INCORRECT | PARTIAL | EXPIRED
- `outcome_date`: ISO date when outcome was recorded
- `outcome_notes`: Free text (required -- forces the user to state WHY)
- `outcome_pnl_pct`: Optional percentage return

**Endpoint:** `PATCH /api/hypotheses/{id}/outcome`
- Validates status is one of the four allowed values
- Requires non-empty outcome_notes
- Records date automatically (no backdating)

**Status definitions:**
- **CORRECT:** predicted direction and approximate magnitude materialized within timeframe
- **INCORRECT:** prediction clearly wrong -- asset moved materially opposite, or mechanism invalidated
- **PARTIAL:** direction right but magnitude materially off, or mechanism different than predicted
- **EXPIRED:** timeframe elapsed without clear directional move -- inconclusive

### 4. New API Endpoints

```
GET  /api/runs/archive        — all runs with summary stats + aggregate outcome counts
GET  /api/runs/{id}/prices    — price snapshots for a run
GET  /api/runs/{id}/walkforward — entry prices + current prices + direction-aware deltas
PATCH /api/hypotheses/{id}/outcome — record outcome
```

**Walk-forward delta computation is direction-aware:**
```
If direction == LONG:  delta = (current - entry) / entry
If direction == SHORT: delta = (entry - current) / entry
```
Positive delta always means "the hypothesis is winning."

### 5. Run Archive Panel (Pipeline Audit Mode)

Compact table of all historical runs showing:
- Run ID, date, theories active (X/8), hypotheses generated, hypotheses survived
- Mini survival bar (4-block visual)
- Aggregate outcome scorecard across ALL hypotheses from ALL runs

Clicking a run row loads its full audit detail (existing 5-stage collapsible audit) plus the walk-forward panel.

### 6. Walk-Forward Panel (Per-Run)

Table at the bottom of each run's audit detail:
- Hypothesis name + primary ticker, direction, entry price, current price, direction-aware delta %
- Delta colored: positive (green), negative (red)
- Per-run outcome summary

### 7. Outcome Section on Hypothesis Detail

New section below Research Notes:
- Entry prices from run_price_snapshots for this hypothesis's predicted_assets
- When outcome is NULL: MARK OUTCOME button -> form with 4 status buttons, required notes textarea, optional P&L %
- When outcome is set: colored status badge, recorded date, notes, P&L

### 8. Ledger Outcome Badges

Small inline badges (V / X / o / --) next to conviction scores on the Ledger's HypothesisTable. Only shown for hypotheses from previous runs (not the current/latest run -- too early to judge).

---

## Database Changes

### New table: run_price_snapshots

```sql
CREATE TABLE IF NOT EXISTS run_price_snapshots (
    run_id TEXT NOT NULL REFERENCES runs(id),
    ticker TEXT NOT NULL,
    price REAL NOT NULL,
    date TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'yahoo_finance',
    PRIMARY KEY (run_id, ticker)
);
```

### Altered table: runs

```sql
ALTER TABLE runs ADD COLUMN briefing_snapshot TEXT;
ALTER TABLE runs ADD COLUMN price_snapshot_date TEXT;
```

### Altered table: hypotheses

```sql
ALTER TABLE hypotheses ADD COLUMN outcome_status TEXT;
ALTER TABLE hypotheses ADD COLUMN outcome_date TEXT;
ALTER TABLE hypotheses ADD COLUMN outcome_notes TEXT;
ALTER TABLE hypotheses ADD COLUMN outcome_pnl_pct REAL;
```

All migrations idempotent (Migration 5 in database.py `_migrate()`).

---

## Files Modified

**Backend (4 files):**
- `backend/db/models.py` — RunPriceSnapshot model, new fields on Run and Hypothesis
- `backend/db/database.py` — Migration 5
- `backend/api/pipeline.py` — Briefing snapshot persistence, price capture, archive/prices/walkforward endpoints, route ordering fix
- `backend/api/hypotheses.py` — Outcome fields in _model_to_dict, PATCH /outcome endpoint

**Frontend (6 files):**
- `frontend/src/App.jsx` — Thread onSelectHypothesis to PipelineView
- `frontend/src/views/PipelineView.jsx` — Run Archive, Walk-Forward, SurvivalBar, refactored AuditMode
- `frontend/src/overlays/HypothesisDetail.jsx` — Outcome section with entry prices + form
- `frontend/src/components/HypothesisTable.jsx` — Outcome badges
- `frontend/src/shared/OutcomeBadge.jsx` — New shared component
- `frontend/src/index.css` — ~300 lines of Hermes Editorial styles

---

## What v5 Does NOT Do

- Does NOT auto-resolve outcomes -- manual human judgment only
- Does NOT add a separate Walk-Forward tab to navigation -- lives inside Pipeline Audit Mode and Hypothesis Detail
- Does NOT fetch live prices on every page load -- the walkforward endpoint fetches on demand
- Does NOT change the pipeline execution flow -- briefing snapshot and price snapshot happen automatically
- Does NOT modify theory modules, sector appendices, generation prompt, or elimination prompt

---

## Status: COMPLETE (2026-03-30)

Commit: 036d786 — "v5: Walk-forward run archive + outcome tracking"
