import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { ActivityChart } from './ActivityChart'

function formatDate(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return d.toLocaleString('pl-PL', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function SourceLinks({ sources, newUrls }) {
  const [expanded, setExpanded] = useState(false)

  if (!sources || sources.length === 0) return null

  const newCount = newUrls ? newUrls.size : 0

  return (
    <div className="source-links">
      <div className="source-links-header">
        <button
          className="source-toggle"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? 'Ukryj' : 'Pokaż'} {sources.length} {sources.length === 1 ? 'źródło' : sources.length < 5 ? 'źródła' : 'źródeł'}
        </button>
        {newCount > 0 && (
          <span className="new-sources-badge">
            <Sparkles size={12} />
            {newCount} {newCount === 1 ? 'nowy' : newCount < 5 ? 'nowe' : 'nowych'}
          </span>
        )}
        <ActivityChart sources={sources} />
      </div>
      {expanded && (
        <ul className="source-list">
          {sources.map((source, i) => {
            const isNewSource = newUrls && newUrls.has(source.url)
            return (
              <li key={i} className={isNewSource ? 'source-item-new' : ''}>
                {isNewSource && <Sparkles size={12} className="source-new-icon" />}
                <a href={source.url} target="_blank" rel="noopener noreferrer">
                  {source.title}
                </a>
                {source.published_at && (
                  <span className="source-date">{formatDate(source.published_at)}</span>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
