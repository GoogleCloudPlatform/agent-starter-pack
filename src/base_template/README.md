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
│   ├── server.py        # FastAPI Backend server
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
│   ├── agent_engine_app.py # Agent Engine application logic
{%- endif %}
│   └── utils/           # Utility functions and helpers
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
| `make playground`    | Launch local development environment with backend and frontend{%- if "adk" in cookiecutter.tags %} - leveraging `adk web` command. {%- endif %}|
| `make backend`       | Deploy agent to Cloud Run (use `IAP=true` to enable Identity-Aware Proxy) |
| `make local-backend` | Launch local development server |
{%- if cookiecutter.deployment_target == 'cloud_run' %}
{%- if cookiecutter.agent_name == 'live_api' %}
| `make ui`       | Launch Agent Playground front-end only |
{%- endif %}
{%- endif %}
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
| `make playground`    | Launch Streamlit interface for testing agent locally and remotely |
| `make backend`       | Deploy agent to Agent Engine |
{%- endif %}
| `make test`          | Run unit and integration tests                                                              |
| `make lint`          | Run code quality checks (codespell, ruff, mypy)                                             |
| `make setup-dev-env` | Set up development environment resources using Terraform                         |
{%- if cookiecutter.data_ingestion %}
| `make data-ingestion`| Run data ingestion pipeline in the Dev environment                                           |
{%- endif %}
| `uv run jupyter lab` | Launch Jupyter notebook                                                                     |

For full command options and usage, refer to the [Makefile](Makefile).

{% if cookiecutter.agent_name == 'live_api' %}
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
make backend
```
{% if cookiecutter.agent_name == 'live_api' %}
**Note:** For secure access to your deployed backend, consider using Identity-Aware Proxy (IAP) by running `make backend IAP=true`.
{%- endif %}

The repository includes a Terraform configuration for the setup of the Dev Google Cloud project.
See [deployment/README.md](deployment/README.md) for instructions.

### Production Deployment

The repository includes a Terraform configuration for the setup of a production Google Cloud project. Refer to [deployment/README.md](deployment/README.md) for detailed instructions on how to deploy the infrastructure and application.

{% if cookiecutter.agent_name != 'live_api' %}
## Monitoring and Observability
> You can use [this Looker Studio dashboard]({%- if "adk" in cookiecutter.tags %}https://lookerstudio.google.com/reporting/46b35167-b38b-4e44-bd37-701ef4307418/page/tEnnC{%- else %}https://lookerstudio.google.com/c/reporting/fa742264-4b4b-4c56-81e6-a667dd0f853f/page/tEnnC{%- endif %}
) template for visualizing events being logged in BigQuery. See the "Setup Instructions" tab to getting started.

The application uses OpenTelemetry for comprehensive observability with all events being sent to Google Cloud Trace and Logging for monitoring and to BigQuery for long term storage. 
{%- endif %}
