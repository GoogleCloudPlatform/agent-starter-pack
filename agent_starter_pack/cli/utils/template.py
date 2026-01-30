# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any

if sys.version_info >= (3, 11):
    from datetime import UTC
else:
    from datetime import timezone

    UTC = timezone.utc  # noqa: UP017 - Required for Python 3.10 compatibility

import yaml
from cookiecutter.main import cookiecutter
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

from agent_starter_pack.cli.utils.version import get_current_version

from .datastores import DATASTORES
from .remote_template import (
    get_base_template_name,
    render_and_merge_makefiles,
)

# =============================================================================
# Agent Name Aliases (Backwards Compatibility)
# =============================================================================
# Maps legacy agent names to their current names.
# This allows users to continue using old names like `--agent adk_base`
# and for remote templates to reference `base_template: adk_base`.
# =============================================================================

AGENT_ALIASES: dict[str, str] = {
    "adk_base": "adk",
    "langgraph_base": "langgraph",
    "custom": "langgraph",
    "custom_a2a": "langgraph",
    "adk_a2a_base": "adk_a2a",
    "adk_base_go": "adk_go",
}


def resolve_agent_alias(name: str | None) -> str | None:
    """Resolve legacy agent name to current name.

    Args:
        name: Agent name (possibly a legacy alias)

    Returns:
        Current agent name, or original if not an alias
    """
    if name is None:
        return None
    resolved = AGENT_ALIASES.get(name, name)
    if resolved != name:
        logging.info(f"Agent '{name}' has been renamed to '{resolved}'")
    return resolved


# =============================================================================
# Conditional Files Configuration
# =============================================================================
# Maps file/directory paths to their inclusion conditions.
# Files are stored with simple names and deleted if condition is False.
# This replaces Jinja2 conditionals in filenames for Windows compatibility.
#
# Format: "relative/path/to/file_or_dir": lambda config: bool_condition
# The config dict contains: agent_name, cicd_runner, is_adk, is_adk_live, is_a2a
# =============================================================================

# Helper: exclude service.tf only for adk_live + agent_engine combination
_exclude_adk_live_agent_engine = lambda c: not (
    c.get("agent_name") == "adk_live" and c.get("deployment_target") == "agent_engine"
)

CONDITIONAL_FILES = {
    # CI/CD runner conditional files (base_template)
    ".cloudbuild": lambda c: c.get("cicd_runner") == "google_cloud_build",
    ".github": lambda c: c.get("cicd_runner") == "github_actions",
    "deployment/terraform/build_triggers.tf": (
        lambda c: c.get("cicd_runner") == "google_cloud_build"
    ),
    "deployment/terraform/wif.tf": (lambda c: c.get("cicd_runner") == "github_actions"),
    # Agent-specific conditional files (uses agent_directory placeholder)
    "{agent_directory}/app_utils/gcs.py": (lambda c: c.get("agent_name") == "adk_live"),
    "{agent_directory}/app_utils/executor": (
        lambda c: c.get("is_a2a") and c.get("agent_name") == "langgraph"
    ),
    "{agent_directory}/app_utils/converters": (
        lambda c: c.get("is_a2a") and c.get("agent_name") == "langgraph"
    ),
    # Agent Engine deployment target conditionals
    "{agent_directory}/app_utils/expose_app.py": lambda c: c.get("is_adk_live"),
    "tests/helpers.py": lambda c: c.get("is_a2a"),
    "deployment/terraform/service.tf": _exclude_adk_live_agent_engine,
    "deployment/terraform/dev/service.tf": _exclude_adk_live_agent_engine,
}


def apply_conditional_files(
    project_path: pathlib.Path,
    config: dict[str, Any],
    agent_directory: str = "app",
) -> None:
    """Apply conditional file logic by deleting files that don't match conditions.

    This function checks each conditional file against its condition and either
    keeps the file (condition True) or renames it to unused_* (condition False)
    so it gets cleaned up by the existing unused file cleanup logic.

    Args:
        project_path: Path to the generated project directory
        config: Configuration dict with keys: agent_name, cicd_runner,
                is_adk, is_adk_live, is_a2a
        agent_directory: Name of the agent directory (replaces {agent_directory} placeholder)
    """
    for rel_path_template, condition_fn in CONDITIONAL_FILES.items():
        # Replace {agent_directory} placeholder
        rel_path = rel_path_template.replace("{agent_directory}", agent_directory)
        file_path = project_path / rel_path

        if not file_path.exists():
            continue

        should_include = condition_fn(config)

        if not should_include:
            # Rename to unused_* so existing cleanup logic handles it
            parent = file_path.parent
            name = file_path.name
            unused_path = parent / f"unused_{name}"

            logging.debug(
                f"Conditional file '{rel_path}' condition False, "
                f"renaming to {unused_path.name}"
            )

            if unused_path.exists():
                if unused_path.is_dir():
                    shutil.rmtree(unused_path)
                else:
                    unused_path.unlink()

            file_path.rename(unused_path)
        else:
            logging.debug(f"Conditional file '{rel_path}' condition True, keeping")


def add_base_template_dependencies_interactively(
    project_path: pathlib.Path,
    base_dependencies: list[str],
    base_template_name: str,
    auto_approve: bool = False,
) -> bool:
    """Interactively add base template dependencies using uv add.

    Args:
        project_path: Path to the project directory
        base_dependencies: List of dependencies from base template's extra_dependencies
        base_template_name: Name of the base template being used
        auto_approve: Whether to skip confirmation and auto-install

    Returns:
        True if dependencies were added successfully, False otherwise
    """
    if not base_dependencies:
        return True

    console = Console()

    # Construct dependency string once for reuse
    deps_str = " ".join(f"'{dep}'" for dep in base_dependencies)

    # Show what dependencies will be added
    console.print(
        f"\n✓ Base template override: Using '{base_template_name}' as foundation",
        style="bold cyan",
    )
    console.print("  This requires adding the following dependencies:", style="white")
    for dep in base_dependencies:
        console.print(f"    • {dep}", style="yellow")

    # Ask for confirmation unless auto-approve
    should_add = True
    if not auto_approve:
        should_add = Confirm.ask(
            "\n? Add these dependencies automatically?", default=True
        )

    if not should_add:
        console.print("\n⚠️  Skipped dependency installation.", style="yellow")
        console.print("   To add them manually later, run:", style="dim")
        console.print(f"       cd {project_path.name}", style="dim")
        console.print(f"       uv add {deps_str}\n", style="dim")
        return False

    # Run uv add
    try:
        if auto_approve:
            console.print(
                f"✓ Auto-installing dependencies: {', '.join(base_dependencies)}",
                style="bold cyan",
            )
        else:
            console.print(f"\n✓ Running: uv add {deps_str}", style="bold cyan")

        # Run uv add in the project directory
        cmd = ["uv", "add", *base_dependencies]
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # Show success message
        if not auto_approve:
            # Show a summary line from uv output
            output_lines = result.stderr.strip().split("\n")
            for line in output_lines:
                if "Resolved" in line or "Installed" in line:
                    console.print(f"  {line}", style="dim")
                    break

        console.print("✓ Dependencies added successfully\n", style="bold green")
        return True

    except subprocess.CalledProcessError as e:
        console.print(
            f"\n✗ Failed to add dependencies: {e.stderr.strip()}", style="bold red"
        )
        console.print("  You can add them manually:", style="yellow")
        console.print(f"      cd {project_path.name}", style="dim")
        console.print(f"      uv add {deps_str}\n", style="dim")
        return False
    except FileNotFoundError:
        console.print(
            "\n✗ uv command not found. Please install uv first.", style="bold red"
        )
        console.print("  Install from: https://docs.astral.sh/uv/", style="dim")
        console.print("\n  To add dependencies manually:", style="yellow")
        console.print(f"      cd {project_path.name}", style="dim")
        console.print(f"      uv add {deps_str}\n", style="dim")
        return False


