# test_thread_api.py -- Tests for GET /api/threads endpoint.
# Verifies thread listing, filtering, response shape, and flag computation.
import json
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import HypothesisThread, Run
from backend.api.threads import _thread_to_dict


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
    """Create a minimal run record."""
    run = Run(id=run_id, timestamp="2026-04-03T12:00:00", status="complete")
    db.add(run)
    db.flush()
    return run


def _seed_hypothesis(db, id="H-20260403-001", *, run_id="R-20260403-120000",
                     thread_id=None, short_name="Test hypothesis",
                     status="SURVIVED", conviction=7.5, lifecycle_action="CONFIRM",
                     source_theory="valuation_mean_reversion",
                     soft_falsifiers=None, generated_date="2026-04-03", **kwargs):
    """Create a hypothesis record."""
    h = HypothesisModel(
        id=id,
        run_id=run_id,
        thread_id=thread_id,
        short_name=short_name,
        full_statement="Full statement for testing.",
        source_theory=source_theory,
        status=status,
        conviction=conviction,
        generated_date=generated_date,
        lifecycle_action=lifecycle_action,
        predicted_assets=json.dumps(["SPY"]),
        asset_direction=json.dumps({"SPY": "LONG"}),
        hard_falsifiers=json.dumps([]),
        soft_falsifiers=json.dumps(soft_falsifiers or []),
        **kwargs,
    )
    db.add(h)
    db.flush()
    return h


def _seed_thread(db, thread_id="T-20260401-120000-01", *, status="ACTIVE",
                 source_theory="valuation_mean_reversion", created_date=None,
                 originating_instance_id="H-20260401-001",
                 originating_run_id="R-20260401-120000",
                 confirmation_count=0, total_instances=1, **kwargs):
    """Create a thread record. Hypothesis and Run must already exist."""
    if created_date is None:
        created_date = "2026-04-01"
    thread = HypothesisThread(
        thread_id=thread_id,
        status=status,
        originating_instance_id=originating_instance_id,
        originating_run_id=originating_run_id,
        source_theory=source_theory,
        created_date=created_date,
        confirmation_count=confirmation_count,
        total_instances=total_instances,
        **kwargs,
    )
    db.add(thread)
    db.flush()
    return thread


def _make_thread_with_instance(db, thread_id="T-20260401-120000-01",
                               run_id="R-20260401-120000",
                               hyp_id="H-20260401-001",
                               status="ACTIVE", **thread_kwargs):
    """Helper: create run -> hypothesis -> thread in correct FK order.

    `status` sets the THREAD status (ACTIVE/RETIRED).
    Use `hyp_status` in thread_kwargs to set hypothesis status (SURVIVED/WOUNDED/KILLED).
    """
    # Check if run already exists
    existing_run = db.query(Run).filter(Run.id == run_id).first()
    if not existing_run:
        _seed_run(db, run_id)

    # Extract hypothesis-specific kwargs
    hyp_kwargs = {}
    for k in ("conviction", "lifecycle_action", "short_name",
              "source_theory", "soft_falsifiers", "generated_date"):
        if k in thread_kwargs:
            hyp_kwargs[k] = thread_kwargs.pop(k)
    # hyp_status overrides the hypothesis status field (default: SURVIVED)
    if "hyp_status" in thread_kwargs:
        hyp_kwargs["status"] = thread_kwargs.pop("hyp_status")

    hyp = _seed_hypothesis(db, id=hyp_id, run_id=run_id, **hyp_kwargs)

    # Now create thread referencing the hypothesis
    thread = _seed_thread(
        db, thread_id=thread_id,
        status=status,
        originating_instance_id=hyp_id,
        originating_run_id=run_id,
        source_theory=hyp.source_theory,
        **thread_kwargs,
    )

    # Link hypothesis to thread
    hyp.thread_id = thread_id
    db.flush()

    return thread, hyp


# ---------------------------------------------------------------------------
# Tests: _thread_to_dict
# ---------------------------------------------------------------------------

