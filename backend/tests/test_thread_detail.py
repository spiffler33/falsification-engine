# test_thread_detail.py -- Tests for GET /api/threads/{thread_id} endpoint.
# Verifies thread detail response shape, instance lineage, flag computation.
import json
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import HypothesisThread, Run
from backend.api.threads import _instance_to_detail, _instance_to_summary


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
    run = Run(id=run_id, timestamp="2026-04-03T12:00:00", status="complete")
    db.add(run)
    db.flush()
    return run


def _seed_hypothesis(db, id="H-20260403-001", *, run_id="R-20260403-120000",
                     thread_id=None, short_name="Test hypothesis",
                     status="SURVIVED", conviction=7.5, lifecycle_action="CONFIRM",
                     source_theory="valuation_mean_reversion",
                     soft_falsifiers=None, generated_date="2026-04-03", **kwargs):
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
        predicted_assets=json.dumps(["SPY", "GLD"]),
        asset_direction=json.dumps({"SPY": "LONG", "GLD": "SHORT"}),
        hard_falsifiers=json.dumps([{"condition": "VIX > 40", "status": "SURVIVED"}]),
        soft_falsifiers=json.dumps(soft_falsifiers or [
            {"name": "Credit spread narrows", "severity": "medium", "status": "CLEAR",
             "metric": "HY OAS 340bps", "threshold": "< 300bps"},
        ]),
        conviction_math=json.dumps({
            "stage1": {"support_strength": 0.70, "evidence_quality": 0.65,
                       "convergence": 0.50, "falsifier_clarity": 0.80, "raw": 0.66},
            "stage2": {"soft_falsifier_discount": -0.10, "overlap_adjustment": -0.05,
                       "adjusted": 5.61},
            "stage3": {"horizon_cap": None, "expression_cap": None,
                       "realization_cap": None, "final": 5.6},
        }),
        **kwargs,
    )
    db.add(h)
    db.flush()
    return h


def _make_thread_with_instances(db, thread_id="T-20260401-120000-01",
                                 num_instances=2):
    """Create a thread with multiple instances across runs."""
    # Run 1 (originating)
    _seed_run(db, "R-20260401-120000")
    hyp1 = _seed_hypothesis(
        db, id="H-20260401-001", run_id="R-20260401-120000",
        conviction=6.0, lifecycle_action="NEW",
        generated_date="2026-04-01",
    )

    thread = HypothesisThread(
        thread_id=thread_id,
        status="ACTIVE",
        originating_instance_id=hyp1.id,
        originating_run_id="R-20260401-120000",
        source_theory="valuation_mean_reversion",
        created_date="2026-04-01",
        confirmation_count=1 if num_instances > 1 else 0,
        total_instances=num_instances,
    )
    db.add(thread)
    db.flush()
    hyp1.thread_id = thread_id
    db.flush()

    if num_instances >= 2:
        # Run 2 (confirmation)
        _seed_run(db, "R-20260403-120000")
        hyp2 = _seed_hypothesis(
            db, id="H-20260403-001", run_id="R-20260403-120000",
            thread_id=thread_id,
            conviction=7.5, lifecycle_action="CONFIRM",
            generated_date="2026-04-03",
        )

    if num_instances >= 3:
        # Run 3 (update)
        _seed_run(db, "R-20260405-120000")
        hyp3 = _seed_hypothesis(
            db, id="H-20260405-001", run_id="R-20260405-120000",
            thread_id=thread_id,
            conviction=8.0, lifecycle_action="UPDATE",
            generated_date="2026-04-05",
        )

    db.commit()
    return thread


# ---------------------------------------------------------------------------
# Tests: _instance_to_detail
# ---------------------------------------------------------------------------

