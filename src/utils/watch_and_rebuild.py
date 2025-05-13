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
import shutil
import subprocess
import time

import click
from rich.console import Console
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

console = Console()


class TemplateHandler(FileSystemEventHandler):
    def __init__(
        self,
        agent_name: str,
        project_name: str,
        deployment_target: str,
        output_dir: str | None,
        region: str,
        extra_params: str | None = None,
    ):
        self.agent_name = agent_name
        self.project_name = project_name
        self.deployment_target = deployment_target
        self.output_dir = output_dir
        self.region = region
        self.extra_params = extra_params
        self.last_rebuild = 0
        self.rebuild_cooldown = 1  # Seconds to wait between rebuilds

    def on_modified(self, event):
        if event.is_directory:
            return

        # Implement cooldown to prevent multiple rapid rebuilds
        current_time = time.time()
        if current_time - self.last_rebuild < self.rebuild_cooldown:
            return

        self.last_rebuild = current_time

        console.print(f"Detected change in {event.src_path}")
        self.rebuild_template()

    def rebuild_template(self):
        try:
            # Clean output directory
            project_path = (
                pathlib.Path(self.output_dir) / self.project_name
                if self.output_dir
                else pathlib.Path(self.project_name)
            )

            # Check if the project directory exists and remove it
            if project_path.exists():
                console.print(
                    f"Removing existing directory: {project_path}", style="yellow"
                )
                shutil.rmtree(project_path)

            # Rebuild using the CLI tool with agent and deployment target
            cmd = [
                "uv",
                "run",
                "-m",
                "src.cli.main",
                "create",
                str(self.project_name),
                "--agent",
                self.agent_name,
                "--deployment-target",
                self.deployment_target,
                "--output-dir",
                str(self.output_dir) if self.output_dir else ".",
                "--auto-approve",
                "--region",
                self.region,
            ]
            
            # Add extra parameters if provided
            if self.extra_params:
                # Split comma-separated parameters and add them individually
                for param in self.extra_params.split(','):
                    cmd.append(param.strip())
                
            console.print(f"Executing: {' '.join(cmd)}", style="bold blue")
            subprocess.run(cmd, check=True)

            console.print("✨ Template rebuilt successfully!", style="bold green")

        except subprocess.CalledProcessError as e:
            console.print(f"Error rebuilding template: {e}", style="bold red")
        except Exception as e:
            console.print(f"Unexpected error: {e}", style="bold red")


@click.command()
@click.argument("agent")
@click.argument("project_name")
@click.option("--deployment-target", "-d", help="Deployment target to use")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="target",
    help="Output directory for the project",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--region", default="us-central1", help="GCP region to use")
@click.option("--extra-params", help="Additional parameters to pass to the create command")
def watch(
    agent: str,
    project_name: str,
    deployment_target: str,
    output_dir: str | None,
    debug: bool,
    region: str,
    extra_params: str | None,
):
    """
    Watch a agent's template and automatically rebuild when changes are detected.

    agent: Name of the agent to watch (e.g., langgraph_base_react)
    PROJECT_NAME: Name of the project to generate
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # Get directories to watch
    root_dir = pathlib.Path(__file__).parent.parent.parent.resolve()
    src_dir = root_dir / "src"
    agents_dir = root_dir / "agents"

    if not agents_dir.exists():
        raise click.BadParameter(f"agents directory not found: {agents_dir}")

    if not src_dir.exists():
        raise click.BadParameter(f"Source directory not found: {src_dir}")

    # Create output directory if it doesn't exist
    if output_dir:
        output_path = pathlib.Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        console.print(f"Using output directory: {output_path}")

    console.print(f"Watching agent: {agent}")
    console.print(f"Deployment target: {deployment_target}")
    console.print(f"Source directory: {src_dir}")
    console.print(f"agents directory: {agents_dir}")
    console.print(f"Project name: {project_name}")
    console.print(f"Region: {region}")
    if extra_params:
        console.print(f"Extra parameters: {extra_params}")

    event_handler = TemplateHandler(
        agent_name=agent,
        project_name=project_name,
        deployment_target=deployment_target,
        output_dir=output_dir,
        region=region,
        extra_params=extra_params,
    )

    observer = Observer()
    # Watch both src and agents directories
    observer.schedule(event_handler, str(src_dir), recursive=True)
    observer.schedule(event_handler, str(agents_dir), recursive=True)
    observer.start()

    try:
        # Trigger initial build
        console.print("\n🏗️ Performing initial build...", style="bold blue")
        event_handler.rebuild_template()

        console.print(
            "\n🔍 Watching for changes (Press Ctrl+C to stop)...", style="bold blue"
        )
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n⏹️ Stopping watch...", style="bold yellow")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    watch()
