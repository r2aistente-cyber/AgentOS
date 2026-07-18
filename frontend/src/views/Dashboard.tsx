import { useCallback, useEffect, useState } from 'react'
import {
  listAgents,
  startAgent,
  stopAgent,
  type AgentInfo,
} from '../api'
import AgentCard from '../components/AgentCard'

interface Props {
  onCreate: () => void
  onChat: (a: AgentInfo) => void
  onConfig: (a: AgentInfo) => void
  onLogs: (a: AgentInfo) => void
}

export default function Dashboard({ onCreate, onChat, onConfig, onLogs }: Props) {
  const [agents, setAgents] = useState<AgentInfo[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      setAgents(await listAgents())
    } catch (e) {
      setError((e as Error).message)
      setAgents([])
    }
  }, [])

  useEffect(() => {
    load()
    // Refresco de estado en vivo cada 5s (barato: solo GET /agents)
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

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>
          <p className="text-sm text-slate-500">
            {agents === null
              ? 'Cargando…'
              : `${agents.length} agente${agents.length === 1 ? '' : 's'} · ${online} activo${online === 1 ? '' : 's'}`}
          </p>
        </div>
        <button
          onClick={onCreate}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
        >
          + Crear Agente
        </button>
      </header>

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
