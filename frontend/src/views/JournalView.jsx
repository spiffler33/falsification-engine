/**
 * JournalView — the human decision/outcome layer.
 * Records when the user acts on a hypothesis, and later what happened.
 *
 * Depends on: GET /api/journal, POST /api/journal, PATCH /api/journal/:id
 * Depends on: JournalEntry, JournalForm components
 */
import { useState, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import JournalEntry from '../components/JournalEntry'
import JournalForm from '../components/JournalForm'

export default function JournalView({ onSelectHypothesis }) {
  const { data: entries, loading, error, refetch } = useApi('/api/journal')
  const [formMode, setFormMode] = useState(null) // null | 'create' | 'close'
  const [closingEntry, setClosingEntry] = useState(null)

  const handleCreate = useCallback(async (data) => {
    try {
      await api.post('/api/journal', data)
      setFormMode(null)
      refetch()
    } catch (err) {
      console.error('Failed to create journal entry:', err)
    }
  }, [refetch])

  const handleClose = useCallback(async (data) => {
    try {
      await api.patch(`/api/journal/${data.id}`, {
        outcome: data.outcome,
        closed_date: data.closed_date,
        status: data.status,
      })
      setFormMode(null)
      setClosingEntry(null)
      refetch()
    } catch (err) {
      console.error('Failed to close position:', err)
    }
  }, [refetch])

  const openCloseForm = useCallback((entry) => {
    setClosingEntry(entry)
    setFormMode('close')
  }, [])

  const handleHypothesisClick = useCallback((hypothesisId) => {
    if (onSelectHypothesis && hypothesisId) {
      api.get(`/api/hypotheses/${hypothesisId}`).then(h => {
        onSelectHypothesis(h)
      }).catch(() => {})
    }
  }, [onSelectHypothesis])

  if (loading) return <div className="loading">Loading journal...</div>
  if (error) return <div className="empty-state">Failed to load journal entries.</div>

  const openEntries = (entries || []).filter(e => e.status === 'OPEN')
  const closedEntries = (entries || []).filter(e => e.status === 'CLOSED')

  return (
    <div className="journal-view">
      <div className="journal-view__header">
        <h2>Decision Journal</h2>
        <button className="btn btn--primary" onClick={() => setFormMode('create')}>
          + RECORD ACTION
        </button>
      </div>

      {(!entries || entries.length === 0) && (
        <div className="empty-state">
          No journal entries yet. Record an action when you act on a hypothesis.
        </div>
      )}

      {openEntries.length > 0 && (
        <div className="journal-view__section">
          <h3 className="journal-view__section-title">Open Positions</h3>
          {openEntries.map(e => (
            <JournalEntry
              key={e.id}
              entry={e}
              onHypothesisClick={handleHypothesisClick}
              onClose={openCloseForm}
            />
          ))}
        </div>
      )}

      {closedEntries.length > 0 && (
        <div className="journal-view__section">
          <h3 className="journal-view__section-title">Closed</h3>
          {closedEntries.map(e => (
            <JournalEntry
              key={e.id}
              entry={e}
              onHypothesisClick={handleHypothesisClick}
            />
          ))}
        </div>
      )}

      {formMode && (
        <JournalForm
          mode={formMode}
          entry={closingEntry}
          onSubmit={formMode === 'close' ? handleClose : handleCreate}
          onCancel={() => { setFormMode(null); setClosingEntry(null) }}
        />
      )}
    </div>
  )
}
