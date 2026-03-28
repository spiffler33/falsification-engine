# Falsification Engine

### A global macro analytical system that treats hypotheses as things to be destroyed, not confirmed

---

Most AI-for-investing systems follow the same pattern: data goes in, agents debate, a buy/sell/hold signal comes out. They force language models into the role of conviction engine -- collapsing distributional reasoning into point predictions, then dressing the output in the language of confidence.

This system takes the opposite approach. It uses LLMs for what they are structurally good at -- generating hypotheses and attacking them -- and keeps them away from what they are structurally bad at: forming conviction under asymmetric consequences.

The result is a five-pass falsification pipeline that produces scored survivors with explicit failure conditions, not recommendations. The human decides what to do.

**Live snapshot:** [falsification-engine on GitHub Pages](https://coddiwomplers.github.io/falsification-engine/) (read-only, static data)

---

## The Core Architectural Principle

LLMs are distributional reasoners trained on symmetric loss. View formation requires causal prioritization under asymmetric consequences.

In concrete terms:

- **Distributional, not point-predictive.** The softmax output at every step is a probability vector. The model is trained to be a bookie (set odds across all horses), not a bettor (pick one horse and size the stake).
- **Symmetric loss, asymmetric decisions.** In training, under-weighting a bullish continuation is penalized identically to under-weighting a bearish one. Real portfolio decisions have deeply asymmetric error costs.
- **Frequency masquerades as conviction.** When distributional skew is overwhelming, the model looks like it has conviction. It has frequency. The distinction surfaces in regime changes and novel situations -- exactly when you need the system most.

The design consequence: do not ask the model for the answer. Use the model to destroy bad answers. Then apply consequence-bearing judgment to what survives.

**The model is a falsification engine, not an oracle.**

---

## The Five-Pass Pipeline

```
Pass 1           Pass 2          Pass 3             Pass 4              Pass 5
ACTIVATION  -->  GENERATION  --> ELIMINATION  -->   CONVICTION    -->   HUMAN
(mechanical)     (LLM)          (LLM, adversarial)  (mechanical)        DECISION

Python math      Claude Opus     Separate prompt     Three-stage         Scored survivors
checks theory    generates       whose only job      mathematical        presented in the
indicators       2-4 hypotheses  is to attack        pipeline            Ledger. The human
against data     per active      each hypothesis.    Raw -> Discounts    decides.
briefing.        theory.         SURVIVED / WOUNDED  -> Gates.
No LLM.                         / KILLED.           No LLM.
                                                    Output: 0-10.
```

The separation is the architecture. The generator never ranks hypotheses. The evaluator never scores conviction. The conviction pipeline never calls an LLM. Each pass does one thing.

LLM passes are human-in-the-loop: the system builds the prompt, you copy it to Claude, paste the response back. This is deliberate -- it keeps the human in the reasoning chain, not just the decision chain.

---

## Theory Modules

Eight modules across six domains provide the intellectual scaffolding. Each module defines activation conditions (indicator thresholds and weights), causal mechanisms, directional predictions, hard and soft falsifiers with pre-registered severity, and downstream implications. The system supports N modules via a registry pattern.

| # | Theory | Domain | Two-Phase | Description |
|---|--------|--------|-----------|-------------|
| 1 | Valuation Mean Reversion | Valuation | No | Equity valuations as long-duration mean-reverting processes. Extreme CAPE, Buffett Indicator, and equity risk premium levels create gravitational pull on forward returns. |
| 2 | Short-Term Debt Cycle | Credit | Yes (Expansion / Contraction) | Cyclical credit expansion and contraction driven by central bank policy and lending standards. Tracks the ~5-8 year business cycle through credit growth, yield curve, and lending conditions. |
| 3 | Long-Term Debt Cycle | Credit | No | Secular debt accumulation relative to productive capacity. When debt/GDP reaches structural limits and monetary policy loses traction, the resolution mechanism (inflation, default, restructuring) becomes the dominant macro force. |
| 4 | Structural Fragility | Risk | Yes (Building / Resolving) | Hidden fragility accumulating in market microstructure -- volatility compression, correlation clustering, liquidity withdrawal. Fragility builds silently, then resolves violently. |
| 5 | Fiscal Dominance -- Liquidity | Fiscal | No | Treasury issuance patterns and reserve dynamics reshaping liquidity conditions. When fiscal deficits dominate the flow-of-funds, monetary policy transmission is subordinated to Treasury cash management. |
| 6 | Fiscal Dominance -- Arithmetic | Fiscal | No | Debt sustainability arithmetic: primary deficits, interest expense trajectories, and the r-g differential. When the arithmetic turns adverse, the policy response becomes the macro variable. |
| 7 | Capital Flows | Flows | Yes (Accumulation / Rotation) | Cross-border and cross-asset capital flows driven by relative growth differentials, yield spreads, and dollar dynamics. Accumulation in one regime seeds the rotation into the next. |
| 8 | Monetary Architecture | Monetary | No | Structural shifts in the monetary plumbing -- reserve regime changes, collateral constraints, central bank balance sheet composition. When the architecture changes, all assets reprice to the new transmission mechanism. |

Three theories are two-phase: the system checks the resolving/contraction/rotation phase first. If active, the building/expansion/accumulation phase is automatically inactive.

---

## Conviction Scoring

A three-stage mechanical pipeline. No LLM. No narrative. Pure math.

**Stage 1 -- Raw Conviction** (epistemic quality)

```
RAW = Support_Strength(0.30) + Evidence_Quality(0.30) + Convergence(0.25) + Falsifier_Clarity(0.15)
```

Four dimensions scored 0.0-1.0 and weighted. Support strength measures current evidence actively supporting predictions. Evidence quality grades source directness and recency (market data > macro data > proxies > narrative). Convergence rewards independent theories predicting the same outcome, discounted for shared upstream dependencies. Falsifier clarity rewards specific, testable failure conditions.

**Stage 2 -- Discounts** (multiplicative penalties)

```
D_falsifier = max(0.05, 1 - sum(severity_weight_i))     # minor=0.10, medium=0.25, major=0.45
D_overlap   = 1 / (1 + overlap_count * 0.25)             # penalizes crowded instruments

SCORE = RAW * D_falsifier * D_overlap * 10
```

Triggered soft falsifiers reduce conviction by their pre-registered severity. Hypotheses sharing instruments with other survivors are penalized for concentration.

**Stage 3 -- Gates** (hard caps on actionability)

```
FINAL = min(SCORE, horizon_cap, expression_cap)
```

Horizon alignment gates: hypotheses outside the portfolio's 1-3 month holding period are capped regardless of conviction. Expression efficiency gates: if the available ETFs are poor proxies for the predicted move, the score is capped.

Output: 0-10 integer. This is a conviction signal, not a recommendation.

---

## Frontend Views

The interface is organized around hypotheses, not theories or agents.

- **Observatory** -- Theory module cards showing activation state (Active / Adjacent / Inactive), the full hypothesis ledger, and the current data briefing. The primary analytical surface.
- **Research** -- Newsletter workflow for assembling weekly research notes from live hypotheses and briefing data. Research inbox for capturing observations, links, and notes tagged to theories for inclusion in the next pipeline run.
- **Pipeline** -- The five-step run workflow. Steps 1-2 (data + activation) and Step 5 (conviction scoring) are automated. Steps 3-4 (generation + elimination) are copy-paste through Claude. Audit mode provides read-only traces of completed runs.
- **Trades** -- Trade tracker linking positions to hypotheses. Computes live P&L via Yahoo Finance, tracks performance by conviction tier, and maintains a full trade journal.
- **Ledger** -- Hypothesis table with delta banner showing changes since last review. Entry point for daily scans.
- **Journal** -- Timestamped analytical notes attached to hypotheses or written freeform.

Design system: Hermes Editorial. Warm cream backgrounds, dark typography, no decoration. Cormorant Garamond for display, EB Garamond for body text, JetBrains Mono for data. No rounded corners, no shadows, no gradients. Structure from line weight and whitespace. Feels like a quarterly letter from a private bank, not a fintech dashboard.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLite (SQLAlchemy ORM) |
| Frontend | React 18 + Vite + vanilla CSS |
| Data | FRED API (macro) + Yahoo Finance via yfinance (markets) |
| LLM | Claude Opus via copy-paste (no API dependency) |
| Design | Hermes Editorial -- Cormorant Garamond, EB Garamond, JetBrains Mono |
| Deployment | GitHub Pages (read-only static snapshot) |

---

## Project Structure

```
falsification-engine/
  backend/
    main.py                  # FastAPI application entry point
    config.py                # Settings, paths, constants
    api/                     # REST endpoints (hypotheses, pipeline, theories, journal, inbox, briefing, trades)
    engine/
      theory_parser.py       # Parse theory module markdown into structured data
      activation.py          # Pass 1: mechanical activation scoring
      prompt_builder.py      # Build generation + elimination prompts
      output_parser.py       # Parse LLM JSON output into hypothesis objects
      conviction.py          # Pass 4: three-stage conviction scoring
      data_agent.py          # FRED + Yahoo Finance data fetching
    db/                      # SQLite models, migrations, seed data
    schemas/                 # Pydantic models for all domain objects
  frontend/
    src/
      views/                 # Observatory, Research, Pipeline, Trades, Ledger, Journal, About
      overlays/              # Hypothesis detail modal
      components/            # UI components
      shared/                # Reusable atoms (badges, tags, sparklines)
  theories/                  # 8 economic theory modules (structured markdown)
  scripts/                   # CLI tools (data fetch, activation, conviction)
  mock_data/                 # Realistic mock data for first-run experience
  data/                      # Generated briefing packets and run artifacts
  docs/                      # Design documents and specifications
```

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- FRED API key (free from https://fred.stlouisfed.org/docs/api/api_key.html)

### Installation

```bash
# Clone and enter
git clone https://github.com/coddiwomplers/falsification-engine.git
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

```bash
# Terminal 1: Backend (port 8000)
uvicorn backend.main:app --reload

# Terminal 2: Frontend (port 5173, proxies /api to backend)
cd frontend
npm run dev
```

Open http://localhost:5173. Mock data loads automatically on first run so you can explore the interface immediately.

### Fetching Real Data

```bash
# Fetch current macro data from FRED + Yahoo Finance
python scripts/run_data.py
```

This produces `data/briefing_packet.json`, which the activation layer scores against and the prompt builder includes in LLM context.

---

## Usage

### Daily Scan (2 minutes)

Open the Ledger. The delta banner shows what changed since your last review -- new hypotheses, conviction changes, kills. Read, mark reviewed, done.

### Research Capture (30 seconds)

Research view, inbox tab. Paste a note or link, tag the relevant theory, add it. Queued for the next pipeline run.

### Full Pipeline Run (30-45 minutes)

1. Go to Pipeline, start a new run
2. **Steps 1-2** (automated): Data briefing loads, activation scores computed
3. **Step 3**: Copy the generation prompt to Claude, paste the response back
4. **Step 4**: Copy the elimination prompt to Claude, paste the response back
5. **Step 5** (automated): Conviction scoring runs, ledger updates

### Newsletter Assembly

Research view, newsletter tab. Select hypotheses and briefing sections, arrange the narrative, export. Weekly cadence.

---

## GitHub Pages Deployment

The published site at [coddiwomplers.github.io/falsification-engine](https://coddiwomplers.github.io/falsification-engine/) is a read-only static snapshot. All write actions (pipeline runs, journal entries, trade logging) are stripped in static mode. The snapshot includes recent newsletters, trades, and the full hypothesis ledger as of the last publish.

This serves as a portfolio piece and a way to share the analytical output without requiring anyone to run the full stack.

---

## What This Is Not

This system does not produce trading signals, portfolio recommendations, or position sizes. It does not automate execution. It does not have a chat interface. It does not ask an LLM for conviction scores.

It produces hypotheses with conviction scores and failure conditions. It tells you what would have to be true for each hypothesis to work, and what would kill it. The human -- with capital at risk and asymmetric consequences -- decides what to do.

That separation is not a limitation. It is the entire point.
