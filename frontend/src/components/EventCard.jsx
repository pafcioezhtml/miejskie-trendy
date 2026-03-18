import { CategoryBadge } from './CategoryBadge'
import { RelevanceIndicator } from './RelevanceIndicator'
import { SourceLinks } from './SourceLinks'
import { TimeRange } from './TimeRange'
import { ActivityChart } from './ActivityChart'

export function EventCard({ event, isUpdated }) {
  return (
    <article className={`event-card${isUpdated ? ' event-card--updated' : ''}`}>
      <div className="event-header">
        <div className="event-meta">
          <CategoryBadge category={event.category} />
          <RelevanceIndicator relevance={event.relevance} />
          {isUpdated && <span className="update-badge">Nowe</span>}
        </div>
        <TimeRange sources={event.sources} />
      </div>
      <h2 className="event-name">{event.name}</h2>
      {event.location && (
        <p className="event-location">
          <span className="location-icon">&#x1F4CD;</span> {event.location}
        </p>
      )}
      <p className="event-description">{event.description}</p>
      <ActivityChart sources={event.sources} />
      <SourceLinks sources={event.sources} />
    </article>
  )
}
