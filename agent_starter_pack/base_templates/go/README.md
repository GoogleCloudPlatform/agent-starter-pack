# {{cookiecutter.project_name}}

A Go agent built with Google's Agent Development Kit (ADK).

## Quick Start

### Prerequisites

- Go 1.24 or later
- Google Cloud SDK (`gcloud`)
- A Google Cloud project with Vertex AI enabled

### Setup

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

## Project Structure

```
{{cookiecutter.project_name}}/
├── main.go              # Application entry point
├── agent/
│   └── agent.go         # Agent implementation
├── e2e/
│   ├── integration/     # Integration tests
│   └── load_test/       # Load testing
├── deployment/
│   └── terraform/       # Infrastructure as Code
├── go.mod               # Go module definition
├── Dockerfile           # Container build
├── GEMINI.md            # AI-assisted development guide
└── Makefile             # Common commands
```

> **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Development Commands

| Command | Description |
|---------|-------------|
| `make playground` | Start local dev UI at http://localhost:8501/ui/ |
| `make local-backend` | Start API server on port 8000 |
| `make test` | Run all tests |
| `make lint` | Run linter (golangci-lint) |
| `make build` | Build binary |
| `make deploy` | Deploy to Cloud Run |

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

## Learn More

- [ADK for Go Documentation](https://google.github.io/adk-docs/)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Agent Starter Pack](https://github.com/GoogleCloudPlatform/agent-starter-pack)
