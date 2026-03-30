# FRONTEND SPECIFICATION — Falsification Engine

*This document specifies the frontend architecture, data contracts, component structure, and implementation plan for the Falsification Engine's web interface. It is produced by the frontend design thread and should be used by (a) the architecture thread for integration into plan.md and claude.md, and (b) Claude Code for direct implementation.*

*Version: 1.0 — March 2026*

---

## Table of Contents

1. Organizing Principle
2. Navigation Hierarchy & View Structure
3. Design System (Hermes Editorial, carried forward)
4. View Specifications (6 views, detailed)
5. Hypothesis Data Shape (the central object)
6. API Contract (what the frontend needs from the backend)
7. User Workflows (3 primary workflows)
8. Visual Mental Models (adapted from Macro Council)
9. Open-Source First-Run Experience
10. Implementation Plan (components, phases, estimates)

---

## 1. Organizing Principle

**The hypothesis is the central data object.** Not theories, not agents, not trades, not assets.

The Macro Council frontend was organized around producers — each agent got a page, each page showed a visual mental model and a narrative, and the War Room tried to reconcile their outputs. That's a newspaper editorial board. The Falsification Engine frontend is organized around claims about the world — hypotheses that are born, attacked, scored, acted upon, and eventually expire or get killed.

Every view in the system either:
- Shows the ledger of hypotheses (Ledger)
- Lets you drill into one hypothesis (Hypothesis Detail)
- Lets you annotate a hypothesis with a decision (Journal)
- Shows the infrastructure that produces hypotheses (Observatory, Pipeline, Briefing)

The producer (which theory module generated the hypothesis) is metadata on the hypothesis, not the organizing axis. Assets are a lens through which to view hypotheses, not a separate data domain. Actions are annotations on hypotheses, not independent records.

**Why this matters for implementation:** Every component that renders hypothesis data should accept a `Hypothesis` object (defined in Section 5) as its primary prop. The Hypothesis object is the single source of truth. Components that show aggregated views (asset grouping, theory filtering) are computed projections of the hypothesis ledger, not independent data stores.

---

## 2. Navigation Hierarchy & View Structure

### Hierarchy

```
PRIMARY:    Ledger (home, daily entry point)
SECONDARY:  Hypothesis Detail (drill from Ledger), Journal (decision layer)
TERTIARY:   Observatory (theory infrastructure)
UTILITY:    Pipeline (operational + audit), Data Briefing (reference + inbox)
```

### Navigation Bar

Horizontal tab bar, always visible, below the header. Five tabs:

| Tab | Label | Priority | Badge? |
|-----|-------|----------|--------|
| 1 | LEDGER | Primary (larger font, always default) | No |
| 2 | JOURNAL | Secondary | No |
| 3 | OBSERVATORY | Tertiary | No |
| 4 | PIPELINE | Utility | No |
| 5 | BRIEFING | Utility | Yes — shows count of queued inbox items |

**Hypothesis Detail** is not a tab — it is a modal/overlay triggered by clicking any hypothesis row in any view. It overlays the current view and closes back to it. This avoids navigation context loss.

### URL Routing (for implementation)

```
/                       → Ledger (default)
/journal                → Journal
/observatory            → Observatory
/pipeline               → Pipeline (Run Mode default)
/pipeline?mode=audit    → Pipeline (Audit Mode)
/briefing               → Data Briefing + Inbox
/hypothesis/:id         → Deep-link to hypothesis detail (opens overlay)
```

---

## 3. Design System: Hermes Editorial

Carried forward from the Macro Council with no changes to the visual language. The aesthetic is a quarterly letter from a private bank — warm, typographic, no emoji, generous whitespace.

### Colors (CSS Variables)

```css
:root {
  /* Backgrounds */
  --bg-primary:    #FAF7F2;   /* cream, main background */
  --bg-secondary:  #F0EBE3;   /* warm stone, cards and fills */
  --bg-inset:      #F5F1EB;   /* subtle inset panels */
  --bg-hover:      #EDE8E0;   /* hover state for interactive rows */

  /* Text */
  --text-primary:   #1C1917;  /* near-black, headings and body */
  --text-secondary: #57534E;  /* dark warm gray, supporting text */
  --text-tertiary:  #A8A29E;  /* warm gray, labels and metadata */

  /* Semantic accents — NO traffic-light colors */
  --accent-negative: #7F1D1D; /* dark brick, danger/killed/short */
  --accent-positive: #365314; /* deep olive, health/survived/long */
  --accent-gold:     #A16207; /* warm gold, warning/wounded/signal */
  --accent-high:     #7C2D12; /* burnt sienna, high conviction/emphasis/CTA */

  /* Borders */
  --border-light:  #E7E5E4;   /* hairline separators */
  --border-medium: #D6D3D1;   /* stronger separators, table headers */
}
```

### Typography

Three font families, strictly role-assigned:

| Role | Font | Usage |
|------|------|-------|
| Display | Cormorant Garamond (600, small-caps, letter-spaced 0.06-0.10em) | Page titles, section headers, nav items, table column headers |
| Body | EB Garamond (400/500, italic for annotations) | Hypothesis statements, elimination notes, journal reasoning, all prose |
| Data | JetBrains Mono (400/500/600) | Numbers, IDs, badges, tags, metrics, code, monospaced labels |

**Rules:**
- No other fonts. Ever.
- Never use EB Garamond for numbers or JetBrains Mono for prose.
- Conviction scores are always JetBrains Mono 600.
- Theory tags are always JetBrains Mono 10px.
- Status badges are always JetBrains Mono 9px uppercase.

### Layout

- Max width: 1200px, centered.
- Padding: 32px horizontal on desktop, 14px on mobile.
- Desktop-first. Mobile is read-only — the Ledger collapses to: status badge, hypothesis name, conviction score, conviction delta.
- No rounded corners on containers. Structure from line weight and whitespace.
- No drop shadows. No gradients. No fill effects.
- Borders are 1px solid, using `--border-light` for rows and `--border-medium` for section dividers.

### Interactive States

