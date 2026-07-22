import { useCallback, useEffect, useRef, useState } from 'react'
import {
  importAgent,
  listAgents,
  startAgent,
  stopAgent,
  type AgentInfo,
} from '../api'
import AgentCard from '../components/AgentCard'

interface HubStats {
  total: number
  online: number
  offline: number
  error: number
}

interface Props {
  onCreate: () => void
  onChat: (a: AgentInfo) => void
  onConfig: (a: AgentInfo) => void
  onLogs: (a: AgentInfo) => void
}

export default function Dashboard({ onCreate, onChat, onConfig, onLogs }: Props) {
  const [agents, setAgents] = useState<AgentInfo[] | null>(null)
  const [stats, setStats] = useState<HubStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      const [agentList, statsRes] = await Promise.all([
        listAgents(),
        fetch('/api/v1/hub/stats').then((r) => (r.ok ? r.json() : null)).catch(() => null),
      ])
      setAgents(agentList)
      if (statsRes) setStats(statsRes as HubStats)
    } catch (e) {
      setError((e as Error).message)
      setAgents([])
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [load])

  const act = async (name: string, fn: (n: string) => Promise<unknown>) => {
    setBusy(name)
    try {
      await fn(name)
      await load()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  const online = agents?.filter((a) => a.status === 'online').length ?? 0
  const importInputRef = useRef<HTMLInputElement>(null)
  const [importing, setImporting] = useState(false)

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    setError(null)
    try {
      await importAgent(file)
      await load()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setImporting(false)
      if (importInputRef.current) importInputRef.current.value = ''
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>
          <p className="text-sm text-slate-500">
            {agents === null
              ? 'Cargando…'
              : `${agents.length} agente${agents.length === 1 ? '' : 's'} · ${online} activo${online === 1 ? '' : 's'}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={importInputRef}
            type="file"
            accept=".tar.gz"
            className="hidden"
            onChange={handleImport}
          />
          <button
            onClick={() => importInputRef.current?.click()}
            disabled={importing}
            className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-700 disabled:opacity-40"
          >
            {importing ? '⏳ Importando…' : '📦 Importar'}
          </button>
          <button
            onClick={onCreate}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
          >
            + Crear Agente
          </button>
        </div>
      </header>

      {/* Barra de stats globales */}
      {stats && (
        <div className="mb-5 grid grid-cols-4 gap-3">
          {[
            { label: 'Total', value: stats.total, color: 'text-slate-300' },
            { label: 'Online', value: stats.online, color: 'text-emerald-400' },
            { label: 'Offline', value: stats.offline, color: 'text-slate-500' },
            { label: 'Error', value: stats.error, color: 'text-rose-400' },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-center"
            >
              <p className={`text-2xl font-bold ${color}`}>{value}</p>
              <p className="text-[11px] text-slate-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg border border-rose-800 bg-rose-950/50 px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}

      {agents === null ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-xl border border-slate-800 bg-slate-900/40"
            />
          ))}
        </div>
      ) : agents.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/30 py-16 text-center">
          <p className="text-4xl">🤖</p>
          <p className="mt-3 text-slate-300">Aún no hay agentes.</p>
          <p className="text-sm text-slate-500">Crea el primero para empezar.</p>
          <button
            onClick={onCreate}
            className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
          >
            + Crear Agente
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {agents.map((a) => (
            <AgentCard
              key={a.name}
              agent={a}
              busy={busy === a.name}
              onChat={onChat}
              onConfig={onConfig}
              onLogs={onLogs}
              onStart={(ag) => act(ag.name, startAgent)}
              onStop={(ag) => act(ag.name, stopAgent)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
