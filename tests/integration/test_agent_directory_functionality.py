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
import shutil
import tempfile
from datetime import datetime

import pytest
from rich.console import Console

from tests.integration.utils import run_command

console = Console()


class TestAgentDirectoryFunctionality:
    """Integration tests for the configurable agent directory feature."""

    def test_create_with_custom_agent_directory_via_remote_template(self) -> None:
        """Test creating a project with custom agent directory from remote template."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)

            # Create a mock remote template with custom agent directory
            remote_template = temp_path / "mock_remote_template"
            remote_template.mkdir(parents=True)

            # Create template structure
            (remote_template / ".template").mkdir()

            # Create pyproject.toml with custom agent directory
            pyproject_content = """[project]
name = "test-remote-template"
version = "0.1.0"
description = "Test template with custom agent directory"
dependencies = ["google-adk>=1.8.0"]

[tool.agent-starter-pack]
base_template = "adk"
name = "Custom Agent Directory Test"
description = "Test template with custom agent directory"

[tool.agent-starter-pack.settings]
agent_directory = "my_chatbot"
deployment_targets = ["agent_engine"]
"""
            (remote_template / "pyproject.toml").write_text(pyproject_content)

            # Create agent files in custom directory
            agent_dir = remote_template / "my_chatbot"
            agent_dir.mkdir()

            agent_content = '''from google.adk.agents import Agent

def greet(name: str = "World") -> str:
    """Greet someone."""
    return f"Hello, {name}! From custom agent directory."

root_agent = Agent(
    name="test_agent",
    model="gemini-3-flash-preview",
    instruction="You are a helpful assistant.",
    tools=[greet],
)
'''
            (agent_dir / "agent.py").write_text(agent_content)

            # Generate project name

            timestamp = datetime.now().strftime("%H%M%S%f")[
                :8
            ]  # Include microseconds for uniqueness, shorter
            project_name = f"test-dir-{timestamp}"
            # Account for name normalization (underscores become hyphens)
            normalized_project_name = project_name.replace("_", "-")
            project_path = temp_path / normalized_project_name

            try:
                # Run create command with local remote template
                cmd = [
                    "python",
                    "-m",
                    "agent_starter_pack.cli.main",
                    "create",
                    project_name,
                    "--agent",
                    f"local@{remote_template}",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--output-dir",
                    str(temp_path),
                ]

                result = run_command(
                    cmd, cwd=pathlib.Path.cwd(), message="Running CLI command"
                )

                # Verify the command succeeded
                assert result.returncode == 0, f"Create command failed: {result.stderr}"

                # Verify project was created
                assert project_path.exists(), "Project directory was not created"

                # Verify custom agent directory was created (not "app")
                chatbot_dir = project_path / "my_chatbot"
                app_dir = project_path / "app"

                assert chatbot_dir.exists(), (
                    "Custom agent directory 'my_chatbot' was not created"
                )
                assert not app_dir.exists(), "Default 'app' directory should not exist"

                # Verify agent.py exists in custom directory
                agent_py = chatbot_dir / "agent.py"
                assert agent_py.exists(), "agent.py not found in custom directory"

                # Verify the content is correct
                agent_content_generated = agent_py.read_text()
                # The App name should match the agent directory
                assert 'name="my_chatbot"' in agent_content_generated, (
                    "App name should match the custom agent directory"
                )

                # Verify pyproject.toml uses custom directory
                pyproject_toml = project_path / "pyproject.toml"
                assert pyproject_toml.exists(), "pyproject.toml not created"

                pyproject_content_generated = pyproject_toml.read_text()
                assert '"my_chatbot"' in pyproject_content_generated, (
                    "pyproject.toml should reference custom agent directory"
                )
                assert '"app"' not in pyproject_content_generated, (
                    "pyproject.toml should not reference default app directory"
                )

                # Verify Makefile uses custom directory
                makefile = project_path / "Makefile"
                assert makefile.exists(), "Makefile not created"

                makefile_content = makefile.read_text()
                assert "my_chatbot" in makefile_content, (
                    "Makefile should reference custom agent directory"
                )
                # Check for hardcoded app module references (not filenames)
                import re

                app_module_pattern = r"\bapp\."  # Word boundary to avoid matching filenames like "agent_engine_app.py"
                assert not re.search(app_module_pattern, makefile_content), (
                    "Makefile should not contain hardcoded app module references"
                )

                console.print(
                    f"✅ Successfully created project with custom agent directory: {project_name}"
                )

            finally:
                # Cleanup
                if project_path.exists():
                    shutil.rmtree(project_path, ignore_errors=True)

    def test_enhance_with_custom_agent_directory_cli_param(self) -> None:
        """Test enhance command with --agent-directory parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)

            # Create a mock existing project
            project_dir = temp_path / "existing_project"
            project_dir.mkdir()

            # Create custom agent directory
            agent_dir = project_dir / "assistant"
            agent_dir.mkdir()

            # Create basic agent.py
            agent_py = agent_dir / "agent.py"
            agent_py.write_text("""# Basic agent implementation
def main():
    print("Hello from assistant!")
""")

            # Create basic pyproject.toml
            pyproject_toml = project_dir / "pyproject.toml"
            pyproject_toml.write_text("""[project]
name = "existing-project"
version = "0.1.0"

[tool.hatch.build.targets.wheel]
packages = ["assistant"]
""")

            # Change to project directory
            original_cwd = pathlib.Path.cwd()

            try:
                os.chdir(project_dir)

                # Run enhance command with custom agent directory
                cmd = [
                    "python",
                    "-m",
                    "agent_starter_pack.cli.main",
                    "enhance",
                    ".",
                    "--agent-directory",
                    "assistant",
                    "--auto-approve",
                    "--skip-checks",
                ]

                result = run_command(
                    cmd, cwd=pathlib.Path.cwd(), message="Running CLI command"
                )

                # Verify the command succeeded
                assert result.returncode == 0, (
                    f"Enhance command failed: {result.stderr}"
                )

                # Verify the assistant directory still exists and wasn't replaced by app
                assert agent_dir.exists(), "Custom agent directory should still exist"
                assert not (project_dir / "app").exists(), (
                    "Default app directory should not be created"
                )

                # Verify enhanced files were created
                makefile = project_dir / "Makefile"
                assert makefile.exists(), "Makefile should be created by enhance"

                # Verify Makefile uses custom directory
                makefile_content = makefile.read_text()
                assert "assistant" in makefile_content, (
                    "Makefile should reference custom agent directory"
                )
                # Check for hardcoded app module references (not filenames)
                import re

                app_module_pattern = r"\bapp\."  # Word boundary to avoid matching filenames like "agent_engine_app.py"
                assert not re.search(app_module_pattern, makefile_content), (
                    "Makefile should not contain hardcoded app module references"
                )

                console.print(
                    "✅ Successfully enhanced project with custom agent directory via CLI"
                )

            finally:
                os.chdir(original_cwd)

    def test_enhance_uses_agent_directory_from_pyproject(self) -> None:
        """Test that enhance uses agent directory specified in pyproject.toml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)

            # Create a mock existing project
            project_dir = temp_path / "existing_project"
            project_dir.mkdir()

            # Create custom agent directory
            agent_dir = project_dir / "bot"
            agent_dir.mkdir()

            # Create basic agent.py
            agent_py = agent_dir / "agent.py"
            agent_py.write_text("""# Basic agent implementation