def validate_agent_directory_name(agent_dir: str, allow_dot: bool = False) -> None:
    """Validate that an agent directory name is a valid Python identifier.

    Args:
        agent_dir: The agent directory name to validate
        allow_dot: If True, allows "." as a special value indicating flat structure

    Raises:
        ValueError: If the agent directory name is not a valid Python identifier

    Note:
        The special value "." indicates flat structure - agent code is in the
        template root. When "." is used, the target directory name will be
        derived from the template folder name.
    """
    if agent_dir == ".":
        if allow_dot:
            return  # "." is valid when explicitly allowed (will be resolved later)
        raise ValueError(
            "Agent directory '.' is not valid in this context. "
            "Use '.' only to indicate flat structure templates."
        )

    if "-" in agent_dir:
        raise ValueError(
            f"Agent directory '{agent_dir}' contains hyphens (-) which are not allowed. "
            "Agent directories must be valid Python identifiers since they're used as module names. "
            "Please use underscores (_) or lowercase letters instead."
        )

    if not agent_dir.replace("_", "a").isidentifier():
        raise ValueError(
            f"Agent directory '{agent_dir}' is not a valid Python identifier. "
            "Agent directories must be valid Python identifiers since they're used as module names. "
            "Please use only lowercase letters, numbers, and underscores, and don't start with a number."
        )


@dataclass
class TemplateConfig:
    name: str
    description: str
    settings: dict[str, bool | list[str]]

    @classmethod
    def from_file(cls, config_path: pathlib.Path) -> "TemplateConfig":
        """Load template config from file with validation"""
        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ValueError(f"Invalid template config format in {config_path}")

            required_fields = ["name", "description", "settings"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                raise ValueError(
                    f"Missing required fields in template config: {missing_fields}"
                )

            return cls(
                name=data["name"],
                description=data["description"],
                settings=data["settings"],
            )
        except yaml.YAMLError as err:
            raise ValueError(f"Invalid YAML in template config: {err}") from err
        except Exception as err:
            raise ValueError(f"Error loading template config: {err}") from err


def get_overwrite_folders(agent_directory: str) -> list[str]:
    """Get folders to overwrite with configurable agent directory."""
    return [agent_directory, "frontend", "tests", "notebooks"]


TEMPLATE_CONFIG_FILE = "templateconfig.yaml"
DEPLOYMENT_TARGETS = ["cloud_run", "agent_engine"]
SUPPORTED_LANGUAGES = ["python", "go"]
DEFAULT_FRONTEND = "None"


def get_available_agents(deployment_target: str | None = None) -> dict:
    """Dynamically load available agents from the agents directory.

    Returns agents grouped by language and framework for display purposes.
    Each agent dict includes: name, description, language, framework.

    Args:
        deployment_target: Optional deployment target to filter agents
    """
    # Define display order for agents within each group
    PRIORITY_ORDER = {
        "adk": 0,
        "adk_a2a": 1,
        "adk_live": 2,
        "agentic_rag": 3,
        "langgraph": 0,
        "adk_go": 0,
    }

    agents_list = []
    agents_dir = pathlib.Path(__file__).parent.parent.parent / "agents"

    for agent_dir in agents_dir.iterdir():
        if agent_dir.is_dir() and not agent_dir.name.startswith("__"):
            template_config_path = agent_dir / ".template" / "templateconfig.yaml"
            if template_config_path.exists():
                try:
                    with open(template_config_path, encoding="utf-8") as f:
                        config = yaml.safe_load(f)
                    agent_name = agent_dir.name
                    settings = config.get("settings", {})

                    # Skip if deployment target specified and agent doesn't support it
                    if deployment_target:
                        targets = settings.get("deployment_targets", [])
                        if isinstance(targets, str):
                            targets = [targets]
                        if deployment_target not in targets:
                            continue

                    # Determine language (default to python)
                    language = settings.get("language", "python")

                    # Determine framework from tags
                    tags = settings.get("tags", [])
                    if "langgraph" in tags:
                        framework = "langgraph"
                    elif "adk" in tags:
                        framework = "adk"
                    else:
                        framework = "other"

                    description = config.get("description", "No description available")
                    display_name = config.get("display_name", agent_name)
                    priority = PRIORITY_ORDER.get(agent_name, 100)

                    agent_info = {
                        "name": agent_name,
                        "display_name": display_name,
                        "description": description,
                        "language": language,
                        "framework": framework,
                        "priority": priority,
                    }
                    agents_list.append(agent_info)
                except Exception as e:
                    logging.warning(f"Could not load agent from {agent_dir}: {e}")

    # Define group order: Python ADK, Python LangGraph, Go ADK, Other
    GROUP_ORDER = {
        ("python", "adk"): 0,
        ("python", "langgraph"): 1,
        ("go", "adk"): 2,
    }

    def sort_key(agent: dict) -> tuple:
        group = (agent["language"], agent["framework"])
        group_order = GROUP_ORDER.get(group, 99)
        return (group_order, agent["priority"], agent["name"])

    agents_list.sort(key=sort_key)

    # Convert to numbered dictionary starting from 1
    agents = {i + 1: agent for i, agent in enumerate(agents_list)}

    return agents


def load_template_config(template_dir: pathlib.Path) -> dict[str, Any]:
    """Read .templateconfig.yaml file to get agent configuration."""
    config_file = template_dir / TEMPLATE_CONFIG_FILE
    if not config_file.exists():
        return {}

    try:
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config if config else {}
    except Exception as e:
        logging.error(f"Error loading template config: {e}")
        return {}


def get_agent_language(
    agent_name: str, remote_config: dict[str, Any] | None = None
) -> str:
    """Get the programming language for the selected agent.

    Args:
        agent_name: Name of the agent
        remote_config: Optional remote template configuration

    Returns:
        Language string ('python' or 'go'), defaults to 'python'
    """
    if remote_config:
        config = remote_config
    else:
        template_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "agents"
            / agent_name
            / ".template"
        )
        config = load_template_config(template_path)

    if not config:
        return "python"

    language = config.get("settings", {}).get("language", "python")
    if language not in SUPPORTED_LANGUAGES:
        logging.warning(
            f"Unsupported language '{language}' for agent {agent_name}, defaulting to python"
        )
        return "python"
    return language


def get_deployment_targets(
    agent_name: str, remote_config: dict[str, Any] | None = None
) -> list:
    """Get available deployment targets for the selected agent."""
    if remote_config:
        config = remote_config
    else:
        template_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "agents"
            / agent_name
            / ".template"
        )
        config = load_template_config(template_path)

    if not config:
        return []

    targets = config.get("settings", {}).get("deployment_targets", [])
    return targets if isinstance(targets, list) else [targets]


def prompt_deployment_target(
    agent_name: str, remote_config: dict[str, Any] | None = None
) -> str:
    """Ask user to select a deployment target for the agent."""
    targets = get_deployment_targets(agent_name, remote_config=remote_config)

    # Define deployment target friendly names and descriptions
    TARGET_INFO = {
        "agent_engine": {
            "display_name": "agent_engine",
            "description": "Vertex AI managed platform",
        },
        "cloud_run": {
            "display_name": "cloud_run",
            "description": "GCP serverless containers",
        },
    }

    if not targets:
        return ""

    console = Console()
    console.print("\n> Please select a deployment target:")
    console.print("\n  [bold cyan]☁️  Deployment Targets[/]")
    for idx, target in enumerate(targets, 1):
        info = TARGET_INFO.get(target, {})
        display_name = info.get("display_name", target)
        description = info.get("description", "")
        name_padded = display_name.ljust(14)
        console.print(f"     {idx}. [bold]{name_padded}[/] [dim]{description}[/]")

    choice = IntPrompt.ask(
        "\nEnter the number of your deployment target choice",
        default=1,
        show_default=True,
    )
    return targets[choice - 1]


