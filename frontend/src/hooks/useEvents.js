import { useState, useEffect, useCallback } from 'react'

export function useEvents() {
  const [events, setEvents] = useState([])
  const [fetchedAt, setFetchedAt] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchEvents = useCallback(async (endpoint = '/api/events', method = 'GET') => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(endpoint, { method })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setEvents(data.events || [])
      setFetchedAt(data.fetched_at)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  const refetch = useCallback(() => {
    fetchEvents('/api/events/refresh', 'POST')
  }, [fetchEvents])

  return { events, fetchedAt, loading, error, refetch }
}
