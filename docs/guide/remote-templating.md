# Remote Templates

Remote templates turn your agent prototype into a production-ready starter pack. A remote template is a Git repository containing your custom agent logic, dependencies, and infrastructure definitions (Terraform). The `agent-starter-pack` CLI uses it to generate a complete, deployable application by automatically adding production-grade boilerplate for testing and multi-target deployment (e.g., Cloud Run, Agent Engine). This lets you share best practices and provide a one-command "get started" experience for any agent.

## Prerequisites

To create a valid remote template, your project structure and dependency definitions must be compatible with `uv`, the Python package manager used by the Agent Starter Pack.

- **`pyproject.toml`:** Your template **must** include a `pyproject.toml` file at its root. This file must be valid and parseable by `uv`. It defines your agent's dependencies and project metadata.
- **Dependency Management:** The starter pack uses `uv` to install the dependencies specified in your `pyproject.toml`. Ensure that your dependencies can be resolved by `uv`.

## Quickstart: Creating Your First Remote Template

Let's build a simple remote template that customizes the built-in `adk_base` agent.

### Step 1: Create the Template Directory Structure

A remote template is structured just like a standard **agent codebase**. The only special part is the `.template/` directory, which holds the configuration.

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

This creates a new **agent** named `my-test-agent` using your local template.

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
-   **`.template/` directory**: This special directory is **only** for the `templateconfig.yaml` file. It is read by the CLI for configuration but is not copied into the final generated **agent**.
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

1.  **[Base Template Files](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/src/base_template)**: The foundational files from the starter pack.
2.  **[Deployment Target Files](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/src/deployment_targets)**: Files for the chosen deployment target (e.g., `cloud_run`).
3.  **[Frontend Files](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/src/frontends)** (Optional): If a `frontend_type` is specified, its files are copied.
4.  **[Base Agent Files](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/agents)**: The application logic from the `base_template` you specified (e.g., files from `agents/adk_base/`).
5.  **Remote Template Files**: **(Highest Precedence)** All files from the root of your remote repository (except for the `.template` directory itself).

## Managing Dependencies

You have full control over the Python dependencies. Both `pyproject.toml` and `uv.lock` must be at the **root** of your remote template repository.
*   **`pyproject.toml`**: Required file that replaces the base template's version. Must include all dependencies for your agent.

*   **`uv.lock`**: Strongly recommended to ensure reproducibility.
    *   If present, it will be copied to the generated agent, guaranteeing exact dependency versions.
    *   If missing, the generated agent will **not** include a `uv.lock` file. The user is expected to generate one by running `make install` or `uv pip sync` after the agent is created.

**Best Practice:** Always run `uv lock` after changing dependencies and commit the resulting lock file.

## Makefile Behavior

If your remote template includes a `Makefile` at the root, it will be used as the primary `Makefile` for the generated project. The system intelligently merges it with the `base_template`'s `Makefile` to ensure that essential commands from the starter pack are not lost.

Here's how the merge logic works:
- **Your Commands Take Precedence**: If a command exists in both your remote `Makefile` and the base `Makefile`, your version is kept.
- **New Commands are Added**: Any commands from your `Makefile` are added.
- **Base Commands are Appended**: Any commands that are in the base `Makefile` but not in yours are appended to your `Makefile`, under a clear separator comment.

This allows you to completely customize the `Makefile` while still inheriting the standard functionality of the starter pack.

## Customizing Infrastructure with Terraform

You can customize the generated agent's infrastructure by adding or replacing Terraform files in your remote template. The templating engine follows a simple rule: your remote template's files take precedence over the base template's files.

-   **Adding New Files:** To add a new Terraform file (e.g., for a custom resource), simply place it in the desired directory.
-   **Overriding Base Files:** To completely replace a file from the base template (e.g., to change the default storage configuration), create a file with the **exact same name** in the corresponding directory of your remote template. Your version of the file will be used instead of the base one.

### Environment-Specific Configuration

The starter pack uses a directory-based approach for managing different deployment environments. The Terraform configurations are split between production/staging and development.

-   **Production/Staging Configuration:** Files in `deployment/terraform/` define the infrastructure for your `staging` and `prod` environments.
-   **Development Configuration:** Files in `deployment/terraform/dev/` define the infrastructure for your `dev` environment. This configuration is typically simpler and uses fewer resources to save costs.

When you create a remote template, you can override files in either of these directories. For example, to change the machine type for your production Cloud Run service, you would replace `deployment/terraform/service.tf`. To change it for your development environment, you would replace `deployment/terraform/dev/service.tf`.

**Example Structure:**
```
my-terraform-template/
├── .template/
│   └── templateconfig.yaml
├── pyproject.toml
└── deployment/
    └── terraform/
        ├── service.tf      # Replaces the base service.tf for 'staging' and 'prod'
        └── dev/
            └── service.tf  # Replaces the base service.tf ONLY for the 'dev' environment
```

For a complete list of configurable infrastructure variables, see the [Deployment guide](./deployment.md).

## Configuration Reference

The `templateconfig.yaml` file is the control center for defining an agent's properties, for both built-in and remote templates. For a complete breakdown of all available fields and their options, see the [Template Config Reference](./template-config-reference.md).

## Usage Reference

### Creating an Agent from a Template

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

*   **ADK Samples Shortcut:** A convenient alias for official Google agent examples. It allows you to create **agents** from the [google/adk-samples](https://github.com/google/adk-samples) repository without needing to type the full URL.
    ```bash
    # Creates an agent from the 'gemini-fullstack' template in adk-samples
    uvx agent-starter-pack create my-agent -a adk@gemini-fullstack
    ```

*   **Local Testing:**
    ```bash
    uvx agent-starter-pack create my-test-agent -a local@./path/to/your/template
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