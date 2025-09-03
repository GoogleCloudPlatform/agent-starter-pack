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

import pathlib
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
from ..utils.template import get_available_agents
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
    current_dir: pathlib.Path, detected_directory: str
) -> str:
    """Display available directories and prompt for agent directory selection."""
    console.print()
    console.print("📁 [bold]Agent Directory Selection[/bold]")
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
        agent_files_exist = any((current_dir / dir_name).glob("*agent*.py"))
        hint = " (contains agent*.py)" if agent_files_exist else ""
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
            custom_dir = Prompt.ask(
                "Enter custom agent directory name", default=detected_directory
            )
            return custom_dir
        else:
            return selected
    else:
        raise ValueError(f"Invalid agent directory selection: {choice}")


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
    "--base-template",
    "-b",
    help="Base template to inherit from (e.g., adk_base, langgraph_base_react, agentic_rag)",
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

    # Display welcome banner for enhance command
    display_welcome_banner(enhance_mode=True)

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
            if selected_base_template != original_base_template_name:
                # Update CLI overrides with the selected base template
                cli_overrides["base_template"] = selected_base_template
                # Preserve agent_directory override if it was set
                if agent_directory:
                    cli_overrides["settings"] = cli_overrides.get("settings", {})
                    cli_overrides["settings"]["agent_directory"] = agent_directory
                base_template = selected_base_template
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

        # Check if detected/default app folder exists before showing interactive selection
        app_folder_exists = (current_dir / detected_agent_directory).exists()

        # Interactive agent directory selection if not provided via CLI, no app folder exists, and not auto-approved
        if not agent_directory and not app_folder_exists and not auto_approve:
            selected_agent_directory = display_agent_directory_selection(
                current_dir, detected_agent_directory
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
            # Check for common agent files
            agent_py = agent_folder / "agent.py"
            if agent_py.exists():
                console.print(
                    f"Detected existing agent structure with [cyan]/{final_agent_directory}/agent.py[/cyan]"
                )
            else:
                console.print(
                    f"ℹ️  [blue]Found /{final_agent_directory} folder[/blue] - ensure your agent code is properly organized within it, including an agent.py file"
                )

    # Prepare CLI overrides to pass to create command
    final_cli_overrides: dict[str, Any] = {}
    if base_template:
        final_cli_overrides["base_template"] = base_template

    # For current directory templates, ensure agent_directory is included in cli_overrides
    if template_path == pathlib.Path(".") and agent_directory:
        final_cli_overrides["settings"] = final_cli_overrides.get("settings", {})
        final_cli_overrides["settings"]["agent_directory"] = agent_directory

    # Call the create command with in-folder mode enabled
    ctx.invoke(
        create,
        project_name=project_name,
        agent=agent_spec,
        deployment_target=deployment_target,
        cicd_runner=cicd_runner,
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
    )