- Hover on table rows: `--bg-hover` background, 0.12s transition.
- Active nav tab: `--accent-high` bottom border (2px).
- Buttons: 1px `--border-medium` border, `--text-secondary` text, no fill. Hover: `--text-primary` text, `--text-secondary` border. Active/selected: `--text-primary` text, `--text-primary` border, `--bg-secondary` fill.
- Primary CTA buttons: `--accent-high` background, `--bg-primary` text.

---

## 4. View Specifications

### 4.1 LEDGER (Primary View — Home)

**Purpose:** The daily entry point. Shows all hypotheses, supports fast scanning of "what changed," and toggles between hypothesis-centric and asset-centric views. This is the new War Room.

#### Layout Structure

```
+──────────────────────────────────────────────────────────+
│  DELTA BANNER (dismissable)                              │
│  Changes since last review: killed, deteriorated,        │
│  improved items. Each clickable → opens detail.          │
│  [MARK REVIEWED] button dismisses.                       │
+──────────────────────────────────────────────────────────+
│  CONTROLS BAR                                            │
│  [BY HYPOTHESIS | BY ASSET]    [ALIVE] [ALL] [WOUNDED]   │
│                                [KILLED]    N hypotheses  │
+──────────────────────────────────────────────────────────+
│  TABLE / GROUPED VIEW                                    │
│  (see below for both modes)                              │
+──────────────────────────────────────────────────────────+
```

#### Delta Banner

The delta banner is the most important UX element for daily use. It appears on load and compares the current state to whatever the user last reviewed (tracked via a `last_reviewed_run_id` in local storage or SQLite).

Delta categories, displayed in this order:

| Category | Criteria | Color | Visual |
|----------|----------|-------|--------|
| KILLED | Was alive, now dead (hard falsifier tripped) | `--accent-negative` | Strikethrough name + kill reason |
| DETERIORATED | Conviction dropped >0.5 since last review | `--accent-gold` | Name + delta explanation |
| IMPROVED | Conviction increased >0.5 since last review | `--accent-positive` | Name + delta explanation |
| NEW | Generated in a run after last review | `--accent-high` | Name + source theory |
| STABLE | Everything else | Not displayed by default | Collapsed/hidden |

Each delta item is clickable — opens Hypothesis Detail.

"MARK REVIEWED" sets `last_reviewed_run_id` to the current run and dismisses the banner. The banner reappears when a new run produces different results.

**Data required:** `GET /api/delta?since_run_id={last_reviewed}` returning categorized hypothesis changes.

#### Hypothesis Table (BY HYPOTHESIS mode)

Default view. A table with these columns:

| Column | Width | Content | Alignment | Font |
|--------|-------|---------|-----------|------|
| Status | 72px | Badge: SURVIVED / WOUNDED / KILLED | Left | JetBrains Mono 9px |
| Hypothesis | flex | Short name (6-12 words) | Left | EB Garamond 14px |
| Theory | auto | `theory_id` as tag | Left | JetBrains Mono 10px |
| Conv. | 52px | Score (e.g., "7.8") + delta below (e.g., "+0.6") | Right | JetBrains Mono 14px/10px |
| Fals. | 44px | Triggered/total (e.g., "1/3" or "0/4") | Center | JetBrains Mono 11px |
| Assets | 90px | ETF ticker tags (max 3, then "+N") | Left | JetBrains Mono 10px |
| Age | 36px | Days since generation (e.g., "12d") | Right | JetBrains Mono 11px |
| Markers | 20px | Dot for position, diamond for research notes | Center | SVG shapes |

**Conviction score color:** >=7 `--accent-positive`, 5-6.9 `--text-primary`, <5 `--text-tertiary`.
**Conviction delta color:** Positive `--accent-positive`, negative `--accent-negative`.
**Falsifier health color:** 0 triggered `--accent-positive`, >0 triggered `--accent-gold`.

