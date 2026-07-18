import type { AgentInfo } from '../api'

interface Props {
  agent: AgentInfo
  onBack: () => void
}

// El streaming/tail de logs en vivo es parte del Sprint 4 (Logs, monitoreo,
// auto-restart): requiere un endpoint GET /agents/{name}/logs en el Hub que
// aún no existe. Esta vista es el andamiaje; se cablea cuando el endpoint esté.
export default function LogsView({ agent, onBack }: Props) {
  return (
    <div className="mx-auto max-w-2xl">
      <button onClick={onBack} className="mb-4 text-sm text-slate-400 hover:text-slate-200">
        ← Volver
      </button>
      <h1 className="mb-4 text-xl font-semibold text-slate-100">📊 Logs · {agent.name}</h1>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 font-mono text-sm">
        <div className="flex items-center gap-2 text-amber-400">
          <span>⚠️</span>
          <span className="not-italic">Vista de logs pendiente (Sprint 4)</span>
        </div>
        <p className="mt-3 font-sans text-slate-400">
          El tail de logs en vivo necesita el endpoint{' '}
          <code className="rounded bg-slate-800 px-1.5 py-0.5 text-xs">
            GET /api/v1/hub/agents/{agent.name}/logs
          </code>{' '}
          en el Hub, que forma parte del Sprint 4 (Logs, monitoreo, auto-restart).
          La UI ya está lista para conectarse en cuanto exista.
        </p>
      </div>
    </div>
  )
}
