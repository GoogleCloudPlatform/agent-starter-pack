{%- if extracted|default(false) %}
# ==============================================================================
# Minimal Makefile for Extracted Agent
# ==============================================================================
# This agent was extracted from a full agent-starter-pack project.
# Run `agent-starter-pack enhance` to add deployment capabilities.
# ==============================================================================

install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; source $$HOME/.local/bin/env; }
	uv sync

playground:
	@echo "==============================================================================="
	@echo "| Starting your agent playground...                                          |"
	@echo "|                                                                             |"
	@echo "| Select the '{{cookiecutter.agent_directory}}' folder to interact with your agent.         |"
	@echo "==============================================================================="
{%- if cookiecutter.is_adk %}
	uv run adk web . --port 8501 --reload_agents
{%- else %}
	@echo "Note: For full playground, run 'agent-starter-pack enhance' first."
	uv run python -c "from {{cookiecutter.agent_directory}}.agent import agent; print(agent)"
{%- endif %}

{%- else %}
# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $HOME/.local/bin/env; }
{%- if cookiecutter.settings.get("commands", {}).get("override", {}).get("install") %}
	{{cookiecutter.settings.get("commands", {}).get("override", {}).get("install")}}
{%- else %}
	uv sync{% if cookiecutter.is_adk_live %} && (cd frontend && npm install){%- endif %}
{%- endif %}

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground
playground:{%- if cookiecutter.is_adk_live %} build-frontend-if-needed{%- endif %}
{%- if cookiecutter.settings.get("commands", {}).get("override", {}).get("playground") %}
{%- if cookiecutter.settings.get("commands", {}).get("override", {}).get("playground") is mapping %}
	{{cookiecutter.settings.get("commands", {}).get("override", {}).get("playground").get(cookiecutter.deployment_target, "")}}
{%- else %}
	{{cookiecutter.settings.get("commands", {}).get("override", {}).get("playground")}}
{%- endif %}
{%- else %}
	@echo "==============================================================================="
	@echo "| 🚀 Starting your agent playground...                                        |"
	@echo "|                                                                             |"
{%- if cookiecutter.is_adk_live %}
	@echo "| 🌐 Access your app at: http://localhost:8000                               |"
{%- endif %}
	@echo "| 💡 Try asking: {{cookiecutter.example_question}}|"
{%- if cookiecutter.is_adk %}
	@echo "|                                                                             |"
	@echo "| 🔍 IMPORTANT: Select the '{{cookiecutter.agent_directory}}' folder to interact with your agent.          |"
{%- endif %}
	@echo "==============================================================================="
{%- if cookiecutter.is_adk_live %}
{%- if cookiecutter.deployment_target == 'agent_engine' %}
	uv run python -m {{cookiecutter.agent_directory}}.app_utils.expose_app --mode local --local-agent {{cookiecutter.agent_directory}}.agent.root_agent
{%- else %}
	uv run uvicorn {{cookiecutter.agent_directory}}.fast_api_app:app --host localhost --port 8000 --reload
{%- endif %}
{%- elif cookiecutter.is_adk %}
	uv run adk web . --port 8501 --reload_agents
{%- elif cookiecutter.is_a2a %}
{%- if cookiecutter.deployment_target == 'cloud_run' %}
	uv run uvicorn {{cookiecutter.agent_directory}}.fast_api_app:app --host localhost --port 8000 --reload &
	$(MAKE) inspector
{%- else %}
{%- if cookiecutter.agent_name == 'langgraph' %}
	@echo "ℹ️  Note: Local playground not supported for LangGraph on Agent Engine."
	@echo "    To test your agent, deploy first with 'make deploy' then use 'make inspector'."
{%- else %}
	@echo "ℹ️  Note: Local playground uses ADK web interface (not A2A endpoints)."
	@echo "    To test A2A protocol, deploy first with 'make deploy' then use 'make inspector'."
	@echo ""
	uv run adk web . --port 8501 --reload_agents
{%- endif %}
{%- endif %}
{%- else %}
	uv run uvicorn {{cookiecutter.agent_directory}}.fast_api_app:app --host localhost --port 8000 --reload
{%- endif %}
{%- endif %}
{%- endif %}
{%- if not extracted|default(false) %}
{%- if cookiecutter.settings.get("commands", {}).get("extra", {}) %}

# ==============================================================================
# Agent-Specific Commands
# ==============================================================================
{%- for cmd_name, cmd_value in cookiecutter.settings.get("commands", {}).get("extra", {}).items() %}
{%- if cmd_value is mapping %}
{%- if cmd_value.command is mapping %}
{%- if cookiecutter.deployment_target in cmd_value.command %}

