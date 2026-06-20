import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Key, LogOut, User, CheckCircle2, AlertCircle,
  Loader2, Eye, EyeOff, Trash2, Activity, Shield, Gauge
} from 'lucide-react'
import './ProfilePanel.css'
const API = 'http://localhost:8000'

export default function ProfilePanel({ authToken, onLogout, onClose }) {
  const [keyStatus, setKeyStatus]     = useState(null)
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [newKey, setNewKey]           = useState('')
  const [showKey, setShowKey]         = useState(false)
  const [saving, setSaving]           = useState(false)
  const [deleting, setDeleting]       = useState(false)
  const [limitInput, setLimitInput]   = useState('')
  const [savingLimit, setSavingLimit] = useState(false)
  const [msg, setMsg]                 = useState(null)

  useEffect(() => { fetchKeyStatus() }, [])

  const fetchKeyStatus = async () => {
    setLoadingStatus(true)
    try {
      const res = await fetch(`${API}/auth/apikey/status`, {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      const data = await res.json()
      setKeyStatus(data)
      setLimitInput(data.token_limit > 0 ? String(data.token_limit) : '')
    } catch { setKeyStatus(null) }
    finally { setLoadingStatus(false) }
  }

  const flash = (type, text) => {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 3500)
  }

  const saveKey = async () => {
    if (!newKey.startsWith('sk-')) { flash('error', 'Key must start with sk-'); return }
    setSaving(true)
    try {
      const res = await fetch(`${API}/auth/apikey`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({ api_key: newKey }),
      })
      if (!res.ok) throw new Error()
      flash('success', 'API key saved')
      setNewKey('')
      await fetchKeyStatus()
    } catch { flash('error', 'Failed to save key') }
    finally { setSaving(false) }
  }

  const deleteKey = async () => {
    if (!confirm('Remove your OpenAI API key?')) return
    setDeleting(true)
    try {
      await fetch(`${API}/auth/apikey`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${authToken}` }
      })
      flash('success', 'API key removed')
      await fetchKeyStatus()
    } catch { flash('error', 'Failed to remove key') }
    finally { setDeleting(false) }
  }

  const saveLimit = async () => {
    const val = limitInput.trim() === '' ? 0 : parseInt(limitInput, 10)
    if (isNaN(val) || val < 0) { flash('error', 'Enter a valid number (0 = unlimited)'); return }
    setSavingLimit(true)
    try {
      const res = await fetch(`${API}/auth/apikey/limit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({ token_limit: val }),
      })
      if (!res.ok) throw new Error()
      flash('success', val === 0 ? 'Limit removed (unlimited)' : `Limit set to ${val.toLocaleString()} tokens`)
      await fetchKeyStatus()
    } catch { flash('error', 'Failed to update limit') }
    finally { setSavingLimit(false) }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    onLogout()
  }

  // Token meter calculation
  const tokensUsed  = keyStatus?.tokens_used  ?? 0
  const tokenLimit  = keyStatus?.token_limit  ?? 0
  const pct = tokenLimit > 0 ? Math.min(100, (tokensUsed / tokenLimit) * 100) : 0
  const meterColor = pct > 90 ? '#f87171' : pct > 70 ? '#fbbf24' : 'var(--accent-primary)'

  return (
    <motion.div className="pp-overlay"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      onClick={onClose}>
      <motion.aside className="pp-panel"
        initial={{ x: -340, opacity: 0 }} animate={{ x: 0, opacity: 1 }}
        exit={{ x: -340, opacity: 0 }}
        transition={{ type: 'spring', damping: 30, stiffness: 320 }}
        onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="pp-header">
          <div className="pp-avatar"><User size={20} /></div>
          <div className="pp-header-text">
            <div className="pp-header-title">Profile & Settings</div>
            <div className="pp-header-sub">Manage your account</div>
          </div>
          <button className="pp-close" onClick={onClose}><X size={16} /></button>
        </div>

        <div className="pp-body">

          {/* ── Section 1: API Key ── */}
          <section className="pp-section">
            <div className="pp-section-header"><Key size={13} /><span>OpenAI API Key</span></div>

            {loadingStatus ? (
              <div className="pp-loading"><Loader2 size={15} className="pp-spin" /> Loading…</div>
            ) : keyStatus?.has_key ? (
              <div className="pp-key-active">
                <CheckCircle2 size={14} className="pp-key-ok-icon" />
                <div className="pp-key-active-info">
                  <div className="pp-key-active-label">Active key</div>
                  <div className="pp-key-masked">{keyStatus.masked_key}</div>
                </div>
                <button className="pp-icon-danger" onClick={deleteKey} disabled={deleting} title="Remove">
                  {deleting ? <Loader2 size={13} className="pp-spin" /> : <Trash2 size={13} />}
                </button>
              </div>
            ) : (
              <div className="pp-key-missing">
                <AlertCircle size={13} />
                <span>No API key — add one below to use DocuMind.</span>
              </div>
            )}

            <div className="pp-key-form">
              <div className="pp-key-input-row">
                <div className="pp-input-wrap">
                  <input
                    type={showKey ? 'text' : 'password'}
                    placeholder={keyStatus?.has_key ? 'Replace key (sk-...)' : 'sk-...'}
                    value={newKey}
                    onChange={e => setNewKey(e.target.value)}
                    className="pp-input mono"
                    onKeyDown={e => e.key === 'Enter' && saveKey()}
                  />
                  <button className="pp-eye" onClick={() => setShowKey(s => !s)} tabIndex={-1}>
                    {showKey ? <EyeOff size={13} /> : <Eye size={13} />}
                  </button>
                </div>
                <button className="pp-save-btn" onClick={saveKey} disabled={saving || !newKey.trim()}>
                  {saving ? <Loader2 size={13} className="pp-spin" /> : 'Save'}
                </button>
              </div>
              <div className="pp-key-hint"><Shield size={11} /> Encrypted at rest, never shared.</div>
            </div>

            <AnimatePresence>
              {msg && (
                <motion.div className={`pp-msg pp-msg-${msg.type}`}
                  initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  {msg.type === 'success' ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
                  {msg.text}
                </motion.div>
              )}
            </AnimatePresence>
          </section>

          {/* ── Section 2: Token Usage ── */}
          {keyStatus?.has_key && (
            <section className="pp-section">
              <div className="pp-section-header"><Activity size={13} /><span>Token Usage</span></div>

              <div className="pp-stats-row">
                <div className="pp-stat-box">
                  <div className="pp-stat-val">{tokensUsed.toLocaleString()}</div>
                  <div className="pp-stat-lbl">Tokens used</div>
                </div>
                <div className="pp-stat-box">
                  <div className="pp-stat-val">{keyStatus.total_calls?.toLocaleString()}</div>
                  <div className="pp-stat-lbl">API calls</div>
                </div>
                <div className="pp-stat-box">
                  <div className="pp-stat-val" style={{ color: tokenLimit > 0 ? meterColor : 'var(--text-muted)' }}>
                    {tokenLimit > 0 ? tokenLimit.toLocaleString() : '∞'}
                  </div>
                  <div className="pp-stat-lbl">Token limit</div>
                </div>
              </div>

              {tokenLimit > 0 && (
                <div className="pp-meter-wrap">
                  <div className="pp-meter-bar">
                    <motion.div
                      className="pp-meter-fill"
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.6, ease: 'easeOut' }}
                      style={{ background: meterColor }}
                    />
                  </div>
                  <div className="pp-meter-labels">
                    <span style={{ color: meterColor }}>{pct.toFixed(1)}% used</span>
                    <span className="pp-meter-remaining">
                      {Math.max(0, tokenLimit - tokensUsed).toLocaleString()} remaining
                    </span>
                  </div>
                  {pct > 90 && (
                    <div className="pp-meter-warning">
                      <AlertCircle size={12} /> Token limit nearly reached
                    </div>
                  )}
                </div>
              )}

              {/* Token limit setter */}
              <div className="pp-limit-block">
                <div className="pp-limit-label">
                  <Gauge size={12} /> Set token limit
                </div>
                <div className="pp-key-input-row">
                  <input
                    type="number"
                    min="0"
                    placeholder="e.g. 100000  (leave blank = unlimited)"
                    value={limitInput}
                    onChange={e => setLimitInput(e.target.value)}
                    className="pp-input"
                    style={{ flex: 1 }}
                  />
                  <button className="pp-save-btn" onClick={saveLimit} disabled={savingLimit}>
                    {savingLimit ? <Loader2 size={13} className="pp-spin" /> : 'Set'}
                  </button>
                </div>
                <div className="pp-key-hint">Leave blank or set 0 for unlimited usage.</div>
              </div>
            </section>
          )}

          {/* ── Section 3: Sign out ── */}
          <section className="pp-section pp-section-danger">
            <div className="pp-section-header"><LogOut size={13} /><span>Session</span></div>
            <button className="pp-logout-btn" onClick={handleLogout}>
              <LogOut size={14} /> Sign out of DocuMind
            </button>
          </section>

        </div>
      </motion.aside>
    </motion.div>
  )
}