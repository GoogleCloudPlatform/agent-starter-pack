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

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from click.testing import CliRunner

from src.cli.commands.create import (
    create,
    display_agent_selection,
)


@pytest.fixture
def mock_cwd() -> Generator[MagicMock, None, None]:
    """Mock for current working directory"""
    with patch("pathlib.Path.cwd") as mock:
        mock.return_value = Path("/mock/cwd")
        yield mock


@pytest.fixture
def mock_mkdir() -> Generator[MagicMock, None, None]:
    """Mock directory creation"""
    with patch("pathlib.Path.mkdir") as mock:
        yield mock


@pytest.fixture
def mock_resolve() -> Generator[MagicMock, None, None]:
    """Mock path resolution"""
    with patch("pathlib.Path.resolve") as mock:
        mock.return_value = Path("/mock/cwd/test-project")
        yield mock


@pytest.fixture
def mock_console() -> Generator[MagicMock, None, None]:
    with patch("src.cli.commands.create.console") as mock:
        yield mock


@pytest.fixture
def mock_verify_credentials() -> Generator[MagicMock, None, None]:
    with patch("src.cli.commands.create.verify_credentials") as mock:
        mock.return_value = {"account": "test@example.com", "project": "test-project"}
        yield mock


@pytest.fixture
def mock_process_template() -> Generator[MagicMock, None, None]:
    with patch("src.cli.commands.create.process_template") as mock:
        yield mock


@pytest.fixture
def mock_get_template_path() -> Generator[MagicMock, None, None]:
    with patch("src.cli.commands.create.get_template_path") as mock:
        mock.return_value = Path("/mock/template/path")
        yield mock


@pytest.fixture
def mock_prompt_deployment_target() -> Generator[MagicMock, None, None]:
    with patch("src.cli.commands.create.prompt_deployment_target") as mock:
        mock.return_value = "cloud_run"
        yield mock


@pytest.fixture
def mock_verify_vertex_connection() -> Generator[MagicMock, None, None]:
    with patch("src.cli.commands.create.verify_vertex_connection") as mock:
        mock.return_value = None  # Success
        yield mock


@pytest.fixture
def mock_subprocess() -> Generator[MagicMock, None, None]:
    with patch("src.cli.commands.create.subprocess.run") as mock:
        mock.return_value = MagicMock(returncode=0)
        yield mock


@pytest.fixture
def mock_get_deployment_targets() -> Generator[MagicMock, None, None]:
    with patch("src.cli.utils.template.get_deployment_targets") as mock:
        mock.return_value = ["cloud_run", "agent_engine"]
        yield mock


@pytest.fixture
def mock_frontend_path() -> Generator[MagicMock, None, None]:
    with patch("pathlib.Path.glob") as mock:
        mock.return_value = [Path("/mock/frontend/path")]
        yield mock


@pytest.fixture
def mock_copy_with_exclusions() -> Generator[MagicMock, None, None]:
    with patch("src.cli.utils.template.copy_with_exclusions") as mock:
        yield mock


@pytest.fixture
def mock_os_chdir() -> Generator[MagicMock, None, None]:
    with patch("os.chdir") as mock:
        yield mock


@pytest.fixture
def mock_load_template_config() -> Generator[MagicMock, None, None]:
    with patch("src.cli.utils.template.load_template_config") as mock:
        mock.return_value = {
            "name": "langgraph_base_react",
            "description": "LangGraph Base React Agent",
            "deployment_targets": ["cloud_run", "agent_engine"],
            "has_pipeline": True,
            "frontend": "streamlit",
        }
        yield mock


@pytest.fixture
def mock_template_path() -> Generator[MagicMock, None, None]:
    with patch("src.cli.utils.template.get_template_path") as mock:
        mock.return_value = "/mock/template/path"
        yield mock


@pytest.fixture
def mock_base_path() -> Generator[MagicMock, None, None]:
    with patch("pathlib.Path") as mock:
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = True
        mock.return_value = mock_path
        yield mock


@pytest.fixture
def mock_get_available_agents() -> Generator[MagicMock, None, None]:
    with patch("src.cli.commands.create.get_available_agents") as mock:
        mock.return_value = {
            1: {
                "name": "langgraph_base_react",
                "description": "LangGraph Base React Agent",
            },
            2: {"name": "another-agent", "description": "Another Test Agent"},
        }
        yield mock


