
# 🚀 Getting Started

This guide quickly walks you through setting up your first agent project.

**Want zero setup?** 👉 [Try in Firebase Studio](https://studio.firebase.google.com/new?template=https%3A%2F%2Fgithub.com%2FGoogleCloudPlatform%2Fagent-starter-pack%2Ftree%2Fmain%2Fsrc%2Fresources%2Fidx) or in [Cloud Shell](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Feliasecchig%2Fasp-open-in-cloud-shell&cloudshell_print=open-in-cs)

### Prerequisites

**Python 3.10+** | **Google Cloud SDK** [Install Guide](https://cloud.google.com/sdk/docs/install) | **Terraform** [Install Guide](https://developer.hashicorp.com/terraform/downloads) | **`uv` (automatically installed)** [Manual Install Guide](https://docs.astral.sh/uv/getting-started/installation/)

### 1. Install the Starter Pack

```bash
# Create and activate a Python virtual environment (Recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install agent-starter-pack
```
Check the [Installation Guide](/guide/installation) for alternative installation methods.

### 2. Create Your Agent Project

Run the `create` command and follow the prompts:

```bash
agent-starter-pack create my-awesome-agent
```

This command:
*   Lets you choose an agent template (e.g., `adk_base`, `agentic_rag`).
*   Lets you select a deployment target (e.g., `cloud_run`, `agent_engine`).
*   Generates a complete project structure (backend, optional frontend, deployment infra).

**Examples:**

```bash
# Create a RAG agent for Cloud Run (select options when prompted)
agent-starter-pack create my-rag-agent

# Create a base ADK agent for Agent Engine directly
agent-starter-pack create my-adk-agent -a adk_base -d agent_engine
```

### 3. Explore and Run Locally

```bash
cd my-awesome-agent && make install && make playground
```

Inside your new project directory (`my-awesome-agent`), you'll find:

*   `app/`: Backend agent code.
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
