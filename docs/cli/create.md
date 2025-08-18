# create

Create new GCP-based AI agent projects from built-in agents or remote templates.

## Usage

```bash
uvx agent-starter-pack create PROJECT_NAME [OPTIONS]
```

## Arguments

- `PROJECT_NAME`: Name for your new agent project directory and base for resource naming.
  *Note: This name will be converted to lowercase and must be 26 characters or less.*

## Template Selection

### `--agent`, `-a` TEMPLATE
Specify which template to use for your agent:

**Built-in agents:**
```bash
uvx agent-starter-pack create my-agent -a adk_base
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

### `--region` REGION
GCP region for deployment (default: `us-central1`)

## Data & Storage Options

### `--include-data-ingestion`, `-i`
Include data ingestion pipeline components in the project.

### `--datastore`, `-ds` DATASTORE
Type of datastore for data ingestion (requires `--include-data-ingestion`):
- `vertex_ai_search`
- `vertex_ai_vector_search` 
- `alloydb`

### `--session-type` TYPE
Session storage type (for Cloud Run deployment):
- `in_memory` - Store sessions in memory
- `alloydb` - Store sessions in AlloyDB
- `agent_engine` - Use Agent Engine session management

## Project Creation Options

### `--output-dir`, `-o` DIRECTORY
Output directory for the project (default: current directory)

### `--agent-directory`, `-dir` DIRECTORY
Name of the agent directory (overrides template default, usually `app`). This determines where your agent code files will be located within the project structure.

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

### `--auto-approve`
Skip interactive confirmation prompts for GCP credentials and region.

### `--skip-checks`
Skip verification checks for GCP authentication and Vertex AI connection.

### `--debug`
Enable debug logging for troubleshooting.

## Examples

### Basic Usage

```bash
# Create a new project interactively
uvx agent-starter-pack create my-agent-project

# Create with specific built-in agent
uvx agent-starter-pack create my-agent -a adk_base -d cloud_run
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
```

### Advanced Configuration

```bash
# Include data ingestion with specific datastore
uvx agent-starter-pack create my-rag-agent -a adk_base -i -ds alloydb -d cloud_run

# Create with custom region and CI/CD
uvx agent-starter-pack create my-agent -a template-url --region europe-west1 --cicd-runner github_actions

# In-folder creation (add to existing project)
uvx agent-starter-pack create my-agent -a adk@data-science --in-folder

# Customize agent directory name
uvx agent-starter-pack create my-agent -a adk_base --agent-directory chatbot

# Skip all prompts for automation
uvx agent-starter-pack create my-agent -a template-url --auto-approve --skip-checks
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
