// snapshot.js — Static mode support for GitHub Pages publishing.
//
// When the app is built with an embedded snapshot (window.__SNAPSHOT__),
// API calls are intercepted and served from the snapshot data instead.
// This makes the app fully functional as a read-only static site.

export function isStaticMode() {
  return Boolean(window.__SNAPSHOT__)
}

export function getSnapshot() {
  return window.__SNAPSHOT__ || null
}

/**
 * Resolve an API path against the embedded snapshot.
 * Returns the data that the API would have returned, or null if unresolvable.
 */
export function resolveFromSnapshot(path) {
  const snap = getSnapshot()
  if (!snap) return null

  // Health check
  if (path === '/api/health') {
    return { status: 'ok', version: '0.1.0', is_mock_data: false, is_static: true }
  }

  // Hypotheses list
  if (path === '/api/hypotheses') {
    return snap.hypotheses || []
  }

  // Single hypothesis
  const hypMatch = path.match(/^\/api\/hypotheses\/(.+)$/)
  if (hypMatch) {
    const id = hypMatch[1]
    return (snap.hypotheses || []).find(h => h.id === id) || null
  }

  // Briefing
  if (path === '/api/briefing/latest') {
    return {
      data: snap.briefing || {},
      staleness_hours: -1,
      is_mock: false,
      is_static: true,
    }
  }

  // Theories
  if (path === '/api/theories') {
    return snap.theories || []
  }

  // Pipeline status (static = complete)
  if (path === '/api/pipeline/status') {
    return {
      current_step: 5,
      run_id: snap.run?.id || '',
      steps: [
        { step: 1, label: 'Data Briefing', type: 'automated', state: 'complete' },
        { step: 2, label: 'Activation Scoring', type: 'automated', state: 'complete' },
        { step: 3, label: 'Generation Pass', type: 'human-in-loop', state: 'complete' },
        { step: 4, label: 'Elimination Pass', type: 'human-in-loop', state: 'complete' },
        { step: 5, label: 'Conviction Scoring', type: 'automated', state: 'complete' },
      ],
    }
  }

  // Runs
  if (path === '/api/runs/latest' || path === '/api/runs') {
    if (!snap.run) return path === '/api/runs' ? [] : null
    const r = {
      id: snap.run.id,
      timestamp: snap.run.timestamp,
      status: snap.run.status,
      hypotheses_generated: (snap.hypotheses || []).length,
      hypotheses_survived: (snap.hypotheses || []).filter(h => h.status === 'SURVIVED').length,
      hypotheses_wounded: (snap.hypotheses || []).filter(h => h.status === 'WOUNDED').length,
      hypotheses_killed: (snap.hypotheses || []).filter(h => h.status === 'KILLED').length,
    }
    return path === '/api/runs' ? [r] : r
  }

  // Run detail
  const runMatch = path.match(/^\/api\/runs\/(.+)$/)
  if (runMatch) {
    return {
      id: snap.run?.id,
      timestamp: snap.run?.timestamp,
      status: snap.run?.status,
      activation_scores: snap.activation_scores || [],
      generation_output: [],
      elimination_output: [],
      hypotheses: snap.hypotheses || [],
    }
  }

  // Delta
  if (path.startsWith('/api/hypotheses/delta')) {
    return { new: [], killed: [], deteriorated: [], improved: [] }
  }

  // Inbox
  if (path.startsWith('/api/inbox')) {
    return []
  }

  // Journal
  if (path === '/api/journal') {
    return []
  }

  // User state
  if (path.startsWith('/api/user')) {
    return { run_id: null }
  }

  return null
}
