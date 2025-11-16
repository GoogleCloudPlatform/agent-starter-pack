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

import pytest

from agent_starter_pack.cli.commands.register_gemini_enterprise import (
    get_discovery_engine_endpoint,
    parse_agent_engine_id,
)


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
