import { useState } from 'react'

export function SourceLinks({ sources }) {
  const [expanded, setExpanded] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="source-links">
      <button
        className="source-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? 'Ukryj' : 'Pokaż'} {sources.length} {sources.length === 1 ? 'źródło' : sources.length < 5 ? 'źródła' : 'źródeł'}
      </button>
      {expanded && (
        <ul className="source-list">
          {sources.map((source, i) => (
            <li key={i}>
              <a href={source.url} target="_blank" rel="noopener noreferrer">
                {source.title}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
