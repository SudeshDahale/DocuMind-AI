import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, Sparkles, User, BookOpen,
  ChevronDown, ChevronUp, Download,
  Zap, Hash, Clock, RotateCcw, FileText
} from 'lucide-react'
import './ChatPanel.css'

// ── Sub-components ────────────────────────────────────────────────────────────

function UsageBar({ usage, queryType }) {
  if (!usage) return null
  return (
    <div className="usage-bar">
      {queryType && <span className="usage-pill type"><Zap size={10} />{queryType}</span>}
      {usage.latency_ms && (
        <span className="usage-pill latency">
          <Clock size={10} />
          {usage.latency_ms < 1000 ? `${usage.latency_ms}ms` : `${(usage.latency_ms / 1000).toFixed(1)}s`}
        </span>
      )}
      {usage.total_tokens && (
        <span className="usage-pill tokens"><Hash size={10} />{usage.total_tokens.toLocaleString()} tokens</span>
      )}
    </div>
  )
}

function CitationCard({ citations, onHighlight }) {
  const [open, setOpen] = useState(false)
  if (!citations?.length) return null
  return (
    <div className="citations-wrapper">
      <button className="citations-toggle" onClick={() => setOpen(o => !o)}>
        <BookOpen size={13} />
        <span>{citations.length} source{citations.length > 1 ? 's' : ''}</span>
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="citations-list"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            {citations.map((c, i) => (
              <div
                key={i}
                className="citation-card"
                onClick={() => onHighlight?.(c.snippet)}
              >
                <div className="citation-header">
                  <FileText size={12} />
                  <span className="citation-file">{c.fileName}</span>
                  <span className="citation-page">p.{c.page}</span>
                </div>
                <p className="citation-snippet">"{c.snippet?.slice(0, 160)}{c.snippet?.length > 160 ? '…' : ''}"</p>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ChatPanel({ workspace, onAnswer, onHighlight }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const docIds = workspace.docs.map(d => d.docId).join(',')
  const hasDoc = workspace.docs.length > 0

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, streamingText])
  useEffect(() => { setMessages([]); setStreamingText('') }, [workspace.id])
  useEffect(() => { inputRef.current?.focus() }, [workspace.id])

  const exportChat = () => {
    if (!messages.length) return
    const txt = messages.map(m =>
      `[${m.role === 'user' ? 'You' : 'DocuMind'}]\n${m.content}\n`
    ).join('\n---\n\n')
    const blob = new Blob([txt], { type: 'text/plain' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = `${workspace.name}-chat.txt`; a.click()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || streaming || !hasDoc) return

    const question = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setStreaming(true)
    setStreamingText('')

    try {
      const fd = new FormData()
      fd.append('doc_ids', docIds)
      fd.append('question', question)
      fd.append('history', JSON.stringify(messages.map(m => ({ role: m.role, content: m.content }))))

      const res = await fetch('http://localhost:8000/ask', { method: 'POST', body: fd })
      if (!res.ok) throw new Error('Request failed')

      const data = await res.json()
      const fullText = data.answer || ''

      // Simulate streaming by revealing text progressively
      let i = 0
      const tick = () => {
        i += Math.ceil(Math.random() * 6) + 4
        setStreamingText(fullText.slice(0, i))
        if (i < fullText.length) {
          setTimeout(tick, 18)
        } else {
          setStreamingText('')
          setStreaming(false)
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: fullText,
            citations: data.citations || [],
            usage: data.usage || null,
            queryType: data.query_type || null,
          }])
          onAnswer?.(data.citations || [])
        }
      }
      setTimeout(tick, 80)

    } catch (err) {
      setStreaming(false)
      setStreamingText('')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Something went wrong. Please try again.',
        citations: [], usage: null, queryType: null,
      }])
    }
  }

  return (
    <div className="chat-panel">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="chat-ws-name">{workspace.name}</span>
          <span className="chat-doc-count">{workspace.docs.length} doc{workspace.docs.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="chat-header-right">
          {messages.length > 0 && (
            <button className="header-btn" onClick={exportChat}>
              <Download size={15} /> Export
            </button>
          )}
          <button className="header-btn" onClick={() => setMessages([])}>
            <RotateCcw size={15} /> Clear
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {!hasDoc && (
          <div className="chat-empty">
            <Sparkles size={36} />
            <p>Add documents to this workspace to start chatting.</p>
          </div>
        )}
        {hasDoc && messages.length === 0 && !streaming && (
          <div className="chat-empty">
            <Sparkles size={36} />
            <h3>Ask anything about your documents</h3>
            <p>{workspace.docs.map(d => d.fileName).join(' · ')}</p>
          </div>
        )}

        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              className={`message ${msg.role}`}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
            >
              <div className="msg-avatar">
                {msg.role === 'user' ? <User size={15} /> : <Sparkles size={15} />}
              </div>
              <div className="msg-body">
                <div className="msg-text">{msg.content}</div>
                {msg.role === 'assistant' && (
                  <>
                    <UsageBar usage={msg.usage} queryType={msg.queryType} />
                    <CitationCard citations={msg.citations} onHighlight={onHighlight} />
                  </>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Streaming bubble */}
        {streaming && (
          <motion.div
            className="message assistant"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="msg-avatar"><Sparkles size={15} /></div>
            <div className="msg-body">
              <div className="msg-text streaming">
                {streamingText || (
                  <span className="typing-dots">
                    <span /><span /><span />
                  </span>
                )}
                {streamingText && <span className="cursor-blink" />}
              </div>
            </div>
          </motion.div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={hasDoc ? `Ask across ${workspace.docs.length} document${workspace.docs.length > 1 ? 's' : ''}…` : 'Add documents first…'}
          disabled={streaming || !hasDoc}
        />
        <button
          type="submit"
          className="send-btn"
          disabled={!input.trim() || streaming || !hasDoc}
        >
          <Send size={17} />
        </button>
      </form>
    </div>
  )
}