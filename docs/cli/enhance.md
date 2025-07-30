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
  - Agent name - Use a built-in agent (e.g., `adk_base`)
  - Remote template - Use a remote template (e.g., `adk@gemini-fullstack`)

## Options

The `enhance` command supports all the same options as [`create`](./create.md), plus:

### `--base-template` TEMPLATE
Override the base template for inheritance when enhancing your existing project. Available base templates include:
- `adk_base` - Basic agent template (default)
- `langgraph_base_react` - LangGraph-based ReAct agent
- `agentic_rag` - RAG-enabled agent template

### Other Options
- `--name, -n` - Project name (defaults to current directory name)
- `--deployment-target, -d` - Deployment target (`agent_engine`, `cloud_run`)
- `--include-data-ingestion, -i` - Include data ingestion pipeline
- `--session-type` - Session storage type
- `--auto-approve` - Skip confirmation prompts
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
# Enhance with specific deployment target
uvx agent-starter-pack enhance adk@data-science --deployment-target cloud_run

# Enhance with data ingestion capabilities
uvx agent-starter-pack enhance --include-data-ingestion --datastore alloydb

# Enhance with custom session storage
uvx agent-starter-pack enhance --session-type alloydb
```

### Base Template Inheritance

```bash
# Enhance current project with LangGraph capabilities
uvx agent-starter-pack enhance . --base-template langgraph_base_react

# Enhance with RAG-enabled base template
uvx agent-starter-pack enhance . --base-template agentic_rag
```

## Project Structure Validation

The enhance command validates your project structure and provides guidance:

**✅ Ideal Structure:**
```
your-project/
├── app/
│   └── agent.py    # Your agent code
├── tests/
└── README.md
```

**⚠️ Missing /app Folder:**
If your project doesn't have an `/app` folder, the command will:
1. Display a warning about project structure
2. Explain the expected structure
3. Ask for confirmation to proceed (unless `--auto-approve` is used)

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

### Base Template Inheritance

When enhancing your existing project (using `local@.` or `local@/path/to/project`), the enhance command will:

1. **Show current inheritance**: Display which base template your project inherits from
2. **Provide guidance**: Show available alternative base templates and how to use them
3. **Support CLI override**: Use `--base-template` to override the base template specified in `pyproject.toml`

The inheritance hierarchy works as follows:
```
Your Existing Project
    ↓ (inherits from)
Base Template (adk_base, langgraph_base_react, etc.)
    ↓ (provides)
Core Infrastructure & Capabilities
```

## Use Cases

**Prototype to Production:**
```bash
# You have a prototype agent in /app/agent.py
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
uvx agent-starter-pack enhance --include-data-ingestion --datastore alloydb
```

**Upgrade Agent Base:**
```bash
# Upgrade from basic to advanced agent template
uvx agent-starter-pack enhance adk@gemini-fullstack

# Or change base template inheritance
uvx agent-starter-pack enhance . --base-template langgraph_base_react
```

## Automatic Backup

The `enhance` command automatically creates a complete backup of your project before making any changes:

- **Location:** `.backup_[dirname]_[timestamp]` in the parent directory
- **Contents:** Complete copy of your entire project directory
- **Timing:** Created before any template files are applied

## Best Practices

1. **Review Backup:** Check that the backup was created successfully
2. **Follow Structure:** Organize your agent code in `/app/agent.py` for best compatibility  
3. **Test Locally:** Use `--auto-approve` in CI/CD but test interactively first
4. **Review Changes:** After enhancement, review the generated files and configuration

## Troubleshooting

**"Project structure warning"**
- Organize your agent code in an `/app` folder
- Use `--auto-approve` to skip the confirmation prompt

**"Enhancement cancelled"**
- Create an `/app` folder with your `agent.py` file
- Re-run the command

**"Dependency conflicts"**
- Review and resolve conflicts in your `pyproject.toml`
- Consider using a virtual environment