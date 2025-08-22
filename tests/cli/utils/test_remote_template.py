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

from src.cli.utils.remote_template import (
    RemoteTemplateSpec,
    fetch_remote_template,
    get_base_template_name,
    load_remote_template_config,
    merge_template_configs,
    parse_agent_spec,
    render_and_merge_makefiles,
)


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
        spec = parse_agent_spec("adk@data-science")
        assert spec is not None
        assert spec.repo_url == "https://github.com/google/adk-samples"
        assert spec.template_path == "python/agents/data-science"
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
            patch("src.cli.utils.remote_template.tomllib.load") as mock_toml_load,
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
                "base_template": "adk_base",
                "name": "template",
                "description": "",
                "agent_directory": "app",
                "has_explicit_config": False,
            }

    @patch("src.cli.utils.remote_template.logging")
    def test_load_remote_template_config_yaml_error(
        self, mock_logging: MagicMock
    ) -> None:
        """Test loading config with TOML parsing error - returns defaults"""
        template_dir = pathlib.Path("/mock/template")

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
                "base_template": "adk_base",
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
            patch("src.cli.utils.remote_template.tomllib.load") as mock_toml_load,
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
        assert result == "adk_base"


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
                "frontend_type": "streamlit",
                "requires_data_ingestion": False,
            }
        }
        remote_config = {
            "settings": {"requires_data_ingestion": True, "custom_setting": "value"}
        }

        result = merge_template_configs(base_config, remote_config)

        # Settings should be merged
        assert result["settings"]["deployment_targets"] == ["cloud_run"]  # From base
        assert result["settings"]["frontend_type"] == "streamlit"  # From base
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

    @patch("src.cli.utils.remote_template.subprocess.run")
    @patch("src.cli.utils.remote_template.tempfile.mkdtemp")
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
name: data-science
description: Data Science Agent
base_template: adk_base
settings:
  requires_data_ingestion: true
  deployment_targets: ["cloud_run"]
"""
                ),
            ),
        ):
            # Parse ADK samples spec
            spec = parse_agent_spec("adk@data-science")
            assert spec is not None
            assert spec.is_adk_samples is True

            # Load config would work in real scenario
            # We're testing the parsing and structure here

    def test_template_validation_scenarios(self) -> None:
        """Test various template validation scenarios"""
        test_cases = [
            # ADK samples
            ("adk@data-science", True),
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
        assert get_base_template_name(empty_config) == "adk_base"

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
        spec = parse_agent_spec("adk@data-science")
        assert spec is not None
        assert spec.repo_url == "https://github.com/google/adk-samples"
        assert spec.template_path == "python/agents/data-science"
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
        assert "lint:" in write_call

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
