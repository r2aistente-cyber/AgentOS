import { useState, useEffect } from 'react'
import {
  createAgent,
  listProviderModels,
  listSpecialties,
  previewSpecialty,
  type AgentConfig,
  type SpecialtySummary,
  type SpecialtyPreview,
} from '../api'
import FolderPicker from '../components/FolderPicker'
import { suggestNumCtx } from '../modelDefaults'

interface Props {
  onDone: () => void
  onCancel: () => void
}

const STEPS = ['Identidad', 'Personalidad', 'LLM', 'Tools y canales', 'Resumen']

const PROVIDERS = ['ollama', 'openai', 'anthropic', 'opencode', 'opencode-go', 'claude-cli', 'custom', 'mock']

// Catálogo estático obtenido de los endpoints reales de cada proveedor.
// Se funde con el catálogo del Hub; el dinámico (Ollama) prevalece.
const STATIC_CATALOG: Record<string, string[]> = {
  // opencode = https://opencode.ai/zen/v1  (todos los modelos premium)
  'opencode': [
    // Claude
    'claude-fable-5',
    'claude-opus-4-8',
    'claude-sonnet-5',
    'claude-sonnet-4-6',
    'claude-haiku-4-5',
    // GPT
    'gpt-5.5',
    'gpt-5.4',
    'gpt-5.4-mini',
    'gpt-5',
    'gpt-5-nano',
    // Gemini
    'gemini-3.5-flash',
    'gemini-3.1-pro',
    'gemini-3-flash',
    // DeepSeek
    'deepseek-v4-pro',
    'deepseek-v4-flash',
    // Otros
    'grok-4.5',
    'kimi-k2.6',
    'glm-5.2',
    'qwen3.6-plus',
    'minimax-m3',
    // Free tier
    'deepseek-v4-flash-free',
  ],
  // opencode-go = https://opencode.ai/zen/go/v1  (modelos Go/open-source)
  'opencode-go': [
    'deepseek-v4-pro',
    'deepseek-v4-flash',
    'kimi-k3',
    'kimi-k2.7-code',
    'kimi-k2.6',
    'kimi-k2.5',
    'glm-5.2',
    'glm-5.1',
    'glm-5',
    'qwen3.7-max',
    'qwen3.7-plus',
    'qwen3.6-plus',
    'qwen3.5-plus',
    'minimax-m3',
    'minimax-m2.7',
    'mimo-v2.5-pro',
    'mimo-v2.5',
    'grok-4.5',
    'hy3-preview',
  ],
  // claude-cli = OAuth de Claude Code (suscripcion Pro, sin API key)
  'claude-cli': [
    'claude-fable-5',
    'claude-opus-4-8',
    'claude-sonnet-5',
    'claude-sonnet-4-6',
    'claude-haiku-4-5',
  ],
  // anthropic = api.anthropic.com directo con API key de pago
  'anthropic': [
    'claude-opus-4-8',
    'claude-sonnet-4-6',
    'claude-haiku-4-5',
  ],
  // openai = api.openai.com directo
  'openai': [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4.1',
    'gpt-4.1-mini',
    'o3',
    'o4-mini',
  ],
}

const ALL_TOOLS = [
  'read_file',
  'write_file',
  'list_files',
  'search_files',
  'search_web',
  'fetch_url',
  'read_document',
  'read_image',
  'save_memory',
  'activar_skill',
  'exec_command',
]

// Estado del formulario, plano para editar fácil; se arma el AgentConfig al final.
interface Form {
  specialty: string
  name: string
  description: string
  install_path: string
  tone: string
  formality: string
  humor: string
  empathy: string
  system_prompt: string
  provider: string
  model: string
  host: string
  temperature: number
  num_ctx: number
  api_key: string
  extra_models: { provider: string; model: string; api_key?: string }[]
  tools: string[]
  brave_api_key: string
  web: boolean
  whatsapp: boolean
  telegram: boolean
  telegram_token: string
  telegram_chat_id: string
  security_level: number
  auto_restart: boolean
}