def prompt_session_type_selection() -> str:
    """Ask user to select a session type for Cloud Run deployment."""
    console = Console()

    session_types = {
        "in_memory": {
            "display_name": "in_memory",
            "description": "Stateless, data in memory",
        },
        "cloud_sql": {
            "display_name": "cloud_sql",
            "description": "PostgreSQL persistence",
        },
        "agent_engine": {
            "display_name": "agent_engine",
            "description": "Managed session service",
        },
    }

    console.print("\n> Please select a session type:")
    console.print("\n  [bold cyan]💾 Session Types[/]")
    for idx, (_key, info) in enumerate(session_types.items(), 1):
        name_padded = info["display_name"].ljust(14)
        console.print(
            f"     {idx}. [bold]{name_padded}[/] [dim]{info['description']}[/]"
        )

    choice = IntPrompt.ask(
        "\nEnter the number of your session type choice",
        default=1,
        show_default=True,
    )

    return list(session_types.keys())[choice - 1]


def _display_datastore_menu(console: Console) -> str:
    """Display the datastore selection menu and return the selected type."""
    console.print("\n> Please select a datastore:")
    console.print("\n  [bold cyan]🗄️  Datastores[/]")
    for i, (key, info) in enumerate(DATASTORES.items(), 1):
        name_padded = key.ljust(24)
        console.print(f"     {i}. [bold]{name_padded}[/] [dim]{info['name']}[/]")

    choice = Prompt.ask(
        "\nEnter the number of your choice",
        choices=[str(i) for i in range(1, len(DATASTORES) + 1)],
        default="1",
    )
    return list(DATASTORES.keys())[int(choice) - 1]


def prompt_datastore_selection(
    agent_name: str, from_cli_flag: bool = False
) -> str | None:
    """Ask user to select a datastore type if the agent supports data ingestion.

    Args:
        agent_name: Name of the agent
        from_cli_flag: Whether this is being called due to explicit --include-data-ingestion flag
    """
    console = Console()

    # If this is from CLI flag, skip the "would you like to include" prompt
    if from_cli_flag:
        return _display_datastore_menu(console)

    # Otherwise, proceed with normal flow
    template_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "agents"
        / agent_name
        / ".template"
    )
    config = load_template_config(template_path)

    if config:
        # If requires_data_ingestion is true, prompt for datastore type without asking if they want it
        if config.get("settings", {}).get("requires_data_ingestion"):
            console.print("\n> This agent includes a data ingestion pipeline.")
            return _display_datastore_menu(console)

        # Only prompt if the agent has optional data ingestion support
        if "requires_data_ingestion" in config.get("settings", {}):
            include = (
                Prompt.ask(
                    "\n> This agent supports data ingestion. Would you like to include a data pipeline?",
                    choices=["y", "n"],
                    default="n",
                ).lower()
                == "y"
            )

            if include:
                return _display_datastore_menu(console)

    # If we get here, we need to prompt for datastore selection for explicit --include-data-ingestion flag
    return _display_datastore_menu(console)


def prompt_cicd_runner_selection() -> str:
    """Ask user to select a CI/CD runner."""
    console = Console()

    cicd_runners = {
        "skip": {
            "display_name": "simple",
            "description": "No CI/CD, add later with 'enhance'",
        },
        "google_cloud_build": {
            "display_name": "google_cloud_build",
            "description": "Fully managed, GCP-integrated",
        },
        "github_actions": {
            "display_name": "github_actions",
            "description": "Workload identity federation",
        },
    }

    console.print("\n> Please select a CI/CD runner:")
    console.print("\n  [bold cyan]🔧 CI/CD Options[/]")
    for idx, (_key, info) in enumerate(cicd_runners.items(), 1):
        name_padded = info["display_name"].ljust(20)
        console.print(
            f"     {idx}. [bold]{name_padded}[/] [dim]{info['description']}[/]"
        )

    choice = IntPrompt.ask(
        "\nEnter the number of your CI/CD runner choice",
        default=1,
        show_default=True,
    )

    return list(cicd_runners.keys())[choice - 1]


def get_template_path(agent_name: str, debug: bool = False) -> pathlib.Path:
    """Get the absolute path to the agent template directory."""
    current_dir = pathlib.Path(__file__).parent.parent.parent
    template_path = current_dir / "agents" / agent_name / ".template"
    if debug:
        logging.debug(f"Looking for template in: {template_path}")
        logging.debug(f"Template exists: {template_path.exists()}")
        if template_path.exists():
            logging.debug(f"Template contents: {list(template_path.iterdir())}")

    if not template_path.exists():
        raise ValueError(f"Template directory not found at {template_path}")

    return template_path


def copy_data_ingestion_files(
    project_template: pathlib.Path, datastore_type: str
) -> None:
    """Copy data processing files to the project template for cookiecutter templating.

    Args:
        project_template: Path to the project template directory
        datastore_type: Type of datastore to use for data ingestion
    """
    data_ingestion_src = pathlib.Path(__file__).parent.parent.parent / "data_ingestion"
    data_ingestion_dst = project_template / "data_ingestion"

    if data_ingestion_src.exists():
        logging.debug(
            f"Copying data processing files from {data_ingestion_src} to {data_ingestion_dst}"
        )

        copy_files(data_ingestion_src, data_ingestion_dst, overwrite=True)

        logging.debug(f"Data ingestion files prepared for datastore: {datastore_type}")
    else:
        logging.warning(
            f"Data processing source directory not found at {data_ingestion_src}"
        )


def _extract_agent_garden_labels(
    agent_garden: bool,
    remote_spec: Any | None,
    remote_template_path: pathlib.Path | None,
) -> tuple[str | None, str | None]:
    """Extract agent sample ID and publisher for Agent Garden labeling.

    This function supports two mechanisms for extracting label information:
    1. From remote_spec metadata (for ADK samples)
    2. Fallback to pyproject.toml parsing (for version-locked templates)

    Args:
        agent_garden: Whether this deployment is from Agent Garden
        remote_spec: Remote template spec with ADK samples metadata
        remote_template_path: Path to remote template directory

    Returns:
        Tuple of (agent_sample_id, agent_sample_publisher) or (None, None) if no labels found
    """
    if not agent_garden:
        return None, None

    agent_sample_id = None
    agent_sample_publisher = None

    # Handle remote specs with ADK samples metadata
    if (
        remote_spec
        and hasattr(remote_spec, "is_adk_samples")
        and remote_spec.is_adk_samples
    ):
        # For ADK samples, template_path is like "python/agents/sample-name"
        agent_sample_id = pathlib.Path(remote_spec.template_path).name
        # For ADK samples, publisher is always "google"
        agent_sample_publisher = "google"
        logging.debug(f"Detected ADK sample from remote_spec: {agent_sample_id}")
        return agent_sample_id, agent_sample_publisher

    # Fallback: Detect ADK samples from pyproject.toml (for version-locked templates)
    if remote_template_path:
        pyproject_path = remote_template_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                if sys.version_info >= (3, 11):
                    import tomllib
                else:
                    import tomli as tomllib

                with open(pyproject_path, "rb") as toml_file:
                    pyproject_data = tomllib.load(toml_file)

                # Extract project name from pyproject.toml
                project_name_from_toml = pyproject_data.get("project", {}).get("name")

                if project_name_from_toml:
                    agent_sample_id = project_name_from_toml
                    agent_sample_publisher = "google"  # ADK samples are from Google
                    logging.debug(
                        f"Detected ADK sample from pyproject.toml: {agent_sample_id}"
                    )
            except Exception as e:
                logging.debug(f"Failed to read pyproject.toml: {e}")

    return agent_sample_id, agent_sample_publisher


