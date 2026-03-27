# Visual Mental Models -- Design Specification
## Macro Council Agent Visualization System

---

## Table of Contents

1. Design Philosophy & Rendering Approach
2. The Trajectory Question (answered)
3. Data Agent Gaps (flagged)
4. Seven Agent Visualizations (detailed designs)
5. Visual Data Schema (per agent)
6. Agent Prompt Additions (template)
7. Implementation Plan

---

## 1. Design Philosophy

Each visualization is a **cognitive artifact** -- it matches how that analyst
actually structures information in their head. Buffett sees a weighing machine.
Dalio sees interlocking cycles. Burry sees a building under stress. Pozsar sees
plumbing. These are not dashboards; they are mental models rendered in ink.

**Why this matters for you specifically:** You have ADHD-compatible work patterns.
Seven 500-word essays will blur. Seven distinct visual shapes -- a gauge, a cycle,
a stress map, a flow diagram -- land in different cognitive slots. You should be
able to glance at the Agent page for 3 seconds and know the shape of their view
before reading a word.

### Aesthetic Rules (extending Hermes Editorial)

- **SVG-first.** Every visualization is a React component rendering inline SVG.
  No charting library. No canvas. Pure declarative SVG with CSS variables.
- **Hand-annotated feel:** Thin 1px strokes. No fill gradients. No drop shadows.
  No rounded corners on containers. Structure from line weight and whitespace.
  Annotations use thin leader lines with small text, like marginalia.
