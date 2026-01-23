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

"""Unit tests for the extract command."""

import pathlib
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agent_starter_pack.cli.commands.extract import (
    SCAFFOLDING_DEPENDENCIES,
    SCAFFOLDING_DIRS,
    SCAFFOLDING_FILES_IN_AGENT_DIR,
    detect_agent_directory,
    extract,
    get_asp_config,
    is_core_dependency,
    is_scaffolding_dependency,
    process_pyproject_toml,
)
from agent_starter_pack.cli.utils.language import (
    LANGUAGE_CONFIGS,
    detect_language,
    get_asp_config_for_language,
)


class TestDependencyClassification:
    """Test dependency classification functions."""

    def test_is_scaffolding_dependency_fastapi(self) -> None:
        """Test that FastAPI is classified as scaffolding."""
        assert is_scaffolding_dependency("fastapi~=0.115.8")
        assert is_scaffolding_dependency("fastapi>=0.100.0")
        assert is_scaffolding_dependency("fastapi")

    def test_is_scaffolding_dependency_uvicorn(self) -> None:
        """Test that uvicorn is classified as scaffolding."""
        assert is_scaffolding_dependency("uvicorn~=0.34.0")
        assert is_scaffolding_dependency("uvicorn")

    def test_is_scaffolding_dependency_asyncpg(self) -> None:
        """Test that asyncpg is classified as scaffolding."""
        assert is_scaffolding_dependency("asyncpg>=0.30.0,<1.0.0")

    def test_is_not_scaffolding_dependency(self) -> None:
        """Test that core dependencies are not classified as scaffolding."""
        assert not is_scaffolding_dependency("google-adk>=1.15.0,<2.0.0")
        assert not is_scaffolding_dependency("langchain")
        assert not is_scaffolding_dependency("pyyaml>=6.0.1")

    def test_is_core_dependency_adk(self) -> None:
        """Test that google-adk is classified as core."""
        assert is_core_dependency("google-adk>=1.15.0,<2.0.0")
        assert is_core_dependency("google-adk")

    def test_is_core_dependency_langchain(self) -> None:
        """Test that langchain is classified as core."""
        assert is_core_dependency("langchain>=0.1.0")
        assert is_core_dependency("langchain-google-genai")

    def test_is_core_dependency_langgraph(self) -> None:
        """Test that langgraph is classified as core."""
        assert is_core_dependency("langgraph>=0.2.0")


class TestProcessPyprojectToml:
    """Test pyproject.toml processing for dependency stripping."""

    def test_strips_scaffolding_dependencies(self, tmp_path: pathlib.Path) -> None:
        """Test that scaffolding dependencies are removed."""
        source = tmp_path / "source.toml"
        dest = tmp_path / "dest.toml"

        source.write_text("""[project]
name = "test"
dependencies = [
    "google-adk>=1.15.0",
    "fastapi~=0.115.8",
    "uvicorn~=0.34.0",
    "asyncpg>=0.30.0",
]

[tool.agent-starter-pack]
name = "test"
""")

        process_pyproject_toml(source, dest)

        result = dest.read_text()
        assert "google-adk>=1.15.0" in result
        assert "fastapi" not in result
        assert "uvicorn" not in result
        assert "asyncpg" not in result

    def test_keeps_core_dependencies(self, tmp_path: pathlib.Path) -> None:
        """Test that core dependencies are preserved."""
        source = tmp_path / "source.toml"
        dest = tmp_path / "dest.toml"

        source.write_text("""[project]
name = "test"
dependencies = [
    "google-adk>=1.15.0",
    "langchain>=0.1.0",
    "langgraph>=0.2.0",
    "gcsfs>=2024.11.0",
]

[tool.agent-starter-pack]
name = "test"
""")

        process_pyproject_toml(source, dest)

        result = dest.read_text()
        assert "google-adk>=1.15.0" in result
        assert "langchain>=0.1.0" in result
        assert "langgraph>=0.2.0" in result
        assert "gcsfs" not in result

    def test_adds_extracted_metadata(self, tmp_path: pathlib.Path) -> None:
        """Test that extracted metadata is added to ASP section."""
        source = tmp_path / "source.toml"
        dest = tmp_path / "dest.toml"

        source.write_text("""[project]
name = "test"

[tool.agent-starter-pack]
name = "test"
""")

        process_pyproject_toml(source, dest)

        result = dest.read_text()
        assert "extracted = true" in result
        assert "extracted_at" in result


