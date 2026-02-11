# Copyright 2026 Google LLC
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

import pytest

from agent_starter_pack.cli.utils.template import (
    copy_flat_structure_agent_files,
    generate_java_package_vars,
    merge_guidance_file,
    validate_agent_directory_name,
)


class TestValidateAgentDirectoryName:
    """Tests for the validate_agent_directory_name function."""

    def test_valid_simple_name(self) -> None:
        """Test that simple valid names pass validation."""
        # Should not raise
        validate_agent_directory_name("app")
        validate_agent_directory_name("myagent")
        validate_agent_directory_name("agent123")

    def test_valid_name_with_underscores(self) -> None:
        """Test that names with underscores pass validation."""
        validate_agent_directory_name("my_agent")
        validate_agent_directory_name("my_cool_agent")
        validate_agent_directory_name("agent_v2")

    def test_dot_rejected_by_default(self) -> None:
        """Test that '.' is rejected without allow_dot flag."""
        with pytest.raises(ValueError, match="not valid"):
            validate_agent_directory_name(".")

    def test_dot_allowed_with_flag(self) -> None:
        """Test that '.' is allowed when allow_dot=True."""
        # Should not raise
        validate_agent_directory_name(".", allow_dot=True)

    def test_hyphenated_name_rejected(self) -> None:
        """Test that hyphenated names are rejected."""
        with pytest.raises(ValueError, match="hyphens"):
            validate_agent_directory_name("my-agent")

    def test_invalid_python_identifier_rejected(self) -> None:
        """Test that invalid Python identifiers are rejected."""
        with pytest.raises(ValueError, match="not a valid Python identifier"):
            validate_agent_directory_name("123agent")  # Starts with number

    def test_empty_string_rejected(self) -> None:
        """Test that empty string is rejected."""
        with pytest.raises(ValueError, match="not a valid Python identifier"):
            validate_agent_directory_name("")

    def test_special_characters_rejected(self) -> None:
        """Test that special characters are rejected."""
        with pytest.raises(ValueError, match="not a valid Python identifier"):
            validate_agent_directory_name("agent@home")

    def test_java_language_skips_python_validation(self) -> None:
        """Test that Java language skips Python identifier validation."""
        # These would fail for Python but should pass for Java
        validate_agent_directory_name("src/main/java", language="java")
        validate_agent_directory_name("my-agent", language="java")
        validate_agent_directory_name("123agent", language="java")

    def test_go_language_skips_python_validation(self) -> None:
        """Test that Go language skips Python identifier validation."""
        # These would fail for Python but should pass for Go
        validate_agent_directory_name("my-agent", language="go")
        validate_agent_directory_name("agent/pkg", language="go")

    def test_python_language_uses_python_validation(self) -> None:
        """Test that Python language uses Python identifier validation."""
        with pytest.raises(ValueError, match="not a valid Python identifier"):
            validate_agent_directory_name("123agent", language="python")
        with pytest.raises(ValueError, match="hyphens"):
            validate_agent_directory_name("my-agent", language="python")


class TestGenerateJavaPackageVars:
    """Tests for the generate_java_package_vars function."""

    def test_simple_project_name(self) -> None:
        """Test generation for simple project name."""
        result = generate_java_package_vars("myagent")
        assert result["java_package"] == "myagent"
        assert result["java_package_path"] == "myagent"

    def test_hyphenated_project_name(self) -> None:
        """Test that hyphens are removed (Java convention: no separators)."""
        result = generate_java_package_vars("my-agent")
        assert result["java_package"] == "myagent"
        assert result["java_package_path"] == "myagent"

    def test_dotted_project_name(self) -> None:
        """Test that dots are removed (Java convention: no separators)."""
        result = generate_java_package_vars("my.agent")
        assert result["java_package"] == "myagent"
        assert result["java_package_path"] == "myagent"

    def test_uppercase_project_name(self) -> None:
        """Test that uppercase is converted to lowercase."""
        result = generate_java_package_vars("MyAgent")
        assert result["java_package"] == "myagent"
        assert result["java_package_path"] == "myagent"

    def test_leading_digit_prefixed(self) -> None:
        """Test that leading digits get underscore prefix."""
        result = generate_java_package_vars("123agent")
        assert result["java_package"] == "_123agent"
        assert result["java_package_path"] == "_123agent"

    def test_mixed_separators(self) -> None:
        """Test project name with mixed hyphens and dots are removed."""
        result = generate_java_package_vars("my-cool.agent")
        assert result["java_package"] == "mycoolagent"
        assert result["java_package_path"] == "mycoolagent"


