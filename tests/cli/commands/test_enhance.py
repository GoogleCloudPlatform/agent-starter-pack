# Copyright 2026 Google LLC
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

import pathlib
import re
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from agent_starter_pack.cli.commands.enhance import (
    _build_enhance_create_args,
    display_base_template_selection,
    enhance,
)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


class TestDisplayBaseTemplateSelection:
    """Test the base template selection function."""

    @patch("agent_starter_pack.cli.commands.enhance.get_available_agents")
    @patch("agent_starter_pack.cli.commands.enhance.IntPrompt.ask")
    def test_base_template_selection_with_current_default(
        self, mock_prompt: MagicMock, mock_get_agents: MagicMock
    ) -> None:
        """Test that current base template is the default selection."""
        # Mock available agents
        mock_get_agents.return_value = {
            1: {"name": "adk", "description": "Basic agent template"},
            2: {"name": "langgraph", "description": "LangGraph ReAct agent"},
            3: {"name": "agentic_rag", "description": "RAG-enabled agent"},
        }

        # Mock user selecting default (current template)
        mock_prompt.return_value = 1

        result = display_base_template_selection("adk")

        assert result == "adk"
        # Check that prompt was called with the correct default (1 for adk)
        mock_prompt.assert_called_once()
        call_args = mock_prompt.call_args
        assert call_args[1]["default"] == 1

    @patch("agent_starter_pack.cli.commands.enhance.get_available_agents")
    @patch("agent_starter_pack.cli.commands.enhance.IntPrompt.ask")
    def test_base_template_selection_different_choice(
        self, mock_prompt: MagicMock, mock_get_agents: MagicMock
    ) -> None:
        """Test selecting a different base template."""
        # Mock available agents
        mock_get_agents.return_value = {
            1: {"name": "adk", "description": "Basic agent template"},
            2: {"name": "langgraph", "description": "LangGraph ReAct agent"},
            3: {"name": "agentic_rag", "description": "RAG-enabled agent"},
        }

        # Mock user selecting option 2
        mock_prompt.return_value = 2

        result = display_base_template_selection("adk")

        assert result == "langgraph"

    @patch("agent_starter_pack.cli.commands.enhance.get_available_agents")
    def test_base_template_selection_no_agents(
        self, mock_get_agents: MagicMock
    ) -> None:
        """Test error handling when no agents are available."""
        mock_get_agents.return_value = {}

        with pytest.raises(click.ClickException):
            display_base_template_selection("adk")


class TestEnhanceCommand:
    """Test the enhance command functionality."""

    @patch("agent_starter_pack.cli.utils.remote_template.get_base_template_name")
    @patch("agent_starter_pack.cli.utils.remote_template.load_remote_template_config")
    @patch("agent_starter_pack.cli.commands.enhance.display_base_template_selection")
    def test_enhance_with_interactive_base_template_selection(
        self,
        mock_display_selection: MagicMock,
        mock_load_config: MagicMock,
        mock_get_base_name: MagicMock,
    ) -> None:
        """Test that enhance prompts for base template when not provided via CLI."""
        # Mock the template config loading
        mock_get_base_name.return_value = "adk"
        mock_load_config.return_value = {"base_template": "adk"}
        mock_display_selection.return_value = "langgraph"

        runner = CliRunner()

        # Create a temporary directory to run enhance in
        with runner.isolated_filesystem():
            # Create an app directory to avoid structure warnings
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").touch()

            # Mock the create command to avoid actually running it
            with patch("agent_starter_pack.cli.commands.enhance.create"):
                # Run enhance without --auto-approve and without --base-template
                runner.invoke(
                    enhance,
                    [
                        ".",
                        "--auto-approve",
                        "--cicd-runner",
                        "skip",
                    ],  # Use auto-approve to skip confirmation prompts
                    input="y\n",  # Confirm enhancement
                )

                # The interactive selection should not be called with --auto-approve
                mock_display_selection.assert_not_called()

    def test_enhance_with_base_template_cli_param(self) -> None:
        """Test that enhance respects --base-template CLI parameter."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create app directory structure
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").touch()

            with patch("agent_starter_pack.cli.commands.enhance.create") as mock_create:
                runner.invoke(
                    enhance,
                    [
                        ".",
                        "--base-template",
                        "langgraph",
                        "--auto-approve",
                        "--cicd-runner",
                        "skip",
                    ],
                )

                # Should call create with the specified base template
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[1]["base_template"] == "langgraph"

    def test_enhance_with_agent_directory_cli_param(self) -> None:
        """Test that enhance respects --agent-directory CLI parameter."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create chatbot directory structure (custom agent directory)
            pathlib.Path("chatbot").mkdir()
            pathlib.Path("chatbot/agent.py").touch()

            with patch("agent_starter_pack.cli.commands.enhance.create") as mock_create:
                runner.invoke(
                    enhance,
                    [
                        ".",
                        "--agent-directory",
                        "chatbot",
                        "--auto-approve",
                        "--cicd-runner",
                        "skip",
                    ],
                )

                # Should call create with the specified agent directory in cli_overrides
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                cli_overrides = call_args[1]["cli_overrides"]
                assert cli_overrides is not None
                assert cli_overrides["settings"]["agent_directory"] == "chatbot"

    @patch("agent_starter_pack.cli.commands.enhance.tomllib.load")
    def test_enhance_auto_detects_agent_directory_from_pyproject(
        self, mock_tomllib_load: MagicMock
    ) -> None:
        """Test that enhance auto-detects agent directory from pyproject.toml."""
        runner = CliRunner()

        # Mock pyproject.toml content with custom packages
        mock_tomllib_load.return_value = {
            "tool": {
                "hatch": {
                    "build": {
                        "targets": {"wheel": {"packages": ["my_agent", "frontend"]}}
                    }
                }
            }
        }

        with runner.isolated_filesystem():
            # Create custom agent directory structure
            pathlib.Path("my_agent").mkdir()
            pathlib.Path("my_agent/agent.py").touch()
            pathlib.Path("pyproject.toml").touch()

            with patch("agent_starter_pack.cli.commands.enhance.create") as mock_create:
                runner.invoke(
                    enhance,
                    [".", "--auto-approve", "--cicd-runner", "skip"],
                )

                # Should call create and detect 'my_agent' from pyproject.toml
                mock_create.assert_called_once()
                # The detected agent directory should be used internally
                # (this tests the detection logic runs successfully)

    def test_enhance_cli_agent_directory_overrides_detection(self) -> None:
        """Test that CLI --agent-directory parameter overrides auto-detection."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create both directories
            pathlib.Path("detected_agent").mkdir()
            pathlib.Path("detected_agent/agent.py").touch()
            pathlib.Path("cli_agent").mkdir()
            pathlib.Path("cli_agent/agent.py").touch()

            # Create pyproject.toml that would detect 'detected_agent'
            pyproject_content = """