class TestAgentDirectoryDetection:
    """Test agent directory detection logic."""

    def test_detect_from_asp_config(self, tmp_path: pathlib.Path) -> None:
        """Test detection from ASP config."""
        asp_config = {"agent_directory": "my_custom_agent"}
        result = detect_agent_directory(tmp_path, asp_config)
        assert result == "my_custom_agent"

    def test_detect_app_directory(self, tmp_path: pathlib.Path) -> None:
        """Test detection of standard 'app' directory."""
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "agent.py").touch()

        result = detect_agent_directory(tmp_path, None)
        assert result == "app"

    def test_detect_agent_directory(self, tmp_path: pathlib.Path) -> None:
        """Test detection of 'agent' directory."""
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()
        (agent_dir / "agent.py").touch()

        result = detect_agent_directory(tmp_path, None)
        assert result == "agent"

    def test_detect_fallback_to_app(self, tmp_path: pathlib.Path) -> None:
        """Test fallback to 'app' when no agent.py found."""
        result = detect_agent_directory(tmp_path, None)
        assert result == "app"


class TestGetAspConfig:
    """Test ASP config reading from pyproject.toml."""

    def test_read_asp_config(self, tmp_path: pathlib.Path) -> None:
        """Test reading valid ASP config."""
        pyproject_content = """
[project]
name = "test-agent"

[tool.agent-starter-pack]
name = "test-agent"
base_template = "adk"
agent_directory = "app"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        config = get_asp_config(tmp_path)

        assert config is not None
        assert config["name"] == "test-agent"
        assert config["base_template"] == "adk"
        assert config["agent_directory"] == "app"

    def test_no_pyproject(self, tmp_path: pathlib.Path) -> None:
        """Test handling missing pyproject.toml."""
        config = get_asp_config(tmp_path)
        assert config is None

    def test_no_asp_section(self, tmp_path: pathlib.Path) -> None:
        """Test handling pyproject.toml without ASP section."""
        pyproject_content = """
[project]
name = "test-agent"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        config = get_asp_config(tmp_path)
        assert config is None


class TestScaffoldingConstants:
    """Test scaffolding configuration constants."""

    def test_scaffolding_dirs_includes_deployment(self) -> None:
        """Test that deployment is in scaffolding dirs."""
        assert "deployment" in SCAFFOLDING_DIRS

    def test_scaffolding_dirs_includes_cicd(self) -> None:
        """Test that CI/CD dirs are in scaffolding dirs."""
        assert ".github" in SCAFFOLDING_DIRS
        assert ".cloudbuild" in SCAFFOLDING_DIRS

    def test_scaffolding_files_in_agent_dir(self) -> None:
        """Test scaffolding files within agent directory."""
        assert "app_utils" in SCAFFOLDING_FILES_IN_AGENT_DIR
        assert "fast_api_app.py" in SCAFFOLDING_FILES_IN_AGENT_DIR
        assert "agent_engine_app.py" in SCAFFOLDING_FILES_IN_AGENT_DIR

    def test_scaffolding_dependencies_list(self) -> None:
        """Test scaffolding dependencies are defined."""
        assert "fastapi" in SCAFFOLDING_DEPENDENCIES
        assert "uvicorn" in SCAFFOLDING_DEPENDENCIES
        assert "asyncpg" in SCAFFOLDING_DEPENDENCIES


class TestExtractCommand:
    """Test the extract command functionality."""

    def test_extract_dry_run(self) -> None:
        """Test extract in dry-run mode."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create minimal source project
            pathlib.Path("pyproject.toml").write_text("""
[project]
name = "test-agent"

