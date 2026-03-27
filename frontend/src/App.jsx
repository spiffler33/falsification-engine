import { Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import Header from './components/Header'
import NavBar from './components/NavBar'
import LedgerView from './views/LedgerView'
import HypothesisDetail from './overlays/HypothesisDetail'
import { api } from './lib/api'

// Placeholder views for Phase 6
function PlaceholderView({ title }) {
  return (
    <div className="view-placeholder">
      <div className="view-placeholder__title">{title}</div>
      <div className="view-placeholder__text">Coming in Phase 6</div>
    </div>
  )
}

export default function App() {
  const [inboxCount, setInboxCount] = useState(0)
  const [selectedHypothesis, setSelectedHypothesis] = useState(null)
  const [isMockData, setIsMockData] = useState(false)
  const [mockDismissed, setMockDismissed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    api.get('/api/health').then(data => {
      if (data?.is_mock_data) setIsMockData(true)
    }).catch(() => {})

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
        navigate('/', { replace: true })
      })
    }
  }, [location.pathname, navigate])

  const openDetail = useCallback((hypothesis) => {
    setSelectedHypothesis(hypothesis)
  }, [])

  const closeDetail = useCallback(() => {
    setSelectedHypothesis(null)
    // If we were on a deep-link, go back to ledger
    if (location.pathname.startsWith('/hypothesis/')) {
      navigate('/', { replace: true })
    }
  }, [location.pathname, navigate])

  return (
    <div className="app-container">
      <Header />
      <NavBar inboxCount={inboxCount} />

      {isMockData && !mockDismissed && (
        <div className="mock-banner">
          <span className="mock-banner__text">
            Displaying mock data. Run the pipeline to generate real hypotheses.
          </span>
          <button
            className="mock-banner__dismiss"
            onClick={() => setMockDismissed(true)}
          >
            DISMISS
          </button>
        </div>
      )}

      <Routes>
        <Route path="/" element={<LedgerView onSelectHypothesis={openDetail} />} />
        <Route path="/journal" element={<PlaceholderView title="Decision Journal" />} />
        <Route path="/observatory" element={<PlaceholderView title="Observatory" />} />
        <Route path="/pipeline" element={<PlaceholderView title="Pipeline" />} />
        <Route path="/briefing" element={<PlaceholderView title="Data Briefing" />} />
        <Route path="/hypothesis/:id" element={<LedgerView onSelectHypothesis={openDetail} />} />
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
