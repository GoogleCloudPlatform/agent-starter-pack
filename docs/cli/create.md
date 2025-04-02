# `create`

The Agent Starter Pack provides CLI commands to help you create and manage AI agent projects.

## Create Command

The `create` command helps you create new GCP-based AI agent projects from templates.

```bash
agent-starter-pack create PROJECT_NAME [OPTIONS]
```

### Arguments

- `PROJECT_NAME`: Name of the project to create (must be 26 characters or less, will be converted to lowercase).

### Options

The following options will be prompted interactively if not provided via the command line:
- `--agent`, `-a`: Agent name or number to use. Lists available agents if omitted.
- `--deployment-target`, `-d`: Deployment target (`agent_engine` or `cloud_run`). Prompts if omitted.
- `--datastore`, `-ds`: Type of datastore to use (`vertex_ai_search`, `vertex_ai_vector_search`). Prompted if `--include-data-ingestion` is specified or if the selected agent requires data ingestion, and this option is omitted.
- `--region`: GCP region for deployment. Defaults to `us-central1`. Prompts for confirmation if not specified and `--auto-approve` is not used.

GCP account and project ID are detected automatically. You will be prompted to confirm or change them unless `--auto-approve` is used.

Additional options:
- `--include-data-ingestion`, `-i`: Include data ingestion pipeline components in the project. If specified without `--datastore`, you will be prompted to select a datastore. Some agents require data ingestion and will enable this automatically.
- `--debug`: Enable debug logging.
- `--output-dir`, `-o`: Output directory for the project (default: current directory).
- `--auto-approve`: Skip interactive confirmation prompts for GCP credentials and region.
- `--skip-checks`: Skip verification checks for `uv` installation, GCP authentication, and Vertex AI connection.

### Example Usage

```bash
# Create a new project interactively
agent-starter-pack create my-agent-project

# Create with specific agent, deployment target, region, and include data ingestion with Vertex AI Search
agent-starter-pack create my-agent-project -a agentic_rag -d cloud_run --region europe-west1 -i -ds vertex_ai_search

# Create without interactive prompts (uses detected GCP credentials)
agent-starter-pack create my-other-agent -a chat_agent -d agent_engine --auto-approve
```
