import { useState, useRef } from 'react'

const MIN_SOURCES_FOR_CHART = 4
const BASE_BIN_HOURS = 6
const DENSE_THRESHOLD = 5

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
  const h1 = String(d.getHours()).padStart(2, '0')
  const endH = d.getHours() + binHours
  const h2 = String(endH).padStart(2, '0')
  return `${day} ${h1}:00–${h2}:00`
}

function subBinHours(count) {
  if (count >= 10) return 1
  if (count >= 7) return 2
  if (count >= DENSE_THRESHOLD) return 3
  return BASE_BIN_HOURS
}

export function ActivityChart({ sources }) {
  const [tooltip, setTooltip] = useState(null)
  const chartRef = useRef(null)

  const dates = (sources || [])
    .map((s) => s.published_at)
    .filter(Boolean)
    .map((iso) => new Date(iso))

  if (dates.length < MIN_SOURCES_FOR_CHART) return null

  const sorted = [...dates].sort((a, b) => a - b)
  const earliest = sorted[0]
  const latest = sorted[sorted.length - 1]

  // Step 1: coarse 6h bins
  const coarseBins = new Map()
  for (const d of sorted) {
    const key = binTimestamp(d, BASE_BIN_HOURS)
    if (!coarseBins.has(key)) coarseBins.set(key, [])
    coarseBins.get(key).push(d)
  }

  // Step 2: build final bins — only subdivide individual dense bins
  const finalBins = new Map()
  const startBin = binTimestamp(earliest, BASE_BIN_HOURS)
  const endBin = binTimestamp(latest, BASE_BIN_HOURS)
  const cursor = new Date(startBin)

  while (cursor.getTime() <= endBin) {
    const coarseKey = cursor.getTime()
    const items = coarseBins.get(coarseKey) || []
    const binH = subBinHours(items.length)

    if (binH === BASE_BIN_HOURS) {
      finalBins.set(coarseKey, { count: items.length, hours: BASE_BIN_HOURS })
    } else {
      // Subdivide only this dense bin
      const windowStart = new Date(coarseKey)
      for (let i = 0; i < BASE_BIN_HOURS / binH; i++) {
        const subTs = new Date(windowStart)
        subTs.setHours(subTs.getHours() + i * binH)
        finalBins.set(subTs.getTime(), { count: 0, hours: binH })
      }
      for (const d of items) {
        const subKey = binTimestamp(d, binH)
        const entry = finalBins.get(subKey)
        if (entry) entry.count++
      }
    }
    cursor.setHours(cursor.getHours() + BASE_BIN_HOURS)
  }

  const buckets = [...finalBins.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([ts, { count, hours }]) => ({
      ts,
      count,
      hours,
      label: formatBinLabel(ts, hours),
    }))

  const max = Math.max(...buckets.map((b) => b.count))
  const PX_PER_HOUR = 2 // fixed scale: 2px per hour for all charts

  const handleMouseEnter = (e, bucket) => {
    const rect = chartRef.current.getBoundingClientRect()
    const barRect = e.currentTarget.getBoundingClientRect()
    setTooltip({
      text: `${bucket.count}`,
      left: barRect.left - rect.left + barRect.width / 2,
    })
  }

  // Build tick labels: hours every 12h, dates on separate row
  const hourTicks = [] // { idx, label }
  const dateTicks = [] // { idx, label }
  let lastDay = -1
  for (let i = 0; i < buckets.length; i++) {
    const d = new Date(buckets[i].ts)
    const hour = d.getHours()
    // Hour ticks at 00 and 12 only
    if (hour % 12 === 0) {
      hourTicks.push({ idx: i, label: String(hour).padStart(2, '0') })
    }
    // Date tick on first bin of each new day
    if (d.getDate() !== lastDay) {
      dateTicks.push({
        idx: i,
        label: d.toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' }),
      })
      lastDay = d.getDate()
    }
  }

  return (
    <div className="activity-chart" ref={chartRef}>
      <div className="chart-bars">
        {buckets.map((b) => {
          return (
            <div
              key={b.ts}
              className="chart-col"
              style={{ width: `${b.hours * PX_PER_HOUR}px` }}
              onMouseEnter={(e) => handleMouseEnter(e, b)}
              onMouseLeave={() => setTooltip(null)}
            >
              <div
                className="chart-bar"
                style={{ height: `${max > 0 ? (b.count / max) * 100 : 0}%` }}
              />
            </div>
          )
        })}
      </div>
      <div className="chart-axis">
        {buckets.map((b, i) => {
          const hTick = hourTicks.find((t) => t.idx === i)
          return (
            <div key={b.ts} className="chart-axis-slot" style={{ width: `${b.hours * PX_PER_HOUR}px` }}>
              {hTick && <span className="chart-tick">{hTick.label}</span>}
            </div>
          )
        })}
      </div>
      {dateTicks.length > 1 && (
        <div className="chart-axis chart-axis-dates">
          {buckets.map((b, i) => {
            const dTick = dateTicks.find((t) => t.idx === i)
            return (
              <div key={b.ts} className="chart-axis-slot" style={{ width: `${b.hours * PX_PER_HOUR}px` }}>
                {dTick && <span className="chart-tick chart-tick-date">{dTick.label}</span>}
              </div>
            )
          })}
        </div>
      )}
      {tooltip && (
        <div
          className="chart-tooltip"
          style={{ left: tooltip.left }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  )
}
