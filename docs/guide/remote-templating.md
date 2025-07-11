# Remote Templates

With remote templating, you can create and share your own agent starter packs without needing to fork the main repository. A remote template is a Git repository that the `agent-starter-pack` CLI can use as a blueprint to create new agent projects. This allows for easy sharing and reuse of customized agent setups.

This guide covers how to build, test, and use remote templates.

## Quickstart: Creating Your First Remote Template

Let's build a simple remote template that customizes the built-in `adk_base` agent.

### Step 1: Create the Template Directory Structure

A remote template is structured just like a standard agent project. The only special part is the `.template/` directory, which holds the configuration.

Create the following structure on your local machine:

```
my-first-remote-template/
├── .template/
│   └── templateconfig.yaml  # Configuration file
├── app/
│   └── agent.py             # Your custom agent logic
└── pyproject.toml           # Your custom dependencies
```

### Step 2: Configure the Template

The `templateconfig.yaml` file is required. It tells the starter pack how to use your template.

Put the following content in `.template/templateconfig.yaml`:

```yaml
# (Required) The built-in agent to use as a foundation.
base_template: "adk_base"

# (Required) Your template's name and description.
name: "My First Remote Template"
description: "A simple template that says hello."

# (Optional) Override settings from the base template.
settings:
  # This template will only support the 'agent_engine' deployment target.
  deployment_targets: ["agent_engine"]
```

### Step 3: Customize Dependencies and Agent Logic

First, define any custom dependencies in `pyproject.toml`. For this example, we'll just use the base dependencies but you could add your own here.

Put the following in `pyproject.toml`:
```toml
[project]
name = "my-first-remote-template"
version = "0.1.0"
dependencies = [
    "google-adk",
]
```

Next, we'll override the default `agent.py` to create a simple "hello world" agent.

Put the following code in `app/agent.py`:

```python
from google.adk.agents import Agent

def get_greeting(name: str = "World") -> str:
    """Returns a friendly greeting from the remote template."""
    return f"Hello, {name}! This greeting comes from a remote template."

root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful AI assistant. Use your tools to answer questions.",
    tools=[get_greeting],
)
```

### Step 4: Test Your Template Locally

Before publishing to Git, you can test your template from your local filesystem using the `local@` prefix.

Run the `create` command from the directory *outside* of your template folder:

```bash
# Make sure you are in the parent directory of 'my-first-remote-template'
uvx agent-starter-pack create my-test-agent -a local@./my-first-remote-template
```

This creates a new project `my-test-agent` using your local template.

### Step 5: Publish and Use Your Template

Once you are satisfied, initialize a Git repository, commit your files, and push them to a provider like GitHub. Now, you or anyone else can use your template directly from its Git URL:

```bash
# Replace with your repository URL
REPO_URL="https://github.com/your-username/my-first-remote-template"

uvx agent-starter-pack create my-remote-agent -a $REPO_URL
```

## Template Structure

A remote template repository mirrors the structure of a standard agent. The templating engine copies the entire contents of your repository and overlays them onto the base agent.

-   **Your Agent Files (`app/`, `tests/`, etc.)**: These should be at the root of your repository. They will overwrite the corresponding files from the `base_template`.
-   **`.template/` directory**: This special directory is **only** for the `templateconfig.yaml` file. It is read by the CLI for configuration but is not copied into the final project.
-   **Dependencies (`pyproject.toml`, `uv.lock`)**: These must be at the root of your repository.

**Example Structure:**
```
my-awesome-template/
├── .template/
│   └── templateconfig.yaml      # (Required) Configuration only.
├── pyproject.toml           # (Required) Custom Python dependencies.
├── uv.lock                  # (Recommended) Locked Python dependencies.
├── app/
│   └── agent.py             # Your custom agent logic.
└── README.md                # Your repository's README.
```

## How File Merging Works

Files are copied and overlaid in the following order, with later steps overwriting earlier ones if files have the same name and path:

1.  **[Base Project Files](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/src/base_template)**: The foundational files from the starter pack.
2.  **[Deployment Target Files](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/src/deployment_targets)**: Files for the chosen deployment target (e.g., `cloud_run`).
3.  **[Frontend Files](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/src/frontends)** (Optional): If a `frontend_type` is specified, its files are copied.
4.  **[Base Agent Files](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/agents)**: The application logic from the `base_template` you specified (e.g., files from `agents/adk_base/`).
5.  **Remote Template Files**: **(Highest Precedence)** All files from the root of your remote repository (except for the `.template` directory itself).

## Managing Dependencies

You have full control over the Python dependencies. Both `pyproject.toml` and `uv.lock` must be at the **root** of your remote template repository.
*   **`pyproject.toml`**: Required file that replaces the base template's version. Must include all dependencies for your agent.

*   **`uv.lock`**: Strongly recommended to ensure reproducibility.
    *   If present, guarantees exact dependency versions.
    *   If missing, falls back to base template's lock file. A new lock file will be generatede by the user when performing installation.

**Best Practice:** Always run `uv lock` after changing dependencies and commit the resulting lock file.

## Makefile Behavior

You cannot replace the `Makefile` from the `base_template`. However, you can add new commands or override existing ones via the `settings.commands` section in your `templateconfig.yaml`.

**Example:**
```yaml
settings:
  commands:
    override:
      # Replaces the default 'make install' command
      install: "uv sync --dev --extra jupyter"
    extra:
      # Adds 'make custom-lint'
      custom-lint:
        command: "ruff check ."
        description: "Run a custom lint check."
```

## Configuration Reference

The `templateconfig.yaml` file is the control center for defining an agent's properties, for both built-in and remote templates. For a complete breakdown of all available fields and their options, see the [Template Config Reference](./template-config-reference.md).

## Usage Reference

### Creating a Project from a Template

Use the `create` command with the `--agent` (`-a`) flag.

*   **Full GitHub URL:**
    ```bash
    uvx agent-starter-pack create my-agent -a https://github.com/my-org/my-repo/tree/main/path-to-template
    ```

*   **Shorthand URL (GitHub, GitLab, Bitbucket):**
    ```bash
    # Specify a branch/tag with @
    uvx agent-starter-pack create my-agent -a github.com/my-org/my-repo/path-to-template@develop
    ```

*   **ADK Samples Shortcut:** A convenient alias for official Google agent examples. It allows you to create projects from the [google/adk-samples](https://github.com/google/adk-samples) repository without needing to type the full URL.
    ```bash
    # Creates a project from the 'gemini-fullstack' template in adk-samples
    uvx agent-starter-pack create my-agent -a adk@gemini-fullstack
    ```

*   **Local Testing:**
    ```bash
    uvx agent-starter-pack create my-test-project -a local@./path/to/your/template
    ```

### Listing Available Agents

The `list` command helps you discover templates.

*   **List Built-in Agents:**
    ```bash
    uvx agent-starter-pack list
    ```

*   **List Agents in a Remote Repository:**
    ```bash
    uvx agent-starter-pack list --source https://github.com/my-org/my-repo
    ```

*   **List Official ADK Samples:**
    ```bash
    uvx agent-starter-pack list --adk
    ```
