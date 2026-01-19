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
    """Start the server in local mode."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "{{cookiecutter.agent_directory}}.fast_api_app:app",
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

                # Verify no error responses
                for idx, response in enumerate(responses):
                    assert "error" not in response, (
                        f"Response {idx} contains error: {response.get('error')}"
                    )

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
        "user_id": "test-user-123",
        "session_id": "test-session-123",
        "log_type": "feedback",
    }

    response = requests.post(FEEDBACK_URL, json=feedback_data, timeout=10)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    logger.info("Feedback endpoint test passed")
{%- else %}

import json
import logging
import os
import subprocess
import sys
import threading
import time
{%- if cookiecutter.is_a2a %}
import uuid
{%- endif %}
from collections.abc import Iterator
from typing import Any

import pytest
import requests
{%- if cookiecutter.is_a2a %}
from a2a.types import (
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendMessageResponse,
    SendStreamingMessageRequest,
    SendStreamingMessageResponse,
    TextPart,
)
{%- endif %}
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000/"
{%- if cookiecutter.is_a2a %}
A2A_RPC_URL = BASE_URL + "a2a/{{cookiecutter.agent_directory}}/"
AGENT_CARD_URL = A2A_RPC_URL + ".well-known/agent-card.json"
{%- elif cookiecutter.is_adk %}
STREAM_URL = BASE_URL + "run_sse"
{%- else %}
STREAM_URL = BASE_URL + "stream_messages"
{%- endif %}
FEEDBACK_URL = BASE_URL + "feedback"

HEADERS = {"Content-Type": "application/json"}


def log_output(pipe: Any, log_func: Any) -> None:
    """Log the output from the given pipe."""
    for line in iter(pipe.readline, ""):
        log_func(line.strip())


def start_server() -> subprocess.Popen[str]:
    """Start the FastAPI server using subprocess and log its output."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "{{cookiecutter.agent_directory}}.fast_api_app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    env = os.environ.copy()
    env["INTEGRATION_TEST"] = "TRUE"
{%- if cookiecutter.session_type == "agent_engine" %}
    # Use in-memory session for local E2E tests instead of creating Agent Engine
    env["USE_IN_MEMORY_SESSION"] = "true"
{%- endif %}
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    # Start threads to log stdout and stderr in real-time
    threading.Thread(
        target=log_output, args=(process.stdout, logger.info), daemon=True
    ).start()
    threading.Thread(
        target=log_output, args=(process.stderr, logger.error), daemon=True
    ).start()

    return process


