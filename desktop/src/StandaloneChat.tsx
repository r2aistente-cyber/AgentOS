import { useEffect, useState } from 'react'
import { getAgent, type AgentInfo } from './api'
import ChatView from './views/ChatView'
import './index.css'

// Chat en ventana propia (window.open). Lee el agente de ?agent=NAME y lo
// resuelve contra el Hub. Así se pueden tener varios agentes flotando a la vez.
export default function StandaloneChat() {
  const [agent, setAgent] = useState<AgentInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  const name = new URLSearchParams(window.location.search).get('agent')

  useEffect(() => {
    if (!name) {
      setError('Falta el parámetro ?agent en la URL.')
      return
    }
    document.title = `Chat · ${name}`
    getAgent(name)
      .then(setAgent)
      .catch((e) => setError((e as Error).message))
  }, [name])

  return (
    <div className="h-screen bg-slate-950 p-4 text-slate-100">
      {error ? (
        <div className="rounded-lg border border-rose-800 bg-rose-950/50 px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      ) : !agent ? (
        <div className="flex h-full items-center justify-center text-sm text-slate-500">
          Cargando agente…
        </div>
      ) : (
        <ChatView agent={agent} />
      )}
    </div>
  )
}
