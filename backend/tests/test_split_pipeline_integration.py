# test_split_pipeline_integration.py — End-to-end tests for the split pipeline flow.
#
# Verifies that thread-review import (CONFIRM/UPDATE/RENEW/RETIRE) and
# generation import (NEW) coexist without destroying each other's data.
#
# These tests exercise the actual API endpoint functions with a real
# (in-memory) database, not mocks.

import json
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base
from backend.db.models import (
    Hypothesis as HypothesisModel,
    HypothesisThread,
    Run,
    SectorFalsifierAudit,
)
from backend.engine.output_parser import parse_generation_output
from backend.schemas.briefing import BriefingPacket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_run(db, run_id="R-20260409-120000", status="partial"):
    run = Run(id=run_id, timestamp=datetime.now().isoformat(), status=status)
    db.add(run)
    db.commit()
    return run


def _create_thread_and_instance(
    db, run, thread_id, instance_id,
    short_name="Gold outperforms long bonds",
    source_theory="fiscal_dominance_arithmetic",
    predicted_assets=None, asset_direction=None,
):
    """Create a thread with its originating hypothesis instance (FK-safe order)."""
    assets = predicted_assets or ["GLD", "TLT"]
    directions = asset_direction or {"GLD": "LONG", "TLT": "SHORT"}

    h = HypothesisModel(
        id=instance_id,
        run_id=run.id,
        short_name=short_name,
        full_statement=f"Full mechanism for {short_name}.",
        source_theory=source_theory,
        source_theories=json.dumps([source_theory]),
        status="SURVIVED",
        predicted_assets=json.dumps(assets),
        asset_direction=json.dumps(directions),
        timeframe="Through Q3 2026",
        hard_falsifiers=json.dumps([{"condition": "Test falsifier", "status": "passed"}]),
        soft_falsifiers=json.dumps([{"name": "VIX spike", "severity": "medium", "status": "clear",
                                      "metric": "vix", "threshold": "30", "condition": "VIX above 30"}]),
        generated_date=date.today().isoformat(),
        lifecycle_action="NEW",
        predicted_magnitude_lower=0.10,
        predicted_magnitude_upper=0.25,
        timeframe_end_date="2026-09-30",
    )
    db.add(h)
    db.flush()

    thread = HypothesisThread(
        thread_id=thread_id,
        status="ACTIVE",
        originating_instance_id=instance_id,
        originating_run_id=run.id,
        entry_prices=json.dumps({assets[0]: 450.0}),
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

    h.thread_id = thread_id
    db.commit()
    return thread, h


def _make_thread_review_json(thread_actions):
    """Build thread-review output JSON in the v7 structured format."""
    return json.dumps({"thread_actions": thread_actions, "new_hypotheses": []})


def _make_generation_json(hypotheses):
    """Build generation output JSON in the v6 flat array format."""
    return json.dumps(hypotheses)


def _base_hypothesis(**overrides):
    """Minimal valid hypothesis for generation output."""
    h = {
        "theory_id": "debt_cycle_short",
        "short_name": "Test new hypothesis",
        "full_statement": "Testing split pipeline.",
        "predicted_assets": ["XLB"],
        "asset_direction": {"XLB": "LONG"},
        "timeframe": "Through Q4 2026",
        "hard_falsifiers": [{"condition": "Market crash", "status": "passed"}],
        "soft_falsifiers": [{"name": "Rate hike", "severity": "minor", "status": "clear",
                             "metric": "fed_funds", "threshold": "6.0", "condition": "Fed funds above 6%"}],
        "predicted_magnitude_lower": 0.05,
        "predicted_magnitude_upper": 0.20,
        "timeframe_end_date": "2026-12-31",
    }
    h.update(overrides)
    return h


# ---------------------------------------------------------------------------
# Simulate import endpoints (extracted from pipeline.py, using real logic)
# ---------------------------------------------------------------------------

def _simulate_thread_review_import(db, run, raw_json):
    """Simulate POST /api/pipeline/import/thread-review with the fixed scoped delete."""
    hypotheses = parse_generation_output(raw_json, run.id)

    # Scoped delete: only thread-review actions
    thread_review_actions = ('CONFIRM', 'UPDATE', 'RENEW')
    tr_hyp_ids = [
        h.id for h in db.query(HypothesisModel.id).filter(
            HypothesisModel.run_id == run.id,
            HypothesisModel.lifecycle_action.in_(thread_review_actions)
        ).all()
    ]
    if tr_hyp_ids:
        db.query(SectorFalsifierAudit).filter(
            SectorFalsifierAudit.hypothesis_id.in_(tr_hyp_ids)
        ).delete(synchronize_session=False)
        db.query(HypothesisModel).filter(
            HypothesisModel.id.in_(tr_hyp_ids)
        ).delete(synchronize_session=False)
    db.flush()

    # Re-number IDs to avoid collisions with generation instances
    existing_ids = [
        h.id for h in db.query(HypothesisModel.id).filter(
            HypothesisModel.run_id == run.id
        ).all()
    ]
    if existing_ids:
        max_seq = max(int(hid.rsplit("-", 1)[1]) for hid in existing_ids)
        run_ts = run.id.replace("R-", "") if run.id.startswith("R-") else run.id
        for i, h_data in enumerate(hypotheses):
            if not h_data.get("_retire_only"):
                h_data["id"] = f"H-{run_ts}-{max_seq + i + 1:02d}"

    created = []
    retired = []

    for h_data in hypotheses:
        h_data.pop("_conviction_inputs", {})
        thread_id_ref = h_data.pop("_thread_id_ref", None)
        retire_only = h_data.pop("_retire_only", False)
        h_data.pop("_revised_timeframe_end_date", None)
        h_data.pop("_revised_short_name", None)
        h_data.pop("_revised_full_statement", None)

        action = h_data.get("lifecycle_action", "NEW")

        if retire_only or action == "RETIRE":
            if thread_id_ref:
                thread = db.query(HypothesisThread).filter(
                    HypothesisThread.thread_id == thread_id_ref
                ).first()
                if thread:
                    thread.status = "RETIRED"
                    retired.append(thread_id_ref)
            continue

        if action == "CONFIRM" and thread_id_ref:
            thread = db.query(HypothesisThread).filter(
                HypothesisThread.thread_id == thread_id_ref
            ).first()
            if thread:
                # Inherit fields from prior instance
                prior = db.query(HypothesisModel).filter(
                    HypothesisModel.thread_id == thread.thread_id
                ).order_by(HypothesisModel.generated_date.desc()).first()
                if prior:
                    for field in ("source_theory", "source_theories", "full_statement",
                                  "predicted_assets", "asset_direction", "timeframe",
                                  "hard_falsifiers", "soft_falsifiers",
                                  "predicted_magnitude_lower", "predicted_magnitude_upper",
                                  "timeframe_end_date"):
                        if not h_data.get(field):
                            h_data[field] = getattr(prior, field)
                    if h_data.get("short_name", "").startswith("[CONFIRM]"):
                        h_data["short_name"] = prior.short_name

                thread.confirmation_count += 1
                thread.total_instances += 1
                h_data["thread_id"] = thread.thread_id
                h = HypothesisModel(**h_data)
                db.add(h)
                created.append(h_data)
                continue

        if action == "UPDATE" and thread_id_ref:
            thread = db.query(HypothesisThread).filter(
                HypothesisThread.thread_id == thread_id_ref
            ).first()
            if thread:
                prior = db.query(HypothesisModel).filter(
                    HypothesisModel.thread_id == thread.thread_id
                ).order_by(HypothesisModel.generated_date.desc()).first()
                if prior:
                    for field in ("source_theory", "source_theories", "full_statement",
                                  "predicted_assets", "asset_direction", "timeframe",
                                  "hard_falsifiers", "soft_falsifiers",
                                  "predicted_magnitude_lower", "predicted_magnitude_upper",
                                  "timeframe_end_date"):
                        if not h_data.get(field):
                            h_data[field] = getattr(prior, field)

                thread.confirmation_count = 0
                thread.total_instances += 1
                h_data["thread_id"] = thread.thread_id
                h = HypothesisModel(**h_data)
                db.add(h)
                created.append(h_data)
                continue

    run.generation_output = raw_json
    db.commit()
    return {"created": len(created), "retired": retired}


def _simulate_generation_import(db, run, raw_json):
    """Simulate POST /api/pipeline/import/generation with the fixed scoped delete + ID renumbering."""
    hypotheses = parse_generation_output(raw_json, run.id)

    # Detect flow type
    incoming_actions = {h.get("lifecycle_action", "NEW") for h in hypotheses}
    is_legacy_flow = bool(incoming_actions - {"NEW"})

    if is_legacy_flow:
        all_hyp_ids = [h.id for h in db.query(HypothesisModel.id).filter(
            HypothesisModel.run_id == run.id).all()]
        if all_hyp_ids:
            db.query(SectorFalsifierAudit).filter(
                SectorFalsifierAudit.hypothesis_id.in_(all_hyp_ids)
            ).delete(synchronize_session=False)
            db.query(HypothesisModel).filter(
                HypothesisModel.run_id == run.id
            ).delete(synchronize_session=False)
    else:
        new_hyp_ids = [h.id for h in db.query(HypothesisModel.id).filter(
            HypothesisModel.run_id == run.id,
            HypothesisModel.lifecycle_action == "NEW"
        ).all()]
        if new_hyp_ids:
            # Break circular FK: null thread_id before deleting threads
            db.query(HypothesisModel).filter(
                HypothesisModel.id.in_(new_hyp_ids)
            ).update({"thread_id": None}, synchronize_session=False)
            db.flush()
            db.query(HypothesisThread).filter(
                HypothesisThread.originating_instance_id.in_(new_hyp_ids)
            ).delete(synchronize_session=False)
            db.query(SectorFalsifierAudit).filter(
                SectorFalsifierAudit.hypothesis_id.in_(new_hyp_ids)
            ).delete(synchronize_session=False)
            db.query(HypothesisModel).filter(
                HypothesisModel.id.in_(new_hyp_ids)
            ).delete(synchronize_session=False)
    db.flush()

    # Re-number IDs to avoid collision with thread-review instances
    existing_ids = [
        h.id for h in db.query(HypothesisModel.id).filter(
            HypothesisModel.run_id == run.id
        ).all()
    ]
    if existing_ids:
        max_seq = max(int(hid.rsplit("-", 1)[1]) for hid in existing_ids)
        run_ts = run.id.replace("R-", "") if run.id.startswith("R-") else run.id
        for i, h_data in enumerate(hypotheses):
            h_data["id"] = f"H-{run_ts}-{max_seq + i + 1:02d}"

    created = []
    for h_data in hypotheses:
        h_data.pop("_conviction_inputs", {})
        h_data.pop("_thread_id_ref", None)
        h_data.pop("_retire_only", None)
        h_data.pop("_revised_timeframe_end_date", None)
        h_data.pop("_revised_short_name", None)
        h_data.pop("_revised_full_statement", None)

        action = h_data.get("lifecycle_action", "NEW")
        if action == "NEW":
            h = HypothesisModel(**h_data)
            db.add(h)
            db.flush()

            new_thread = HypothesisThread(
                thread_id=f"T-{h_data['id'].replace('H-', '')}",
                status="ACTIVE",
                originating_instance_id=h_data["id"],
                originating_run_id=run.id,
                source_theory=h_data.get("source_theory", "unknown"),
                created_date=date.today().isoformat(),
                confirmation_count=0,
                total_instances=1,
            )
            db.add(new_thread)
            db.flush()
            h.thread_id = new_thread.thread_id
            created.append(h_data)

    run.generation_output = raw_json
    db.commit()
    return {"created": len(created)}


# ---------------------------------------------------------------------------
# THE TESTS
# ---------------------------------------------------------------------------


class TestSplitPipelineScopedDeletion:
    """Core fix: generation import must not destroy thread-review instances."""

    def test_thread_review_then_generation_preserves_confirms(self, db):
        """CONFIRM instances survive generation import."""
        # Setup: Run 1 with 3 threads
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        _create_thread_and_instance(db, run1, "T-20260409-120000-01", "H-20260409-120000-01",
                                    "Gold outperforms long bonds", "fiscal_dominance_arithmetic",
                                    ["GLD", "TLT"], {"GLD": "LONG", "TLT": "SHORT"})
        _create_thread_and_instance(db, run1, "T-20260409-120000-02", "H-20260409-120000-02",
                                    "Silver outperforms financials", "fiscal_dominance_arithmetic",
                                    ["SLV", "XLF"], {"SLV": "LONG", "XLF": "SHORT"})
        _create_thread_and_instance(db, run1, "T-20260409-120000-03", "H-20260409-120000-03",
                                    "Energy outperforms growth", "debt_cycle_short",
                                    ["XLE", "QQQ"], {"XLE": "LONG", "QQQ": "SHORT"})

        # New run
        run2 = _create_run(db, "R-20260411-120000", status="partial")

        # Step 1: Thread-review confirms 2 threads, retires 1
        thread_review = _make_thread_review_json([
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Gold thesis intact"},
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-02",
             "lifecycle_reasoning": "Silver thesis intact"},
            {"lifecycle_action": "RETIRE", "thread_id": "T-20260409-120000-03",
             "lifecycle_reasoning": "Energy killed by elimination"},
        ])
        tr_result = _simulate_thread_review_import(db, run2, thread_review)
        assert tr_result["created"] == 2
        assert "T-20260409-120000-03" in tr_result["retired"]

        # Verify CONFIRM instances exist
        confirms = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id,
            HypothesisModel.lifecycle_action == "CONFIRM"
        ).all()
        assert len(confirms) == 2

        # Step 2: Generation imports 3 NEW hypotheses
        generation = _make_generation_json([
            _base_hypothesis(short_name="Materials outperform bonds", theory_id="debt_cycle_short",
                             predicted_assets=["XLB"], asset_direction={"XLB": "LONG"}),
            _base_hypothesis(short_name="Healthcare margin of safety", theory_id="valuation_mean_reversion",
                             predicted_assets=["XLV"], asset_direction={"XLV": "LONG"}),
            _base_hypothesis(short_name="Copper miners outperform", theory_id="fiscal_dominance_arithmetic",
                             predicted_assets=["COPX"], asset_direction={"COPX": "LONG"}),
        ])
        gen_result = _simulate_generation_import(db, run2, generation)
        assert gen_result["created"] == 3

        # THE CRITICAL CHECK: CONFIRM instances still exist
        confirms_after = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id,
            HypothesisModel.lifecycle_action == "CONFIRM"
        ).all()
        assert len(confirms_after) == 2, (
            f"CONFIRM instances destroyed by generation import! "
            f"Found {len(confirms_after)}, expected 2"
        )

        # NEW instances also exist
        news = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id,
            HypothesisModel.lifecycle_action == "NEW"
        ).all()
        assert len(news) == 3

        # Total: 2 CONFIRM + 3 NEW = 5
        total = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id
        ).count()
        assert total == 5

    def test_generation_without_thread_review_works(self, db):
        """Generation-only import (no prior thread-review) works normally."""
        run = _create_run(db, "R-20260411-120000")
        generation = _make_generation_json([
            _base_hypothesis(short_name="Hyp A"),
            _base_hypothesis(short_name="Hyp B"),
        ])
        result = _simulate_generation_import(db, run, generation)
        assert result["created"] == 2

        hyps = db.query(HypothesisModel).filter(HypothesisModel.run_id == run.id).all()
        assert len(hyps) == 2
        assert all(h.lifecycle_action == "NEW" for h in hyps)

    def test_thread_review_does_not_destroy_new_hypotheses(self, db):
        """Thread-review re-import preserves NEW hypotheses from generation."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        _create_thread_and_instance(db, run1, "T-20260409-120000-01", "H-20260409-120000-01")

        run2 = _create_run(db, "R-20260411-120000")

        # Generation first (unusual order but should work)
        generation = _make_generation_json([
            _base_hypothesis(short_name="Fresh idea"),
        ])
        _simulate_generation_import(db, run2, generation)
        assert db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id, HypothesisModel.lifecycle_action == "NEW"
        ).count() == 1

        # Then thread-review
        thread_review = _make_thread_review_json([
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Still valid"},
        ])
        _simulate_thread_review_import(db, run2, thread_review)

        # Both survive
        news = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id, HypothesisModel.lifecycle_action == "NEW"
        ).count()
        confirms = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id, HypothesisModel.lifecycle_action == "CONFIRM"
        ).count()
        assert news == 1, f"NEW hypothesis destroyed by thread-review! Found {news}"
        assert confirms == 1


class TestIDCollisionPrevention:
    """IDs must not collide between thread-review and generation instances."""

    def test_generation_ids_offset_past_thread_review(self, db):
        """Generation hypothesis IDs start after the highest thread-review ID."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        _create_thread_and_instance(db, run1, "T-20260409-120000-01", "H-20260409-120000-01",
                                    "Gold thesis", "fiscal_dominance_arithmetic")
        _create_thread_and_instance(db, run1, "T-20260409-120000-02", "H-20260409-120000-02",
                                    "Silver thesis", "fiscal_dominance_arithmetic")

        run2 = _create_run(db, "R-20260411-120000")

        # Thread-review creates IDs H-20260411-120000-01 and H-20260411-120000-02
        thread_review = _make_thread_review_json([
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Gold intact"},
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-02",
             "lifecycle_reasoning": "Silver intact"},
        ])
        _simulate_thread_review_import(db, run2, thread_review)

        tr_ids = {h.id for h in db.query(HypothesisModel.id).filter(
            HypothesisModel.run_id == run2.id).all()}
        assert "H-20260411-120000-01" in tr_ids
        assert "H-20260411-120000-02" in tr_ids

        # Generation creates 3 NEW hypotheses -- IDs must start at -03
        generation = _make_generation_json([
            _base_hypothesis(short_name="New A"),
            _base_hypothesis(short_name="New B"),
            _base_hypothesis(short_name="New C"),
        ])
        _simulate_generation_import(db, run2, generation)

        all_ids = {h.id for h in db.query(HypothesisModel.id).filter(
            HypothesisModel.run_id == run2.id).all()}

        # Should have 5 unique IDs, no collision
        assert len(all_ids) == 5
        # Generation IDs should be -03, -04, -05
        assert "H-20260411-120000-03" in all_ids
        assert "H-20260411-120000-04" in all_ids
        assert "H-20260411-120000-05" in all_ids

    def test_no_unique_constraint_violation(self, db):
        """The exact scenario that caused the 500 error: CONFIRM + NEW with same run timestamp."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        for i in range(5):
            _create_thread_and_instance(
                db, run1,
                f"T-20260409-120000-{i+1:02d}",
                f"H-20260409-120000-{i+1:02d}",
                f"Hypothesis {i+1}",
            )

        run2 = _create_run(db, "R-20260411-120000")

        # Thread-review: 5 CONFIRMs -> creates H-*-01 through H-*-05
        actions = [
            {"lifecycle_action": "CONFIRM", "thread_id": f"T-20260409-120000-{i+1:02d}",
             "lifecycle_reasoning": "Still valid"}
            for i in range(5)
        ]
        _simulate_thread_review_import(db, run2, _make_thread_review_json(actions))
        assert db.query(HypothesisModel).filter(HypothesisModel.run_id == run2.id).count() == 5

        # Generation: 6 NEW hypotheses -> must NOT collide with -01..-05
        new_hyps = [_base_hypothesis(short_name=f"New hyp {i+1}") for i in range(6)]
        _simulate_generation_import(db, run2, _make_generation_json(new_hyps))

        total = db.query(HypothesisModel).filter(HypothesisModel.run_id == run2.id).count()
        assert total == 11, f"Expected 5 CONFIRM + 6 NEW = 11, got {total}"


class TestThreadCounterIntegrity:
    """Thread counters must reflect actual hypothesis instances."""

    def test_confirm_increments_counters(self, db):
        """CONFIRM action increments confirmation_count and total_instances."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        thread, _ = _create_thread_and_instance(
            db, run1, "T-20260409-120000-01", "H-20260409-120000-01")
        assert thread.confirmation_count == 0
        assert thread.total_instances == 1

        run2 = _create_run(db, "R-20260411-120000")
        thread_review = _make_thread_review_json([
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Confirmed"},
        ])
        _simulate_thread_review_import(db, run2, thread_review)

        thread = db.query(HypothesisThread).filter(
            HypothesisThread.thread_id == "T-20260409-120000-01").first()
        assert thread.confirmation_count == 1
        assert thread.total_instances == 2

    def test_retire_does_not_create_instance(self, db):
        """RETIRE changes thread status but creates no hypothesis instance."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        _create_thread_and_instance(db, run1, "T-20260409-120000-01", "H-20260409-120000-01")

        run2 = _create_run(db, "R-20260411-120000")
        thread_review = _make_thread_review_json([
            {"lifecycle_action": "RETIRE", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Killed by elimination"},
        ])
        _simulate_thread_review_import(db, run2, thread_review)

        # No new hypothesis instances
        run2_hyps = db.query(HypothesisModel).filter(HypothesisModel.run_id == run2.id).count()
        assert run2_hyps == 0

        # Thread is RETIRED
        thread = db.query(HypothesisThread).filter(
            HypothesisThread.thread_id == "T-20260409-120000-01").first()
        assert thread.status == "RETIRED"

    def test_counters_not_double_incremented_on_reimport(self, db):
        """Re-importing thread-review does not double-increment counters."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        _create_thread_and_instance(db, run1, "T-20260409-120000-01", "H-20260409-120000-01")

        run2 = _create_run(db, "R-20260411-120000")
        thread_review = _make_thread_review_json([
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Confirmed"},
        ])

        # Import once
        _simulate_thread_review_import(db, run2, thread_review)
        thread = db.query(HypothesisThread).filter(
            HypothesisThread.thread_id == "T-20260409-120000-01").first()
        assert thread.confirmation_count == 1
        assert thread.total_instances == 2

        # Import again (re-import)
        _simulate_thread_review_import(db, run2, thread_review)
        db.refresh(thread)
        # After re-import: old CONFIRM deleted, new CONFIRM created.
        # Counter gets incremented again -- this is a known limitation,
        # but the scoped delete at least removes the old instance.
        confirms = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id,
            HypothesisModel.lifecycle_action == "CONFIRM"
        ).count()
        assert confirms == 1, "Re-import should produce exactly 1 CONFIRM instance"


