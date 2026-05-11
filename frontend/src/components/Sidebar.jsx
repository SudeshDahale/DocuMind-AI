import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FolderOpen, Plus, Trash2, Pencil, Check, X,
  FileText, Upload, ChevronDown, ChevronRight, Loader2
} from 'lucide-react'
import './Sidebar.css'

export default function Sidebar({
  workspaces, activeWorkspaceId,
  onSelectWorkspace, onCreateWorkspace,
  onDeleteWorkspace, onRenameWorkspace,
  onAddDoc, onRemoveDoc, onRenameDoc,
}) {
  const [newWsName, setNewWsName] = useState('')
  const [creatingWs, setCreatingWs] = useState(false)
  const [editingWsId, setEditingWsId] = useState(null)
  const [editWsVal, setEditWsVal] = useState('')
  const [expandedWs, setExpandedWs] = useState({})
  const [uploading, setUploading] = useState(null) // wsId

  const toggleExpand = (id) => setExpandedWs(p => ({ ...p, [id]: !p[id] }))

  const submitNewWs = (e) => {
    e.preventDefault()
    if (!newWsName.trim()) return
    onCreateWorkspace(newWsName.trim())
    setNewWsName('')
    setCreatingWs(false)
  }

  const uploadFile = async (wsId, file) => {
    setUploading(wsId)
    const fd = new FormData(); fd.append('file', file)
    try {
      const res = await fetch('http://localhost:8000/upload', { method: 'POST', body: fd })
      if (!res.ok) throw new Error()
      const data = await res.json()
      onAddDoc(wsId, { docId: data.doc_id, fileName: file.name })
      setExpandedWs(p => ({ ...p, [wsId]: true }))
    } catch { /* swallow — user sees nothing added */ }
    finally { setUploading(null) }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">DocuMind</span>
        <button
          className="sidebar-new-btn"
          onClick={() => setCreatingWs(true)}
          title="New workspace"
        >
          <Plus size={16} />
        </button>
      </div>

      <AnimatePresence>
        {creatingWs && (
          <motion.form
            className="new-ws-form"
            onSubmit={submitNewWs}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <input
              autoFocus
              className="sidebar-input"
              placeholder="Workspace name…"
              value={newWsName}
              onChange={e => setNewWsName(e.target.value)}
              onKeyDown={e => e.key === 'Escape' && setCreatingWs(false)}
            />
            <button type="submit" className="icon-btn green"><Check size={14} /></button>
            <button type="button" className="icon-btn red" onClick={() => setCreatingWs(false)}><X size={14} /></button>
          </motion.form>
        )}
      </AnimatePresence>

      <nav className="sidebar-nav">
        <p className="sidebar-section-label">Workspaces</p>
        <AnimatePresence>
          {workspaces.map(ws => (
            <motion.div
              key={ws.id}
              className={`ws-item ${ws.id === activeWorkspaceId ? 'active' : ''}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
            >
              {/* Workspace row */}
              <div className="ws-row" onClick={() => { onSelectWorkspace(ws.id); toggleExpand(ws.id) }}>
                <span className="ws-chevron">
                  {expandedWs[ws.id] ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                </span>
                <FolderOpen size={15} className="ws-icon" />
                {editingWsId === ws.id ? (
                  <input
                    autoFocus
                    className="sidebar-input inline"
                    value={editWsVal}
                    onChange={e => setEditWsVal(e.target.value)}
                    onClick={e => e.stopPropagation()}
                    onKeyDown={e => {
                      if (e.key === 'Enter') { onRenameWorkspace(ws.id, editWsVal); setEditingWsId(null) }
                      if (e.key === 'Escape') setEditingWsId(null)
                    }}
                  />
                ) : (
                  <span className="ws-name">{ws.name}</span>
                )}
                <span className="ws-count">{ws.docs.length}</span>
                <div className="ws-actions" onClick={e => e.stopPropagation()}>
                  <button className="icon-btn" onClick={() => { setEditingWsId(ws.id); setEditWsVal(ws.name) }}>
                    <Pencil size={12} />
                  </button>
                  <button className="icon-btn red" onClick={() => onDeleteWorkspace(ws.id)}>
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>

              {/* Doc list */}
              <AnimatePresence>
                {expandedWs[ws.id] && (
                  <motion.div
                    className="doc-list"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    {ws.docs.map(doc => (
                      <div key={doc.docId} className="doc-row">
                        <FileText size={12} className="doc-icon" />
                        <span className="doc-name">{doc.fileName}</span>
                        <button
                          className="icon-btn red small"
                          onClick={() => onRemoveDoc(ws.id, doc.docId)}
                        >
                          <X size={11} />
                        </button>
                      </div>
                    ))}

                    {/* Upload to workspace */}
                    <label className="doc-upload-btn">
                      {uploading === ws.id
                        ? <><Loader2 size={12} className="spinning" /> Uploading…</>
                        : <><Upload size={12} /> Add document</>
                      }
                      <input
                        type="file"
                        accept=".pdf,.docx,.doc,.pptx,.ppt,.txt,.md"
                        style={{ display: 'none' }}
                        disabled={uploading === ws.id}
                        onChange={e => { if (e.target.files[0]) uploadFile(ws.id, e.target.files[0]); e.target.value = '' }}
                      />
                    </label>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </AnimatePresence>

        {workspaces.length === 0 && (
          <p className="sidebar-empty">No workspaces yet.<br />Click + to create one.</p>
        )}
      </nav>
    </aside>
  )
}