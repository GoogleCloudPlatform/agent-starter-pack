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
import logging
import os
import time

from locust import HttpUser, between, task

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Vertex AI and load agent config
with open("deployment_metadata.json") as f:
    remote_agent_engine_id = json.load(f)["remote_agent_engine_id"]

parts = remote_agent_engine_id.split("/")
project_id = parts[1]
location = parts[3]
engine_id = parts[5]

# Convert remote agent engine ID to streaming URL.
base_url = f"https://{location}-aiplatform.googleapis.com"
url_path = f"/v1beta1/projects/{project_id}/locations/{location}/reasoningEngines/{engine_id}:streamQuery"

logger.info("Using remote agent engine ID: %s", remote_agent_engine_id)
logger.info("Using base URL: %s", base_url)
logger.info("Using URL path: %s", url_path)


class ChatStreamUser(HttpUser):
    """Simulates a user interacting with the chat stream API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = base_url  # Set the base host URL for Locust

    @task
    def chat_stream(self) -> None:
        """Simulates a chat stream interaction."""
        headers = {"Content-Type": "application/json"}
        headers["Authorization"] = f"Bearer {os.environ['_AUTH_TOKEN']}"
{% if "adk" in cookiecutter.tags %}
        data = {
            "input": {
                "message": "What's the weather in San Francisco?",
                "user_id": "test",
            }
        }
{% else %}
        data = {
            "input": {
                "input": {
                    "messages": [
                        {"type": "human", "content": "Hello, AI!"},
                        {"type": "ai", "content": "Hello!"},
                        {"type": "human", "content": "How are you?"},
                    ]
                },
                "config": {
                    "metadata": {"user_id": "test-user", "session_id": "test-session"}
                },
            }
        }
{% endif %}
        start_time = time.time()
        with self.client.post(
            url_path,
            headers=headers,
            json=data,
            catch_response=True,
            name="/stream_messages first message",
            stream=True,
            params={"alt": "sse"},
        ) as response:
            if response.status_code == 200:
                events = []
                for line in response.iter_lines():
                    if line:
                        event = json.loads(line)
                        events.append(event)
                end_time = time.time()
                total_time = end_time - start_time
                self.environment.events.request.fire(
                    request_type="POST",
                    name="/stream_messages end",
                    response_time=total_time * 1000,  # Convert to milliseconds
                    response_length=len(json.dumps(events)),
                    response=response,
                    context={},
                )
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
