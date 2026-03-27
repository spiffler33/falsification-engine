# PROJECT BRIEF: Falsification Engine for Global Macro
## Architecture Thread — Starting Document

*This document is the intellectual foundation for a new thread. It carries forward everything learned from the Macro Council design process and the "hypothesis generation vs view formation" research. The goal of the new thread is to design — through discussion, not monologue — a system that is architecturally faithful to how LLMs actually work, rather than forcing them into a role they are structurally unsuited for.*

*Read this entire document before responding. Then discuss, don't build.*

---

## PART 1: THE CORE INSIGHT (settled — do not re-derive, build on this)

### What LLMs Actually Optimize For

LLMs are trained via next-token prediction with cross-entropy loss. This produces a density estimator over plausible continuations — a system optimized to spread probability mass across all reasonable possibilities, weighted by contextual frequency. The architecture is structurally a **hypothesis generator**, not a **conviction engine**.

Specific consequences:

1. **Distributional, not point-predictive.** The softmax output at every step is a probability vector. The model is trained to be a bookie (set odds across all horses) not a bettor (pick one horse and size the stake). Cross-entropy rewards calibration, not conviction.

2. **Symmetric loss, asymmetric decisions.** In training, under-weighting a bullish continuation is penalized identically to under-weighting a bearish one. But real decisions have deeply asymmetric error costs — missing a hidden fragility that blows up a position is categorically worse than missing an upside scenario. Nothing in the loss function encodes this asymmetry.

3. **Branching, not converging.** Autoregressive generation is excellent at exploring conditional paths ("if X, then possibly Y or Z"). This is the backbone of hypothesis enumeration. But a committed view is a convergence operation — collapsing branches into one position. The architecture pulls one direction; the task demands the other.

4. **Frequency masquerades as conviction.** When distributional skew is overwhelming (95% of training contexts with conditions X, Y, Z lead to outcome A), the model looks like it has conviction. It has frequency. The distinction surfaces in novel situations, regime changes, or when a low-frequency variable dominates the outcome.

### The Precise Formulation

**LLMs are distributional reasoners trained on symmetric loss. View formation requires causal prioritization under asymmetric consequences.**

- Hypothesis generation asks: *what could be true?*
- View formation asks: *what is load-bearing, and what is the penalty if I'm wrong?*

LLMs excel at the first. They are structurally unsuited for the second.

### What This Means for System Design

Do not ask the model for the answer. Use the model to **destroy bad answers** — then apply consequence-bearing judgment (human or rule-based) to what survives.

**The model is a falsification engine, not an oracle.**

---

## PART 2: WHAT EVERYONE ELSE BUILDS (settled — this is the competitive landscape)

### The Universal Pattern

Every major open-source AI-for-investing project follows the same architecture:

```
Data → Agents (personas or roles) analyze/debate → Collapse to buy/sell/hold signal
```

| Project | Stars | Pattern | Why It Fails |
|---------|-------|---------|-------------|
| AI Hedge Fund (virattt) | ~49.5k | 12 persona agents vote → PM signal | Committee theater. Personas form views, not prune them. |
| TradingAgents (Tauric) | ~38k | Analyst → bull/bear debate → trader → risk veto | Debate serves consensus, not falsification. Best architecture of the lot but still collapses to a view. |
| FinRobot (AI4Finance) | ~3k | Forecasting agents → equity reports → signals | Report generator. Collapses to directional forecasts. |

### What None of Them Do

- Treat the problem as hypothesis pruning rather than prediction
- Score conviction or uncertainty (no Bayesian updating, no confidence intervals, no Kelly sizing)
- Separate pipeline stages: generate possibilities → form conviction → size position → monitor downside
- Incorporate asymmetric risk structurally (not as a prompt, as architecture)
- Combine LLM reasoning with deterministic quantitative models
- Publish calibrated, walk-forward results

### The Architectural Error

They jam four distinct cognitive operations into one undifferentiated LLM loop. They force the model to do Layer 4 work (commit under asymmetry) using Layer 1 architecture (distributional search). This is the category error our system must not repeat.

---

## PART 3: THE FOUR-LAYER FRAMEWORK (settled as conceptual scaffold — implementation is open)

### Layer 1: Search (LLM-native)

Generate candidate hypotheses: explanations, hidden variables, second-order effects, edge cases, analogies, historical parallels. The task is combinatorial, retrieval-heavy, and rewards breadth. The model's distributional training is perfectly suited.

