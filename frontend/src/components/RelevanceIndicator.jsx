const RELEVANCE_CONFIG = {
  high: { dots: 3, color: '#dc2626', label: 'Wysoka' },
  medium: { dots: 2, color: '#f59e0b', label: 'Średnia' },
  low: { dots: 1, color: '#6b7280', label: 'Niska' },
}

export function RelevanceIndicator({ relevance }) {
  const config = RELEVANCE_CONFIG[relevance] || RELEVANCE_CONFIG.medium

  return (
    <span className="relevance" title={`Istotność: ${config.label}`}>
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          className="relevance-dot"
          style={{
            backgroundColor: i <= config.dots ? config.color : '#e5e7eb',
          }}
        />
      ))}
    </span>
  )
}
