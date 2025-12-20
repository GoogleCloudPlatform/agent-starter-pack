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

import pytest

from {{cookiecutter.agent_directory}}.agent import (
    analyze_text,
    assistant_agent,
    calculate,
    create_crew,
    generate_ideas,
    get_current_time,
    run_agent,
)


def test_get_current_time():
    """Test the time tool."""
    # CrewAI tools are Tool objects, invoke via .run()
    result = get_current_time.run()
    assert result is not None
    assert "current time" in result.lower()
    assert "UTC" in result


def test_calculate_tool():
    """Test the calculator tool."""
    # Test basic addition
    result = calculate.run(expression="2 + 2")
    assert result is not None
    assert "4" in result

    # Test multiplication
    result = calculate.run(expression="10 * 5")
    assert result is not None
    assert "50" in result

    # Test complex expression
    result = calculate.run(expression="(10 + 5) * 2")
    assert result is not None
    assert "30" in result


def test_analyze_text_tool():
    """Test the text analysis tool."""
    test_text = "This is a great test. It has multiple sentences!"
    result = analyze_text.run(text=test_text)
    assert result is not None
    assert "Word count:" in result
    assert "Character" in result
    assert "Sentence count:" in result
    # Should detect positive sentiment
    assert "Positive" in result or "sentiment" in result.lower()


def test_generate_ideas_tool():
    """Test the idea generation tool."""
    result = generate_ideas.run(topic="mobile apps", count=3)
    assert result is not None
    assert "mobile apps" in result.lower()
    assert "3" in result or "ideas" in result.lower()


def test_create_crew():
    """Test crew creation."""
    crew = create_crew("What time is it?")
    assert crew is not None
    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
    assert crew.agents[0].role == "AI Assistant"


def test_assistant_agent_properties():
    """Test assistant agent configuration."""
    assert assistant_agent is not None
    assert assistant_agent.role == "AI Assistant"
    assert assistant_agent.allow_delegation is False
    assert (
        len(assistant_agent.tools) == 4
    )  # calculate, analyze_text, get_current_time, generate_ideas


@pytest.mark.integration
def test_run_agent_time_query():
    """Integration test: Run agent with time query."""
    query = "What time is it?"
    response = run_agent(query)
    assert response is not None
    assert len(response) > 0
    assert isinstance(response, str)


@pytest.mark.integration
def test_run_agent_calculation():
    """Integration test: Run agent with calculation query."""
    query = "Calculate 25 * 4 + 10"
    response = run_agent(query)
    assert response is not None
    assert len(response) > 0
    # Should contain the answer 110 somewhere in the response
    assert "110" in response


@pytest.mark.integration
def test_run_agent_text_analysis():
    """Integration test: Run agent with text analysis query."""
    query = "Analyze this text: 'Agent Starter Pack makes AI development easy!'"
    response = run_agent(query)
    assert response is not None
    assert len(response) > 0
    # Response should be substantive
    assert len(response) > 50, "Response should be substantive"
