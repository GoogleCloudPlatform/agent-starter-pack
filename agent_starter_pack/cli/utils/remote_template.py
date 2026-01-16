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

import logging
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from jinja2 import Environment
from packaging import version as pkg_version
from rich.console import Console


@dataclass
class RemoteTemplateSpec:
    """Parsed remote template specification."""

    repo_url: str
    template_path: str
    git_ref: str
    is_adk_samples: bool = False


def parse_agent_spec(agent_spec: str) -> RemoteTemplateSpec | None:
    """Parse agent specification to determine if it's a remote template.

    Args:
        agent_spec: Agent specification string

    Returns:
        RemoteTemplateSpec if remote template, None if local template
    """
    # Check for local@ prefix
    if agent_spec.startswith("local@"):
        return None

    # Check for adk@ shortcut
    if agent_spec.startswith("adk@"):
        sample_name = agent_spec[4:]  # Remove "adk@" prefix
        return RemoteTemplateSpec(
            repo_url="https://github.com/google/adk-samples",
            template_path=f"python/agents/{sample_name}",
            git_ref="main",
            is_adk_samples=True,
        )

    # GitHub /tree/ URL pattern
    tree_pattern = r"^(https?://[^/]+/[^/]+/[^/]+)/tree/([^/]+)/(.*)$"
    match = re.match(tree_pattern, agent_spec)
    if match:
        repo_url = match.group(1)
        git_ref = match.group(2)
        template_path = match.group(3)
        return RemoteTemplateSpec(
            repo_url=repo_url,
            template_path=template_path.strip("/"),
            git_ref=git_ref,
        )

    # General remote pattern: <repo_url>[/<path>][@<ref>]
    # Handles github.com, gitlab.com, etc.
    remote_pattern = r"^(https?://[^/]+/[^/]+/[^/]+)(?:/(.*?))?(?:@([^/]+))?/?$"
    match = re.match(remote_pattern, agent_spec)
    if match:
        repo_url = match.group(1)
        template_path_with_ref = match.group(2) or ""
        git_ref_from_url = match.group(3)

        # Separate path and ref if ref is part of the path
        template_path = template_path_with_ref
        git_ref = git_ref_from_url or "main"

        if "@" in template_path:
            path_parts = template_path.split("@")
            template_path = path_parts[0]
            git_ref = path_parts[1]

        # Check if this is the ADK samples repository
        is_adk_samples = repo_url == "https://github.com/google/adk-samples"

        return RemoteTemplateSpec(
            repo_url=repo_url,
            template_path=template_path.strip("/"),
            git_ref=git_ref,
            is_adk_samples=is_adk_samples,
        )

    # GitHub shorthand: <org>/<repo>[/<path>][@<ref>]
    github_shorthand_pattern = r"^([^/]+)/([^/]+)(?:/(.*?))?(?:@([^/]+))?/?$"
    match = re.match(github_shorthand_pattern, agent_spec)
    if match and "/" in agent_spec:  # Ensure it has at least one slash
        org = match.group(1)
        repo = match.group(2)
        template_path = match.group(3) or ""
        git_ref = match.group(4) or "main"

        # Check if this is the ADK samples repository
        is_adk_samples = org == "google" and repo == "adk-samples"

        return RemoteTemplateSpec(
            repo_url=f"https://github.com/{org}/{repo}",
            template_path=template_path,
            git_ref=git_ref,
            is_adk_samples=is_adk_samples,
        )

    return None


