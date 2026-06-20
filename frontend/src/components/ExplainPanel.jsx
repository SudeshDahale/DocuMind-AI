// frontend/src/components/ExplainPanel.jsx
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, ChevronDown, ChevronUp, Sparkles, Loader2, AlertCircle, Star } from 'lucide-react'
import './ExplainPanel.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const DIFFICULTY_COLORS = {
  Beginner:     { bg: 'rgba(0,255,163,0.1)',  border: 'rgba(0,255,163,0.3)',  text: '#00ffa3' },
  Intermediate: { bg: 'rgba(0,212,255,0.1)',  border: 'rgba(0,212,255,0.3)',  text: '#00d4ff' },
  Advanced:     { bg: 'rgba(139,92,246,0.1)', border: 'rgba(139,92,246,0.3)', text: '#8b5cf6' },
}

function SectionCard({ section, index }) {
  const [open, setOpen] = useState(index === 0)
  const colors = DIFFICULTY_COLORS[section.difficulty] || DIFFICULTY_COLORS.Intermediate

  return (
    <motion.div
      className="explain-section-card"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <button className="explain-section-header" onClick={() => setOpen(o => !o)}>
        <div className="explain-section-title-row">
          <span className="explain-section-num">{index + 1}</span>
          <span className="explain-section-title">{section.title}</span>
        </div>
        <div className="explain-section-meta">
          <span
            className="explain-difficulty-badge"
            style={{ background: colors.bg, borderColor: colors.border, color: colors.text }}
          >
            {section.difficulty}
          </span>
          {section.page_hint && (
            <span className="explain-page-hint">{section.page_hint}</span>
          )}
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="explain-section-body"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <p className="explain-section-explanation">{section.explanation}</p>
            {section.key_takeaways?.length > 0 && (
              <div className="explain-takeaways">
                <span className="explain-takeaways-label">Key Takeaways</span>
                <ul>
                  {section.key_takeaways.map((t, i) => (
                    <li key={i}><Star size={10} />{t}</li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function ExplainPanel({ workspace }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [error, setError]     = useState(null)

  const hasDoc = workspace.docs.length > 0
  const docIds = workspace.docs.map(d => d.docId).join(',')

  const handleExplain = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const fd = new FormData()
      fd.append('doc_ids', docIds)
      const token = localStorage.getItem('token')
      const res = await fetch(`${API}/explain`, {
        method: 'POST',
        body: fd,
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to explain document')
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (!hasDoc) {
    return (
      <div className="explain-empty">
        <BookOpen size={36} />
        <p>Add documents to this workspace to use Explain mode.</p>
      </div>
    )
  }

  return (
    <div className="explain-panel">
      <div className="explain-intro">
        <div className="explain-intro-text">
          <h3>Document Tutor</h3>
          <p>Get a section-by-section breakdown of your document with plain-English explanations and key takeaways.</p>
        </div>
        <button
          className="explain-run-btn"
          onClick={handleExplain}
          disabled={loading}
        >
          {loading ? <><Loader2 size={14} className="spinning" /> Analyzing…</> : <><Sparkles size={14} /> Explain Document</>}
        </button>
      </div>

      {error && (
        <div className="explain-error">
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      <AnimatePresence>
        {result && (
          <motion.div
            className="explain-result"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="explain-overview-card">
              <div className="explain-overview-header">
                <BookOpen size={15} />
                <span>Document Overview</span>
                <span className="explain-section-count">{result.total_sections} sections</span>
              </div>
              <p className="explain-overview-text">{result.document_summary}</p>
            </div>

            <div className="explain-sections-list">
              {result.sections?.map((section, i) => (
                <SectionCard key={i} section={section} index={i} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {!loading && !result && !error && (
        <div className="explain-placeholder">
          <p>Click "Explain Document" to get an AI-powered breakdown.</p>
          <p className="explain-docs-list">{workspace.docs.map(d => d.fileName).join(' · ')}</p>
        </div>
      )}
    </div>
  )
}