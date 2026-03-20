/** Format ISO date as "18 mar 09:15" */
export function formatShortDate(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return d.toLocaleString('pl-PL', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Format ISO date as "18 marca 2026, 09:15" */
export function formatFullDate(iso) {
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

/** Format ISO date as "18 mar 09:15:30" (with seconds, for logs) */
export function formatLogDate(iso) {
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
