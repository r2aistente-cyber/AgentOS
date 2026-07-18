import { useState } from 'react'
import { createAgent, type AgentConfig } from '../api'
import FolderPicker from '../components/FolderPicker'

interface Props {
  onDone: () => void
  onCancel: () => void
}

const STEPS = ['Identidad', 'Personalidad', 'LLM', 'Tools y canales', 'Resumen']

const PROVIDERS = ['ollama', 'openai', 'anthropic', 'opencode', 'opencode-go', 'custom', 'mock']

// Catálogo del catálogo Go de OpenCode (suscripción, usa OPENCODE_API_KEY).
const OPENCODE_GO_MODELS = [
  'deepseek-v4-flash',
  'deepseek-v4-pro',
  'kimi-k2.6',
  'kimi-k2.7-code',
  'glm-5.2',
  'minimax-m2.7',
  'qwen3.6-plus',
]
const ALL_TOOLS = [
  'read_file',
  'write_file',
  'list_files',
  'search_web',
  'read_document',
  'read_image',
  'exec_command',
]

// Estado del formulario, plano para editar fácil; se arma el AgentConfig al final.
interface Form {
  name: string
  description: string
  install_path: string
  tone: string
  formality: string
  humor: string
  system_prompt: string
  provider: string
  model: string
  host: string
  temperature: number
  api_key: string
  extra_models: { provider: string; model: string }[]
  tools: string[]
  web: boolean
  whatsapp: boolean
  telegram: boolean
  telegram_token: string
  telegram_chat_id: string
  security_level: number
  auto_restart: boolean
}

const DEFAULT: Form = {
  name: '',
  description: '',
  install_path: '',
  tone: 'directo',
  formality: 'tu',
  humor: 'poco',
  system_prompt: 'Eres un asistente útil.',
  provider: 'ollama',
  model: 'qwen2.5:latest',
  host: 'http://localhost:11434',
  temperature: 0.7,
  api_key: '',
  extra_models: [],
  tools: ['read_file', 'write_file', 'list_files', 'search_web'],
  web: true,
  whatsapp: false,
  telegram: false,
  telegram_token: '',
  telegram_chat_id: '',
  security_level: 2,
  auto_restart: false,
}

