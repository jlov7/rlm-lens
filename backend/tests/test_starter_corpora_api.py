from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from rlm_lens.main import create_app


def test_starter_corpora_catalog_and_materialization() -> None:
    app = create_app()
    with TestClient(app) as client:
        listing = client.get("/api/starter-corpora")
        assert listing.status_code == 200
        packs = listing.json()
        ids = {pack["id"] for pack in packs}
        assert {"fixture-small", "synthetic-medium", "oss-flask-main"}.issubset(ids)

        materialize = client.post("/api/starter-corpora/synthetic-medium/materialize")
        assert materialize.status_code == 200
        payload = materialize.json()
        assert payload["pack_id"] == "synthetic-medium"
        assert payload["installed"] is True
        assert payload["files_total"] >= 150
        assert Path(payload["path"]).exists()


def test_starter_corpus_missing_pack_returns_404() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.post("/api/starter-corpora/does-not-exist/materialize")
        assert response.status_code == 404
