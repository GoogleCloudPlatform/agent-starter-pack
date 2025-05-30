# Installation

There are several ways to install the Agent Starter Pack. Choose the method that works best for your workflow.

**Want zero setup?** 👉 [Try in Firebase Studio](https://studio.firebase.google.com/new?template=https%3A%2F%2Fgithub.com%2FGoogleCloudPlatform%2Fagent-starter-pack%2Ftree%2Fmain%2Fsrc%2Fresources%2Fidx) or in [Cloud Shell](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Feliasecchig%2Fasp-open-in-cloud-shell&cloudshell_print=open-in-cs)

## `uvx` for Quick Project Creation

If you have [uv](https://astral.sh/uv) installed, you can create projects without a permanent installation:
```bash
uvx agent-starter-pack create my-awesome-agent
```

## Virtual Environment Installation

Installs into an isolated Python environment.

```bash
# Create and activate venv
python -m venv .venv && source .venv/bin/activate # source .venv/Scripts/activate for Windows Git Bash

# Install using pip or uv
pip install agent-starter-pack
```

## Persistent CLI Installation

Installs the `agent-starter-pack` command globally.

### With `pipx` (Isolated Global Tool)
```bash
# Install pipx (if needed)
python3 -m pip install --user pipx && python3 -m pipx ensurepath

# Install Agent Starter Pack
pipx install agent-starter-pack
```

### With `uv tool install` (Fast, Isolated Global Tool)
Requires `uv` (see `uvx` section for install).
```bash
uv tool install agent-starter-pack
```

## Create Project (After Persistent/Venv Install)

If you installed via `pipx`, `uv tool install`, or in a virtual environment:
```bash
agent-starter-pack create my-awesome-agent
```

## Managing Installation

### Upgrading
*   **`uvx`:** Not needed (always uses latest).
*   **`pipx`:** `pipx upgrade agent-starter-pack`
*   **`uv tool`:** `uv tool install agent-starter-pack` (this upgrades)
*   **`pip`/`uv pip` (in .venv):** `(uv) pip install --upgrade agent-starter-pack`

### Uninstalling
*   **`uvx`:** Not applicable.
*   **`pipx`:** `pipx uninstall agent-starter-pack`
*   **`uv tool`:** `uv tool uninstall agent-starter-pack`
*   **`pip`/`uv pip` (in .venv):** `(uv) pip uninstall agent-starter-pack`

## Troubleshooting Common Installation Issues

### Command Not Found After Installation

If you encounter "command not found" errors after installation:

1.  **Check your PATH**: Ensure that the Python scripts directory is in your PATH:
    ```bash
    echo $PATH
    ```
2.  **Verify installation location**: Check where the package was installed:
    ```bash
    pip show agent-starter-pack
    ```
3.  **Manual path addition**: If needed, add the scripts directory to your PATH:
    ```bash
    export PATH="$HOME/.local/bin:$PATH"
    # For user installations
    ```
    Add this line to your `~/.bashrc` or `~/.zshrc` for persistence.

### Permission Errors During Installation

If you encounter permission errors:

1.  **Use user installation mode**:
    ```bash
    pip install --user agent-starter-pack
    ```
2.  **Check directory permissions**:
    ```bash
    ls -la ~/.local/bin
    ```
3.  **Fix permissions if needed**:
    ```bash
    chmod +x ~/.local/bin/agent-starter-pack
    ```

### Python Version Compatibility Issues

If you encounter Python version errors:

1.  **Check your Python version**:
    ```bash
    python --version
    ```
2.  **Install a compatible Python version** if needed (3.10 or newer is required).
3.  **Create a virtual environment with the correct Python version**:
    ```bash
    python3.10 -m venv .venv
    source .venv/bin/activate
    ```

### Package Dependency Conflicts

If you encounter dependency conflicts:

1.  **Use a clean virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install agent-starter-pack
    ```
2.  **Update pip and setuptools**:
    ```bash
    pip install --upgrade pip setuptools
    ```
3.  **Install with verbose output to identify conflicts**:
    ```bash
    pip install -v agent-starter-pack
    ```

### Installation Verification

To verify your installation is working correctly:

1.  **Check the installed version**:
    ```bash
    agent-starter-pack --version
    ```
2.  **Run the help command**:
    ```bash
    agent-starter-pack --help
    ```

If you continue to experience issues, please [file an issue](https://github.com/GoogleCloudPlatform/agent-starter-pack/issues) with details about your environment and the specific error messages you're encountering.
