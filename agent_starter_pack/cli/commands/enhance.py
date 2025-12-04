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
import subprocess
import sys
from typing import Any

import click
from rich.console import Console
from rich.prompt import IntPrompt, Prompt

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from ..utils.logging import display_welcome_banner, handle_cli_error
from ..utils.template import get_available_agents, validate_agent_directory_name
from ..utils.version import get_current_version
from .create import (
    create,
    get_available_base_templates,
    shared_template_options,
    validate_base_template,
)

console = Console()

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
    """Read agent-starter-pack config from project's pyproject.toml.

    Args:
        project_dir: Path to the project directory

    Returns:
        The [tool.agent-starter-pack] config dict if found, None otherwise
    """
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Config is stored under [tool.agent-starter-pack]
        return pyproject_data.get("tool", {}).get("agent-starter-pack")
    except Exception as e:
        logging.debug(f"Could not read config from pyproject.toml: {e}")
        return None


def check_and_execute_with_project_version_lock(project_dir: pathlib.Path) -> bool:
    """Check if project has asp_version and execute with that version if different.

    Args:
        project_dir: Path to the project directory

    Returns:
        True if version lock was found and executed, False otherwise
    """
    # Skip version locking if ASP_SKIP_VERSION_LOCK env var is set
    if os.environ.get("ASP_SKIP_VERSION_LOCK") == "1":
        return False

    project_config = get_project_asp_config(project_dir)
    if not project_config:
        return False

    project_version = project_config.get("asp_version")
    if not project_version:
        return False

    current_version = get_current_version()

    # Check if versions match (ignoring dev versions like 0.0.0)
    if current_version == "0.0.0":
        # Development mode, skip version lock
        return False

    if project_version == current_version:
        # Already running the correct version
        return False

    # Versions differ, need to re-execute with locked version
    console.print(
        f"🔒 Project was generated with agent-starter-pack version {project_version}",
        style="bold blue",
    )
    console.print(
        f"📦 Switching from {current_version} to {project_version}...",
        style="dim",
    )

    # Build args from project config instead of forwarding sys.argv
    # This ensures we use the same settings the project was generated with
    args = ["enhance", "--auto-approve", "--skip-checks"]

    # Add base template from metadata
    base_template = project_config.get("base_template")
    if base_template:
        args.extend(["--base-template", base_template])

    # Add all create_params dynamically
    create_params = project_config.get("create_params", {})
    for key, value in create_params.items():
        # Skip None, "none", "None", False, and empty values
        if (
            value is None
            or value is False
            or str(value).lower() == "none"
            or value == ""
        ):
            continue

        arg_name = f"--{key.replace('_', '-')}"
        if value is True:
            args.append(arg_name)
        else:
            args.extend([arg_name, str(value)])

    try:
        # Check if uvx is available
        subprocess.run(["uvx", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(
            f"❌ Project requires agent-starter-pack version {project_version}, but 'uvx' is not installed",
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

    try:
        # Execute uvx with the locked version
        cmd = ["uvx", f"agent-starter-pack@{project_version}", *args]
        logging.debug(f"Executing nested command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        return True

    except subprocess.CalledProcessError as e:
        console.print(
            f"❌ Failed to execute with locked version {project_version}: {e}",
            style="bold red",
        )
        console.print(
            "⚠️  Continuing with current version, but compatibility is not guaranteed",
            style="yellow",
        )

    return False


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
            agent_py_exists = (current_dir / dir_name / "agent.py").exists()
            root_agent_yaml_exists = (
                current_dir / dir_name / "root_agent.yaml"
            ).exists()
            if root_agent_yaml_exists:
                hint = " (has root_agent.yaml)"
            elif agent_py_exists:
                hint = " (has agent.py)"
            else:
                hint = ""
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
@click.option(
    "--adk",
    is_flag=True,
    help="Shortcut for --base-template adk_base",
)
@shared_template_options
@handle_cli_error
def enhance(
    ctx: click.Context,
    template_path: pathlib.Path,
    name: str | None,
    deployment_target: str | None,
    cicd_runner: str | None,
    prototype: bool,
    include_data_ingestion: bool,
    datastore: str | None,
    session_type: str | None,
    debug: bool,
    auto_approve: bool,
    region: str,
    skip_checks: bool,
    agent_garden: bool,
    base_template: str | None,
    adk: bool,
    agent_directory: str | None,
    google_api_key: str | None = None,
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
    - An agent name (e.g., adk_base)
    - A remote template (e.g., adk@data-science)

    The command will validate your project structure and provide guidance if needed.
    """

    # Check for version lock early (before showing any output)
    # This ensures we use the same ASP version that generated the project
    current_dir = pathlib.Path.cwd()
    if check_and_execute_with_project_version_lock(current_dir):
        # Successfully re-executed with locked version, exit this process
        return

    # Display welcome banner for enhance command
    display_welcome_banner(enhance_mode=True)

    # Setup debug logging if enabled
    if debug:
        logging.basicConfig(level=logging.DEBUG, force=True)
        console.print("> Debug mode enabled")
        logging.debug("Starting enhance command in debug mode")

    # Handle --adk shortcut
    if adk:
        if base_template:
            raise click.ClickException(
                "Cannot use --adk with --base-template. Use one or the other."
            )
        base_template = "adk_base"

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
        console.print("• A backup will be created before any changes")
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

        # Determine agent directory: CLI param > pyproject.toml detection > default
        detected_agent_directory = "app"  # default
        if not agent_directory:  # Only try to detect if not provided via CLI
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
                            if pkg != "frontend":
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
            # Check for YAML config agent (root_agent.yaml) or agent.py
            root_agent_yaml = agent_folder / "root_agent.yaml"
            agent_py = agent_folder / "agent.py"

            # Determine required object outside of if/else blocks to avoid NameError
            is_adk = base_template and "adk" in base_template.lower()
            required_object = "root_agent" if is_adk else "agent"

            if root_agent_yaml.exists():
                # YAML config agent detected
                console.print(
                    f"✅ Found [cyan]/{final_agent_directory}/root_agent.yaml[/cyan] (YAML config agent)"
                )
                console.print(
                    "   An agent.py shim will be generated automatically for deployment compatibility."
                )
                if is_adk:
                    console.print(
                        "   📖 Learn more: [cyan][link=https://google.github.io/adk-docs/agents/agent-config/]ADK Agent Config guide[/link][/cyan]"
                    )
            elif agent_py.exists():
                console.print(
                    f"✅ Found [cyan]/{final_agent_directory}/agent.py[/cyan]"
                )

                try:
                    content = agent_py.read_text(encoding="utf-8")

                    # Look for the required object definition using static analysis
                    patterns = [
                        rf"^\s*{required_object}\s*=",  # assignment: root_agent = ...
                        rf"^\s*def\s+{required_object}",  # function: def root_agent(...)
                        rf"from\s+.*\s+import\s+.*{required_object}",  # import: from ... import root_agent
                    ]

                    found = any(
                        re.search(pattern, content, re.MULTILINE)
                        for pattern in patterns
                    )

                    if found:
                        console.print(
                            f"✅ Found '{required_object}' definition in {final_agent_directory}/agent.py"
                        )
                    else:
                        console.print(
                            f"⚠️  [yellow]Missing '{required_object}' variable in {final_agent_directory}/agent.py[/yellow]"
                        )
                        console.print(
                            "   This variable should contain your main agent instance for deployment."
                        )
                        console.print(
                            f"   Example: [cyan]{required_object} = YourAgentClass()[/cyan]"
                        )
                        # Show ADK docs link for ADK templates
                        if is_adk:
                            console.print(
                                "   📖 Learn more: [cyan][link=https://google.github.io/adk-docs/get-started/quickstart/#agentpy]ADK agent.py guide[/link][/cyan]"
                            )
                        console.print()
                        if not auto_approve:
                            if not click.confirm(
                                f"Continue enhancement? (You can add '{required_object}' later)",
                                default=True,
                            ):
                                console.print(
                                    "✋ [yellow]Enhancement cancelled.[/yellow]"
                                )
                                return

                except Exception as e:
                    console.print(
                        f"⚠️  [yellow]Warning: Could not read {final_agent_directory}/agent.py: {e}[/yellow]"
                    )
            else:
                console.print(
                    f"⚠️  [yellow]Warning: {final_agent_directory}/agent.py not found[/yellow]"
                )
                console.print(
                    f"   Create {final_agent_directory}/agent.py with your agent logic and define: [cyan]{required_object} = your_agent_instance[/cyan]"
                )
                console.print()
                if not auto_approve:
                    if not click.confirm(
                        f"Continue enhancement? (An example {final_agent_directory}/agent.py will be created for you)",
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
        include_data_ingestion=include_data_ingestion,
        datastore=datastore,
        session_type=session_type,
        debug=debug,
        output_dir=None,  # Use current directory
        auto_approve=auto_approve,
        region=region,
        skip_checks=skip_checks,
        in_folder=True,  # Always use in-folder mode for enhance
        agent_directory=final_agent_directory
        if template_path == pathlib.Path(".")
        else agent_directory,
        agent_garden=agent_garden,
        base_template=base_template,
        skip_welcome=True,  # Skip welcome message since enhance shows its own
        cli_overrides=final_cli_overrides if final_cli_overrides else None,
        google_api_key=google_api_key,
    )
