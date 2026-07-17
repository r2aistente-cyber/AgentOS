const BASE = "/api/v1";

export interface Message {
  role: "user" | "assistant";
  content: string;
  tools_used?: string[];
  pending?: boolean;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
}

export interface OllamaModel {
  name: string;
  size: number;
}

export async function sendMessage(
  message: string,
  sessionId: string | null,
  specialty = "core"
): Promise<{ session_id: string; reply: string; tools_used: string[]; tokens: number }> {
  const res = await fetch("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, user_id: "xavier", specialty_id: specialty }),
  });
  if (!res.ok) throw new Error(`Chat error ${res.status}`);
  return res.json();
}

export async function listSessions(): Promise<Session[]> {
  const res = await fetch(`${BASE}/sessions`);
  if (!res.ok) return [];
  return res.json();
}

export async function newSession(title = "Nueva sesión"): Promise<Session> {
  const res = await fetch(`${BASE}/sessions/new`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function deleteSession(id: string): Promise<void> {
  await fetch(`${BASE}/sessions/${id}`, { method: "DELETE" });
}

export async function getSessionMessages(id: string): Promise<Message[]> {
  const res = await fetch(`${BASE}/sessions/${id}`);
  if (!res.ok) return [];
  const data = await res.json();
  return (data.messages || []).map((m: { role: string; content: string }) => ({
    role: m.role,
    content: m.content,
  }));
}

export async function listModels(): Promise<string[]> {
  try {
    const res = await fetch(`${BASE}/models`);
    if (!res.ok) return [];
    const data = await res.json();
    return (data.models || []).map((m: OllamaModel) => m.name);
  } catch {
    return [];
  }
}

export async function switchModel(model: string): Promise<void> {
  await fetch(`${BASE}/models/switch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
  });
}

export async function getActiveModel(): Promise<string> {
  try {
    const res = await fetch(`${BASE}/models/active`);
    if (!res.ok) return "qwen2.5:latest";
    const data = await res.json();
    return data.model || "qwen2.5:latest";
  } catch {
    return "qwen2.5:latest";
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch("/health", { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}
