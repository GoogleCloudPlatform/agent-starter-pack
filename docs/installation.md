# Installation

There are several ways to install the Agent Starter Pack. Choose the method that works best for your workflow.

## Using pipx (Recommended)

The recommended way to install the Agent Starter Pack is with [pipx](https://pypa.github.io/pipx/), which installs the package in an isolated environment while making the commands globally available:

```bash
# Install pipx if you don't have it
python3 -m pip install --user pipx && python3 -m pipx ensurepath
source ~/.bashrc  # or ~/.zshrc depending on your shell

# Install the Agent Starter Pack
pipx install agent-starter-pack
```

## Using pip with a virtual environment

You can also install the Agent Starter Pack in a virtual environment:

```bash
# Create and activate a Python virtual environment
python -m venv venv && source venv/bin/activate

# Install the Agent Starter Pack
pip install agent-starter-pack
```

## Using uv (Fast Python package installer)

For a faster installation experience, you can use [uv](https://astral.sh/uv):

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

source $HOME/.local/bin/env (sh, bash, zsh)
source $HOME/.local/bin/env.fish (fish)

# Install the Agent Starter Pack
uv pip install agent-starter-pack
```

## Getting Started

After installation, you can create a new agent project:

```bash
# Create a new agent project
agent-starter-pack create my-awesome-agent
```


## Upgrading

To upgrade, use the same tool you used for installation:

```bash
pipx upgrade agent-starter-pack  # Using pipx
pip install --upgrade agent-starter-pack  # Using pip
uv pip install --upgrade agent-starter-pack  # Using uv
```

## Uninstalling

To uninstall, use the same tool you used for installation:

```bash
pipx uninstall agent-starter-pack # Using pipx
pip uninstall agent-starter-pack  # Using pip
uv pip uninstall agent-starter-pack  # Using uv
```
