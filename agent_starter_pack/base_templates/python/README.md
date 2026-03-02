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
{%- if cookiecutter.deployment_target in ('cloud_run', 'gke') %}
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
{%- if cookiecutter.deployment_target == 'gke' %}
│   ├── k8s/                   # Kubernetes manifests for GKE deployment
{%- endif %}
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
{%- if cookiecutter.deployment_target in ('cloud_run', 'gke') %}
| `make deploy`        | Deploy agent to {{ 'GKE' if cookiecutter.deployment_target == 'gke' else 'Cloud Run' }}                                                                   |
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

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
{%- if extracted|default(false) %}
| `uvx agent-starter-pack enhance` | Add CI/CD pipelines and Terraform infrastructure |
{%- else %}
{%- if cookiecutter.cicd_runner == 'skip' %}
| `uvx agent-starter-pack enhance` | Add CI/CD pipelines and Terraform infrastructure |
{%- endif %}
| `uvx agent-starter-pack setup-cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
{%- endif %}
| `uvx agent-starter-pack upgrade` | Auto-upgrade to latest version while preserving customizations |
| `uvx agent-starter-pack extract` | Extract minimal, shareable version of your agent |

---
{%- endif %}
{%- if not extracted|default(false) %}

## Development

Edit your agent logic in `{{cookiecutter.agent_directory}}/agent.py` and test with `make playground` - it auto-reloads on save.
{%- if cookiecutter.cicd_runner != 'skip' %}
Use notebooks in `notebooks/` for prototyping and Vertex AI Evaluation.
{%- endif %}
See the [development guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/development-guide) for the full workflow.

## Deployment

```bash
gcloud config set project <your-project-id>
make deploy
```
{%- if cookiecutter.is_adk_live %}

For secure access, use Identity-Aware Proxy: `make deploy IAP=true`
{%- endif %}
{%- if cookiecutter.cicd_runner == 'skip' %}

To add CI/CD and Terraform, run `uvx agent-starter-pack enhance`.
{%- endif %}
To set up your production infrastructure, run `uvx agent-starter-pack setup-cicd`.
See the [deployment guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/deployment) for details.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.
See the [observability guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/observability) for queries and dashboards.
{%- if cookiecutter.is_a2a %}

## A2A Inspector

This agent supports the [A2A Protocol](https://a2a-protocol.org/). Use `make inspector` to test interoperability.
See the [A2A Inspector docs](https://github.com/a2aproject/a2a-inspector) for details.
{%- endif %}
{%- endif %}
