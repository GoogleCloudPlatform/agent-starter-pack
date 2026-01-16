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
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from agent_starter_pack.cli.utils.remote_template import (
    RemoteTemplateSpec,
    _detect_flat_structure,
    _infer_agent_directory_for_adk,
    check_and_execute_with_version_lock,
    fetch_remote_template,
    get_base_template_name,
    load_remote_template_config,
    merge_template_configs,
    parse_agent_spec,
    parse_agent_starter_pack_version_from_lock,
    render_and_merge_makefiles,
)
from agent_starter_pack.cli.utils.template import _extract_agent_garden_labels


class TestRemoteTemplateSpec:
    def test_remote_template_spec_creation(self) -> None:
        """Test RemoteTemplateSpec dataclass creation"""
        spec = RemoteTemplateSpec(
            repo_url="https://github.com/org/repo",
            template_path="path/to/template",
            git_ref="main",
        )
        assert spec.repo_url == "https://github.com/org/repo"
        assert spec.template_path == "path/to/template"
        assert spec.git_ref == "main"
        assert spec.is_adk_samples is False

    def test_remote_template_spec_adk_samples(self) -> None:
        """Test RemoteTemplateSpec with adk_samples flag"""
        spec = RemoteTemplateSpec(
            repo_url="https://github.com/google/adk-samples",
            template_path="python/agents/test",
            git_ref="main",
            is_adk_samples=True,
        )
        assert spec.is_adk_samples is True


class TestParseAgentSpec:
    def test_parse_adk_shortcut(self) -> None:
        """Test parsing ADK shortcut format"""
        spec = parse_agent_spec("adk@academic-research")
        assert spec is not None
        assert spec.repo_url == "https://github.com/google/adk-samples"
        assert spec.template_path == "python/agents/academic-research"
        assert spec.git_ref == "main"
        assert spec.is_adk_samples is True

    def test_parse_full_url_with_path_and_ref(self) -> None:
        """Test parsing full URL with path and ref"""
        spec = parse_agent_spec("https://github.com/org/repo/path/to/template@develop")
        assert spec is not None
        assert spec.repo_url == "https://github.com/org/repo"
        assert spec.template_path == "path/to/template"
        assert spec.git_ref == "develop"
        assert spec.is_adk_samples is False

    def test_parse_full_url_without_path(self) -> None:
        """Test parsing full URL without path"""
        spec = parse_agent_spec("https://github.com/org/repo")
        assert spec is not None
        assert spec.repo_url == "https://github.com/org/repo"
        assert spec.template_path == ""
        assert spec.git_ref == "main"

    def test_parse_github_shorthand_with_path(self) -> None:
        """Test parsing GitHub shorthand with path"""
        spec = parse_agent_spec("org/repo/path/to/template@feature")
        assert spec is not None
        assert spec.repo_url == "https://github.com/org/repo"
        assert spec.template_path == "path/to/template"
        assert spec.git_ref == "feature"

    def test_parse_github_shorthand_simple(self) -> None:
        """Test parsing simple GitHub shorthand"""
        spec = parse_agent_spec("org/repo")
        assert spec is not None
        assert spec.repo_url == "https://github.com/org/repo"
        assert spec.template_path == ""
        assert spec.git_ref == "main"

    def test_parse_local_template(self) -> None:
        """Test that local template names return None"""
        spec = parse_agent_spec("local_template")
        assert spec is None

    def test_parse_invalid_format(self) -> None:
        """Test invalid format returns None"""
        spec = parse_agent_spec("invalid")
        assert spec is None

    def test_parse_edge_cases(self) -> None:
        """Test edge cases in parsing"""
        # URL with trailing slash
        spec = parse_agent_spec("https://github.com/org/repo/")
        assert spec is not None
        assert spec.template_path == ""

        # GitHub shorthand with trailing slash
        spec = parse_agent_spec("org/repo/")
        assert spec is not None
        assert spec.template_path == ""


