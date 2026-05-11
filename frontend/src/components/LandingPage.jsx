import { useState } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, Zap, Brain, FolderOpen, ArrowRight } from 'lucide-react'
import './LandingPage.css'

export default function LandingPage({ onCreateWorkspace }) {
  const [name, setName] = useState('')

  const submit = (e) => {
    e.preventDefault()
    const n = name.trim() || 'My Workspace'
    onCreateWorkspace(n)
  }

  return (
    <div className="landing">
      <motion.div
        className="landing-content"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="landing-badge">
          <Sparkles size={14} />
          <span>AI-Powered Document Intelligence</span>
        </div>

        <h1 className="landing-title">
          <span className="gradient-text">DocuMind</span>
        </h1>
        <p className="landing-sub">
          Organise your documents into workspaces.<br />Ask questions across multiple files at once.
        </p>

        <div className="landing-features">
          {[
            { icon: <FolderOpen size={18} />, label: 'Workspace Collections' },
            { icon: <Brain size={18} />, label: 'Multi-Doc Reasoning' },
            { icon: <Zap size={18} />, label: 'Streaming Answers' },
          ].map(f => (
            <div key={f.label} className="landing-feature">
              {f.icon}
              <span>{f.label}</span>
            </div>
          ))}
        </div>

        <form className="landing-form" onSubmit={submit}>
          <input
            className="landing-input"
            placeholder="Name your first workspace…"
            value={name}
            onChange={e => setName(e.target.value)}
            autoFocus
          />
          <motion.button
            className="landing-btn"
            type="submit"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            Get Started
            <ArrowRight size={18} />
          </motion.button>
        </form>
      </motion.div>
    </div>
  )
}