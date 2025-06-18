# {{cookiecutter.project_name}}

{{cookiecutter.agent_description}}
Agent generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) version `{{ cookiecutter.package_version }}`

## Project Structure

This project is organized as follows:

```
{{cookiecutter.project_name}}/
├── app/                 # Core application code
│   ├── agent.py         # Main agent logic
{%- if cookiecutter.deployment_target == 'cloud_run' %}
│   ├── server.py        # FastAPI Backend server
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
│   ├── agent_engine_app.py # Agent Engine application logic
{%- endif %}
│   └── utils/           # Utility functions and helpers
├── deployment/          # Infrastructure and deployment scripts
├── notebooks/           # Jupyter notebooks for prototyping and evaluation
├── tests/               # Unit, integration, and load tests
├── Makefile             # Makefile for common commands
└── pyproject.toml       # Project dependencies and configuration
```

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager - [Install](https://docs.astral.sh/uv/getting-started/installation/)
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
| `make backend`       | Deploy agent to Cloud Run |
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
| `make setup-dev-env` | Set up development environment resources using Terraform                                    |
{%- if cookiecutter.data_ingestion %}
| `make data-ingestion`| Run data ingestion pipeline in the Dev environment                                           |
{%- endif %}
| `uv run jupyter lab` | Launch Jupyter notebook                                                                     |

For full command options and usage, refer to the [Makefile](Makefile).

{% if cookiecutter.agent_name == 'live_api' %}
## Usage

This template follows a "bring your own agent" approach - you focus on your business logic in `app/agent.py`, and the template handles the surrounding components (UI, infrastructure, deployment, monitoring).

Here’s the recommended workflow for local development:

1.  **Install Dependencies (if needed):**
    ```bash
    make install
    ```

2.  **Start the Backend Server:**
    Open a terminal and run:
    ```bash
    make local-backend
    ```
    The backend is ready when you see `INFO:     Application startup complete.` Wait for this message before starting the frontend.

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

3.  **Start the Frontend UI:**
    Open *another* terminal and run:
    ```bash
    make ui
    ```
    This launches the Streamlit application, which connects to the backend server (by default at `http://localhost:8000`).

4.  **Interact and Iterate:**
    *   Open the Streamlit UI in your browser (usually `http://localhost:8501` or `http://localhost:3001`).
    *   Click the play button in the UI to connect to the backend.
    *   Interact with the agent! Try prompts like: *"Using the tool you have, define Governance in the context MLOPs"*
    *   Modify the agent logic in `app/agent.py`. The backend server (FastAPI with `uvicorn --reload`) should automatically restart when you save changes. Refresh the frontend if needed to see behavioral changes.

<details>
<summary><b>Cloud Shell Usage</b></summary>

To run the agent using Google Cloud Shell:

1.  **Start the Frontend:**
    In a Cloud Shell tab, run:
    ```bash
    make ui
    ```
    Accept prompts to use a different port if 3000 is busy. Click the `localhost:PORT` link for the web preview.

2.  **Start the Backend:**
    Open a *new* Cloud Shell tab. Set your project: `gcloud config set project [PROJECT_ID]`. Then run:
    ```bash
    make local-backend
    ```

3.  **Configure Backend Web Preview:**
    Use the Cloud Shell Web Preview feature to expose port 8000. Change the default port from 8080 to 8000. See [Cloud Shell Web Preview documentation](https://cloud.google.com/shell/docs/using-web-preview#preview_the_application).

4.  **Connect Frontend to Backend:**
    *   Copy the URL generated by the backend web preview (e.g., `https://8000-cs-....cloudshell.dev/`).
    *   Paste this URL into the "Server URL" field in the frontend UI settings (in the first tab).
    *   Click the "Play button" to connect.

*   **Note:** The feedback feature in the frontend might not work reliably in Cloud Shell due to cross-origin issues between the preview URLs.
</details>

</details>
{%- else %}
## Usage

This template follows a "bring your own agent" approach - you focus on your business logic, and the template handles everything else (UI, infrastructure, deployment, monitoring).

1. **Prototype:** Build your Generative AI Agent using the intro notebooks in `notebooks/` for guidance. Use Vertex AI Evaluation to assess performance.
2. **Integrate:** Import your agent into the app by editing `app/agent.py`.
3. **Test:** Explore your agent functionality using the Streamlit playground with `make playground`. The playground offers features like chat history, user feedback, and various input types, and automatically reloads your agent on code changes.
4. **Deploy:** Set up and initiate the CI/CD pipelines, customizing tests as necessary. Refer to the [deployment section](#deployment) for comprehensive instructions. For streamlined infrastructure deployment, simply run `uvx agent-starter-pack setup-cicd`. Check out the [`agent-starter-pack setup-cicd` CLI command](https://googlecloudplatform.github.io/agent-starter-pack/cli/setup_cicd.html). Currently only supporting Github.
5. **Monitor:** Track performance and gather insights using Cloud Logging, Tracing, and the Looker Studio dashboard to iterate on your application.
{% endif %}

## Deployment

> **Note:** For a streamlined one-command deployment of the entire CI/CD pipeline and infrastructure using Terraform, you can use the [`agent-starter-pack setup-cicd` CLI command](https://googlecloudplatform.github.io/agent-starter-pack/cli/setup_cicd.html). Currently only supporting Github.

### Dev Environment

You can test deployment towards a Dev Environment using the following command:

```bash
gcloud config set project <your-dev-project-id>
make backend
```
{% if cookiecutter.agent_name == 'live_api' %}
**Accessing the Deployed Backend Locally:**

To connect your local frontend (`make ui`) to the backend deployed on Cloud Run, use the `gcloud` proxy:

1.  **Start the proxy:**
    ```bash
    # Replace with your actual service name, project, and region
    gcloud run services proxy gemini-agent-service --port 8000 --project $PROJECT_ID --region $REGION
    ```
    Keep this terminal running.

2.  **Connect Frontend:** Your deployed backend is now accessible locally at `http://localhost:8000`. Point your Streamlit UI to this address.
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
