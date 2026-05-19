# Copyright 2026 Google LLC
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

from {{cookiecutter.agent_directory}}.agent import get_weather, run_agent


def test_weather_known_city() -> None:
    """Test that get_weather returns data for a known city."""
    result = get_weather(location="San Francisco")
    assert "60 degrees" in result
    assert "foggy" in result.lower()


def test_weather_unknown_city() -> None:
    """Test that get_weather returns default for an unknown city."""
    result = get_weather(location="Atlantis")
    assert "90 degrees" in result


def test_run_agent() -> None:
    """Test that run_agent returns a non-empty response."""
    response = run_agent("What's the weather in San Francisco?")
    assert isinstance(response, str)
    assert len(response) > 0
