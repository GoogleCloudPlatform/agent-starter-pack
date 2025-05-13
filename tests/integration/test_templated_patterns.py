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

import pytest
from rich.console import Console

from tests.utils.get_agents import get_test_combinations_to_run

console = Console()
TARGET_DIR = "target"


def run_command(
    cmd: list[str],
    cwd: pathlib.Path | None,
    message: str,
    stream_output: bool = True,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Helper function to run commands and stream output"""
    console.print(f"\n[bold blue]{message}...[/]")
    try:
        # Using Popen to stream output
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            bufsize=1,  # Line-buffered
            env=env,
        ) as process:
            if stream_output:
                # Stream stdout
                if process.stdout:
                    for line in process.stdout:
                        console.print(line.strip())

                # Stream stderr
                if process.stderr:
                    for line in process.stderr:
                        console.print("[bold red]" + line.strip())
            else:
                # Consume the output but don't print it
                if process.stdout:
                    for _ in process.stdout:
                        pass
                if process.stderr:
                    for _ in process.stderr:
                        pass

            # Wait for the process to complete and get the return code
            returncode = process.wait()

        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, cmd)

        console.print(f"[green]✓[/] {message} completed successfully")
        return subprocess.CompletedProcess(cmd, returncode, "", "")

    except subprocess.CalledProcessError:
        console.print(f"[bold red]Error: {message}[/]")
        raise


def _run_agent_test(
    agent: str, deployment_target: str, extra_params: list[str] | None = None
) -> None:
    """Common test logic for both deployment targets"""
    # Generate a shorter project name to avoid exceeding character limits
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
            "Templating project",
        )

        # Verify essential files
        essential_files = [
            "pyproject.toml",
            "app/agent.py",
        ]
        for file in essential_files:
            assert (project_path / file).exists(), f"Missing file: {file}"

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
            stream_output=False,
        )

        # Run tests
        test_dirs = ["tests/unit", "tests/integration"]
        for test_dir in test_dirs:
            # Set environment variable for integration tests
            env = os.environ.copy()
            env["INTEGRATION_TEST"] = "TRUE"

            run_command(
                ["uv", "run", "pytest", test_dir],
                project_path,
                f"Running {test_dir} tests",
                env=env,
            )

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        raise


@pytest.mark.parametrize(
    "agent,deployment_target,extra_params",
    get_test_combinations_to_run(),
    # Edit here to manually force a specific combination e.g [("langgraph_base_react", "agent_engine", None)]
)
def test_agent_deployment(
    agent: str, deployment_target: str, extra_params: list[str] | None
) -> None:
    """Test agent templates with different deployment targets"""
    console.print(f"[bold cyan]Testing combination:[/] {agent}, {deployment_target}")
    _run_agent_test(agent, deployment_target, extra_params)
