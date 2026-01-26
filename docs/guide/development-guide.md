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

::: code-group
```text [Python Projects]
app/           # Backend agent code (prompts, tools, business logic)
.cloudbuild/   # CI/CD for Google Cloud Build (if selected)
.github/       # CI/CD for GitHub Actions (if selected)
deployment/    # Terraform infrastructure-as-code files
tests/         # Unit, integration, and load tests
notebooks/     # Jupyter notebooks for prototyping
frontend/      # (If applicable) Web UI for your agent
README.md      # Project-specific instructions
GEMINI.md      # AI assistant context file
```

```text [Go Projects]
agent/         # Backend agent code (tools, business logic)
.cloudbuild/   # CI/CD for Google Cloud Build (if selected)
.github/       # CI/CD for GitHub Actions (if selected)
deployment/    # Terraform infrastructure-as-code files
e2e/           # Integration and load tests
README.md      # Project-specific instructions
GEMINI.md      # AI assistant context file
```
:::

Your development loop will look like this:

**Python Projects**

1. **Prototype:** Use notebooks in `notebooks/` for rapid experimentation
2. **Integrate:** Edit `app/agent.py` to incorporate your logic
3. **Test:** Run the interactive playground with hot-reloading

**Go Projects**

1. **Integrate:** Edit `agent/agent.go` to add tools and logic
2. **Test:** Run the interactive playground to test changes

```bash
# Install dependencies and launch the local playground
make install && make playground
```

::: tip Package Management
::: code-group
```bash [Python (uv)]
uv add <package>      # Add dependency
uv remove <package>   # Remove dependency
```

```bash [Go]
go get <package>      # Add dependency
go mod tidy           # Clean up dependencies
```
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

## 4. Keeping Your Project Up-to-Date

As agent-starter-pack evolves with new features, security fixes, and best practices, you can upgrade your existing projects to newer versions using the `upgrade` command.

```bash
# Preview what would change
uvx agent-starter-pack upgrade --dry-run

# Apply the upgrade
uvx agent-starter-pack upgrade
```

The upgrade uses an intelligent 3-way merge:
- **Auto-updates** scaffolding files you haven't modified
- **Preserves** your customizations when ASP hasn't changed those files
- **Prompts** you to resolve conflicts when both have changed

➡️ See the [`upgrade` CLI reference](../cli/upgrade.md) for detailed usage.

## 5. Advanced Customization

Tailor the starter pack further to meet your specific requirements.

*   **RAG Data Ingestion**: For Retrieval Augmented Generation (RAG) agents, configure data pipelines to process your information and load embeddings into Vertex AI Search or Vector Search.
    ➡️ See the [Data Ingestion Guide](./data-ingestion.md).
*   **Custom Terraform**: Modify Terraform configurations in `deployment/terraform/` for unique infrastructure needs.
    ➡️ Refer to the [Deployment Guide](./deployment.md).
*   **CI/CD Pipelines**: The CI/CD workflow definitions are located in the `.github/workflows` or `.cloudbuild` directories. You can customize these YAML files to add new steps, change triggers, or modify deployment logic.