[tool.hatch.build.targets.wheel]
packages = ["detected_agent", "frontend"]
"""
            pathlib.Path("pyproject.toml").write_text(
                pyproject_content, encoding="utf-8"
            )

            with patch("agent_starter_pack.cli.commands.enhance.create") as mock_create:
                runner.invoke(
                    enhance,
                    [
                        ".",
                        "--agent-directory",
                        "cli_agent",
                        "--auto-approve",
                        "--cicd-runner",
                        "skip",
                    ],
                )

                # CLI parameter should override auto-detection
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                cli_overrides = call_args[1]["cli_overrides"]
                assert cli_overrides is not None
                assert cli_overrides["settings"]["agent_directory"] == "cli_agent"

    def test_enhance_warns_about_missing_agent_directory(self) -> None:
        """Test that enhance shows warning when agent directory doesn't exist."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Don't create any agent directory

            with patch("agent_starter_pack.cli.commands.enhance.create") as mock_create:
                result = runner.invoke(
                    enhance,
                    [
                        ".",
                        "--agent-directory",
                        "missing_agent",
                        "--auto-approve",
                        "--cicd-runner",
                        "skip",
                    ],
                )

                # Should show warning about missing directory but still proceed
                assert "PROJECT STRUCTURE WARNING" in result.output
                assert "missing_agent" in result.output
                mock_create.assert_called_once()

    def test_enhance_with_combined_params(self) -> None:
        """Test enhance with both --base-template and --agent-directory."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create custom agent directory
            pathlib.Path("my_chatbot").mkdir()
            pathlib.Path("my_chatbot/agent.py").touch()

            with patch("agent_starter_pack.cli.commands.enhance.create") as mock_create:
                runner.invoke(
                    enhance,
                    [
                        ".",
                        "--base-template",
                        "langgraph",
                        "--agent-directory",
                        "my_chatbot",
                        "--auto-approve",
                        "--cicd-runner",
                        "skip",
                    ],
                )

                # Should call create with both parameters
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[1]["base_template"] == "langgraph"

                cli_overrides = call_args[1]["cli_overrides"]
                assert cli_overrides is not None
                assert cli_overrides["base_template"] == "langgraph"
                assert cli_overrides["settings"]["agent_directory"] == "my_chatbot"

    def test_enhance_with_adk_flag_sets_base_template(self) -> None:
        """Test that --adk flag sets base_template to adk."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create app directory structure
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").touch()

            with patch("agent_starter_pack.cli.commands.enhance.create") as mock_create:
                runner.invoke(
                    enhance,
                    [".", "--adk", "--auto-approve", "--cicd-runner", "skip"],
                )

                # Should call create with base_template set to adk
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[1]["base_template"] == "adk"

    def test_enhance_adk_flag_conflicts_with_base_template(self) -> None:
        """Test that --adk and --base-template cannot be used together."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create app directory structure
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").touch()

            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--adk",
                    "--base-template",
                    "langgraph",
                    "--auto-approve",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Should fail with an error about conflicting options
            assert result.exit_code != 0
            assert "Cannot use --adk with --base-template" in result.output


class TestEnhanceAgentEngineAppGeneration:
    """Test that enhance properly generates agent_engine_app.py with correct imports."""

    @pytest.mark.parametrize(
        "base_template,expected_import",
        [
            ("adk", "app as adk_app"),
            ("adk_live", "app as adk_app"),
            ("langgraph", "agent"),
            ("agentic_rag", "app as adk_app"),  # agentic_rag is ADK-based
        ],
    )
    def test_agent_engine_app_has_correct_import(
        self, base_template: str, expected_import: str, tmp_path: pathlib.Path
    ) -> None:
        """Test that agent_engine_app.py imports the correct variable based on base template."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory with agent.py
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            agent_file = agent_dir / "agent.py"

            # Create appropriate agent.py content based on template type
            if "adk" in base_template or base_template == "agentic_rag":
                agent_content = """from google.adk.agents import Agent
from google.adk.apps import App

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

app = App(root_agent=root_agent, name="app")
"""
            else:
                agent_content = """from langchain_core.runnables import RunnablePassthrough

agent = RunnablePassthrough()
"""
            agent_file.write_text(agent_content)

            # Run enhance with the specified base template
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    base_template,
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify agent.py content was NOT modified (customer file preservation)
            preserved_agent_content = agent_file.read_text()
            assert preserved_agent_content == agent_content, (
                f"agent.py was modified! Expected:\n{agent_content}\n\nGot:\n{preserved_agent_content}"
            )

            # Verify agent_engine_app.py was created (deployment target specific)
            agent_engine_app = agent_dir / "agent_engine_app.py"
            assert agent_engine_app.exists(), (
                f"agent_engine_app.py not created in {agent_dir}"
            )

            # Read the content and verify the correct import
            content = agent_engine_app.read_text()

            # For A2A non-ADK agents (like langgraph), they don't import from app.agent
            if base_template == "langgraph":
                # Verify A2A-specific imports for LangGraph agents
                # Check both module path and class name (handles multi-line formatting)
                assert (
                    "from app.app_utils.executor.a2a_agent_executor import" in content
                    and "LangGraphAgentExecutor" in content
                ), (
                    f"Expected A2A LangGraph imports in agent_engine_app.py but got:\n{content}"
                )
            else:
                # For ADK-based agents, verify the standard import
                expected_import_line = f"from app.agent import {expected_import}"
                assert expected_import_line in content, (
                    f"Expected '{expected_import_line}' in agent_engine_app.py but got:\n{content}"
                )

    def test_agent_engine_app_created_in_custom_agent_directory(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that agent_engine_app.py is created in custom agent directory."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create custom agent directory
            agent_dir = pathlib.Path("my_custom_agent")
            agent_dir.mkdir()
            agent_file = agent_dir / "agent.py"
            agent_content = """from google.adk.agents import Agent
from google.adk.apps import App

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

app = App(root_agent=root_agent, name="app")
"""
            agent_file.write_text(agent_content)

            # Run enhance with custom agent directory
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk",
                    "--agent-directory",
                    "my_custom_agent",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify agent.py content was NOT modified (customer file preservation)
            preserved_agent_content = agent_file.read_text()
            assert preserved_agent_content == agent_content, (
                f"agent.py in custom directory was modified! Expected:\n{agent_content}\n\nGot:\n{preserved_agent_content}"
            )

            # Verify agent_engine_app.py was created in custom directory
            agent_engine_app = agent_dir / "agent_engine_app.py"
            assert agent_engine_app.exists(), (
                f"agent_engine_app.py not created in {agent_dir}"
            )

            # Verify the import uses the custom directory name
            content = agent_engine_app.read_text()
            expected_import_line = "from my_custom_agent.agent import app as adk_app"
            assert expected_import_line in content, (
                f"Expected '{expected_import_line}' in agent_engine_app.py"
            )


class TestEnhanceAgentDirectoryPrompt:
    """Test that enhance shows the correct required variable in prompts."""

    @patch("agent_starter_pack.cli.commands.enhance.display_agent_directory_selection")
    @patch("agent_starter_pack.cli.utils.remote_template.get_base_template_name")
    @patch("agent_starter_pack.cli.utils.remote_template.load_remote_template_config")
    def test_prompt_shows_root_agent_for_adk_templates(
        self,
        mock_load_config: MagicMock,
        mock_get_base_name: MagicMock,
        mock_display_selection: MagicMock,
    ) -> None:
        """Test that agent directory prompt shows 'root_agent' for ADK templates."""
        runner = CliRunner()

        # Mock the template config to return an ADK base template
        mock_get_base_name.return_value = "adk"
        mock_load_config.return_value = {"base_template": "adk"}
        mock_display_selection.return_value = "app"

        with runner.isolated_filesystem():
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            with patch("agent_starter_pack.cli.commands.enhance.create"):
                runner.invoke(
                    enhance,
                    [".", "--base-template", "adk"],
                    input="n\n",  # Cancel enhancement
                )

                # Verify display_agent_directory_selection was called with base_template
                if mock_display_selection.called:
                    call_args = mock_display_selection.call_args
                    # The base_template should be passed to the function
                    assert call_args[0][2] == "adk"  # Third positional arg

    @patch("agent_starter_pack.cli.commands.enhance.display_agent_directory_selection")
    @patch("agent_starter_pack.cli.utils.remote_template.get_base_template_name")
    @patch("agent_starter_pack.cli.utils.remote_template.load_remote_template_config")
    def test_prompt_shows_agent_for_non_adk_templates(
        self,
        mock_load_config: MagicMock,
        mock_get_base_name: MagicMock,
        mock_display_selection: MagicMock,
    ) -> None:
        """Test that agent directory prompt shows 'agent' for non-ADK templates."""
        runner = CliRunner()

        # Mock the template config to return a non-ADK base template
        mock_get_base_name.return_value = "langgraph"
        mock_load_config.return_value = {"base_template": "langgraph"}
        mock_display_selection.return_value = "app"

        with runner.isolated_filesystem():
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("agent = None")

            with patch("agent_starter_pack.cli.commands.enhance.create"):
                runner.invoke(
                    enhance,
                    [".", "--base-template", "langgraph"],
                    input="n\n",  # Cancel enhancement
                )

                # Verify display_agent_directory_selection was called with base_template
                if mock_display_selection.called:
                    call_args = mock_display_selection.call_args
                    # The base_template should be passed to the function
                    assert call_args[0][2] == "langgraph"


class TestEnhanceFilePopulation:
    """Test that enhance properly populates files based on configuration."""

    def test_adk_live_populates_frontend_files(self, tmp_path: pathlib.Path) -> None:
        """Test that adk_live agent populates frontend files (regression test for bug)."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory with adk_live agent.py
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            agent_file = agent_dir / "agent.py"

            agent_content = """from google.adk.agents import Agent

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)
"""
            agent_file.write_text(agent_content)

            # Run enhance with adk_live base template
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk_live",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify frontend files were populated for adk_live
            # adk_live uses adk_live_react frontend
            frontend_dir = pathlib.Path("frontend")
            assert frontend_dir.exists(), "Frontend directory was not created"

            # Check for key frontend files
            key_frontend_files = [
                frontend_dir / "src" / "App.tsx",
                frontend_dir / "src" / "index.tsx",
                frontend_dir / "package.json",
            ]

            for frontend_file in key_frontend_files:
                assert frontend_file.exists(), (
                    f"Expected frontend file {frontend_file} was not created for adk_live"
                )

            # Verify agent.py was modified to add app object (backward compatibility)
            preserved_agent_content = agent_file.read_text()
            expected_content = """from google.adk.agents import Agent

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