# {{ cmd_value.get("description") }}
{{ cmd_name }}:
	{{ cmd_value.command[cookiecutter.deployment_target] }}
{%- endif %}
{%- else %}

# {{ cmd_value.get("description") }}
{{ cmd_name }}:
	{{ cmd_value.command if cmd_value.command is string else "" }}
{%- endif %}
{%- else %}

# {{ cmd_value.get("description", "") }}
{{ cmd_name }}:
	{{ cmd_value }}
{%- endif %}
{%- endfor %}
{%- endif %}
{%- if cookiecutter.deployment_target == 'cloud_run' or (cookiecutter.deployment_target == 'agent_engine' and cookiecutter.is_adk_live) %}

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server with hot-reload
local-backend:
{%- if cookiecutter.deployment_target == 'cloud_run' %}
	uv run uvicorn {{cookiecutter.agent_directory}}.fast_api_app:app --host localhost --port 8000 --reload
{%- else %}
	uv run python -m {{cookiecutter.agent_directory}}.app_utils.expose_app --mode local --port 8000  --local-agent {{cookiecutter.agent_directory}}.agent.root_agent
{%- endif %}
{%- endif %}
{%- if cookiecutter.is_adk_live %}

# ==============================================================================
# ADK Live Commands
# ==============================================================================

# Build the frontend for production
build-frontend:
	(cd frontend && npm run build)

# Build the frontend only if needed (conditional build)
build-frontend-if-needed:
	@if [ ! -d "frontend/build" ] || [ ! -f "frontend/build/index.html" ]; then \
		echo "Frontend build directory not found or incomplete. Building..."; \
		$(MAKE) build-frontend; \
	elif [ "frontend/package.json" -nt "frontend/build/index.html" ] || \
		 find frontend/src -newer frontend/build/index.html 2>/dev/null | head -1 | grep -q .; then \
		echo "Frontend source files are newer than build. Rebuilding..."; \
		$(MAKE) build-frontend; \
	else \
		echo "Frontend build is up to date. Skipping build..."; \
	fi
{%- if cookiecutter.deployment_target == 'agent_engine' %}

# Connect to remote deployed agent
playground-remote: build-frontend-if-needed
	@echo "==============================================================================="
	@echo "| 🚀 Connecting to REMOTE agent...                                           |"
	@echo "|                                                                             |"
	@echo "| 🌐 Access your app at: http://localhost:8000                               |"
	@echo "| ☁️  Connected to deployed agent engine                                      |"
	@echo "==============================================================================="
	uv run python -m {{cookiecutter.agent_directory}}.app_utils.expose_app --mode remote
{%- endif %}
{%- endif %}
{%- if cookiecutter.is_adk_live and cookiecutter.deployment_target == 'agent_engine' %}

# Start the frontend UI separately for development (requires backend running separately)
ui:
	(cd frontend && PORT=8501 npm start)

# Launch dev playground with both frontend and backend hot-reload
playground-dev:
	@echo "==============================================================================="
	@echo "| 🚀 Starting your agent playground in DEV MODE...                           |"
	@echo "|                                                                             |"
	@echo "| 🌐 Frontend: http://localhost:8501                                         |"
	@echo "| 🌐 Backend:  http://localhost:8000                                         |"
	@echo "| 💡 Try asking: {{cookiecutter.example_question}}|"
	@echo "| 🔄 Both frontend and backend will auto-reload on changes                    |"
	@echo "==============================================================================="
	@echo "Starting backend server..."
	$(MAKE) local-backend &
	@echo "Starting frontend dev server..."
	$(MAKE) ui
{%- endif %}
{%- if cookiecutter.is_a2a %}

# ==============================================================================
# A2A Protocol Inspector
# ==============================================================================

# Launch A2A Protocol Inspector to test your agent implementation
inspector: setup-inspector-if-needed build-inspector-if-needed
	@echo "==============================================================================="
	@echo "| 🔍 A2A Protocol Inspector                                                  |"
	@echo "==============================================================================="
	@echo "| 🌐 Inspector UI: http://localhost:5001                                     |"
	@echo "|                                                                             |"
{%- if cookiecutter.deployment_target == 'cloud_run' %}
	@echo "| 💡 Testing Locally:                                                         |"
	@echo "|    Paste this URL into the inspector:                                      |"
	@echo "|    http://localhost:8000/a2a/{{cookiecutter.agent_directory}}/.well-known/agent-card.json              |"
	@echo "|                                                                             |"
{%- endif %}
	@echo "| 💡 Testing Remote Deployment:                                               |"
{%- if cookiecutter.deployment_target == 'cloud_run' %}
	@echo "|    <SERVICE_URL>/a2a/{{cookiecutter.agent_directory}}/.well-known/agent-card.json"
	@echo "|    (Get SERVICE_URL from 'make deploy' output or Cloud Console)            |"
	@echo "|                                                                             |"
	@echo "|    🔐 Auth: Expand 'Authentication & Headers', select 'Bearer Token',       |"
	@echo "|       and paste output of: gcloud auth print-identity-token                |"
{%- else %}
	@echo "|    Use the Agent Card URL from 'make deploy' output                        |"
	@echo "|                                                                             |"
	@echo "|    🔐 Auth: Expand 'Authentication & Headers', select 'Bearer Token',       |"
	@echo "|       and paste output of: gcloud auth print-access-token                  |"
	@echo "|                                                                             |"
	@echo "| ℹ️  Note: Local testing requires deploying to Agent Engine first.          |"
{%- endif %}
	@echo "==============================================================================="
	@echo ""
	cd tools/a2a-inspector/backend && uv run app.py

