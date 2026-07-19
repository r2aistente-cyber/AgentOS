import { useEffect, useRef, useState } from 'react'
import type { AgentInfo } from '../api'

interface Props {
  agent: AgentInfo
  onBack: () => void
}

const TAIL_OPTIONS = [50, 100, 200, 500]
const HUB_BASE = '/api/v1/hub'

function colorLine(line: string): string {
  const l = line.toLowerCase()
  if (l.includes('error') || l.includes('exception') || l.includes('traceback') || l.includes('critical'))
    return 'text-rose-400'
  if (l.includes('warning') || l.includes('warn')) return 'text-amber-400'
  if (l.includes('info')) return 'text-slate-300'
  if (l.includes('debug')) return 'text-slate-500'
  return 'text-slate-400'
}

export default function LogsView({ agent, onBack }: Props) {
  const [lines, setLines] = useState<string[]>([])
  const [tail, setTail] = useState(100)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [paused, setPaused] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const autoScroll = useRef(true)
  const esRef = useRef<EventSource | null>(null)
  const pausedRef = useRef(false)

  pausedRef.current = paused

  useEffect(() => {
    // Limpiar líneas al cambiar agente o tail
    setLines([])
    setError(null)
    setConnected(false)

    const url = `${HUB_BASE}/agents/${encodeURIComponent(agent.name)}/logs/stream?tail=${tail}`
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => setConnected(true)

    es.onmessage = (e) => {
      if (pausedRef.current) return
      const line = e.data as string
      if (!line) return
      setLines((prev) => {
        const next = [...prev, line]
        // Limitar a tail*2 líneas en memoria
        return next.length > tail * 2 ? next.slice(-tail) : next
      })
      if (autoScroll.current) {
        requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }))
      }
    }

    es.onerror = () => {
      setConnected(false)
      setError('SSE desconectado — reconectando…')
      // El navegador reconecta automáticamente; limpiamos el mensaje tras 3s
      setTimeout(() => setError(null), 3000)
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [agent.name, tail])

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    autoScroll.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  }

  const scrollToBottom = () => {
    autoScroll.current = true
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const clearLines = () => setLines([])

  return (
    <div className="mx-auto flex h-full max-w-4xl flex-col">
      {/* Header */}
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <button onClick={onBack} className="text-sm text-slate-400 hover:text-slate-200">
          ← Volver
        </button>
        <h1 className="text-base font-semibold text-slate-100">📋 Logs · {agent.name}</h1>

        <div className="ml-auto flex items-center gap-2">
          <select
            value={tail}
            onChange={(e) => setTail(Number(e.target.value))}
            className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200 outline-none"
          >
            {TAIL_OPTIONS.map((n) => (
              <option key={n} value={n}>
                tail {n}
              </option>
            ))}
          </select>

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

          <button
            onClick={clearLines}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs text-slate-200 hover:bg-slate-700"
            title="Limpiar pantalla"
          >
            🗑️
          </button>

          <button
            onClick={scrollToBottom}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs text-slate-200 hover:bg-slate-700"
            title="Ir al final"
          >
            ↓ Final
          </button>
        </div>
      </div>

      {/* Indicador de estado */}
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`h-2 w-2 rounded-full ${
            paused
              ? 'bg-amber-400'
              : connected
                ? 'animate-pulse bg-emerald-400'
                : 'bg-rose-500'
          }`}
        />
        <span className="text-[11px] text-slate-500">
          {paused
            ? 'Pausado'
            : connected
              ? `En vivo (SSE) · ${lines.length} líneas`
              : 'Conectando…'}
        </span>
        {error && <span className="text-[11px] text-amber-400">{error}</span>}
      </div>

      {/* Cuerpo del log */}
      <div
        className="flex-1 overflow-y-auto rounded-xl border border-slate-800 bg-black/70 p-4 font-mono text-xs"
        onScroll={handleScroll}
      >
        {lines.length === 0 ? (
          <p className="text-slate-500 animate-pulse">
            {agent.status !== 'online'
              ? 'El agente está detenido. Inícialo para generar logs.'
              : 'Esperando logs…'}
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