class TestCopyFlatStructureAgentFiles:
    """Tests for the copy_flat_structure_agent_files function."""

    def test_python_files_copied_to_agent_directory(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that Python files are copied to the agent directory."""
        # Setup source
        src = tmp_path / "src"
        src.mkdir()
        (src / "agent.py").write_text("root_agent = None")
        (src / "__init__.py").write_text("")
        (src / "utils.py").write_text("# utils")

        # Setup destination
        dst = tmp_path / "dst"
        dst.mkdir()

        copy_flat_structure_agent_files(src, dst, "myagent")

        # Verify Python files are in agent directory
        assert (dst / "myagent" / "agent.py").exists()
        assert (dst / "myagent" / "__init__.py").exists()
        assert (dst / "myagent" / "utils.py").exists()

    def test_non_python_files_copied_to_project_root(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that non-Python files are copied to project root."""
        # Setup source
        src = tmp_path / "src"
        src.mkdir()
        (src / "agent.py").write_text("root_agent = None")
        (src / "config.yaml").write_text("key: value")
        (src / "data.json").write_text("{}")

        # Setup destination
        dst = tmp_path / "dst"
        dst.mkdir()

        copy_flat_structure_agent_files(src, dst, "myagent")

        # Verify non-Python files are in project root
        assert (dst / "config.yaml").exists()
        assert (dst / "data.json").exists()
        # Python file should be in agent directory
        assert (dst / "myagent" / "agent.py").exists()

    def test_subdirectories_copied_to_project_root(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that subdirectories are copied to project root."""
        # Setup source
        src = tmp_path / "src"
        src.mkdir()
        (src / "agent.py").write_text("root_agent = None")
        subdir = src / "resources"
        subdir.mkdir()
        (subdir / "data.txt").write_text("data")

        # Setup destination
        dst = tmp_path / "dst"
        dst.mkdir()

        copy_flat_structure_agent_files(src, dst, "myagent")

        # Verify subdirectory is in project root
        assert (dst / "resources").is_dir()
        assert (dst / "resources" / "data.txt").exists()

    def test_skipped_files_not_copied(self, tmp_path: pathlib.Path) -> None:
        """Test that pyproject.toml, README.md, etc. are not copied."""
        # Setup source
        src = tmp_path / "src"
        src.mkdir()
        (src / "agent.py").write_text("root_agent = None")
        (src / "pyproject.toml").write_text("[project]")
        (src / "README.md").write_text("# README")
        (src / "uv.lock").write_text("lock content")
        (src / ".gitignore").write_text("*.pyc")

        # Setup destination
        dst = tmp_path / "dst"
        dst.mkdir()

        copy_flat_structure_agent_files(src, dst, "myagent")

        # Verify skipped files are not copied
        assert not (dst / "pyproject.toml").exists()
        assert not (dst / "README.md").exists()
        assert not (dst / "uv.lock").exists()
        assert not (dst / ".gitignore").exists()
        # But agent.py should be copied
        assert (dst / "myagent" / "agent.py").exists()

    def test_pycache_not_copied(self, tmp_path: pathlib.Path) -> None:
        """Test that __pycache__ directories are not copied."""
        # Setup source
        src = tmp_path / "src"
        src.mkdir()
        (src / "agent.py").write_text("root_agent = None")
        pycache = src / "__pycache__"
        pycache.mkdir()
        (pycache / "agent.cpython-311.pyc").write_bytes(b"bytecode")

        # Setup destination
        dst = tmp_path / "dst"
        dst.mkdir()

        copy_flat_structure_agent_files(src, dst, "myagent")

        # Verify __pycache__ is not copied
        assert not (dst / "__pycache__").exists()
        assert not (dst / "myagent" / "__pycache__").exists()

    def test_hidden_files_not_copied(self, tmp_path: pathlib.Path) -> None:
        """Test that hidden files (starting with .) are not copied."""
        # Setup source
        src = tmp_path / "src"
        src.mkdir()
        (src / "agent.py").write_text("root_agent = None")
        (src / ".env").write_text("SECRET=value")
        (src / ".hidden_file").write_text("hidden")

        # Setup destination
        dst = tmp_path / "dst"
        dst.mkdir()

        copy_flat_structure_agent_files(src, dst, "myagent")

        # Verify hidden files are not copied
        assert not (dst / ".env").exists()
        assert not (dst / ".hidden_file").exists()

    def test_agent_directory_created_if_not_exists(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that agent directory is created if it doesn't exist."""
        # Setup source
        src = tmp_path / "src"
        src.mkdir()
        (src / "agent.py").write_text("root_agent = None")

        # Setup destination (empty)
        dst = tmp_path / "dst"
        dst.mkdir()

        copy_flat_structure_agent_files(src, dst, "new_agent")

        # Verify agent directory was created
        assert (dst / "new_agent").is_dir()
        assert (dst / "new_agent" / "agent.py").exists()


class TestMergeGuidanceFile:
    """Tests for the merge_guidance_file function."""

    def test_creates_new_file_when_none_exists(self, tmp_path: pathlib.Path) -> None:
        """Test that a new guidance file is created when none exists."""
        new_content = """<!-- ASP-MANAGED-START: agent-guidance -->
<!-- Generated by Agent Starter Pack v0.36.0 -->
# Agent Guide
This is ASP content.
<!-- ASP-MANAGED-END: agent-guidance -->"""

        merge_guidance_file(tmp_path, "GEMINI.md", new_content)

        guidance_file = tmp_path / "GEMINI.md"
        assert guidance_file.exists()
        assert guidance_file.read_text() == new_content

    def test_prepends_asp_section_to_existing_file_without_markers(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that ASP section is prepended when file exists without markers."""
        # Create existing file without ASP markers
        existing_content = """# My Custom Notes

This is my personal guidance for this project."""
        guidance_file = tmp_path / "GEMINI.md"
        guidance_file.write_text(existing_content)

        new_content = """<!-- ASP-MANAGED-START: agent-guidance -->
<!-- Generated by Agent Starter Pack v0.36.0 -->
# Agent Guide
This is ASP content.
<!-- ASP-MANAGED-END: agent-guidance -->"""

        merge_guidance_file(tmp_path, "GEMINI.md", new_content)

        result = guidance_file.read_text()
        assert "<!-- ASP-MANAGED-START:" in result
        assert "<!-- ASP-MANAGED-END:" in result
        assert "# My Custom Notes" in result
        # ASP section should come first
        assert result.index("ASP-MANAGED-START") < result.index("My Custom Notes")

    def test_replaces_asp_section_preserves_user_content(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that ASP section is replaced while user content is preserved."""
        # Create existing file with ASP markers and user content
        existing_content = """<!-- ASP-MANAGED-START: agent-guidance -->
<!-- Generated by Agent Starter Pack v0.35.0 -->
# Old Agent Guide
This is old ASP content.
<!-- ASP-MANAGED-END: agent-guidance -->

# My Custom Notes

This is my personal guidance that should be preserved."""
        guidance_file = tmp_path / "GEMINI.md"
        guidance_file.write_text(existing_content)

        new_content = """<!-- ASP-MANAGED-START: agent-guidance -->
<!-- Generated by Agent Starter Pack v0.36.0 -->
# New Agent Guide
This is new ASP content with updates.
<!-- ASP-MANAGED-END: agent-guidance -->"""

        merge_guidance_file(tmp_path, "GEMINI.md", new_content)

        result = guidance_file.read_text()
        # New ASP content should be present
        assert "v0.36.0" in result
        assert "New Agent Guide" in result
        assert "new ASP content with updates" in result
        # Old ASP content should be gone
        assert "v0.35.0" not in result
        assert "Old Agent Guide" not in result
        assert "old ASP content" not in result
        # User content should be preserved
        assert "# My Custom Notes" in result
        assert "my personal guidance that should be preserved" in result

    def test_handles_custom_filename(self, tmp_path: pathlib.Path) -> None:
        """Test that custom guidance filenames work correctly."""
        new_content = """<!-- ASP-MANAGED-START: agent-guidance -->
# Agent Guide
<!-- ASP-MANAGED-END: agent-guidance -->"""

        merge_guidance_file(tmp_path, "CLAUDE.md", new_content)

        claude_file = tmp_path / "CLAUDE.md"
        assert claude_file.exists()
        assert "Agent Guide" in claude_file.read_text()

    def test_preserves_content_before_and_after_asp_section(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that content before and after ASP section is preserved."""
        existing_content = """# Header Before ASP

Some content before ASP section.

<!-- ASP-MANAGED-START: agent-guidance -->
Old ASP content
<!-- ASP-MANAGED-END: agent-guidance -->

# Content After ASP

Some content after ASP section."""
        guidance_file = tmp_path / "GEMINI.md"
        guidance_file.write_text(existing_content)

        new_content = """<!-- ASP-MANAGED-START: agent-guidance -->
New ASP content
<!-- ASP-MANAGED-END: agent-guidance -->"""

        merge_guidance_file(tmp_path, "GEMINI.md", new_content)

        result = guidance_file.read_text()
        # Content before should be preserved
        assert "# Header Before ASP" in result
        assert "Some content before ASP section." in result
        # ASP section should be updated
        assert "New ASP content" in result
        assert "Old ASP content" not in result
        # Content after should be preserved
        assert "# Content After ASP" in result
        assert "Some content after ASP section." in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
