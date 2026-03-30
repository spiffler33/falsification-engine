# plan.md — Falsification Engine Implementation Plan

## Project Summary

Build a local web application that implements a five-pass falsification engine for global macro analysis. The system generates testable hypotheses from economic theory modules, attacks them adversarially, scores survivors mechanically, and presents a decision surface to the human operator.

Tech stack: FastAPI + SQLite (backend), React 18 + Vite + vanilla CSS (frontend), Python scripts (data agent, activation scoring, conviction scoring).

---

## What Already Exists

The following are complete and in the repo:

- **8 theory modules** (`theories/THEORY_MODULE_*.md`) — structured markdown with activation conditions, mechanisms, predictions, falsifiers with severity
- **Interface contract** (`docs/ECONOMIC_THEORIES_INTERFACE_CONTRACT.md`) — defines the theory module schema the system depends on
- **Frontend specification** (`docs/FRONTEND_SPEC_v1.md`) — complete spec with component tree, data shapes, API contracts, design system, SQLite schema
- **Data infrastructure brief** (`docs/DATA_INFRASTRUCTURE_BRIEF.md`) — data sources, ETF universe, computed metrics
- **Architecture brief** (`docs/falsification_engine_brief.md`) — intellectual foundation
- **Visual mental models spec** (`docs/VISUAL_MENTAL_MODELS_SPEC.md`) — SVG visualization designs (v2 feature)

---

## Target File Structure

