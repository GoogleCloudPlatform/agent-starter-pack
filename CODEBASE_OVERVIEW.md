# Agent Starter Pack - Codebase Overview

## Project Purpose

Production-ready templating system for building GenAI agents on Google Cloud Platform. Bridges the "production gap" (3-9 month period) between prototyping and production deployment.

**Core Value**: Developers focus on agent logic (prompts, LLM interactions, business logic) while the starter pack provides infrastructure, CI/CD, monitoring, evaluation, and security.

## Main Functionality

- **Template Generation**: Create production-ready agent projects from pre-built templates
- **Enhancement**: Add capabilities to existing projects
- **Multi-Framework Support**: Google ADK, LangGraph, custom agents
- **Infrastructure as Code**: Terraform-based deployment on Cloud Run or Agent Engine
- **CI/CD Automation**: GitHub Actions or Google Cloud Build pipelines
- **Data Ingestion**: RAG pipelines for Vertex AI Search/Vector Search

## Directory Structure

### `agent_starter_pack/agents/` - Agent Templates (5 total)
- **adk_base**: Base ReAct agent using Google's Agent Development Kit
- **adk_a2a_base**: ADK agent with Agent2Agent (A2A) Protocol support
- **adk_live**: Real-time multimodal agent with Gemini Live API
- **agentic_rag**: RAG agent for document retrieval
- **langgraph_base**: Base ReAct agent using LangChain's LangGraph

### `agent_starter_pack/base_template/` - Core Template
Applied to ALL generated projects containing:
- `deployment/terraform/`: Infrastructure as code (IAM, APIs, storage, telemetry)
- `Makefile`: Build automation
- `pyproject.toml`: Python project configuration
- Jinja2 templates with `{{cookiecutter.*}}` variables

### `agent_starter_pack/cli/` - Command-Line Interface
- `commands/`: CLI commands (create, enhance, list, setup_cicd, register_gemini_enterprise)
- `utils/`: Helper functions (template processing, GCP auth, datastores, remote templates)
- `main.py`: Entry point (registered in pyproject.toml → `[project.scripts]`)

### `agent_starter_pack/deployment_targets/` - Environment Overrides
**4-layer architecture** with environment-specific files:
- `agent_engine/`: Vertex AI Agent Engine deployment (agent_engine_app.py)
- `cloud_run/`: Cloud Run deployment (fast_api_app.py)
- Each contains app code, tests, Terraform overrides

### `agent_starter_pack/frontends/` - UI Components
- `adk_live_react/`: React frontend for real-time multimodal agents

### `agent_starter_pack/data_ingestion/` - RAG Pipeline
- `data_ingestion_pipeline/`: Vertex AI Pipeline components for embedding generation
- `submit_pipeline.py`: Pipeline submission script

### Other Key Directories
- `.github/workflows/`: GitHub Actions (release automation, docs)
- `.cloudbuild/`: Google Cloud Build configs (CI, CD, Terraform)
- `docs/`: VitePress documentation site
- `tests/`: Unit, integration, E2E tests

## Entry Points & Core Files

### CLI Entry Point
**File**: [agent_starter_pack/cli/main.py](agent_starter_pack/cli/main.py)
**Registration**: `pyproject.toml` → `[project.scripts]` → `agent-starter-pack = "agent_starter_pack.cli.main:cli"`

**Commands**: create, enhance, list, setup_cicd, register_gemini_enterprise

### Template Processing
**File**: [agent_starter_pack/cli/utils/template.py](agent_starter_pack/cli/utils/template.py)
**Key Function**: `process_template()` orchestrates multi-layer templating

### Agent Implementation
Per-template structure:
- **Agent logic**: `agents/{template_name}/app/agent.py`
- **Cloud Run deployment**: `deployment_targets/cloud_run/{{cookiecutter.agent_directory}}/fast_api_app.py`
- **Agent Engine deployment**: `deployment_targets/agent_engine/{{cookiecutter.agent_directory}}/agent_engine_app.py`

### Configuration Files
**Per-agent**: `agents/{template}/.template/templateconfig.yaml`
```yaml
description: "Agent description"
settings:
  requires_data_ingestion: false
  requires_session: true
  deployment_targets: ["agent_engine", "cloud_run"]
  extra_dependencies: ["google-adk>=1.15.0"]
  tags: ["adk"]
```

