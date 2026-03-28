/**
 * NewsletterImportPanel -- Textarea for pasting newsletter output from Claude.
 * Auto-detects and strips the <TRADES> JSON block from the newsletter text,
 * sending clean content + structured trade recommendations to the backend.
 *
 * Depends on: POST /api/newsletter/import
 */
import { useState, useCallback } from 'react'
import { api } from '../lib/api'

function parseTradesBlock(raw) {
  const match = raw.match(/<TRADES>\s*([\s\S]*?)\s*<\/TRADES>/i)
  if (!match) return { content: raw.trim(), trades: [] }

  const content = raw.replace(/<TRADES>[\s\S]*?<\/TRADES>/i, '').trim()
  try {
    const trades = JSON.parse(match[1].trim())
    if (!Array.isArray(trades)) return { content, trades: [] }
    return { content, trades }
  } catch {
    return { content, trades: [] }
  }
}

export default function NewsletterImportPanel({ onImported, onCancel }) {
  const [rawText, setRawText] = useState('')
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null)

  const handlePreview = useCallback(() => {
    if (!rawText.trim()) return
    const parsed = parseTradesBlock(rawText)
    setPreview(parsed)
    setError(null)
  }, [rawText])

  const handleImport = useCallback(async () => {
    const parsed = preview || parseTradesBlock(rawText)
    if (!parsed.content) {
      setError('Newsletter content is empty')
      return
    }

    setImporting(true)
    setError(null)
    try {
      const result = await api.post('/api/newsletter/import', {
        content: parsed.content,
        trade_recommendations: parsed.trades,
      })
      if (onImported) onImported(result)
    } catch (err) {
      setError(err.message || 'Failed to import newsletter')
    } finally {
      setImporting(false)
    }
  }, [rawText, preview, onImported])

  return (
    <div className="newsletter-import">
      <div className="newsletter-import__header">
        <h3>Import Newsletter</h3>
        {onCancel && (
          <button className="btn" onClick={onCancel}>CANCEL</button>
        )}
      </div>

      <p className="newsletter-import__hint">
        Paste the full Claude output below. The system will automatically
        extract the &lt;TRADES&gt; block for trade recommendations.
      </p>

      <textarea
        className="newsletter-import__textarea"
        value={rawText}
        onChange={e => { setRawText(e.target.value); setPreview(null) }}
        placeholder="Paste newsletter output here..."
        rows={16}
        disabled={importing}
      />

      {error && (
        <div className="newsletter-import__error">{error}</div>
      )}

      {preview && (
        <div className="newsletter-import__preview">
          <div className="newsletter-import__preview-header">
            <span>Preview</span>
            <span className="newsletter-import__trade-count">
              {preview.trades.length} trade recommendation{preview.trades.length !== 1 ? 's' : ''} detected
            </span>
          </div>
          {preview.trades.length > 0 && (
            <div className="newsletter-import__trades-preview">
              {preview.trades.map((t, i) => (
                <span key={i} className="newsletter-import__trade-tag">
                  {t.ticker} {t.direction} (conv {t.conviction})
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="newsletter-import__actions">
        {!preview ? (
          <button
            className="btn"
            onClick={handlePreview}
            disabled={!rawText.trim()}
          >
            PREVIEW
          </button>
        ) : (
          <button
            className="btn btn--primary"
            onClick={handleImport}
            disabled={importing}
          >
            {importing ? 'IMPORTING...' : 'IMPORT NEWSLETTER'}
          </button>
        )}
      </div>
    </div>
  )
}