def _inject_app_object_if_missing(
    agent_py_path: pathlib.Path, agent_directory: str, console: Console
) -> None:
    """Inject app object into agent.py if missing (backward compatibility for ADK).

    Args:
        agent_py_path: Path to the agent.py file
        agent_directory: Name of the agent directory for logging
        console: Rich console for user feedback
    """
    try:
        content = agent_py_path.read_text(encoding="utf-8")
        # Check for app object (assignment, function definition, or import)
        app_patterns = [
            r"^\s*app\s*=",  # assignment: app = ...
            r"^\s*def\s+app\(",  # function: def app(...)
            r"from\s+.*\s+import\s+.*\bapp\b",  # import: from ... import app
        ]
        has_app = any(
            re.search(pattern, content, re.MULTILINE) for pattern in app_patterns
        )

        if not has_app:
            console.print(
                f"ℹ️  Adding 'app' object to [cyan]{agent_directory}/agent.py[/cyan] for backward compatibility",
                style="dim",
            )
            # Add import and app object at the end of the file
            content = content.rstrip()
            if "from google.adk.apps import App" not in content:
                content += "\n\nfrom google.adk.apps import App\n"
            content += f'\napp = App(root_agent=root_agent, name="{agent_directory}")\n'

            # Write the modified content back
            agent_py_path.write_text(content, encoding="utf-8")
    except Exception as e:
        logging.warning(
            f"Could not inject app object into {agent_directory}/agent.py: {type(e).__name__}: {e}"
        )


def _generate_yaml_agent_shim(
    agent_py_path: pathlib.Path,
    agent_directory: str,
    console: Console,
    force: bool = False,
) -> None:
    """Generate agent.py shim for YAML config agents.

    When a root_agent.yaml is detected, this function generates an agent.py
    that loads the YAML config and exposes the root_agent and app objects
    required by the deployment pipeline.

    Args:
        agent_py_path: Path where agent.py should be created/updated
        agent_directory: Name of the agent directory for logging
        console: Rich console for user feedback
        force: If True, overwrite existing agent.py even if it has root_agent defined.
               Used when the user explicitly has a root_agent.yaml.
    """
    root_agent_yaml = agent_py_path.parent / "root_agent.yaml"

    if not root_agent_yaml.exists():
        return

    # Check if agent.py already exists and has root_agent defined
    if agent_py_path.exists() and not force:
        try:
            content = agent_py_path.read_text(encoding="utf-8")
            if re.search(r"^\s*root_agent\s*=", content, re.MULTILINE):
                logging.debug(
                    f"{agent_directory}/agent.py already has root_agent defined"
                )
                return
        except Exception as e:
            logging.warning(f"Could not read existing agent.py: {e}")

    console.print(
        f"ℹ️  Generating [cyan]{agent_directory}/agent.py[/cyan] shim for YAML config agent",
        style="dim",
    )

    shim_content = f'''"""Agent module that loads the YAML config agent.

This file is auto-generated to provide compatibility with the deployment pipeline.
Edit root_agent.yaml to modify your agent configuration.
"""

from pathlib import Path

from google.adk.agents import config_agent_utils
from google.adk.apps import App

_AGENT_DIR = Path(__file__).parent
root_agent = config_agent_utils.from_config(str(_AGENT_DIR / "root_agent.yaml"))
app = App(root_agent=root_agent, name="{agent_directory}")
'''

    try:
        agent_py_path.write_text(shim_content, encoding="utf-8")
        logging.debug(f"Generated YAML agent shim at {agent_py_path}")
    except Exception as e:
        logging.warning(
            f"Could not generate YAML agent shim at {agent_py_path}: {type(e).__name__}: {e}"
        )


