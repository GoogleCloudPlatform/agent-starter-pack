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

"""Tests for upgrade utilities."""

import pathlib
import tempfile

import pytest

from agent_starter_pack.cli.utils.upgrade import (
    FileCompareResult,
    categorize_file,
    collect_all_files,
    group_results_by_action,
    merge_pyproject_dependencies,
    three_way_compare,
    write_merged_dependencies,
)


class TestCategorizeFile:
    """Tests for file categorization."""

    def test_agent_code_patterns(self) -> None:
        """Test that agent code files are correctly categorized."""
        assert categorize_file("app/agent.py") == "agent_code"
        assert categorize_file("app/tools/search.py") == "agent_code"
        assert categorize_file("app/prompts/main.py") == "agent_code"

    def test_go_agent_code_patterns(self) -> None:
        """Test that Go agent code files are correctly categorized."""
        assert categorize_file("agent/agent.go", "agent") == "agent_code"
        assert categorize_file("agent/tools/search.go", "agent") == "agent_code"
        assert categorize_file("agent/handlers/main.go", "agent") == "agent_code"
        # Default app directory
        assert categorize_file("app/agent.go") == "agent_code"
        assert categorize_file("app/utils/helper.go") == "agent_code"

    def test_config_files(self) -> None:
        """Test that config files are correctly categorized."""
        assert categorize_file("deployment/vars/dev.tfvars") == "config_files"
        assert categorize_file(".env") == "config_files"

    def test_dependencies(self) -> None:
        """Test that pyproject.toml is categorized as dependencies."""
        assert categorize_file("pyproject.toml") == "dependencies"

    def test_go_dependencies(self) -> None:
        """Test that Go dependency files are correctly categorized."""
        assert categorize_file("go.mod") == "dependencies"
        assert categorize_file("go.sum") == "dependencies"
        assert categorize_file(".asp.toml") == "dependencies"

    def test_scaffolding_files(self) -> None:
        """Test that scaffolding files are correctly categorized."""
        assert categorize_file("deployment/terraform/main.tf") == "scaffolding"
        assert categorize_file(".github/workflows/deploy.yaml") == "scaffolding"
        assert categorize_file("Makefile") == "scaffolding"
        assert categorize_file("tests/conftest.py") == "scaffolding"

    def test_custom_agent_directory(self) -> None:
        """Test categorization with custom agent directory."""
        assert categorize_file("my_agent/agent.py", "my_agent") == "agent_code"
        assert categorize_file("my_agent/tools/custom.py", "my_agent") == "agent_code"
        # Default app directory should not match
        assert categorize_file("app/agent.py", "my_agent") == "scaffolding"

    def test_custom_agent_directory_go(self) -> None:
        """Test categorization with custom agent directory for Go."""
        assert categorize_file("my_agent/agent.go", "my_agent") == "agent_code"
        assert categorize_file("my_agent/handlers/api.go", "my_agent") == "agent_code"
        # Default agent directory should not match
        assert categorize_file("agent/agent.go", "my_agent") == "scaffolding"


