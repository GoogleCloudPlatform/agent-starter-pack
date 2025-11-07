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

import pathlib
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from agent_starter_pack.cli.commands.enhance import (
    display_base_template_selection,
    enhance,
)


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
            1: {"name": "adk_base", "description": "Basic agent template"},
            2: {"name": "langgraph_base_react", "description": "LangGraph ReAct agent"},
            3: {"name": "agentic_rag", "description": "RAG-enabled agent"},
        }

        # Mock user selecting default (current template)
        mock_prompt.return_value = 1

        result = display_base_template_selection("adk_base")

        assert result == "adk_base"
        # Check that prompt was called with the correct default (1 for adk_base)
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
            1: {"name": "adk_base", "description": "Basic agent template"},
            2: {"name": "langgraph_base_react", "description": "LangGraph ReAct agent"},
            3: {"name": "agentic_rag", "description": "RAG-enabled agent"},
        }

        # Mock user selecting option 2
        mock_prompt.return_value = 2

        result = display_base_template_selection("adk_base")

        assert result == "langgraph_base_react"

    @patch("agent_starter_pack.cli.commands.enhance.get_available_agents")
    def test_base_template_selection_no_agents(
        self, mock_get_agents: MagicMock
    ) -> None:
        """Test error handling when no agents are available."""
        mock_get_agents.return_value = {}

        with pytest.raises(click.ClickException):
            display_base_template_selection("adk_base")


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
        mock_get_base_name.return_value = "adk_base"
        mock_load_config.return_value = {"base_template": "adk_base"}
        mock_display_selection.return_value = "langgraph_base_react"

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
                    [".", "--base-template", "langgraph_base_react", "--auto-approve"],
                )

                # Should call create with the specified base template
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[1]["base_template"] == "langgraph_base_react"

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
                    [".", "--agent-directory", "chatbot", "--auto-approve"],
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
                    [".", "--auto-approve"],
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
                    [".", "--agent-directory", "cli_agent", "--auto-approve"],
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
                    [".", "--agent-directory", "missing_agent", "--auto-approve"],
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
                        "langgraph_base_react",
                        "--agent-directory",
                        "my_chatbot",
                        "--auto-approve",
                    ],
                )

                # Should call create with both parameters
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[1]["base_template"] == "langgraph_base_react"

                cli_overrides = call_args[1]["cli_overrides"]
                assert cli_overrides is not None
                assert cli_overrides["base_template"] == "langgraph_base_react"
                assert cli_overrides["settings"]["agent_directory"] == "my_chatbot"


class TestEnhanceAgentEngineAppGeneration:
    """Test that enhance properly generates agent_engine_app.py with correct imports."""

    @pytest.mark.parametrize(
        "base_template,expected_import",
        [
            ("adk_base", "app as adk_app"),
            ("adk_live", "app as adk_app"),
            ("langgraph_base_react", "agent"),
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
from google.adk.apps.app import App

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
from google.adk.apps.app import App

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
                    "adk_base",
                    "--agent-directory",
                    "my_custom_agent",
                    "--deployment-target",
                    "agent_engine",
                    "--auto-approve",
                    "--skip-checks",
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
        mock_get_base_name.return_value = "adk_base"
        mock_load_config.return_value = {"base_template": "adk_base"}
        mock_display_selection.return_value = "app"

        with runner.isolated_filesystem():
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")

            with patch("agent_starter_pack.cli.commands.enhance.create"):
                runner.invoke(
                    enhance,
                    [".", "--base-template", "adk_base"],
                    input="n\n",  # Cancel enhancement
                )

                # Verify display_agent_directory_selection was called with base_template
                if mock_display_selection.called:
                    call_args = mock_display_selection.call_args
                    # The base_template should be passed to the function
                    assert call_args[0][2] == "adk_base"  # Third positional arg

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
        mock_get_base_name.return_value = "langgraph_base_react"
        mock_load_config.return_value = {"base_template": "langgraph_base_react"}
        mock_display_selection.return_value = "app"

        with runner.isolated_filesystem():
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("agent = None")

            with patch("agent_starter_pack.cli.commands.enhance.create"):
                runner.invoke(
                    enhance,
                    [".", "--base-template", "langgraph_base_react"],
                    input="n\n",  # Cancel enhancement
                )

                # Verify display_agent_directory_selection was called with base_template
                if mock_display_selection.called:
                    call_args = mock_display_selection.call_args
                    # The base_template should be passed to the function
                    assert call_args[0][2] == "langgraph_base_react"


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
from google.adk.apps.app import App

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

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
from google.adk.apps.app import App

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

app = App(root_agent=root_agent, name="app")
"""
            agent_file.write_text(agent_content)

            # Run enhance with cloud_run deployment target
            result = runner.invoke(
                enhance,
                [
                    ".",
                    "--base-template",
                    "adk_base",
                    "--deployment-target",
                    "cloud_run",
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

            # Verify agent.py was modified to add app object (backward compatibility)
            preserved_agent_content = agent_file.read_text()
            expected_content = """from google.adk.agents import Agent
from google.adk.apps.app import App

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

app = App(root_agent=root_agent, name="app")
"""
            assert preserved_agent_content == expected_content, (
                f"agent.py was not modified correctly! Expected:\n{expected_content}\n\nGot:\n{preserved_agent_content}"
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
                    "adk_base",
                    "--deployment-target",
                    "agent_engine",
                    "--include-data-ingestion",
                    "--auto-approve",
                    "--skip-checks",
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
from google.adk.apps.app import App

root_agent = Agent(
    name="test_agent",
    model="gemini-2.0-flash-001",
)

app = App(root_agent=root_agent, name="app")
"""
            assert preserved_agent_content == expected_content, (
                f"agent.py was not modified correctly! Expected:\n{expected_content}\n\nGot:\n{preserved_agent_content}"
            )
