// Cliente del Hub / AgentOS. Todas las rutas del Hub cuelgan de /api/v1/hub.
// En dev, vite.config.ts proxea /api -> http://localhost:8234.
const HUB = '/api/v1/hub'

// ---- Tipos ----

export type AgentStatus = 'offline' | 'starting' | 'online' | 'error'

// Espejo de hub/models.py::AgentInfo
export interface AgentInfo {
  name: string
  port: number
  dir: string
  install_path: string
  status: AgentStatus
  pid: number | null
  auto_restart: boolean
}

// Config del agente (espejo de hub/templates/default_config.yaml)
export interface AgentConfig {
  agent?: { name?: string; description?: string; status?: string }
  personality?: {
    tone?: string
    formality?: string
    humor?: string
    empathy?: string
  }
  system_prompt?: string
  llm?: {
    provider?: string
    model?: string
    host?: string
    temperature?: number
    api_key?: string
  }
  tools?: { allow?: string[] }
  security?: { level?: number }
  channels?: {
    web?: boolean
    whatsapp?: { enabled?: boolean }
    telegram?: { enabled?: boolean; token?: string; chat_id?: string }
  }
  auto_restart?: boolean
}

export interface DirListing {
  path: string
  parent: string | null
  drives: string[]
  dirs: string[]
  home: string
}

export interface HubInfo {
  service?: string
  version?: string
  agents?: number
  online?: number
}

export interface ChatResponse {
  session_id: string
  reply: string
  tools_used?: string[]
  tokens?: number
}

// ---- Helpers ----

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(detail)
  }
  // 204 / respuestas vacías
  const text = await res.text()
  return (text ? JSON.parse(text) : {}) as T
}

// ---- Hub ----

export const getHubInfo = () => req<HubInfo>(`${HUB}/info`)
export const getHubHealth = () => req<Record<string, unknown>>(`${HUB}/health`)

export const listDir = (path?: string) =>
  req<DirListing>(`${HUB}/fs${path ? `?path=${encodeURIComponent(path)}` : ''}`)

// ---- Agentes ----

export const listAgents = () => req<AgentInfo[]>(`${HUB}/agents`)

export const getAgent = (name: string) =>
  req<AgentInfo>(`${HUB}/agents/${encodeURIComponent(name)}`)

export const createAgent = (payload: {
  name: string
  install_path?: string
  config: AgentConfig
}) =>
  req<AgentInfo>(`${HUB}/agents`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const deleteAgent = (name: string, archive = true) =>
  req<{ deleted: string; archived: boolean }>(
    `${HUB}/agents/${encodeURIComponent(name)}?archive=${archive}`,
    { method: 'DELETE' },
  )

export const startAgent = (name: string) =>
  req<AgentInfo>(`${HUB}/agents/${encodeURIComponent(name)}/start`, {
    method: 'POST',
  })

export const stopAgent = (name: string) =>
  req<AgentInfo>(`${HUB}/agents/${encodeURIComponent(name)}/stop`, {
    method: 'POST',
  })

export const restartAgent = (name: string) =>
  req<AgentInfo>(`${HUB}/agents/${encodeURIComponent(name)}/restart`, {
    method: 'POST',
  })

export const getAgentConfig = (name: string) =>
  req<AgentConfig>(`${HUB}/agents/${encodeURIComponent(name)}/config`)

export const updateAgentConfig = (name: string, config: AgentConfig) =>
  req<AgentConfig>(`${HUB}/agents/${encodeURIComponent(name)}/config`, {
    method: 'PUT',
    body: JSON.stringify({ config }),
  })

// ---- Chat directo al agente ----
// El proxy del Hub (/hub/proxy/{agent}/chat) es del Sprint 4; hoy hablamos
// directo al puerto del agente. Requiere CORS abierto en el agente (dev).
export async function chatWithAgent(
  port: number,
  message: string,
  sessionId: string | null,
): Promise<ChatResponse> {
  const res = await fetch(`http://localhost:${port}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  })
  if (!res.ok) throw new Error(`Chat error: ${res.status}`)
  return res.json()
}

export interface UploadResult {
  filename: string
  size: number
}

// Sube un archivo (imagen o documento) a la carpeta del agente. El agente luego
// puede leerlo con sus tools read_document / read_image.
export async function uploadToAgent(port: number, file: File): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`http://localhost:${port}/api/v1/upload`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`Upload error: ${res.status}`)
  return res.json()
}
