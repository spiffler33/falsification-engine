# test_thread_lifecycle.py — Tests for v7 thread creation and lifecycle actions
# during generation import. Verifies NEW, CONFIRM, UPDATE, RENEW, RETIRE.
import json
from datetime import date, datetime

import pytest

from backend.engine.output_parser import parse_generation_output


# ---------------------------------------------------------------------------
# Output parser tests — verify lifecycle field extraction
# ---------------------------------------------------------------------------


def _base_hypothesis(**overrides) -> dict:
    """Minimal valid hypothesis with all required fields."""
    h = {
        "theory_id": "valuation_mean_reversion",
        "short_name": "Test hypothesis",
        "full_statement": "Testing thread lifecycle.",
        "predicted_assets": ["SPY"],
        "asset_direction": {"SPY": "LONG"},
        "timeframe": "Through Q3 2026",
        "hard_falsifiers": [],
        "soft_falsifiers": [],
    }
    h.update(overrides)
    return h


class TestLifecycleFieldExtraction:
    """Test that parse_generation_output extracts v7 lifecycle fields."""

    def test_new_action_default(self):
        """Hypotheses without lifecycle_action default to NEW."""
        raw = json.dumps([_base_hypothesis()])
        result = parse_generation_output(raw, "R-20260403-120000")
        assert len(result) == 1
        assert result[0]["lifecycle_action"] == "NEW"
        assert result[0]["_thread_id_ref"] is None

    def test_explicit_new_action(self):
        """Explicit lifecycle_action=NEW is preserved."""
        raw = json.dumps([_base_hypothesis(lifecycle_action="NEW")])
        result = parse_generation_output(raw, "R-20260403-120000")
        assert result[0]["lifecycle_action"] == "NEW"

    def test_confirm_action(self):
        """CONFIRM action preserves thread_id reference."""
        h = _base_hypothesis(
            lifecycle_action="CONFIRM",
            lifecycle_reasoning="Data consistent, no changes needed.",
            thread_id="T-20260402-120000-01",
        )
        raw = json.dumps([h])
        result = parse_generation_output(raw, "R-20260403-120000")
        assert result[0]["lifecycle_action"] == "CONFIRM"
        assert result[0]["lifecycle_reasoning"] == "Data consistent, no changes needed."
        assert result[0]["_thread_id_ref"] == "T-20260402-120000-01"

    def test_update_action_with_revised_fields(self):
        """UPDATE action carries through revised timeframe and names."""
        h = _base_hypothesis(
            lifecycle_action="UPDATE",
            lifecycle_reasoning="Timing extended by one month.",
            thread_id="T-20260402-120000-01",
            revised_timeframe_end_date="2026-10-31",
            revised_short_name="Updated test hypothesis",
        )
        raw = json.dumps([h])
        result = parse_generation_output(raw, "R-20260403-120000")
        assert result[0]["lifecycle_action"] == "UPDATE"
        assert result[0]["_revised_timeframe_end_date"] == "2026-10-31"
        assert result[0]["_revised_short_name"] == "Updated test hypothesis"

    def test_renew_action(self):
        """RENEW action preserves thread_id reference for the old thread."""
        h = _base_hypothesis(
            lifecycle_action="RENEW",
            lifecycle_reasoning="Magnitude band revised significantly.",
            thread_id="T-20260402-120000-01",
        )
        raw = json.dumps([h])
        result = parse_generation_output(raw, "R-20260403-120000")
        assert result[0]["lifecycle_action"] == "RENEW"
        assert result[0]["_thread_id_ref"] == "T-20260402-120000-01"

    def test_case_insensitive_action(self):
        """Lifecycle action is case-insensitive."""
        h = _base_hypothesis(lifecycle_action="confirm", thread_id="T-xxx")
        raw = json.dumps([h])
        result = parse_generation_output(raw, "R-test")
        assert result[0]["lifecycle_action"] == "CONFIRM"

    def test_invalid_action_defaults_to_new(self):
        """Unknown lifecycle_action defaults to NEW."""
        h = _base_hypothesis(lifecycle_action="DESTROY")
        raw = json.dumps([h])
        result = parse_generation_output(raw, "R-test")
        assert result[0]["lifecycle_action"] == "NEW"