class TestThreadToDict:
    """Test the _thread_to_dict helper function."""

    def test_basic_shape(self, db):
        """Response includes all required fields for the Ledger."""
        thread, hyp = _make_thread_with_instance(db)
        db.commit()

        result = _thread_to_dict(thread, hyp, db)

        # Thread-level fields
        assert result["thread_id"] == "T-20260401-120000-01"
        assert result["thread_status"] == "ACTIVE"
        assert result["created_date"] == "2026-04-01"
        assert isinstance(result["thread_age_days"], int)
        assert result["confirmation_count"] == 0
        assert result["total_instances"] == 1

        # Latest instance fields
        assert result["id"] == hyp.id
        assert result["latest_instance_id"] == hyp.id
        assert result["short_name"] == "Test hypothesis"
        assert result["status"] == "SURVIVED"
        assert result["conviction"] == 7.5
        assert result["lifecycle_action"] == "CONFIRM"

        # Assets
        assert result["predicted_assets"] == ["SPY"]
        assert result["asset_direction"] == {"SPY": "LONG"}

        # Flags
        assert result["stale_count"] == 0
        assert result["escalated_count"] == 0
        assert result["has_emergent_risk"] is False

    def test_thread_age_computation(self, db):
        """Thread age should be days since created_date."""
        today = date.today()
        five_days_ago = (today - timedelta(days=5)).isoformat()

        thread, hyp = _make_thread_with_instance(
            db, created_date=five_days_ago)
        db.commit()

        result = _thread_to_dict(thread, hyp, db)
        assert result["thread_age_days"] == 5

    def test_stale_count(self, db):
        """Stale count should count falsifiers with staleness_flag=STALE."""
        soft_f = [
            {"name": "F1", "severity": "minor", "status": "CLEAR", "staleness_flag": "STALE"},
            {"name": "F2", "severity": "medium", "status": "TRIGGERED"},
            {"name": "F3", "severity": "minor", "status": "CLEAR", "staleness_flag": "STALE"},
        ]
        thread, hyp = _make_thread_with_instance(db, soft_falsifiers=soft_f)
        db.commit()

        result = _thread_to_dict(thread, hyp, db)
        assert result["stale_count"] == 2
        assert result["falsifier_health"]["triggered"] == 1
        assert result["falsifier_health"]["total"] == 3

    def test_escalated_count(self, db):
        """Escalated count should count ESCALATED_UNTESTABLE falsifiers."""
        soft_f = [
            {"name": "F1", "severity": "minor", "status": "ESCALATED_UNTESTABLE"},
            {"name": "F2", "severity": "medium", "status": "CLEAR"},
        ]
        thread, hyp = _make_thread_with_instance(db, soft_falsifiers=soft_f)
        db.commit()

        result = _thread_to_dict(thread, hyp, db)
        assert result["escalated_count"] == 1

    def test_emergent_risk_flag(self, db):
        """has_emergent_risk should be true when emergent_risk_condition is set."""
        thread, hyp = _make_thread_with_instance(db)
        # Set emergent risk directly on the hypothesis
        hyp.emergent_risk_condition = "Credit event in China"
        hyp.emergent_risk_severity = "major"
        db.flush()
        db.commit()

        result = _thread_to_dict(thread, hyp, db)
        assert result["has_emergent_risk"] is True
        assert result["emergent_risk_severity"] == "major"

    def test_conviction_prev_from_prior_instance(self, db):
        """conviction_prev should come from the prior instance in the thread."""
        # Run 1 + originating hypothesis
        thread, hyp1 = _make_thread_with_instance(
            db, run_id="R-20260401-120000",
            hyp_id="H-20260401-001",
            conviction=6.0, lifecycle_action="NEW",
            generated_date="2026-04-01",
            total_instances=2,
        )

        # Run 2 + second hypothesis in same thread
        _seed_run(db, "R-20260403-120000")
        hyp2 = _seed_hypothesis(
            db, id="H-20260403-001", run_id="R-20260403-120000",
            thread_id=thread.thread_id,
            conviction=7.5, lifecycle_action="CONFIRM",
            generated_date="2026-04-03",
        )
        db.commit()

        result = _thread_to_dict(thread, hyp2, db)
        assert result["conviction_prev"] == 6.0
        assert result["conviction"] == 7.5

    def test_retired_thread_status(self, db):
        """Retired threads should have thread_status=RETIRED."""
        thread, hyp = _make_thread_with_instance(
            db, status="RETIRED", lifecycle_action="RETIRE")
        db.commit()

        result = _thread_to_dict(thread, hyp, db)
        assert result["thread_status"] == "RETIRED"


# ---------------------------------------------------------------------------
# Tests: list_threads sort and filter logic
# ---------------------------------------------------------------------------