from google.adk.apps import App

app = App(root_agent=root_agent, name="app")
"""
            assert preserved_agent_content == expected_content, (
                f"agent.py was not modified correctly! Expected:\n{expected_content}\n\nGot:\n{preserved_agent_content}"
            )

    def test_cloud_run_deployment_populates_files(self, tmp_path: pathlib.Path) -> None:
        """Test that Cloud Run deployment target populates deployment-specific files."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            agent_file = agent_dir / "agent.py"

            agent_content = """from google.adk.agents import Agent
from google.adk.apps import App

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

app = App(root_agent=root_agent, name="app")
"""
            agent_file.write_text(agent_content)

            # Run enhance with cloud_run deployment target and explicit cicd-runner
            # (auto-approve defaults to 'skip' which doesn't generate Terraform)
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk",
                    "--deployment-target",
                    "cloud_run",
                    "--cicd-runner",
                    "google_cloud_build",
                    "--auto-approve",
                    "--skip-checks",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify Cloud Run specific files were populated
            cloud_run_files = [
                agent_dir / "fast_api_app.py",  # Cloud Run FastAPI app
                pathlib.Path("Dockerfile"),  # Cloud Run Dockerfile
                pathlib.Path("deployment") / "terraform" / "service.tf",
            ]

            for cloud_run_file in cloud_run_files:
                assert cloud_run_file.exists(), (
                    f"Expected Cloud Run file {cloud_run_file} was not created"
                )

            # Verify agent.py was NOT modified for cloud_run (no injection for cloud_run)
            preserved_agent_content = agent_file.read_text()
            # For cloud_run, agent.py should remain unchanged
            assert preserved_agent_content == agent_content, (
                f"agent.py should not be modified for cloud_run! Expected:\n{agent_content}\n\nGot:\n{preserved_agent_content}"
            )

    def test_data_ingestion_populates_files(self, tmp_path: pathlib.Path) -> None:
        """Test that --include-data-ingestion actually populates data pipeline files."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            agent_file = agent_dir / "agent.py"

            agent_content = """from google.adk.agents import Agent

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)
"""
            agent_file.write_text(agent_content)

            # Run enhance with data ingestion enabled
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk",
                    "--deployment-target",
                    "agent_engine",
                    "--include-data-ingestion",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify data ingestion files were populated
            data_ingestion_files = [
                pathlib.Path("data_ingestion")
                / "data_ingestion_pipeline"
                / "pipeline.py",
                pathlib.Path("data_ingestion")
                / "data_ingestion_pipeline"
                / "submit_pipeline.py",
                pathlib.Path("data_ingestion")
                / "data_ingestion_pipeline"
                / "components"
                / "ingest_data.py",
                pathlib.Path("data_ingestion")
                / "data_ingestion_pipeline"
                / "components"
                / "process_data.py",
            ]

            for data_file in data_ingestion_files:
                assert data_file.exists(), (
                    f"Expected data ingestion file {data_file} was not created"
                )

            # Verify agent.py was modified to add app object (backward compatibility)
            preserved_agent_content = agent_file.read_text()
            expected_content = """from google.adk.agents import Agent

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