class TestFetchRemoteTemplate:
    @patch("subprocess.run")
    @patch("tempfile.mkdtemp")
    @patch("shutil.rmtree")
    def test_fetch_remote_template_git_failure(
        self,
        mock_rmtree: MagicMock,
        mock_mkdtemp: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Test remote template fetching with git failure"""
        mock_mkdtemp.return_value = "/tmp/test_dir"
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="git clone", stderr="Git error"
        )

        spec = RemoteTemplateSpec(
            repo_url="https://github.com/org/repo",
            template_path="",
            git_ref="main",
        )

        with pytest.raises(RuntimeError, match="Git clone failed"):
            fetch_remote_template(spec)

        mock_rmtree.assert_called_once_with(
            pathlib.Path("/tmp/test_dir"), ignore_errors=True
        )

    @patch("subprocess.run")
    @patch("tempfile.mkdtemp")
    @patch("pathlib.Path.exists")
    @patch("shutil.rmtree")
    def test_fetch_remote_template_path_not_found(
        self,
        mock_rmtree: MagicMock,
        mock_exists: MagicMock,
        mock_mkdtemp: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Test remote template fetching with template path not found"""
        mock_mkdtemp.return_value = "/tmp/test_dir"
        mock_exists.return_value = False
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        spec = RemoteTemplateSpec(
            repo_url="https://github.com/org/repo",
            template_path="nonexistent/path",
            git_ref="main",
        )

        with pytest.raises(
            RuntimeError,
            match="An unexpected error occurred after fetching remote template: Template path not found in the repository: nonexistent/path",
        ):
            fetch_remote_template(spec)

        mock_rmtree.assert_called_once()


class TestLoadRemoteTemplateConfig:
    def test_load_remote_template_config_primary_location(self) -> None:
        """Test loading config from pyproject.toml"""
        config_content = b"""
[tool.agent-starter-pack]
name = "test-template"
description = "Test template"

[tool.agent-starter-pack.settings]
requires_data_ingestion = false
"""
        template_dir = pathlib.Path("/mock/template")

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=config_content)),
            patch(
                "agent_starter_pack.cli.utils.remote_template.tomllib.load"
            ) as mock_toml_load,
        ):
            mock_toml_load.return_value = {
                "tool": {
                    "agent-starter-pack": {
                        "name": "test-template",
                        "description": "Test template",
                        "settings": {"requires_data_ingestion": False},
                    }
                }
            }
            result = load_remote_template_config(template_dir)

            assert result["name"] == "test-template"
            assert result["description"] == "Test template"
            assert result["settings"]["requires_data_ingestion"] is False

    def test_load_remote_template_config_no_file(self) -> None:
        """Test loading config when no config file exists - returns defaults"""
        template_dir = pathlib.Path("/mock/template")

        with patch("pathlib.Path.exists", return_value=False):
            result = load_remote_template_config(template_dir)

            # Should return defaults when no pyproject.toml exists
            assert result == {
                "base_template": "adk",
                "name": "template",
                "description": "",
                "agent_directory": "app",
                "has_explicit_config": False,
            }

    @patch("agent_starter_pack.cli.utils.remote_template._detect_flat_structure")
    @patch("agent_starter_pack.cli.utils.remote_template.logging")
    def test_load_remote_template_config_yaml_error(
        self, mock_logging: MagicMock, mock_detect_flat: MagicMock
    ) -> None:
        """Test loading config with TOML parsing error - returns defaults"""
        template_dir = pathlib.Path("/mock/template")
        mock_detect_flat.return_value = False  # Don't trigger flat structure detection

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "builtins.open",
                mock_open(read_data="invalid: yaml: content:"),
            ),
        ):
            result = load_remote_template_config(template_dir)

            # Should return defaults when pyproject.toml parsing fails
            assert result == {
                "base_template": "adk",
                "name": "template",
                "description": "",
                "agent_directory": "app",
                "has_explicit_config": False,
            }
            mock_logging.error.assert_called_once()

    def test_load_remote_template_config_with_cli_overrides(self) -> None:
        """Test loading config with CLI overrides taking precedence"""
        template_dir = pathlib.Path("/mock/template")
        cli_overrides = {
            "name": "CLI Override Name",
            "base_template": "custom_base",
            "settings": {"custom_setting": True},
        }

        config_content = b"""
[tool.agent-starter-pack]
name = "TOML Name"
description = "TOML Description"
base_template = "toml_base"

[tool.agent-starter-pack.settings]
requires_data_ingestion = true
"""

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=config_content)),
            patch(
                "agent_starter_pack.cli.utils.remote_template.tomllib.load"
            ) as mock_toml_load,
        ):
            mock_toml_load.return_value = {
                "tool": {
                    "agent-starter-pack": {
                        "name": "TOML Name",
                        "description": "TOML Description",
                        "base_template": "toml_base",
                        "settings": {"requires_data_ingestion": True},
                    }
                }
            }

            result = load_remote_template_config(
                template_dir, cli_overrides=cli_overrides
            )

            # CLI overrides should take precedence
            assert result["name"] == "CLI Override Name"  # CLI override
            assert result["base_template"] == "custom_base"  # CLI override
            assert result["description"] == "TOML Description"  # From TOML
            assert result["settings"]["custom_setting"] is True  # CLI override
            assert result["settings"]["requires_data_ingestion"] is True  # From TOML


class TestGetBaseTemplateName:
    def test_get_base_template_name_specified(self) -> None:
        """Test getting base template name when specified"""
        config: dict[str, Any] = {"base_template": "custom_base"}
        result = get_base_template_name(config)
        assert result == "custom_base"

    def test_get_base_template_name_default(self) -> None:
        """Test getting default base template name"""
        config: dict[str, Any] = {}
        result = get_base_template_name(config)
        assert result == "adk"


