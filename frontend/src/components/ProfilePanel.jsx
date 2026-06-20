import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Key, LogOut, User, CheckCircle2, AlertCircle,
  Loader2, Eye, EyeOff, Trash2, Activity, Shield
} from 'lucide-react'
import './ProfilePanel.css'

export default function ProfilePanel({ authToken, onLogout, onClose }) {
  const [keyStatus, setKeyStatus] = useState(null)
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [newKey, setNewKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => { fetchKeyStatus() }, [])

  const fetchKeyStatus = async () => {
    setLoadingStatus(true)
    try {
      const res = await fetch('http://localhost:8000/auth/apikey/status', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setKeyStatus(await res.json())
    } catch { setKeyStatus(null) }
    finally { setLoadingStatus(false) }
  }

  const flashMsg = (type, text) => {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 3500)
  }

  const saveKey = async () => {
    if (!newKey.startsWith('sk-')) { flashMsg('error', 'Key must start with sk-'); return }
    setSaving(true)
    try {
      const res = await fetch('http://localhost:8000/auth/apikey', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({ api_key: newKey }),
      })
      if (!res.ok) throw new Error()
      flashMsg('success', 'API key saved successfully')
      setNewKey('')
      await fetchKeyStatus()
    } catch { flashMsg('error', 'Failed to save key') }
    finally { setSaving(false) }
  }

  const deleteKey = async () => {
    if (!confirm('Remove your OpenAI API key? You won\'t be able to use DocuMind until you add a new one.')) return
    setDeleting(true)
    try {
      await fetch('http://localhost:8000/auth/apikey', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` }
      })
      flashMsg('success', 'API key removed')
      await fetchKeyStatus()
    } catch { flashMsg('error', 'Failed to remove key') }
    finally { setDeleting(false) }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    onLogout()
  }

  return (
    <motion.div
      className="pp-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.aside
        className="pp-panel"
        initial={{ x: -320, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: -320, opacity: 0 }}
        transition={{ type: 'spring', damping: 30, stiffness: 320 }}
        onClick={e => e.stopPropagation()}
      >
        {/* ── Header ── */}
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
            <div className="pp-section-header">
              <Key size={14} />
              <span>OpenAI API Key</span>
            </div>

            {loadingStatus ? (
              <div className="pp-loading"><Loader2 size={16} className="pp-spin" /> Loading…</div>
            ) : keyStatus?.has_key ? (
              <div className="pp-key-active">
                <div className="pp-key-active-row">
                  <CheckCircle2 size={15} className="pp-key-ok-icon" />
                  <div className="pp-key-active-info">
                    <div className="pp-key-active-label">Active key</div>
                    <div className="pp-key-masked">{keyStatus.masked_key}</div>
                  </div>
                  <button
                    className="pp-icon-danger"
                    onClick={deleteKey}
                    disabled={deleting}
                    title="Remove key"
                  >
                    {deleting ? <Loader2 size={13} className="pp-spin" /> : <Trash2 size={13} />}
                  </button>
                </div>
              </div>
            ) : (
              <div className="pp-key-missing">
                <AlertCircle size={14} />
                <span>No API key configured. Add one below to use DocuMind.</span>
              </div>
            )}

            <div className="pp-key-form">
              <p className="pp-key-form-label">
                {keyStatus?.has_key ? 'Replace key' : 'Add your key'}
              </p>
              <div className="pp-key-input-row">
                <div className="pp-input-wrap">
                  <input
                    type={showKey ? 'text' : 'password'}
                    placeholder="sk-..."
                    value={newKey}
                    onChange={e => setNewKey(e.target.value)}
                    className="pp-input mono"
                    onKeyDown={e => e.key === 'Enter' && saveKey()}
                  />
                  <button className="pp-eye" onClick={() => setShowKey(s => !s)} tabIndex={-1}>
                    {showKey ? <EyeOff size={13} /> : <Eye size={13} />}
                  </button>
                </div>
                <button
                  className="pp-save-btn"
                  onClick={saveKey}
                  disabled={saving || !newKey.trim()}
                >
                  {saving ? <Loader2 size={13} className="pp-spin" /> : 'Save'}
                </button>
              </div>
              <p className="pp-key-hint">
                <Shield size={11} /> Your key is encrypted at rest and never shared.
              </p>
            </div>

            <AnimatePresence>
              {msg && (
                <motion.div
                  className={`pp-msg pp-msg-${msg.type}`}
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                >
                  {msg.type === 'success' ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
                  {msg.text}
                </motion.div>
              )}
            </AnimatePresence>
          </section>

          {/* ── Section 2: Usage ── */}
          {keyStatus?.has_key && (
            <section className="pp-section">
              <div className="pp-section-header">
                <Activity size={14} />
                <span>Usage</span>
              </div>
              <div className="pp-stat-grid">
                <div className="pp-stat">
                  <div className="pp-stat-value">{keyStatus.total_calls?.toLocaleString() ?? 0}</div>
                  <div className="pp-stat-label">Total API calls</div>
                </div>
              </div>
            </section>
          )}

          {/* ── Section 3: Sign out ── */}
          <section className="pp-section pp-section-danger">
            <div className="pp-section-header">
              <LogOut size={14} />
              <span>Session</span>
            </div>
            <button className="pp-logout-btn" onClick={handleLogout}>
              <LogOut size={14} />
              Sign out of DocuMind
            </button>
          </section>

        </div>
      </motion.aside>
    </motion.div>
  )
}