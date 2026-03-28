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
    """Convert Trade model to frontend-friendly dict — primitives only."""
    return {
        "id": t.id,
        "hypothesis_id": t.hypothesis_id,
        "run_id": t.run_id,
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
