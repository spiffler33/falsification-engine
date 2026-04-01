import { useState, useEffect, useCallback } from 'react'
import StatusBadge from '../shared/StatusBadge'
import TheoryTag from '../shared/TheoryTag'
import { AssetTags } from '../shared/AssetTag'
import Sparkline from '../shared/Sparkline'
import OutcomeBadge from '../shared/OutcomeBadge'
import { fmtConviction, fmtDate, convictionTier } from '../lib/format'
import { computeFreshnessLabel, FRESHNESS_CLASS, FRESHNESS_ACTION, getRealizationCap } from '../lib/freshness'
import { api } from '../lib/api'
import { isStaticMode } from '../lib/snapshot'

/**
 * HypothesisDetail — full interrogation modal overlay.
 * 7 sections: Identity, Full Statement, Conviction Scoring,
 * Falsifier Health, Elimination Audit, Research Notes, Your Position.
 */
export default function HypothesisDetail({ hypothesis: h, onClose }) {
  const [showNoteInput, setShowNoteInput] = useState(false)
  const [noteText, setNoteText] = useState('')
  const [trades, setTrades] = useState([])

  // Fetch trades linked to this hypothesis
  useEffect(() => {
    if (h?.id) {
      api.get(`/api/trades?hypothesis_id=${h.id}`).then(data => {
        setTrades(data || [])
      }).catch(() => {})
    }
  }, [h?.id])

  // ESC to close
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  // Click backdrop to close
  const handleBackdropClick = useCallback((e) => {
    if (e.target === e.currentTarget) onClose()
  }, [onClose])

  const handleAddNote = () => {
    if (!noteText.trim()) return
    api.post('/api/inbox', {
      content: noteText.trim(),
      hypothesis_id: h.id,
    }).then(() => {
      setNoteText('')
      setShowNoteInput(false)
    }).catch(() => {})
  }

  const [sectorAuditOpen, setSectorAuditOpen] = useState(false)

  // Outcome tracking state
  const [entryPrices, setEntryPrices] = useState(null)
  const [showOutcomeForm, setShowOutcomeForm] = useState(false)
  const [outcomeStatus, setOutcomeStatus] = useState('')
  const [outcomeNotes, setOutcomeNotes] = useState('')
  const [outcomePnl, setOutcomePnl] = useState('')
  const [outcomeSaving, setOutcomeSaving] = useState(false)
  const [outcomeError, setOutcomeError] = useState(null)
  // Local outcome state (so we don't need to re-fetch the whole hypothesis)
  const [localOutcome, setLocalOutcome] = useState(null)

  // Fetch entry prices from run price snapshots
  useEffect(() => {
    if (h?.run_id) {
      api.get(`/api/runs/${h.run_id}/prices`).then(data => {
        setEntryPrices(data || null)
      }).catch(() => setEntryPrices(null))
    }
  }, [h?.run_id])

  const handleSaveOutcome = useCallback(() => {
    if (!outcomeStatus || !outcomeNotes.trim()) return
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
    api.patch(`/api/hypotheses/${h.id}/outcome`, body).then(updated => {
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
  }, [h?.id, outcomeStatus, outcomeNotes, outcomePnl])

  if (!h) return null

  // Resolve outcome: local override > hypothesis data
  const outcome = localOutcome || (h.outcome_status ? {
    status: h.outcome_status,
    date: h.outcome_date,
    notes: h.outcome_notes,
    pnl_pct: h.outcome_pnl_pct,
  } : null)

  const cm = h.conviction_math || {}
  const s1 = cm.stage1 || {}
  const s2 = cm.stage2 || {}
  const s3 = cm.stage3 || {}

  const hasSectorAudit =
    h.sector_appendices_applied && h.sector_appendices_applied.length > 0

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-panel">
        <button className="modal-close" onClick={onClose}>X</button>

        {/* A. Identity */}
        <div className="detail-section">
          <div className="detail-id">{h.id}</div>
          <div className="detail-name">{h.short_name}</div>
          <div className="detail-meta">
            <StatusBadge status={h.status} />
            <TheoryTag theoryId={h.source_theory} label={h.source_theory_label} />
            <span className="detail-timeframe">{h.timeframe}</span>
            <AssetTags assets={h.predicted_assets} directions={h.asset_direction} />
          </div>
        </div>

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
                label="Soft falsifier"
                value={fmtDiscount(s2.soft_falsifier_discount)}
                negative={s2.soft_falsifier_discount < 0}
              />
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
          {h.conviction_history && h.conviction_history.length >= 2 && (
            <div className="conviction-trail">
              <span className="conviction-trail__label">90-day trail</span>
              <Sparkline data={h.conviction_history} />
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

          {/* Soft falsifiers */}
          {h.soft_falsifiers && h.soft_falsifiers.length > 0 && (
            <ul className="falsifier-list">
              {h.soft_falsifiers.map((f, i) => (
                <li key={i} className="falsifier-item">
                  <span className={`falsifier-dot falsifier-dot--${f.status === 'TRIGGERED' ? 'triggered' : 'clear'}`} />
                  <span className="falsifier-name">{f.name}</span>
                  <span className={`falsifier-severity falsifier-severity--${f.severity}`}>
                    {f.severity}
                  </span>
                  <span className="falsifier-metric">
                    {f.metric} / {f.threshold}
                  </span>
                </li>
              ))}
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

        {/* D3. Realization — payoff band progress, freshness label */}
        <RealizationSection hypothesis={h} />

        {/* D4. Continuation Lineage (conditional) */}
        {h.continuation_of && (
          <div className="detail-section">
            <div className="detail-section__title">Continuation Lineage</div>
            <div className="continuation-lineage">
              <div className="continuation-lineage__parent">
                Continues{' '}
                <span className="continuation-lineage__id">{h.continuation_of}</span>
                <span className="continuation-lineage__gen">Gen {h.continuation_generation || 2}</span>
              </div>
              {h.continuation_justification && (
                <div className="continuation-lineage__justification">
                  {h.continuation_justification}
                </div>
              )}
            </div>
          </div>
        )}

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

        {/* G. Outcome (walk-forward tracking) */}
        <div className="detail-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span className="detail-section__title" style={{ margin: 0 }}>Outcome</span>
            {outcome ? (
              <OutcomeBadge status={outcome.status} size="large" />
            ) : (
              <span className="outcome-pending-label">PENDING</span>
            )}
          </div>

          {/* Entry prices */}
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

          {/* Recorded outcome display */}
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

          {/* Mark outcome button / form */}
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

        {/* H. Your Position (conditional — legacy journal-based) */}
        {h.has_action && h.position && (
          <div className="detail-section">
            <div className="detail-section__title">Your Position</div>
            <div className="position-card">
              <div className="position-card__action">{h.position.action}</div>
              <div className="position-card__meta">
                <span className="position-card__field">
                  <span className="position-card__field-label">Date: </span>
                  {fmtDate(h.position.date)}
                </span>
                {h.position.size && (
                  <span className="position-card__field">
                    <span className="position-card__field-label">Size: </span>
                    {h.position.size}
                  </span>
                )}
                <span className="position-card__field">
                  <span className="position-card__field-label">Entry conv: </span>
                  {fmtConviction(h.position.conviction_at_entry)}
                </span>
                <span className="position-card__field">
                  <span className="position-card__field-label">Current: </span>
                  {fmtConviction(h.conviction)}
                </span>
                <span className={`position-card__status position-card__status--${(h.position.status || 'open').toLowerCase()}`}>
                  {h.position.status || 'OPEN'}
                </span>
              </div>
            </div>
          </div>
        )}

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
      </div>
    </div>
  )
}

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

  // Progress bar position: where expression_return sits relative to the band
  // 0% = 0 return, 100% = upper bound. Lower bound is marked along the way.
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

      {/* Freshness label + action hint */}
      {freshnessLabel !== 'INDETERMINATE' && (
        <div className="realization-freshness">
          <span className={`freshness-badge freshness-badge--large ${freshCls}`}>
            {freshnessLabel}
          </span>
          <span className="realization-freshness__action">{actionHint}</span>
        </div>
      )}

      {/* Payoff band */}
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

          {/* Progress bar */}
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

      {/* Expression return */}
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

      {/* Time elapsed */}
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

      {/* Realization cap annotation */}
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
