// frontend/src/components/ComparePanel.jsx
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { GitCompare, Loader2, AlertCircle, CheckCircle2, XCircle, MinusCircle, Sparkles } from 'lucide-react'
import './ComparePanel.css'

function SimilarityMeter({ score }) {
  const color = score > 70 ? '#00ffa3' : score > 40 ? '#00d4ff' : '#8b5cf6'
  return (
    <div className="similarity-meter">
      <div className="similarity-label">
        <span>Similarity Score</span>
        <span style={{ color }} className="similarity-score">{score}%</span>
      </div>
      <div className="similarity-track">
        <motion.div
          className="similarity-fill"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

const WINNER_CONFIG = {
  A:   { icon: CheckCircle2, color: '#00ffa3', label: 'Doc A' },
  B:   { icon: CheckCircle2, color: '#00d4ff', label: 'Doc B' },
  Tie: { icon: MinusCircle,  color: '#8b5cf6', label: 'Tie'   },
}

export default function ComparePanel({ workspace }) {
  const docs = workspace.docs
  const [docA, setDocA]         = useState('')
  const [docB, setDocB]         = useState('')
  const [focus, setFocus]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState(null)
  const [error, setError]       = useState(null)

  const canCompare = docA && docB && docA !== docB

  const handleCompare = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const fd = new FormData()
      fd.append('doc_id_a', docA)
      fd.append('doc_id_b', docB)
      if (focus.trim()) fd.append('focus', focus.trim())
      const res = await fetch('http://localhost:8000/compare', { method: 'POST', body: fd })
      if (!res.ok) throw new Error('Comparison failed')
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (docs.length < 2) {
    return (
      <div className="compare-empty">
        <GitCompare size={36} />
        <p>Upload at least <strong>2 documents</strong> to this workspace to compare them.</p>
        <span>{docs.length === 1 ? '1 document uploaded — need 1 more.' : 'No documents yet.'}</span>
      </div>
    )
  }

  return (
    <div className="compare-panel">
      {/* Setup */}
      <div className="compare-setup">
        <div className="compare-setup-row">
          <div className="compare-select-group">
            <label>Document A</label>
            <select value={docA} onChange={e => setDocA(e.target.value)} className="compare-select">
              <option value="">Select document…</option>
              {docs.filter(d => d.docId !== docB).map(d => (
                <option key={d.docId} value={d.docId}>{d.fileName}</option>
              ))}
            </select>
          </div>

          <div className="compare-vs-badge">VS</div>

          <div className="compare-select-group">
            <label>Document B</label>
            <select value={docB} onChange={e => setDocB(e.target.value)} className="compare-select">
              <option value="">Select document…</option>
              {docs.filter(d => d.docId !== docA).map(d => (
                <option key={d.docId} value={d.docId}>{d.fileName}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="compare-focus-row">
          <input
            className="compare-focus-input"
            placeholder="Optional: focus the comparison on a specific aspect (e.g. 'pricing', 'methodology')…"
            value={focus}
            onChange={e => setFocus(e.target.value)}
          />
          <button
            className="compare-run-btn"
            onClick={handleCompare}
            disabled={!canCompare || loading}
          >
            {loading
              ? <><Loader2 size={14} className="spinning" />Comparing…</>
              : <><Sparkles size={14} />Compare</>}
          </button>
        </div>
      </div>

      {error && (
        <div className="compare-error">
          <AlertCircle size={15} /><span>{error}</span>
        </div>
      )}

      <AnimatePresence>
        {result && (
          <motion.div className="compare-result" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>

            {/* Overview */}
            <div className="compare-overview-card">
              <div className="compare-doc-names">
                <span className="compare-doc-badge a">{result.doc_a_name}</span>
                <GitCompare size={16} className="compare-vs-icon" />
                <span className="compare-doc-badge b">{result.doc_b_name}</span>
              </div>
              <p className="compare-overview-text">{result.overview}</p>
              <SimilarityMeter score={result.similarity_score ?? 0} />
            </div>

            {/* Differences table */}
            {result.differences?.length > 0 && (
              <div className="compare-section">
                <h4 className="compare-section-title">Key Differences</h4>
                <div className="compare-diff-table">
                  <div className="compare-diff-header">
                    <span>Aspect</span>
                    <span>{result.doc_a_name}</span>
                    <span>{result.doc_b_name}</span>
                    <span>Edge</span>
                  </div>
                  {result.differences.map((d, i) => {
                    const cfg = WINNER_CONFIG[d.winner] || WINNER_CONFIG.Tie
                    const WinIcon = cfg.icon
                    return (
                      <motion.div
                        key={i}
                        className="compare-diff-row"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.04 }}
                      >
                        <span className="diff-aspect">{d.aspect}</span>
                        <span className="diff-cell">{d.doc_a}</span>
                        <span className="diff-cell">{d.doc_b}</span>
                        <span className="diff-winner" style={{ color: cfg.color }}>
                          <WinIcon size={13} />{cfg.label}
                        </span>
                      </motion.div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Similarities */}
            {result.similarities?.length > 0 && (
              <div className="compare-section">
                <h4 className="compare-section-title">Similarities</h4>
                <div className="compare-pills-grid">
                  {result.similarities.map((s, i) => (
                    <div key={i} className="compare-similarity-item">
                      <CheckCircle2 size={13} className="sim-icon" />
                      <div>
                        <strong>{s.point}</strong>
                        {s.detail && <p>{s.detail}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Unique sections */}
            <div className="compare-unique-row">
              {result.unique_to_a?.length > 0 && (
                <div className="compare-unique-card">
                  <h5>Only in {result.doc_a_name}</h5>
                  <ul>{result.unique_to_a.map((u, i) => <li key={i}><XCircle size={11} />{u}</li>)}</ul>
                </div>
              )}
              {result.unique_to_b?.length > 0 && (
                <div className="compare-unique-card b">
                  <h5>Only in {result.doc_b_name}</h5>
                  <ul>{result.unique_to_b.map((u, i) => <li key={i}><XCircle size={11} />{u}</li>)}</ul>
                </div>
              )}
            </div>

            {/* Recommendation */}
            {result.recommendation && (
              <div className="compare-recommendation">
                <Sparkles size={14} />
                <div>
                  <strong>Recommendation</strong>
                  <p>{result.recommendation}</p>
                </div>
              </div>
            )}

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}