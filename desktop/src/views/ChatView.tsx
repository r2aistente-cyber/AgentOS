import { useEffect, useRef, useState } from 'react'
import {
  chatWithAgent,
  createAgentSession,
  getAgent,
  getAgentModels,
  getSessionMessages,
  listAgentSessions,
  startAgent,
  uploadToAgent,
  type AgentInfo,
  type AgentSession,
  type ModelOption,
} from '../api'

interface Props {
  agent: AgentInfo
  onBack?: () => void
}

interface Msg {
  role: 'user' | 'assistant'
  content: string
  tools?: string[]
  attachments?: string[]
}

interface Ctx {
  tokens: number
  limit: number
}

export default function ChatView({ agent: initialAgent, onBack }: Props) {
  const [agent, setAgent] = useState<AgentInfo>(initialAgent)
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessions, setSessions] = useState<AgentSession[]>([])
  const [models, setModels] = useState<ModelOption[]>([])
  const [activeModel, setActiveModel] = useState<string>('')
  const [context, setContext] = useState<Ctx | null>(null)
  const [sending, setSending] = useState(false)
  const [starting, setStarting] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [attachments, setAttachments] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const docInputRef = useRef<HTMLInputElement>(null)

  const online = agent.status === 'online'

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // #1: refleja el estado real del agente (si lo detienes desde el Hub).
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        setAgent(await getAgent(initialAgent.name))
      } catch {
        /* Hub caído o agente borrado: se ignora hasta el próximo tick */
      }
    }, 4000)
    return () => clearInterval(id)
  }, [initialAgent.name])

  // #6/#12: al estar en línea, carga las sesiones y reabre la más reciente.
  // #11: carga la lista de modelos configurados y fija el activo por defecto.
  useEffect(() => {
    if (!online) return
    let cancelled = false
    ;(async () => {
      try {
        const list = await listAgentSessions(agent.port)
        if (cancelled) return
        setSessions(list)
        if (list.length > 0 && !sessionId) await loadSession(list[0].id)
      } catch {
        /* agente recién iniciado sin sesiones aún */
      }
      try {
        const m = await getAgentModels(agent.port)
        if (cancelled) return
        setModels(m.models)
        setActiveModel((cur) => cur || m.default)
      } catch {
        /* sin lista de modelos: se usa el default del agente */
      }
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [online, agent.port])

  const refreshSessions = async () => {
    try {
      setSessions(await listAgentSessions(agent.port))
    } catch {
      /* ignore */
    }
  }

  // #6: reconstruye una conversación desde la BD del agente.
  const loadSession = async (sid: string) => {
    setSessionId(sid)
    setContext(null)
    try {
      const msgs = await getSessionMessages(agent.port, sid)
      setMessages(
        msgs
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .map((m) => ({
            role: m.role as 'user' | 'assistant',
            content: m.content,
            tools: m.tools_used,
          })),
      )
    } catch (e) {
      setError((e as Error).message)
    }
  }

  // #12: nueva sesión de trabajo con el mismo agente.
  const newSession = async () => {
    try {
      const s = await createAgentSession(agent.port)
      setSessionId(s.id)
      setMessages([])
      setContext(null)
      await refreshSessions()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  // Inicia el agente y espera (poll) hasta que esté en línea.
  const handleStart = async () => {
    setStarting(true)
    setError(null)
    try {
      await startAgent(agent.name)
      for (let i = 0; i < 10; i++) {
        await new Promise((r) => setTimeout(r, 800))
        const fresh = await getAgent(agent.name)
        setAgent(fresh)
        if (fresh.status === 'online') break
        if (fresh.status === 'error') throw new Error('El agente falló al iniciar')
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setStarting(false)
    }
  }

  // Sube los archivos elegidos a la carpeta del agente y los deja como adjuntos.
  const handleFiles = async (list: FileList | null) => {
    if (!list || list.length === 0) return
    setUploading(true)
    setError(null)
    try {
      for (const file of Array.from(list)) {
        const res = await uploadToAgent(agent.port, file)
        setAttachments((a) => (a.includes(res.filename) ? a : [...a, res.filename]))
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setUploading(false)
      if (imageInputRef.current) imageInputRef.current.value = ''
      if (docInputRef.current) docInputRef.current.value = ''
    }
  }

  const removeAttachment = (name: string) =>
    setAttachments((a) => a.filter((n) => n !== name))

  const send = async () => {
    const text = input.trim()
    if ((!text && attachments.length === 0) || sending || !online) return
    const atts = attachments
    const payload =
      atts.length > 0
        ? `${text}${text ? '\n\n' : ''}[Adjuntos: ${atts.join(', ')}]`
        : text
    setInput('')
    setAttachments([])
    setError(null)
    setMessages((m) => [...m, { role: 'user', content: text, attachments: atts }])
    setSending(true)
    const wasNew = !sessionId
    try {
      const res = await chatWithAgent(agent.port, payload, sessionId, activeModel || null)
      setSessionId(res.session_id)
      if (res.context_tokens != null && res.context_limit != null) {
        setContext({ tokens: res.context_tokens, limit: res.context_limit })
      }
      setMessages((m) => [...m, { role: 'assistant', content: res.reply, tools: res.tools_used }])
      if (wasNew) await refreshSessions()
    } catch (e) {
      setError((e as Error).message)
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: '⚠️ No se pudo contactar al agente. ¿Está en línea?' },
      ])
    } finally {
      setSending(false)
    }
  }

  const ctxPct = context ? Math.min(100, Math.round((context.tokens / context.limit) * 100)) : 0
  const ctxColor = ctxPct < 60 ? 'bg-emerald-500' : ctxPct < 85 ? 'bg-amber-500' : 'bg-rose-500'

  return (
    <div className="flex h-full w-full flex-col">
      <div className="mb-3 flex items-center gap-3">
        {onBack && (
          <button onClick={onBack} className="text-sm text-slate-400 hover:text-slate-200">
            ← Volver
          </button>
        )}
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <h1 className="text-base font-semibold text-slate-100">{agent.name}</h1>
          <span className="font-mono text-xs text-slate-500">:{agent.port}</span>
          <span className={`h-2 w-2 rounded-full ${online ? 'bg-emerald-400' : 'bg-slate-500'}`} />
        </div>

        <div className="ml-auto flex items-center gap-2">
          {/* #11: selector de modelo (cambia en caliente, sin reiniciar) */}
          {models.length > 0 && (
            <select
              value={activeModel}
              onChange={(e) => setActiveModel(e.target.value)}
              disabled={!online}
              className="max-w-[11rem] rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-indigo-200 outline-none disabled:opacity-40"
              title="Modelo (cambia sin reiniciar)"
            >
              {models.map((m) => (
                <option key={m.ref} value={m.ref}>
                  🧠 {m.label}
                </option>
              ))}
            </select>
          )}

          {/* #12: selector de sesión de trabajo */}
          <select
            value={sessionId ?? ''}
            onChange={(e) => e.target.value && loadSession(e.target.value)}
            disabled={!online || sessions.length === 0}
            className="max-w-[10rem] rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200 outline-none disabled:opacity-40"
            title="Sesión de trabajo"
          >
            {sessions.length === 0 && <option value="">Sin sesiones</option>}
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
          <button
            onClick={newSession}
            disabled={!online}
            title="Nueva sesión"
            className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-200 hover:bg-slate-700 disabled:opacity-40"
          >
            ＋ Nueva
          </button>
        </div>
      </div>

      {!online && (
        <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-amber-800 bg-amber-950/30 px-4 py-3 text-sm text-amber-200">
          <span>
            El agente está <strong>detenido</strong>. Inícialo para poder chatear.
          </span>
          <button
            onClick={handleStart}
            disabled={starting}
            className="shrink-0 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
          >
            {starting ? 'Iniciando…' : '▶️ Iniciar agente'}
          </button>
        </div>
      )}

      <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        {messages.length === 0 && (
          <p className="mt-10 text-center text-sm text-slate-500">
            {online
              ? 'Escribe un mensaje para hablar con el agente.'
              : 'Inicia el agente para empezar a chatear.'}
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] select-text rounded-2xl px-4 py-2 text-sm ${
                m.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-100'
              }`}
            >
              {m.content && <p className="whitespace-pre-wrap">{m.content}</p>}
              {m.attachments && m.attachments.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {m.attachments.map((f) => (
                    <span key={f} className="rounded bg-black/20 px-1.5 py-0.5 text-[11px]">
                      📎 {f}
                    </span>
                  ))}
                </div>
              )}
              {m.tools && m.tools.length > 0 && (
                <p className="mt-1 text-[11px] opacity-70">🔧 {m.tools.join(', ')}</p>
              )}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-slate-800 px-4 py-2 text-sm text-slate-400">
              <span className="animate-pulse">escribiendo…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* #7: medidor de uso de contexto */}
      {context && (
        <div className="mt-2 flex items-center gap-2">
          <span className="text-[11px] text-slate-500">Contexto</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800">
            <div className={`h-full ${ctxColor} transition-all`} style={{ width: `${ctxPct}%` }} />
          </div>
          <span className="font-mono text-[11px] text-slate-400">
            {context.tokens.toLocaleString()} / {context.limit.toLocaleString()} ({ctxPct}%)
          </span>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}

      {/* Adjuntos pendientes de enviar */}
      {(attachments.length > 0 || uploading) && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {attachments.map((f) => (
            <span
              key={f}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-200"
            >
              📎 {f}
              <button
                onClick={() => removeAttachment(f)}
                className="text-slate-500 hover:text-rose-400"
                title="Quitar"
              >
                ✕
              </button>
            </span>
          ))}
          {uploading && <span className="text-xs text-slate-500 animate-pulse">subiendo…</span>}
        </div>
      )}

      {/* Inputs ocultos para imágenes y documentos */}
      <input
        ref={imageInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <input
        ref={docInputRef}
        type="file"
        accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls,.pptx,.json"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div className="mt-3 flex gap-2">
        <button
          onClick={() => imageInputRef.current?.click()}
          disabled={!online || uploading}
          title="Subir imagen"
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 transition hover:bg-slate-700 disabled:opacity-40"
        >
          🖼️
        </button>
        <button
          onClick={() => docInputRef.current?.click()}
          disabled={!online || uploading}
          title="Subir documento"
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 transition hover:bg-slate-700 disabled:opacity-40"
        >
          📎
        </button>
        <input
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-100 outline-none focus:border-indigo-500 disabled:opacity-50"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
          placeholder={online ? `Mensaje para ${agent.name}…` : 'Agente detenido'}
          disabled={!online}
        />
        <button
          onClick={send}
          disabled={sending || (!input.trim() && attachments.length === 0) || !online}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-40"
        >
          ▶️
        </button>
      </div>
    </div>
  )
}
