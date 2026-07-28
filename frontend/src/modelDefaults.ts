// num_ctx sugerido por proveedor/modelo. El usuario puede sobreescribir.
//
// Compartido entre CreateWizard.tsx (se aplica al elegir modelo al crear un
// agente) y AgentDetail.tsx (se aplica al cambiar provider/model editando
// uno ya creado) — antes solo vivía en CreateWizard, así que cambiar de
// modelo en la página de edición dejaba num_ctx con el valor viejo (ej. un
// agente que pasó de ollama/qwen2.5 a opencode-go/deepseek-v4-pro seguía
// mostrando la ventana de contexto de 8192 de qwen2.5 en vez de 1.000.000).
export const NUM_CTX_DEFAULTS: Record<string, number> = {
  // opencode-go
  'opencode-go/deepseek-v4-pro':  1000000,
  'opencode-go/deepseek-v4-flash': 1000000,
  'opencode-go/kimi-k3':          128000,
  'opencode-go/kimi-k2.7-code':   128000,
  'opencode-go/kimi-k2.6':        128000,
  'opencode-go/kimi-k2.5':        128000,
  'opencode-go/qwen3.7-max':       32000,
  'opencode-go/qwen3.7-plus':      32000,
  'opencode-go/qwen3.6-plus':      32000,
  'opencode-go/qwen3.5-plus':      32000,
  // opencode
  'opencode/deepseek-v4-pro':     1000000,
  'opencode/deepseek-v4-flash':   1000000,
  'opencode/claude-fable-5':      200000,
  'opencode/claude-opus-4-8':     200000,
  'opencode/claude-sonnet-5':     200000,
  'opencode/claude-sonnet-4-6':   200000,
  'opencode/claude-haiku-4-5':    200000,
  'opencode/gpt-5.5':             128000,
  'opencode/gpt-5.4':             128000,
  'opencode/gpt-5.4-mini':        128000,
  'opencode/gpt-5':               128000,
  // claude-cli (OAuth)
  'claude-cli/claude-fable-5':    200000,
  'claude-cli/claude-opus-4-8':   200000,
  'claude-cli/claude-sonnet-5':   200000,
  'claude-cli/claude-sonnet-4-6': 200000,
  'claude-cli/claude-haiku-4-5':  200000,
  // anthropic (API key de pago)
  'anthropic/claude-opus-4-8':    200000,
  'anthropic/claude-sonnet-4-6':  200000,
  'anthropic/claude-haiku-4-5':   200000,
  // openai
  'openai/gpt-4o':                128000,
  'openai/gpt-4o-mini':           128000,
  'openai/gpt-4.1':               128000,
  'openai/o3':                    200000,
  'openai/o4-mini':               200000,
}

const PROVIDER_DEFAULTS: Record<string, number> = {
  anthropic: 200000,
  'claude-cli': 200000,
  openai: 128000,
  opencode: 128000,
  'opencode-go': 64000,
}

export function suggestNumCtx(provider: string, model: string): number {
  return (
    NUM_CTX_DEFAULTS[`${provider}/${model}`] ??
    PROVIDER_DEFAULTS[provider] ??
    8192
  )
}
