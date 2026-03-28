# trades.py -- Trade tracker CRUD + price refresh + performance aggregation.
# Depends on: db/database.py, db/models.py
# Depended on by: main.py (router registration)
from __future__ import annotations

import json
import subprocess
from datetime import date, datetime

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import Run, Trade

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


def _next_trade_id(db: Session) -> str:
    """Generate T-YYYY-NNN sequential ID."""
    year = date.today().year
    prefix = f"T-{year}-"
    existing = (
        db.query(Trade)
        .filter(Trade.id.like(f"{prefix}%"))
        .order_by(desc(Trade.id))
        .first()
    )
    if existing:
        seq = int(existing.id.split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:03d}"


def _trade_to_dict(t: Trade) -> dict:
    """Convert Trade model to frontend-friendly dict."""
    direction_sign = 1 if t.direction == "LONG" else -1
    days = None
    if t.entry_date:
        try:
            entry_dt = datetime.fromisoformat(t.entry_date).date()
            days = (date.today() - entry_dt).days
        except (ValueError, TypeError):
            pass

    return {
        "id": t.id,
        "hypothesis_id": t.hypothesis_id,
        "run_id": t.run_id,
        "ticker": t.ticker,
        "direction": t.direction,
        "entry_date": t.entry_date,
        "entry_price": t.entry_price,
        "shares": t.shares,
        "notional": t.notional,
        "conviction_at_entry": t.conviction_at_entry,
        "current_price": t.current_price,
        "unrealized_pnl": t.unrealized_pnl,
        "unrealized_pct": t.unrealized_pct,
        "days_held": days if t.status == "OPEN" else t.days_held,
        "exit_date": t.exit_date,
        "exit_price": t.exit_price,
        "realized_pnl": t.realized_pnl,
        "realized_pct": t.realized_pct,
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
    notional = float(entry_price) * float(shares)

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
        notional=notional,
        conviction_at_entry=h.conviction,
        current_price=float(entry_price),  # starts at entry
        unrealized_pnl=0.0,
        unrealized_pct=0.0,
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
def update_trade(trade_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")

    # Close trade
    if "exit_price" in payload:
        exit_price = float(payload["exit_price"])
        direction_sign = 1 if trade.direction == "LONG" else -1
        realized_pnl = (exit_price - trade.entry_price) * trade.shares * direction_sign
        realized_pct = ((exit_price - trade.entry_price) / trade.entry_price) * direction_sign * 100

        trade.exit_price = exit_price
        trade.exit_date = payload.get("exit_date", date.today().isoformat())
        trade.exit_reason = payload.get("exit_reason", "manual")
        trade.realized_pnl = round(realized_pnl, 2)
        trade.realized_pct = round(realized_pct, 2)
        trade.status = "CLOSED"
        trade.current_price = exit_price
        trade.unrealized_pnl = 0.0
        trade.unrealized_pct = 0.0

        # Compute final days held
        try:
            entry_dt = datetime.fromisoformat(trade.entry_date).date()
            exit_dt = datetime.fromisoformat(trade.exit_date).date()
            trade.days_held = (exit_dt - entry_dt).days
        except (ValueError, TypeError):
            pass

    # Update current price manually
    if "current_price" in payload and "exit_price" not in payload:
        current = float(payload["current_price"])
        direction_sign = 1 if trade.direction == "LONG" else -1
        trade.current_price = current
        trade.unrealized_pnl = round(
            (current - trade.entry_price) * trade.shares * direction_sign, 2
        )
        trade.unrealized_pct = round(
            ((current - trade.entry_price) / trade.entry_price) * direction_sign * 100, 2
        )

    db.commit()
    db.refresh(trade)
    return _trade_to_dict(trade)


@router.get("/trades/refresh")
def refresh_trade_prices(db: Session = Depends(get_db)):
    """Fetch current prices for all open trades via Yahoo Finance."""
    open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
    if not open_trades:
        return {"updated": 0, "trades": []}

    tickers = list({t.ticker for t in open_trades})

    # Fetch prices via curl (same approach as data_agent.py — avoids TLS fingerprinting blocks)
    prices = {}
    for tick in tickers:
        price = _fetch_current_price(tick)
        if price is not None:
            prices[tick] = price

    if not prices:
        raise HTTPException(status_code=502, detail="No price data returned from Yahoo Finance")

    updated = 0
    for trade in open_trades:
        if trade.ticker in prices:
            current = prices[trade.ticker]
            direction_sign = 1 if trade.direction == "LONG" else -1
            trade.current_price = round(current, 2)
            trade.unrealized_pnl = round(
                (current - trade.entry_price) * trade.shares * direction_sign, 2
            )
            trade.unrealized_pct = round(
                ((current - trade.entry_price) / trade.entry_price) * direction_sign * 100, 2
            )
            updated += 1

    db.commit()

    refreshed = [_trade_to_dict(t) for t in open_trades]
    return {"updated": updated, "prices": prices, "trades": refreshed}


@router.get("/trades/performance")
def trade_performance(db: Session = Depends(get_db)):
    """Aggregate performance stats across all trades."""
    all_trades = db.query(Trade).all()
    open_trades = [t for t in all_trades if t.status == "OPEN"]
    closed_trades = [t for t in all_trades if t.status == "CLOSED"]

    # Open P&L
    open_pnl = sum(t.unrealized_pnl or 0 for t in open_trades)
    open_notional = sum(t.notional or 0 for t in open_trades)

    # Closed stats
    wins = [t for t in closed_trades if (t.realized_pnl or 0) > 0]
    losses = [t for t in closed_trades if (t.realized_pnl or 0) <= 0]
    win_rate = len(wins) / len(closed_trades) if closed_trades else None
    total_realized = sum(t.realized_pnl or 0 for t in closed_trades)

    # Avg return by conviction tier
    conviction_tiers = {}
    for t in closed_trades:
        conv = int(t.conviction_at_entry) if t.conviction_at_entry else 0
        if conv not in conviction_tiers:
            conviction_tiers[conv] = []
        conviction_tiers[conv].append(t.realized_pct or 0)

    avg_by_conviction = {
        k: round(sum(v) / len(v), 2) for k, v in conviction_tiers.items()
    }

    return {
        "open_count": len(open_trades),
        "closed_count": len(closed_trades),
        "open_pnl": round(open_pnl, 2),
        "open_notional": round(open_notional, 2),
        "total_realized": round(total_realized, 2),
        "win_rate": round(win_rate, 3) if win_rate is not None else None,
        "wins": len(wins),
        "losses": len(losses),
        "avg_return_by_conviction": avg_by_conviction,
    }
