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
import subprocess

import click
from click.core import ParameterSource
from rich.console import Console
from rich.prompt import IntPrompt, Prompt

from ..utils.datastores import DATASTORE_TYPES
from ..utils.gcp import verify_credentials, verify_vertex_connection
from ..utils.logging import handle_cli_error
from ..utils.template import (
    get_available_agents,
    get_template_path,
    load_template_config,
    process_template,
    prompt_datastore_selection,
    prompt_deployment_target,
)

console = Console()


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
@click.argument("project_name")
@click.option("--agent", "-a", help="agent name or number to use")
@click.option(
    "--deployment-target",
    "-d",
    type=click.Choice(["agent_engine", "cloud_run"]),
    help="Deployment target name",
)
@click.option(
    "--include-data-ingestion",
    "-i",
    is_flag=True,
    help="Include data ingestion pipeline in the project",
)
@click.option(
    "--datastore",
    "-ds",
    type=click.Choice(DATASTORE_TYPES),
    help="Type of datastore to use for data ingestion (requires --include-data-ingestion)",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory for the project (default: current directory)",
)
@click.option(
    "--auto-approve", is_flag=True, help="Skip credential confirmation prompts"
)
@click.option(
    "--region",
    help="GCP region for deployment (default: us-central1)",
    default="us-central1",
)
@click.option(
    "--skip-checks",
    is_flag=True,
    help="Skip verification checks for uv, GCP and Vertex AI",
    default=False,
)
@handle_cli_error
def create(
    ctx: click.Context,
    project_name: str,
    agent: str | None,
    deployment_target: str | None,
    include_data_ingestion: bool,
    datastore: str | None,
    debug: bool,
    output_dir: str | None,
    auto_approve: bool,
    region: str,
    skip_checks: bool,
) -> None:
    """Create GCP-based AI agent projects from templates."""
    try:
        # Display welcome banner
        console.print("\n=== GCP Agent Starter Pack :rocket:===", style="bold blue")
        console.print("Welcome to the Agent Starter Pack!")
        console.print(
            "This tool will help you create an end-to-end production-ready AI agent in Google Cloud!\n"
        )
        # Validate project name
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

        # Convert output_dir to Path if provided, otherwise use current directory
        destination_dir = pathlib.Path(output_dir) if output_dir else pathlib.Path.cwd()
        destination_dir = destination_dir.resolve()  # Convert to absolute path

        # Check if project would exist in output directory
        project_path = destination_dir / project_name
        if project_path.exists():
            console.print(
                f"Error: Project directory '{project_path}' already exists",
                style="bold red",
            )
            return

        # Agent selection
        selected_agent = None
        if agent:
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
                    raise ValueError(f"Invalid agent name or number: {agent}") from err

        final_agent = (
            selected_agent
            if selected_agent
            else display_agent_selection(deployment_target)
        )
        if debug:
            logging.debug(f"Selected agent: {agent}")

        template_path = (
            pathlib.Path(__file__).parent.parent.parent.parent
            / "agents"
            / final_agent
            / "template"
        )
        config = load_template_config(template_path)
        # Data ingestion and datastore selection
        if include_data_ingestion or datastore:
            # If datastore is specified but include_data_ingestion is not, set it to True
            include_data_ingestion = True

            # If include_data_ingestion is True but no datastore is specified, prompt for it
            if not datastore:
                # Pass a flag to indicate this is from explicit CLI flag
                datastore = prompt_datastore_selection(final_agent, from_cli_flag=True)

            if debug:
                logging.debug(f"Data ingestion enabled: {include_data_ingestion}")
                logging.debug(f"Selected datastore type: {datastore}")
        else:
            # Check if the agent requires data ingestion
            if config and config.get("settings", {}).get("requires_data_ingestion"):
                include_data_ingestion = True
                datastore = prompt_datastore_selection(final_agent)

                if debug:
                    logging.debug(
                        f"Data ingestion required by agent: {include_data_ingestion}"
                    )
                    logging.debug(f"Selected datastore type: {datastore}")

        # Deployment target selection
        final_deployment = (
            deployment_target
            if deployment_target
            else prompt_deployment_target(final_agent)
        )
        if debug:
            logging.debug(f"Selected deployment target: {final_deployment}")

        # Region confirmation (if not explicitly passed)
        if (
            not auto_approve
            and ctx.get_parameter_source("region") != ParameterSource.COMMANDLINE
        ):
            region = prompt_region_confirmation(region)
        if debug:
            logging.debug(f"Selected region: {region}")

        # GCP Setup
        logging.debug("Setting up GCP...")

        creds_info = {}
        if not skip_checks:
            # Set up GCP environment
            try:
                creds_info = setup_gcp_environment(
                    auto_approve=auto_approve,
                    skip_checks=skip_checks,
                    region=region,
                    debug=debug,
                )
            except Exception as e:
                if debug:
                    logging.warning(f"GCP environment setup failed: {e}")
                console.print(
                    f"> Warning: GCP environment setup failed: {e}", style="yellow"
                )
                console.print(
                    "> Please check your authentication settings and permissions. "
                    "Visit https://cloud.google.com/vertex-ai/docs/authentication for help.",
                    style="yellow",
                )
                console.print(
                    "> Continuing with template processing...", style="yellow"
                )

        # Process template
        template_path = get_template_path(final_agent, debug=debug)
        if debug:
            logging.debug(f"Template path: {template_path}")
            logging.debug(f"Processing template for project: {project_name}")

        # Create output directory if it doesn't exist
        if not destination_dir.exists():
            destination_dir.mkdir(parents=True)

        if debug:
            logging.debug(f"Output directory: {destination_dir}")

        process_template(
            final_agent,
            template_path,
            project_name,
            deployment_target=final_deployment,
            include_data_ingestion=include_data_ingestion,
            datastore=datastore,
            output_dir=destination_dir,
        )

        # Replace region in all files if a different region was specified
        if region != "us-central1":
            replace_region_in_files(project_path, region, debug=debug)

        project_path = destination_dir / project_name
        cd_path = project_path if output_dir else project_name

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
        console.print("\n> 👍 Done. Execute the following command to get started:")

        console.print("\n> Success! Your agent project is ready.")
        console.print(
            f"\n📖 Project README: [cyan]cat {cd_path}/README.md[/]"
            "\n   Online Development Guide: [cyan][link=https://goo.gle/asp-dev]https://goo.gle/asp-dev[/link][/cyan]"
        )
        # Determine the correct path to display based on whether output_dir was specified
        console.print("\n🚀 To get started, run the following command:")

        # Check if the agent has a 'dev' command in its settings
        if config["settings"].get("commands", {}).get("extra", {}).get("dev"):
            console.print(
                f"   [bold bright_green]cd {cd_path} && make install && make dev[/]"
            )
        else:
            console.print(
                f"   [bold bright_green]cd {cd_path} && make install && make playground[/]"
            )
    except Exception:
        if debug:
            logging.exception(
                "An error occurred:"
            )  # This will print the full stack trace
        raise


