const CATEGORY_COLORS = {
  transport: { bg: '#dbeafe', text: '#1e40af' },
  inwestycje: { bg: '#d1fae5', text: '#065f46' },
  protest: { bg: '#fee2e2', text: '#991b1b' },
  kultura: { bg: '#ede9fe', text: '#5b21b6' },
  infrastruktura: { bg: '#fef3c7', text: '#92400e' },
  pogoda: { bg: '#e0f2fe', text: '#0369a1' },
  polityka_lokalna: { bg: '#fce7f3', text: '#9d174d' },
  bezpieczenstwo: { bg: '#fee2e2', text: '#dc2626' },
  inne: { bg: '#f3f4f6', text: '#374151' },
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
