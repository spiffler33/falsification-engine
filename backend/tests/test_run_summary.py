# test_run_summary.py -- Tests for Task 14: Pipeline Run summary data.
# Verifies that _model_to_dict exposes thread_id, lifecycle_action,
# lifecycle_reasoning, and that the run detail endpoint includes them.
import json

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base
from backend.db.models import Hypothesis as HypothesisModel
from backend.db.models import HypothesisThread, Run
from backend.api.hypotheses import _model_to_dict


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


def _seed_hypothesis(db, hyp_id, *, run_id, thread_id=None,
                     lifecycle_action="CONFIRM", lifecycle_reasoning="Stable thesis",
                     short_name="Test hypothesis", conviction=7.5, status="SURVIVED",
                     source_theory="valuation_mean_reversion"):
    h = HypothesisModel(
        id=hyp_id,
        run_id=run_id,
        thread_id=thread_id,
        short_name=short_name,
        full_statement="Full statement.",
        source_theory=source_theory,
        status=status,
        conviction=conviction,
        generated_date="2026-04-03",
        lifecycle_action=lifecycle_action,
        lifecycle_reasoning=lifecycle_reasoning,
        predicted_assets=json.dumps(["SPY"]),
        asset_direction=json.dumps({"SPY": "LONG"}),
        hard_falsifiers=json.dumps([]),
        soft_falsifiers=json.dumps([]),
    )
    db.add(h)
    db.flush()
    return h


def _make_linked(db, hyp_id, thread_id, *, run_id, **hyp_kwargs):
    """Create hypothesis -> thread -> link, respecting FK order."""
    source = hyp_kwargs.get("source_theory", "valuation_mean_reversion")
    h = _seed_hypothesis(db, hyp_id, run_id=run_id, **hyp_kwargs)
    thread = HypothesisThread(
        thread_id=thread_id,
        status="ACTIVE",
        originating_instance_id=hyp_id,
        originating_run_id=run_id,
        source_theory=source,
        created_date="2026-04-01",
    )
    db.add(thread)
    db.flush()
    h.thread_id = thread_id
    db.flush()
    return h, thread


# ---------------------------------------------------------------------------
# Tests: _model_to_dict includes v7 thread lifecycle fields
# ---------------------------------------------------------------------------

class TestModelToDictThreadFields:
    """_model_to_dict must expose thread_id, lifecycle_action, lifecycle_reasoning."""

    def test_includes_thread_id(self, db):
        run = _seed_run(db)
        h, _ = _make_linked(db, "H-001", "T-20260401-120000-01", run_id=run.id)

        result = _model_to_dict(h, db)
        assert result["thread_id"] == "T-20260401-120000-01"

    def test_includes_lifecycle_action(self, db):
        run = _seed_run(db)
        h, _ = _make_linked(db, "H-001", "T-20260401-120000-01",
                            run_id=run.id, lifecycle_action="UPDATE")

        result = _model_to_dict(h, db)
        assert result["lifecycle_action"] == "UPDATE"

    def test_includes_lifecycle_reasoning(self, db):
        run = _seed_run(db)
        h, _ = _make_linked(db, "H-001", "T-20260401-120000-01",
                            run_id=run.id,
                            lifecycle_reasoning="New data strengthens thesis")

        result = _model_to_dict(h, db)
        assert result["lifecycle_reasoning"] == "New data strengthens thesis"

    def test_null_thread_id_when_unlinked(self, db):
        """Hypotheses not yet linked to a thread return None."""
        run = _seed_run(db)
        h = _seed_hypothesis(db, "H-001", run_id=run.id, thread_id=None)

        result = _model_to_dict(h, db)
        assert result["thread_id"] is None

    def test_null_lifecycle_action_when_unset(self, db):
        """Hypotheses without lifecycle_action return None."""
        run = _seed_run(db)
        h = _seed_hypothesis(db, "H-001", run_id=run.id,
                             lifecycle_action=None, lifecycle_reasoning=None)

        result = _model_to_dict(h, db)
        assert result["lifecycle_action"] is None
        assert result["lifecycle_reasoning"] is None


class TestModelToDictAllActions:
    """Each lifecycle action type is correctly passed through."""

    @pytest.mark.parametrize("action", ["CONFIRM", "UPDATE", "RENEW", "RETIRE", "NEW"])
    def test_action_passthrough(self, db, action):
        run = _seed_run(db)
        h, _ = _make_linked(db, "H-001", "T-20260401-120000-01",
                            run_id=run.id, lifecycle_action=action)

        result = _model_to_dict(h, db)
        assert result["lifecycle_action"] == action


class TestRunDetailIncludesThreadFields:
    """The run detail endpoint shape includes thread lifecycle fields.

    Tests _model_to_dict output when called from the run detail context,
    verifying the complete shape the frontend RunSummary component expects.
    """

    def test_run_hypotheses_have_thread_fields(self, db):
        """All hypotheses in a run carry thread_id and lifecycle_action."""
        run = _seed_run(db)

        # Mix of actions: CONFIRM, UPDATE, NEW
        h1, _ = _make_linked(db, "H-001", "T-20260401-120000-01",
                             run_id=run.id, lifecycle_action="CONFIRM",
                             short_name="Breadth rotation")

        h2, _ = _make_linked(db, "H-002", "T-20260401-120000-02",
                             run_id=run.id, lifecycle_action="UPDATE",
                             short_name="Gold debasement hedge")

        h3 = _seed_hypothesis(db, "H-003", run_id=run.id,
                              thread_id=None, lifecycle_action="NEW",
                              short_name="Oil shock energy")

        # Simulate what the run detail endpoint does
        hyps = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run.id
        ).all()
        dicts = [_model_to_dict(h, db) for h in hyps]

        assert len(dicts) == 3

        # Verify all have the required fields
        for d in dicts:
            assert "thread_id" in d
            assert "lifecycle_action" in d
            assert "lifecycle_reasoning" in d

        # Verify specific values by id
        by_id = {d["id"]: d for d in dicts}
        assert by_id["H-001"]["lifecycle_action"] == "CONFIRM"
        assert by_id["H-001"]["thread_id"] == "T-20260401-120000-01"
        assert by_id["H-002"]["lifecycle_action"] == "UPDATE"
        assert by_id["H-003"]["lifecycle_action"] == "NEW"
        assert by_id["H-003"]["thread_id"] is None

    def test_action_count_derivable_from_run_data(self, db):
        """Frontend can derive action counts from the hypotheses array.

        This tests the contract: given hypotheses with lifecycle_action,
        grouping by action produces the expected counts.
        """
        run = _seed_run(db)

        actions = ["CONFIRM", "CONFIRM", "CONFIRM", "UPDATE", "NEW", "NEW"]
        for i, action in enumerate(actions):
            tid = f"T-20260401-120000-{i:02d}"
            hid = f"H-{i:03d}"
            _make_linked(db, hid, tid, run_id=run.id,
                         lifecycle_action=action,
                         short_name=f"Hypothesis {i}")

        hyps = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run.id
        ).all()
        dicts = [_model_to_dict(h, db) for h in hyps]

        # Derive counts like the frontend does
        counts = {}
        for d in dicts:
            a = d["lifecycle_action"] or "NEW"
            counts[a] = counts.get(a, 0) + 1

        assert counts == {"CONFIRM": 3, "UPDATE": 1, "NEW": 2}