def process_template(
    agent_name: str,
    template_dir: pathlib.Path,
    project_name: str,
    deployment_target: str | None = None,
    cicd_runner: str | None = None,
    include_data_ingestion: bool = False,
    datastore: str | None = None,
    session_type: str | None = None,
    output_dir: pathlib.Path | None = None,
    remote_template_path: pathlib.Path | None = None,
    remote_config: dict[str, Any] | None = None,
    in_folder: bool = False,
    cli_overrides: dict[str, Any] | None = None,
    agent_garden: bool = False,
    remote_spec: Any | None = None,
    google_api_key: str | None = None,
    google_cloud_project: str | None = None,
) -> None:
    """Process the template directory and create a new project.

    Args:
        agent_name: Name of the agent template to use
        template_dir: Directory containing the template files
        project_name: Name of the project to create
        deployment_target: Optional deployment target (agent_engine or cloud_run)
        cicd_runner: Optional CI/CD runner to use
        include_data_ingestion: Whether to include data pipeline components
        datastore: Optional datastore type for data ingestion
        session_type: Optional session type for cloud_run deployment
        output_dir: Optional output directory path, defaults to current directory
        remote_template_path: Optional path to remote template for overlay
        remote_config: Optional remote template configuration
        in_folder: Whether to template directly into the output directory instead of creating a subdirectory
        cli_overrides: Optional CLI override values that should take precedence over template config
        agent_garden: Whether this deployment is from Agent Garden
        google_api_key: Optional Google AI Studio API key to generate .env file
        google_cloud_project: Optional GCP project ID to populate .env file
    """
    logging.debug(f"Processing template from {template_dir}")
    logging.debug(f"Project name: {project_name}")
    logging.debug(f"Include pipeline: {datastore}")
    logging.debug(f"Output directory: {output_dir}")

    # Create console for user feedback
    console = Console()

    def get_agent_directory(
        template_config: dict[str, Any], cli_overrides: dict[str, Any] | None = None
    ) -> str:
        """Get agent directory with CLI override support.

        Handles the special case where agent_directory is "." (flat structure),
        deriving the target directory name from the remote template folder name.
        """
        agent_dir = None
        if (
            cli_overrides
            and "settings" in cli_overrides
            and "agent_directory" in cli_overrides["settings"]
        ):
            agent_dir = cli_overrides["settings"]["agent_directory"]
        else:
            agent_dir = template_config.get("settings", {}).get(
                "agent_directory", "app"
            )

        # Handle "." (flat structure) - derive target from folder name
        if agent_dir == ".":
            if remote_template_path:
                # Derive from remote template folder name
                folder_name = remote_template_path.name.replace("-", "_")
                logging.debug(
                    f"Flat structure (-dir .): deriving target '{folder_name}' from folder name"
                )
                agent_dir = folder_name
            else:
                # Fallback to "app" for non-remote templates
                logging.debug("Flat structure (-dir .): using 'app' as fallback")
                agent_dir = "app"

        # Validate agent directory is a valid Python identifier
        validate_agent_directory_name(agent_dir)

        return agent_dir

    # Handle remote vs local templates
    is_remote = remote_template_path is not None

    if is_remote:
        # For remote templates, determine the base template
        base_template_name = get_base_template_name(remote_config or {})
        agent_path = (
            pathlib.Path(__file__).parent.parent.parent / "agents" / base_template_name
        )
        logging.debug(f"Remote template using base: {base_template_name}")
    elif cli_overrides and cli_overrides.get("base_template"):
        # For in-folder mode with base_template override, use the agent template
        base_template_name = cli_overrides["base_template"]
        agent_path = (
            pathlib.Path(__file__).parent.parent.parent / "agents" / base_template_name
        )
        logging.debug(f"Using base template override: {base_template_name}")
    else:
        # For local templates, use the existing logic
        base_template_name = (
            agent_name  # agent_name is the base template for local templates
        )
        agent_path = template_dir.parent  # Get parent of template dir

    logging.debug(f"agent path: {agent_path}")
    logging.debug(f"agent path exists: {agent_path.exists()}")
    logging.debug(
        f"agent path contents: {list(agent_path.iterdir()) if agent_path.exists() else 'N/A'}"
    )

    # Use provided output_dir or current directory
    destination_dir = output_dir if output_dir else pathlib.Path.cwd()

    # Create output directory if it doesn't exist
    if not destination_dir.exists():
        destination_dir.mkdir(parents=True)

    # Create a new temporary directory and use it as our working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)

        # Important: Store the original working directory
        original_dir = pathlib.Path.cwd()

        try:
            os.chdir(temp_path)  # Change to temp directory

            # Extract agent sample info for labeling when using agent garden with remote templates
            agent_sample_id, agent_sample_publisher = _extract_agent_garden_labels(
                agent_garden, remote_spec, remote_template_path
            )

            # Create the cookiecutter template structure
            cookiecutter_template = temp_path / "template"
            cookiecutter_template.mkdir(parents=True)
            project_template = cookiecutter_template / "{{cookiecutter.project_name}}"
            project_template.mkdir(parents=True)

            # Get agent directory and language from config early for use in file copying
            if remote_config:
                early_config = remote_config
            else:
                template_path = pathlib.Path(template_dir)
                early_config = load_template_config(template_path)
            agent_directory = get_agent_directory(early_config, cli_overrides)
            language = get_agent_language(agent_name, remote_config)

            # Base paths for template structure
            base_templates_path = (
                pathlib.Path(__file__).parent.parent.parent / "base_templates"
            )

            # 1. First copy shared base template files (language-agnostic)
            shared_base_path = base_templates_path / "_shared"
            if shared_base_path.exists():
                copy_files(
                    shared_base_path,
                    project_template,
                    agent_name,
                    overwrite=True,
                    agent_directory=agent_directory,
                )
                logging.debug(
                    f"1a. Copied shared base template from {shared_base_path}"
                )

            # 1b. Copy language-specific base template files
            language_base_path = base_templates_path / language
            if language_base_path.exists():
                copy_files(
                    language_base_path,
                    project_template,
                    agent_name,
                    overwrite=True,
                    agent_directory=agent_directory,
                )
                logging.debug(
                    f"1b. Copied {language} base template from {language_base_path}"
                )
            else:
                raise FileNotFoundError(
                    f"Language base template not found: {language_base_path}"
                )

            # 2. Process deployment target if specified
            if deployment_target and deployment_target in DEPLOYMENT_TARGETS:
                deployment_targets_path = (
                    pathlib.Path(__file__).parent.parent.parent / "deployment_targets"
                )

                # 2a. Copy shared deployment target files (language-agnostic)
                shared_deployment_path = (
                    deployment_targets_path / deployment_target / "_shared"
                )
                if shared_deployment_path.exists():
                    copy_files(
                        shared_deployment_path,
                        project_template,
                        agent_name=agent_name,
                        overwrite=True,
                        agent_directory=agent_directory,
                    )
                    logging.debug(
                        f"2a. Copied shared deployment files from {shared_deployment_path}"
                    )

                # 2b. Copy language-specific deployment target files
                language_deployment_path = (
                    deployment_targets_path / deployment_target / language
                )
                if language_deployment_path.exists():
                    copy_files(
                        language_deployment_path,
                        project_template,
                        agent_name=agent_name,
                        overwrite=True,
                        agent_directory=agent_directory,
                    )
                    logging.debug(
                        f"2b. Copied {language} deployment files from {language_deployment_path}"
                    )

            # 3. Copy data ingestion files if needed
            if include_data_ingestion and datastore:
                logging.debug(
                    f"3. Including data processing files with datastore: {datastore}"
                )
                copy_data_ingestion_files(project_template, datastore)

            # 4. Skip remote template files during cookiecutter processing
            # Remote files will be copied after cookiecutter to avoid Jinja conflicts
            if is_remote and remote_template_path:
                logging.debug(
                    "4. Skipping remote template files during cookiecutter processing - will copy after templating"
                )

            # Load and validate template config first
            if remote_config:
                config = remote_config
            else:
                template_path = pathlib.Path(template_dir)
                config = load_template_config(template_path)

            if not config:
                raise ValueError("Could not load template config")

            # Validate deployment target
            available_targets = config.get("settings", {}).get("deployment_targets", [])
            if isinstance(available_targets, str):
                available_targets = [available_targets]

            if deployment_target and deployment_target not in available_targets:
                raise ValueError(
                    f"Invalid deployment target '{deployment_target}'. Available targets: {available_targets}"
                )

            # Use the already loaded config
            template_config = config

            # Process frontend files (after config is properly loaded with CLI overrides)
            frontend_type = template_config.get("settings", {}).get(
                "frontend_type", DEFAULT_FRONTEND
            )
            copy_frontend_files(frontend_type, project_template)
            logging.debug(f"5. Processed frontend files for type: {frontend_type}")

            # 6. Copy agent-specific files to override base template (using final config)
            if agent_path.exists():
                agent_directory = get_agent_directory(template_config, cli_overrides)

                # For remote/local templates with base_template override, always use "app"
                # as the source directory since base templates store agent code in "app/"
                if is_remote or (cli_overrides and cli_overrides.get("base_template")):
                    template_agent_directory = "app"
                else:
                    # Get the template's default agent directory (usually "app")
                    template_agent_directory = template_config.get("settings", {}).get(
                        "agent_directory", "app"
                    )

                # Copy agent directory (always from "app" to target directory)
                source_agent_folder = agent_path / template_agent_directory
                logging.debug(
                    f"6. Source agent folder: {source_agent_folder}, exists: {source_agent_folder.exists()}"
                )
                target_agent_folder = project_template / agent_directory
                if source_agent_folder.exists():
                    logging.debug(
                        f"6. Copying agent folder {template_agent_directory} -> {agent_directory} with override"
                    )
                    copy_files(
                        source_agent_folder,
                        target_agent_folder,
                        agent_name,
                        overwrite=True,
                        agent_directory=agent_directory,
                    )

                # Copy other folders (frontend, tests, notebooks)
                other_folders = ["frontend", "tests", "notebooks"]
                for folder in other_folders:
                    agent_folder = agent_path / folder
                    project_folder = project_template / folder
                    if agent_folder.exists():
                        logging.debug(f"6. Copying {folder} folder with override")
                        copy_files(
                            agent_folder,
                            project_folder,
                            agent_name,
                            overwrite=True,
                            agent_directory=agent_directory,
                        )

            # Check if data processing should be included
            if include_data_ingestion and datastore:
                logging.debug(
                    f"Including data processing files with datastore: {datastore}"
                )
                copy_data_ingestion_files(project_template, datastore)

            # Create cookiecutter.json in the template root
            # Get settings from template config
            settings = template_config.get("settings", {})
            extra_deps = settings.get("extra_dependencies", [])
            frontend_type = settings.get("frontend_type", DEFAULT_FRONTEND)
            tags = settings.get("tags", ["None"])

            # Load adk-cheatsheet.md and llm.txt for injection
            adk_cheatsheet_path = (
                pathlib.Path(__file__).parent.parent.parent
                / "resources"
                / "docs"
                / "adk-cheatsheet.md"
            )
            with open(adk_cheatsheet_path, encoding="utf-8") as md_file:
                adk_cheatsheet_content = md_file.read()

            llm_txt_path = (
                pathlib.Path(__file__).parent.parent.parent.parent / "llm.txt"
            )
            with open(llm_txt_path, encoding="utf-8") as txt_file:
                llm_txt_content = txt_file.read()

            cookiecutter_config = {
                "project_name": project_name,
                "agent_name": agent_name,
                "package_version": get_current_version(),
                "generated_at": datetime.now(tz=UTC).isoformat(),
                "agent_description": template_config.get("description", ""),
                "example_question": template_config.get("example_question", "").ljust(
                    61
                ),
                "settings": settings,
                "tags": tags,
                "is_adk": "adk" in tags,
                "is_adk_live": "adk_live" in tags,
                "is_a2a": "a2a" in tags,
                "language": language,
                "deployment_target": deployment_target or "",
                "cicd_runner": cicd_runner or "google_cloud_build",
                "session_type": session_type or "",
                "frontend_type": frontend_type,
                "extra_dependencies": [extra_deps],
                "data_ingestion": include_data_ingestion,
                "datastore_type": datastore if datastore else "",
                "agent_directory": get_agent_directory(template_config, cli_overrides),
                "agent_garden": agent_garden,
                "agent_sample_id": agent_sample_id or "",
                "agent_sample_publisher": agent_sample_publisher or "",
                "use_google_api_key": bool(google_api_key),
                "google_cloud_project": google_cloud_project or "your-gcp-project-id",
                "adk_cheatsheet": adk_cheatsheet_content,
                "llm_txt": llm_txt_content,
                "_copy_without_render": [
                    "*.ipynb",  # Don't render notebooks
                    "*.json",  # Don't render JSON files
                    "*.tsx",  # Don't render TypeScript React files
                    "*.ts",  # Don't render TypeScript files
                    "*.jsx",  # Don't render JavaScript React files
                    "*.js",  # Don't render JavaScript files
                    "*.css",  # Don't render CSS files
                    "*.sum",  # Don't render Go sum files
                    "e2e/**/*",  # Don't render Go e2e test files (contain Go {{ }} syntax)
                    "frontend/**/*",  # Don't render frontend directory recursively
                    "notebooks/*",  # Don't render notebooks directory
                    ".git/*",  # Don't render git directory
                    "__pycache__/*",  # Don't render cache
                    "**/__pycache__/*",
                    ".pytest_cache/*",
                    ".venv/*",
                    "**/.venv/*",  # Don't render .venv at any depth
                    "*templates.py",  # Don't render templates files
                    "Makefile",  # Don't render Makefile - handled by render_and_merge_makefiles
                ],
            }

            with open(
                cookiecutter_template / "cookiecutter.json", "w", encoding="utf-8"
            ) as json_file:
                json.dump(cookiecutter_config, json_file, indent=4)

            logging.debug(f"Template structure created at {cookiecutter_template}")
            logging.debug(
                f"Directory contents: {list(cookiecutter_template.iterdir())}"
            )

            # Process the template
            cookiecutter(
                str(cookiecutter_template),
                no_input=True,
                overwrite_if_exists=True,
                extra_context={
                    "project_name": project_name,
                    "agent_name": agent_name,
                },
            )
            logging.debug("Template processing completed successfully")

            # Now overlay remote template files if present (after cookiecutter processing)
            if is_remote and remote_template_path:
                generated_project_dir = temp_path / project_name
                logging.debug(
                    f"Copying remote template files from {remote_template_path} to {generated_project_dir}"
                )

                # Preserve base template README and pyproject.toml files before overwriting
                preserve_files = ["README.md"]

                # Only preserve pyproject.toml if the remote template doesn't have starter pack integration
                remote_pyproject = remote_template_path / "pyproject.toml"
                if remote_pyproject.exists():
                    try:
                        remote_pyproject_content = remote_pyproject.read_text()
                        # Check for starter pack integration markers
                        has_starter_pack_integration = (
                            "[tool.agent-starter-pack]" in remote_pyproject_content
                        )
                        if not has_starter_pack_integration:
                            preserve_files.append("pyproject.toml")
                            logging.debug(
                                "Remote pyproject.toml lacks starter pack integration - will preserve base template version"
                            )
                        else:
                            logging.debug(
                                "Remote pyproject.toml has starter pack integration - using remote version only"
                            )
                    except Exception as e:
                        logging.warning(
                            f"Could not read remote pyproject.toml: {e}. Will preserve base template version."
                        )
                        preserve_files.append("pyproject.toml")
                else:
                    preserve_files.append("pyproject.toml")

                for preserve_file in preserve_files:
                    base_file = generated_project_dir / preserve_file
                    remote_file = remote_template_path / preserve_file

                    if base_file.exists() and remote_file.exists():
                        # Preserve the base template file with starter_pack prefix
                        base_name = pathlib.Path(preserve_file).stem
                        extension = pathlib.Path(preserve_file).suffix
                        preserved_file = (
                            generated_project_dir
                            / f"starter_pack_{base_name}{extension}"
                        )
                        shutil.copy2(base_file, preserved_file)
                        logging.debug(
                            f"Preserved base template {preserve_file} as starter_pack_{base_name}{extension}"
                        )

                # Check if this is a flat structure template
                # Flat structure can be detected via:
                # 1. Auto-detection (is_flat_structure flag in remote_config)
                # 2. source_agent_directory set to "." in config
                # 3. CLI override with -dir . (agent_directory = ".")
                cli_agent_dir = (
                    cli_overrides.get("settings", {}).get("agent_directory")
                    if cli_overrides
                    else None
                )
                is_flat_structure = (cli_agent_dir == ".") or (
                    remote_config and remote_config.get("is_flat_structure", False)
                )

                if is_flat_structure:
                    # For flat structures, Python files go to agent_directory
                    logging.debug(
                        f"Flat structure detected: copying files to {agent_directory}/"
                    )
                    copy_flat_structure_agent_files(
                        remote_template_path,
                        generated_project_dir,
                        agent_directory,
                    )
                else:
                    # Standard structure: copy as-is
                    copy_files(
                        remote_template_path,
                        generated_project_dir,
                        agent_name=agent_name,
                        overwrite=True,
                        agent_directory=agent_directory,
                    )
                logging.debug("Remote template files copied successfully")

                # Handle ADK agent compatibility
                is_adk = "adk" in base_template_name.lower()
                agent_py_path = generated_project_dir / agent_directory / "agent.py"
                root_agent_yaml = (
                    generated_project_dir / agent_directory / "root_agent.yaml"
                )

                if is_adk:
                    # Check for YAML config agent first
                    if root_agent_yaml.exists():
                        _generate_yaml_agent_shim(
                            agent_py_path, agent_directory, console
                        )
                    elif agent_py_path.exists():
                        # Inject app object if missing (backward compatibility)
                        _inject_app_object_if_missing(
                            agent_py_path, agent_directory, console
                        )

            # Move the generated project to the final destination
            generated_project_dir = temp_path / project_name

            if in_folder:
                # For in-folder mode, copy files directly to the destination directory
                final_destination = destination_dir
                logging.debug(
                    f"In-folder mode: copying files from {generated_project_dir} to {final_destination}"
                )

                if generated_project_dir.exists():
                    # Copy all files from generated project to destination directory
                    for item in generated_project_dir.iterdir():
                        dest_item = final_destination / item.name

                        # Special handling for README files - always preserve existing README
                        # Special handling for pyproject.toml files - only preserve for in-folder updates
                        should_preserve_file = item.name.lower().startswith(
                            "readme"
                        ) or (item.name == "pyproject.toml" and in_folder)
                        if (
                            should_preserve_file
                            and (final_destination / item.name).exists()
                        ):
                            # The existing file stays, use base template file with starter_pack prefix
                            base_name = item.stem
                            extension = item.suffix
                            dest_item = (
                                final_destination
                                / f"starter_pack_{base_name}{extension}"
                            )

                            # Try to use base template file instead of templated file
                            # Use language-specific base path
                            base_file = language_base_path / item.name
                            if base_file.exists():
                                logging.debug(
                                    f"{item.name} conflict: preserving existing {item.name}, using base template {item.name} as starter_pack_{base_name}{extension}"
                                )
                                # Process the base template file through cookiecutter
                                try:
                                    import tempfile as tmp_module

                                    with (
                                        tmp_module.TemporaryDirectory() as temp_file_dir
                                    ):
                                        temp_file_path = pathlib.Path(temp_file_dir)

                                        # Create a minimal cookiecutter structure for just the file
                                        file_template_dir = (
                                            temp_file_path / "file_template"
                                        )
                                        file_template_dir.mkdir()
                                        file_project_dir = (
                                            file_template_dir
                                            / "{{cookiecutter.project_name}}"
                                        )
                                        file_project_dir.mkdir()

                                        # Copy base file to template structure
                                        shutil.copy2(
                                            base_file, file_project_dir / item.name
                                        )

                                        # Create cookiecutter.json with same config as main template
                                        with open(
                                            file_template_dir / "cookiecutter.json",
                                            "w",
                                            encoding="utf-8",
                                        ) as config_file:
                                            json.dump(
                                                cookiecutter_config,
                                                config_file,
                                                indent=4,
                                            )

                                        # Process the file template
                                        cookiecutter(
                                            str(file_template_dir),
                                            no_input=True,
                                            overwrite_if_exists=True,
                                            output_dir=str(temp_file_path),
                                            extra_context={
                                                "project_name": project_name,
                                                "agent_name": agent_name,
                                            },
                                        )

                                        # Copy the processed file
                                        processed_file = (
                                            temp_file_path / project_name / item.name
                                        )
                                        if processed_file.exists():
                                            shutil.copy2(processed_file, dest_item)
                                        else:
                                            # Fallback to original behavior if processing fails
                                            shutil.copy2(item, dest_item)

                                except Exception as e:
                                    logging.warning(
                                        f"Failed to process base template {item.name}: {e}. Using templated {item.name} instead."
                                    )
                                    shutil.copy2(item, dest_item)
                            else:
                                # Fallback to original behavior if base file doesn't exist
                                logging.debug(
                                    f"{item.name} conflict: preserving existing {item.name}, saving templated {item.name} as starter_pack_{base_name}{extension}"
                                )
                                shutil.copy2(item, dest_item)
                        else:
                            # Normal file copying
                            if item.is_dir():
                                if dest_item.exists():
                                    shutil.rmtree(dest_item)
                                shutil.copytree(item, dest_item, dirs_exist_ok=True)
                            else:
                                shutil.copy2(item, dest_item)
                    logging.debug(
                        f"Project files successfully copied to {final_destination}"
                    )
            else:
                # Standard mode: create project subdirectory
                final_destination = destination_dir / project_name
                logging.debug(
                    f"Standard mode: moving project from {generated_project_dir} to {final_destination}"
                )

                if generated_project_dir.exists():
                    # Check for existing README and pyproject.toml files before removing destination
                    existing_preserved_files = []
                    if final_destination.exists():
                        for item in final_destination.iterdir():
                            if item.is_file() and (
                                item.name.lower().startswith("readme")
                                or item.name == "pyproject.toml"
                            ):
                                existing_preserved_files.append(
                                    (item.name, item.read_text())
                                )
                        shutil.rmtree(final_destination)

                    shutil.copytree(
                        generated_project_dir, final_destination, dirs_exist_ok=True
                    )

                    # Restore existing README and pyproject.toml files with starter_pack prefix
                    for file_name, file_content in existing_preserved_files:
                        base_name = pathlib.Path(file_name).stem
                        extension = pathlib.Path(file_name).suffix
                        preserved_file_path = (
                            final_destination / f"starter_pack_{base_name}{extension}"
                        )
                        preserved_file_path.write_text(file_content)
                        logging.debug(
                            f"File preservation: existing {file_name} preserved as starter_pack_{base_name}{extension}"
                        )

                    logging.debug(
                        f"Project successfully created at {final_destination}"
                    )

            # Always check if the project was successfully created before proceeding
            if not final_destination.exists():
                logging.error(
                    f"Final destination directory not found at {final_destination}"
                )
                raise FileNotFoundError(
                    f"Final destination directory not found at {final_destination}"
                )

            # Render and merge Makefiles.
            # If it's a local template, remote_template_path will be None,
            # and only the base Makefile will be rendered.
            # Use language-specific base path for Makefile
            makefile_base_path = language_base_path
            render_and_merge_makefiles(
                base_template_path=makefile_base_path,
                final_destination=final_destination,
                cookiecutter_config=cookiecutter_config,
                remote_template_path=remote_template_path,
            )

            # Delete appropriate files based on ADK tag
            agent_directory = get_agent_directory(template_config, cli_overrides)

            # Handle YAML config agents for in-folder mode
            # This runs after all files have been copied to the final destination
            # Use force=True because the user's root_agent.yaml takes precedence
            # over the base template's agent.py
            if in_folder:
                final_agent_py_path = final_destination / agent_directory / "agent.py"
                final_root_agent_yaml = (
                    final_destination / agent_directory / "root_agent.yaml"
                )
                if final_root_agent_yaml.exists():
                    _generate_yaml_agent_shim(
                        final_agent_py_path, agent_directory, console, force=True
                    )

            # Apply conditional file logic (Windows-compatible replacement for Jinja2 filenames)
            conditional_config = {
                "agent_name": agent_name,
                "deployment_target": deployment_target,
                "cicd_runner": cicd_runner or "google_cloud_build",
                "is_adk": "adk" in tags,
                "is_adk_live": "adk_live" in tags,
                "is_a2a": "a2a" in tags,
            }
            apply_conditional_files(
                final_destination, conditional_config, agent_directory
            )

            # Clean up unused_* files and directories created by conditional templates
            import glob

            unused_patterns = [
                final_destination / "unused_*",
                final_destination / "**" / "unused_*",
            ]

            for pattern in unused_patterns:
                for unused_path_str in glob.glob(str(pattern), recursive=True):
                    unused_path = pathlib.Path(unused_path_str)
                    if unused_path.exists():
                        if unused_path.is_dir():
                            shutil.rmtree(unused_path)
                            logging.debug(f"Deleted unused directory: {unused_path}")
                        else:
                            unused_path.unlink()
                            logging.debug(f"Deleted unused file: {unused_path}")

            # Clean up additional files for prototype/minimal mode (cicd_runner == "skip")
            if cicd_runner == "skip":
                # Remove deployment folder
                deployment_dir = final_destination / "deployment"
                if deployment_dir.exists():
                    shutil.rmtree(deployment_dir)
                    logging.debug(f"Prototype mode: deleted {deployment_dir}")

                # Remove load_test folder
                load_test_dir = final_destination / "tests" / "load_test"
                if load_test_dir.exists():
                    shutil.rmtree(load_test_dir)
                    logging.debug(f"Prototype mode: deleted {load_test_dir}")

                # Remove notebooks folder
                notebooks_dir = final_destination / "notebooks"
                if notebooks_dir.exists():
                    shutil.rmtree(notebooks_dir)
                    logging.debug(f"Prototype mode: deleted {notebooks_dir}")

            # Handle pyproject.toml and uv.lock files (Python only)
            if language == "python":
                if is_remote and remote_template_path:
                    # For remote templates, use their pyproject.toml and uv.lock if they exist
                    remote_pyproject = remote_template_path / "pyproject.toml"
                    remote_uv_lock = remote_template_path / "uv.lock"

                    if remote_pyproject.exists():
                        shutil.copy2(
                            remote_pyproject, final_destination / "pyproject.toml"
                        )
                        logging.debug("Used pyproject.toml from remote template")

                    if remote_uv_lock.exists():
                        shutil.copy2(remote_uv_lock, final_destination / "uv.lock")
                        logging.debug("Used uv.lock from remote template")
                elif deployment_target:
                    # For local templates, use the existing logic
                    lock_path = (
                        pathlib.Path(__file__).parent.parent.parent
                        / "resources"
                        / "locks"
                        / f"uv-{agent_name}-{deployment_target}.lock"
                    )
                    logging.debug(f"Looking for lock file at: {lock_path}")
                    logging.debug(f"Lock file exists: {lock_path.exists()}")
                    if not lock_path.exists():
                        raise FileNotFoundError(f"Lock file not found: {lock_path}")
                    # Copy and rename to uv.lock in the project directory
                    shutil.copy2(lock_path, final_destination / "uv.lock")
                    logging.debug(
                        f"Copied lock file from {lock_path} to {final_destination}/uv.lock"
                    )

                    # Replace cookiecutter project name with actual project name in lock file
                    lock_file_path = final_destination / "uv.lock"
                    with open(lock_file_path, "r+", encoding="utf-8") as lock_file:
                        content = lock_file.read()
                        lock_file.seek(0)
                        lock_file.write(
                            content.replace(
                                "{{cookiecutter.project_name}}", project_name
                            )
                        )
                        lock_file.truncate()
                    logging.debug(
                        f"Updated project name in lock file at {lock_file_path}"
                    )

            # Generate .env file for Google API Key if provided
            if google_api_key:
                if language == "go":
                    # For Go templates, update the root .env file
                    env_file_path = final_destination / ".env"
                    env_content = f"""# Local development configuration
# Using Google AI Studio API Key

GOOGLE_API_KEY={google_api_key}
"""
                    env_file_path.write_text(env_content)
                    logging.debug(f"Updated .env file at {env_file_path}")
                    console.print(
                        "📝 Updated [cyan].env[/cyan] file for Google AI Studio"
                    )
                else:
                    # For Python templates, create .env in agent directory
                    env_file_path = final_destination / agent_directory / ".env"
                    env_content = f"""# AI Studio Configuration
GOOGLE_API_KEY={google_api_key}
"""
                    env_file_path.write_text(env_content)
                    logging.debug(f"Generated .env file at {env_file_path}")
                    console.print(
                        f"📝 Generated .env file at [cyan]{agent_directory}/.env[/cyan] "
                        "for Google AI Studio"
                    )

        except Exception as e:
            logging.error(f"Failed to process template: {e!s}")
            raise

        finally:
            # Always restore the original working directory
            os.chdir(original_dir)


