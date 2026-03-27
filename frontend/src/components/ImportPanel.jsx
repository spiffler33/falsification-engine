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
      // Validate JSON syntax before sending
      try {
        JSON.parse(text)
      } catch {
        setError('Invalid JSON. Please paste the complete output from Claude.')
        setImporting(false)
        return
      }

      await onImport(text)
      setText('')
    } catch (err) {
      // Surface structured error details from backend ParseError
      if (err.message) {
        try {
          const detail = JSON.parse(err.message.replace(/^API POST [^:]+: \d+ /, ''))
          const parts = [detail.message || 'Import failed.']
          if (detail.field_errors && detail.field_errors.length > 0) {
            parts.push('\n\nField errors:\n' + detail.field_errors.join('\n'))
          }
          setError(parts.join(''))
        } catch {
          setError(err.message || 'Import failed. Check the output format.')
        }
      } else {
        setError('Import failed. Check the output format.')
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