*Use the model aggressively here. Temperature, breadth, tolerance for contradiction.*

### Layer 2: Compression (LLM-assisted, bias-corrected)

Rank which hypotheses deserve further attention. LLMs can help but tend to flatten importance toward salience (popularity bias) and recency. This layer needs domain-weighted priors — possibly hybrid: LLM generates ranking, calibrated quantitative logic adjusts for base rates and frequency biases.

*The model helps here but should not have final say.*

### Layer 3: Causal Prioritization (LLM-limited, human/rule-heavy)

Determine which mechanisms are actually decisive. Many causal stories are coherent; few are decision-relevant. The bottleneck is not narrating causation but prioritizing which causal structure is load-bearing under uncertainty.

This layer should combine:
- LLM-generated stress tests and counterfactuals ("what would kill this thesis?")
- Structured elimination protocols (explicitly falsify each hypothesis against data)
- Human or rule-based judgment on which survivals warrant action

*The model is a tool here, not the decision-maker.*

### Layer 4: Action Under Asymmetry (quantitative + human)

Choose despite incomplete knowledge, with unequal penalties for different errors. Size the position. Define exit conditions. Set failure criteria. This layer should be overwhelmingly quantitative and human-governed. The LLM's role is narrow: stress-test the chosen view, monitor for disconfirming evidence, flag assumption violations.

*The model is a watchdog here, not the pilot.*

### Critical Design Principle

**These layers are not a pipeline the model runs end-to-end.** They are distinct cognitive operations with different optimal tools. Different prompts. Different models potentially. Different interfaces. The system boundary between layers is where architectural integrity lives.

---

## PART 4: WHAT WE LEARNED FROM MACRO COUNCIL (carry forward selectively)

### What Worked in the Design

1. **Economic theories as the structural core.** Plan v3's shift from "personas producing narratives" to "economic theories applied through a hypothesis pipeline" was the right move. The theories — valuation mean reversion, debt cycle mechanics, structural fragility, fiscal dominance, capital flow dynamics, monetary system architecture — are domain lenses, not personalities. They should survive into the new system.

2. **The hypothesis pipeline concept.** Generate → test → eliminate → report survivors. This was the intellectual innovation in plan_v3 and it directly anticipates the falsification-engine architecture. The schema with hypotheses containing mechanism, prediction, evidence_for, evidence_against, status, failure_conditions — that's good. It needs refinement, not replacement.

3. **The data agent separation.** Fetching and computing market data is a deterministic task. Keeping it separate from the interpretive/analytical agents was correct. The briefing packet concept (structured JSON with growth, inflation, rates, liquidity, credit, sentiment, markets) is solid infrastructure.

4. **The war room as synthesis layer.** Cross-referencing independent analyses to find confirmed, contested, and orphan signals — this is the right output structure. The implementation needs to change (it was still collapsing toward "views") but the concept is sound.

5. **The visual mental models.** Each agent having a distinct cognitive visualization (gauge, cycle compass, stress map, flow diagram, triangle, capital flow map, plumbing schematic) was a strong design decision. Visualizing the *shape* of each analytical lens, not just the conclusion, supports the ADHD-compatible scanning workflow the user needs.

### What Was Wrong or Incomplete

1. **Personas as the organizing unit.** "You are Warren Buffett" is asking the model to form views. Even plan_v3's shift to "economic theories with personality as incidental" didn't go far enough — the prompt architecture still centered on producing a narrative in someone's voice. The new system should organize around **analytical domains**, not people.

2. **All agents doing the same job.** Every agent generated hypotheses AND formed views AND suggested trades. That's the undifferentiated loop problem. Different layers of the framework should be handled by different system components — not all by one monolithic agent prompt.

3. **No explicit elimination step.** The hypothesis pipeline in plan_v3 asked agents to report hypothesis status (SUPPORTED / WEAKENED / DISCONFIRMED). But the elimination was self-reported by the same agent that generated the hypothesis. That's asking the prosecutor to also be the judge. Elimination should be adversarial — a separate pass, possibly a separate prompt, specifically tasked with attacking the hypothesis.

4. **No asymmetric risk handling.** "Risk" in the macro council was "what could go wrong" stated narratively. There was no structural mechanism for: asymmetric loss weighting, position sizing from conviction, or distinguishing "this might not work" from "this could blow up."

5. **War room collapsed to opinion averaging.** Despite the design intent, the war room synthesis was still fundamentally: collect 6 views → find where they agree → that's the signal. A falsification-engine war room should instead: collect surviving hypotheses → identify which have withstood the most attacks → flag which are untested → highlight what evidence would change everything.

