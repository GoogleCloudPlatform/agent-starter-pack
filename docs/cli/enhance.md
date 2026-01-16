# enhance

The `enhance` command adds agent-starter-pack capabilities to existing projects without creating a new directory. It's designed for upgrading prototypes to production-ready agents in-place.

## Usage

```bash
uvx agent-starter-pack enhance [TEMPLATE_PATH] [OPTIONS]
```

## Arguments

- `TEMPLATE_PATH` (optional): Can be:
  - `.` (default) - Use current directory as template
  - Local directory path - Use another local directory as template  
  - Agent name - Use a built-in agent (e.g., `adk`)
  - Remote template - Use a remote template (e.g., `adk@gemini-fullstack`)

## Options

The `enhance` command supports all the same options as [`create`](./create.md), including `--agent-directory`, `--deployment-target`, `--include-data-ingestion`, etc., plus enhance-specific options:

### Enhance-Specific Options

#### `--base-template` TEMPLATE
Override the base template for inheritance when enhancing your existing project. Available base templates include:
- `adk` - Basic agent template (default)
- `langgraph` - LangGraph-based ReAct agent
- `agentic_rag` - RAG-enabled agent template

### Key Shared Options

#### `--agent-directory`, `-dir` DIRECTORY
Name of the agent directory (overrides template default, usually `app`). This determines where your agent code files will be located within the project structure.

**Auto-detection:** When not specified, the enhance command attempts to auto-detect your agent directory from your `pyproject.toml` file by examining the `tool.hatch.build.targets.wheel.packages` configuration.

### Other Shared Options
- `--name, -n` - Project name (defaults to current directory name)
- `--deployment-target, -d` - Deployment target (`agent_engine`, `cloud_run`)
- `--include-data-ingestion, -i` - Include data ingestion pipeline
- `--session-type` - Session storage type
- `--google-api-key, --api-key, -k` - Use Google AI Studio API key (or placeholder if no value provided)
- `--auto-approve, --yes, -y` - Skip confirmation prompts and use defaults
- And all other `create` command options

## Examples

### Basic Enhancement

```bash
# Enhance current project with default template
uvx agent-starter-pack enhance

# Enhance with a specific agent template
uvx agent-starter-pack enhance adk@gemini-fullstack

# Enhance with custom project name
uvx agent-starter-pack enhance --name my-enhanced-agent
```

### Advanced Options

```bash
# Enhance with custom agent directory
uvx agent-starter-pack enhance . --agent-directory chatbot

# Enhance with specific deployment target
uvx agent-starter-pack enhance adk@data-science --deployment-target cloud_run

# Enhance with data ingestion capabilities
uvx agent-starter-pack enhance --include-data-ingestion --datastore cloud_sql

# Enhance with custom session storage
uvx agent-starter-pack enhance --session-type cloud_sql
```

### Base Template Inheritance

```bash
# Enhance current project with LangGraph capabilities
uvx agent-starter-pack enhance . --base-template langgraph

# Enhance with RAG-enabled base template
uvx agent-starter-pack enhance . --base-template agentic_rag
```

## Project Structure Validation

The enhance command validates your project structure and provides guidance:

**✅ Ideal Structure:**
```
your-project/
├── app/
│   └── agent.py         # Python agent with root_agent
│   └── root_agent.yaml  # OR YAML config agent (auto-detected)
├── tests/
└── README.md
```

**Note:** YAML config agents (`root_agent.yaml`) are automatically detected. An `agent.py` shim is generated to load the YAML config for deployment compatibility.

**⚠️ Missing Agent Folder:**
If your project doesn't have an agent directory (default: `/app`), the command will:
1. Display a warning about project structure
2. Explain the expected structure
3. Ask for confirmation to proceed (unless `--auto-approve` is used)

**💡 Custom Agent Directory:**
Use `--agent-directory` to specify a different directory name if your agent code is organized differently:
```bash
uvx agent-starter-pack enhance . --agent-directory my_agent
```

## How It Works

The `enhance` command is essentially an alias for:
```bash
uvx agent-starter-pack create PROJECT_NAME --agent TEMPLATE --in-folder
```

It automatically:
- Uses the current directory name as the project name (unless `--name` is specified)
- Enables `--in-folder` mode to template directly into the current directory
- Validates the project structure for compatibility
- Applies the same file merging logic as the `create` command

### Version Locking

When enhancing a project that was created with agent-starter-pack, the command automatically uses the same version that generated the project:

1. Reads `asp_version` from `[tool.agent-starter-pack]` in `pyproject.toml`
2. If the version differs from the current CLI, re-executes with the locked version via `uvx agent-starter-pack@{version}`
3. Uses stored `create_params` to ensure identical configuration

This ensures compatibility and consistent behavior when adding features to existing projects.

**Skip version lock:** Set `ASP_SKIP_VERSION_LOCK=1` to use the current CLI version instead.

### Base Template Inheritance

When enhancing your existing project (using `local@.` or `local@/path/to/project`), the enhance command will:

1. **Show current inheritance**: Display which base template your project inherits from
2. **Provide guidance**: Show available alternative base templates and how to use them
3. **Support CLI override**: Use `--base-template` to override the base template specified in `pyproject.toml`

The inheritance hierarchy works as follows:
```
Your Existing Project
    ↓ (inherits from)
Base Template (adk, langgraph, etc.)
    ↓ (provides)
Core Infrastructure & Capabilities
```

## Use Cases

**Prototype to Production:**
```bash
# Created with --prototype, now ready to add CI/CD
uvx agent-starter-pack enhance --cicd-runner google_cloud_build

# Or add a specific template
uvx agent-starter-pack enhance adk@production-ready
```

**Add Infrastructure:**
```bash
# Add Terraform and deployment capabilities
uvx agent-starter-pack enhance --deployment-target cloud_run
```

**Add Data Pipeline:**
```bash
# Add data ingestion to existing agent
uvx agent-starter-pack enhance --include-data-ingestion --datastore cloud_sql
```

**Upgrade Agent Base:**
```bash
# Upgrade from basic to advanced agent template
uvx agent-starter-pack enhance adk@gemini-fullstack

# Or change base template inheritance
uvx agent-starter-pack enhance . --base-template langgraph
```

## Automatic Backup

The `enhance` command automatically creates a complete backup of your project before making any changes:

- **Location:** `.backup_[dirname]_[timestamp]` in the parent directory
- **Contents:** Complete copy of your entire project directory
- **Timing:** Created before any template files are applied

## Best Practices

1. **Review Backup:** Check that the backup was created successfully
2. **Follow Structure:** Organize your agent code in `/app/agent.py` for best compatibility
3. **Test Locally:** Use `-y` in CI/CD but test interactively first
4. **Review Changes:** After enhancement, review the generated files and configuration

## Troubleshooting

**"Project structure warning"**
- Organize your agent code in an `/app` folder (or specify custom directory with `--agent-directory`)
- Use `-y` to skip the confirmation prompt

**"Enhancement cancelled"**
- Create an `/app` folder with your `agent.py` file
- Re-run the command

**"Dependency conflicts"**
- Review and resolve conflicts in your `pyproject.toml`
- Consider using a virtual environment