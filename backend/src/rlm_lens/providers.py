from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Literal

SESSION_PROVIDER_KEY_HEADER = "X-RLM-LENS-PROVIDER-KEY"
_MAX_SESSION_KEY_LEN = 512


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    key_env_vars: tuple[str, ...]
    default_model: str
    recommended_models: tuple[str, ...]
    transport: Literal["native", "openai_compatible"]


_PROVIDER_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        id="openai",
        label="OpenAI",
        key_env_vars=("OPENAI_API_KEY",),
        default_model="gpt-5-nano",
        recommended_models=("gpt-5-mini", "gpt-5-nano"),
        transport="native",
    ),
    ProviderSpec(
        id="anthropic",
        label="Anthropic",
        key_env_vars=("ANTHROPIC_API_KEY",),
        default_model="claude-3-5-sonnet-latest",
        recommended_models=("claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"),
        transport="native",
    ),
    ProviderSpec(
        id="gemini",
        label="Google Gemini",
        key_env_vars=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        default_model="gemini-2.0-flash",
        recommended_models=("gemini-2.0-flash", "gemini-1.5-pro"),
        transport="native",
    ),
    ProviderSpec(
        id="xai",
        label="xAI",
        key_env_vars=("XAI_API_KEY",),
        default_model="grok-beta",
        recommended_models=("grok-beta", "grok-vision-beta"),
        transport="native",
    ),
    ProviderSpec(
        id="openrouter",
        label="OpenRouter",
        key_env_vars=("OPENROUTER_API_KEY",),
        default_model="openai/gpt-4o-mini",
        recommended_models=("openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet"),
        transport="openai_compatible",
    ),
    ProviderSpec(
        id="together",
        label="Together",
        key_env_vars=("TOGETHER_API_KEY",),
        default_model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        recommended_models=("meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "Qwen/Qwen2.5-72B-Instruct-Turbo"),
        transport="openai_compatible",
    ),
    ProviderSpec(
        id="groq",
        label="Groq",
        key_env_vars=("GROQ_API_KEY",),
        default_model="llama-3.3-70b-versatile",
        recommended_models=("llama-3.3-70b-versatile", "mixtral-8x7b-32768"),
        transport="openai_compatible",
    ),
    ProviderSpec(
        id="fireworks",
        label="Fireworks",
        key_env_vars=("FIREWORKS_API_KEY",),
        default_model="accounts/fireworks/models/llama-v3p1-70b-instruct",
        recommended_models=("accounts/fireworks/models/llama-v3p1-70b-instruct", "accounts/fireworks/models/qwen2p5-72b-instruct"),
        transport="openai_compatible",
    ),
)

_PROVIDER_MAP = {provider.id: provider for provider in _PROVIDER_SPECS}


def normalize_provider_id(provider: str | None) -> str:
    candidate = (provider or "openai").strip().lower()
    if not candidate:
        return "openai"
    return candidate if candidate in _PROVIDER_MAP else "openai"


def normalize_provider_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > _MAX_SESSION_KEY_LEN:
        return None
    return normalized


def get_provider_spec(provider: str | None) -> ProviderSpec:
    return _PROVIDER_MAP[normalize_provider_id(provider)]


def provider_key_present(provider: str | None, provider_api_key: str | None = None) -> bool:
    if normalize_provider_api_key(provider_api_key) is not None:
        return True
    spec = get_provider_spec(provider)
    return any(bool(os.getenv(env_var)) for env_var in spec.key_env_vars)


def provider_key_hint(provider: str | None) -> str:
    spec = get_provider_spec(provider)
    return " or ".join(spec.key_env_vars)


def provider_keys_present_map() -> dict[str, bool]:
    return {spec.id: provider_key_present(spec.id) for spec in _PROVIDER_SPECS}


def list_provider_payloads() -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for spec in _PROVIDER_SPECS:
        payloads.append(
            {
                "id": spec.id,
                "label": spec.label,
                "transport": spec.transport,
                "default_model": spec.default_model,
                "recommended_models": list(spec.recommended_models),
                "key_env_vars": list(spec.key_env_vars),
                "key_env_var": spec.key_env_vars[0],
                "key_present": provider_key_present(spec.id),
            }
        )
    return payloads


def build_provider_diagnostics(selected_provider: str | None = None) -> dict[str, object]:
    selected = normalize_provider_id(selected_provider)
    keys_present = provider_keys_present_map()
    return {
        "selected": selected,
        "openai_api_key_present": keys_present.get("openai", False),
        "keys_present": keys_present,
        "available": list_provider_payloads(),
        "byok_header_supported": True,
        "byok_header_name": SESSION_PROVIDER_KEY_HEADER,
        "session_key_storage": "ephemeral_request_header_only",
    }