def check_and_execute_with_version_lock(
    template_dir: pathlib.Path,
    original_agent_spec: str | None = None,
    locked: bool = False,
    project_name: str | None = None,
) -> bool:
    """Check if remote template has agent-starter-pack version lock and execute if found.

    Args:
        template_dir: Path to the fetched template directory
        original_agent_spec: The original agent spec (remote URL) to replace with local path
        locked: Whether this is already a locked execution (prevents recursion)
        project_name: Project name (may have been entered interactively)

    Returns:
        True if version lock was found and executed, False otherwise
    """
    # Skip version locking if we're already in a locked execution (prevents recursion)
    # or if ASP_SKIP_VERSION_LOCK env var is set to "1" (for testing with local ASP)
    if locked or os.environ.get("ASP_SKIP_VERSION_LOCK") == "1":
        return False
    uv_lock_path = template_dir / "uv.lock"
    version = parse_agent_starter_pack_version_from_lock(uv_lock_path)

    if version:
        console = Console()
        console.print(
            f"🔒 Remote template requires agent-starter-pack version {version}",
            style="bold blue",
        )
        console.print(
            f"📦 Switching to version {version}...",
            style="dim",
        )

        # Reconstruct the original command but with version constraint
        import sys

        original_args = sys.argv[1:]  # Skip 'agent-starter-pack' or script name

        # Add version lock specific parameters and handle remote URL replacement
        if original_agent_spec:
            # Check if --agent flag exists in original args
            agent_flag_exists = "--agent" in original_args or "-a" in original_args

            if agent_flag_exists:
                # Replace remote agent spec with local path
                original_args = [
                    f"local@{template_dir}" if arg == original_agent_spec else arg
                    for arg in original_args
                ]
            else:
                # Agent was selected interactively, add --agent flag
                original_args.extend(["--agent", f"local@{template_dir}"])

        # Add project_name if provided interactively (not in original args)
        if project_name:
            # Check if project_name is already in the args (as positional argument)
            # The create command signature is: create [PROJECT_NAME] [OPTIONS]
            # If project_name was provided via CLI, it would be in sys.argv
            # We check by looking for it in the original sys.argv
            if project_name not in sys.argv:
                # Insert project_name as positional argument after 'create'
                # Click is flexible so appending also works if 'create' isn't found
                if "create" in original_args:
                    create_idx = original_args.index("create")
                    original_args.insert(create_idx + 1, project_name)
                else:
                    original_args.append(project_name)

        # Add version lock flags only for ASP versions 0.14.1 and above
        if pkg_version.parse(version) > pkg_version.parse("0.14.1"):
            original_args.extend(["--skip-welcome", "--locked"])

        try:
            # Check if uvx is available
            subprocess.run(["uvx", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print(
                f"❌ Remote template requires agent-starter-pack version {version}, but 'uvx' is not installed",
                style="bold red",
            )
            console.print(
                "💡 Install uv to use version-locked remote templates:",
                style="bold blue",
            )
            console.print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
            console.print(
                "   OR visit: https://docs.astral.sh/uv/getting-started/installation/"
            )
            sys.exit(1)

        try:
            # Execute uvx with the locked version
            cmd = ["uvx", f"agent-starter-pack@{version}", *original_args]
            logging.debug(f"Executing nested command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            return True

        except subprocess.CalledProcessError as e:
            console.print(
                f"❌ Failed to execute with locked version {version}: {e}",
                style="bold red",
            )
            console.print(
                "⚠️  Continuing with current version, but compatibility is not guaranteed",
                style="yellow",
            )
            # Continue with current execution instead of failing completely

    return False


def fetch_remote_template(
    spec: RemoteTemplateSpec,
    original_agent_spec: str | None = None,
    locked: bool = False,
    project_name: str | None = None,
) -> tuple[pathlib.Path, pathlib.Path]:
    """Fetch remote template and return path to template directory.

    Uses Git to clone the remote repository. If the template contains a uv.lock
    with agent-starter-pack version constraint, will execute nested uvx command.

    Args:
        spec: Remote template specification
        original_agent_spec: Original agent spec string (used to prevent recursion)
        locked: Whether this is already a locked execution (prevents recursion)
        project_name: Project name (may have been entered interactively)

    Returns:
        A tuple containing:
        - Path to the fetched template directory.
        - Path to the top-level temporary directory that should be cleaned up.
    """
    temp_dir = tempfile.mkdtemp(prefix="asp_remote_template_")
    temp_path = pathlib.Path(temp_dir)
    repo_path = temp_path / "repo"

    # Attempt Git Clone
    try:
        clone_url = spec.repo_url

        # Build clone command with --single-branch (optimized for branches)
        clone_cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--branch",
            spec.git_ref,
            clone_url,
            str(repo_path),
        ]

        logging.debug(
            f"Attempting to clone remote template with Git: {' '.join(clone_cmd)}"
        )
        # GIT_TERMINAL_PROMPT=0 prevents git from prompting for credentials
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )

        # If clone with --single-branch fails, retry without it (for tags)
        if result.returncode != 0:
            # Check if the error is related to branch not found (indicates it's likely a tag)
            if "Remote branch" in result.stderr or "not found" in result.stderr:
                logging.debug(
                    f"Clone with --single-branch failed, retrying without it (git_ref '{spec.git_ref}' is likely a tag)"
                )
                clone_cmd_without_single_branch = [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    spec.git_ref,
                    clone_url,
                    str(repo_path),
                ]
                subprocess.run(
                    clone_cmd_without_single_branch,
                    capture_output=True,
                    text=True,
                    check=True,
                    encoding="utf-8",
                    env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                )
                logging.debug("Git clone successful (without --single-branch).")
            else:
                # Different error, raise it
                raise subprocess.CalledProcessError(
                    result.returncode, clone_cmd, result.stdout, result.stderr
                )
        else:
            logging.debug("Git clone successful.")
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise RuntimeError(f"Git clone failed: {e.stderr.strip()}") from e

    # Process the successfully fetched template
    try:
        if spec.template_path:
            template_dir = repo_path / spec.template_path
        else:
            template_dir = repo_path

        if not template_dir.exists():
            raise FileNotFoundError(
                f"Template path not found in the repository: {spec.template_path}"
            )

        # Check for version lock and execute nested command if found
        if check_and_execute_with_version_lock(
            template_dir, original_agent_spec, locked, project_name
        ):
            # If we executed with locked version, the nested process will handle everything
            # Clean up and exit successfully
            shutil.rmtree(temp_path, ignore_errors=True)
            # Exit with success since the nested command will handle the rest
            sys.exit(0)

        return template_dir, temp_path
    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_path, ignore_errors=True)
        raise RuntimeError(
            f"An unexpected error occurred after fetching remote template: {e}"
        ) from e


