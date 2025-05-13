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

import os
import pathlib
import subprocess
from datetime import datetime

from rich.console import Console

from tests.utils.get_agents import get_test_combinations_to_run

console = Console()
TARGET_DIR = "target"


def run_command(
    cmd: list[str], cwd: pathlib.Path | None, message: str
) -> subprocess.CompletedProcess[bytes]:
    """Helper function to run commands and handle output"""
    console.print(f"\n[bold blue]{message}...[/]")

    # For mypy, we want to see the output even if it fails
    is_mypy = cmd[2] == "mypy"

    if is_mypy:
        # For mypy, run without capturing output to preserve formatting
        mypy_result = subprocess.run(
            cmd,
            check=False,  # Don't check return code for mypy
            cwd=cwd,
        )

        if mypy_result.returncode != 0:
            console.print(
                f"[bold red]Mypy failed with exit code: {mypy_result.returncode}[/]"
            )
            raise subprocess.CalledProcessError(mypy_result.returncode, cmd, None, None)
        return mypy_result
    else:
        # For other commands, use capture_output
        try:
            result = subprocess.run(
                cmd, check=True, capture_output=True, text=False, cwd=cwd
            )

            console.print(f"[green]✓[/] {message} completed successfully")
            if result.stdout:
                console.print(result.stdout.decode())

            return result

        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error: {message}[/]")
            if e.stdout:
                console.print(e.stdout.decode())
            if e.stderr:
                console.print(e.stderr.decode())
            console.print(f"[bold red]Exit code: {e.returncode}[/]")
            raise


def test_template_linting(
    agent: str, deployment_target: str, extra_params: list[str] | None = None
) -> None:
    """Test linting for a specific agent template"""
    timestamp = datetime.now().strftime("%m%d%H%M%S")
    project_name = f"{agent[:8]}-{deployment_target[:5]}-{timestamp}".replace("_", "-")
    project_path = pathlib.Path(TARGET_DIR) / project_name
    region = "us-central1" if agent == "live_api" else "europe-west4"

    try:
        # Create target directory if it doesn't exist
        os.makedirs(TARGET_DIR, exist_ok=True)

        # Template the project
        cmd = [
            "python",
            "-m",
            "src.cli.main",
            "create",
            project_name,
            "--agent",
            agent,
            "--deployment-target",
            deployment_target,
            "--region",
            region,
            "--auto-approve",
            "--skip-checks",
        ]

        # Add any extra parameters
        if extra_params:
            cmd.extend(extra_params)

        run_command(
            cmd,
            pathlib.Path(TARGET_DIR),
            f"Templating {agent} project with {deployment_target}",
        )

        # Install dependencies
        run_command(
            [
                "uv",
                "sync",
                "--dev",
                "--extra",
                "lint",
                "--frozen",
            ],
            project_path,
            "Installing dependencies",
        )

        # Run linting commands one by one
        lint_commands = [
            ["uv", "run", "codespell"],
            ["uv", "run", "ruff", "check", ".", "--diff"],
            ["uv", "run", "ruff", "format", ".", "--check", "--diff"],
            ["uv", "run", "mypy", "."],
        ]

        for cmd in lint_commands:
            try:
                command_name = cmd[2]
                command_args = cmd[3] if len(cmd) > 3 else ""
                run_command(cmd, project_path, f"Running {command_name} {command_args}")
            except subprocess.CalledProcessError as e:
                console.print(f"[bold red]Linting failed on {cmd[2]}[/]")
                if e.stdout:
                    console.print(e.stdout)
                if e.stderr:
                    console.print(e.stderr)
                raise

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        raise


def test_all_templates() -> None:
    """Test linting for all template combinations"""
    combinations = get_test_combinations_to_run()

    for agent, deployment_target, extra_params in combinations:
        console.print(f"\n[bold cyan]Testing {agent} with {deployment_target}[/]")
        test_template_linting(agent, deployment_target, extra_params)


if __name__ == "__main__":
    test_all_templates()
