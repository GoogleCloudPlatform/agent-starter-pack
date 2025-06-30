# Development Guide

This guide walks you through the entire lifecycle of creating, developing, deploying, and monitoring your agent project.

::: tip Our Philosophy: "Bring Your Own Agent"
This starter pack provides the scaffolding for UI, infrastructure, deployment, and monitoring. You focus on building your unique agent logic, and we handle the rest.
:::

::: details Create Your Project
You can use the `pip` workflow for a traditional setup, or `uvx` to create a project in a single command without a permanent install.

::: code-group
```bash [pip]
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install the package
pip install agent-starter-pack

# 3. Run the create command
agent-starter-pack create my-awesome-agent
```

```bash [⚡ uvx]
# This single command downloads and runs the latest version
`uvx agent-starter-pack create my-awesome-agent
```
:::

## 1. Local Development & Iteration

Navigate into your new project to begin development.

```bash
cd my-awesome-agent
```

Inside, you'll find a complete project structure:

::: tip Leveraging AI Tools (like Gemini CLI)
The starter pack includes a `GEMINI.md` file with guidance formatted for AI interaction. Tools like the [Gemini CLI](https://github.com/google-gemini/gemini-cli) can leverage this file when used within your project directory, providing context for questions about your template.
:::

*   `app/`: Backend agent code (prompts, tools, business logic).
*   `deployment/`: Terraform infrastructure code.
*   `tests/`: Unit and integration tests.
*   `notebooks/`: Jupyter notebooks for prototyping and evaluation.
*   `frontend/`: (If applicable) Web UI for interacting with your agent.
*   `README.md`: **Project-specific instructions for your chosen template.**
*   `GEMINI.md`: Use this file with AI tools (like [Gemini CLI](https://github.com/google-gemini/gemini-cli)) to ask questions about the template, ADK concepts, or project structure.


Your development loop will look like this:

1.  **Prototype:** Use the notebooks in `notebooks/` for rapid experimentation with your agent's core logic. This is ideal for trying new prompts or tools before integrating them.
2.  **Integrate:** Edit `app/agent.py` and other files in the `app/` directory to incorporate your new logic into the main application.
3.  **Test:** Run the interactive UI playground to test your changes. It features hot-reloading, chat history, and user feedback.

```bash
# Install dependencies and launch the local playground
make install && make playground
```
> Note: The specific UI playground launched by `make playground` depends on the agent template you selected during creation.

## 2. Deploy to the Cloud

Once you're satisfied with local testing, you are ready to deploy your agent to Google Cloud.

*All `make` commands should be run from the root of your agent project (`my-awesome-agent`).*

### A. Cloud Development Environment Setup

First, provision a non-production environment in the cloud for remote testing.

**i. Set Google Cloud Project**
Configure `gcloud` to target your development project.
```bash
# Replace YOUR_DEV_PROJECT_ID with your actual Google Cloud Project ID
gcloud config set project YOUR_DEV_PROJECT_ID
```

**ii. Provision Cloud Resources**
This command uses Terraform to set up necessary cloud resources for your dev environment.
```bash
make setup-dev-env
```

**iii. Deploy Agent Backend**
Build and deploy your agent's backend to the dev environment.
```bash
make backend
```

### B. Production-Ready Deployment with CI/CD

For reliable, automated deployments, a CI/CD pipeline is essential.

**Option 1: One-Command CI/CD Setup (Recommended for GitHub)**
The `agent-starter-pack` CLI can automate the entire CI/CD setup process.
```bash
uvx agent-starter-pack setup-cicd
```
This command creates a GitHub repository, connects it to Cloud Build, provisions staging/production infrastructure, and configures deployment triggers. For details, see the [`setup-cicd` CLI reference](../cli/setup_cicd).

**Option 2: Manual CI/CD Setup**
For full control or for other Git providers, refer to the [manual deployment setup guide](./deployment.md).

**Trigger Your First Deployment**
After CI/CD is configured, commit and push your code to trigger the pipeline.
```bash
git add -A
git config --global user.email "you@example.com" # If not already configured
git config --global user.name "Your Name"     # If not already configured
git commit -m "Initial commit of agent code"
git push --set-upstream origin main
```

## 3. Monitor Your Deployed Agent

Track your agent's performance using integrated observability tools. OpenTelemetry events are automatically sent to Google Cloud services.

*   **Cloud Trace & Logging**: Inspect request flows, analyze latencies, and review prompts/outputs. Access traces at: `https://console.cloud.google.com/traces/list?project=YOUR_PROD_PROJECT_ID`
*   **BigQuery**: Route trace and log data to BigQuery for long-term storage and advanced analytics.
*   **Looker Studio Dashboards**: Visualize agent performance with pre-built templates:
    *   ADK Agents: [Looker Studio ADK Dashboard](https://lookerstudio.google.com/c/reporting/46b35167-b38b-4e44-bd37-701ef4307418/page/tEnnC)
    *   Non-ADK Agents: [Looker Studio Non-ADK Dashboard](https://lookerstudio.google.com/c/reporting/fa742264-4b4b-4c56-81e6-a667dd0f853f/page/tEnnC)
    *(Remember to follow the "Setup Instructions" within the dashboards to connect your data sources).*

➡️ For details, see the [Observability Guide](./observability.md).

## 4. Advanced Customization

Tailor the starter pack further to meet your specific requirements.

*   **RAG Data Ingestion**: For Retrieval Augmented Generation (RAG) agents, configure data pipelines to process your information and load embeddings into Vertex AI Search or Vector Search.
    ➡️ See the [Data Ingestion Guide](./data-ingestion.md).
*   **Custom Terraform**: Modify Terraform configurations in `deployment/terraform/` for unique infrastructure needs.
    ➡️ Refer to the [Deployment Guide](./deployment.md).