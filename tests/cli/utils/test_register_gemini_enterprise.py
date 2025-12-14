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

"""Tests for Gemini Enterprise registration utility functions."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
import requests

from agent_starter_pack.cli.commands.register_gemini_enterprise import (
    get_current_project_id,
    get_discovery_engine_endpoint,
    get_gemini_enterprise_console_url,
    get_project_number,
    list_gemini_enterprise_apps,
    parse_agent_engine_id,
)


class TestGetCurrentProjectId:
    """Tests for get_current_project_id function."""

    @patch("agent_starter_pack.cli.commands.register_gemini_enterprise.default")
    def test_get_current_project_id_success(self, mock_default: MagicMock) -> None:
        """Test getting current project ID from auth defaults."""
        mock_credentials = MagicMock()
        mock_default.return_value = (mock_credentials, "my-project-id")

        result = get_current_project_id()

        assert result == "my-project-id"

    @patch("agent_starter_pack.cli.commands.register_gemini_enterprise.default")
    def test_get_current_project_id_none(self, mock_default: MagicMock) -> None:
        """Test when auth defaults return None for project."""
        mock_credentials = MagicMock()
        mock_default.return_value = (mock_credentials, None)

        result = get_current_project_id()

        assert result is None

    @patch("agent_starter_pack.cli.commands.register_gemini_enterprise.default")
    def test_get_current_project_id_error(self, mock_default: MagicMock) -> None:
        """Test when auth defaults fail."""
        mock_default.side_effect = Exception("Auth error")

        result = get_current_project_id()

        assert result is None


class TestGetProjectNumber:
    """Tests for get_project_number function."""

    @patch("agent_starter_pack.cli.utils.command.subprocess.run")
    @patch(
        "shutil.which", return_value="gcloud"
    )  # Mock shutil.which for consistent test behavior
    def test_get_project_number_from_id(
        self, mock_which: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test getting project number from project ID."""
        mock_result = MagicMock()
        mock_result.stdout = "123456789\n"
        mock_run.return_value = mock_result

        result = get_project_number("my-project-id")

        assert result == "123456789"
        # gcloud command is called via centralized run_gcloud_command helper
        mock_run.assert_called_once_with(
            [
                "gcloud",
                "projects",
                "describe",
                "my-project-id",
                "--format=value(projectNumber)",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=None,
            shell=False,
        )

    @patch("agent_starter_pack.cli.utils.command.subprocess.run")
    def test_get_project_number_already_number(self, mock_run: MagicMock) -> None:
        """Test that numeric input is returned as-is when lookup fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "gcloud")

        result = get_project_number("123456789")

        assert result == "123456789"

    @patch("agent_starter_pack.cli.utils.command.subprocess.run")
    def test_get_project_number_lookup_fails(self, mock_run: MagicMock) -> None:
        """Test that None is returned when lookup fails for non-numeric input."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "gcloud")

        result = get_project_number("invalid-project")

        assert result is None


class TestGetGeminiEnterpriseConsoleUrl:
    """Tests for get_gemini_enterprise_console_url function."""

    def test_console_url_global(self) -> None:
        """Test console URL construction for global location."""
        ge_app_id = "projects/123456/locations/global/collections/default_collection/engines/my-engine"
        project_id = "my-project"

        result = get_gemini_enterprise_console_url(ge_app_id, project_id)

        expected = (
            "https://console.cloud.google.com/gemini-enterprise/locations/global/"
            "engines/my-engine/overview/dashboard?project=my-project"
        )
        assert result == expected

    def test_console_url_regional(self) -> None:
        """Test console URL construction for regional location."""
        ge_app_id = "projects/123456/locations/eu/collections/default_collection/engines/my-eu-engine"
        project_id = "my-eu-project"

        result = get_gemini_enterprise_console_url(ge_app_id, project_id)

        expected = (
            "https://console.cloud.google.com/gemini-enterprise/locations/eu/"
            "engines/my-eu-engine/overview/dashboard?project=my-eu-project"
        )
        assert result == expected

    def test_console_url_invalid_format(self) -> None:
        """Test that invalid GE app ID returns None."""
        ge_app_id = "invalid-format"
        project_id = "my-project"

        result = get_gemini_enterprise_console_url(ge_app_id, project_id)

        assert result is None


class TestDiscoveryEngineEndpoint:
    """Tests for get_discovery_engine_endpoint function."""

    @pytest.mark.parametrize(
        "location,expected",
        [
            ("global", "https://discoveryengine.googleapis.com"),
            ("eu", "https://eu-discoveryengine.googleapis.com"),
            ("us", "https://us-discoveryengine.googleapis.com"),
        ],
    )
    def test_discovery_engine_endpoints(self, location: str, expected: str) -> None:
        """Test that supported locations return correct endpoints."""
        endpoint = get_discovery_engine_endpoint(location)
        assert endpoint == expected


class TestParseAgentEngineId:
    """Tests for parse_agent_engine_id function."""

    def test_valid_agent_engine_id(self) -> None:
        """Test parsing a valid Agent Engine resource name."""
        agent_id = (
            "projects/123456789/locations/us-central1/reasoningEngines/9876543210"
        )
        result = parse_agent_engine_id(agent_id)

        assert result is not None
        assert result["project"] == "123456789"
        assert result["location"] == "us-central1"
        assert result["engine_id"] == "9876543210"

    def test_invalid_agent_engine_id_wrong_format(self) -> None:
        """Test that invalid format returns None."""
        invalid_id = "projects/123/locations/us-central1/engines/123"
        result = parse_agent_engine_id(invalid_id)
        assert result is None

    def test_invalid_agent_engine_id_too_short(self) -> None:
        """Test that too short ID returns None."""
        invalid_id = "projects/123/locations/us-central1"
        result = parse_agent_engine_id(invalid_id)
        assert result is None

    def test_invalid_agent_engine_id_wrong_keywords(self) -> None:
        """Test that wrong keywords return None."""
        invalid_id = "projects/123/regions/us-central1/reasoningEngines/456"
        result = parse_agent_engine_id(invalid_id)
        assert result is None


class TestListGeminiEnterpriseApps:
    """Tests for list_gemini_enterprise_apps function."""

    @patch(
        "agent_starter_pack.cli.commands.register_gemini_enterprise.get_access_token"
    )
    @patch("agent_starter_pack.cli.commands.register_gemini_enterprise.requests.get")
    def test_list_apps_success(
        self, mock_get: MagicMock, mock_get_token: MagicMock
    ) -> None:
        """Test successfully listing Gemini Enterprise apps."""
        mock_get_token.return_value = "fake-token"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "engines": [
                {
                    "name": "projects/123/locations/global/collections/default_collection/engines/engine1",
                    "displayName": "Test App 1",
                },
                {
                    "name": "projects/123/locations/global/collections/default_collection/engines/engine2",
                    "displayName": "Test App 2",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = list_gemini_enterprise_apps("123", "global")

        assert result is not None
        assert len(result) == 2
        assert result[0]["displayName"] == "Test App 1"
        assert result[1]["displayName"] == "Test App 2"

    @patch(
        "agent_starter_pack.cli.commands.register_gemini_enterprise.get_access_token"
    )
    @patch("agent_starter_pack.cli.commands.register_gemini_enterprise.requests.get")
    def test_list_apps_empty(
        self, mock_get: MagicMock, mock_get_token: MagicMock
    ) -> None:
        """Test listing when no apps exist."""
        mock_get_token.return_value = "fake-token"
        mock_response = MagicMock()
        mock_response.json.return_value = {"engines": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = list_gemini_enterprise_apps("123", "global")

        assert result is not None
        assert len(result) == 0

    @patch(
        "agent_starter_pack.cli.commands.register_gemini_enterprise.get_access_token"
    )
    @patch("agent_starter_pack.cli.commands.register_gemini_enterprise.requests.get")
    def test_list_apps_404_returns_empty(
        self, mock_get: MagicMock, mock_get_token: MagicMock
    ) -> None:
        """Test that 404 error returns empty list."""
        mock_get_token.return_value = "fake-token"
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Create HTTPError with response attribute
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_get.return_value.raise_for_status.side_effect = http_error

        result = list_gemini_enterprise_apps("123", "global")

        assert result == []

    @patch(
        "agent_starter_pack.cli.commands.register_gemini_enterprise.get_access_token"
    )
    @patch("agent_starter_pack.cli.commands.register_gemini_enterprise.requests.get")
    def test_list_apps_other_error_returns_none(
        self, mock_get: MagicMock, mock_get_token: MagicMock
    ) -> None:
        """Test that other HTTP errors return None."""
        mock_get_token.return_value = "fake-token"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Create HTTPError with response attribute
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_get.return_value.raise_for_status.side_effect = http_error

        result = list_gemini_enterprise_apps("123", "global")

        assert result is None
