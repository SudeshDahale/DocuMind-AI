import { useState, useEffect, useCallback, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import SourcesPanel from './components/SourcesPanel'
import LandingPage from './components/LandingPage'
import Background from './components/Background'
import AuthModal from './components/AuthModal'
import ProfilePanel from './components/ProfilePanel'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [workspaces, setWorkspaces]         = useState([])
  const [activeWorkspaceId, setActiveWorkspaceId] = useState(null)
  const [appStarted, setAppStarted]         = useState(false)
  const [activeSources, setActiveSources]   = useState([])
  const [highlightText, setHighlightText]   = useState('')
  const [authToken, setAuthToken]           = useState(() => localStorage.getItem('token'))
  const [showProfile, setShowProfile]       = useState(false)
  const [wsLoaded, setWsLoaded]             = useState(false)
  const saveTimer = useRef(null)

  const activeWorkspace = workspaces.find(w => w.id === activeWorkspaceId) || null

  // ── Load workspaces from server on login ────────────────────────────────
  useEffect(() => {
    if (!authToken || wsLoaded) return
    ;(async () => {
      try {
        const res = await fetch(`${API}/auth/workspaces/load`, {
          headers: { Authorization: `Bearer ${authToken}` }
        })
        if (!res.ok) return
        const data = await res.json()
        if (data.workspaces?.length) {
          setWorkspaces(data.workspaces)
          setActiveWorkspaceId(data.workspaces[0].id)
          setAppStarted(true)
        }
      } catch {}
      finally { setWsLoaded(true) }
    })()
  }, [authToken])

  // ── Auto-save workspaces to server (debounced 1.5s) ─────────────────────
  const persistWorkspaces = useCallback((wsList) => {
    if (!authToken || !wsLoaded) return
    clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(async () => {
      try {
        await fetch(`${API}/auth/workspaces/save`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authToken}`,
          },
          body: JSON.stringify({ workspaces: wsList }),
        })
      } catch {}
    }, 1500)
  }, [authToken, wsLoaded])

  // Save whenever workspaces change
  useEffect(() => {
    if (wsLoaded && workspaces.length > 0) persistWorkspaces(workspaces)
  }, [workspaces, wsLoaded])

  // ── Auth ────────────────────────────────────────────────────────────────
  const handleAuth = (token) => {
    setAuthToken(token)
    setWsLoaded(false)
  }

  const handleLogout = () => {
    setAuthToken(null)
    setWorkspaces([])
    setActiveWorkspaceId(null)
    setAppStarted(false)
    setShowProfile(false)
    setWsLoaded(false)
    localStorage.removeItem('token')
  }

  // ── Workspace actions ───────────────────────────────────────────────────
  const createWorkspace = (name) => {
    const id = crypto.randomUUID()
    const updated = [...workspaces, { id, name, docs: [] }]
    setWorkspaces(updated)
    setActiveWorkspaceId(id)
    setAppStarted(true)
  }

  const deleteWorkspace = async (wsId) => {
    const ws = workspaces.find(w => w.id === wsId)
    if (ws) {
      for (const doc of ws.docs) {
        await fetch(`${API}/documents/${doc.docId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${authToken}` }
        }).catch(() => {})
      }
    }
    const updated = workspaces.filter(w => w.id !== wsId)
    setWorkspaces(updated)
    if (activeWorkspaceId === wsId) {
      setActiveWorkspaceId(updated[0]?.id || null)
      if (updated.length === 0) setAppStarted(false)
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
    await fetch(`${API}/documents/${docId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${authToken}` }
    }).catch(() => {})
    setWorkspaces(prev => prev.map(w =>
      w.id === wsId ? { ...w, docs: w.docs.filter(d => d.docId !== docId) } : w
    ))
  }

  const renameDoc = async (wsId, docId, newName) => {
    const fd = new FormData(); fd.append('fileName', newName)
    await fetch(`${API}/documents/${docId}/rename`, {
      method: 'PATCH', body: fd,
      headers: { Authorization: `Bearer ${authToken}` }
    }).catch(() => {})
    setWorkspaces(prev => prev.map(w =>
      w.id === wsId
        ? { ...w, docs: w.docs.map(d => d.docId === docId ? { ...d, fileName: newName } : d) }
        : w
    ))
  }

  const handleAnswer = (citations) => {
    setActiveSources(citations || [])
    setHighlightText('')
  }

  // ── Render ──────────────────────────────────────────────────────────────
  if (!authToken) {
    return <><Background /><AuthModal onAuth={handleAuth} /></>
  }

  if (!appStarted && wsLoaded) {
    return (
      <>
        <Background />
        <LandingPage onCreateWorkspace={createWorkspace} />
        <AnimatePresence>
          {showProfile && (
            <ProfilePanel authToken={authToken} onLogout={handleLogout} onClose={() => setShowProfile(false)} />
          )}
        </AnimatePresence>
      </>
    )
  }

  if (!wsLoaded) {
    return (
      <>
        <Background />
        <div style={{ height:'100vh', display:'flex', alignItems:'center', justifyContent:'center', color:'var(--text-muted)', gap:12 }}>
          <div className="pp-spin" style={{ width:20, height:20, border:'2px solid var(--border-color)', borderTopColor:'var(--accent-primary)', borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
          Loading your workspaces…
        </div>
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
        onOpenProfile={() => setShowProfile(true)}
      />
      <main className="app-main">
        <AnimatePresence mode="wait">
          {activeWorkspace ? (
            <motion.div key={activeWorkspace.id} className="workspace-view"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}>
              <ChatPanel workspace={activeWorkspace} onAnswer={handleAnswer}
                onHighlight={setHighlightText} authToken={authToken} />
              <SourcesPanel sources={activeSources} highlightText={highlightText}
                onHighlight={setHighlightText} />
            </motion.div>
          ) : (
            <motion.div key="empty" className="empty-workspace"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <p>Select or create a workspace</p>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <AnimatePresence>
        {showProfile && (
          <ProfilePanel authToken={authToken} onLogout={handleLogout} onClose={() => setShowProfile(false)} />
        )}
      </AnimatePresence>
    </div>
  )
}

export default App