**Root**: [pyproject.toml](pyproject.toml) - project metadata, dependencies, CLI scripts, linting rules

## Template Processing Flow (4-Layer Architecture)

```
1. Base Template (base_template/)
   ↓ Applied to ALL projects
2. Deployment Target (deployment_targets/{target}/)
   ↓ Environment-specific overrides
3. Frontend Type (frontends/{type}/)
   ↓ UI-specific files (if applicable)
4. Agent Template (agents/{name}/)
   ↓ Agent-specific logic
```

**Rendering Process**:
1. Variable resolution from CLI flags, prompts, template configs
2. File copying with overlays (base → deployment → frontend → agent)
3. Jinja2 rendering (`{{ cookiecutter.variable }}`, `{% if %}` logic)
4. Post-processing (directory renaming, cleanup)

## Key Dependencies

### Core Package
```toml
click>=8.1.7                    # CLI framework
cookiecutter>=2.6.0             # Template engine
google-cloud-aiplatform>=1.120.0  # Vertex AI SDK
rich>=13.7.0                    # Terminal UI
pyyaml>=6.0.1                   # YAML parsing
```

### Agent-Specific
- **ADK**: `google-adk>=1.15.0` (Agent Development Kit)
- **LangGraph**: `langchain~=1.0.7`, `langgraph~=1.0.3`, `a2a-sdk[http-server]~=0.3.12`
- **RAG**: `langchain-google-vertexai~=2.0.7`, `langchain-google-community[vertexaisearch]~=2.0.7`

### Development
- **Linting**: ruff, mypy, codespell, black, flake8, isort
- **Testing**: pytest, pytest-cov, pytest-mock, pytest-xdist
- **Documentation**: sphinx, myst-parser, sphinx-click

### Infrastructure
- **IaC**: Terraform (GCP resource provisioning)
- **CI/CD**: GitHub Actions, Google Cloud Build
- **Build**: `uv` (modern Python package manager), Make

## Google Cloud Services Used

- **Vertex AI**: Gemini models, Agent Engine, Pipelines, Search, Vector Search, Embeddings
- **Cloud Run**: Serverless container deployment
- **Cloud Build**: CI/CD pipelines
- **Artifact Registry**: Container images
- **Secret Manager**: Credentials storage
- **Cloud Storage**: Artifacts, logs
- **Cloud SQL**: Optional session storage (PostgreSQL)
- **Cloud Logging & Trace**: Observability

## AI/LLM Integrations

**IMPORTANT**: This is exclusively a **Google Cloud/Gemini project**. No Anthropic/Claude integrations exist.

### Gemini Models (via Vertex AI)
- **gemini-3-pro-preview** (primary model)
- **gemini-2.0-flash-exp** (adk_live)

### Access Methods
- `google-adk` library (Agent Development Kit)
- `langchain-google-genai`
- `langchain-google-vertexai`
- Direct Vertex AI SDK

### Authentication
```python
# GCP credentials (default)
import google.auth
credentials, project_id = google.auth.default()

# API key (alternative)
os.environ["GOOGLE_API_KEY"] = "..."
```

## Key Features

1. **Multi-Framework Support**: Google ADK, LangGraph, Agent2Agent (A2A) Protocol
2. **Dual Deployment**: Cloud Run (serverless containers) or Agent Engine (managed hosting)
3. **Data Ingestion**: Vertex AI Pipelines for RAG (3 datastores: Vertex AI Search, Vector Search, Cloud SQL/pgvector)
4. **CI/CD Automation**: `setup_cicd` command creates GitHub repo, Cloud Build/GitHub Actions
5. **Session Management**: in_memory, cloud_sql, agent_engine
6. **Observability**: Cloud Logging, OpenTelemetry, Cloud Trace
7. **Remote Templates**: `local@/path`, `adk@gemini-fullstack`, `github.com/org/repo@branch`
8. **Frontend Support**: React for `adk_live` multimodal chat

## Build & Deployment

### Package Management (uv)
```bash
uv sync --dev --frozen           # Install dependencies
uv run agent-starter-pack create  # Run CLI
uvx agent-starter-pack create     # Execute without install
```

### Makefile Targets
```bash
make install    # Install dependencies
make test       # Run pytest
make lint       # Run ruff, mypy, codespell
make docs-dev   # Start VitePress docs server
```

