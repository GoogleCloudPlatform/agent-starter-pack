# {{cookiecutter.project_name}}

{{cookiecutter.agent_description}}
Agent generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) version `{{ cookiecutter.package_version }}`

## Project Structure

This project is organized as follows:

```
{{cookiecutter.project_name}}/
├── {{cookiecutter.agent_directory}}/                 # Core application code
│   ├── agent.py         # Main agent logic
{%- if cookiecutter.deployment_target == 'cloud_run' %}
│   ├── fast_api_app.py  # FastAPI Backend server
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
│   ├── agent_engine_app.py # Agent Engine application logic
{%- endif %}
│   └── app_utils/       # App utilities and helpers
{%- if cookiecutter.cicd_runner == 'google_cloud_build' %}
├── .cloudbuild/         # CI/CD pipeline configurations for Google Cloud Build
{%- elif cookiecutter.cicd_runner == 'github_actions' %}
├── .github/             # CI/CD pipeline configurations for GitHub Actions
{%- endif %}
├── deployment/          # Infrastructure and deployment scripts
├── notebooks/           # Jupyter notebooks for prototyping and evaluation
├── tests/               # Unit, integration, and load tests
├── Makefile             # Makefile for common commands
├── GEMINI.md            # AI-assisted development guide
└── pyproject.toml       # Project dependencies and configuration
```

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)
- **Terraform**: For infrastructure deployment - [Install](https://developer.hashicorp.com/terraform/downloads)
- **make**: Build automation tool - [Install](https://www.gnu.org/software/make/) (pre-installed on most Unix-based systems)


## Quick Start (Local Testing)

Install required packages and launch the local development environment:

```bash
make install && make playground
```

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `make install`       | Install all required dependencies using uv                                                  |
{%- if cookiecutter.settings.get("commands", {}).get("extra", {}) %}
{%- for cmd_name, cmd_value in cookiecutter.settings.get("commands", {}).get("extra", {}).items() %}
| `make {{ cmd_name }}`       | {% if cmd_value is mapping %}{% if cmd_value.description %}{{ cmd_value.description }}{% else %}{% if cookiecutter.deployment_target in cmd_value %}{{ cmd_value[cookiecutter.deployment_target] }}{% else %}{{ cmd_value.command if cmd_value.command is string else "" }}{% endif %}{% endif %}{% else %}{{ cmd_value }}{% endif %} |
{%- endfor %}
{%- endif %}
{%- if cookiecutter.deployment_target == 'cloud_run' %}
| `make playground`    | Launch local development environment with backend and frontend{%- if cookiecutter.is_adk %} - leveraging `adk web` command. {%- endif %}|
| `make deploy`        | Deploy agent to Cloud Run (use `IAP=true` to enable Identity-Aware Proxy, `PORT=8080` to specify container port) |
| `make local-backend` | Launch local development server with hot-reload |
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
| `make playground`    | Launch Streamlit interface for testing agent locally and remotely |
| `make deploy`        | Deploy agent to Agent Engine |
{%- if cookiecutter.is_adk_live %}
| `make local-backend` | Launch local development server with hot-reload |
| `make ui`            | Start the frontend UI separately for development (requires backend running separately) |
| `make playground-dev` | Launch dev playground with both frontend and backend hot-reload |
| `make playground-remote` | Connect to remote deployed agent with local frontend |
| `make build-frontend` | Build the frontend for production |
{%- endif %}
{%- if cookiecutter.is_adk %}
| `make register-gemini-enterprise` | Register deployed agent to Gemini Enterprise ([docs](https://googlecloudplatform.github.io/agent-starter-pack/cli/register_gemini_enterprise.html)) |
{%- endif -%}
{%- endif -%}
{# TODO: Remove 'and cookiecutter.deployment_target == 'cloud_run'' when inspector adds HTTP-JSON support #}
{%- if cookiecutter.is_adk_a2a and cookiecutter.deployment_target == 'cloud_run' %}
| `make inspector`     | Launch A2A Protocol Inspector to test your agent implementation                             |
{%- endif %}
| `make test`          | Run unit and integration tests                                                              |
| `make lint`          | Run code quality checks (codespell, ruff, mypy)                                             |
| `make setup-dev-env` | Set up development environment resources using Terraform                         |
{%- if cookiecutter.data_ingestion %}
| `make data-ingestion`| Run data ingestion pipeline in the Dev environment                                           |
{%- endif %}

For full command options and usage, refer to the [Makefile](Makefile).

{# TODO: Remove 'and cookiecutter.deployment_target == 'cloud_run'' condition #}
{# when a2a-inspector adds HTTP-JSON transport support (currently JSON-RPC 2.0 only) #}
{%- if cookiecutter.is_adk_a2a %}
{%- if cookiecutter.deployment_target == 'cloud_run' %}

## Using the A2A Inspector

This agent implements the [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/), enabling interoperability with agents across different frameworks and languages.

The [A2A Inspector](https://github.com/a2aproject/a2a-inspector) provides the following core features:
- 🔍 View agent card and capabilities
- ✅ Validate A2A specification compliance
- 💬 Test communication with live chat interface
- 🐛 Debug with raw JSON-RPC 2.0 message console

### Local Testing

1. Start your agent:
   ```bash
   make local-backend
   ```

2. In a separate terminal, launch the A2A Protocol Inspector:
   ```bash
   make inspector
   ```

3. Open http://localhost:5001 and connect to `http://localhost:8000`

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
    This launches the Streamlit application, which connects to the backend server at `http://localhost:8000`.
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

1. **Prototype:** Build your Generative AI Agent using the intro notebooks in `notebooks/` for guidance. Use Vertex AI Evaluation to assess performance.
2. **Integrate:** Import your agent into the app by editing `{{cookiecutter.agent_directory}}/agent.py`.
3. **Test:** Explore your agent functionality using the Streamlit playground with `make playground`. The playground offers features like chat history, user feedback, and various input types, and automatically reloads your agent on code changes.
4. **Deploy:** Set up and initiate the CI/CD pipelines, customizing tests as necessary. Refer to the [deployment section](#deployment) for comprehensive instructions. For streamlined infrastructure deployment, simply run `uvx agent-starter-pack setup-cicd`. Check out the [`agent-starter-pack setup-cicd` CLI command](https://googlecloudplatform.github.io/agent-starter-pack/cli/setup_cicd.html). Currently supports GitHub with both Google Cloud Build and GitHub Actions as CI/CD runners.
5. **Monitor:** Track performance and gather insights using Cloud Logging, Tracing, and the Looker Studio dashboard to iterate on your application.

The project includes a `GEMINI.md` file that provides context for AI tools like Gemini CLI when asking questions about your template.
{% endif %}

## Deployment

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

{% if not cookiecutter.is_adk_live %}
## Monitoring and Observability
> You can use [this Looker Studio dashboard]({%- if cookiecutter.is_adk %}https://lookerstudio.google.com/reporting/46b35167-b38b-4e44-bd37-701ef4307418/page/tEnnC{%- else %}https://lookerstudio.google.com/c/reporting/fa742264-4b4b-4c56-81e6-a667dd0f853f/page/tEnnC{%- endif %}
) template for visualizing events being logged in BigQuery. See the "Setup Instructions" tab to getting started.

The application uses OpenTelemetry for comprehensive observability with all events being sent to Google Cloud Trace and Logging for monitoring and to BigQuery for long term storage. 
{%- endif %}
