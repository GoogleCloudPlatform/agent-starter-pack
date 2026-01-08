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

import pytest

from agent_starter_pack.cli.utils.template import (
    copy_flat_structure_agent_files,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
