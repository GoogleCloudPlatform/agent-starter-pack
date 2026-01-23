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

"""Tests for shared language utilities."""

import pathlib

import pytest

from agent_starter_pack.cli.utils.language import (
    LANGUAGE_CONFIGS,
    detect_language,
    get_asp_config_for_language,
    get_language_config,
    update_asp_version,
)


class TestLanguageConfigs:
    """Tests for LANGUAGE_CONFIGS structure."""

    def test_python_config_exists(self) -> None:
        """Test that Python configuration exists and is complete."""
        assert "python" in LANGUAGE_CONFIGS
        python_config = LANGUAGE_CONFIGS["python"]
        assert python_config["detection_files"] == ["pyproject.toml"]
        assert python_config["config_file"] == "pyproject.toml"
        assert python_config["config_path"] == ["tool", "agent-starter-pack"]
        assert python_config["version_key"] == "asp_version"
        assert python_config["lock_command"] == ["uv", "lock"]
        assert python_config["strip_dependencies"] is True
        assert python_config["display_name"] == "Python"

    def test_go_config_exists(self) -> None:
        """Test that Go configuration exists and is complete."""
        assert "go" in LANGUAGE_CONFIGS
        go_config = LANGUAGE_CONFIGS["go"]
        assert go_config["detection_files"] == ["go.mod"]
        assert go_config["config_file"] == ".asp.toml"
        assert go_config["config_path"] == ["project"]
        assert go_config["version_key"] == "version"
        assert go_config["lock_command"] == ["go", "mod", "tidy"]
        assert go_config["strip_dependencies"] is False
        assert go_config["display_name"] == "Go"

    def test_all_configs_have_required_keys(self) -> None:
        """Test that all language configs have consistent structure."""
        required_keys = [
            "detection_files",
            "config_file",
            "config_path",
            "version_key",
            "project_files",
            "lock_file",
            "lock_command",
            "lock_command_name",
            "strip_dependencies",
            "display_name",
        ]
        for lang, config in LANGUAGE_CONFIGS.items():
            for key in required_keys:
                assert key in config, f"Language '{lang}' missing key '{key}'"


class TestDetectLanguage:
    """Tests for detect_language function."""

    def test_detect_python_from_pyproject(self, tmp_path: pathlib.Path) -> None:
        """Test detection of Python project from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        result = detect_language(tmp_path)
        assert result == "python"

    def test_detect_go_from_go_mod(self, tmp_path: pathlib.Path) -> None:
        """Test detection of Go project from go.mod."""
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")

        result = detect_language(tmp_path)
        assert result == "go"

    def test_detect_from_asp_toml_language_field(self, tmp_path: pathlib.Path) -> None:
        """Test detection from explicit language field in .asp.toml."""
        (tmp_path / ".asp.toml").write_text('[project]\nlanguage = "go"')
        # Even with pyproject.toml present, explicit language wins
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        result = detect_language(tmp_path)
        assert result == "go"

    def test_detect_defaults_to_python(self, tmp_path: pathlib.Path) -> None:
        """Test default to Python when no indicators found."""
        result = detect_language(tmp_path)
        assert result == "python"

    def test_go_takes_precedence_over_python(self, tmp_path: pathlib.Path) -> None:
        """Test that Go detection takes precedence when go.mod exists."""
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")
        # Python pyproject.toml should not override Go detection
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        result = detect_language(tmp_path)
        # Go should be detected because go.mod is more specific
        assert result == "go"


class TestGetAspConfigForLanguage:
    """Tests for get_asp_config_for_language function."""

    def test_read_python_config(self, tmp_path: pathlib.Path) -> None:
        """Test reading ASP config from pyproject.toml."""
        pyproject_content = """
[project]
name = "test-agent"

