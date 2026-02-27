# Creating Remote Templates

This guide is for developers who want to create and share their own remote templates. Remote templates let you package your custom agent logic, dependencies, and infrastructure definitions into a reusable Git repository that others can use to generate production-ready agents.

## Requirements for Template Creators

When creating a remote template, you need to consider:

### Dependencies (`pyproject.toml`)
**Required for custom dependencies:** If your agent has custom Python dependencies, you **must** include a `pyproject.toml` file at the template root with those dependencies listed.

For guidance on the structure and content of your `pyproject.toml`, you can reference the [base template pyproject.toml](https://github.com/GoogleCloudPlatform/agent-starter-pack/blob/main/agent-starter-pack/base_template/pyproject.toml) as an example of the expected format and common dependencies.

### Configuration (`[tool.agent-starter-pack]`)
**Optional but recommended:** Add this section to your `pyproject.toml` for:
- **Discoverability:** Templates with this section appear in `uvx agent-starter-pack list` commands
- **Customization:** Override default behaviors like base template, deployment targets, etc.
- **Metadata:** Provide clear name and description for your template

### Smart Defaults
Templates work even without explicit configuration thanks to intelligent defaults based on your repository structure.

## Quick Start: Creating Your First Template

Let's build a simple remote template that customizes the built-in `adk` agent.

### Step 1: Create the Template Structure

A remote template mirrors a standard agent codebase:

```
my-first-remote-template/
├── pyproject.toml           # Dependencies and configuration
├── app/
│   └── agent.py             # Your custom agent logic
└── README.md                # Template documentation
```

### Step 2: Configure Dependencies and Settings

Create a `pyproject.toml` file:

```toml
[project]
name = "my-first-remote-template"
version = "0.1.0"
description = "A simple template that says hello"
dependencies = [
    "google-adk>=1.8.0",
]

[tool.agent-starter-pack]
# The built-in agent to use as a foundation
base_template = "adk"

# Template metadata (optional - falls back to [project] section)
name = "My First Remote Template"
description = "A simple template that demonstrates custom greetings"

# Override settings from the base template
[tool.agent-starter-pack.settings]
# This template will only support the 'agent_engine' deployment target
deployment_targets = ["agent_engine"]
# Optional: Customize the directory name for agent files (default: "app")
agent_directory = "app"

```

### Step 3: Create Your Custom Agent Logic

Create your custom agent logic in `app/agent.py`:

```python
from google.adk.agents import Agent

def get_greeting(name: str = "World") -> str:
    """Returns a friendly greeting from the remote template."""
    return f"Hello, {name}! This greeting comes from a remote template."

root_agent = Agent(
    name="root_agent",
    model="gemini-3-flash-preview",
    instruction="You are a helpful AI assistant. Use your tools to answer questions.",
    tools=[get_greeting],
)
```

### Step 4: Test Locally

Test your template locally before publishing:

```bash
# Run from the parent directory of 'my-first-remote-template'
uvx agent-starter-pack create my-test-agent -a local@./my-first-remote-template
```

### Step 5: Publish and Share

Initialize a Git repository and push to GitHub:

```bash
cd my-first-remote-template
git init
git add .
git commit -m "Initial remote template"
git remote add origin https://github.com/your-username/my-first-remote-template
git push -u origin main
```

Now anyone can use your template:
```bash
uvx agent-starter-pack create my-remote-agent -a https://github.com/your-username/my-first-remote-template
```

## Template Structure Details

### Required Files

**pyproject.toml (Required for custom dependencies):**
- Must be at the root of your repository
- Defines your agent's Python dependencies  
- Contains optional `[tool.agent-starter-pack]` configuration

### Recommended Structure

```
my-awesome-template/
├── pyproject.toml           # Dependencies and configuration
├── uv.lock                  # (Recommended) Locked dependencies  
├── app/
│   └── agent.py             # Your custom agent logic
├── tests/
│   └── test_agent.py        # Your custom tests
├── deployment/
│   └── terraform/
│       └── custom.tf        # Custom infrastructure
└── README.md                # Template documentation
```

### Configuration Format

```toml
[project]
name = "my-awesome-template"
description = "An awesome AI agent template"
dependencies = ["google-adk>=1.8.0", "custom-lib"]

[tool.agent-starter-pack]
# Base template to inherit from - users can override with --base-template flag
base_template = "adk"
name = "My Awesome Template"  # Optional: falls back to [project].name
description = "Custom description"  # Optional: falls back to [project].description

# Optional: Skill-ready metadata for intent routing and future skill generation
skill_triggers = [
  "build a customer support assistant",
  "create a tool-using chatbot",
]
skill_workflow = [
  "Define tools and model instruction",
  "Wire agent runtime and local entrypoints",
  "Test and package for deployment",
]
skill_inputs = ["User prompts", "Required API credentials"]
skill_outputs = ["Structured agent responses"]
skill_constraints = ["Requires API key configuration"]
skill_references = ["docs/architecture.md", "notebooks/evaluation.ipynb"]

[tool.agent-starter-pack.settings]
deployment_targets = ["cloud_run", "agent_engine"]
frontend_type = "None"
# Optional: Customize the directory name for agent files (default: "app")
agent_directory = "app"
```

**Note:** Users can override the `base_template` when creating from your template using `--base-template`. When they do, the CLI will automatically prompt them to add any additional dependencies required by the new base template using `uv add`.

## Configuration Reference

### Configuration Fallback Behavior

The system intelligently falls back between configuration sources:

1. **`[tool.agent-starter-pack]` section** (highest priority)
2. **`[project]` section** (fallback for `name` and `description`)  
3. **Smart defaults** (based on repository structure)

**Example with fallbacks:**
```toml
[project]
name = "my-agent-template"
description = "A template for building chatbots"

# This section is optional - without it, falls back to [project] + defaults
[tool.agent-starter-pack]
base_template = "adk"  # Override default
# name and description will use [project] values
```

### Skill Metadata Fields (Optional)

Remote template authors can include optional skill metadata under `[tool.agent-starter-pack]`:

- `skill_triggers`: list of user intents/phrases that should map to this template.
- `skill_workflow`: ordered high-level steps for using or implementing the template.
- `skill_inputs`: expected inputs (prompts, files, credentials, etc.).
- `skill_outputs`: expected outputs/artifacts.
- `skill_constraints`: guardrails, prerequisites, or known limitations.
- `skill_references`: paths to supporting docs, notebooks, or specs.

Validation rules:

- Every skill field is optional.
- If present, each field must be a list of strings.
- Malformed values produce clear CLI validation errors (for invalid type) and warnings (for suspicious but parseable values like empty lists).

### Agent Directory Configuration

By default, agent files are expected to be in an `app/` directory. You can customize this using the `agent_directory` setting:

```toml
[tool.agent-starter-pack.settings]
agent_directory = "my_agent"  # Custom directory name
```

This is useful when:
- You want to use a different directory name for consistency with your project structure
- You're creating specialized templates with domain-specific naming (e.g., `chatbot/`, `assistant/`, `agent/`)
- You need to avoid conflicts with existing codebases that use `app/` for other purposes

**Important:** When using a custom `agent_directory`, ensure your Python imports and Docker configurations match the new directory name.

For complete configuration options, see the [Template Config Reference](../guide/template-config-reference.md).


## How File Merging Works

When someone uses your template, files are copied and overlaid in this order (later steps overwrite earlier ones):

1. **Base Template Files**: The foundational files from the starter pack
2. **Deployment Target Files**: Files for the chosen deployment target (e.g., `cloud_run`)
3. **Frontend Files** (Optional): If a `frontend_type` is specified
4. **Base Agent Files**: The application logic from the `base_template` (e.g., `adk`)
5. **Remote Template Files** (Highest Precedence): All files from your repository root

This means your template files will override any conflicting files from the base system.

## Managing Dependencies

### Python Dependencies

**pyproject.toml (Required for custom deps):**
```toml
[project]
dependencies = [
    "google-adk>=1.8.0",
    "your-custom-package>=1.0.0",
    "another-dependency",
]
```

**uv.lock (Strongly Recommended):**
- Run `uv lock` after changing dependencies
- Commit the resulting `uv.lock` file for reproducibility
- If present, it guarantees exact dependency versions for users

**Best Practice:** Always include a `uv.lock` file for reproducible builds.

### Version Locking for Guaranteed Compatibility

For maximum compatibility and stability, you can lock your remote template to a specific version of the Agent Starter Pack. This ensures that your template will always be processed with the exact version it was designed for, preventing potential breaking changes from affecting your users.

**To enable version locking:**

1. **Add agent-starter-pack as a dev dependency** in your `pyproject.toml`:
   ```toml
   [dependency-groups]
   dev = [
       "agent-starter-pack==0.14.1",  # Lock to specific version
       # ... your other dev dependencies
   ]
   ```

2. **Generate the lock file:**
   ```bash
   uv lock
   ```

3. **Commit both files:**
   ```bash
   git add pyproject.toml uv.lock
   git commit -m "Lock agent-starter-pack version for compatibility"
   ```

**How it works:**
- When users fetch your remote template, the starter pack automatically detects the locked version in `uv.lock`
- It then executes `uvx agent-starter-pack==VERSION` with the locked version (requires `uv` to be installed)
- This guarantees your template is processed with the exact version you tested it with

**Requirements:**
- Users must have `uv` installed to use version-locked templates
- If `uv` is not available, the command will fail with installation instructions

**When to use version locking:**
- ✅ Your template uses specific starter pack features that might change
- ✅ You want to guarantee long-term stability for your users
- ✅ Your template is critical infrastructure that needs predictable behavior
- ❌ You always want the latest starter pack features (trade-off: potential breaking changes)

**Example user experience:**
```bash
uvx agent-starter-pack create my-project -a github.com/you/your-template

# Output:
# 🔒 Remote template specifies agent-starter-pack version 0.14.1 in uv.lock
# 📦 Executing nested command: uvx agent-starter-pack==0.14.1
# [continues with locked version]
```

### Makefile Customization

If your template includes a `Makefile`, it will be intelligently merged:
- **Your commands take precedence**: If a command exists in both makefiles, yours is kept
- **New commands are added**: Any unique commands from your Makefile are included
- **Base commands are preserved**: Essential commands from the base Makefile are appended

This lets you customize the build process while preserving starter pack functionality.

## Customizing Infrastructure

### Terraform Overrides

You can customize the generated agent's infrastructure by adding or replacing Terraform files:

- **Adding New Files**: Place new `.tf` files in the appropriate directory
- **Overriding Base Files**: Create files with the same name to completely replace base files

### Environment-Specific Configuration

**Production/Staging Configuration:**
```
deployment/terraform/
├── service.tf      # Replaces base service.tf for 'staging' and 'prod'
└── variables.tf    # Custom variables
```

**Development Configuration:**
```
deployment/terraform/dev/
├── service.tf      # Replaces base service.tf ONLY for 'dev'
└── variables.tf    # Dev-specific variables
```

**Example Structure:**
```
my-terraform-template/
├── pyproject.toml
└── deployment/
    └── terraform/
        ├── service.tf      # Production/staging override
        └── dev/
            └── service.tf  # Development override
```

For complete infrastructure customization options, see the [Deployment guide](../guide/deployment.md).

## Testing Your Template

### Local Testing
```bash
# Test from parent directory
uvx agent-starter-pack create test-project -a local@./your-template

# Test with different options
uvx agent-starter-pack create test-project -a local@./your-template --deployment-target cloud_run
```

### Validation Checklist

Before publishing, verify:
- [ ] `pyproject.toml` has all required dependencies
- [ ] Agent code is in appropriate directory structure (usually `/app` or configured `agent_directory`)
- [ ] `uv lock` generates without errors
- [ ] Local testing creates working agent
- [ ] README documents usage and requirements
- [ ] Configuration section enables discoverability

## Publishing Best Practices

### Repository Organization
- Use clear, descriptive repository names
- Include comprehensive README with usage examples
- Tag releases for stable versions
- Document any special requirements or setup

### Versioning
```bash
# Tag stable releases
git tag v1.0.0
git push origin v1.0.0

# Users can reference specific versions
uvx agent-starter-pack create my-agent -a github.com/user/template@v1.0.0
```

### Documentation
Include in your template's README:
- Purpose and use case of the template
- Usage examples
- Configuration options
- Prerequisites or special requirements
- Changelog for updates

## Troubleshooting for Template Authors

### "Template works but doesn't show up in `list`"
- Add `[tool.agent-starter-pack]` section to your `pyproject.toml`
- The `list` command only shows templates with explicit configuration

### "Template fails with dependency errors" 
- Ensure your `pyproject.toml` includes all required dependencies
- Run `uv lock` to generate a `uv.lock` file for reproducibility
- Test locally: `uvx agent-starter-pack create test -a local@./your-template`

### "Template uses wrong base or missing features"
- Check your `[tool.agent-starter-pack]` configuration
- Verify `base_template` is set correctly (defaults to "adk")
- Review available settings in the [Template Config Reference](../guide/template-config-reference.md)

### "Users report missing dependencies"
- Your `pyproject.toml` may be incomplete
- Consider providing a more comprehensive dependency list
- Include usage instructions in your README

## Examples and Inspiration

### Popular Template Patterns

**Data Science Agent:**
```toml
[tool.agent-starter-pack]
base_template = "adk"
[tool.agent-starter-pack.settings]
deployment_targets = ["cloud_run"]
extra_dependencies = ["pandas", "numpy", "scikit-learn"]
```

**Chat Bot Template:**
```toml
[tool.agent-starter-pack]
base_template = "adk"
[tool.agent-starter-pack.settings]
frontend_type = "None"
deployment_targets = ["agent_engine", "cloud_run"]
```

**Enterprise Template:**
```toml
[tool.agent-starter-pack]
base_template = "adk"
[tool.agent-starter-pack.settings]
session_type = "cloud_sql"
deployment_targets = ["cloud_run"]
include_data_ingestion = true
```

### Official Examples
- Browse [google/adk-samples](https://github.com/google/adk-samples) for production-ready examples
- Use `uvx agent-starter-pack list --adk` to see available official templates

## Next Steps

- **Start simple**: Begin with basic agent logic, add complexity gradually
- **Study examples**: Examine successful templates in adk-samples
- **Get feedback**: Share with the community and iterate based on usage
- **Stay updated**: Follow starter pack updates for new features and best practices
