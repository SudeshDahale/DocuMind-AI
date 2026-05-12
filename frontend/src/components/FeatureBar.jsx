// frontend/src/components/FeatureBar.jsx
import { MessageSquare, BookOpen, GitCompare, FileBarChart2 } from 'lucide-react'
import './FeatureBar.css'

const MODES = [
  { id: 'chat',    label: 'Chat',    icon: MessageSquare },
  { id: 'explain', label: 'Explain', icon: BookOpen },
  { id: 'compare', label: 'Compare', icon: GitCompare },
  { id: 'report',  label: 'Report',  icon: FileBarChart2 },
]

export default function FeatureBar({ mode, onModeChange, hasDoc }) {
  return (
    <div className="feature-bar">
      {MODES.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          className={`feature-tab ${mode === id ? 'active' : ''}`}
          onClick={() => onModeChange(id)}
          disabled={!hasDoc && id !== 'chat'}
          title={!hasDoc && id !== 'chat' ? 'Add documents first' : label}
        >
          <Icon size={14} />
          <span>{label}</span>
        </button>
      ))}
    </div>
  )
}