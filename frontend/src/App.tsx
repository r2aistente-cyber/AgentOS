import { useEffect, useRef, useState } from 'react'
import { sendMessage, listSessions, newSession, getSession, deleteSession, uploadFile } from './api'
import type { Session } from './api'
import Sidebar from './components/Sidebar'
import ChatBubble from './components/ChatBubble'
import type { ChatMessage } from './components/ChatBubble'
import ChatInput from './components/ChatInput'
import './index.css'

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    listSessions().then((s) => {
      setSessions(s)
      if (s.length > 0) loadSession(s[0].id)
    })
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadSession = async (id: string) => {
    setActiveId(id)
    try {
      const data = await getSession(id)
      setMessages(
        data.messages
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content }))
      )
    } catch {
      setMessages([])
    }
  }

  const handleNew = async () => {
    const id = await newSession('core', 'Nueva sesión')
    const updated = await listSessions()
    setSessions(updated)
    setActiveId(id)
    setMessages([])
  }

  const handleDelete = async (id: string) => {
    await deleteSession(id)
    const updated = await listSessions()
    setSessions(updated)
    if (activeId === id) {
      if (updated.length > 0) loadSession(updated[0].id)
      else { setActiveId(null); setMessages([]) }
    }
  }

  const handleSend = async (text: string, file?: File) => {
    if (loading) return

    let sessionId = activeId
    if (!sessionId) {
      sessionId = await newSession()
      const updated = await listSessions()
      setSessions(updated)
      setActiveId(sessionId)
    }

    let message = text
    if (file) {
      try {
        const uploaded = await uploadFile(file)
        message = `${text}\n\n[Archivo subido: ${uploaded.filename} — id: ${uploaded.file_id}]`
      } catch {
        message = `${text}\n\n[Error al subir archivo]`
      }
    }

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: message },
      { role: 'assistant', content: '', pending: true },
    ])
    setLoading(true)

    try {
      const res = await sendMessage(message, sessionId)
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: res.reply, tools_used: res.tools_used },
      ])
      const updated = await listSessions()
      setSessions(updated)
    } catch (err) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: `⚠️ Error: ${err}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={loadSession}
        onNew={handleNew}
        onDelete={handleDelete}
      />

      <div className="flex flex-col flex-1 min-w-0">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2 bg-gray-900/50">
          <span className="text-violet-400 text-sm font-medium">
            {sessions.find((s) => s.id === activeId)?.title ?? 'R2 Autonomous'}
          </span>
          <span className="text-gray-600 text-xs ml-auto">qwen2.5:latest · :8234</span>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center select-none">
              <div className="text-5xl mb-3">🤖</div>
              <h2 className="text-gray-200 font-semibold text-lg mb-1">R2 Autonomous</h2>
              <p className="text-gray-500 text-sm">Tu agente personal. 100% local.</p>
              <p className="text-gray-700 text-xs mt-1">Ollama · qwen2.5:latest</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatBubble key={i} msg={msg} />
          ))}
          <div ref={bottomRef} />
        </div>

        <ChatInput onSend={handleSend} disabled={loading} />
      </div>
    </div>
  )
}
