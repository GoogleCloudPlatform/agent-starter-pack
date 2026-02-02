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
    find_agent_file,
    get_agent_file_hint,
    get_asp_config_for_language,
    get_language_config,
    update_asp_version,
    validate_agent_file,
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

    def test_java_config_exists(self) -> None:
        """Test that Java configuration exists and is complete."""
        assert "java" in LANGUAGE_CONFIGS
        java_config = LANGUAGE_CONFIGS["java"]
        assert java_config["detection_files"] == ["pom.xml"]
        assert java_config["config_file"] == "pom.xml"
        assert java_config["config_format"] == "maven_properties"
        assert java_config["config_path"] == []
        assert java_config["version_key"] == "asp.version"
        assert java_config["lock_command"] == ["mvn", "dependency:resolve"]
        assert java_config["strip_dependencies"] is False
        assert java_config["display_name"] == "Java"
        assert java_config["lock_file"] is None

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
            "agent_file",
            "agent_variable",
            "agent_in_subdirectory",
        ]
        for lang, config in LANGUAGE_CONFIGS.items():
            for key in required_keys:
                assert key in config, f"Language '{lang}' missing key '{key}'"

    def test_agent_file_configs(self) -> None:
        """Test agent file configuration for each language."""
        assert LANGUAGE_CONFIGS["python"]["agent_file"] == "agent.py"
        assert LANGUAGE_CONFIGS["python"]["agent_variable"] == "root_agent"
        assert LANGUAGE_CONFIGS["python"]["agent_in_subdirectory"] is False

        assert LANGUAGE_CONFIGS["go"]["agent_file"] == "agent.go"
        assert LANGUAGE_CONFIGS["go"]["agent_variable"] == "RootAgent"
        assert LANGUAGE_CONFIGS["go"]["agent_in_subdirectory"] is False

        assert LANGUAGE_CONFIGS["java"]["agent_file"] == "Agent.java"
        assert LANGUAGE_CONFIGS["java"]["agent_variable"] == "ROOT_AGENT"
        assert LANGUAGE_CONFIGS["java"]["agent_in_subdirectory"] is True
        assert LANGUAGE_CONFIGS["java"]["agent_file_pattern"] == "**/Agent.java"


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

    def test_detect_java_from_pom_xml(self, tmp_path: pathlib.Path) -> None:
        """Test detection of Java project from pom.xml."""
        (tmp_path / "pom.xml").write_text(
            '<?xml version="1.0"?><project><artifactId>test</artifactId></project>'
        )

        result = detect_language(tmp_path)
        assert result == "java"

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

    def test_read_java_config(self, tmp_path: pathlib.Path) -> None:
        """Test reading ASP config from pom.xml Maven properties for Java."""
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>test</groupId>
  <artifactId>test-java-agent</artifactId>
  <version>1.0.0</version>
  <properties>
    <asp.name>test-java-agent</asp.name>
    <asp.language>java</asp.language>
    <asp.base_template>adk_java</asp.base_template>
    <asp.version>0.31.0</asp.version>
    <asp.deployment_target>cloud_run</asp.deployment_target>
  </properties>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_content)

        config = get_asp_config_for_language(tmp_path, "java")

        assert config is not None
        assert config["name"] == "test-java-agent"
        assert config["language"] == "java"
        assert config["base_template"] == "adk_java"
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

    def test_returns_java_config(self) -> None:
        """Test getting Java configuration."""
        config = get_language_config("java")
        assert config["display_name"] == "Java"
        assert config["config_file"] == "pom.xml"

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

    def test_update_java_version(self, tmp_path: pathlib.Path) -> None:
        """Test updating version in pom.xml Maven properties for Java."""
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>test</groupId>
  <artifactId>test-java</artifactId>
  <version>1.0.0</version>
  <properties>
    <asp.name>test-java</asp.name>
    <asp.version>0.30.0</asp.version>
  </properties>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_content)

        result = update_asp_version(tmp_path, "java", "0.31.0")

        assert result is True
        content = (tmp_path / "pom.xml").read_text()
        assert "<asp.version>0.31.0</asp.version>" in content
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


class TestFindAgentFile:
    """Tests for find_agent_file function."""

    def test_find_python_agent_file(self, tmp_path: pathlib.Path) -> None:
        """Test finding agent.py in Python project."""
        agent_dir = tmp_path / "app"
        agent_dir.mkdir()
        (agent_dir / "agent.py").write_text("root_agent = Agent()")

        result = find_agent_file(tmp_path, "python", "app")

        assert result is not None
        assert result.name == "agent.py"
        assert result.exists()

    def test_find_go_agent_file(self, tmp_path: pathlib.Path) -> None:
        """Test finding agent.go in Go project."""
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()
        (agent_dir / "agent.go").write_text("var RootAgent Agent")

        result = find_agent_file(tmp_path, "go", "agent")

        assert result is not None
        assert result.name == "agent.go"
        assert result.exists()

    def test_find_java_agent_file_in_subdirectory(self, tmp_path: pathlib.Path) -> None:
        """Test finding Agent.java in Java package subdirectory."""
        # Create Java package structure
        java_dir = tmp_path / "src" / "main" / "java"
        package_dir = java_dir / "com" / "example" / "agent"
        package_dir.mkdir(parents=True)
        (package_dir / "Agent.java").write_text("public static Agent ROOT_AGENT;")

        result = find_agent_file(tmp_path, "java", "src/main/java")

        assert result is not None
        assert result.name == "Agent.java"
        assert result.exists()

    def test_find_yaml_agent_file(self, tmp_path: pathlib.Path) -> None:
        """Test finding root_agent.yaml takes precedence."""
        agent_dir = tmp_path / "app"
        agent_dir.mkdir()
        (agent_dir / "root_agent.yaml").write_text("name: my_agent")
        (agent_dir / "agent.py").write_text("root_agent = Agent()")

        result = find_agent_file(tmp_path, "python", "app")

        assert result is not None
        assert result.name == "root_agent.yaml"

    def test_find_agent_file_missing_directory(self, tmp_path: pathlib.Path) -> None:
        """Test that missing agent directory returns None."""
        result = find_agent_file(tmp_path, "python", "app")
        assert result is None

    def test_find_agent_file_missing_file(self, tmp_path: pathlib.Path) -> None:
        """Test that missing agent file returns None."""
        agent_dir = tmp_path / "app"
        agent_dir.mkdir()
        # Directory exists but no agent file

        result = find_agent_file(tmp_path, "python", "app")
        assert result is None


