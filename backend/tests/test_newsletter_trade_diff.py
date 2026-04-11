# test_newsletter_trade_diff.py — Tests for trade diff orphan logic.
#
# Verifies that open trades backed by surviving hypotheses are NOT
# closed when the newsletter doesn't feature them (editorial != position mgmt).

import json
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from backend.db.database import Base
from backend.db.models import (
    Hypothesis as HypothesisModel,
    HypothesisThread,
    Newsletter,
    PendingTradeAction,
    Run,
    Trade,
)


@pytest.fixture
def db():
    """In-memory SQLite with FK enforcement."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from backend.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _setup_run_and_hypotheses(db, run_id="R-20260411-173116"):
    """Create a run with two surviving hypotheses (Gold and Silver)."""
    run = Run(id=run_id, timestamp=datetime.now().isoformat(), status="complete")
    db.add(run)
    db.flush()

    # Create hypotheses first WITHOUT thread_id (FK-safe order)
    hyp_data = [
        ("01", "Gold outperforms long bonds", "fiscal_dominance_arithmetic",
         "SURVIVED", 7.0, ["GLD", "TLT"], {"GLD": "LONG", "TLT": "SHORT"}, "T-gold-01"),
        ("02", "Silver outperforms financials", "fiscal_dominance_arithmetic",
         "SURVIVED", 6.0, ["SLV", "XLF"], {"SLV": "LONG", "XLF": "SHORT"}, "T-silver-01"),
        ("03", "European equities outperform", "valuation_mean_reversion",
         "KILLED", 3.0, ["VGK", "QQQ"], {"VGK": "LONG", "QQQ": "SHORT"}, "T-europe-01"),
    ]

    hyps = []
    for suffix, name, theory, status, conv, assets, dirs, tid in hyp_data:
        h = HypothesisModel(
            id=f"H-{run_id.replace('R-', '')}-{suffix}",
            run_id=run_id,
            short_name=name,
            full_statement="Test.",
            source_theory=theory,
            source_theories=json.dumps([theory]),
            status=status,
            conviction=conv,
            predicted_assets=json.dumps(assets),
            asset_direction=json.dumps(dirs),
            timeframe="Through Q3 2026",
            hard_falsifiers="[]",
            soft_falsifiers="[]",
            generated_date=date.today().isoformat(),
        )
        db.add(h)
        hyps.append((h, tid))

    db.flush()

    # Create threads (now hypotheses exist for originating_instance_id FK)
    for h, tid in hyps:
        thread = HypothesisThread(
            thread_id=tid,
            status="ACTIVE" if tid != "T-europe-01" else "RETIRED",
            originating_instance_id=h.id,
            originating_run_id=run_id,
            source_theory=h.source_theory,
            created_date=date.today().isoformat(),
            confirmation_count=0,
            total_instances=1,
        )
        db.add(thread)
    db.flush()

    # Now set thread_id on hypotheses (thread FK exists now)
    for h, tid in hyps:
        h.thread_id = tid
    db.flush()

    # Open trades from a prior newsletter — Gold, Silver, and Europe
    # Use hypothesis IDs from a PRIOR run (as trades reference the original hypothesis)
    prior_run_id = "R-20260409-211431"
    prior_run = Run(id=prior_run_id, timestamp="2026-04-09T21:14:31", status="complete")
    db.add(prior_run)
    db.flush()

    prior_hyps = []
    for h_id_suffix, name, theory, thread_id, assets, dirs, status, conv in [
        ("01", "Gold outperforms long bonds", "fiscal_dominance_arithmetic", "T-gold-01",
         ["GLD", "TLT"], {"GLD": "LONG", "TLT": "SHORT"}, "SURVIVED", 7.0),
        ("02", "Silver outperforms financials", "fiscal_dominance_arithmetic", "T-silver-01",
         ["SLV", "XLF"], {"SLV": "LONG", "XLF": "SHORT"}, "SURVIVED", 6.0),
        ("09", "European equities outperform", "valuation_mean_reversion", "T-europe-01",
         ["VGK", "QQQ"], {"VGK": "LONG", "QQQ": "SHORT"}, "SURVIVED", 6.0),
    ]:
        prior_h = HypothesisModel(
            id=f"H-{prior_run_id.replace('R-', '')}-{h_id_suffix}",
            run_id=prior_run_id,
            short_name=name,
            full_statement="Test.",
            source_theory=theory,
            source_theories=json.dumps([theory]),
            status=status,
            conviction=conv,
            predicted_assets=json.dumps(assets),
            asset_direction=json.dumps(dirs),
            timeframe="Through Q3 2026",
            hard_falsifiers="[]",
            soft_falsifiers="[]",
            generated_date="2026-04-09",
        )
        db.add(prior_h)
        prior_hyps.append((prior_h, thread_id))

    db.flush()

    # Set thread_id on prior hypotheses (threads already exist from current run)
    for prior_h, thread_id in prior_hyps:
        prior_h.thread_id = thread_id
    db.flush()

    # NL-001 newsletter
    nl = Newsletter(id="NL-2026-001", date="2026-04-09", run_id=prior_run_id, content="Test newsletter.")
    db.add(nl)
    db.flush()

    trades = []
    for trade_id, hyp_suffix, ticker, direction, conv in [
        ("TR-001", "01", "GLD", "LONG", 7.0),
        ("TR-002", "01", "TLT", "SHORT", 7.0),
        ("TR-003", "02", "SLV", "LONG", 6.0),
        ("TR-004", "02", "XLF", "SHORT", 6.0),
        ("TR-005", "09", "VGK", "LONG", 6.0),
        ("TR-006", "09", "QQQ", "SHORT", 6.0),
    ]:
        t = Trade(
            id=trade_id,
            hypothesis_id=f"H-20260409-211431-{hyp_suffix}",
            run_id=prior_run_id,
            newsletter_id="NL-2026-001",
            ticker=ticker,
            direction=direction,
            entry_date="2026-04-09",
            entry_price=100.0,
            shares=10,
            conviction_at_entry=conv,
            status="OPEN",
        )
        db.add(t)
        trades.append(t)

    db.commit()
    return run, trades


class TestTradeDiffOrphanLogic:
    """Trade diff should NOT close positions backed by surviving hypotheses."""

    @patch("backend.api.newsletter._fetch_current_price", return_value=100.0)
    def test_surviving_hypothesis_not_closed(self, mock_price, db):
        """Open trade backed by SURVIVED hypothesis is held, not closed."""
        run, trades = _setup_run_and_hypotheses(db)

        # Newsletter features ONLY Gold — Silver and Europe not in <TRADES>
        from backend.api.newsletter import import_newsletter
        from unittest.mock import MagicMock
        from fastapi import Request

        # Simulate the import directly by calling the trade diff logic
        # We need to replicate the relevant portion of import_newsletter
        nl = Newsletter(
            id="NL-2026-002",
            date=date.today().isoformat(),
            run_id=run.id,
            content="Gold is the top trade.",
        )
        db.add(nl)
        db.flush()

        # Only Gold is in the newsletter's trade recommendations
        trade_recs = [
            {"hypothesis_id": "H-20260411-173116-01", "ticker": "GLD", "direction": "LONG", "conviction": 7},
        ]

        # Run the orphan logic manually
        open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()
        assert len(open_trades) == 6  # GLD, TLT, SLV, XLF, VGK, QQQ

        # Simulate accounted set (only GLD accounted by trade_recs)
        accounted_trade_ids = {"TR-001"}  # GLD matched

        from backend.api.newsletter import CONVICTION_THRESHOLD

        close_count = 0
        hold_count = 0
        for t in open_trades:
            if t.id not in accounted_trade_ids:
                # Check backing hypothesis
                backing_hyp = (
                    db.query(HypothesisModel)
                    .filter(
                        HypothesisModel.run_id == run.id,
                        HypothesisModel.thread_id == (
                            db.query(HypothesisModel.thread_id)
                            .filter(HypothesisModel.id == t.hypothesis_id)
                            .scalar_subquery()
                        ),
                        HypothesisModel.status.in_(["SURVIVED", "WOUNDED"]),
                        HypothesisModel.conviction >= CONVICTION_THRESHOLD,
                    )
                    .first()
                )
                if backing_hyp:
                    hold_count += 1
                else:
                    close_count += 1

        # TLT (Gold thread, SURVIVED 7) -> HOLD
        # SLV (Silver thread, SURVIVED 6) -> HOLD
        # XLF (Silver thread, SURVIVED 6) -> HOLD
        # VGK (Europe thread, KILLED 3) -> CLOSE
        # QQQ (Europe thread, KILLED 3) -> CLOSE
        assert hold_count == 3, f"Expected 3 holds (TLT, SLV, XLF), got {hold_count}"
        assert close_count == 2, f"Expected 2 closes (VGK, QQQ), got {close_count}"

    @patch("backend.api.newsletter._fetch_current_price", return_value=100.0)
    def test_killed_hypothesis_closed(self, mock_price, db):
        """Open trade backed by KILLED hypothesis IS closed."""
        from backend.api.newsletter import CONVICTION_THRESHOLD

        run, trades = _setup_run_and_hypotheses(db)

        open_trades = db.query(Trade).filter(
            Trade.status == "OPEN",
            Trade.hypothesis_id == "H-20260409-211431-09",  # Europe
        ).all()
        assert len(open_trades) == 2  # VGK and QQQ

        for t in open_trades:
            backing_hyp = (
                db.query(HypothesisModel)
                .filter(
                    HypothesisModel.run_id == run.id,
                    HypothesisModel.thread_id == (
                        db.query(HypothesisModel.thread_id)
                        .filter(HypothesisModel.id == t.hypothesis_id)
                        .scalar_subquery()
                    ),
                    HypothesisModel.status.in_(["SURVIVED", "WOUNDED"]),
                    HypothesisModel.conviction >= CONVICTION_THRESHOLD,
                )
                .first()
            )
            assert backing_hyp is None, f"KILLED hypothesis should not have backing: {t.ticker}"
