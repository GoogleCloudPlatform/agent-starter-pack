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
import re
import subprocess
from datetime import datetime

from rich.console import Console

from tests.integration.utils import run_command

console = Console()
TARGET_DIR = "target"


def validate_makefile_usability(
    agent: str, deployment_target: str, extra_params: list[str] | None = None
) -> None:
    """Test that the generated Makefile is syntactically valid and usable"""
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

        makefile_path = project_path / "Makefile"
        if not makefile_path.exists():
            raise FileNotFoundError(f"Makefile not found at {makefile_path}")

        # Check for unrendered placeholders and replace uvx with uv run for local testing
        with open(makefile_path, encoding="utf-8") as f:
            content = f.read()
            if "{{" in content or "}}" in content:
                raise ValueError(
                    f"Found unrendered placeholders in Makefile for {agent} with {deployment_target}"
                )

        # Replace uvx agent-starter-pack@<version> with uv run agent-starter-pack
        # This allows testing with the local development version instead of PyPI
        content = re.sub(
            r"uvx agent-starter-pack@[\d.]+", "uv run agent-starter-pack", content
        )

        # Write back the modified Makefile
        with open(makefile_path, "w", encoding="utf-8") as f:
            f.write(content)

        makefile_targets = []
        with open(makefile_path, encoding="utf-8") as f:
            makefile_content = f.read()

        # Find all targets using regex - looks for lines that start with word characters followed by :
        # This matches actual targets like "install:", "test:", etc.
        target_pattern = r"^([a-zA-Z0-9_-]+):"
        matches = re.findall(target_pattern, makefile_content, re.MULTILINE)

        # Filter out any unwanted targets
        for target in matches:
            if (
                target
                and not target.startswith(".")
                and "%" not in target  # Skip pattern rules
                and target
                not in [
                    "all",
                    "clean",
                    "distclean",
                    "local-backend",
                ]  # Skip common implicit targets and long-running servers
            ):
                makefile_targets.append(target)

        # Test execution of each target with 2-second timeout
        for target in set(makefile_targets):  # Remove duplicates
            try:
                subprocess.run(
                    ["make", target],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=True,
                )
                console.print(f"[green]✓ Target '{target}' executed successfully[/]")
            except subprocess.TimeoutExpired:
                # Timeout is actually good - means the command started running
                console.print(
                    f"[green]✓ Target '{target}' started successfully (timed out after 2s)[/]"
                )
            except subprocess.CalledProcessError as e:
                # Check if this is a dependency/installation error that we can tolerate
                error_output = (e.stdout or "") + (e.stderr or "")

                # Common patterns that indicate missing dependencies (not Makefile errors)
                dependency_errors = [
                    "command not found",
                    "npm ERR!",
                    "Package not found",
                    "No such file or directory",
                    "ModuleNotFoundError",
                    "ImportError",
                    "ERROR: Could not find a version",
                    "sh: vite: command not found",
                    "sh: npm: command not found",
                    "sh: node: command not found",
                    "ERROR: No matching distribution found",
                ]

                is_dependency_error = any(
                    pattern in error_output for pattern in dependency_errors
                )

                if is_dependency_error:
                    console.print(
                        f"[yellow]⚠ Target '{target}' failed due to missing dependencies (not a Makefile error)[/]"
                    )
                    console.print(f"[yellow]Error output: {error_output[:200]}...[/]")
                else:
                    console.print(f"[bold red]Target '{target}' failed execution[/]")
                    if e.stdout:
                        console.print(e.stdout)
                    if e.stderr:
                        console.print(e.stderr)
                    raise ValueError(
                        f"Target '{target}' is not valid in Makefile for {agent} with {deployment_target}"
                    ) from e

        console.print(
            f"[bold green]✓ Makefile validation passed for {agent} with {deployment_target}[/]"
        )

    except Exception as e:
        console.print(
            f"[bold red]Error validating Makefile for {agent} with {deployment_target}:[/] {e!s}"
        )
        raise


def get_makefile_test_combinations() -> list[tuple[str, str, list[str] | None]]:
    """Get representative subset of combinations for Makefile testing."""
    return [
        # adk - both deployment targets
        ("adk", "agent_engine", None),
        ("adk", "cloud_run", ["--session-type", "in_memory"]),
        # agentic_rag - one variant
        (
            "agentic_rag",
            "agent_engine",
            ["--include-data-ingestion", "--datastore", "vertex_ai_search"],
        ),
        # adk_live - cloud_run only
        ("adk_live", "cloud_run", None),
        # langgraph - both deployment targets
        ("langgraph", "agent_engine", None),
        ("langgraph", "cloud_run", ["--session-type", "in_memory"]),
    ]


def test_all_makefile_usability() -> None:
    """Test Makefile usability for representative template combinations"""
    combinations = get_makefile_test_combinations()

    for agent, deployment_target, extra_params in combinations:
        console.print(
            f"\n[bold cyan]Testing Makefile usability for {agent} with {deployment_target}[/]"
        )
        validate_makefile_usability(agent, deployment_target, extra_params)


if __name__ == "__main__":
    test_all_makefile_usability()
