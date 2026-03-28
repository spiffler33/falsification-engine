import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'

/**
 * NewsletterPromptOverlay — assembles and displays the system + user prompts
 * for newsletter generation. User copies these into Claude.ai.
 */
export default function NewsletterPromptOverlay({ onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.get('/api/newsletter/prompt')
      .then(d => {
        setData(d)
        setLoading(false)
      })
      .catch(err => {
        const msg = err.message || 'Failed to assemble prompt'
        // Extract detail from API error
        const match = msg.match(/\d+ (.+)/)
        setError(match ? match[1] : msg)
        setLoading(false)
      })
  }, [])

  // ESC to close
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdropClick = useCallback((e) => {
    if (e.target === e.currentTarget) onClose()
  }, [onClose])

  const copyToClipboard = useCallback(async (text, setter) => {
    try {
      await navigator.clipboard.writeText(text)
      setter(true)
      setTimeout(() => setter(false), 2000)
    } catch {
      // Fallback
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setter(true)
      setTimeout(() => setter(false), 2000)
    }
  }, [])

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-panel newsletter-prompt-panel">
        {/* Top bar */}
        <div className="newsletter-prompt__topbar">
          {data && (
            <button
              className="btn btn--primary newsletter-prompt__copy-all"
              onClick={() => copyToClipboard(
                data.system_prompt + '\n\n' + data.user_prompt,
                setCopied
              )}
            >
              {copied ? 'COPIED' : 'COPY PROMPT'}
            </button>
          )}
          <button className="modal-close" onClick={onClose} style={{ position: 'static' }}>
            CLOSE
          </button>
        </div>

        {data && (
          <p className="newsletter-prompt__instruction">
            Copy and paste into Claude chat. The style instructions and data are combined into a single prompt.
          </p>
        )}

        {loading && (
          <div className="newsletter-prompt__loading">
            <em>Assembling prompt...</em>
          </div>
        )}

        {error && (
          <div className="newsletter-prompt__error">
            {error}
          </div>
        )}

        {data && (
          <div className="newsletter-prompt__section">
            <pre className="newsletter-prompt__content newsletter-prompt__content--user">
              {data.system_prompt + '\n\n' + data.user_prompt}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
