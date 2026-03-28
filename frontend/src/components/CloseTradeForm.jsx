/**
 * CloseTradeForm — modal for closing an open trade.
 * Records exit price, date, and reason.
 */
import { useState, useEffect, useCallback } from 'react'

const EXIT_REASONS = [
  { value: 'manual', label: 'Manual close' },
  { value: 'hypothesis_killed', label: 'Hypothesis killed' },
  { value: 'target_reached', label: 'Target reached' },
  { value: 'stop_hit', label: 'Stop hit' },
  { value: 'expired', label: 'Expired / timeframe ended' },
]

export default function CloseTradeForm({ trade, onSubmit, onCancel }) {
  const [exitPrice, setExitPrice] = useState('')
  const [exitDate, setExitDate] = useState(new Date().toISOString().slice(0, 10))
  const [exitReason, setExitReason] = useState('manual')

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onCancel])

  const handleBackdropClick = useCallback((e) => {
    if (e.target === e.currentTarget) onCancel()
  }, [onCancel])

  const handleSubmit = useCallback((e) => {
    e.preventDefault()
    if (!exitPrice) return
    onSubmit({
      id: trade.id,
      exit_price: parseFloat(exitPrice),
      exit_date: exitDate,
      exit_reason: exitReason,
    })
  }, [trade.id, exitPrice, exitDate, exitReason, onSubmit])

  const dirSign = trade.direction === 'LONG' ? 1 : -1
  const previewPnl = exitPrice
    ? ((parseFloat(exitPrice) - trade.entry_price) * trade.shares * dirSign)
    : null
  const previewPct = exitPrice
    ? ((parseFloat(exitPrice) - trade.entry_price) / trade.entry_price * dirSign * 100)
    : null

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-panel modal-panel--form">
        <button className="modal-close" onClick={onCancel}>X</button>
        <div className="detail-section__title" style={{ marginBottom: '20px' }}>
          Close Trade: {trade.ticker} {trade.direction}
        </div>

        <div className="trade-form__hyp-info" style={{ marginBottom: '16px' }}>
          <span>Entry: ${trade.entry_price?.toFixed(2)}</span>
          <span>{trade.shares} shares</span>
          <span>{trade.hypothesis_id}</span>
        </div>

        <form onSubmit={handleSubmit} className="trade-form">
          <label className="trade-form__label">
            Exit Price
            <input
              type="number"
              step="0.01"
              value={exitPrice}
              onChange={e => setExitPrice(e.target.value)}
              className="trade-form__input"
              autoFocus
            />
          </label>

          <label className="trade-form__label">
            Exit Date
            <input
              type="date"
              value={exitDate}
              onChange={e => setExitDate(e.target.value)}
              className="trade-form__input"
            />
          </label>

          <label className="trade-form__label">
            Reason
            <select
              value={exitReason}
              onChange={e => setExitReason(e.target.value)}
              className="trade-form__select"
            >
              {EXIT_REASONS.map(r => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </label>

          {previewPnl != null && (
            <div className={`trade-form__preview ${previewPnl >= 0 ? 'perf--positive' : 'perf--negative'}`}>
              P&L: {previewPnl >= 0 ? '+' : ''}${previewPnl.toFixed(2)}
              {' '}({previewPct >= 0 ? '+' : ''}{previewPct.toFixed(2)}%)
            </div>
          )}

          <div className="trade-form__actions">
            <button type="button" className="btn" onClick={onCancel}>CANCEL</button>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={!exitPrice}
            >
              CLOSE TRADE
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
