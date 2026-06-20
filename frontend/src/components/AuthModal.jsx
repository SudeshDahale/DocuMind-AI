import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './AuthModal.css'
import { Sparkles, Mail, Lock, ArrowRight, Loader2, AlertCircle, Eye, EyeOff, Brain, FolderOpen, Zap } from 'lucide-react'

export default function AuthModal({ onAuth }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) { setError('Please fill in all fields'); return }
    setError(''); setLoading(true)
    try {
      const res = await fetch(`http://localhost:8000/auth/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Authentication failed')
      localStorage.setItem('token', data.token)
      onAuth(data.token, data.user)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const switchMode = () => {
    setMode(m => m === 'login' ? 'signup' : 'login')
    setError('')
    setPassword('')
  }

  return (
    <div className="auth-shell">
      {/* Left panel — branding */}
      <div className="auth-left">
        <motion.div
          className="auth-brand"
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="auth-logo-badge">
            <Sparkles size={20} />
          </div>
          <h1 className="auth-brand-name">DocuMind</h1>
          <p className="auth-brand-sub">
            Your AI-powered document intelligence platform. Ask questions, compare documents, and extract insights instantly.
          </p>

          <div className="auth-features">
            {[
              { icon: <FolderOpen size={16} />, title: 'Workspace Collections', desc: 'Organise documents into focused workspaces' },
              { icon: <Brain size={16} />, title: 'Multi-Doc Reasoning', desc: 'Ask questions across multiple files at once' },
              { icon: <Zap size={16} />, title: 'Instant Answers', desc: 'Powered by GPT-4 with source citations' },
            ].map(f => (
              <div key={f.title} className="auth-feature-item">
                <div className="auth-feature-icon">{f.icon}</div>
                <div>
                  <div className="auth-feature-title">{f.title}</div>
                  <div className="auth-feature-desc">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Right panel — form */}
      <div className="auth-right">
        <motion.div
          className="auth-card"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={mode}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <div className="auth-card-header">
                <h2 className="auth-card-title">
                  {mode === 'login' ? 'Welcome back' : 'Create account'}
                </h2>
                <p className="auth-card-sub">
                  {mode === 'login'
                    ? 'Sign in to access your workspaces'
                    : 'Start chatting with your documents'}
                </p>
              </div>

              <form className="auth-form" onSubmit={submit}>
                <div className="auth-field">
                  <label className="auth-label">Email</label>
                  <div className="auth-input-wrap">
                    <Mail size={15} className="auth-input-icon" />
                    <input
                      type="email"
                      className="auth-input"
                      placeholder="you@example.com"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      autoFocus
                      autoComplete="email"
                    />
                  </div>
                </div>

                <div className="auth-field">
                  <label className="auth-label">Password</label>
                  <div className="auth-input-wrap">
                    <Lock size={15} className="auth-input-icon" />
                    <input
                      type={showPass ? 'text' : 'password'}
                      className="auth-input"
                      placeholder="••••••••"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                    />
                    <button
                      type="button"
                      className="auth-eye-btn"
                      onClick={() => setShowPass(s => !s)}
                      tabIndex={-1}
                    >
                      {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>

                <AnimatePresence>
                  {error && (
                    <motion.div
                      className="auth-error"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                    >
                      <AlertCircle size={14} />
                      <span>{error}</span>
                    </motion.div>
                  )}
                </AnimatePresence>

                <button className="auth-submit-btn" type="submit" disabled={loading}>
                  {loading
                    ? <><Loader2 size={16} className="auth-spinning" /> Please wait…</>
                    : <>{mode === 'login' ? 'Sign in' : 'Create account'} <ArrowRight size={16} /></>
                  }
                </button>
              </form>

              <div className="auth-switch">
                {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}
                {' '}
                <button className="auth-switch-btn" onClick={switchMode}>
                  {mode === 'login' ? 'Sign up' : 'Sign in'}
                </button>
              </div>
            </motion.div>
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  )
}