**KILLED rows:** Opacity 0.4, text-decoration line-through. On hover, opacity rises to 0.65.
**WOUNDED rows:** Subtle `--accent-gold` background tint (#A162070A).

**Default sort:** Conviction score descending (alive hypotheses only).
**Filters:** alive (default), all, wounded, killed. Implemented as toggle buttons, not a dropdown.

**Row click:** Opens Hypothesis Detail overlay.

**Mobile collapse (< 768px):** Hide columns 5-8 (Fals., Assets, Age, Markers). Show: Status, Hypothesis, Theory, Conv.

#### Asset View (BY ASSET mode)

Groups alive hypotheses by predicted ETF ticker. Each group shows:

```
+──────────────────────────────────────────────────────────+
│  GLD    LONG    2 hypotheses    2-theory convergence     │
├──────────────────────────────────────────────────────────┤
│  [standard table rows for hypotheses predicting GLD]     │
│  (same columns as hypothesis table, minus Assets col)    │
+──────────────────────────────────────────────────────────+
│  IBIT   LONG    1 hypothesis    Fiscal Dom. (Arithmetic) │
├──────────────────────────────────────────────────────────┤
│  [table rows]                                            │
+──────────────────────────────────────────────────────────+
```

**Group header fields:**
- Ticker (JetBrains Mono 16px bold)
- Direction consensus badge: LONG / SHORT / MIXED (if hypotheses disagree on direction)
- Hypothesis count
- If >=2 hypotheses from different theories: "N-theory convergence" (italic, right-aligned)
- If 1 hypothesis: show theory label

**Sort:** Groups sorted by max conviction of constituent hypotheses, descending.

**Direction mapping:** Each hypothesis must specify `asset_direction` — a map of ticker → "LONG" | "SHORT" for each predicted asset. This is how the system knows that `structural_fragility` predicting HY spread widening means SHORT HYG, while `fiscal_dominance_liquidity` predicting gold strength means LONG GLD.

**This view replaces the Macro Council's Expression Menu.** Instead of aggregating agent opinions per ticker, it aggregates surviving hypothesis support per ticker.

---

### 4.2 HYPOTHESIS DETAIL (Secondary — Modal Overlay)

**Purpose:** Full interrogation of a single hypothesis. "Why did this survive? What would kill it? Show me the math."

**Triggered by:** Clicking any hypothesis row in any view (Ledger, Journal, Pipeline audit).

**Layout:** Fixed-position overlay with semi-transparent backdrop. Panel is 860px max-width, vertically scrollable, with 36px padding.

#### Sections (top to bottom)

**A. Identity**
- Hypothesis ID (JetBrains Mono 11px, tertiary)
- Short name (Cormorant Garamond 22px, 600 weight)
- Meta row: status badge, theory tag, timeframe, asset tags

**B. Full Statement**
- Section title: "HYPOTHESIS"
- The full hypothesis text (EB Garamond 15px, max-width 660px, line-height 1.6)
- This is the complete mechanism + prediction + timeframe + assets

**C. Conviction Scoring**
- Section title: "CONVICTION SCORING"
- Three-column grid (collapses to single column on mobile):

| Stage 1: Raw | Stage 2: Discounts | Stage 3: Gates |
|---|---|---|
| Support strength: 0.82 | Soft falsifier: 0.00 | Horizon cap: --- |
| Evidence quality: 0.78 | Overlap penalty: -0.10 | Expression cap: --- |
| Convergence: 0.85 | | |
| Falsifier clarity: 0.90 | | |
| **Raw: 7.4** | **Adjusted: 7.3** | **Final: 7.8** |

- Each stage in a `--bg-inset` panel with `--border-light` border.
- Negative values (discounts, caps) in `--accent-negative`.
- Final score in 20px JetBrains Mono, colored by conviction tier.
- Below the grid: 90-day conviction trail sparkline (120px wide, 22px tall).

**D. Falsifier Health**
- Section title: "FALSIFIER HEALTH"
- Hard falsifiers listed first with PASSED / FAILED badge.
- Soft falsifiers listed with: status dot (green=clear, red=triggered), name (EB Garamond 13px), severity badge (minor/medium/major with appropriate coloring), current metric value vs threshold (JetBrains Mono 10px, right-aligned).

**Severity badge colors:**
- minor: `--text-tertiary` text, `--border-light` border
- medium: `--accent-gold` text, gold-tinted border
- major: `--accent-negative` text, red-tinted border

**E. Elimination Audit**
- Section title: "ELIMINATION AUDIT"
- Full text of the adversarial elimination pass reasoning (EB Garamond 14px, italic, `--text-secondary`, max-width 660px).
- This is the transparency layer — the user can read the adversary's full argument.

**F. Research Notes (with inline input)**
- Section title: "RESEARCH NOTES" with "+ ADD NOTE" button
- Clicking ADD NOTE expands a textarea with "QUEUE FOR NEXT RUN" primary button.
- Existing notes displayed as inset cards: date, source, content.
- This is the hypothesis-level research input surface.

**G. Your Position (conditional — only if action recorded)**
- Section title: "YOUR POSITION"
- Inset card showing: action (LONG GLD), date, size, conviction at entry, current conviction, status (OPEN/CLOSED).
- Links to the Journal entry.

#### Close Behavior
- ESC key or click backdrop or click close button.
- Returns to the view that triggered it (no navigation context loss).

---

### 4.3 JOURNAL (Secondary)

**Purpose:** The human decision/outcome layer. Records when the user acts on a hypothesis, and later what happened. The system does not recommend actions — the Journal is where the user completes the loop.

#### Layout

```
+──────────────────────────────────────────────────────────+
│  DECISION JOURNAL                        [+ RECORD ACTION]│
+──────────────────────────────────────────────────────────+
│  JOURNAL ENTRY (card)                                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  LONG GLD                              2026-03-18  │  │
│  │  "Fiscal liquidity supports gold through Q3 2026"  │  │
│  │  Size: 8%   Entry conv: 7.2   Current: 7.8  OPEN  │  │
│  │  Three-theory convergence on gold. Fiscal...       │  │
│  └────────────────────────────────────────────────────┘  │
+──────────────────────────────────────────────────────────+
```

#### Journal Entry Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hypothesis_id` | FK → Hypothesis | Yes | Which hypothesis prompted the action |
| `date` | ISO date | Yes | When the action was taken |
| `action` | string | Yes | e.g., "LONG GLD", "SHORT HYG", "NO ACTION — watching" |
| `size` | string | No | Portfolio percentage allocated |
| `conviction_at_entry` | float | Auto | Conviction score at time of recording |
| `reasoning` | text | Yes | Free-text: why the user is acting (or not) |
| `status` | enum | Auto | OPEN / CLOSED |
| `outcome` | text | No | Filled in later: what happened, what was learned |
| `closed_date` | ISO date | No | When the position was closed / hypothesis expired |

#### Interaction

- **"+ RECORD ACTION"** opens a form overlay. User selects a hypothesis (dropdown search or pre-populated if navigating from Hypothesis Detail), fills in action, size, reasoning.
- **Hypothesis name** in each entry is clickable → opens Hypothesis Detail.
- **Closing a position:** User clicks "CLOSE POSITION" on an open entry, records outcome text and date.
- **"Current conviction"** auto-updates from the hypothesis ledger on each render — this lets the user see if their position's underlying hypothesis has strengthened or weakened since entry.

#### Future Feature: Pattern Analysis

Over time, the Journal accumulates data for pattern detection:
- Distribution of conviction scores at action vs inaction
- Win rate by theory source
- Win rate by conviction tier
- Average holding period vs hypothesis timeframe
- Positions where conviction deteriorated and user held anyway

This is not in v1 but the data model should support it.

---

### 4.4 OBSERVATORY (Tertiary)

**Purpose:** Background context layer showing the 8 theory modules, their activation state, and configuration. "Why is the system generating these types of hypotheses?"

#### Layout

2-column grid of theory cards (collapses to 1-column on mobile).

#### Theory Card

```
+──────────────────────────────────────────────────────────+
│  Fiscal Dominance (Liquidity)                  ACTIVE    │
│  ████████████████████████████░░░░░               91%     │
│  Activation: 91%                                         │
+──────────────────────────────────────────────────────────+
```

**Fields:**
- Theory name (Cormorant Garamond 14px, 600 weight)
- Tier badge: ACTIVE (`--accent-positive`), ADJACENT (`--accent-gold`), INACTIVE (`--text-tertiary`)
- Activation score bar (3px height, colored by tier)
- Activation percentage (JetBrains Mono 10px)
- Phase label for two-phase theories (JetBrains Mono 10px)

**Visual treatment by tier:**
- Active: 3px `--accent-positive` left border
- Adjacent: 3px `--accent-gold` left border
- Inactive: 3px `--border-light` left border, 0.55 opacity

**Card click behavior (v2):** Expand to show activation condition breakdown — which indicators are met, which aren't, how close the score is to the next tier threshold. Also link to Ledger filtered by that theory.

**Where the visual mental models live:** Each theory card could render its characteristic visual in miniature (gauge for valuation, cycle compass for debt cycle, stress bars for fragility). In v1, the activation bar is sufficient. In v2, the theory-specific visuals from the Visual Mental Models spec can be adapted here — they now answer "is this theory's mechanism operative?" instead of "what does this persona think?"

---

### 4.5 PIPELINE (Utility — Two Modes)

**Purpose:** The operational workflow for running the five-pass pipeline, and the retrospective audit of completed runs.

#### Mode Toggle

Two buttons at top: RUN MODE (default) and AUDIT MODE.

#### Run Mode

Shows the 5 pipeline steps as a vertical workflow with status indicators.

**Step states:**
- `complete` — green checkmark indicator, step completed
- `ready` — `--accent-high` indicator, user action required
- `waiting` — gray indicator, blocked on prior step

**Pipeline steps:**

| # | Label | Type | Status Logic |
|---|-------|------|-------------|
| 1 | Data Briefing | Automated | Complete when briefing packet is fresh (< 24h old) |
| 2 | Activation Scoring | Automated | Complete when activation scores computed from current briefing |
| 3 | Generation Pass | Human-in-loop | Ready when steps 1-2 complete. Shows: SHOW PROMPT, COPY TO CLIPBOARD, IMPORT RESULT |
| 4 | Elimination Pass | Human-in-loop | Ready when step 3 output imported. Same buttons. |
| 5 | Conviction Scoring | Automated | Runs mechanically after step 4 import. Updates Ledger. |

**The "ready" step is the key interaction.** When step 3 (Generation) is ready:

1. **SHOW PROMPT** — expands a `--bg-inset` panel showing the full prompt text: system instructions, Active/Adjacent theories, briefing packet reference, queued inbox items. This is the text the user copies to Claude.
2. **COPY TO CLIPBOARD** — copies the prompt to clipboard.
3. **IMPORT RESULT** — opens a textarea/file-upload where the user pastes Claude's JSON output. The system parses it, stores the hypotheses, and advances to step 4.

Same pattern for step 4 (Elimination): the prompt includes the generated hypotheses, the theory modules, and the data briefing. The user copies it to Claude, gets the adversarial output, imports it back.

**Below the steps:** a panel showing "Queued Inbox Items" — research notes and links that will be incorporated into the generation prompt. This gives the user visibility into what new information is feeding the next run.

**The prompt text for step 3 should include:**

```
SYSTEM: You are the Generation Pass of a Falsification Engine.

ACTIVE THEORIES: {list with scores}
ADJACENT (max 1 wildcard): {list with scores}

INBOX ITEMS (new since last run):
{each queued inbox item}

TASK: Generate 2-4 hypotheses per Active theory. Each must include:
- theory_id: which theory this derives from
- short_name: 6-12 word summary
- mechanism: the causal chain
- prediction: specific, testable, with magnitude and timeframe
- predicted_assets: ETF tickers with direction (LONG/SHORT)
- hard_falsifiers: conditions that kill the hypothesis
- soft_falsifiers: conditions that wound it (with severity)
- timeframe: when the prediction should resolve

DATA BRIEFING: [attached/inline]

Output JSON array of hypothesis objects.
```

**The prompt text for step 4 should include:**

```
SYSTEM: You are the Elimination Pass of a Falsification Engine.
Your ONLY job is to attack each hypothesis and find reasons it should die.

HYPOTHESES TO ATTACK: [from step 3 output]
THEORY MODULES: [the theories those hypotheses invoke]
DATA BRIEFING: [current briefing]

For each hypothesis, attempt:
1. Hard falsifier check — is any hard falsifier currently triggered? Check each one against the data briefing and current conditions.
2. Soft falsifier check — is any soft falsifier currently triggered or close to triggering? Include the price action falsifier: has the primary predicted asset moved 15%+ against the hypothesis direction? Report each soft falsifier's status and severity.
3. Cross-theory attack — does another Active theory's mechanism contradict this hypothesis?
4. Evidence quality assessment — is the supporting evidence strong or weak?
5. Composition integrity — for multi-theory hypotheses, does combining theories narrow or broaden the prediction?

STATUS ASSIGNMENT RULES (mechanical — you do not have discretion here):
- KILLED: Any hard falsifier triggered, OR 2+ major soft falsifiers triggered, OR 3+ soft falsifiers of any severity triggered.
- WOUNDED: 1+ soft falsifier triggered AND the triggered falsifier(s) create directional doubt about the hypothesis prediction.
- SURVIVED: No hard falsifiers triggered AND fewer soft falsifiers triggered than the WOUNDED/KILLED thresholds.

For purposes of these status rules, "soft falsifiers" includes both theory-level soft falsifiers AND any falsifiers from active sector appendices that the evaluator has marked as both TRIGGERED and RELEVANT to the hypothesis's load-bearing mechanism. A sector falsifier that is triggered but NOT relevant does not count toward WOUNDED or KILLED thresholds.

CRITICAL CONSTRAINT: Assign status ONLY based on pre-registered falsifiers listed in the hypothesis's parent theory module(s), plus any falsifiers from active sector appendices that the evaluator has marked as both TRIGGERED and RELEVANT to the hypothesis's load-bearing mechanism. If no pre-registered falsifier is triggered (and no sector falsifier is both triggered and relevant), the status is SURVIVED regardless of your assessment of price action, market conditions, or narrative. You are checking a list, not forming a view. If you believe a hypothesis should be WOUNDED or KILLED but cannot point to a specific pre-registered falsifier that is triggered, then the falsifier list has a gap — note this in your reasoning as "FALSIFIER GAP: [description]" so the system operator can add the missing falsifier. Do NOT compensate for the gap by overriding the status.

Output: each hypothesis tagged SURVIVED / WOUNDED / KILLED with:
- Each falsifier checked with current status (CLEAR / TRIGGERED / CLOSE / UNTESTABLE)
- The specific falsifier(s) that justify WOUNDED or KILLED status
- Any FALSIFIER GAP flags for conditions you believe should be falsifiers but aren't pre-registered
- Full reasoning for the status assignment
```

#### Audit Mode

Shows a completed run's five stages, top to bottom, as a read-only trace. Each stage is a collapsible section:

1. **Activation:** 8 theories with tier and score
2. **Generation:** All hypotheses produced, grouped by source theory
3. **Elimination:** Same hypotheses with status badges and kill/wound reasons. Killed hypotheses shown with strikethrough.
4. **Conviction Scoring:** Surviving hypotheses ranked by final conviction score
5. **Human Decision:** Placeholder text: "N hypotheses survived. The system has done its work."

**Run selector (v2):** Dropdown or timeline to select which historical run to audit. v1 shows the most recent run.

---

### 4.6 DATA BRIEFING (Utility — Reference + Inbox)

**Purpose:** Two functions: (1) display the current data briefing packet so the user can verify what the system sees, and (2) provide the research inbox for adding new information.

#### Research Inbox (top section)

This is the primary input surface for the user's daily reading workflow. It must be extremely lightweight — the user is capturing something they just read before they forget it.

```
+──────────────────────────────────────────────────────────+
│  RESEARCH INBOX (2 queued for next run)                   │
│  [paste a link or write a note...                    ] [ADD]│
+──────────────────────────────────────────────────────────+
│  2026-03-25  FT: CLO managers warn of maturity wall       │
│              ft.com  [structural_fragility]      QUEUED   │
│  2026-03-24  42 Macro net liquidity model shows TGA...    │
│              42 Macro  [fiscal_dom_liq]          QUEUED   │
│  2026-03-22  Lyn Alden: Why this cycle is different...    │
│              lynalden.com  [fisc_liq, debt_short] INCORP  │
+──────────────────────────────────────────────────────────+
```

**Inbox Item Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Auto | Unique identifier |
| `date` | ISO date | Auto | When added |
| `type` | enum | Auto-detect | "link" (starts with http) or "note" (free text) |
| `content` | text | Yes | The link URL or the note text |
| `source` | string | Optional | Publication or author name |
| `theories` | string[] | Optional | Tag with relevant theory_ids |
| `status` | enum | Auto | "queued" → "incorporated" after a pipeline run |
| `hypothesis_id` | FK | Optional | If added from a Hypothesis Detail, links to it |

**Interaction:**
- Text input + ADD button. That's it. Minimal friction.
- Optional: after adding, a dropdown appears to tag with theory domains. If skipped, the item is untagged and the generation prompt includes it as general context.
- Items with "queued" status are included in the next generation prompt.
- After a pipeline run, queued items are marked "incorporated."

**The inbox is also accessible from Hypothesis Detail** (Section F: Research Notes). When adding a note from Hypothesis Detail, the `hypothesis_id` is auto-linked. The note appears in both the global inbox (Briefing view) and on the hypothesis's research notes section.

#### Briefing Packet Display (bottom section)

The structured JSON briefing packet rendered as a readable grid. Six panels in a 3-column layout:

| Panel | Key Fields |
|-------|-----------|
| Growth | GDP, ISM, Unemployment, Payrolls, Claims |
| Inflation | CPI YoY, Core PCE, 5Y/10Y Breakevens |
| Rates | Fed Funds, 2Y, 10Y, 30Y, 2s10s, Real 10Y |
| Liquidity | Net Liquidity, Fed BS, TGA, RRP, M2 YoY |
| Credit | HY Spread, IG Spread, direction |
| Sentiment | VIX, VIX vs Realized |

Each field shows: name, current value (JetBrains Mono), direction/trend tag (JetBrains Mono 9px), and last-updated timestamp on hover.

**Staleness flag:** If a data field is older than expected (>24h for daily data, >7d for weekly), display in `--accent-gold` text with a staleness warning.

---

## 5. Hypothesis Data Shape

This is the central data object. All frontend components consume this shape.

```typescript
interface Hypothesis {
  // Identity
  id: string;                    // e.g., "H-2026-037-01"
  run_id: string;                // which pipeline run generated this
  short_name: string;            // 6-12 word summary
  full_statement: string;        // complete mechanism + prediction + timeframe

  // Provenance
  source_theory: string;         // theory_id (e.g., "fiscal_dominance_liquidity")
  source_theory_label: string;   // display name (e.g., "Fiscal Dom. (Liquidity)")
  source_theories: string[];     // for multi-theory hypotheses, all contributing theory_ids
  generated_date: string;        // ISO date

  // Pipeline state
  status: "SURVIVED" | "WOUNDED" | "KILLED";
  conviction: number;            // 0.0 - 10.0, final score from conviction pipeline
  conviction_prev: number;       // score from previous run (for delta display)
  conviction_history: number[];  // array of scores across runs (for sparkline)

  // Conviction math (full transparency)
  conviction_math: {
    stage1: {
      support_strength: number;    // 0.0 - 1.0 (weight: 0.30)
      evidence_quality: number;    // 0.0 - 1.0 (weight: 0.30)
      convergence: number;         // 0.0 - 1.0 (weight: 0.25)
      falsifier_clarity: number;   // 0.0 - 1.0 (weight: 0.15)
      raw: number;                 // weighted sum, scaled to 0-10
    };
    stage2: {
      soft_falsifier_discount: number;  // 0.0 or negative
      overlap_penalty: number;          // 0.0 or negative
      adjusted: number;                 // raw + discounts
    };
    stage3: {
      horizon_cap: number | null;       // null if not binding, negative if binding
      expression_cap: number | null;    // null if not binding, negative if binding
      final: number;                    // the published score
    };
  };

  // Falsifiers
  hard_falsifiers: {
    condition: string;
    status: "passed" | "FAILED";
    detail?: string;              // explanation if failed
  }[];

  soft_falsifiers: {
    name: string;
    severity: "minor" | "medium" | "major";
    status: "clear" | "TRIGGERED";
    metric: string;               // current value as string
    threshold: string;            // threshold as string
  }[];

  falsifier_health: {
    triggered: number;            // count of triggered soft falsifiers
    total: number;                // total soft falsifiers
  };

  // Predictions
  predicted_assets: string[];             // ETF tickers
  asset_direction: Record<string, "LONG" | "SHORT">;  // per-ticker direction
  timeframe: string;                      // e.g., "Through Q3 2026"

  // Elimination
  elimination_notes: string;     // full adversarial reasoning text

  // Metadata
  age: number;                   // days since generated_date
  delta_type: "NEW" | "IMPROVED" | "DETERIORATED" | "KILLED" | "STABLE";

  // Human annotations
  has_action: boolean;           // true if a Journal entry exists for this hypothesis
  research_notes: {
    id: string;
    date: string;
    type: "link" | "note";
    content: string;
    source: string;
  }[];
}
```

### Derived Projections

These are computed from the hypothesis ledger, not stored independently:

**Asset groups** (for BY ASSET view):
```typescript
interface AssetGroup {
  ticker: string;
  direction_consensus: "LONG" | "SHORT" | "MIXED";
  hypotheses: Hypothesis[];          // sorted by conviction desc
  theory_count: number;              // unique source theories
  max_conviction: number;            // for group sorting
}
```

**Delta set** (for delta banner):
```typescript
interface DeltaSet {
  killed: Hypothesis[];              // was alive, now KILLED
  deteriorated: Hypothesis[];        // conviction dropped > 0.5
  improved: Hypothesis[];            // conviction increased > 0.5
  new_hypotheses: Hypothesis[];      // generated after last review
  stable: Hypothesis[];              // everything else
}
```

---

## 6. API Contract

The frontend requires these endpoints from the FastAPI backend.

### Core Hypothesis APIs

| Method | Endpoint | Returns | Notes |
|--------|----------|---------|-------|
| GET | `/api/hypotheses` | `Hypothesis[]` | All hypotheses. Query params: `status`, `theory_id`, `asset`. Default sort: conviction desc. |
| GET | `/api/hypotheses/{id}` | `Hypothesis` | Single hypothesis with full detail |
| GET | `/api/hypotheses/delta?since_run_id={id}` | `DeltaSet` | Categorized changes since a specific run |
| GET | `/api/hypotheses/{id}/history` | `ConvictionHistoryEntry[]` | Conviction scores across runs for sparkline |

### Pipeline APIs

| Method | Endpoint | Returns | Notes |
|--------|----------|---------|-------|
| GET | `/api/runs` | `Run[]` | List of pipeline runs with metadata |
| GET | `/api/runs/latest` | `Run` | Most recent completed run |
| GET | `/api/runs/{id}` | `RunDetail` | Full run with all stage outputs (for audit mode) |
| GET | `/api/pipeline/status` | `PipelineStatus` | Current state of each step (complete/ready/waiting) |
| GET | `/api/pipeline/prompt/generation` | `string` | The generation prompt text for copy-paste |
| GET | `/api/pipeline/prompt/elimination` | `string` | The elimination prompt text (requires generation output) |
| POST | `/api/pipeline/import/generation` | `Hypothesis[]` | Import generation output JSON |
| POST | `/api/pipeline/import/elimination` | `Hypothesis[]` | Import elimination output JSON, triggers conviction scoring |

### Theory APIs

| Method | Endpoint | Returns | Notes |
|--------|----------|---------|-------|
| GET | `/api/theories` | `TheoryModule[]` | All 8 theories with current activation scores |
| GET | `/api/theories/{id}` | `TheoryModule` | Single theory with full detail |
| GET | `/api/theories/activation` | `ActivationScores` | Current activation tier + score for all theories |

### Journal APIs

| Method | Endpoint | Returns | Notes |
|--------|----------|---------|-------|
| GET | `/api/journal` | `JournalEntry[]` | All journal entries, newest first |
| POST | `/api/journal` | `JournalEntry` | Create new entry |
| PATCH | `/api/journal/{id}` | `JournalEntry` | Update (close position, add outcome) |

### Inbox APIs

| Method | Endpoint | Returns | Notes |
|--------|----------|---------|-------|
| GET | `/api/inbox` | `InboxItem[]` | All inbox items, newest first |
| POST | `/api/inbox` | `InboxItem` | Add new item (status: "queued") |
| GET | `/api/inbox/queued` | `InboxItem[]` | Only queued items (for pipeline prompt inclusion) |

### Briefing API

| Method | Endpoint | Returns | Notes |
|--------|----------|---------|-------|
| GET | `/api/briefing/latest` | `BriefingPacket` | Current data briefing with staleness metadata |

### User State

| Method | Endpoint | Returns | Notes |
|--------|----------|---------|-------|
| GET | `/api/user/last_reviewed` | `{ run_id: string }` | Last run the user reviewed (for delta computation) |
| POST | `/api/user/last_reviewed` | `{ run_id: string }` | Mark a run as reviewed |

---

## 7. User Workflows

### Workflow 1: Daily Scan (~2 minutes)

```
1. Open app → Ledger loads
2. Delta banner shows what changed
3. Scan KILLED items (anything I held that just died?)
4. Scan DETERIORATED items (conviction dropping on active positions?)
5. Scan IMPROVED items (anything I should add to?)
6. Click any interesting item → Hypothesis Detail
7. Check falsifier health panel → is anything close to triggering?
8. Click "MARK REVIEWED" on delta banner
9. Done
```

**Design implication:** The delta banner must load instantly and contain enough information to complete this workflow without opening any detail panels. The parenthetical reason after each delta item (e.g., "hard falsifier: credit impulse +2.4%") is essential.

### Workflow 2: Research Capture (~30 seconds per item)

```
1. Read something (FT, 42 Macro, Lyn Alden, own observation)
2. Option A: Go to Briefing tab → paste into inbox → optionally tag theory → ADD
3. Option B: If it relates to a specific hypothesis:
   a. Open Hypothesis Detail
   b. Click "+ ADD NOTE"
   c. Paste link/text → QUEUE FOR NEXT RUN
4. Done — item is queued for next pipeline run
```

**Design implication:** The inbox input must be a single text field with a single button. No forms, no required fields beyond the content itself. Theory tagging is optional. The user should be able to capture something in under 30 seconds.

### Workflow 3: Pipeline Run (~30-45 minutes, weekly)

```
1. Go to Pipeline tab (Run Mode)
2. Step 1 (Data Briefing): verify briefing is fresh → auto-complete
3. Step 2 (Activation): verify activation scores look right → auto-complete
4. Step 3 (Generation):
   a. Click SHOW PROMPT → review prompt includes Active theories + inbox items
   b. Click COPY TO CLIPBOARD
   c. Open Claude.ai → paste prompt + attach briefing packet
   d. Claude produces generation output (JSON)
   e. Copy Claude's output
   f. Back to Pipeline → click IMPORT RESULT → paste JSON
   g. System parses, stores hypotheses, advances to step 4
5. Step 4 (Elimination):
   a. Click SHOW PROMPT → review prompt includes generated hypotheses
   b. Same copy-paste-to-Claude-import cycle
   c. System parses, stores elimination results
6. Step 5 (Conviction Scoring): runs mechanically → auto-complete
7. System updates the Ledger with new/updated hypotheses
8. Return to Ledger → delta banner shows all changes from this run
```

**Design implication:** The Pipeline Run Mode must clearly indicate which step is actionable (the "ready" state) and disable buttons for steps that are blocked. The IMPORT RESULT interaction is the critical moment — it must accept either pasted JSON or a file upload, parse it, validate the schema, and provide clear error messages if the format is wrong.

---

## 8. Visual Mental Models (Adapted)

The visual mental models from the Macro Council spec (VISUAL_MENTAL_MODELS_SPEC.md) have two natural homes in the new architecture. This is a v2 feature — v1 works without them.

### Home 1: Theory Observatory

Each theory card in the Observatory could render its characteristic visual in miniature, showing activation state:

| Theory | Visual | What It Shows in New System |
|--------|--------|---------------------------|
| `valuation_mean_reversion` | Valuation gauge | ERP compression level, how stretched |
| `debt_cycle_short` | Cycle compass | Where in the 5-8 year credit cycle |
| `debt_cycle_long` | Long wave timeline | MP1/MP2/MP3 position |
| `structural_fragility` | Stress bars | Which stress domains are elevated |
| `fiscal_dominance_liquidity` | Flow diagram | Deficit → liquidity → asset price pipeline |
| `fiscal_dominance_arithmetic` | Interest expense triangle | Expense trajectory vs GDP |
| `capital_flows` | Hub-spoke flow map | Dollar gravity, EM/DM flow direction |
| `monetary_architecture` | Plumbing schematic | Reserve/collateral system health |

These visuals now answer "is this mechanism operative?" rather than "what does this persona think?" — a better question.

### Home 2: Hypothesis Detail — Falsifier Health

A new visual type, universal across all hypotheses (not theory-specific). Shows the hypothesis's vulnerability surface:

- Each soft falsifier gets a horizontal bar showing current metric value relative to threshold
- Color shifts from `--accent-positive` (far from threshold) through `--accent-gold` (approaching) to `--accent-negative` (triggered)
- Hard falsifiers get binary pass/fail indicators
- The visual communicates fragility at a glance: all green = robust, amber bars = watch closely, red = triggered

This is the most important daily visual — more important than the theory-specific visuals.

### Rendering Approach (unchanged from old spec)

- SVG-first. React components rendering inline SVG.
- No charting library. No canvas. CSS variables for all colors.
- Hand-annotated feel: thin 1px strokes, no gradients, no shadows.
- Max 720px wide within the 1200px layout.
- Trajectory shown as 90-day sparkline or ghost positions.

---

## 9. Open-Source First-Run Experience

When someone clones the repo, adds their API key, and runs the system for the first time, they should understand the architecture from the UI itself.

### What They See

1. **Ledger** loads with mock hypotheses (the same mock data in the interactive mockup). The delta banner shows example changes.
2. **Pipeline (Audit Mode)** shows a complete mock run with all five stages traced. The user can follow a hypothesis from activation through generation through elimination through scoring.
3. **Observatory** shows the 8 theories with realistic activation scores.
4. **Briefing** shows a mock briefing packet with example inbox items.

### Mock Data Package

The repo should include a `mock_data/` directory with:

```
mock_data/
├── briefing_packet.json      # realistic macro data
├── activation_scores.json    # computed from mock briefing
├── generation_output.json    # 6 hypotheses from 4 Active theories
├── elimination_output.json   # same hypotheses with SURVIVED/WOUNDED/KILLED
├── conviction_scores.json    # mechanical scoring of survivors
├── inbox_items.json          # 3 example inbox items
└── journal_entries.json      # 1 example journal entry
```

### First-Run Detection

On first load (no runs in SQLite), the system should:
1. Load mock data automatically
2. Display a small banner: "Running with mock data. Run your first pipeline to replace with real analysis."
3. Pre-populate the Pipeline (Audit Mode) with the mock run so the user can trace the architecture

---

## 10. Implementation Plan

### Component Tree

```
App.jsx
├── Header.jsx
├── NavBar.jsx
├── views/
│   ├── LedgerView.jsx
│   │   ├── DeltaBanner.jsx
│   │   ├── LedgerControls.jsx (toggle + filters)
│   │   ├── HypothesisTable.jsx
│   │   └── AssetGroupView.jsx
│   │       └── AssetGroup.jsx
│   ├── JournalView.jsx
│   │   ├── JournalEntry.jsx
│   │   └── JournalForm.jsx (modal)
│   ├── ObservatoryView.jsx
│   │   └── TheoryCard.jsx
│   ├── PipelineView.jsx
│   │   ├── PipelineRunMode.jsx
│   │   │   ├── PipelineStep.jsx
│   │   │   ├── PromptPreview.jsx
│   │   │   └── ImportPanel.jsx
│   │   └── PipelineAuditMode.jsx
│   │       └── AuditStage.jsx
│   └── BriefingView.jsx
│       ├── ResearchInbox.jsx
│       │   ├── InboxForm.jsx
│       │   └── InboxItem.jsx
│       └── BriefingGrid.jsx
│           └── BriefingPanel.jsx
├── overlays/
│   └── HypothesisDetail.jsx
│       ├── ConvictionMath.jsx
│       ├── FalsifierHealth.jsx
│       ├── EliminationAudit.jsx
│       ├── ResearchNotes.jsx (with inline input)
│       └── PositionCard.jsx
└── shared/
    ├── StatusBadge.jsx
    ├── TheoryTag.jsx
    ├── AssetTag.jsx
    ├── ConvictionDisplay.jsx (score + delta)
    ├── FalsifierCompact.jsx (triggered/total)
    ├── Sparkline.jsx (SVG)
    └── ActionMarker.jsx
```

### Build Phases

**Phase 1: Data Layer + Shell (~2 hours)**
1. SQLite schema for hypotheses, runs, journal, inbox
2. FastAPI endpoints (all from Section 6)
3. Mock data seeding
4. React + Vite scaffold with routing

**Phase 2: Ledger (~3 hours)**
1. HypothesisTable with all columns
2. DeltaBanner with categorized changes
3. LedgerControls with filter pills
4. AssetGroupView with direction consensus
5. BY HYPOTHESIS / BY ASSET toggle

**Phase 3: Hypothesis Detail (~2 hours)**
1. Modal overlay with backdrop
2. All 7 sections (A through G)
3. ConvictionMath three-column grid
4. FalsifierHealth with dots and severity badges
5. Research Notes with inline input

**Phase 4: Pipeline (~2 hours)**
1. Run Mode with step workflow
2. Prompt generation (building prompt text from Active theories + inbox)
3. Import panel (paste JSON + validation)
4. Audit Mode with collapsible stages
5. Mode toggle

**Phase 5: Supporting Views (~2 hours)**
1. Journal with entry cards and form
2. Observatory with theory grid
3. Briefing with inbox and data grid

**Phase 6: Polish (~1 hour)**
1. Mobile responsive collapse
2. Keyboard shortcuts (ESC to close detail, / to search)
3. Loading states
4. Error handling for import parsing
5. First-run mock data detection

**Estimated total: 12-14 hours of implementation.**

### Technology Choices

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | React 18 + Vite | Fast dev, component model matches the spec |
| Routing | React Router v6 | Standard, lightweight |
| State | React Context + useReducer | No external state library needed at this scale |
| Styling | CSS variables + vanilla CSS | Matches Hermes Editorial, no Tailwind (too generic) |
| Charts/SVG | Hand-rolled SVG components | Required by design system (no charting library) |
| Backend | FastAPI + SQLite | Already specified in architecture |
| HTTP | fetch + SWR or React Query | Cache management for hypothesis data |

### SQLite Schema (core tables)

```sql
CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  status TEXT NOT NULL,  -- 'complete' | 'partial'
  generation_output TEXT,  -- raw JSON from Claude
  elimination_output TEXT, -- raw JSON from Claude
  activation_scores TEXT   -- JSON map of theory_id → tier
);

CREATE TABLE hypotheses (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id),
  short_name TEXT NOT NULL,
  full_statement TEXT NOT NULL,
  source_theory TEXT NOT NULL,
  source_theories TEXT,  -- JSON array for multi-theory
  status TEXT NOT NULL,  -- 'SURVIVED' | 'WOUNDED' | 'KILLED'
  conviction REAL,
  conviction_math TEXT,  -- full JSON of 3-stage pipeline
  hard_falsifiers TEXT,  -- JSON array
  soft_falsifiers TEXT,  -- JSON array
  predicted_assets TEXT, -- JSON array of tickers
  asset_direction TEXT,  -- JSON map ticker → direction
  timeframe TEXT,
  elimination_notes TEXT,
  generated_date TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE journal_entries (
  id TEXT PRIMARY KEY,
  hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
  date TEXT NOT NULL,
  action TEXT NOT NULL,
  size TEXT,
  conviction_at_entry REAL,
  reasoning TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  outcome TEXT,
  closed_date TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE inbox_items (
  id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  type TEXT NOT NULL,  -- 'link' | 'note'
  content TEXT NOT NULL,
  source TEXT,
  theories TEXT,  -- JSON array of theory_ids
  hypothesis_id TEXT REFERENCES hypotheses(id),  -- if added from detail
  status TEXT NOT NULL DEFAULT 'queued',
  incorporated_run_id TEXT REFERENCES runs(id),
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE user_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
-- Stores: last_reviewed_run_id, etc.
```

---

## Appendix: What This Spec Does NOT Cover

- **Theory module CRUD in the frontend.** Theory modules are markdown files maintained by the user outside the app. The Observatory displays them but does not edit them. (A future version could add inline theory editing.)
- **Automated data agent.** The data briefing is assumed to be produced by a separate Python script. The frontend only displays and validates staleness.
- **Backtesting or P&L tracking.** The Journal records decisions and outcomes but does not compute portfolio returns.
- **Authentication.** The system runs locally. No auth needed.
- **Dark mode.** Explicitly deferred.
- **Mobile input.** Mobile is read-only. All input surfaces (inbox, journal, import) are desktop-only.

---

*This specification is the contract between the design thread and the implementation. The data shapes, API endpoints, and component names defined here should be used directly by Claude Code. The design system and layout rules are non-negotiable — they are the visual identity of the system.*