class TestValidateAgentFile:
    """Tests for validate_agent_file function."""

    def test_validate_python_agent_file_valid(self, tmp_path: pathlib.Path) -> None:
        """Test validating Python agent file with root_agent."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text("root_agent = MyAgent()")

        is_valid, error_msg = validate_agent_file(agent_file, "python")

        assert is_valid is True
        assert error_msg is None

    def test_validate_python_agent_file_invalid(self, tmp_path: pathlib.Path) -> None:
        """Test validating Python agent file without root_agent."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text("agent = MyAgent()")

        is_valid, error_msg = validate_agent_file(agent_file, "python")

        assert is_valid is False
        assert error_msg is not None
        assert "root_agent" in error_msg

    def test_validate_go_agent_file_valid(self, tmp_path: pathlib.Path) -> None:
        """Test validating Go agent file with RootAgent."""
        agent_file = tmp_path / "agent.go"
        agent_file.write_text("var RootAgent = NewAgent()")

        is_valid, error_msg = validate_agent_file(agent_file, "go")

        assert is_valid is True
        assert error_msg is None

    def test_validate_java_agent_file_valid(self, tmp_path: pathlib.Path) -> None:
        """Test validating Java agent file with ROOT_AGENT."""
        agent_file = tmp_path / "Agent.java"
        agent_file.write_text("public static final Agent ROOT_AGENT = new Agent();")

        is_valid, error_msg = validate_agent_file(agent_file, "java")

        assert is_valid is True
        assert error_msg is None

    def test_validate_java_agent_file_invalid(self, tmp_path: pathlib.Path) -> None:
        """Test validating Java agent file without ROOT_AGENT."""
        agent_file = tmp_path / "Agent.java"
        agent_file.write_text("public class Agent { }")

        is_valid, error_msg = validate_agent_file(agent_file, "java")

        assert is_valid is False
        assert error_msg is not None
        assert "ROOT_AGENT" in error_msg

    def test_validate_yaml_agent_file_always_valid(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that YAML config agents are always valid."""
        agent_file = tmp_path / "root_agent.yaml"
        agent_file.write_text("name: my_agent")

        is_valid, error_msg = validate_agent_file(agent_file, "python")

        assert is_valid is True
        assert error_msg is None


class TestGetAgentFileHint:
    """Tests for get_agent_file_hint function."""

    def test_hint_for_python_agent(self, tmp_path: pathlib.Path) -> None:
        """Test hint generation for Python agent.py."""
        (tmp_path / "agent.py").write_text("root_agent = Agent()")

        hint = get_agent_file_hint(tmp_path)

        assert hint == " (has agent.py)"

    def test_hint_for_go_agent(self, tmp_path: pathlib.Path) -> None:
        """Test hint generation for Go agent.go."""
        (tmp_path / "agent.go").write_text("var RootAgent Agent")

        hint = get_agent_file_hint(tmp_path)

        assert hint == " (has agent.go)"

    def test_hint_for_java_agent_in_subdirectory(self, tmp_path: pathlib.Path) -> None:
        """Test hint generation for Java Agent.java in subdirectory."""
        package_dir = tmp_path / "com" / "example"
        package_dir.mkdir(parents=True)
        (package_dir / "Agent.java").write_text("public class Agent {}")

        hint = get_agent_file_hint(tmp_path)

        assert hint == " (has Agent.java)"

    def test_hint_for_yaml_agent(self, tmp_path: pathlib.Path) -> None:
        """Test hint generation for YAML config agent."""
        (tmp_path / "root_agent.yaml").write_text("name: my_agent")

        hint = get_agent_file_hint(tmp_path)

        assert hint == " (has root_agent.yaml)"

    def test_hint_yaml_takes_precedence(self, tmp_path: pathlib.Path) -> None:
        """Test that YAML config takes precedence in hint."""
        (tmp_path / "root_agent.yaml").write_text("name: my_agent")
        (tmp_path / "agent.py").write_text("root_agent = Agent()")

        hint = get_agent_file_hint(tmp_path)

        assert hint == " (has root_agent.yaml)"

    def test_hint_for_empty_directory(self, tmp_path: pathlib.Path) -> None:
        """Test hint for directory without agent files."""
        hint = get_agent_file_hint(tmp_path)
        assert hint == ""

    def test_hint_for_non_directory(self, tmp_path: pathlib.Path) -> None:
        """Test hint for non-directory path returns empty."""
        file_path = tmp_path / "some_file.txt"
        file_path.write_text("content")

        hint = get_agent_file_hint(file_path)

        assert hint == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
