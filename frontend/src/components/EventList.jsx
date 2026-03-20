import { EventCard } from './EventCard'

export function EventList({ events, newEventIds, newSourceUrls }) {
  if (events.length === 0) {
    return <p className="empty-state">Brak wydarzeń do wyświetlenia.</p>
  }

  return (
    <div className="event-grid">
      {events.map((event) => (
        <EventCard
          key={event.id}
          event={event}
          isNew={newEventIds.has(event.id)}
          newUrls={newSourceUrls.get(event.id) || null}
        />
      ))}
    </div>
  )
}
