# newsletter.py -- Newsletter prompt builder endpoint.
# Depends on: db/database.py, db/models.py, config.py
# Depended on by: main.py (router registration)
#
# Assembles a system prompt + user prompt for the newsletter.
# The user copies these into Claude.ai — no API call from the backend.
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis, Run
from backend.config import DATA_DIR, MOCK_DATA_DIR

router = APIRouter(tags=["newsletter"])

CONVICTION_THRESHOLD = 6

SYSTEM_PROMPT = """You are a macro strategist writing a weekly newsletter. Your style is:
- Terse, declarative sentences. No hedging language.
- Lead with the trade, then the mechanism, then the risk.
- Every sentence must be load-bearing. No filler, no "in conclusion."
- Use the structured data provided. Do not add analysis beyond what the data supports.
- The newsletter must fit on one A4 page when printed in 11pt type.
- Maximum 4 trade ideas. Only include hypotheses with conviction >= 6.
- For "WHAT BREAKS IT": pick the 2 falsifiers closest to triggering or the 2 with highest severity. State the condition and the current data value.

Output format (exactly this structure):

MERIDIAN MACRO WEEKLY                                    [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HIGHEST CONVICTION: [trade name]                    Conviction: [X]/10
  > THESIS: [2-3 sentences: what the mechanism is, why now]
  > EXPRESSION: [ticker(s) and direction]
  > WHAT BREAKS IT: [the 2 most important falsifiers, current status]

[Repeat for each qualifying hypothesis, max 4 entries]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGIME CONTEXT
  > Active theories: [list with activation %]
  > Key data: [3-4 most relevant data points from briefing]
  > What we're watching: [top UNTESTABLE falsifiers awaiting data]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM: Falsification Engine v2 | 8 theory modules | Mechanical scoring
This is not investment advice. These are hypotheses that survived
systematic falsification. What the system found != what you should do.

Maximum 800 words total. Use ASCII characters only — no emoji, no unicode arrows."""


@router.get("/newsletter/prompt")
def get_newsletter_prompt(db: Session = Depends(get_db)):
    """Assemble system + user prompts for newsletter generation via Claude.ai."""

    # 1. Find the latest run
    latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()
    if not latest_run:
        raise HTTPException(status_code=400, detail="No pipeline runs found")

    # 2. Fetch SURVIVED hypotheses with conviction >= threshold from latest run
    qualifying = (
        db.query(Hypothesis)
        .filter(
            Hypothesis.run_id == latest_run.id,
            Hypothesis.status == "SURVIVED",
            Hypothesis.conviction >= CONVICTION_THRESHOLD,
        )
        .order_by(desc(Hypothesis.conviction))
        .all()
    )

    if not qualifying:
        raise HTTPException(
            status_code=400,
            detail="No hypotheses meet conviction >= 6 threshold in the latest run",
        )

    # 3. Parse activation scores from the run
    activation_scores = json.loads(latest_run.activation_scores) if latest_run.activation_scores else {}

    # 4. Load briefing summary
    briefing_summary = _load_briefing_summary()

    # 5. Collect UNTESTABLE falsifiers across qualifying hypotheses
    untestable = []
    for h in qualifying:
        soft_f = json.loads(h.soft_falsifiers) if h.soft_falsifiers else []
        hard_f = json.loads(h.hard_falsifiers) if h.hard_falsifiers else []
        for f in soft_f + hard_f:
            if f.get("status") == "UNTESTABLE":
                untestable.append({
                    "hypothesis": h.short_name,
                    "falsifier": f.get("name") or f.get("condition", ""),
                    "severity": f.get("severity", ""),
                })

    # 6. Build the user prompt
    user_prompt = _build_user_prompt(qualifying, activation_scores, briefing_summary, untestable)

    return {
        "system_prompt": SYSTEM_PROMPT.strip(),
        "user_prompt": user_prompt,
    }


def _load_briefing_summary() -> str:
    """Load key data points from the briefing packet."""
    for path in [DATA_DIR / "briefing_packet.json", MOCK_DATA_DIR / "briefing_packet.json"]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            lines = []
            lines.append(f"Timestamp: {data.get('timestamp', 'unknown')}")

            # Extract key sections
            for section_name in ["growth", "inflation", "rates", "liquidity", "credit", "sentiment"]:
                section = data.get(section_name, {})
                if isinstance(section, dict):
                    for key, val in section.items():
                        if val is not None:
                            lines.append(f"  {section_name}.{key}: {val}")

            # Computed metrics
            computed = data.get("computed", {})
            if isinstance(computed, dict):
                for key, val in computed.items():
                    if val is not None:
                        lines.append(f"  computed.{key}: {val}")

            return "\n".join(lines)
    return "(No briefing data available)"