class TestInstanceToDetail:
    """Test the full instance detail helper."""

    def test_basic_shape(self, db):
        """Response includes all fields needed for the ThreadDetail overlay."""
        _seed_run(db)
        hyp = _seed_hypothesis(db)
        db.commit()

        result = _instance_to_detail(hyp, db)

        # Identity
        assert result["id"] == "H-20260403-001"
        assert result["short_name"] == "Test hypothesis"
        assert result["status"] == "SURVIVED"
        assert result["conviction"] == 7.5

        # Conviction math present
        assert result["conviction_math"] is not None
        assert "stage1" in result["conviction_math"]
        assert "stage2" in result["conviction_math"]
        assert "stage3" in result["conviction_math"]

        # Falsifiers present
        assert len(result["hard_falsifiers"]) == 1
        assert result["hard_falsifiers"][0]["condition"] == "VIX > 40"
        assert len(result["soft_falsifiers"]) == 1
        assert result["soft_falsifiers"][0]["name"] == "Credit spread narrows"

        # Assets
        assert result["predicted_assets"] == ["SPY", "GLD"]
        assert result["asset_direction"]["GLD"] == "SHORT"

    def test_emergent_risk_fields(self, db):
        """Emergent risk fields appear in instance detail."""
        _seed_run(db)
        hyp = _seed_hypothesis(db,
            emergent_risk_condition="China credit event",
            emergent_risk_severity="major",
            emergent_risk_causal_chain="Contagion to EM flows")
        db.commit()

        result = _instance_to_detail(hyp, db)
        assert result["emergent_risk_condition"] == "China credit event"
        assert result["emergent_risk_severity"] == "major"
        assert result["emergent_risk_causal_chain"] == "Contagion to EM flows"

    def test_lifecycle_fields(self, db):
        """Lifecycle action and reasoning appear in detail."""
        _seed_run(db)
        hyp = _seed_hypothesis(db,
            lifecycle_action="UPDATE",
            lifecycle_reasoning="Timeframe extended due to delayed Fed action")
        db.commit()

        result = _instance_to_detail(hyp, db)
        assert result["lifecycle_action"] == "UPDATE"
        assert result["lifecycle_reasoning"] == "Timeframe extended due to delayed Fed action"

    def test_realization_fields(self, db):
        """Realization primitives appear in detail."""
        _seed_run(db)
        hyp = _seed_hypothesis(db,
            predicted_magnitude_lower=0.05,
            predicted_magnitude_upper=0.15,
            expression_return=0.08,
            realization_vs_lower=1.6,
            realization_vs_upper=0.53,
            time_elapsed_pct=0.35,
            timeframe_end_date="2026-06-30")
        db.commit()

        result = _instance_to_detail(hyp, db)
        assert result["predicted_magnitude_lower"] == 0.05
        assert result["predicted_magnitude_upper"] == 0.15
        assert result["expression_return"] == 0.08
        assert result["realization_vs_lower"] == 1.6
        assert result["time_elapsed_pct"] == 0.35
        assert result["timeframe_end_date"] == "2026-06-30"


# ---------------------------------------------------------------------------
# Tests: _instance_to_summary
# ---------------------------------------------------------------------------

class TestInstanceToSummary:
    """Test the compact instance summary for the lineage panel."""

    def test_basic_shape(self, db):
        """Summary includes compact fields for lineage display."""
        _seed_run(db)
        hyp = _seed_hypothesis(db)
        db.commit()

        result = _instance_to_summary(hyp)

        assert result["id"] == "H-20260403-001"
        assert result["run_id"] == "R-20260403-120000"
        assert result["generated_date"] == "2026-04-03"
        assert result["lifecycle_action"] == "CONFIRM"
        assert result["status"] == "SURVIVED"
        assert result["conviction"] == 7.5

    def test_falsifier_summary_counts(self, db):
        """Summary counts triggered, stale, escalated, untestable correctly."""
        soft_f = [
            {"name": "F1", "severity": "minor", "status": "TRIGGERED"},
            {"name": "F2", "severity": "medium", "status": "CLEAR",
             "staleness_flag": "STALE"},
            {"name": "F3", "severity": "major", "status": "ESCALATED_UNTESTABLE"},
            {"name": "F4", "severity": "minor", "status": "UNTESTABLE"},
        ]
        _seed_run(db)
        hyp = _seed_hypothesis(db, soft_falsifiers=soft_f)
        db.commit()

        result = _instance_to_summary(hyp)

        assert result["falsifier_summary"]["triggered"] == 1
        assert result["falsifier_summary"]["total"] == 4
        assert result["falsifier_summary"]["stale"] == 1
        assert result["falsifier_summary"]["escalated"] == 1
        assert result["falsifier_summary"]["untestable"] == 1

    def test_emergent_risk_flag(self, db):
        """has_emergent_risk should be true when condition is set."""
        _seed_run(db)
        hyp = _seed_hypothesis(db,
            emergent_risk_condition="Systemic counterparty risk")
        db.commit()

        result = _instance_to_summary(hyp)
        assert result["has_emergent_risk"] is True

    def test_no_emergent_risk(self, db):
        """has_emergent_risk should be false when no condition."""
        _seed_run(db)
        hyp = _seed_hypothesis(db)
        db.commit()

        result = _instance_to_summary(hyp)
        assert result["has_emergent_risk"] is False


