import { CategoryBadge } from './CategoryBadge'
import { RelevanceIndicator } from './RelevanceIndicator'
import { SourceLinks } from './SourceLinks'

function formatTime(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return d.toLocaleString('pl-PL', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function EventCard({ event }) {
  return (
    <article className="event-card">
      <div className="event-header">
        <div className="event-meta">
          <CategoryBadge category={event.category} />
          <RelevanceIndicator relevance={event.relevance} />
        </div>
        {event.first_seen_at && (
          <span className="event-time">
            {formatTime(event.first_seen_at)}
          </span>
        )}
      </div>
      <h2 className="event-name">{event.name}</h2>
      {event.location && (
        <p className="event-location">
          <span className="location-icon">&#x1F4CD;</span> {event.location}
        </p>
      )}
      <p className="event-description">{event.description}</p>
      <SourceLinks sources={event.sources} />
    </article>
  )
}
