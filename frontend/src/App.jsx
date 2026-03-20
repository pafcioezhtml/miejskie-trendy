import { useState } from 'react'
import { Settings, ScrollText } from 'lucide-react'
import { useEvents } from './hooks/useEvents'
import { EventList } from './components/EventList'
import { LogsDialog } from './components/LogsDialog'
import { SettingsDialog } from './components/SettingsDialog'
import './App.css'

function App() {
  const { events, fetchedAt, loading, error, newEventIds, newSourceUrls } = useEvents()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [logsOpen, setLogsOpen] = useState(false)

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
        <div className="header-actions">
          {fetchedAt && (
            <span className="fetched-at">
              Zaktualizowano: {formatTime(fetchedAt)}
            </span>
          )}
          <button
            className="header-icon-btn"
            onClick={() => setLogsOpen(true)}
            title="Logi"
          >
            <ScrollText size={18} />
          </button>
          <button
            className="header-icon-btn"
            onClick={() => setSettingsOpen(true)}
            title="Ustawienia"
          >
            <Settings size={18} />
          </button>
        </div>
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
          <EventList events={events} newEventIds={newEventIds} newSourceUrls={newSourceUrls} />
        )}
      </main>

      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
      <LogsDialog
        open={logsOpen}
        onClose={() => setLogsOpen(false)}
      />
    </div>
  )
}

export default App
