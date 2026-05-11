import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import SourcesPanel from './components/SourcesPanel'
import LandingPage from './components/LandingPage'
import Background from './components/Background'
import './App.css'

function App() {
  const [workspaces, setWorkspaces] = useState([])         // [{id, name, docs:[]}]
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(null)
  const [appStarted, setAppStarted] = useState(false)
  const [activeSources, setActiveSources] = useState([])   // chunks from last answer
  const [highlightText, setHighlightText] = useState('')

  const activeWorkspace = workspaces.find(w => w.id === activeWorkspaceId) || null

  // ── Workspace actions ───────────────────────────────────────────────────
  const createWorkspace = (name) => {
    const id = crypto.randomUUID()
    setWorkspaces(prev => [...prev, { id, name, docs: [] }])
    setActiveWorkspaceId(id)
    setAppStarted(true)
  }

  const deleteWorkspace = async (wsId) => {
    const ws = workspaces.find(w => w.id === wsId)
    if (ws) {
      for (const doc of ws.docs) {
        await fetch(`http://localhost:8000/documents/${doc.docId}`, { method: 'DELETE' }).catch(() => {})
      }
    }
    setWorkspaces(prev => prev.filter(w => w.id !== wsId))
    if (activeWorkspaceId === wsId) {
      const remaining = workspaces.filter(w => w.id !== wsId)
      setActiveWorkspaceId(remaining[0]?.id || null)
      if (remaining.length === 0) setAppStarted(false)
    }
  }

  const renameWorkspace = (wsId, name) => {
    setWorkspaces(prev => prev.map(w => w.id === wsId ? { ...w, name } : w))
  }

  // ── Doc actions ─────────────────────────────────────────────────────────
  const addDoc = (wsId, doc) => {
    setWorkspaces(prev => prev.map(w =>
      w.id === wsId ? { ...w, docs: [...w.docs, doc] } : w
    ))
  }

  const removeDoc = async (wsId, docId) => {
    await fetch(`http://localhost:8000/documents/${docId}`, { method: 'DELETE' }).catch(() => {})
    setWorkspaces(prev => prev.map(w =>
      w.id === wsId ? { ...w, docs: w.docs.filter(d => d.docId !== docId) } : w
    ))
  }

  const renameDoc = async (wsId, docId, newName) => {
    const fd = new FormData(); fd.append('fileName', newName)
    await fetch(`http://localhost:8000/documents/${docId}/rename`, { method: 'PATCH', body: fd }).catch(() => {})
    setWorkspaces(prev => prev.map(w =>
      w.id === wsId
        ? { ...w, docs: w.docs.map(d => d.docId === docId ? { ...d, fileName: newName } : d) }
        : w
    ))
  }

  // ── Sources callback ────────────────────────────────────────────────────
  const handleAnswer = (citations) => {
    setActiveSources(citations || [])
    setHighlightText('')
  }

  if (!appStarted) {
    return (
      <>
        <Background />
        <LandingPage onCreateWorkspace={createWorkspace} />
      </>
    )
  }

  return (
    <div className="app-shell">
      <Background />
      <Sidebar
        workspaces={workspaces}
        activeWorkspaceId={activeWorkspaceId}
        onSelectWorkspace={setActiveWorkspaceId}
        onCreateWorkspace={createWorkspace}
        onDeleteWorkspace={deleteWorkspace}
        onRenameWorkspace={renameWorkspace}
        onAddDoc={addDoc}
        onRemoveDoc={removeDoc}
        onRenameDoc={renameDoc}
      />
      <main className="app-main">
        <AnimatePresence mode="wait">
          {activeWorkspace ? (
            <motion.div
              key={activeWorkspace.id}
              className="workspace-view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <ChatPanel
                workspace={activeWorkspace}
                onAnswer={handleAnswer}
                onHighlight={setHighlightText}
              />
              <SourcesPanel
                sources={activeSources}
                highlightText={highlightText}
                onHighlight={setHighlightText}
              />
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              className="empty-workspace"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <p>Select or create a workspace</p>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}

export default App