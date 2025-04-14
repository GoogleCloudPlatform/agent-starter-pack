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

import json
import os
import time
{%- if "adk" in cookiecutter.tags %}
import uuid

import requests
from locust import HttpUser, between, task
{%- else %}

from locust import HttpUser, between, task
{%- endif %}
{% if "adk" in cookiecutter.tags %}
ENDPOINT = "/run_sse"
{% else %}
ENDPOINT = "/stream_messages"
{% endif %}

class ChatStreamUser(HttpUser):
    """Simulates a user interacting with the chat stream API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    @task
    def chat_stream(self) -> None:
        """Simulates a chat stream interaction."""
        headers = {"Content-Type": "application/json"}
        if os.environ.get("_ID_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['_ID_TOKEN']}"
{%- if "adk" in cookiecutter.tags %}
        # Create session first
        user_id = f"user_{uuid.uuid4()}"
        session_id = f"session_{uuid.uuid4()}"
        session_data = {"state": {"preferred_language": "English", "visit_count": 5}}
        requests.post(
            f"{self.client.base_url}/apps/app/users/{user_id}/sessions/{session_id}",
            headers=headers,
            json=session_data,
            timeout=10,
        )

        # Send chat message
        data = {
            "app_name": "app",
            "user_id": user_id,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": "What's the weather in San Francisco?"}],
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
            if response.status_code == 200:
                events = []
                for line in response.iter_lines():
                    if line:
{%- if "adk" in cookiecutter.tags %}
                        # SSE format is "data: {json}"
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: "):
                            event_json = line_str[6:]  # Remove "data: " prefix
                            event = json.loads(event_json)
                            events.append(event)
{%- else %}
                        event = json.loads(line)
                        events.append(event)
{%- endif %}
                end_time = time.time()
                total_time = end_time - start_time
                self.environment.events.request.fire(
                    request_type="POST",
                    name=f"{ENDPOINT} end",
                    response_time=total_time * 1000,  # Convert to milliseconds
                    response_length=len(json.dumps(events)),
                    response=response,
                    context={},
                )
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