### Deployment Workflow
1. **Create Project**: `uvx agent-starter-pack create my-agent -a adk_base -d cloud_run`
2. **Setup Infrastructure**: `cd my-agent/deployment && make setup-dev-env` (Terraform)
3. **Setup CI/CD**: `uvx agent-starter-pack setup_cicd` (creates GitHub repo, triggers)
4. **Deploy**: CI/CD triggers on PR (test), main merge (staging), tag push (production)

### Terraform Structure
- **Base**: `deployment/terraform/` (APIs, IAM, storage)
- **Dev**: `deployment/terraform/dev/` (development environment)
- **Modules**: Deployment target-specific (Cloud Run, Agent Engine)

## Important Implementation Details

### 1. Jinja2 Whitespace Control (Critical for linting)
```jinja
{%- if condition -%}  # Strip both sides
{% if condition %}    # Preserve whitespace
{%- endif %}         # Strip before tag
```
Documented in [GEMINI.md](GEMINI.md) - most common source of linting failures

### 2. Cookiecutter Variable Naming
- Uses underscores: `cookiecutter.agent_directory`
- Project names normalized: uppercase → lowercase, `_` → `-`
- Max 26 characters (GCP resource name limits)

### 3. Multi-Agent Testing
```bash
_TEST_AGENT_COMBINATION="adk_base,cloud_run,--session-type,in_memory" \
  make lint-templated-agents
```

### 4. Unified Service Account
Single `app_sa` per environment (not per deployment target) in `deployment/terraform/iam.tf`

### 5. Version Locking
`.asp-version` file + `--locked` flag ensures reproducible template rendering

### 6. Template Inheritance
Remote templates specify `base_template` in pyproject.toml, inherit base files, override specific ones

### 7. Prototype Mode
`--prototype` flag skips CI/CD and Terraform for quick testing

### 8. Agent2Agent (A2A) Protocol
Enables distributed agent communication via HTTP with agent card generation

### 9. Conditional Compilation
```jinja
{% if cookiecutter.agent_name == "adk_live" %}
# ADK Live-specific code
{% elif cookiecutter.is_a2a %}
# A2A-specific code
{% else %}
# Default code
{% endif %}
```

## Testing Strategy

- **Unit tests**: `tests/unit/`
- **Integration tests**: `tests/integration/`
- **E2E tests**: `tests/e2e/`
- **Multi-combination testing**: Tests all agent × deployment × session combinations
- **Linting**: Ruff, mypy, codespell must pass on generated projects

## Release Process

1. Manual trigger: GitHub Actions `workflow_dispatch` with version bump (patch/minor)
2. Auto-creates release PR with version bump
3. Auto-approves and enables auto-merge
4. On merge: Manual approval required for PyPI publish
5. Publishes to PyPI, creates GitHub release

## Configuration Hierarchy

1. **Agent Template Config**: `agents/{name}/.template/templateconfig.yaml`
2. **Cookiecutter Variables**: Dynamically generated from CLI flags + prompts + configs
3. **Generated Project**: `generated_project/pyproject.toml` → `[tool.agent-starter-pack]`
4. **Terraform Variables**: `deployment/terraform/dev/vars/env.tfvars`

## Key Files Reference

- [pyproject.toml](pyproject.toml) - Package metadata, dependencies, CLI scripts
- [Makefile](Makefile) - Development commands
- [GEMINI.md](GEMINI.md) - AI coding agent guide (whitespace, templating, testing)
- [llm.txt](llm.txt) - LLM-optimized project documentation
- [agent_starter_pack/cli/main.py](agent_starter_pack/cli/main.py) - CLI entry point
- [agent_starter_pack/cli/utils/template.py](agent_starter_pack/cli/utils/template.py) - Template processing engine

## Session Types

- **in_memory**: No persistence, fastest, resets on restart
- **cloud_sql**: PostgreSQL-backed, persistent across restarts
- **agent_engine**: Managed by Vertex AI Agent Engine

## Deployment Targets

### Cloud Run (fast_api_app.py)
- Serverless containers with FastAPI
- HTTP endpoints, CORS support
- Flexible session management (in_memory, cloud_sql, agent_engine)
- Manual scaling configuration

### Agent Engine (agent_engine_app.py)
- Native Vertex AI deployment
- Uses `AdkApp`, `A2aAgent`, or `PreviewAdkApp`
- Managed sessions and artifact storage (GCS or in-memory)
- Automatic scaling and monitoring