def _build_user_prompt(
    hypotheses: list[Hypothesis],
    activation_scores: dict,
    briefing_summary: str,
    untestable: list[dict],
) -> str:
    """Assemble the structured data payload for the user prompt."""
    sections = []
    sections.append("Generate the newsletter from this data:")
    sections.append("")

    # Hypotheses
    sections.append(f"HYPOTHESES (conviction >= {CONVICTION_THRESHOLD}, ordered by conviction desc):")
    sections.append("")
    for h in hypotheses:
        conv_math = json.loads(h.conviction_math) if h.conviction_math else {}
        soft_f = json.loads(h.soft_falsifiers) if h.soft_falsifiers else []
        hard_f = json.loads(h.hard_falsifiers) if h.hard_falsifiers else []
        assets = json.loads(h.predicted_assets) if h.predicted_assets else []
        directions = json.loads(h.asset_direction) if h.asset_direction else {}

        sections.append(f"  [{h.short_name}]")
        sections.append(f"    Theory: {h.source_theory}")
        sections.append(f"    Conviction: {h.conviction}/10")
        sections.append(f"    Thesis: {h.full_statement}")
        sections.append(f"    Timeframe: {h.timeframe}")

        # Assets with direction
        asset_lines = []
        for ticker in assets:
            direction = directions.get(ticker, "?")
            asset_lines.append(f"{ticker} {direction}")
        sections.append(f"    Expression: {', '.join(asset_lines)}")

        # Top falsifiers (sorted by severity: major > medium > minor)
        severity_order = {"major": 0, "medium": 1, "minor": 2}
        all_falsifiers = []
        for f in hard_f:
            all_falsifiers.append({
                "type": "HARD",
                "condition": f.get("condition", ""),
                "status": f.get("status", ""),
                "severity": "hard",
            })
        for f in soft_f:
            all_falsifiers.append({
                "type": "SOFT",
                "name": f.get("name", ""),
                "severity": f.get("severity", "minor"),
                "status": f.get("status", ""),
                "metric": f.get("metric", ""),
                "threshold": f.get("threshold", ""),
            })

        # Sort: triggered first, then by severity
        all_falsifiers.sort(key=lambda x: (
            0 if x["status"] in ("TRIGGERED", "FAILED") else 1,
            severity_order.get(x.get("severity", "minor"), 3),
        ))

        sections.append("    Falsifiers:")
        for f in all_falsifiers[:6]:  # Cap at 6 most important
            if f["type"] == "HARD":
                sections.append(f"      HARD: {f['condition']} [{f['status']}]")
            else:
                sections.append(
                    f"      SOFT ({f['severity']}): {f['name']} [{f['status']}]"
                    + (f" metric={f['metric']} threshold={f['threshold']}" if f.get("metric") else "")
                )

        sections.append("")

    # Active theories
    sections.append("ACTIVE THEORIES:")
    # activation_scores is a list of objects, each with theory_id, tier/effective_tier, score
    theories_list = activation_scores if isinstance(activation_scores, list) else []
    active_found = False
    for t in theories_list:
        tier = t.get("tier") or t.get("effective_tier") or "Unknown"
        if tier == "Active":
            theory_id = t.get("theory_id", "?")
            score = t.get("score", 0)
            if isinstance(score, (int, float)) and score is not None:
                sections.append(f"  {theory_id}: {score:.0%}")
            else:
                sections.append(f"  {theory_id}: {tier}")
            active_found = True
    if not active_found:
        # Show all non-inactive for context
        for t in theories_list:
            tier = t.get("tier") or t.get("effective_tier") or "Unknown"
            if tier != "Inactive":
                sections.append(f"  {t.get('theory_id', '?')}: {tier}")
    sections.append("")

    # Briefing summary
    sections.append("BRIEFING SUMMARY:")
    sections.append(briefing_summary)
    sections.append("")

    # Untestable falsifiers
    sections.append("UNTESTABLE FALSIFIERS:")
    if untestable:
        for u in untestable:
            sections.append(f"  [{u['hypothesis']}] {u['falsifier']}" + (f" (severity: {u['severity']})" if u['severity'] else ""))
    else:
        sections.append("  (none)")

    return "\n".join(sections)