class TestThreeWayCompare:
    """Tests for 3-way file comparison."""

    @pytest.fixture
    def temp_dirs(self) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp:
            project = pathlib.Path(temp) / "project"
            old_template = pathlib.Path(temp) / "old"
            new_template = pathlib.Path(temp) / "new"

            project.mkdir()
            old_template.mkdir()
            new_template.mkdir()

            yield project, old_template, new_template

    def test_auto_update_unchanged_by_user(
        self, temp_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test auto-update when user didn't modify file."""
        project, old_template, new_template = temp_dirs

        # Create same file in project and old template
        (project / "test.txt").write_text("old content")
        (old_template / "test.txt").write_text("old content")
        # New template has updated content
        (new_template / "test.txt").write_text("new content")

        result = three_way_compare("test.txt", project, old_template, new_template)

        assert result.action == "auto_update"
        assert "didn't modify" in result.reason.lower()

    def test_preserve_asp_unchanged(
        self, temp_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test preserve when ASP didn't change file."""
        project, old_template, new_template = temp_dirs

        # User modified file
        (project / "test.txt").write_text("user modified")
        # Old and new template have same content
        (old_template / "test.txt").write_text("template content")
        (new_template / "test.txt").write_text("template content")

        result = three_way_compare("test.txt", project, old_template, new_template)

        assert result.action == "preserve"
        assert "asp didn't change" in result.reason.lower()

    def test_conflict_both_changed(
        self, temp_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test conflict when both user and ASP changed file."""
        project, old_template, new_template = temp_dirs

        # All three have different content
        (project / "test.txt").write_text("user content")
        (old_template / "test.txt").write_text("old content")
        (new_template / "test.txt").write_text("new content")

        result = three_way_compare("test.txt", project, old_template, new_template)

        assert result.action == "conflict"
        assert "both" in result.reason.lower()

    def test_new_file_in_asp(
        self, temp_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test detection of new file in ASP."""
        project, old_template, new_template = temp_dirs

        # Only exists in new template
        (new_template / "new_file.txt").write_text("new content")

        result = three_way_compare("new_file.txt", project, old_template, new_template)

        assert result.action == "new"
        assert "new file" in result.reason.lower()

    def test_removed_file_in_asp_user_unchanged(
        self, temp_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test detection of removed file when user didn't modify."""
        project, old_template, new_template = temp_dirs

        # File exists in project and old template, not in new
        (project / "old_file.txt").write_text("same content")
        (old_template / "old_file.txt").write_text("same content")

        result = three_way_compare("old_file.txt", project, old_template, new_template)

        assert result.action == "removed"

    def test_removed_file_in_asp_user_modified(
        self, temp_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test conflict when removed file was modified by user."""
        project, old_template, new_template = temp_dirs

        # User modified a file that was removed in new template
        (project / "old_file.txt").write_text("user modified")
        (old_template / "old_file.txt").write_text("original content")

        result = three_way_compare("old_file.txt", project, old_template, new_template)

        assert result.action == "conflict"

    def test_skip_agent_code(
        self, temp_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test that agent code is always skipped."""
        project, old_template, new_template = temp_dirs

        (project / "app").mkdir()
        (project / "app/agent.py").write_text("user agent")
        (old_template / "app").mkdir()
        (old_template / "app/agent.py").write_text("old agent")
        (new_template / "app").mkdir()
        (new_template / "app/agent.py").write_text("new agent")

        result = three_way_compare("app/agent.py", project, old_template, new_template)

        assert result.action == "skip"
        assert result.category == "agent_code"

    def test_skip_config_files(
        self, temp_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test that config files are always skipped."""
        project, old_template, new_template = temp_dirs

        (project / ".env").write_text("SECRET=user")
        (old_template / ".env").write_text("SECRET=old")
        (new_template / ".env").write_text("SECRET=new")

        result = three_way_compare(".env", project, old_template, new_template)

        assert result.action == "skip"
        assert result.category == "config_files"


class TestCollectAllFiles:
    """Tests for collecting files from directories."""

    def test_collects_from_all_dirs(self) -> None:
        """Test that files are collected from all three directories."""
        with tempfile.TemporaryDirectory() as temp:
            project = pathlib.Path(temp) / "project"
            old_template = pathlib.Path(temp) / "old"
            new_template = pathlib.Path(temp) / "new"

            project.mkdir()
            old_template.mkdir()
            new_template.mkdir()

            (project / "project_file.txt").write_text("content")
            (old_template / "old_file.txt").write_text("content")
            (new_template / "new_file.txt").write_text("content")

            files = collect_all_files(project, old_template, new_template)

            assert "project_file.txt" in files
            assert "old_file.txt" in files
            assert "new_file.txt" in files

    def test_excludes_patterns(self) -> None:
        """Test that excluded patterns are not collected."""
        with tempfile.TemporaryDirectory() as temp:
            project = pathlib.Path(temp) / "project"
            project.mkdir()

            (project / ".git").mkdir()
            (project / ".git/config").write_text("content")
            (project / "real_file.txt").write_text("content")

            files = collect_all_files(
                project, project, project, exclude_patterns=[".git/**"]
            )

            assert ".git/config" not in files
            assert "real_file.txt" in files


class TestGroupResultsByAction:
    """Tests for grouping results by action."""

    def test_groups_correctly(self) -> None:
        """Test that results are grouped by action."""
        results = [
            FileCompareResult("file1.txt", "scaffolding", "auto_update", "reason"),
            FileCompareResult("file2.txt", "scaffolding", "preserve", "reason"),
            FileCompareResult("file3.txt", "scaffolding", "conflict", "reason"),
            FileCompareResult("file4.txt", "scaffolding", "auto_update", "reason"),
        ]

        groups = group_results_by_action(results)

        assert len(groups["auto_update"]) == 2
        assert len(groups["preserve"]) == 1
        assert len(groups["conflict"]) == 1
        assert len(groups["skip"]) == 0


class TestMergePyprojectDependencies:
    """Tests for dependency merging."""

    @pytest.fixture
    def pyproject_dirs(self) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
        """Create temporary directories with pyproject.toml files."""
        with tempfile.TemporaryDirectory() as temp:
            current = pathlib.Path(temp) / "current"
            old_template = pathlib.Path(temp) / "old"
            new_template = pathlib.Path(temp) / "new"

            current.mkdir()
            old_template.mkdir()
            new_template.mkdir()

            yield current, old_template, new_template

    def _write_pyproject(self, path: pathlib.Path, deps: list[str]) -> None:
        """Write a pyproject.toml with the given dependencies."""
        deps_str = ", ".join(f'"{d}"' for d in deps)
        content = f"""
[project]
name = "test-project"
dependencies = [{deps_str}]
"""
        (path / "pyproject.toml").write_text(content)

    def test_updated_dependency(
        self, pyproject_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test detection of updated dependency."""
        current, old_template, new_template = pyproject_dirs

        self._write_pyproject(current, ["google-adk>=0.2.0"])
        self._write_pyproject(old_template, ["google-adk>=0.2.0"])
        self._write_pyproject(new_template, ["google-adk>=0.3.0"])

        result = merge_pyproject_dependencies(
            current / "pyproject.toml",
            old_template / "pyproject.toml",
            new_template / "pyproject.toml",
        )

        updated = [c for c in result.changes if c.change_type == "updated"]
        assert len(updated) == 1
        assert updated[0].name == "google-adk"

    def test_user_added_dependency_kept(
        self, pyproject_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test that user-added dependencies are preserved."""
        current, old_template, new_template = pyproject_dirs

        self._write_pyproject(current, ["google-adk>=0.2.0", "my-custom-lib>=1.0.0"])
        self._write_pyproject(old_template, ["google-adk>=0.2.0"])
        self._write_pyproject(new_template, ["google-adk>=0.3.0"])

        result = merge_pyproject_dependencies(
            current / "pyproject.toml",
            old_template / "pyproject.toml",
            new_template / "pyproject.toml",
        )

        kept = [c for c in result.changes if c.change_type == "kept"]
        assert len(kept) == 1
        assert kept[0].name == "my-custom-lib"

        # Check merged deps contains both
        merged_names = [d.split(">")[0].split("=")[0] for d in result.merged_deps]
        assert "google-adk" in merged_names
        assert "my-custom-lib" in merged_names

    def test_new_asp_dependency(
        self, pyproject_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test detection of new ASP dependency."""
        current, old_template, new_template = pyproject_dirs

        self._write_pyproject(current, ["google-adk>=0.2.0"])
        self._write_pyproject(old_template, ["google-adk>=0.2.0"])
        self._write_pyproject(new_template, ["google-adk>=0.3.0", "new-dep>=1.0.0"])

        result = merge_pyproject_dependencies(
            current / "pyproject.toml",
            old_template / "pyproject.toml",
            new_template / "pyproject.toml",
        )

        added = [c for c in result.changes if c.change_type == "added"]
        assert len(added) == 1
        assert added[0].name == "new-dep"

    def test_removed_asp_dependency(
        self, pyproject_dirs: tuple[pathlib.Path, pathlib.Path, pathlib.Path]
    ) -> None:
        """Test detection of removed ASP dependency."""
        current, old_template, new_template = pyproject_dirs

        self._write_pyproject(current, ["google-adk>=0.2.0", "old-dep>=1.0.0"])
        self._write_pyproject(old_template, ["google-adk>=0.2.0", "old-dep>=1.0.0"])
        self._write_pyproject(new_template, ["google-adk>=0.3.0"])

        result = merge_pyproject_dependencies(
            current / "pyproject.toml",
            old_template / "pyproject.toml",
            new_template / "pyproject.toml",
        )

        removed = [c for c in result.changes if c.change_type == "removed"]
        assert len(removed) == 1
        assert removed[0].name == "old-dep"


class TestWriteMergedDependencies:
    """Tests for writing merged dependencies back to pyproject.toml."""

    def test_writes_dependencies_correctly(self, tmp_path: pathlib.Path) -> None:
        """Test that dependencies are written correctly to pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
dependencies = [
    "old-dep>=1.0.0",
]
"""
        )

        merged_deps = ["google-adk>=0.3.0", "my-custom-lib>=1.0.0"]
        result = write_merged_dependencies(pyproject, merged_deps)

        assert result is True
        content = pyproject.read_text()
        assert '"google-adk>=0.3.0"' in content
        assert '"my-custom-lib>=1.0.0"' in content
        assert "old-dep" not in content

    def test_handles_empty_dependencies(self, tmp_path: pathlib.Path) -> None:
        """Test writing empty dependencies list."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
dependencies = ["some-dep>=1.0.0"]
"""
        )

        result = write_merged_dependencies(pyproject, [])

        assert result is True
        content = pyproject.read_text()
        assert "dependencies = []" in content

    def test_returns_false_for_missing_file(self, tmp_path: pathlib.Path) -> None:
        """Test that missing file returns False."""
        pyproject = tmp_path / "nonexistent.toml"

        result = write_merged_dependencies(pyproject, ["dep>=1.0.0"])

        assert result is False


class TestCollectAllFilesDeepExclusion:
    """Tests for ** glob pattern exclusions in collect_all_files."""

    def test_excludes_deeply_nested_git_files(self) -> None:
        """Test that .git/** excludes deeply nested files."""
        with tempfile.TemporaryDirectory() as temp:
            project = pathlib.Path(temp) / "project"
            project.mkdir()

            # Create deeply nested .git structure
            git_dir = project / ".git" / "objects" / "pack"
            git_dir.mkdir(parents=True)
            (git_dir / "pack-123.idx").write_text("content")
            (project / ".git" / "config").write_text("content")
            (project / ".git" / "HEAD").write_text("ref: refs/heads/main")

            # Create a real file
            (project / "README.md").write_text("content")

            files = collect_all_files(
                project, project, project, exclude_patterns=[".git/**"]
            )

            assert ".git/config" not in files
            assert ".git/HEAD" not in files
            assert ".git/objects/pack/pack-123.idx" not in files
            assert "README.md" in files

    def test_excludes_venv_deeply_nested(self) -> None:
        """Test that .venv/** excludes deeply nested virtual env files."""
        with tempfile.TemporaryDirectory() as temp:
            project = pathlib.Path(temp) / "project"
            project.mkdir()

            # Create nested venv structure
            venv_lib = project / ".venv" / "lib" / "python3.12" / "site-packages"
            venv_lib.mkdir(parents=True)
            (venv_lib / "some_package" / "__init__.py").parent.mkdir()
            (venv_lib / "some_package" / "__init__.py").write_text("content")

            # Create a real file
            (project / "main.py").write_text("content")

            files = collect_all_files(
                project, project, project, exclude_patterns=[".venv/**"]
            )

            assert (
                ".venv/lib/python3.12/site-packages/some_package/__init__.py"
                not in files
            )
            assert "main.py" in files


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
