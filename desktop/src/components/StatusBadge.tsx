import type { AgentStatus } from '../api'

const MAP: Record<AgentStatus, { dot: string; label: string; text: string }> = {
  online: { dot: 'bg-emerald-400', label: 'En línea', text: 'text-emerald-400' },
  starting: { dot: 'bg-amber-400 animate-pulse', label: 'Iniciando', text: 'text-amber-400' },
  offline: { dot: 'bg-slate-500', label: 'Detenido', text: 'text-slate-400' },
  error: { dot: 'bg-rose-500', label: 'Error', text: 'text-rose-400' },
}

export default function StatusBadge({ status }: { status: AgentStatus }) {
  const s = MAP[status] ?? MAP.offline
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      <span className={`h-2 w-2 rounded-full ${s.dot}`} />
      <span className={s.text}>{s.label}</span>
    </span>
  )
}
