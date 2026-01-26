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

"""Tests for upgrade command."""

import pathlib
import re
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from agent_starter_pack.cli.commands.upgrade import upgrade


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


class TestUpgradeErrorCases:
    """Test error handling in upgrade command."""

    def test_missing_asp_metadata(self, tmp_path: pathlib.Path) -> None:
        """Test error when pyproject.toml has no ASP metadata."""
        # Create pyproject.toml without [tool.agent-starter-pack] section
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
version = "0.1.0"
"""
        )

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path)])
        output = strip_ansi(result.output)

        assert result.exit_code == 1
        assert "No agent-starter-pack metadata found" in output
        assert "[tool.agent-starter-pack]" in output

    def test_missing_asp_version(self, tmp_path: pathlib.Path) -> None:
        """Test error when metadata exists but asp_version is missing."""
        # Create pyproject.toml with ASP metadata but no asp_version
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
base_template = "adk"
"""
        )

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path)])
        output = strip_ansi(result.output)

        assert result.exit_code == 1
        assert "No asp_version found" in output

    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_already_at_latest_version(
        self, mock_version, tmp_path: pathlib.Path
    ) -> None:
        """Test message when project is already at latest version."""
        mock_version.return_value = "0.31.0"

        # Create pyproject.toml with matching version
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
base_template = "adk"
asp_version = "0.31.0"
"""
        )

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path)])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "already at version 0.31.0" in output

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_uvx_not_available(
        self, mock_version, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test error when uvx is not installed."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = False

        # Create pyproject.toml with older version
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
base_template = "adk"
asp_version = "0.30.0"
"""
        )

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path)])
        output = strip_ansi(result.output)

        assert result.exit_code == 1
        assert "uvx" in output
        assert "required" in output.lower()


class TestUpgradeDryRun:
    """Test dry-run mode."""

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_dry_run_no_changes_applied(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that dry-run doesn't modify files."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        # Mock template creation to create minimal template structure
        def create_template(_args, output_dir, project_name, _version=None):
            del _args, _version  # Unused
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                """
[project]
name = "test-project"
dependencies = []
"""
            )
            (template_dir / "README.md").write_text("# Test")
            return True

        mock_create.side_effect = create_template

        # Create project with older version
        pyproject = tmp_path / "pyproject.toml"
        original_content = """
[project]
name = "test-project"
version = "0.1.0"
dependencies = []

[tool.agent-starter-pack]
name = "test-project"
base_template = "adk"
asp_version = "0.30.0"
"""
        pyproject.write_text(original_content)

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--dry-run"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Dry run complete" in output
        # Verify file wasn't modified
        assert pyproject.read_text() == original_content


class TestUpgradeE2E:
    """End-to-end tests for upgrade command."""

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_auto_update_unchanged_files(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that unchanged files are auto-updated."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, version=None):
            del _args  # Unused
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            if version == "0.30.0":
                # Old template
                (template_dir / "Makefile").write_text("# Old Makefile")
            else:
                # New template
                (template_dir / "Makefile").write_text("# New Makefile with updates")
            return True

        mock_create.side_effect = create_template

        # Create project with file matching old template (user didn't modify)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = []\n\n'
            '[tool.agent-starter-pack]\nname = "test"\n'
            'base_template = "adk"\nasp_version = "0.30.0"'
        )
        makefile = tmp_path / "Makefile"
        makefile.write_text("# Old Makefile")  # Same as old template

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--auto-approve"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Upgrade complete" in output
        # Verify file was updated
        assert "New Makefile with updates" in makefile.read_text()

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_preserve_user_modified_files_when_asp_unchanged(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that user-modified files are preserved when ASP didn't change them."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, _version=None):
            del _args, _version  # Unused
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            # Same content in old and new template
            (template_dir / "Makefile").write_text("# Template Makefile")
            return True

        mock_create.side_effect = create_template

        # Create project with user-modified file
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = []\n\n'
            '[tool.agent-starter-pack]\nname = "test"\n'
            'base_template = "adk"\nasp_version = "0.30.0"'
        )
        makefile = tmp_path / "Makefile"
        makefile.write_text("# My custom Makefile")  # User modified

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--auto-approve"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        # Verify user's file was preserved
        assert "My custom Makefile" in makefile.read_text()
        assert "Preserving" in output or "preserve" in output.lower()

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_detects_conflict_when_both_changed(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that conflicts are detected when both user and ASP changed a file."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, version=None):
            del _args  # Unused
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            if version == "0.30.0":
                (template_dir / "Makefile").write_text("# Old template")
            else:
                (template_dir / "Makefile").write_text("# New template")
            return True

        mock_create.side_effect = create_template

        # Create project with user-modified file (different from both templates)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = []\n\n'
            '[tool.agent-starter-pack]\nname = "test"\n'
            'base_template = "adk"\nasp_version = "0.30.0"'
        )
        makefile = tmp_path / "Makefile"
        makefile.write_text("# User modified")  # Different from both templates

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--auto-approve"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Conflict" in output
        # With auto-approve, user's version is kept
        assert "User modified" in makefile.read_text()

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_skips_agent_code(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that agent code files are never modified."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, _version=None):
            del _args, _version  # Unused
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / "pyproject.toml").write_text(
                '[project]\nname = "test"\ndependencies = []'
            )
            (template_dir / "app").mkdir()
            (template_dir / "app/agent.py").write_text("# Template agent")
            return True

        mock_create.side_effect = create_template

        # Create project with agent code
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\ndependencies = []\n\n'
            '[tool.agent-starter-pack]\nname = "test"\n'
            'base_template = "adk"\nasp_version = "0.30.0"'
        )
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        agent_file = app_dir / "agent.py"
        agent_file.write_text("# My custom agent code")

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--auto-approve"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Skipping" in output
        # Verify agent code was NOT modified
        assert "My custom agent code" in agent_file.read_text()


