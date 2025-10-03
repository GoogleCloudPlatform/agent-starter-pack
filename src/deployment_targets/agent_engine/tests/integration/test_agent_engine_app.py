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
{%- if cookiecutter.agent_name == "adk_live" %}

import asyncio
import json
import logging
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
import requests
from websockets.asyncio.client import connect

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

WS_URL = "ws://127.0.0.1:8000/ws"
FEEDBACK_URL = "http://127.0.0.1:8000/feedback"


def log_output(pipe: Any, log_func: Any) -> None:
    """Log the output from the given pipe."""
    for line in iter(pipe.readline, ""):
        log_func(line.strip())


def start_server() -> subprocess.Popen[str]:
    """Start the server using expose_app in local mode."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.utils.expose_app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding="utf-8",
    )

    # Start threads to log stdout and stderr in real-time
    threading.Thread(
        target=log_output, args=(process.stdout, logger.info), daemon=True
    ).start()
    threading.Thread(
        target=log_output, args=(process.stderr, logger.error), daemon=True
    ).start()

    return process


def wait_for_server(timeout: int = 60, interval: int = 1) -> bool:
    """Wait for the server to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get("http://127.0.0.1:8000/docs", timeout=10)
            if response.status_code == 200:
                logger.info("Server is ready")
                return True
        except Exception:
            pass
        time.sleep(interval)
    logger.error(f"Server did not become ready within {timeout} seconds")
    return False


@pytest.fixture(scope="module")
def server_fixture(request: Any) -> Iterator[subprocess.Popen[str]]:
    """Pytest fixture to start and stop the server for testing."""
    logger.info("Starting server process")
    server_process = start_server()
    if not wait_for_server():
        pytest.fail("Server failed to start")
    logger.info("Server process started")

    def stop_server() -> None:
        logger.info("Stopping server process")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Server process did not terminate, killing it")
            server_process.kill()
            server_process.wait()
        logger.info("Server process stopped")

    request.addfinalizer(stop_server)
    yield server_process


@pytest.mark.asyncio
async def test_websocket_audio_input(server_fixture: subprocess.Popen[str]) -> None:
    """Test websocket with audio input in local mode."""

    async def send_message(websocket: Any, message: dict[str, Any]) -> None:
        """Helper to send JSON messages."""
        await websocket.send(json.dumps(message))

    async def receive_message(websocket: Any, timeout: float = 5.0) -> dict[str, Any]:
        """Helper to receive messages with timeout."""
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            if isinstance(response, bytes):
                return json.loads(response.decode())
            if isinstance(response, str):
                return json.loads(response)
            return response
        except asyncio.TimeoutError as exc:
            raise TimeoutError(
                f"No response received within {timeout} seconds"
            ) from exc

    try:
        await asyncio.sleep(2)

        async with connect(WS_URL, ping_timeout=10, close_timeout=10) as websocket:
            try:
                # Wait for setupComplete
                setup_response = await receive_message(websocket, timeout=10.0)
                assert "setupComplete" in setup_response
                logger.info("Received setupComplete")

                # Send dummy audio chunk with user_id
                dummy_audio = bytes([0] * 1024)
                audio_msg = {
                    "user_id": "test-user",
                    "realtimeInput": {
                        "mediaChunks": [
                            {
                                "mimeType": "audio/pcm;rate=16000",
                                "data": dummy_audio.hex(),
                            }
                        ]
                    },
                }
                await send_message(websocket, audio_msg)
                logger.info("Sent audio chunk")

                # Send text message to complete the turn (matching frontend format)
                text_msg = {
                    "content": {
                        "role": "user",
                        "parts": [{"text": "Test audio"}],
                    }
                }
                await send_message(websocket, text_msg)
                logger.info("Sent text completion")

                # Collect responses
                responses = []
                for _ in range(10):
                    try:
                        response = await receive_message(websocket, timeout=5.0)
                        responses.append(response)
                        logger.info(f"Received: {response}")

                        if isinstance(response, dict) and response.get("turn_complete"):
                            break
                    except TimeoutError:
                        break

                # Verify we got responses
                assert len(responses) > 0, "No responses received"

                logger.info(f"Audio test passed. Received {len(responses)} responses")

            finally:
                await websocket.close()

    except Exception as e:
        logger.error(f"Audio test failed: {e}")
        raise


def test_feedback_endpoint(server_fixture: subprocess.Popen[str]) -> None:
    """Test the feedback endpoint."""
    feedback_data = {
        "score": 5,
        "text": "Great response!",
        "run_id": "test-run-123",
        "user_id": "test-user",
        "log_type": "feedback",
    }

    response = requests.post(FEEDBACK_URL, json=feedback_data, timeout=10)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    logger.info("Feedback endpoint test passed")
{% else %}

import logging

import pytest
{%- if cookiecutter.is_adk %}
from google.adk.events.event import Event

from {{cookiecutter.agent_directory}}.agent import root_agent
from {{cookiecutter.agent_directory}}.agent_engine_app import AgentEngineApp
{%- else %}

from {{cookiecutter.agent_directory}}.agent_engine_app import AgentEngineApp
{%- endif %}


@pytest.fixture
def agent_app() -> AgentEngineApp:
    """Fixture to create and set up AgentEngineApp instance"""
{%- if cookiecutter.is_adk %}
    app = AgentEngineApp(agent=root_agent)
{%- else %}
    app = AgentEngineApp()
{%- endif %}
    app.set_up()
    return app

{% if cookiecutter.is_adk %}
@pytest.mark.asyncio
async def test_agent_stream_query(agent_app: AgentEngineApp) -> None:
    """
    Integration test for the agent stream query functionality.
    Tests that the agent returns valid streaming responses.
    """
    # Create message and events for the async_stream_query
    message = "What's the weather in San Francisco?"
    events = []
    async for event in agent_app.async_stream_query(message=message, user_id="test"):
        events.append(event)
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
{% endif %}{% endif %}