const MIN_SOURCES_FOR_CHART = 4

export function ActivityChart({ sources }) {
  const dates = (sources || [])
    .map((s) => s.published_at)
    .filter(Boolean)
    .map((iso) => new Date(iso))

  if (dates.length < MIN_SOURCES_FOR_CHART) return null

  // Determine bucket size based on date range
  const sorted = [...dates].sort((a, b) => a - b)
  const earliest = sorted[0]
  const latest = sorted[sorted.length - 1]
  const rangeHours = (latest - earliest) / (1000 * 60 * 60)

  // Use hourly buckets if range <= 48h, otherwise daily
  const useHours = rangeHours <= 48
  const bucketKey = useHours
    ? (d) => `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:00`
    : (d) => d.toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' })

  // Count per bucket
  const counts = new Map()
  for (const d of sorted) {
    const key = bucketKey(d)
    counts.set(key, (counts.get(key) || 0) + 1)
  }

  // Fill gaps for hourly view
  if (useHours) {
    const cursor = new Date(earliest)
    cursor.setMinutes(0, 0, 0)
    const end = new Date(latest)
    end.setMinutes(0, 0, 0)
    while (cursor <= end) {
      const key = bucketKey(cursor)
      if (!counts.has(key)) counts.set(key, 0)
      cursor.setHours(cursor.getHours() + 1)
    }
  }

  // Sort buckets chronologically
  const buckets = [...counts.entries()].sort((a, b) => {
    // Relies on the fact that our keys sort correctly for same-format strings
    return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0
  })

  const max = Math.max(...buckets.map(([, v]) => v))

  return (
    <div className="activity-chart">
      <div className="chart-bars">
        {buckets.map(([label, count]) => (
          <div key={label} className="chart-col" title={`${label}: ${count}`}>
            <div
              className="chart-bar"
              style={{ height: `${max > 0 ? (count / max) * 100 : 0}%` }}
            />
          </div>
        ))}
      </div>
      <div className="chart-labels">
        <span>{buckets[0]?.[0]}</span>
        <span>{buckets[buckets.length - 1]?.[0]}</span>
      </div>
    </div>
  )
}
