FROM ghcr.io/astral-sh/uv:python3.12-bookworm

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/README.md /app/backend/
WORKDIR /app/backend
RUN uv sync --frozen --no-dev

COPY backend/src /app/backend/src

ENV PYTHONPATH=/app/backend/src \
    RLM_LENS_BACKEND_HOST=0.0.0.0 \
    RLM_LENS_BACKEND_PORT=8765

EXPOSE 8765

CMD ["uv", "run", "uvicorn", "rlm_lens.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8765"]