def prompt_region_confirmation(default_region: str = "us-central1") -> str:
    """Prompt user to confirm or change the default region."""
    new_region = Prompt.ask(
        "\nEnter desired GCP region (Gemini uses global endpoint by default)",
        default=default_region,
        show_default=True,
    )

    return new_region if new_region else default_region


def display_agent_selection(deployment_target: str | None = None) -> str:
    """Display available agents and prompt for selection."""
    agents = get_available_agents(deployment_target=deployment_target)

    if not agents:
        if deployment_target:
            raise click.ClickException(
                f"No agents available for deployment target '{deployment_target}'"
            )
        raise click.ClickException("No valid agents found")

    console.print("\n> Please select a agent to get started:")
    for num, agent in agents.items():
        console.print(
            f"{num}. [bold]{agent['name']}[/] - [dim]{agent['description']}[/]"
        )

    choice = IntPrompt.ask(
        "\nEnter the number of your template choice", default=1, show_default=True
    )

    if choice not in agents:
        raise ValueError(f"Invalid agent selection: {choice}")

    return agents[choice]["name"]


def set_gcp_project(project_id: str, set_quota_project: bool = True) -> None:
    """Set the GCP project and optionally the application default quota project.

    Args:
        project_id: The GCP project ID to set.
        set_quota_project: Whether to set the application default quota project.
    """
    try:
        subprocess.run(
            ["gcloud", "config", "set", "project", project_id],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"\n> Error setting project to {project_id}:")
        console.print(e.stderr)
        raise

    if set_quota_project:
        try:
            subprocess.run(
                [
                    "gcloud",
                    "auth",
                    "application-default",
                    "set-quota-project",
                    project_id,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            console.print("> Error setting application default quota project:")
            console.print(e.stderr)
            raise

    console.print(f"> Successfully configured project: {project_id}")


def setup_gcp_environment(
    auto_approve: bool, skip_checks: bool, region: str, debug: bool
) -> dict:
    """Set up the GCP environment with proper credentials and project.

    Args:
        auto_approve: Whether to skip confirmation prompts
        skip_checks: Whether to skip verification checks
        region: GCP region for deployment
        debug: Whether debug logging is enabled

    Returns:
        Dictionary with credential information
    """
    # Skip all verification if requested
    if skip_checks:
        if debug:
            logging.debug("Skipping verification checks due to --skip-checks flag")
        console.print("> Skipping verification checks", style="yellow")
        return {"project": "unknown"}

    # Verify current GCP credentials
    if debug:
        logging.debug("Verifying GCP credentials...")
    creds_info = verify_credentials()
    # Handle credential verification and project selection
    if not auto_approve:
        creds_info = _handle_credential_verification(creds_info)
        # If user chose to skip verification, don't test Vertex AI connection
        if creds_info.get("skip_vertex_test", False):
            console.print("> Skipping Vertex AI connection test", style="yellow")
        else:
            # Test Vertex AI connection
            _test_vertex_ai_connection(creds_info["project"], region)
    else:
        # Even with auto_approve, we should still set the GCP project
        set_gcp_project(creds_info["project"], set_quota_project=True)
        # Test Vertex AI connection
        _test_vertex_ai_connection(creds_info["project"], region)

    return creds_info


def _handle_credential_verification(creds_info: dict) -> dict:
    """Handle verification of credentials and project selection.

    Args:
        creds_info: Current credential information

    Returns:
        Updated credential information
    """
    # Check if running in Cloud Shell
    if os.environ.get("CLOUD_SHELL") == "true":
        if creds_info["project"] == "":
            console.print(
                "> It looks like you are running in Cloud Shell.", style="bold blue"
            )
            console.print(
                "> You need to set up a project ID to continue, but you haven't setup a project yet.",
                style="bold blue",
            )
            new_project = Prompt.ask("\n> Enter a project ID", default=None)
            while not new_project:
                console.print(
                    "> Project ID cannot be empty. Please try again.", style="bold red"
                )
                new_project = Prompt.ask("\n> Enter a project ID", default=None)
            creds_info["project"] = new_project
            set_gcp_project(creds_info["project"], set_quota_project=False)
        return creds_info

    # Ask user if current credentials are correct or if they want to skip
    console.print(f"\n> You are logged in with account: '{creds_info['account']}'")
    console.print(f"> You are using project: '{creds_info['project']}'")

    choices = ["Y", "skip", "edit"]
    response = Prompt.ask(
        "> Do you want to continue? (The CLI will check if Vertex AI is enabled in this project)",
        choices=choices,
        default="Y",
    ).lower()

    if response == "skip":
        console.print("> Skipping credential verification", style="yellow")
        creds_info["skip_vertex_test"] = True
        return creds_info

    change_creds = response == "edit"

    if change_creds:
        # Handle credential change
        console.print("\n> Initiating new login...")
        subprocess.run(["gcloud", "auth", "login", "--update-adc"], check=True)
        console.print("> Login successful. Verifying new credentials...")

        # Re-verify credentials after login
        creds_info = verify_credentials()

        # Prompt for project change
        console.print(
            f"\n> You are now logged in with account: '{creds_info['account']}'."
        )
        console.print(f"> Current project is: '{creds_info['project']}'.")
        choices = ["y", "skip", "edit"]
        response = Prompt.ask(
            "> Do you want to continue? (The CLI will verify Vertex AI access in this project)",
            choices=choices,
            default="y",
        ).lower()

        if response == "skip":
            console.print("> Skipping project verification", style="yellow")
            creds_info["skip_vertex_test"] = True
            return creds_info

        if response == "edit":
            # Prompt for new project ID
            new_project = Prompt.ask("\n> Enter the new project ID")
            creds_info["project"] = new_project

    set_gcp_project(creds_info["project"], set_quota_project=True)
    return creds_info


def _test_vertex_ai_connection(project_id: str, region: str) -> None:
    """Test connection to Vertex AI.

    Args:
        project_id: GCP project ID
        region: GCP region for deployment
    """
    console.print("> Testing GCP and Vertex AI Connection...")
    try:
        verify_vertex_connection(
            project_id=project_id,
            location=region,
        )
        console.print(
            f"> ✓ Successfully verified connection to Vertex AI in project {project_id}"
        )
    except Exception as e:
        console.print(
            f"> ✗ Failed to connect to Vertex AI: {e!s}\n"
            f"> Please check your authentication settings and permissions. "
            f"Visit https://cloud.google.com/vertex-ai/docs/authentication for help.",
            style="bold red",
        )


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
