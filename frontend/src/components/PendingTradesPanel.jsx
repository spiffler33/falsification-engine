/**
 * PendingTradesPanel -- Displays pending trade actions from newsletter import.
 * User reviews each action (OPEN/CLOSE/REDUCE) and signs off to execute.
 *
 * Depends on: GET /api/trades/pending, POST /api/trades/signoff
 */
import { useState, useCallback, useMemo } from 'react'
import { api } from '../lib/api'

const ACTION_LABELS = {
  OPEN: 'OPEN',
  CLOSE: 'CLOSE',
  REDUCE: 'REDUCE',
}

export default function PendingTradesPanel({ pendingActions, onSignoffComplete }) {
  const [approvals, setApprovals] = useState(() => {
    const init = {}
    for (const a of (pendingActions || [])) {
      init[a.id] = true  // default: all approved
    }
    return init
  })
  const [signing, setSigning] = useState(false)
  const [error, setError] = useState(null)

  const toggleApproval = useCallback((id) => {
    setApprovals(prev => ({ ...prev, [id]: !prev[id] }))
  }, [])

  const approvedCount = useMemo(() => {
    return Object.values(approvals).filter(Boolean).length
  }, [approvals])

  const handleSignoff = useCallback(async () => {
    setSigning(true)
    setError(null)
    try {
      const actions = Object.entries(approvals).map(([id, approved]) => ({
        pending_action_id: id,
        approved,
      }))
      await api.post('/api/trades/signoff', { actions })
      if (onSignoffComplete) onSignoffComplete()
    } catch (err) {
      setError(err.message || 'Signoff failed')
    } finally {
      setSigning(false)
    }
  }, [approvals, onSignoffComplete])

  const handleRejectAll = useCallback(async () => {
    setSigning(true)
    setError(null)
    try {
      const actions = (pendingActions || []).map(a => ({
        pending_action_id: a.id,
        approved: false,
      }))
      await api.post('/api/trades/signoff', { actions })
      if (onSignoffComplete) onSignoffComplete()
    } catch (err) {
      setError(err.message || 'Reject failed')
    } finally {
      setSigning(false)
    }
  }, [pendingActions, onSignoffComplete])

  if (!pendingActions || pendingActions.length === 0) return null

  return (
    <div className="pending-trades">
      <div className="pending-trades__header">
        <h3>Pending Trade Actions</h3>
        <span className="pending-trades__count">
          {pendingActions.length} action{pendingActions.length !== 1 ? 's' : ''} from newsletter
        </span>
      </div>

      {error && (
        <div className="pending-trades__error">{error}</div>
      )}

      <div className="trades-table-wrap">
        <table className="trades-table">
          <thead>
            <tr>
              <th></th>
              <th>Action</th>
              <th>Ticker</th>
              <th>Dir</th>
              <th className="trades-table__num">Conv</th>
              <th className="trades-table__num">Shares</th>
              <th className="trades-table__num">Price</th>
              <th className="trades-table__num">Notional</th>
              <th>Hyp</th>
            </tr>
          </thead>
          <tbody>
            {pendingActions.map(a => {
              const notional = (a.proposed_shares || 0) * (a.proposed_price || 0)
              return (
                <tr key={a.id} className={`trades-table__row ${!approvals[a.id] ? 'trades-table__row--rejected' : ''}`}>
                  <td>
                    <input
                      type="checkbox"
                      checked={approvals[a.id] || false}
                      onChange={() => toggleApproval(a.id)}
                    />
                  </td>
                  <td>
                    <span className={`pending-trades__action pending-trades__action--${a.action_type.toLowerCase()}`}>
                      {ACTION_LABELS[a.action_type] || a.action_type}
                    </span>
                  </td>
                  <td className="trades-table__ticker">{a.ticker}</td>
                  <td className={`trades-table__dir trades-table__dir--${(a.direction || '').toLowerCase()}`}>
                    {a.direction}
                  </td>
                  <td className="trades-table__num trades-table__conviction">{a.conviction}</td>
                  <td className="trades-table__num">
                    {a.action_type === 'REDUCE'
                      ? `${a.reduce_to_shares} (from current)`
                      : a.proposed_shares}
                  </td>
                  <td className="trades-table__num">
                    {a.proposed_price ? `$${a.proposed_price.toFixed(2)}` : '---'}
                  </td>
                  <td className="trades-table__num">
                    {notional > 0 ? `$${notional.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '---'}
                  </td>
                  <td className="pending-trades__hyp">{a.hypothesis_id}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="pending-trades__actions">
        <button
          className="btn btn--primary"
          onClick={handleSignoff}
          disabled={signing || approvedCount === 0}
        >
          {signing ? 'EXECUTING...' : `SIGN OFF (${approvedCount})`}
        </button>
        <button
          className="btn"
          onClick={handleRejectAll}
          disabled={signing}
        >
          REJECT ALL
        </button>
      </div>
    </div>
  )
}
