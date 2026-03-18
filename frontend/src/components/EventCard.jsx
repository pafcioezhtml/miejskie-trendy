import { CategoryBadge } from './CategoryBadge'
import { RelevanceIndicator } from './RelevanceIndicator'
import { SourceLinks } from './SourceLinks'

export function EventCard({ event }) {
  return (
    <article className="event-card">
      <div className="event-header">
        <div className="event-meta">
          <CategoryBadge category={event.category} />
          <RelevanceIndicator relevance={event.relevance} />
        </div>
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