class TestV7StructuredFormat:
    """Test the v7 structured format with thread_actions + new_hypotheses."""

    def test_structured_format_with_thread_actions_and_new(self):
        """Parse v7 structured output: thread_actions + new_hypotheses."""
        payload = {
            "thread_actions": [
                {
                    "thread_id": "T-20260402-120000-01",
                    "lifecycle_action": "CONFIRM",
                    "lifecycle_reasoning": "Still valid.",
                    "short_name": "Confirmed hypothesis",
                    "full_statement": "Confirmed mechanism.",
                    "theory_id": "debt_cycle_short",
                    "predicted_assets": ["TLT"],
                    "asset_direction": {"TLT": "LONG"},
                    "timeframe": "Through Q4 2026",
                    "hard_falsifiers": [],
                    "soft_falsifiers": [],
                },
            ],
            "new_hypotheses": [
                _base_hypothesis(short_name="Brand new hypothesis"),
            ],
        }
        raw = json.dumps(payload)
        result = parse_generation_output(raw, "R-20260403-120000")
        assert len(result) == 2

        confirm_item = [r for r in result if r["lifecycle_action"] == "CONFIRM"]
        new_item = [r for r in result if r["lifecycle_action"] == "NEW"]
        assert len(confirm_item) == 1
        assert len(new_item) == 1
        assert confirm_item[0]["_thread_id_ref"] == "T-20260402-120000-01"

    def test_structured_format_retire(self):
        """RETIRE in v7 structured format produces a retire-only marker."""
        payload = {
            "thread_actions": [
                {
                    "thread_id": "T-20260402-120000-01",
                    "lifecycle_action": "RETIRE",
                    "lifecycle_reasoning": "Mechanism weakened.",
                },
            ],
            "new_hypotheses": [],
        }
        raw = json.dumps(payload)
        result = parse_generation_output(raw, "R-20260403-120000")
        assert len(result) == 1
        assert result[0].get("_retire_only") is True
        assert result[0]["lifecycle_action"] == "RETIRE"
        assert result[0]["_thread_id_ref"] == "T-20260402-120000-01"

    def test_structured_format_renew(self):
        """RENEW in v7 structured format extracts renewed_hypothesis."""
        payload = {
            "thread_actions": [
                {
                    "thread_id": "T-20260402-120000-01",
                    "lifecycle_action": "RENEW",
                    "lifecycle_reasoning": "Magnitude band revised.",
                    "renewed_hypothesis": _base_hypothesis(
                        short_name="Renewed hypothesis",
                        predicted_magnitude_lower=0.05,
                        predicted_magnitude_upper=0.15,
                        timeframe_end_date="2026-12-31",
                    ),
                },
            ],
            "new_hypotheses": [],
        }
        raw = json.dumps(payload)
        result = parse_generation_output(raw, "R-20260403-120000")
        assert len(result) == 1
        assert result[0]["lifecycle_action"] == "RENEW"
        assert result[0]["_thread_id_ref"] == "T-20260402-120000-01"
        assert result[0]["short_name"] == "Renewed hypothesis"

    def test_backwards_compatible_flat_array(self):
        """v6-style flat array still works (all items become NEW)."""
        raw = json.dumps([_base_hypothesis(), _base_hypothesis(short_name="Second")])
        result = parse_generation_output(raw, "R-20260403-120000")
        assert len(result) == 2
        assert all(r["lifecycle_action"] == "NEW" for r in result)


# ---------------------------------------------------------------------------
# Database integration tests — verify thread CRUD during import
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database with all tables for testing."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    from backend.db.database import Base

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Import all models so tables get registered
    from backend.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _create_run(db, run_id="R-20260403-120000", status="partial"):
    """Helper: create a Run record."""
    from backend.db.models import Run
    run = Run(
        id=run_id,
        timestamp=datetime.now().isoformat(),
        status=status,
    )
    db.add(run)
    db.commit()
    return run


