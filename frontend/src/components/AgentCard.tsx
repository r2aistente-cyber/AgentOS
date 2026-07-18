import type { AgentInfo } from '../api'
import StatusBadge from './StatusBadge'

interface Props {
  agent: AgentInfo
  busy?: boolean
  onChat: (a: AgentInfo) => void
  onConfig: (a: AgentInfo) => void
  onLogs: (a: AgentInfo) => void
  onStart: (a: AgentInfo) => void
  onStop: (a: AgentInfo) => void
}

function Btn({
  children,
  onClick,
  disabled,
  variant = 'default',
}: {
  children: React.ReactNode
  onClick: () => void
  disabled?: boolean
  variant?: 'default' | 'primary' | 'danger'
}) {
  const base =
    'rounded-md px-2.5 py-1 text-xs font-medium transition disabled:opacity-40 disabled:cursor-not-allowed'
  const styles = {
    default: 'bg-slate-800 hover:bg-slate-700 text-slate-200',
    primary: 'bg-indigo-600 hover:bg-indigo-500 text-white',
    danger: 'bg-rose-600/90 hover:bg-rose-500 text-white',
  }[variant]
  return (
    <button className={`${base} ${styles}`} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  )
}

export default function AgentCard({
  agent,
  busy,
  onChat,
  onConfig,
  onLogs,
  onStart,
  onStop,
}: Props) {
  const online = agent.status === 'online'
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm transition hover:border-slate-700">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-lg">🤖</span>
            <h3 className="truncate text-base font-semibold text-slate-100">{agent.name}</h3>
          </div>
          <p className="mt-0.5 truncate text-xs text-slate-500" title={agent.install_path}>
            {agent.install_path}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge status={agent.status} />
          <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[11px] font-mono text-slate-400">
            :{agent.port}
          </span>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Btn variant="primary" onClick={() => onChat(agent)} disabled={busy}>
          💬 Chat
        </Btn>
        <Btn onClick={() => onLogs(agent)} disabled={busy}>
          📊 Logs
        </Btn>
        <Btn onClick={() => onConfig(agent)} disabled={busy}>
          ⚙️ Config
        </Btn>
        {online ? (
          <Btn variant="danger" onClick={() => onStop(agent)} disabled={busy}>
            ⏹️ Detener
          </Btn>
        ) : (
          <Btn variant="primary" onClick={() => onStart(agent)} disabled={busy}>
            ▶️ Iniciar
          </Btn>
        )}
      </div>
    </div>
  )
}
