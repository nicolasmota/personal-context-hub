# Personal Context Hub
# Usage: make [target]
# Override: make serve PORT=9000 DATA_DIR=/tmp/pch
# Python 3.12+ workspace via uv.

UV       ?= uv
PORT     ?= 8765
HOST     ?= 127.0.0.1
DATA_DIR ?= $(HOME)/.pch

.DEFAULT_GOAL := help

.PHONY: help install sync lint format test test-forbidden test-perf \
        test-all test-dist serve openapi demo-agent bridge clean dist release \
        check-secrets

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nTargets:\n"} \
		/^[a-zA-Z0-9_.-]+:.*##/ { printf "  %-18s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf "\nVariables: UV PORT HOST DATA_DIR\n\n"

install: sync ## Install the Python 3.12+ workspace

sync: ## Install Python 3.12+ workspace with uv
	$(UV) sync --all-packages

check-secrets: ## Fail if git-tracked paths match the secrets deny-list
	$(UV) run python scripts/check_secrets.py

lint: ## Lint Python with Ruff
	$(UV) run ruff check packages

format: ## Format Python with Ruff
	$(UV) run ruff format packages

test: ## Run the default pytest suite
	$(UV) run pytest -m "not release"

test-dist: ## Packaged wheel install from dist/ (network, slow)
	$(UV) run pytest -m release

test-forbidden: ## Run forbidden-context isolation tests (SC-003)
	$(UV) run pytest -m forbidden_context

test-perf: ## Run search/scale performance tests (SC-009)
	$(UV) run pytest -m perf

test-all: test test-forbidden ## Default suite plus forbidden-context

serve: ## Loopback API with auto-reload
	$(UV) run pch-server --headless --reload --host $(HOST) --port $(PORT) --data-dir $(DATA_DIR)

openapi: ## Dump OpenAPI 3.1 JSON to docs/openapi.json
	$(UV) run python -c "from pathlib import Path; from pch_core.service import Hub; from pch_server.rest.app import create_app; import json, tempfile; \
hub = Hub(Path(tempfile.mkdtemp()), plain=True); \
Path('docs').mkdir(exist_ok=True); \
Path('docs/openapi.json').write_text(json.dumps(create_app(hub).openapi(), indent=2))"

demo-agent: ## Pair the reference agent (CODE= from Hub pairing link)
	@test -n "$(CODE)" || (echo "usage: make demo-agent CODE=<pairing-code>"; exit 1)
	$(UV) run pch-sdk demo-agent --pair $(CODE) --base http://$(HOST):$(PORT)

bridge: ## Run the MCP stdio bridge (TOKEN= from a connection recipe)
	@test -n "$(TOKEN)" || (echo "usage: make bridge TOKEN=<connection-token>"; exit 1)
	PCH_TOKEN=$(TOKEN) PCH_BASE=http://$(HOST):$(PORT) $(UV) run pch-sdk mcp-bridge

dist: ## Build wheels and run the release gate (no publish)
	$(UV) run python scripts/build_release.py
	$(UV) run python scripts/check_release.py

release: dist ## Build wheels, gate them, and publish
	$(UV) publish

clean: ## Remove caches, build artifacts, and the local venv
	rm -rf .venv .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