def should_exclude_path(
    path: pathlib.Path, agent_name: str, agent_directory: str = "app"
) -> bool:
    """Determine if a path should be excluded based on the agent type."""
    if agent_name == "adk_live":
        # Exclude the unit test utils folder and agent utils folder for adk_live
        if "tests/unit/test_utils" in str(path) or f"{agent_directory}/utils" in str(
            path
        ):
            logging.debug(f"Excluding path for adk_live: {path}")
            return True
    return False


def copy_files(
    src: pathlib.Path,
    dst: pathlib.Path,
    agent_name: str | None = None,
    overwrite: bool = False,
    agent_directory: str = "app",
) -> None:
    """
    Copy files with configurable behavior for exclusions and overwrites.

    Args:
        src: Source path
        dst: Destination path
        agent_name: Name of the agent (for agent-specific exclusions)
        overwrite: Whether to overwrite existing files (True) or skip them (False)
        agent_directory: Name of the agent directory (for agent-specific exclusions)
    """

    def should_skip(path: pathlib.Path) -> bool:
        """Determine if a file/directory should be skipped during copying."""
        if path.suffix in [".pyc"]:
            return True
        if "__pycache__" in str(path) or path.name == "__pycache__":
            return True
        if ".git" in path.parts:
            return True
        if agent_name is not None and should_exclude_path(
            path, agent_name, agent_directory
        ):
            return True
        if path.is_dir() and path.name == ".template":
            return True
        return False

    def log_windows_path_warning(path: pathlib.Path) -> None:
        """Log a warning if path exceeds Windows MAX_PATH limit."""
        if sys.platform == "win32":
            path_str = str(path.absolute())
            if len(path_str) >= 260:
                logging.error(
                    f"Path length ({len(path_str)} chars) may exceed Windows limit. Try using a shorter output directory."
                )

    if src.is_dir():
        if not dst.exists():
            try:
                dst.mkdir(parents=True)
                logging.debug(f"Created directory: {dst}")
            except OSError as e:
                logging.error(f"Failed to create directory: {dst}")
                logging.error(f"Error: {e}")
                raise
        for item in src.iterdir():
            if should_skip(item):
                logging.debug(f"Skipping file/directory: {item}")
                continue

            d = dst / item.name
            if item.is_dir():
                copy_files(item, d, agent_name, overwrite, agent_directory)
            else:
                if overwrite or not d.exists():
                    try:
                        # Ensure parent directory exists before copying
                        d.parent.mkdir(parents=True, exist_ok=True)
                        logging.debug(f"Copying file: {item} -> {d}")
                        shutil.copy2(item, d)
                    except OSError:
                        logging.error(f"Failed to copy: {item} -> {d}")
                        log_windows_path_warning(d)
                        raise
                else:
                    logging.debug(f"Skipping existing file: {d}")
    else:
        if not should_skip(src):
            if overwrite or not dst.exists():
                try:
                    # Ensure parent directory exists before copying
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    logging.debug(f"Copying file: {src} -> {dst}")
                    shutil.copy2(src, dst)
                except OSError:
                    logging.error(f"Failed to copy: {src} -> {dst}")
                    log_windows_path_warning(dst)
                    raise