from google.adk.apps import App

app = App(root_agent=root_agent, name="app")
"""
            assert preserved_agent_content == expected_content, (
                f"agent.py was not modified correctly! Expected:\n{expected_content}\n\nGot:\n{preserved_agent_content}"
            )


class TestEnhanceYamlAgentShim:
    """Test that enhance properly generates agent.py shim for YAML config agents."""

    def test_yaml_agent_shim_generated_for_agent_engine(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that agent.py shim is generated when root_agent.yaml exists."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory with root_agent.yaml (no agent.py)
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            yaml_file = agent_dir / "root_agent.yaml"

            yaml_content = """name: test_agent
model: gemini-2.0-flash-001
instruction: You are a helpful assistant.
"""
            yaml_file.write_text(yaml_content)

            # Run enhance with agent_engine deployment target
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify agent.py shim was generated
            agent_file = agent_dir / "agent.py"
            assert agent_file.exists(), "agent.py shim was not created"

            content = agent_file.read_text()

            # Verify the shim loads from YAML config
            assert "config_agent_utils" in content, (
                f"Expected config_agent_utils import in agent.py but got:\n{content}"
            )
            assert 'from_config(str(_AGENT_DIR / "root_agent.yaml"))' in content, (
                f"Expected from_config call in agent.py but got:\n{content}"
            )
            assert "root_agent = " in content, (
                f"Expected root_agent assignment in agent.py but got:\n{content}"
            )
            assert "app = App(" in content, (
                f"Expected app assignment in agent.py but got:\n{content}"
            )
            assert 'name="app"' in content, (
                f"Expected App name='app' (matching agent directory) but got:\n{content}"
            )

            # Verify root_agent.yaml was preserved
            preserved_yaml = yaml_file.read_text()
            assert preserved_yaml == yaml_content, (
                f"root_agent.yaml was modified! Expected:\n{yaml_content}\n\nGot:\n{preserved_yaml}"
            )

            # Verify the generated shim is valid Python syntax
            compile(content, agent_file, "exec")

    def test_yaml_agent_shim_generated_for_cloud_run(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that agent.py shim is generated for Cloud Run deployment."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory with root_agent.yaml
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            yaml_file = agent_dir / "root_agent.yaml"

            yaml_content = """name: test_agent
