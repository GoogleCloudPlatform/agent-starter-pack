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


"""Helper functions for testing AgentEngineApp with A2A protocol."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from starlette.requests import Request

if TYPE_CHECKING:
    from {{cookiecutter.agent_directory}}.agent_engine_app import AgentEngineApp

# Test constants
POLL_MAX_ATTEMPTS = 30
POLL_INTERVAL_SECONDS = 1.0
TEST_ARTIFACTS_BUCKET = "test-artifacts-bucket"


def receive_wrapper(data: dict[str, Any] | None) -> Callable[[], Awaitable[dict]]:
    """Creates a mock ASGI receive callable for testing.

    Args:
        data: Dictionary to encode as JSON request body

    Returns:
        Async callable that returns mock ASGI receive message
    """

    async def receive() -> dict:
        byte_data = json.dumps(data).encode("utf-8")
        return {"type": "http.request", "body": byte_data, "more_body": False}

    return receive


def build_post_request(
    data: dict[str, Any] | None = None, path_params: dict[str, str] | None = None
) -> Request:
    """Builds a mock Starlette Request object for a POST request with JSON data.

    Args:
        data: JSON data to include in request body
        path_params: Path parameters to include in request scope

    Returns:
        Mock Starlette Request object
    """
    scope: dict[str, Any] = {
        "type": "http",
        "http_version": "1.1",
        "headers": [(b"content-type", b"application/json")],
        "app": None,
    }
    if path_params:
        scope["path_params"] = path_params
    receiver = receive_wrapper(data)
    return Request(scope, receiver)


def build_get_request(path_params: dict[str, str] | None) -> Request:
    """Builds a mock Starlette Request object for a GET request.

    Args:
        path_params: Path parameters to include in request scope

    Returns:
        Mock Starlette Request object
    """
    scope: dict[str, Any] = {
        "type": "http",
        "http_version": "1.1",
        "query_string": b"",
        "app": None,
    }
    if path_params:
        scope["path_params"] = path_params

    async def receive() -> dict:
        return {"type": "http.disconnect"}

    return Request(scope, receive)


async def poll_task_completion(
    agent_app: "AgentEngineApp",
    task_id: str,
    max_attempts: int = POLL_MAX_ATTEMPTS,
    interval: float = POLL_INTERVAL_SECONDS,
) -> dict[str, Any]:
    """Poll for task completion and return final response.

    Args:
        agent_app: The AgentEngineApp instance to poll
        task_id: The task ID to poll for
        max_attempts: Maximum number of polling attempts
        interval: Seconds to wait between polls

    Returns:
        Final task response when completed

    Raises:
        AssertionError: If task fails or times out
    """
    for _ in range(max_attempts):
        poll_request = build_get_request({"id": task_id})
        response = await agent_app.on_get_task(
            request=poll_request,
            context=None,
        )

        task_state = response.get("status", {}).get("state", "")

        if task_state == "TASK_STATE_COMPLETED":
            return response
        elif task_state == "TASK_STATE_FAILED":
            raise AssertionError(f"Task failed: {response}")

        await asyncio.sleep(interval)

    raise AssertionError(
        f"Task did not complete within {max_attempts * interval} seconds"
    )