def copy_frontend_files(frontend_type: str, project_template: pathlib.Path) -> None:
    """Copy files from the specified frontend folder directly to project root."""
    # Skip copying if frontend_type is "None" or empty
    if not frontend_type or frontend_type == "None":
        logging.debug("Frontend type is 'None' or empty, skipping frontend files")
        return

    # Skip copying if frontend_type is "inspector" - it's installed at runtime via make inspector
    if frontend_type == "inspector":
        logging.debug("Frontend type is 'inspector', skipping (installed at runtime)")
        return

    # Get the frontends directory path
    frontends_path = (
        pathlib.Path(__file__).parent.parent.parent / "frontends" / frontend_type
    )

    if frontends_path.exists():
        logging.debug(f"Copying frontend files from {frontends_path}")
        # Copy frontend files directly to project root instead of a nested frontend directory
        copy_files(frontends_path, project_template, overwrite=True)
    else:
        logging.warning(f"Frontend type directory not found: {frontends_path}")
        # Don't fall back to default if it's "None" - just skip
        if DEFAULT_FRONTEND != "None":
            logging.info(f"Falling back to default frontend: {DEFAULT_FRONTEND}")
            copy_frontend_files(DEFAULT_FRONTEND, project_template)
        else:
            logging.debug("No default frontend configured, skipping frontend files")


