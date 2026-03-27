# models.py — SQLAlchemy ORM models matching FRONTEND_SPEC Section 10 schema.
# Depends on: db/database.py (Base)
# Depended on by: all API routes, db/seed.py
from sqlalchemy import Column, Float, ForeignKey, Text

from backend.db.database import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(Text, primary_key=True)
    timestamp = Column(Text, nullable=False)
    status = Column(Text, nullable=False)  # 'complete' | 'partial'
    generation_output = Column(Text)  # raw JSON from Claude
    elimination_output = Column(Text)  # raw JSON from Claude
    activation_scores = Column(Text)  # JSON map of theory_id -> tier


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id = Column(Text, primary_key=True)
    run_id = Column(Text, ForeignKey("runs.id"), nullable=False)
    short_name = Column(Text, nullable=False)
    full_statement = Column(Text, nullable=False)
    source_theory = Column(Text, nullable=False)
    source_theories = Column(Text)  # JSON array for multi-theory
    status = Column(Text, nullable=False)  # 'SURVIVED' | 'WOUNDED' | 'KILLED'
    conviction = Column(Float)
    conviction_math = Column(Text)  # full JSON of 3-stage pipeline
    hard_falsifiers = Column(Text)  # JSON array
    soft_falsifiers = Column(Text)  # JSON array
    predicted_assets = Column(Text)  # JSON array of tickers
    asset_direction = Column(Text)  # JSON map ticker -> direction
    timeframe = Column(Text)
    elimination_notes = Column(Text)
    generated_date = Column(Text, nullable=False)
    created_at = Column(Text, server_default="(datetime('now'))")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Text, primary_key=True)
    hypothesis_id = Column(Text, ForeignKey("hypotheses.id"), nullable=False)
    date = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    size = Column(Text)
    conviction_at_entry = Column(Float)
    reasoning = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="OPEN")
    outcome = Column(Text)
    closed_date = Column(Text)
    created_at = Column(Text, server_default="(datetime('now'))")


class InboxItem(Base):
    __tablename__ = "inbox_items"

    id = Column(Text, primary_key=True)
    date = Column(Text, nullable=False)
    type = Column(Text, nullable=False)  # 'link' | 'note'
    content = Column(Text, nullable=False)
    source = Column(Text)
    theories = Column(Text)  # JSON array of theory_ids
    hypothesis_id = Column(Text, ForeignKey("hypotheses.id"))
    status = Column(Text, nullable=False, server_default="queued")
    incorporated_run_id = Column(Text, ForeignKey("runs.id"))
    created_at = Column(Text, server_default="(datetime('now'))")


class UserState(Base):
    __tablename__ = "user_state"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