# Internal: Setup inspector if not already present (runs once)
# TODO: Update to --branch v1.0.0 when a2a-inspector publishes releases
setup-inspector-if-needed:
	@if [ ! -d "tools/a2a-inspector" ]; then \
		echo "" && \
		echo "📦 First-time setup: Installing A2A Inspector..." && \
		echo "" && \
		mkdir -p tools && \
		git clone --quiet https://github.com/a2aproject/a2a-inspector.git tools/a2a-inspector && \
		(cd tools/a2a-inspector && git -c advice.detachedHead=false checkout --quiet 893e4062f6fbd85a8369228ce862ebbf4a025694) && \
		echo "📥 Installing Python dependencies..." && \
		(cd tools/a2a-inspector && uv sync --quiet) && \
		echo "📥 Installing Node.js dependencies..." && \
		(cd tools/a2a-inspector/frontend && npm install --silent) && \
		echo "🔨 Building frontend..." && \
		(cd tools/a2a-inspector/frontend && npm run build --silent) && \
		echo "" && \
		echo "✅ A2A Inspector setup complete!" && \
		echo ""; \
	fi

# Internal: Build inspector frontend if needed
build-inspector-if-needed:
	@if [ -d "tools/a2a-inspector" ] && [ ! -f "tools/a2a-inspector/frontend/public/script.js" ]; then \
		echo "🔨 Building inspector frontend..."; \
		cd tools/a2a-inspector/frontend && npm run build; \
	fi
{%- endif %}

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# Deploy the agent remotely
{%- if cookiecutter.deployment_target == 'cloud_run' %}
# Usage: make deploy [IAP=true] [PORT=8080] - Set IAP=true to enable Identity-Aware Proxy, PORT to specify container port
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
# Usage: make deploy [AGENT_IDENTITY=true] - Set AGENT_IDENTITY=true to enable per-agent IAM identity (Preview)
{%- endif %}
deploy:
{%- if cookiecutter.deployment_target == 'cloud_run' %}
	PROJECT_ID=$$(gcloud config get-value project) && \
{%- if cookiecutter.is_a2a %}
	PROJECT_NUMBER=$$(gcloud projects describe $$PROJECT_ID --format="value(projectNumber)") && \
{%- endif %}
	gcloud beta run deploy {{cookiecutter.project_name}} \
		--source . \
		--memory "4Gi" \
		--project $$PROJECT_ID \
		--region "us-central1" \
		--no-allow-unauthenticated \
		--no-cpu-throttling \
		--labels "{% if cookiecutter.is_adk %}created-by=adk{% if cookiecutter.agent_garden %},{% endif %}{% endif %}{% if cookiecutter.agent_garden %}deployed-with=agent-garden{% if cookiecutter.agent_sample_id %},vertex-agent-sample-id={{cookiecutter.agent_sample_id}},vertex-agent-sample-publisher={{cookiecutter.agent_sample_publisher}}{% endif %}{% endif %}" \
		--update-build-env-vars "AGENT_VERSION=$(shell awk -F'"' '/^version = / {print $$2}' pyproject.toml || echo '0.0.0')" \
		--update-env-vars \
		"{%- if cookiecutter.is_a2a %}APP_URL=https://{{cookiecutter.project_name}}-$$PROJECT_NUMBER.us-central1.run.app{%- endif %}{%- if cookiecutter.data_ingestion %}{% if cookiecutter.is_a2a %},{% endif %}{%- if cookiecutter.datastore_type == "vertex_ai_search" %}DATA_STORE_ID={{cookiecutter.project_name}}-datastore,DATA_STORE_REGION=us{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}VECTOR_SEARCH_INDEX={{cookiecutter.project_name}}-vector-search,VECTOR_SEARCH_INDEX_ENDPOINT={{cookiecutter.project_name}}-vector-search-endpoint,VECTOR_SEARCH_BUCKET=$$PROJECT_ID-{{cookiecutter.project_name}}-vs{%- endif %}{%- endif %}" \
		$(if $(IAP),--iap) \
		$(if $(PORT),--port=$(PORT))
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
	# Export dependencies to requirements file using uv export.
	(uv export --no-hashes --no-header --no-dev --no-emit-project --no-annotate > {{cookiecutter.agent_directory}}/app_utils/.requirements.txt 2>/dev/null || \
	uv export --no-hashes --no-header --no-dev --no-emit-project > {{cookiecutter.agent_directory}}/app_utils/.requirements.txt) && \
	uv run -m {{cookiecutter.agent_directory}}.app_utils.deploy \
		--source-packages=./{{cookiecutter.agent_directory}} \
		--entrypoint-module={{cookiecutter.agent_directory}}.agent_engine_app \
		--entrypoint-object=agent_engine \
		--requirements-file={{cookiecutter.agent_directory}}/app_utils/.requirements.txt \
		$(if $(AGENT_IDENTITY),--agent-identity)
{%- endif %}

