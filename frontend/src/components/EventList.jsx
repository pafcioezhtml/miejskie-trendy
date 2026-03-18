import { EventCard } from './EventCard'

export function EventList({ events }) {
  if (events.length === 0) {
    return <p className="empty-state">Brak wydarzeń do wyświetlenia.</p>
  }

  return (
    <div className="event-grid">
      {events.map((event) => (
        <EventCard key={event.id} event={event} />
      ))}
    </div>
  )
}
