from rlm_lens.runtime.adapter import RLMAdapter
from rlm_lens.runtime.environment import EnvironmentStatus


def test_adapter_warns_when_openai_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = RLMAdapter(model="gpt-5-nano", provider="openai", environment="docker")
    warnings = adapter.warnings()
    assert any("OPENAI_API_KEY" in warning for warning in warnings)


def test_adapter_warns_when_anthropic_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    adapter = RLMAdapter(model="claude-3-5-sonnet-latest", provider="anthropic", environment="docker")
    warnings = adapter.warnings()
    assert any("ANTHROPIC_API_KEY" in warning for warning in warnings)


def test_adapter_accepts_ephemeral_provider_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    adapter = RLMAdapter(
        model="openai/gpt-4o-mini",
        provider="openrouter",
        environment="docker",
        provider_api_key="sk-session-test",
    )
    warnings = adapter.warnings()
    assert not any("OPENROUTER_API_KEY" in warning for warning in warnings)


def test_adapter_warns_when_docker_not_running(monkeypatch) -> None:
    monkeypatch.setattr(
        "rlm_lens.runtime.adapter.get_environment_status",
        lambda: EnvironmentStatus(docker_installed=True, docker_running=False),
    )
    adapter = RLMAdapter(model="gpt-5-nano", provider="openai", environment="docker")
    assert any("Docker sandbox unavailable" in warning for warning in adapter.warnings())


def test_adapter_fallback_subcall_contains_warnings(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = RLMAdapter(model="gpt-5-nano", provider="openai", environment="local")
    subcall = adapter.call_submodel("Find retry policy")
    assert subcall.response.startswith("Fallback analysis:")
    assert len(subcall.warnings) >= 1
