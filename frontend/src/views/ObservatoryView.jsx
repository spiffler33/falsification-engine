/**
 * ObservatoryView -- Full context layer.
 * 1. Theory cards (activation state)
 * 2. Hypothesis ledger (delta banner, filters, table/asset view)
 * 3. Data briefing grid
 *
 * Depends on: GET /api/theories, GET /api/hypotheses, GET /api/hypotheses/delta,
 *             GET /api/briefing/latest
 */
import { useState, useEffect, useMemo, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import TheoryCard from '../components/TheoryCard'
import TheoryDetail from '../overlays/TheoryDetail'
import DeltaBanner from '../components/DeltaBanner'
import HypothesisTable from '../components/HypothesisTable'
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

  // ---- Hypotheses (from LedgerView) ----
  const [viewMode, setViewMode] = useState('hypothesis')
  const [filter, setFilter] = useState('ALIVE')
  const [runScope, setRunScope] = useState('latest') // 'latest' | 'all'
  const [delta, setDelta] = useState(null)
  const [lastReviewedRunId, setLastReviewedRunId] = useState(
    () => localStorage.getItem('last_reviewed_run_id') || null
  )
  const { data: hypotheses, loading: hypLoading } = useApi('/api/hypotheses')

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

  // Determine the latest run_id from the data.
  // Compare run_id (R-YYYYMMDD-HHMMSS) not generated_date (YYYY-MM-DD),
  // because multiple runs on the same day share the same generated_date.
  const latestRunId = useMemo(() => {
    if (!hypotheses || hypotheses.length === 0) return null
    let latest = hypotheses[0]
    for (const h of hypotheses) {
      if ((h.run_id || '') > (latest.run_id || '')) latest = h
    }
    return latest.run_id
  }, [hypotheses])

  const filtered = useMemo(() => {
    if (!hypotheses) return []
    let list = [...hypotheses]

    // Run scope filter
    if (runScope === 'latest' && latestRunId) {
      list = list.filter(h => h.run_id === latestRunId)
    }

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
    }
    list.sort((a, b) => (b.conviction || 0) - (a.conviction || 0))
    return list
  }, [hypotheses, filter, runScope, latestRunId])

  const handleMarkReviewed = () => {
    if (hypotheses && hypotheses.length > 0) {
      const latestRunId = hypotheses[0]?.run_id
      if (latestRunId) {
        localStorage.setItem('last_reviewed_run_id', latestRunId)
        setLastReviewedRunId(latestRunId)
        api.put('/api/user-state', { last_reviewed_run_id: latestRunId }).catch(() => {})
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

      {/* Hypothesis Ledger */}
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
            <div className="btn-group">
              <button
                className={`btn ${runScope === 'latest' ? 'btn--active' : ''}`}
                onClick={() => setRunScope('latest')}
              >
                LATEST RUN
              </button>
              <button
                className={`btn ${runScope === 'all' ? 'btn--active' : ''}`}
                onClick={() => setRunScope('all')}
              >
                ALL RUNS
              </button>
            </div>
            <span className="controls-bar__count">
              {filtered.length} {filtered.length === 1 ? 'hypothesis' : 'hypotheses'}
            </span>
          </div>
        </div>

        {hypLoading ? (
          <div className="loading">Loading hypotheses...</div>
        ) : viewMode === 'hypothesis' ? (
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
