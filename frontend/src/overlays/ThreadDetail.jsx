import { useState, useEffect, useCallback } from 'react'
import StatusBadge from '../shared/StatusBadge'
import TheoryTag from '../shared/TheoryTag'
import { AssetTags } from '../shared/AssetTag'
import Sparkline from '../shared/Sparkline'
import OutcomeBadge from '../shared/OutcomeBadge'
import FreshnessBadge from '../shared/FreshnessBadge'
import ThreadAgeBadge from '../shared/ThreadAgeBadge'
import LifecycleActionBadge from '../shared/LifecycleActionBadge'
import ThreadFlagsBadge from '../shared/ThreadFlagsBadge'
import FalsifierLifecycleBadge from '../shared/FalsifierLifecycleBadge'
import { fmtConviction, fmtDate, convictionTier } from '../lib/format'
import { computeFreshnessLabel, FRESHNESS_CLASS, FRESHNESS_ACTION, getRealizationCap } from '../lib/freshness'
import { api } from '../lib/api'
import { isStaticMode } from '../lib/snapshot'

/**
 * ThreadDetail -- full thread interrogation overlay.
 * Replaces HypothesisDetail for thread-centered navigation.
 *
 * Sections:
 *   A. Thread Identity (thread_id, age, lifecycle action, status)
 *   B. Full Statement (from latest instance)
 *   C. Conviction Scoring (3-stage math breakdown)
 *   D. Falsifier Health (with lifecycle badges: CLEAR/TRIGGERED/UNTESTABLE/STALE/ESCALATED_UNTESTABLE)
 *   D2. Sector Falsifier Audit (collapsible)
 *   D3. Emergent Risk (if filled)
 *   D4. Realization (payoff band, freshness)
 *   E. Elimination Audit
 *   F. Research Notes
 *   G. Outcome
 *   H. Linked Trades
 *   L. Lineage Panel (collapsible -- all instances in thread)
 */
