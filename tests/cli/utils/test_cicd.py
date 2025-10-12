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

"""Tests for CI/CD utility functions."""

from unittest.mock import MagicMock, patch

import pytest
from cli.utils.cicd import ProjectConfig, print_cicd_summary, run_command


@pytest.fixture
def mock_console() -> MagicMock:
    """Mock console for testing output"""
    with patch("cli.utils.cicd.console") as mock:
        yield mock


@pytest.fixture
def mock_run_command() -> MagicMock:
    """Mock run_command function"""
    with patch("agent_starter_pack.cli.utils.cicd.run_command") as mock:
        yield mock


def test_project_config() -> None:
    """Test ProjectConfig initialization with minimal required fields"""
    config = ProjectConfig(
        staging_project_id="test-staging",
        prod_project_id="test-prod",
        cicd_project_id="test-cicd",
        agent="test-agent",
        deployment_target="cloud-run",
        repository_name="test-repo",
        repository_owner="test-owner",
        dev_project_id="test-dev",
    )

    assert config.dev_project_id == "test-dev"
    assert config.region == "us-central1"  # default value
    assert config.git_provider == "github"  # default value


def test_print_cicd_summary(mock_console: MagicMock) -> None:
    """Test CICD summary printing"""
    config = ProjectConfig(
        staging_project_id="test-staging",
        prod_project_id="test-prod",
        cicd_project_id="test-cicd",
        agent="test-agent",
        deployment_target="cloud-run",
        repository_name="test-repo",
        repository_owner="test-owner",
        dev_project_id="test-dev",
    )

    print_cicd_summary(
        config=config,
        github_username="test-user",
        repo_url="https://github.com/test-user/test-repo",
        cloud_build_url="https://console.cloud.google.com/cloud-build/builds?project=test-cicd",
    )

    # Verify specific expected messages were printed
    assert mock_console.print.call_count > 0


def test_run_command(capsys: pytest.CaptureFixture) -> None:
    """Test run_command output formatting"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="test output", stderr="")

        result = run_command(["test", "command"], capture_output=True)

        captured = capsys.readouterr()
        assert "🔄 Running command: test command" in captured.out
        assert result.stdout == "test output"
