# Copyright 2026 Google LLC
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
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import click
from packaging import version as pkg_version
from rich.console import Console
from rich.prompt import IntPrompt, Prompt

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from ..utils.backup import create_project_backup
from ..utils.generation_metadata import metadata_to_cli_args
from ..utils.language import (
    detect_language,
    find_agent_file,
    get_agent_file_hint,
    get_asp_config_for_language,
    get_language_config,
    validate_agent_file,
)
from ..utils.logging import display_welcome_banner, handle_cli_error
from ..utils.merge import (
    apply_changes,
    display_results,
    run_create_command,
)
from ..utils.template import (
    get_available_agents,
    resolve_agent_alias,
    validate_agent_directory_name,
)
from ..utils.upgrade import (
    compare_all_files,
    group_results_by_action,
    merge_pyproject_dependencies,
    write_merged_dependencies,
)
from ..utils.version import get_current_version
from .create import (
    create,
    get_available_base_templates,
    shared_template_options,
    validate_base_template,
)

console = Console()

# Environment variable names for saved config handling
_ENV_USING_SAVED_CONFIG = "_ASP_USING_SAVED_CONFIG"
_ENV_SKIP_VERSION_LOCK = "ASP_SKIP_VERSION_LOCK"

# Directories to exclude when scanning for agent directories
_EXCLUDED_DIRS = {
    ".git",
    ".github",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "build",
    "dist",
    ".terraform",
}


def get_project_asp_config(project_dir: pathlib.Path) -> dict[str, Any] | None:
    """Read agent-starter-pack config from project config files.

    Uses shared language utilities for config detection.

    For Python projects: config in pyproject.toml under [tool.agent-starter-pack]
    For Go projects: config in .asp.toml under [project]
    For Java projects: config in pom.xml as asp.* Maven properties

    Args:
        project_dir: Path to the project directory

    Returns:
        Normalized config dict if found, None otherwise.
        The returned dict has a consistent structure with keys:
        - base_template, asp_version, agent_directory, create_params, language
    """
    # Detect language first
    language = detect_language(project_dir)

    # Get config using shared utility
    config = get_asp_config_for_language(project_dir, language)
    if not config:
        return None

    # For Go projects, normalize the config structure
    if language == "go":
        return {
            "base_template": config.get("base_template"),
            "asp_version": config.get("version"),
            "agent_directory": config.get("agent_directory", "agent"),
            "language": config.get("language", "go"),
            "create_params": {
                "deployment_target": config.get("deployment_target"),
                "cicd_runner": config.get("cicd_runner"),
            },
        }

    # For Java projects, normalize the config structure (same as Go)
    if language == "java":
        return {
            "base_template": config.get("base_template"),
            "asp_version": config.get("version"),
            "agent_directory": config.get("agent_directory", "src/main/java"),
            "language": config.get("language", "java"),
            "create_params": {
                "deployment_target": config.get("deployment_target"),
                "cicd_runner": config.get("cicd_runner"),
            },
        }

    # For TypeScript projects, normalize the config structure (same as Go)
    if language == "typescript":
        return {
            "base_template": config.get("base_template"),
            "asp_version": config.get("version"),
            "agent_directory": config.get("agent_directory", "app"),
            "language": config.get("language", "typescript"),
            "create_params": {
                "deployment_target": config.get("deployment_target"),
                "cicd_runner": config.get("cicd_runner"),
            },
        }

    # For Python, add language key and return as-is
    config["language"] = language
    return config


def _should_skip_config_value(value: Any) -> bool:
    """Check if a config value should be skipped (empty, none, skip, etc.)."""
    return value is None or value is False or str(value).lower() in ("none", "skip", "")


def build_args_from_config(
    project_config: dict[str, Any],
    auto_approve: bool = False,
    cli_overrides: dict[str, str] | None = None,
) -> list[str]:
    """Build CLI arguments from project config.

    Args:
        project_config: The [tool.agent-starter-pack] config dict
        auto_approve: If True, add --auto-approve to args
        cli_overrides: Additional CLI args to merge (e.g., from original command)

    Returns:
        List of CLI arguments to pass to enhance command
    """
    # --skip-deps is added because dependencies were already installed on first run
    # --skip-welcome avoids showing the banner twice
    args = ["enhance", "--skip-deps", "--skip-welcome"]

    # Pass through auto-approve if it was set on the original command
    if auto_approve:
        args.append("--auto-approve")

    # Add base template from metadata
    base_template = project_config.get("base_template")
    if base_template:
        args.extend(["--base-template", base_template])

    # Add agent directory from metadata
    agent_directory = project_config.get("agent_directory")
    if agent_directory:
        args.extend(["--agent-directory", agent_directory])

    # Add all create_params dynamically
    # "skip" is filtered out so enhance can prompt for CI/CD on prototype projects
    create_params = project_config.get("create_params", {})
    for key, value in create_params.items():
        if _should_skip_config_value(value):
            continue

        arg_name = f"--{key.replace('_', '-')}"
        if value is True:
            args.append(arg_name)
        else:
            args.extend([arg_name, str(value)])

    # Merge CLI overrides (these take precedence over saved config)
    # This ensures user-provided args like --cicd-runner are passed through
    if cli_overrides:
        for arg_name, value in cli_overrides.items():
            # Convert to CLI format
            cli_arg = f"--{arg_name.replace('_', '-')}"
            # Remove existing arg if present (to override)
            # Find and remove any existing occurrence
            i = 0
            while i < len(args):
                if args[i] == cli_arg:
                    # Remove the arg and its value if present
                    args.pop(i)
                    if i < len(args) and not args[i].startswith("--"):
                        args.pop(i)
                else:
                    i += 1
            # Add the override
            if value is True:
                args.append(cli_arg)
            elif value is not False and value is not None:
                args.extend([cli_arg, str(value)])

    return args