6. **No feedback loop.** No mechanism to track: which hypotheses survived → which were acted on → what actually happened → what the system should update. Without this, the system cannot improve.

---

## PART 5: THE USER (context for design decisions)

- 20-year trading desk veteran (volatility trading, risk management, Deutsche Bank Global Emerging Markets)
- Managing ~$1.5M personal capital through liquid ETFs on Interactive Brokers
- ~1 month holding periods, global macro, not a fund
- ADHD-compatible work patterns: needs systems that work with curiosity and intermittent bursts of focus, not rigid daily routines
- Learns by writing — plans to blog publicly about macro views
- Bloomberg access at work, but this system runs independently at home
- Current stack: IBKR for execution, 42 Macro, Lyn Alden, FT, MacroMicro, Feedly Pro, Claude Max
- Key influences: Drobny books, Manual of Ideas, Ben Thompson/Stratechery
- Describes self as a businessman who builds processes and systems, not a trader
- This is a thinking system, not a trading system. It produces views (for the human), not orders.

### What the User Actually Needs

A system that, in ~30-45 minutes of engagement per day (some days more, some days zero), gives him:

1. A structured scan of the macro landscape through multiple theoretical lenses
2. Hypotheses that have been generated AND attacked — not just "here are some ideas" but "here's what survives scrutiny"
3. A clear view of where theories agree, disagree, and where the evidence is thin
4. Specific prompts for his own thinking: "this is the question you should be wrestling with today"
5. Over time, a written record of hypotheses, eliminations, and outcomes that becomes a learning corpus

**He does NOT need:**
- Automated trading signals
- A portfolio optimizer
- Real-time alerts
- A system that tells him what to do

**He DOES need:**
- A system that shows him what to think about
- A system that attacks his existing views
- A system that surfaces what he might be missing
- A system that tracks whether his reasoning was right or wrong after the fact

---

## PART 6: ECONOMIC THEORIES TO CARRY FORWARD (the structural evidence base)

These are the domain lenses. They are not personas. They are testable theoretical frameworks, each with a core mechanism, historical evidence, leading indicators, predictions, and failure conditions.

### 1. Valuation Mean Reversion & Margin of Safety
**Core mechanism:** Asset prices oscillate around intrinsic value. When equity risk premium compresses below zero, rational allocators have no incentive to bear equity risk. Capital flows to risk-free instruments. Resolution: drawdown.
**Key metrics:** Buffett Indicator, Shiller CAPE, equity risk premium, sector P/E and P/B, cash yield
**Failure modes:** Permanently higher margins, structural low r*, financial repression, currency devaluation inflating nominal prices

### 2. Debt Cycle Mechanics (Short-term + Long-term)
**Core mechanism:** Credit expansion amplifies activity until debt service exceeds income growth. Two overlapping cycles: short-term (5-8 years, rate policy) and long-term (50-75 years, ZLB forces escalation to QE then fiscal-monetary coordination).
**Key metrics:** ISM, unemployment, credit spreads, yield curve, Fed balance sheet, debt/GDP, MP classification
**Failure modes:** Productivity revolution extending cycle, orderly deleveraging, dollar reserve status maintained

### 3. Structural Fragility (Minsky Dynamics)
**Core mechanism:** Stability is destabilizing. Low vol + easy credit + rising prices → progressive risk-taking → concentration amplifies through passive flows → non-linear drawdown when turn comes.
**Key metrics:** Top-10 concentration, HY spreads, VIX vs realized gap, margin debt, capex/revenue mismatch, QQQ/IWM divergence
**Failure modes:** Central bank backstop, earnings delivery, continued passive inflows

### 4. Fiscal Dominance
**Core mechanism:** When deficit spending is large enough, it overwhelms monetary policy. Rate hikes become stimulative (higher interest expense = larger deficit = more spending). Net liquidity drives asset prices. Fiscal arithmetic forces eventual devaluation.
**Key metrics:** Deficit pace, net liquidity, interest expense (% of receipts), gold/oil ratio, foreign Treasury holdings, hard vs nominal asset performance
**Failure modes:** Genuine fiscal consolidation, productivity boom >4% GDP growth, deflation shock

