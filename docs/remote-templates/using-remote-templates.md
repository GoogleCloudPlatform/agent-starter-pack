# Using Remote Templates

Remote templates let you instantly create production-ready AI agents from Git repositories. Any Git repository can be used as a template - the system automatically handles fetching, configuration, and generating your complete agent project.

## How It Works

When you use a remote template, the system:

1. **Fetches** the template repository from Git
2. **Checks for version locking** - if the template specifies a starter pack version in `uv.lock`, automatically uses that version for guaranteed compatibility
3. **Applies intelligent defaults** based on repository structure
4. **Merges** template files with base agent infrastructure
5. **Generates** a complete, production-ready agent project

The file merging follows this priority order:
1. Base template files (foundation)
2. Deployment target files (Cloud Run, Agent Engine, etc.)
3. Frontend files (if specified)
4. Built-in agent files (adk, etc.)
5. **Remote template files (highest priority)**

## Quick Start

Using a remote template is simple - just provide any Git repository URL:

```bash
# Use any GitHub repository as a template
uvx agent-starter-pack create my-agent -a https://github.com/user/my-template

# Use shorthand notation
uvx agent-starter-pack create my-agent -a github.com/user/my-template@main

# Use official ADK samples
uvx agent-starter-pack create my-agent -a adk@gemini-fullstack

# Use your existing project
uvx agent-starter-pack create my-agent -a local@./path/to/project
```

The system automatically handles the rest - fetching the template, applying intelligent defaults, and generating your production-ready agent.

## Template URL Formats

### Full GitHub URLs
```bash
# Complete GitHub URL (copy from browser)
uvx agent-starter-pack create my-agent -a https://github.com/my-org/my-repo/tree/main/path-to-template
```

### Shorthand URLs
```bash
# GitHub shorthand
uvx agent-starter-pack create my-agent -a github.com/my-org/my-repo/path-to-template

# Specify branch or tag with @
uvx agent-starter-pack create my-agent -a github.com/my-org/my-repo/path-to-template@develop

# Works with GitLab, Bitbucket, etc.
uvx agent-starter-pack create my-agent -a gitlab.com/my-org/my-repo/template@v1.0
```