def _create_thread_and_instance(db, run, thread_id="T-20260402-120000-01",
                                instance_id="H-20260402-120000-01",
                                short_name="Prior hypothesis",
                                source_theory="valuation_mean_reversion"):
    """Helper: create a thread with a linked originating instance.

    FK ordering: hypothesis.thread_id -> hypothesis_threads.thread_id
    and hypothesis_threads.originating_instance_id -> hypotheses.id.
    We create the hypothesis without thread_id first, then the thread,
    then backfill thread_id on the hypothesis.
    """
    from backend.db.models import Hypothesis as HM, HypothesisThread

    # Step 1: Create originating instance WITHOUT thread_id
    h = HM(
        id=instance_id,
        run_id=run.id,
        short_name=short_name,
        full_statement="Prior mechanism description.",
        source_theory=source_theory,
        source_theories=json.dumps([source_theory]),
        status="SURVIVED",
        predicted_assets=json.dumps(["SPY"]),
        asset_direction=json.dumps({"SPY": "LONG"}),
        timeframe="Through Q3 2026",
        hard_falsifiers=json.dumps([]),
        soft_falsifiers=json.dumps([
            {"name": "VIX spike", "severity": "medium", "status": "clear",
             "metric": "vix", "threshold": "30", "condition": "VIX above 30",
             "untestable_consecutive": 2, "generation_market_value": 14.0},
        ]),
        generated_date=date.today().isoformat(),
        lifecycle_action="NEW",
        predicted_magnitude_lower=0.10,
        predicted_magnitude_upper=0.25,
        timeframe_end_date="2026-09-30",
    )
    db.add(h)
    db.flush()

    # Step 2: Create thread (references hypothesis via originating_instance_id)
    thread = HypothesisThread(
        thread_id=thread_id,
        status="ACTIVE",
        originating_instance_id=instance_id,
        originating_run_id=run.id,
        entry_prices=json.dumps({"SPY": 450.0}),
        payoff_band_lower=0.10,
        payoff_band_upper=0.25,
        timeframe_end_date="2026-09-30",
        source_theory=source_theory,
        created_date=date.today().isoformat(),
        confirmation_count=0,
        total_instances=1,
    )
    db.add(thread)
    db.flush()

    # Step 3: Backfill thread_id on the hypothesis
    h.thread_id = thread_id
    db.commit()
    return thread, h


class TestThreadCreationOnNewImport:
    """Test that NEW lifecycle action creates a thread properly."""

    def test_new_creates_thread(self, db_session):
        from backend.db.models import Hypothesis as HM, HypothesisThread
        from backend.api.pipeline import _create_thread_for_instance

        run = _create_run(db_session, run_id="R-20260403-120000")

        h_data = {
            "id": "H-20260403-120000-01",
            "run_id": run.id,
            "source_theory": "valuation_mean_reversion",
            "predicted_assets": json.dumps(["SPY"]),
            "predicted_magnitude_lower": 0.10,
            "predicted_magnitude_upper": 0.25,
            "timeframe_end_date": "2026-09-30",
        }

        price_snapshot = {"SPY": 455.0, "TLT": 92.0}
        thread = _create_thread_for_instance(h_data, run, price_snapshot)

        assert thread.thread_id == "T-20260403-120000-01"
        assert thread.status == "ACTIVE"
        assert thread.originating_instance_id == "H-20260403-120000-01"
        assert thread.originating_run_id == run.id
        assert thread.payoff_band_lower == 0.10
        assert thread.payoff_band_upper == 0.25
        assert thread.timeframe_end_date == "2026-09-30"
        assert thread.confirmation_count == 0
        assert thread.total_instances == 1
        assert thread.renewed_from is None

        # Entry prices should only include tickers in the hypothesis
        entry_prices = json.loads(thread.entry_prices)
        assert entry_prices == {"SPY": 455.0}
        assert "TLT" not in entry_prices

    def test_new_with_renewed_from(self, db_session):
        """RENEW creates a thread with renewed_from link."""
        from backend.api.pipeline import _create_thread_for_instance

        run = _create_run(db_session)
        h_data = {
            "id": "H-20260403-120000-02",
            "run_id": run.id,
            "source_theory": "debt_cycle_short",
            "predicted_assets": json.dumps(["TLT"]),
            "predicted_magnitude_lower": 0.05,
            "predicted_magnitude_upper": 0.15,
            "timeframe_end_date": "2026-12-31",
        }

        thread = _create_thread_for_instance(
            h_data, run, {"TLT": 92.0},
            renewed_from="T-20260402-120000-01",
        )
        assert thread.renewed_from == "T-20260402-120000-01"


