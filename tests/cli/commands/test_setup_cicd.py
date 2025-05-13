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

"""Tests for setup-cicd command."""

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
from click.testing import CliRunner

from cli.utils.cicd import ProjectConfig
from src.cli.commands.setup_cicd import (
    display_intro_message,
    display_production_note,
    setup_cicd,
    setup_git_repository,
    update_build_triggers,
)


@pytest.fixture
def mock_cwd() -> MagicMock:
    """Mock for current working directory"""
    with patch("pathlib.Path.cwd") as mock:
        mock.return_value = Path("/mock/cwd")
        yield mock


@pytest.fixture
def mock_verify_credentials() -> MagicMock:
    """Mock credentials verification"""
    with patch("src.cli.commands.setup_cicd.verify_credentials") as mock:
        mock.return_value = {"account": "test@example.com", "project": "test-project"}
        yield mock


@pytest.fixture
def mock_e2e_deployment() -> MagicMock:
    """Mock E2EDeployment class"""
    with patch("src.cli.commands.setup_cicd.E2EDeployment") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_terraform_files() -> None:
    """Mock terraform file operations"""
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.glob") as mock_glob,
        patch("builtins.open", mock_open()),
        patch("shutil.copy2"),
    ):
        mock_exists.return_value = True
        mock_glob.return_value = [Path("mock_file.tf")]
        yield


@pytest.fixture
def mock_path() -> MagicMock:
    """Mock Path operations"""
    with patch("pathlib.Path") as mock:
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = True
        mock_path.open = MagicMock()
        mock.return_value = mock_path
        yield mock


@pytest.fixture
def mock_template_files() -> None:
    """Mock template files existence and copying"""
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.is_file") as mock_is_file,
        patch("pathlib.Path.open", mock_open()),
        patch("shutil.copy2"),
        patch("pathlib.Path.parent", return_value=Path("/mock/parent")),
        patch("pathlib.Path.glob", return_value=[Path("mock_file.tf")]),
    ):
        mock_exists.return_value = True
        mock_is_file.return_value = True
        yield


