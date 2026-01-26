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
import os
import time
import uuid

from locust import User, between, task
from websockets.sync.client import connect

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Timeout settings for Gemini Live
CONNECTION_TIMEOUT = 60
MESSAGE_TIMEOUT = 30


class WebSocketUser(User):
    """Simulates a user interacting with the ADK Live WebSocket API."""

    wait_time = between(5, 10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws = None
        self.user_id = f"loadtest_{uuid.uuid4()}"

    def on_start(self):
        """Connect to WebSocket when user starts."""
        ws_url = self.host.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws"

        # Add authorization header if ID token is available (for Cloud Run)
        additional_headers = {}
        id_token = os.environ.get("_ID_TOKEN")
        if id_token:
            additional_headers["Authorization"] = f"Bearer {id_token}"

        try:
            self.ws = connect(
                ws_url,
                open_timeout=CONNECTION_TIMEOUT,
                additional_headers=additional_headers if additional_headers else None,
            )
            # Wait for setupComplete
            response = self.ws.recv(timeout=MESSAGE_TIMEOUT)
            data = json.loads(response)
            if "setupComplete" in data:
                logger.info("WebSocket connection established, setupComplete received")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.ws = None

    def on_stop(self):
        """Close WebSocket when user stops."""
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass

    @task
    def chat_message(self) -> None:
        """Send a chat message through WebSocket to ADK Live agent."""
        if not self.ws:
            logger.warning("No WebSocket connection, attempting reconnect")
            self.on_start()
            if not self.ws:
                return

        start_time = time.time()

        try:
            # Send dummy audio chunk with user_id (matching integration test format)
            dummy_audio = bytes([0] * 1024)
            audio_msg = {
                "user_id": self.user_id,
                "realtimeInput": {
                    "mediaChunks": [
                        {
                            "mimeType": "audio/pcm;rate=16000",
                            "data": dummy_audio.hex(),
                        }
                    ]
                },
            }
            self.ws.send(json.dumps(audio_msg))
            logger.info(f"Sent audio chunk for user {self.user_id}")

            # Send text message to complete the turn (matching integration test format)
            text_msg = {
                "content": {
                    "role": "user",
                    "parts": [{"text": "What's the weather in San Francisco?"}],
                }
            }
            self.ws.send(json.dumps(text_msg))
            logger.info("Sent text message")

            # Collect responses
            responses = []
            has_error = False
            turn_complete = False

            for _ in range(20):
                try:
                    response = self.ws.recv(timeout=MESSAGE_TIMEOUT)
                    if isinstance(response, bytes):
                        data = json.loads(response.decode())
                    else:
                        data = json.loads(response)

                    responses.append(data)
                    logger.debug(
                        f"Received: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                    )

                    if isinstance(data, dict):
                        if "error" in data:
                            has_error = True
                            logger.error(f"Error response: {data['error']}")
                            break
                        if data.get("turn_complete") or data.get("turnComplete"):
                            turn_complete = True
                            break

                        # Check serverContent for turn complete
                        server_content = data.get("serverContent", {})
                        if server_content.get("turnComplete"):
                            turn_complete = True
                            break

                except TimeoutError:
                    logger.warning("Timeout waiting for response")
                    break
                except Exception as e:
                    logger.error(f"Error receiving: {e}")
                    break

            end_time = time.time()
            total_time = (end_time - start_time) * 1000  # ms

            if len(responses) > 0 and not has_error:
                self.environment.events.request.fire(
                    request_type="WebSocket",
                    name="chat_message",
                    response_time=total_time,
                    response_length=len(responses),
                    response=None,
                    context={},
                    exception=None,
                )
                logger.info(
                    f"Request completed in {total_time:.0f}ms with {len(responses)} responses"
                )
            else:
                self.environment.events.request.fire(
                    request_type="WebSocket",
                    name="chat_message",
                    response_time=total_time,
                    response_length=len(responses),
                    response=None,
                    context={},
                    exception=Exception("No responses or error"),
                )

        except Exception as e:
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            logger.error(f"Request failed: {e}")
            self.environment.events.request.fire(
                request_type="WebSocket",
                name="chat_message",
                response_time=total_time,
                response_length=0,
                response=None,
                context={},
                exception=e,
            )
            # Reconnect on failure
            self.on_stop()
            self.on_start()
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

        session_response = self.client.post(
            f"/apps/{{cookiecutter.agent_directory}}/users/{user_id}/sessions",
            headers=headers,
            json=session_data,
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
