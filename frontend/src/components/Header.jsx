import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { isStaticMode } from '../lib/snapshot'
import { api } from '../lib/api'

export default function Header() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('fe-theme') || 'day'
  })
  const [publishing, setPublishing] = useState(false)
  const [publishMsg, setPublishMsg] = useState(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme === 'night' ? 'night' : '')
    localStorage.setItem('fe-theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'night' ? 'day' : 'night')
  }

  const publish = useCallback(async () => {
    if (!confirm('Publish current state to GitHub Pages? This will build and push to gh-pages branch.')) return
    setPublishing(true)
    setPublishMsg(null)
    try {
      const result = await api.post('/api/publish')
      setPublishMsg('Published successfully')
      setTimeout(() => setPublishMsg(null), 5000)
    } catch (err) {
      setPublishMsg('Publish failed: ' + (err.message || 'unknown error'))
    } finally {
      setPublishing(false)
    }
  }, [])

  return (
    <header className="app-header">
      <div className="app-header__row">
        <div>
          <div className="app-header__title">Falsification Engine</div>
          <div className="app-header__subtitle">Global Macro Hypothesis Ledger</div>
        </div>
        <div className="app-header__actions">
          <Link to="/about" className="app-header__about-link">ABOUT</Link>
          {!isStaticMode() && (
            <button
              className="theme-toggle"
              onClick={publish}
              disabled={publishing}
            >
              {publishing ? 'PUBLISHING...' : 'PUBLISH'}
            </button>
          )}
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'night' ? 'DAY' : 'NIGHT'}
          </button>
        </div>
      </div>
      {publishMsg && (
        <div className="publish-msg" style={{
          fontFamily: 'var(--font-data)',
          fontSize: '10px',
          color: publishMsg.includes('failed') ? 'var(--accent-negative)' : 'var(--accent-positive)',
          marginTop: '4px',
        }}>
          {publishMsg}
        </div>
      )}
    </header>
  )
}
