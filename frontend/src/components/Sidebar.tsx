import type { Session } from '../api'

interface Props {
  sessions: Session[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}

export default function Sidebar({ sessions, activeId, onSelect, onNew, onDelete }: Props) {
  return (
    <div className="w-60 bg-gray-900 border-r border-gray-800 flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <span className="font-semibold text-gray-100 text-sm">R2 Autonomous</span>
        </div>
        <button
          onClick={onNew}
          className="text-gray-400 hover:text-white hover:bg-gray-800 w-7 h-7 rounded-lg flex items-center justify-center transition-colors text-lg"
          title="Nueva sesión"
        >
          +
        </button>
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto py-2">
        {sessions.length === 0 && (
          <p className="text-gray-600 text-xs text-center mt-4">Sin sesiones</p>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`group flex items-center gap-2 mx-2 mb-0.5 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
              s.id === activeId ? 'bg-violet-900/50 text-violet-200' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
            }`}
            onClick={() => onSelect(s.id)}
          >
            <span className="text-xs">💬</span>
            <span className="text-xs flex-1 truncate">{s.title}</span>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(s.id) }}
              className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all text-xs"
              title="Eliminar"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-800 text-xs text-gray-600 text-center">
        v1.1 · puerto 8234
      </div>
    </div>
  )
}
