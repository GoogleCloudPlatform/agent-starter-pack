# {{cookiecutter.project_name}}

A Go agent built with Google's Agent Development Kit (ADK).
{%- if extracted|default(false) %}

Extracted from a project generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack)
{%- endif %}

## Project Structure

```
{{cookiecutter.project_name}}/
├── main.go              # Application entry point
├── agent/
│   └── agent.go         # Agent implementation
{%- if not extracted|default(false) %}
├── e2e/
│   ├── integration/     # Integration tests
│   └── load_test/       # Load testing
├── deployment/
│   └── terraform/       # Infrastructure as Code
{%- endif %}
├── go.mod               # Go module definition
{%- if not extracted|default(false) %}
├── Dockerfile           # Container build
├── GEMINI.md            # AI-assisted development guide
{%- endif %}
└── Makefile             # {% if extracted|default(false) %}Development commands{% else %}Common commands{% endif %}
```
{%- if not extracted|default(false) %}

> **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.
{%- endif %}

## Requirements
{%- if extracted|default(false) %}

- **Go**: 1.24 or later - [Install](https://go.dev/doc/install)
- **golangci-lint**: For code quality checks - [Install](https://golangci-lint.run/welcome/install/)
{%- else %}

- Go 1.24 or later
- Google Cloud SDK (`gcloud`)
- A Google Cloud project with Vertex AI enabled
{%- endif %}

## Quick Start
{%- if extracted|default(false) %}

```bash
make install && make playground
```
{%- else %}

1. **Install dependencies:**
   ```bash
   make install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Google Cloud project ID
   ```

3. **Run the playground:**
   ```bash
   make playground
   ```
   Open http://localhost:8501/ui/ in your browser.
{%- endif %}

## Commands

| Command | Description |
|---------|-------------|
| `make install` | Download Go dependencies |
| `make playground` | Launch local development environment |
| `make lint` | Run code quality checks (golangci-lint) |
{%- if not extracted|default(false) %}
| `make test` | Run all tests |
| `make local-backend` | Start API server on port 8000 |
| `make build` | Build binary |
| `make deploy` | Deploy to Cloud Run |
{%- endif %}

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
{%- if extracted|default(false) %}
| `uvx agent-starter-pack enhance` | Add CI/CD pipelines and Terraform infrastructure |
{%- else %}
| `uvx agent-starter-pack setup-cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
{%- endif %}
| `uvx agent-starter-pack upgrade` | Auto-upgrade to latest version while preserving customizations |
| `uvx agent-starter-pack extract` | Extract minimal, shareable version of your agent |

---
{%- endif %}
{%- if not extracted|default(false) %}

## Development

Edit your agent logic in `agent/agent.go` and test with `make playground` - it auto-reloads on save.
See the [development guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/development-guide) for the full workflow.

## Deployment

```bash
gcloud config set project <your-project-id>
make deploy
```

See the [deployment guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/deployment) for production CI/CD setup.

## Learn More

- [ADK for Go Documentation](https://google.github.io/adk-docs/)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack)
{%- endif %}
