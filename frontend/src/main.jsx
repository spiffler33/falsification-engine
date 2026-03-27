import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// In static mode (GitHub Pages), use HashRouter since there's no server
// to handle SPA fallback routing. In dev/production, use BrowserRouter.
const isStatic = Boolean(window.__SNAPSHOT__)
const Router = isStatic ? HashRouter : BrowserRouter

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Router>
      <App />
    </Router>
  </React.StrictMode>
)
