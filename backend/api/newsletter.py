# newsletter.py -- Newsletter prompt builder + import/storage/trade-diffing.
# Depends on: db/database.py, db/models.py, config.py
# Depended on by: main.py (router registration)
#
# Assembles a system prompt + user prompt for the newsletter.
# The user copies these into Claude.ai, then pastes the output back.
# On import, the backend stores the newsletter and generates pending
# trade actions by diffing recommendations against open trades.
from __future__ import annotations

import json
import re
import subprocess
from datetime import date, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import (
    Hypothesis,
    HypothesisThread,
    Newsletter,
    PendingTradeAction,
    Run,
    Trade,
)
from backend.config import DATA_DIR, MOCK_DATA_DIR

router = APIRouter(tags=["newsletter"])

CONVICTION_THRESHOLD = 5
BASE_ALLOCATION = 10000  # $10k notional per trade at conviction 10

YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

SYSTEM_PROMPT = """You are a macro strategist writing a weekly newsletter. Your style is:
- Terse, declarative sentences. No hedging language.
- Lead with the trade, then the mechanism, then the risk.
- Every sentence must be load-bearing. No filler, no "in conclusion."
- Use the structured data provided. Do not add analysis beyond what the data supports.
- The newsletter must fit on one A4 page when printed in 11pt type.
- Maximum 4 trade ideas. Only include hypotheses with conviction >= 5.
- For "WHAT BREAKS IT": pick the 2 falsifiers closest to triggering or the 2 with highest severity. State the condition and the current data value.
- IMPORTANT: If all surviving hypotheses scored at or near the conviction floor (5/10), say so plainly. Open with a MARKET POSTURE section stating that conviction is low across the board and why. Do not manufacture confidence. "We do not have a strong view this week" is a valid and honest output. Explain what is keeping conviction low (e.g., exogenous uncertainty, conflicting signals, data gaps) and what would need to change for conviction to build.
- Hypotheses belong to THREADS that persist across pipeline runs. Use thread context to convey stability: a thread CONFIRMed across multiple runs is an established view; a NEW thread is a fresh call. Mention continuity naturally (e.g., "now in its 4th week" or "new this week") -- do not list lifecycle actions mechanically.
- When a hypothesis has realization data (expression return vs. payoff band), incorporate it naturally: "GLD +6.2%, tracking the lower bound of the 10-20% band" conveys more than just repeating the thesis.

Output format (exactly this structure):

MERIDIAN MACRO WEEKLY                                    [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MARKET POSTURE
  > [1-3 sentences: overall conviction level, what is driving it, what
     would change it. When conviction is low, say so. When exogenous
     factors (policy uncertainty, geopolitical risk) dominate, name them.]

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
SYSTEM: Falsification Engine v7 | 8 theory modules | Mechanical scoring | Thread lifecycle
This is not investment advice. These are hypotheses that survived
systematic falsification. What the system found != what you should do.

Maximum 800 words total. Use ASCII characters only -- no emoji, no unicode arrows.

IMPORTANT: After the newsletter text, on a new line, output a JSON block wrapped in
<TRADES> tags containing the trade recommendations from the newsletter. Each entry
must include the thread_id, hypothesis_id (current instance), primary ticker, direction,
and conviction score.
Format:

<TRADES>
[{"thread_id": "T-...", "hypothesis_id": "H-...", "ticker": "GLD", "direction": "LONG", "conviction": 8}]
</TRADES>

Include ONLY the hypotheses that appear in the newsletter. Use the exact thread_id and
hypothesis_id values from the data provided below."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_current_price(ticker: str) -> float | None:
    """Fetch latest closing price for a ticker via Yahoo v8 chart API + curl."""
    url = f"{YAHOO_BASE_URL}/{ticker}?range=5d&interval=1d&includePrePost=false"
    try:
        result = subprocess.run(
            [
                "curl", "-s", "--max-time", "10",
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                url,
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0 or not result.stdout:
            return None
        data = json.loads(result.stdout)
        chart_result = data.get("chart", {}).get("result")
        if not chart_result:
            return None
        quotes = chart_result[0].get("indicators", {}).get("quote", [{}])[0]
        closes = quotes.get("close", [])
        valid = [c for c in closes if c is not None]
        return round(valid[-1], 2) if valid else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


def _next_newsletter_id(db: Session) -> str:
    year = date.today().year
    prefix = f"NL-{year}-"
    existing = (
        db.query(Newsletter)
        .filter(Newsletter.id.like(f"{prefix}%"))
        .order_by(desc(Newsletter.id))
        .first()
    )
    seq = int(existing.id.split("-")[-1]) + 1 if existing else 1
    return f"{prefix}{seq:03d}"


_pta_counter = 0

def _next_pta_id(db: Session) -> str:
    global _pta_counter
    existing = (
        db.query(PendingTradeAction)
        .order_by(desc(PendingTradeAction.id))
        .first()
    )
    db_seq = int(existing.id.replace("PTA-", "")) if existing else 0
    _pta_counter = max(_pta_counter, db_seq) + 1
    return f"PTA-{_pta_counter:03d}"


def _next_trade_id(db: Session) -> str:
    year = date.today().year
    prefix = f"T-{year}-"
    existing = (
        db.query(Trade)
        .filter(Trade.id.like(f"{prefix}%"))
        .order_by(desc(Trade.id))
        .first()
    )
    seq = int(existing.id.split("-")[-1]) + 1 if existing else 1
    return f"{prefix}{seq:03d}"


def _compute_shares(conviction: float, price: float) -> float:
    """Compute position size based on conviction and price."""
    if price <= 0:
        return 0
    allocation = BASE_ALLOCATION * (conviction / 10)
    return round(allocation / price)


def _newsletter_to_dict(nl: Newsletter, truncate_content: bool = False) -> dict:
    recs = json.loads(nl.trade_recommendations) if nl.trade_recommendations else []
    content = nl.content
    if truncate_content:
        # First non-empty line as preview
        lines = [l for l in content.split("\n") if l.strip()]
        content = lines[0] if lines else ""
    return {
        "id": nl.id,
        "date": nl.date,
        "run_id": nl.run_id,
        "content": content,
        "trade_recommendations": recs,
        "trade_count": len(recs),
        "created_at": nl.created_at,
    }


def _pta_to_dict(pta: PendingTradeAction) -> dict:
    return {
        "id": pta.id,
        "newsletter_id": pta.newsletter_id,
        "action_type": pta.action_type,
        "hypothesis_id": pta.hypothesis_id,
        "ticker": pta.ticker,
        "direction": pta.direction,
        "conviction": pta.conviction,
        "proposed_shares": pta.proposed_shares,
        "proposed_price": pta.proposed_price,
        "existing_trade_id": pta.existing_trade_id,
        "reduce_to_shares": pta.reduce_to_shares,
        "status": pta.status,
        "executed_at": pta.executed_at,
        "executed_price": pta.executed_price,
    }


# ---------------------------------------------------------------------------
# Prompt builder (existing)
# ---------------------------------------------------------------------------

@router.get("/newsletter/prompt")
def get_newsletter_prompt(db: Session = Depends(get_db)):
    """Assemble system + user prompts for newsletter generation via Claude.ai."""

    latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()
    if not latest_run:
        raise HTTPException(status_code=400, detail="No pipeline runs found")

    qualifying = (
        db.query(Hypothesis)
        .filter(
            Hypothesis.run_id == latest_run.id,
            Hypothesis.status.in_(["SURVIVED", "WOUNDED"]),
            Hypothesis.conviction >= CONVICTION_THRESHOLD,
        )
        .order_by(desc(Hypothesis.conviction))
        .all()
    )

    if not qualifying:
        raise HTTPException(
            status_code=400,
            detail=f"No hypotheses meet conviction >= {CONVICTION_THRESHOLD} threshold in the latest run",
        )

    # Gather thread data for qualifying hypotheses (v7)
    thread_ids = [h.thread_id for h in qualifying if h.thread_id]
    threads_by_id: dict[str, HypothesisThread] = {}
    if thread_ids:
        threads = db.query(HypothesisThread).filter(HypothesisThread.thread_id.in_(thread_ids)).all()
        threads_by_id = {t.thread_id: t for t in threads}

    activation_scores = json.loads(latest_run.activation_scores) if latest_run.activation_scores else {}
    briefing_summary = _load_briefing_summary()

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

    user_prompt = _build_user_prompt(qualifying, activation_scores, briefing_summary, untestable, threads_by_id)

    return {
        "system_prompt": SYSTEM_PROMPT.strip(),
        "user_prompt": user_prompt,
    }


# ---------------------------------------------------------------------------
# Newsletter import + trade diffing
# ---------------------------------------------------------------------------

@router.post("/newsletter/import")
def import_newsletter(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Import a newsletter and generate pending trade actions."""
    content = payload.get("content", "").strip()
    trade_recs = payload.get("trade_recommendations", [])

    if not content:
        raise HTTPException(status_code=400, detail="Newsletter content is required")

    # Get latest run for context
    latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()

    # Store newsletter
    nl = Newsletter(
        id=_next_newsletter_id(db),
        date=date.today().isoformat(),
        run_id=latest_run.id if latest_run else None,
        content=content,
        trade_recommendations=json.dumps(trade_recs) if trade_recs else None,
    )
    db.add(nl)
    db.flush()  # flush so newsletter FK is available for pending actions

    # Cancel any previous PENDING actions (only latest newsletter matters)
    db.query(PendingTradeAction).filter(
        PendingTradeAction.status == "PENDING"
    ).update({"status": "REJECTED"})

    # Diff recommendations against current open trades
    open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()

    # Build lookup: hypothesis_id -> open trade
    open_by_hyp = {}
    for t in open_trades:
        open_by_hyp[t.hypothesis_id] = t

    # Track which open trades are accounted for by recommendations
    accounted_trade_ids = set()
    pending_actions = []

    for rec in trade_recs:
        hyp_id = rec.get("hypothesis_id")
        ticker = rec.get("ticker", "").upper()
        direction = rec.get("direction", "LONG").upper()
        conviction = rec.get("conviction", 0)

        if not hyp_id or not ticker:
            continue

        # Fetch current price for sizing
        price = _fetch_current_price(ticker)
        if price is None:
            price = 0

        target_shares = _compute_shares(conviction, price) if price > 0 else 0

        existing = open_by_hyp.get(hyp_id)
        if existing and existing.ticker == ticker:
            accounted_trade_ids.add(existing.id)

            if conviction < existing.conviction_at_entry:
                # Conviction dropped -> REDUCE
                new_shares = _compute_shares(conviction, existing.entry_price)
                if new_shares < existing.shares:
                    pta = PendingTradeAction(
                        id=_next_pta_id(db),
                        newsletter_id=nl.id,
                        action_type="REDUCE",
                        hypothesis_id=hyp_id,
                        ticker=ticker,
                        direction=direction,
                        conviction=conviction,
                        proposed_shares=new_shares,
                        proposed_price=price,
                        existing_trade_id=existing.id,
                        reduce_to_shares=new_shares,
                        status="PENDING",
                    )
                    db.add(pta)
                    pending_actions.append(pta)
            # Same or higher conviction -> no action needed
        else:
            # New recommendation -> OPEN
            pta = PendingTradeAction(
                id=_next_pta_id(db),
                newsletter_id=nl.id,
                action_type="OPEN",
                hypothesis_id=hyp_id,
                ticker=ticker,
                direction=direction,
                conviction=conviction,
                proposed_shares=target_shares,
                proposed_price=price,
                status="PENDING",
            )
            db.add(pta)
            pending_actions.append(pta)

    # Open trades not in recommendations -> CLOSE
    for t in open_trades:
        if t.id not in accounted_trade_ids:
            price = _fetch_current_price(t.ticker)
            pta = PendingTradeAction(
                id=_next_pta_id(db),
                newsletter_id=nl.id,
                action_type="CLOSE",
                hypothesis_id=t.hypothesis_id,
                ticker=t.ticker,
                direction=t.direction,
                conviction=0,
                proposed_shares=0,
                proposed_price=price or 0,
                existing_trade_id=t.id,
                status="PENDING",
            )
            db.add(pta)
            pending_actions.append(pta)

    db.commit()
    db.refresh(nl)

    return {
        "newsletter": _newsletter_to_dict(nl),
        "pending_actions": [_pta_to_dict(p) for p in pending_actions],
        "pending_count": len(pending_actions),
    }


