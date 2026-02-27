# upgrade

The `upgrade` command updates your project to the latest version of agent-starter-pack using an intelligent 3-way merge. It automatically applies updates to scaffolding files while preserving your customizations.

## Usage

```bash
uvx agent-starter-pack upgrade [PROJECT_PATH] [OPTIONS]
```

## Arguments

- `PROJECT_PATH` (optional): Path to the project to upgrade (default: current directory)

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--dry-run` | `false` | Preview changes without applying them |
| `--auto-approve, -y` | `false` | Auto-apply non-conflicting changes without prompts |
| `--debug` | `false` | Enable debug logging |

## Examples

### Basic Upgrade

```bash
# Upgrade current project
uvx agent-starter-pack upgrade

# Upgrade a specific project
uvx agent-starter-pack upgrade /path/to/project
```

### Preview Changes

```bash
# See what would change without applying
uvx agent-starter-pack upgrade --dry-run
```

### Non-Interactive Upgrade

```bash
# Auto-approve all non-conflicting changes
uvx agent-starter-pack upgrade -y
```

## How the 3-Way Merge Works

The upgrade command uses a 3-way comparison between:
1. **Your current project** - The files as they exist now
2. **Old ASP template** - What ASP generated at your project's version
3. **New ASP template** - What ASP generates at the latest version

This enables intelligent decision-making:

| Your Changes | ASP Changes | Result |
|--------------|-------------|--------|
| None | Updated | **Auto-update** - Apply ASP's changes |
| Modified | None | **Preserve** - Keep your changes |
| Modified | Updated | **Conflict** - Prompt for resolution |
| N/A | New file | **Add** - Prompt to add new file |
| N/A | Removed | **Remove** - Prompt to remove file |

### Files Always Preserved

The following are never modified by upgrade:
- **Agent code** (e.g., `app/agent.py`, custom modules)
- **Configuration files** (`.env`, secrets, local configs)

### Conflict Resolution

When both you and ASP have modified a file, you'll be prompted:
- **(v)iew diff** - See the differences between versions
- **(k)eep yours** - Preserve your current version
- **(u)se new** - Replace with ASP's new version
- **(s)kip** - Don't change the file

## Dependency Handling

### Python Projects

The upgrade command intelligently merges dependencies in `pyproject.toml`:

- **ASP dependencies updated** → Automatically update version
- **Your custom dependencies** → Preserved unchanged
- **New ASP dependencies** → Added to your project
- **Removed ASP dependencies** → Optionally removed

Version constraints are respected, and your custom additions are never removed.

### Go Projects

For Go projects, dependencies in `go.mod` and `go.sum` are categorized as project dependencies and handled during 3-way comparison. The upgrade command does not perform automatic dependency merging for Go projects - Go's module system handles this natively.

## Language Support

The upgrade command supports both Python and Go projects:

| Language | Config File | Version Key | Dependency Handling |
|----------|-------------|-------------|---------------------|
| Python | `pyproject.toml` | `asp_version` | Automatic merge |
| Go | `.asp.toml` | `version` | 3-way compare |

Language is auto-detected from project files.

## Requirements

- **uvx**: Required for re-generating templates at specific versions
- **Project metadata**:
  - Python: `pyproject.toml` must have `[tool.agent-starter-pack]` with `asp_version`
  - Go: `.asp.toml` must have `[project]` with `version`

## How It Works

1. **Reads project metadata** to determine current ASP version
2. **Re-generates old template** using `uvx agent-starter-pack@{old_version}`
3. **Re-generates new template** using current ASP version
4. **Compares all files** using 3-way diff
5. **Applies changes** based on comparison results
6. **Updates metadata** to reflect new version

## Example Workflow

```bash
# Check current version in pyproject.toml
grep asp_version pyproject.toml
# asp_version = "0.30.0"

# Preview what would change
uvx agent-starter-pack upgrade --dry-run

# Output shows:
# Auto-updating (unchanged by you):
#   ✓ deployment/terraform/main.tf
#   ✓ .github/workflows/ci.yaml
#
# Preserving (you modified, ASP unchanged):
#   ✓ Makefile
#
# Conflicts (both changed):
#   ⚠ deployment/terraform/variables.tf

# Apply the upgrade
uvx agent-starter-pack upgrade

# Resolve any conflicts interactively
# ...

# Verify upgrade
grep asp_version pyproject.toml
# asp_version = "0.31.0"
```

## Best Practices

1. **Commit before upgrading** - Ensure you can easily revert if needed
2. **Use dry-run first** - Preview changes before applying
3. **Review conflicts carefully** - Don't blindly accept new versions
4. **Test after upgrade** - Run `make test` to verify everything works
5. **Check dependency changes** - Review any updated package versions

## Troubleshooting

**"No agent-starter-pack metadata found"**
- Python: Ensure `pyproject.toml` has `[tool.agent-starter-pack]` section
- Go: Ensure `.asp.toml` has `[project]` section
- This project may not have been created with agent-starter-pack

**"No asp_version found"**
- Python: Add `asp_version = "X.Y.Z"` to `[tool.agent-starter-pack]` in `pyproject.toml`
- Go: Add `version = "X.Y.Z"` to `[project]` in `.asp.toml`
- Use the version you originally created the project with

**"Failed to generate old template"**
- The old version may not be available on PyPI
- Try upgrading from a more recent version

**"uvx is required but not installed"**
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
