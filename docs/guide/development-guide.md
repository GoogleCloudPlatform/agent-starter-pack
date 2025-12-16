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
agent-starter-pack create
```

```bash [⚡ uvx]
# This single command downloads and runs the latest version
uvx agent-starter-pack create
```
:::

## 1. Local Development & Iteration

Navigate into your new project to begin development.

```bash
cd <your-project>
```

Inside, you'll find a complete project structure:

*   `app/`: Backend agent code (prompts, tools, business logic). Directory name is configurable via the `--agent-directory` parameter.
*   `.cloudbuild/`: CI/CD pipeline configurations for Google Cloud Build (if you selected Cloud Build as your CI/CD runner).
*   `.github/`: CI/CD pipeline configurations for GitHub Actions (if you selected GitHub Actions as your CI/CD runner).
*   `deployment/`: Terraform infrastructure-as-code files.
*   `tests/`: Unit, integration, and load tests.
*   `notebooks/`: Jupyter notebooks for prototyping and evaluation.
*   `frontend/`: (If applicable) Web UI for interacting with your agent.
*   `README.md`: **Project-specific instructions for your chosen template.**
*   `GEMINI.md`: Use this file with AI tools (like [Gemini CLI](https://github.com/google-gemini/gemini-cli)) to ask questions about the template, ADK concepts, or project structure.

Your development loop will look like this:

1.  **Prototype:** Use the notebooks in `notebooks/` for rapid experimentation with your agent's core logic. This is ideal for trying new prompts or tools before integrating them.
2.  **Integrate:** Edit `app/agent.py` and other files in the agent directory (usually `app/`, but configurable) to incorporate your new logic into the main application.
3.  **Test:** Run the interactive UI playground to test your changes. It features hot-reloading, chat history, and user feedback.

```bash
# Install dependencies and launch the local playground
make install && make playground
```

::: tip Package Management with uv
Add new dependencies with `uv add <package>` and remove them with `uv remove <package>`.
:::
> Note: The specific UI playground launched by `make playground` depends on the agent template you selected during creation.

## 2. Deploy to the Cloud

Once you're satisfied with local testing, you are ready to deploy your agent to Google Cloud. The process involves two main stages: first, deploying to a hands-on development environment for quick iteration, and second, setting up a formal CI/CD pipeline for staging and production.

*All `make` commands should be run from the root of your agent project.*

### Stage 1: Deploy to a Cloud Development Environment

This initial stage is for provisioning a non-production environment in the cloud for remote testing and iteration.

**i. Set Google Cloud Project**

Configure `gcloud` to target your development project.
```bash
# Replace YOUR_DEV_PROJECT_ID with your actual Google Cloud Project ID
gcloud config set project YOUR_DEV_PROJECT_ID
```

**ii. Provision Cloud Resources**

This command uses Terraform to set up the necessary cloud resources for your dev environment.

::: tip Optional Step
This step is recommended to create a development environment that closely mirrors production (including dedicated service accounts and IAM permissions). However, for simple deployments, you can consider this step optional and proceed directly to deploying the backend if you have sufficient permissions.
:::

```bash
make setup-dev-env
```

**iii. Deploy Agent Backend**

Build and deploy your agent's backend to the dev environment.
```bash
make deploy
```

### Stage 2: Set Up the Path to Production with CI/CD

Once you've refined your agent in the development environment, the next stage is to set up a fully automated CI/CD pipeline for seamless deployment through staging and into production.

#### Option 1: Automated CI/CD Setup

From the root of your agent project, run:
```bash
agent-starter-pack setup-cicd
```
This single command handles everything:
- Creates a GitHub repository.
- Connects it to your chosen CI/CD provider (Google Cloud Build or GitHub Actions).
- Provisions all necessary infrastructure for your **staging and production environments** using Terraform.
- Configures the deployment triggers.

For a detailed walkthrough, see the [**`setup-cicd` CLI reference**](../cli/setup_cicd).

#### Option 2: Manual CI/CD Setup

For full control or for use with other Git providers, refer to the [manual deployment setup guide](./deployment.md).

#### Trigger Your First Deployment

After the CI/CD setup is complete, commit and push your code to trigger the pipeline. This will deploy your agent to the staging environment first.
```bash
git add -A
git config --global user.email "you@example.com" # If not already configured
git config --global user.name "Your Name"     # If not already configured
git commit -m "Initial commit of agent code"
git push --set-upstream origin main
```


## 3. Monitor Your Deployed Agent

Track your agent's performance using integrated observability tools. OpenTelemetry GenAI instrumentation automatically captures telemetry data and exports it to Google Cloud services.

*   **BigQuery**: Query telemetry data including token usage, model interactions, and performance metrics. Data is automatically available via external tables and linked datasets.
*   **Cloud Logging**: View GenAI operation logs and user feedback in dedicated Cloud Logging buckets with 10-year retention.
*   **Cloud Trace**: Inspect request flows and analyze latencies for GenAI operations at: `https://console.cloud.google.com/traces/list?project=YOUR_PROJECT_ID`
*   **Visualization** (Optional): Connect your BigQuery data to BI tools for custom dashboards.

➡️ For complete setup instructions, example queries, and testing in dev, see the [Observability Guide](./observability.md).

## 4. Advanced Customization

Tailor the starter pack further to meet your specific requirements.

*   **RAG Data Ingestion**: For Retrieval Augmented Generation (RAG) agents, configure data pipelines to process your information and load embeddings into Vertex AI Search or Vector Search.
    ➡️ See the [Data Ingestion Guide](./data-ingestion.md).
*   **Custom Terraform**: Modify Terraform configurations in `deployment/terraform/` for unique infrastructure needs.
    ➡️ Refer to the [Deployment Guide](./deployment.md).
*   **CI/CD Pipelines**: The CI/CD workflow definitions are located in the `.github/workflows` or `.cloudbuild` directories. You can customize these YAML files to add new steps, change triggers, or modify deployment logic.
