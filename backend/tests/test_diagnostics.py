from fastapi.testclient import TestClient

from rlm_lens.main import create_app


def test_diagnostics_shape() -> None:
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/diagnostics")
        assert res.status_code == 200
        payload = res.json()
        assert "provider" in payload
        assert "environment" in payload
        assert isinstance(payload["provider"]["openai_api_key_present"], bool)
        assert isinstance(payload["provider"]["keys_present"], dict)
        assert isinstance(payload["provider"]["available"], list)
        assert any(item["id"] == "openai" for item in payload["provider"]["available"])
        assert any(item["id"] == "anthropic" for item in payload["provider"]["available"])
        assert isinstance(payload["provider"]["keys_present"]["openai"], bool)
        assert isinstance(payload["provider"]["keys_present"]["anthropic"], bool)
        assert payload["provider"]["byok_header_supported"] is True
        assert isinstance(payload["environment"]["docker_installed"], bool)
        assert isinstance(payload["environment"]["docker_running"], bool)
