from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from .api.router import router as api_router
from .config import load_settings
from .services import Services


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    app.state.settings = settings
    app.state.services = Services(settings.data_dir)
    yield
    services: Services = app.state.services
    await services.shutdown()


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(title="RLM-Lens", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


def main() -> None:
    settings = load_settings()
    reload_enabled = os.getenv("RLM_LENS_RELOAD", "0").strip().lower() in {"1", "true", "yes", "on"}
    uvicorn.run("rlm_lens.main:create_app", host=settings.host, port=settings.port, reload=reload_enabled, factory=True)


if __name__ == "__main__":
    main()
