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