def wait_for_server(timeout: int = 90, interval: int = 1) -> bool:
    """Wait for the server to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
{%- if cookiecutter.is_a2a %}
            response = requests.get(AGENT_CARD_URL, timeout=10)
{%- else %}
            response = requests.get("http://127.0.0.1:8000/docs", timeout=10)
{%- endif %}
            if response.status_code == 200:
                logger.info("Server is ready")
                return True
        except RequestException:
            pass
        time.sleep(interval)
    logger.error(f"Server did not become ready within {timeout} seconds")
    return False


@pytest.fixture(scope="session")
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
        server_process.wait()
        logger.info("Server process stopped")

    request.addfinalizer(stop_server)
    yield server_process


def test_chat_stream(server_fixture: subprocess.Popen[str]) -> None:
{%- if cookiecutter.is_a2a %}
    """Test the chat stream functionality using A2A JSON-RPC protocol."""
    logger.info("Starting chat stream test")

    message = Message(
        message_id=f"msg-user-{uuid.uuid4()}",
        role=Role.user,
        parts=[Part(root=TextPart(text="Hi!"))],
    )

    request = SendStreamingMessageRequest(
        id="test-req-001",
        params=MessageSendParams(message=message),
    )

    # Send the request
    response = requests.post(
        A2A_RPC_URL,
        headers=HEADERS,
        json=request.model_dump(mode="json", exclude_none=True),
        stream=True,
        timeout=60,
    )
    assert response.status_code == 200

    # Parse streaming JSON-RPC responses
    responses: list[SendStreamingMessageResponse] = []

    for line in response.iter_lines():
        if line:
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                event_json = line_str[6:]
                json_data = json.loads(event_json)
                streaming_response = SendStreamingMessageResponse.model_validate(
                    json_data
                )
                responses.append(streaming_response)

    assert responses, "No responses received from stream"

    # Check for final status update
    final_responses = [
        r.root
        for r in responses
        if hasattr(r.root, "result")
        and hasattr(r.root.result, "final")
        and r.root.result.final is True
    ]
    assert final_responses, "No final response received"

    final_response = final_responses[-1]
    assert final_response.result.kind == "status-update"
    assert hasattr(final_response.result, "status")
    assert final_response.result.status.state == "completed"

    # Check for artifact content
    artifact_responses = [
        r.root
        for r in responses
        if hasattr(r.root, "result") and r.root.result.kind == "artifact-update"
    ]
    assert artifact_responses, "No artifact content received in stream"

    # Verify text content is in the artifact
    artifact_response = artifact_responses[-1]
    assert hasattr(artifact_response.result, "artifact")
    artifact = artifact_response.result.artifact
    assert artifact.parts, "Artifact has no parts"

    has_text = any(
        part.root.kind == "text" and hasattr(part.root, "text") and part.root.text
        for part in artifact.parts
    )
    assert has_text, "No text content found in artifact"
{%- else %}
    """Test the chat stream functionality."""
    logger.info("Starting chat stream test")
{% if cookiecutter.is_adk %}
    # Create session first
    user_id = "test_user_123"
    session_data = {"state": {"preferred_language": "English", "visit_count": 1}}

    session_url = f"{BASE_URL}/apps/{{cookiecutter.agent_directory}}/users/{user_id}/sessions"
    session_response = requests.post(
        session_url,
        headers=HEADERS,
        json=session_data,
        timeout=60,
    )
    assert session_response.status_code == 200
    logger.info(f"Session creation response: {session_response.json()}")
    session_id = session_response.json()["id"]

    # Then send chat message
    data = {
        "app_name": "{{cookiecutter.agent_directory}}",
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": "Hi!"}],
        },
        "streaming": True,
    }
{% else %}
    data = {
        "input": {
            "messages": [
                {"type": "human", "content": "Hello, AI!"},
                {"type": "ai", "content": "Hello!"},
                {"type": "human", "content": "Who are you?"},
            ]
        },
        "config": {"metadata": {"user_id": "test-user", "session_id": "test-session"}},
    }
{% endif %}
    response = requests.post(
        STREAM_URL, headers=HEADERS, json=data, stream=True, timeout=60
    )
    assert response.status_code == 200

{%- if cookiecutter.is_adk %}
    # Parse SSE events from response
    events = []
    for line in response.iter_lines():
        if line:
            # SSE format is "data: {json}"
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                event_json = line_str[6:]  # Remove "data: " prefix
                event = json.loads(event_json)
                events.append(event)

    assert events, "No events received from stream"
    # Check for valid content in the response
    has_text_content = False
    for event in events:
        content = event.get("content")
        if (
            content is not None
            and content.get("parts")
            and any(part.get("text") for part in content["parts"])
        ):
            has_text_content = True
            break
{%- else %}
    events = [json.loads(line) for line in response.iter_lines() if line]
    assert events, "No events received from stream"

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
{%- endif %}
{%- endif %}


{%- if cookiecutter.is_a2a %}


def test_chat_non_streaming(server_fixture: subprocess.Popen[str]) -> None:
    """Test the non-streaming chat functionality using A2A JSON-RPC protocol."""
    logger.info("Starting non-streaming chat test")

    message = Message(
        message_id=f"msg-user-{uuid.uuid4()}",
        role=Role.user,
        parts=[Part(root=TextPart(text="Hi!"))],
    )

    request = SendMessageRequest(
        id="test-req-002",
        params=MessageSendParams(message=message),
    )

    response = requests.post(
        A2A_RPC_URL,
        headers=HEADERS,
        json=request.model_dump(mode="json", exclude_none=True),
        timeout=60,
    )
    assert response.status_code == 200

    # Parse the single JSON-RPC response
    response_data = response.json()
    message_response = SendMessageResponse.model_validate(response_data)
    logger.info(f"Received response: {message_response}")

    # For non-streaming, the result is a Task object
    json_rpc_resp = message_response.root
    assert hasattr(json_rpc_resp, "result")
    task = json_rpc_resp.result
    assert task.kind == "task"
    assert hasattr(task, "status")
    assert task.status.state == "completed"

    # Check that we got artifacts (the final agent output)
    assert hasattr(task, "artifacts")
    assert task.artifacts, "No artifacts in task"

    # Verify we got text content in the artifact
    artifact = task.artifacts[0]
    assert artifact.parts, "Artifact has no parts"

    has_text = any(
        part.root.kind == "text" and hasattr(part.root, "text") and part.root.text
        for part in artifact.parts
    )
    assert has_text, "No text content found in artifact"


def test_chat_stream_error_handling(server_fixture: subprocess.Popen[str]) -> None:
    """Test the chat stream error handling with invalid A2A request."""
    logger.info("Starting chat stream error handling test")

    invalid_data = {
        "jsonrpc": "2.0",
        "id": "test-error-001",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                # Missing required 'parts' field
                "messageId": f"msg-user-{uuid.uuid4()}",
            }
        },
    }

    response = requests.post(
        A2A_RPC_URL, headers=HEADERS, json=invalid_data, timeout=10
    )
    assert response.status_code == 200

    response_data = response.json()
    error_response = JSONRPCErrorResponse.model_validate(response_data)
    assert "error" in response_data, "Expected JSON-RPC error in response"

    # Assert error for invalid parameters
    assert error_response.error.code == -32602

    logger.info("Error handling test completed successfully")
{%- else %}


def test_chat_stream_error_handling(server_fixture: subprocess.Popen[str]) -> None:
    """Test the chat stream error handling."""
    logger.info("Starting chat stream error handling test")
    data = {
        "input": {"messages": [{"type": "invalid_type", "content": "Cause an error"}]}
    }
    response = requests.post(
        STREAM_URL, headers=HEADERS, json=data, stream=True, timeout=10
    )

    assert response.status_code == 422, (
        f"Expected status code 422, got {response.status_code}"
    )
    logger.info("Error handling test completed successfully")
{%- endif %}


def test_collect_feedback(server_fixture: subprocess.Popen[str]) -> None:
    """
    Test the feedback collection endpoint (/feedback) to ensure it properly
    logs the received feedback.
    """
    # Create sample feedback data
    feedback_data = {
        "score": 4,
        "user_id": "test-user-456",
        "session_id": "test-session-456",
        "text": "Great response!",
    }

    response = requests.post(
        FEEDBACK_URL, json=feedback_data, headers=HEADERS, timeout=10
    )
    assert response.status_code == 200


{%- if cookiecutter.is_a2a %}


def test_a2a_agent_json_generation(server_fixture: subprocess.Popen[str]) -> None:
    """
    Test that the agent.json file is automatically generated and served correctly
    via the well-known URI.
    """
    # Verify the A2A endpoint serves the agent card
    response = requests.get(AGENT_CARD_URL, timeout=10)
    assert response.status_code == 200, f"A2A endpoint returned {response.status_code}"

    # Validate required fields in served agent card
    served_agent_card = response.json()
    required_fields = [
        "name",
        "description",
        "skills",
        "capabilities",
        "url",
        "version",
    ]
    for field in required_fields:
        assert field in served_agent_card, (
            f"Missing required field in served agent card: {field}"
        )


{%- endif %}
{%- if cookiecutter.session_type == "agent_engine" %}


@pytest.fixture(scope="session", autouse=True)
def cleanup_agent_engine_sessions() -> None:
    """Cleanup agent engine sessions created during tests."""
    yield  # Run tests first

    # Cleanup after tests complete
    from vertexai import agent_engines

    try:
        # Use same environment variable as server, default to project name
        default_agent_name = "{{cookiecutter.project_name}}"
        agent_name = os.environ.get("AGENT_ENGINE_SESSION_NAME", default_agent_name)

        # Find and delete agent engines with this name
        existing_agents = list(agent_engines.list(filter=f"display_name={agent_name}"))

        for agent_engine in existing_agents:
            try:
                agent_engines.delete(resource_name=agent_engine.name)
                logger.info(f"Cleaned up agent engine: {agent_engine.name}")
            except Exception as e:
                logger.warning(
                    f"Failed to cleanup agent engine {agent_engine.name}: {e}"
                )
    except Exception as e:
        logger.warning(f"Failed to cleanup agent engine sessions: {e}")
{%- endif %}
{%- endif %}
