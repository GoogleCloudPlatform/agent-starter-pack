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
