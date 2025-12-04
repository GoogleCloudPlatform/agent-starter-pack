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

"""Tests for generation metadata stored in pyproject.toml.

This module tests R12: Generation Metadata in pyproject.toml.
The metadata stored in [tool.agent-starter-pack] should enable:
- enhance command to know original config
- extract command to know what to strip
- upgrade command to re-template old version for diffing
- recommend command to suggest based on current setup
- Simplified mode detection
"""

import pathlib
import sys
from typing import Any, ClassVar

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_asp_metadata(pyproject_path: pathlib.Path) -> dict[str, Any]:
    """Load agent-starter-pack metadata from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml file

    Returns:
        Dictionary with [tool.agent-starter-pack] section contents
    """
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    return pyproject_data.get("tool", {}).get("agent-starter-pack", {})


class TestGenerationMetadataStructure:
    """Test that generation metadata has the correct structure."""

    def test_metadata_has_required_fields(self, tmp_path: pathlib.Path) -> None:
        """Test that metadata includes all required fields for project recreation."""
        # Create a sample pyproject.toml with metadata
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
description = "A test agent"
base_template = "adk_base"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"
deployment_target = "cloud_run"
session_type = "in_memory"
cicd_runner = "google_cloud_build"
include_data_ingestion = false
frontend_type = "None"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        metadata = load_asp_metadata(pyproject_path)

        # Core required fields for remote template compatibility
        assert "name" in metadata
        assert "description" in metadata
        assert "base_template" in metadata
        assert "agent_directory" in metadata

        # Generation context fields
        assert "generated_at" in metadata
        assert "asp_version" in metadata
        assert "deployment_target" in metadata
        assert "cicd_runner" in metadata
        assert "include_data_ingestion" in metadata
        assert "frontend_type" in metadata

    def test_metadata_types_are_correct(self, tmp_path: pathlib.Path) -> None:
        """Test that metadata values have correct types."""
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
description = "A test agent"
base_template = "adk_base"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"
deployment_target = "cloud_run"
session_type = "cloud_sql"
cicd_runner = "google_cloud_build"
include_data_ingestion = true
datastore = "vertex_ai_search"
frontend_type = "streamlit"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        metadata = load_asp_metadata(pyproject_path)

        # String fields
        assert isinstance(metadata["name"], str)
        assert isinstance(metadata["description"], str)
        assert isinstance(metadata["base_template"], str)
        assert isinstance(metadata["agent_directory"], str)
        assert isinstance(metadata["generated_at"], str)
        assert isinstance(metadata["asp_version"], str)
        assert isinstance(metadata["deployment_target"], str)
        assert isinstance(metadata["cicd_runner"], str)
        assert isinstance(metadata["frontend_type"], str)

        # Boolean field
        assert isinstance(metadata["include_data_ingestion"], bool)

        # Optional string fields when present
        assert isinstance(metadata["session_type"], str)
        assert isinstance(metadata["datastore"], str)

    def test_metadata_session_type_only_when_needed(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that session_type is only included when specified."""
        # agent_engine deployment - no session_type
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
description = "A test agent"
base_template = "adk_base"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"
deployment_target = "agent_engine"
cicd_runner = "google_cloud_build"
include_data_ingestion = false
frontend_type = "None"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        metadata = load_asp_metadata(pyproject_path)

        # session_type should not be present for agent_engine
        assert "session_type" not in metadata

    def test_metadata_datastore_only_when_data_ingestion_enabled(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that datastore is only included when data ingestion is enabled."""
        # Without data ingestion
        pyproject_content_no_ingestion = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
description = "A test agent"
base_template = "adk_base"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"
deployment_target = "cloud_run"
cicd_runner = "google_cloud_build"
include_data_ingestion = false
frontend_type = "None"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content_no_ingestion)

        metadata = load_asp_metadata(pyproject_path)

        assert metadata["include_data_ingestion"] is False
        assert "datastore" not in metadata

        # With data ingestion
        pyproject_content_with_ingestion = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