# Alias for 'make deploy' for backward compatibility
backend: deploy

{%- if cookiecutter.cicd_runner != 'skip' %}

# ==============================================================================
# Infrastructure Setup
# ==============================================================================

# Set up development environment resources using Terraform
setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)
{%- endif %}
{%- if cookiecutter.data_ingestion %}

# ==============================================================================
# Data Ingestion (RAG capabilities)
# ==============================================================================

# Run the data ingestion pipeline for RAG capabilities
data-ingestion:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd data_ingestion && uv run data_ingestion_pipeline/submit_pipeline.py \
		--project-id=$$PROJECT_ID \
		--region="us-central1" \
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
		--data-store-id="{{cookiecutter.project_name}}-datastore" \
		--data-store-region="us" \
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
		--vector-search-index="{{cookiecutter.project_name}}-vector-search" \
		--vector-search-index-endpoint="{{cookiecutter.project_name}}-vector-search-endpoint" \
		--vector-search-data-bucket-name="$$PROJECT_ID-{{cookiecutter.project_name}}-vs" \
{%- endif %}
		--service-account="{{cookiecutter.project_name}}-rag@$$PROJECT_ID.iam.gserviceaccount.com" \
		--pipeline-root="gs://$$PROJECT_ID-{{cookiecutter.project_name}}-rag" \
		--pipeline-name="data-ingestion-pipeline")
{%- endif %}
{%- endif %}

# ==============================================================================
# Testing & Code Quality
# ==============================================================================
{%- if not extracted|default(false) %}

# Run unit and integration tests
test:
	uv sync --dev
	uv run pytest tests/unit && uv run pytest tests/integration
{%- endif %}

# Run code quality checks (codespell, ruff, ty)
lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run ty check .
{%- if not extracted|default(false) %}
{%- if (cookiecutter.is_a2a and cookiecutter.deployment_target == 'cloud_run') or (cookiecutter.is_adk and not cookiecutter.is_a2a and cookiecutter.deployment_target == 'agent_engine') %}

# ==============================================================================
# Gemini Enterprise Integration
# ==============================================================================

# Register the deployed agent to Gemini Enterprise
# Usage: make register-gemini-enterprise (interactive - will prompt for required details)
# For non-interactive use, set env vars: ID or GEMINI_ENTERPRISE_APP_ID (full GE resource name)
# Optional env vars: GEMINI_DISPLAY_NAME, GEMINI_DESCRIPTION{%- if cookiecutter.deployment_target == 'agent_engine' %}, GEMINI_TOOL_DESCRIPTION, AGENT_ENGINE_ID{%- endif %}{%- if cookiecutter.deployment_target == 'cloud_run' %}, AGENT_CARD_URL{%- endif %}
register-gemini-enterprise:
{%- if cookiecutter.deployment_target == 'cloud_run' and cookiecutter.is_a2a %}
	@PROJECT_ID=$$(gcloud config get-value project 2>/dev/null) && \
	PROJECT_NUMBER=$$(gcloud projects describe $$PROJECT_ID --format="value(projectNumber)" 2>/dev/null) && \
	uvx agent-starter-pack@{{ cookiecutter.package_version }} register-gemini-enterprise \
		--agent-card-url="https://{{cookiecutter.project_name}}-$$PROJECT_NUMBER.us-central1.run.app/a2a/{{cookiecutter.agent_directory}}/.well-known/agent-card.json" \
		--deployment-target="{{cookiecutter.deployment_target}}" \
		--project-number="$$PROJECT_NUMBER"
{%- else %}
	@uvx agent-starter-pack@{{ cookiecutter.package_version }} register-gemini-enterprise
{%- endif %}
{%- endif %}
{%- endif %}
