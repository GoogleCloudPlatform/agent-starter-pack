
# 🚀 Getting Started

This guide quickly walks you through setting up your first agent project.

**Want zero setup?** 👉 [Try in Firebase Studio](https://studio.firebase.google.com/new?template=https%3A%2F%2Fgithub.com%2FGoogleCloudPlatform%2Fagent-starter-pack%2Ftree%2Fmain%2Fsrc%2Fresources%2Fidx)

### Prerequisites

Ensure you have:

1.  **Python 3.10+**
2.  **Google Cloud SDK:** [Install Guide](https://cloud.google.com/sdk/docs/install).
3.  **Terraform:** [Install Guide](https://developer.hashicorp.com/terraform/downloads).

### 1. Install the Starter Pack

```bash
# Create and activate a Python virtual environment (Recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install agent-starter-pack
```

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

You're ready to go!

*   **Customize:** Modify the code in `app/` to edit prompts, configure tools, adjust API endpoints, customize business logic, extend functionality!
*   **Deploy in minutes:** Use the [setup-cicd](/cli/setup_cicd) command.
*   **Customized the deployment:** Use Terraform in `deployment/` to deploy to Google Cloud or follow the deployment guide ([Deployment Guide](/guide/deployment)). 
*   **Add Data (RAG):** Configure [Data Ingestion](/guide/data-ingestion).
*   **Monitor:** Explore [Observability](/guide/observability) features.
