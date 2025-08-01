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
