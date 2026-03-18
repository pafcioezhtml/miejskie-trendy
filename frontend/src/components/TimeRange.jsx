function formatShort(d) {
  return d.toLocaleString('pl-PL', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function sameDay(a, b) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

export function TimeRange({ sources }) {
  const dates = (sources || [])
    .map((s) => s.published_at)
    .filter(Boolean)
    .map((iso) => new Date(iso))
    .sort((a, b) => a - b)

  if (dates.length === 0) return null

  const earliest = dates[0]
  const latest = dates[dates.length - 1]

  if (sameDay(earliest, latest)) {
    // Same day — show "18 mar 09:15 – 17:30"
    const dayStr = earliest.toLocaleString('pl-PL', { day: 'numeric', month: 'short' })
    const t1 = earliest.toLocaleString('pl-PL', { hour: '2-digit', minute: '2-digit' })
    const t2 = latest.toLocaleString('pl-PL', { hour: '2-digit', minute: '2-digit' })
    return (
      <span className="event-time">
        {t1 === t2 ? `${dayStr} ${t1}` : `${dayStr} ${t1} – ${t2}`}
      </span>
    )
  }

  // Different days
  return (
    <span className="event-time">
      {formatShort(earliest)} – {formatShort(latest)}
    </span>
  )
}