model: gemini-2.0-flash-001
instruction: You are a helpful assistant.
"""
            yaml_file.write_text(yaml_content)

            # Run enhance with cloud_run deployment target
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk",
                    "--deployment-target",
                    "cloud_run",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify agent.py shim was generated
            agent_file = agent_dir / "agent.py"
            assert agent_file.exists(), "agent.py shim was not created for cloud_run"

            content = agent_file.read_text()

            # Verify the shim loads from YAML config
            assert "config_agent_utils" in content, (
                f"Expected config_agent_utils import in agent.py but got:\n{content}"
            )
            assert 'from_config(str(_AGENT_DIR / "root_agent.yaml"))' in content, (
                f"Expected from_config call in agent.py but got:\n{content}"
            )

    def test_yaml_agent_shim_in_custom_directory(self, tmp_path: pathlib.Path) -> None:
        """Test that agent.py shim is generated in custom agent directory."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create custom agent directory with root_agent.yaml
            agent_dir = pathlib.Path("my_agent")
            agent_dir.mkdir()
            yaml_file = agent_dir / "root_agent.yaml"

            yaml_content = """name: custom_agent
model: gemini-2.0-flash-001
"""
            yaml_file.write_text(yaml_content)

            # Run enhance with custom agent directory
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk",
                    "--agent-directory",
                    "my_agent",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify agent.py shim was generated in custom directory
            agent_file = agent_dir / "agent.py"
            assert agent_file.exists(), f"agent.py shim was not created in {agent_dir}"

            content = agent_file.read_text()
            assert "config_agent_utils" in content
            # Verify app name matches the custom agent directory
            assert 'name="my_agent"' in content, (
                f"Expected app name to match agent directory 'my_agent' but got:\n{content}"
            )

    def test_yaml_agent_detection_message_shown(self, tmp_path: pathlib.Path) -> None:
        """Test that enhance shows YAML config agent detection message."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory with root_agent.yaml
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            yaml_file = agent_dir / "root_agent.yaml"
            yaml_file.write_text("name: test_agent\n")

            # Run enhance
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Verify the YAML detection message was shown
            assert "root_agent.yaml" in result.output, (
                f"Expected YAML detection message in output:\n{result.output}"
            )
            assert "YAML config agent" in result.output, (
                f"Expected 'YAML config agent' in output:\n{result.output}"
            )

    def test_yaml_agent_shim_overwrites_template_agent_py(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that YAML shim overwrites the base template's agent.py."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory with root_agent.yaml
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            yaml_file = agent_dir / "root_agent.yaml"
            yaml_file.write_text("name: yaml_agent\nmodel: gemini-2.0-flash-001\n")

            # Run enhance - base template will copy its agent.py first,
            # but YAML shim should overwrite it
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify agent.py contains the shim, not the base template content
            agent_file = agent_dir / "agent.py"
            content = agent_file.read_text()

            # Should have the YAML loader, not the base template's Agent definition
            assert "config_agent_utils" in content, (
                "agent.py should contain YAML shim, not base template content"
            )
            assert 'from_config(str(_AGENT_DIR / "root_agent.yaml"))' in content, (
                "agent.py should load from root_agent.yaml"
            )

            # Should NOT have the base template's get_weather function
            assert "get_weather" not in content, (
                "agent.py should not contain base template's get_weather function"
            )


class TestEnhanceAdkAppInjection:
    """Test that enhance properly injects app object for all ADK templates."""

    @pytest.mark.parametrize(
        "base_template",
        [
            "adk",
            "adk_a2a",
            "adk_live",
        ],
    )
    def test_app_injected_for_adk_templates_without_app(
        self, base_template: str, tmp_path: pathlib.Path
    ) -> None:
        """Test that app object is injected for ADK templates that only have root_agent."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory with ONLY root_agent (no app)
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            agent_file = agent_dir / "agent.py"

            # This simulates a remote template that only defines root_agent
            agent_content = """from google.adk.agents import Agent

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
    instruction="You are a helpful assistant.",
)
"""
            agent_file.write_text(agent_content)

            # Run enhance with the ADK base template
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    base_template,
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify app object was injected
            modified_content = agent_file.read_text()
            assert "from google.adk.apps import App" in modified_content, (
                f"Expected App import to be injected for {base_template}"
            )
            assert 'app = App(root_agent=root_agent, name="app")' in modified_content, (
                f"Expected app object to be injected for {base_template}"
            )

    def test_app_not_injected_for_non_adk_templates(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that app object is NOT injected for non-ADK templates."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory with agent (not root_agent)
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            agent_file = agent_dir / "agent.py"

            agent_content = """from langchain_core.runnables import RunnablePassthrough

agent = RunnablePassthrough()
"""
            agent_file.write_text(agent_content)

            # Run enhance with langgraph (non-ADK)
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "langgraph",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            # Check that enhance succeeded
            assert result.exit_code == 0, (
                f"Enhance failed with output:\n{result.output}"
            )

            # Verify app object was NOT injected (langgraph doesn't need it)
            modified_content = agent_file.read_text()
            assert "from google.adk.apps import App" not in modified_content, (
                "App import should NOT be injected for langgraph"
            )

    def test_app_not_injected_when_already_present(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that app object is not duplicated when already present."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create agent directory with both root_agent AND app
            agent_dir = pathlib.Path("app")
            agent_dir.mkdir()
            agent_file = agent_dir / "agent.py"

            agent_content = """from google.adk.agents import Agent
from google.adk.apps import App

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

app = App(root_agent=root_agent, name="my_agent")
"""
            agent_file.write_text(agent_content)

            # Run enhance
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
                    "--cicd-runner",
                    "skip",
                ],
            )

            assert result.exit_code == 0

            # Verify content was NOT modified (app already exists)
            modified_content = agent_file.read_text()
            assert modified_content == agent_content, (
                "agent.py should not be modified when app already exists"
            )

    def test_is_adk_derived_from_base_template_name_not_tags(self) -> None:
        """Verify is_adk is derived from base_template_name, not tags.

        This is the core fix: remote templates using adk_a2a may not
        have explicit tags, but should still get app injection based on
        the base_template_name containing 'adk'.
        """
        test_cases = [
            ("adk", True),
            ("adk_a2a", True),
            ("adk_live", True),
            ("ADK_BASE", True),  # Case insensitive
            ("langgraph", False),
            ("agentic_rag", False),
        ]

        for base_template_name, expected_is_adk in test_cases:
            is_adk_enhance = (
                base_template_name is not None and "adk" in base_template_name.lower()
            )

            is_adk_template = "adk" in base_template_name.lower()

            assert is_adk_enhance == expected_is_adk, (
                f"enhance.py pattern failed for {base_template_name}"
            )
            assert is_adk_template == expected_is_adk, (
                f"template.py pattern failed for {base_template_name}"
            )
            assert is_adk_enhance == is_adk_template, (
                f"Patterns don't match for {base_template_name}"
            )