```
falsification-engine/
├── CLAUDE.md
├── plan.md
├── .env.example                    # FRED_API_KEY, ANTHROPIC_API_KEY (optional)
├── requirements.txt
├── package.json                    # root scripts for convenience
│
├── docs/                           # design documents (read-only reference)
│   ├── ECONOMIC_THEORIES_INTERFACE_CONTRACT.md
│   ├── FRONTEND_SPEC_v1.md
│   ├── DATA_INFRASTRUCTURE_BRIEF.md
│   ├── VISUAL_MENTAL_MODELS_SPEC.md
│   └── falsification_engine_brief.md
│
├── theories/                       # theory modules (read by activation layer)
│   ├── THEORY_MODULE_valuation_mean_reversion_v1.md
│   ├── THEORY_MODULE_debt_cycle_short_v1.md
│   ├── THEORY_MODULE_debt_cycle_long_v1.md
│   ├── THEORY_MODULE_structural_fragility_v1.md
│   ├── THEORY_MODULE_fiscal_dominance_liquidity_v1.md
│   ├── THEORY_MODULE_fiscal_dominance_arithmetic_v1.md
│   ├── THEORY_MODULE_capital_flows_v1.md
│   └── THEORY_MODULE_monetary_architecture_v1.md
│
├── backend/
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # settings, paths, constants
│   ├── db/
│   │   ├── database.py             # SQLite setup, session management
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   └── seed.py                 # mock data seeding for first-run
│   ├── api/
│   │   ├── hypotheses.py           # hypothesis CRUD + delta endpoint
│   │   ├── pipeline.py             # pipeline status, prompt generation, import
│   │   ├── theories.py             # theory listing + activation scores
│   │   ├── journal.py              # journal CRUD
│   │   ├── inbox.py                # inbox CRUD
│   │   ├── briefing.py             # data briefing endpoint
│   │   └── user_state.py           # last_reviewed tracking
│   ├── engine/
│   │   ├── theory_parser.py        # parse theory module markdown → structured data
│   │   ├── activation.py           # Pass 1: mechanical activation scoring
│   │   ├── prompt_builder.py       # Build generation + elimination prompts
│   │   ├── output_parser.py        # Parse LLM JSON output → hypothesis objects
│   │   ├── conviction.py           # Pass 4: three-stage conviction scoring
│   │   └── data_agent.py           # FRED + Yahoo data fetching
│   └── schemas/
│       ├── hypothesis.py           # Pydantic models for hypothesis
│       ├── theory.py               # Pydantic models for parsed theory modules
│       ├── briefing.py             # Pydantic models for data briefing packet
│       ├── pipeline.py             # Pydantic models for pipeline state
│       └── scoring.py              # Pydantic models for conviction math
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css               # Hermes Editorial design system
│   │   ├── views/
│   │   │   ├── LedgerView.jsx      # Primary — home, daily entry point
│   │   │   ├── JournalView.jsx     # Decision recording + outcome tracking
│   │   │   ├── ObservatoryView.jsx # Theory module display + activation state
│   │   │   ├── PipelineView.jsx    # Run mode + audit mode
│   │   │   └── BriefingView.jsx    # Data briefing + research inbox
│   │   ├── overlays/
│   │   │   └── HypothesisDetail.jsx # Full hypothesis interrogation modal
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── NavBar.jsx
│   │   │   ├── DeltaBanner.jsx
│   │   │   ├── HypothesisTable.jsx
│   │   │   ├── AssetGroupView.jsx
│   │   │   ├── TheoryCard.jsx
│   │   │   ├── PipelineStep.jsx
│   │   │   ├── PromptPreview.jsx
│   │   │   ├── ImportPanel.jsx
│   │   │   ├── JournalEntry.jsx
│   │   │   ├── JournalForm.jsx
│   │   │   ├── ResearchInbox.jsx
│   │   │   ├── BriefingGrid.jsx
│   │   │   ├── ConvictionMath.jsx
│   │   │   ├── FalsifierHealth.jsx
│   │   │   └── EliminationAudit.jsx
│   │   ├── shared/
│   │   │   ├── StatusBadge.jsx
│   │   │   ├── TheoryTag.jsx
│   │   │   ├── AssetTag.jsx
│   │   │   ├── ConvictionDisplay.jsx
│   │   │   ├── FalsifierCompact.jsx
│   │   │   ├── Sparkline.jsx
│   │   │   └── ActionMarker.jsx
│   │   ├── hooks/
│   │   │   └── useApi.js
│   │   └── lib/
│   │       ├── api.js
│   │       └── format.js
│   └── public/
│
├── mock_data/
│   ├── briefing_packet.json
│   ├── activation_scores.json
│   ├── generation_output.json
│   ├── elimination_output.json
│   ├── conviction_scores.json
│   ├── inbox_items.json
│   └── journal_entries.json
│
├── scripts/
│   ├── run_data.py                 # CLI: fetch FRED + Yahoo, produce briefing
│   ├── run_activation.py           # CLI: compute activation scores
│   └── run_conviction.py           # CLI: run conviction scoring on imported results
│
└── data/
    └── falsification.db            # SQLite database (gitignored)
```

---

## Build Phases

### Phase 1: Foundation + Theory Parser (~2 hours)

**Goal:** Project scaffold, database, theory module parsing, and activation scoring working.

1. **Project setup**
   - Python venv, requirements.txt (fastapi, uvicorn, sqlalchemy, pydantic, yfinance, fredapi, httpx)
   - React + Vite scaffold
   - .env.example with FRED_API_KEY

2. **SQLite schema** — implement tables from FRONTEND_SPEC_v1.md Section 10:
   - runs, hypotheses, journal_entries, inbox_items, user_state

3. **Theory module parser** (`backend/engine/theory_parser.py`)
   - Parse markdown theory modules into structured Python objects
   - Extract: activation_conditions (indicator tables with metric, threshold, direction, weight), falsifiers (hard + soft with severity), predictions, metadata
   - Handle two-phase modules (separate activation tables per phase)
   - Load all modules from `theories/` directory
   - **Test:** parse all 8 modules, verify indicator weights sum to ~1.0 per module/phase

4. **Activation scoring** (`backend/engine/activation.py`)
   - Takes parsed theory modules + data briefing packet
   - Checks each indicator against briefing data
   - Computes weighted activation score
   - Returns Active/Adjacent/Inactive per theory (per-phase for two-phase modules)
   - Two-phase logic: check resolving/contraction/rotation first
   - **This is the most critical piece of infrastructure.** Get it right.

