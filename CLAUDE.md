# CLAUDE.md — Falsification Engine

## What This Is

A global macro analytical system for personal use (~$1.5M AUM, liquid ETFs, ~1-3 month holding periods). The system generates testable hypotheses from economic theory modules, attacks them adversarially, scores survivors mechanically, and presents a decision surface to the human operator.

**This is NOT a trading system. It does not produce signals, recommendations, or orders. It produces hypotheses with conviction scores and failure conditions. The human decides what to do.**

## Context Window Management

You have a finite context window. Manage it actively, don't wait for compaction.

**After completing each Phase (not each file — each Phase from plan.md):**
1. Stop and say: "Phase N complete. Summary of what was built: [list files created/modified and their purpose]. Ready to clear context and start Phase N+1."
2. Wait for me to confirm before proceeding.

**Within a phase, after completing each major component** (e.g., theory parser done, activation scoring done):
1. Write a brief checkpoint comment at the top of the file you just finished: what it does, what it depends on, what depends on it.
2. If you notice your context is getting heavy (you're struggling to recall earlier decisions or re-reading files you already read), say so. I will clear context and give you a resumption prompt.

**When resuming after context clear:**
- Re-read CLAUDE.md and plan.md first
- Then read only the files relevant to the current phase
- Do not re-read completed phases' code unless you need to interface with it

**Do not:**
- Hold more than 3-4 files in context simultaneously
- Re-read theory module markdown once you've confirmed the parser works on it
- Keep frontend spec in context while working on backend (and vice versa)
```

The key insight: you're telling it to **announce checkpoints** rather than silently continuing. That gives you the natural breakpoints to clear context even though permissions aren't stopping it. The "stop and summarize" pattern means you stay in control of the rhythm without micromanaging each file.

When you clear context and resume, give it something like:
```
Phases 1-2 are complete. The theory parser, activation scoring, conviction scoring, and data agent are all working. Start Phase 3: Backend API + Pipeline. Re-read CLAUDE.md, plan.md, and docs/FRONTEND_SPEC_v1.md Section 6 (API contracts) before building.

## The Core Architectural Principle

**LLMs are distributional reasoners trained on symmetric loss. View formation requires causal prioritization under asymmetric consequences.**

LLMs are structurally hypothesis generators, not conviction engines. They are trained to spread probability mass across plausible continuations, not to commit under uncertainty. The system uses this strength (hypothesis generation) and compensates for the weakness (conviction, asymmetric risk assessment) with mechanical scoring and human judgment.

**The model is a falsification engine, not an oracle.** Do not ask the model for the answer. Use the model to destroy bad answers. Then apply consequence-bearing judgment to what survives.

This principle must be honored everywhere in the implementation:
- The generator produces hypotheses. It does NOT rank them by importance or recommend actions.
- The evaluator attacks hypotheses. It does NOT decide how much conviction survivors deserve.
- The conviction scoring pipeline is pure math. No LLM calls. No narrative.
- The human sees scored survivors and decides. The system never says "you should buy X."

## The Five Passes

### Pass 1: Activation (Mechanical — Python)
Check each theory module's activation conditions against the current data briefing. Each indicator has a threshold, direction, and weight. Compute weighted activation score per theory. Two-phase theories (structural_fragility, debt_cycle_short, capital_flows) are scored per-phase — check the resolving/contraction/rotation phase first; if Active, the building/expansion/accumulation phase is Inactive.

Output: each theory tagged Active (≥0.60) / Adjacent (0.30-0.59) / Inactive (<0.30).

**No LLM involved. This is a Python function.**

### Pass 2: Generation (LLM)
Active theory modules + at most 1 Adjacent wildcard + data briefing + queued inbox items → prompt to Claude Opus. Claude produces 2-4 hypotheses per Active theory, each with:
- theory_id (source theory)
- short_name (6-12 words)
- mechanism (causal chain from theory module)
- prediction (specific, testable, with magnitude and timeframe)
- predicted_assets (ETF tickers with LONG/SHORT direction)
- hard_falsifiers (conditions that kill the hypothesis)
- soft_falsifiers (conditions that wound it, with severity: minor/medium/major inherited from theory module)
- timeframe

**The generator must NOT:**
- Rank hypotheses by importance
- Recommend actions
- Produce hypotheses from Inactive theories
- Combine theories in ways that broaden rather than narrow predictions (the evaluator will kill these)

### Pass 3: Elimination (LLM, adversarial — separate prompt)
A different prompt, different instructions, whose ONLY job is to attack each hypothesis. Checks:
1. Hard falsifier check — is any hard falsifier currently triggered? If yes, hypothesis KILLED.
2. Soft falsifier state — which are triggered? Report count and which ones. Do NOT assess severity (that's pre-registered in the theory module).
3. Cross-theory attack — does another Active theory's mechanism contradict this hypothesis?
4. Evidence quality assessment — is the supporting evidence strong or weak? Grade: direct market data > high-quality macro data > proxies > narrative inference.
5. Composition integrity (multi-theory hypotheses only) — did combining theories narrow the prediction and make it more falsifiable? If not, KILLED as narrative padding.

Output per hypothesis: SURVIVED / WOUNDED / KILLED + full reasoning chain.

**The evaluator must NOT:**
- Assign conviction scores
- Decide whether soft falsifiers are "serious enough" to kill
- Recommend which survivors to act on
- Soften its attacks ("this is a minor concern" — if it's worth mentioning, state it plainly)

### Pass 4: Conviction Scoring (Mechanical — Python)
Three-stage mathematical pipeline. No LLM. No narrative.

**Stage 1: Raw Conviction (epistemic quality)**
Four dimensions, weighted:
- Support strength: 0.30 — current evidence actively supporting predictions
- Evidence quality: 0.30 — source quality, directness, recency, consistency
- Convergence: 0.25 — independent theories predicting same outcome (discounted for shared upstream dependencies)
- Falsifier clarity: 0.15 — how testable and specific are the failure conditions

```
RAW = S(0.30) + Q(0.30) + C(0.25) + F(0.15)
```
Range: 0.0 to 1.0

**Stage 2: Discounts (multiplicative)**

Soft falsifier health discount:
```
D_f = max(0.05, 1 - Σ(severity_weight_i) for each triggered soft falsifier)
```
Where: minor = 0.10, medium = 0.25, major = 0.45

Exposure overlap penalty:
```
D_o = 1 / (1 + overlap_count × 0.25)
```
Where overlap_count = number of other surviving hypotheses sharing the same primary instrument.

```
DISCOUNTED = RAW × D_f × D_o
SCORE = DISCOUNTED × 10
```

**Stage 3: Gates (hard caps on actionability)**

Horizon alignment (H), scored 0.0-1.0:
- H < 0.10 → capped at 1/10
- H < 0.25 → capped at 2/10
- H < 0.40 → capped at 4/10
- H ≥ 0.40 → no cap

Expression efficiency (E), scored 0.0-1.0:
- E < 0.15 → capped at 1/10
- E < 0.30 → capped at 3/10
- E ≥ 0.30 → no cap

```
FINAL = min(SCORE, horizon_cap, expression_cap)
```
Round to nearest integer. Output: 0-10 conviction signal.

### Pass 5: Human Decision Layer
The system presents scored survivors. The human decides. This is a frontend concern — see FRONTEND_SPEC_v1.md.

## Theory Module Registry

8 modules across 6 domains. Stored as structured markdown in `theories/`. The system must support N modules — do not hardcode 8.

| # | theory_id | Two-Phase? |
|---|-----------|-----------|
| 1 | valuation_mean_reversion | No |
| 2 | debt_cycle_short | Yes (Expansion / Contraction) |
| 3 | debt_cycle_long | No |
| 4 | structural_fragility | Yes (Building / Resolving) |
| 5 | fiscal_dominance_liquidity | No |
| 6 | fiscal_dominance_arithmetic | No |
| 7 | capital_flows | Yes (Accumulation / Rotation) |
| 8 | monetary_architecture | No |

Each module has: activation_conditions (with indicators, thresholds, weights), core_mechanism (causal chain), predictions_when_active (directional + conditional), downstream_implications, falsifiers (hard + soft with severity), and metadata.

See `docs/ECONOMIC_THEORIES_INTERFACE_CONTRACT.md` for the full interface contract.

## Theory Module Parsing

The theory modules are in markdown. You need to parse them into structured data for the activation layer and conviction scoring. The key sections to extract:

1. **activation_conditions** — the indicator tables with metric, threshold, direction, weight
2. **falsifiers.hard** — the hard falsifier table
3. **falsifiers.soft** — the soft falsifier table WITH severity column (minor/medium/major)
4. **predictions_when_active** — directional predictions with assets, magnitude, timeframe
5. **downstream_implications** — the affects[] table
6. **metadata** — the JSON block

Two-phase modules have separate activation condition tables for each phase. Parse both. The phase check order matters: check resolving/contraction/rotation first.

## Data Briefing Packet

The data agent produces a structured JSON briefing. Sources: FRED API (free key) + Yahoo Finance (yfinance). See `docs/DATA_INFRASTRUCTURE_BRIEF.md` for the full field list.

Key sections: growth, inflation, rates, liquidity, credit, sentiment, computed, markets.

The activation layer checks theory indicators against these field names. The field names in the theory modules' activation conditions reference briefing packet fields — they must match.

## Execution Model

The system is human-in-the-loop for LLM passes. The user:
1. Triggers the data agent (automated Python script)
2. Activation scoring runs mechanically
3. Copies the generation prompt to Claude.ai, pastes the output back
4. Copies the elimination prompt to Claude.ai, pastes the output back
5. Conviction scoring runs mechanically
6. Reviews results in the frontend

The Pipeline view in the frontend manages this workflow. See `docs/FRONTEND_SPEC_v1.md` Section 4.5.

Future: LLM passes could be automated via API. Design the prompt-building and output-parsing to support both copy-paste and API execution.

## Frontend

React 18 + Vite. Vanilla CSS with CSS variables (Hermes Editorial design system). No Tailwind. No charting library — hand-rolled SVG.

The hypothesis is the central data object. Everything is organized around the hypothesis ledger, not around theories or agents.

Six views: Ledger (home), Hypothesis Detail (modal), Journal, Observatory, Pipeline, Briefing.

See `docs/FRONTEND_SPEC_v1.md` for complete specifications including component tree, data shapes, API contracts, and build phases.

## Backend

FastAPI + SQLite. The backend serves the frontend and runs the mechanical passes (activation, conviction scoring).

Key tables: runs, hypotheses, journal_entries, inbox_items, user_state.

See `docs/FRONTEND_SPEC_v1.md` Section 6 for the full API contract and Section 10 for the SQLite schema.

## Design System: Hermes Editorial

Warm, muted, typographic. Feels like a quarterly letter from a private bank.

- **No emoji. Ever.** ASCII only.
- **No rounded corners** on containers.
- **No drop shadows, gradients, or fill effects.**
- Colors: cream backgrounds (#FAF7F2), dark text (#1C1917), brick red accent (#7C2D12), olive green (#365314), gold (#A16207), dark brick (#7F1D1D)
- Typography: Cormorant Garamond (display), EB Garamond (body), JetBrains Mono (data)
- Max width 1200px, generous whitespace, desktop-first
- Structure from line weight and whitespace, not decoration

See `docs/FRONTEND_SPEC_v1.md` Section 3 for full CSS variables and rules.

## What NOT To Build

- Automated trading or execution
- Portfolio optimizer or P&L tracker
- Real-time alerts or WebSocket streaming
- Authentication (runs locally)
- Dark mode
- Mobile input surfaces (mobile is read-only)
- AI chat interface ("talk to your hypotheses")
- Any component that asks the LLM for a conviction score or trade recommendation

## What NOT To Do Architecturally

- Do not let the generator rank hypotheses — it generates, period
- Do not let the evaluator score conviction — it attacks, period
- Do not use an LLM in the conviction scoring pipeline — it's math
- Do not collapse the five passes into fewer passes — the separation is the architecture
- Do not organize the frontend around theories or agents — organize around hypotheses
- Do not produce "balanced" or "hedged" outputs — the system takes positions through conviction scores, the hedge is in the falsification process
- Do not combine theories in ways that make hypotheses harder to falsify — the evaluator kills these
- Do not hardcode 8 theories — support N modules via the registry pattern

## File References

- `docs/ECONOMIC_THEORIES_INTERFACE_CONTRACT.md` — Theory module interface, activation scoring, composition rules
- `docs/FRONTEND_SPEC_v1.md` — Complete frontend specification with component tree, data shapes, API contracts
- `docs/DATA_INFRASTRUCTURE_BRIEF.md` — Data sources, ETF universe, briefing packet schema
- `docs/VISUAL_MENTAL_MODELS_SPEC.md` — SVG visualization designs (v2 feature, not v1)
- `docs/falsification_engine_brief.md` — Intellectual foundation, competitive landscape, design philosophy
- `theories/THEORY_MODULE_*.md` — The 8 theory modules (the intellectual core of the system)
- `plan.md` — Implementation plan with build phases
