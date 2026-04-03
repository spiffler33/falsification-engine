# test_walkforward_audit_columns.py -- Tests for Task 15: Pipeline Audit columns.
# Verifies that the walkforward endpoint returns thread_age, lifecycle_action,
# stale_count, escalated_count, and has_emergent_risk per row.
import json
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base
from backend.db.models import (
    Hypothesis as HypothesisModel,
    HypothesisThread,
    Run,
    RunPriceSnapshot,
)


# ---------------------------------------------------------------------------
# Test fixture: in-memory database
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """Create an in-memory SQLite database with all tables."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_run(db, run_id="R-20260403-120000"):
    run = Run(id=run_id, timestamp="2026-04-03T12:00:00", status="complete",
              price_snapshot_date="2026-04-03")
    db.add(run)
    db.flush()
    return run


def _seed_price_snapshot(db, run_id, ticker="SPY", price=500.0):
    snap = RunPriceSnapshot(
        run_id=run_id, ticker=ticker, price=price,
        date="2026-04-03", source="yahoo_finance",
    )
    db.add(snap)
    db.flush()


def _seed_thread(db, thread_id, *, hyp_id, run_id, created_date="2026-03-20",
                 source_theory="valuation_mean_reversion"):
    thread = HypothesisThread(
        thread_id=thread_id,
        status="ACTIVE",
        originating_instance_id=hyp_id,
        originating_run_id=run_id,
        source_theory=source_theory,
        created_date=created_date,
    )
    db.add(thread)
    db.flush()
    return thread


def _seed_hypothesis(db, hyp_id, *, run_id, thread_id=None,
                     lifecycle_action="NEW", short_name="Test hyp",
                     soft_falsifiers=None, emergent_risk_condition=None):
    """Create a hypothesis. If thread_id is given, it must already exist."""
    h = HypothesisModel(
        id=hyp_id,
        run_id=run_id,
        short_name=short_name,
        full_statement="Full statement.",
        source_theory="valuation_mean_reversion",
        status="SURVIVED",
        conviction=7.5,
        generated_date="2026-04-03",
        lifecycle_action=lifecycle_action,
        predicted_assets=json.dumps(["SPY"]),
        asset_direction=json.dumps({"SPY": "LONG"}),
        hard_falsifiers=json.dumps([]),
        soft_falsifiers=json.dumps(soft_falsifiers or []),
        emergent_risk_condition=emergent_risk_condition,
    )
    db.add(h)
    db.flush()
    # Link thread after flush to respect FK order
    if thread_id:
        h.thread_id = thread_id
        db.flush()
    return h


def _call_walkforward(db, run_id):
    """Call the walkforward endpoint function directly, mocking price fetches."""
    from backend.api.pipeline import get_run_walkforward

    with patch("backend.api.trades._fetch_current_price", return_value=505.0):
        return get_run_walkforward(run_id, db)


# ---------------------------------------------------------------------------
# Tests: v7 audit column fields in walkforward rows
# ---------------------------------------------------------------------------

class TestWalkforwardThreadAge:
    """Thread age = days since thread creation."""

    def test_thread_age_computed_correctly(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        h = _seed_hypothesis(db, "H-001", run_id=run.id)
        _seed_thread(db, "T-01", hyp_id="H-001", run_id=run.id,
                     created_date="2026-03-20")
        h.thread_id = "T-01"
        db.commit()

        result = _call_walkforward(db, run.id)
        row = result["rows"][0]
        expected_age = (date.today() - date(2026, 3, 20)).days
        assert row["thread_age"] == expected_age

    def test_thread_age_null_when_no_thread(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        _seed_hypothesis(db, "H-001", run_id=run.id, thread_id=None)
        db.commit()

        result = _call_walkforward(db, run.id)
        row = result["rows"][0]
        assert row["thread_age"] is None


class TestWalkforwardLifecycleAction:
    """lifecycle_action is passed through from the hypothesis row."""

    def test_action_confirm(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        _seed_hypothesis(db, "H-001", run_id=run.id, lifecycle_action="CONFIRM")
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["lifecycle_action"] == "CONFIRM"

    def test_action_update(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        _seed_hypothesis(db, "H-001", run_id=run.id, lifecycle_action="UPDATE")
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["lifecycle_action"] == "UPDATE"

    def test_action_null_for_legacy(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        _seed_hypothesis(db, "H-001", run_id=run.id, lifecycle_action=None)
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["lifecycle_action"] is None


class TestWalkforwardStaleCount:
    """stale_count = number of soft falsifiers with staleness_flag == 'STALE'."""

    def test_counts_stale_flags(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        soft_f = [
            {"name": "f1", "staleness_flag": "STALE", "status": "CLEAR"},
            {"name": "f2", "staleness_flag": "STALE", "status": "TRIGGERED"},
            {"name": "f3", "staleness_flag": None, "status": "CLEAR"},
        ]
        _seed_hypothesis(db, "H-001", run_id=run.id, soft_falsifiers=soft_f)
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["stale_count"] == 2

    def test_zero_when_no_stale(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        soft_f = [
            {"name": "f1", "status": "CLEAR"},
            {"name": "f2", "status": "TRIGGERED"},
        ]
        _seed_hypothesis(db, "H-001", run_id=run.id, soft_falsifiers=soft_f)
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["stale_count"] == 0

    def test_zero_when_no_falsifiers(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        _seed_hypothesis(db, "H-001", run_id=run.id, soft_falsifiers=[])
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["stale_count"] == 0


class TestWalkforwardEscalatedCount:
    """escalated_count = number of falsifiers with status == 'ESCALATED_UNTESTABLE'."""

    def test_counts_escalated(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        soft_f = [
            {"name": "f1", "status": "ESCALATED_UNTESTABLE", "untestable_consecutive": 3},
            {"name": "f2", "status": "UNTESTABLE", "untestable_consecutive": 1},
            {"name": "f3", "status": "ESCALATED_UNTESTABLE", "untestable_consecutive": 4},
        ]
        _seed_hypothesis(db, "H-001", run_id=run.id, soft_falsifiers=soft_f)
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["escalated_count"] == 2

    def test_zero_when_none_escalated(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        soft_f = [
            {"name": "f1", "status": "CLEAR"},
            {"name": "f2", "status": "UNTESTABLE", "untestable_consecutive": 2},
        ]
        _seed_hypothesis(db, "H-001", run_id=run.id, soft_falsifiers=soft_f)
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["escalated_count"] == 0


class TestWalkforwardEmergentRisk:
    """has_emergent_risk = bool(emergent_risk_condition)."""

    def test_true_when_present(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        _seed_hypothesis(db, "H-001", run_id=run.id,
                         emergent_risk_condition="Tariff escalation threatens supply chain")
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["has_emergent_risk"] is True

    def test_false_when_absent(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)
        _seed_hypothesis(db, "H-001", run_id=run.id, emergent_risk_condition=None)
        db.commit()

        result = _call_walkforward(db, run.id)
        assert result["rows"][0]["has_emergent_risk"] is False


class TestWalkforwardMultipleRows:
    """Multiple hypotheses in one run get correct per-row enrichment."""

    def test_mixed_rows(self, db):
        run = _seed_run(db)
        _seed_price_snapshot(db, run.id)

        # H-001: threaded, CONFIRM, 1 STALE, 1 ESCALATED, emergent risk
        h1 = _seed_hypothesis(db, "H-001", run_id=run.id,
                              lifecycle_action="CONFIRM",
                              soft_falsifiers=[
                                  {"name": "f1", "staleness_flag": "STALE", "status": "CLEAR"},
                                  {"name": "f2", "status": "ESCALATED_UNTESTABLE"},
                              ],
                              emergent_risk_condition="Supply chain disruption")
        _seed_thread(db, "T-01", hyp_id="H-001", run_id=run.id,
                     created_date="2026-03-01")
        h1.thread_id = "T-01"

        # H-002: no thread, NEW, clean health
        _seed_hypothesis(db, "H-002", run_id=run.id,
                         lifecycle_action="NEW", short_name="Clean hyp",
                         soft_falsifiers=[{"name": "f1", "status": "CLEAR"}])
        db.commit()

        result = _call_walkforward(db, run.id)
        rows = {r["hypothesis_id"]: r for r in result["rows"]}

        # H-001
        r1 = rows["H-001"]
        assert r1["lifecycle_action"] == "CONFIRM"
        assert r1["thread_age"] == (date.today() - date(2026, 3, 1)).days
        assert r1["stale_count"] == 1
        assert r1["escalated_count"] == 1
        assert r1["has_emergent_risk"] is True

        # H-002
        r2 = rows["H-002"]
        assert r2["lifecycle_action"] == "NEW"
        assert r2["thread_age"] is None
        assert r2["stale_count"] == 0
        assert r2["escalated_count"] == 0
        assert r2["has_emergent_risk"] is False
