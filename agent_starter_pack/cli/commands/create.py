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

import datetime
import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
from collections.abc import Callable

import click
from click.core import ParameterSource
from rich.console import Console
from rich.prompt import IntPrompt, Prompt

from ..utils.command import run_gcloud_command
from ..utils.datastores import DATASTORE_TYPES, DATASTORES
from ..utils.gcp import verify_credentials_and_vertex
from ..utils.logging import display_welcome_banner, handle_cli_error
from ..utils.remote_template import (
    fetch_remote_template,
    get_base_template_name,
    load_remote_template_config,
    merge_template_configs,
    parse_agent_spec,
)
from ..utils.template import (
    add_base_template_dependencies_interactively,
    get_agent_language,
    get_available_agents,
    get_deployment_targets,
    get_template_path,
    load_template_config,
    process_template,
    prompt_cicd_runner_selection,
    prompt_datastore_selection,
    prompt_deployment_target,
    prompt_session_type_selection,
    resolve_agent_alias,
)

console = Console()

# Export the shared decorator for use by other commands
__all__ = ["create", "shared_template_options"]


def shared_template_options(f: Callable) -> Callable:
    """Decorator to add shared options for template-based commands."""
    # Apply options in reverse order since decorators are applied bottom-up
    f = click.option(
        "-k",
        "--google-api-key",
        "--api-key",
        is_flag=False,
        flag_value="YOUR_API_KEY",
        default=None,
        help="Use Google AI Studio API key instead of Vertex AI. If provided without a value, generates a .env file with a placeholder.",
    )(f)
    f = click.option(
        "-ag",
        "--agent-garden",
        is_flag=True,
        help="Deployed from Agent Garden - customizes welcome messages",
        default=False,
    )(f)
    f = click.option(
        "--skip-deps",
        is_flag=True,
        help="Skip base template dependency installation (used when reusing saved config)",
        default=False,
        hidden=True,
    )(f)
    f = click.option(
        "-s",
        "--skip-checks",
        is_flag=True,
        help="Skip verification checks for GCP and Vertex AI",
        default=False,
    )(f)
    f = click.option(
        "--region",
        help="GCP region for deployment (default: us-central1)",
        default="us-central1",
    )(f)
    f = click.option(
        "--auto-approve",
        "--yes",
        "-y",
        is_flag=True,
        help="Skip credential confirmation prompts",
    )(f)
    f = click.option("--debug", is_flag=True, help="Enable debug logging")(f)
    f = click.option(
        "--session-type",
        type=click.Choice(["in_memory", "cloud_sql", "agent_engine"]),
        help="Type of session storage to use",
    )(f)
    f = click.option(
        "--datastore",
        "-ds",
        type=click.Choice(DATASTORE_TYPES),
        help="Type of datastore to use for data ingestion (requires --include-data-ingestion)",
    )(f)
    f = click.option(
        "--include-data-ingestion",
        "-i",
        is_flag=True,
        help="Include data ingestion pipeline in the project",
    )(f)
    f = click.option(
        "--prototype",
        "-p",
        is_flag=True,
        help="Create minimal project without CI/CD or Terraform infrastructure",
        default=False,
    )(f)
    f = click.option(
        "--cicd-runner",
        type=click.Choice(["google_cloud_build", "github_actions", "skip"]),
        help="CI/CD runner to use",
    )(f)
    f = click.option(
        "--deployment-target",
        "-d",
        type=click.Choice(["agent_engine", "cloud_run"]),
        help="Deployment target name",
    )(f)
    f = click.option(
        "--agent-directory",
        "-dir",
        help="Name of the agent directory (overrides template default)",
    )(f)
    f = click.option(
        "--base-template",
        "-bt",
        help="Base template to use (overrides template default, only for remote templates)",
    )(f)
    return f


def get_available_base_templates() -> list[str]:
    """Get list of available base templates for inheritance.

    Returns:
        List of base template names.
    """
    agents = get_available_agents()
    return sorted([agent_info["name"] for agent_info in agents.values()])


def validate_base_template(base_template: str) -> bool:
    """Validate that a base template exists.

    Args:
        base_template: Name of the base template to validate

    Returns:
        True if the base template exists, False otherwise
    """
    available_templates = get_available_base_templates()
    return base_template in available_templates


def get_standard_ignore_patterns() -> Callable[[str, list[str]], list[str]]:
    """Get standard ignore patterns for copying directories.

    Returns:
        A callable that can be used with shutil.copytree's ignore parameter.
    """
    exclude_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        ".next",
        "dist",
        "build",
        ".DS_Store",
        ".vscode",
        ".idea",
        "*.egg-info",
        ".mypy_cache",
        ".ty",
        ".coverage",
        "htmlcov",
        ".tox",
        ".cache",
    }

    def ignore_patterns(dir: str, files: list[str]) -> list[str]:
        return [f for f in files if f in exclude_dirs or f.startswith(".backup_")]

    return ignore_patterns


def normalize_project_name(project_name: str) -> str:
    """Normalize project name for better compatibility with cloud resources and tools."""

    needs_normalization = (
        any(char.isupper() for char in project_name) or "_" in project_name
    )

    if needs_normalization:
        normalized_name = project_name
        console.print(
            "Note: Project names are normalized (lowercase, hyphens only) for better compatibility with cloud resources and tools.",
            style="dim",
        )
        if any(char.isupper() for char in normalized_name):
            normalized_name = normalized_name.lower()
            console.print(
                f"Info: Converting to lowercase for compatibility: '{project_name}' -> '{normalized_name}'",
                style="bold yellow",
            )

        if "_" in normalized_name:
            # Capture the name state before this specific change
            name_before_hyphenation = normalized_name
            normalized_name = normalized_name.replace("_", "-")
            console.print(
                f"Info: Replacing underscores with hyphens for compatibility: '{name_before_hyphenation}' -> '{normalized_name}'",
                style="yellow",
            )

        return normalized_name

    return project_name


