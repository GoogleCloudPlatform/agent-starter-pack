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
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from agent_starter_pack.cli.utils.template import (
    add_base_template_dependencies_interactively,
)


class TestAddBaseTemplateDependencies:
    """Tests for interactive base template dependency addition."""

    @patch("agent_starter_pack.cli.utils.template.subprocess.run")
    @patch("agent_starter_pack.cli.utils.template.Console")
    def test_auto_approve_adds_dependencies(
        self, _mock_console: MagicMock, mock_subprocess: MagicMock
    ) -> None:
        """Test that auto-approve mode automatically adds dependencies."""
        mock_subprocess.return_value = MagicMock(
            returncode=0, stderr="Resolved 111 packages in 1.2s"
        )

        project_path = pathlib.Path("/test/project")
        base_deps = ["google-adk>=1.16.0,<2.0.0", "a2a-sdk~=0.3.9"]

        result = add_base_template_dependencies_interactively(
            project_path, base_deps, "adk_a2a", auto_approve=True
        )

        assert result is True
        mock_subprocess.assert_called_once_with(
            ["uv", "add", "google-adk>=1.16.0,<2.0.0", "a2a-sdk~=0.3.9"],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("agent_starter_pack.cli.utils.template.subprocess.run")
    @patch("agent_starter_pack.cli.utils.template.Console")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_confirm_yes(
        self,
        mock_confirm: MagicMock,
        _mock_console: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Test interactive mode when user confirms."""
        mock_confirm.return_value = True
        mock_subprocess.return_value = MagicMock(
            returncode=0, stderr="Resolved 111 packages in 1.2s"
        )

        project_path = pathlib.Path("/test/project")
        base_deps = ["a2a-sdk~=0.3.9"]

        result = add_base_template_dependencies_interactively(
            project_path, base_deps, "adk_a2a", auto_approve=False
        )

        assert result is True
        mock_confirm.assert_called_once()
        mock_subprocess.assert_called_once()

    @patch("agent_starter_pack.cli.utils.template.Console")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_confirm_no(
        self, mock_confirm: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test interactive mode when user declines."""
        mock_confirm.return_value = False

        project_path = pathlib.Path("/test/project")
        base_deps = ["a2a-sdk~=0.3.9"]

        result = add_base_template_dependencies_interactively(
            project_path, base_deps, "adk_a2a", auto_approve=False
        )

        assert result is False
        # Verify console shows instructions
        console_instance = mock_console.return_value
        assert console_instance.print.call_count >= 3  # Warning + instructions

    @patch("agent_starter_pack.cli.utils.template.subprocess.run")
    @patch("agent_starter_pack.cli.utils.template.Console")
    def test_subprocess_failure(
        self, mock_console: MagicMock, mock_subprocess: MagicMock
    ) -> None:
        """Test handling of subprocess failure."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "uv add", stderr="Network error"
        )

        project_path = pathlib.Path("/test/project")
        base_deps = ["a2a-sdk~=0.3.9"]

        result = add_base_template_dependencies_interactively(
            project_path, base_deps, "adk_a2a", auto_approve=True
        )

        assert result is False
        # Verify error message shown
        console_instance = mock_console.return_value
        print_calls = [str(call) for call in console_instance.print.call_args_list]
        assert any("Failed to add dependencies" in str(call) for call in print_calls)

    @patch("agent_starter_pack.cli.utils.template.Console")
    def test_uv_not_found(self, mock_console: MagicMock) -> None:
        """Test handling when uv is not installed."""
        project_path = pathlib.Path("/test/project")
        base_deps = ["a2a-sdk~=0.3.9"]

        with patch(
            "agent_starter_pack.cli.utils.template.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError("uv not found")

            result = add_base_template_dependencies_interactively(
                project_path, base_deps, "adk_a2a", auto_approve=True
            )

        assert result is False
        # Verify helpful error message
        console_instance = mock_console.return_value
        print_calls = [str(call) for call in console_instance.print.call_args_list]
        assert any("uv command not found" in str(call) for call in print_calls)

    def test_empty_dependencies(self) -> None:
        """Test that empty dependency list returns True without doing anything."""
        project_path = pathlib.Path("/test/project")

        result = add_base_template_dependencies_interactively(
            project_path, [], "adk", auto_approve=True
        )

        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
