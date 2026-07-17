import { useState, useEffect, useRef, useCallback } from "react";
import {
  Plus, Trash2, Send, Bot, Wrench, Wifi, WifiOff,
  ChevronDown, Cpu, Zap,
} from "lucide-react";
import {
  sendMessage, listSessions, newSession, deleteSession,
  getSessionMessages, listModels, switchModel, getActiveModel,
  checkHealth, type Session, type Message,
} from "./api";

const TOOL_EMOJI: Record<string, string> = {
  read_file: "📄", write_file: "✏️", list_files: "📁", search_files: "🔍",
  search_web: "🌐", fetch_url: "🔗", save_memory: "💾", get_memory: "🧠",
  list_memories: "🗂️", exec_command: "⚡", clone_repo: "📥", commit_push: "📤",
  create_issue: "🐛", create_pr: "🔀", list_issues: "📋", list_prs: "📑",
  list_repos: "📦", npm_install: "📦", npm_build: "🔨", npm_run: "▶️",
  run_tests: "🧪", send_whatsapp: "📱",
};

function ToolBadge({ name }: { name: string }) {
  const emoji = TOOL_EMOJI[name] ?? "🔧";
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-700 text-zinc-300 text-xs font-mono">
      {emoji} {name}
    </span>
  );
}

function ChatBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center mr-2 shrink-0 mt-1">
          <Bot size={14} className="text-white" />
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? "max-w-[65%]" : ""}`}>
        <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-violet-600 text-white rounded-br-sm"
            : "bg-zinc-800 text-zinc-100 rounded-bl-sm"
        }`}>
          {msg.pending ? (
            <span className="flex gap-1">
              <span className="animate-bounce">•</span>
              <span className="animate-bounce [animation-delay:150ms]">•</span>
              <span className="animate-bounce [animation-delay:300ms]">•</span>
            </span>
          ) : msg.content}
        </div>
        {msg.tools_used && msg.tools_used.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5 ml-1">
            {msg.tools_used.map((t) => <ToolBadge key={t} name={t} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function ModelDropdown({ models, active, onSwitch }: {
  models: string[];
  active: string;
  onSwitch: (m: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs transition-colors"
      >
        <Cpu size={12} />
        <span className="max-w-[140px] truncate">{active}</span>
        <ChevronDown size={11} />
      </button>
      {open && (
        <div className="absolute top-full mt-1 left-0 z-50 min-w-[200px] bg-zinc-900 border border-zinc-700 rounded-xl shadow-xl overflow-hidden">
          {models.map(m => (
            <button
              key={m}
              onClick={() => { onSwitch(m); setOpen(false); }}
              className={`w-full text-left px-3 py-2 text-xs hover:bg-zinc-800 transition-colors flex items-center gap-2 ${
                m === active ? "text-violet-400 font-medium" : "text-zinc-300"
              }`}
            >
              <Cpu size={11} />
              {m}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<string[]>([]);
  const [activeModel, setActiveModel] = useState("qwen2.5:latest");
  const [online, setOnline] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  useEffect(() => {
    loadSessions();
    loadModels();
    const interval = setInterval(async () => {
      setOnline(await checkHealth());
    }, 15000);
    checkHealth().then(setOnline);
    return () => clearInterval(interval);
  }, []);

  async function loadSessions() {
    const list = await listSessions();
    setSessions(list);
    if (list.length > 0 && !activeSessionId) {
      setActiveSessionId(list[0].id);
      const msgs = await getSessionMessages(list[0].id);
      setMessages(msgs);
    }
  }

  async function loadModels() {
    const [list, active] = await Promise.all([listModels(), getActiveModel()]);
    setModels(list);
    setActiveModel(active);
  }

  const handleNewSession = async () => {
    const s = await newSession();
    setSessions(prev => [s, ...prev]);
    setActiveSessionId(s.id);
    setMessages([]);
  };

  const handleSelectSession = async (id: string) => {
    if (id === activeSessionId) return;
    setActiveSessionId(id);
    const msgs = await getSessionMessages(id);
    setMessages(msgs);
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await deleteSession(id);
    setSessions(prev => prev.filter(s => s.id !== id));
    if (activeSessionId === id) {
      const remaining = sessions.filter(s => s.id !== id);
      if (remaining.length > 0) {
        handleSelectSession(remaining[0].id);
      } else {
        setActiveSessionId(null);
        setMessages([]);
      }
    }
  };

  const handleSwitchModel = async (model: string) => {
    await switchModel(model);
    setActiveModel(model);
  };

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");

    const userMsg: Message = { role: "user", content: text };
    const pendingMsg: Message = { role: "assistant", content: "", pending: true };
    setMessages(prev => [...prev, userMsg, pendingMsg]);
    setLoading(true);

    try {
      const result = await sendMessage(text, activeSessionId);
      if (!activeSessionId) {
        setActiveSessionId(result.session_id);
        await loadSessions();
      }
      const assistantMsg: Message = {
        role: "assistant",
        content: result.reply,
        tools_used: result.tools_used,
      };
      setMessages(prev => [...prev.slice(0, -1), assistantMsg]);
    } catch {
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: "assistant", content: "❌ Error conectando al backend. ¿Está corriendo en :8234?" },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, activeSessionId]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const sessionTitle = (s: Session) =>
    s.title || `Sesión ${s.id.slice(0, 6)}`;

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 select-none">

      {/* ── Barra de sesiones ── */}
      <div className="flex items-center gap-1 px-2 py-1.5 bg-zinc-900 border-b border-zinc-800 overflow-x-auto shrink-0">
        {sessions.map(s => (
          <div
            key={s.id}
            onClick={() => handleSelectSession(s.id)}
            className={`group flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs cursor-pointer transition-colors shrink-0 ${
              s.id === activeSessionId
                ? "bg-zinc-700 text-white"
                : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
            }`}
          >
            <span className="max-w-[120px] truncate">{sessionTitle(s)}</span>
            <button
              onClick={(e) => handleDeleteSession(e, s.id)}
              className="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity"
            >
              <Trash2 size={11} />
            </button>
          </div>
        ))}
        <button
          onClick={handleNewSession}
          className="ml-auto shrink-0 p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
          title="Nueva sesión"
        >
          <Plus size={16} />
        </button>
      </div>

      {/* ── Barra rápida: modelo + estado ── */}
      <div className="flex items-center gap-3 px-4 py-2 bg-zinc-900/60 border-b border-zinc-800 shrink-0">
        <ModelDropdown models={models} active={activeModel} onSwitch={handleSwitchModel} />
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-zinc-800 text-zinc-400 text-xs">
          <Zap size={11} className="text-yellow-400" />
          Nivel 3
        </div>
        <div className={`ml-auto flex items-center gap-1.5 text-xs ${online ? "text-green-400" : "text-red-400"}`}>
          {online ? <Wifi size={13} /> : <WifiOff size={13} />}
          {online ? "Backend online" : "Backend offline"}
        </div>
      </div>

      {/* ── Área de mensajes ── */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-zinc-600 gap-3">
            <div className="w-16 h-16 rounded-full bg-zinc-800 flex items-center justify-center">
              <Bot size={32} className="text-violet-500" />
            </div>
            <p className="text-sm">Hola Xavier, ¿en qué te ayudo?</p>
            <p className="text-xs text-zinc-700">Ctrl+Space para abrir/cerrar</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatBubble key={i} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* ── Input ── */}
      <div className="px-4 pb-4 pt-2 shrink-0 bg-zinc-950">
        <div className="flex items-end gap-2 bg-zinc-800 rounded-2xl px-4 py-3 border border-zinc-700 focus-within:border-violet-500 transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe un mensaje... (Enter para enviar, Shift+Enter para nueva línea)"
            rows={1}
            className="flex-1 bg-transparent text-sm text-zinc-100 placeholder-zinc-500 resize-none outline-none max-h-40 leading-relaxed"
            style={{ height: "auto" }}
            onInput={e => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = Math.min(t.scrollHeight, 160) + "px";
            }}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-2 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
          >
            {loading ? (
              <Wrench size={16} className="text-white animate-spin" />
            ) : (
              <Send size={16} className="text-white" />
            )}
          </button>
        </div>
        <p className="text-center text-zinc-700 text-xs mt-1.5">
          R2 Autonomous · {activeModel}
        </p>
      </div>
    </div>
  );
}