def _detect_flat_structure(template_dir: pathlib.Path) -> bool:
    """Detect if template has a flat structure (agent code in root).

    A flat structure means:
    - agent.py exists directly in the template root
    - No obvious agent subdirectory exists (like 'app/' or folder_name as package)

    Args:
        template_dir: Path to template directory

    Returns:
        True if template has flat structure, False otherwise
    """
    # Check if agent.py exists in root
    agent_py_in_root = (template_dir / "agent.py").exists()
    if not agent_py_in_root:
        return False

    # Check for common agent subdirectory patterns
    folder_name = template_dir.name.replace("-", "_")
    potential_agent_dirs = ["app", folder_name]

    for subdir in potential_agent_dirs:
        subdir_path = template_dir / subdir
        if subdir_path.is_dir() and (subdir_path / "agent.py").exists():
            # Found a proper agent subdirectory
            return False

    logging.debug(
        f"Detected flat structure in {template_dir}: agent.py in root, no agent subdirectory"
    )
    return True


def _infer_agent_directory_for_adk(
    template_dir: pathlib.Path, is_adk_sample: bool
) -> dict[str, Any]:
    """Infer agent configuration for ADK samples only using Python conventions.

    Args:
        template_dir: Path to template directory
        is_adk_sample: Whether this is an ADK sample

    Returns:
        Dictionary with inferred configuration, or empty dict if not ADK sample
    """
    if not is_adk_sample:
        return {}

    # Check for flat structure (agent code in root)
    is_flat = _detect_flat_structure(template_dir)

    # Convert folder name to Python package convention (hyphens to underscores)
    folder_name = template_dir.name
    target_agent_directory = folder_name.replace("-", "_")

    if is_flat:
        logging.debug(
            f"Flat structure detected: source is '.', target agent_directory is '{target_agent_directory}'"
        )
        return {
            "settings": {
                "agent_directory": target_agent_directory,
                "source_agent_directory": ".",  # Special value for flat structure
            },
            "has_explicit_config": False,
            "is_flat_structure": True,
        }

    logging.debug(
        f"Inferred agent_directory '{target_agent_directory}' from folder name '{folder_name}' for ADK sample"
    )

    return {
        "settings": {
            "agent_directory": target_agent_directory,
        },
        "has_explicit_config": False,
    }


