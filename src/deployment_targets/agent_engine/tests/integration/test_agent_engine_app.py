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

import logging

import pytest
{%- if "adk" in cookiecutter.tags %}
from google.adk.events.event import Event

from app.agent import root_agent
from app.agent_engine_app import AgentEngineApp
{%- else %}

from app.agent_engine_app import AgentEngineApp
{%- endif %}


@pytest.fixture
def agent_app() -> AgentEngineApp:
    """Fixture to create and set up AgentEngineApp instance"""
{%- if "adk" in cookiecutter.tags %}
    app = AgentEngineApp(agent=root_agent)
{%- else %}
    app = AgentEngineApp()
{%- endif %}
    app.set_up()
    return app

{% if "adk" in cookiecutter.tags %}
def test_agent_stream_query(agent_app: AgentEngineApp) -> None:
    """
    Integration test for the agent stream query functionality.
    Tests that the agent returns valid streaming responses.
    """
    # Create message and events for the stream_query
    message = "What's the weather in San Francisco?"
    events = list(agent_app.stream_query(message=message, user_id="test"))
    assert len(events) > 0, "Expected at least one chunk in response"

    # Check for valid content in the response
    has_text_content = False
    for event in events:
        validated_event = Event.model_validate(event)
        content = validated_event.content
        if (
            content is not None
            and content.parts
            and any(part.text for part in content.parts)
        ):
            has_text_content = True
            break

    assert has_text_content, "Expected at least one event with text content"


def test_agent_feedback(agent_app: AgentEngineApp) -> None:
    """
    Integration test for the agent feedback functionality.
    Tests that feedback can be registered successfully.
    """
    feedback_data = {
        "score": 5,
        "text": "Great response!",
        "invocation_id": "test-run-123",
    }

    # Should not raise any exceptions
    agent_app.register_feedback(feedback_data)

    # Test invalid feedback
    with pytest.raises(ValueError):
        invalid_feedback = {
            "score": "invalid",  # Score must be numeric
            "text": "Bad feedback",
            "invocation_id": "test-run-123",
        }
        agent_app.register_feedback(invalid_feedback)

    logging.info("All assertions passed for agent feedback test")
{% else %}
def test_agent_stream_query(agent_app: AgentEngineApp) -> None:
    """
    Integration test for the agent stream query functionality.
    Tests that the agent returns valid streaming responses.
    """
    input_dict = {
        "messages": [
            {"type": "human", "content": "Test message"},
        ],
        "user_id": "test-user",
        "session_id": "test-session",
    }

    events = list(agent_app.stream_query(input=input_dict))

    assert len(events) > 0, "Expected at least one chunk in response"

    # Verify each event is a tuple of message and metadata
    for event in events:
        assert isinstance(event, list), "Event should be a list"
        assert len(event) == 2, "Event should contain message and metadata"
        message, _ = event

        # Verify message structure
        assert isinstance(message, dict), "Message should be a dictionary"
        assert message["type"] == "constructor"
        assert "kwargs" in message, "Constructor message should have kwargs"

    # Verify at least one message has content
    has_content = False
    for event in events:
        message = event[0]
        if message.get("type") == "constructor" and "content" in message["kwargs"]:
            has_content = True
            break
    assert has_content, "At least one message should have content"


def test_agent_query(agent_app: AgentEngineApp) -> None:
    """
    Integration test for the agent query functionality.
    Tests that the agent returns valid responses.
    """
    input_dict = {
        "messages": [
            {"type": "human", "content": "Test message"},
        ],
        "user_id": "test-user",
        "session_id": "test-session",
    }

    response = agent_app.query(input=input_dict)

    # Basic response validation
    assert isinstance(response, dict), "Response should be a dictionary"
    assert "messages" in response, "Response should contain messages"
    assert len(response["messages"]) > 0, "Response should have at least one message"

    # Validate last message is AI response with content
    message = response["messages"][-1]
    kwargs = message["kwargs"]
    assert kwargs["type"] == "ai", "Last message should be AI response"
    assert len(kwargs["content"]) > 0, "AI message content should not be empty"

    logging.info("All assertions passed for agent query test")


def test_agent_feedback(agent_app: AgentEngineApp) -> None:
    """
    Integration test for the agent feedback functionality.
    Tests that feedback can be registered successfully.
    """
    feedback_data = {
        "score": 5,
        "text": "Great response!",
        "run_id": "test-run-123",
    }

    # Should not raise any exceptions
    agent_app.register_feedback(feedback_data)

    # Test invalid feedback
    with pytest.raises(ValueError):
        invalid_feedback = {
            "score": "invalid",  # Score must be numeric
            "text": "Bad feedback",
            "run_id": "test-run-123",
        }
        agent_app.register_feedback(invalid_feedback)

    logging.info("All assertions passed for agent feedback test")
{% endif %}