def get_display_params_from_config(project_config: dict[str, Any]) -> dict[str, Any]:
    """Extract display-worthy parameters from project config.

    Args:
        project_config: The [tool.agent-starter-pack] config dict

    Returns:
        Dict of parameter names to values for display
    """
    display_params: dict[str, Any] = {}

    # Add top-level config values
    base_template = project_config.get("base_template")
    if base_template:
        display_params["base_template"] = base_template

    agent_directory = project_config.get("agent_directory")
    if agent_directory:
        display_params["agent_directory"] = agent_directory

    asp_version = project_config.get("asp_version")
    if asp_version:
        display_params["asp_version"] = asp_version

    # Add create_params
    create_params = project_config.get("create_params", {})
    for key, value in create_params.items():
        if _should_skip_config_value(value):
            continue
        display_params[key] = value

    return display_params


def _display_saved_config(
    display_params: dict[str, Any],
    project_version: str | None,
    current_version: str,
    use_different_version: bool,
) -> None:
    """Display detected saved configuration to the user."""
    console.print()
    console.print("📋 [bold]Detected saved configuration from previous setup:[/bold]")
    console.print()
    for key, value in display_params.items():
        display_key = key.replace("_", " ").title()
        console.print(f"   • {display_key}: [cyan]{value}[/cyan]")

    if use_different_version and project_version:
        console.print()
        console.print(
            f"   • Version: [cyan]{project_version}[/cyan] (current: {current_version})"
        )
    console.print()


def _should_use_different_version(
    project_version: str | None, current_version: str
) -> bool:
    """Determine if we need to switch to a different ASP version."""
    skip_version_lock = os.environ.get(_ENV_SKIP_VERSION_LOCK) == "1"
    return (
        not skip_version_lock
        and project_version is not None
        and current_version != "0.0.0"
        and project_version != current_version
    )