@pytest.fixture
def tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Provide a temporary directory path"""
    return tmp_path_factory.mktemp("test")


@pytest.fixture
def mock_tempfile(tmp_path: Path) -> MagicMock:
    """Mock tempfile for testing"""
    with patch("tempfile.NamedTemporaryFile") as mock:
        temp_file = tmp_path / "temp_file"
        mock.return_value.__enter__.return_value.name = str(temp_file)
        yield mock


@pytest.fixture
def mock_console() -> MagicMock:
    """Mock console output"""
    with patch("src.cli.commands.setup_cicd.console") as mock:
        yield mock


@pytest.fixture
def mock_run_command() -> MagicMock:
    """Mock command execution"""
    with patch("src.cli.commands.setup_cicd.run_command") as mock:
        # Mock GitHub username query
        mock.return_value = MagicMock(stdout="test-user", returncode=0)
        yield mock


@pytest.fixture
def mock_setup_terraform_backend() -> MagicMock:
    """Mock Terraform backend setup"""
    with patch("src.cli.commands.setup_cicd.setup_terraform_backend") as mock:
        yield mock


@pytest.fixture
def mock_create_github_connection() -> MagicMock:
    """Mock GitHub connection creation"""
    with patch("src.cli.commands.setup_cicd.create_github_connection") as mock:
        yield mock


class TestSetupCICD:
    """Test class for setup-cicd command"""

    def test_display_intro_message(self, mock_console: MagicMock) -> None:
        """Test intro message display"""
        display_intro_message()
        mock_console.print.assert_any_call(
            "\n⚠️  WARNING: The setup-cicd command is experimental and may have unexpected behavior.",
            style="bold yellow",
        )

    def test_display_production_note(self, mock_console: MagicMock) -> None:
        """Test production note display"""
        display_production_note()
        mock_console.print.assert_any_call("\n⚡ Setup Note:", style="bold yellow")

    def test_setup_git_repository(
        self, mock_run_command: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test Git repository setup"""
        config = ProjectConfig(
            dev_project_id="test-dev",
            staging_project_id="test-staging",
            prod_project_id="test-prod",
            cicd_project_id="test-cicd",
            agent="test-agent",
            deployment_target="cloud-run",
            repository_name="test-repo",
        )

        # Test when .git doesn't exist
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            # Configure mock_run_command behavior
            mock_run_command.side_effect = [
                MagicMock(returncode=0),  # git init
                MagicMock(stdout="test-user", returncode=0),  # gh api user
                subprocess.CalledProcessError(
                    1, ["git", "remote", "get-url"]
                ),  # git remote get-url fails
                MagicMock(returncode=0),  # git remote add
            ]

            github_username = setup_git_repository(config)

            assert github_username == "test-user"

            # Verify git init was called
            mock_run_command.assert_any_call(["git", "init", "-b", "main"])

            # Verify GitHub username was fetched
            mock_run_command.assert_any_call(
                ["gh", "api", "user", "--jq", ".login"], capture_output=True
            )

            # Verify remote was added
            mock_run_command.assert_any_call(
                [
                    "git",
                    "remote",
                    "add",
                    "origin",
                    "https://github.com/test-user/test-repo.git",
                ]
            )

        # Test when .git exists and remote is configured
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True

            mock_run_command.reset_mock()
            mock_run_command.side_effect = [
                MagicMock(stdout="test-user", returncode=0),  # gh api user
                MagicMock(returncode=0),  # git remote get-url succeeds
            ]

            github_username = setup_git_repository(config)

            assert github_username == "test-user"

            # Verify git init was not called
            assert not any(
                "git init" in str(call) for call in mock_run_command.call_args_list
            )

            # Verify remote was not added
            assert not any(
                "git remote add" in str(call)
                for call in mock_run_command.call_args_list
            )

    def test_update_build_triggers(self, tmp_path: Path) -> None:
        """Test build triggers configuration update"""
        # Create a temporary directory structure
        tf_dir = tmp_path / "deployment" / "terraform"
        tf_dir.mkdir(parents=True)

        # Create test build_triggers.tf with initial content
        build_triggers_path = tf_dir / "build_triggers.tf"
        initial_content = """
        depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
        repository = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"
        """
        build_triggers_path.write_text(initial_content)

        # Run the function
        update_build_triggers(tf_dir)

        # Read the modified content
        modified_content = build_triggers_path.read_text()

        # Verify the changes
        assert "google_cloudbuildv2_repository.repo" in modified_content
        assert (
            "depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services, google_cloudbuildv2_repository.repo]"
            in modified_content
        )

    def test_setup_cicd_basic(
        self,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
        mock_run_command: MagicMock,
        mock_setup_terraform_backend: MagicMock,
        mock_create_github_connection: MagicMock,
        mock_template_files: None,
    ) -> None:
        """Test basic setup with minimal required arguments"""
        runner = CliRunner()

        # Set up mock responses for different command calls
        def run_command_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            command = args[0]
            mock_response = MagicMock()

            print(f"\nMocked command: {command}")

            # Mock gcloud services list
            if "gcloud" in command and "services" in command and "list" in command:
                mock_response.stdout = "[]"
                mock_response.returncode = 0
                print("Mocking gcloud services list")
            # Mock GitHub username API call
            elif "gh" in command and "api" in command and "user" in command:
                mock_response.stdout = "test-user"
                mock_response.returncode = 0
                print("Mocking GitHub username API call")
            # Mock git remote get-url
            elif "git" in command and "remote" in command and "get-url" in command:
                mock_response.stdout = "git@github.com:test-user/test-repo.git"
                mock_response.returncode = 0
                print("Mocking git remote get-url")
            # Mock terraform commands
            elif "terraform" in command:
                mock_response.stdout = ""
                mock_response.returncode = 0
                print("Mocking terraform command")
            # Mock repository view command
            elif "gh" in command and "repo" in command and "view" in command:
                mock_response.stdout = '{"isEmpty": true}'
                mock_response.returncode = 0
                print("Mocking repository view command")
            # Mock gsutil commands
            elif "gsutil" in command:
                mock_response.stdout = ""
                mock_response.returncode = 0
                print("Mocking gsutil command")
            # Mock git init
            elif "git" in command and "init" in command:
                mock_response.stdout = ""
                mock_response.returncode = 0
                print("Mocking git init")
            # Mock gcloud builds commands
            elif "gcloud" in command and "builds" in command:
                mock_response.stdout = json.dumps(
                    {
                        "installationState": {"stage": "COMPLETE"},
                        "githubConfig": {
                            "authorizerCredential": {
                                "oauthTokenSecretVersion": "projects/test-project/secrets/oauth-token/versions/1"
                            },
                            "appInstallationId": "test-installation-id",
                        },
                    }
                )
                mock_response.returncode = 0
                print("Mocking gcloud builds command")
            # Mock gcloud projects commands
            elif "gcloud" in command and "projects" in command:
                mock_response.stdout = "123456789"  # Mock project number
                mock_response.returncode = 0
                print("Mocking gcloud projects command")
            # Default response for any other command
            else:
                mock_response.stdout = ""
                mock_response.returncode = 0
                print(f"Default mock for command: {command}")

            return mock_response

        mock_run_command.side_effect = run_command_side_effect
        mock_create_github_connection.return_value = (
            "oauth-token",
            "test-installation-id",
        )

        # Mock E2EDeployment
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.copy2"),
            patch("builtins.open", mock_open()),
            patch("src.cli.utils.cicd.ensure_apis_enabled"),
            patch(
                "src.cli.utils.cicd.run_command", side_effect=run_command_side_effect
            ),
            patch("src.cli.commands.setup_cicd.E2EDeployment") as mock_e2e,
            patch(
                "click.prompt",
                side_effect=[
                    "1",  # Git provider selection
                    "1",  # Repository option (1 for new repo)
                    "test-repo",  # Repository name
                    "test-user",  # Repository owner
                    "y",  # Confirmation prompt
                ],
            ),
            patch("click.confirm", return_value=True),
            patch("pathlib.Path.glob") as mock_glob,
            patch(
                "src.cli.utils.gcp.verify_credentials",
                return_value={"account": "test@example.com", "project": "test-project"},
            ),
        ):
            mock_e2e_instance = MagicMock()
            mock_e2e.return_value = mock_e2e_instance
            mock_glob.return_value = [Path("mock.tf")]

            print("\nInvoking setup_cicd command...")
            result = runner.invoke(
                setup_cicd,
                [
                    "--staging-project",
                    "test-staging",
                    "--prod-project",
                    "test-prod",
                    "--cicd-project",
                    "test-cicd",
                    "--auto-approve",
                ],
            )

            if result.exception:
                print(f"Exception: {result.exception}")
                print(f"Output: {result.output}")
                print(f"\nCommand exit code: {result.exit_code}")

            assert result.exit_code == 0
            mock_create_github_connection.assert_called_once()
            mock_setup_terraform_backend.assert_called()

    def test_setup_cicd_invalid_working_directory(self, mock_cwd: MagicMock) -> None:
        """Test setup fails when not in project root"""
        runner = CliRunner()

        with patch("pathlib.Path.exists", return_value=False):
            result = runner.invoke(
                setup_cicd,
                [
                    "--staging-project",
                    "test-staging",
                    "--prod-project",
                    "test-prod",
                    "--cicd-project",
                    "test-cicd",
                    "--github-pat",
                    "test-pat",
                    "--auto-approve",
                ],
            )

        assert result.exit_code != 0
        assert "must be run from the project root directory" in result.output

    def test_setup_cicd_interactive_prompt_for_missing_args(
        self, mock_cwd: MagicMock
    ) -> None:
        """Test setup prompts for missing required arguments interactively"""
        runner = CliRunner()

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "src.cli.utils.cicd.run_command",
                side_effect=subprocess.CalledProcessError(1, "gcloud"),
            ),
        ):
            # Simulate user entering "test-prod" when prompted
            result = runner.invoke(
                setup_cicd,
                [
                    "--staging-project",
                    "test-staging",  # Missing prod project, should prompt for it
                ],
                input="test-prod\n",  # Simulate user input for prod project
            )

        assert "Enter your production project ID" in result.output

    def test_setup_cicd_with_github_pat(
        self,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
        mock_run_command: MagicMock,
        mock_e2e_deployment: MagicMock,
        mock_terraform_files: None,
    ) -> None:
        """Test setup with GitHub PAT authentication"""
        runner = CliRunner()

        # Set up mock responses for different command calls
        def run_command_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            command = args[0]
            mock_response = MagicMock()

            # Mock gcloud services list
            if "gcloud" in command and "services" in command and "list" in command:
                mock_response.stdout = "[]"
                mock_response.returncode = 0
            # Mock GitHub username API call
            elif "gh" in command and "api" in command and "user" in command:
                mock_response.stdout = "test-user"
                mock_response.returncode = 0
            # Mock terraform commands
            elif "terraform" in command:
                mock_response.stdout = ""
                mock_response.returncode = 0
            # Mock gcloud secrets commands
            elif "gcloud" in command and "secrets" in command:
                mock_response.stdout = ""
                mock_response.returncode = 0

            return mock_response

        mock_run_command.side_effect = run_command_side_effect

        # Mock E2EDeployment
        with (
            patch("pathlib.Path.exists", return_value=True) as mock_exists,
            patch("src.cli.utils.cicd.ensure_apis_enabled"),
            patch(
                "src.cli.utils.cicd.run_command", side_effect=run_command_side_effect
            ),
            patch("src.cli.commands.setup_cicd.E2EDeployment") as mock_e2e,
            patch("builtins.open", mock_open()),
            patch("shutil.copy2"),
        ):
            mock_e2e_instance = MagicMock()
            mock_e2e.return_value = mock_e2e_instance

            def exists_side_effect() -> bool:
                return True

            mock_exists.side_effect = exists_side_effect

            result = runner.invoke(
                setup_cicd,
                [
                    "--staging-project",
                    "test-staging",
                    "--prod-project",
                    "test-prod",
                    "--cicd-project",
                    "test-cicd",
                    "--git-provider",
                    "github",
                    "--github-pat",
                    "test-pat",
                    "--github-app-installation-id",
                    "test-id",
                    "--auto-approve",
                ],
            )

        assert result.exit_code == 0


@pytest.fixture
def mock_path_exists() -> MagicMock:
    """Mock Path.exists() to simulate pyproject.toml presence"""
    with patch("pathlib.Path.exists", return_value=True):
        yield


def test_setup_cicd_invalid_git_provider(mock_path_exists: MagicMock) -> None:
    """Test setup_cicd fails with invalid git provider"""
    runner = CliRunner()

    result = runner.invoke(
        setup_cicd,
        [
            "--staging-project",
            "test-staging",
            "--prod-project",
            "test-prod",
            "--cicd-project",
            "test-cicd",
            "--git-provider",
            "gitlab",  # Currently unsupported
        ],
    )

    assert result.exit_code != 0
    assert "Invalid value for '--git-provider'" in result.output