class TestGoProjectUpgrade:
    """Test upgrade command for Go projects."""

    def test_go_project_missing_version(self, tmp_path: pathlib.Path) -> None:
        """Test error when Go project has no version in .asp.toml."""
        # Create .asp.toml without version
        asp_toml = tmp_path / ".asp.toml"
        asp_toml.write_text(
            """
[project]
name = "test-go-project"
language = "go"
base_template = "adk_go"
"""
        )
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path)])
        output = strip_ansi(result.output)

        assert result.exit_code == 1
        assert "No asp_version found" in output
        # Should mention Go-specific config
        assert ".asp.toml" in output or "version" in output

    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_go_project_already_at_latest(
        self, mock_version, tmp_path: pathlib.Path
    ) -> None:
        """Test message when Go project is already at latest version."""
        mock_version.return_value = "0.31.0"

        # Create Go project with matching version
        asp_toml = tmp_path / ".asp.toml"
        asp_toml.write_text(
            """
[project]
name = "test-go-project"
language = "go"
base_template = "adk_go"
version = "0.31.0"
"""
        )
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path)])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "already at version 0.31.0" in output

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_go_project_dry_run(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that dry-run doesn't modify Go project files."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, version=None):
            del _args
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            v = version or "0.31.0"
            (template_dir / ".asp.toml").write_text(
                f'[project]\nname = "test"\nversion = "{v}"'
            )
            (template_dir / "go.mod").write_text("module test\n\ngo 1.21")
            # Create different Makefile content to trigger changes
            if version == "0.30.0":
                (template_dir / "Makefile").write_text("# Old Makefile")
            else:
                (template_dir / "Makefile").write_text("# New Makefile")
            return True

        mock_create.side_effect = create_template

        # Create Go project with older version
        asp_toml = tmp_path / ".asp.toml"
        original_content = """
[project]
name = "test-go-project"
language = "go"
version = "0.30.0"
"""
        asp_toml.write_text(original_content)
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")
        makefile = tmp_path / "Makefile"
        original_makefile = "# Old Makefile"
        makefile.write_text(original_makefile)

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--dry-run"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Dry run complete" in output
        # Verify files weren't modified
        assert asp_toml.read_text() == original_content
        assert makefile.read_text() == original_makefile

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_go_project_auto_update_unchanged_files(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that unchanged Go files are auto-updated."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, version=None):
            del _args
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            v = version or "0.31.0"
            (template_dir / ".asp.toml").write_text(
                f'[project]\nname = "test"\nversion = "{v}"'
            )
            (template_dir / "go.mod").write_text("module test\n\ngo 1.21")
            if version == "0.30.0":
                (template_dir / "Makefile").write_text("# Old Makefile")
            else:
                (template_dir / "Makefile").write_text("# New Makefile with updates")
            return True

        mock_create.side_effect = create_template

        # Create Go project with file matching old template
        asp_toml = tmp_path / ".asp.toml"
        asp_toml.write_text(
            '[project]\nname = "test"\nlanguage = "go"\nversion = "0.30.0"'
        )
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")
        makefile = tmp_path / "Makefile"
        makefile.write_text("# Old Makefile")  # Same as old template

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--auto-approve"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Upgrade complete" in output
        # Verify file was updated
        assert "New Makefile with updates" in makefile.read_text()

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_go_project_preserve_user_modified_files(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that user-modified Go files are preserved when ASP didn't change."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, _version=None):
            del _args, _version
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / ".asp.toml").write_text(
                '[project]\nname = "test"\nversion = "0.31.0"'
            )
            (template_dir / "go.mod").write_text("module test\n\ngo 1.21")
            # Same content in old and new template
            (template_dir / "Makefile").write_text("# Template Makefile")
            return True

        mock_create.side_effect = create_template

        # Create Go project with user-modified file
        asp_toml = tmp_path / ".asp.toml"
        asp_toml.write_text(
            '[project]\nname = "test"\nlanguage = "go"\nversion = "0.30.0"'
        )
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")
        makefile = tmp_path / "Makefile"
        makefile.write_text("# My custom Go Makefile")  # User modified

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--auto-approve"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        # Verify user's file was preserved
        assert "My custom Go Makefile" in makefile.read_text()
        assert "Preserving" in output or "preserve" in output.lower()

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_go_project_detects_conflict(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that conflicts are detected in Go projects."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, version=None):
            del _args
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            v = version or "0.31.0"
            (template_dir / ".asp.toml").write_text(
                f'[project]\nname = "test"\nversion = "{v}"'
            )
            (template_dir / "go.mod").write_text("module test\n\ngo 1.21")
            if version == "0.30.0":
                (template_dir / "Makefile").write_text("# Old template")
            else:
                (template_dir / "Makefile").write_text("# New template")
            return True

        mock_create.side_effect = create_template

        # Create Go project with user-modified file (different from both templates)
        asp_toml = tmp_path / ".asp.toml"
        asp_toml.write_text(
            '[project]\nname = "test"\nlanguage = "go"\nversion = "0.30.0"'
        )
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")
        makefile = tmp_path / "Makefile"
        makefile.write_text("# User modified Go Makefile")

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--auto-approve"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Conflict" in output
        # With auto-approve, user's version is kept
        assert "User modified Go Makefile" in makefile.read_text()

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_go_project_skips_agent_code(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that Go agent code files are never modified."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, _version=None):
            del _args, _version
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            (template_dir / ".asp.toml").write_text(
                '[project]\nname = "test"\nversion = "0.31.0"'
            )
            (template_dir / "go.mod").write_text("module test\n\ngo 1.21")
            (template_dir / "agent").mkdir()
            (template_dir / "agent/agent.go").write_text("// Template agent")
            return True

        mock_create.side_effect = create_template

        # Create Go project with agent code
        asp_toml = tmp_path / ".asp.toml"
        asp_toml.write_text(
            """
[project]
name = "test-go-project"
language = "go"
base_template = "adk_go"
version = "0.30.0"
agent_directory = "agent"
"""
        )
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()
        agent_file = agent_dir / "agent.go"
        agent_file.write_text("// My custom Go agent code")

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--auto-approve"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Skipping" in output
        # Verify Go agent code was NOT modified
        assert "My custom Go agent code" in agent_file.read_text()

    @patch("agent_starter_pack.cli.commands.upgrade._ensure_uvx_available")
    @patch("agent_starter_pack.cli.commands.upgrade._run_create_command")
    @patch("agent_starter_pack.cli.commands.upgrade.get_current_version")
    def test_go_project_updates_version_in_asp_toml(
        self, mock_version, mock_create, mock_uvx, tmp_path: pathlib.Path
    ) -> None:
        """Test that Go project version is updated in .asp.toml."""
        mock_version.return_value = "0.31.0"
        mock_uvx.return_value = True

        def create_template(_args, output_dir, project_name, version=None):
            del _args
            template_dir = output_dir / project_name
            template_dir.mkdir(parents=True)
            v = version or "0.31.0"
            (template_dir / ".asp.toml").write_text(
                f'[project]\nname = "test"\nversion = "{v}"'
            )
            (template_dir / "go.mod").write_text("module test\n\ngo 1.21")
            (template_dir / "Makefile").write_text(
                "# Template Makefile" if version == "0.30.0" else "# Updated Makefile"
            )
            return True

        mock_create.side_effect = create_template

        # Create Go project
        asp_toml = tmp_path / ".asp.toml"
        asp_toml.write_text(
            """
[project]
name = "test-go-project"
language = "go"
version = "0.30.0"
"""
        )
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")
        (tmp_path / "Makefile").write_text("# Template Makefile")

        runner = CliRunner()
        result = runner.invoke(upgrade, [str(tmp_path), "--auto-approve"])
        output = strip_ansi(result.output)

        assert result.exit_code == 0
        assert "Upgrade complete" in output

        # Verify .asp.toml was updated with new version
        updated_content = asp_toml.read_text()
        assert 'version = "0.31.0"' in updated_content
        assert "0.30.0" not in updated_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
