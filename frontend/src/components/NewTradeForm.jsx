/**
 * NewTradeForm — modal for opening a new trade linked to a hypothesis.
 * Hypothesis selector auto-populates ticker options and direction.
 *
 * Depends on: GET /api/hypotheses
 */
import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'

export default function NewTradeForm({ onSubmit, onCancel }) {
  const [hypotheses, setHypotheses] = useState([])
  const [selectedHypId, setSelectedHypId] = useState('')
  const [selectedHyp, setSelectedHyp] = useState(null)
  const [ticker, setTicker] = useState('')
  const [direction, setDirection] = useState('LONG')
  const [entryPrice, setEntryPrice] = useState('')
  const [shares, setShares] = useState('')
  const [entryDate, setEntryDate] = useState(new Date().toISOString().slice(0, 10))

  useEffect(() => {
    api.get('/api/hypotheses').then(data => {
      const eligible = (data || []).filter(h =>
        h.status === 'SURVIVED' || h.status === 'WOUNDED'
      )
      setHypotheses(eligible)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedHypId) {
      setSelectedHyp(null)
      setTicker('')
      setDirection('LONG')
      return
    }
    const hyp = hypotheses.find(h => h.id === selectedHypId)
    setSelectedHyp(hyp || null)
    if (hyp) {
      const assets = hyp.predicted_assets || []
      const dirs = hyp.asset_direction || {}
      if (assets.length > 0) {
        setTicker(assets[0])
        setDirection(dirs[assets[0]] || 'LONG')
      }
    }
  }, [selectedHypId, hypotheses])

  const handleTickerChange = useCallback((t) => {
    setTicker(t)
    if (selectedHyp && selectedHyp.asset_direction) {
      setDirection(selectedHyp.asset_direction[t] || 'LONG')
    }
  }, [selectedHyp])

  const handleSubmit = useCallback((e) => {
    e.preventDefault()
    if (!selectedHypId || !ticker || !entryPrice || !shares) return
    onSubmit({
      hypothesis_id: selectedHypId,
      ticker,
      direction,
      entry_price: parseFloat(entryPrice),
      shares: parseFloat(shares),
      entry_date: entryDate,
    })
  }, [selectedHypId, ticker, direction, entryPrice, shares, entryDate, onSubmit])

  // ESC to close
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onCancel])

  const handleBackdropClick = useCallback((e) => {
    if (e.target === e.currentTarget) onCancel()
  }, [onCancel])

  const notional = entryPrice && shares
    ? (parseFloat(entryPrice) * parseFloat(shares)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : null

  const assets = selectedHyp?.predicted_assets || []

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-panel modal-panel--form">
        <button className="modal-close" onClick={onCancel}>X</button>
        <div className="detail-section__title" style={{ marginBottom: '20px' }}>New Trade</div>

        <form onSubmit={handleSubmit} className="trade-form">
          {/* Hypothesis selector */}
          <label className="trade-form__label">
            Hypothesis
            <select
              value={selectedHypId}
              onChange={e => setSelectedHypId(e.target.value)}
              className="trade-form__select"
            >
              <option value="">-- Select hypothesis --</option>
              {hypotheses.map(h => (
                <option key={h.id} value={h.id}>
                  {h.id} -- {h.short_name} (conv: {h.conviction}, {h.status})
                </option>
              ))}
            </select>
          </label>

          {selectedHyp && (
            <div className="trade-form__hyp-info">
              <span className="trade-form__hyp-theory">{selectedHyp.source_theory}</span>
              <span className="trade-form__hyp-status">{selectedHyp.status}</span>
              <span className="trade-form__hyp-conv">Conviction: {selectedHyp.conviction}</span>
            </div>
          )}

          {/* Ticker */}
          <label className="trade-form__label">
            Ticker
            {assets.length > 0 ? (
              <select
                value={ticker}
                onChange={e => handleTickerChange(e.target.value)}
                className="trade-form__select"
              >
                {assets.map(a => (
                  <option key={a} value={a}>
                    {a} ({selectedHyp?.asset_direction?.[a] || 'LONG'})
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={ticker}
                onChange={e => setTicker(e.target.value.toUpperCase())}
                className="trade-form__input"
                placeholder="e.g. GLD"
              />
            )}
          </label>

          {/* Direction */}
          <label className="trade-form__label">
            Direction
            <select
              value={direction}
              onChange={e => setDirection(e.target.value)}
              className="trade-form__select"
            >
              <option value="LONG">LONG</option>
              <option value="SHORT">SHORT</option>
            </select>
          </label>

          {/* Entry price */}
          <label className="trade-form__label">
            Entry Price
            <input
              type="number"
              step="0.01"
              value={entryPrice}
              onChange={e => setEntryPrice(e.target.value)}
              className="trade-form__input"
              placeholder="295.40"
            />
          </label>

          {/* Shares */}
          <label className="trade-form__label">
            Shares
            <input
              type="number"
              step="1"
              value={shares}
              onChange={e => setShares(e.target.value)}
              className="trade-form__input"
              placeholder="100"
            />
          </label>

          {/* Entry date */}
          <label className="trade-form__label">
            Entry Date
            <input
              type="date"
              value={entryDate}
              onChange={e => setEntryDate(e.target.value)}
              className="trade-form__input"
            />
          </label>

          {/* Notional preview */}
          {notional && (
            <div className="trade-form__notional">
              Notional: ${notional}
            </div>
          )}

          <div className="trade-form__actions">
            <button type="button" className="btn" onClick={onCancel}>CANCEL</button>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={!selectedHypId || !ticker || !entryPrice || !shares}
            >
              OPEN TRADE
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
