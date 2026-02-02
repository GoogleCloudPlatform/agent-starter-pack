# {{cookiecutter.project_name}}

A Java agent built with Google's Agent Development Kit (ADK).
{%- if extracted|default(false) %}

Extracted from a project generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack)
{%- endif %}

## Project Structure

```
{{cookiecutter.project_name}}/
├── pom.xml                  # Maven project file
├── src/
│   ├── main/
│   │   ├── java/{{cookiecutter.java_package_path}}/
│   │   │   ├── Main.java    # Application entry point
│   │   │   └── Agent.java   # Agent implementation
│   │   └── resources/
│   │       └── application.properties
│   └── test/java/{{cookiecutter.java_package_path}}/
│       └── unit/            # Unit tests
{%- if not extracted|default(false) %}
│       └── e2e/             # End-to-end tests
│           ├── integration/ # Server integration tests
│           └── load_test/   # Load tests
├── deployment/
│   └── terraform/           # Infrastructure as Code
├── Dockerfile               # Container build
├── GEMINI.md                # AI-assisted development guide
{%- endif %}
└── Makefile                 # {% if extracted|default(false) %}Development commands{% else %}Common commands{% endif %}
```
{%- if not extracted|default(false) %}

> **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.
{%- endif %}

## Requirements
{%- if extracted|default(false) %}

- **Java**: 17 or later - [Install](https://adoptium.net/)
- **Maven**: 3.9 or later - [Install](https://maven.apache.org/install.html)
{%- else %}

- Java 17 or later
- Maven 3.9 or later
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
   Open http://localhost:8080/dev-ui/ in your browser.
{%- endif %}

## Commands

| Command | Description |
|---------|-------------|
| `make install` | Download Maven dependencies |
| `make playground` | Launch local development environment with web UI |
| `make test` | Run unit and e2e integration tests |
| `make build` | Build JAR file |
| `make clean` | Clean build artifacts |
| `make lint` | Run code quality checks |
{%- if not extracted|default(false) %}
| `make local-backend` | Start server on port 8080 |
| `make deploy` | Deploy to Cloud Run |
| `make load-test` | Run load tests (requires running server) |
| `make inspector` | Launch A2A Protocol Inspector |
| `make setup-dev-env` | Set up Terraform infrastructure |
| `make register-gemini-enterprise` | Register agent with Gemini Enterprise |
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
# Run unit and e2e integration tests
make test

# Run load tests locally (start server first with `make local-backend`)
make load-test

# Run load tests against remote deployment
make load-test URL=https://your-service.run.app

# Run load tests with custom parameters
make load-test DURATION=60 USERS=20 RAMP=5
```

Use `make inspector` to launch the A2A Protocol Inspector for interactive testing.

## Keeping Up-to-Date

To upgrade this project to the latest agent-starter-pack version:

```bash
uvx agent-starter-pack upgrade
```

This intelligently merges updates while preserving your customizations. Use `--dry-run` to preview changes first. See the [upgrade CLI reference](https://googlecloudplatform.github.io/agent-starter-pack/cli/upgrade.html) for details.

## Learn More

- [ADK for Java Documentation](https://google.github.io/adk-docs/)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack)
{%- endif %}
