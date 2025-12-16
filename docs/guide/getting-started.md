# 🚀 Getting Started

This guide quickly walks you through setting up your first agent project.

**Want zero setup?** 👉 [Try in Firebase Studio](https://studio.firebase.google.com/new?template=https%3A%2F%2Fgithub.com%2FGoogleCloudPlatform%2Fagent-starter-pack%2Ftree%2Fmain%2Fsrc%2Fresources%2Fidx) or in [Cloud Shell](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Feliasecchig%2Fasp-open-in-cloud-shell&cloudshell_print=open-in-cs)

### Prerequisites

**Python 3.10+** | **Google Cloud SDK** [Install Guide](https://cloud.google.com/sdk/docs/install) | **Terraform** [Install Guide](https://developer.hashicorp.com/terraform/downloads) | **`uv` (Optional, Recommended)** [Install Guide](https://docs.astral.sh/uv/getting-started/installation/)

### 1. Create Your Agent Project

You can use the `pip` workflow for a traditional setup, or `uvx` to create a project in a single command without a permanent install. Choose your preferred method below.

::: code-group

```bash [pip]
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install the package
pip install agent-starter-pack

# 3. Run the create command
agent-starter-pack create
```

```bash [⚡ uvx]
# This single command downloads and runs the latest version
uvx agent-starter-pack create
```

:::

No matter which method you choose, the `create` command will:
*   Let you choose an agent template (e.g., `adk_base`, `agentic_rag`).
*   Let you select a deployment target (e.g., `cloud_run`, `agent_engine`).
*   Generate a complete project structure (backend, optional frontend, deployment infra).

**Examples:**

```bash
# You can also pass flags to skip the prompts
agent-starter-pack create my-adk-agent -a adk_base -d agent_engine
```

### 2. Explore and Run Locally

Now, navigate into your new project and run its setup commands.

```bash
cd <your-project> && make install && make playground
```

Inside your new project directory, you'll find:

*   `app/`: Backend agent code (or custom directory name if configured).
*   `deployment/`: Terraform infrastructure code.
*   `tests/`: Unit and integration tests for your agent.
*   `notebooks/`: Jupyter notebooks for getting started with evaluation.
*   `frontend/`: (If applicable) Web UI for interacting with your agent.
*   `README.md`: **Project-specific instructions for running locally and deploying.**

➡️ **Follow the instructions in *your new project's* `README.md` to run it locally.**

### Next Steps

You're ready to go! See the [Development Guide](/guide/development-guide) for detailed instructions on extending, customizing and deploying your agent.

- **Add Data (RAG):** Configure [Data Ingestion](/guide/data-ingestion) for knowledge-based agents.
- **Monitor Performance:** Explore [Observability](/guide/observability) features for production monitoring.
- **Deploy to Production:** Follow the [Deployment Guide](/guide/deployment) to deploy your agent to Google Cloud.
- **Explore the Code:** Use [CodeWiki](https://codewiki.google/github.com/googlecloudplatform/agent-starter-pack) for AI-powered code navigation and understanding.