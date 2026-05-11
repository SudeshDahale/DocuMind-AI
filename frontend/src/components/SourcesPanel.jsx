import { motion, AnimatePresence } from 'framer-motion'
import { FileText, Search, BookOpen } from 'lucide-react'
import './SourcesPanel.css'

function highlight(text, query) {
  if (!query || !text) return text
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark className="hl">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}

export default function SourcesPanel({ sources, highlightText, onHighlight }) {
  return (
    <aside className="sources-panel">
      <div className="sources-header">
        <BookOpen size={15} />
        <span>Sources</span>
        {sources.length > 0 && <span className="sources-count">{sources.length}</span>}
      </div>

      <div className="sources-body">
        <AnimatePresence mode="wait">
          {sources.length === 0 ? (
            <motion.div
              key="empty"
              className="sources-empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Search size={28} />
              <p>Retrieved chunks will appear here after you ask a question.</p>
            </motion.div>
          ) : (
            <motion.div
              key="list"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="sources-list"
            >
              {sources.map((src, i) => (
                <motion.div
                  key={i}
                  className={`source-card ${highlightText && src.snippet?.toLowerCase().includes(highlightText.toLowerCase()) ? 'highlighted' : ''}`}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  onClick={() => onHighlight?.(highlightText === src.snippet ? '' : src.snippet)}
                >
                  <div className="source-meta">
                    <FileText size={12} />
                    <span className="source-file">{src.fileName}</span>
                    <span className="source-page">p.{src.page}</span>
                  </div>
                  <p className="source-text">
                    {highlight(src.snippet, highlightText)}
                  </p>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </aside>
  )
}