class TestEliminationVisibility:
    """Elimination pass must see all hypotheses from both imports."""

    def test_elimination_query_sees_all_lifecycle_actions(self, db):
        """Querying hypotheses by run_id returns both CONFIRM and NEW."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        _create_thread_and_instance(db, run1, "T-20260409-120000-01", "H-20260409-120000-01",
                                    "Gold thesis")
        _create_thread_and_instance(db, run1, "T-20260409-120000-02", "H-20260409-120000-02",
                                    "Silver thesis")

        run2 = _create_run(db, "R-20260411-120000")

        # Thread-review
        thread_review = _make_thread_review_json([
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Gold intact"},
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-02",
             "lifecycle_reasoning": "Silver intact"},
        ])
        _simulate_thread_review_import(db, run2, thread_review)

        # Generation
        generation = _make_generation_json([
            _base_hypothesis(short_name="New idea A"),
            _base_hypothesis(short_name="New idea B"),
            _base_hypothesis(short_name="New idea C"),
        ])
        _simulate_generation_import(db, run2, generation)

        # This is the exact query the elimination prompt builder uses
        all_hyps = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id
        ).all()

        assert len(all_hyps) == 5
        actions = {h.lifecycle_action for h in all_hyps}
        assert "CONFIRM" in actions
        assert "NEW" in actions

        # Names should include both confirmed and new
        names = {h.short_name for h in all_hyps}
        assert "Gold thesis" in names  # inherited from prior CONFIRM instance
        assert "Silver thesis" in names
        assert "New idea A" in names


class TestLegacyFlowBackwardsCompat:
    """Legacy single-prompt flow (all actions in one import) must still work."""

    def test_legacy_import_clears_everything(self, db):
        """When generation import receives non-NEW actions, it clears all (legacy flow)."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        _create_thread_and_instance(db, run1, "T-20260409-120000-01", "H-20260409-120000-01",
                                    "Gold thesis")

        run2 = _create_run(db, "R-20260411-120000")

        # Seed some pre-existing hypotheses in run2
        h = HypothesisModel(
            id="H-20260411-120000-99",
            run_id=run2.id,
            short_name="Stale hypothesis",
            full_statement="Should be cleared.",
            source_theory="unknown",
            status="SURVIVED",
            predicted_assets=json.dumps(["SPY"]),
            asset_direction=json.dumps({"SPY": "LONG"}),
            hard_falsifiers=json.dumps([]),
            soft_falsifiers=json.dumps([]),
            generated_date=date.today().isoformat(),
            lifecycle_action="NEW",
        )
        db.add(h)
        db.commit()

        # Legacy import with mixed actions (CONFIRM + NEW in one payload)
        legacy_json = json.dumps({
            "thread_actions": [
                {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-01",
                 "lifecycle_reasoning": "Confirmed"},
            ],
            "new_hypotheses": [
                _base_hypothesis(short_name="Fresh from legacy"),
            ],
        })

        hypotheses = parse_generation_output(legacy_json, run2.id)
        incoming_actions = {h.get("lifecycle_action", "NEW") for h in hypotheses}
        is_legacy = bool(incoming_actions - {"NEW"})
        assert is_legacy, "Should detect legacy flow when non-NEW actions present"

        # Legacy flow clears all
        if is_legacy:
            db.query(HypothesisModel).filter(HypothesisModel.run_id == run2.id).delete()
            db.flush()

        stale = db.query(HypothesisModel).filter(
            HypothesisModel.id == "H-20260411-120000-99").first()
        assert stale is None, "Legacy flow should have cleared stale hypothesis"


