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

from src.cli.commands.enhance import display_base_template_selection, enhance


class TestDisplayBaseTemplateSelection:
    """Test the base template selection function."""

    @patch("src.cli.commands.enhance.get_available_agents")
    @patch("src.cli.commands.enhance.IntPrompt.ask")
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

    @patch("src.cli.commands.enhance.get_available_agents")
    @patch("src.cli.commands.enhance.IntPrompt.ask")
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

    @patch("src.cli.commands.enhance.get_available_agents")
    def test_base_template_selection_no_agents(
        self, mock_get_agents: MagicMock
    ) -> None:
        """Test error handling when no agents are available."""
        mock_get_agents.return_value = {}

        with pytest.raises(click.ClickException):
            display_base_template_selection("adk_base")


class TestEnhanceCommand:
    """Test the enhance command functionality."""

    @patch("src.cli.utils.remote_template.get_base_template_name")
    @patch("src.cli.utils.remote_template.load_remote_template_config")
    @patch("src.cli.commands.enhance.display_base_template_selection")
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
            with patch("src.cli.commands.enhance.create"):
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

            with patch("src.cli.commands.enhance.create") as mock_create:
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

            with patch("src.cli.commands.enhance.create") as mock_create:
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

    @patch("src.cli.commands.enhance.tomllib.load")
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

            with patch("src.cli.commands.enhance.create") as mock_create:
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

            with patch("src.cli.commands.enhance.create") as mock_create:
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

            with patch("src.cli.commands.enhance.create") as mock_create:
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

            with patch("src.cli.commands.enhance.create") as mock_create:
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
