import { useRef, useState } from 'react'

interface Props {
  onSend: (text: string, file?: File) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('')
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const send = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) onSend(`[Archivo adjunto: ${file.name}]`, file)
  }

  return (
    <div
      className={`border-t border-gray-800 p-3 ${dragging ? 'bg-violet-950' : 'bg-gray-950'}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      {dragging && (
        <div className="text-center text-violet-400 text-sm py-1 mb-2">
          Suelta el archivo aquí...
        </div>
      )}

      <div className="flex gap-2 items-end">
        <button
          onClick={() => fileRef.current?.click()}
          className="text-gray-500 hover:text-gray-300 p-2 rounded-lg hover:bg-gray-800 transition-colors shrink-0"
          title="Adjuntar archivo"
        >
          📎
        </button>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
          placeholder="Escribe un mensaje... (Enter para enviar, Shift+Enter para nueva línea)"
          rows={1}
          className="flex-1 bg-gray-800 text-gray-100 rounded-xl px-4 py-2.5 text-sm resize-none outline-none border border-gray-700 focus:border-violet-500 placeholder-gray-500 disabled:opacity-50 transition-colors"
          style={{ minHeight: '42px', maxHeight: '120px' }}
        />

        <button
          onClick={send}
          disabled={disabled || !text.trim()}
          className="bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl px-4 py-2.5 text-sm font-medium transition-colors shrink-0"
        >
          ➤
        </button>
      </div>

      <input
        ref={fileRef}
        type="file"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onSend(`[Archivo adjunto: ${file.name}]`, file)
          e.target.value = ''
        }}
      />
    </div>
  )
}