class TestCreateCommand:
    def test_create_with_all_options(
        self,
        mock_console: MagicMock,
        mock_verify_credentials: MagicMock,
        mock_process_template: MagicMock,
        mock_get_template_path: MagicMock,
        mock_subprocess: MagicMock,
        mock_cwd: MagicMock,
        mock_get_available_agents: MagicMock,
        mock_mkdir: MagicMock,
        mock_resolve: MagicMock,
        mock_verify_vertex_connection: MagicMock,
    ) -> None:
        """Test create command with all options provided"""
        runner = CliRunner()

        # Set up expected subprocess calls
        mock_subprocess.side_effect = [
            MagicMock(returncode=0),  # gcp account set
            MagicMock(returncode=0),  # gcp project set
            MagicMock(returncode=0),  # gcp quota project set
        ]

        with patch("pathlib.Path.exists", return_value=False):
            result = runner.invoke(
                create,
                [
                    "test-project",
                    "--agent",
                    "1",
                    "--deployment-target",
                    "cloud_run",
                    "--include-data-ingestion",
                    "--datastore",
                    "vertex_ai_vector_search",
                    "--auto-approve",
                    "--region",
                    "us-central1",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        expected_calls = [
            call(
                ["gcloud", "config", "set", "project", "test-project"],
                check=True,
                capture_output=True,
                text=True,
            ),
            call(
                [
                    "gcloud",
                    "auth",
                    "application-default",
                    "set-quota-project",
                    "test-project",
                ],
                check=True,
                capture_output=True,
                text=True,
            ),
        ]
        mock_subprocess.assert_has_calls(expected_calls, any_order=True)
        # Verify that process_template was called
        mock_process_template.assert_called_once()

    def test_create_with_auto_approve(
        self,
        mock_console: MagicMock,
        mock_verify_credentials: MagicMock,
        mock_process_template: MagicMock,
        mock_get_template_path: MagicMock,
        mock_get_available_agents: MagicMock,
        mock_prompt_deployment_target: MagicMock,
        mock_subprocess: MagicMock,
        mock_cwd: MagicMock,
        mock_mkdir: MagicMock,
        mock_resolve: MagicMock,
        mock_verify_vertex_connection: MagicMock,
    ) -> None:
        """Test create command with auto-approve flag"""
        runner = CliRunner()

        # Set up expected subprocess calls for set_gcp_project
        mock_subprocess.side_effect = [
            MagicMock(returncode=0),  # gcloud config set project
            MagicMock(
                returncode=0
            ),  # gcloud auth application-default set-quota-project
        ]

        with patch("pathlib.Path.exists", return_value=False):
            result = runner.invoke(
                create, ["test-project", "--agent", "1", "--auto-approve"]
            )

        assert result.exit_code == 0

        # Verify the expected subprocess calls
        expected_calls = [
            call(
                ["gcloud", "config", "set", "project", "test-project"],
                check=True,
                capture_output=True,
                text=True,
            ),
            call(
                [
                    "gcloud",
                    "auth",
                    "application-default",
                    "set-quota-project",
                    "test-project",
                ],
                check=True,
                capture_output=True,
                text=True,
            ),
        ]
        mock_subprocess.assert_has_calls(expected_calls, any_order=True)
        mock_process_template.assert_called_once()

    def test_create_interactive(
        self,
        mock_console: MagicMock,
        mock_verify_credentials: MagicMock,
        mock_process_template: MagicMock,
        mock_get_template_path: MagicMock,
        mock_get_available_agents: MagicMock,
        mock_prompt_deployment_target: MagicMock,
        mock_subprocess: MagicMock,
        mock_cwd: MagicMock,
        mock_mkdir: MagicMock,
        mock_resolve: MagicMock,
        mock_verify_vertex_connection: MagicMock,
    ) -> None:
        """Test create command in interactive mode"""
        runner = CliRunner()

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("rich.prompt.IntPrompt.ask") as mock_int_prompt,
            patch("rich.prompt.Prompt.ask") as mock_prompt,
        ):
            mock_int_prompt.return_value = 1  # Select first agent
            mock_prompt.return_value = "n"  # Don't change credentials

            result = runner.invoke(create, ["test-project"])

        assert result.exit_code == 0
        mock_get_available_agents.assert_called_once()

    def test_create_existing_project_dir(
        self, mock_console: MagicMock, mock_cwd: MagicMock
    ) -> None:
        """Test create command with existing project directory"""
        runner = CliRunner()
        expected_path = Path("/mock/cwd/existing-project")

        with patch("pathlib.Path.exists", return_value=True):
            result = runner.invoke(create, ["existing-project"], catch_exceptions=False)

        assert (
            result.exit_code == 0
        )  # Changed to 0 since we're handling the exit in the function
        mock_console.print.assert_any_call(
            f"Error: Project directory '{expected_path}' already exists",
            style="bold red",
        )

    def test_create_gcp_credential_change(
        self,
        mock_subprocess: MagicMock,
        mock_console: MagicMock,
        mock_verify_credentials: MagicMock,
        mock_process_template: MagicMock,
        mock_get_template_path: MagicMock,
        mock_get_available_agents: MagicMock,
        mock_prompt_deployment_target: MagicMock,
        mock_cwd: MagicMock,
        mock_mkdir: MagicMock,
        mock_resolve: MagicMock,
        mock_verify_vertex_connection: MagicMock,
    ) -> None:
        """Test create command with GCP credential change"""
        runner = CliRunner()

        # Set up the verify_credentials mock to return different values on subsequent calls
        mock_verify_credentials.side_effect = [
            {"account": "test@example.com", "project": "test-project"},  # First call
            {"account": "new@example.com", "project": "new-project"},  # After login
        ]

        # Set up expected subprocess calls
        mock_subprocess.side_effect = [
            MagicMock(returncode=0),  # gcloud auth login
            MagicMock(returncode=0),  # gcloud config set project
            MagicMock(
                returncode=0
            ),  # gcloud auth application-default set-quota-project
        ]

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("rich.prompt.Prompt.ask") as mock_prompt,
        ):
            # Set up credential change responses
            mock_prompt.side_effect = [
                "edit",  # Change credentials when prompted
                "y",  # Continue after login
            ]

            result = runner.invoke(
                create,
                [
                    "test-project",
                    "--agent",
                    "1",
                    "--deployment-target",
                    "cloud_run",
                    "--region",
                    "us-central1",
                ],
                catch_exceptions=False,
            )
        assert result.exit_code == 0

        # Verify subprocess was called with the right arguments for login
        mock_subprocess.assert_any_call(
            ["gcloud", "auth", "login", "--update-adc"], check=True
        )

    def test_create_with_invalid_agent_name(
        self,
        mock_console: MagicMock,
        mock_verify_credentials: MagicMock,
        mock_get_available_agents: MagicMock,
        mock_verify_vertex_connection: MagicMock,
        mock_subprocess: MagicMock,
        mock_cwd: MagicMock,
        mock_mkdir: MagicMock,
        mock_resolve: MagicMock,
    ) -> None:
        """Test create command fails with invalid agent name"""
        runner = CliRunner()

        with patch("pathlib.Path.exists", return_value=False):
            result = runner.invoke(
                create, ["test-project", "--agent", "non_existent_agent"]
            )

        assert result.exit_code != 0  # Just verify it failed
        # Check the error message in the log output
        assert "Invalid agent name or number: non_existent_agent" in result.output

    def test_create_with_invalid_deployment_target(
        self,
        mock_console: MagicMock,
        mock_verify_credentials: MagicMock,
        mock_get_available_agents: MagicMock,
    ) -> None:
        """Test create command fails with invalid deployment target"""
        runner = CliRunner()

        result = runner.invoke(
            create,
            ["test-project", "--agent", "1", "--deployment-target", "invalid_target"],
        )

        assert result.exit_code == 2  # Click returns 2 for invalid choice errors
        assert "Invalid value for '--deployment-target'" in result.output
        assert (
            "'invalid_target' is not one of 'agent_engine', 'cloud_run'"
            in result.output
        )

    def test_display_agent_selection(
        self, mock_get_available_agents: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test agent selection display and prompt"""
        with patch("rich.prompt.IntPrompt.ask") as mock_prompt:
            mock_prompt.return_value = 1
            result = display_agent_selection()

        assert result == "langgraph_base_react"
        mock_get_available_agents.assert_called_once()

    def test_normalize_project_name(self, mock_console: MagicMock) -> None:
        """Test the normalize_project_name function directly"""
        from src.cli.commands.create import normalize_project_name

        # Test with uppercase characters
        result = normalize_project_name("TestProject")
        assert result == "testproject"
        mock_console.print.assert_any_call(
            "Note: Project names are normalized (lowercase, hyphens only) for better compatibility with cloud resources and tools.",
            style="dim",
        )
        mock_console.print.assert_any_call(
            "Info: Converting to lowercase for compatibility: 'TestProject' -> 'testproject'",
            style="bold yellow",
        )

        # Reset mock for next test
        mock_console.reset_mock()

        # Test with underscores
        result = normalize_project_name("test_project")
        assert result == "test-project"
        mock_console.print.assert_any_call(
            "Info: Replacing underscores with hyphens for compatibility: 'test_project' -> 'test-project'",
            style="yellow",
        )

        # Reset mock for next test
        mock_console.reset_mock()

        # Test with both uppercase and underscores
        result = normalize_project_name("Test_Project")
        assert result == "test-project"
        mock_console.print.assert_any_call(
            "Note: Project names are normalized (lowercase, hyphens only) for better compatibility with cloud resources and tools.",
            style="dim",
        )
        mock_console.print.assert_any_call(
            "Info: Converting to lowercase for compatibility: 'Test_Project' -> 'test_project'",
            style="bold yellow",
        )
        mock_console.print.assert_any_call(
            "Info: Replacing underscores with hyphens for compatibility: 'test_project' -> 'test-project'",
            style="yellow",
        )

        # Test with already normalized name
        mock_console.reset_mock()
        result = normalize_project_name("test-project")
        assert result == "test-project"
        mock_console.print.assert_not_called()
