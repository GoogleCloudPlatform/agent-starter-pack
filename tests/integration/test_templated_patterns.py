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
from datetime import datetime

import pytest
from rich.console import Console

from tests.integration.utils import run_command
from tests.utils.get_agents import get_test_combinations_to_run

console = Console()
TARGET_DIR = "target"


def _run_agent_test(
    agent: str, deployment_target: str, extra_params: list[str] | None = None
) -> None:
    """Common test logic for both deployment targets"""
    # Generate a shorter project name to avoid exceeding character limits
    timestamp = datetime.now().strftime("%m%d%H%M%S")
    project_name = f"{agent[:8]}-{deployment_target[:5]}-{timestamp}".replace("_", "-")
    project_path = pathlib.Path(TARGET_DIR) / project_name
    region = "us-central1" if agent == "adk_live" else "europe-west4"
    try:
        # Create target directory if it doesn't exist
        os.makedirs(TARGET_DIR, exist_ok=True)

        # Template the project
        cmd = [
            "python",
            "-m",
            "agent_starter_pack.cli.main",
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

        # Determine agent directory from extra_params
        agent_directory = "app"  # default
        if extra_params:
            # Check for -dir or --agent-directory parameter
            for i, param in enumerate(extra_params):
                if param in ["-dir", "--agent-directory"] and i + 1 < len(extra_params):
                    agent_directory = extra_params[i + 1]
                    break

        # Verify essential files
        essential_files = [
            "pyproject.toml",
            f"{agent_directory}/agent.py",
        ]
        for file in essential_files:
            assert (project_path / file).exists(), f"Missing file: {file}"

        # Verify A2A inspector setup for A2A agents
        if agent == "langgraph_base":
            # A2A agents use inspector which is installed at runtime via make inspector
            # Just verify the Makefile has the inspector target
            makefile_path = project_path / "Makefile"
            assert makefile_path.exists(), "Makefile missing"
            makefile_content = makefile_path.read_text()
            assert "inspector:" in makefile_content, (
                "inspector target missing in Makefile"
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
    # Edit here to manually force a specific combination e.g [("langgraph_base", "agent_engine", None)]
)
def test_agent_deployment(
    agent: str, deployment_target: str, extra_params: list[str] | None
) -> None:
    """Test agent templates with different deployment targets"""
    console.print(f"[bold cyan]Testing combination:[/] {agent}, {deployment_target}")
    _run_agent_test(agent, deployment_target, extra_params)
