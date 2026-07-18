import { useEffect, useRef, useState } from 'react'
import {
  chatWithAgent,
  getAgent,
  startAgent,
  uploadToAgent,
  type AgentInfo,
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

export default function ChatView({ agent: initialAgent, onBack }: Props) {
  const [agent, setAgent] = useState<AgentInfo>(initialAgent)
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [starting, setStarting] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [attachments, setAttachments] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)
  const docInputRef = useRef<HTMLInputElement>(null)

  const online = agent.status === 'online'

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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

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

  const send = async () => {
    const text = input.trim()
    if ((!text && attachments.length === 0) || sending || !online) return
    const atts = attachments
    // El agente lee los adjuntos de su carpeta con read_document / read_image.
    const payload =
      atts.length > 0
        ? `${text}${text ? '\n\n' : ''}[Adjuntos: ${atts.join(', ')}]`
        : text
    setInput('')
    setAttachments([])
    setError(null)
    setMessages((m) => [...m, { role: 'user', content: text, attachments: atts }])
    setSending(true)
    try {
      const res = await chatWithAgent(agent.port, payload, sessionId)
      setSessionId(res.session_id)
      setMessages((m) => [...m, { role: 'assistant', content: res.reply, tools: res.tools_used }])
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

  return (
    <div className="mx-auto flex h-[calc(100vh-6rem)] max-w-2xl flex-col">
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
              className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
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