def main():
    print("Hello from bot!")
""")

            # Create pyproject.toml with custom agent directory setting
            pyproject_toml = project_dir / "pyproject.toml"
            pyproject_toml.write_text("""[project]
name = "existing-project"
version = "0.1.0"

[tool.hatch.build.targets.wheel]
packages = ["bot", "frontend"]

[tool.agent-starter-pack.settings]
agent_directory = "bot"
""")

            # Change to project directory
            original_cwd = pathlib.Path.cwd()

            try:
                os.chdir(project_dir)

                # Run enhance command without CLI agent directory (should read from pyproject.toml)
                cmd = [
                    "python",
                    "-m",
                    "agent_starter_pack.cli.main",
                    "enhance",
                    ".",
                    "--auto-approve",
                    "--skip-checks",
                ]

                result = run_command(
                    cmd, cwd=pathlib.Path.cwd(), message="Running CLI command"
                )

                # Verify the command succeeded
                assert result.returncode == 0, (
                    f"Enhance command failed: {result.stderr}"
                )

                # Verify the bot directory still exists
                assert agent_dir.exists(), "Custom agent directory should still exist"
                assert not (project_dir / "app").exists(), (
                    "Default app directory should not be created"
                )

                # Verify enhanced files were created
                makefile = project_dir / "Makefile"
                assert makefile.exists(), "Makefile should be created by enhance"

                # Verify Makefile uses agent directory from pyproject.toml
                makefile_content = makefile.read_text()
                assert "bot" in makefile_content, (
                    "Makefile should reference agent directory from pyproject.toml"
                )
                # Check for hardcoded app module references (not filenames)
                import re

                app_module_pattern = r"\bapp\."  # Word boundary to avoid matching filenames like "agent_engine_app.py"
                assert not re.search(app_module_pattern, makefile_content), (
                    "Makefile should not contain hardcoded app module references"
                )

                console.print(
                    "✅ Successfully enhanced project with agent directory from pyproject.toml"
                )

            finally:
                os.chdir(original_cwd)

    @pytest.mark.parametrize("deployment_target", ["cloud_run", "agent_engine"])
    def test_enhance_with_yaml_config_agent(self, deployment_target: str) -> None:
        """Test that enhance generates working agent.py shim for root_agent.yaml."""
        output_dir = pathlib.Path("target")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%H%M%S%f")[:8]
        project_name = f"yaml-{deployment_target[:3]}-{timestamp}"
        project_path = output_dir / project_name

        # Create project directory with YAML config agent
        # Use "my_agent" to avoid conflict with tests/integration/test_agent.py
        project_path.mkdir(parents=True)
        agent_dir = project_path / "my_agent"
        agent_dir.mkdir()

        # Create root_agent.yaml
        yaml_content = """name: my_agent