def load_remote_template_config(
    template_dir: pathlib.Path,
    cli_overrides: dict[str, Any] | None = None,
    is_adk_sample: bool = False,
) -> dict[str, Any]:
    """Load template configuration from remote template's pyproject.toml with CLI overrides.

    Loads configuration from [tool.agent-starter-pack] section with fallbacks
    to [project] section for name and description if not specified. CLI overrides
    take precedence over all other sources. For ADK samples without explicit config,
    uses smart inference for agent directory naming.

    Args:
        template_dir: Path to template directory
        cli_overrides: Configuration overrides from CLI (takes highest precedence)
        is_adk_sample: Whether this is an ADK sample (enables smart inference)

    Returns:
        Template configuration dictionary with merged sources
    """
    config: dict[str, Any] = {}
    has_explicit_config = False

    # Start with defaults
    defaults = {
        "base_template": "adk",
        "name": template_dir.name,
        "description": "",
        "agent_directory": "app",  # Default for non-ADK samples
    }
    config.update(defaults)

    # Load from pyproject.toml if it exists
    pyproject_path = template_dir / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)

            # Extract the agent-starter-pack configuration
            toml_config = pyproject_data.get("tool", {}).get("agent-starter-pack", {})

            # Fallback to [project] fields if not specified in agent-starter-pack section
            project_info = pyproject_data.get("project", {})

            # Track if we have explicit configuration
            has_explicit_config = bool(toml_config)

            # Apply pyproject.toml configuration (overrides defaults)
            if toml_config:
                config.update(toml_config)
                logging.debug("Found explicit [tool.agent-starter-pack] configuration")

            # Apply [project] fallbacks if not already set
            if "name" not in toml_config and "name" in project_info:
                config["name"] = project_info["name"]

            if "description" not in toml_config and "description" in project_info:
                config["description"] = project_info["description"]

            logging.debug(f"Loaded template config from {pyproject_path}")
        except Exception as e:
            logging.error(f"Error loading pyproject.toml config: {e}")
    else:
        # No pyproject.toml found
        if is_adk_sample:
            logging.debug(
                f"No pyproject.toml found for ADK sample {template_dir.name}, will use inference"
            )
        else:
            logging.debug(
                f"No pyproject.toml found for template {template_dir.name}, using defaults"
            )

    # Apply ADK inference if no explicit config and this is an ADK sample
    if not has_explicit_config and is_adk_sample:
        try:
            inferred_config = _infer_agent_directory_for_adk(
                template_dir, is_adk_sample
            )
            config.update(inferred_config)
            logging.debug("Applied ADK inference for template without explicit config")
        except Exception as e:
            logging.warning(f"Failed to apply ADK inference for {template_dir}: {e}")
            # Continue with default configuration

    # Detect flat structure for all remote templates (not just ADK samples)
    # This handles cases where agent.py is in root with no subdirectory
    if not has_explicit_config and not is_adk_sample:
        if _detect_flat_structure(template_dir):
            folder_name = template_dir.name.replace("-", "_")
            config.setdefault("settings", {})
            config["settings"]["agent_directory"] = folder_name
            config["settings"]["source_agent_directory"] = "."
            config["is_flat_structure"] = True
            logging.debug(
                f"Detected flat structure for non-ADK template: source='.', target='{folder_name}'"
            )

    # Add metadata about configuration source
    config["has_explicit_config"] = bool(has_explicit_config)

    # Apply CLI overrides (highest precedence) using deep merge
    if cli_overrides:
        config = merge_template_configs(config, cli_overrides)
        logging.debug(f"Applied CLI overrides: {cli_overrides}")

    return config


