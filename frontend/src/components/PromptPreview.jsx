/**
 * PromptPreview — expandable panel showing the full prompt text.
 * Rendered in --bg-inset with monospace font for readability.
 */
export default function PromptPreview({ prompt, visible, onToggle }) {
  if (!visible) return null

  return (
    <div className="prompt-preview">
      <div className="prompt-preview__header">
        <span className="prompt-preview__title">Prompt Preview</span>
        <button className="btn" onClick={onToggle}>HIDE</button>
      </div>
      <pre className="prompt-preview__text">{prompt || 'Loading prompt...'}</pre>
    </div>
  )
}
