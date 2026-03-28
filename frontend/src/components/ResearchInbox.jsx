/**
 * ResearchInbox — lightweight input for capturing research notes and links.
 * Extremely low friction: text input + ADD button.
 * Optional theory tagging after adding.
 *
 * Depends on: GET /api/inbox, POST /api/inbox
 */
import { useState, useCallback } from 'react'
import { api } from '../lib/api'
import { isStaticMode } from '../lib/snapshot'
import { fmtDate, shortTheory } from '../lib/format'

const THEORY_IDS = [
  'valuation_mean_reversion',
  'debt_cycle_short',
  'debt_cycle_long',
  'structural_fragility',
  'fiscal_dominance_liquidity',
  'fiscal_dominance_arithmetic',
  'capital_flows',
  'monetary_architecture',
]

export default function ResearchInbox({ items, onRefetch }) {
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const queuedCount = (items || []).filter(i => i.status === 'queued').length

  const handleAdd = useCallback(async () => {
    if (!content.trim()) return
    setSubmitting(true)
    try {
      const type = content.trim().startsWith('http') ? 'link' : 'note'
      await api.post('/api/inbox', { content: content.trim(), type })
      setContent('')
      if (onRefetch) onRefetch()
    } catch (err) {
      console.error('Failed to add inbox item:', err)
    } finally {
      setSubmitting(false)
    }
  }, [content, onRefetch])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleAdd()
    }
  }, [handleAdd])

  const statusClass = (status) => {
    if (status === 'queued') return 'inbox-item__status--queued'
    return 'inbox-item__status--incorporated'
  }

  return (
    <div className="research-inbox">
      <div className="research-inbox__header">
        <h3>Research Inbox</h3>
        <span className="research-inbox__count">
          {queuedCount} queued for next run
        </span>
      </div>

      {!isStaticMode() && (
        <div className="research-inbox__input-row">
          <input
            className="research-inbox__input"
            type="text"
            placeholder="paste a link or write a note..."
            value={content}
            onChange={e => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={submitting}
          />
          <button
            className="btn btn--primary research-inbox__add"
            onClick={handleAdd}
            disabled={!content.trim() || submitting}
          >
            ADD
          </button>
        </div>
      )}

      <div className="research-inbox__list">
        {(items || []).map(item => (
          <div key={item.id} className="inbox-item">
            <span className="inbox-item__date">{fmtDate(item.date)}</span>
            <span className="inbox-item__content">
              {item.type === 'link' ? (
                <span className="inbox-item__link">{item.content}</span>
              ) : (
                item.content
              )}
            </span>
            {item.source && (
              <span className="inbox-item__source">{item.source}</span>
            )}
            {item.theories && item.theories.length > 0 && (
              <span className="inbox-item__theories">
                {item.theories.map(t => (
                  <span key={t} className="theory-tag">{shortTheory(t)}</span>
                ))}
              </span>
            )}
            <span className={`inbox-item__status ${statusClass(item.status)}`}>
              {(item.status || '').toUpperCase()}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
