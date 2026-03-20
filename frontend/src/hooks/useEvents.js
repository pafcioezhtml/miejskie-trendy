import { useState, useEffect, useCallback, useRef } from 'react'

const POLL_INTERVAL = 30_000 // 30 seconds

export function useEvents() {
  const [events, setEvents] = useState([])
  const [fetchedAt, setFetchedAt] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // newEventIds: brand new events (not in previous snapshot)
  const [newEventIds, setNewEventIds] = useState(new Set())
  // newSourceUrls: map of eventId → Set of new source URLs
  const [newSourceUrls, setNewSourceUrls] = useState(new Map())

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

      if (prevSnapshotRef.current) {
        const prev = prevSnapshotRef.current
        const brandNew = new Set()
        const updatedSources = new Map()

        for (const ev of newEvents) {
          const old = prev.get(ev.id)
          if (!old) {
            brandNew.add(ev.id)
          } else {
            // Find source URLs that weren't there before
            const currentUrls = new Set(ev.sources.map((s) => s.url))
            const added = new Set()
            for (const url of currentUrls) {
              if (!old.sourceUrls.has(url)) {
                added.add(url)
              }
            }
            if (added.size > 0) {
              updatedSources.set(ev.id, added)
            }
          }
        }

        if (brandNew.size > 0) setNewEventIds(brandNew)
        if (updatedSources.size > 0) {
          setNewSourceUrls((prev) => {
            const merged = new Map(prev)
            for (const [id, urls] of updatedSources) {
              const existing = merged.get(id) || new Set()
              for (const u of urls) existing.add(u)
              merged.set(id, existing)
            }
            return merged
          })
        }
      }

      // Save snapshot for next comparison
      const snapshot = new Map()
      for (const ev of newEvents) {
        snapshot.set(ev.id, {
          sourceUrls: new Set(ev.sources.map((s) => s.url)),
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

  // Clear "new event" badges after 30s, but keep newSourceUrls until next refresh
  useEffect(() => {
    if (newEventIds.size === 0) return
    const timer = setTimeout(() => setNewEventIds(new Set()), 30_000)
    return () => clearTimeout(timer)
  }, [newEventIds])

  // Clear newSourceUrls on each fresh data fetch (they persist across polls
  // but reset when the underlying data actually changes via scheduler)
  const prevFetchedAt = useRef(null)
  useEffect(() => {
    if (fetchedAt && prevFetchedAt.current && fetchedAt !== prevFetchedAt.current) {
      setNewSourceUrls(new Map())
    }
    prevFetchedAt.current = fetchedAt
  }, [fetchedAt])

  return { events, fetchedAt, loading, error, newEventIds, newSourceUrls }
}
