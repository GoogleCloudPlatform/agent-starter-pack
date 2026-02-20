# 🚀 Getting Started

This guide quickly walks you through setting up your first agent project.

**Want zero setup?** 👉 [Try in Firebase Studio](https://studio.firebase.google.com/new?template=https%3A%2F%2Fgithub.com%2FGoogleCloudPlatform%2Fagent-starter-pack%2Ftree%2Fmain%2Fsrc%2Fresources%2Fidx) or in [Cloud Shell](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Feliasecchig%2Fasp-open-in-cloud-shell&cloudshell_print=open-in-cs)

### Prerequisites

**Python 3.10+** (or **Go 1.21+** for Go templates, or **Node.js 20+** for TypeScript templates) | **Google Cloud SDK** [Install Guide](https://cloud.google.com/sdk/docs/install) | **Terraform** [Install Guide](https://developer.hashicorp.com/terraform/downloads) | **`uv` (Recommended)** [Install Guide](https://docs.astral.sh/uv/getting-started/installation/)

### 1. Create Your Agent Project

::: code-group

```bash [⚡ uvx (Recommended)]
# Single command - no install needed
uvx agent-starter-pack create
```

```bash [pip]
# Create and activate a virtual environment
# On Windows use: .venv\Scripts\activate
python -m venv .venv && source .venv/bin/activate

# Install and run
pip install agent-starter-pack
agent-starter-pack create
```

:::

No matter which method you choose, the `create` command will:
*   Let you choose an agent template (e.g., `adk`, `adk_go`, `adk_ts`, `agentic_rag`).
*   Let you select a deployment target (e.g., `cloud_run`, `gke`, `agent_engine`).
*   Generate a complete project structure (backend, optional frontend, deployment infra).

**Examples:**

```bash
# Python agent with Agent Engine
agent-starter-pack create my-adk-agent -a adk -d agent_engine

# Go agent with Cloud Run
agent-starter-pack create my-go-agent -a adk_go -d cloud_run

# TypeScript agent with Cloud Run
agent-starter-pack create my-ts-agent -a adk_ts -d cloud_run
```

### 2. Explore and Run Locally

Now, navigate into your new project and run its setup commands.

```bash
cd <your-project> && make install && make playground
```

Inside your new project directory, you'll find:

*   `app/` (Python/TypeScript) or `agent/` (Go): Backend agent code.
*   `deployment/`: Terraform infrastructure code.
*   `tests/` (Python/TypeScript) or `e2e/` (Go): Unit and integration tests.
*   `notebooks/`: (Python only) Jupyter notebooks for evaluation.
*   `frontend/`: (If applicable) Web UI for interacting with your agent.
*   `README.md`: **Project-specific instructions for running locally and deploying.**

➡️ **Follow the instructions in *your new project's* `README.md` to run it locally.**

### Next Steps

See the [Development Guide](/guide/development-guide) for the full workflow, or jump to:
- [Data Ingestion](/guide/data-ingestion) - Add RAG capabilities
- [Deployment Guide](/guide/deployment) - Deploy to Google Cloud
- [Observability](/guide/observability/) - Monitor your agent

---

## Command Cheatsheet

Quick reference for all available commands.

### Project Setup

| Command | What It Does |
|---------|--------------|
| `uvx agent-starter-pack create` | **Scaffold a production-ready AI agent** in seconds (Python/Go/TypeScript/Java) |
| `uvx agent-starter-pack enhance` | **Add CI/CD pipelines** and Terraform infrastructure to existing projects |
| `uvx agent-starter-pack setup-cicd` | **One-command setup** of entire CI/CD pipeline + infrastructure |

### Development Workflow

| Command | What It Does |
|---------|--------------|
| `make install` | Install all dependencies |
| `make playground` | **Launch interactive local playground** with live reload |
| `make lint` | Run code quality checks |
| `make test` | Run unit + integration tests |

### Deployment

| Command | What It Does |
|---------|--------------|
| `make deploy` | **Deploy your agent to Google Cloud** (Agent Engine, Cloud Run, or GKE) in one command |
| `make setup-dev-env` | **Provision infrastructure** using Terraform |
| `make register-gemini-enterprise` | **Integrate with Gemini Enterprise** - make your agent available to your org |

### Maintenance & Sharing

| Command | What It Does |
|---------|--------------|
| `uvx agent-starter-pack upgrade` | **Auto-upgrade to latest version** while preserving your customizations |
| `uvx agent-starter-pack extract` | **Extract a minimal, shareable agent** from your project |
| `uvx agent-starter-pack list` | Browse available templates |

See [Agent Templates Overview](/agents/overview) for all available templates.
