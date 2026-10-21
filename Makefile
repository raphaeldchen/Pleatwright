# Build + test entry points. CI runs `make PYTHON=python test`.
PYTHON ?= .venv/bin/python
HARNESS := mcp_harness

.PHONY: test test-app app app-dev clean

test: ## Run the full suite (minutes): pipeline, then the app server.
	cd $(HARNESS) && PYTHONPATH=.:tests $(PYTHON) -m pytest tests/ -q
	$(MAKE) test-app

test-app: ## App server tests only.
	cd $(HARNESS) && PYTHONPATH=.:tests:../app/server $(PYTHON) -m pytest ../app/server/tests -q -p no:cacheprovider

app: ## Build the UI and serve the app at http://127.0.0.1:8000
	cd app/web && npm ci && npm run build
	cd $(HARNESS) && PYTHONPATH=.:../app/server $(PYTHON) -m pleatwright_app

app-dev: ## API on :8000 + Vite with hot reload on :5173
	trap 'kill 0' INT TERM; \
	(cd $(HARNESS) && PYTHONPATH=.:../app/server $(PYTHON) -m pleatwright_app --no-ui) & \
	(cd app/web && npm run dev) & wait

clean:
	rm -rf $(HARNESS)/__pycache__ $(HARNESS)/tests/__pycache__ $(HARNESS)/.pytest_cache app/web/dist