5. **Conviction scoring** (`backend/engine/conviction.py`)
   - Three-stage pipeline: raw conviction → discounts → gates
   - Inputs: hypothesis objects with conviction_math fields from evaluator
   - Stage 1: weighted sum (S×0.30 + Q×0.30 + C×0.25 + F×0.15)
   - Stage 2: soft falsifier discount (minor=0.10, medium=0.25, major=0.45), overlap penalty
   - Stage 3: horizon cap + expression cap
   - Output: 0-10 integer conviction score per hypothesis
   - **Pure math. No LLM. No narrative.**

### Phase 2: Data Agent + Briefing (~1.5 hours)

**Goal:** Automated data fetching producing a structured briefing packet.

1. **FRED integration** (`backend/engine/data_agent.py`)
   - Fetch ~22 macro series: GDP, CPI, core PCE, Fed Funds, yields (2Y, 10Y, 30Y), unemployment, payrolls, claims, ISM proxy, Fed balance sheet, TGA, RRP, M2, HY spread, IG spread, breakevens
   - Cache with staleness tracking

2. **Yahoo Finance integration**
   - Fetch ETF prices and returns (1M, 3M, 12M) for full universe
   - VIX, FX pairs (DXY, CNYUSD, EURUSD, JPYUSD)

3. **Computed metrics**
   - equity_risk_premium, net_liquidity + 30d change, gold_oil_ratio, em_us_relative, qqq_iwm_ratio, vix_vs_realized, yield curves (2s10s, 3m10y), real_10y, hard_vs_nominal_12m

4. **Briefing packet JSON schema** — Pydantic model matching the field names referenced in theory module activation conditions

5. **CLI script** (`scripts/run_data.py`) — fetch all data, produce briefing_packet.json

### Phase 3: Backend API + Pipeline (~2 hours)

**Goal:** All API endpoints from FRONTEND_SPEC_v1.md Section 6 working.

1. **Hypothesis APIs** — CRUD + delta endpoint + history
2. **Pipeline APIs** — status, prompt generation, import parsing
3. **Theory APIs** — list with activation scores
4. **Journal APIs** — CRUD with position tracking
5. **Inbox APIs** — CRUD with status tracking
6. **Briefing API** — serve latest briefing with staleness
7. **User state API** — last_reviewed tracking

**Prompt builder** (`backend/engine/prompt_builder.py`):
- Generation prompt: system instructions + Active theories (full content) + at most 1 Adjacent wildcard + briefing packet + queued inbox items
- Elimination prompt: system instructions + hypotheses from generation + theory modules + briefing packet
- See FRONTEND_SPEC_v1.md Section 4.5 for prompt templates

**Output parser** (`backend/engine/output_parser.py`):
- Parse generation JSON → hypothesis objects
- Parse elimination JSON → hypothesis status updates
- Schema validation with clear error messages for malformed input

### Phase 4: Mock Data + First-Run Experience (~1 hour)

**Goal:** The app works with realistic mock data before any real pipeline run.

1. **Generate mock data** for all 7 files in `mock_data/`:
   - Realistic briefing packet reflecting current-ish macro conditions
   - Activation scores computed from mock briefing
   - 6-8 mock hypotheses from 4 Active theories (mix of single-theory and multi-theory)
   - Elimination results: 2 KILLED, 2 WOUNDED, 4 SURVIVED
   - Conviction scores for survivors
   - 3 example inbox items
   - 1 example journal entry

2. **Seed script** (`backend/db/seed.py`) — load mock data into SQLite on first run

3. **First-run detection** — if no runs exist in DB, load mock data and show banner

### Phase 5: Frontend — Ledger + Hypothesis Detail (~3 hours)

**Goal:** The primary daily-use views working.

Follow FRONTEND_SPEC_v1.md Sections 4.1 and 4.2 exactly.