class TestBuildEnhanceCreateArgs:
    """Test the _build_enhance_create_args helper function."""

    def test_basic_metadata_conversion(self) -> None:
        """Test converting project metadata to CLI args."""
        config = {
            "base_template": "adk",
            "agent_directory": "app",
            "create_params": {
                "deployment_target": "agent_engine",
                "session_type": "in_memory",
            },
        }
        args = _build_enhance_create_args(config)
        assert "--agent" in args
        assert "adk" in args
        assert "--deployment-target" in args
        assert "agent_engine" in args
        assert "--session-type" in args
        assert "in_memory" in args

    def test_cli_overrides_take_precedence(self) -> None:
        """Test that CLI overrides replace saved config values."""
        config = {
            "base_template": "adk",
            "create_params": {
                "deployment_target": "agent_engine",
            },
        }
        overrides = {"deployment_target": "cloud_run"}
        args = _build_enhance_create_args(config, overrides)
        assert "cloud_run" in args
        assert "agent_engine" not in args

    def test_no_overrides_returns_metadata_args(self) -> None:
        """Test with no overrides returns metadata-based args only."""
        config = {
            "base_template": "adk",
            "create_params": {"deployment_target": "cloud_run"},
        }
        args = _build_enhance_create_args(config, None)
        assert "--agent" in args
        assert "adk" in args
        assert "--deployment-target" in args
        assert "cloud_run" in args

    def test_skip_values_are_filtered(self) -> None:
        """Test that skip/none values are filtered from overrides."""
        config = {
            "base_template": "adk",
            "create_params": {},
        }
        overrides = {"cicd_runner": "skip", "deployment_target": "cloud_run"}
        args = _build_enhance_create_args(config, overrides)
        assert "--cicd-runner" not in args
        assert "--deployment-target" in args