model: gemini-2.5-flash
instruction: You are a helpful assistant.
"""
        (agent_dir / "root_agent.yaml").write_text(yaml_content)

        # Run enhance command with YAML agent directory
        cmd = [
            "python",
            "-m",
            "agent_starter_pack.cli.main",
            "enhance",
            ".",
            "--agent-directory",
            "my_agent",
            "--base-template",
            "adk",
            "--deployment-target",
            deployment_target,
            "--auto-approve",
            "--skip-checks",
        ]

        run_command(cmd, cwd=project_path, message="Running enhance command")

        # Verify critical files were created
        assert (agent_dir / "__init__.py").exists(), (
            f"__init__.py not found in {agent_dir}"
        )
        assert (agent_dir / "agent.py").exists(), f"agent.py not found in {agent_dir}"

        # Install dependencies
        run_command(
            ["uv", "sync", "--dev"],
            project_path,
            "Installing dependencies",
            stream_output=False,
        )

        # Run integration tests (excluding test_agent.py) to verify app works
        test_env = os.environ.copy()
        test_env["INTEGRATION_TEST"] = "TRUE"

        run_command(
            [
                "uv",
                "run",
                "pytest",
                "tests/integration",
                "--ignore=tests/integration/test_agent.py",
                "-v",
            ],
            project_path,
            "Running integration tests",
            env=test_env,
        )

        console.print(
            f"[bold green]✓[/] YAML config agent test passed for {deployment_target}"
        )

    @pytest.mark.parametrize("deployment_target", ["cloud_run", "agent_engine"])
    def test_agent_directory_in_different_deployment_targets(
        self, deployment_target: str
    ) -> None:
        """Test that custom agent directories work with different deployment targets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)

            # Generate project name

            timestamp = datetime.now().strftime("%H%M%S%f")[
                :8
            ]  # Include microseconds for uniqueness, shorter
            project_name = f"test-{deployment_target[:3]}-{timestamp}"  # Shorten deployment target name too
            # Account for name normalization (underscores become hyphens)
            normalized_project_name = project_name.replace("_", "-")
            project_path = temp_path / normalized_project_name

            # Create a mock remote template with custom agent directory
            remote_template = temp_path / "mock_remote_template"
            remote_template.mkdir(parents=True)

            # Create template structure
            (remote_template / ".template").mkdir()

            # Create pyproject.toml with custom agent directory
            pyproject_content = f'''[project]
name = "test-remote-template"
version = "0.1.0"
description = "Test template with custom agent directory for {deployment_target}"
dependencies = ["google-adk>=1.8.0"]

[tool.agent-starter-pack]
base_template = "adk"

[tool.agent-starter-pack.settings]
agent_directory = "service"
deployment_targets = ["{deployment_target}"]
'''
            (remote_template / "pyproject.toml").write_text(pyproject_content)

            # Create agent files in custom directory
            agent_dir = remote_template / "service"
            agent_dir.mkdir()
            (agent_dir / "agent.py").write_text("# Test agent")

            try:
                # Run create command
                cmd = [
                    "python",
                    "-m",
                    "agent_starter_pack.cli.main",
                    "create",
                    project_name,
                    "--agent",
                    f"local@{remote_template}",
                    "--deployment-target",
                    deployment_target,
                    "--auto-approve",
                    "--skip-checks",
                    "--output-dir",
                    str(temp_path),
                ]

                result = run_command(
                    cmd, cwd=pathlib.Path.cwd(), message="Running CLI command"
                )

                # Verify the command succeeded
                assert result.returncode == 0, (
                    f"Create command failed for {deployment_target}: {result.stderr}"
                )

                # Verify custom agent directory exists
                service_dir = project_path / "service"
                assert service_dir.exists(), (
                    f"Custom agent directory 'service' not created for {deployment_target}"
                )

                # Verify deployment-specific files use custom directory
                if deployment_target == "cloud_run":
                    dockerfile = project_path / "Dockerfile"
                    if dockerfile.exists():
                        dockerfile_content = dockerfile.read_text()
                        assert "service" in dockerfile_content, (
                            f"Dockerfile should reference custom agent directory for {deployment_target}"
                        )

                console.print(
                    f"✅ Successfully tested custom agent directory with {deployment_target}"
                )

            finally:
                # Cleanup
                if project_path.exists():
                    shutil.rmtree(project_path, ignore_errors=True)
