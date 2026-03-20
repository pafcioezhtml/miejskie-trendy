import { useState, useEffect } from 'react'
import { X } from 'lucide-react'

export function SettingsDialog({ open, onClose }) {
  const [settings, setSettings] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (open) {
      fetch('/api/settings')
        .then((r) => r.json())
        .then(setSettings)
        .catch((e) => setError(e.message))
    }
  }, [open])

  if (!open) return null

  const handleChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
    setSuccess(false)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setSuccess(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h2>Ustawienia</h2>
          <button className="dialog-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {!settings ? (
          <p className="dialog-loading">Ładowanie...</p>
        ) : (
          <div className="dialog-body">
            <section className="settings-section">
              <h3>Odświeżanie</h3>

              <label className="settings-row">
                <span>Automatyczne odświeżanie</span>
                <select
                  value={settings.update_enabled}
                  onChange={(e) => handleChange('update_enabled', e.target.value)}
                >
                  <option value="true">Włączone</option>
                  <option value="false">Wyłączone</option>
                </select>
              </label>

              <label className="settings-row">
                <span>Interwał (minuty)</span>
                <input
                  type="number"
                  min="5"
                  max="1440"
                  value={settings.update_interval_minutes}
                  onChange={(e) =>
                    handleChange('update_interval_minutes', e.target.value)
                  }
                  disabled={settings.update_enabled !== 'true'}
                />
              </label>
            </section>

            <section className="settings-section">
              <h3>Klucze API</h3>

              <label className="settings-row">
                <span>Anthropic API Key</span>
                <input
                  type="password"
                  value={settings.anthropic_api_key}
                  onChange={(e) =>
                    handleChange('anthropic_api_key', e.target.value)
                  }
                  placeholder="sk-ant-..."
                />
              </label>

              <label className="settings-row">
                <span>Wykop Key</span>
                <input
                  type="password"
                  value={settings.wykop_key}
                  onChange={(e) => handleChange('wykop_key', e.target.value)}
                  placeholder="Opcjonalne"
                />
              </label>

              <label className="settings-row">
                <span>Wykop Secret</span>
                <input
                  type="password"
                  value={settings.wykop_secret}
                  onChange={(e) => handleChange('wykop_secret', e.target.value)}
                  placeholder="Opcjonalne"
                />
              </label>
            </section>

            {error && <p className="settings-error">Błąd: {error}</p>}
            {success && <p className="settings-success">Zapisano</p>}

            <div className="dialog-footer">
              <button className="btn-secondary" onClick={onClose}>
                Anuluj
              </button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Zapisywanie...' : 'Zapisz'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
