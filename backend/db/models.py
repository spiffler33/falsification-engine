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
    regime_flags_active = Column(Text)  # JSON array of active flag_ids at run time
    sector_appendices_loaded = Column(Text)  # JSON array of sector_ids injected into Pass 3
    briefing_snapshot = Column(Text)  # Full JSON of briefing packet at run time
    price_snapshot_date = Column(Text)  # ISO date when price snapshots were captured


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
    resolution_channel = Column(Text)  # One of 6 channel keys
    resolution_channel_original = Column(Text)  # If evaluator corrected the tag
    sector_appendices_applied = Column(Text)  # JSON array of sector_ids checked for this hypothesis
    elimination_notes = Column(Text)
    generated_date = Column(Text, nullable=False)
    created_at = Column(Text, server_default="(datetime('now'))")
    # Outcome tracking (walk-forward analysis)
    outcome_status = Column(Text)  # NULL | CORRECT | INCORRECT | PARTIAL | EXPIRED
    outcome_date = Column(Text)  # ISO date when outcome was recorded
    outcome_notes = Column(Text)  # Free text: what happened, why this verdict
    outcome_pnl_pct = Column(Float)  # Optional: % return from run date to outcome date

    # Realization engine (v6 Phase 1)
    predicted_magnitude_lower = Column(Float)  # e.g., 0.15 for 15%
    predicted_magnitude_upper = Column(Float)  # e.g., 0.30 for 30%
    timeframe_end_date = Column(Text)  # ISO date for payoff band end
    expression_return = Column(Float)  # Last computed expression-level return
    realization_vs_lower = Column(Float)  # expression_return / magnitude_lower
    realization_vs_upper = Column(Float)  # expression_return / magnitude_upper
    time_elapsed_pct = Column(Float)  # Fraction of holding window consumed


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


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Text, primary_key=True)  # "T-2026-001"
    hypothesis_id = Column(Text, ForeignKey("hypotheses.id"), nullable=False)
    run_id = Column(Text)  # pipeline run at entry
    newsletter_id = Column(Text, ForeignKey("newsletters.id"))  # originating newsletter

    # Primitives
    ticker = Column(Text, nullable=False)
    direction = Column(Text, nullable=False)  # "LONG" | "SHORT"
    entry_date = Column(Text, nullable=False)
    entry_price = Column(Float, nullable=False)
    shares = Column(Float, nullable=False)
    conviction_at_entry = Column(Float)

    # Exit (null until closed)
    exit_date = Column(Text)
    exit_price = Column(Float)
    exit_reason = Column(Text)  # hypothesis_killed | target_reached | stop_hit | manual | expired

    # Status
    status = Column(Text, nullable=False, server_default="OPEN")  # "OPEN" | "CLOSED"

    # Hypothesis snapshot at entry (denormalized for historical record)
    hypothesis_short_name = Column(Text)
    hypothesis_theory = Column(Text)
    hypothesis_status_at_entry = Column(Text)  # SURVIVED | WOUNDED

    created_at = Column(Text, server_default="(datetime('now'))")


class Newsletter(Base):
    __tablename__ = "newsletters"

    id = Column(Text, primary_key=True)  # "NL-2026-001"
    date = Column(Text, nullable=False)  # ISO date of import
    run_id = Column(Text, ForeignKey("runs.id"))
    content = Column(Text, nullable=False)  # full ASCII newsletter text
    trade_recommendations = Column(Text)  # JSON array of structured recs
    created_at = Column(Text, server_default="(datetime('now'))")


class PendingTradeAction(Base):
    __tablename__ = "pending_trade_actions"

    id = Column(Text, primary_key=True)  # "PTA-001"
    newsletter_id = Column(Text, ForeignKey("newsletters.id"), nullable=False)
    action_type = Column(Text, nullable=False)  # "OPEN" | "CLOSE" | "REDUCE"

    # For OPEN: new trade info (no FK — hypothesis may come from newsletter rec, not always in DB)
    hypothesis_id = Column(Text)
    ticker = Column(Text)
    direction = Column(Text)
    conviction = Column(Float)
    proposed_shares = Column(Float)
    proposed_price = Column(Float)

    # For CLOSE/REDUCE: existing trade reference
    existing_trade_id = Column(Text)
    reduce_to_shares = Column(Float)  # for REDUCE: new target share count

    # Status
    status = Column(Text, nullable=False, server_default="PENDING")
    executed_at = Column(Text)
    executed_price = Column(Float)

    created_at = Column(Text, server_default="(datetime('now'))")


class SectorFalsifierAudit(Base):
    __tablename__ = "sector_falsifier_audit"

    id = Column(Text, primary_key=True)
    hypothesis_id = Column(Text, ForeignKey("hypotheses.id"), nullable=False)
    sector_id = Column(Text, nullable=False)
    falsifier_id = Column(Text, nullable=False)
    metric_value_found = Column(Text)
    triggered = Column(Text, nullable=False)  # YES | NO
    relevant = Column(Text, nullable=False)  # YES | NO | N/A
    reasoning = Column(Text)
    severity_applied = Column(Text)  # minor | medium | major | NONE
    run_id = Column(Text, ForeignKey("runs.id"), nullable=False)
    created_at = Column(Text, server_default="(datetime('now'))")


class RunPriceSnapshot(Base):
    __tablename__ = "run_price_snapshots"

    run_id = Column(Text, ForeignKey("runs.id"), primary_key=True)
    ticker = Column(Text, primary_key=True)
    price = Column(Float, nullable=False)
    date = Column(Text, nullable=False)  # ISO date of the price
    source = Column(Text, nullable=False, server_default="yahoo_finance")


class UserState(Base):
    __tablename__ = "user_state"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
