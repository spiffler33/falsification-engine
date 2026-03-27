/**
 * JournalForm — overlay form for recording a new action or closing a position.
 * When creating: user selects hypothesis, fills action, size, reasoning.
 * When closing: user fills outcome text and date.
 */
import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { fmtDate } from '../lib/format'

export default function JournalForm({ mode, entry, onSubmit, onCancel }) {
  // mode: 'create' | 'close'
  const { data: hypotheses } = useApi(mode === 'create' ? '/api/hypotheses?status=SURVIVED&status=WOUNDED' : null)

  const [hypothesisId, setHypothesisId] = useState(entry?.hypothesis_id || '')
  const [action, setAction] = useState('')
  const [size, setSize] = useState('')
  const [reasoning, setReasoning] = useState('')
  const [outcome, setOutcome] = useState(entry?.outcome || '')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (entry?.hypothesis_id) setHypothesisId(entry.hypothesis_id)
  }, [entry])

  function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)

    if (mode === 'close') {
      onSubmit({
        id: entry.id,
        outcome,
        closed_date: new Date().toISOString().slice(0, 10),
        status: 'CLOSED',
      })
    } else {
      onSubmit({
        hypothesis_id: hypothesisId,
        action,
        size: size || null,
        reasoning,
        date: new Date().toISOString().slice(0, 10),
      })
    }
  }

  const isCreateValid = hypothesisId && action.trim() && reasoning.trim()
  const isCloseValid = outcome.trim()
  const isValid = mode === 'close' ? isCloseValid : isCreateValid

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-panel journal-form" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onCancel}>x</button>
        <h3 className="journal-form__title">
          {mode === 'close' ? 'Close Position' : 'Record Action'}
        </h3>

        <form onSubmit={handleSubmit}>
          {mode === 'create' && (
            <>
              <div className="journal-form__field">
                <label className="journal-form__label">Hypothesis</label>
                <select
                  className="journal-form__select"
                  value={hypothesisId}
                  onChange={e => setHypothesisId(e.target.value)}
                >
                  <option value="">Select a hypothesis...</option>
                  {(hypotheses || []).map(h => (
                    <option key={h.id} value={h.id}>{h.short_name}</option>
                  ))}
                </select>
              </div>

              <div className="journal-form__field">
                <label className="journal-form__label">Action</label>
                <input
                  className="journal-form__input"
                  type="text"
                  placeholder='e.g., "LONG GLD", "SHORT HYG", "NO ACTION -- watching"'
                  value={action}
                  onChange={e => setAction(e.target.value)}
                />
              </div>

              <div className="journal-form__field">
                <label className="journal-form__label">Size (optional)</label>
                <input
                  className="journal-form__input"
                  type="text"
                  placeholder="e.g., 8%"
                  value={size}
                  onChange={e => setSize(e.target.value)}
                />
              </div>

              <div className="journal-form__field">
                <label className="journal-form__label">Reasoning</label>
                <textarea
                  className="journal-form__textarea"
                  placeholder="Why are you taking this action (or choosing not to)?"
                  value={reasoning}
                  onChange={e => setReasoning(e.target.value)}
                  rows={4}
                />
              </div>
            </>
          )}

          {mode === 'close' && (
            <>
              <div className="journal-form__context">
                <span className="journal-form__context-label">Closing: </span>
                {entry?.action}
                <span className="journal-form__context-date"> ({fmtDate(entry?.date)})</span>
              </div>
              <div className="journal-form__field">
                <label className="journal-form__label">Outcome</label>
                <textarea
                  className="journal-form__textarea"
                  placeholder="What happened? What was learned?"
                  value={outcome}
                  onChange={e => setOutcome(e.target.value)}
                  rows={4}
                />
              </div>
            </>
          )}

          <div className="journal-form__actions">
            <button type="button" className="btn" onClick={onCancel}>CANCEL</button>
            <button type="submit" className="btn btn--primary" disabled={!isValid || submitting}>
              {mode === 'close' ? 'CLOSE POSITION' : 'RECORD'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
