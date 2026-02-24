import type { Diagnostics, ProviderOption } from './types';

export const FALLBACK_PROVIDER_OPTIONS: ProviderOption[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    transport: 'native',
    default_model: 'gpt-5-nano',
    recommended_models: ['gpt-5-mini', 'gpt-5-nano'],
    key_env_vars: ['OPENAI_API_KEY'],
    key_env_var: 'OPENAI_API_KEY',
    key_present: false,
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    transport: 'native',
    default_model: 'claude-3-5-sonnet-latest',
    recommended_models: ['claude-3-5-sonnet-latest', 'claude-3-5-haiku-latest'],
    key_env_vars: ['ANTHROPIC_API_KEY'],
    key_env_var: 'ANTHROPIC_API_KEY',
    key_present: false,
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    transport: 'native',
    default_model: 'gemini-2.0-flash',
    recommended_models: ['gemini-2.0-flash', 'gemini-1.5-pro'],
    key_env_vars: ['GEMINI_API_KEY', 'GOOGLE_API_KEY'],
    key_env_var: 'GEMINI_API_KEY',
    key_present: false,
  },
  {
    id: 'xai',
    label: 'xAI',
    transport: 'native',
    default_model: 'grok-beta',
    recommended_models: ['grok-beta', 'grok-vision-beta'],
    key_env_vars: ['XAI_API_KEY'],
    key_env_var: 'XAI_API_KEY',
    key_present: false,
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    transport: 'openai_compatible',
    default_model: 'openai/gpt-4o-mini',
    recommended_models: ['openai/gpt-4o-mini', 'anthropic/claude-3.5-sonnet'],
    key_env_vars: ['OPENROUTER_API_KEY'],
    key_env_var: 'OPENROUTER_API_KEY',
    key_present: false,
  },
  {
    id: 'together',
    label: 'Together',
    transport: 'openai_compatible',
    default_model: 'meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo',
    recommended_models: ['meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo', 'Qwen/Qwen2.5-72B-Instruct-Turbo'],
    key_env_vars: ['TOGETHER_API_KEY'],
    key_env_var: 'TOGETHER_API_KEY',
    key_present: false,
  },
  {
    id: 'groq',
    label: 'Groq',
    transport: 'openai_compatible',
    default_model: 'llama-3.3-70b-versatile',
    recommended_models: ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768'],
    key_env_vars: ['GROQ_API_KEY'],
    key_env_var: 'GROQ_API_KEY',
    key_present: false,
  },
  {
    id: 'fireworks',
    label: 'Fireworks',
    transport: 'openai_compatible',
    default_model: 'accounts/fireworks/models/llama-v3p1-70b-instruct',
    recommended_models: ['accounts/fireworks/models/llama-v3p1-70b-instruct', 'accounts/fireworks/models/qwen2p5-72b-instruct'],
    key_env_vars: ['FIREWORKS_API_KEY'],
    key_env_var: 'FIREWORKS_API_KEY',
    key_present: false,
  },
];

export function providerOptionsFromDiagnostics(diagnostics: Diagnostics | null): ProviderOption[] {
  const available = diagnostics?.provider.available;
  if (Array.isArray(available) && available.length > 0) {
    return available;
  }
  return FALLBACK_PROVIDER_OPTIONS;
}

export function providerOptionById(providerId: string, diagnostics: Diagnostics | null): ProviderOption | undefined {
  return providerOptionsFromDiagnostics(diagnostics).find((item) => item.id === providerId);
}

export function providerLabel(providerId: string, diagnostics: Diagnostics | null): string {
  return providerOptionById(providerId, diagnostics)?.label ?? providerId;
}

export function providerDefaultModel(providerId: string, diagnostics: Diagnostics | null): string {
  return providerOptionById(providerId, diagnostics)?.default_model ?? 'gpt-5-nano';
}

export function providerEnvHint(providerId: string, diagnostics: Diagnostics | null): string {
  const option = providerOptionById(providerId, diagnostics);
  if (!option) {
    return 'OPENAI_API_KEY';
  }
  if (option.key_env_vars.length <= 1) {
    return option.key_env_var;
  }
  return option.key_env_vars.join(' or ');
}

export function providerKeyReady(providerId: string, diagnostics: Diagnostics | null): boolean {
  const keysPresent = diagnostics?.provider.keys_present;
  if (keysPresent && typeof keysPresent === 'object' && providerId in keysPresent) {
    return Boolean(keysPresent[providerId]);
  }
  if (providerId === 'openai') {
    return Boolean(diagnostics?.provider.openai_api_key_present);
  }
  const option = providerOptionById(providerId, diagnostics);
  return Boolean(option?.key_present);
}