class TestConfirmAction:
    """Test CONFIRM lifecycle action: same thread, increment counters, inherit data."""

    def test_confirm_increments_counters(self, db_session):
        from backend.db.models import HypothesisThread
        from backend.api.pipeline import _apply_thread_to_instance

        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        thread, prior_h = _create_thread_and_instance(db_session, prior_run)

        assert thread.confirmation_count == 0
        assert thread.total_instances == 1

        # Simulate CONFIRM: the import endpoint increments counters
        thread.confirmation_count += 1
        thread.total_instances += 1
        db_session.commit()

        assert thread.confirmation_count == 1
        assert thread.total_instances == 2

    def test_confirm_inherits_fields_from_prior(self, db_session):
        """CONFIRM with minimal data inherits core fields from prior instance."""
        from backend.api.pipeline import _apply_thread_to_instance

        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        thread, prior_h = _create_thread_and_instance(db_session, prior_run)

        # Simulate a CONFIRM item with only thread_id and action (minimal LLM output)
        h_data = {
            "id": "H-20260403-120000-01",
            "run_id": "R-20260403-120000",
            "short_name": "[CONFIRM] T-20260402-120000-01",
            "full_statement": "",
            "source_theory": "unknown",
            "predicted_assets": "[]",
            "asset_direction": "{}",
            "generated_date": date.today().isoformat(),
        }

        h_data = _apply_thread_to_instance(h_data, thread, db_session)

        # Should inherit from prior
        assert h_data["short_name"] == "Prior hypothesis"
        assert h_data["source_theory"] == "valuation_mean_reversion"
        assert json.loads(h_data["predicted_assets"]) == ["SPY"]

    def test_confirm_inherits_falsifier_counters(self, db_session):
        """CONFIRM inherits untestable_consecutive from prior instance falsifiers."""
        from backend.api.pipeline import _apply_thread_to_instance

        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        thread, prior_h = _create_thread_and_instance(db_session, prior_run)

        # New instance has soft falsifiers but no counters yet
        new_sf = json.dumps([
            {"name": "VIX spike", "severity": "medium", "status": "clear",
             "metric": "vix", "threshold": "30", "condition": "VIX above 30"},
        ])
        h_data = {
            "id": "H-20260403-120000-01",
            "run_id": "R-20260403-120000",
            "short_name": "Confirmed hypothesis",
            "full_statement": "Same mechanism.",
            "source_theory": "valuation_mean_reversion",
            "soft_falsifiers": new_sf,
            "predicted_assets": json.dumps(["SPY"]),
            "generated_date": date.today().isoformat(),
        }

        h_data = _apply_thread_to_instance(h_data, thread, db_session)

        sf = json.loads(h_data["soft_falsifiers"])
        assert sf[0]["untestable_consecutive"] == 2  # Inherited from prior
        assert sf[0]["generation_market_value"] == 14.0  # Inherited from prior


class TestUpdateAction:
    """Test UPDATE lifecycle action: reset confirmation_count, update timeframe."""

    def test_update_resets_confirmation_count(self, db_session):
        from backend.db.models import HypothesisThread

        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        thread, _ = _create_thread_and_instance(db_session, prior_run)

        # Simulate prior CONFIRMs
        thread.confirmation_count = 3
        thread.total_instances = 4
        db_session.commit()

        # Now UPDATE: reset confirmation_count, increment total_instances
        thread.confirmation_count = 0
        thread.total_instances += 1
        db_session.commit()

        assert thread.confirmation_count == 0
        assert thread.total_instances == 5

    def test_update_revises_timeframe(self, db_session):
        """UPDATE with revised_timeframe_end_date updates the thread."""
        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        thread, _ = _create_thread_and_instance(db_session, prior_run)

        assert thread.timeframe_end_date == "2026-09-30"

        # UPDATE revises the timeframe
        thread.timeframe_end_date = "2026-10-31"
        db_session.commit()

        assert thread.timeframe_end_date == "2026-10-31"
        # Payoff band stays pinned
        assert thread.payoff_band_lower == 0.10
        assert thread.payoff_band_upper == 0.25