### 5. Capital Flow Dynamics & Multipolar Rebalancing
**Core mechanism:** Capital flows to highest risk-adjusted returns. Persistent Western home bias creates systematic EM mispricing. Dollar weakening permits EM outperformance. China credit impulse is global demand catalyst.
**Key metrics:** RMB direction, DXY, China PMI, EM/DM relative PE, EEM vs SPY, China credit impulse
**Failure modes:** Dollar strengthening, China structural decline, US productivity miracle, geopolitical fragmentation

### 6. Monetary System Architecture & Collateral Theory
**Core mechanism:** Collateral substitution — central banks replacing Treasuries with gold as reserve assets post-2022 sanctions. Plumbing stress (basis swaps, repo rates, term premium) leads prices.
**Key metrics:** CB gold purchases, Treasury foreign holdings %, SWIFT dollar share, RRP, term premium, cross-currency basis
**Failure modes:** Geopolitical detente, no credible dollar alternative, US fiscal discipline, gold capacity limits

---

## PART 7: OPEN QUESTIONS FOR THIS THREAD

These are the design decisions we need to make through discussion. Do not resolve them in your first response — discuss, probe, propose options, let me react.

### A. What is an "agent" in this system?

The macro council had 6 agents, each applying one economic theory. Is that the right abstraction? Alternatives:

- **Domain agents** (one per theoretical lens, similar to current but stripped of persona)
- **Function agents** (one generates hypotheses, one attacks them, one synthesizes — functional separation rather than domain separation)
- **Hybrid** (domain agents for Layer 1-2, functional agents for Layer 3-4)
- **No agents at all** (a single sophisticated prompt pipeline with different stages, not different "agents")

The word "agent" may itself be misleading. It implies autonomy and view-formation. Maybe what we need are "lenses" and "passes" — not actors with opinions, but analytical operations applied sequentially.

### B. How does elimination actually work?

This is the hardest design question. Options:

- **Self-elimination:** Each domain generates hypotheses and also stress-tests them (current macro council approach — known to be weak because prosecutors shouldn't judge their own cases)
- **Cross-elimination:** Domain A's hypotheses are attacked by Domain B's framework (creates interesting tensions: fiscal dominance hypothesis tested against debt cycle theory)
- **Dedicated adversary:** A separate "red team" pass whose only job is to find the weakest point in each surviving hypothesis
- **Data-driven elimination:** Hypotheses generate specific testable predictions → system checks predictions against actual data → mechanical pass/fail
- **Some combination**

### C. Where does the human enter the loop?

In the macro council, the human entered at the end: read the outputs, form own view. In the falsification engine, where is human judgment most valuable?

- After Layer 1 (curate which hypotheses are worth testing)?
- After Layer 3 (decide which survivors to act on)?
- As the adversary (the human IS the red team)?
- As the updater (the human feeds back outcomes and adjusts the system)?

### D. What is the output?

The macro council output was: 6 agent reports + war room synthesis + expression menu. What should the falsification engine output?

- A ranked list of surviving hypotheses with confidence and failure conditions?
- A "what to think about today" briefing?
- A decision journal that the human completes?
- An interactive system where the human can interrogate each hypothesis?
- Something else?

### E. Execution model?

The macro council moved to copy-paste-into-Claude-Opus. Is that still right? Options:

- Keep copy-paste (maximum quality, maximum flexibility, ~30 min/day)
- API-driven automation (lower quality per call if using Sonnet, but hands-free)
- Hybrid (data agent automated, analytical passes manual in Claude)
- Web app with structured prompt chains (the system prompts the human, not the other way around)

### F. What is the minimum viable version?

What is the smallest thing we could build that would:
1. Demonstrate the falsification-engine architecture working
2. Produce output good enough to use for real capital decisions
3. Be presentable as a tweetstorm + repo

### G. What do we call this?

"Macro Council" was the persona-era name. If the system is now a falsification engine organized around economic theories rather than investor personalities, what is it?

---

## PART 8: SUCCESS CRITERIA

The system succeeds if:

1. It produces hypotheses that are **attacked before the user sees them** — the user receives survivors, not candidates
2. It clearly separates **what the model found** from **what the user must decide**
3. It handles **asymmetric risk** structurally — fragile theses are eliminated more aggressively than robust ones are promoted
4. It creates a **written record** that enables learning over time
5. It is **usable in 30-45 minutes** on days when the user engages, and degrades gracefully on days he doesn't
6. It is **architecturally novel** relative to the landscape — not another committee simulator
7. A reader of the tweetstorm would understand immediately why this is different and want to fork it

---

*Now: read this, sit with it, and let's discuss. Start with whatever question or reaction is most alive for you. Don't try to solve everything at once.*
