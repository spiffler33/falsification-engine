/**
 * NewsletterList -- Scrollable index of stored newsletters.
 * Click to expand full text in a <pre> block.
 *
 * Depends on: GET /api/newsletters, GET /api/newsletters/:id
 */
import { useState, useCallback } from 'react'
import { api } from '../lib/api'
import { fmtDate } from '../lib/format'

export default function NewsletterList({ newsletters, onRefetch }) {
  const [expandedId, setExpandedId] = useState(null)
  const [expandedContent, setExpandedContent] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const handleToggle = useCallback(async (nl) => {
    if (expandedId === nl.id) {
      setExpandedId(null)
      setExpandedContent(null)
      return
    }

    setExpandedId(nl.id)
    setLoadingDetail(true)
    try {
      const detail = await api.get(`/api/newsletters/${nl.id}`)
      setExpandedContent(detail)
    } catch {
      setExpandedContent(null)
    } finally {
      setLoadingDetail(false)
    }
  }, [expandedId])

  if (!newsletters || newsletters.length === 0) {
    return (
      <div className="newsletter-list__empty">
        No newsletters yet. Generate one from high-conviction hypotheses.
      </div>
    )
  }

  return (
    <div className="newsletter-list">
      {newsletters.map(nl => (
        <div key={nl.id} className="newsletter-list__item">
          <button
            className={`newsletter-list__row ${expandedId === nl.id ? 'newsletter-list__row--expanded' : ''}`}
            onClick={() => handleToggle(nl)}
          >
            <span className="newsletter-list__date">{fmtDate(nl.date)}</span>
            <span className="newsletter-list__title">{nl.content}</span>
            <span className="newsletter-list__meta">
              {nl.trade_count > 0 && (
                <span className="newsletter-list__trade-count">
                  {nl.trade_count} trade{nl.trade_count !== 1 ? 's' : ''}
                </span>
              )}
              <span className="newsletter-list__id">{nl.id}</span>
            </span>
          </button>

          {expandedId === nl.id && (
            <div className="newsletter-list__detail">
              {loadingDetail ? (
                <div className="loading">Loading...</div>
              ) : expandedContent ? (
                <pre className="newsletter-list__content">
                  {expandedContent.content}
                </pre>
              ) : (
                <div className="empty-state">Failed to load newsletter.</div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