class TestMergeTemplateConfigs:
    def test_merge_template_configs_simple(self) -> None:
        """Test simple config merging"""
        base_config = {"name": "base", "description": "Base template", "version": "1.0"}
        remote_config = {"name": "remote", "description": "Remote template"}

        result = merge_template_configs(base_config, remote_config)

        assert result["name"] == "remote"  # Remote overrides
        assert result["description"] == "Remote template"  # Remote overrides
        assert result["version"] == "1.0"  # Base preserved

    def test_merge_template_configs_settings(self) -> None:
        """Test merging with nested settings"""
        base_config = {
            "settings": {
                "deployment_targets": ["cloud_run"],
                "frontend_type": "None",
                "requires_data_ingestion": False,
            }
        }
        remote_config = {
            "settings": {"requires_data_ingestion": True, "custom_setting": "value"}
        }

        result = merge_template_configs(base_config, remote_config)

        # Settings should be merged
        assert result["settings"]["deployment_targets"] == ["cloud_run"]  # From base
        assert result["settings"]["frontend_type"] == "None"  # From base
        assert result["settings"]["requires_data_ingestion"] is True  # Remote overrides
        assert result["settings"]["custom_setting"] == "value"  # From remote

    def test_merge_template_configs_no_mutation(self) -> None:
        """Test that original configs are not mutated"""
        base_config = {"name": "base", "settings": {"key": "value"}}
        remote_config = {"name": "remote", "settings": {"key": "new_value"}}

        original_base = base_config.copy()
        original_remote = remote_config.copy()

        merge_template_configs(base_config, remote_config)

        # Original configs should be unchanged
        assert base_config == original_base
        assert remote_config == original_remote


class TestRemoteTemplateIntegration:
    """Integration tests for remote template functionality"""

    @patch("agent_starter_pack.cli.utils.remote_template.subprocess.run")
    @patch("agent_starter_pack.cli.utils.remote_template.tempfile.mkdtemp")
    def test_end_to_end_adk_samples(
        self, mock_mkdtemp: MagicMock, mock_subprocess: MagicMock
    ) -> None:
        """Test end-to-end ADK samples workflow"""
        # Setup mocks
        mock_mkdtemp.return_value = "/tmp/test"
        mock_subprocess.return_value = MagicMock(returncode=0)

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "builtins.open",
                mock_open(
                    read_data="""
name: academic-research
description: Academic Research Agent
base_template: adk
settings:
  requires_data_ingestion: true
  deployment_targets: ["cloud_run"]
"""
                ),
            ),
        ):
            # Parse ADK samples spec
            spec = parse_agent_spec("adk@academic-research")
            assert spec is not None
            assert spec.is_adk_samples is True

            # Load config would work in real scenario
            # We're testing the parsing and structure here

    def test_template_validation_scenarios(self) -> None:
        """Test various template validation scenarios"""
        test_cases = [
            # ADK samples
            ("adk@academic-research", True),
            ("adk@custom-agent", True),
            # GitHub URLs
            ("https://github.com/org/repo", True),
            ("https://github.com/org/repo/path@branch", True),
            # GitHub shorthand
            ("org/repo", True),
            ("org/repo/path@tag", True),
            # Local templates (should not parse as remote)
            ("local_agent", False),
            ("simple_name", False),
            # Invalid formats
            ("invalid-url", False),
            ("", False),
        ]

        for agent_spec, should_be_remote in test_cases:
            spec = parse_agent_spec(agent_spec)
            if should_be_remote:
                assert spec is not None, (
                    f"Expected {agent_spec} to be parsed as remote template"
                )
            else:
                assert spec is None, (
                    f"Expected {agent_spec} to be parsed as local template"
                )

    def test_error_handling_edge_cases(self) -> None:
        """Test error handling for edge cases"""
        # Test with None input
        assert parse_agent_spec("") is None

        # Test with malformed URLs
        assert parse_agent_spec("http://") is None
        assert parse_agent_spec("://github.com/org/repo") is None

        # Test config loading with empty config
        empty_config: dict[str, Any] = {}
        assert get_base_template_name(empty_config) == "adk"

        # Test merge with empty configs
        result = merge_template_configs({}, {})
        assert result == {}


class TestParseAgentSpecWithGitSuffix:
    """Tests for parsing agent specs that may or may not include the .git suffix."""

    def test_parse_full_url_with_git_suffix(self) -> None:
        """Test parsing a full URL that already includes the .git suffix."""
        spec = parse_agent_spec("https://github.com/org/repo.git")
        assert spec is not None
        assert spec.repo_url == "https://github.com/org/repo.git"
        assert spec.template_path == ""
        assert spec.git_ref == "main"

    def test_parse_full_url_with_path_and_git_suffix(self) -> None:
        """Test parsing a full URL with a path, where the repo has a .git suffix."""
        spec = parse_agent_spec("https://github.com/org/repo.git/path/to/template")
        assert spec is not None
        assert spec.repo_url == "https://github.com/org/repo.git"
        assert spec.template_path == "path/to/template"
        assert spec.git_ref == "main"

    def test_parse_full_url_with_path_ref_and_git_suffix(self) -> None:
        """Test parsing a full URL with path, ref, and .git suffix."""
        spec = parse_agent_spec(
            "https://github.com/org/repo.git/path/to/template@develop"
        )
        assert spec is not None
        assert spec.repo_url == "https://github.com/org/repo.git"
        assert spec.template_path == "path/to/template"
        assert spec.git_ref == "develop"

    def test_parse_adk_shortcut_not_affected(self) -> None:
        """Ensure the adk@ shortcut remains unaffected."""
        spec = parse_agent_spec("adk@academic-research")
        assert spec is not None
        assert spec.repo_url == "https://github.com/google/adk-samples"
        assert spec.template_path == "python/agents/academic-research"
        assert spec.git_ref == "main"
        assert spec.is_adk_samples is True

    def test_parse_github_shorthand_not_affected(self) -> None:
        """Ensure GitHub shorthand parsing remains unaffected."""
        spec = parse_agent_spec("org/repo")
        assert spec is not None
        assert spec.repo_url == "https://github.com/org/repo"
        assert spec.template_path == ""
        assert spec.git_ref == "main"


