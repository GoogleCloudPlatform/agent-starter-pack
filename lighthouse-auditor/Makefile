.PHONY: install test playground backend ui setup-dev-env lint check-deps install-node-deps

check-deps:
	@echo "Checking dependencies..."
	@command -v node >/dev/null 2>&1 || { echo "Node.js is not installed. Please install Node.js first: https://nodejs.org/"; exit 1; }
	@command -v npm >/dev/null 2>&1 || { echo "npm is not installed. Please install npm first: https://docs.npmjs.com/downloading-and-installing-node-js-and-npm"; exit 1; }
	@command -v chromium >/dev/null 2>&1 || { echo "Chromium is not installed. Please install Chromium first using your system package manager"; exit 1; }

install-node-deps:
	@echo "Installing Node.js dependencies..."
	npm install
	npm install -g lighthouse chrome-launcher

install: check-deps
	@echo "Installing Python dependencies..."
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source ~/.bashrc; }
	uv sync --dev --extra streamlit --extra jupyter --frozen
	@echo "Installing Node.js dependencies..."
	$(MAKE) install-node-deps
	@echo "Installation complete!"

test:
	uv run pytest tests/unit && uv run pytest tests/integration

playground:
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload &
	uv run streamlit run frontend/streamlit_app.py --browser.serverAddress=localhost --server.enableCORS=false --server.enableXsrfProtection=false

backend:
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload

ui:
	uv run streamlit run streamlit/streamlit_app.py --browser.serverAddress=localhost --server.enableCORS=false --server.enableXsrfProtection=false

setup-dev-env:
	@if [ -z "$$PROJECT_ID" ]; then echo "Error: PROJECT_ID environment variable is not set"; exit 1; fi
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)

lint:
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run mypy .
