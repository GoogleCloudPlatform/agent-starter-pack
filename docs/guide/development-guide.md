# Development Guide

::: tip Note
This starter pack embraces a **"bring your own agent"** philosophy. You focus on your unique business logic, and we provide the scaffolding for UI, infrastructure, deployment, and monitoring.
:::

### 1. Prototype Your Agent
Begin by building and experimenting with your Generative AI Agent.

*   Use the introductory notebooks in `notebooks/` for guidance. This is ideal for rapid experimentation and focused agent logic development before integrating into the full application structure
*   Evaluate its performance with [Vertex AI Evaluation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview).

### 2. Integrate Your Agent
Incorporate your prototyped agent into the application.

*   Edit `app/agent.py` to import and configure your agent.
*   Customize code within the `app/` directory (e.g., prompts, tools, API endpoints, business logic, functionality).

### 3. Test Locally
Iterate on your agent using the built-in UI playground. It automatically reloads on code changes and offers features like chat history, user feedback, and diverse input types.

> Note: The specific UI playground (e.g., Streamlit, ADK web UI) launched by `make playground` depends on the agent template you selected.

### 4. Deploy to the Cloud
Once you're satisfied with local testing, you are ready to deploy your agent to Google Cloud!

*All `make` commands should be run from the root of your agent project.*

#### A. Cloud Development Environment Setup
Establish a development (dev) environment in the cloud for initial remote testing.

**i. Set Google Cloud Project:**
Configure `gcloud` to target your development project:
```bash
# Replace YOUR_DEV_PROJECT_ID with your actual Google Cloud Project ID
gcloud config set project YOUR_DEV_PROJECT_ID
```

**ii. Provision Cloud Resources:**
This command uses Terraform (scripts in `deployment/terraform/dev/`) to set up necessary cloud resources (IAM, databases, etc.):
```bash
make setup-dev-env
```

**iii. 🚀 Deploy Agent Backend:**
Build and deploy your agent's backend to the dev environment:
```bash
make backend
```

#### B. Production-Ready Deployment with CI/CD
For reliable, automated deployments to staging and production, a CI/CD pipeline is essential. Customize tests within your pipeline as needed.

**Option 1: One-Command CI/CD Setup (Recommended for GitHub)**
The `agent-starter-pack` CLI streamlines CI/CD setup with GitHub:
```bash
uvx agent-starter-pack setup-cicd
```
This automates creating a GitHub repository, connecting to Cloud Build, setting up staging/production infrastructure with Terraform, and configuring CI/CD triggers.

Follow the interactive prompts. For critical systems needing granular control, consider the manual setup.
See the [`agent-starter-pack setup-cicd` CLI reference](../cli/setup_cicd) for details. *(Note: Automated setup currently supports GitHub only).*

**Option 2: Manual CI/CD Setup**
For full control and compatibility with other Git providers, refer to the [manual deployment setup guide](./deployment.md).

**Initial Commit & Push (After CI/CD Setup):**
Once CI/CD is configured, commit and push your code to trigger the first pipeline run:
```bash
git add -A
git config --global user.email "you@example.com" # If not already configured
git config --global user.name "Your Name"     # If not already configured
git commit -m "Initial commit of agent code"
git push --set-upstream origin main
```

### 5. Monitor Your Deployed Agent
Track your agent's performance and gather insights using integrated observability tools.

*   **Technology**: OpenTelemetry events are sent to Google Cloud.
*   **Cloud Trace & Logging**: Inspect request flows, analyze latencies, and review prompts/outputs. Access traces at: `https://console.cloud.google.com/traces/list?project=YOUR_PROD_PROJECT_ID`
*   **BigQuery**: Route trace and log data to BigQuery for long-term storage and advanced analytics.
*   **Looker Studio Dashboards**: Visualize agent performance with pre-built templates:
    *   ADK Agents: [Looker Studio ADK Dashboard](https://lookerstudio.google.com/c/reporting/46b35167-b38b-4e44-bd37-701ef4307418/page/tEnnC)
    *   Non-ADK Agents: [Looker Studio Non-ADK Dashboard](https://lookerstudio.google.com/c/reporting/fa742264-4b4b-4c56-81e6-a667dd0f853f/page/tEnnC)
    *(Remember to follow the "Setup Instructions" within the dashboards to connect your project's data sources).*

➡️ For details, see the [Observability Guide](./observability.md).

### 6. Advanced Customization & Data
Tailor the starter pack further to meet specific needs.

*   **RAG Data Ingestion**: For Retrieval Augmented Generation (RAG) agents, configure data pipelines to process your information and load embeddings into Vertex AI Search or Vector Search.
    ➡️ See the [Data Ingestion Guide](./data-ingestion.md).
*   **Custom Terraform**: Modify Terraform configurations in `deployment/terraform/` for unique infrastructure requirements.
    ➡️ Refer to the [Deployment Guide](./deployment.md).