[tool.agent-starter-pack]
name = "test-agent"
base_template = "adk"
agent_directory = "app"
""")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text("root_agent = None")
            pathlib.Path("app/__init__.py").touch()
            pathlib.Path("deployment").mkdir()
            pathlib.Path(".github").mkdir()

            result = runner.invoke(
                extract,
                ["../output", "--dry-run"],
            )

            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            assert not pathlib.Path("../output").exists()

    def test_extract_no_config_file(self) -> None:
        """Test extract fails without any project config file."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                extract,
                ["../output"],
            )

            assert result.exit_code == 1
            assert "No project config file found" in result.output

    def test_extract_no_asp_config_prompts(self) -> None:
        """Test extract warns when no ASP config present."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            pathlib.Path("pyproject.toml").write_text("""
[project]
name = "test-agent"
""")

            result = runner.invoke(
                extract,
                ["../output"],
                input="n\n",  # Don't continue
            )

            assert "Warning" in result.output
            assert "agent-starter-pack" in result.output

    def test_extract_output_exists_without_force(self) -> None:
        """Test extract fails when output exists without --force."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create source
            pathlib.Path("pyproject.toml").write_text("""
[project]
name = "test-agent"

[tool.agent-starter-pack]
agent_directory = "app"
""")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").touch()

            # Create existing output
            pathlib.Path("output").mkdir()

            result = runner.invoke(
                extract,
                ["output"],
            )

            assert result.exit_code == 1
            assert "already exists" in result.output
            assert "--force" in result.output

    @patch("agent_starter_pack.cli.commands.extract.subprocess.run")
    def test_extract_creates_output(self, mock_subprocess: MagicMock) -> None:
        """Test that extract creates output directory with core files."""
        # Mock uv lock to succeed
        mock_subprocess.return_value = MagicMock(returncode=0)

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create source project
            pathlib.Path("pyproject.toml").write_text("""
[project]
name = "test-agent"
dependencies = [
    "google-adk>=1.15.0",
    "fastapi~=0.115.8",
]

[tool.agent-starter-pack]
name = "test-agent"
base_template = "adk"
agent_directory = "app"
""")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").write_text(
                "from google.adk.agents import Agent\nroot_agent = Agent()"
            )
            pathlib.Path("app/__init__.py").touch()
            pathlib.Path("app/custom_module.py").write_text("# Custom code")
            pathlib.Path("app/app_utils").mkdir()
            pathlib.Path("app/app_utils/telemetry.py").touch()
            pathlib.Path("README.md").write_text("# Test Agent")
            pathlib.Path(".gitignore").write_text(".venv/")
            pathlib.Path("deployment").mkdir()
            pathlib.Path("deployment/terraform").mkdir()
            pathlib.Path(".github").mkdir()
            pathlib.Path(".cloudbuild").mkdir()

            result = runner.invoke(
                extract,
                ["output"],
            )

            assert result.exit_code == 0
            assert pathlib.Path("output").exists()
            assert pathlib.Path("output/app").exists()
            assert pathlib.Path("output/app/agent.py").exists()
            assert pathlib.Path("output/app/custom_module.py").exists()
            assert pathlib.Path("output/pyproject.toml").exists()
            assert pathlib.Path("output/Makefile").exists()
            assert pathlib.Path("output/README.md").exists()
            assert pathlib.Path("output/.gitignore").exists()

            # Scaffolding should not be copied
            assert not pathlib.Path("output/deployment").exists()
            assert not pathlib.Path("output/.github").exists()
            assert not pathlib.Path("output/.cloudbuild").exists()
            assert not pathlib.Path("output/app/app_utils").exists()

    @patch("agent_starter_pack.cli.commands.extract.subprocess.run")
    def test_extract_removes_tests_by_default(self, mock_subprocess: MagicMock) -> None:
        """Test that tests are removed by default."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create source project
            pathlib.Path("pyproject.toml").write_text("""
[project]
name = "test-agent"

