interface Props {
  tools: string[]
}

const TOOL_ICONS: Record<string, string> = {
  read_file: '📄', write_file: '✏️', list_files: '📁', search_files: '🔍',
  search_web: '🌐', fetch_url: '🔗',
  save_memory: '💾', get_memory: '🧠', list_memories: '📚',
  send_whatsapp: '📱',
}

export default function ToolBadge({ tools }: Props) {
  if (!tools.length) return null
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {tools.map((t, i) => (
        <span
          key={i}
          className="text-xs bg-gray-800 text-gray-400 rounded px-2 py-0.5 border border-gray-700"
        >
          {TOOL_ICONS[t] ?? '🔧'} {t}
        </span>
      ))}
    </div>
  )
}