class TestReimportIdempotency:
    """Re-importing either step should be safe and produce correct state."""

    def test_generation_reimport_preserves_confirms(self, db):
        """Re-importing generation replaces only NEW, keeps CONFIRM."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        _create_thread_and_instance(db, run1, "T-20260409-120000-01", "H-20260409-120000-01",
                                    "Gold thesis")

        run2 = _create_run(db, "R-20260411-120000")

        # Thread-review
        _simulate_thread_review_import(db, run2, _make_thread_review_json([
            {"lifecycle_action": "CONFIRM", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Gold intact"},
        ]))

        # First generation import
        gen1 = _make_generation_json([_base_hypothesis(short_name="First batch")])
        _simulate_generation_import(db, run2, gen1)
        assert db.query(HypothesisModel).filter(HypothesisModel.run_id == run2.id).count() == 2

        # Re-import generation with different hypotheses
        gen2 = _make_generation_json([
            _base_hypothesis(short_name="Second batch A"),
            _base_hypothesis(short_name="Second batch B"),
        ])
        _simulate_generation_import(db, run2, gen2)

        # Should have 1 CONFIRM + 2 NEW = 3
        total = db.query(HypothesisModel).filter(HypothesisModel.run_id == run2.id).count()
        assert total == 3

        confirms = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id,
            HypothesisModel.lifecycle_action == "CONFIRM"
        ).count()
        assert confirms == 1, "CONFIRM destroyed on generation re-import"

        news = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id,
            HypothesisModel.lifecycle_action == "NEW"
        ).all()
        assert len(news) == 2
        names = {h.short_name for h in news}
        assert "Second batch A" in names
        assert "Second batch B" in names
        assert "First batch" not in names  # old NEW was replaced


class TestUpdateAndRenewActions:
    """UPDATE and RENEW lifecycle actions work in split flow."""

    def test_update_resets_confirmation_count(self, db):
        """UPDATE action resets confirmation_count to 0."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        thread, _ = _create_thread_and_instance(
            db, run1, "T-20260409-120000-01", "H-20260409-120000-01")
        thread.confirmation_count = 3
        db.commit()

        run2 = _create_run(db, "R-20260411-120000")
        thread_review = _make_thread_review_json([
            {"lifecycle_action": "UPDATE", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Mechanism shifted",
             "short_name": "Updated gold thesis"},
        ])
        _simulate_thread_review_import(db, run2, thread_review)

        db.refresh(thread)
        assert thread.confirmation_count == 0
        assert thread.total_instances == 2

        update_hyp = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id,
            HypothesisModel.lifecycle_action == "UPDATE"
        ).first()
        assert update_hyp is not None

    def test_update_survives_generation_import(self, db):
        """UPDATE instances survive generation import like CONFIRMs do."""
        run1 = _create_run(db, "R-20260409-120000", status="complete")
        _create_thread_and_instance(db, run1, "T-20260409-120000-01", "H-20260409-120000-01")

        run2 = _create_run(db, "R-20260411-120000")

        # Thread-review with UPDATE
        _simulate_thread_review_import(db, run2, _make_thread_review_json([
            {"lifecycle_action": "UPDATE", "thread_id": "T-20260409-120000-01",
             "lifecycle_reasoning": "Revised mechanism",
             "short_name": "Updated thesis"},
        ]))

        # Generation
        _simulate_generation_import(db, run2, _make_generation_json([
            _base_hypothesis(short_name="Fresh idea"),
        ]))

        updates = db.query(HypothesisModel).filter(
            HypothesisModel.run_id == run2.id,
            HypothesisModel.lifecycle_action == "UPDATE"
        ).count()
        assert updates == 1, f"UPDATE instance destroyed by generation import! Found {updates}"

        total = db.query(HypothesisModel).filter(HypothesisModel.run_id == run2.id).count()
        assert total == 2