- **Color from the palette only.** No traffic-light red/amber/green.
  - Stress/danger: `--accent-negative` (#7F1D1D dark brick)
  - Health/calm: `--accent-positive` (#365314 deep olive)
  - Emphasis/signal: `--accent-gold` (#A16207 warm gold)
  - Neutral/dormant: `--text-tertiary` (#A8A29E warm gray)
  - High conviction: `--accent-high` (#7C2D12 burnt sienna)
  - Background fills: `--bg-inset` (#F5F1EB) or `--bg-secondary` (#F0EBE3)
- **Typography in SVG:**
  - Titles/labels: Cormorant Garamond, small-caps, letter-spaced
  - Data values: JetBrains Mono, always
  - Annotations: EB Garamond italic, small
- **Dimensions:** Each SVG is max 720px wide (fits within 1200px layout with
  generous margins), 400-550px tall. Responsive down to 640px.

### Page Layout (Agent Detail Page)

```
+------------------------------------------------------------+
|  BUFFETT  (Cormorant, small-caps, letter-spaced)           |
|  "Overvalued -- Patience Required"                         |
|  2026-03-21 :: confidence 0.82                             |
+------------------------------------------------------------+
|                                                            |
|          [ VISUAL MENTAL MODEL ]                           |
|          (the primary read -- SVG, ~450px tall)            |
|                                                            |
+------------------------------------------------------------+
|                                                            |
|   THEMES               |   TRADE IDEAS                     |
|   (1-2 cards)          |   (1-3 cards)                     |
|                        |                                   |
+------------------------------------------------------------+
|                                                            |
|   MACRO NARRATIVE                                          |
|   (the 400-700 word essay, EB Garamond body)               |
|   This is the deep dive. Read it when the visual           |
|   raises a question.                                       |
|                                                            |
+------------------------------------------------------------+
```

---

## 2. The Trajectory Question

**Answer: Current state as primary. 90-day trail as secondary annotation.**

A single-day snapshot is noise. You know this from vol trading -- you never looked
at a single VIX print without the term structure and recent path. But the visual
must not become a time-series chart. The mental model IS the current state; the
trail provides context for whether things are getting better or worse.

**Implementation:**

- Store each agent's `visual_data` in SQLite alongside the existing output.
  You already store runs with timestamps -- add a `visual_data` JSON column.
- On the frontend, query last 90 days of `visual_data` for the active agent.
- Each visualization shows trail differently (see agent-specific designs below):
  - **Dalio:** Dotted path showing where the cycle-position dot has traveled.
  - **Burry:** Tiny 90-day sparklines next to each stress bar.
  - **Buffett:** Ghost needles on the gauge at 30/60/90 days ago.
  - **Alden:** Trend arrows (up/down/flat) on each flow metric vs 30d ago.
  - **Gromen:** Edge thickness change annotations ("stressed +2 vs 30d ago").
  - **Gave:** Faded arrows showing prior capital flow directions.
  - **Pozsar:** Sparklines on key plumbing metrics.

- Trail always rendered in `--text-tertiary` at reduced opacity. Never competes
  with current state.

**Why 90 days:** Your holding period is ~1 month. 3x gives enough context to see
regime shifts forming. Also pragmatically: daily runs x 90 days = 90 stored
snapshots per agent, which is trivial in SQLite.

---

## 3. Data Agent Gaps

The current briefing packet (FRED + Yahoo) is **good enough for 5 of 7 agents**
but has real gaps for Gave and Pozsar especially. Here is the audit:

### Currently Available (sufficient)

| Agent | Needs | Covered By |
|-------|-------|------------|
| Buffett | Valuations, credit spreads, yields, SPY | FRED (yields, spreads) + Yahoo (SPY, SHY) + web search (CAPE, Buffett Indicator) |
| Dalio | Growth, inflation, rates, liquidity, credit | FRED (all macro series) + Yahoo (cross-asset) |
| Burry | Credit spreads, VIX, sector concentration, rates | FRED (spreads) + Yahoo (VIX, sector ETFs, IWM/SPY ratio) |
| Alden | Deficits, interest expense, net liquidity, hard assets | FRED (Fed BS, TGA, RRP) + Yahoo (GLD, IBIT, TIP) + web search (deficit data) |
| Gromen | Interest expense, gold, oil, dollar, yields | FRED (yields) + Yahoo (GLD, USO, UUP, DBC) + web search (fiscal data, auction data) |

### Gaps to Fill

| Agent | Missing Data | Proposed Source | Priority |
|-------|-------------|-----------------|----------|
| **Gave** | RMB/USD exchange rate | Yahoo: add `CNYUSD=X` | HIGH -- his #1 indicator |
| **Gave** | China PMI (manufacturing + services) | Web search only (no free API) -- agent gets this via search | MEDIUM |
| **Gave** | EM vs DM relative PE | Web search only -- agent gets this via search | MEDIUM |
| **Gave** | EM capital flow data | Web search only | LOW |
| **Pozsar** | Cross-currency basis swaps | Not available free. Agent must web search. | MEDIUM |
| **Pozsar** | Central bank gold purchases (annual/quarterly) | Web search only | MEDIUM |
| **Pozsar** | SWIFT payment share data | Web search only (IMF/BIS reports) | LOW |
| **Pozsar** | Treasury term premium | FRED: add `THREEFYTP10` (10Y term premium, NY Fed model) | HIGH |
| **All** | SPY P/E ratio (for equity risk premium calc) | Yahoo: can derive from SPY price + earnings data, or web search | MEDIUM |
| **Gromen** | Gold/Oil ratio | Compute from Yahoo: GLD price / USO price (proxy) | HIGH -- signature metric |
| **Dalio** | Monetary policy stance classification | Agent infers from rates data -- no new source needed | N/A |

### Recommended Data Agent Additions

```python
# Add to FRED_SERIES:
"TERM_PREMIUM_10Y": "THREEFYTP10",    # Pozsar needs this

# Add to YAHOO_TICKERS["other"]:
"CNYUSD=X",   # RMB/USD for Gave
"DX-Y.NYB",   # DXY index (more standard than UUP for dollar direction)

# Add to computed metrics in briefing.py:
"gold_oil_ratio": GLD_price / USO_price,   # Gromen signature metric
"net_liquidity": fed_bs - tga - rrp,       # Already implied, make explicit
"spy_hy_spread_combined": ...,             # Burry uses this cross-signal
"em_us_relative": EEM_return - SPY_return, # Gave relative performance
```

### What Stays as Web Search

Deficit pace, interest expense, China PMI, central bank gold purchases, SWIFT data,
Treasury auction metrics -- these are all qualitative/narrative data that the agents
source via their web search queries. They don't need to be in the structured
briefing packet. The agents' prompts already specify the exact search strings.

**Key point:** The `visual_data` schema I define below only requires data that the
agent can obtain from the briefing packet + its web searches. The agent produces
the visual_data; the frontend just renders it. No additional backend computation
needed beyond the 4 additions above.

---

## 4. Seven Agent Visualizations

---

### 4.1  BUFFETT -- The Valuation Gauge

**Mental model:** A weighing machine. Is the market cheap or expensive? Three
concentric semicircular gauges (like a vintage instrument panel), each with a
needle. One glance tells you: expensive, and here's the opportunity cost of
owning equities.

**Visual description:**

```
          THE WEIGHING MACHINE

    Buffett Indicator   1.87
    ╭────────────────────╮
    │  ◠◠◠◠◠◠◠◠◠◠◠◠◠◠  │   ← outer arc: Buffett Indicator
    │   ◠◠◠◠◠◠◠◠◠◠◠◠   │   ← middle arc: Shiller CAPE
    │    ◠◠◠◠◠◠◠◠◠◠    │   ← inner arc: Equity Risk Premium
    │         ↑          │
    │       needle       │
    ╰────────────────────╯

    CAPE  36.2          ERP  0.4%
    ────────────────────────────
    Cash yield (SHY): 4.8%
    "Cash pays you to wait."
```

**Three arcs, each a 180-degree semicircle:**

1. **Outer arc -- Buffett Indicator** (Market Cap / GDP)
   - Scale: 0.6 to 2.2
   - Zones: Cheap (0.6-0.8, olive), Fair (0.8-1.2, warm gray), Expensive (1.2-1.6, gold), Extreme (1.6+, brick)
   - Needle position shows current reading with JetBrains Mono value label

2. **Middle arc -- Shiller CAPE**
   - Scale: 10 to 45
   - Zones: Cheap (<17, olive), Fair (17-25, warm gray), Elevated (25-35, gold), Danger (35+, brick)
   - Historical average marked with a thin tick line

3. **Inner arc -- Equity Risk Premium**
   - Scale: -2% to +8%
   - Zones: Negative/zero (brick), Thin (<2%, gold), Adequate (2-4%, warm gray), Fat (4%+, olive)
   - This arc runs INVERTED: left is dangerous (low ERP), right is attractive (high ERP)

**Below the gauge:** Single line in EB Garamond italic showing the cash yield
(SHY rate) and Buffett's verdict. This is computed by the agent: one of
"Cash pays you to wait." / "Prices are approaching fair value." /
"The arithmetic is becoming attractive."

**Trajectory:** Three ghost needles per arc at 30/60/90 days, rendered as thin
lines in `--text-tertiary` at 30% opacity. Shows direction of travel.

**Action verdict badge:** Below the gauge, a simple text badge:
`PATIENCE` / `SELECTIVE` / `DEPLOY` in small-caps, letter-spaced.

---

### 4.2  DALIO -- The Cycle Compass

**Mental model:** The economic machine. Two overlapping cycles (short-term debt
cycle and long-term debt cycle) with current position marked. Plus a monetary
policy indicator showing which "tool" is active.

**Visual description:**

```
         THE ECONOMIC MACHINE

   Long-term debt cycle
   ╭──────────────────────────────╮
   │                              │
   │    Early ──── Peak           │
   │     │    ╲  ╱    │           │
   │     │     ●     │  ← current │
   │     │    ╱  ╲    │  position  │
   │    Trough ── Late            │
   │                              │
   │   Short-term debt cycle      │
   │   [similar smaller circle    │
   │    with position marked]     │
   ╰──────────────────────────────╯

   ┌─────────┬─────────┬─────────┐
   │  MP1    │  MP2    │  MP3    │
   │ rates   │ QE/QT   │ fiscal  │
   │         │  ████   │         │
   └─────────┴─────────┴─────────┘
   Active: MP2 (QT) → MP3 transition
```

**Two concentric elliptical cycle tracks:**

1. **Outer ring -- Long-term debt cycle** (~75-100 year)
   - Four quadrants labeled: Early Expansion / Bubble / Deleveraging / Reflation
   - Current position shown as a filled dot on the ring
   - Agent places this based on debt/GDP, asset prices, monetary policy extremity
   - The ring is drawn as a continuous path with quadrant labels at 12/3/6/9 o'clock

2. **Inner ring -- Short-term debt cycle** (~5-10 year)
   - Four phases: Early Cycle / Mid Cycle / Late Cycle / Contraction
   - Separate position dot (smaller)
   - These can be in different quadrants (e.g., late short-term cycle within
     a long-term bubble phase)

**Below the cycles -- Monetary Policy bar:**

Three adjacent rectangles labeled MP1 / MP2 / MP3:
- MP1: Interest rate policy (conventional)
- MP2: Quantitative easing/tightening (balance sheet)
- MP3: Fiscal-monetary coordination (deficit spending)

The active policy is filled with `--accent-gold`. A transition arrow shows
direction if shifting between regimes.

**Growth/Inflation quadrant overlay** (small, top-right corner):
A tiny 2x2 grid showing the Layer 1 regime position from Dalio's perspective:
- Goldilocks / Reflation / Stagflation / Deflation
- Dot showing current position, matching his regime_assessment

**Trajectory:** The cycle position dots leave a dotted trail (last 90 days of
positions on both rings). You can see if the short-term cycle is progressing
clockwise (normal) or moving erratically.

---

### 4.3  BURRY -- The Stress Fracture Map

**Mental model:** A building's structural assessment. Each load-bearing element
is rated for stress. When too many elements are strained simultaneously, the
structure fails. He's looking for the thing that's about to break.

**Visual description:**

```
         STRESS FRACTURES

   CREDIT         ████████████░░░  82%
   spread stress  ──────────────────── ← sparkline (90d)

   VALUATION      █████████████░░  87%
   CAPE/earnings  ──────────────────── ← sparkline (90d)

   SPECULATION    ██████████████░  93%  ← THIS ONE SCREAMS
   concentration  ──────────────────── ← sparkline (90d)

   LEVERAGE       ████████░░░░░░░  55%
   margin/debt    ──────────────────── ← sparkline (90d)

   VOLATILITY     ███░░░░░░░░░░░░  22%
   VIX/skew       ──────────────────── ← sparkline (90d)

   LIQUIDITY      ██████████░░░░░  68%
   funding stress ──────────────────── ← sparkline (90d)

   ─────────────────────────────────────
   STRUCTURAL INTEGRITY: COMPROMISED
   "The concentration in mega-cap tech
    is historically unprecedented."
```

**Six horizontal stress bars**, each representing a domain Burry monitors:

1. **Credit Stress** -- HY spread percentile vs 10-year range + IG spread
2. **Valuation Excess** -- CAPE vs history, SPY PE, concentration premium
3. **Speculative Intensity** -- Top-heaviness (QQQ/IWM divergence as proxy for
   mega-cap concentration), momentum extremity
4. **Leverage** -- Margin debt levels (web search), credit growth
5. **Volatility Complacency** -- VIX level + VIX vs realized vol gap
6. **Liquidity Fragility** -- Bid-ask proxies, RRP levels, funding conditions

Each bar is 0-100% (a percentile vs. that metric's historical range).

**Visual treatment:**
- Bars fill left-to-right.
- Fill color shifts from `--accent-positive` (low stress, <30%) through
  `--text-tertiary` (moderate, 30-60%) through `--accent-gold` (elevated,
  60-80%) to `--accent-negative` (extreme, 80%+).
- The HIGHEST stress bar gets extra visual weight: thicker bar, the value
  label is in `--accent-negative`, and a thin annotation line extends right
  with Burry's one-line comment on that specific risk.
- A tiny 90-day sparkline sits below each bar (40px wide, 12px tall) showing
  the trajectory of that metric.

**Bottom verdict:** "STRUCTURAL INTEGRITY:" followed by one of:
`SOUND` / `HAIRLINE CRACKS` / `COMPROMISED` / `CRITICAL`
Plus Burry's one-sentence summary of the primary risk.

**The key design insight:** Most of the time, several bars are moderate and one
or two are extreme. That asymmetry IS the signal. When everything is moderate,
Burry has nothing to say. When one bar is at 95%, that's his short thesis.

---

### 4.4  ALDEN -- The Fiscal Dominance Engine

**Mental model:** A flow diagram showing how fiscal policy is the primary
transmission mechanism, not monetary policy. Money flows from left to right:
fiscal deficit → financial system → asset prices. With a bypass showing that
monetary policy (rates) is being overwhelmed.

**Visual description:**

```
         THE FISCAL ENGINE

   ┌─────────────┐         ┌──────────────┐         ┌─────────────┐
   │   DEFICIT    │────────>│  NET         │────────>│  ASSET      │
   │   PACE       │         │  LIQUIDITY   │         │  RESPONSE   │
   │              │         │              │         │              │
   │  $2.1T ann.  │  flow   │  $5.8T       │  flow   │  GLD +14%   │
   │  ▲ rising    │  ════>  │  ▲ expanding │  ════>  │  IBIT +42%  │
   │              │         │              │         │  SPY +8%    │
   └─────────────┘         └──────────────┘         │  TLT -6%    │
         │                        ▲                  └─────────────┘
         │                        │
         ▼                        │
   ┌─────────────┐         ┌──────────────┐
   │  INTEREST    │────────>│  FED BALANCE │
   │  EXPENSE     │  forces │  SHEET       │
   │              │         │              │
   │  $1.1T ann.  │         │  $7.4T       │
   │  18% of rev  │         │  ▼ QT but    │
   │              │         │    slowing    │
   └─────────────┘         └──────────────┘

   ┌──────────────────────────────────────┐
   │  MONETARY POLICY (RATES): 5.25%     │
   │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
   │  effectiveness: DIMINISHED           │
   │  (fiscal stimulus > monetary drag)   │
   └──────────────────────────────────────┘
```

**Five nodes in an L-shaped flow:**

Top row (left to right):
1. **Deficit Pace** -- Annual deficit run-rate, direction arrow, context vs history
2. **Net Liquidity** -- Fed BS minus TGA minus RRP, direction, level
3. **Asset Response** -- Hard assets (GLD, IBIT, SLV) returns + nominal assets (SPY) + losers (TLT)

Bottom row (left, connecting up to Net Liquidity):
4. **Interest Expense** -- Annualized, as % of revenue, with the "math doesn't work" threshold annotated
5. **Fed Balance Sheet** -- Level, direction (QT/QE/pause), whether being forced to expand

**Connection arrows:** Thick when flow is strong (deficit is large AND net
liquidity is expanding AND assets responding). Thin/dashed when the connection
is weak or broken.

**Below the flow: Monetary Policy effectiveness bar.** A single horizontal bar
showing the agent's assessment of monetary policy effectiveness (0-100%).
At 0% monetary policy is completely dominated by fiscal. At 100% monetary
policy is primary driver. In fiscal dominance, this bar is mostly empty.

**Trajectory:** Each node value shows direction arrow (▲/▼/►) plus a small
"vs 30d" annotation showing the change.

---

### 4.5  GROMEN -- The Nexus Triangle

**Mental model:** Three forces in tension -- the Dollar, Energy, and the
Fiscal Position. Connected by edges that can be stable or stressed. Gold
sits at the center as the release valve. When the triangle's edges are all
stressed, gold must rise.

**Visual description:**

```
            THE NEXUS

           FISCAL
          ╱$1.1T int ╲
         ╱  expense    ╲
        ╱  ▲ STRESSED   ╲
       ╱                  ╲
      ╱                    ╲
   DOLLAR ──────────────── ENERGY
   UUP -3%    petrodollar   USO +8%
   weakening   fracturing    rising

              ◉
            GOLD
           GLD +14%
          "the release
             valve"

   ──────────────────────────
   THE MATH:
   Interest expense: $1.1T
   Defense spending: $886B
   Tax receipts:     $4.8T
   Int/Receipts:     23%
   ──────────────────────────
   Verdict: UNTENABLE
```

**Three nodes at the vertices of an equilateral triangle:**

1. **FISCAL** (top) -- Interest expense level, deficit pace, the arithmetic
2. **DOLLAR** (bottom-left) -- UUP direction, reserve status indicators
3. **ENERGY** (bottom-right) -- USO/DBC direction, petrodollar status

**Three edges connecting them:**
- **Fiscal ↔ Dollar:** Does the fiscal position threaten dollar credibility?
  Edge labeled with status: STABLE / STRAINED / FRACTURING
- **Dollar ↔ Energy:** Petrodollar system status. Is energy trade moving
  away from dollar settlement?
  Edge labeled: INTACT / SHIFTING / FRACTURING
- **Energy ↔ Fiscal:** Does energy cost worsen the fiscal position?
  Edge labeled: MANAGEABLE / STRAINED / CRITICAL

Each edge has a thickness proportional to stress level (1px = stable,
2px = strained, 3px = fracturing). Color shifts from `--text-tertiary`
through `--accent-gold` to `--accent-negative`.

**Center node -- GOLD:** The release valve. Shows GLD return, direction,
and Gromen's gold/oil ratio.

**Below the triangle: "THE MATH" box.** A small table of the 4-5 fiscal
arithmetic numbers that Gromen hammers every week. Interest expense vs.
defense spending vs. tax receipts. Verdict: SUSTAINABLE / STRAINED / UNTENABLE.

**Trajectory:** Edge thickness 90 days ago shown as a faint dashed line
alongside the current edge. If edges are thickening, the triangle is
getting more stressed.

---

### 4.6  GAVE -- The Capital Flow Map

**Mental model:** A stylized world map (not a literal map -- an abstract
geographic arrangement) showing where capital is flowing. Arrows between
regions. Arrow thickness = flow magnitude. The dollar is the gravity field.

**Visual description:**

```
          CAPITAL FLOWS

                  DOLLAR: WEAKENING ▼
          ┌────────────────────────────┐
          │         ◇ dollar           │
          │       ╱     ╲              │
          │     ╱         ╲            │
          │   ╱             ╲          │
   ┌──────┤ ╱               ╲ ┌───────┐
   │ US   │←─────────────────→│ CHINA  │
   │      │   rotating out    │        │
   │SPY+8%│   ══════════════> │FXI+18% │
   │QQQ+5%│                   │KWEB+22%│
   └──────┘                   └────────┘
       │                          │
       │          ┌───────┐       │
       └─────────>│ INDIA  │<─────┘
                  │INDA+12%│
                  └───────┘
       │          ┌───────┐
       └─────────>│EUROPE │
                  │VGK+6% │
                  └───────┘

   CONVICTION MAP:
   China   ████████████████  HIGH
   India   ████████████░░░░  MEDIUM
   Europe  ████████░░░░░░░░  MEDIUM
   Japan   ████░░░░░░░░░░░░  LOW
   US      reduce exposure
```

**Layout: Hub-and-spoke with regional nodes:**

Center-top: **Dollar direction indicator** (the gravity field).
A single line: "DOLLAR: STRENGTHENING ▲ / STABLE ► / WEAKENING ▼"
When dollar is weakening, all EM arrows get thicker (the tide is with them).

Regional nodes arranged spatially:
- **US** (center-left): SPY, QQQ returns
- **China** (center-right): FXI, KWEB returns + RMB direction
- **India** (lower-center): INDA return
- **Japan** (lower-right): EWJ return
- **Europe** (lower-left): VGK return
- **Broad EM** (below center): EEM return

**Arrows between regions:**
- Direction shows capital flow direction (Gave's assessment)
- Thickness shows magnitude (thin = small rotation, thick = major flow)
- Color: `--accent-gold` for flows Gave sees as significant/tradeable,
  `--text-tertiary` for background flows

**Bottom: Conviction ladder.** Horizontal bars for each region showing
Gave's conviction level. This is his "what I'd actually buy" summary.

**Trajectory:** Previous flow directions (30d ago) shown as faded arrows.
If arrows have reversed or strengthened, that's the signal.

**RMB indicator:** Small dedicated callout next to China node:
"RMB: strengthening / weakening / stable" -- his #1 signal.

---

### 4.7  POZSAR -- The Plumbing Schematic

**Mental model:** A literal plumbing diagram. Pipes, reservoirs, pressure
gauges. The monetary system's load-bearing infrastructure. Where is
collateral flowing? Where is pressure building? Where has the Fed had
to intervene?

**Visual description:**

```
         MONETARY PLUMBING

   ┌───────────────────────────────────────────┐
   │            RESERVES SYSTEM                 │
   │                                           │
   │  ┌─────────┐    ┌─────────┐   ┌────────┐ │
   │  │ FED BS  │───>│   TGA   │──>│  RRP   │ │
   │  │ $7.4T   │    │ $680B   │   │ $120B  │ │
   │  │ ▼ QT    │    │ ▲ build │   │ ▼ drain│ │
   │  └────┬────┘    └─────────┘   └────────┘ │
   │       │                                   │
   │       ▼  net liquidity: $6.6T ▲           │
   └───────────────────────────────────────────┘
              │
              ▼
   ┌───────────────────────────────────────────┐
   │          COLLATERAL TRANSITION             │
   │                                           │
   │  OLD COLLATERAL          NEW COLLATERAL    │
   │  ┌──────────┐           ┌──────────┐      │
   │  │Treasuries│ ──────>   │   GOLD   │      │
   │  │ declining│ CB shift  │  rising  │      │
   │  │ share    │           │  1,100t  │      │
   │  └──────────┘           └──────────┘      │
   │       │                      │            │
   │  ┌──────────┐           ┌──────────┐      │
   │  │  SWIFT   │           │COMMODITIES│     │
   │  │  $ share │ ──────>   │  DBC +6%  │     │
   │  │  58% ▼   │           │  "new $"  │     │
   │  └──────────┘           └──────────┘      │
   └───────────────────────────────────────────┘

   STRESS GAUGES:
   Term premium     ████████░░  elevated
   Funding stress   ███░░░░░░░  normal
   CB gold buying   █████████░  record pace
```

**Two-tier structure:**

**Upper tier -- Reserves System:**
Three connected reservoirs (rectangles with thick borders) showing:
1. **Fed Balance Sheet** -- level, direction (QT/QE), with pipe leading to...
2. **TGA (Treasury General Account)** -- level, direction (building/draining)
3. **Reverse Repo** -- level, direction (draining toward zero)

Connected by directional pipes. Net liquidity computed and shown on the
output pipe flowing down.

**Lower tier -- Collateral Transition:**
A left-to-right transformation showing old reserve assets being replaced:
- LEFT: Treasuries (declining share), SWIFT dollar share (declining)
- RIGHT: Gold (rising, CB purchases), Commodities (new collateral)
- Arrow between them represents the Bretton Woods III transition

**Bottom: Three stress gauges** (small horizontal bars):
1. **Term premium** -- from FRED data + web search
2. **Funding stress** -- cross-currency basis, repo rate anomalies
3. **Central bank gold buying pace** -- from web search

Each gauge: 0-100% with the same color ramp as Burry's bars.

**Trajectory:** Each reservoir shows a tiny sparkline of its level over
90 days. The reservoirs FILL/DRAIN visually -- the rectangle's fill level
corresponds to relative size (e.g., RRP nearly empty = rectangle nearly
empty).

---

## 5. Visual Data Schema (per agent)

Each agent prompt will be updated to produce a `visual_data` object alongside
the existing `regime_assessment`, `macro_narrative`, `themes`, and `trade_ideas`.

### 5.1 Buffett -- visual_data

```json
{
  "visual_type": "valuation_gauge",
  "gauges": {
    "buffett_indicator": {
      "value": 1.87,
      "zone": "extreme",
      "label": "Market Cap / GDP"
    },
    "shiller_cape": {
      "value": 36.2,
      "zone": "danger",
      "historical_avg": 17.0,
      "label": "Shiller CAPE"
    },
    "equity_risk_premium": {
      "value": 0.4,
      "zone": "negative_real",
      "label": "Equity Risk Premium %"
    }
  },
  "cash_yield": 4.8,
  "verdict": "patience",
  "verdict_quote": "Cash pays you to wait."
}
```

### 5.2 Dalio -- visual_data

```json
{
  "visual_type": "cycle_compass",
  "long_term_cycle": {
    "phase": "bubble",
    "position_angle": 72,
    "description": "Late-stage debt accumulation with asset inflation"
  },
  "short_term_cycle": {
    "phase": "late_cycle",
    "position_angle": 255,
    "description": "Growth decelerating, inflation sticky, policy constrained"
  },
  "monetary_policy": {
    "active": "MP2",
    "transitioning_to": "MP3",
    "mp1_status": "restrictive",
    "mp2_status": "QT_slowing",
    "mp3_status": "fiscal_expanding"
  },
  "quadrant": {
    "growth_score": -0.2,
    "inflation_score": 0.4,
    "label": "Stagflationary lean"
  }
}
```

### 5.3 Burry -- visual_data

```json
{
  "visual_type": "stress_fractures",
  "bars": [
    {
      "id": "credit",
      "label": "Credit Stress",
      "value": 82,
      "detail": "HY spread 420bp, 82nd percentile vs 10Y range",
      "is_primary_risk": false
    },
    {
      "id": "valuation",
      "label": "Valuation Excess",
      "value": 87,
      "detail": "CAPE 36.2, top decile historically",
      "is_primary_risk": false
    },
    {
      "id": "speculation",
      "label": "Speculative Intensity",
      "value": 93,
      "detail": "Top 7 stocks = 32% of SPY. QQQ/IWM ratio at ATH.",
      "is_primary_risk": true
    },
    {
      "id": "leverage",
      "label": "Leverage",
      "value": 55,
      "detail": "Margin debt elevated but not extreme",
      "is_primary_risk": false
    },
    {
      "id": "volatility",
      "label": "Vol Complacency",
      "value": 22,
      "detail": "VIX 14.2, well below realized. Skew flat.",
      "is_primary_risk": false
    },
    {
      "id": "liquidity",
      "label": "Liquidity Fragility",
      "value": 68,
      "detail": "RRP nearly drained. Reserves declining.",
      "is_primary_risk": false
    }
  ],
  "structural_integrity": "compromised",
  "primary_risk_summary": "Mega-cap concentration is historically unprecedented. The top 7 names are 32% of the index.",
  "overall_stress_score": 68
}
```

### 5.4 Alden -- visual_data

```json
{
  "visual_type": "fiscal_engine",
  "nodes": {
    "deficit": {
      "value": "$2.1T",
      "annualized": true,
      "direction": "rising",
      "detail": "Monthly pace accelerating"
    },
    "interest_expense": {
      "value": "$1.1T",
      "annualized": true,
      "pct_of_revenue": 18,
      "direction": "rising",
      "detail": "Now exceeds defense spending"
    },
    "net_liquidity": {
      "value": "$5.8T",
      "direction": "expanding",
      "fed_bs": "$7.4T",
      "tga": "$680B",
      "rrp": "$120B",
      "detail": "Net liquidity rising despite QT"
    },
    "fed_balance_sheet": {
      "value": "$7.4T",
      "direction": "contracting_slowing",
      "detail": "QT pace slowing, forced expansion likely"
    },
    "asset_response": {
      "hard_assets": [
        {"ticker": "GLD", "return_1m": "+4.2%", "signal": "positive"},
        {"ticker": "IBIT", "return_1m": "+12.1%", "signal": "positive"},
        {"ticker": "SLV", "return_1m": "+3.8%", "signal": "positive"}
      ],
      "nominal_assets": [
        {"ticker": "SPY", "return_1m": "+1.2%", "signal": "neutral"},
        {"ticker": "TLT", "return_1m": "-2.8%", "signal": "negative"}
      ]
    }
  },
  "flows": {
    "deficit_to_liquidity": "strong",
    "liquidity_to_assets": "strong",
    "interest_to_fed": "building",
    "fed_to_liquidity": "constrained"
  },
  "monetary_effectiveness": 25,
  "regime_label": "Fiscal Dominance Active"
}
```

### 5.5 Gromen -- visual_data

```json
{
  "visual_type": "nexus_triangle",
  "nodes": {
    "fiscal": {
      "interest_expense": "$1.1T",
      "vs_defense": "$886B",
      "vs_receipts_pct": 23,
      "direction": "deteriorating"
    },
    "dollar": {
      "uup_return_3m": "-3.2%",
      "direction": "weakening",
      "reserve_status": "eroding"
    },
    "energy": {
      "uso_return_3m": "+8.1%",
      "dbc_return_3m": "+5.4%",
      "petrodollar_status": "shifting"
    },
    "gold": {
      "gld_return_3m": "+14.2%",
      "gold_oil_ratio": 28.4,
      "gold_oil_ratio_avg": 22.0,
      "direction": "rising"
    }
  },
  "edges": {
    "fiscal_dollar": {
      "stress": "fracturing",
      "stress_score": 85,
      "label": "Fiscal threatens dollar credibility"
    },
    "dollar_energy": {
      "stress": "shifting",
      "stress_score": 65,
      "label": "Petrodollar settlement diversifying"
    },
    "energy_fiscal": {
      "stress": "strained",
      "stress_score": 55,
      "label": "Energy costs add to fiscal burden"
    }
  },
  "math_table": {
    "interest_expense": "$1.1T",
    "defense_spending": "$886B",
    "tax_receipts": "$4.8T",
    "interest_pct_receipts": "23%"
  },
  "verdict": "untenable"
}
```

### 5.6 Gave -- visual_data

```json
{
  "visual_type": "capital_flows",
  "dollar_direction": "weakening",
  "dollar_strength": -0.6,
  "rmb_direction": "strengthening",
  "rmb_signal": "positive",
  "regions": [
    {
      "id": "us",
      "label": "United States",
      "tickers": [
        {"symbol": "SPY", "return_3m": "+3.2%"},
        {"symbol": "QQQ", "return_3m": "+1.8%"}
      ],
      "conviction": "reduce",
      "position": "left"
    },
    {
      "id": "china",
      "label": "China",
      "tickers": [
        {"symbol": "FXI", "return_3m": "+18.2%"},
        {"symbol": "KWEB", "return_3m": "+22.1%"}
      ],
      "conviction": "high",
      "conviction_score": 90,
      "position": "right"
    },
    {
      "id": "india",
      "label": "India",
      "tickers": [
        {"symbol": "INDA", "return_3m": "+12.4%"}
      ],
      "conviction": "medium",
      "conviction_score": 65,
      "position": "bottom_center"
    },
    {
      "id": "japan",
      "label": "Japan",
      "tickers": [
        {"symbol": "EWJ", "return_3m": "+4.2%"}
      ],
      "conviction": "low",
      "conviction_score": 30,
      "position": "bottom_right"
    },
    {
      "id": "europe",
      "label": "Europe",
      "tickers": [
        {"symbol": "VGK", "return_3m": "+6.1%"}
      ],
      "conviction": "medium",
      "conviction_score": 55,
      "position": "bottom_left"
    }
  ],
  "flows": [
    {
      "from": "us",
      "to": "china",
      "magnitude": "major",
      "label": "Rotation into China recovery"
    },
    {
      "from": "us",
      "to": "india",
      "magnitude": "moderate",
      "label": "Structural allocation building"
    },
    {
      "from": "china",
      "to": "europe",
      "magnitude": "moderate",
      "label": "China demand lifts European exporters"
    }
  ]
}
```

### 5.7 Pozsar -- visual_data

```json
{
  "visual_type": "plumbing_schematic",
  "reserves": {
    "fed_bs": {
      "value": "$7.4T",
      "direction": "contracting",
      "detail": "QT $60B/month"
    },
    "tga": {
      "value": "$680B",
      "direction": "building",
      "detail": "Treasury rebuilding cash buffer"
    },
    "rrp": {
      "value": "$120B",
      "direction": "draining",
      "detail": "Nearly exhausted, was $2.5T at peak"
    },
    "net_liquidity": {
      "value": "$6.6T",
      "direction": "expanding",
      "detail": "TGA and RRP drain offset QT"
    }
  },
  "collateral_transition": {
    "old_collateral": {
      "treasuries_share": "58%",
      "treasuries_direction": "declining",
      "swift_dollar_share": "47%",
      "swift_direction": "declining"
    },
    "new_collateral": {
      "gold_cb_purchases_tonnes": 1100,
      "gold_direction": "rising",
      "commodities_return": "+6.2%",
      "commodities_direction": "rising"
    }
  },
  "stress_gauges": [
    {
      "id": "term_premium",
      "label": "Term Premium",
      "value": 72,
      "status": "elevated"
    },
    {
      "id": "funding_stress",
      "label": "Funding Stress",
      "value": 28,
      "status": "normal"
    },
    {
      "id": "cb_gold",
      "label": "CB Gold Buying",
      "value": 88,
      "status": "record_pace"
    }
  ],
  "transition_verdict": "accelerating"
}
```

---

## 6. Agent Prompt Additions

Each agent's existing prompt gets a new section inserted after OUTPUT REQUIREMENTS:

### Template (adapt per agent):

```markdown
## VISUAL DATA OUTPUT

In addition to your macro_narrative, themes, and trade_ideas, you must produce
a `visual_data` object that powers your visual mental model on the dashboard.

This visual shows [DESCRIPTION OF THIS AGENT'S SPECIFIC VISUAL].

Your visual_data must contain:

[AGENT-SPECIFIC SCHEMA FROM SECTION 5]

### How to populate visual_data:

- [field_1]: Compute from [briefing_packet.field] by [method].
  Use these thresholds: [specific numbers].
- [field_2]: Obtain from web search for "[specific query]".
- [field_3]: Your analytical judgment, expressed as one of:
  [option_a] / [option_b] / [option_c].

### Calibration:
- When [condition], the visual should show [specific state].
- When [opposite condition], the visual should show [opposite state].
- The visual_data values must be CONSISTENT with your macro_narrative
  and regime_assessment. If your narrative says markets are overvalued,
  your gauge better show "expensive."
```

### Key principle for prompt additions:

The visual_data fields fall into three categories:

1. **Computed from briefing data** -- the agent extracts specific numbers
   (e.g., HY spread value, net liquidity calculation). These are mechanical.

2. **Sourced from web search** -- the agent's required web searches already
   cover these (e.g., CAPE for Buffett, deficit pace for Alden). No new
   searches needed.

3. **Analytical judgment** -- the agent makes a qualitative call expressed
   as a structured choice (e.g., cycle phase, stress level, flow direction).
   These must be consistent with the narrative.

**Critical constraint:** The visual_data must not require additional API calls.
It's produced IN THE SAME agent run that produces the narrative. The agent
already has all the data it needs from the briefing packet + web search.
This adds ~200-400 tokens to each agent's output. At Sonnet pricing, that's
roughly $0.003-0.005 additional cost per agent per day. Negligible.

---

## 7. Implementation Plan

### Phase 1: Schema & Backend (est. 1 hour)
1. Add `visual_data` JSON column to agent_runs table in SQLite
2. Update Pydantic schemas to include visual_data per agent type
3. Update agent runner to parse and store visual_data
4. Add API endpoint: `GET /api/agents/{id}/visual_history?days=90`

### Phase 2: Agent Prompt Updates (est. 2 hours)
1. Add VISUAL DATA OUTPUT section to each of the 7 agent prompts
2. Update the base output schema documentation in each prompt
3. Generate mock visual_data for all 7 agents (for frontend dev)
4. Test with one real agent run to validate output parsing

### Phase 3: Frontend Components (est. 3-4 hours)
Build 7 React components, one per agent visualization:
1. `ValuationGauge.jsx` -- Buffett (SVG arcs + needles)
2. `CycleCompass.jsx` -- Dalio (SVG concentric rings + dots)
3. `StressFractures.jsx` -- Burry (SVG horizontal bars + sparklines)
4. `FiscalEngine.jsx` -- Alden (SVG flow diagram + nodes)
5. `NexusTriangle.jsx` -- Gromen (SVG triangle + center node)
6. `CapitalFlows.jsx` -- Gave (SVG hub-spoke + arrows)
7. `PlumbingSchematic.jsx` -- Pozsar (SVG reservoirs + pipes)

Plus shared utilities:
- `SparklineSmall.jsx` -- 40x12px SVG sparkline for trajectory
- `StressBar.jsx` -- Reusable horizontal stress bar (Burry + Pozsar)
- `DirectionArrow.jsx` -- ▲/▼/► with semantic color

### Phase 4: Integration (est. 1 hour)
1. Update Agent.jsx page to render the appropriate visual component
2. Wire visual_history API for trajectory data
3. Add the 4 new data fields to the data agent
4. End-to-end test with real agent run

### Estimated total: 7-8 hours of implementation work.

---

## Open Questions for You

1. **Dalio cycle angles:** The position on the cycle ring is expressed as an
   angle (0-360). Should I provide the agent with strict angle guidelines
   (e.g., "early expansion = 315-45 degrees") or let it express phase +
   confidence and compute the angle on the frontend? I lean frontend-computed
   to keep the prompt simpler.

2. **Burry's percentiles:** His stress bars need historical percentile context
   (e.g., "HY spread is at 82nd percentile vs. 10-year range"). The data agent
   doesn't currently store historical ranges. Two options:
   (a) Hardcode approximate historical ranges in the prompt (cheaper, good enough)
   (b) Have the data agent compute rolling percentiles (more accurate, more work)
   I recommend (a) for v1 and (b) later.

3. **Home page previews:** Should each agent card on the Home dashboard show a
   TINY version of their visual (like a favicon-sized icon of the gauge/triangle)?
   Or just the text summary? Tiny visuals would be distinctive but complex.

4. **War Room integration:** The Council/War Room page currently does cross-agent
   thesis comparison. Should it also show all 7 visuals in a grid? That could be
   a powerful "at a glance" view -- you scan 7 different mental models and see
   where they agree/disagree visually.
