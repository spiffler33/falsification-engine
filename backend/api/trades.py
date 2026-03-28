# trades.py -- Trade tracker CRUD + price lookup.
# Backend stores primitives only. All derived values (P&L, days held,
# notional, performance stats) are computed at render time by the frontend.
# Depends on: db/database.py, db/models.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json
import subprocess
from datetime import date

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import PendingTradeAction, Run, Trade

router = APIRouter(tags=["trades"])

YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


def _fetch_current_price(ticker: str) -> Optional[float]:
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
        if not valid:
            return None

        return round(valid[-1], 2)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


_trade_counter = 0

def _next_trade_id(db: Session) -> str:
    """Generate T-YYYY-NNN sequential ID, safe for batch inserts."""
    global _trade_counter
    year = date.today().year
    prefix = f"T-{year}-"
    existing = (
        db.query(Trade)
        .filter(Trade.id.like(f"{prefix}%"))
        .order_by(desc(Trade.id))
        .first()
    )
    db_seq = int(existing.id.split("-")[-1]) if existing else 0
    _trade_counter = max(_trade_counter, db_seq) + 1
    return f"{prefix}{_trade_counter:03d}"


def _trade_to_dict(t: Trade) -> dict:
    """Convert Trade model to frontend-friendly dict — primitives only."""
    return {
        "id": t.id,
        "hypothesis_id": t.hypothesis_id,
        "run_id": t.run_id,
        "newsletter_id": t.newsletter_id,
        "ticker": t.ticker,
        "direction": t.direction,
        "entry_date": t.entry_date,
        "entry_price": t.entry_price,
        "shares": t.shares,
        "conviction_at_entry": t.conviction_at_entry,
        "exit_date": t.exit_date,
        "exit_price": t.exit_price,
        "exit_reason": t.exit_reason,
        "status": t.status,
        "hypothesis_short_name": t.hypothesis_short_name,
        "hypothesis_theory": t.hypothesis_theory,
        "hypothesis_status_at_entry": t.hypothesis_status_at_entry,
    }


@router.get("/trades")
def list_trades(
    status: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    hypothesis_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Trade)
    if status:
        q = q.filter(Trade.status == status.upper())
    if ticker:
        q = q.filter(Trade.ticker == ticker.upper())
    if hypothesis_id:
        q = q.filter(Trade.hypothesis_id == hypothesis_id)
    trades = q.order_by(desc(Trade.entry_date)).all()
    return [_trade_to_dict(t) for t in trades]


