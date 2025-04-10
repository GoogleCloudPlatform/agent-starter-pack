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

from locust import HttpUser, between, task


class ChatStreamUser(HttpUser):
    """Simulates a user interacting with the chat stream API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    @task
    def chat_stream(self) -> None:
        """Simulates a chat stream interaction."""
        headers = {"Content-Type": "application/json"}
        if os.environ.get("_ID_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['_ID_TOKEN']}"

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

        start_time = time.time()

        with self.client.post(
            "/stream_messages",
            headers=headers,
            json=data,
            catch_response=True,
            name="/stream_messages first message",
            stream=True,
        ) as response:
            if response.status_code == 200:
                events = []
                for line in response.iter_lines():
                    if line:
                        event = json.loads(line)
                        events.append(event)
                        for chunk in event:
                            if (
                                isinstance(chunk, dict)
                                and chunk.get("type") == "constructor"
                            ):
                                if not chunk.get("kwargs", {}).get("content"):
                                    continue
                                response.success()
                                end_time = time.time()
                                total_time = end_time - start_time
                                self.environment.events.request.fire(
                                    request_type="POST",
                                    name="/stream_messages end",
                                    response_time=total_time
                                    * 1000,  # Convert to milliseconds
                                    response_length=len(json.dumps(events)),
                                    response=response,
                                    context={},
                                )
                                return
                response.failure("No valid response content received")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