# ---------------------------------------------------------------------------
# Tests: get_thread_detail endpoint logic
# ---------------------------------------------------------------------------

class TestGetThreadDetail:
    """Test the full thread detail response."""

    def test_thread_with_multiple_instances(self, db):
        """Thread detail includes all instances in lineage."""
        thread = _make_thread_with_instances(db, num_instances=3)

        from backend.api.threads import _instance_to_detail, _instance_to_summary
        from sqlalchemy import desc

        instances = (
            db.query(HypothesisModel)
            .filter(HypothesisModel.thread_id == thread.thread_id)
            .order_by(desc(HypothesisModel.generated_date), desc(HypothesisModel.run_id))
            .all()
        )

        assert len(instances) == 3
        # Latest should be the most recent
        assert instances[0].id == "H-20260405-001"
        assert instances[0].lifecycle_action == "UPDATE"
        assert instances[1].id == "H-20260403-001"
        assert instances[2].id == "H-20260401-001"

        # Check summaries
        summaries = [_instance_to_summary(inst) for inst in instances]
        assert summaries[0]["lifecycle_action"] == "UPDATE"
        assert summaries[1]["lifecycle_action"] == "CONFIRM"
        assert summaries[2]["lifecycle_action"] == "NEW"

    def test_conviction_history_across_instances(self, db):
        """Conviction history should span all instances in chronological order."""
        thread = _make_thread_with_instances(db, num_instances=3)

        from sqlalchemy import desc
        instances = (
            db.query(HypothesisModel)
            .filter(HypothesisModel.thread_id == thread.thread_id)
            .order_by(desc(HypothesisModel.generated_date))
            .all()
        )

        conviction_history = [
            inst.conviction for inst in reversed(instances) if inst.conviction is not None
        ]

        # Oldest first: 6.0, 7.5, 8.0
        assert conviction_history == [6.0, 7.5, 8.0]

    def test_single_instance_thread(self, db):
        """Thread with only NEW instance should work correctly."""
        thread = _make_thread_with_instances(db, num_instances=1)

        from sqlalchemy import desc
        instances = (
            db.query(HypothesisModel)
            .filter(HypothesisModel.thread_id == thread.thread_id)
            .order_by(desc(HypothesisModel.generated_date))
            .all()
        )

        assert len(instances) == 1
        assert instances[0].lifecycle_action == "NEW"

    def test_thread_with_renewed_from(self, db):
        """Thread with renewed_from should include the link."""
        _seed_run(db, "R-20260401-120000")
        hyp = _seed_hypothesis(db, id="H-20260401-001", run_id="R-20260401-120000",
                               lifecycle_action="NEW", generated_date="2026-04-01")

        thread = HypothesisThread(
            thread_id="T-20260403-120000-01",
            status="ACTIVE",
            originating_instance_id=hyp.id,
            originating_run_id="R-20260401-120000",
            source_theory="valuation_mean_reversion",
            created_date="2026-04-03",
            renewed_from="T-20260320-120000-01",
        )
        db.add(thread)
        db.flush()
        hyp.thread_id = thread.thread_id
        db.commit()

        assert thread.renewed_from == "T-20260320-120000-01"

    def test_thread_age_computation(self, db):
        """Thread age should be days since created_date."""
        today = date.today()
        ten_days_ago = (today - timedelta(days=10)).isoformat()

        _seed_run(db, "R-20260401-120000")
        hyp = _seed_hypothesis(db, id="H-20260401-001", run_id="R-20260401-120000",
                               lifecycle_action="NEW", generated_date="2026-04-01")

        thread = HypothesisThread(
            thread_id="T-20260401-120000-01",
            status="ACTIVE",
            originating_instance_id=hyp.id,
            originating_run_id="R-20260401-120000",
            source_theory="valuation_mean_reversion",
            created_date=ten_days_ago,
        )
        db.add(thread)
        db.flush()
        hyp.thread_id = thread.thread_id
        db.commit()

        created = date.fromisoformat(thread.created_date)
        age_days = (date.today() - created).days
        assert age_days == 10


