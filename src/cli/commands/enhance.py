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

import click
from rich.console import Console

from ..utils.logging import display_welcome_banner, handle_cli_error
from .create import create, shared_template_options

console = Console()


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
) -> None:
    """Enhance your existing project with AI agent capabilities.

    This command is an alias for 'create' with --in-folder mode enabled, designed to
    add agent-starter-pack features to your existing project in-place rather than
    creating a new project directory.

    For best compatibility, your project should follow the agent-starter-pack structure
    with agent code organized in an /app folder (containing agent.py, etc.).

    TEMPLATE_PATH can be:
    - A local directory path (e.g., . for current directory)
    - An agent name (e.g., adk_base)
    - A remote template (e.g., adk@data-science)

    The command will validate your project structure and provide guidance if needed.
    """

    # Display welcome banner for enhance command
    display_welcome_banner(enhance_mode=True)
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

    # Validate project structure when using current directory template
    if template_path == pathlib.Path("."):
        current_dir = pathlib.Path.cwd()
        app_folder = current_dir / "app"

        if not app_folder.exists() or not app_folder.is_dir():
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
                "📁 [bold]Expected Structure:[/bold] [cyan]/app[/cyan] folder containing your agent code"
            )
            console.print(f"📍 [bold]Current Directory:[/bold] {current_dir}")
            console.print("❌ [bold red]Missing:[/bold red] /app folder")
            console.print()
            console.print(
                "[dim]The enhance command can still proceed, but for best compatibility"
                "your agent code should be organized in an /app folder structure.[/dim]"
            )
            console.print()

            # Ask for confirmation unless auto-approve is enabled
            if not auto_approve:
                import click

                if not click.confirm("Continue with enhancement?", default=False):
                    console.print()
                    console.print("✋ [yellow]Enhancement cancelled.[/yellow]")
                    console.print(
                        "💡 [dim]Tip: Create an /app folder with your agent.py file and try again.[/dim]"
                    )
                    return
                console.print()
        else:
            # Check for common agent files
            agent_py = app_folder / "agent.py"
            if agent_py.exists():
                console.print(
                    "Detected existing agent structure with [cyan]/app/agent.py[/cyan]"
                )
            else:
                console.print(
                    "ℹ️  [blue]Found /app folder[/blue] - ensure your agent code is properly organized within it"
                )

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
        skip_welcome=True,  # Skip welcome message since enhance shows its own
    )