def _ensure_uvx_available(project_version: str) -> None:
    """Ensure uvx is installed, exit with instructions if not."""
    try:
        subprocess.run(["uvx", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(
            f"❌ Project requires agent-starter-pack version {project_version}, "
            "but 'uvx' is not installed",
            style="bold red",
        )
        console.print(
            "💡 Install uv to use version-locked projects:",
            style="bold blue",
        )
        console.print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
        console.print(
            "   OR visit: https://docs.astral.sh/uv/getting-started/installation/"
        )
        sys.exit(1)


def _execute_with_saved_config(
    args: list[str], project_version: str | None, use_different_version: bool
) -> bool:
    """Execute enhance command with saved config args.

    Returns:
        True if execution succeeded, False otherwise
    """
    if use_different_version and project_version:
        console.print(
            f"📦 Using agent-starter-pack version {project_version}...",
            style="dim",
        )
        _ensure_uvx_available(project_version)
        cmd = ["uvx", f"agent-starter-pack@{project_version}", *args]
    else:
        console.print("✅ Using saved configuration", style="dim")
        cmd = ["agent-starter-pack", *args]

    logging.debug(f"Executing command: {' '.join(cmd)}")

    # Set env var to prevent infinite loop in nested execution
    env = os.environ.copy()
    env[_ENV_USING_SAVED_CONFIG] = "1"

    try:
        subprocess.run(cmd, check=True, env=env)
        return True
    except subprocess.CalledProcessError as e:
        if use_different_version:
            console.print(
                f"❌ Failed to execute with locked version {project_version}: {e}",
                style="bold red",
            )
            console.print(
                "⚠️  Continuing with current version, but compatibility is not guaranteed",
                style="yellow",
            )
        else:
            console.print(
                f"❌ Failed to execute with saved config: {e}",
                style="bold red",
            )
        return False


def check_and_execute_with_saved_config(
    project_dir: pathlib.Path,
    auto_approve: bool = False,
    cli_overrides: dict[str, Any] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> bool | dict[str, Any]:
    """Check for saved config and offer to reuse it.

    If config is found, displays it to the user and asks whether to use it.
    If yes, executes enhance with the saved parameters.
    If user chooses "customize", returns interactive overrides dict.

    Args:
        project_dir: Path to the project directory
        auto_approve: If True, skip confirmation prompt and use saved config
        cli_overrides: CLI args to pass through (e.g., cicd_runner from original command)
        force: If True, include --force in subprocess args (skipped for old versions)
        dry_run: If True, include --dry-run in subprocess args (skipped for old versions)

    Returns:
        True if config was used and executed successfully.
        False if no saved config found or execution failed.
        dict if user chose "customize" — contains only the changed parameters.
    """
    # Skip if already executing with saved config (prevents infinite loop)
    if os.environ.get(_ENV_USING_SAVED_CONFIG) == "1":
        return False

    project_config = get_project_asp_config(project_dir)
    if not project_config:
        return False

    display_params = get_display_params_from_config(project_config)
    if not display_params:
        return False

    current_version = get_current_version()
    project_version = project_config.get("asp_version")
    use_different_version = _should_use_different_version(
        project_version, current_version
    )

    # Show detected configuration and ask user
    _display_saved_config(
        display_params, project_version, current_version, use_different_version
    )

    if not auto_approve:
        use_saved = Prompt.ask(
            "Use these settings?",
            choices=["y", "customize"],
            default="y",
        )
        if use_saved != "y":
            return _prompt_customize_overrides(project_config)

    # Build and execute the command
    args = build_args_from_config(project_config, auto_approve, cli_overrides)
    # --force and --dry-run were introduced in this version; strip them
    # when re-executing against an older locked version to avoid crashes.
    is_older_version = (
        use_different_version
        and project_version is not None
        and pkg_version.parse(project_version) < pkg_version.parse(current_version)
    )
    if not is_older_version:
        if force:
            args.append("--force")
        if dry_run:
            args.append("--dry-run")
    return _execute_with_saved_config(args, project_version, use_different_version)


def _prompt_customize_overrides(project_config: dict[str, Any]) -> dict[str, Any]:
    """Prompt user to customize project settings interactively.

    Shows each configurable parameter with the current saved value as default.
    Returns only the parameters that were changed.

    Args:
        project_config: The saved project configuration

    Returns:
        Dict of only the changed parameter names to new values
    """
    create_params = project_config.get("create_params", {})
    overrides: dict[str, Any] = {}

    console.print()
    console.print("[bold]Customize your project settings:[/bold]")
    console.print("[dim](Press Enter to keep current value)[/dim]")
    console.print()

    # Deployment target
    current_deployment = create_params.get("deployment_target", "agent_engine")
    deployment_choices = ["agent_engine", "cloud_run", "gke", "none"]
    new_deployment = Prompt.ask(
        f"  Deployment target (current: {current_deployment})",
        choices=deployment_choices,
        default=current_deployment,
    )
    if new_deployment != current_deployment:
        overrides["deployment_target"] = new_deployment

    # Session type — only relevant for cloud_run
    effective_deployment = new_deployment
    if effective_deployment in ("cloud_run", "gke"):
        current_session = create_params.get("session_type", "in_memory")
        session_choices = ["in_memory", "cloud_sql", "agent_engine"]
        new_session = Prompt.ask(
            f"  Session type (current: {current_session})",
            choices=session_choices,
            default=current_session,
        )
        if new_session != current_session:
            overrides["session_type"] = new_session

    # CI/CD runner
    current_cicd = create_params.get("cicd_runner", "skip")
    cicd_choices = ["google_cloud_build", "github_actions", "skip"]
    new_cicd = Prompt.ask(
        f"  CI/CD runner (current: {current_cicd})",
        choices=cicd_choices,
        default=current_cicd,
    )
    if new_cicd != current_cicd:
        overrides["cicd_runner"] = new_cicd

    console.print()
    return overrides


def display_base_template_selection(current_base: str) -> str:
    """Display available base templates and prompt for selection."""
    agents = get_available_agents()

    if not agents:
        raise click.ClickException("No base templates available")

    console.print()
    console.print("🔧 [bold]Base Template Selection[/bold]")
    console.print()
    console.print(f"Your project currently inherits from: [cyan]{current_base}[/cyan]")
    console.print("Available base templates:")

    # Create a mapping of choices to agent names
    template_choices = {}
    choice_num = 1
    current_choice = None

    for agent in agents.values():
        template_choices[choice_num] = agent["name"]
        current_indicator = " (current)" if agent["name"] == current_base else ""
        console.print(
            f"  {choice_num}. [bold]{agent['name']}[/]{current_indicator} - [dim]{agent['description']}[/]"
        )
        if agent["name"] == current_base:
            current_choice = choice_num
        choice_num += 1

    if current_choice is None:
        current_choice = 1

    console.print()
    choice = IntPrompt.ask(
        "Select base template", default=current_choice, show_default=True
    )

    if choice in template_choices:
        return template_choices[choice]
    else:
        raise ValueError(f"Invalid base template selection: {choice}")


def display_agent_directory_selection(
    current_dir: pathlib.Path, detected_directory: str, base_template: str | None = None
) -> str:
    """Display available directories and prompt for agent directory selection."""
    # Determine the required object name based on base template
    is_adk = base_template and "adk" in base_template.lower()
    required_object = "root_agent" if is_adk else "agent"

    while True:
        console.print()
        console.print("📁 [bold]Agent Directory Selection[/bold]")
        console.print()
        console.print("Your project needs an agent directory containing:")
        if is_adk:
            console.print(
                "  • [cyan]agent.py[/cyan] with [cyan]root_agent[/cyan] variable, or"
            )
            console.print("  • [cyan]root_agent.yaml[/cyan] (YAML config agent)")
        else:
            console.print("  • [cyan]agent.py[/cyan] file with your agent logic")
            console.print(
                f"  • [cyan]{required_object}[/cyan] variable defined in agent.py"
            )
        console.print()
        console.print("Choose where your agent code is located:")

        # Get all directories in the current path (excluding hidden and common non-agent dirs)
        available_dirs = [
            item.name
            for item in current_dir.iterdir()
            if (
                item.is_dir()
                and not item.name.startswith(".")
                and item.name not in _EXCLUDED_DIRS
            )
        ]

        # Sort directories and create choices
        available_dirs.sort()

        directory_choices = {}
        choice_num = 1
        default_choice = None

        # Only include the detected directory if it actually exists
        if detected_directory in available_dirs:
            directory_choices[choice_num] = detected_directory
            current_indicator = (
                " (detected)" if detected_directory != "app" else " (default)"
            )
            console.print(
                f"  {choice_num}. [bold]{detected_directory}[/]{current_indicator}"
            )
            default_choice = choice_num
            choice_num += 1
            # Remove from available_dirs to avoid duplication
            available_dirs.remove(detected_directory)

        # Add other available directories
        for dir_name in available_dirs:
            directory_choices[choice_num] = dir_name
            # Check if this directory might contain agent code
            hint = get_agent_file_hint(current_dir / dir_name, base_template)
            console.print(f"  {choice_num}. [bold]{dir_name}[/]{hint}")
            if (
                default_choice is None
            ):  # If no detected directory exists, use first available as default
                default_choice = choice_num
            choice_num += 1

        # Add option for custom directory
        custom_choice = choice_num
        directory_choices[custom_choice] = "__custom__"
        console.print(f"  {custom_choice}. [bold]Enter custom directory name[/]")

        # If no directories found and no default set, default to custom option
        if default_choice is None:
            default_choice = custom_choice

        console.print()
        choice = IntPrompt.ask(
            "Select agent directory", default=default_choice, show_default=True
        )

        if choice in directory_choices:
            selected = directory_choices[choice]
            if selected == "__custom__":
                console.print()
                while True:
                    custom_dir = Prompt.ask(
                        "Enter custom agent directory name", default=detected_directory
                    )
                    try:
                        validate_agent_directory_name(custom_dir)
                        return custom_dir
                    except ValueError as e:
                        console.print(f"[bold red]Error:[/] {e}", style="bold red")
                        console.print("Please try again with a valid directory name.")
            else:
                # Validate existing directory selection as well
                try:
                    validate_agent_directory_name(selected)
                    return selected
                except ValueError as e:
                    console.print(f"[bold red]Error:[/] {e}", style="bold red")
                    console.print(
                        "This directory cannot be used as an agent directory. Please select another option."
                    )
                    console.print()
                    # Continue the loop to re-prompt without recursion
                    continue
        else:
            console.print(
                f"[bold red]Error:[/] Invalid selection: {choice}", style="bold red"
            )
            console.print("Please choose a valid option from the list.")
            console.print()
            # Continue the loop to re-prompt without recursion
            continue


def _build_enhance_create_args(
    project_config: dict[str, Any],
    cli_overrides: dict[str, Any] | None = None,
) -> list[str]:
    """Build CLI args for create command from project config and enhance overrides.

    Merges saved metadata with any CLI overrides provided by the user.

    Args:
        project_config: The saved project configuration
        cli_overrides: CLI args from the enhance command to merge in

    Returns:
        List of CLI arguments for the create command
    """
    # Start with metadata-based args
    args = metadata_to_cli_args(project_config)

    if not cli_overrides:
        return args

    # Merge CLI overrides (these take precedence over saved config)
    for key, value in cli_overrides.items():
        if _should_skip_config_value(value):
            continue

        arg_name = f"--{key.replace('_', '-')}"

        # Remove existing arg if present (to override)
        while arg_name in args:
            i = args.index(arg_name)
            # Remove the arg name
            args.pop(i)
            # If it had a value (i.e., the next item is not a flag), remove that too
            if i < len(args) and not args[i].startswith("--"):
                args.pop(i)

        # Add the override
        if value is True:
            args.append(arg_name)
        elif value is not False and value is not None:
            args.extend([arg_name, str(value)])

    return args


def _run_smart_merge(
    project_dir: pathlib.Path,
    project_config: dict[str, Any],
    cli_overrides: dict[str, Any] | None,
    auto_approve: bool,
    dry_run: bool,
) -> bool:
    """Run smart-merge using 3-way comparison.

    Generates the "old" template (what was originally generated) and the "new"
    template (with enhance params), then does a 3-way comparison to only
    overwrite files the user hasn't modified.

    Args:
        project_dir: Path to the current project
        project_config: Saved project configuration from metadata
        cli_overrides: CLI arguments from the enhance command
        auto_approve: If True, auto-apply non-conflicting changes
        dry_run: If True, preview changes without applying

    Returns:
        True if smart-merge completed successfully, False otherwise
    """
    project_name = project_config.get("name", project_dir.name)
    agent_directory = project_config.get("agent_directory", "app")
    language = project_config.get("language", "python")

    # Build args for the "old" template (original generation params)
    old_args = metadata_to_cli_args(project_config)

    # Build args for the "new" template (with enhance overrides merged)
    new_args = _build_enhance_create_args(project_config, cli_overrides)

    # Check if there's actually a difference in template params
    if old_args == new_args:
        # No template difference — fall through to interactive flow
        # (user may want to add params like cicd_runner interactively)
        logging.debug("Smart-merge: old_args == new_args, falling through")
        return False

    # Create temp directories
    temp_base = pathlib.Path(tempfile.mkdtemp(prefix="asp_enhance_"))
    old_template_dir = temp_base / "old"
    new_template_dir = temp_base / "new"

    try:
        console.print()
        console.print("[dim]Generating templates for comparison...[/dim]")

        # Generate old template (what was originally generated)
        console.print("[dim]  - Original template...[/dim]")
        if not run_create_command(old_args, old_template_dir, project_name):
            console.print(
                "[bold red]Error:[/bold red] Failed to generate original template"
            )
            console.print("[dim]Falling back to standard overwrite mode.[/dim]")
            return False

        # Generate new template (with enhance params)
        console.print("[dim]  - Enhanced template...[/dim]")
        if not run_create_command(new_args, new_template_dir, project_name):
            console.print(
                "[bold red]Error:[/bold red] Failed to generate enhanced template"
            )
            console.print("[dim]Falling back to standard overwrite mode.[/dim]")
            return False

        # The templates are created in subdirectories named after the project
        old_template_project = old_template_dir / project_name
        new_template_project = new_template_dir / project_name

        console.print()

        # Compare all files
        console.print("[dim]Comparing files...[/dim]")
        results = compare_all_files(
            project_dir,
            old_template_project,
            new_template_project,
            agent_directory,
        )

        # Group by action
        groups = group_results_by_action(results)

        # Handle dependency merging (only for Python projects)
        lang_config = get_language_config(language)
        dep_result = None
        if lang_config.get("strip_dependencies", True):
            dep_result = merge_pyproject_dependencies(
                project_dir / "pyproject.toml",
                old_template_project / "pyproject.toml",
                new_template_project / "pyproject.toml",
            )

        console.print()

        # Display results
        display_results(groups, dep_result.changes if dep_result else [], dry_run)

        # Check if there's anything to do
        total_changes = (
            len(groups["auto_update"])
            + len(groups["new"])
            + len(groups["removed"])
            + len(groups["conflict"])
        )

        has_dep_changes = dep_result and dep_result.changes
        if total_changes == 0 and not has_dep_changes:
            console.print("[bold green]✅[/bold green] No file changes needed!")
            return True

        # Confirm before applying
        if not auto_approve and not dry_run:
            prompt_text = "\nProceed with enhancement?"
            if groups["conflict"]:
                prompt_text = "\nProceed? (you'll resolve conflicts next)"
            proceed = Prompt.ask(
                prompt_text,
                choices=["y", "n"],
                default="y",
            )
            if proceed != "y":
                console.print("[yellow]Enhancement cancelled.[/yellow]")
                return True  # Return True since user chose to cancel

        # Back up before applying changes
        if not dry_run:
            try:
                create_project_backup(
                    project_dir, console=console, auto_approve=auto_approve
                )
            except click.Abort:
                return True  # User cancelled

        # Apply changes
        counts = apply_changes(
            groups,
            project_dir,
            new_template_project,
            auto_approve,
            dry_run,
        )

        # Apply dependency changes (Python only)
        if not dry_run and dep_result and dep_result.changes:
            write_merged_dependencies(
                project_dir / "pyproject.toml",
                dep_result.merged_deps,
            )

        # Summary
        console.print()
        if dry_run:
            console.print(
                "[bold yellow]Dry run complete.[/bold yellow] "
                "Run without --dry-run to apply changes."
            )
        else:
            console.print(f"  Updated: {counts['updated']} files")
            console.print(f"  Added: {counts['added']} files")
            console.print(f"  Removed: {counts['removed']} files")
            if counts["conflicts_kept"] or counts["conflicts_updated"]:
                console.print(
                    f"  Conflicts: {counts['conflicts_updated']} updated, "
                    f"{counts['conflicts_kept']} kept yours"
                )
            console.print()
            console.print("[bold green]✅ Enhance complete![/bold green]")

        return True

    finally:
        # Cleanup temp directories
        shutil.rmtree(temp_base, ignore_errors=True)


@click.command()
@click.pass_context
@click.argument(
    "template_path",
    type=click.Path(path_type=pathlib.Path),
    default=".",
    required=False,
)
@click.option(
    "--name",
    "-n",
    help="Project name for templating (defaults to current directory name)",
)
@shared_template_options
@click.option(
    "--adk",
    is_flag=True,
    help="Shortcut for --base-template adk",
    default=False,
)
@click.option(
    "--force",
    is_flag=True,
    help="Force overwrite all files (skip smart-merge comparison)",
    default=False,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without applying them (requires saved metadata)",
    default=False,
)
@click.option(
    "--skip-welcome",
    is_flag=True,
    hidden=True,
    help="Skip the welcome banner (used by nested commands)",
    default=False,
)
@handle_cli_error
def enhance(
    ctx: click.Context,
    template_path: pathlib.Path,
    name: str | None,
    deployment_target: str | None,
    cicd_runner: str | None,
    prototype: bool,
    datastore: str | None,
    session_type: str | None,
    debug: bool,
    auto_approve: bool,
    region: str,
    skip_checks: bool,
    skip_deps: bool,
    agent_garden: bool,
    base_template: str | None,
    adk: bool,
    force: bool,
    dry_run: bool,
    agent_directory: str | None,
    skip_welcome: bool = False,
    google_api_key: str | None = None,
    bq_analytics: bool = False,
    agent_guidance_filename: str = "GEMINI.md",
) -> None:
    """Enhance your existing project with AI agent capabilities.

    This command is an alias for 'create' with --in-folder mode enabled, designed to
    add agent-starter-pack features to your existing project in-place rather than
    creating a new project directory.

    For best compatibility, your project should follow the agent-starter-pack structure
    with agent code organized in an agent directory (default: /app, configurable via
    --agent-directory).

    TEMPLATE_PATH can be:
    - A local directory path (e.g., . for current directory)
    - An agent name (e.g., adk)
    - A remote template (e.g., adk@data-science)

    The command will validate your project structure and provide guidance if needed.
    """

    # Display welcome banner for enhance command (unless skipped by nested command)
    if not skip_welcome:
        display_welcome_banner(enhance_mode=True)

    # Check for saved config and offer to reuse it
    # This handles both version locking AND reusing previous settings
    current_dir = pathlib.Path.cwd()

    # Build CLI overrides from explicitly provided args to pass through
    cli_override_args: dict[str, Any] = {}
    if cicd_runner:
        cli_override_args["cicd_runner"] = cicd_runner
    if deployment_target:
        cli_override_args["deployment_target"] = deployment_target
    if session_type:
        cli_override_args["session_type"] = session_type
    if datastore:
        cli_override_args["datastore"] = datastore
    if base_template:
        cli_override_args["base_template"] = base_template
    if agent_directory:
        cli_override_args["agent_directory"] = agent_directory
    if prototype:
        cli_override_args["prototype"] = prototype
    if agent_guidance_filename != "GEMINI.md":
        cli_override_args["agent_guidance_filename"] = agent_guidance_filename

    # Smart-merge is the default when saved config exists (unless --force).
    # Skip if running in subprocess with saved config (subprocess re-execution
    # replays the same params, so smart-merge would compare identical templates).
    is_saved_config_subprocess = os.environ.get(_ENV_USING_SAVED_CONFIG) == "1"
    has_cli_overrides = any(
        not _should_skip_config_value(v) for v in cli_override_args.values()
    )

    if dry_run and force:
        console.print(
            "[bold red]Error:[/bold red] --dry-run is not compatible with --force mode."
        )
        return

    if not force and not is_saved_config_subprocess:
        project_config = get_project_asp_config(current_dir)
        if project_config:
            # Determine overrides source: CLI flags or interactive customize
            overrides: dict[str, Any] | None = None
            if has_cli_overrides:
                overrides = cli_override_args
            elif not auto_approve:
                # Show saved config, prompt y/customize
                saved_config_result = check_and_execute_with_saved_config(
                    current_dir,
                    auto_approve=auto_approve,
                    cli_overrides=cli_override_args,
                    dry_run=dry_run,
                )
                if saved_config_result is True:
                    return  # "y" → subprocess executed
                elif isinstance(saved_config_result, dict):
                    overrides = saved_config_result
                    if not overrides:
                        console.print(
                            "[bold green]✅[/bold green] No changes selected. "
                            "Project is already up to date."
                        )
                        return
                # saved_config_result is False → no saved config (shouldn't happen
                # since we already checked project_config above)
            else:
                # auto_approve with no CLI overrides
                if dry_run:
                    # Can't do anything non-interactively without overrides
                    console.print(
                        "[bold red]Error:[/bold red] --dry-run requires specifying what to change "
                        "(e.g. --deployment-target cloud_run) or interactive customization."
                    )
                    return
                # Use saved config subprocess
                if check_and_execute_with_saved_config(
                    current_dir,
                    auto_approve=auto_approve,
                    cli_overrides=cli_override_args,
                ):
                    return

            if overrides:
                if _run_smart_merge(
                    current_dir,
                    project_config,
                    overrides,
                    auto_approve,
                    dry_run,
                ):
                    return
                # If smart-merge returned False, fall through to brute-force
                console.print(
                    "[yellow]⚠️  Smart-merge failed, falling back to standard mode.[/yellow]"
                )
            elif dry_run:
                # dry_run with auto_approve and no CLI overrides — nothing to do
                console.print(
                    "[bold red]Error:[/bold red] --dry-run requires specifying what to change "
                    "(e.g. --deployment-target cloud_run) or interactive customization."
                )
                return
        elif dry_run:
            console.print(
                "[bold red]Error:[/bold red] --dry-run requires saved project metadata "
                "(pyproject.toml with [tool.agent-starter-pack] section)."
            )
            return
        elif has_cli_overrides:
            console.print(
                "[dim]No saved metadata found - using standard overwrite mode.[/dim]"
            )
    else:
        # --force or subprocess re-execution: try saved config subprocess
        if not is_saved_config_subprocess:
            saved_config_result = check_and_execute_with_saved_config(
                current_dir,
                auto_approve=auto_approve,
                cli_overrides=cli_override_args,
                force=force,
            )
            if saved_config_result is True:
                return
            # If customize dict returned here (force mode), ignore it —
            # force means brute-force overwrite

    # Setup debug logging if enabled
    if debug:
        logging.basicConfig(level=logging.DEBUG, force=True)
        console.print("> Debug mode enabled")
        logging.debug("Starting enhance command in debug mode")

    # Default cicd_runner to "skip" for programmatic invocation
    if auto_approve and not cicd_runner:
        console.print(
            "[yellow]Warning: --cicd-runner not specified with --auto-approve. "
            "Defaulting to 'skip'. Use --cicd-runner to configure CI/CD.[/yellow]"
        )
        cicd_runner = "skip"

    # Handle --adk shortcut
    if adk:
        if base_template:
            raise click.ClickException(
                "Cannot use --adk with --base-template. Use one or the other."
            )
        base_template = "adk"

    # Resolve base template aliases (backwards compatibility)
    base_template = resolve_agent_alias(base_template)

    # Validate base template if provided
    if base_template and not validate_base_template(base_template):
        available_templates = get_available_base_templates()
        console.print(
            f"Error: Base template '{base_template}' not found.", style="bold red"
        )
        console.print(
            f"Available base templates: {', '.join(available_templates)}",
            style="yellow",
        )
        return

    # Determine project name
    if name:
        project_name = name
    else:
        # Use current directory name as default
        current_dir = pathlib.Path.cwd()
        project_name = current_dir.name
        console.print(
            f"Using current directory name as project name: {project_name}", style="dim"
        )

    # Show confirmation prompt for enhancement unless auto-approved
    if not auto_approve:
        current_dir = pathlib.Path.cwd()
        console.print()
        console.print(
            "🚀 [blue]Ready to enhance your project with deployment capabilities[/blue]"
        )
        console.print(f"📂 {current_dir}")
        console.print()
        console.print("[bold]What will happen:[/bold]")
        console.print("• New template files will be added to this directory")
        console.print("• Your existing files will be preserved")
        console.print("• A backup will be created in ~/.agent-starter-pack/backups/")
        console.print()

        if not click.confirm(
            f"Continue with enhancement? {click.style('[Y/n]: ', fg='blue', bold=True)}",
            default=True,
            show_default=False,
        ):
            console.print("✋ [yellow]Enhancement cancelled.[/yellow]")
            return
        console.print()

    # Determine agent specification based on template_path
    if template_path == pathlib.Path("."):
        # Current directory - use local@ syntax
        agent_spec = "local@."
    elif template_path.is_dir():
        # Other local directory
        agent_spec = f"local@{template_path.resolve()}"
    else:
        # Assume it's an agent name or remote spec
        agent_spec = str(template_path)

    # Show base template inheritance info early for local projects
    if agent_spec.startswith("local@"):
        from ..utils.remote_template import (
            get_base_template_name,
            load_remote_template_config,
        )

        # Prepare CLI overrides for base template and agent directory
        cli_overrides: dict[str, Any] = {}
        if base_template:
            cli_overrides["base_template"] = base_template
        if agent_directory:
            cli_overrides["settings"] = cli_overrides.get("settings", {})
            cli_overrides["settings"]["agent_directory"] = agent_directory

        # Load config from current directory for inheritance info
        current_dir = pathlib.Path.cwd()
        source_config = load_remote_template_config(current_dir, cli_overrides)
        original_base_template_name = get_base_template_name(source_config)

        # Interactive base template selection if not provided via CLI and not auto-approved
        if not base_template and not auto_approve:
            selected_base_template = display_base_template_selection(
                original_base_template_name
            )
            # Always set base_template to the selected value (even if unchanged)
            base_template = selected_base_template
            if selected_base_template != original_base_template_name:
                # Update CLI overrides with the selected base template
                cli_overrides["base_template"] = selected_base_template
                # Preserve agent_directory override if it was set
                if agent_directory:
                    cli_overrides["settings"] = cli_overrides.get("settings", {})
                    cli_overrides["settings"]["agent_directory"] = agent_directory
                console.print(
                    f"✅ Selected base template: [cyan]{selected_base_template}[/cyan]"
                )
                console.print()
        elif not base_template and auto_approve:
            # Auto-select the detected base template when auto-approving
            base_template = original_base_template_name

        # Reload config with potential base template override
        if cli_overrides.get("base_template"):
            source_config = load_remote_template_config(current_dir, cli_overrides)

        base_template_name = get_base_template_name(source_config)

        # Show current inheritance info
        if not auto_approve or base_template:
            console.print()
            console.print(
                f"Template inherits from base: [cyan][link=https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/main/agents/{base_template_name}]{base_template_name}[/link][/cyan]"
            )
            console.print()

    # Validate project structure when using current directory template
    if template_path == pathlib.Path("."):
        current_dir = pathlib.Path.cwd()

        # Detect if this is a Go, Java, or TypeScript project from base_template or config
        is_go_project = base_template and base_template.endswith("_go")
        is_java_project = base_template and base_template.endswith("_java")
        is_ts_project = base_template and base_template.endswith("_ts")
        asp_config = get_project_asp_config(current_dir)
        if asp_config:
            if asp_config.get("language") == "go":
                is_go_project = True
            elif asp_config.get("language") == "java":
                is_java_project = True
            elif asp_config.get("language") == "typescript":
                is_ts_project = True

        # Determine agent directory: CLI param > config detection > language default
        if is_go_project:
            detected_agent_directory = "agent"
        elif is_java_project:
            detected_agent_directory = "src/main/java"
        else:
            detected_agent_directory = "app"
        if not agent_directory:  # Only try to detect if not provided via CLI
            # First check .asp.toml/pyproject.toml config
            config_agent_dir = asp_config.get("agent_directory") if asp_config else None
            if config_agent_dir and isinstance(config_agent_dir, str):
                detected_agent_directory = config_agent_dir
            elif not is_go_project and not is_java_project:
                # For Python, also try to detect from hatch config
                pyproject_path = current_dir / "pyproject.toml"
                if pyproject_path.exists():
                    try:
                        with open(pyproject_path, "rb") as f:
                            pyproject_data = tomllib.load(f)
                        packages = (
                            pyproject_data.get("tool", {})
                            .get("hatch", {})
                            .get("build", {})
                            .get("targets", {})
                            .get("wheel", {})
                            .get("packages", [])
                        )
                        if packages:
                            # Find the first package that isn't 'frontend'
                            for pkg in packages:
                                if isinstance(pkg, str) and pkg != "frontend":
                                    detected_agent_directory = pkg
                                    break
                    except Exception as e:
                        if debug:
                            console.print(
                                f"[dim]Could not auto-detect agent directory: {e}[/dim]"
                            )
                        pass  # Fall back to default

        # Interactive agent directory selection if not provided via CLI and not auto-approved
        if not agent_directory and not auto_approve:
            selected_agent_directory = display_agent_directory_selection(
                current_dir, detected_agent_directory, base_template
            )
            final_agent_directory = selected_agent_directory
            console.print(
                f"✅ Selected agent directory: [cyan]{selected_agent_directory}[/cyan]"
            )
            console.print()
        else:
            final_agent_directory = agent_directory or detected_agent_directory

        # Show info about agent directory selection
        if agent_directory:
            console.print(
                f"ℹ️  Using CLI-specified agent directory: [cyan]{agent_directory}[/cyan]"
            )
        elif detected_agent_directory != "app":
            console.print(
                f"ℹ️  Auto-detected agent directory: [cyan]{detected_agent_directory}[/cyan]"
            )

        agent_folder = current_dir / final_agent_directory

        if not agent_folder.exists() or not agent_folder.is_dir():
            console.print()
            console.print(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            console.print("⚠️  [bold yellow]PROJECT STRUCTURE WARNING[/bold yellow] ⚠️")
            console.print(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            console.print()
            console.print(
                f"📁 [bold]Expected Structure:[/bold] [cyan]/{final_agent_directory}[/cyan] folder containing your agent code"
            )
            console.print(f"📍 [bold]Current Directory:[/bold] {current_dir}")
            console.print(
                f"❌ [bold red]Missing:[/bold red] /{final_agent_directory} folder"
            )
            console.print()
            console.print(
                f"The enhance command can still proceed, but for best compatibility"
                f" your agent code should be organized in a /{final_agent_directory} folder structure."
            )
            console.print()

            # Ask for confirmation after showing the structure warning
            console.print("💡 Options:")
            console.print(
                f"   • Create a /{final_agent_directory} folder and move your agent code there"
            )
            if final_agent_directory == "app":
                console.print(
                    "   • Use [cyan]--agent-directory <custom_name>[/cyan] if your agent code is in a different directory"
                )
            else:
                console.print(
                    "   • Use [cyan]--agent-directory <custom_name>[/cyan] to specify your existing agent directory"
                )
            console.print()

            if not auto_approve:
                if not click.confirm(
                    f"Continue with enhancement despite missing /{final_agent_directory} folder?",
                    default=True,
                ):
                    console.print("✋ [yellow]Enhancement cancelled.[/yellow]")
                    return
        else:
            # Detect language for proper agent file handling
            language = "python"  # default
            if is_go_project:
                language = "go"
            elif is_java_project:
                language = "java"
            elif is_ts_project:
                language = "typescript"

            lang_config = get_language_config(language)
            is_adk = base_template and "adk" in base_template.lower()
            required_var = lang_config.get("agent_variable", "root_agent")

            # Find agent file using shared utility
            agent_file = find_agent_file(current_dir, language, final_agent_directory)

            if agent_file and agent_file.name == "root_agent.yaml":
                # YAML config agent detected
                console.print(
                    f"✅ Found [cyan]{agent_file.relative_to(current_dir)}[/cyan] (YAML config agent)"
                )
                console.print(
                    "   An agent.py shim will be generated automatically for deployment compatibility."
                )
                if is_adk:
                    console.print(
                        "   📖 Learn more: [cyan][link=https://google.github.io/adk-docs/agents/agent-config/]ADK Agent Config guide[/link][/cyan]"
                    )
            elif agent_file:
                # Agent file found
                console.print(
                    f"✅ Found [cyan]{agent_file.relative_to(current_dir)}[/cyan]"
                )

                # Validate the agent file contains the required variable
                is_valid, error_msg = validate_agent_file(agent_file, language)
                if is_valid:
                    console.print(
                        f"✅ Found '{required_var}' definition in {agent_file.name}"
                    )
                else:
                    console.print(f"⚠️  [yellow]{error_msg}[/yellow]")
                    console.print(
                        "   This variable should contain your main agent instance for deployment."
                    )
                    console.print(
                        f"   Example: [cyan]{required_var} = YourAgentClass()[/cyan]"
                    )
                    # Show ADK docs link for ADK templates
                    if is_adk:
                        console.print(
                            "   📖 Learn more: [cyan][link=https://google.github.io/adk-docs/get-started/quickstart/#agentpy]ADK agent.py guide[/link][/cyan]"
                        )
                    console.print()
                    if not auto_approve:
                        if not click.confirm(
                            f"Continue enhancement? (You can add '{required_var}' later)",
                            default=True,
                        ):
                            console.print("✋ [yellow]Enhancement cancelled.[/yellow]")
                            return
            else:
                # No agent file found - suggest creating one
                expected_file = lang_config.get("agent_file", "agent.py")
                console.print(
                    f"⚠️  [yellow]Warning: {expected_file} not found in {final_agent_directory}/[/yellow]"
                )
                console.print(
                    f"   Create {final_agent_directory}/{expected_file} with your agent logic"
                )
                if language == "python":
                    console.print(
                        f"   and define: [cyan]{required_var} = your_agent_instance[/cyan]"
                    )
                console.print()
                if not auto_approve:
                    if not click.confirm(
                        f"Continue enhancement? (An example {expected_file} will be created for you)",
                        default=True,
                    ):
                        console.print("✋ [yellow]Enhancement cancelled.[/yellow]")
                        return

    # Prepare CLI overrides to pass to create command
    final_cli_overrides: dict[str, Any] = {}
    if base_template:
        final_cli_overrides["base_template"] = base_template

    # For current directory templates, ensure agent_directory is included in cli_overrides
    # final_agent_directory is set from interactive selection or CLI/detection
    if template_path == pathlib.Path(".") and final_agent_directory:
        final_cli_overrides["settings"] = final_cli_overrides.get("settings", {})
        final_cli_overrides["settings"]["agent_directory"] = final_agent_directory

    # Call the create command with in-folder mode enabled
    ctx.invoke(
        create,
        project_name=project_name,
        agent=agent_spec,
        deployment_target=deployment_target,
        cicd_runner=cicd_runner,
        prototype=prototype,
        datastore=datastore,
        session_type=session_type,
        debug=debug,
        output_dir=None,  # Use current directory
        auto_approve=auto_approve,
        region=region,
        skip_checks=skip_checks,
        skip_deps=skip_deps,
        in_folder=True,  # Always use in-folder mode for enhance
        agent_directory=final_agent_directory
        if template_path == pathlib.Path(".")
        else agent_directory,
        agent_garden=agent_garden,
        base_template=base_template,
        skip_welcome=True,  # Skip welcome message since enhance shows its own
        cli_overrides=final_cli_overrides if final_cli_overrides else None,
        google_api_key=google_api_key,
        bq_analytics=bq_analytics,
        agent_guidance_filename=agent_guidance_filename,
    )