# ---------------------------------------------------------------------------
# Tests: Falsifier lifecycle status resolution
# ---------------------------------------------------------------------------

class TestFalsifierLifecycleResolution:
    """Test the status resolution logic that the frontend uses."""

    def test_clear_status(self):
        f = {"name": "F1", "severity": "minor", "status": "CLEAR"}
        assert _resolve_lifecycle_status(f) == "CLEAR"

    def test_triggered_status(self):
        f = {"name": "F1", "severity": "medium", "status": "TRIGGERED"}
        assert _resolve_lifecycle_status(f) == "TRIGGERED"

    def test_untestable_status(self):
        f = {"name": "F1", "severity": "minor", "status": "UNTESTABLE"}
        assert _resolve_lifecycle_status(f) == "UNTESTABLE"

    def test_stale_flag(self):
        f = {"name": "F1", "severity": "minor", "status": "CLEAR",
             "staleness_flag": "STALE"}
        assert _resolve_lifecycle_status(f) == "STALE"

    def test_escalated_untestable(self):
        f = {"name": "F1", "severity": "major", "status": "ESCALATED_UNTESTABLE"}
        assert _resolve_lifecycle_status(f) == "ESCALATED_UNTESTABLE"

    def test_triggered_by_passage(self):
        f = {"name": "F1", "severity": "medium", "status": "CLEAR",
             "staleness_flag": "TRIGGERED_BY_PASSAGE"}
        assert _resolve_lifecycle_status(f) == "TRIGGERED_BY_PASSAGE"

    def test_staleness_classification_field(self):
        """staleness_classification is an alternate field name for staleness_flag."""
        f = {"name": "F1", "severity": "minor", "status": "CLEAR",
             "staleness_classification": "STALE"}
        assert _resolve_lifecycle_status(f) == "STALE"

    def test_escalated_takes_priority(self):
        """ESCALATED_UNTESTABLE should take priority over STALE."""
        f = {"name": "F1", "severity": "major", "status": "ESCALATED_UNTESTABLE",
             "staleness_flag": "STALE"}
        assert _resolve_lifecycle_status(f) == "ESCALATED_UNTESTABLE"


def _resolve_lifecycle_status(f):
    """Mirror of the frontend resolveLifecycleStatus function for testing."""
    if f.get("status") == "ESCALATED_UNTESTABLE":
        return "ESCALATED_UNTESTABLE"
    if f.get("staleness_flag") == "TRIGGERED_BY_PASSAGE" or f.get("staleness_classification") == "TRIGGERED_BY_PASSAGE":
        return "TRIGGERED_BY_PASSAGE"
    if f.get("staleness_flag") == "STALE" or f.get("staleness_classification") == "STALE":
        return "STALE"
    if f.get("status") == "UNTESTABLE":
        return "UNTESTABLE"
    if f.get("status") == "TRIGGERED":
        return "TRIGGERED"
    return "CLEAR"
