# extract

The `extract` command creates a minimal, shareable version of your agent by stripping away deployment infrastructure while preserving your core agent logic. This is useful for sharing agents, creating starter templates, or distributing agent code without the full project scaffolding.

## Usage

```bash
uvx agent-starter-pack extract OUTPUT_PATH [OPTIONS]
```

## Arguments

- `OUTPUT_PATH` (required): Path where the extracted agent will be created

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--source, -s` | `.` (current directory) | Source project directory |
| `--dry-run` | `false` | Show what would be extracted without making changes |
| `--force, -f` | `false` | Overwrite output directory if it exists |
| `--debug` | `false` | Enable debug logging |

## Examples

### Basic Extraction

```bash
# Extract current project to a new directory
uvx agent-starter-pack extract ../my-agent-share

# Extract from a specific source directory
uvx agent-starter-pack extract ./shared-agent --source /path/to/project
```

### Preview Changes

```bash
# See what would be extracted without making changes
uvx agent-starter-pack extract ../my-agent-share --dry-run
```

### Overwrite Existing

```bash
# Force overwrite if output directory exists
uvx agent-starter-pack extract ../my-agent-share --force
```

## What Gets Extracted

The extract command preserves your core agent code while removing deployment scaffolding:

**Kept (Agent Code):**
- Agent directory (e.g., `app/`) with your `agent.py` and custom modules
- `pyproject.toml` (with scaffolding dependencies removed)
- `.gitignore`
- `GEMINI.md` (if present)

**Removed (Scaffolding):**
- `deployment/` - Terraform infrastructure
- `.github/` or `.cloudbuild/` - CI/CD pipelines
- `frontend/` - UI components
- `data_ingestion/` - Data pipeline code
- `notebooks/` - Jupyter notebooks
- `tests/` - Test files
- `tools/` - Build tools
- Scaffolding files in agent directory (`fast_api_app.py`, `agent_engine_app.py`, `app_utils/`)

**Generated:**
- Minimal `Makefile` with basic commands (`install`, `playground`, `lint`)
- Simplified `README.md` for the extracted project

## How It Works

1. **Detects project language** (Python or Go) from project files
2. **Reads ASP metadata** from `pyproject.toml` or `.asp.toml`
3. **Copies agent code** excluding scaffolding files
4. **Strips scaffolding dependencies** from `pyproject.toml`
5. **Generates minimal Makefile and README** for standalone use
6. **Regenerates lock file** (`uv lock` or `go mod tidy`)

## Relationship to `enhance`

The `extract` and `enhance` commands are complementary:

```
Full Project ──extract──> Minimal Agent ──enhance──> Full Project
```

- **extract**: Remove scaffolding to create a shareable, minimal agent
- **enhance**: Add scaffolding back to restore production capabilities

This workflow enables:
1. **Sharing**: Extract your agent, share it with others
2. **Receiving**: Others run `enhance` to add their own deployment infrastructure
3. **Customization**: Recipients can choose different deployment targets, CI/CD runners, etc.

## Example Workflow

```bash
# 1. Create a full project
uvx agent-starter-pack create my-agent -a adk -d cloud_run

# 2. Develop your agent...
cd my-agent
# ... edit app/agent.py ...

# 3. Extract for sharing
uvx agent-starter-pack extract ../my-agent-share

# 4. Share the extracted agent (e.g., push to GitHub)
cd ../my-agent-share
git init && git add . && git commit -m "Initial agent"

# 5. Recipients can enhance with their own preferences
uvx agent-starter-pack enhance --deployment-target agent_engine
```

## Language Support

The extract command supports both Python and Go projects:

| Language | Config File | Lock Command |
|----------|-------------|--------------|
| Python | `pyproject.toml` | `uv lock` |
| Go | `.asp.toml` | `go mod tidy` |

Language is auto-detected from project files.
