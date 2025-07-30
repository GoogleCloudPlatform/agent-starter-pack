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

from rich.console import Console

from tests.integration.utils import run_command

console = Console()
TARGET_DIR = "target"


def test_remote_templating() -> None:
    """Test creating an agent from a remote template."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    project_name = f"myagent-{timestamp}"
    output_dir = pathlib.Path(TARGET_DIR)
    project_path = output_dir / project_name
    remote_url = (
        "https://github.com/eliasecchig/adk-samples-copy/python/agents/gemini-fullstack"
    )

    try:
        # Create target directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Template the project from the remote URL
        cmd = [
            "python",
            "-m",
            "src.cli.main",
            "create",
            project_name,
            "-a",
            remote_url,
            "--deployment-target",
            "agent_engine",
            "--auto-approve",
            "--skip-checks",
        ]

        run_command(
            cmd,
            output_dir,
            f"Templating remote agent {project_name}",
        )

        # Verify essential files are created
        essential_files = [
            "pyproject.toml",
            "app/agent.py",
            "app/config.py",
            "README.md",
        ]
        for file in essential_files:
            assert (project_path / file).exists(), f"Missing file: {file}"

        run_command(
            [
                "uv",
                "sync",
                "--dev",
                "--extra",
                "lint",
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

        console.print(
            f"[bold green]✓[/] Remote templating test passed for {project_name}"
        )

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        raise
