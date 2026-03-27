# Falsification Engine

A global macro analytical system that generates testable hypotheses from economic theory modules, attacks them adversarially, scores survivors mechanically, and presents a decision surface to the human operator.

**This is not a trading system.** It does not produce signals, recommendations, or orders. It produces hypotheses with conviction scores and failure conditions. The human decides what to do.

## Architecture

Five-pass pipeline:

1. **Activation** (mechanical) -- Check theory module activation conditions against current data. Python math, no LLM.
2. **Generation** (LLM) -- Active theories + data briefing produce 2-4 hypotheses per theory.
3. **Elimination** (LLM, adversarial) -- A separate prompt whose only job is to attack each hypothesis.
4. **Conviction Scoring** (mechanical) -- Three-stage mathematical pipeline: raw conviction, discounts, gates. No LLM.
5. **Human Decision** -- Scored survivors presented in the Ledger. The human decides.

The key principle: LLMs generate hypotheses and attack them. LLMs never score conviction or recommend actions. The separation is the architecture.

## Tech Stack

- **Backend:** FastAPI + SQLite (SQLAlchemy ORM)
- **Frontend:** React 18 + Vite + vanilla CSS (Hermes Editorial design system)
- **Data:** FRED API + Yahoo Finance (yfinance)
- **Design:** Cormorant Garamond + EB Garamond + JetBrains Mono. No emoji. No rounded corners.

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- FRED API key (free from https://fred.stlouisfed.org/docs/api/api_key.html)

### Installation

```bash
# Clone and enter
git clone <repo-url>
cd falsification-engine

# Python environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..

# Configure API key
cp .env.example .env
# Edit .env and add your FRED_API_KEY
```

### Running

Start both backend and frontend:

```bash
# Terminal 1: Backend (port 8000)
uvicorn backend.main:app --reload

# Terminal 2: Frontend (port 5173, proxies /api to backend)
cd frontend
npm run dev
```

Open http://localhost:5173. On first run, mock data loads automatically so you can explore the interface immediately.

### Fetching Real Data

```bash
# Fetch current macro data from FRED + Yahoo Finance
python scripts/run_data.py
```

This produces `data/briefing_packet.json`. The system uses this for activation scoring and prompt building.

## Usage

### Daily Scan (2 minutes)

Open the Ledger. The delta banner shows what changed since your last review: new hypotheses, conviction changes, kills. Read, mark reviewed, done.

### Research Capture (30 seconds)

Go to Briefing > Research Inbox. Paste a note or link, tag the relevant theory, hit ADD. It gets queued for the next pipeline run.

### Full Pipeline Run (30-45 minutes)

1. Go to Pipeline > Run Mode
2. **Step 1-2** (automated): Data briefing loads, activation scores computed
3. **Step 3**: Click COPY TO CLIPBOARD, paste into Claude, paste the response back into IMPORT RESULT
4. **Step 4**: Same pattern with the elimination prompt
5. **Step 5** (automated): Conviction scoring runs, Ledger updates

## Project Structure

```
falsification-engine/
  backend/
    main.py              # FastAPI app
    api/                 # REST endpoints
    engine/              # Theory parser, activation, conviction, prompts
    db/                  # SQLite models + seed
    schemas/             # Pydantic models
  frontend/
    src/
      views/             # Ledger, Pipeline, Observatory, Journal, Briefing
      overlays/          # Hypothesis detail modal
      components/        # UI components
      shared/            # Reusable atoms (badges, tags, sparklines)
  theories/              # 8 economic theory modules (structured markdown)
  mock_data/             # Realistic mock data for first-run experience
  scripts/               # CLI tools (data fetch, activation, conviction)
  docs/                  # Design documents and specifications
```

## Theory Modules

8 modules across 6 domains. The system supports N modules via a registry pattern.

| Theory | Two-Phase |
|--------|-----------|
| Valuation Mean Reversion | No |
| Short-Term Debt Cycle | Yes (Expansion / Contraction) |
| Long-Term Debt Cycle | No |
| Structural Fragility | Yes (Building / Resolving) |
| Fiscal Dominance -- Liquidity | No |
| Fiscal Dominance -- Arithmetic | No |
| Capital Flows | Yes (Accumulation / Rotation) |
| Monetary Architecture | No |

## Conviction Scoring

Three-stage mechanical pipeline (no LLM):

**Stage 1 -- Raw Conviction:** Weighted sum of support strength (0.30), evidence quality (0.30), convergence (0.25), falsifier clarity (0.15).

**Stage 2 -- Discounts:** Soft falsifier health discount (triggered falsifiers reduce score by severity: minor=0.10, medium=0.25, major=0.45). Exposure overlap penalty for hypotheses sharing instruments.

**Stage 3 -- Gates:** Hard caps from horizon alignment and expression efficiency. Final output: 0-10 integer.

## Frontend Views

- **Ledger** -- Daily entry point. Delta banner, hypothesis table, asset grouping.
- **Hypothesis Detail** -- Full interrogation modal with conviction math, falsifier health, elimination audit.
- **Pipeline** -- Run mode (5-step workflow) and audit mode (read-only trace of completed runs).
- **Observatory** -- Theory module cards with activation state.
- **Briefing** -- Research inbox + data briefing grid.