class TestSmartMerge:
    """Test the smart-merge functionality in enhance command."""

    @patch("agent_starter_pack.cli.commands.enhance.run_create_command")
    def test_smart_merge_auto_updates_unchanged_files(
        self, mock_create, tmp_path: pathlib.Path
    ) -> None:
        """Test that unchanged files are auto-updated via smart-merge."""

        def create_template(args, output_dir, project_name, version=None):
            del version
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            if "--deployment-target" in args and "cloud_run" in args:
                # New template (enhanced)
                (template_dir / "Makefile").write_text("# Enhanced Makefile")
                (template_dir / "Dockerfile").write_text("FROM python:3.11")
            else:
                # Old template (original)
                (template_dir / "Makefile").write_text("# Original Makefile")
            return True

        mock_create.side_effect = create_template

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create project with ASP metadata
            pyproject = pathlib.Path("pyproject.toml")
            pyproject.write_text(
                '[project]\nname = "test"\ndependencies = []\n\n'
                '[tool.agent-starter-pack]\nname = "test"\n'
                'base_template = "adk"\nasp_version = "0.30.0"\n\n'
                "[tool.agent-starter-pack.create_params]\n"
                'deployment_target = "agent_engine"\n'
            )
            # Makefile matches old template (user didn't modify)
            pathlib.Path("Makefile").write_text("# Original Makefile")

            # Create agent directory
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--deployment-target",
                    "cloud_run",
                    "--auto-approve",
                    "--cicd-runner",
                    "skip",
                ],
            )

            output = strip_ansi(result.output)
            assert result.exit_code == 0, f"Failed with output:\n{result.output}"

            # Verify Makefile was auto-updated
            assert "Enhanced Makefile" in pathlib.Path("Makefile").read_text()

    @patch("agent_starter_pack.cli.commands.enhance.run_create_command")
    def test_smart_merge_preserves_user_modified_files(
        self, mock_create, tmp_path: pathlib.Path
    ) -> None:
        """Test that user-modified files are preserved when template didn't change."""

        def create_template(args, output_dir, project_name, version=None):
            del version, args
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            # Same content in old and new template
            (template_dir / "Makefile").write_text("# Template Makefile")
            return True

        mock_create.side_effect = create_template

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            pyproject = pathlib.Path("pyproject.toml")
            pyproject.write_text(
                '[project]\nname = "test"\ndependencies = []\n\n'
                '[tool.agent-starter-pack]\nname = "test"\n'
                'base_template = "adk"\nasp_version = "0.30.0"\n\n'
                "[tool.agent-starter-pack.create_params]\n"
                'deployment_target = "agent_engine"\n'
            )
            # User modified the Makefile
            pathlib.Path("Makefile").write_text("# My custom Makefile")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--deployment-target",
                    "cloud_run",
                    "--auto-approve",
                    "--cicd-runner",
                    "skip",
                ],
            )

            output = strip_ansi(result.output)
            assert result.exit_code == 0, f"Failed with output:\n{result.output}"

            # Verify user's Makefile was preserved
            assert "My custom Makefile" in pathlib.Path("Makefile").read_text()

    @patch("agent_starter_pack.cli.commands.enhance.run_create_command")
    def test_smart_merge_detects_conflicts(
        self, mock_create, tmp_path: pathlib.Path
    ) -> None:
        """Test that conflicts are detected when both user and template changed."""

        def create_template(args, output_dir, project_name, version=None):
            del version
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            if "--deployment-target" in args and "cloud_run" in args:
                (template_dir / "Makefile").write_text("# New template Makefile")
            else:
                (template_dir / "Makefile").write_text("# Old template Makefile")
            return True

        mock_create.side_effect = create_template

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            pyproject = pathlib.Path("pyproject.toml")
            pyproject.write_text(
                '[project]\nname = "test"\ndependencies = []\n\n'
                '[tool.agent-starter-pack]\nname = "test"\n'
                'base_template = "adk"\nasp_version = "0.30.0"\n\n'
                "[tool.agent-starter-pack.create_params]\n"
                'deployment_target = "agent_engine"\n'
            )
            # User modified (different from both templates)
            pathlib.Path("Makefile").write_text("# User modified Makefile")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--deployment-target",
                    "cloud_run",
                    "--auto-approve",
                    "--cicd-runner",
                    "skip",
                ],
            )

            output = strip_ansi(result.output)
            assert result.exit_code == 0, f"Failed with output:\n{result.output}"
            assert "Conflict" in output
            # With auto-approve, user's version is kept
            assert "User modified Makefile" in pathlib.Path("Makefile").read_text()

    @patch("agent_starter_pack.cli.commands.enhance.run_create_command")
    def test_smart_merge_adds_new_files(
        self, mock_create, tmp_path: pathlib.Path
    ) -> None:
        """Test that new files from the enhanced template are added."""

        def create_template(args, output_dir, project_name, version=None):
            del version
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            (template_dir / "Makefile").write_text("# Makefile")
            if "--deployment-target" in args and "cloud_run" in args:
                # New template has a Dockerfile that old doesn't
                (template_dir / "Dockerfile").write_text("FROM python:3.11")
            return True

        mock_create.side_effect = create_template

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            pyproject = pathlib.Path("pyproject.toml")
            pyproject.write_text(
                '[project]\nname = "test"\ndependencies = []\n\n'
                '[tool.agent-starter-pack]\nname = "test"\n'
                'base_template = "adk"\nasp_version = "0.30.0"\n\n'
                "[tool.agent-starter-pack.create_params]\n"
                'deployment_target = "agent_engine"\n'
            )
            pathlib.Path("Makefile").write_text("# Makefile")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--deployment-target",
                    "cloud_run",
                    "--auto-approve",
                    "--cicd-runner",
                    "skip",
                ],
            )

            output = strip_ansi(result.output)
            assert result.exit_code == 0, f"Failed with output:\n{result.output}"
            assert "New files" in output
            # Verify new file was added
            assert pathlib.Path("Dockerfile").exists()

    @patch("agent_starter_pack.cli.commands.enhance.run_create_command")
    def test_smart_merge_dry_run(self, mock_create, tmp_path: pathlib.Path) -> None:
        """Test that --dry-run shows changes without applying."""

        def create_template(args, output_dir, project_name, version=None):
            del version
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            if "--deployment-target" in args and "cloud_run" in args:
                (template_dir / "Makefile").write_text("# Enhanced Makefile")
                (template_dir / "Dockerfile").write_text("FROM python:3.11")
            else:
                (template_dir / "Makefile").write_text("# Original Makefile")
            return True

        mock_create.side_effect = create_template

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            pyproject = pathlib.Path("pyproject.toml")
            pyproject.write_text(
                '[project]\nname = "test"\ndependencies = []\n\n'
                '[tool.agent-starter-pack]\nname = "test"\n'
                'base_template = "adk"\nasp_version = "0.30.0"\n\n'
                "[tool.agent-starter-pack.create_params]\n"
                'deployment_target = "agent_engine"\n'
            )
            pathlib.Path("Makefile").write_text("# Original Makefile")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--deployment-target",
                    "cloud_run",
                    "--auto-approve",
                    "--cicd-runner",
                    "skip",
                    "--dry-run",
                ],
            )

            output = strip_ansi(result.output)
            assert result.exit_code == 0, f"Failed with output:\n{result.output}"
            assert "Dry run" in output
            # Verify files were NOT modified
            assert "Original Makefile" in pathlib.Path("Makefile").read_text()
            assert not pathlib.Path("Dockerfile").exists()


