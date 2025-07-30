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
from unittest.mock import Mock, patch

from click.testing import CliRunner

from src.cli.commands.create import create
from src.cli.utils.remote_template import parse_agent_spec


def create_fake_template(
    tmp_path: pathlib.Path, base_template: str = "adk_base"
) -> pathlib.Path:
    template_dir = tmp_path / "my-local-template"
    template_dir.mkdir(parents=True)
    (template_dir / "pyproject.toml").write_text(
        f"""[tool.agent-starter-pack]
base_template = "{base_template}"

[tool.agent-starter-pack.settings]
requires_session = false
"""
    )
    return template_dir


@patch("src.cli.commands.create.setup_gcp_environment")
@patch("src.cli.commands.create.process_template")
@patch("src.cli.commands.create.replace_region_in_files")
def test_create_with_local_path(
    mock_replace_region: Mock,
    mock_process_template: Mock,
    mock_setup_gcp: Mock,
    tmp_path: pathlib.Path,
) -> None:
    """Test the create command with a local@ path for the agent."""
    runner = CliRunner()
    fake_template_path = create_fake_template(tmp_path)
    mock_setup_gcp.return_value = {"project": "test-project"}

    result = runner.invoke(
        create,
        [
            "my-test-project",
            "--agent",
            f"local@{fake_template_path}",
            "--skip-checks",
            "--auto-approve",
            "--deployment-target",
            "agent_engine",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "Using local template:" in result.output

    mock_process_template.assert_called_once()
    call_args, call_kwargs = mock_process_template.call_args

    # The template path should now be inside a temporary directory
    actual_template_path = call_args[1]
    assert "asp_local_template_" in str(actual_template_path)
    assert actual_template_path.name == ".template"

    # The remote_template_path should also be the temporary directory
    actual_remote_path = call_kwargs["remote_template_path"]
    assert "asp_local_template_" in str(actual_remote_path)
    assert actual_remote_path.name == "my-local-template"


@patch("src.cli.commands.create.setup_gcp_environment")
@patch("src.cli.commands.create.process_template")
@patch("src.cli.commands.create.replace_region_in_files")
def test_create_with_in_folder_flag(
    mock_replace_region: Mock,
    mock_process_template: Mock,
    mock_setup_gcp: Mock,
    tmp_path: pathlib.Path,
) -> None:
    """Test the create command with --in-folder flag."""
    runner = CliRunner()
    fake_template_path = create_fake_template(tmp_path)
    mock_setup_gcp.return_value = {"project": "test-project"}

    # Create a fake current directory
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    result = runner.invoke(
        create,
        [
            "my-test-project",
            "--agent",
            f"local@{fake_template_path}",
            "--skip-checks",
            "--auto-approve",
            "--deployment-target",
            "agent_engine",
            "--in-folder",
            "--output-dir",
            str(work_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "Using local template:" in result.output

    mock_process_template.assert_called_once()
    _, call_kwargs = mock_process_template.call_args

    # Verify that in_folder was passed as True
    assert call_kwargs["in_folder"] is True

    # The output_dir should be the work directory for in-folder mode
    assert call_kwargs["output_dir"] == work_dir


@patch("src.cli.commands.create.setup_gcp_environment")
@patch("src.cli.commands.create.process_template")
@patch("src.cli.commands.create.replace_region_in_files")
def test_create_with_in_folder_is_permissive(
    mock_replace_region: Mock,
    mock_process_template: Mock,
    mock_setup_gcp: Mock,
    tmp_path: pathlib.Path,
) -> None:
    """Test that --in-folder is permissive and doesn't warn about existing files."""
    runner = CliRunner()
    fake_template_path = create_fake_template(tmp_path)
    mock_setup_gcp.return_value = {"project": "test-project"}

    # Create a directory with existing files
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "existing_file.py").write_text("# existing content")
    (work_dir / ".gitignore").write_text("# allowed file")

    result = runner.invoke(
        create,
        [
            "my-test-project",
            "--agent",
            f"local@{fake_template_path}",
            "--skip-checks",
            "--auto-approve",
            "--deployment-target",
            "agent_engine",
            "--in-folder",
            "--output-dir",
            str(work_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    # Should not show warnings about existing files in permissive in-folder mode
    assert "Warning: Directory" not in result.output
    assert "contains files that may be overwritten" not in result.output

    mock_process_template.assert_called_once()


def test_parse_agent_spec_ignores_local_prefix() -> None:
    """Test that parse_agent_spec returns None for local@ prefix."""
    spec = parse_agent_spec("local@/some/path")
    assert spec is None


def test_readme_conflict_handling_logic(tmp_path: pathlib.Path) -> None:
    """Test the basic README conflict detection logic (simplified version).

    Note: This tests the conflict detection pattern, but the actual process_template
    function now uses base template README instead of templated README when conflicts occur.
    """
    import shutil

    # Set up directories
    final_destination = tmp_path / "destination"
    final_destination.mkdir(parents=True)
    generated_project_dir = tmp_path / "generated"
    generated_project_dir.mkdir(parents=True)

    # Create existing README in destination
    existing_readme_content = (
        "# Existing Project\n\nThis is my existing README content."
    )
    (final_destination / "README.md").write_text(existing_readme_content)

    # Create templated README in generated project
    templated_readme_content = "# Test Project\n\nThis is the templated README content."
    (generated_project_dir / "README.md").write_text(templated_readme_content)

    # Also create a non-conflicting file
    (generated_project_dir / "other_file.py").write_text("# Other file content")

    # Simulate the in-folder copying logic from process_template
    for item in generated_project_dir.iterdir():
        dest_item = final_destination / item.name

        # Special handling for README files - rename templated README if conflict exists
        if (
            item.name.lower().startswith("readme")
            and (final_destination / item.name).exists()
        ):
            # The existing README stays, save the templated one with a different name
            base_name = item.stem
            extension = item.suffix
            dest_item = final_destination / f"starter_pack_{base_name}{extension}"

        if item.is_dir():
            if dest_item.exists():
                shutil.rmtree(dest_item)
            shutil.copytree(item, dest_item, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest_item)

    # Verify results
    original_readme = final_destination / "README.md"
    templated_readme = final_destination / "starter_pack_README.md"
    other_file = final_destination / "other_file.py"

    # Original README should be preserved with original content
    assert original_readme.exists()
    assert original_readme.read_text() == existing_readme_content

    # Templated README should be saved with new name
    assert templated_readme.exists()
    assert templated_readme.read_text() == templated_readme_content

    # Other files should copy normally
    assert other_file.exists()
    assert other_file.read_text() == "# Other file content"