def get_base_template_name(config: dict[str, Any]) -> str:
    """Get base template name from remote template config.

    Args:
        config: Template configuration dictionary

    Returns:
        Base template name (defaults to "adk"), with legacy aliases resolved
    """
    # Lazy import to avoid circular dependency
    from .template import resolve_agent_alias

    base_template = config.get("base_template", "adk")
    return resolve_agent_alias(base_template) or "adk"


def merge_template_configs(
    base_config: dict[str, Any], remote_config: dict[str, Any]
) -> dict[str, Any]:
    """Merge base template config with remote template config using a deep merge.

    Args:
        base_config: Base template configuration
        remote_config: Remote template configuration

    Returns:
        Merged configuration with remote overriding base
    """
    import copy

    def deep_merge(d1: dict[str, Any], d2: dict[str, Any]) -> dict[str, Any]:
        """Recursively merges d2 into d1."""
        for k, v in d2.items():
            if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                d1[k] = deep_merge(d1[k], v)
            else:
                d1[k] = v
        return d1

    # Start with a deep copy of the base to avoid modifying it
    merged_config = copy.deepcopy(base_config)

    # Perform the deep merge
    return deep_merge(merged_config, remote_config)


def discover_adk_agents(repo_path: pathlib.Path) -> dict[int, dict[str, Any]]:
    """Discover and load all ADK agents from a repository with inference support.

    Args:
        repo_path: Path to the cloned ADK samples repository

    Returns:
        Dictionary mapping agent numbers to agent info with keys:
        - name: Agent display name
        - description: Agent description
        - path: Relative path from repo root
        - spec: adk@ specification string
        - has_explicit_config: Whether agent has explicit configuration
    """
    import logging

    adk_agents = {}

    # Search specifically for agents in python/agents/* directories
    agents_dir = repo_path / "python" / "agents"
    logging.debug(f"Looking for agents in: {agents_dir}")
    if agents_dir.exists():
        all_items = list(agents_dir.iterdir())
        logging.debug(
            f"Found items in agents directory: {[item.name for item in all_items]}"
        )

        # Collect all agents first, then sort by configuration type
        all_agents = []

        for agent_dir in sorted(agents_dir.iterdir()):
            if not agent_dir.is_dir():
                logging.debug(f"Skipping non-directory: {agent_dir.name}")
                continue
            logging.debug(f"Processing agent directory: {agent_dir.name}")

            try:
                # Load configuration with ADK inference support
                config = load_remote_template_config(
                    template_dir=agent_dir, is_adk_sample=True
                )

                agent_name = config.get("name", agent_dir.name)
                description = config.get("description", "")
                has_explicit_config = config.get("has_explicit_config", False)

                # Get the relative path from repo root
                relative_path = agent_dir.relative_to(repo_path)
                agent_spec_name = agent_dir.name

                agent_info = {
                    "name": agent_name,
                    "description": description,
                    "path": str(relative_path),
                    "spec": f"adk@{agent_spec_name}",
                    "has_explicit_config": has_explicit_config,
                }
                all_agents.append(agent_info)

            except Exception as e:
                logging.warning(f"Could not load agent from {agent_dir}: {e}")

        # Sort agents: explicit config first, then inferred (both alphabetically within their groups)
        all_agents.sort(key=lambda x: (not x["has_explicit_config"], x["name"].lower()))

        # Convert to numbered dictionary
        for i, agent_info in enumerate(all_agents, 1):
            adk_agents[i] = agent_info

    return adk_agents


