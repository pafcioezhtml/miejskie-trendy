const MIN_SOURCES_FOR_CHART = 4
const BASE_BIN_HOURS = 6
const DENSE_THRESHOLD = 5 // if a 6h bin has >= this many, subdivide

function binTimestamp(d, binHours) {
  const ts = new Date(d)
  const h = ts.getHours()
  const binStart = Math.floor(h / binHours) * binHours
  ts.setHours(binStart, 0, 0, 0)
  return ts.getTime()
}

function formatBinLabel(ts, binHours) {
  const d = new Date(ts)
  const day = d.toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' })
  const h = d.getHours()
  return `${day} ${String(h).padStart(2, '0')}:00–${String(h + binHours).padStart(2, '0')}:00`
}

export function ActivityChart({ sources }) {
  const dates = (sources || [])
    .map((s) => s.published_at)
    .filter(Boolean)
    .map((iso) => new Date(iso))

  if (dates.length < MIN_SOURCES_FOR_CHART) return null

  const sorted = [...dates].sort((a, b) => a - b)
  const earliest = sorted[0]
  const latest = sorted[sorted.length - 1]

  // Step 1: bin into 6h buckets
  const coarseBins = new Map()
  for (const d of sorted) {
    const key = binTimestamp(d, BASE_BIN_HOURS)
    coarseBins.set(key, (coarseBins.get(key) || 0) + 1)
  }

  // Step 2: check if any bin is dense → subdivide those into smaller bins
  const maxInBin = Math.max(...coarseBins.values())
  const needsSubdivide = maxInBin >= DENSE_THRESHOLD

  let binHours = BASE_BIN_HOURS
  if (needsSubdivide) {
    // Use 2h bins if very dense, 3h otherwise
    binHours = maxInBin >= 10 ? 1 : maxInBin >= 7 ? 2 : 3
  }

  // Step 3: re-bin with final bin size
  const bins = new Map()
  for (const d of sorted) {
    const key = binTimestamp(d, binHours)
    bins.set(key, (bins.get(key) || 0) + 1)
  }

  // Step 4: fill gaps so empty bins show as zero
  const startBin = binTimestamp(earliest, binHours)
  const endBin = binTimestamp(latest, binHours)
  const cursor = new Date(startBin)
  while (cursor.getTime() <= endBin) {
    const key = cursor.getTime()
    if (!bins.has(key)) bins.set(key, 0)
    cursor.setHours(cursor.getHours() + binHours)
  }

  // Sort chronologically
  const buckets = [...bins.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([ts, count]) => ({
      ts,
      count,
      label: formatBinLabel(ts, binHours),
    }))

  const max = Math.max(...buckets.map((b) => b.count))

  // Narrower bars for subdivided bins
  const barMinWidth = binHours < BASE_BIN_HOURS ? '2px' : '4px'

  return (
    <div className="activity-chart">
      <div className="chart-bars">
        {buckets.map((b) => (
          <div
            key={b.ts}
            className="chart-col"
            style={{ minWidth: barMinWidth }}
            title={`${b.label}: ${b.count}`}
          >
            <div
              className="chart-bar"
              style={{ height: `${max > 0 ? (b.count / max) * 100 : 0}%` }}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
