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

"""Integration tests for CrewAI agent."""

import os

import pytest

from {{cookiecutter.agent_directory}}.agent import (
    create_crew,
    get_current_time,
    research_agent,
    run_agent,
)


def test_get_current_time():
    """Test the time tool."""
    # CrewAI tools are Tool objects, invoke via .run()
    result = get_current_time.run()
    assert result is not None
    assert "current time" in result.lower()
    assert "UTC" in result


def test_create_crew():
    """Test crew creation."""
    crew = create_crew("What time is it?")
    assert crew is not None
    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
    assert crew.agents[0].role == "Research Assistant"


def test_research_agent_properties():
    """Test research agent configuration."""
    assert research_agent is not None
    assert research_agent.role == "Research Assistant"
    assert research_agent.allow_delegation is False
    assert len(research_agent.tools) == 2  # web_search and get_current_time


@pytest.mark.integration
def test_run_agent_time_query():
    """Integration test: Run agent with time query."""
    query = "What time is it?"
    response = run_agent(query)
    assert response is not None
    assert len(response) > 0
    assert isinstance(response, str)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY") or not os.getenv("GOOGLE_CSE_ID"),
    reason="Google Search API credentials not set",
)
def test_run_agent_with_search():
    """Integration test: Run agent with web search query.

    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables.
    """
    query = "What is the capital of France?"
    response = run_agent(query)
    assert response is not None
    assert len(response) > 0
    # Should mention Paris in the response
    assert "paris" in response.lower()


@pytest.mark.integration
def test_run_agent_mock_search():
    """Integration test: Run agent with mock search (no API keys needed)."""
    # Temporarily unset API keys to test mock functionality
    old_api_key = os.environ.pop("GOOGLE_API_KEY", None)
    old_cse_id = os.environ.pop("GOOGLE_CSE_ID", None)

    try:
        query = "What is the latest news about AI?"
        response = run_agent(query)
        assert response is not None
        assert len(response) > 0
        # Agent should produce a response even with mock search
        # The response should be substantive (not just an error message)
        assert len(response) > 100, "Response should be substantive"
    finally:
        # Restore environment variables
        if old_api_key:
            os.environ["GOOGLE_API_KEY"] = old_api_key
        if old_cse_id:
            os.environ["GOOGLE_CSE_ID"] = old_cse_id
