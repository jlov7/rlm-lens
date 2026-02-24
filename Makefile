SHELL := /bin/bash

BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8765
FRONTEND_PORT ?= 5173

.PHONY: dev check e2e verify-visual demo starter-corpora clean backend-dev frontend-dev

dev:
	@set -euo pipefail; \
	cd $(BACKEND_DIR) && uv sync --group dev; \
	cd ../$(FRONTEND_DIR) && pnpm install; \
	( cd ../$(BACKEND_DIR) && RLM_LENS_BACKEND_HOST=$(BACKEND_HOST) RLM_LENS_BACKEND_PORT=$(BACKEND_PORT) RLM_LENS_RELOAD=1 uv run python -m rlm_lens.main ) & \
	BACK_PID=$$!; \
	( cd ../$(FRONTEND_DIR) && RLM_LENS_FRONTEND_PORT=$(FRONTEND_PORT) pnpm dev --host $(BACKEND_HOST) --port $(FRONTEND_PORT) ) & \
	FRONT_PID=$$!; \
	trap 'kill $$BACK_PID $$FRONT_PID 2>/dev/null || true' EXIT INT TERM; \
	wait $$BACK_PID $$FRONT_PID

backend-dev:
	@cd $(BACKEND_DIR) && uv sync --group dev && RLM_LENS_RELOAD=1 uv run python -m rlm_lens.main

frontend-dev:
	@cd $(FRONTEND_DIR) && pnpm install && pnpm dev --host $(BACKEND_HOST) --port $(FRONTEND_PORT)

check:
	@set -euo pipefail; \
	cd $(BACKEND_DIR) && uv sync --group dev && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src && uv run pytest; \
	cd ../$(FRONTEND_DIR) && pnpm install && pnpm lint && pnpm typecheck && pnpm test

e2e:
	@set -euo pipefail; \
	cd $(BACKEND_DIR) && uv sync --group dev; \
	cd ../$(FRONTEND_DIR) && pnpm install; \
	( cd ../$(BACKEND_DIR) && RLM_LENS_BACKEND_HOST=$(BACKEND_HOST) RLM_LENS_BACKEND_PORT=$(BACKEND_PORT) uv run python -m rlm_lens.main ) & \
	BACK_PID=$$!; \
	( cd ../$(FRONTEND_DIR) && RLM_LENS_FRONTEND_PORT=$(FRONTEND_PORT) pnpm dev --host $(BACKEND_HOST) --port $(FRONTEND_PORT) ) & \
	FRONT_PID=$$!; \
	trap 'kill $$BACK_PID $$FRONT_PID 2>/dev/null || true' EXIT INT TERM; \
	for i in {1..60}; do curl -sf http://$(BACKEND_HOST):$(BACKEND_PORT)/api/health && break || sleep 1; done; \
	for i in {1..60}; do curl -sf http://$(BACKEND_HOST):$(FRONTEND_PORT) >/dev/null && break || sleep 1; done; \
	cd ../$(FRONTEND_DIR) && pnpm exec playwright install chromium && pnpm e2e

verify-visual:
	@set -euo pipefail; \
	cd $(BACKEND_DIR) && uv sync --group dev; \
	cd ../$(FRONTEND_DIR) && pnpm install; \
	( cd ../$(BACKEND_DIR) && RLM_LENS_BACKEND_HOST=$(BACKEND_HOST) RLM_LENS_BACKEND_PORT=$(BACKEND_PORT) uv run python -m rlm_lens.main ) & \
	BACK_PID=$$!; \
	( cd ../$(FRONTEND_DIR) && RLM_LENS_FRONTEND_PORT=$(FRONTEND_PORT) pnpm dev --host $(BACKEND_HOST) --port $(FRONTEND_PORT) ) & \
	FRONT_PID=$$!; \
	trap 'kill $$BACK_PID $$FRONT_PID 2>/dev/null || true' EXIT INT TERM; \
	for i in {1..60}; do curl -sf http://$(BACKEND_HOST):$(BACKEND_PORT)/api/health && break || sleep 1; done; \
	for i in {1..60}; do curl -sf http://$(BACKEND_HOST):$(FRONTEND_PORT) >/dev/null && break || sleep 1; done; \
	cd ../$(FRONTEND_DIR) && pnpm exec playwright install chromium firefox webkit && pnpm visual && pnpm visual:index

demo:
	@set -euo pipefail; \
	cd $(BACKEND_DIR) && uv sync --group dev; \
	cd ../$(FRONTEND_DIR) && pnpm install; \
	( cd ../$(BACKEND_DIR) && RLM_LENS_BACKEND_HOST=$(BACKEND_HOST) RLM_LENS_BACKEND_PORT=$(BACKEND_PORT) uv run python -m rlm_lens.main ) & \
	BACK_PID=$$!; \
	( cd ../$(FRONTEND_DIR) && RLM_LENS_FRONTEND_PORT=$(FRONTEND_PORT) pnpm dev --host $(BACKEND_HOST) --port $(FRONTEND_PORT) ) & \
	FRONT_PID=$$!; \
	trap 'kill $$BACK_PID $$FRONT_PID 2>/dev/null || true' EXIT INT TERM; \
	for i in {1..60}; do curl -sf http://$(BACKEND_HOST):$(BACKEND_PORT)/api/health && break || sleep 1; done; \
	cd ../$(BACKEND_DIR) && uv run python -m rlm_lens.demo; \
	open "http://$(BACKEND_HOST):$(FRONTEND_PORT)/?demo=1" >/dev/null 2>&1 || true; \
	echo "Demo ready at http://$(BACKEND_HOST):$(FRONTEND_PORT)"; \
	wait $$BACK_PID $$FRONT_PID

starter-corpora:
	@set -euo pipefail; \
	cd $(BACKEND_DIR); \
	uv sync --group dev; \
	uv run python -m rlm_lens.starter_corpora_cli list; \
	echo ""; \
	echo "Materializing synthetic-medium pack..."; \
	uv run python -m rlm_lens.starter_corpora_cli materialize --pack synthetic-medium

clean:
	@rm -rf .rlm-lens backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache frontend/node_modules frontend/dist frontend/playwright-report frontend/test-results
