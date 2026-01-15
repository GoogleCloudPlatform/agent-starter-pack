# create

Create new GCP-based AI agent projects from built-in agents or remote templates.

## Usage

```bash
uvx agent-starter-pack create [PROJECT_NAME] [OPTIONS]
```

## Arguments

- `PROJECT_NAME` (optional): Name for your new agent project directory and base for resource naming.
  If omitted, you'll be prompted interactively (or defaults to `my-agent` with `--auto-approve`).
  *Note: This name will be converted to lowercase and must be 26 characters or less.*

## Template Selection

### `--agent`, `-a` TEMPLATE
Specify which template to use for your agent:

**Built-in agents:**
```bash
uvx agent-starter-pack create my-agent -a adk
uvx agent-starter-pack create my-agent -a chat_agent
```

**Remote templates:**
```bash
# Full GitHub URL
uvx agent-starter-pack create my-agent -a https://github.com/user/repo

# Shorthand notation  
uvx agent-starter-pack create my-agent -a github.com/user/repo@main

# ADK samples shortcut
uvx agent-starter-pack create my-agent -a adk@gemini-fullstack

# Use your existing project as source
uvx agent-starter-pack create my-agent -a local@./path/to/project
```

If omitted, you'll see an interactive list of available agents.

## Deployment Options

### `--deployment-target`, `-d` TARGET
Deployment target for your agent:
- `cloud_run` - Deploy to Google Cloud Run
- `agent_engine` - Deploy to Google Cloud Agent Engine

### `--cicd-runner` RUNNER
CI/CD runner to use:
- `google_cloud_build` - Use Google Cloud Build
- `github_actions` - Use GitHub Actions
- `skip` - No CI/CD (minimal project, same as `--prototype`)

### `--prototype`, `-p`
Create a minimal project without CI/CD or Terraform infrastructure. Ideal for:
- Quick prototyping and experimentation
- Learning and tutorials
- Teams with custom deployment pipelines

**What gets skipped:**
- `.github/workflows/` or `.cloudbuild/`
- `deployment/` (Terraform)
- `tests/load_test/`
- Makefile `setup-dev-env` target

**Upgrade path:** Run `uvx agent-starter-pack enhance` later to add CI/CD scaffolding.

### `--region` REGION
GCP region for deployment (default: `us-central1`)

## Data & Storage Options

### `--include-data-ingestion`, `-i`
Include data ingestion pipeline components in the project.

### `--datastore`, `-ds` DATASTORE
Type of datastore for data ingestion (requires `--include-data-ingestion`):
- `vertex_ai_search`
- `vertex_ai_vector_search` 
- `vertex_ai_vector_search` 
- `cloud_sql`

### `--session-type` TYPE
Session storage type (for Cloud Run deployment):
- `in_memory` - Store sessions in memory
- `cloud_sql` - Store sessions in Cloud SQL (PostgreSQL)
- `agent_engine` - Use Agent Engine session management

## Project Creation Options

### `--output-dir`, `-o` DIRECTORY
Output directory for the project (default: current directory)

### `--agent-directory`, `-dir` DIRECTORY
Name of the agent directory (overrides template default, usually `app`). This determines where your agent code files will be located within the project structure.

### `--base-template`, `-bt` TEMPLATE
Override the base template specified in a remote template's configuration. Only applicable when using remote templates with the `--agent` flag. This allows you to use a different built-in agent as the foundation instead of the one specified in the remote template's `pyproject.toml`.

**Interactive dependency management:**
When overriding the base template, you'll be prompted to add required dependencies using `uv add`:

```bash
# Use adk_a2a as base instead of the remote template's default
uvx agent-starter-pack create my-agent -a github.com/user/template --base-template adk_a2a

✓ Base template override: Using 'adk_a2a' as foundation
  This requires adding the following dependencies:
    • google-adk>=1.16.0,<2.0.0
    • a2a-sdk~=0.3.9

? Add these dependencies automatically? [Y/n]
```

