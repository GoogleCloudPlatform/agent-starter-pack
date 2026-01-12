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
from tests.utils.get_agents import get_test_combinations_to_run

console = Console()
TARGET_DIR = "target"


def test_template_linting(
    agent: str, deployment_target: str, extra_params: list[str] | None = None
) -> None:
    """Test linting for a specific agent template"""
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
            f"Templating {agent} project with {deployment_target}",
        )

        # Check for unrendered placeholders in Makefile
        makefile_path = project_path / "Makefile"
        if makefile_path.exists():
            with open(makefile_path, encoding="utf-8") as f:
                content = f.read()
                if "{{" in content or "}}" in content:
                    raise ValueError(
                        f"Found unrendered placeholders in Makefile for {agent} with {deployment_target}"
                    )

        # Run make install and make lint (works for both Python and Go projects)
        run_command(["make", "install"], project_path, "Installing dependencies")
        run_command(["make", "lint"], project_path, "Running lint")

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
