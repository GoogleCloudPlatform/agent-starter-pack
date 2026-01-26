# {{cookiecutter.project_name}}

{{cookiecutter.agent_description}}
{%- if extracted|default(false) %}
Extracted from a project generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) version `{{ cookiecutter.package_version }}`
{%- else %}
Agent generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) version `{{ cookiecutter.package_version }}`
{%- endif %}

## Project Structure

```
{{cookiecutter.project_name}}/
├── {{cookiecutter.agent_directory}}/         # Core agent code
│   ├── agent.py               # Main agent logic
{%- if extracted|default(false) %}
│   └── ...                    # Custom modules
{%- else %}
{%- if cookiecutter.deployment_target == 'cloud_run' %}
│   ├── fast_api_app.py        # FastAPI Backend server
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
│   ├── agent_engine_app.py    # Agent Engine application logic
{%- endif %}
│   └── app_utils/             # App utilities and helpers
{%- if cookiecutter.is_a2a and cookiecutter.agent_name == 'langgraph' %}
│       ├── executor/          # A2A protocol executor implementation
│       └── converters/        # Message converters for A2A protocol
{%- endif %}
{%- if cookiecutter.cicd_runner == 'google_cloud_build' %}
├── .cloudbuild/               # CI/CD pipeline configurations for Google Cloud Build
{%- elif cookiecutter.cicd_runner == 'github_actions' %}
├── .github/                   # CI/CD pipeline configurations for GitHub Actions
{%- endif %}
{%- if cookiecutter.cicd_runner != 'skip' %}
├── deployment/                # Infrastructure and deployment scripts
{%- if cookiecutter.agent_name != 'adk_live' %}
├── notebooks/                 # Jupyter notebooks for prototyping and evaluation
{%- endif %}
{%- endif %}
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
{%- endif %}
├── Makefile                   # Development commands
└── pyproject.toml             # Project dependencies
```
{%- if not extracted|default(false) %}

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.
{%- endif %}

## Requirements
{%- if extracted|default(false) %}