With `--auto-approve`, dependencies are added automatically without prompting:
```bash
uvx agent-starter-pack create my-agent -a template --base-template adk_a2a --auto-approve
# Dependencies are added automatically
```

### `--in-folder`
Create agent files directly in the current directory instead of creating a new project subdirectory.

**Standard behavior:**
```bash
uvx agent-starter-pack create my-agent -a template
# Creates: ./my-agent/[project files]
```

**In-folder behavior:**
```bash  
uvx agent-starter-pack create my-agent -a template --in-folder
# Creates: ./[project files] (in current directory)
```

**Use cases:**
- Adding agent capabilities to existing projects
- Working within established repository structures
- Containerized development environments

**Automatic Backup:** When using `--in-folder`, a complete backup of your directory is automatically created as `.backup_[dirname]_[timestamp]` before any changes are made.

## Automation Options

### `--auto-approve`, `--yes`, `-y`
Skip interactive confirmation prompts and use sensible defaults:
- Project name defaults to `my-agent`
- Agent defaults to first available (typically `adk`)
- Deployment target defaults to `agent_engine`
- CI/CD runner defaults to `google_cloud_build`

### `--google-api-key`, `--api-key`, `-k` [KEY]
Use Google AI Studio API key instead of Vertex AI. If provided without a value, generates a `.env` file with a `YOUR_API_KEY` placeholder.

### `--skip-checks`
Skip verification checks for GCP authentication and Vertex AI connection.

### `--debug`
Enable debug logging for troubleshooting.

## Examples

### Quick Start

```bash
# Create with all defaults (project: my-agent, agent: adk, target: agent_engine)
uvx agent-starter-pack create -y

# Fully interactive mode
uvx agent-starter-pack create

# Quick prototype (no CI/CD, no Terraform)
uvx agent-starter-pack create my-prototype -p -d agent_engine
```

### Basic Usage

```bash
# Create a new project with specific name
uvx agent-starter-pack create my-agent-project

# Create with specific built-in agent (Python)
uvx agent-starter-pack create my-agent -a adk -d cloud_run

# Create a Go agent (Cloud Run only)
uvx agent-starter-pack create my-go-agent -a adk_go
```

### Remote Templates

```bash
# Use ADK samples
uvx agent-starter-pack create my-agent -a adk@gemini-fullstack

# Use GitHub repository
uvx agent-starter-pack create my-agent -a https://github.com/user/my-template

# Use shorthand notation with branch
uvx agent-starter-pack create my-agent -a github.com/user/template@develop

# Use your existing project
uvx agent-starter-pack create my-agent -a local@./my-project

# Override the base template of a remote template
uvx agent-starter-pack create my-agent -a adk@data-science --base-template adk_live
```

### Advanced Configuration

```bash
# Include data ingestion with specific datastore
uvx agent-starter-pack create my-rag-agent -a adk -i -ds cloud_sql -d cloud_run

# Create with custom region and CI/CD
uvx agent-starter-pack create my-agent -a template-url --region europe-west1 --cicd-runner github_actions

# In-folder creation (add to existing project)
uvx agent-starter-pack create my-agent -a adk@data-science --in-folder

# Customize agent directory name
uvx agent-starter-pack create my-agent -a adk --agent-directory chatbot

# Skip all prompts for automation
uvx agent-starter-pack create my-agent -a template-url -y --skip-checks
```

### Output Directory

```bash
# Create in specific directory
uvx agent-starter-pack create my-agent -o ./projects/

# Create in current directory with in-folder
uvx agent-starter-pack create existing-project -a template-url --in-folder
```

## Related Commands

- [`enhance`](./enhance.md) - Add agent capabilities to existing projects (automatically uses `--in-folder`)
- [`list`](./list.md) - List available templates and agents

## See Also

- [Using Remote Templates](../remote-templates/using-remote-templates.md) - Complete guide for using remote templates
- [Creating Remote Templates](../remote-templates/creating-remote-templates.md) - Guide for creating your own templates