@click.command()
@click.pass_context
@click.argument("project_name", required=False, default=None)
@click.option(
    "--agent",
    "-a",
    help="Template identifier to use. Can be a local agent name (e.g., `chat_agent`), a local path (`local@/path/to/template`), an `adk-samples` shortcut (e.g., `adk@data-science`), or a remote Git URL. Both shorthand (e.g., `github.com/org/repo/path@main`) and full URLs from your browser (e.g., `https://github.com/org/repo/tree/main/path`) are supported. Lists available local templates if omitted.",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory for the project (default: current directory)",
)
@click.option(
    "--in-folder",
    "-if",
    is_flag=True,
    help="Template files directly into the current directory instead of creating a new project directory",
    default=False,
)
@click.option(
    "--skip-welcome",
    is_flag=True,
    hidden=True,
    help="Skip the welcome banner",
    default=False,
)
@click.option(
    "--locked",
    is_flag=True,
    hidden=True,
    help="Internal flag for version-locked remote templates",
    default=False,
)
@shared_template_options
@click.option(
    "--adk",
    is_flag=True,
    help="Quickstart mode: adk + agent_engine + prototype, skips prompts",
    default=False,
)
@handle_cli_error
def create(
    ctx: click.Context,
    project_name: str,
    agent: str | None,
    deployment_target: str | None,
    cicd_runner: str | None,
    adk: bool,
    prototype: bool,
    include_data_ingestion: bool,
    datastore: str | None,
    session_type: str | None,
    debug: bool,
    output_dir: str | None,
    auto_approve: bool,
    region: str,
    skip_checks: bool,
    skip_deps: bool,
    in_folder: bool,
    agent_directory: str | None,
    agent_garden: bool = False,
    base_template: str | None = None,
    skip_welcome: bool = False,
    locked: bool = False,
    cli_overrides: dict | None = None,
    google_api_key: str | None = None,
) -> None:
    """Create GCP-based AI agent projects from templates."""
    try:
        console = Console()

        # Display welcome banner (unless skipped)
        if not skip_welcome:
            display_welcome_banner(agent, agent_garden=agent_garden)

        # Handle missing project name
        if not project_name:
            if auto_approve:
                project_name = "my-agent"
                console.print(
                    f"Info: Project name not specified. Defaulting to '{project_name}' in auto-approve mode.",
                    style="yellow",
                )
            else:
                # Convert output_dir to Path for directory existence check
                check_dir = (
                    pathlib.Path(output_dir) if output_dir else pathlib.Path.cwd()
                ).resolve()

                while True:
                    project_name = Prompt.ask(
                        "\n> Enter a name for your project",
                        default="my-agent",
                        show_default=True,
                    )
                    if len(project_name) > 26:
                        console.print(
                            f"Error: Project name '{project_name}' exceeds 26 characters. Please use a shorter name.",
                            style="bold red",
                        )
                        continue
                    # Check if directory already exists
                    normalized_name = normalize_project_name(project_name)
                    if (check_dir / normalized_name).exists():
                        console.print(
                            f"Error: Project directory '{check_dir / normalized_name}' already exists. Please choose a different name.",
                            style="bold red",
                        )
                        continue
                    break

        # Validate project name (for CLI-provided names)
        if len(project_name) > 26:
            console.print(
                f"Error: Project name '{project_name}' exceeds 26 characters. Please use a shorter name.",
                style="bold red",
            )
            return

        project_name = normalize_project_name(project_name)

        # Setup debug logging if enabled
        if debug:
            logging.basicConfig(level=logging.DEBUG)
            console.print("> Debug mode enabled")
            logging.debug("Starting CLI in debug mode")

        # Handle --adk quickstart flag
        if adk:
            console.print(
                "⚡ ADK quickstart: adk + Agent Engine + prototype mode\n",
                style="cyan",
            )

            if agent and agent != "adk":
                console.print(
                    f"Info: --agent '{agent}' ignored due to --adk flag (using adk).",
                    style="yellow",
                )
            agent = "adk"

            if deployment_target and deployment_target != "agent_engine":
                console.print(
                    f"Info: --deployment-target '{deployment_target}' ignored due to --adk flag (using agent_engine).",
                    style="yellow",
                )
            deployment_target = "agent_engine"

            # Enable prototype mode and auto-approve
            prototype = True
            auto_approve = True

            if debug:
                logging.debug(
                    "ADK quickstart mode: agent=adk, deployment_target=agent_engine, prototype=True, auto_approve=True"
                )

        # Convert output_dir to Path if provided, otherwise use current directory
        destination_dir = pathlib.Path(output_dir) if output_dir else pathlib.Path.cwd()
        destination_dir = destination_dir.resolve()  # Convert to absolute path

        if in_folder:
            # For in-folder templating, use the current directory directly
            project_path = destination_dir
            # In-folder mode is permissive - we assume the user wants to enhance their existing repo

            # Create backup of entire directory before in-folder templating
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = project_path / f".backup_{project_path.name}_{timestamp}"

            console.print("📦 [blue]Creating backup before modification...[/blue]")

            try:
                shutil.copytree(
                    project_path, backup_dir, ignore=get_standard_ignore_patterns()
                )
                console.print(f"Backup created: [cyan]{backup_dir.name}[/cyan]")
            except Exception as e:
                console.print(
                    f"⚠️  [yellow]Warning: Could not create backup: {e}[/yellow]"
                )
                if not auto_approve:
                    if not click.confirm("Continue without backup?", default=True):
                        console.print("✋ [red]Operation cancelled.[/red]")
                        return

            console.print()
        else:
            # Check if project would exist in output directory
            project_path = destination_dir / project_name
            if project_path.exists():
                console.print(
                    f"Error: Project directory '{project_path}' already exists",
                    style="bold red",
                )
                return

        # Resolve agent name aliases (backwards compatibility)
        agent = resolve_agent_alias(agent)

        # Agent selection - handle remote templates
        selected_agent = None
        template_source_path = None
        temp_dir_to_clean = None
        remote_spec = None

        if agent:
            if agent.startswith("local@"):
                path_str = agent.split("@", 1)[1]
                local_path = pathlib.Path(path_str).resolve()
                if not local_path.is_dir():
                    raise click.ClickException(
                        f"Local path not found or not a directory: {local_path}"
                    )

                # Create a temporary directory and copy the local template to it
                temp_dir = tempfile.mkdtemp(prefix="asp_local_template_")
                temp_dir_to_clean = temp_dir
                template_source_path = pathlib.Path(temp_dir) / local_path.name
                shutil.copytree(
                    local_path,
                    template_source_path,
                    ignore=get_standard_ignore_patterns(),
                )

                # Check for version lock and execute nested command if found
                from ..utils.remote_template import check_and_execute_with_version_lock

                if check_and_execute_with_version_lock(
                    template_source_path, agent, locked, project_name
                ):
                    # If we executed with locked version, cleanup and exit
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return

                selected_agent = f"local_{template_source_path.name}"
                if locked:
                    # In locked mode, show a nicer message
                    console.print("✅ Using version-locked template", style="green")
                else:
                    console.print(f"Using local template: {local_path}")
                logging.debug(
                    f"Copied local template to temporary dir: {template_source_path}"
                )
            else:
                # Check if it's a remote template specification
                remote_spec = parse_agent_spec(agent)
                if remote_spec:
                    if remote_spec.is_adk_samples:
                        console.print(
                            f"> Fetching template: {remote_spec.template_path}",
                            style="bold blue",
                        )
                    else:
                        console.print(f"Fetching remote template: {agent}")
                    template_source_path, temp_dir_path = fetch_remote_template(
                        remote_spec, agent, locked, project_name
                    )
                    temp_dir_to_clean = str(temp_dir_path)
                    selected_agent = f"remote_{hash(agent)}"  # Generate unique name for remote template

                    # Show informational message for ADK samples with smart defaults
                    if remote_spec.is_adk_samples:
                        config = load_remote_template_config(
                            template_source_path, is_adk_sample=True
                        )
                        if not config.get("has_explicit_config", True):
                            console = Console()
                            console.print(
                                "\n[blue]ℹ️  Note: The starter pack uses heuristics to template this ADK sample agent.[/]"
                            )
                            console.print(
                                "[dim]   The starter pack attempts to create a working codebase, but you'll need to follow the generated README for complete setup.[/]"
                            )
                else:
                    # Handle local agent selection
                    agents = get_available_agents()
                    # First check if it's a valid agent name
                    if any(p["name"] == agent for p in agents.values()):
                        selected_agent = agent
                    else:
                        # Try numeric agent selection if input is a number
                        try:
                            agent_num = int(agent)
                            if agent_num in agents:
                                selected_agent = agents[agent_num]["name"]
                            else:
                                raise ValueError(f"Invalid agent number: {agent_num}")
                        except ValueError as err:
                            raise ValueError(
                                f"Invalid agent name or number: {agent}"
                            ) from err

        # Agent selection
        final_agent = selected_agent
        if not final_agent:
            if auto_approve:
                # Default to first available agent in auto-approve mode
                agents = get_available_agents(deployment_target=deployment_target)
                if not agents:
                    raise click.ClickException(
                        "Error: No agents available for the selected deployment target."
                    )
                final_agent = next(iter(agents.values()))["name"]
                console.print(
                    f"Info: --agent not specified. Defaulting to '{final_agent}' in auto-approve mode.",
                    style="yellow",
                )
            else:
                final_agent = display_agent_selection(deployment_target)

            # If browse functionality returned a remote agent spec, process it like CLI input
            if final_agent and final_agent.startswith("adk@"):
                # Set agent to the returned spec for remote processing
                agent = final_agent

                # Process the remote template spec just like CLI input
                remote_spec = parse_agent_spec(agent)
                if remote_spec:
                    if remote_spec.is_adk_samples:
                        console.print(
                            f"> Fetching template: {remote_spec.template_path}",
                            style="bold blue",
                        )
                    else:
                        console.print(f"Fetching remote template: {agent}")
                    template_source_path, temp_dir_path = fetch_remote_template(
                        remote_spec, agent, locked, project_name
                    )
                    temp_dir_to_clean = str(temp_dir_path)
                    final_agent = f"remote_{hash(agent)}"  # Generate unique name for remote template

                    # Show informational message for ADK samples with smart defaults
                    if remote_spec.is_adk_samples:
                        config = load_remote_template_config(
                            template_source_path, is_adk_sample=True
                        )
                        if not config.get("has_explicit_config", True):
                            console = Console()
                            console.print(
                                "\n[blue]ℹ️  Note: The starter pack uses heuristics to template this ADK sample agent.[/]"
                            )
                            console.print(
                                "[dim]   The starter pack attempts to create a working codebase, but you'll need to follow the generated README for complete setup.[/]"
                            )

        if debug:
            logging.debug(f"Selected agent: {final_agent}")

        # Load template configuration based on whether it's remote or local
        # Track original base template to detect actual overrides (not just selection)
        original_base_template: str | None = None
        if template_source_path:
            # Prepare CLI overrides for remote template config
            # Initialize cli_overrides if not provided (e.g., from enhance command)
            if cli_overrides is None:
                cli_overrides = {}

            # First, get the original base template BEFORE applying cli_overrides
            # This allows us to detect if user is actually overriding vs selecting same
            original_config = load_remote_template_config(
                template_source_path,
                None,  # No CLI overrides to get original value
                is_adk_sample=remote_spec.is_adk_samples if remote_spec else False,
            )
            original_base_template = get_base_template_name(original_config)

            if base_template:
                # Validate that the base template exists
                if not validate_base_template(base_template):
                    available_templates = get_available_base_templates()
                    console.print(
                        f"Error: Base template '{base_template}' not found.",
                        style="bold red",
                    )
                    console.print(
                        f"Available base templates: {', '.join(available_templates)}",
                        style="yellow",
                    )
                    raise click.Abort()
                cli_overrides["base_template"] = base_template

            # Load remote template config with CLI overrides
            source_config = load_remote_template_config(
                template_source_path,
                cli_overrides,
                is_adk_sample=remote_spec.is_adk_samples if remote_spec else False,
            )

            # Remote templates now work even without pyproject.toml thanks to defaults
            if debug and source_config:
                logging.debug(f"Final remote template config: {source_config}")

            # Load base template config for inheritance
            base_template_name = get_base_template_name(source_config)
            if debug:
                logging.debug(f"Using base template: {base_template_name}")

            base_template_path = (
                pathlib.Path(__file__).parent.parent.parent
                / "agents"
                / base_template_name
                / ".template"
            )
            base_config = load_template_config(base_template_path)

            # Merge configs: remote inherits from and overrides base
            config = merge_template_configs(base_config, source_config)
            # For remote templates, use the template/ subdirectory as the template source
            template_path = template_source_path / ".template"
        else:
            template_path = (
                pathlib.Path(__file__).parent.parent.parent
                / "agents"
                / final_agent
                / ".template"
            )
            config = load_template_config(template_path)

            # Apply CLI overrides for local templates if provided (e.g., from enhance command)
            if cli_overrides:
                config = merge_template_configs(config, cli_overrides)
                if debug:
                    logging.debug(
                        f"Applied CLI overrides to local template config: {cli_overrides}"
                    )
        # Data ingestion and datastore selection
        # Check language early for data ingestion validation
        early_agent_language = get_agent_language(final_agent)

        # Go agents don't support data ingestion
        if early_agent_language == "go":
            if include_data_ingestion or datastore:
                console.print(
                    "Warning: Go agents do not support data ingestion. "
                    "Ignoring --include-data-ingestion and --datastore flags.",
                    style="yellow",
                )
                include_data_ingestion = False
                datastore = None
        elif include_data_ingestion or datastore:
            include_data_ingestion = True
            if not datastore:
                if auto_approve:
                    # Default to the first available datastore in non-interactive mode
                    datastore = next(iter(DATASTORES.keys()))
                    console.print(
                        f"Info: --datastore not specified. Defaulting to '{datastore}' in auto-approve mode.",
                        style="yellow",
                    )
                else:
                    datastore = prompt_datastore_selection(
                        final_agent, from_cli_flag=True
                    )
            if debug:
                logging.debug(f"Data ingestion enabled: {include_data_ingestion}")
                logging.debug(f"Selected datastore type: {datastore}")
        else:
            # Check if the agent requires data ingestion
            if config and config.get("settings", {}).get("requires_data_ingestion"):
                include_data_ingestion = True
                if not datastore:
                    if auto_approve:
                        datastore = next(iter(DATASTORES.keys()))
                        console.print(
                            f"Info: --datastore not specified. Defaulting to '{datastore}' in auto-approve mode.",
                            style="yellow",
                        )
                    else:
                        datastore = prompt_datastore_selection(final_agent)
                if debug:
                    logging.debug(
                        f"Data ingestion required by agent: {include_data_ingestion}"
                    )
                    logging.debug(f"Selected datastore type: {datastore}")

        # Deployment target selection
        # For remote templates, we need to use the base template name for deployment target selection
        deployment_agent_name = final_agent
        remote_config = None
        if template_source_path:
            # Use the base template name from remote config for deployment target selection
            deployment_agent_name = get_base_template_name(config)
            remote_config = config

        final_deployment = deployment_target
        if not final_deployment:
            available_targets = get_deployment_targets(
                deployment_agent_name, remote_config=remote_config
            )
            if not available_targets:
                raise click.ClickException(
                    f"Error: No deployment targets available for agent '{deployment_agent_name}'."
                )
            # Auto-select if only one target available or in auto-approve mode
            if len(available_targets) == 1:
                final_deployment = available_targets[0]
                console.print(
                    f"Info: Using '{final_deployment}' (only available deployment target for this agent).",
                    style="yellow",
                )
            elif auto_approve:
                final_deployment = available_targets[0]
                console.print(
                    f"Info: --deployment-target not specified. Defaulting to '{final_deployment}' in auto-approve mode.",
                    style="yellow",
                )
            else:
                final_deployment = prompt_deployment_target(
                    deployment_agent_name, remote_config=remote_config
                )
        if debug:
            logging.debug(f"Selected deployment target: {final_deployment}")

        # Session type validation and selection (only for agents that require session management)
        final_session_type = session_type

        # Get agent language for language-specific validation
        agent_language = get_agent_language(deployment_agent_name, remote_config)

        # Go agents only support in-memory sessions
        if agent_language == "go":
            final_session_type = "in_memory"
            if session_type and session_type != "in_memory":
                console.print(
                    "Warning: Go agents only support in-memory sessions. "
                    "Using in-memory sessions for this agent.",
                    style="yellow",
                )
        else:
            # Python agents - check if session management is required
            requires_session = config.get("settings", {}).get("requires_session", False)

            # Session type selection is only available for these agents on cloud_run
            session_type_supported_agents = ("adk", "agentic_rag")

            if requires_session:
                if final_deployment == "agent_engine" and session_type:
                    console.print(
                        "Error: --session-type cannot be used with agent_engine deployment target. "
                        "Agent Engine handles session management internally.",
                        style="bold red",
                    )
                    return

                if final_deployment == "cloud_run":
                    if deployment_agent_name in session_type_supported_agents:
                        # Allow session type selection for supported agents
                        if not session_type:
                            if auto_approve:
                                final_session_type = "in_memory"
                                console.print(
                                    "Info: --session-type not specified. Defaulting to 'in_memory' in auto-approve mode.",
                                    style="yellow",
                                )
                            else:
                                final_session_type = prompt_session_type_selection()
                    else:
                        # For unsupported agents, always use in_memory
                        final_session_type = "in_memory"
                        if session_type and session_type != "in_memory":
                            console.print(
                                f"Warning: Session type selection is only available for {', '.join(session_type_supported_agents)} agents. "
                                "Using in-memory sessions for this agent.",
                                style="yellow",
                            )
            else:
                # Agents that don't require session management always use in-memory sessions
                final_session_type = "in_memory"
                if session_type and session_type != "in_memory":
                    console.print(
                        "Warning: Session type options are only available for agents that require session management. "
                        "Using in-memory sessions for this agent.",
                        style="yellow",
                    )

        if debug and final_session_type:
            logging.debug(f"Selected session type: {final_session_type}")

        # CI/CD runner selection
        # --prototype flag or agent_garden mode defaults to "skip" (minimal project)
        if prototype or agent_garden:
            if cicd_runner and cicd_runner != "skip":
                console.print(
                    f"Info: --cicd-runner '{cicd_runner}' ignored due to {'--prototype' if prototype else '--agent-garden'} flag.",
                    style="yellow",
                )
            final_cicd_runner = "skip"
            if debug:
                logging.debug("Prototype mode: setting cicd_runner to 'skip'")
        elif cicd_runner:
            final_cicd_runner = cicd_runner
        elif auto_approve:
            final_cicd_runner = "skip"
            console.print(
                "Info: --cicd-runner not specified. Defaulting to 'skip' (simple mode) in auto-approve mode.",
                style="yellow",
            )
        else:
            final_cicd_runner = prompt_cicd_runner_selection()
        if debug:
            logging.debug(f"Selected CI/CD runner: {final_cicd_runner}")

        # Region confirmation (if not explicitly passed)
        if (
            not auto_approve
            and ctx.get_parameter_source("region") != ParameterSource.COMMANDLINE
        ):
            # Show Agent Engine supported regions link if agent_garden flag is set
            if agent_garden:
                console.print(
                    "\n📍 [blue]Agent Engine Supported Regions:[/blue]\n"
                    "   [cyan]https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview#supported-regions[/cyan]"
                )
            region = prompt_region_confirmation(region, agent_garden=agent_garden)
        if debug:
            logging.debug(f"Selected region: {region}")

        # GCP Setup
        logging.debug("Setting up GCP...")

        creds_info = {}
        if not skip_checks and not google_api_key:
            # Set up GCP environment
            try:
                creds_info = setup_gcp_environment(
                    auto_approve=auto_approve,
                    skip_checks=skip_checks,
                    region=region,
                    debug=debug,
                    agent_garden=agent_garden,
                )
            except Exception as e:
                if debug:
                    logging.warning(f"GCP environment setup failed: {e}")
                console.print(f"> ⚠️  {e}", style="bold yellow")
                console.print(
                    "> Continuing with template processing...", style="yellow"
                )
        elif skip_checks and not google_api_key and final_agent.endswith("_go"):
            # For Go templates, try to get project ID from gcloud config even when skipping checks
            # This is needed because Go's .env requires a valid project ID for local development
            try:
                result = subprocess.run(
                    ["gcloud", "config", "get-value", "project"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                project_id = result.stdout.strip()
                if project_id:
                    creds_info = {"project": project_id}
                    logging.debug(f"Got project ID from gcloud config: {project_id}")
            except Exception as e:
                logging.debug(f"Could not get project ID from gcloud: {e}")

        # Process template
        if not template_source_path:
            template_path = get_template_path(final_agent, debug=debug)
        # template_path is already set above for remote templates

        if debug:
            logging.debug(f"Template path: {template_path}")
            logging.debug(f"Processing template for project: {project_name}")

        # Create output directory if it doesn't exist
        if not destination_dir.exists():
            destination_dir.mkdir(parents=True)

        if debug:
            logging.debug(f"Output directory: {destination_dir}")

        # Construct CLI overrides for template processing
        final_cli_overrides = cli_overrides or {}
        if agent_directory:
            if "settings" not in final_cli_overrides:
                final_cli_overrides["settings"] = {}
            final_cli_overrides["settings"]["agent_directory"] = agent_directory

        try:
            # Process template (handles both local and remote templates)
            process_template(
                agent_name=final_agent,
                template_dir=template_path,
                project_name=project_name,
                deployment_target=final_deployment,
                cicd_runner=final_cicd_runner,
                include_data_ingestion=include_data_ingestion,
                datastore=datastore,
                session_type=final_session_type,
                output_dir=destination_dir,
                remote_template_path=template_source_path,
                remote_config=config,
                in_folder=in_folder,
                cli_overrides=final_cli_overrides,
                agent_garden=agent_garden,
                remote_spec=remote_spec,
                google_api_key=google_api_key,
                google_cloud_project=creds_info.get("project"),
            )

            # Replace region in all files if a different region was specified
            if region != "us-central1":
                replace_region_in_files(project_path, region, debug=debug)

            # Handle base template dependencies if override was used
            # Skip if --skip-deps is set (used when reusing saved config)
            # Only trigger if the base template is ACTUALLY different from the original
            # (not just selected from interactive menu but same as default)
            is_actual_override = (
                base_template
                and original_base_template
                and base_template != original_base_template
            )
            if (
                is_actual_override
                and base_template
                and template_source_path
                and remote_config
                and not skip_deps
            ):
                # Load base template config to get extra_dependencies
                base_template_path = get_template_path(base_template, debug=debug)
                base_config = load_template_config(base_template_path)
                base_deps = base_config.get("settings", {}).get(
                    "extra_dependencies", []
                )

                if base_deps:
                    # Call interactive dependency addition
                    add_base_template_dependencies_interactively(
                        project_path,
                        base_deps,
                        base_template,
                        auto_approve=auto_approve,
                    )
        finally:
            # Clean up the temporary directory if one was created
            if temp_dir_to_clean:
                try:
                    shutil.rmtree(temp_dir_to_clean)
                    logging.debug(
                        f"Successfully cleaned up temporary directory: {temp_dir_to_clean}"
                    )
                except OSError as e:
                    logging.warning(
                        f"Failed to clean up temporary directory {temp_dir_to_clean}: {e}"
                    )

        if not in_folder:
            project_path = destination_dir / project_name
            cd_path = project_path if output_dir else project_name
        else:
            project_path = destination_dir
            cd_path = "."

        if include_data_ingestion:
            project_id = creds_info.get("project", "")
            console.print(
                f"\n[bold white]===== DATA INGESTION SETUP =====[/bold white]\n"
                f"This agent uses a datastore for grounded responses.\n"
                f"The agent will work without data, but for optimal results:\n"
                f"1. Set up dev environment:\n"
                f"   [white italic]export PROJECT_ID={project_id} && cd {cd_path} && make setup-dev-env[/white italic]\n\n"
                f"   See deployment/README.md for more info\n"
                f"2. Run the data ingestion pipeline:\n"
                f"   [white italic]export PROJECT_ID={project_id} && cd {cd_path} && make data-ingestion[/white italic]\n\n"
                f"   See data_ingestion/README.md for more info\n"
                f"[bold white]=================================[/bold white]\n"
            )
        console.print("\n[bold green]✅ Success![/] Your agent project is ready.\n")

        console.print("[bold cyan]📖 Documentation[/]")
        console.print(f"   README:    [cyan]cat {cd_path}/README.md[/]")
        console.print(
            "   Dev Guide: [cyan][link=https://goo.gle/asp-dev]https://goo.gle/asp-dev[/link][/cyan]"
        )

        # Show enhance hint for prototype mode
        if final_cicd_runner == "skip":
            console.print(
                "\n[bold cyan]💡 Tip[/]\n"
                "   Once ready for production, run: [cyan]uvx agent-starter-pack enhance[/]"
            )

        # Determine the correct path to display based on whether output_dir was specified
        # Check if the agent has a 'dev' command in its settings
        interactive_command = config.get("settings", {}).get(
            "interactive_command", "playground"
        )
        console.print("\n[bold cyan]🚀 Get Started[/]")
        console.print(
            f"   [bold bright_green]cd {cd_path} && make install && make {interactive_command}[/]"
        )
    except Exception:
        if debug:
            logging.exception(
                "An error occurred:"
            )  # This will print the full stack trace
        raise


def prompt_region_confirmation(
    default_region: str = "us-central1", agent_garden: bool = False
) -> str:
    """Prompt user to confirm or change the default region."""
    new_region = Prompt.ask(
        "\n🌍 Enter GCP region (Gemini uses global endpoint)",
        default=default_region,
        show_default=True,
    )

    return new_region if new_region else default_region


def display_agent_selection(deployment_target: str | None = None) -> str:
    """Display available agents grouped by language/framework and prompt for selection."""
    agents = get_available_agents(deployment_target=deployment_target)

    if not agents:
        if deployment_target:
            raise click.ClickException(
                f"No agents available for deployment target '{deployment_target}'"
            )
        raise click.ClickException("No valid agents found")

    # Group headers for display
    GROUP_HEADERS = {
        ("python", "adk"): "🐍 Python (ADK)",
        ("python", "langgraph"): "🐍 Python (A2A)",
        ("go", "adk"): "🔵 Go (ADK)",
    }

    console.print("\n> Please select an agent to get started:")

    current_group = None
    for num, agent in agents.items():
        agent_group = (agent["language"], agent["framework"])

        # Print group header when transitioning to a new group
        if agent_group != current_group:
            current_group = agent_group
            header = GROUP_HEADERS.get(agent_group, "Other")
            console.print(f"\n  [bold cyan]{header}[/]")

        # Align agent names for cleaner display (use display_name if available)
        display_name = agent.get("display_name", agent["name"])
        name_padded = display_name.ljust(14)
        console.print(
            f"     {num}. [bold]{name_padded}[/] [dim]{agent['description']}[/]"
        )

    # Add special option for adk-samples
    adk_samples_option = len(agents) + 1
    console.print("\n  [bold cyan]🌐 Community[/]")
    console.print(
        f"     {adk_samples_option}. [bold][link=https://github.com/google/adk-samples]google/adk-samples[/link][/] [dim]Browse community agents[/]"
    )

    choice = IntPrompt.ask(
        "\nEnter the number of your template choice", default=1, show_default=True
    )

    if choice == adk_samples_option:
        return display_adk_samples_selection()
    elif choice in agents:
        return agents[choice]["name"]
    else:
        raise ValueError(f"Invalid agent selection: {choice}")


def display_adk_samples_selection() -> str:
    """Display adk-samples agents and prompt for selection."""

    from ..utils.remote_template import fetch_remote_template, parse_agent_spec

    console.print("\n> Fetching agents from [bold blue]google/adk-samples[/]...")

    try:
        # Parse the adk-samples repository
        spec = parse_agent_spec("https://github.com/google/adk-samples")
        if not spec:
            raise RuntimeError("Failed to parse adk-samples repository")

        # Fetch the repository
        repo_path, _ = fetch_remote_template(spec)

        # Use shared ADK discovery function
        from ..utils.remote_template import discover_adk_agents

        adk_agents = discover_adk_agents(repo_path)

        if not adk_agents:
            console.print("No agents found in adk-samples repository", style="yellow")
            # Fall back to local agents
            return display_agent_selection()

        console.print("\n> Available agents from [bold blue]google/adk-samples[/]:")

        # Show explanation for inferred agents at the top
        from ..utils.remote_template import display_adk_caveat_if_needed

        display_adk_caveat_if_needed(adk_agents)

        for num, agent in adk_agents.items():
            name_with_indicator = agent["name"]
            if not agent.get("has_explicit_config", True):
                name_with_indicator += " *"

            console.print(
                f"{num}. [bold]{name_with_indicator}[/] - [dim]{agent['description']}[/]"
            )

        # Add option to go back to local agents
        back_option = len(adk_agents) + 1
        console.print(
            f"{back_option}. [bold]← Back to built-in agents[/] - [dim]Return to local agent selection[/]"
        )

        choice = IntPrompt.ask(
            "\nEnter the number of your choice", default=1, show_default=True
        )

        if choice == back_option:
            return display_agent_selection()
        elif choice in adk_agents:
            # Return the adk@ spec for the selected agent
            selected_agent = adk_agents[choice]
            console.print(
                f"\n> Selected: [bold]{selected_agent['name']}[/] from adk-samples"
            )
            return selected_agent["spec"]
        else:
            raise ValueError(f"Invalid agent selection: {choice}")

    except Exception as e:
        console.print(f"Error fetching adk-samples agents: {e}", style="bold red")
        console.print("Falling back to built-in agents...", style="yellow")
        return display_agent_selection()


def set_gcp_project(project_id: str, set_quota_project: bool = True) -> None:
    """Set the GCP project and optionally the application default quota project.

    Args:
        project_id: The GCP project ID to set.
        set_quota_project: Whether to set the application default quota project.
    """
    try:
        run_gcloud_command(
            ["config", "set", "project", project_id],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"\n> Error setting project to {project_id}:")
        console.print(e.stderr)
        raise

    if set_quota_project:
        try:
            run_gcloud_command(
                ["auth", "application-default", "set-quota-project", project_id],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            logging.debug(f"Setting quota project failed: {e.stderr}")

    console.print(f"> Successfully configured project: {project_id}")


def setup_gcp_environment(
    auto_approve: bool,
    skip_checks: bool,
    region: str,
    debug: bool,
    agent_garden: bool = False,
) -> dict:
    """Set up the GCP environment with proper credentials and project.

    Args:
        auto_approve: Whether to skip confirmation prompts
        skip_checks: Whether to skip verification checks
        region: GCP region for deployment
        debug: Whether debug logging is enabled
        agent_garden: Whether this deployment is from Agent Garden

    Returns:
        Dictionary with credential information
    """
    # Skip all verification if requested
    if skip_checks:
        if debug:
            logging.debug("Skipping verification checks due to --skip-checks flag")
        console.print("> Skipping verification checks", style="yellow")
        return {"project": "unknown"}

    if debug:
        logging.debug("Verifying GCP credentials...")

    context = "agent-garden" if agent_garden else None

    # Interactive mode: show prompts and allow user to change credentials
    if not auto_approve and not agent_garden:
        creds_info = _handle_interactive_credentials(context)
    else:
        # Non-interactive mode
        console.print("> Verifying GCP credentials...")
        creds_info = verify_credentials_and_vertex(context=context, auto_approve=True)
        console.print(f"> ✓ Connected to project: {creds_info['project']}")

    return creds_info


def _handle_interactive_credentials(context: str | None = None) -> dict:
    """Handle interactive credential verification and project selection.

    Args:
        context: Optional context for user agent

    Returns:
        Dictionary with credential information
    """
    # First, get credentials to show to user
    console.print("> Verifying GCP credentials...")
    try:
        creds_info = verify_credentials_and_vertex(context=context, auto_approve=False)
    except Exception:
        # If verification fails, we still want to show what we can and let user fix it
        import google.auth

        try:
            credentials, project = google.auth.default()
            account = getattr(credentials, "service_account_email", None) or getattr(
                credentials, "_account", None
            )
            if not account:
                result = run_gcloud_command(
                    ["config", "get-value", "account"],
                    check=False,
                    capture_output=True,
                )
                account = result.stdout.strip() or "Unknown"
            creds_info = {"project": project or "Unknown", "account": account}
        except Exception:
            creds_info = {"project": "Unknown", "account": "Unknown"}

    # Check if running in Cloud Shell with no project
    if os.environ.get("CLOUD_SHELL") == "true" and not creds_info.get("project"):
        console.print(
            "> It looks like you are running in Cloud Shell.", style="bold blue"
        )
        console.print(
            "> You need to set up a project ID to continue.",
            style="bold blue",
        )
        new_project = Prompt.ask("\n> Enter a project ID", default=None)
        while not new_project:
            console.print(
                "> Project ID cannot be empty. Please try again.", style="bold red"
            )
            new_project = Prompt.ask("\n> Enter a project ID", default=None)
        set_gcp_project(new_project, set_quota_project=False)
        # Re-verify with new project
        return verify_credentials_and_vertex(context=context, auto_approve=False)

    # Show current credentials and ask user
    console.print(f"\n> You are logged in with account: '{creds_info['account']}'")
    console.print(f"> You are using project: '{creds_info['project']}'")

    choices = ["Y", "skip", "edit"]
    response = Prompt.ask(
        "> Do you want to continue? (The CLI will check if Vertex AI is enabled in this project)",
        choices=choices,
        default="Y",
    ).lower()

    if response == "skip":
        console.print("> Skipping verification", style="yellow")
        return creds_info

    if response == "edit":
        # Handle credential change
        console.print("\n> Initiating new login...")
        try:
            run_gcloud_command(["auth", "login", "--update-adc"], check=True)
            console.print("> Login successful.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            console.print(f"> ⚠️  {e}", style="yellow")
            console.print("> Continuing with template processing...")

    # Verify credentials and Vertex AI (with interactive API enablement prompt)
    console.print("> Testing Vertex AI connection...")
    creds_info = verify_credentials_and_vertex(context=context, auto_approve=False)
    console.print(f"> ✓ Connected to project: {creds_info['project']}")

    return creds_info


def replace_region_in_files(
    project_path: pathlib.Path, new_region: str, debug: bool = False
) -> None:
    """Replace all instances of 'us-central1' with the specified region in project files.
    Also handles vertex_ai_search region mapping.

    Args:
        project_path: Path to the project directory
        new_region: The new region to use
        debug: Whether to enable debug logging
    """
    if debug:
        logging.debug(
            f"Replacing region 'us-central1' with '{new_region}' in {project_path}"
        )

    # Define allowed file extensions
    allowed_extensions = {
        ".md",
        ".py",
        ".tfvars",
        ".yaml",
        ".tf",
        ".yml",
        "Makefile",
        "makefile",
    }

    # Skip directories that shouldn't be modified
    skip_dirs = {".git", "__pycache__", "venv", ".venv", "node_modules"}

    # Determine data_store_region region value
    if new_region.startswith("us"):
        data_store_region = "us"
    elif new_region.startswith("europe"):
        data_store_region = "eu"
    else:
        data_store_region = "global"

    for file_path in project_path.rglob("*"):
        # Skip directories and files with unwanted extensions
        if (
            file_path.is_dir()
            or any(skip_dir in file_path.parts for skip_dir in skip_dirs)
            or (
                file_path.suffix not in allowed_extensions
                and file_path.name not in allowed_extensions
            )
        ):
            continue

        try:
            content = file_path.read_text()
            modified = False

            # Replace standard region references
            if "us-central1" in content:
                if debug:
                    logging.debug(f"Replacing region in {file_path}")
                content = content.replace("us-central1", new_region)
                modified = True

            # Replace data_store_region region if present (all variants)
            if 'data_store_region = "us"' in content:
                if debug:
                    logging.debug(f"Replacing vertex_ai_search region in {file_path}")
                content = content.replace(
                    'data_store_region = "us"',
                    f'data_store_region = "{data_store_region}"',
                )
                modified = True
            elif 'data_store_region="us"' in content:
                if debug:
                    logging.debug(f"Replacing data_store_region in {file_path}")
                content = content.replace(
                    'data_store_region="us"', f'data_store_region="{data_store_region}"'
                )
                modified = True
            elif 'data-store-region="us"' in content:
                if debug:
                    logging.debug(f"Replacing data-store-region in {file_path}")
                content = content.replace(
                    'data-store-region="us"', f'data-store-region="{data_store_region}"'
                )
                modified = True
            elif "_DATA_STORE_REGION: us" in content:
                if debug:
                    logging.debug(f"Replacing _DATA_STORE_REGION in {file_path}")
                content = content.replace(
                    "_DATA_STORE_REGION: us", f"_DATA_STORE_REGION: {data_store_region}"
                )
                modified = True
            elif '"DATA_STORE_REGION", "us"' in content:
                if debug:
                    logging.debug(f"Replacing DATA_STORE_REGION in {file_path}")
                content = content.replace(
                    '"DATA_STORE_REGION", "us"',
                    f'"DATA_STORE_REGION", "{data_store_region}"',
                )
                modified = True

            if modified:
                file_path.write_text(content)

        except UnicodeDecodeError:
            # Skip files that can't be read as text
            continue
