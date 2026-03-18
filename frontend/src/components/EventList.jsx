import { EventCard } from './EventCard'

export function EventList({ events, updatedIds }) {
  if (events.length === 0) {
    return <p className="empty-state">Brak wydarzeń do wyświetlenia.</p>
  }

  return (
    <div className="event-grid">
      {events.map((event) => (
        <EventCard
          key={event.id}
          event={event}
          isUpdated={updatedIds.has(event.id)}
        />
      ))}
    </div>
  )
}