def display_adk_caveat_if_needed(agents: dict[int, dict[str, Any]]) -> None:
    """Display helpful note for agents that use inference.

    Args:
        agents: Dictionary of agent info from discover_adk_agents
    """
    console = Console()
    inferred_agents = [
        a for a in agents.values() if not a.get("has_explicit_config", True)
    ]
    if inferred_agents:
        console.print(
            "\n[blue]ℹ️  Note: Agents marked with * are templated using starter pack heuristics for ADK samples.[/]"
        )
        console.print(
            "[dim]   The starter pack attempts to create a working codebase, but you'll need to follow the generated README for complete setup.[/]"
        )


def parse_agent_starter_pack_version_from_lock(
    uv_lock_path: pathlib.Path,
) -> str | None:
    """Parse agent-starter-pack version from uv.lock file.

    Args:
        uv_lock_path: Path to uv.lock file

    Returns:
        Version string if found, None otherwise
    """
    if not uv_lock_path.exists():
        return None

    try:
        with open(uv_lock_path, "rb") as f:
            lock_data = tomllib.load(f)

        # Look for agent-starter-pack in the packages section
        packages = lock_data.get("package", [])
        for package in packages:
            if package.get("name") == "agent-starter-pack":
                version = package.get("version")
                if version:
                    logging.debug(
                        f"Found agent-starter-pack version {version} in uv.lock"
                    )
                    return version

    except Exception as e:
        logging.warning(f"Error parsing uv.lock file {uv_lock_path}: {e}")

    return None


def render_and_merge_makefiles(
    base_template_path: pathlib.Path,
    final_destination: pathlib.Path,
    cookiecutter_config: dict,
    remote_template_path: pathlib.Path | None = None,
) -> None:
    """
    Renders the base and remote Makefiles separately, then merges them.

    If remote_template_path is not provided, only the base Makefile is rendered.
    """

    env = Environment()

    # Render the base Makefile
    base_makefile_path = base_template_path / "Makefile"
    if base_makefile_path.exists():
        with open(base_makefile_path, encoding="utf-8") as f:
            base_template = env.from_string(f.read())
        rendered_base_makefile = base_template.render(cookiecutter=cookiecutter_config)
    else:
        rendered_base_makefile = ""

    # Render the remote Makefile if a path is provided
    rendered_remote_makefile = ""
    if remote_template_path:
        remote_makefile_path = remote_template_path / "Makefile"
        if remote_makefile_path.exists():
            with open(remote_makefile_path, encoding="utf-8") as f:
                remote_template = env.from_string(f.read())
            rendered_remote_makefile = remote_template.render(
                cookiecutter=cookiecutter_config
            )

    # Merge the rendered Makefiles
    if rendered_base_makefile and rendered_remote_makefile:
        # A simple merge: remote content first, then append missing commands from base
        base_commands = set(
            re.findall(r"^([a-zA-Z0-9_-]+):", rendered_base_makefile, re.MULTILINE)
        )
        remote_commands = set(
            re.findall(r"^([a-zA-Z0-9_-]+):", rendered_remote_makefile, re.MULTILINE)
        )
        missing_commands = base_commands - remote_commands

        if missing_commands:
            commands_to_append = ["\n\n# --- Commands from Agent Starter Pack ---\n\n"]
            for command in sorted(missing_commands):
                command_block_match = re.search(
                    rf"^{command}:.*?(?=\n\n(?:^#.*\n)*?^[a-zA-Z0-9_-]+:|" + r"\Z)",
                    rendered_base_makefile,
                    re.MULTILINE | re.DOTALL,
                )
                if command_block_match:
                    commands_to_append.append(command_block_match.group(0))
                    commands_to_append.append("\n\n")

            final_makefile_content = rendered_remote_makefile + "".join(
                commands_to_append
            )
        else:
            final_makefile_content = rendered_remote_makefile
    elif rendered_remote_makefile:
        final_makefile_content = rendered_remote_makefile
    else:
        final_makefile_content = rendered_base_makefile

    # Write the final merged Makefile
    with open(final_destination / "Makefile", "w", encoding="utf-8") as f:
        f.write(final_makefile_content)
    logging.debug("Rendered and merged Makefile written to final destination.")
