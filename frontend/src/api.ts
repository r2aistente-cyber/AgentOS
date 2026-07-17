const BASE = '/api/v1'

export interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
}

export interface ChatResponse {
  session_id: string
  reply: string
  tools_used: string[]
  tokens: number
}

export interface Session {
  id: string
  user_id: string
  specialty_id: string
  title: string
  created_at: string
}

export interface Model {
  name: string
  size: number
}

export async function sendMessage(
  message: string,
  sessionId: string | null,
  specialtyId = 'core',
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, specialty_id: specialtyId }),
  })
  if (!res.ok) throw new Error(`Chat error: ${res.status}`)
  return res.json()
}

export async function listSessions(): Promise<Session[]> {
  const res = await fetch(`${BASE}/sessions`)
  if (!res.ok) throw new Error('Error cargando sesiones')
  return res.json()
}

export async function newSession(specialtyId = 'core', title = 'Nueva sesión'): Promise<string> {
  const res = await fetch(`${BASE}/sessions/new`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ specialty_id: specialtyId, title }),
  })
  const data = await res.json()
  return data.session_id
}

export async function getSession(sessionId: string): Promise<{ session: Session; messages: Message[] }> {
  const res = await fetch(`${BASE}/sessions/${sessionId}`)
  if (!res.ok) throw new Error('Sesión no encontrada')
  return res.json()
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${BASE}/sessions/${sessionId}`, { method: 'DELETE' })
}

export async function listModels(): Promise<Model[]> {
  const res = await fetch(`${BASE}/models`)
  if (!res.ok) return []
  return res.json()
}

export async function uploadFile(file: File): Promise<{ file_id: string; filename: string }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/files/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Error subiendo archivo')
  return res.json()
}