def copy_deployment_files(
    deployment_target: str,
    agent_name: str,
    project_template: pathlib.Path,
    agent_directory: str = "app",
) -> None:
    """Copy files from the specified deployment target folder."""
    if not deployment_target:
        return

    deployment_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "deployment_targets"
        / deployment_target
    )

    if deployment_path.exists():
        logging.debug(f"Copying deployment files from {deployment_path}")
        # Pass agent_name to respect agent-specific exclusions
        copy_files(
            deployment_path,
            project_template,
            agent_name=agent_name,
            overwrite=True,
            agent_directory=agent_directory,
        )
    else:
        logging.warning(f"Deployment target directory not found: {deployment_path}")


def copy_flat_structure_agent_files(
    src: pathlib.Path,
    dst: pathlib.Path,
    agent_directory: str,
) -> None:
    """Copy agent files from a flat structure template to the agent directory.

    For flat structure templates, Python files (*.py) in the root are copied
    to the agent directory, while other files are copied to the project root.

    Args:
        src: Source path (template root with flat structure)
        dst: Destination path (project root)
        agent_directory: Target agent directory name
    """
    agent_dst = dst / agent_directory
    agent_dst.mkdir(parents=True, exist_ok=True)

    # Files that should go to agent directory
    agent_file_extensions = {".py"}
    # Files to skip entirely
    skip_files = {"pyproject.toml", "uv.lock", "README.md", ".gitignore"}

    for item in src.iterdir():
        if item.name.startswith(".") or item.name in skip_files:
            continue
        if item.name == "__pycache__":
            continue

        if item.is_file():
            if item.suffix in agent_file_extensions:
                # Python files go to agent directory
                dest_file = agent_dst / item.name
                logging.debug(
                    f"Flat structure: copying {item.name} -> {agent_directory}/{item.name}"
                )
                shutil.copy2(item, dest_file)
            else:
                # Other files go to project root
                dest_file = dst / item.name
                logging.debug(f"Flat structure: copying {item.name} -> {item.name}")
                shutil.copy2(item, dest_file)
        elif item.is_dir():
            # Directories are copied to project root (preserving structure)
            dest_dir = dst / item.name
            logging.debug(f"Flat structure: copying directory {item.name}")
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(item, dest_dir)
