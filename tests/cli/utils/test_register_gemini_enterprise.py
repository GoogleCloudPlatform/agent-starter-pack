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

from agent_starter_pack.cli.utils.register_gemini_enterprise import (
    get_discovery_engine_endpoint,
)


class TestDiscoveryEngineEndpoint:
    """Tests for get_discovery_engine_endpoint function."""

    def test_global_location(self) -> None:
        """Test that global location returns the standard endpoint."""
        endpoint = get_discovery_engine_endpoint("global")
        assert endpoint == "https://discoveryengine.googleapis.com"

    def test_eu_location(self) -> None:
        """Test that EU location returns the EU regional endpoint."""
        endpoint = get_discovery_engine_endpoint("eu")
        assert endpoint == "https://eu-discoveryengine.googleapis.com"

    def test_us_location(self) -> None:
        """Test that US location returns the US regional endpoint."""
        endpoint = get_discovery_engine_endpoint("us")
        assert endpoint == "https://us-discoveryengine.googleapis.com"

    def test_asia_location(self) -> None:
        """Test that Asia location returns the Asia regional endpoint."""
        endpoint = get_discovery_engine_endpoint("asia")
        assert endpoint == "https://asia-discoveryengine.googleapis.com"

    def test_custom_region(self) -> None:
        """Test that custom regions follow the same pattern."""
        endpoint = get_discovery_engine_endpoint("australia")
        assert endpoint == "https://australia-discoveryengine.googleapis.com"

    @pytest.mark.parametrize(
        "location,expected",
        [
            ("global", "https://discoveryengine.googleapis.com"),
            ("eu", "https://eu-discoveryengine.googleapis.com"),
            ("us", "https://us-discoveryengine.googleapis.com"),
            ("asia", "https://asia-discoveryengine.googleapis.com"),
            ("europe-west1", "https://europe-west1-discoveryengine.googleapis.com"),
            ("us-central1", "https://us-central1-discoveryengine.googleapis.com"),
        ],
    )
    def test_various_locations(self, location: str, expected: str) -> None:
        """Test various location formats return correct endpoints."""
        endpoint = get_discovery_engine_endpoint(location)
        assert endpoint == expected
