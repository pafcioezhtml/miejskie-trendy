import { MapPin } from 'lucide-react'
import { CategoryBadge } from './CategoryBadge'
import { RelevanceIndicator } from './RelevanceIndicator'
import { SourceLinks } from './SourceLinks'
import { TimeRange } from './TimeRange'

export function EventCard({ event, isNew, newUrls }) {
  const hasUpdates = isNew || (newUrls && newUrls.size > 0)

  return (
    <article className={`event-card${hasUpdates ? ' event-card--updated' : ''}`}>
      <div className="event-header">
        <div className="event-meta">
          <CategoryBadge category={event.category} />
          <RelevanceIndicator relevance={event.relevance} />
          {isNew && <span className="update-badge">Nowy temat</span>}
        </div>
        <TimeRange sources={event.sources} />
      </div>
      <h2 className="event-name">{event.name}</h2>
      {event.location && (
        <p className="event-location">
          <MapPin size={14} /> {event.location}
        </p>
      )}
      <p className="event-description">{event.description}</p>
      <SourceLinks sources={event.sources} newUrls={newUrls} />
    </article>
  )
}
