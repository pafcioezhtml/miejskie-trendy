const CATEGORY_COLORS = {
  transport: { bg: 'rgba(59, 130, 246, 0.15)', text: '#60a5fa' },
  inwestycje: { bg: 'rgba(34, 197, 94, 0.15)', text: '#4ade80' },
  protest: { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171' },
  kultura: { bg: 'rgba(168, 85, 247, 0.15)', text: '#c084fc' },
  infrastruktura: { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24' },
  pogoda: { bg: 'rgba(6, 182, 212, 0.15)', text: '#22d3ee' },
  polityka_lokalna: { bg: 'rgba(236, 72, 153, 0.15)', text: '#f472b6' },
  bezpieczenstwo: { bg: 'rgba(239, 68, 68, 0.15)', text: '#fb923c' },
  inne: { bg: 'rgba(148, 163, 184, 0.15)', text: '#94a3b8' },
}

const CATEGORY_LABELS = {
  transport: 'Transport',
  inwestycje: 'Inwestycje',
  protest: 'Protest',
  kultura: 'Kultura',
  infrastruktura: 'Infrastruktura',
  pogoda: 'Pogoda',
  polityka_lokalna: 'Polityka lokalna',
  bezpieczenstwo: 'Bezpieczeństwo',
  inne: 'Inne',
}

export function CategoryBadge({ category }) {
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.inne
  const label = CATEGORY_LABELS[category] || category

  return (
    <span
      className="category-badge"
      style={{ backgroundColor: colors.bg, color: colors.text }}
    >
      {label}
    </span>
  )
}
