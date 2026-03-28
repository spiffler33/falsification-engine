import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import Header from './components/Header'
import NavBar from './components/NavBar'
import ResearchView from './views/ResearchView'
import ObservatoryView from './views/ObservatoryView'
import PipelineView from './views/PipelineView'
import TradesView from './views/TradesView'
import AboutView from './views/AboutView'
import HypothesisDetail from './overlays/HypothesisDetail'
import { api } from './lib/api'
import { isStaticMode, getSnapshot } from './lib/snapshot'

export default function App() {
  const [inboxCount, setInboxCount] = useState(0)
  const [selectedHypothesis, setSelectedHypothesis] = useState(null)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    api.get('/api/inbox?status=queued').then(data => {
      if (Array.isArray(data)) setInboxCount(data.length)
    }).catch(() => {})
  }, [])

  // Handle deep-link to hypothesis detail
  useEffect(() => {
    const match = location.pathname.match(/^\/hypothesis\/(.+)$/)
    if (match) {
      api.get(`/api/hypotheses/${match[1]}`).then(h => {
        setSelectedHypothesis(h)
      }).catch(() => {
        navigate('/observatory', { replace: true })
      })
    }
  }, [location.pathname, navigate])

  const openDetail = useCallback((hypothesis) => {
    setSelectedHypothesis(hypothesis)
  }, [])

  const closeDetail = useCallback(() => {
    setSelectedHypothesis(null)
    if (location.pathname.startsWith('/hypothesis/')) {
      navigate('/observatory', { replace: true })
    }
  }, [location.pathname, navigate])

  return (
    <div className="app-container">
      <Header />
      <NavBar inboxCount={inboxCount} />

      {isStaticMode() && (
        <div className="static-banner">
          <span className="static-banner__text">
            Read-only snapshot -- published {(() => {
              const ts = getSnapshot()?.snapshot_timestamp
              if (!ts) return ''
              const d = new Date(ts)
              return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                + ' at ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
            })()}
          </span>
        </div>
      )}

      <Routes>
        <Route path="/" element={<ResearchView />} />
        <Route path="/observatory" element={<ObservatoryView onSelectHypothesis={openDetail} />} />
        <Route path="/pipeline" element={<PipelineView />} />
        <Route path="/trades" element={<TradesView onSelectHypothesis={openDetail} />} />
        <Route path="/about" element={<AboutView />} />
        <Route path="/briefing" element={<Navigate to="/observatory" replace />} />
        <Route path="/hypothesis/:id" element={<ObservatoryView onSelectHypothesis={openDetail} />} />
      </Routes>

      {selectedHypothesis && (
        <HypothesisDetail
          hypothesis={selectedHypothesis}
          onClose={closeDetail}
        />
      )}
    </div>
  )
}
