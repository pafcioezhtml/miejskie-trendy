const RELEVANCE_CONFIG = {
  high: { dots: 3, color: '#f87171', label: 'Wysoka' },
  medium: { dots: 2, color: '#fbbf24', label: 'Średnia' },
  low: { dots: 1, color: '#64748b', label: 'Niska' },
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
            backgroundColor: i <= config.dots ? config.color : 'rgba(148, 163, 184, 0.2)',
          }}
        />
      ))}
    </span>
  )
}
