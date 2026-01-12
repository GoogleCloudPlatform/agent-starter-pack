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

import json
import logging
import time
from typing import Any

from locust import User, between, task
from websockets.exceptions import WebSocketException
from websockets.sync.client import connect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketUser(User):
    """Simulates a user making websocket requests to the remote agent engine."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    abstract = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.ws_url = (
            self.host.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
        )

    @task
    def websocket_audio_conversation(self) -> None:
        """Test a full websocket conversation with audio input."""
        start_time = time.time()
        response_count = 0
        exception = None

        try:
            response_count = self._websocket_interaction()

            # Mark as failure if we got no valid responses
            if response_count == 0:
                exception = Exception("No responses received from agent")

        except WebSocketException as e:
            exception = e
            logger.error(f"WebSocket error: {e}")
        except Exception as e:
            exception = e
            logger.error(f"Unexpected error: {e}")
        finally:
            total_time = int((time.time() - start_time) * 1000)

            # Report the request metrics to Locust
            self.environment.events.request.fire(
                request_type="WS",
                name="websocket_conversation",
                response_time=total_time,
                response_length=response_count * 100,  # Approximate response size
                response=None,
                context={},
                exception=exception,
            )

    def _websocket_interaction(self) -> int:
        """Handle the websocket interaction and return response count."""
        response_count = 0

        with connect(self.ws_url, open_timeout=10, close_timeout=20) as websocket:
            # Wait for setupComplete
            setup_response = websocket.recv(timeout=10.0)
            setup_data = json.loads(setup_response)
            assert "setupComplete" in setup_data, (
                f"Expected setupComplete, got {setup_data}"
            )
            logger.info("Received setupComplete")

            # Send dummy audio chunk with user_id
            dummy_audio = bytes([0] * 1024)
            audio_msg = {
                "user_id": "load-test-user",
                "realtimeInput": {
                    "mediaChunks": [
                        {
                            "mimeType": "audio/pcm;rate=16000",
                            "data": dummy_audio.hex(),
                        }
                    ]
                },
            }
            websocket.send(json.dumps(audio_msg))
            logger.info("Sent audio chunk")

            # Send text message to complete the turn
            text_msg = {
                "content": {
                    "role": "user",
                    "parts": [{"text": "Hello!"}],
                }
            }
            websocket.send(json.dumps(text_msg))
            logger.info("Sent text completion")

            # Collect responses until turn_complete or timeout
            for _ in range(20):  # Max 20 responses
                try:
                    response = websocket.recv(timeout=10.0)
                    response_data = json.loads(response)
                    response_count += 1
                    logger.debug(f"Received response: {response_data}")

                    if isinstance(response_data, dict) and response_data.get(
                        "turn_complete"
                    ):
                        logger.info(f"Turn complete after {response_count} responses")
                        break
                except TimeoutError:
                    logger.info(f"Timeout after {response_count} responses")
                    break

        return response_count


class RemoteAgentUser(WebSocketUser):
    """User for testing remote agent engine deployment."""

    # Set the host via command line: locust -f load_test.py --host=https://your-deployed-service.run.app
    host = "http://localhost:8000"  # Default for local testing
{%- else %}

import json
import logging
import os
import time
{%- if cookiecutter.is_a2a %}
import uuid

from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    SendStreamingMessageRequest,
    TextPart,
)
from locust import HttpUser, between, task
{%- elif cookiecutter.is_adk %}
import uuid

import requests
from locust import HttpUser, between, task
{%- else %}

from locust import HttpUser, between, task
{%- endif %}
{%- if cookiecutter.is_a2a %}

ENDPOINT = "/a2a/{{cookiecutter.agent_directory}}"
{%- elif cookiecutter.is_adk %}

ENDPOINT = "/run_sse"
{%- else %}

ENDPOINT = "/stream_messages"
{%- endif %}

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChatStreamUser(HttpUser):
    """Simulates a user interacting with the chat stream API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    @task
    def chat_stream(self) -> None:
{%- if cookiecutter.is_a2a %}
        """Simulates a chat stream interaction using A2A protocol."""
        headers = {"Content-Type": "application/json"}
        if os.environ.get("_ID_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['_ID_TOKEN']}"

        message = Message(
            message_id=f"msg-user-{uuid.uuid4()}",
            role=Role.user,
            parts=[Part(root=TextPart(text="Hello! What's the weather in New York?"))],
        )

        request = SendStreamingMessageRequest(
            id=f"req-{uuid.uuid4()}",
            params=MessageSendParams(message=message),
        )

        start_time = time.time()

        with self.client.post(
            ENDPOINT,
            name=f"{ENDPOINT} message",
            headers=headers,
            json=request.model_dump(mode="json", exclude_none=True),
            catch_response=True,
            stream=True,
        ) as response:
{%- else %}
        """Simulates a chat stream interaction."""
        headers = {"Content-Type": "application/json"}
        if os.environ.get("_ID_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['_ID_TOKEN']}"
{%- if cookiecutter.is_adk %}
        # Create session first
        user_id = f"user_{uuid.uuid4()}"
        session_data = {"state": {"preferred_language": "English", "visit_count": 1}}

        session_url = f"{self.client.base_url}/apps/{{cookiecutter.agent_directory}}/users/{user_id}/sessions"
        session_response = requests.post(
            session_url,
            headers=headers,
            json=session_data,
            timeout=10,
        )

        # Get session_id from response
        session_id = session_response.json()["id"]

        # Send chat message
        data = {
            "app_name": "{{cookiecutter.agent_directory}}",
            "user_id": user_id,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": "Hello! Weather in New york?"}],
            },
            "streaming": True,
        }
{%- else %}
        data = {
            "input": {
                "messages": [
                    {"type": "human", "content": "Hello, AI!"},
                    {"type": "ai", "content": "Hello!"},
                    {"type": "human", "content": "Who are you?"},
                ]
            },
            "config": {
                "metadata": {"user_id": "test-user", "session_id": "test-session"}
            },
        }
{%- endif %}
        start_time = time.time()

        with self.client.post(
            ENDPOINT,
            name=f"{ENDPOINT} message",
            headers=headers,
            json=data,
            catch_response=True,
            stream=True,
            params={"alt": "sse"},
        ) as response:
{%- endif %}
            if response.status_code == 200:
                events = []
                has_error = False
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        events.append(line_str)

                        if "429 Too Many Requests" in line_str:
                            self.environment.events.request.fire(
                                request_type="POST",
                                name=f"{ENDPOINT} rate_limited 429s",
                                response_time=0,
                                response_length=len(line),
                                response=response,
                                context={},
                            )

                        # Check for error responses in the JSON payload
                        try:
                            event_data = json.loads(line_str)
                            if isinstance(event_data, dict) and "code" in event_data:
                                # Flag any non-2xx codes as errors
                                if event_data["code"] >= 400:
                                    has_error = True
                                    error_msg = event_data.get(
                                        "message", "Unknown error"
                                    )
                                    response.failure(f"Error in response: {error_msg}")
                                    logger.error(
                                        "Received error response: code=%s, message=%s",
                                        event_data["code"],
                                        error_msg,
                                    )
                        except json.JSONDecodeError:
                            # If it's not valid JSON, continue processing
                            pass

                end_time = time.time()
                total_time = end_time - start_time

                # Only fire success event if no errors were found
                if not has_error:
                    self.environment.events.request.fire(
                        request_type="POST",
                        name=f"{ENDPOINT} end",
                        response_time=total_time * 1000,  # Convert to milliseconds
                        response_length=len(events),
                        response=response,
                        context={},
                    )
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
{%- endif %}
