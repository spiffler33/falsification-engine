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
    import sqlite3
    raw = eng.raw_connection()
    try:
        cursor = raw.cursor()
        # Add newsletter_id to trades if missing
        cols = [r[1] for r in cursor.execute("PRAGMA table_info(trades)").fetchall()]
        if "newsletter_id" in cols:
            return
        cursor.execute("ALTER TABLE trades ADD COLUMN newsletter_id TEXT REFERENCES newsletters(id)")
        raw.commit()
    except Exception:
        pass  # Column may already exist or table may not exist yet
    finally:
        raw.close()