class TestRenderAndMergeMakefiles:
    """Tests for the render_and_merge_makefiles function."""

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_and_merge_with_missing_commands(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that missing commands are merged from base to remote."""
        base_content = (
            "install:\n"
            "\t@echo 'installing {{cookiecutter.project_name}}'\n\n"
            "lint:\n"
            "\t@echo 'linting'\n"
        )
        remote_content = (
            "install:\n\t@echo 'remote-install {{cookiecutter.project_name}}'\n"
        )

        # Mock file existence
        mock_exists.return_value = True

        # Set up mock file reads for base and remote Makefiles
        mock_file.return_value.read.side_effect = [base_content, remote_content]

        # Create mock file paths
        base_path = pathlib.Path("base_template")
        remote_path = pathlib.Path("remote_template")
        dest_path = pathlib.Path("destination")

        # Mock cookiecutter config
        config = {"project_name": "test_project"}

        # Run the function
        render_and_merge_makefiles(
            base_template_path=base_path,
            final_destination=dest_path,
            cookiecutter_config=config,
            remote_template_path=remote_path,
        )

        # Check that the final Makefile was written correctly
        mock_file.assert_called_with(dest_path / "Makefile", "w", encoding="utf-8")
        handle = mock_file()
        written_content = handle.write.call_args[0][0]

        # Assert that the remote install command is present
        assert "remote-install test_project" in written_content
        # Assert that the merged lint command is present
        assert "lint:" in written_content
        assert "@echo 'linting'" in written_content
        # Assert that the base install command is NOT present
        assert "@echo 'installing test_project'" not in written_content

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_and_merge_with_no_missing_commands(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that only remote content is used when no commands are missing."""
        # Both base and remote have the same command, so no merging should happen
        base_content = "install:\n\t@echo 'installing {{cookiecutter.project_name}}'\n"
        remote_content = (
            "install:\n\t@echo 'remote-install {{cookiecutter.project_name}}'\n"
        )

        # Mock file existence
        mock_exists.return_value = True
        mock_file.return_value.read.side_effect = [base_content, remote_content]

        base_path = pathlib.Path("base_template")
        remote_path = pathlib.Path("remote_template")
        dest_path = pathlib.Path("destination")
        config = {"project_name": "test_project"}

        render_and_merge_makefiles(
            base_template_path=base_path,
            final_destination=dest_path,
            cookiecutter_config=config,
            remote_template_path=remote_path,
        )

        # Get the write calls to the destination file
        write_calls = [
            call for call in mock_file.return_value.write.call_args_list if call[0]
        ]
        assert len(write_calls) > 0

        write_call = write_calls[0][0][0]
        assert "remote-install test_project" in write_call
        # Since both have 'install' command, no base commands should be appended
        assert "Commands from Agent Starter Pack" not in write_call

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_and_merge_with_empty_remote_makefile(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test that base content is used when remote Makefile is empty."""
        base_content = "install:\n\t@echo 'installing {{cookiecutter.project_name}}'\n\nlint:\n\t@echo 'linting'\n"
        remote_content = ""

        # Mock file existence
        mock_exists.return_value = True
        mock_file.return_value.read.side_effect = [base_content, remote_content]

        base_path = pathlib.Path("base_template")
        remote_path = pathlib.Path("remote_template")
        dest_path = pathlib.Path("destination")
        config = {"project_name": "test_project"}

        render_and_merge_makefiles(
            base_template_path=base_path,
            final_destination=dest_path,
            cookiecutter_config=config,
            remote_template_path=remote_path,
        )

        # Get the write calls to the destination file
        write_calls = [
            call for call in mock_file.return_value.write.call_args_list if call[0]
        ]
        assert len(write_calls) > 0

        write_call = write_calls[0][0][0]
        assert "installing test_project" in write_call


class TestParseAgentStarterPackVersionFromLock:
    """Test parsing agent-starter-pack version from uv.lock files."""

    def test_parse_version_from_valid_lock_file(self) -> None:
        """Test parsing version from a valid uv.lock file."""
        lock_content = {
            "version": 1,
            "package": [
                {
                    "name": "agent-starter-pack",
                    "version": "0.14.1",
                    "source": {"registry": "https://pypi.org/simple"},
                },
                {
                    "name": "other-package",
                    "version": "1.0.0",
                    "source": {"registry": "https://pypi.org/simple"},
                },
            ],
        }

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "agent_starter_pack.cli.utils.remote_template.tomllib.load"
            ) as mock_toml_load,
            patch("builtins.open", mock_open()),
        ):
            mock_toml_load.return_value = lock_content

            lock_path = pathlib.Path("/mock/template/uv.lock")
            result = parse_agent_starter_pack_version_from_lock(lock_path)

            assert result == "0.14.1"

    def test_parse_version_no_agent_starter_pack(self) -> None:
        """Test parsing when agent-starter-pack is not in the lock file."""
        lock_content = {
            "version": 1,
            "package": [
                {
                    "name": "other-package",
                    "version": "1.0.0",
                    "source": {"registry": "https://pypi.org/simple"},
                },
            ],
        }

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "agent_starter_pack.cli.utils.remote_template.tomllib.load"
            ) as mock_toml_load,
            patch("builtins.open", mock_open()),
        ):
            mock_toml_load.return_value = lock_content

            lock_path = pathlib.Path("/mock/template/uv.lock")
            result = parse_agent_starter_pack_version_from_lock(lock_path)

            assert result is None

    def test_parse_version_file_not_exists(self) -> None:
        """Test parsing when uv.lock file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            lock_path = pathlib.Path("/mock/template/uv.lock")
            result = parse_agent_starter_pack_version_from_lock(lock_path)

            assert result is None

    def test_parse_version_invalid_toml(self) -> None:
        """Test parsing when uv.lock file has invalid TOML."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "agent_starter_pack.cli.utils.remote_template.tomllib.load"
            ) as mock_toml_load,
            patch("builtins.open", mock_open()),
            patch(
                "agent_starter_pack.cli.utils.remote_template.logging.warning"
            ) as mock_warning,
        ):
            mock_toml_load.side_effect = Exception("Invalid TOML")

            lock_path = pathlib.Path("/mock/template/uv.lock")
            result = parse_agent_starter_pack_version_from_lock(lock_path)

            assert result is None
            mock_warning.assert_called_once()

    def test_parse_version_no_version_field(self) -> None:
        """Test parsing when agent-starter-pack package has no version field."""
        lock_content = {
            "version": 1,
            "package": [
                {
                    "name": "agent-starter-pack",
                    "source": {"registry": "https://pypi.org/simple"},
                },
            ],
        }

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "agent_starter_pack.cli.utils.remote_template.tomllib.load"
            ) as mock_toml_load,
            patch("builtins.open", mock_open()),
        ):
            mock_toml_load.return_value = lock_content

            lock_path = pathlib.Path("/mock/template/uv.lock")
            result = parse_agent_starter_pack_version_from_lock(lock_path)

            assert result is None


class TestCheckAndExecuteWithVersionLock:
    """Test version lock checking and execution functionality."""

    @patch(
        "agent_starter_pack.cli.utils.remote_template.parse_agent_starter_pack_version_from_lock"
    )
    def test_no_version_lock_found(self, mock_parse_version: MagicMock) -> None:
        """Test when no version lock is found."""
        mock_parse_version.return_value = None

        template_dir = pathlib.Path("/mock/template")
        result = check_and_execute_with_version_lock(template_dir)

        assert result is False
        mock_parse_version.assert_called_once_with(template_dir / "uv.lock")

    @patch(
        "agent_starter_pack.cli.utils.remote_template.parse_agent_starter_pack_version_from_lock"
    )
    def test_already_locked_execution(self, mock_parse_version: MagicMock) -> None:
        """Test that locked execution is skipped to prevent recursion."""
        template_dir = pathlib.Path("/mock/template")
        result = check_and_execute_with_version_lock(template_dir, locked=True)

        assert result is False
        mock_parse_version.assert_not_called()

    @patch("agent_starter_pack.cli.utils.remote_template.subprocess.run")
    @patch(
        "agent_starter_pack.cli.utils.remote_template.parse_agent_starter_pack_version_from_lock"
    )
    @patch("agent_starter_pack.cli.utils.remote_template.Console")
    def test_version_lock_uvx_not_available(
        self,
        mock_console: MagicMock,
        mock_parse_version: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Test when version lock is found but uvx is not available."""
        mock_parse_version.return_value = "0.14.1"
        mock_subprocess.side_effect = FileNotFoundError("uvx not found")

        template_dir = pathlib.Path("/mock/template")

        with pytest.raises(SystemExit, match="1"):
            check_and_execute_with_version_lock(template_dir)

        # Verify console messages
        console_instance = mock_console.return_value
        assert (
            console_instance.print.call_count >= 3
        )  # Version message, error, and install instructions

    @patch(
        "sys.argv",
        ["agent-starter-pack", "create", "test-project", "-a", "remote/template"],
    )
    @patch("agent_starter_pack.cli.utils.remote_template.subprocess.run")
    @patch(
        "agent_starter_pack.cli.utils.remote_template.parse_agent_starter_pack_version_from_lock"
    )
    @patch("agent_starter_pack.cli.utils.remote_template.Console")
    def test_version_lock_successful_execution(
        self,
        mock_console: MagicMock,
        mock_parse_version: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Test successful version lock execution."""
        mock_parse_version.return_value = "0.14.2"

        # Mock uvx availability check (first call) and execution (second call)
        mock_subprocess.side_effect = [
            MagicMock(returncode=0),  # uvx --version succeeds
            MagicMock(returncode=0),  # uvx execution succeeds
        ]

        template_dir = pathlib.Path("/mock/template")
        original_spec = "remote/template"

        result = check_and_execute_with_version_lock(template_dir, original_spec)

        assert result is True

        # Verify the correct command was executed
        expected_cmd = [
            "uvx",
            "agent-starter-pack@0.14.2",
            "create",
            "test-project",
            "-a",
            "local@/mock/template",
            "--skip-welcome",
            "--locked",
        ]
        mock_subprocess.assert_called_with(expected_cmd, check=True)

    @patch(
        "sys.argv",
        ["agent-starter-pack", "create", "test-project", "-a", "remote/template"],
    )
    @patch("agent_starter_pack.cli.utils.remote_template.subprocess.run")
    @patch(
        "agent_starter_pack.cli.utils.remote_template.parse_agent_starter_pack_version_from_lock"
    )
    @patch("agent_starter_pack.cli.utils.remote_template.Console")
    def test_version_lock_execution_failure(
        self,
        mock_console: MagicMock,
        mock_parse_version: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Test version lock execution failure with graceful fallback."""
        mock_parse_version.return_value = "0.14.1"

        # Mock uvx availability check succeeds but execution fails
        mock_subprocess.side_effect = [
            MagicMock(returncode=0),  # uvx --version succeeds
            subprocess.CalledProcessError(
                1, "uvx", stderr="Execution failed"
            ),  # uvx execution fails
        ]

        template_dir = pathlib.Path("/mock/template")
        original_spec = "remote/template"

        result = check_and_execute_with_version_lock(template_dir, original_spec)

        assert result is False

        # Verify error and warning messages were printed
        console_instance = mock_console.return_value
        print_calls = [call[0][0] for call in console_instance.print.call_args_list]
        assert any(
            "Failed to execute with locked version" in call for call in print_calls
        )
        assert any("Continuing with current version" in call for call in print_calls)

    @patch("sys.argv", ["agent-starter-pack", "create", "test-project"])
    @patch("agent_starter_pack.cli.utils.remote_template.subprocess.run")
    @patch(
        "agent_starter_pack.cli.utils.remote_template.parse_agent_starter_pack_version_from_lock"
    )
    @patch("agent_starter_pack.cli.utils.remote_template.Console")
    def test_version_lock_no_original_spec(
        self,
        mock_console: MagicMock,
        mock_parse_version: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Test version lock execution without original agent spec replacement."""
        mock_parse_version.return_value = "0.14.2"

        # Mock uvx availability and execution
        mock_subprocess.side_effect = [
            MagicMock(returncode=0),  # uvx --version succeeds
            MagicMock(returncode=0),  # uvx execution succeeds
        ]

        template_dir = pathlib.Path("/mock/template")

        result = check_and_execute_with_version_lock(template_dir)

        assert result is True

        # Verify the command was executed without agent spec replacement
        expected_cmd = [
            "uvx",
            "agent-starter-pack@0.14.2",
            "create",
            "test-project",
            "--skip-welcome",
            "--locked",
        ]
        mock_subprocess.assert_called_with(expected_cmd, check=True)

    @patch(
        "sys.argv",
        ["agent-starter-pack", "create", "test-project", "-a", "remote/template"],
    )
    @patch("agent_starter_pack.cli.utils.remote_template.subprocess.run")
    @patch(
        "agent_starter_pack.cli.utils.remote_template.parse_agent_starter_pack_version_from_lock"
    )
    @patch("agent_starter_pack.cli.utils.remote_template.Console")
    def test_version_lock_old_version_no_flags(
        self,
        mock_console: MagicMock,
        mock_parse_version: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Test version lock execution with older ASP version that doesn't support --locked flag."""
        mock_parse_version.return_value = "0.14.0"  # Older version

        # Mock uvx availability and execution
        mock_subprocess.side_effect = [
            MagicMock(returncode=0),  # uvx --version succeeds
            MagicMock(returncode=0),  # uvx execution succeeds
        ]

        template_dir = pathlib.Path("/mock/template")
        original_spec = "remote/template"

        result = check_and_execute_with_version_lock(template_dir, original_spec)

        assert result is True

        # Verify the command was executed without --skip-welcome and --locked flags
        expected_cmd = [
            "uvx",
            "agent-starter-pack@0.14.0",
            "create",
            "test-project",
            "-a",
            "local@/mock/template",
        ]
        mock_subprocess.assert_called_with(expected_cmd, check=True)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_and_merge_handles_complex_command_blocks(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test rendering and merging with multi-line, complex command blocks."""
        base_content = (
            "setup-dev-env:\n"
            "\tPROJECT_ID=$(gcloud config get-value project) && \\\n"
            "\t(cd deployment/terraform/dev && terraform init && terraform apply --auto-approve)\n\n"
            "test:\n"
            "\t@echo 'running tests for {{cookiecutter.project_name}}'\n"
        )
        remote_content = (
            "test:\n\t@echo 'running remote tests for {{cookiecutter.project_name}}'\n"
        )

        # Mock file existence
        mock_exists.return_value = True
        mock_file.return_value.read.side_effect = [base_content, remote_content]

        base_path = pathlib.Path("base_template")
        remote_path = pathlib.Path("remote_template")
        dest_path = pathlib.Path("destination")
        config = {"project_name": "test_project"}

        render_and_merge_makefiles(
            base_template_path=base_path,
            final_destination=dest_path,
            cookiecutter_config=config,
            remote_template_path=remote_path,
        )

        # Get the write calls to the destination file
        write_calls = [
            call for call in mock_file.return_value.write.call_args_list if call[0]
        ]
        assert len(write_calls) > 0

        write_call = write_calls[0][0][0]
        assert "running remote tests for test_project" in write_call
        assert "Commands from Agent Starter Pack" in write_call
        assert "setup-dev-env:" in write_call

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_and_merge_with_missing_files(
        self, mock_file: MagicMock, mock_exists: MagicMock
    ) -> None:
        """Test handling when base or remote Makefile doesn't exist."""
        # Test case: base exists, remote doesn't
        # Mock exists to return True for base Makefile, False for remote
        mock_exists.side_effect = [
            True,
            False,
        ]  # First call (base) True, second (remote) False

        mock_file.return_value.read.return_value = (
            "install:\n\t@echo 'installing {{cookiecutter.project_name}}'\n"
        )

        base_path = pathlib.Path("base_template")
        remote_path = pathlib.Path("remote_template")
        dest_path = pathlib.Path("destination")
        config = {"project_name": "test_project"}

        render_and_merge_makefiles(
            base_template_path=base_path,
            final_destination=dest_path,
            cookiecutter_config=config,
            remote_template_path=remote_path,
        )

        # Get the write calls to the destination file
        write_calls = [
            call for call in mock_file.return_value.write.call_args_list if call[0]
        ]
        assert len(write_calls) > 0

        write_call = write_calls[0][0][0]
        assert "installing test_project" in write_call


class TestAgentGardenLabelExtraction:
    """Test the logic for extracting agent_garden labels."""

    def test_extract_from_remote_spec_adk_samples(self) -> None:
        """Test extracting labels from remote_spec when is_adk_samples=True."""
        remote_spec = RemoteTemplateSpec(
            repo_url="https://github.com/google/adk-samples",
            template_path="python/agents/RAG",
            git_ref="main",
            is_adk_samples=True,
        )

        agent_sample_id, agent_sample_publisher = _extract_agent_garden_labels(
            agent_garden=True,
            remote_spec=remote_spec,
            remote_template_path=None,
        )

        assert agent_sample_id == "RAG"
        assert agent_sample_publisher == "google"

    def test_extract_from_pyproject_toml(self) -> None:
        """Test extracting labels from pyproject.toml fallback."""
        import sys

        remote_template_path = pathlib.Path("/test/template")

        pyproject_content = b"""
[project]
name = "rag"
version = "0.1.0"
"""

        # Mock the toml data that would be loaded
        mock_toml_data = {"project": {"name": "rag", "version": "0.1.0"}}

        # Determine which toml library to mock based on Python version
        if sys.version_info >= (3, 11):
            toml_module = "tomllib"
        else:
            toml_module = "tomli"

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=pyproject_content)),
            patch(f"{toml_module}.load") as mock_toml_load,
        ):
            mock_toml_load.return_value = mock_toml_data

            agent_sample_id, agent_sample_publisher = _extract_agent_garden_labels(
                agent_garden=True,
                remote_spec=None,
                remote_template_path=remote_template_path,
            )

        assert agent_sample_id == "rag"
        assert agent_sample_publisher == "google"

    def test_no_labels_when_agent_garden_false(self) -> None:
        """Test that labels are not set when agent_garden=False."""
        remote_spec = RemoteTemplateSpec(
            repo_url="https://github.com/google/adk-samples",
            template_path="python/agents/RAG",
            git_ref="main",
            is_adk_samples=True,
        )

        agent_sample_id, agent_sample_publisher = _extract_agent_garden_labels(
            agent_garden=False,
            remote_spec=remote_spec,
            remote_template_path=None,
        )

        # Labels should remain None when agent_garden=False
        assert agent_sample_id is None
        assert agent_sample_publisher is None

    def test_no_labels_when_no_pyproject_toml(self) -> None:
        """Test that labels remain empty when pyproject.toml doesn't exist."""
        remote_template_path = pathlib.Path("/test/template")

        with patch("pathlib.Path.exists", return_value=False):
            agent_sample_id, agent_sample_publisher = _extract_agent_garden_labels(
                agent_garden=True,
                remote_spec=None,
                remote_template_path=remote_template_path,
            )

        assert agent_sample_id is None
        assert agent_sample_publisher is None


class TestDetectFlatStructure:
    """Tests for the _detect_flat_structure function."""

    def test_flat_structure_agent_py_in_root_no_subdirs(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test detection of flat structure with agent.py in root and no agent subdirectory."""
        # Create flat structure
        (tmp_path / "agent.py").write_text("root_agent = None")
        (tmp_path / "__init__.py").write_text("")

        result = _detect_flat_structure(tmp_path)
        assert result is True

    def test_nested_structure_agent_py_in_app_subdir(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that nested structure (agent.py in app/) is not detected as flat."""
        # Create nested structure
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "agent.py").write_text("root_agent = None")
        (app_dir / "__init__.py").write_text("")

        result = _detect_flat_structure(tmp_path)
        assert result is False

    def test_nested_structure_agent_py_in_folder_name_subdir(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that nested structure with folder-named subdir is not detected as flat."""
        # Create a template dir named "bigquery" with agent code in bigquery/ subdir
        template_dir = tmp_path / "bigquery"
        template_dir.mkdir()
        agent_subdir = template_dir / "bigquery"
        agent_subdir.mkdir()
        (agent_subdir / "agent.py").write_text("root_agent = None")

        result = _detect_flat_structure(template_dir)
        assert result is False

    def test_no_agent_py_at_all(self, tmp_path: pathlib.Path) -> None:
        """Test that structure without agent.py is not detected as flat."""
        (tmp_path / "README.md").write_text("# Test")

        result = _detect_flat_structure(tmp_path)
        assert result is False

    def test_agent_py_in_both_root_and_subdir_prefers_nested(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that when agent.py exists in both root and subdir, nested is preferred."""
        # Create agent.py in root
        (tmp_path / "agent.py").write_text("root_agent = None")
        # Create agent.py in app/ subdir
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "agent.py").write_text("root_agent = None")

        result = _detect_flat_structure(tmp_path)
        assert result is False  # Prefer nested structure

    def test_flat_structure_with_hyphenated_folder_name(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test flat structure detection with hyphenated folder name."""
        template_dir = tmp_path / "my-agent"
        template_dir.mkdir()
        (template_dir / "agent.py").write_text("root_agent = None")

        result = _detect_flat_structure(template_dir)
        assert result is True


class TestInferAgentDirectoryForAdkWithFlatStructure:
    """Tests for _infer_agent_directory_for_adk with flat structure detection."""

    def test_flat_adk_sample_returns_flat_config(self, tmp_path: pathlib.Path) -> None:
        """Test that flat ADK sample returns config with source_agent_directory='.'."""
        # Create flat structure
        (tmp_path / "agent.py").write_text("root_agent = None")

        result = _infer_agent_directory_for_adk(tmp_path, is_adk_sample=True)

        assert result.get("is_flat_structure") is True
        assert result.get("settings", {}).get("source_agent_directory") == "."
        assert result.get("settings", {}).get(
            "agent_directory"
        ) == tmp_path.name.replace("-", "_")
        assert result.get("has_explicit_config") is False

    def test_nested_adk_sample_returns_standard_config(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that nested ADK sample returns standard config without flat flags."""
        # Create nested structure
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "agent.py").write_text("root_agent = None")

        result = _infer_agent_directory_for_adk(tmp_path, is_adk_sample=True)

        assert (
            result.get("is_flat_structure") is None
            or result.get("is_flat_structure") is False
        )
        assert result.get("settings", {}).get("source_agent_directory") is None
        assert result.get("settings", {}).get(
            "agent_directory"
        ) == tmp_path.name.replace("-", "_")

    def test_non_adk_sample_returns_empty_config(self, tmp_path: pathlib.Path) -> None:
        """Test that non-ADK sample returns empty config."""
        (tmp_path / "agent.py").write_text("root_agent = None")

        result = _infer_agent_directory_for_adk(tmp_path, is_adk_sample=False)

        assert result == {}

    def test_flat_adk_sample_with_hyphenated_name(self, tmp_path: pathlib.Path) -> None:
        """Test that hyphenated folder name is converted to underscores."""
        template_dir = tmp_path / "my-cool-agent"
        template_dir.mkdir()
        (template_dir / "agent.py").write_text("root_agent = None")

        result = _infer_agent_directory_for_adk(template_dir, is_adk_sample=True)

        assert result.get("settings", {}).get("agent_directory") == "my_cool_agent"


class TestLoadRemoteTemplateConfigWithFlatStructure:
    """Tests for load_remote_template_config with flat structure detection."""

    def test_non_adk_template_with_flat_structure_auto_detects(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that non-ADK template with flat structure is auto-detected."""
        # Create flat structure
        (tmp_path / "agent.py").write_text("root_agent = None")

        result = load_remote_template_config(tmp_path, is_adk_sample=False)

        assert result.get("is_flat_structure") is True
        assert result.get("settings", {}).get("source_agent_directory") == "."
        # Target agent directory should be derived from folder name
        assert result.get("settings", {}).get(
            "agent_directory"
        ) == tmp_path.name.replace("-", "_")

    def test_non_adk_template_with_nested_structure_no_flat_flags(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that non-ADK template with nested structure has no flat flags."""
        # Create nested structure
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "agent.py").write_text("root_agent = None")

        result = load_remote_template_config(tmp_path, is_adk_sample=False)

        assert (
            result.get("is_flat_structure") is None
            or result.get("is_flat_structure") is False
        )
        assert result.get("settings", {}).get("source_agent_directory") is None

    def test_template_with_explicit_config_no_flat_detection(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that template with explicit config does not trigger flat detection."""
        # Create flat structure
        (tmp_path / "agent.py").write_text("root_agent = None")
        # Create pyproject.toml with explicit config
        pyproject_content = b"""
[tool.agent-starter-pack]
name = "my-template"
base_template = "adk"

[tool.agent-starter-pack.settings]
agent_directory = "custom_agent"
"""
        (tmp_path / "pyproject.toml").write_bytes(pyproject_content)

        result = load_remote_template_config(tmp_path, is_adk_sample=False)

        # Explicit config should be used, no flat detection
        assert result.get("has_explicit_config") is True
        assert result.get("settings", {}).get("agent_directory") == "custom_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
