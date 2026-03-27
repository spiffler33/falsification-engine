import { Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import Header from './components/Header'
import NavBar from './components/NavBar'
import LedgerView from './views/LedgerView'
import JournalView from './views/JournalView'
import ObservatoryView from './views/ObservatoryView'
import PipelineView from './views/PipelineView'
import BriefingView from './views/BriefingView'
import HypothesisDetail from './overlays/HypothesisDetail'
import { api } from './lib/api'

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
        <Route path="/journal" element={<JournalView onSelectHypothesis={openDetail} />} />
        <Route path="/observatory" element={<ObservatoryView />} />
        <Route path="/pipeline" element={<PipelineView />} />
        <Route path="/briefing" element={<BriefingView />} />
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
