from __future__ import annotations

from unittest.mock import patch

from rlm_lens.config import load_settings
from rlm_lens.main import main


def test_port_falls_back_to_platform_port(monkeypatch) -> None:
    monkeypatch.delenv("RLM_LENS_BACKEND_PORT", raising=False)
    monkeypatch.setenv("PORT", "9001")

    settings = load_settings()
    assert settings.port == 9001


def test_explicit_backend_port_overrides_platform_port(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "9001")
    monkeypatch.setenv("RLM_LENS_BACKEND_PORT", "8765")

    settings = load_settings()
    assert settings.port == 8765


def test_main_uses_reload_flag_from_env(monkeypatch) -> None:
    monkeypatch.setenv("RLM_LENS_BACKEND_HOST", "127.0.0.1")
    monkeypatch.setenv("RLM_LENS_BACKEND_PORT", "8765")
    monkeypatch.setenv("RLM_LENS_RELOAD", "1")

    with patch("rlm_lens.main.uvicorn.run") as run_mock:
        main()

    assert run_mock.call_count == 1
    _, kwargs = run_mock.call_args
    assert kwargs["reload"] is True


def test_main_reload_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("RLM_LENS_BACKEND_HOST", "127.0.0.1")
    monkeypatch.setenv("RLM_LENS_BACKEND_PORT", "8765")
    monkeypatch.delenv("RLM_LENS_RELOAD", raising=False)

    with patch("rlm_lens.main.uvicorn.run") as run_mock:
        main()

    assert run_mock.call_count == 1
    _, kwargs = run_mock.call_args
    assert kwargs["reload"] is False
