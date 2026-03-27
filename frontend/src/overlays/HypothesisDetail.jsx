import { useState, useEffect, useCallback } from 'react'
import StatusBadge from '../shared/StatusBadge'
import TheoryTag from '../shared/TheoryTag'
import { AssetTags } from '../shared/AssetTag'
import Sparkline from '../shared/Sparkline'
import { fmtConviction, fmtDate, convictionTier } from '../lib/format'
import { api } from '../lib/api'

/**
 * HypothesisDetail — full interrogation modal overlay.
 * 7 sections: Identity, Full Statement, Conviction Scoring,
 * Falsifier Health, Elimination Audit, Research Notes, Your Position.
 */
export default function HypothesisDetail({ hypothesis: h, onClose }) {
  const [showNoteInput, setShowNoteInput] = useState(false)
  const [noteText, setNoteText] = useState('')

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

  if (!h) return null

  const cm = h.conviction_math || {}
  const s1 = cm.stage1 || {}
  const s2 = cm.stage2 || {}
  const s3 = cm.stage3 || {}

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
            {!showNoteInput && (
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

        {/* G. Your Position (conditional) */}
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
      </div>
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

function fmtScore(val) {
  if (val == null) return '--'
  return val.toFixed(2)
}

function fmtDiscount(val) {
  if (val == null) return '0.00'
  if (val === 0) return '0.00'
  return val.toFixed(2)
}
