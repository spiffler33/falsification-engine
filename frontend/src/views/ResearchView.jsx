/**
 * ResearchView -- Primary entry point. Newsletter workflow + archive + research inbox.
 *
 * Top: Newsletter generation (prompt builder) and import (paste-back)
 * Middle: Newsletter index (stored newsletters, click to expand)
 * Bottom: Research inbox (reuses existing component)
 *
 * Depends on: GET /api/newsletter/prompt, GET /api/newsletters,
 *             POST /api/newsletter/import, GET /api/inbox
 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import NewsletterList from '../components/NewsletterList'
import NewsletterImportPanel from '../components/NewsletterImportPanel'
import ResearchInbox from '../components/ResearchInbox'

export default function ResearchView() {
  const navigate = useNavigate()
  const { data: newsletters, loading: nlLoading, refetch: refetchNewsletters } = useApi('/api/newsletters')
  const { data: inboxItems, loading: inboxLoading, refetch: refetchInbox } = useApi('/api/inbox')

  // Prompt generation state
  const [showPrompt, setShowPrompt] = useState(false)
  const [promptData, setPromptData] = useState(null)
  const [promptLoading, setPromptLoading] = useState(false)
  const [promptError, setPromptError] = useState(null)
  const [copied, setCopied] = useState(false)

  // Import state
  const [showImport, setShowImport] = useState(false)
  const [importResult, setImportResult] = useState(null)

  const handleGeneratePrompt = useCallback(async () => {
    if (showPrompt && promptData) {
      setShowPrompt(false)
      return
    }
    setPromptLoading(true)
    setPromptError(null)
    try {
      const data = await api.get('/api/newsletter/prompt')
      setPromptData(data)
      setShowPrompt(true)
    } catch (err) {
      const msg = err.message || 'Failed to assemble prompt'
      const match = msg.match(/\d+ (.+)/)
      setPromptError(match ? match[1] : msg)
    } finally {
      setPromptLoading(false)
    }
  }, [showPrompt, promptData])

  const handleCopy = useCallback(async () => {
    if (!promptData) return
    const text = promptData.system_prompt + '\n\n' + promptData.user_prompt
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [promptData])

  const handleImported = useCallback((result) => {
    setImportResult(result)
    setShowImport(false)
    setShowPrompt(false)
    refetchNewsletters()
  }, [refetchNewsletters])

  return (
    <div className="research-view">
      {/* Newsletter Workflow */}
      <div className="research-view__section">
        <div className="research-view__section-header">
          <h2>Newsletter</h2>
          <div className="research-view__actions">
            <button
              className="btn btn--newsletter"
              onClick={handleGeneratePrompt}
              disabled={promptLoading}
            >
              {promptLoading ? 'LOADING...' : showPrompt ? 'HIDE PROMPT' : 'GENERATE PROMPT'}
            </button>
            <button
              className="btn btn--primary"
              onClick={() => { setShowImport(!showImport); setImportResult(null) }}
            >
              {showImport ? 'CANCEL IMPORT' : 'IMPORT NEWSLETTER'}
            </button>
          </div>
        </div>

        {promptError && (
          <div className="research-view__error">{promptError}</div>
        )}

        {/* Import success banner */}
        {importResult && (
          <div className="research-view__success">
            Newsletter imported ({importResult.newsletter?.id}).
            {importResult.pending_count > 0 ? (
              <>
                {' '}{importResult.pending_count} pending trade action{importResult.pending_count !== 1 ? 's' : ''} created.{' '}
                <button
                  className="research-view__trades-link"
                  onClick={() => navigate('/trades')}
                >
                  Review on Trades tab
                </button>
              </>
            ) : (
              ' No trade changes needed.'
            )}
          </div>
        )}

        {/* Prompt display */}
        {showPrompt && promptData && (
          <div className="research-view__prompt">
            <div className="research-view__prompt-bar">
              <span className="research-view__prompt-hint">
                Copy and paste into Claude chat.
              </span>
              <button className="btn btn--primary" onClick={handleCopy}>
                {copied ? 'COPIED' : 'COPY PROMPT'}
              </button>
            </div>
            <pre className="research-view__prompt-content">
              {promptData.system_prompt + '\n\n' + promptData.user_prompt}
            </pre>
          </div>
        )}

        {/* Import panel */}
        {showImport && (
          <NewsletterImportPanel
            onImported={handleImported}
            onCancel={() => setShowImport(false)}
          />
        )}
      </div>

      {/* Newsletter Archive */}
      <div className="research-view__section">
        <h3>Archive</h3>
        {nlLoading ? (
          <div className="loading">Loading newsletters...</div>
        ) : (
          <NewsletterList
            newsletters={newsletters}
            onRefetch={refetchNewsletters}
          />
        )}
      </div>

      <div className="research-view__divider" />

      {/* Research Inbox */}
      <div className="research-view__section">
        {inboxLoading ? (
          <div className="loading">Loading inbox...</div>
        ) : (
          <ResearchInbox items={inboxItems} onRefetch={refetchInbox} />
        )}
      </div>
    </div>
  )
}