- **uv**: Python package manager - [Install](https://docs.astral.sh/uv/getting-started/installation/)
{%- else %}

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)
{%- if cookiecutter.cicd_runner != 'skip' %}
- **Terraform**: For infrastructure deployment - [Install](https://developer.hashicorp.com/terraform/downloads)
{%- endif %}
- **make**: Build automation tool - [Install](https://www.gnu.org/software/make/) (pre-installed on most Unix-based systems)
{%- endif %}


## Quick Start
{%- if extracted|default(false) %}

```bash
make install && make playground
```
{%- else %}

Install required packages and launch the local development environment:

```bash
make install && make playground
```

{%- if cookiecutter.is_adk %}
> **📊 Observability Note:** Agent telemetry (Cloud Trace) is always enabled. Prompt-response logging (GCS, BigQuery, Cloud Logging) is **disabled** locally, **enabled by default** in deployed environments (metadata only - no prompts/responses). See [Monitoring and Observability](#monitoring-and-observability) for details.
{%- else %}
> **📊 Observability Note:** Agent telemetry (Cloud Trace) is always enabled. Prompt-response logging is not available for LangGraph agents due to SDK limitations with streaming.
{%- endif %}
{%- endif %}

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `make install`       | Install dependencies using uv                                                               |
| `make playground`    | Launch local development environment                                                        |
| `make lint`          | Run code quality checks                                                                     |
{%- if not extracted|default(false) %}
{%- if cookiecutter.settings.get("commands", {}).get("extra", {}) %}
{%- for cmd_name, cmd_value in cookiecutter.settings.get("commands", {}).get("extra", {}).items() %}
| `make {{ cmd_name }}`       | {% if cmd_value is mapping %}{% if cmd_value.description %}{{ cmd_value.description }}{% else %}{% if cookiecutter.deployment_target in cmd_value %}{{ cmd_value[cookiecutter.deployment_target] }}{% else %}{{ cmd_value.command if cmd_value.command is string else "" }}{% endif %}{% endif %}{% else %}{{ cmd_value }}{% endif %} |
{%- endfor %}
{%- endif %}
| `make test`          | Run unit and integration tests                                                              |
{%- if cookiecutter.deployment_target == 'cloud_run' %}
| `make deploy`        | Deploy agent to Cloud Run                                                                   |
| `make local-backend` | Launch local development server with hot-reload                                             |
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
| `make deploy`        | Deploy agent to Agent Engine                                                                |
{%- if cookiecutter.is_adk_live %}
| `make local-backend` | Launch local development server with hot-reload                                             |
| `make ui`            | Start the frontend UI separately for development                                            |
| `make playground-dev` | Launch dev playground with both frontend and backend hot-reload                            |
| `make playground-remote` | Connect to remote deployed agent with local frontend                                    |
| `make build-frontend` | Build the frontend for production                                                          |
{%- endif %}
{%- if cookiecutter.is_adk or cookiecutter.is_a2a %}
| `make register-gemini-enterprise` | Register deployed agent to Gemini Enterprise                                  |
{%- endif -%}
{%- endif -%}
{%- if cookiecutter.is_a2a %}
| `make inspector`     | Launch A2A Protocol Inspector                                                               |
{%- endif %}
{%- if cookiecutter.cicd_runner != 'skip' %}
| `make setup-dev-env` | Set up development environment resources using Terraform                                   |
{%- endif %}
{%- if cookiecutter.data_ingestion %}
| `make data-ingestion`| Run data ingestion pipeline                                                                 |
{%- endif %}

For full command options and usage, refer to the [Makefile](Makefile).
{%- endif %}
{%- if extracted|default(false) %}

## Adding Deployment Capabilities

This is a minimal extracted agent. To add deployment infrastructure (CI/CD, Terraform, Cloud Run/Agent Engine support) and testing scaffolding, run:

```bash
agent-starter-pack enhance
```

This will restore the full project structure with deployment capabilities.
{%- endif %}
{%- if not extracted|default(false) %}
{%- if cookiecutter.is_a2a %}

## Using the A2A Inspector

This agent implements the [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/), enabling interoperability with agents across different frameworks and languages.

The [A2A Inspector](https://github.com/a2aproject/a2a-inspector) provides the following core features:
- 🔍 View agent card and capabilities
- ✅ Validate A2A specification compliance
- 💬 Test communication with live chat interface
- 🐛 Debug with the raw message console

### Local Testing
{%- if cookiecutter.deployment_target == 'cloud_run' %}

1. Start your agent:
   ```bash
   make local-backend
   ```

2. In a separate terminal, launch the A2A Protocol Inspector:
   ```bash
   make inspector
   ```

3. Open http://localhost:5001 and connect to `http://localhost:8000/a2a/{{cookiecutter.agent_directory}}/.well-known/agent-card.json`
{%- else %}

> **Note:** For Agent Engine deployments, local testing with A2A endpoints requires deployment first, as `make playground` uses the ADK web interface. For local development, use `make playground`. To test A2A protocol compliance, follow the Remote Testing instructions below.
{%- endif %}

### Remote Testing

1. Deploy your agent:
   ```bash
   make deploy
   ```

2. Launch the inspector:
   ```bash
   make inspector
   ```

3. Get an authentication token:
   ```bash
{%- if cookiecutter.deployment_target == 'cloud_run' %}
   gcloud auth print-identity-token
{%- else %}
   gcloud auth print-access-token
{%- endif %}
   ```

4. In the inspector UI at http://localhost:5001:
   - Add an HTTP header with name: `Authorization`
   - Set the value to: `Bearer <your-token-from-step-3>`
{%- if cookiecutter.deployment_target == 'cloud_run' %}
   - Connect to your deployed Cloud Run URL
{%- else %}
   - Connect to your Agent Engine URL using this format:
     ```
     https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{REGION}/reasoningEngines/{ENGINE_ID}/a2a/v1/card
     ```
     Find your `PROJECT_ID`, `REGION`, and `ENGINE_ID` in the `latest_deployment_metadata.json` file created after deployment.
{%- endif %}
{%- endif %}

{% if cookiecutter.is_adk_live %}
## Usage

This template follows a "bring your own agent" approach - you focus on your business logic in `{{cookiecutter.agent_directory}}/agent.py`, and the template handles the surrounding components (UI, infrastructure, deployment, monitoring).

Here’s the recommended workflow for local development:

1.  **Install Dependencies (if needed):**
    ```bash
    make install
    ```

2.  **Start the Full Stack Server:**
    The FastAPI server now serves both the backend API and frontend interface:
    ```bash
    make local-backend
    ```
    The server is ready when you see `INFO:     Application startup complete.` The frontend will be available at `http://localhost:8000`.

    <details>
    <summary><b>Optional: Use AI Studio / API Key instead of Vertex AI</b></summary>

    By default, the backend uses Vertex AI and Application Default Credentials. If you prefer to use Google AI Studio and an API key:

    ```bash
    export VERTEXAI=false
    export GOOGLE_API_KEY="your-google-api-key" # Replace with your actual key
    make local-backend
    ```
    Ensure `GOOGLE_API_KEY` is set correctly in your environment.
    </details>
    <br>

    <details>
    <summary><b>Alternative: Run Frontend Separately</b></summary>

    If you prefer to run the frontend separately (useful for frontend development), you can still use:
    ```bash
    make ui
    ```
    This launches the frontend application, which connects to the backend server at `http://localhost:8000`.
    </details>
    <br>

3.  **Interact and Iterate:**
    *   Open your browser and navigate to `http://localhost:8000` to access the integrated frontend.
    *   Click the play button in the UI to connect to the backend.
    *   Interact with the agent! Try prompts like: *"Using the tool you have, define Governance in the context MLOPs"*
    *   Modify the agent logic in `{{cookiecutter.agent_directory}}/agent.py`. The backend server (FastAPI with `uvicorn --reload`) should automatically restart when you save changes. Refresh the frontend if needed to see behavioral changes.


</details>
{%- else %}
## Usage

This template follows a "bring your own agent" approach - you focus on your business logic, and the template handles everything else (UI, infrastructure, deployment, monitoring).

{%- if cookiecutter.cicd_runner != 'skip' %}
1. **Prototype:** Build your Generative AI Agent using the intro notebooks in `notebooks/` for guidance. Use Vertex AI Evaluation to assess performance.
2. **Integrate:** Import your agent into the app by editing `{{cookiecutter.agent_directory}}/agent.py`.
3. **Test:** Explore your agent functionality using the local playground with `make playground`. The playground automatically reloads your agent on code changes.
4. **Deploy:** Set up and initiate the CI/CD pipelines, customizing tests as necessary. Refer to the [deployment section](#deployment) for comprehensive instructions. For streamlined infrastructure deployment, simply run `uvx agent-starter-pack setup-cicd`. Check out the [`agent-starter-pack setup-cicd` CLI command](https://googlecloudplatform.github.io/agent-starter-pack/cli/setup_cicd.html). Currently supports GitHub with both Google Cloud Build and GitHub Actions as CI/CD runners.
5. **Monitor:** Track performance and gather insights using BigQuery telemetry data, Cloud Logging, and Cloud Trace to iterate on your application.
{%- else %}
1. **Develop:** Edit your agent logic in `{{cookiecutter.agent_directory}}/agent.py`.
2. **Test:** Explore your agent functionality using the local playground with `make playground`. The playground automatically reloads your agent on code changes.
3. **Enhance:** When ready for production, run `uvx agent-starter-pack enhance` to add CI/CD pipelines, Terraform infrastructure, and evaluation notebooks.
{%- endif %}

The project includes a `GEMINI.md` file that provides context for AI tools like Gemini CLI when asking questions about your template.
{% endif %}

## Deployment
{%- if cookiecutter.cicd_runner != 'skip' %}

> **Note:** For a streamlined one-command deployment of the entire CI/CD pipeline and infrastructure using Terraform, you can use the [`agent-starter-pack setup-cicd` CLI command](https://googlecloudplatform.github.io/agent-starter-pack/cli/setup_cicd.html). Currently supports GitHub with both Google Cloud Build and GitHub Actions as CI/CD runners.

### Dev Environment

You can test deployment towards a Dev Environment using the following command:

```bash
gcloud config set project <your-dev-project-id>
make deploy
```
{% if cookiecutter.is_adk_live %}
**Note:** For secure access to your deployed backend, consider using Identity-Aware Proxy (IAP) by running `make deploy IAP=true`.
{%- endif %}

The repository includes a Terraform configuration for the setup of the Dev Google Cloud project.
See [deployment/README.md](deployment/README.md) for instructions.

### Production Deployment

The repository includes a Terraform configuration for the setup of a production Google Cloud project. Refer to [deployment/README.md](deployment/README.md) for detailed instructions on how to deploy the infrastructure and application.
{%- else %}

You can deploy your agent to a Dev Environment using the following command:

```bash
gcloud config set project <your-dev-project-id>
make deploy
```
{% if cookiecutter.is_adk_live %}
**Note:** For secure access to your deployed backend, consider using Identity-Aware Proxy (IAP) by running `make deploy IAP=true`.
{%- endif %}

When ready for production deployment with CI/CD pipelines and Terraform infrastructure, run `uvx agent-starter-pack enhance` to add these capabilities.
{%- endif %}

## Monitoring and Observability

The application provides two levels of observability:

**1. Agent Telemetry Events (Always Enabled)**
- OpenTelemetry traces and spans exported to **Cloud Trace**
- Tracks agent execution, latency, and system metrics

{%- if cookiecutter.is_adk %}

**2. Prompt-Response Logging (Configurable)**
- GenAI instrumentation captures LLM interactions (tokens, model, timing)
- Exported to **Google Cloud Storage** (JSONL), **BigQuery** (external tables), and **Cloud Logging** (dedicated bucket)

| Environment | Prompt-Response Logging |
|-------------|-------------------------|
| **Local Development** (`make playground`) | ❌ Disabled by default |
{%- if cookiecutter.cicd_runner != 'skip' %}
| **Deployed Environments** (via Terraform) | ✅ **Enabled by default** (privacy-preserving: metadata only, no prompts/responses) |
{%- endif %}

**To enable locally:** Set `LOGS_BUCKET_NAME` and `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT`.
{%- if cookiecutter.cicd_runner != 'skip' %}

**To disable in deployments:** Edit Terraform config to set `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false`.
{%- endif %}
{%- else %}

**Note:** Prompt-response logging is not available for LangGraph agents due to SDK limitations with streaming responses.
{%- endif %}

See the [observability guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/observability.html) for detailed instructions, example queries, and visualization options.

## Keeping Up-to-Date

To upgrade this project to the latest agent-starter-pack version:

```bash
uvx agent-starter-pack upgrade
```

This intelligently merges updates while preserving your customizations. Use `--dry-run` to preview changes first. See the [upgrade CLI reference](https://googlecloudplatform.github.io/agent-starter-pack/cli/upgrade.html) for details.
{%- endif %}