export default function ThreadDetail({ thread: threadFromLedger, onClose }) {
  const [threadData, setThreadData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lineageOpen, setLineageOpen] = useState(false)
  const [expandedInstance, setExpandedInstance] = useState(null)
  const [showNoteInput, setShowNoteInput] = useState(false)
  const [noteText, setNoteText] = useState('')
  const [sectorAuditOpen, setSectorAuditOpen] = useState(false)
  const [trades, setTrades] = useState([])

  // Outcome tracking state
  const [showOutcomeForm, setShowOutcomeForm] = useState(false)
  const [outcomeStatus, setOutcomeStatus] = useState('')
  const [outcomeNotes, setOutcomeNotes] = useState('')
  const [outcomePnl, setOutcomePnl] = useState('')
  const [outcomeSaving, setOutcomeSaving] = useState(false)
  const [outcomeError, setOutcomeError] = useState(null)
  const [localOutcome, setLocalOutcome] = useState(null)
  const [entryPrices, setEntryPrices] = useState(null)

  const threadId = threadFromLedger?.thread_id

  // Fetch full thread detail
  useEffect(() => {
    if (!threadId) return
    setLoading(true)
    setError(null)
    api.get(`/api/threads/${threadId}`)
      .then(data => {
        setThreadData(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message || 'Failed to load thread')
        setLoading(false)
      })
  }, [threadId])

  // Fetch trades for latest instance
  useEffect(() => {
    if (!threadData?.latest?.id) return
    api.get(`/api/trades?hypothesis_id=${threadData.latest.id}`)
      .then(data => setTrades(data || []))
      .catch(() => {})
  }, [threadData?.latest?.id])

  // Fetch entry prices from run price snapshots
  useEffect(() => {
    if (!threadData?.latest?.run_id) return
    api.get(`/api/runs/${threadData.latest.run_id}/prices`)
      .then(data => setEntryPrices(data || null))
      .catch(() => setEntryPrices(null))
  }, [threadData?.latest?.run_id])

  // ESC to close
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdropClick = useCallback((e) => {
    if (e.target === e.currentTarget) onClose()
  }, [onClose])

  const handleAddNote = () => {
    if (!noteText.trim() || !threadData?.latest?.id) return
    api.post('/api/inbox', {
      content: noteText.trim(),
      hypothesis_id: threadData.latest.id,
    }).then(() => {
      setNoteText('')
      setShowNoteInput(false)
    }).catch(() => {})
  }

  const handleSaveOutcome = useCallback(() => {
    if (!outcomeStatus || !outcomeNotes.trim() || !threadData?.latest?.id) return
    setOutcomeSaving(true)
    setOutcomeError(null)
    const body = {
      outcome_status: outcomeStatus,
      outcome_notes: outcomeNotes.trim(),
    }
    if (outcomePnl !== '') {
      const parsed = parseFloat(outcomePnl)
      if (!isNaN(parsed)) body.outcome_pnl_pct = parsed
    }
    api.patch(`/api/hypotheses/${threadData.latest.id}/outcome`, body).then(updated => {
      setLocalOutcome({
        status: updated.outcome_status,
        date: updated.outcome_date,
        notes: updated.outcome_notes,
        pnl_pct: updated.outcome_pnl_pct,
      })
      setShowOutcomeForm(false)
      setOutcomeSaving(false)
    }).catch(err => {
      setOutcomeError(err.message || 'Failed to save outcome')
      setOutcomeSaving(false)
    })
  }, [threadData?.latest?.id, outcomeStatus, outcomeNotes, outcomePnl])

  if (!threadId) return null

  if (loading) {
    return (
      <div className="modal-backdrop" onClick={handleBackdropClick}>
        <div className="modal-panel">
          <button className="modal-close" onClick={onClose}>X</button>
          <div className="detail-section" style={{ textAlign: 'center', padding: '40px 0' }}>
            Loading thread detail...
          </div>
        </div>
      </div>
    )
  }

  if (error || !threadData) {
    return (
      <div className="modal-backdrop" onClick={handleBackdropClick}>
        <div className="modal-panel">
          <button className="modal-close" onClick={onClose}>X</button>
          <div className="detail-section" style={{ textAlign: 'center', padding: '40px 0' }}>
            {error || 'Thread not found.'}
          </div>
        </div>
      </div>
    )
  }

  const h = threadData.latest
  const cm = h.conviction_math || {}
  const s1 = cm.stage1 || {}
  const s2 = cm.stage2 || {}
  const s3 = cm.stage3 || {}

  const hasSectorAudit = h.sector_appendices_applied && h.sector_appendices_applied.length > 0

  // Resolve outcome: local override > latest instance data
  const outcome = localOutcome || (h.outcome_status ? {
    status: h.outcome_status,
    date: h.outcome_date,
    notes: h.outcome_notes,
    pnl_pct: h.outcome_pnl_pct,
  } : null)

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-panel">
        <button className="modal-close" onClick={onClose}>X</button>

        {/* A. Thread Identity */}
        <div className="detail-section">
          <div className="thread-detail-identity">
            <div className="thread-detail-identity__ids">
              <span className="detail-id">{threadData.thread_id}</span>
              <span className="thread-detail-identity__instance-id">{h.id}</span>
            </div>
            <div className="detail-name">{h.short_name}</div>
            <div className="detail-meta">
              <StatusBadge status={h.status} />
              <LifecycleActionBadge action={h.lifecycle_action} />
              <TheoryTag theoryId={threadData.source_theory} label={threadData.source_theory_label} />
              <span className="detail-timeframe">{h.timeframe}</span>
              <AssetTags assets={h.predicted_assets} directions={h.asset_direction} />
            </div>
            <div className="thread-detail-identity__meta-row">
              <ThreadAgeBadge
                days={threadData.thread_age_days}
                confirmationCount={threadData.confirmation_count}
              />
              <ThreadFlagsBadge
                staleCount={threadData.latest.soft_falsifiers?.filter(
                  sf => sf.staleness_flag === 'STALE' || sf.staleness_classification === 'STALE'
                ).length || 0}
                escalatedCount={threadData.latest.soft_falsifiers?.filter(
                  sf => sf.status === 'ESCALATED_UNTESTABLE'
                ).length || 0}
                hasEmergentRisk={!!h.emergent_risk_condition}
              />
              {threadData.thread_status === 'RETIRED' && (
                <span className="thread-detail-identity__retired">RETIRED</span>
              )}
              {threadData.renewed_from && (
                <span className="thread-detail-identity__renewed">
                  Renewed from {threadData.renewed_from}
                </span>
              )}
              <span className="thread-detail-identity__instances">
                {threadData.total_instances} instance{threadData.total_instances !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>

        {/* Lifecycle reasoning (if present) */}
        {h.lifecycle_reasoning && (
          <div className="detail-section thread-detail-reasoning">
            <div className="detail-section__title">Lifecycle Reasoning</div>
            <p className="detail-statement">{h.lifecycle_reasoning}</p>
          </div>
        )}

        {/* B. Full Statement */}
        <div className="detail-section">
          <div className="detail-section__title">Hypothesis</div>
          <p className="detail-statement">{h.full_statement}</p>
        </div>

        {/* C. Conviction Scoring */}
        <div className="detail-section">
          <div className="detail-section__title">Conviction Scoring</div>
          <div className="conviction-grid">
            {/* Stage 1: Raw */}
            <div className="conviction-stage">
              <div className="conviction-stage__title">Stage 1: Raw</div>
              <StageRow label="Support strength" value={fmtScore(s1.support_strength)} />
              <StageRow label="Evidence quality" value={fmtScore(s1.evidence_quality)} />
              <StageRow label="Convergence" value={fmtScore(s1.convergence)} />
              <StageRow label="Falsifier clarity" value={fmtScore(s1.falsifier_clarity)} />
              <div className="conviction-stage__total">
                <span className="conviction-stage__total-label">Raw</span>
                <span className="conviction-stage__total-value">
                  {fmtConviction(s1.raw)}
                </span>
              </div>
            </div>

            {/* Stage 2: Discounts */}
            <div className="conviction-stage">
              <div className="conviction-stage__title">Stage 2: Discounts</div>
              <StageRow
                label="D_f (falsifier)"
                value={fmtDiscount(s2.soft_falsifier_discount)}
                negative={s2.soft_falsifier_discount < 0}
              />
              {s2.untestable_discount != null && s2.untestable_discount !== 0 && (
                <StageRow
                  label="D_u (untestable)"
                  value={fmtDiscount(s2.untestable_discount)}
                  negative={s2.untestable_discount < 0}
                />
              )}
              <StageRow
                label="Overlap adj."
                value={s2.overlap_adjustment != null ? (s2.overlap_adjustment >= 0 ? '+' : '') + s2.overlap_adjustment.toFixed(2) : fmtDiscount(s2.overlap_penalty)}
                negative={(s2.overlap_adjustment != null ? s2.overlap_adjustment : s2.overlap_penalty) < 0}
              />
              <div className="conviction-stage__total">
                <span className="conviction-stage__total-label">Adjusted</span>
                <span className="conviction-stage__total-value">
                  {fmtConviction(s2.adjusted)}
                </span>
              </div>
            </div>

            {/* Stage 3: Gates */}
            <div className="conviction-stage">
              <div className="conviction-stage__title">Stage 3: Gates</div>
              <StageRow
                label="Horizon cap"
                value={s3.horizon_cap != null ? fmtConviction(s3.horizon_cap) : '---'}
                isNull={s3.horizon_cap == null}
                negative={s3.horizon_cap != null}
              />
              <StageRow
                label="Expression cap"
                value={s3.expression_cap != null ? fmtConviction(s3.expression_cap) : '---'}
                isNull={s3.expression_cap == null}
                negative={s3.expression_cap != null}
              />
              <StageRow
                label="Realization cap"
                value={s3.realization_cap != null ? fmtConviction(s3.realization_cap) : '---'}
                isNull={s3.realization_cap == null}
                negative={s3.realization_cap != null}
              />
              {s3.freshness_label && s3.realization_cap != null && (
                <div className="conviction-stage__annotation">
                  Cap from {s3.freshness_label} state
                </div>
              )}
              <div className="conviction-stage__total">
                <span className="conviction-stage__total-label">Final</span>
                <span className={`conviction-stage__total-value conviction-final ${convictionTier(s3.final)}`}>
                  {fmtConviction(s3.final)}
                </span>
              </div>
            </div>
          </div>

          {/* Conviction trail sparkline */}
          {threadData.conviction_history && threadData.conviction_history.length >= 2 && (
            <div className="conviction-trail">
              <span className="conviction-trail__label">Thread conviction trail</span>
              <Sparkline data={threadData.conviction_history} />
            </div>
          )}
        </div>

        {/* D. Falsifier Health */}
        <div className="detail-section">
          <div className="detail-section__title">Falsifier Health</div>

          {/* Hard falsifiers */}
          {h.hard_falsifiers && h.hard_falsifiers.length > 0 && (
            <ul className="falsifier-list" style={{ marginBottom: '12px' }}>
              {h.hard_falsifiers.map((f, i) => (
                <li key={i} className="falsifier-item">
                  <span className={`falsifier-dot falsifier-dot--${f.status === 'FAILED' ? 'failed' : 'passed'}`} />
                  <span className="falsifier-name">{f.condition}</span>
                  <span className={`status-badge status-badge--${f.status === 'FAILED' ? 'killed' : 'survived'}`}>
                    {f.status}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {/* Soft falsifiers with lifecycle badges */}
          {h.soft_falsifiers && h.soft_falsifiers.length > 0 && (
            <ul className="falsifier-list">
              {h.soft_falsifiers.map((f, i) => {
                const lifecycleStatus = resolveLifecycleStatus(f)
                return (
                  <li key={i} className="falsifier-item falsifier-item--v7">
                    <span className={`falsifier-dot falsifier-dot--${dotClass(f)}`} />
                    <span className="falsifier-name">{f.name}</span>
                    <span className="falsifier-item__badges">
                      <span className={`falsifier-severity falsifier-severity--${f.severity}`}>
                        {f.severity}
                      </span>
                      <FalsifierLifecycleBadge
                        status={lifecycleStatus}
                        consecutiveCount={f.untestable_consecutive || 0}
                      />
                    </span>
                    <span className="falsifier-metric">
                      {f.metric} / {f.threshold}
                    </span>
                    {/* Staleness reasoning (if STALE or TRIGGERED_BY_PASSAGE) */}
                    {f.staleness_reasoning && (
                      <div className="falsifier-item__staleness-note">
                        {f.staleness_reasoning}
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        {/* D2. Sector Falsifier Audit (collapsible, conditional) */}
        {hasSectorAudit && (
          <div className="detail-section">
            <button
              className="sector-audit__header"
              onClick={() => setSectorAuditOpen(o => !o)}
            >
              <span className="sector-audit__title">
                Sector Falsifier Audit
                <span className="sector-audit__sectors">
                  {h.sector_appendices_applied.map(s => s.display_name || s.sector_id || s).join(', ')}
                </span>
              </span>
              <span className="sector-audit__toggle">
                {sectorAuditOpen ? '\u2212' : '+'}
              </span>
            </button>

            {sectorAuditOpen && (
              <div className="sector-audit__content">
                {(h.sector_falsifier_audit || []).map((entry, i) => (
                  <div
                    key={entry.id || i}
                    className={`sector-audit__row ${sectorAuditRowClass(entry)}`}
                  >
                    <div className="sector-audit__row-header">
                      <span className={`sector-audit__dot sector-audit__dot--${sectorAuditRowClass(entry)}`} />
                      <span className="sector-audit__condition">{entry.condition}</span>
                      <span className="sector-audit__badges">
                        <span className={`sector-audit__badge sector-audit__badge--triggered-${entry.triggered?.toLowerCase()}`}>
                          {entry.triggered}
                        </span>
                        <span className={`sector-audit__badge sector-audit__badge--relevant-${(entry.relevant || 'na').toLowerCase().replace('/', '')}`}>
                          {entry.relevant}
                        </span>
                        {entry.triggered === 'YES' && entry.relevant === 'YES' && (
                          <span className={`falsifier-severity falsifier-severity--${entry.severity_applied}`}>
                            {entry.severity_applied}
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="sector-audit__row-detail">
                      <span className="sector-audit__metric-label">Metric value: </span>
                      <span className="sector-audit__metric-value">{entry.metric_value_found || '---'}</span>
                    </div>
                    {entry.reasoning && (
                      <div className="sector-audit__reasoning">{entry.reasoning}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* D3. Emergent Risk (conditional) */}
        {h.emergent_risk_condition && (
          <div className="detail-section thread-detail-emergent">
            <div className="detail-section__title">Emergent Risk</div>
            <div className="emergent-risk-card">
              <div className="emergent-risk-card__header">
                <span className={`falsifier-severity falsifier-severity--${h.emergent_risk_severity}`}>
                  {h.emergent_risk_severity}
                </span>
                <span className="emergent-risk-card__label">INJECTED BY EVALUATOR</span>
              </div>
              <div className="emergent-risk-card__condition">{h.emergent_risk_condition}</div>
              {h.emergent_risk_causal_chain && (
                <div className="emergent-risk-card__chain">{h.emergent_risk_causal_chain}</div>
              )}
            </div>
          </div>
        )}

        {/* D4. Realization */}
        <RealizationSection hypothesis={h} />

        {/* E. Elimination Audit */}
        <div className="detail-section">
          <div className="detail-section__title">Elimination Audit</div>
          <p className="elimination-text">
            {h.elimination_notes || 'No elimination notes recorded.'}
          </p>
        </div>

        {/* F. Research Notes */}
        <div className="detail-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span className="detail-section__title" style={{ margin: 0 }}>Research Notes</span>
            {!showNoteInput && !isStaticMode() && (
              <button className="research-notes__add" onClick={() => setShowNoteInput(true)}>
                + ADD NOTE
              </button>
            )}
          </div>

          {showNoteInput && (
            <div className="note-input">
              <textarea
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
                placeholder="Paste a link or write a note..."
                autoFocus
              />
              <div className="note-input__actions">
                <button className="btn" onClick={() => { setShowNoteInput(false); setNoteText('') }}>
                  CANCEL
                </button>
                <button className="btn btn--primary" onClick={handleAddNote}>
                  QUEUE FOR NEXT RUN
                </button>
              </div>
            </div>
          )}

          {h.research_notes && h.research_notes.length > 0 ? (
            h.research_notes.map(note => (
              <div key={note.id} className="research-note">
                <div className="research-note__date">{fmtDate(note.date)}</div>
                <div className="research-note__content">{note.content}</div>
                {note.source && (
                  <div className="research-note__source">{note.source}</div>
                )}
              </div>
            ))
          ) : (
            !showNoteInput && <div className="empty-state" style={{ padding: '12px 0' }}>No research notes yet.</div>
          )}
        </div>

        {/* G. Outcome */}
        <div className="detail-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span className="detail-section__title" style={{ margin: 0 }}>Outcome</span>
            {outcome ? (
              <OutcomeBadge status={outcome.status} size="large" />
            ) : (
              <span className="outcome-pending-label">PENDING</span>
            )}
          </div>

          {entryPrices?.prices && h.predicted_assets?.length > 0 && (
            <div className="outcome-entry-prices">
              <span className="outcome-entry-prices__label">
                Entry prices (run date {fmtDate(entryPrices.price_snapshot_date || h.generated_date)}):
              </span>
              <span className="outcome-entry-prices__values">
                {h.predicted_assets.map((ticker, i) => {
                  const p = entryPrices.prices[ticker]
                  return (
                    <span key={ticker} className="outcome-entry-price">
                      {i > 0 && <span className="outcome-entry-price__sep">|</span>}
                      {ticker}: {p ? `$${p.price.toFixed(2)}` : '---'}
                    </span>
                  )
                })}
              </span>
            </div>
          )}

          {outcome && (
            <div className="outcome-recorded">
              <div className="outcome-recorded__date">Recorded: {fmtDate(outcome.date)}</div>
              <div className="outcome-recorded__notes">{outcome.notes}</div>
              {outcome.pnl_pct != null && (
                <div className={`outcome-recorded__pnl ${outcome.pnl_pct >= 0 ? 'perf--positive' : 'perf--negative'}`}>
                  P&L: {outcome.pnl_pct >= 0 ? '+' : ''}{outcome.pnl_pct.toFixed(1)}%
                </div>
              )}
            </div>
          )}

          {!outcome && !showOutcomeForm && !isStaticMode() && (
            <button className="btn btn--primary" onClick={() => setShowOutcomeForm(true)}>
              MARK OUTCOME
            </button>
          )}

          {showOutcomeForm && (
            <div className="outcome-form">
              <div className="outcome-form__label">Status:</div>
              <div className="outcome-form__statuses">
                {['CORRECT', 'INCORRECT', 'PARTIAL', 'EXPIRED'].map(s => (
                  <button
                    key={s}
                    className={`btn outcome-form__status-btn ${outcomeStatus === s ? 'outcome-form__status-btn--active outcome-form__status-btn--' + s.toLowerCase() : ''}`}
                    onClick={() => setOutcomeStatus(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
              <div className="outcome-form__label">What happened:</div>
              <textarea
                className="outcome-form__notes"
                value={outcomeNotes}
                onChange={e => setOutcomeNotes(e.target.value)}
                placeholder="State why this verdict..."
                rows={3}
              />
              <div className="outcome-form__label">P&L % (optional):</div>
              <input
                className="outcome-form__pnl"
                type="number"
                step="0.1"
                value={outcomePnl}
                onChange={e => setOutcomePnl(e.target.value)}
                placeholder="e.g. 4.8 or -2.3"
              />
              {outcomeError && <div className="outcome-form__error">{outcomeError}</div>}
              <div className="outcome-form__actions">
                <button className="btn" onClick={() => { setShowOutcomeForm(false); setOutcomeError(null) }}>
                  CANCEL
                </button>
                <button
                  className="btn btn--primary"
                  onClick={handleSaveOutcome}
                  disabled={!outcomeStatus || !outcomeNotes.trim() || outcomeSaving}
                >
                  {outcomeSaving ? 'SAVING...' : 'SAVE'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* H. Linked Trades */}
        {trades.length > 0 && (
          <div className="detail-section">
            <div className="detail-section__title">Trades</div>
            {trades.map(t => {
              const isOpen = t.status === 'OPEN'
              const sign = t.direction === 'LONG' ? 1 : -1
              const refPrice = isOpen ? null : t.exit_price
              const pnl = refPrice != null ? (refPrice - t.entry_price) * t.shares * sign : null
              const pct = refPrice != null ? ((refPrice - t.entry_price) / t.entry_price) * sign * 100 : null
              const pnlClass = (pnl || 0) >= 0 ? 'perf--positive' : 'perf--negative'
              const entryDt = t.entry_date ? new Date(t.entry_date) : null
              const endDt = t.exit_date ? new Date(t.exit_date) : new Date()
              const days = entryDt ? Math.round((endDt - entryDt) / 86400000) : null
              return (
                <div key={t.id} className="detail-trade-card">
                  <div className="detail-trade-card__header">
                    <span className="detail-trade-card__id">{t.id}</span>
                    <span className="detail-trade-card__ticker">{t.ticker}</span>
                    <span className={`detail-trade-card__dir detail-trade-card__dir--${t.direction.toLowerCase()}`}>
                      {t.direction}
                    </span>
                    <span className={`detail-trade-card__status detail-trade-card__status--${t.status.toLowerCase()}`}>
                      {t.status}
                    </span>
                  </div>
                  <div className="detail-trade-card__meta">
                    <span>Entry: ${t.entry_price?.toFixed(2)}</span>
                    {!isOpen && t.exit_price != null && <span>Exit: ${t.exit_price.toFixed(2)}</span>}
                    {pnl != null ? (
                      <span className={pnlClass}>
                        {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} ({pct >= 0 ? '+' : ''}{pct.toFixed(2)}%)
                      </span>
                    ) : (
                      isOpen && <span className="detail-trade-card__open-note">Use Trades view to refresh prices</span>
                    )}
                    <span>{t.shares} shares</span>
                    {days != null && <span>{days}d</span>}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* L. Lineage Panel (collapsible) */}
        {threadData.instances && threadData.instances.length > 0 && (
          <div className="detail-section thread-detail-lineage">
            <button
              className="lineage-panel__header"
              onClick={() => setLineageOpen(o => !o)}
            >
              <span className="lineage-panel__title">
                Instance Lineage
                <span className="lineage-panel__count">{threadData.instances.length}</span>
              </span>
              <span className="lineage-panel__toggle">
                {lineageOpen ? '\u2212' : '+'}
              </span>
            </button>

            {lineageOpen && (
              <div className="lineage-panel__content">
                {threadData.instances.map((inst, idx) => {
                  const isLatest = idx === 0
                  const isExpanded = expandedInstance === inst.id
                  return (
                    <div
                      key={inst.id}
                      className={`lineage-instance ${isLatest ? 'lineage-instance--latest' : ''}`}
                    >
                      <button
                        className="lineage-instance__row"
                        onClick={() => setExpandedInstance(isExpanded ? null : inst.id)}
                      >
                        <span className="lineage-instance__date">{fmtDate(inst.generated_date)}</span>
                        <LifecycleActionBadge action={inst.lifecycle_action} />
                        <StatusBadge status={inst.status} />
                        <span className={`lineage-instance__conviction ${convictionTier(inst.conviction)}`}>
                          {fmtConviction(inst.conviction)}
                        </span>
                        <span className="lineage-instance__falsifiers">
                          {inst.falsifier_summary.triggered}/{inst.falsifier_summary.total}
                        </span>
                        {inst.has_emergent_risk && (
                          <span className="lineage-instance__emr">EMR</span>
                        )}
                        {isLatest && <span className="lineage-instance__current">CURRENT</span>}
                        <span className="lineage-instance__toggle">
                          {isExpanded ? '\u2212' : '+'}
                        </span>
                      </button>

                      {isExpanded && (
                        <div className="lineage-instance__detail">
                          <div className="lineage-instance__detail-row">
                            <span className="lineage-instance__detail-label">Instance ID</span>
                            <span className="lineage-instance__detail-value">{inst.id}</span>
                          </div>
                          <div className="lineage-instance__detail-row">
                            <span className="lineage-instance__detail-label">Run</span>
                            <span className="lineage-instance__detail-value">{inst.run_id}</span>
                          </div>
                          <div className="lineage-instance__detail-row">
                            <span className="lineage-instance__detail-label">Falsifiers</span>
                            <span className="lineage-instance__detail-value">
                              {inst.falsifier_summary.triggered} triggered / {inst.falsifier_summary.total} total
                              {inst.falsifier_summary.stale > 0 && ` | ${inst.falsifier_summary.stale} stale`}
                              {inst.falsifier_summary.escalated > 0 && ` | ${inst.falsifier_summary.escalated} escalated`}
                              {inst.falsifier_summary.untestable > 0 && ` | ${inst.falsifier_summary.untestable} untestable`}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}

                {/* RENEW link */}
                {threadData.renewed_from && (
                  <div className="lineage-panel__renew-link">
                    Renewed from thread {threadData.renewed_from}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}


// --- Sub-components ---

function RealizationSection({ hypothesis: h }) {
  const hasPayoffBand = h.predicted_magnitude_lower != null && h.predicted_magnitude_upper != null
  const hasRealization = h.expression_return != null

  if (!hasPayoffBand && !hasRealization) return null

  const freshnessLabel = computeFreshnessLabel(
    h.realization_vs_lower, h.realization_vs_upper, h.time_elapsed_pct
  )
  const freshCls = FRESHNESS_CLASS[freshnessLabel] || ''
  const actionHint = FRESHNESS_ACTION[freshnessLabel] || ''
  const realizationCap = getRealizationCap(freshnessLabel)

  const upperBound = h.predicted_magnitude_upper || 1
  const progressPct = hasRealization
    ? Math.max(0, Math.min(100, (h.expression_return / upperBound) * 100))
    : 0
  const lowerPct = hasPayoffBand
    ? (h.predicted_magnitude_lower / upperBound) * 100
    : 0

  return (
    <div className="detail-section">
      <div className="detail-section__title">Realization</div>

      {freshnessLabel !== 'INDETERMINATE' && (
        <div className="realization-freshness">
          <span className={`freshness-badge freshness-badge--large ${freshCls}`}>
            {freshnessLabel}
          </span>
          <span className="realization-freshness__action">{actionHint}</span>
        </div>
      )}

      {hasPayoffBand && (
        <div className="realization-band">
          <div className="realization-band__header">
            <span className="realization-band__label">Payoff band</span>
            <span className="realization-band__values">
              {(h.predicted_magnitude_lower * 100).toFixed(0)}% -- {(h.predicted_magnitude_upper * 100).toFixed(0)}%
            </span>
            {h.timeframe_end_date && (
              <span className="realization-band__end">
                through {fmtDate(h.timeframe_end_date)}
              </span>
            )}
          </div>

          {hasRealization && (
            <div className="realization-bar">
              <div className="realization-bar__track">
                <div
                  className="realization-bar__lower-mark"
                  style={{ left: `${lowerPct}%` }}
                  title={`Lower bound: ${(h.predicted_magnitude_lower * 100).toFixed(0)}%`}
                />
                <div
                  className={`realization-bar__fill ${h.expression_return < 0 ? 'realization-bar__fill--negative' : ''}`}
                  style={{ width: `${Math.abs(progressPct)}%` }}
                />
              </div>
              <div className="realization-bar__labels">
                <span>0%</span>
                <span>{(upperBound * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
        </div>
      )}

      {hasRealization && (
        <div className="realization-metrics">
          <div className="realization-metric">
            <span className="realization-metric__label">Expression return</span>
            <span className={`realization-metric__value ${h.expression_return >= 0 ? 'perf--positive' : 'perf--negative'}`}>
              {h.expression_return >= 0 ? '+' : ''}{(h.expression_return * 100).toFixed(1)}%
            </span>
          </div>
          {h.realization_vs_lower != null && (
            <div className="realization-metric">
              <span className="realization-metric__label">vs. lower bound</span>
              <span className="realization-metric__value">{(h.realization_vs_lower * 100).toFixed(0)}%</span>
            </div>
          )}
          {h.realization_vs_upper != null && (
            <div className="realization-metric">
              <span className="realization-metric__label">vs. upper bound</span>
              <span className="realization-metric__value">{(h.realization_vs_upper * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>
      )}

      {h.time_elapsed_pct != null && (
        <div className="realization-time">
          <span className="realization-time__label">Holding window elapsed</span>
          <div className="realization-time__bar">
            <div
              className="realization-time__fill"
              style={{ width: `${Math.min(100, h.time_elapsed_pct * 100)}%` }}
            />
          </div>
          <span className="realization-time__value">{(h.time_elapsed_pct * 100).toFixed(0)}%</span>
        </div>
      )}

      {realizationCap != null && (
        <div className="realization-cap-note">
          Realization cap: {realizationCap.toFixed(1)} ({freshnessLabel})
        </div>
      )}
    </div>
  )
}


function StageRow({ label, value, negative, isNull }) {
  let cls = 'conviction-stage__value'
  if (negative) cls += ' conviction-stage__value--negative'
  if (isNull) cls += ' conviction-stage__value--null'

  return (
    <div className="conviction-stage__row">
      <span className="conviction-stage__label">{label}</span>
      <span className={cls}>{value}</span>
    </div>
  )
}

function sectorAuditRowClass(entry) {
  if (entry.triggered !== 'YES') return 'clear'
  if (entry.relevant === 'YES') return 'threat'
  return 'present'
}

function fmtScore(val) {
  if (val == null) return '--'
  return val.toFixed(2)
}

function fmtDiscount(val) {
  if (val == null) return '0.00'
  if (val === 0) return '0.00'
  return val.toFixed(2)
}

/**
 * Resolve the display lifecycle status for a soft falsifier.
 * Priority: ESCALATED_UNTESTABLE > TRIGGERED_BY_PASSAGE > STALE > UNTESTABLE > TRIGGERED > CLEAR
 */
function resolveLifecycleStatus(f) {
  if (f.status === 'ESCALATED_UNTESTABLE') return 'ESCALATED_UNTESTABLE'
  if (f.staleness_flag === 'TRIGGERED_BY_PASSAGE' || f.staleness_classification === 'TRIGGERED_BY_PASSAGE') {
    return 'TRIGGERED_BY_PASSAGE'
  }
  if (f.staleness_flag === 'STALE' || f.staleness_classification === 'STALE') return 'STALE'
  if (f.status === 'UNTESTABLE') return 'UNTESTABLE'
  if (f.status === 'TRIGGERED') return 'TRIGGERED'
  return 'CLEAR'
}

/**
 * Compute dot color class for soft falsifier based on lifecycle status.
 */
function dotClass(f) {
  const status = resolveLifecycleStatus(f)
  if (status === 'TRIGGERED' || status === 'TRIGGERED_BY_PASSAGE' || status === 'ESCALATED_UNTESTABLE') {
    return 'triggered'
  }
  if (status === 'STALE') return 'stale'
  if (status === 'UNTESTABLE') return 'untestable'
  return 'clear'
}
