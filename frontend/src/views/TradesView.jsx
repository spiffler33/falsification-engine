/**
 * TradesView — Trade tracker linked to hypotheses.
 * Backend stores primitives only. All derived values (P&L, days held,
 * notional, performance stats) are computed here at render time.
 *
 * Depends on: GET /api/trades, POST /api/trades, PATCH /api/trades/:id,
 *             GET /api/prices?tickers=...
 */
import { useState, useCallback, useEffect, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import NewTradeForm from '../components/NewTradeForm'
import CloseTradeForm from '../components/CloseTradeForm'

// ---------------------------------------------------------------------------
// Derived-value helpers — all computation lives here, not in the backend
// ---------------------------------------------------------------------------

function dirSign(direction) {
  return direction === 'LONG' ? 1 : -1
}

function daysHeld(entryDate, exitDate) {
  if (!entryDate) return null
  const entry = new Date(entryDate)
  const end = exitDate ? new Date(exitDate) : new Date()
  return Math.round((end - entry) / 86400000)
}

function enrichTrade(t, prices) {
  const sign = dirSign(t.direction)
  const days = daysHeld(t.entry_date, t.exit_date)
  const notional = t.entry_price * t.shares

  if (t.status === 'CLOSED' && t.exit_price != null) {
    const pnl = (t.exit_price - t.entry_price) * t.shares * sign
    const pct = ((t.exit_price - t.entry_price) / t.entry_price) * sign * 100
    return { ...t, notional, days_held: days, realized_pnl: pnl, realized_pct: pct }
  }

  // OPEN trade — use live price if available
  const current = prices[t.ticker] ?? null
  const pnl = current != null ? (current - t.entry_price) * t.shares * sign : null
  const pct = current != null ? ((current - t.entry_price) / t.entry_price) * sign * 100 : null
  return { ...t, notional, days_held: days, current_price: current, unrealized_pnl: pnl, unrealized_pct: pct }
}

function computePerformance(openTrades, closedTrades) {
  const openPnl = openTrades.reduce((s, t) => s + (t.unrealized_pnl || 0), 0)
  const openNotional = openTrades.reduce((s, t) => s + (t.notional || 0), 0)

  const wins = closedTrades.filter(t => (t.realized_pnl || 0) > 0)
  const losses = closedTrades.filter(t => (t.realized_pnl || 0) <= 0)
  const winRate = closedTrades.length > 0 ? wins.length / closedTrades.length : null
  const totalRealized = closedTrades.reduce((s, t) => s + (t.realized_pnl || 0), 0)

  // Avg return by conviction tier
  const tiers = {}
  for (const t of closedTrades) {
    const conv = Math.round(t.conviction_at_entry || 0)
    if (!tiers[conv]) tiers[conv] = []
    tiers[conv].push(t.realized_pct || 0)
  }
  const avgByConviction = {}
  for (const [k, v] of Object.entries(tiers)) {
    avgByConviction[k] = v.reduce((a, b) => a + b, 0) / v.length
  }

  return { openPnl, openNotional, totalRealized, winRate, wins: wins.length, losses: losses.length, avgByConviction }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TradesView({ onSelectHypothesis }) {
  const { data: trades, loading, error, refetch } = useApi('/api/trades')
  const [prices, setPrices] = useState({})
  const [showNewForm, setShowNewForm] = useState(false)
  const [closingTrade, setClosingTrade] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  // Fetch prices for open trade tickers
  const fetchPrices = useCallback(async (tradeList) => {
    const openTickers = [...new Set((tradeList || []).filter(t => t.status === 'OPEN').map(t => t.ticker))]
    if (openTickers.length === 0) return
    setRefreshing(true)
    try {
      const data = await api.get(`/api/prices?tickers=${openTickers.join(',')}`)
      if (data) setPrices(data)
    } catch (err) {
      console.error('Failed to fetch prices:', err)
    } finally {
      setRefreshing(false)
    }
  }, [])

  // Auto-fetch prices on mount when trades load
  useEffect(() => {
    if (trades && trades.length > 0) fetchPrices(trades)
  }, [trades, fetchPrices])

  // Enrich trades with derived values
  const enriched = useMemo(() => (trades || []).map(t => enrichTrade(t, prices)), [trades, prices])
  const openTrades = useMemo(() => enriched.filter(t => t.status === 'OPEN'), [enriched])
  const closedTrades = useMemo(() => enriched.filter(t => t.status === 'CLOSED'), [enriched])
  const perf = useMemo(() => computePerformance(openTrades, closedTrades), [openTrades, closedTrades])

  const handleCreate = useCallback(async (data) => {
    try {
      await api.post('/api/trades', data)
      setShowNewForm(false)
      refetch()
    } catch (err) {
      console.error('Failed to create trade:', err)
    }
  }, [refetch])

  const handleClose = useCallback(async (data) => {
    try {
      await api.patch(`/api/trades/${data.id}`, {
        exit_price: data.exit_price,
        exit_date: data.exit_date,
        exit_reason: data.exit_reason,
      })
      setClosingTrade(null)
      refetch()
    } catch (err) {
      console.error('Failed to close trade:', err)
    }
  }, [refetch])

  const handleRefresh = useCallback(() => {
    fetchPrices(trades)
  }, [trades, fetchPrices])

  const handleHypothesisClick = useCallback((hypothesisId) => {
    if (onSelectHypothesis && hypothesisId) {
      api.get(`/api/hypotheses/${hypothesisId}`).then(h => {
        onSelectHypothesis(h)
      }).catch(() => {})
    }
  }, [onSelectHypothesis])

  if (loading) return <div className="loading">Loading trades...</div>
  if (error) return <div className="empty-state">Failed to load trades.</div>

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
      {(openTrades.length > 0 || closedTrades.length > 0) && (
        <div className="trades-view__performance">
          <h3>Performance</h3>
          <div className="perf-grid">
            <PerfStat label="Open P&L" value={fmtPnl(perf.openPnl)} pnl={perf.openPnl} />
            <PerfStat label="Open Notional" value={fmtDollar(perf.openNotional)} />
            {closedTrades.length > 0 && (
              <>
                <PerfStat label="Realized" value={fmtPnl(perf.totalRealized)} pnl={perf.totalRealized} />
                <PerfStat label="Win Rate" value={perf.winRate != null ? `${(perf.winRate * 100).toFixed(0)}%` : '---'} />
                <PerfStat label="W / L" value={`${perf.wins} / ${perf.losses}`} />
              </>
            )}
            {Object.keys(perf.avgByConviction).length > 0 && (
              <div className="perf-conviction-breakdown">
                <span className="perf-stat__label">Avg Return by Conviction:</span>
                {Object.entries(perf.avgByConviction)
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
      <td className="trades-table__num">{t.current_price != null ? `$${t.current_price.toFixed(2)}` : '---'}</td>
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
