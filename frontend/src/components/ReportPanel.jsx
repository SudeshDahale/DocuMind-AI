// frontend/src/components/ReportPanel.jsx
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileBarChart2, Loader2, AlertCircle, Sparkles, Download, ChevronDown, ChevronUp, CheckCircle2, Lightbulb, Clock, Type } from 'lucide-react'
import './ReportPanel.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const REPORT_TYPES = [
  { id: 'executive', label: 'Executive',  desc: 'High-level for stakeholders'  },
  { id: 'technical', label: 'Technical',  desc: 'In-depth with data points'    },
  { id: 'summary',   label: 'Summary',    desc: 'Comprehensive all-audience'   },
]

function SectionBlock({ section, index }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="report-section-block">
      <button className="report-section-toggle" onClick={() => setOpen(o => !o)}>
        <span className="report-section-heading">{section.heading}</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="report-section-content"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <p>{section.content}</p>
            {section.highlights?.length > 0 && (
              <ul className="report-highlights">
                {section.highlights.map((h, i) => (
                  <li key={i}><CheckCircle2 size={12} />{h}</li>
                ))}
              </ul>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function ReportPanel({ workspace }) {
  const [reportType, setReportType]     = useState('executive')
  const [instructions, setInstructions] = useState('')
  const [loading, setLoading]           = useState(false)
  const [result, setResult]             = useState(null)
  const [error, setError]               = useState(null)

  const hasDoc = workspace.docs.length > 0
  const docIds = workspace.docs.map(d => d.docId).join(',')

  const handleGenerate = async () => {
  setLoading(true)
  setError(null)
  setResult(null)
  try {
    const fd = new FormData()
    fd.append('doc_ids', docIds)
    fd.append('report_type', reportType)
    if (instructions.trim()) fd.append('custom_instructions', instructions.trim())
    const token = localStorage.getItem('token')
    const res = await fetch(`${API}/report`, {
      method: 'POST',
      body: fd,
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('Report generation failed')
    setResult(await res.json())
  } catch (e) {
    setError(e.message)
  } finally {
    setLoading(false)
  }
}

  const handleDownload = () => {
    if (!result) return
    const lines = [
      result.title,
      '='.repeat(result.title.length),
      '',
      'EXECUTIVE SUMMARY',
      '-'.repeat(18),
      result.executive_summary,
      '',
      ...result.sections.flatMap(s => [
        s.heading.toUpperCase(),
        '-'.repeat(s.heading.length),
        s.content,
        ...(s.highlights?.map(h => `• ${h}`) || []),
        '',
      ]),
      'KEY FINDINGS',
      '-'.repeat(12),
      ...(result.key_findings?.map(f => `• ${f}`) || []),
      '',
      'RECOMMENDATIONS',
      '-'.repeat(15),
      ...(result.recommendations?.map(r => `• ${r}`) || []),
      '',
      'CONCLUSION',
      '-'.repeat(10),
      result.conclusion,
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${result.title.replace(/[^a-z0-9]/gi, '_')}.txt`
    a.click()
  }

  if (!hasDoc) {
    return (
      <div className="report-empty">
        <FileBarChart2 size={36} />
        <p>Add documents to this workspace to generate reports.</p>
      </div>
    )
  }

  return (
    <div className="report-panel">
      {/* Setup */}
      <div className="report-setup">
        <div className="report-type-selector">
          {REPORT_TYPES.map(t => (
            <button
              key={t.id}
              className={`report-type-btn ${reportType === t.id ? 'active' : ''}`}
              onClick={() => setReportType(t.id)}
            >
              <span className="report-type-label">{t.label}</span>
              <span className="report-type-desc">{t.desc}</span>
            </button>
          ))}
        </div>

        <textarea
          className="report-instructions"
          placeholder="Optional: custom instructions (e.g. 'Focus on risk factors', 'Use formal tone', 'Include a SWOT section')…"
          value={instructions}
          onChange={e => setInstructions(e.target.value)}
          rows={2}
        />

        <button
          className="report-generate-btn"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading
            ? <><Loader2 size={14} className="spinning" />Generating Report…</>
            : <><Sparkles size={14} />Generate Report</>}
        </button>
      </div>

      {error && (
        <div className="report-error">
          <AlertCircle size={15} /><span>{error}</span>
        </div>
      )}

      <AnimatePresence>
        {result && (
          <motion.div className="report-result" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>

            {/* Title + meta */}
            <div className="report-title-card">
              <div className="report-title-row">
                <h2 className="report-title">{result.title}</h2>
                <button className="report-download-btn" onClick={handleDownload}>
                  <Download size={14} /> Download
                </button>
              </div>
              <div className="report-meta">
                <span><Type size={12} />{result.report_type} report</span>
                {result.metadata?.reading_time_minutes && (
                  <span><Clock size={12} />{result.metadata.reading_time_minutes} min read</span>
                )}
                {result.metadata?.confidence_score && (
                  <span><Sparkles size={12} />{result.metadata.confidence_score}% confidence</span>
                )}
              </div>
            </div>

            {/* Executive Summary */}
            <div className="report-exec-summary">
              <h4>Executive Summary</h4>
              <p>{result.executive_summary}</p>
            </div>

            {/* Sections */}
            {result.sections?.length > 0 && (
              <div className="report-sections">
                {result.sections.map((s, i) => (
                  <SectionBlock key={i} section={s} index={i} />
                ))}
              </div>
            )}

            {/* Key Findings + Recommendations */}
            <div className="report-findings-row">
              {result.key_findings?.length > 0 && (
                <div className="report-findings-card">
                  <h4><Sparkles size={13} />Key Findings</h4>
                  <ul>
                    {result.key_findings.map((f, i) => (
                      <li key={i}><CheckCircle2 size={12} />{f}</li>
                    ))}
                  </ul>
                </div>
              )}
              {result.recommendations?.length > 0 && (
                <div className="report-rec-card">
                  <h4><Lightbulb size={13} />Recommendations</h4>
                  <ul>
                    {result.recommendations.map((r, i) => (
                      <li key={i}><CheckCircle2 size={12} />{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Conclusion */}
            {result.conclusion && (
              <div className="report-conclusion">
                <h4>Conclusion</h4>
                <p>{result.conclusion}</p>
              </div>
            )}

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}