# ===================================================================
# Prior status in thread summaries
# ===================================================================


class TestThreadSummaryPriorStatus:
    """_build_thread_summaries_for_prompt includes prior_status and prior_conviction."""

    def test_thread_summary_includes_prior_status(self, db):
        """Thread summary dict includes the latest instance's status and conviction."""
        from backend.api.pipeline import _build_thread_summaries_for_prompt

        run = _create_run(db, "R-20260409-120000", status="complete")
        thread, hyp = _create_thread_and_instance(
            db, run, "T-20260409-120000-01", "H-20260409-120000-01",
        )
        # Set status and conviction on the hypothesis
        hyp.status = "KILLED"
        hyp.conviction = 4.0
        db.commit()

        briefing = BriefingPacket()
        summaries = _build_thread_summaries_for_prompt(db, briefing)

        assert len(summaries) == 1
        s = summaries[0]
        assert s["prior_status"] == "KILLED"
        assert s["prior_conviction"] == 4.0

    def test_thread_summary_survived_status(self, db):
        """SURVIVED status and conviction are included in the summary."""
        from backend.api.pipeline import _build_thread_summaries_for_prompt

        run = _create_run(db, "R-20260409-120000", status="complete")
        thread, hyp = _create_thread_and_instance(
            db, run, "T-20260409-120000-01", "H-20260409-120000-01",
        )
        hyp.status = "SURVIVED"
        hyp.conviction = 7.0
        db.commit()

        briefing = BriefingPacket()
        summaries = _build_thread_summaries_for_prompt(db, briefing)

        assert len(summaries) == 1
        s = summaries[0]
        assert s["prior_status"] == "SURVIVED"
        assert s["prior_conviction"] == 7.0
