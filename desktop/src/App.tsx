import { useEffect, useState } from 'react'
import { getHubInfo, type AgentInfo } from './api'
import Dashboard from './views/Dashboard'
import CreateWizard from './views/CreateWizard'
import AgentDetail from './views/AgentDetail'
import LogsView from './views/LogsView'
import './index.css'

type View =
  | { name: 'dashboard' }
  | { name: 'create' }
  | { name: 'detail'; agent: AgentInfo }
  | { name: 'logs'; agent: AgentInfo }

// El chat abre en su propia ventana NATIVA de Tauri (fuera del Hub), así se
// pueden tener varios agentes en pantalla a la vez. Reusa la ventana por agente.
// Fallback a window.open solo si se corre fuera de Tauri (dev en navegador).
async function openChatWindow(a: AgentInfo) {
  const label = `chat_${a.name}`
  const url = `index.html?view=chat&agent=${encodeURIComponent(a.name)}`
  const isTauri = '__TAURI_INTERNALS__' in window

  if (!isTauri) {
    window.open(`?view=chat&agent=${encodeURIComponent(a.name)}`, label, 'popup=yes,width=440,height=680')
    return
  }

  const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow')
  const existing = await WebviewWindow.getByLabel(label)
  if (existing) {
    await existing.setFocus()
    return
  }
  const win = new WebviewWindow(label, {
    url,
    title: `Chat · ${a.name}`,
    width: 440,
    height: 680,
    resizable: true,
  })
  win.once('tauri://error', (e) => console.error('No se pudo abrir la ventana de chat:', e))
}

const NAV = [
  { key: 'dashboard', icon: '🏠', label: 'Dashboard' },
  { key: 'create', icon: '➕', label: 'Crear Agente' },
] as const

export default function App() {
  const [view, setView] = useState<View>({ name: 'dashboard' })
  const [hubUp, setHubUp] = useState<boolean | null>(null)

  useEffect(() => {
    const ping = () =>
      getHubInfo()
        .then(() => setHubUp(true))
        .catch(() => setHubUp(false))
    ping()
    const id = setInterval(ping, 10000)
    return () => clearInterval(id)
  }, [])

  const goDash = () => setView({ name: 'dashboard' })

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-800 bg-slate-900/40 p-4">
        <div className="mb-6 flex items-center gap-2 px-1">
          <span className="text-2xl">🤖</span>
          <div>
            <h1 className="text-sm font-bold text-slate-100">R2 Hub</h1>
            <p className="text-[11px] text-slate-500">AgentOS v2.0</p>
          </div>
        </div>

        <nav className="flex flex-col gap-1">
          {NAV.map((n) => {
            const active = view.name === n.key
            return (
              <button
                key={n.key}
                onClick={() => setView({ name: n.key } as View)}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                  active
                    ? 'bg-indigo-600/20 text-indigo-300'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <span>{n.icon}</span>
                {n.label}
              </button>
            )
          })}
        </nav>

        <div className="mt-auto flex items-center gap-2 px-1 text-[11px]">
          <span
            className={`h-2 w-2 rounded-full ${
              hubUp === null ? 'bg-slate-600' : hubUp ? 'bg-emerald-400' : 'bg-rose-500'
            }`}
          />
          <span className="text-slate-500">
            Hub {hubUp === null ? '…' : hubUp ? 'en línea' : 'sin conexión'}
          </span>
        </div>
      </aside>

      {/* Contenido */}
      <main className="flex-1 overflow-y-auto p-8">
        {hubUp === false && (
          <div className="mx-auto mb-6 max-w-5xl rounded-lg border border-rose-800 bg-rose-950/50 px-4 py-3 text-sm text-rose-300">
            No hay conexión con el Hub (<code>http://localhost:8234</code>). Arráncalo con{' '}
            <code className="rounded bg-slate-800 px-1 py-0.5">python -m hub.main</code>.
          </div>
        )}

        {view.name === 'dashboard' && (
          <Dashboard
            onCreate={() => setView({ name: 'create' })}
            onChat={openChatWindow}
            onConfig={(a) => setView({ name: 'detail', agent: a })}
            onLogs={(a) => setView({ name: 'logs', agent: a })}
          />
        )}
        {view.name === 'create' && (
          <CreateWizard onDone={goDash} onCancel={goDash} />
        )}
        {view.name === 'detail' && (
          <AgentDetail
            agent={view.agent}
            onBack={goDash}
            onDeleted={goDash}
            onChanged={goDash}
          />
        )}
        {view.name === 'logs' && <LogsView agent={view.agent} onBack={goDash} />}
      </main>
    </div>
  )
}