const DEFAULT: Form = {
  specialty: '',
  name: '',
  description: '',
  install_path: '',
  tone: 'directo',
  formality: 'tu',
  humor: 'poco',
  empathy: 'neutral',
  system_prompt: 'Eres un asistente útil.',
  provider: 'ollama',
  model: 'qwen2.5:latest',
  host: 'http://localhost:11434',
  temperature: 0.7,
  num_ctx: 8192,
  api_key: '',
  extra_models: [],
  tools: ['read_file', 'write_file', 'list_files', 'search_web'],
  brave_api_key: '',
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
  const [modelCatalog, setModelCatalog] = useState<Record<string, string[] | null>>({})
  const [specialties, setSpecialties] = useState<SpecialtySummary[]>([])
  const [specialtyPreview, setSpecialtyPreview] = useState<SpecialtyPreview | null>(null)
  const [specialtyError, setSpecialtyError] = useState<string | null>(null)

  // Carga el catálogo de modelos al montar el wizard; el estático sirve de base.
  useEffect(() => {
    setModelCatalog(STATIC_CATALOG)
    listProviderModels()
      .then((dynamic) => setModelCatalog({ ...STATIC_CATALOG, ...dynamic }))
      .catch(() => {})
    listSpecialties()
      .then(setSpecialties)
      .catch(() => {})
  }, [])

  // Elegir una specialty prellena personalidad/modelo/tools desde su
  // config_body resuelto — todo sigue editable después en los pasos
  // siguientes. "" (Personalizado) vuelve al comportamiento de siempre.
  const applySpecialty = async (id: string) => {
    set('specialty', id)
    setSpecialtyError(null)
    if (!id) {
      setSpecialtyPreview(null)
      return
    }
    try {
      const preview = await previewSpecialty(id)
      setSpecialtyPreview(preview)
      const cb = preview.config_body
      setF((p) => ({
        ...p,
        system_prompt: cb.system_prompt ?? p.system_prompt,
        tone: cb.personality?.tone ?? p.tone,
        formality: cb.personality?.formality ?? p.formality,
        humor: cb.personality?.humor ?? p.humor,
        empathy: cb.personality?.empathy ?? p.empathy,
        provider: cb.llm?.provider ?? p.provider,
        model: cb.llm?.model ?? p.model,
        temperature: cb.llm?.temperature ?? p.temperature,
        tools: cb.tools?.allow && !cb.tools.allow.includes('*') ? cb.tools.allow : p.tools,
        security_level: cb.security?.level ?? p.security_level,
      }))
    } catch (e) {
      setSpecialtyPreview(null)
      setSpecialtyError((e as Error).message)
    }
  }

  // Modelos disponibles para el proveedor actual (o null si es campo libre)
  const availableModels: string[] | null = modelCatalog[f.provider] ?? null

  const set = <K extends keyof Form>(k: K, v: Form[K]) => setF((p) => ({ ...p, [k]: v }))

  // Cambia provider: resetea modelo y auto-sugiere num_ctx
  const setProvider = (provider: string) =>
    setF((p) => ({
      ...p,
      provider,
      model: '',
      num_ctx: suggestNumCtx(provider, ''),
    }))

  // Cambia modelo: auto-sugiere num_ctx manteniendo el provider
  const setModel = (model: string) =>
    setF((p) => ({
      ...p,
      model,
      num_ctx: suggestNumCtx(p.provider, model),
    }))

  const nameValid = /^[a-zA-Z0-9_-]{2,40}$/.test(f.name)
  // claude-cli usa OAuth local — no pide API key
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
      personality: { tone: f.tone, formality: f.formality, humor: f.humor, empathy: f.empathy },
      system_prompt: f.system_prompt,
      llm: {
        provider: f.provider,
        model: f.model,
        host: f.host,
        temperature: f.temperature,
        num_ctx: f.num_ctx,
        ...(needsKey && f.api_key ? { api_key: f.api_key } : {}),
        // #10: modelos disponibles para elegir en el chat (#11).
        models: [
          { provider: f.provider, model: f.model, label: f.model },
          ...f.extra_models
            .filter((m) => m.model.trim())
            .map((m) => ({
              provider: m.provider,
              model: m.model.trim(),
              label: m.model.trim(),
              ...(m.api_key?.trim() ? { api_key: m.api_key.trim() } : {}),
            })),
        ],
      },
      tools: { allow: f.tools },
      ...(f.brave_api_key.trim() ? { search: { brave_api_key: f.brave_api_key.trim() } } : {}),
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
        specialty: f.specialty || undefined,
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
              label="Specialty"
              hint="Prellena personalidad, modelo, tools y skills desde una plantilla existente. Todo sigue editable después. 'Personalizado' es el comportamiento de siempre (sin plantilla)."
            >
              <select
                className={inputCls}
                value={f.specialty}
                onChange={(e) => applySpecialty(e.target.value)}
              >
                <option value="">Personalizado (sin specialty)</option>
                {specialties.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              {specialtyError && (
                <span className="mt-1 block text-xs text-rose-400">{specialtyError}</span>
              )}
            </Field>

            {specialtyPreview && (
              <div className="space-y-2 rounded-lg border border-indigo-900/60 bg-indigo-950/20 p-3 text-xs">
                <p className="text-slate-300">
                  <span className="font-medium text-slate-200">Modelo sugerido:</span>{' '}
                  {specialtyPreview.config_body.llm?.provider}/{specialtyPreview.config_body.llm?.model}
                  {' · '}
                  <span className="font-medium text-slate-200">Tools:</span>{' '}
                  {specialtyPreview.config_body.tools?.allow?.length ?? 0}
                </p>
                {specialtyPreview.always_on.length > 0 && (
                  <div>
                    <p className="font-medium text-slate-200">Skills siempre activas</p>
                    <ul className="list-inside list-disc text-slate-400">
                      {specialtyPreview.always_on.map((s) => (
                        <li key={s.name}><span className="font-mono text-slate-300">{s.name}</span>: {s.description}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {specialtyPreview.on_demand.length > 0 && (
                  <div>
                    <p className="font-medium text-slate-200">Skills bajo demanda</p>
                    <ul className="list-inside list-disc text-slate-400">
                      {specialtyPreview.on_demand.map((s) => (
                        <li key={s.name}><span className="font-mono text-slate-300">{s.name}</span>: {s.description}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {specialtyPreview.missing_knowledge_files.length > 0 && (
                  <p className="text-amber-400">
                    ⚠️ Archivos de conocimiento faltantes: {specialtyPreview.missing_knowledge_files.join(', ')}
                  </p>
                )}
              </div>
            )}

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
            <div className="grid grid-cols-4 gap-3">
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
              <Field label="Empatía">
                <select className={inputCls} value={f.empathy} onChange={(e) => set('empathy', e.target.value)}>
                  {['neutral', 'profesional', 'cercana', 'leal'].map((o) => (
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
                <select className={inputCls} value={f.provider} onChange={(e) => setProvider(e.target.value)}>
                  {PROVIDERS.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </Field>
              <Field label="Modelo">
                {availableModels ? (
                  <select
                    className={inputCls}
                    value={f.model}
                    onChange={(e) => setModel(e.target.value)}
                  >
                    <option value="">— elige modelo —</option>
                    {availableModels.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    className={inputCls}
                    value={f.model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="qwen2.5:latest / claude-opus-4-8 / gpt-4o"
                  />
                )}
              </Field>
            </div>
            {(f.provider === 'ollama' || f.provider === 'custom') && (
              <Field label="Host / Base URL">
                <input className={inputCls} value={f.host} onChange={(e) => set('host', e.target.value)} />
              </Field>
            )}
            {needsKey && (
              <Field label="API key" hint="Preferí la variable de entorno del proveedor si podés. Si la ponés acá, queda en el config.yaml del agente (nunca se incluye si lo exportás).">
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

            <Field label="Contexto (num_ctx / tokens)" hint={`Auto-sugerido: ${suggestNumCtx(f.provider, f.model).toLocaleString()} · editable`}>
              <input
                type="number"
                min={1024}
                max={200000}
                step={1024}
                value={f.num_ctx}
                onChange={(e) => set('num_ctx', Math.max(1024, Number(e.target.value)))}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-500"
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
              {f.extra_models.map((em, i) => {
                const needsExtraKey = ['openai', 'anthropic', 'opencode', 'opencode-go'].includes(em.provider)
                return (
                  <div key={i} className="mb-2 space-y-1">
                    <div className="flex items-center gap-2">
                      <select
                        value={em.provider}
                        onChange={(e) => {
                          const next = [...f.extra_models]
                          next[i] = { ...next[i], provider: e.target.value, model: '', api_key: '' }
                          set('extra_models', next)
                        }}
                        className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
                      >
                        {PROVIDERS.map((p) => (
                          <option key={p} value={p}>{p}</option>
                        ))}
                      </select>
                      {modelCatalog[em.provider] ? (
                        <select
                          value={em.model}
                          onChange={(e) => {
                            const next = [...f.extra_models]
                            next[i] = { ...next[i], model: e.target.value }
                            set('extra_models', next)
                          }}
                          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100"
                        >
                          <option value="">— elige modelo —</option>
                          {modelCatalog[em.provider]!.map((m) => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          value={em.model}
                          onChange={(e) => {
                            const next = [...f.extra_models]
                            next[i] = { ...next[i], model: e.target.value }
                            set('extra_models', next)
                          }}
                          placeholder="id del modelo"
                          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-indigo-500"
                        />
                      )}
                      <button
                        type="button"
                        onClick={() => set('extra_models', f.extra_models.filter((_, j) => j !== i))}
                        className="text-slate-500 hover:text-rose-400"
                        title="Quitar"
                      >
                        ✕
                      </button>
                    </div>
                    {needsExtraKey && (
                      <input
                        type="password"
                        value={em.api_key ?? ''}
                        onChange={(e) => {
                          const next = [...f.extra_models]
                          next[i] = { ...next[i], api_key: e.target.value }
                          set('extra_models', next)
                        }}
                        placeholder={`API key para ${em.provider} (sk-… / oc-…)`}
                        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-indigo-500"
                      />
                    )}
                  </div>
                )
              })}
              {availableModels && (
                <p className="text-xs text-slate-500">
                  {availableModels.length} modelos disponibles en {f.provider}
                </p>
              )}
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

            {f.tools.includes('search_web') && (
              <Field
                label="Brave Search API key (opcional)"
                hint="Sin key, search_web usa DuckDuckGo gratis. Se guarda en el config.yaml del agente — nunca se incluye si lo exportás."
              >
                <input
                  type="password"
                  className={inputCls}
                  value={f.brave_api_key}
                  onChange={(e) => set('brave_api_key', e.target.value)}
                  placeholder="BSA…"
                />
              </Field>
            )}

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
                ['Specialty', f.specialty || 'personalizado'],
                ['Nombre', f.name],
                ['Descripción', f.description || '—'],
                ['Ubicación', f.install_path || 'por defecto'],
                ['Personalidad', `${f.tone} · ${f.formality} · humor ${f.humor} · empatía ${f.empathy}`],
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
