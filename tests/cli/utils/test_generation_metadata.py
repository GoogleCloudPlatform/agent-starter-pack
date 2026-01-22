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

from agent_starter_pack.cli.utils.generation_metadata import metadata_to_cli_args


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
base_template = "adk"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"

[tool.agent-starter-pack.create_params]
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

        # create_params section
        assert "create_params" in metadata
        create_params = metadata["create_params"]
        assert "deployment_target" in create_params
        assert "cicd_runner" in create_params
        assert "include_data_ingestion" in create_params
        assert "frontend_type" in create_params

    def test_metadata_types_are_correct(self, tmp_path: pathlib.Path) -> None:
        """Test that metadata values have correct types."""
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
description = "A test agent"
base_template = "adk"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"

[tool.agent-starter-pack.create_params]
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
        create_params = metadata["create_params"]

        # String fields in metadata
        assert isinstance(metadata["name"], str)
        assert isinstance(metadata["description"], str)
        assert isinstance(metadata["base_template"], str)
        assert isinstance(metadata["agent_directory"], str)
        assert isinstance(metadata["generated_at"], str)
        assert isinstance(metadata["asp_version"], str)

        # String fields in create_params
        assert isinstance(create_params["deployment_target"], str)
        assert isinstance(create_params["cicd_runner"], str)
        assert isinstance(create_params["frontend_type"], str)

        # Boolean field
        assert isinstance(create_params["include_data_ingestion"], bool)

        # Optional string fields when present
        assert isinstance(create_params["session_type"], str)
        assert isinstance(create_params["datastore"], str)

    def test_metadata_session_type_none_when_not_specified(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that session_type is 'none' when not specified."""
        # agent_engine deployment - session_type is "none"
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
description = "A test agent"
base_template = "adk"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"

[tool.agent-starter-pack.create_params]
deployment_target = "agent_engine"
session_type = "none"
cicd_runner = "google_cloud_build"
include_data_ingestion = false
datastore = "none"
frontend_type = "None"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        metadata = load_asp_metadata(pyproject_path)
        create_params = metadata["create_params"]

        # session_type should be "none" for agent_engine
        assert create_params["session_type"] == "none"

    def test_metadata_datastore_none_when_data_ingestion_disabled(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that datastore is 'none' when data ingestion is disabled."""
        # Without data ingestion - datastore is "none"
        pyproject_content_no_ingestion = """
[project]
name = "test-project"
version = "0.1.0"

[tool.agent-starter-pack]
name = "test-project"
description = "A test agent"
base_template = "adk"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"

[tool.agent-starter-pack.create_params]
deployment_target = "cloud_run"
session_type = "in_memory"
cicd_runner = "google_cloud_build"
include_data_ingestion = false
datastore = "none"
frontend_type = "None"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content_no_ingestion)

        metadata = load_asp_metadata(pyproject_path)
        create_params = metadata["create_params"]

        assert create_params["include_data_ingestion"] is False
        assert create_params["datastore"] == "none"

        # With data ingestion - datastore has actual value
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

[tool.agent-starter-pack.create_params]
deployment_target = "cloud_run"
session_type = "cloud_sql"
cicd_runner = "google_cloud_build"
include_data_ingestion = true
datastore = "vertex_ai_search"
frontend_type = "None"
"""
        pyproject_path.write_text(pyproject_content_with_ingestion)

        metadata = load_asp_metadata(pyproject_path)
        create_params = metadata["create_params"]

        assert create_params["include_data_ingestion"] is True
        assert create_params["datastore"] == "vertex_ai_search"


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

[tool.agent-starter-pack.create_params]
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
base_template = "adk"
agent_directory = "custom_app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"

[tool.agent-starter-pack.create_params]
deployment_target = "agent_engine"
cicd_runner = "google_cloud_build"
include_data_ingestion = false
frontend_type = "None"
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        metadata = load_asp_metadata(pyproject_path)
        create_params = metadata["create_params"]

        # Verify metadata can be used to determine original settings
        assert metadata["base_template"] == "adk"
        assert metadata["agent_directory"] == "custom_app"
        assert create_params["deployment_target"] == "agent_engine"
        assert create_params["cicd_runner"] == "google_cloud_build"
        assert create_params["include_data_ingestion"] is False
        assert create_params["frontend_type"] == "None"


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
base_template = "adk"
agent_directory = "app"
generated_at = "2025-12-04T15:35:34.021638+00:00"
asp_version = "0.25.0"

[tool.agent-starter-pack.create_params]
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
        assert metadata["base_template"] == "adk"
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
            ("adk", "cloud_run", "in_memory", "google_cloud_build"),
            ("adk", "agent_engine", None, "google_cloud_build"),
            ("adk", "cloud_run", "cloud_sql", "github_actions"),
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
        assert "create_params" in metadata, "Missing create_params in metadata"
        create_params = metadata["create_params"]
        assert "deployment_target" in create_params, (
            "Missing deployment_target in create_params"
        )
        assert "cicd_runner" in create_params, "Missing cicd_runner in create_params"

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

        Iterates through all SCAFFOLDING_PATTERNS and compares file contents.

        Args:
            path1: First project path
            path2: Second project path

        Returns:
            List of differences found
        """
        differences: list[str] = []

        for pattern in self.SCAFFOLDING_PATTERNS:
            files1 = sorted(path1.glob(pattern))
            files2 = sorted(path2.glob(pattern))

            rel_files1 = {f.relative_to(path1) for f in files1}
            rel_files2 = {f.relative_to(path2) for f in files2}

            if rel_files1 != rel_files2:
                mismatch = rel_files1.symmetric_difference(rel_files2)
                differences.append(
                    f"File list mismatch for pattern '{pattern}': {mismatch}"
                )
                continue

            for file1 in files1:
                file2 = path2 / file1.relative_to(path1)
                content1 = file1.read_text()
                content2 = file2.read_text()

                # Special handling for pyproject.toml to ignore dynamic fields
                if file1.name == "pyproject.toml":
                    differences.extend(
                        self._compare_pyproject_toml(file1, file2, path1)
                    )
                elif content1 != content2:
                    differences.append(
                        f"File content differs for {file1.relative_to(path1)}"
                    )

        return differences

    def _compare_pyproject_toml(
        self,
        file1: pathlib.Path,
        file2: pathlib.Path,
        base_path: pathlib.Path,
    ) -> list[str]:
        """Compare pyproject.toml files using TOML parsing.

        Ignores dynamic fields like generated_at and asp_version.

        Args:
            file1: First pyproject.toml path
            file2: Second pyproject.toml path
            base_path: Base path for relative path display

        Returns:
            List of differences found
        """
        differences: list[str] = []

        with open(file1, "rb") as f1, open(file2, "rb") as f2:
            data1 = tomllib.load(f1)
            data2 = tomllib.load(f2)

        # Pop keys that are expected to differ before comparison
        for data in [data1, data2]:
            if asp_metadata := data.get("tool", {}).get("agent-starter-pack"):
                asp_metadata.pop("generated_at", None)
                asp_metadata.pop("asp_version", None)

        if data1 != data2:
            differences.append(
                f"pyproject.toml content differs (ignoring dynamic fields): "
                f"{file1.relative_to(base_path)}"
            )

        return differences


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
