import { useCallback, useEffect, useRef, useState } from 'react'
import { getAgentLogs, type AgentInfo } from '../api'

interface Props {
  agent: AgentInfo
  onBack: () => void
}

const TAIL_OPTIONS = [50, 100, 200, 500]

function colorLine(line: string): string {
  const l = line.toLowerCase()
  if (l.includes('error') || l.includes('exception') || l.includes('traceback')) return 'text-rose-400'
  if (l.includes('warning') || l.includes('warn')) return 'text-amber-400'
  if (l.includes('info')) return 'text-slate-300'
  if (l.includes('debug')) return 'text-slate-500'
  return 'text-slate-400'
}

export default function LogsView({ agent, onBack }: Props) {
  const [lines, setLines] = useState<string[]>([])
  const [tail, setTail] = useState(100)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [paused, setPaused] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const autoScroll = useRef(true)

  const load = useCallback(async () => {
    if (paused) return
    try {
      const res = await getAgentLogs(agent.name, tail)
      setLines(res.lines)
      setError(null)
      if (autoScroll.current) {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [agent.name, tail, paused])

  useEffect(() => {
    setLoading(true)
    load()
    const id = setInterval(load, 2000)
    return () => clearInterval(id)
  }, [load])

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    autoScroll.current = atBottom
  }

  return (
    <div className="mx-auto flex h-full max-w-4xl flex-col">
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <button onClick={onBack} className="text-sm text-slate-400 hover:text-slate-200">
          ← Volver
        </button>
        <h1 className="text-base font-semibold text-slate-100">📋 Logs · {agent.name}</h1>
        <span className={`h-2 w-2 rounded-full ${agent.status === 'online' ? 'bg-emerald-400' : 'bg-slate-500'}`} />
        <div className="ml-auto flex items-center gap-2">
          {/* Tail selector */}
          <select
            value={tail}
            onChange={(e) => setTail(Number(e.target.value))}
            className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200 outline-none"
          >
            {TAIL_OPTIONS.map((n) => (
              <option key={n} value={n}>
                últimas {n} líneas
              </option>
            ))}
          </select>
          {/* Pause/resume */}
          <button
            onClick={() => setPaused((p) => !p)}
            className={`rounded-lg border px-3 py-1 text-xs font-medium transition ${
              paused
                ? 'border-amber-700 bg-amber-950/40 text-amber-300 hover:bg-amber-950/70'
                : 'border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700'
            }`}
          >
            {paused ? '▶️ Reanudar' : '⏸ Pausar'}
          </button>
          {/* Scroll to bottom */}
          <button
            onClick={() => {
              autoScroll.current = true
              bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
            }}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs text-slate-200 hover:bg-slate-700"
            title="Ir al final"
          >
            ↓ Final
          </button>
        </div>
      </div>

      {/* Live indicator */}
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`h-2 w-2 rounded-full ${paused ? 'bg-amber-400' : 'animate-pulse bg-emerald-400'}`}
        />
        <span className="text-[11px] text-slate-500">
          {paused ? 'Pausado' : 'En vivo · actualiza cada 2s'}
          {lines.length > 0 && ` · ${lines.length} líneas`}
        </span>
      </div>

      {/* Log body */}
      <div
        className="flex-1 overflow-y-auto rounded-xl border border-slate-800 bg-black/60 p-4 font-mono text-xs"
        onScroll={handleScroll}
      >
        {loading && lines.length === 0 ? (
          <p className="text-slate-500 animate-pulse">Cargando logs…</p>
        ) : error ? (
          <p className="text-rose-400">Error: {error}</p>
        ) : lines.length === 0 ? (
          <p className="text-slate-500">
            {agent.status !== 'online'
              ? 'El agente está detenido. Inícialo para generar logs.'
              : 'Sin logs todavía. El archivo se crea cuando el agente arranca.'}
          </p>
        ) : (
          lines.map((line, i) => (
            <div key={i} className={`leading-5 ${colorLine(line)}`}>
              {line || ' '}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