[tool.agent-starter-pack]
agent_directory = "app"
""")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").touch()
            pathlib.Path("tests").mkdir()
            pathlib.Path("tests/test_agent.py").touch()

            result = runner.invoke(
                extract,
                ["output"],
            )

            assert result.exit_code == 0
            assert not pathlib.Path("output/tests").exists()

    @patch("agent_starter_pack.cli.commands.extract.subprocess.run")
    def test_extract_with_force_overwrites(self, mock_subprocess: MagicMock) -> None:
        """Test that --force overwrites existing output."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create source
            pathlib.Path("pyproject.toml").write_text("""
[project]
name = "test-agent"

[tool.agent-starter-pack]
agent_directory = "app"
""")
            pathlib.Path("app").mkdir()
            pathlib.Path("app/agent.py").touch()

            # Create existing output with a file
            pathlib.Path("output").mkdir()
            pathlib.Path("output/old_file.txt").write_text("old content")

            result = runner.invoke(
                extract,
                ["output", "--force"],
            )

            assert result.exit_code == 0
            assert pathlib.Path("output").exists()
            # Old file should be gone
            assert not pathlib.Path("output/old_file.txt").exists()


class TestLanguageConfiguration:
    """Test language configuration and detection."""

    def test_language_configs_has_python(self) -> None:
        """Test that Python configuration exists."""
        assert "python" in LANGUAGE_CONFIGS
        python_config = LANGUAGE_CONFIGS["python"]
        assert python_config["detection_files"] == ["pyproject.toml"]
        assert python_config["config_file"] == "pyproject.toml"
        assert python_config["lock_command"] == ["uv", "lock"]
        assert python_config["strip_dependencies"] is True

    def test_language_configs_has_go(self) -> None:
        """Test that Go configuration exists."""
        assert "go" in LANGUAGE_CONFIGS
        go_config = LANGUAGE_CONFIGS["go"]
        assert go_config["detection_files"] == ["go.mod"]
        assert go_config["config_file"] == ".asp.toml"
        assert go_config["lock_command"] == ["go", "mod", "tidy"]
        assert go_config["strip_dependencies"] is False

    def test_language_configs_extensible(self) -> None:
        """Test that language configs have consistent structure."""
        required_keys = [
            "detection_files",
            "config_file",
            "config_path",
            "project_files",
            "lock_file",
            "lock_command",
            "strip_dependencies",
            "display_name",
        ]
        for lang, config in LANGUAGE_CONFIGS.items():
            for key in required_keys:
                assert key in config, f"Language '{lang}' missing key '{key}'"


class TestLanguageDetection:
    """Test language detection logic."""

    def test_detect_python_project(self, tmp_path: pathlib.Path) -> None:
        """Test detection of Python project."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        result = detect_language(tmp_path)
        assert result == "python"

    def test_detect_go_project(self, tmp_path: pathlib.Path) -> None:
        """Test detection of Go project."""
        (tmp_path / "go.mod").write_text("module test\n\ngo 1.21")

        result = detect_language(tmp_path)
        assert result == "go"

    def test_detect_from_asp_toml_language_field(self, tmp_path: pathlib.Path) -> None:
        """Test detection from explicit language field in .asp.toml."""
        (tmp_path / ".asp.toml").write_text('[project]\nlanguage = "go"')
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        result = detect_language(tmp_path)
        assert result == "go"

    def test_detect_defaults_to_python(self, tmp_path: pathlib.Path) -> None:
        """Test default to Python when no indicators found."""
        result = detect_language(tmp_path)
        assert result == "python"


class TestGetAspConfigForLanguage:
    """Test ASP config reading for different languages."""

    def test_read_python_config(self, tmp_path: pathlib.Path) -> None:
        """Test reading ASP config from pyproject.toml."""
        pyproject_content = """
[project]
name = "test-agent"