[tool.agent-starter-pack]
name = "test-agent"
base_template = "adk"
agent_directory = "app"
asp_version = "0.31.0"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        config = get_asp_config_for_language(tmp_path, "python")

        assert config is not None
        assert config["name"] == "test-agent"
        assert config["base_template"] == "adk"
        assert config["asp_version"] == "0.31.0"

    def test_read_go_config(self, tmp_path: pathlib.Path) -> None:
        """Test reading ASP config from .asp.toml for Go."""
        asp_toml_content = """
[project]
name = "test-go-agent"
language = "go"
base_template = "adk_go"
version = "0.31.0"
deployment_target = "cloud_run"
"""
        (tmp_path / ".asp.toml").write_text(asp_toml_content)

        config = get_asp_config_for_language(tmp_path, "go")

        assert config is not None
        assert config["name"] == "test-go-agent"
        assert config["language"] == "go"
        assert config["base_template"] == "adk_go"
        assert config["version"] == "0.31.0"

    def test_missing_config_file_returns_none(self, tmp_path: pathlib.Path) -> None:
        """Test that missing config file returns None."""
        config = get_asp_config_for_language(tmp_path, "python")
        assert config is None

    def test_unknown_language_returns_none(self, tmp_path: pathlib.Path) -> None:
        """Test that unknown language returns None."""
        config = get_asp_config_for_language(tmp_path, "unknown_lang")
        assert config is None

    def test_missing_nested_config_returns_none(self, tmp_path: pathlib.Path) -> None:
        """Test that missing nested config path returns None."""
        # pyproject.toml exists but without [tool.agent-starter-pack]
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        config = get_asp_config_for_language(tmp_path, "python")
        assert config is None


class TestGetLanguageConfig:
    """Tests for get_language_config function."""

    def test_returns_python_config(self) -> None:
        """Test getting Python configuration."""
        config = get_language_config("python")
        assert config["display_name"] == "Python"
        assert config["config_file"] == "pyproject.toml"

    def test_returns_go_config(self) -> None:
        """Test getting Go configuration."""
        config = get_language_config("go")
        assert config["display_name"] == "Go"
        assert config["config_file"] == ".asp.toml"

    def test_returns_python_for_unknown(self) -> None:
        """Test that unknown language falls back to Python config."""
        config = get_language_config("unknown")
        assert config["display_name"] == "Python"


class TestUpdateAspVersion:
    """Tests for update_asp_version function."""

    def test_update_python_version(self, tmp_path: pathlib.Path) -> None:
        """Test updating version in pyproject.toml."""
        pyproject_content = """
[project]
name = "test"

[tool.agent-starter-pack]
name = "test"
asp_version = "0.30.0"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        result = update_asp_version(tmp_path, "python", "0.31.0")

        assert result is True
        content = (tmp_path / "pyproject.toml").read_text()
        assert 'asp_version = "0.31.0"' in content
        assert "0.30.0" not in content

    def test_update_go_version(self, tmp_path: pathlib.Path) -> None:
        """Test updating version in .asp.toml."""
        asp_toml_content = """
[project]
name = "test-go"
language = "go"
version = "0.30.0"
"""
        (tmp_path / ".asp.toml").write_text(asp_toml_content)

        result = update_asp_version(tmp_path, "go", "0.31.0")

        assert result is True
        content = (tmp_path / ".asp.toml").read_text()
        assert 'version = "0.31.0"' in content
        assert "0.30.0" not in content

    def test_update_single_quoted_version(self, tmp_path: pathlib.Path) -> None:
        """Test updating version with single quotes."""
        pyproject_content = """
[project]
name = "test"

[tool.agent-starter-pack]
asp_version = '0.30.0'
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        result = update_asp_version(tmp_path, "python", "0.31.0")

        assert result is True
        content = (tmp_path / "pyproject.toml").read_text()
        assert "'0.31.0'" in content

    def test_returns_false_for_missing_file(self, tmp_path: pathlib.Path) -> None:
        """Test that missing file returns False."""
        result = update_asp_version(tmp_path, "python", "0.31.0")
        assert result is False

    def test_returns_false_for_missing_version_key(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that missing version key returns False."""
        # File exists but has no asp_version
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        result = update_asp_version(tmp_path, "python", "0.31.0")
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
