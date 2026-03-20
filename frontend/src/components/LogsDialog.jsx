import { useState, useEffect, useRef } from 'react'
import { X } from 'lucide-react'

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('pl-PL', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

const LEVEL_CLASSES = {
  error: 'log-error',
  warning: 'log-warning',
  info: '',
}

export function LogsDialog({ open, onClose }) {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    fetch('/api/logs')
      .then((r) => r.json())
      .then((data) => {
        setLogs(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [open])

  // Auto-refresh every 10s while open
  useEffect(() => {
    if (!open) return
    const interval = setInterval(() => {
      fetch('/api/logs')
        .then((r) => r.json())
        .then(setLogs)
        .catch(() => {})
    }, 10_000)
    return () => clearInterval(interval)
  }, [open])

  if (!open) return null

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog dialog-logs" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h2>Logi aktualizacji</h2>
          <button className="dialog-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="logs-body">
          {loading ? (
            <p className="dialog-loading">Ładowanie...</p>
          ) : logs.length === 0 ? (
            <p className="dialog-loading">Brak logów</p>
          ) : (
            <div className="logs-list">
              {[...logs].reverse().map((log, i) => (
                <div key={i} className={`log-entry ${LEVEL_CLASSES[log.level] || ''}`}>
                  <span className="log-time">{formatTime(log.timestamp)}</span>
                  <span className="log-msg">{log.message}</span>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
