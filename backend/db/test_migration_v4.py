"""Tests for v4 migration: sector appendix persistence.

Covers:
  - Fresh database: all structures created via create_all + migrate
  - Existing database: migration is idempotent (no errors on re-run)
  - sector_falsifier_audit table: write and read records with all fields
  - runs.sector_appendices_loaded: JSON serialization/deserialization
  - hypotheses.sector_appendices_applied: JSON storage
"""

import json
import os
import tempfile
import uuid

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from backend.db import models  # noqa: F401 — register models with Base
from backend.db.database import Base, _migrate


def _make_engine(db_path: str):
    """Create an engine + session for a temporary SQLite file."""
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


@pytest.fixture()
def fresh_db(tmp_path):
    """A fresh database with all tables created from ORM models + migration."""
    db_path = str(tmp_path / "fresh.db")
    engine = _make_engine(db_path)
    Base.metadata.create_all(bind=engine)
    _migrate(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session, engine
    session.close()
    engine.dispose()


@pytest.fixture()
def existing_db(tmp_path):
    """An existing database (v3 schema) that then gets the v4 migration applied."""
    db_path = str(tmp_path / "existing.db")
    engine = _make_engine(db_path)

    # Create v3-era tables manually (no sector columns, no audit table)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE runs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                generation_output TEXT,
                elimination_output TEXT,
                activation_scores TEXT,
                regime_flags_active TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE hypotheses (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id),
                short_name TEXT NOT NULL,
                full_statement TEXT NOT NULL,
                source_theory TEXT NOT NULL,
                source_theories TEXT,
                status TEXT NOT NULL,
                conviction REAL,
                conviction_math TEXT,
                hard_falsifiers TEXT,
                soft_falsifiers TEXT,
                predicted_assets TEXT,
                asset_direction TEXT,
                timeframe TEXT,
                resolution_channel TEXT,
                resolution_channel_original TEXT,
                elimination_notes TEXT,
                generated_date TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """))
        # Insert a row to verify data preservation
        conn.execute(text("""
            INSERT INTO runs (id, timestamp, status) VALUES ('R-test', '2026-03-29T00:00:00', 'complete')
        """))
        conn.execute(text("""
            INSERT INTO hypotheses (id, run_id, short_name, full_statement, source_theory, status, generated_date)
            VALUES ('H-test', 'R-test', 'Test hypothesis', 'Full statement', 'valuation_mean_reversion', 'SURVIVED', '2026-03-29')
        """))
        conn.commit()

    # Now apply migration
    _migrate(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session, engine
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Fresh database — all structures created
# ---------------------------------------------------------------------------

def test_fresh_db_has_sector_falsifier_audit_table(fresh_db):
    session, engine = fresh_db
    with engine.connect() as conn:
        tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
    assert "sector_falsifier_audit" in tables


def test_fresh_db_hypotheses_has_sector_appendices_applied(fresh_db):
    session, engine = fresh_db
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(hypotheses)")).fetchall()]
    assert "sector_appendices_applied" in cols


def test_fresh_db_runs_has_sector_appendices_loaded(fresh_db):
    session, engine = fresh_db
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(runs)")).fetchall()]
    assert "sector_appendices_loaded" in cols


# ---------------------------------------------------------------------------
# Existing database — idempotent migration, data preserved
# ---------------------------------------------------------------------------

def test_existing_db_migration_adds_sector_columns(existing_db):
    session, engine = existing_db
    with engine.connect() as conn:
        hyp_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(hypotheses)")).fetchall()]
        run_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(runs)")).fetchall()]
    assert "sector_appendices_applied" in hyp_cols
    assert "sector_appendices_loaded" in run_cols


def test_existing_db_creates_audit_table(existing_db):
    session, engine = existing_db
    with engine.connect() as conn:
        tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
    assert "sector_falsifier_audit" in tables


def test_existing_db_preserves_data(existing_db):
    session, engine = existing_db
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id, status FROM runs WHERE id = 'R-test'")).fetchone()
    assert row is not None
    assert row[0] == "R-test"
    assert row[1] == "complete"


def test_existing_db_preserves_hypothesis_data(existing_db):
    session, engine = existing_db
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id, short_name, sector_appendices_applied FROM hypotheses WHERE id = 'H-test'")).fetchone()
    assert row is not None
    assert row[0] == "H-test"
    assert row[1] == "Test hypothesis"
    assert row[2] is None  # new column defaults to NULL


def test_existing_db_double_migration_no_error(existing_db):
    """Running migration twice should not raise."""
    _, engine = existing_db
    _migrate(engine)  # second time — must be idempotent
    _migrate(engine)  # third time — still safe


# ---------------------------------------------------------------------------
# sector_falsifier_audit — write and read
# ---------------------------------------------------------------------------

def test_write_and_read_audit_record(fresh_db):
    session, engine = fresh_db
    with engine.connect() as conn:
        # Create prerequisite run + hypothesis
        conn.execute(text("""
            INSERT INTO runs (id, timestamp, status) VALUES ('R-001', '2026-03-29T00:00:00', 'partial')
        """))
        conn.execute(text("""
            INSERT INTO hypotheses (id, run_id, short_name, full_statement, source_theory, status, generated_date)
            VALUES ('H-001', 'R-001', 'Tech overweight', 'Full', 'structural_fragility', 'WOUNDED', '2026-03-29')
        """))

        # Write audit record
        audit_id = f"SA-{uuid.uuid4().hex[:12]}"
        conn.execute(text("""
            INSERT INTO sector_falsifier_audit
                (id, hypothesis_id, sector_id, falsifier_id, metric_value_found, triggered, relevant, reasoning, severity_applied, run_id)
            VALUES (:id, :hid, :sid, :fid, :mv, :trig, :rel, :reason, :sev, :rid)
        """), {
            "id": audit_id,
            "hid": "H-001",
            "sid": "tech_ai",
            "fid": "tech_sf_01",
            "mv": "1.6x",
            "trig": "YES",
            "rel": "YES",
            "reason": "Semiconductor inventory ratio exceeds 1.5x threshold",
            "sev": "medium",
            "rid": "R-001",
        })
        conn.commit()

        # Read it back
        row = conn.execute(text("""
            SELECT id, hypothesis_id, sector_id, falsifier_id, metric_value_found,
                   triggered, relevant, reasoning, severity_applied, run_id
            FROM sector_falsifier_audit WHERE id = :id
        """), {"id": audit_id}).fetchone()

    assert row is not None
    assert row[0] == audit_id
    assert row[1] == "H-001"
    assert row[2] == "tech_ai"
    assert row[3] == "tech_sf_01"
    assert row[4] == "1.6x"
    assert row[5] == "YES"
    assert row[6] == "YES"
    assert row[7] == "Semiconductor inventory ratio exceeds 1.5x threshold"
    assert row[8] == "medium"
    assert row[9] == "R-001"


# ---------------------------------------------------------------------------
# runs.sector_appendices_loaded — JSON serialization
# ---------------------------------------------------------------------------

def test_run_sector_appendices_loaded_json(fresh_db):
    session, engine = fresh_db
    sector_ids = ["tech_ai", "energy"]
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO runs (id, timestamp, status, sector_appendices_loaded)
            VALUES ('R-002', '2026-03-29T01:00:00', 'partial', :sal)
        """), {"sal": json.dumps(sector_ids)})
        conn.commit()

        row = conn.execute(text("SELECT sector_appendices_loaded FROM runs WHERE id = 'R-002'")).fetchone()

    assert row is not None
    loaded = json.loads(row[0])
    assert loaded == ["tech_ai", "energy"]


# ---------------------------------------------------------------------------
# hypotheses.sector_appendices_applied — JSON storage
# ---------------------------------------------------------------------------

def test_hypothesis_sector_appendices_applied(fresh_db):
    session, engine = fresh_db
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO runs (id, timestamp, status) VALUES ('R-003', '2026-03-29T02:00:00', 'complete')
        """))
        conn.execute(text("""
            INSERT INTO hypotheses (id, run_id, short_name, full_statement, source_theory, status, generated_date, sector_appendices_applied)
            VALUES ('H-003', 'R-003', 'Energy play', 'Full statement', 'capital_flows', 'SURVIVED', '2026-03-29', :saa)
        """), {"saa": json.dumps(["energy"])})
        conn.commit()

        row = conn.execute(text("SELECT sector_appendices_applied FROM hypotheses WHERE id = 'H-003'")).fetchone()

    assert row is not None
    applied = json.loads(row[0])
    assert applied == ["energy"]
