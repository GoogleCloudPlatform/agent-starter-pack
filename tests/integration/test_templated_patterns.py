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

from src.cli.utils.template import get_available_agents, get_deployment_targets

console = Console()
TARGET_DIR = "target"


def run_command(
    cmd: list[str], cwd: pathlib.Path | None, message: str, stream_output: bool = True
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


def _run_agent_test(agent: str, deployment_target: str) -> None:
    """Common test logic for both deployment targets"""
    project_name = (
        f"test_{agent}_{deployment_target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    project_path = pathlib.Path(TARGET_DIR) / project_name
    region = "us-central1" if agent == "multimodal_live_api" else "europe-west4"
    try:
        # Create target directory if it doesn't exist
        os.makedirs(TARGET_DIR, exist_ok=True)

        # Template the project
        run_command(
            [
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
            ],
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

        # Check frontend folder exists and is not empty
        frontend_path = project_path / "frontend"
        assert frontend_path.exists(), "Frontend folder missing"
        assert any(frontend_path.iterdir()), "Frontend folder is empty"

        # Install dependencies
        run_command(
            [
                "uv",
                "sync",
                "--dev",
                "--extra",
                "streamlit",
                "--extra",
                "jupyter",
                "--frozen",
            ],
            project_path,
            "Installing dependencies",
            stream_output=False,
        )

        # Run tests
        test_dirs = ["tests/unit", "tests/integration"]
        for test_dir in test_dirs:
            run_command(
                ["uv", "run", "pytest", test_dir],
                project_path,
                f"Running {test_dir} tests",
            )

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        raise


def get_test_combinations() -> list[tuple[str, str]]:
    """Generate all valid agent and deployment target combinations for testing."""
    combinations = []
    agents = get_available_agents()

    for agent_info in agents.values():
        agent_name = agent_info["name"]
        # Get available deployment targets for this agent
        targets = get_deployment_targets(agent_name)

        # Add each valid combination
        for target in targets:
            combinations.append((agent_name, target))

    return combinations


def get_test_combinations_to_run() -> list[tuple[str, str]]:
    """Get the test combinations to run, either from environment or all available."""
    if os.environ.get("_TEST_AGENT_COMBINATION"):
        env_combo_parts = os.environ.get("_TEST_AGENT_COMBINATION", "").split(",")
        if len(env_combo_parts) == 2:
            env_combo = (env_combo_parts[0], env_combo_parts[1])
            console.print(
                f"[bold blue]Running test for combination from environment:[/] {env_combo}"
            )
            return [env_combo]
        else:
            console.print(
                f"[bold red]Invalid environment combination format:[/] {env_combo_parts}"
            )

    combos = get_test_combinations()
    console.print(f"[bold blue]Running tests for all combinations:[/] {combos}")
    return combos


@pytest.mark.parametrize(
    "agent,deployment_target",
    get_test_combinations_to_run(),
    # Edit here to manually force a specific combination e.g ("langgraph_base_react", "agent_engine")
)
def test_agent_deployment(agent: str, deployment_target: str) -> None:
    """Test agent templates with different deployment targets"""
    console.print(f"[bold cyan]Testing combination:[/] {agent}, {deployment_target}")
    _run_agent_test(agent, deployment_target)