### ADK Samples Shortcut
A convenient alias for official Google agent examples from the [google/adk-samples](https://github.com/google/adk-samples) repository:

```bash
# Creates an agent from the 'gemini-fullstack' template in adk-samples
uvx agent-starter-pack create my-agent -a adk@gemini-fullstack

# Other popular ADK samples
uvx agent-starter-pack create my-agent -a adk@data-science
uvx agent-starter-pack create my-agent -a adk@chat-agent
```

### Your Existing Projects
```bash
# Use your existing project as source
uvx agent-starter-pack create my-test-agent -a local@./path/to/your/project
uvx agent-starter-pack create my-test-agent -a local@/absolute/path/to/project
```

## Advanced Usage

### In-Folder Creation
Create agent files directly in your current directory instead of creating a new subdirectory:

```bash
# Standard: creates ./my-agent/ directory
uvx agent-starter-pack create my-agent -a template-url

# In-folder: creates files in current directory
uvx agent-starter-pack create my-agent -a template-url --in-folder
```

See the [create CLI documentation](../cli/create.md) for complete details on the `--in-folder` flag.

### Enhancing Existing Projects
Use the `enhance` command to add agent capabilities to existing projects:

```bash
# Add agent functionality to current project
uvx agent-starter-pack enhance adk@gemini-fullstack
```

See the [enhance CLI documentation](../cli/enhance.md) for complete usage details.

### Template Options
All `create` command options work with remote templates:

```bash
# Specify deployment target
uvx agent-starter-pack create my-agent -a template-url --deployment-target cloud_run

# Include data ingestion
uvx agent-starter-pack create my-agent -a template-url --include-data-ingestion --datastore cloud_sql

# Custom session storage
uvx agent-starter-pack create my-agent -a template-url --session-type cloud_sql

# Override the base template
uvx agent-starter-pack create my-agent -a template-url --base-template adk_live

# Skip verification checks
uvx agent-starter-pack create my-agent -a template-url --skip-checks
```

### Overriding Base Templates

Remote templates can specify a base template in their `pyproject.toml` configuration. You can override this using the `--base-template` flag to use a different foundational agent:

```bash
# Use adk_a2a as the base instead of what the template specifies
uvx agent-starter-pack create my-agent -a adk@data-science --base-template adk_a2a

✓ Base template override: Using 'adk_a2a' as foundation
  This requires adding the following dependencies:
    • google-adk>=1.16.0,<2.0.0
    • a2a-sdk~=0.3.9

? Add these dependencies automatically? [Y/n] y

✓ Running: uv add 'google-adk>=1.16.0,<2.0.0' 'a2a-sdk~=0.3.9'
  Resolved 111 packages in 1.2s
✓ Dependencies added successfully
```

#### Interactive Dependency Management

When you override the base template, the CLI:
1. **Shows required dependencies** - Lists all dependencies needed by the new base template
2. **Prompts for confirmation** - Asks if you want to add them automatically
3. **Runs `uv add`** - Uses standard `uv` commands to add dependencies with proper version resolution
4. **Handles conflicts** - `uv` automatically resolves any version conflicts between remote template and base dependencies

**Skipping dependency installation:**
```bash
? Add these dependencies automatically? [Y/n] n

⚠️  Skipped dependency installation.
   To add them manually later, run:
       cd my-agent
       uv add 'google-adk>=1.16.0,<2.0.0' 'a2a-sdk~=0.3.9'
```

**Automatic installation with `--auto-approve`:**
```bash
uvx agent-starter-pack create my-agent -a template --base-template adk_a2a --auto-approve

✓ Base template override: Using 'adk_a2a' as foundation
✓ Auto-installing dependencies: google-adk>=1.16.0,<2.0.0, a2a-sdk~=0.3.9
  Resolved 111 packages in 1.2s
✓ Dependencies added successfully
```

#### Use Cases

Base template override is useful when:
- You want to use a remote template's logic with a different foundational agent
- The template's default base doesn't match your deployment needs (e.g., switching from Cloud Run to Agent Engine)
- You're experimenting with different base agents for the same custom logic
- You need features from a different base (e.g., A2A protocol support via `adk_a2a`)

## Discovering Templates

### List Available Templates

**Built-in agents:**
```bash
uvx agent-starter-pack list
```

**Official ADK samples:**
```bash
uvx agent-starter-pack list --adk
```

**Templates in a specific repository:**
```bash
uvx agent-starter-pack list --source https://github.com/my-org/my-templates
```

**Note:** Only templates with proper configuration appear in `list` results. Templates without explicit configuration still work but aren't discoverable via the `list` command.

### Browse ADK Samples Interactively
```bash
# Launch interactive browser for ADK samples
uvx agent-starter-pack create my-agent
# (Choose to browse ADK samples when prompted)
```

## Troubleshooting

### Common Issues

**"Remote template not found or access denied"**
- Verify the repository URL is correct and publicly accessible
- For private repositories, ensure you have proper Git credentials configured
- Try the full GitHub URL format: `https://github.com/user/repo`

**"Template generates but has missing dependencies"**
- The template may not have a proper `pyproject.toml` - contact the template author
- As a workaround, manually add missing dependencies to the generated project

**"Command fails with Git errors"**
- Ensure Git is installed and configured
- Check your internet connection
- For private repos, verify your SSH keys or access tokens

**"Generated project won't run"**
- Run `make install` in the generated project to install dependencies
- Check the project's README for specific setup instructions
- Ensure you have the required Python version (check `pyproject.toml`)

### Getting Help

If you encounter issues with a specific template:
1. Check the template's repository README for usage instructions
2. Look for issues or discussions in the template's repository
3. Contact the template author through the repository's issue tracker

For general Agent Starter Pack issues:
- Visit the [Agent Starter Pack repository](https://github.com/GoogleCloudPlatform/agent-starter-pack)
- Check the [troubleshooting guide](../guide/troubleshooting.md)

## Next Steps

- **Using templates**: Start with `adk@gemini-fullstack` for a full-featured example
- **Creating your own**: See [Creating Remote Templates](./creating-remote-templates.md)
- **CLI reference**: Explore all options in [create](../cli/create.md) and [enhance](../cli/enhance.md) commands