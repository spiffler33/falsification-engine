/**
 * ImportPanel — textarea for pasting LLM JSON output back into the system.
 * Validates JSON structure and shows clear error messages.
 */
import { useState, useCallback } from 'react'

export default function ImportPanel({ stage, onImport, visible, onToggle }) {
  // stage: 'generation' | 'elimination'
  const [text, setText] = useState('')
  const [error, setError] = useState(null)
  const [importing, setImporting] = useState(false)

  const handleImport = useCallback(async () => {
    setError(null)
    setImporting(true)
    try {
      await onImport(text)
      setText('')
    } catch (err) {
      // Surface the actual error from the backend
      const raw = err.message || 'Import failed.'
      // Try to extract structured detail from the API error
      const jsonMatch = raw.match(/\d+\s+(\{.+)/)
      if (jsonMatch) {
        try {
          const detail = JSON.parse(jsonMatch[1])
          const msg = detail.detail?.message || detail.detail || detail.message || raw
          const fieldErrors = detail.detail?.field_errors || detail.field_errors || []
          const parts = [typeof msg === 'string' ? msg : JSON.stringify(msg)]
          if (fieldErrors.length > 0) {
            parts.push('\n\nField errors:\n' + fieldErrors.join('\n'))
          }
          setError(parts.join(''))
        } catch {
          setError(raw)
        }
      } else {
        setError(raw)
      }
    } finally {
      setImporting(false)
    }
  }, [text, onImport])

  if (!visible) return null

  return (
    <div className="import-panel">
      <div className="import-panel__header">
        <span className="import-panel__title">
          Import {stage === 'generation' ? 'Generation' : 'Elimination'} Output
        </span>
        <button className="btn" onClick={onToggle}>HIDE</button>
      </div>
      <textarea
        className="import-panel__textarea"
        placeholder={`Paste Claude's ${stage} JSON output here...`}
        value={text}
        onChange={e => { setText(e.target.value); setError(null) }}
        rows={12}
      />
      {error && (
        <div className="import-panel__error">{error}</div>
      )}
      <div className="import-panel__actions">
        <button
          className="btn btn--primary"
          onClick={handleImport}
          disabled={!text.trim() || importing}
        >
          {importing ? 'IMPORTING...' : 'IMPORT'}
        </button>
      </div>
    </div>
  )
}