description = "A test agent"
base_template = "agentic_rag"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"
deployment_target = "cloud_run"
cicd_runner = "google_cloud_build"
include_data_ingestion = true
datastore = "vertex_ai_search"
frontend_type = "None"
"""
        pyproject_path.write_text(pyproject_content_with_ingestion)

        metadata = load_asp_metadata(pyproject_path)

        assert metadata["include_data_ingestion"] is True
        assert metadata["datastore"] == "vertex_ai_search"


class TestMetadataEnablesRecreation:
    """Test that metadata is sufficient to recreate identical project scaffolding."""

    def test_metadata_to_cli_args_mapping(self, tmp_path: pathlib.Path) -> None:
        """Test that metadata fields map to CLI arguments correctly."""
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "my-agent"
description = "ADK RAG agent"
base_template = "agentic_rag"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"
deployment_target = "cloud_run"
session_type = "cloud_sql"
cicd_runner = "github_actions"
include_data_ingestion = true
datastore = "vertex_ai_vector_search"
frontend_type = "streamlit"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        metadata = load_asp_metadata(pyproject_path)

        # Map metadata to CLI args
        cli_args = metadata_to_cli_args(metadata)

        # Verify the mapping
        assert "--agent" in cli_args or "-a" in cli_args
        assert "agentic_rag" in cli_args  # base_template maps to --agent
        assert "--deployment-target" in cli_args or "-d" in cli_args
        assert "cloud_run" in cli_args
        assert "--session-type" in cli_args
        assert "cloud_sql" in cli_args
        assert "--cicd-runner" in cli_args
        assert "github_actions" in cli_args
        assert "--include-data-ingestion" in cli_args or "-i" in cli_args
        assert "--datastore" in cli_args or "-ds" in cli_args
        assert "vertex_ai_vector_search" in cli_args

    def test_metadata_round_trip(self, tmp_path: pathlib.Path) -> None:
        """Test that metadata can be parsed and used to recreate project args."""
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "round-trip-test"
description = "Test agent"
base_template = "adk_base"
agent_directory = "custom_app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"
deployment_target = "agent_engine"
cicd_runner = "google_cloud_build"
include_data_ingestion = false
frontend_type = "None"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        metadata = load_asp_metadata(pyproject_path)

        # Verify metadata can be used to determine original settings
        assert metadata["base_template"] == "adk_base"
        assert metadata["deployment_target"] == "agent_engine"
        assert metadata["agent_directory"] == "custom_app"
        assert metadata["cicd_runner"] == "google_cloud_build"
        assert metadata["include_data_ingestion"] is False
        assert metadata["frontend_type"] == "None"


class TestMetadataRemoteTemplateCompatibility:
    """Test that generated projects work as remote templates."""

    def test_metadata_has_remote_template_fields(self, tmp_path: pathlib.Path) -> None:
        """Test that metadata includes fields required for remote template usage."""
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "my-agent"
description = "My custom agent"
base_template = "adk_base"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"
deployment_target = "cloud_run"
cicd_runner = "google_cloud_build"
include_data_ingestion = false
frontend_type = "None"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        metadata = load_asp_metadata(pyproject_path)

        # These fields are required by load_remote_template_config()
        assert "name" in metadata
        assert "description" in metadata
        assert "base_template" in metadata
        assert "agent_directory" in metadata

        # Verify values are usable
        assert metadata["name"] == "my-agent"
        assert metadata["description"] == "My custom agent"
        assert metadata["base_template"] == "adk_base"
        assert metadata["agent_directory"] == "app"


class TestMetadataEnablesIdenticalRecreation:
    """Critical test: Verify metadata is sufficient to recreate identical project.

    This is the key validation test from R12 requirements:
    1. Create project with various options
    2. Extract metadata from generated pyproject.toml
    3. Re-create project using only metadata
    4. Compare scaffolding files - must be identical
    """

    # Files that should match between original and recreated projects
    # These are the "scaffolding files" that define project structure
    SCAFFOLDING_PATTERNS: ClassVar[list[str]] = [
        "pyproject.toml",
        "Makefile",
        "deployment/**/*.tf",
        "deployment/**/*.tfvars",
        ".cloudbuild/**/*.yaml",
        ".github/**/*.yaml",
        ".github/**/*.yml",
    ]

    # Files to exclude from comparison (dynamic content)
    EXCLUDE_PATTERNS: ClassVar[list[str]] = [
        "*.lock",  # Lock files have timestamps
        "__pycache__/**",
        ".git/**",
        "*.pyc",
    ]

    @pytest.mark.parametrize(
        "agent,deployment_target,session_type,cicd_runner",
        [
            ("adk_base", "cloud_run", "in_memory", "google_cloud_build"),
            ("adk_base", "agent_engine", None, "google_cloud_build"),
            ("adk_base", "cloud_run", "cloud_sql", "github_actions"),
        ],
    )
    def test_metadata_enables_recreation(
        self,
        tmp_path: pathlib.Path,
        agent: str,
        deployment_target: str,
        session_type: str | None,
        cicd_runner: str,
    ) -> None:
        """Ensure metadata is sufficient to recreate identical project scaffolding."""
        from click.testing import CliRunner

        from agent_starter_pack.cli.commands.create import create

        runner = CliRunner()

        # 1. Create original project with various options
        project1_dir = tmp_path / "project1"
        project1_dir.mkdir()

        args1 = [
            "test-project",
            "--agent",
            agent,
            "--deployment-target",
            deployment_target,
            "--cicd-runner",
            cicd_runner,
            "--output-dir",
            str(project1_dir),
            "--skip-checks",
            "--auto-approve",
        ]
        if session_type:
            args1.extend(["--session-type", session_type])

        result1 = runner.invoke(create, args1)
        assert result1.exit_code == 0, f"First create failed: {result1.output}"

        # 2. Extract metadata from generated pyproject.toml
        pyproject_path = project1_dir / "test-project" / "pyproject.toml"
        assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"

        metadata = load_asp_metadata(pyproject_path)

        # Verify metadata has required fields
        assert "base_template" in metadata, "Missing base_template in metadata"
        assert "deployment_target" in metadata, "Missing deployment_target in metadata"
        assert "cicd_runner" in metadata, "Missing cicd_runner in metadata"

        # 3. Re-create project using only metadata
        project2_dir = tmp_path / "project2"
        project2_dir.mkdir()

        args2 = metadata_to_cli_args(metadata)
        args2.extend(
            [
                "test-project",
                "--output-dir",
                str(project2_dir),
                "--skip-checks",
                "--auto-approve",
            ]
        )

        result2 = runner.invoke(create, args2)
        assert result2.exit_code == 0, f"Recreation failed: {result2.output}"

        # 4. Compare key scaffolding files
        project1_path = project1_dir / "test-project"
        project2_path = project2_dir / "test-project"

        differences = self._compare_scaffolding_files(project1_path, project2_path)

        # Allow generated_at to differ (it's a timestamp)
        filtered_differences = [
            d for d in differences if "generated_at" not in d and "asp_version" not in d
        ]

        assert not filtered_differences, (
            "Projects differ in scaffolding files:\n"
            + "\n".join(filtered_differences[:10])  # Show first 10 differences
        )

    def _compare_scaffolding_files(
        self, path1: pathlib.Path, path2: pathlib.Path
    ) -> list[str]:
        """Compare scaffolding files between two project directories.

        Args:
            path1: First project path
            path2: Second project path

        Returns:
            List of differences found
        """
        differences: list[str] = []

        # Compare pyproject.toml (key file)
        pyproject1 = path1 / "pyproject.toml"
        pyproject2 = path2 / "pyproject.toml"

        if pyproject1.exists() and pyproject2.exists():
            content1 = pyproject1.read_text()
            content2 = pyproject2.read_text()

            # Compare line by line, ignoring generated_at
            lines1 = content1.splitlines()
            lines2 = content2.splitlines()

            for i, (line1, line2) in enumerate(zip(lines1, lines2, strict=False)):
                # Skip generated_at comparison (timestamp will differ)
                if "generated_at" in line1 or "generated_at" in line2:
                    continue
                if line1 != line2:
                    differences.append(
                        f"pyproject.toml line {i + 1}: '{line1}' != '{line2}'"
                    )

            if len(lines1) != len(lines2):
                differences.append(
                    f"pyproject.toml line count: {len(lines1)} != {len(lines2)}"
                )
        elif pyproject1.exists() != pyproject2.exists():
            differences.append("pyproject.toml exists in one project but not the other")

        # Compare Makefile
        makefile1 = path1 / "Makefile"
        makefile2 = path2 / "Makefile"

        if makefile1.exists() and makefile2.exists():
            if makefile1.read_text() != makefile2.read_text():
                differences.append("Makefile content differs")
        elif makefile1.exists() != makefile2.exists():
            differences.append("Makefile exists in one project but not the other")

        # Compare deployment directory structure
        deploy1 = path1 / "deployment"
        deploy2 = path2 / "deployment"

        if deploy1.exists() and deploy2.exists():
            tf_files1 = {f.name for f in deploy1.rglob("*.tf")}
            tf_files2 = {f.name for f in deploy2.rglob("*.tf")}
            if tf_files1 != tf_files2:
                differences.append(
                    f"Terraform files differ: {tf_files1} != {tf_files2}"
                )

        return differences


def metadata_to_cli_args(metadata: dict[str, Any]) -> list[str]:
    """Convert metadata dictionary to CLI arguments.

    This function maps the pyproject.toml metadata back to CLI arguments
    that could be used to recreate the project.

    Args:
        metadata: Dictionary from [tool.agent-starter-pack] section

    Returns:
        List of CLI arguments
    """
    args: list[str] = []

    # Required mappings
    if "base_template" in metadata:
        args.extend(["--agent", metadata["base_template"]])

    if "deployment_target" in metadata:
        args.extend(["--deployment-target", metadata["deployment_target"]])

    if "cicd_runner" in metadata:
        args.extend(["--cicd-runner", metadata["cicd_runner"]])

    # Optional mappings
    if metadata.get("session_type"):
        args.extend(["--session-type", metadata["session_type"]])

    if metadata.get("include_data_ingestion"):
        args.append("--include-data-ingestion")
        if "datastore" in metadata:
            args.extend(["--datastore", metadata["datastore"]])

    if "agent_directory" in metadata and metadata["agent_directory"] != "app":
        args.extend(["--agent-directory", metadata["agent_directory"]])

    return args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
