import { useState, useEffect, useCallback, useRef } from 'react'

const POLL_INTERVAL = 30_000 // 30 seconds

export function useEvents() {
  const [events, setEvents] = useState([])
  const [fetchedAt, setFetchedAt] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatedIds, setUpdatedIds] = useState(new Set())
  const prevSnapshotRef = useRef(null)

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch('/api/events')
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || `HTTP ${res.status}`)
      }
      const data = await res.json()
      const newEvents = data.events || []

      // Detect changes: new events or events with new sources
      if (prevSnapshotRef.current) {
        const prev = prevSnapshotRef.current
        const changed = new Set()
        for (const ev of newEvents) {
          const old = prev.get(ev.id)
          if (!old) {
            // Brand new event
            changed.add(ev.id)
          } else if (ev.sources.length !== old.sourceCount || ev.last_updated_at !== old.lastUpdated) {
            // Updated event (new sources or description changed)
            changed.add(ev.id)
          }
        }
        if (changed.size > 0) {
          setUpdatedIds(changed)
          // Clear highlight after 30 seconds
          setTimeout(() => setUpdatedIds(new Set()), 30_000)
        }
      }

      // Save snapshot for next comparison
      const snapshot = new Map()
      for (const ev of newEvents) {
        snapshot.set(ev.id, {
          sourceCount: ev.sources.length,
          lastUpdated: ev.last_updated_at,
        })
      }
      prevSnapshotRef.current = snapshot

      setEvents(newEvents)
      setFetchedAt(data.fetched_at)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  // Poll for updates
  useEffect(() => {
    const interval = setInterval(fetchEvents, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchEvents])

  return { events, fetchedAt, loading, error, updatedIds }
}
