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
REMOTE_URL = "adk@academic-research"


def _run_remote_templating_test(
    project_name: str,
    skip_version_lock: bool = False,
    deployment_target: str = "agent_engine",
) -> None:
    """Helper to run remote templating test with common logic.

    Args:
        project_name: Name for the generated project
        skip_version_lock: If True, set ASP_SKIP_VERSION_LOCK=1 to use local ASP
        deployment_target: Deployment target (agent_engine or cloud_run)
    """
    output_dir = pathlib.Path(TARGET_DIR)
    project_path = output_dir / project_name

    try:
        # Create target directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Set up environment
        env = os.environ.copy()
        if skip_version_lock:
            env["ASP_SKIP_VERSION_LOCK"] = "1"

        # Template the project from the remote URL
        cmd = [
            "python",
            "-m",
            "agent_starter_pack.cli.main",
            "create",
            project_name,
            "-a",
            REMOTE_URL,
            "--deployment-target",
            deployment_target,
            "--auto-approve",
            "--skip-checks",
        ]

        suffix = " (using local ASP)" if skip_version_lock else ""
        run_command(
            cmd,
            output_dir,
            f"Templating remote agent {project_name}{suffix}",
            env=env,
        )

        # Verify essential files are created
        essential_files = [
            "pyproject.toml",
            "README.md",
        ]
        for file in essential_files:
            assert (project_path / file).exists(), f"Missing file: {file}"

        # Find the agent directory (could be 'app' or the agent name like 'academic_research')
        agent_dirs = [
            d
            for d in project_path.iterdir()
            if d.is_dir() and (d / "agent.py").exists()
        ]
        assert len(agent_dirs) == 1, (
            f"Expected exactly one agent directory, found: {agent_dirs}"
        )
        agent_dir = agent_dirs[0]
        assert (agent_dir / "agent.py").exists(), "Missing agent.py in agent directory"

        # Install dependencies
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
            test_env = os.environ.copy()
            test_env["INTEGRATION_TEST"] = "TRUE"

            run_command(
                ["uv", "run", "pytest", test_dir],
                project_path,
                f"Running {test_dir} tests",
                env=test_env,
            )

        test_type = "with local ASP " if skip_version_lock else ""
        console.print(
            f"[bold green]✓[/] Remote templating {test_type}test passed for {project_name}"
        )

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e!s}")
        raise


def test_remote_templating() -> None:
    """Test creating an agent from a remote template."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    project_name = f"myagent-{timestamp}"
    _run_remote_templating_test(project_name, skip_version_lock=False)


def test_remote_templating_with_local_asp() -> None:
    """Test creating an agent from a remote template using local ASP version.

    Uses ASP_SKIP_VERSION_LOCK to bypass the uv.lock version constraint,
    allowing testing of remote templates with the current development version.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # Use shorter name prefix to stay within 26 char limit
    project_name = f"agent-l-{timestamp}"
    _run_remote_templating_test(project_name, skip_version_lock=True)


def test_remote_templating_cloud_run() -> None:
    """Test creating an agent from a remote template with Cloud Run deployment."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    project_name = f"agent-cr-{timestamp}"
    _run_remote_templating_test(
        project_name, skip_version_lock=True, deployment_target="cloud_run"
    )