function Field({
  label,
  children,
  hint,
}: {
  label: string
  children: React.ReactNode
  hint?: string
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-300">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  )
}

const inputCls =
  'w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-500'

export default function CreateWizard({ onDone, onCancel }: Props) {
  const [step, setStep] = useState(0)
  const [f, setF] = useState<Form>(DEFAULT)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pickerOpen, setPickerOpen] = useState(false)

  const set = <K extends keyof Form>(k: K, v: Form[K]) => setF((p) => ({ ...p, [k]: v }))

  const nameValid = /^[a-zA-Z0-9_-]{2,40}$/.test(f.name)
  const needsKey = ['openai', 'anthropic', 'opencode', 'opencode-go'].includes(f.provider)

  const canNext = () => {
    if (step === 0) return nameValid
    if (step === 2) return f.model.trim().length > 0
    return true
  }

  const toggleTool = (t: string) =>
    set('tools', f.tools.includes(t) ? f.tools.filter((x) => x !== t) : [...f.tools, t])

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    const config: AgentConfig = {
      agent: { name: f.name, description: f.description },
      personality: { tone: f.tone, formality: f.formality, humor: f.humor },
      system_prompt: f.system_prompt,
      llm: {
        provider: f.provider,
        model: f.model,
        host: f.host,
        temperature: f.temperature,
        ...(needsKey && f.api_key ? { api_key: f.api_key } : {}),
        // #10: modelos disponibles para elegir en el chat (#11).
        models: [
          { provider: f.provider, model: f.model, label: f.model },
          ...f.extra_models
            .filter((m) => m.model.trim())
            .map((m) => ({ provider: m.provider, model: m.model.trim(), label: m.model.trim() })),
        ],
      },
      tools: { allow: f.tools },
      security: { level: f.security_level },
      channels: {
        web: f.web,
        whatsapp: { enabled: f.whatsapp },
        telegram: {
          enabled: f.telegram,
          ...(f.telegram && f.telegram_token ? { token: f.telegram_token } : {}),
          ...(f.telegram && f.telegram_chat_id ? { chat_id: f.telegram_chat_id } : {}),
        },
      },
      auto_restart: f.auto_restart,
    }
    try {
      await createAgent({
        name: f.name,
        install_path: f.install_path || undefined,
        config,
      })
      onDone()
    } catch (e) {
      setError((e as Error).message)
      setStep(4)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      {pickerOpen && (
        <FolderPicker
          initialPath={f.install_path || undefined}
          onSelect={(p) => {
            set('install_path', p)
            setPickerOpen(false)
          }}
          onClose={() => setPickerOpen(false)}
        />
      )}

      {/* Progreso */}
      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-slate-100">✨ Crear Agente</h1>
          <span className="text-sm text-slate-500">
            Paso {step + 1} de {STEPS.length}
          </span>
        </div>
        <div className="flex gap-1">
          {STEPS.map((s, i) => (
            <div key={s} className="flex-1">
              <div
                className={`h-1.5 rounded-full ${i <= step ? 'bg-indigo-500' : 'bg-slate-800'}`}
              />
              <span
                className={`mt-1 block text-[11px] ${i === step ? 'text-indigo-300' : 'text-slate-600'}`}
              >
                {s}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        {/* Paso 1: Identidad */}
        {step === 0 && (
          <div className="space-y-4">
            <Field
              label="Nombre del agente"
              hint="Letras, números, guiones. 2–40 caracteres. Será el identificador."
            >
              <input
                className={inputCls}
                value={f.name}
                onChange={(e) => set('name', e.target.value)}
                placeholder="mi-agente"
                autoFocus
              />
              {f.name && !nameValid && (
                <span className="mt-1 block text-xs text-rose-400">
                  Solo letras, números, guion y guion bajo (2–40).
                </span>
              )}
            </Field>
            <Field label="Descripción">
              <input
                className={inputCls}
                value={f.description}
                onChange={(e) => set('description', e.target.value)}
                placeholder="Asistente personal"
              />
            </Field>
            <Field
              label="📁 Ubicación de instalación"
              hint="Vacío = ubicación por defecto (~/AgentOS/agents/<nombre>)."
            >
              <div className="flex gap-2">
                <input
                  className={inputCls}
                  value={f.install_path}
                  onChange={(e) => set('install_path', e.target.value)}
                  placeholder="C:\AgentOS\agents"
                />
                <button
                  type="button"
                  onClick={() => setPickerOpen(true)}
                  className="shrink-0 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 transition hover:bg-slate-700"
                >
                  📂 Examinar
                </button>
              </div>
            </Field>
          </div>
        )}

        {/* Paso 2: Personalidad */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <Field label="Tono">
                <select className={inputCls} value={f.tone} onChange={(e) => set('tone', e.target.value)}>
                  {['directo', 'cercano', 'formal', 'entusiasta'].map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </Field>
              <Field label="Trato">
                <select className={inputCls} value={f.formality} onChange={(e) => set('formality', e.target.value)}>
                  <option value="tu">Tú</option>
                  <option value="usted">Usted</option>
                </select>
              </Field>
              <Field label="Humor">
                <select className={inputCls} value={f.humor} onChange={(e) => set('humor', e.target.value)}>
                  {['nada', 'poco', 'medio', 'mucho'].map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </Field>
            </div>
            <Field label="System prompt" hint="Instrucción base que define al agente.">
              <textarea
                className={`${inputCls} h-28 resize-none`}
                value={f.system_prompt}
                onChange={(e) => set('system_prompt', e.target.value)}
              />
            </Field>
          </div>
        )}

        {/* Paso 3: LLM */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Proveedor">
                <select className={inputCls} value={f.provider} onChange={(e) => set('provider', e.target.value)}>
                  {PROVIDERS.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </Field>
              <Field label="Modelo">
                <input
                  className={inputCls}
                  value={f.model}
                  onChange={(e) => set('model', e.target.value)}
                  placeholder="qwen2.5:latest / claude-opus-4-8 / gpt-4o"
                />
              </Field>
            </div>
            {(f.provider === 'ollama' || f.provider === 'custom') && (
              <Field label="Host / Base URL">
                <input className={inputCls} value={f.host} onChange={(e) => set('host', e.target.value)} />
              </Field>
            )}
            {needsKey && (
              <Field label="API key" hint="Se guarda vía get_secret (variable de entorno), no en texto plano.">
                <input
                  type="password"
                  className={inputCls}
                  value={f.api_key}
                  onChange={(e) => set('api_key', e.target.value)}
                  placeholder="sk-…"
                />
              </Field>
            )}
            <Field label={`Temperatura: ${f.temperature.toFixed(2)}`}>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={f.temperature}
                onChange={(e) => set('temperature', Number(e.target.value))}
                className="w-full accent-indigo-500"
              />
            </Field>

            {/* #10: modelos adicionales para poder elegir en el chat (#11) */}
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-300">Modelos adicionales</span>
                <button
                  type="button"
                  onClick={() =>
                    set('extra_models', [...f.extra_models, { provider: 'ollama', model: '' }])
                  }
                  className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-200 hover:bg-slate-700"
                >
                  ＋ Agregar
                </button>
              </div>
              <p className="mb-2 text-xs text-slate-500">
                Se podrán elegir/cambiar en el chat sin reiniciar. El primario es el de arriba.
              </p>
              {f.extra_models.length === 0 && (
                <p className="text-xs text-slate-600">Ninguno. El agente usará solo el modelo primario.</p>
              )}
              {f.extra_models.map((em, i) => (
                <div key={i} className="mb-2 flex items-center gap-2">
                  <select
                    value={em.provider}
                    onChange={(e) => {
                      const next = [...f.extra_models]
                      next[i] = { ...next[i], provider: e.target.value }
                      set('extra_models', next)
                    }}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
                  >
                    {PROVIDERS.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                  <input
                    list={em.provider === 'opencode-go' ? 'opencode-go-models' : undefined}
                    value={em.model}
                    onChange={(e) => {
                      const next = [...f.extra_models]
                      next[i] = { ...next[i], model: e.target.value }
                      set('extra_models', next)
                    }}
                    placeholder="id del modelo"
                    className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={() => set('extra_models', f.extra_models.filter((_, j) => j !== i))}
                    className="text-slate-500 hover:text-rose-400"
                    title="Quitar"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <datalist id="opencode-go-models">
                {OPENCODE_GO_MODELS.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            </div>
          </div>
        )}

        {/* Paso 4: Tools y canales */}
        {step === 3 && (
          <div className="space-y-5">
            <div>
              <span className="mb-2 block text-sm font-medium text-slate-300">Tools permitidas</span>
              <div className="grid grid-cols-2 gap-2">
                {ALL_TOOLS.map((t) => (
                  <label
                    key={t}
                    className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={f.tools.includes(t)}
                      onChange={() => toggleTool(t)}
                      className="accent-indigo-500"
                    />
                    <span className="font-mono text-slate-300">{t}</span>
                    {t === 'exec_command' && <span className="ml-auto text-xs text-amber-400">⚠️</span>}
                  </label>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Nivel de seguridad">
                <select
                  className={inputCls}
                  value={f.security_level}
                  onChange={(e) => set('security_level', Number(e.target.value))}
                >
                  <option value={1}>1 — permisivo</option>
                  <option value={2}>2 — estándar</option>
                  <option value={3}>3 — estricto</option>
                </select>
              </Field>
              <div className="flex flex-col justify-end gap-2 pb-1">
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input type="checkbox" checked={f.web} onChange={(e) => set('web', e.target.checked)} className="accent-indigo-500" />
                  Canal web
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input type="checkbox" checked={f.whatsapp} onChange={(e) => set('whatsapp', e.target.checked)} className="accent-indigo-500" />
                  WhatsApp
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input type="checkbox" checked={f.telegram} onChange={(e) => set('telegram', e.target.checked)} className="accent-indigo-500" />
                  Telegram
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input type="checkbox" checked={f.auto_restart} onChange={(e) => set('auto_restart', e.target.checked)} className="accent-indigo-500" />
                  Auto-reinicio
                </label>
              </div>
            </div>

            {/* Credenciales de Telegram (solo si está activo) */}
            {f.telegram && (
              <div className="grid grid-cols-2 gap-3 rounded-lg border border-sky-900/60 bg-sky-950/20 p-3">
                <Field label="Bot token" hint="De @BotFather.">
                  <input
                    type="password"
                    className={inputCls}
                    value={f.telegram_token}
                    onChange={(e) => set('telegram_token', e.target.value)}
                    placeholder="123456:ABC-…"
                  />
                </Field>
                <Field label="Chat ID" hint="Destino de los mensajes.">
                  <input
                    className={inputCls}
                    value={f.telegram_chat_id}
                    onChange={(e) => set('telegram_chat_id', e.target.value)}
                    placeholder="1586486025"
                  />
                </Field>
              </div>
            )}
          </div>
        )}

        {/* Paso 5: Resumen */}
        {step === 4 && (
          <div className="space-y-3 text-sm">
            <h2 className="text-base font-semibold text-slate-100">Resumen</h2>
            {error && (
              <div className="rounded-lg border border-rose-800 bg-rose-950/50 px-3 py-2 text-rose-300">
                {error}
              </div>
            )}
            <dl className="divide-y divide-slate-800 rounded-lg border border-slate-800">
              {[
                ['Nombre', f.name],
                ['Descripción', f.description || '—'],
                ['Ubicación', f.install_path || 'por defecto'],
                ['Personalidad', `${f.tone} · ${f.formality} · humor ${f.humor}`],
                ['LLM', `${f.provider} / ${f.model} · temp ${f.temperature}`],
                ['Tools', f.tools.join(', ') || 'ninguna'],
                ['Canales', [f.web && 'web', f.whatsapp && 'whatsapp', f.telegram && 'telegram'].filter(Boolean).join(', ') || 'ninguno'],
                ['Seguridad', `nivel ${f.security_level}${f.auto_restart ? ' · auto-restart' : ''}`],
              ].map(([k, v]) => (
                <div key={k} className="flex gap-3 px-3 py-2">
                  <dt className="w-28 shrink-0 text-slate-500">{k}</dt>
                  <dd className="text-slate-200">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>

      {/* Navegación */}
      <div className="mt-5 flex items-center justify-between">
        <button
          onClick={step === 0 ? onCancel : () => setStep((s) => s - 1)}
          className="rounded-lg px-4 py-2 text-sm text-slate-400 transition hover:text-slate-200"
        >
          {step === 0 ? 'Cancelar' : '← Atrás'}
        </button>
        {step < STEPS.length - 1 ? (
          <button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canNext()}
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-40"
          >
            Siguiente →
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={submitting || !nameValid}
            className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:opacity-40"
          >
            {submitting ? 'Creando…' : '✓ Crear agente'}
          </button>
        )}
      </div>
    </div>
  )
}
