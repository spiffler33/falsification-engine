/**
 * TradesView — Trade tracker linked to hypotheses.
 * Records live trades, tracks P&L, correlates conviction with outcomes.
 *
 * Depends on: GET /api/trades, POST /api/trades, PATCH /api/trades/:id,
 *             GET /api/trades/refresh, GET /api/trades/performance,
 *             GET /api/hypotheses?status=SURVIVED&status=WOUNDED
 */
import { useState, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import { fmtDate } from '../lib/format'
import NewTradeForm from '../components/NewTradeForm'
import CloseTradeForm from '../components/CloseTradeForm'

export default function TradesView({ onSelectHypothesis }) {
  const { data: trades, loading, error, refetch } = useApi('/api/trades')
  const { data: perf, refetch: refetchPerf } = useApi('/api/trades/performance')
  const [showNewForm, setShowNewForm] = useState(false)
  const [closingTrade, setClosingTrade] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const handleCreate = useCallback(async (data) => {
    try {
      await api.post('/api/trades', data)
      setShowNewForm(false)
      refetch()
      refetchPerf()
    } catch (err) {
      console.error('Failed to create trade:', err)
    }
  }, [refetch, refetchPerf])

  const handleClose = useCallback(async (data) => {
    try {
      await api.patch(`/api/trades/${data.id}`, {
        exit_price: data.exit_price,
        exit_date: data.exit_date,
        exit_reason: data.exit_reason,
      })
      setClosingTrade(null)
      refetch()
      refetchPerf()
    } catch (err) {
      console.error('Failed to close trade:', err)
    }
  }, [refetch, refetchPerf])

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await api.get('/api/trades/refresh')
      refetch()
      refetchPerf()
    } catch (err) {
      console.error('Failed to refresh prices:', err)
    } finally {
      setRefreshing(false)
    }
  }, [refetch, refetchPerf])

  const handleHypothesisClick = useCallback((hypothesisId) => {
    if (onSelectHypothesis && hypothesisId) {
      api.get(`/api/hypotheses/${hypothesisId}`).then(h => {
        onSelectHypothesis(h)
      }).catch(() => {})
    }
  }, [onSelectHypothesis])

  if (loading) return <div className="loading">Loading trades...</div>
  if (error) return <div className="empty-state">Failed to load trades.</div>

  const allTrades = trades || []
  const openTrades = allTrades.filter(t => t.status === 'OPEN')
  const closedTrades = allTrades.filter(t => t.status === 'CLOSED')

  return (
    <div className="trades-view">
      {/* Open Trades */}
      <div className="trades-view__header">
        <h2>Open Trades</h2>
        <div className="trades-view__actions">
          {openTrades.length > 0 && (
            <button
              className="btn"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              {refreshing ? 'REFRESHING...' : 'REFRESH PRICES'}
            </button>
          )}
          <button className="btn btn--primary" onClick={() => setShowNewForm(true)}>
            + NEW TRADE
          </button>
        </div>
      </div>

      {openTrades.length === 0 ? (
        <div className="empty-state">
          No open trades. Open a trade when you act on a hypothesis.
        </div>
      ) : (
        <table className="trades-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Dir</th>
              <th className="trades-table__num">Entry</th>
              <th className="trades-table__num">Current</th>
              <th className="trades-table__num">P&L</th>
              <th className="trades-table__num">%</th>
              <th className="trades-table__num">Days</th>
              <th className="trades-table__num">Conv</th>
              <th>Hyp</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {openTrades.map(t => (
              <TradeRow
                key={t.id}
                trade={t}
                onClose={() => setClosingTrade(t)}
                onHypothesisClick={handleHypothesisClick}
              />
            ))}
          </tbody>
        </table>
      )}

      {/* Closed Trades */}
      {closedTrades.length > 0 && (
        <>
          <div className="trades-view__section-header">
            <h3>Closed Trades</h3>
          </div>
          <table className="trades-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Dir</th>
                <th className="trades-table__num">Entry</th>
                <th className="trades-table__num">Exit</th>
                <th className="trades-table__num">P&L</th>
                <th className="trades-table__num">%</th>
                <th className="trades-table__num">Days</th>
                <th className="trades-table__num">Conv</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {closedTrades.map(t => (
                <ClosedTradeRow key={t.id} trade={t} />
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* Performance */}
      {perf && (openTrades.length > 0 || closedTrades.length > 0) && (
        <div className="trades-view__performance">
          <h3>Performance</h3>
          <div className="perf-grid">
            <PerfStat label="Open P&L" value={fmtPnl(perf.open_pnl)} pnl={perf.open_pnl} />
            <PerfStat label="Open Notional" value={fmtDollar(perf.open_notional)} />
            {perf.closed_count > 0 && (
              <>
                <PerfStat label="Realized" value={fmtPnl(perf.total_realized)} pnl={perf.total_realized} />
                <PerfStat label="Win Rate" value={perf.win_rate != null ? `${(perf.win_rate * 100).toFixed(0)}%` : '---'} />
                <PerfStat label="W / L" value={`${perf.wins} / ${perf.losses}`} />
              </>
            )}
            {Object.keys(perf.avg_return_by_conviction || {}).length > 0 && (
              <div className="perf-conviction-breakdown">
                <span className="perf-stat__label">Avg Return by Conviction:</span>
                {Object.entries(perf.avg_return_by_conviction)
                  .sort(([a], [b]) => Number(b) - Number(a))
                  .map(([conv, avg]) => (
                    <span key={conv} className="perf-conviction-tier">
                      <span className="perf-conviction-tier__score">{conv}:</span>
                      <span className={`perf-conviction-tier__return ${avg >= 0 ? 'perf--positive' : 'perf--negative'}`}>
                        {avg >= 0 ? '+' : ''}{avg.toFixed(2)}%
                      </span>
                    </span>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      {showNewForm && (
        <NewTradeForm
          onSubmit={handleCreate}
          onCancel={() => setShowNewForm(false)}
        />
      )}

      {closingTrade && (
        <CloseTradeForm
          trade={closingTrade}
          onSubmit={handleClose}
          onCancel={() => setClosingTrade(null)}
        />
      )}
    </div>
  )
}


function TradeRow({ trade: t, onClose, onHypothesisClick }) {
  const pnlClass = (t.unrealized_pnl || 0) >= 0 ? 'perf--positive' : 'perf--negative'

  return (
    <tr className="trades-table__row">
      <td className="trades-table__ticker">{t.ticker}</td>
      <td className={`trades-table__dir trades-table__dir--${t.direction.toLowerCase()}`}>
        {t.direction}
      </td>
      <td className="trades-table__num">${t.entry_price?.toFixed(2)}</td>
      <td className="trades-table__num">{t.current_price ? `$${t.current_price.toFixed(2)}` : '---'}</td>
      <td className={`trades-table__num ${pnlClass}`}>{fmtPnl(t.unrealized_pnl)}</td>
      <td className={`trades-table__num ${pnlClass}`}>{fmtPct(t.unrealized_pct)}</td>
      <td className="trades-table__num">{t.days_held ?? '---'}</td>
      <td className="trades-table__num trades-table__conviction">{t.conviction_at_entry}</td>
      <td>
        <button
          className="trades-table__hyp-link"
          onClick={() => onHypothesisClick(t.hypothesis_id)}
          title={t.hypothesis_short_name}
        >
          {t.hypothesis_id}
        </button>
      </td>
      <td>
        <button className="btn btn--small" onClick={onClose}>CLOSE</button>
      </td>
    </tr>
  )
}


function ClosedTradeRow({ trade: t }) {
  const pnlClass = (t.realized_pnl || 0) >= 0 ? 'perf--positive' : 'perf--negative'
  const reasonLabel = {
    hypothesis_killed: 'Hyp killed',
    target_reached: 'Target',
    stop_hit: 'Stop',
    manual: 'Manual',
    expired: 'Expired',
  }

  return (
    <tr className="trades-table__row trades-table__row--closed">
      <td className="trades-table__ticker">{t.ticker}</td>
      <td className={`trades-table__dir trades-table__dir--${t.direction.toLowerCase()}`}>
        {t.direction}
      </td>
      <td className="trades-table__num">${t.entry_price?.toFixed(2)}</td>
      <td className="trades-table__num">${t.exit_price?.toFixed(2)}</td>
      <td className={`trades-table__num ${pnlClass}`}>{fmtPnl(t.realized_pnl)}</td>
      <td className={`trades-table__num ${pnlClass}`}>{fmtPct(t.realized_pct)}</td>
      <td className="trades-table__num">{t.days_held ?? '---'}</td>
      <td className="trades-table__num trades-table__conviction">{t.conviction_at_entry}</td>
      <td className="trades-table__reason">{reasonLabel[t.exit_reason] || t.exit_reason || '---'}</td>
    </tr>
  )
}


function PerfStat({ label, value, pnl }) {
  let cls = 'perf-stat'
  if (pnl != null) cls += pnl >= 0 ? ' perf--positive' : ' perf--negative'
  return (
    <div className={cls}>
      <span className="perf-stat__label">{label}</span>
      <span className="perf-stat__value">{value}</span>
    </div>
  )
}


function fmtPnl(val) {
  if (val == null) return '---'
  const sign = val >= 0 ? '+' : ''
  return `${sign}$${val.toFixed(2)}`
}

function fmtPct(val) {
  if (val == null) return '---'
  const sign = val >= 0 ? '+' : ''
  return `${sign}${val.toFixed(2)}%`
}

function fmtDollar(val) {
  if (val == null) return '---'
  return `$${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}
