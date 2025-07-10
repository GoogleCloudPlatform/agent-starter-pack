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
    template_subdir = template_dir / ".template"
    template_subdir.mkdir(parents=True)
    (template_subdir / "templateconfig.yaml").write_text(
        f"base_template: {base_template}\nsettings:\n  requires_session: false\n"
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

    expected_template_path = fake_template_path / ".template"
    assert call_args[1] == expected_template_path
    assert call_kwargs["remote_template_path"] == fake_template_path.resolve()


def test_parse_agent_spec_ignores_local_prefix() -> None:
    """Test that parse_agent_spec returns None for local@ prefix."""
    spec = parse_agent_spec("local@/some/path")
    assert spec is None