@router.post("/trades")
def create_trade(payload: dict = Body(...), db: Session = Depends(get_db)):
    hypothesis_id = payload.get("hypothesis_id")
    if not hypothesis_id:
        raise HTTPException(status_code=400, detail="hypothesis_id is required")

    h = db.query(HypothesisModel).filter(HypothesisModel.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail=f"Hypothesis {hypothesis_id} not found")

    ticker = payload.get("ticker", "").upper()
    direction = payload.get("direction", "LONG").upper()
    entry_price = payload.get("entry_price")
    shares = payload.get("shares")

    if not ticker or entry_price is None or shares is None:
        raise HTTPException(status_code=400, detail="ticker, entry_price, and shares are required")

    entry_date = payload.get("entry_date", date.today().isoformat())

    # Get current run_id
    latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()

    trade = Trade(
        id=_next_trade_id(db),
        hypothesis_id=hypothesis_id,
        run_id=latest_run.id if latest_run else None,
        ticker=ticker,
        direction=direction,
        entry_date=entry_date,
        entry_price=float(entry_price),
        shares=float(shares),
        conviction_at_entry=h.conviction,
        status="OPEN",
        hypothesis_short_name=h.short_name,
        hypothesis_theory=h.source_theory,
        hypothesis_status_at_entry=h.status,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return _trade_to_dict(trade)


@router.patch("/trades/{trade_id}")
def close_trade(trade_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")

    if "exit_price" in payload:
        trade.exit_price = float(payload["exit_price"])
        trade.exit_date = payload.get("exit_date", date.today().isoformat())
        trade.exit_reason = payload.get("exit_reason", "manual")
        trade.status = "CLOSED"

    db.commit()
    db.refresh(trade)
    return _trade_to_dict(trade)


@router.get("/trades/pending")
def list_pending_actions(db: Session = Depends(get_db)):
    """List all PENDING trade actions from newsletter imports."""
    actions = (
        db.query(PendingTradeAction)
        .filter(PendingTradeAction.status == "PENDING")
        .all()
    )
    return [
        {
            "id": a.id,
            "newsletter_id": a.newsletter_id,
            "action_type": a.action_type,
            "hypothesis_id": a.hypothesis_id,
            "ticker": a.ticker,
            "direction": a.direction,
            "conviction": a.conviction,
            "proposed_shares": a.proposed_shares,
            "proposed_price": a.proposed_price,
            "existing_trade_id": a.existing_trade_id,
            "reduce_to_shares": a.reduce_to_shares,
            "status": a.status,
        }
        for a in actions
    ]


@router.post("/trades/signoff")
def signoff_trades(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Execute approved pending trade actions at live prices."""
    actions = payload.get("actions", [])
    if not actions:
        raise HTTPException(status_code=400, detail="No actions provided")

    results = []
    for item in actions:
        pta_id = item.get("pending_action_id")
        approved = item.get("approved", False)

        pta = db.query(PendingTradeAction).filter(PendingTradeAction.id == pta_id).first()
        if not pta or pta.status != "PENDING":
            continue

        if not approved:
            pta.status = "REJECTED"
            results.append({"id": pta_id, "status": "REJECTED"})
            continue

        # Fetch live price for execution
        live_price = _fetch_current_price(pta.ticker)
        if live_price is None:
            live_price = pta.proposed_price or 0

        now = date.today().isoformat()

        if pta.action_type == "OPEN":
            # Create new trade
            h = db.query(HypothesisModel).filter(HypothesisModel.id == pta.hypothesis_id).first()
            shares = pta.proposed_shares
            if live_price > 0 and pta.conviction:
                # Recompute shares at live price
                from backend.api.newsletter import BASE_ALLOCATION
                allocation = BASE_ALLOCATION * (pta.conviction / 10)
                shares = round(allocation / live_price)

            latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()
            trade = Trade(
                id=_next_trade_id(db),
                hypothesis_id=pta.hypothesis_id,
                run_id=latest_run.id if latest_run else None,
                newsletter_id=pta.newsletter_id,
                ticker=pta.ticker,
                direction=pta.direction,
                entry_date=now,
                entry_price=live_price,
                shares=shares,
                conviction_at_entry=pta.conviction,
                status="OPEN",
                hypothesis_short_name=h.short_name if h else None,
                hypothesis_theory=h.source_theory if h else None,
                hypothesis_status_at_entry=h.status if h else None,
            )
            db.add(trade)
            results.append({"id": pta_id, "status": "EXECUTED", "trade_id": trade.id})

        elif pta.action_type == "CLOSE":
            # Close existing trade
            existing = db.query(Trade).filter(Trade.id == pta.existing_trade_id).first()
            if existing:
                existing.exit_price = live_price
                existing.exit_date = now
                existing.exit_reason = "newsletter_removed"
                existing.status = "CLOSED"
                results.append({"id": pta_id, "status": "EXECUTED", "trade_id": existing.id})
            else:
                results.append({"id": pta_id, "status": "REJECTED", "reason": "trade not found"})

        elif pta.action_type == "REDUCE":
            # Partial close: reduce shares on existing trade
            existing = db.query(Trade).filter(Trade.id == pta.existing_trade_id).first()
            if existing and pta.reduce_to_shares is not None:
                close_shares = existing.shares - pta.reduce_to_shares
                if close_shares > 0:
                    # Close the excess portion
                    existing.exit_price = live_price
                    existing.exit_date = now
                    existing.exit_reason = "conviction_reduced"
                    existing.status = "CLOSED"

                    # Open a new smaller position at original entry price
                    h = db.query(HypothesisModel).filter(HypothesisModel.id == pta.hypothesis_id).first()
                    latest_run = db.query(Run).order_by(desc(Run.timestamp)).first()
                    new_trade = Trade(
                        id=_next_trade_id(db),
                        hypothesis_id=pta.hypothesis_id,
                        run_id=latest_run.id if latest_run else None,
                        newsletter_id=pta.newsletter_id,
                        ticker=existing.ticker,
                        direction=existing.direction,
                        entry_date=existing.entry_date,
                        entry_price=existing.entry_price,
                        shares=pta.reduce_to_shares,
                        conviction_at_entry=pta.conviction,
                        status="OPEN",
                        hypothesis_short_name=existing.hypothesis_short_name,
                        hypothesis_theory=existing.hypothesis_theory,
                        hypothesis_status_at_entry=existing.hypothesis_status_at_entry,
                    )
                    db.add(new_trade)
                    results.append({"id": pta_id, "status": "EXECUTED", "closed_trade_id": existing.id, "new_trade_id": new_trade.id})
                else:
                    results.append({"id": pta_id, "status": "REJECTED", "reason": "no shares to reduce"})
            else:
                results.append({"id": pta_id, "status": "REJECTED", "reason": "trade not found"})

        pta.status = "EXECUTED"
        pta.executed_at = now
        pta.executed_price = live_price

    db.commit()
    return {"results": results}


@router.get("/prices")
def get_prices(tickers: str = Query(...)):
    """Fetch current prices for given tickers. Stores nothing.
    Usage: GET /api/prices?tickers=GLD,SPY,RSP
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="No tickers provided")

    prices = {}
    for tick in ticker_list:
        price = _fetch_current_price(tick)
        if price is not None:
            prices[tick] = price

    return prices