@router.get("/newsletters")
def list_newsletters(db: Session = Depends(get_db)):
    """List all newsletters, newest first."""
    newsletters = db.query(Newsletter).order_by(desc(Newsletter.date)).all()
    return [_newsletter_to_dict(nl, truncate_content=True) for nl in newsletters]


@router.get("/newsletters/{newsletter_id}")
def get_newsletter(newsletter_id: str, db: Session = Depends(get_db)):
    """Get full newsletter detail."""
    nl = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
    if not nl:
        raise HTTPException(status_code=404, detail=f"Newsletter {newsletter_id} not found")

    # Include pending actions for this newsletter
    actions = (
        db.query(PendingTradeAction)
        .filter(PendingTradeAction.newsletter_id == newsletter_id)
        .all()
    )

    result = _newsletter_to_dict(nl)
    result["pending_actions"] = [_pta_to_dict(a) for a in actions]
    return result


# ---------------------------------------------------------------------------
# Briefing helpers (unchanged)
# ---------------------------------------------------------------------------

def _load_briefing_summary() -> str:
    """Load key data points from the briefing packet."""
    for path in [DATA_DIR / "briefing_packet.json", MOCK_DATA_DIR / "briefing_packet.json"]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            lines = []
            lines.append(f"Timestamp: {data.get('timestamp', 'unknown')}")

            for section_name in ["growth", "inflation", "rates", "liquidity", "credit", "sentiment"]:
                section = data.get(section_name, {})
                if isinstance(section, dict):
                    for key, val in section.items():
                        if val is not None:
                            lines.append(f"  {section_name}.{key}: {val}")

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
    threads_by_id: dict | None = None,
) -> str:
    """Assemble the structured data payload for the user prompt."""
    if threads_by_id is None:
        threads_by_id = {}

    sections = []
    sections.append("Generate the newsletter from this data:")
    sections.append("")

    sections.append(f"HYPOTHESES (conviction >= {CONVICTION_THRESHOLD}, ordered by conviction desc):")
    sections.append("")
    for h in hypotheses:
        conv_math = json.loads(h.conviction_math) if h.conviction_math else {}
        soft_f = json.loads(h.soft_falsifiers) if h.soft_falsifiers else []
        hard_f = json.loads(h.hard_falsifiers) if h.hard_falsifiers else []
        assets = json.loads(h.predicted_assets) if h.predicted_assets else []
        directions = json.loads(h.asset_direction) if h.asset_direction else {}

        sections.append(f"  [{h.short_name}]")
        sections.append(f"    Instance ID: {h.id}")

        # Thread context (v7)
        thread = threads_by_id.get(h.thread_id) if h.thread_id else None
        if thread:
            sections.append(f"    Thread ID: {thread.thread_id}")
            action = h.lifecycle_action or "NEW"
            sections.append(f"    Lifecycle: {action} (run {thread.total_instances} of thread, {thread.confirmation_count} consecutive confirms)")
            sections.append(f"    Thread created: {thread.created_date}")
        elif h.thread_id:
            sections.append(f"    Thread ID: {h.thread_id}")
            if h.lifecycle_action:
                sections.append(f"    Lifecycle: {h.lifecycle_action}")

        sections.append(f"    Theory: {h.source_theory}")
        sections.append(f"    Conviction: {h.conviction}/10")
        sections.append(f"    Thesis: {h.full_statement}")
        sections.append(f"    Timeframe: {h.timeframe}")

        asset_lines = []
        for ticker in assets:
            direction = directions.get(ticker, "?")
            asset_lines.append(f"{ticker} {direction}")
        sections.append(f"    Expression: {', '.join(asset_lines)}")

        # Realization data (v6/v7)
        if h.expression_return is not None:
            sections.append(f"    Realization: {h.expression_return:+.1%} expression return")
            if h.realization_vs_lower is not None and h.realization_vs_upper is not None:
                sections.append(f"      {h.realization_vs_lower:.2f}x lower bound, {h.realization_vs_upper:.2f}x upper bound")
            if h.time_elapsed_pct is not None:
                sections.append(f"      {h.time_elapsed_pct:.0%} of time elapsed")

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

        all_falsifiers.sort(key=lambda x: (
            0 if x["status"] in ("TRIGGERED", "FAILED") else 1,
            severity_order.get(x.get("severity", "minor"), 3),
        ))

        sections.append("    Falsifiers:")
        for f in all_falsifiers[:6]:
            if f["type"] == "HARD":
                sections.append(f"      HARD: {f['condition']} [{f['status']}]")
            else:
                sections.append(
                    f"      SOFT ({f['severity']}): {f['name']} [{f['status']}]"
                    + (f" metric={f['metric']} threshold={f['threshold']}" if f.get("metric") else "")
                )

        sections.append("")

    sections.append("ACTIVE THEORIES:")
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
        for t in theories_list:
            tier = t.get("tier") or t.get("effective_tier") or "Unknown"
            if tier != "Inactive":
                sections.append(f"  {t.get('theory_id', '?')}: {tier}")
    sections.append("")

    sections.append("BRIEFING SUMMARY:")
    sections.append(briefing_summary)
    sections.append("")

    sections.append("UNTESTABLE FALSIFIERS:")
    if untestable:
        for u in untestable:
            sections.append(f"  [{u['hypothesis']}] {u['falsifier']}" + (f" (severity: {u['severity']})" if u['severity'] else ""))
    else:
        sections.append("  (none)")

    return "\n".join(sections)