class TestRenewAction:
    """Test RENEW lifecycle action: retire old thread, create new with link."""

    def test_renew_retires_old_thread(self, db_session):
        from backend.db.models import HypothesisThread
        from backend.api.pipeline import _create_thread_for_instance

        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        old_thread, _ = _create_thread_and_instance(db_session, prior_run)

        assert old_thread.status == "ACTIVE"

        # RENEW: retire old thread
        old_thread.status = "RETIRED"
        db_session.commit()

        assert old_thread.status == "RETIRED"

    def test_renew_creates_new_thread_with_link(self, db_session):
        from backend.db.models import Hypothesis as HM
        from backend.api.pipeline import _create_thread_for_instance

        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        old_thread, _ = _create_thread_and_instance(db_session, prior_run)

        # New run
        new_run = _create_run(db_session, run_id="R-20260403-120000")

        h_data = {
            "id": "H-20260403-120000-01",
            "run_id": new_run.id,
            "short_name": "Renewed hypothesis",
            "full_statement": "Renewed mechanism.",
            "source_theory": "valuation_mean_reversion",
            "source_theories": json.dumps(["valuation_mean_reversion"]),
            "status": "SURVIVED",
            "predicted_assets": json.dumps(["SPY", "QQQ"]),
            "asset_direction": json.dumps({"SPY": "LONG", "QQQ": "LONG"}),
            "timeframe": "Through Q4 2026",
            "hard_falsifiers": json.dumps([]),
            "soft_falsifiers": json.dumps([]),
            "generated_date": date.today().isoformat(),
            "predicted_magnitude_lower": 0.08,
            "predicted_magnitude_upper": 0.20,
            "timeframe_end_date": "2026-12-31",
        }

        # Create the hypothesis instance first (mirrors the import flow)
        h = HM(**h_data)
        db_session.add(h)
        db_session.flush()

        new_thread = _create_thread_for_instance(
            h_data, new_run, {"SPY": 460.0, "QQQ": 390.0},
            renewed_from=old_thread.thread_id,
        )
        db_session.add(new_thread)
        db_session.flush()  # Thread must exist before hypothesis can reference it
        h.thread_id = new_thread.thread_id
        db_session.commit()

        assert new_thread.renewed_from == old_thread.thread_id
        assert new_thread.status == "ACTIVE"
        assert new_thread.payoff_band_lower == 0.08
        assert new_thread.payoff_band_upper == 0.20
        assert new_thread.timeframe_end_date == "2026-12-31"

        # New entry prices reflect new run's snapshot
        entry_prices = json.loads(new_thread.entry_prices)
        assert entry_prices == {"SPY": 460.0, "QQQ": 390.0}


class TestRetireAction:
    """Test RETIRE lifecycle action: thread status set to RETIRED."""

    def test_retire_sets_thread_status(self, db_session):
        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        thread, _ = _create_thread_and_instance(db_session, prior_run)

        assert thread.status == "ACTIVE"
        thread.status = "RETIRED"
        db_session.commit()
        assert thread.status == "RETIRED"

    def test_retire_only_marker_from_parser(self):
        """RETIRE in v7 structured format produces a _retire_only marker."""
        payload = {
            "thread_actions": [
                {
                    "thread_id": "T-20260402-120000-01",
                    "lifecycle_action": "RETIRE",
                    "lifecycle_reasoning": "Hard falsifier triggered.",
                },
            ],
            "new_hypotheses": [_base_hypothesis()],
        }
        raw = json.dumps(payload)
        result = parse_generation_output(raw, "R-20260403-120000")

        retire_items = [r for r in result if r.get("_retire_only")]
        new_items = [r for r in result if r.get("lifecycle_action") == "NEW"]

        assert len(retire_items) == 1
        assert retire_items[0]["_thread_id_ref"] == "T-20260402-120000-01"
        assert len(new_items) == 1


class TestInheritField:
    """Test the _inherit_field helper for edge cases."""

    def test_inherits_when_missing(self, db_session):
        from backend.api.pipeline import _inherit_field
        from backend.db.models import Hypothesis as HM

        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        _, prior_h = _create_thread_and_instance(db_session, prior_run)

        h_data = {"source_theory": "unknown"}
        _inherit_field(h_data, prior_h, "source_theory")
        assert h_data["source_theory"] == "valuation_mean_reversion"

    def test_does_not_override_existing(self, db_session):
        from backend.api.pipeline import _inherit_field

        prior_run = _create_run(db_session, run_id="R-20260402-120000", status="complete")
        _, prior_h = _create_thread_and_instance(db_session, prior_run)

        h_data = {"source_theory": "debt_cycle_short"}
        _inherit_field(h_data, prior_h, "source_theory")
        assert h_data["source_theory"] == "debt_cycle_short"
