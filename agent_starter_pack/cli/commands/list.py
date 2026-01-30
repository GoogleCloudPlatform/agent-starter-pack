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
import pathlib
import sys

import click

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from rich.console import Console
from rich.table import Table

from ..utils.remote_template import fetch_remote_template, parse_agent_spec
from ..utils.template import get_available_agents

console = Console()


def display_agents_from_path(
    base_path: pathlib.Path, source_name: str, is_adk_samples: bool = False
) -> None:
    """Scans a directory and displays available agents."""
    table = Table(
        title=f"Available agents in [bold blue]{source_name}[/]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Name", style="bold")
    table.add_column("Path", style="cyan")
    table.add_column("Description", style="dim")

    if not base_path.is_dir():
        console.print(f"Directory not found: {base_path}", style="bold red")
        return

    found_agents = False
    adk_agents = {}

    if is_adk_samples:
        # For ADK samples, use the shared discovery function
        from ..utils.remote_template import discover_adk_agents

        adk_agents = discover_adk_agents(base_path)

        for agent_info in adk_agents.values():
            # Add indicator for inferred agents
            name_with_indicator = agent_info["name"]
            if not agent_info.get("has_explicit_config", True):
                name_with_indicator += " *"

            table.add_row(
                name_with_indicator, f"/{agent_info['path']}", agent_info["description"]
            )
            found_agents = True
    else:
        # Original logic for non-ADK sources: Search for pyproject.toml files with explicit config
        for config_path in sorted(base_path.glob("**/pyproject.toml")):
            try:
                with open(config_path, "rb") as f:
                    pyproject_data = tomllib.load(f)

                config = pyproject_data.get("tool", {}).get("agent-starter-pack", {})

                # Skip pyproject.toml files that don't have agent-starter-pack config
                if not config:
                    continue

                template_root = config_path.parent

                # Use fallbacks to [project] section if needed
                project_info = pyproject_data.get("project", {})
                agent_name = (
                    config.get("name") or project_info.get("name") or template_root.name
                )
                description = (
                    config.get("description") or project_info.get("description") or ""
                )

                # Display the agent's path relative to the scanned directory
                relative_path = template_root.relative_to(base_path)

                table.add_row(agent_name, f"/{relative_path}", description)
                found_agents = True

            except Exception as e:
                logging.warning(f"Could not load agent from {config_path.parent}: {e}")

    if not found_agents:
        console.print(f"No agents found in {source_name}", style="yellow")
    else:
        # Show explanation for inferred agents at the top (only for ADK samples)
        if is_adk_samples:
            from ..utils.remote_template import display_adk_caveat_if_needed

            display_adk_caveat_if_needed(adk_agents)

        console.print(table)


def list_remote_agents(remote_source: str, scan_from_root: bool = False) -> None:
    """Lists agents from a remote source (Git URL)."""
    spec = parse_agent_spec(remote_source)
    if not spec:
        console.print(f"Invalid remote source: {remote_source}", style="bold red")
        return

    console.print(f"\nFetching agents from [bold blue]{remote_source}[/]...")

    try:
        # fetch_remote_template clones the repo and returns a path to the
        # specific template directory within the repo.
        template_dir_path = fetch_remote_template(spec)

        # fetch_remote_template always returns a tuple of (repo_path, template_path)
        repo_path, template_path = template_dir_path
        scan_path = repo_path if scan_from_root else template_path

        # Check if this is ADK samples to enable inference
        is_adk_samples = (
            spec.is_adk_samples if hasattr(spec, "is_adk_samples") else False
        )

        display_agents_from_path(
            scan_path, remote_source, is_adk_samples=is_adk_samples
        )

    except (RuntimeError, FileNotFoundError) as e:
        console.print(f"Error: {e}", style="bold red")


@click.command("list")
@click.option(
    "--adk",
    is_flag=True,
    help="List agents from the official google/adk-samples repository.",
)
@click.option(
    "--source",
    "-s",
    help="List agents from a local path or a remote Git URL.",
)
def list_agents(adk: bool, source: str | None) -> None:
    """
    Lists available agent templates.

    Defaults to listing built-in agents if no options are provided.
    """
    if adk and source:
        console.print(
            "Error: --adk and --source are mutually exclusive.", style="bold red"
        )
        return

    if adk:
        list_remote_agents("https://github.com/google/adk-samples", scan_from_root=True)
        return

    if source:
        source_path = pathlib.Path(source)
        if source_path.is_dir():
            display_agents_from_path(source_path, f"local directory '{source}'")
        elif parse_agent_spec(source):
            list_remote_agents(source)
        else:
            console.print(
                f"Error: Source '{source}' is not a valid local directory or remote URL.",
                style="bold red",
            )
        return

    # Default behavior: list built-in agents
    agents = get_available_agents()
    if not agents:
        console.print("No built-in agents found.", style="yellow")
        return

    table = Table(
        title="Available built-in agents",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Number", style="dim", width=12)
    table.add_column("Name", style="bold")
    table.add_column("Description")

    for i, (_, agent) in enumerate(agents.items()):
        display_name = agent.get("display_name", agent["name"])
        table.add_row(str(i + 1), display_name, agent["description"])
    console.print(table)
