# database.py — SQLite setup and session management.
# Depends on: backend/config.py
# Depended on by: all API routes, db/models.py, db/seed.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import DB_PATH, settings

# Ensure data directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite needs this for FastAPI
    echo=False,
)


# Enable WAL mode and foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist, and apply lightweight migrations."""
    from backend.db import models  # noqa: F401 — import triggers table registration
    Base.metadata.create_all(bind=engine)
    _migrate(engine)


def _migrate(eng):
    """Apply column additions that create_all won't handle on existing tables."""
    raw = eng.raw_connection()
    try:
        cursor = raw.cursor()

        def _add_column(table, column, col_type, extra=""):
            rows = cursor.execute(f"PRAGMA table_info({table})").fetchall()
            if not rows:
                return  # table doesn't exist yet; create_all will handle it
            cols = [r[1] for r in rows]
            if column not in cols:
                stmt = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                if extra:
                    stmt += f" {extra}"
                cursor.execute(stmt)

        # Migration 1: newsletter_id on trades
        _add_column("trades", "newsletter_id", "TEXT", "REFERENCES newsletters(id)")

        # Migration 2: regime_flags_active on runs (v3)
        _add_column("runs", "regime_flags_active", "TEXT")

        # Migration 3: resolution channel fields on hypotheses (v3)
        _add_column("hypotheses", "resolution_channel", "TEXT")
        _add_column("hypotheses", "resolution_channel_original", "TEXT")

        # Migration 4: sector appendix persistence (v4)
        _add_column("hypotheses", "sector_appendices_applied", "TEXT")
        _add_column("runs", "sector_appendices_loaded", "TEXT")

        # Migration 4b: sector_falsifier_audit table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sector_falsifier_audit (
                id TEXT PRIMARY KEY,
                hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
                sector_id TEXT NOT NULL,
                falsifier_id TEXT NOT NULL,
                metric_value_found TEXT,
                triggered TEXT NOT NULL,
                relevant TEXT NOT NULL,
                reasoning TEXT,
                severity_applied TEXT,
                run_id TEXT NOT NULL REFERENCES runs(id),
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Migration 5: walk-forward analysis (briefing snapshot + price snapshots + outcomes)
        _add_column("runs", "briefing_snapshot", "TEXT")
        _add_column("runs", "price_snapshot_date", "TEXT")
        _add_column("hypotheses", "outcome_status", "TEXT")
        _add_column("hypotheses", "outcome_date", "TEXT")
        _add_column("hypotheses", "outcome_notes", "TEXT")
        _add_column("hypotheses", "outcome_pnl_pct", "REAL")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_price_snapshots (
                run_id TEXT NOT NULL REFERENCES runs(id),
                ticker TEXT NOT NULL,
                price REAL NOT NULL,
                date TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'yahoo_finance',
                PRIMARY KEY (run_id, ticker)
            )
        """)

        raw.commit()
    except Exception:
        pass  # Table may not exist yet on fresh DB (create_all handles it)
    finally:
        raw.close()
