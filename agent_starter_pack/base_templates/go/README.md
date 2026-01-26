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
{%- if extracted|default(false) %}

## Adding Deployment Capabilities

This is a minimal extracted agent. To add deployment infrastructure (CI/CD, Terraform, Cloud Run support) and testing scaffolding, run:

```bash
agent-starter-pack enhance
```

This will restore the full project structure with deployment capabilities.
{%- endif %}
{%- if not extracted|default(false) %}

## Deployment

### Quick Deploy

```bash
make deploy
```

### CI/CD Pipeline

This project includes CI/CD configuration for:
- **Cloud Build**: `.cloudbuild/` directory
- **GitHub Actions**: `.github/workflows/` directory

See `deployment/README.md` for detailed deployment instructions.

## Testing

```bash
# Run all tests
make test

# Run load tests (requires server on port 8000)
make local-backend  # In one terminal
make load-test      # In another terminal
```

## Keeping Up-to-Date

To upgrade this project to the latest agent-starter-pack version:

```bash
uvx agent-starter-pack upgrade
```

This intelligently merges updates while preserving your customizations. Use `--dry-run` to preview changes first. See the [upgrade CLI reference](https://googlecloudplatform.github.io/agent-starter-pack/cli/upgrade.html) for details.

## Learn More

- [ADK for Go Documentation](https://google.github.io/adk-docs/)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack)
{%- endif %}