1. **Design system CSS** (`frontend/src/index.css`)
   - All CSS variables from FRONTEND_SPEC_v1.md Section 3
   - Font imports (Google Fonts: Cormorant Garamond, EB Garamond, JetBrains Mono)
   - Base typography rules
   - Layout constraints (1200px max-width, padding, borders)

2. **App shell** — Header, NavBar with 5 tabs, routing

3. **LedgerView** — delta banner, controls bar (BY HYPOTHESIS / BY ASSET toggle, status filters), hypothesis table with all columns
   - Delta banner: KILLED, DETERIORATED, IMPROVED, NEW, STABLE categories
   - Hypothesis table: Status, Hypothesis, Theory, Conv., Fals., Assets, Age, Markers
   - Asset view: grouped by ETF ticker with direction consensus

4. **HypothesisDetail** — modal overlay with all 7 sections:
   - Identity, Full Statement, Conviction Scoring (3-column grid), Falsifier Health (dots + severity badges), Elimination Audit, Research Notes (with inline input), Your Position

5. **Shared components** — StatusBadge, TheoryTag, AssetTag, ConvictionDisplay, FalsifierCompact, Sparkline (SVG), ActionMarker

### Phase 6: Frontend — Supporting Views (~2.5 hours)

**Goal:** All remaining views working.

Follow FRONTEND_SPEC_v1.md Sections 4.3-4.6 exactly.

1. **PipelineView** — Run Mode (5-step workflow with prompt preview, copy-to-clipboard, import panel) + Audit Mode (collapsible stages showing full run trace)

2. **JournalView** — Entry cards with action, hypothesis link, conviction at entry vs current, status. Form for recording new actions.

3. **ObservatoryView** — 2-column grid of theory cards with activation bar, tier badge, phase label for two-phase theories.

4. **BriefingView** — Research inbox (text input + ADD, theory tagging, status tracking) + briefing packet display (6-panel grid: growth, inflation, rates, liquidity, credit, sentiment)

### Phase 7: Integration + Polish (~1.5 hours)

1. **End-to-end flow:** Run pipeline from data fetch through conviction scoring, verify Ledger updates correctly
2. **Import validation:** Clear error messages when pasted JSON doesn't match expected schema
3. **Mobile responsive:** Ledger collapses to Status + Hypothesis + Theory + Conv on mobile
4. **Keyboard shortcuts:** ESC to close detail modal
5. **Loading states** for API calls
6. **First-run banner** with mock data notice
7. **README.md** — setup instructions, architecture overview, screenshot

---

## Critical Implementation Notes

### Theory Module Parsing Is Hard

The theory modules are rich markdown documents, not structured data files. The parser must:
- Find activation condition tables and extract rows with: indicator name, metric source, threshold, direction, weight
- Handle two-phase modules where Phase A and Phase B have separate tables
- Find soft falsifier tables and extract the severity column (minor/medium/major)
- Handle qualitative indicators (weight=qualitative) — exclude from mechanical score
- Extract metadata JSON blocks

Strategy: use regex or a markdown parser to find table sections by header, then parse rows. The table format is consistent across all 8 modules because they were generated from the same template.

### Activation Scoring Must Match Theory Module Field Names

The activation conditions reference briefing packet field names like `credit.hy_spread`, `^VIX`, `liquidity.reverse_repo`, computed metrics like `qqq_iwm_ratio`, and web-search-required fields.

For v1:
- Match mechanical indicators against briefing packet fields
- Skip web-search-required indicators (mark them as "requires manual check")
- Skip qualitative indicators
- The activation score from mechanical indicators alone is sufficient for v1

### Prompt Building Is the Bridge

The generation and elimination prompts are the interface between the mechanical system and the LLM. They must:
- Include the full text of Active theory modules (the LLM needs the mechanism descriptions, not just the structured data)
- Include the briefing packet as structured data
- Include queued inbox items
- Specify the exact output JSON schema the import parser expects
- For elimination: include the generated hypotheses with their pre-registered falsifiers