[tool.agent-starter-pack]
name = "test-agent"
base_template = "adk"
agent_directory = "app"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        config = get_asp_config_for_language(tmp_path, "python")

        assert config is not None
        assert config["name"] == "test-agent"
        assert config["base_template"] == "adk"

    def test_read_go_config(self, tmp_path: pathlib.Path) -> None:
        """Test reading ASP config from .asp.toml for Go."""
        asp_toml_content = """
[project]
name = "test-go-agent"
language = "go"
base_template = "adk_go"
deployment_target = "cloud_run"
"""
        (tmp_path / ".asp.toml").write_text(asp_toml_content)

        config = get_asp_config_for_language(tmp_path, "go")

        assert config is not None
        assert config["name"] == "test-go-agent"
        assert config["language"] == "go"
        assert config["base_template"] == "adk_go"

    def test_missing_config_file_returns_none(self, tmp_path: pathlib.Path) -> None:
        """Test that missing config file returns None."""
        config = get_asp_config_for_language(tmp_path, "python")
        assert config is None

    def test_unknown_language_returns_none(self, tmp_path: pathlib.Path) -> None:
        """Test that unknown language returns None."""
        config = get_asp_config_for_language(tmp_path, "unknown_lang")
        assert config is None


class TestGoProjectExtraction:
    """Test extraction of Go projects."""

    @patch("agent_starter_pack.cli.commands.extract.subprocess.run")
    def test_extract_go_project_dry_run(self, mock_subprocess: MagicMock) -> None:
        """Test dry-run mode for Go project."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create Go project structure
            pathlib.Path("go.mod").write_text("module test-agent\n\ngo 1.21")
            pathlib.Path("go.sum").touch()
            pathlib.Path(".asp.toml").write_text("""
[project]
name = "test-go-agent"
language = "go"
base_template = "adk_go"
agent_directory = "agent"
""")
            pathlib.Path("agent").mkdir()
            pathlib.Path("agent/agent.go").write_text("package agent")
            pathlib.Path("deployment").mkdir()

            result = runner.invoke(
                extract,
                ["../output", "--dry-run"],
            )

            assert result.exit_code == 0
            assert "DRY RUN" in result.output
            assert "Go" in result.output
            assert not pathlib.Path("../output").exists()

    @patch("agent_starter_pack.cli.commands.extract.subprocess.run")
    def test_extract_go_project_copies_go_files(
        self, mock_subprocess: MagicMock
    ) -> None:
        """Test that Go project extraction copies go.mod and .asp.toml."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create Go project structure
            pathlib.Path("go.mod").write_text("module test-agent\n\ngo 1.21")
            pathlib.Path("go.sum").write_text("// checksums")
            pathlib.Path(".asp.toml").write_text("""
[project]
name = "test-go-agent"
language = "go"
base_template = "adk_go"
agent_directory = "agent"
""")
            pathlib.Path("agent").mkdir()
            pathlib.Path("agent/agent.go").write_text("package agent")
            pathlib.Path("README.md").write_text("# Test Agent")
            pathlib.Path(".gitignore").write_text("bin/")

            result = runner.invoke(
                extract,
                ["output"],
            )

            assert result.exit_code == 0
            assert pathlib.Path("output").exists()
            assert pathlib.Path("output/go.mod").exists()
            assert pathlib.Path("output/go.sum").exists()
            assert pathlib.Path("output/.asp.toml").exists()
            assert pathlib.Path("output/agent").exists()
            assert pathlib.Path("output/Makefile").exists()

    @patch("agent_starter_pack.cli.commands.extract.subprocess.run")
    def test_extract_go_project_runs_go_mod_tidy(
        self, mock_subprocess: MagicMock
    ) -> None:
        """Test that Go extraction runs 'go mod tidy'."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create Go project
            pathlib.Path("go.mod").write_text("module test-agent\n\ngo 1.21")
            pathlib.Path(".asp.toml").write_text("""
[project]
name = "test-go-agent"
language = "go"
agent_directory = "agent"
""")
            pathlib.Path("agent").mkdir()
            pathlib.Path("agent/agent.go").write_text("package agent")

            runner.invoke(extract, ["output"])

            # Verify go mod tidy was called
            calls = mock_subprocess.call_args_list
            go_mod_tidy_called = any(
                call[0][0] == ["go", "mod", "tidy"] for call in calls
            )
            assert go_mod_tidy_called
