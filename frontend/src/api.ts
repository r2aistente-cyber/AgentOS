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
    num_ctx?: number
    models?: { provider: string; model: string; label?: string }[]
  }
  tools?: { allow?: string[] }
  search?: { brave_api_key?: string }
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
  tokens_used?: number
  context_tokens?: number
  context_limit?: number
}

export interface AgentSession {
  id: string
  title: string
  created_at?: string
}

export interface SessionMessage {
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  tools_used?: string[]
  tokens?: number
}

// ---- Helpers del Hub ----

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
  const text = await res.text()
  return (text ? JSON.parse(text) : {}) as T
}

// ---- Cache de tokens por nombre de agente ----
// null  = token verificado como ausente (agente sin auth)
// undefined = no consultado aún
const _tokenCache = new Map<string, string | null>()

/** Obtiene el Bearer token del agente desde el Hub (con cache).
 *  Solo cachea respuestas exitosas; errores de red no se cachean
 *  para que el próximo intento reintente al Hub.
 */
async function resolveToken(agentName: string): Promise<string | null> {
  if (_tokenCache.has(agentName)) return _tokenCache.get(agentName)!
  try {
    const r = await req<{ token: string | null; auth_required: boolean }>(
      `${HUB}/agents/${encodeURIComponent(agentName)}/token`,
    )
    const token = r.auth_required ? r.token : null
    _tokenCache.set(agentName, token)
    return token
  } catch {
    // Hub no responde o endpoint ausente: NO cachear — reintentar en próximo mensaje.
    return null
  }
}

/** Invalida el token en cache (útil cuando se recrea un agente). */
export function invalidateToken(agentName: string) {
  _tokenCache.delete(agentName)
}

/**
 * fetch() autenticado al agente. Añade Authorization si hay token disponible.
 * Devuelve la respuesta cruda para que el caller haga el parsing que necesite.
 */
async function agentFetch(
  agentName: string,
  port: number,
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = await resolveToken(agentName)
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const url = `http://localhost:${port}${path}`
  return fetch(url, { ...init, headers })
}

// ---- Hub ----

export const getHubInfo = () => req<HubInfo>(`${HUB}/info`)
export const getHubHealth = () => req<Record<string, unknown>>(`${HUB}/health`)

export async function listProviderModels(): Promise<Record<string, string[] | null>> {
  return req<Record<string, string[] | null>>(`${HUB}/models`)
}

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

// ---- Chat directo al agente (autenticado) ----

export async function chatWithAgent(
  agentName: string,
  port: number,
  message: string,
  sessionId: string | null,
  model?: string | null,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const res = await agentFetch(agentName, port, '/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, model: model || null }),
    signal,
  })
  if (!res.ok) throw new Error(`Chat error: ${res.status}`)
  return res.json()
}

export interface ModelOption {
  ref: string
  provider: string
  model: string
  label: string
}

export async function getAgentModels(
  agentName: string,
  port: number,
): Promise<{ models: ModelOption[]; default: string }> {
  const res = await agentFetch(agentName, port, '/api/v1/models')
  if (!res.ok) throw new Error(`Models error: ${res.status}`)
  return res.json()
}

export interface UploadResult {
  filename: string
  size: number
}

// ---- Sesiones del agente (directo al puerto, autenticado) ----

export async function listAgentSessions(agentName: string, port: number): Promise<AgentSession[]> {
  const res = await agentFetch(agentName, port, '/api/v1/sessions')
  if (!res.ok) throw new Error(`Sessions error: ${res.status}`)
  return res.json()
}

export async function createAgentSession(
  agentName: string,
  port: number,
  title = 'Nueva sesión',
): Promise<AgentSession> {
  const res = await agentFetch(agentName, port, '/api/v1/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  if (!res.ok) throw new Error(`Create session error: ${res.status}`)
  return res.json()
}

export async function getSessionMessages(
  agentName: string,
  port: number,
  sessionId: string,
): Promise<SessionMessage[]> {
  const res = await agentFetch(agentName, port, `/api/v1/sessions/${sessionId}/messages`)
  if (!res.ok) throw new Error(`History error: ${res.status}`)
  return res.json()
}

export async function deleteAgentSession(
  agentName: string,
  port: number,
  sessionId: string,
): Promise<void> {
  await agentFetch(agentName, port, `/api/v1/sessions/${sessionId}`, { method: 'DELETE' })
}

export async function uploadToAgent(
  agentName: string,
  port: number,
  file: File,
): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await agentFetch(agentName, port, '/api/v1/upload', {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`Upload error: ${res.status}`)
  return res.json()
}

// ---- Export / Import (vía Hub) ----

export interface ExportResult {
  path: string
  filename: string
  size_kb: number
}

/** Exporta el agente a ~/AgentOS/exports/ en el servidor y devuelve la ruta. */
export async function exportAgent(name: string): Promise<ExportResult> {
  return req<ExportResult>(`${HUB}/agents/${encodeURIComponent(name)}/export`, {
    method: 'POST',
  })
}

/** Importa un agente desde un archivo .tar.gz. */
export async function importAgent(file: File): Promise<AgentInfo> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${HUB}/agents/import`, { method: 'POST', body: form })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try { const b = await res.json(); if (b?.detail) detail = b.detail } catch {}
    throw new Error(detail)
  }
  return res.json()
}

// ---- Logs y stats del agente (vía Hub, sin token — rutas del Hub) ----

export interface AgentLogs {
  lines: string[]
  count: number
}

export interface AgentStats {
  cpu_percent: number | null
  mem_mb: number | null
  uptime: number
}

export const getAgentLogs = (name: string, tail = 200) =>
  req<AgentLogs>(`${HUB}/agents/${encodeURIComponent(name)}/logs?tail=${tail}`)

export const getAgentStats = (name: string) =>
  req<AgentStats>(`${HUB}/agents/${encodeURIComponent(name)}/stats`)