The prompts in FRONTEND_SPEC_v1.md Section 4.5 are templates. Flesh them out with the full system instructions from CLAUDE.md's Pass 2 and Pass 3 sections.

### The Hypothesis Object Is the Central Data Type

Every component should work with the Hypothesis interface defined in FRONTEND_SPEC_v1.md Section 5. The conviction_math field provides full transparency into the three-stage scoring pipeline. The delta_type field drives the delta banner. The conviction_history array drives sparklines.

### No External State Management

React Context + useReducer is sufficient. The hypothesis ledger is fetched from the API. No Redux, no Zustand, no external state library.

### No Charting Library

All visualizations are hand-rolled SVG components using CSS variables. Sparklines are simple polyline SVGs. The design system forbids charting libraries.

---

## Estimated Total: 13-15 hours

| Phase | Hours | Dependency |
|-------|-------|-----------|
| 1. Foundation + Theory Parser | 2.0 | None |
| 2. Data Agent + Briefing | 1.5 | Phase 1 |
| 3. Backend API + Pipeline | 2.0 | Phase 1 |
| 4. Mock Data + First-Run | 1.0 | Phases 1-3 |
| 5. Frontend — Ledger + Detail | 3.0 | Phase 3 |
| 6. Frontend — Supporting Views | 2.5 | Phase 5 |
| 7. Integration + Polish | 1.5 | All |

---

### v5: Walk-Forward Run Archive + Outcome Tracking (COMPLETE)

**Goal:** Enable retrospective walk-forward analysis across pipeline runs. After 8+ runs, the user can look back at every run and answer: What did the system detect? What hypotheses survived? What were asset prices when the system spoke? Was it right?

**Backend:**
1. **Briefing snapshot** — Complete briefing packet saved as JSON on run record at run creation time
2. **Price snapshots** — `run_price_snapshots` table captures closing prices for all predicted tickers after conviction scoring
3. **Outcome tracking** — `PATCH /api/hypotheses/{id}/outcome` with CORRECT/INCORRECT/PARTIAL/EXPIRED status, required notes, optional P&L %
4. **Archive + walkforward endpoints** — `GET /api/runs/archive` (summary stats + outcome counts), `GET /api/runs/{id}/prices`, `GET /api/runs/{id}/walkforward` (direction-aware delta computation)

**Frontend:**
5. **Run Archive panel** — Compact table of all historical runs with theory activation counts, survival rates (mini-bar), and aggregate outcome scorecard. Appears in Pipeline Audit Mode.
6. **Walk-Forward panel** — Per-run table of entry prices vs current prices with direction-aware delta. Positive delta always means hypothesis winning.
7. **Outcome section on Hypothesis Detail** — Entry prices, MARK OUTCOME form (4 status buttons, notes, optional P&L), recorded outcome display
8. **Ledger outcome badges** — Inline badges next to conviction scores for previous-run hypotheses

**Database migration 5:** `briefing_snapshot` + `price_snapshot_date` on runs, `outcome_status`/`outcome_date`/`outcome_notes`/`outcome_pnl_pct` on hypotheses, `run_price_snapshots` table.

---

## Success Criteria

The system succeeds if:

1. **Hypotheses are attacked before the user sees them.** The user receives survivors with conviction scores, not raw candidates.
2. **What the model found is clearly separated from what the user must decide.** The system never says "you should" — it says "this survived with score 7/10, these falsifiers are close to triggering."
3. **Asymmetric risk is handled structurally** — through the conviction scoring pipeline's soft falsifier discounts and gate caps, not through narrative disclaimers.
4. **The system creates a written record** — hypothesis ledger + journal enable learning over time.
5. **Usable in 2 minutes for a daily scan** (delta banner), 30 seconds for research capture (inbox), and 30-45 minutes for a full pipeline run (weekly).
6. **First-run experience works** — clone, configure API key, run, see mock data, understand the architecture from the UI.
7. **Architecturally novel** — not another committee simulator or multi-agent debate. A falsification engine with mechanical conviction scoring.
