import { useEffect, useRef, useState } from 'react'
import {
  deleteAgent,
  exportAgent,
  getAgentConfig,
  listProviderModels,
  restartAgent,
  startAgent,
  stopAgent,
  updateAgentConfig,
  type AgentConfig,
  type AgentInfo,
} from '../api'
import StatusBadge from '../components/StatusBadge'

const HUB = '/api/v1/hub'

interface WaStatus {
  running: boolean
  ready: boolean
  waiting_qr: boolean
  error: string | null
  messages_in?: number
  messages_out?: number
  sidecar_port?: number
}

function WhatsAppPanel({ agent }: { agent: AgentInfo }) {
  const [status, setStatus] = useState<WaStatus | null>(null)
  const [qrImage, setQrImage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = async () => {
    try {
      const r = await fetch(`${HUB}/agents/${encodeURIComponent(agent.name)}/whatsapp/status`)
      if (r.ok) setStatus(await r.json())
    } catch {}
  }

  const fetchQr = async () => {
    try {
      const r = await fetch(`${HUB}/agents/${encodeURIComponent(agent.name)}/whatsapp/qr`)
      if (r.ok) {
        const d = await r.json()
        setQrImage(d.qr_image || null)
      } else {
        setQrImage(null)
      }
    } catch {}
  }

  useEffect(() => {
    fetchStatus()
    pollRef.current = setInterval(async () => {
      await fetchStatus()
    }, 3000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [agent.name])

  useEffect(() => {
    if (status?.waiting_qr) {
      fetchQr()
      const id = setInterval(fetchQr, 5000)
      return () => clearInterval(id)
    } else {
      setQrImage(null)
    }
  }, [status?.waiting_qr])

  const start = async () => {
    setBusy(true)
    try {
      await fetch(`${HUB}/agents/${encodeURIComponent(agent.name)}/whatsapp/start`, { method: 'POST' })
      await fetchStatus()
    } catch {} finally { setBusy(false) }
  }

  const stop = async () => {
    setBusy(true)
    try {
      await fetch(`${HUB}/agents/${encodeURIComponent(agent.name)}/whatsapp/stop`, { method: 'POST' })
      setQrImage(null)
      await fetchStatus()
    } catch {} finally { setBusy(false) }
  }

  const dotColor = !status?.running ? 'bg-slate-500'
    : status.ready ? 'bg-emerald-400'
    : status.waiting_qr ? 'bg-amber-400 animate-pulse'
    : 'bg-rose-500'

  const statusText = !status?.running ? 'Detenido'
    : status.ready ? 'Conectado ✓'
    : status.waiting_qr ? 'Esperando QR'
    : status.error ? `Error: ${status.error}` : 'Iniciando…'

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-base">📱</span>
          <h3 className="text-sm font-semibold text-slate-200">WhatsApp</h3>
          <span className={`h-2 w-2 rounded-full ${dotColor}`} />
          <span className="text-xs text-slate-400">{statusText}</span>
        </div>
        <div className="flex gap-2">
          {status?.running ? (
            <button onClick={stop} disabled={busy}
              className="rounded-md bg-rose-600/80 px-3 py-1 text-xs font-medium text-white hover:bg-rose-500 disabled:opacity-40">
              ⏹ Detener
            </button>
          ) : (
            <button onClick={start} disabled={busy}
              className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-40">
              ▶ Iniciar sidecar
            </button>
          )}
        </div>
      </div>

      {status?.waiting_qr && (
        <div className="mt-3 text-center">
          <p className="mb-2 text-xs text-amber-400">
            Abre WhatsApp → Dispositivos vinculados → Vincular un dispositivo → Escanea:
          </p>
          {qrImage ? (
            <img src={qrImage} alt="QR WhatsApp" className="mx-auto rounded-lg border border-slate-700" style={{ width: 200, height: 200 }} />
          ) : (
            <div className="mx-auto h-48 w-48 animate-pulse rounded-lg bg-slate-800" />
          )}
        </div>
      )}

      {status?.ready && (
        <div className="mt-3 flex gap-4 text-xs text-slate-500">
          <span>📥 {status.messages_in ?? 0} recibidos</span>
          <span>📤 {status.messages_out ?? 0} enviados</span>
          {status.sidecar_port && <span>puerto :{status.sidecar_port}</span>}
        </div>
      )}
    </div>
  )
}

interface Props {
  agent: AgentInfo
  onBack: () => void
  onDeleted: () => void
  onChanged: () => void
}

const inputCls =
  'w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-500'

export default function AgentDetail({ agent, onBack, onDeleted, onChanged }: Props) {
  const [config, setConfig] = useState<AgentConfig | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [modelCatalog, setModelCatalog] = useState<Record<string, string[] | null>>({})

  useEffect(() => {
    getAgentConfig(agent.name)
      .then(setConfig)
      .catch((e) => setError((e as Error).message))
    listProviderModels().then(setModelCatalog).catch(() => {})
  }, [agent.name])

  // Modelos disponibles para el proveedor actual
  const availableModels: string[] | null = config
    ? (modelCatalog[config.llm?.provider ?? ''] ?? null)
    : null

  const patch = (fn: (c: AgentConfig) => AgentConfig) =>
    setConfig((c) => (c ? fn(c) : c))

  const doAction = async (fn: (n: string) => Promise<unknown>, label: string) => {
    setBusy(true)
    setError(null)
    setMsg(null)
    try {
      await fn(agent.name)
      setMsg(`${label} ✓`)
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const save = async () => {
    if (!config) return
    setBusy(true)
    setError(null)
    setMsg(null)
    try {
      await updateAgentConfig(agent.name, config)
      setMsg('Configuración guardada ✓')
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async () => {
    if (!confirm(`¿Eliminar el agente "${agent.name}"? (se archiva una copia)`)) return
    setBusy(true)
    try {
      await deleteAgent(agent.name, true)
      onDeleted()
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  const doExport = async () => {
    setBusy(true)
    setError(null)
    setMsg(null)
    try {
      await exportAgent(agent.name)
      setMsg('Exportación lista — revisa tus descargas ✓')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const online = agent.status === 'online'

  return (
    <div className="mx-auto max-w-2xl">
      <button onClick={onBack} className="mb-4 text-sm text-slate-400 hover:text-slate-200">
        ← Volver
      </button>

      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">⚙️ {agent.name}</h1>
          <div className="mt-1 flex items-center gap-3">
            <StatusBadge status={agent.status} />
            <span className="font-mono text-xs text-slate-500">
              puerto :{agent.port}
              {agent.pid ? ` · pid ${agent.pid}` : ''}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          {online ? (
            <>
              <button onClick={() => doAction(restartAgent, 'Reiniciado')} disabled={busy} className="rounded-lg bg-slate-800 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-700 disabled:opacity-40">
                🔄 Reiniciar
              </button>
              <button onClick={() => doAction(stopAgent, 'Detenido')} disabled={busy} className="rounded-lg bg-rose-600/90 px-3 py-1.5 text-sm text-white hover:bg-rose-500 disabled:opacity-40">
                ⏹️ Detener
              </button>
            </>
          ) : (
            <button onClick={() => doAction(startAgent, 'Iniciado')} disabled={busy} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-500 disabled:opacity-40">
              ▶️ Iniciar
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-rose-800 bg-rose-950/50 px-4 py-3 text-sm text-rose-300">{error}</div>
      )}
      {msg && (
        <div className="mb-4 rounded-lg border border-emerald-800 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-300">{msg}</div>
      )}

      <div className="mb-4">
        <WhatsAppPanel agent={agent} />
      </div>

      {config === null ? (
        <div className="h-64 animate-pulse rounded-xl border border-slate-800 bg-slate-900/40" />
      ) : (
        <div className="space-y-5 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-300">Proveedor / Modelo</span>
            <div className="grid grid-cols-2 gap-3">
              <select
                className={inputCls}
                value={config.llm?.provider ?? 'ollama'}
                onChange={(e) => patch((c) => ({ ...c, llm: { ...c.llm, provider: e.target.value } }))}
              >
                {['ollama', 'openai', 'anthropic', 'opencode', 'opencode-go', 'custom', 'mock'].map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              {availableModels ? (
                <select
                  className={inputCls}
                  value={config.llm?.model ?? ''}
                  onChange={(e) => patch((c) => ({ ...c, llm: { ...c.llm, model: e.target.value } }))}
                >
                  {availableModels.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              ) : (
                <input
                  className={inputCls}
                  value={config.llm?.model ?? ''}
                  onChange={(e) => patch((c) => ({ ...c, llm: { ...c.llm, model: e.target.value } }))}
                />
              )}
            </div>
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-300">
              Temperatura: {(config.llm?.temperature ?? 0.7).toFixed(2)}
            </span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={config.llm?.temperature ?? 0.7}
              onChange={(e) => patch((c) => ({ ...c, llm: { ...c.llm, temperature: Number(e.target.value) } }))}
              className="w-full accent-indigo-500"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-300">System prompt</span>
            <textarea
              className={`${inputCls} h-24 resize-none`}
              value={config.system_prompt ?? ''}
              onChange={(e) => patch((c) => ({ ...c, system_prompt: e.target.value }))}
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={config.auto_restart ?? false}
              onChange={(e) => patch((c) => ({ ...c, auto_restart: e.target.checked }))}
              className="accent-indigo-500"
            />
            Auto-reinicio si el agente cae
          </label>

          <p className="text-xs text-slate-500">
            Nota: los cambios de config se aplican al reiniciar el agente.
          </p>

          <div className="flex items-center justify-between border-t border-slate-800 pt-4">
            <div className="flex gap-3">
              <button onClick={remove} disabled={busy} className="text-sm text-rose-400 hover:text-rose-300 disabled:opacity-40">
                🗑️ Eliminar
              </button>
              <button onClick={doExport} disabled={busy} className="text-sm text-indigo-400 hover:text-indigo-300 disabled:opacity-40">
                📦 Exportar
              </button>
            </div>
            <button onClick={save} disabled={busy} className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40">
              {busy ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
