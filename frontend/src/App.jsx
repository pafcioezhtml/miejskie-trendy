import { useEvents } from './hooks/useEvents'
import { EventList } from './components/EventList'
import './App.css'

function App() {
  const { events, fetchedAt, loading, error, updatedIds } = useEvents()

  const formatTime = (iso) => {
    if (!iso) return ''
    const d = new Date(iso)
    return d.toLocaleString('pl-PL', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>Miejskie Trendy</h1>
          <p className="subtitle">Bieżące wydarzenia w Warszawie</p>
        </div>
        {fetchedAt && (
          <span className="fetched-at">
            Zaktualizowano: {formatTime(fetchedAt)}
          </span>
        )}
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            Błąd: {error}
          </div>
        )}

        {loading && events.length === 0 ? (
          <div className="loading">
            <div className="spinner" />
            <p>Ładowanie wydarzeń...</p>
          </div>
        ) : (
          <EventList events={events} updatedIds={updatedIds} />
        )}
      </main>
    </div>
  )
}

export default App