class TestListThreads:
    """Test thread listing behavior."""

    def test_empty_database(self, db):
        """Empty database returns empty thread list."""
        threads = db.query(HypothesisThread).all()
        assert len(threads) == 0

    def test_active_threads_sorted_by_conviction(self, db):
        """Active threads should be sorted by conviction descending."""
        t1, h1 = _make_thread_with_instance(
            db, thread_id="T-20260401-120000-01",
            hyp_id="H-001", conviction=6.0,
        )
        t2, h2 = _make_thread_with_instance(
            db, thread_id="T-20260401-120000-02",
            hyp_id="H-002", conviction=8.0,
        )
        db.commit()

        # Build results same way as endpoint
        from sqlalchemy import desc
        threads = db.query(HypothesisThread).all()
        results = []
        for thread in threads:
            latest = (
                db.query(HypothesisModel)
                .filter(HypothesisModel.thread_id == thread.thread_id)
                .order_by(desc(HypothesisModel.generated_date), desc(HypothesisModel.run_id))
                .first()
            )
            if latest:
                results.append(_thread_to_dict(thread, latest, db))

        results.sort(key=lambda t: (
            0 if t["thread_status"] == "ACTIVE" else 1,
            -(t["conviction"] or 0),
        ))

        assert len(results) == 2
        assert results[0]["conviction"] == 8.0
        assert results[1]["conviction"] == 6.0

    def test_retired_threads_after_active(self, db):
        """Retired threads should appear after active threads in sort."""
        t_active, _ = _make_thread_with_instance(
            db, thread_id="T-20260401-120000-01",
            hyp_id="H-001", conviction=5.0,
        )
        t_retired, _ = _make_thread_with_instance(
            db, thread_id="T-20260401-120000-02",
            hyp_id="H-002", conviction=9.0,
            status="RETIRED",
        )
        db.commit()

        from sqlalchemy import desc
        threads = db.query(HypothesisThread).all()
        results = []
        for thread in threads:
            latest = (
                db.query(HypothesisModel)
                .filter(HypothesisModel.thread_id == thread.thread_id)
                .order_by(desc(HypothesisModel.generated_date), desc(HypothesisModel.run_id))
                .first()
            )
            if latest:
                results.append(_thread_to_dict(thread, latest, db))

        results.sort(key=lambda t: (
            0 if t["thread_status"] == "ACTIVE" else 1,
            -(t["conviction"] or 0),
        ))

        assert len(results) == 2
        assert results[0]["thread_status"] == "ACTIVE"
        assert results[1]["thread_status"] == "RETIRED"

    def test_confirmation_count_display(self, db):
        """Thread with multiple confirmations shows correct count."""
        thread, hyp = _make_thread_with_instance(
            db, confirmation_count=3, total_instances=4)
        db.commit()

        result = _thread_to_dict(thread, hyp, db)
        assert result["confirmation_count"] == 3
        assert result["total_instances"] == 4

    def test_staleness_classification_counted(self, db):
        """Falsifiers with staleness_classification=STALE also count."""
        soft_f = [
            {"name": "F1", "severity": "minor", "status": "CLEAR",
             "staleness_classification": "STALE"},
        ]
        thread, hyp = _make_thread_with_instance(db, soft_falsifiers=soft_f)
        db.commit()

        result = _thread_to_dict(thread, hyp, db)
        assert result["stale_count"] == 1

    def test_freshness_label_from_conviction_math(self, db):
        """Freshness label should be extracted from conviction_math."""
        thread, hyp = _make_thread_with_instance(db)
        conv_math = {
            "stage1": {"raw": 7.0},
            "stage2": {"adjusted": 6.5},
            "stage3": {"final": 6.5, "freshness_label": "WORKING"},
        }
        hyp.conviction_math = json.dumps(conv_math)
        db.flush()
        db.commit()

        result = _thread_to_dict(thread, hyp, db)
        assert result["freshness_label"] == "WORKING"

    def test_thread_with_no_instances_skipped(self, db):
        """Thread with no linked instances should be skipped in listing."""
        # Create run + hypothesis but don't link to thread
        run = _seed_run(db, "R-20260401-120000")
        hyp = _seed_hypothesis(db, id="H-orphan", run_id=run.id)
        # Create thread pointing to that hypothesis but don't set thread_id on hyp
        thread = _seed_thread(
            db, originating_instance_id=hyp.id,
            originating_run_id=run.id,
        )
        db.commit()

        from sqlalchemy import desc
        threads = db.query(HypothesisThread).all()
        results = []
        for t in threads:
            latest = (
                db.query(HypothesisModel)
                .filter(HypothesisModel.thread_id == t.thread_id)
                .order_by(desc(HypothesisModel.generated_date))
                .first()
            )
            if latest:
                results.append(_thread_to_dict(t, latest, db))

        assert len(results) == 0
