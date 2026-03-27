import { useState, useEffect, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import DeltaBanner from '../components/DeltaBanner'
import HypothesisTable from '../components/HypothesisTable'
import AssetGroupView from '../components/AssetGroupView'

const FILTERS = ['ALIVE', 'ALL', 'WOUNDED', 'KILLED']

/**
 * LedgerView — the primary daily entry point.
 * Delta banner at top, controls bar, then hypothesis table or asset group view.
 */
export default function LedgerView({ onSelectHypothesis }) {
  const [viewMode, setViewMode] = useState('hypothesis') // 'hypothesis' | 'asset'
  const [filter, setFilter] = useState('ALIVE')
  const [delta, setDelta] = useState(null)
  const [lastReviewedRunId, setLastReviewedRunId] = useState(
    () => localStorage.getItem('last_reviewed_run_id') || null
  )

  const { data: hypotheses, loading, error, refetch } = useApi('/api/hypotheses')

  // Fetch delta on mount
  useEffect(() => {
    if (lastReviewedRunId) {
      api.get(`/api/hypotheses/delta?since_run_id=${lastReviewedRunId}`)
        .then(setDelta)
        .catch(() => setDelta(null))
    } else {
      // No last review — show all as NEW
      api.get('/api/hypotheses/delta?since_run_id=')
        .then(setDelta)
        .catch(() => setDelta(null))
    }
  }, [lastReviewedRunId])

  // Filter hypotheses
  const filtered = useMemo(() => {
    if (!hypotheses) return []
    let list = [...hypotheses]

    switch (filter) {
      case 'ALIVE':
        list = list.filter(h => h.status !== 'KILLED')
        break
      case 'WOUNDED':
        list = list.filter(h => h.status === 'WOUNDED')
        break
      case 'KILLED':
        list = list.filter(h => h.status === 'KILLED')
        break
      // 'ALL' — no filter
    }

    // Default sort: conviction desc
    list.sort((a, b) => (b.conviction || 0) - (a.conviction || 0))
    return list
  }, [hypotheses, filter])

  const handleMarkReviewed = () => {
    // Find the latest run_id from the hypotheses
    if (hypotheses && hypotheses.length > 0) {
      const latestRunId = hypotheses[0]?.run_id
      if (latestRunId) {
        localStorage.setItem('last_reviewed_run_id', latestRunId)
        setLastReviewedRunId(latestRunId)
        // Update on server too
        api.put('/api/user-state', { last_reviewed_run_id: latestRunId }).catch(() => {})
      }
    }
    setDelta(null)
  }

  if (loading) return <div className="loading">Loading hypotheses...</div>
  if (error) return <div className="empty-state">Failed to load hypotheses. Is the backend running?</div>

  return (
    <div>
      <DeltaBanner
        delta={delta}
        onSelectHypothesis={onSelectHypothesis}
        onMarkReviewed={handleMarkReviewed}
      />

      <div className="controls-bar">
        <div className="controls-bar__left">
          <div className="btn-group">
            <button
              className={`btn ${viewMode === 'hypothesis' ? 'btn--active' : ''}`}
              onClick={() => setViewMode('hypothesis')}
            >
              BY HYPOTHESIS
            </button>
            <button
              className={`btn ${viewMode === 'asset' ? 'btn--active' : ''}`}
              onClick={() => setViewMode('asset')}
            >
              BY ASSET
            </button>
          </div>

          <div className="btn-group">
            {FILTERS.map(f => (
              <button
                key={f}
                className={`btn ${filter === f ? 'btn--active' : ''}`}
                onClick={() => setFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="controls-bar__right">
          <span className="controls-bar__count">
            {filtered.length} {filtered.length === 1 ? 'hypothesis' : 'hypotheses'}
          </span>
        </div>
      </div>

      {viewMode === 'hypothesis' ? (
        <HypothesisTable
          hypotheses={filtered}
          onSelect={onSelectHypothesis}
        />
      ) : (
        <AssetGroupView
          hypotheses={filtered}
          onSelect={onSelectHypothesis}
        />
      )}
    </div>
  )
}
