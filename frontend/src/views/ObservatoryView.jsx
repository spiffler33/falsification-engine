/**
 * ObservatoryView -- Full context layer (v7: thread-centered).
 * 1. Theory cards (activation state)
 * 2. Thread ledger (delta banner, filters, thread table / asset view)
 * 3. Data briefing grid
 *
 * Depends on: GET /api/theories, GET /api/threads, GET /api/hypotheses/delta,
 *             GET /api/briefing/latest
 */
import { useState, useEffect, useMemo, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import TheoryCard from '../components/TheoryCard'
import TheoryDetail from '../overlays/TheoryDetail'
import DeltaBanner from '../components/DeltaBanner'
import ThreadTable from '../components/ThreadTable'
import AssetGroupView from '../components/AssetGroupView'
import BriefingGrid from '../components/BriefingGrid'

const FILTERS = ['ALIVE', 'ALL', 'WOUNDED', 'KILLED']

export default function ObservatoryView({ onSelectHypothesis }) {
  // ---- Theory detail overlay ----
  const [selectedTheory, setSelectedTheory] = useState(null)
  const handleTheoryClick = useCallback((theory) => setSelectedTheory(theory), [])
  const closeTheoryDetail = useCallback(() => setSelectedTheory(null), [])

  // ---- Theories ----
  const { data: theories, loading: theoriesLoading } = useApi('/api/theories')

  // ---- Threads (v7: primary ledger data source) ----
  const [viewMode, setViewMode] = useState('thread') // 'thread' | 'asset'
  const [filter, setFilter] = useState('ALIVE')
  const [showRetired, setShowRetired] = useState(true)
  const [delta, setDelta] = useState(null)
  const [lastReviewedRunId, setLastReviewedRunId] = useState(
    () => localStorage.getItem('last_reviewed_run_id') || null
  )
  const { data: threads, loading: threadLoading } = useApi('/api/threads')

  // Delta still works at instance level — shows what changed since last review
  useEffect(() => {
    if (lastReviewedRunId) {
      api.get(`/api/hypotheses/delta?since_run_id=${lastReviewedRunId}`)
        .then(setDelta)
        .catch(() => setDelta(null))
    } else {
      api.get('/api/hypotheses/delta?since_run_id=')
        .then(setDelta)
        .catch(() => setDelta(null))
    }
  }, [lastReviewedRunId])

  // Filter and sort threads
  const filtered = useMemo(() => {
    if (!threads) return []
    let list = [...threads]

    // Status filter (on latest instance status)
    switch (filter) {
      case 'ALIVE':
        list = list.filter(t => t.status !== 'KILLED' && t.thread_status !== 'RETIRED')
        break
      case 'WOUNDED':
        list = list.filter(t => t.status === 'WOUNDED')
        break
      case 'KILLED':
        list = list.filter(t => t.status === 'KILLED')
        break
      // 'ALL' — no status filter
    }

    // Retired visibility
    if (!showRetired) {
      list = list.filter(t => t.thread_status !== 'RETIRED')
    }

    // Sort: active threads by conviction desc, retired at bottom
    list.sort((a, b) => {
      const aRetired = a.thread_status === 'RETIRED' ? 1 : 0
      const bRetired = b.thread_status === 'RETIRED' ? 1 : 0
      if (aRetired !== bRetired) return aRetired - bRetired
      return (b.conviction || 0) - (a.conviction || 0)
    })

    return list
  }, [threads, filter, showRetired])

  // Count active vs retired for display
  const activeCount = useMemo(() => {
    return filtered.filter(t => t.thread_status !== 'RETIRED').length
  }, [filtered])
  const retiredCount = useMemo(() => {
    return filtered.filter(t => t.thread_status === 'RETIRED').length
  }, [filtered])

  const handleMarkReviewed = () => {
    if (threads && threads.length > 0) {
      // Find the latest run_id across all threads
      let latestRun = ''
      for (const t of threads) {
        if ((t.run_id || '') > latestRun) latestRun = t.run_id
      }
      if (latestRun) {
        localStorage.setItem('last_reviewed_run_id', latestRun)
        setLastReviewedRunId(latestRun)
        api.put('/api/user-state', { last_reviewed_run_id: latestRun }).catch(() => {})
      }
    }
    setDelta(null)
  }

  // ---- Briefing ----
  const { data: briefing, loading: briefingLoading } = useApi('/api/briefing/latest')

  // ---- Theory sort ----
  const tierOrder = { active: 0, adjacent: 1, inactive: 2 }
  const sortedTheories = useMemo(() => {
    if (!theories) return []
    return [...theories].sort((a, b) => {
      const ta = tierOrder[a.tier] ?? 2
      const tb = tierOrder[b.tier] ?? 2
      if (ta !== tb) return ta - tb
      return (b.activation_score ?? 0) - (a.activation_score ?? 0)
    })
  }, [theories])

  return (
    <div className="observatory-view">
      {/* Theory Cards */}
      <h2>Observatory</h2>
      {theoriesLoading ? (
        <div className="loading">Loading theories...</div>
      ) : sortedTheories.length > 0 ? (
        <div className="observatory-grid">
          {sortedTheories.map(t => (
            <TheoryCard key={t.theory_id} theory={t} onClick={handleTheoryClick} />
          ))}
        </div>
      ) : (
        <div className="empty-state">No theory modules found.</div>
      )}

      {/* Thread Ledger */}
      <div className="observatory-view__ledger">
        <DeltaBanner
          delta={delta}
          onSelectHypothesis={onSelectHypothesis}
          onMarkReviewed={handleMarkReviewed}
        />

        <div className="controls-bar">
          <div className="controls-bar__left">
            <div className="btn-group">
              <button
                className={`btn ${viewMode === 'thread' ? 'btn--active' : ''}`}
                onClick={() => setViewMode('thread')}
              >
                BY THREAD
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
            <button
              className={`btn ${showRetired ? 'btn--active' : ''}`}
              onClick={() => setShowRetired(!showRetired)}
            >
              {showRetired ? 'HIDE RETIRED' : 'SHOW RETIRED'}
            </button>
            <span className="controls-bar__count">
              {activeCount} {activeCount === 1 ? 'thread' : 'threads'}
              {showRetired && retiredCount > 0 && (
                <span className="controls-bar__retired-count"> + {retiredCount} retired</span>
              )}
            </span>
          </div>
        </div>

        {threadLoading ? (
          <div className="loading">Loading threads...</div>
        ) : viewMode === 'thread' ? (
          <ThreadTable
            threads={filtered}
            onSelect={onSelectHypothesis}
          />
        ) : (
          <AssetGroupView
            hypotheses={filtered}
            onSelect={onSelectHypothesis}
          />
        )}
      </div>

      {/* Data Briefing */}
      <div className="observatory-view__briefing">
        <h3>Data Briefing</h3>
        {briefing && (
          <div className="briefing-view__timestamp">
            {briefing.is_mock && <span className="briefing-view__mock-badge">MOCK DATA</span>}
            {briefing.staleness_hours != null && briefing.staleness_hours >= 0 && (
              <span>Staleness: {briefing.staleness_hours < 1 ? '<1h' : `${Math.round(briefing.staleness_hours)}h`}</span>
            )}
          </div>
        )}
        {briefingLoading ? (
          <div className="loading">Loading briefing...</div>
        ) : briefing ? (
          <BriefingGrid briefing={briefing} />
        ) : (
          <div className="empty-state">No briefing data available.</div>
        )}
      </div>

      {selectedTheory && (
        <TheoryDetail theory={selectedTheory} onClose={closeTheoryDetail} />
      )}
    </div>
  )
}
