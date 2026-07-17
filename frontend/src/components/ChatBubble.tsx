import ToolBadge from './ToolBadge'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  tools_used?: string[]
  pending?: boolean
}

interface Props {
  msg: ChatMessage
}

export default function ChatBubble({ msg }: Props) {
  const isUser = msg.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center text-xs mr-2 mt-0.5 shrink-0">
          🤖
        </div>
      )}

      <div className={`max-w-[78%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words ${
            isUser
              ? 'bg-violet-600 text-white rounded-br-sm'
              : 'bg-gray-800 text-gray-100 rounded-bl-sm'
          } ${msg.pending ? 'opacity-60' : ''}`}
        >
          {msg.pending ? (
            <span className="flex gap-1 items-center text-gray-400">
              <span className="animate-bounce delay-0">●</span>
              <span className="animate-bounce delay-100">●</span>
              <span className="animate-bounce delay-200">●</span>
            </span>
          ) : (
            msg.content
          )}
        </div>

        {msg.tools_used && <ToolBadge tools={msg.tools_used} />}
      </div>

      {isUser && (
        <div className="w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center text-xs ml-2 mt-0.5 shrink-0">
          X
        </div>
      )}
    </div>
  )
}