class TestSmartMergeFallback:
    """Test fallback behavior when smart-merge can't be used."""

    @patch(
        "agent_starter_pack.cli.commands.enhance.check_and_execute_with_saved_config"
    )
    def test_force_flag_skips_smart_merge(
        self, mock_saved_config, tmp_path: pathlib.Path
    ) -> None:
        """Test that --force bypasses smart-merge and uses standard overwrite."""
        # Prevent subprocess execution of saved config
        mock_saved_config.return_value = False

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create project with metadata (smart-merge would normally activate)
            pyproject = pathlib.Path("pyproject.toml")
            pyproject.write_text(
                '[project]\nname = "test"\ndependencies = []\n\n'
                '[tool.agent-starter-pack]\nname = "test"\n'
                'base_template = "adk"\nasp_version = "0.30.0"\n\n'
                "[tool.agent-starter-pack.create_params]\n"
                'deployment_target = "agent_engine"\n'
            )
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            with patch("agent_starter_pack.cli.commands.enhance.create") as mock_create:
                result = runner.invoke(
                    enhance,
                    [
                        ".",
                        "--force",
                        "--auto-approve",
                        "--cicd-runner",
                        "skip",
                    ],
                )

                # With --force, should fall through to create command
                mock_create.assert_called_once()

    @patch(
        "agent_starter_pack.cli.commands.enhance.check_and_execute_with_saved_config"
    )
    def test_no_metadata_falls_back_to_standard_mode(
        self, mock_saved_config, tmp_path: pathlib.Path
    ) -> None:
        """Test that enhance falls back to standard mode when no metadata exists."""
        mock_saved_config.return_value = False

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # No pyproject.toml - no metadata
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            with patch("agent_starter_pack.cli.commands.enhance.create") as mock_create:
                result = runner.invoke(
                    enhance,
                    [
                        ".",
                        "--auto-approve",
                        "--cicd-runner",
                        "skip",
                    ],
                )

                output = strip_ansi(result.output)
                assert "No saved metadata found" in output
                # Should fall through to create command
                mock_create.assert_called_once()

    def test_dry_run_without_metadata_shows_error(self, tmp_path: pathlib.Path) -> None:
        """Test that --dry-run without metadata shows an error."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--dry-run",
                    "--auto-approve",
                    "--cicd-runner",
                    "skip",
                ],
            )

            output = strip_ansi(result.output)
            assert "--dry-run requires saved project metadata" in output

    def test_dry_run_with_force_shows_error(self, tmp_path: pathlib.Path) -> None:
        """Test that --dry-run with --force shows an error."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            pyproject = pathlib.Path("pyproject.toml")
            pyproject.write_text(
                '[project]\nname = "test"\n\n'
                '[tool.agent-starter-pack]\nname = "test"\n'
                'base_template = "adk"\nasp_version = "0.30.0"\n'
            )
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--dry-run",
                    "--force",
                    "--auto-approve",
                    "--cicd-runner",
                    "skip",
                ],
            )

            output = strip_ansi(result.output)
            assert "--dry-run is not compatible with --force" in output

    @patch(
        "agent_starter_pack.cli.commands.enhance.check_and_execute_with_saved_config"
    )
    @patch("agent_starter_pack.cli.commands.enhance.run_create_command")
    def test_smart_merge_failure_falls_back(
        self, mock_run_create, mock_saved_config, tmp_path: pathlib.Path
    ) -> None:
        """Test that smart-merge failure falls back to standard mode."""
        # Make template generation fail
        mock_run_create.return_value = False
        mock_saved_config.return_value = False

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            pyproject = pathlib.Path("pyproject.toml")
            pyproject.write_text(
                '[project]\nname = "test"\ndependencies = []\n\n'
                '[tool.agent-starter-pack]\nname = "test"\n'
                'base_template = "adk"\nasp_version = "0.30.0"\n\n'
                "[tool.agent-starter-pack.create_params]\n"
                'deployment_target = "agent_engine"\n'
            )
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            with patch(
                "agent_starter_pack.cli.commands.enhance.create"
            ) as mock_create_cmd:
                result = runner.invoke(
                    enhance,
                    [
                        ".",
                        "--deployment-target",
                        "cloud_run",
                        "--auto-approve",
                        "--cicd-runner",
                        "skip",
                    ],
                )

                output = strip_ansi(result.output)
                assert "falling back" in output.lower()
                # Should fall through to create command
                mock_create_cmd.assert_called_once()

    @patch("agent_starter_pack.cli.commands.enhance.run_create_command")
    def test_smart_merge_no_changes_needed(
        self, mock_create, tmp_path: pathlib.Path
    ) -> None:
        """Test that smart-merge reports when no changes are needed."""

        def create_template(args, output_dir, project_name, version=None):
            del version, args
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            (template_dir / "Makefile").write_text("# Same Makefile")
            return True

        mock_create.side_effect = create_template

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            pyproject = pathlib.Path("pyproject.toml")
            pyproject.write_text(
                '[project]\nname = "test"\ndependencies = []\n\n'
                '[tool.agent-starter-pack]\nname = "test"\n'
                'base_template = "adk"\nasp_version = "0.30.0"\n\n'
                "[tool.agent-starter-pack.create_params]\n"
                'deployment_target = "agent_engine"\n'
            )
            pathlib.Path("Makefile").write_text("# Same Makefile")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--cicd-runner",
                    "skip",
                ],
            )

            output = strip_ansi(result.output)
            assert result.exit_code == 0, f"Failed with output:\n{result.output}"
            assert "No file changes needed" in output or "No changes" in output
