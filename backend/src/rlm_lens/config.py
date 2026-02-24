from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    data_dir: Path
    default_corpus_path: str | None
    cors_origins: list[str]


def _parse_csv_env(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_settings() -> Settings:
    host = os.getenv("RLM_LENS_BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("RLM_LENS_BACKEND_PORT", os.getenv("PORT", "8765")))
    default_corpus_path = os.getenv("RLM_LENS_DEFAULT_CORPUS_PATH") or None
    data_dir = Path(os.getenv("RLM_LENS_DATA_DIR", str(Path.cwd() / ".rlm-lens")))
    cors_origins = _parse_csv_env(
        os.getenv(
            "RLM_LENS_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        )
    )
    return Settings(
        host=host,
        port=port,
        data_dir=data_dir,
        default_corpus_path=default_corpus_path,
        cors_origins=cors_origins,
    )
