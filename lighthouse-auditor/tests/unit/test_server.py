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
import sys
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from google.auth.credentials import Credentials
from langchain_core.messages import HumanMessage

from app.utils.typing import InputChat

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def mock_google_cloud_credentials() -> Generator[None, None, None]:
    """Mock Google Cloud credentials for testing."""
    with patch.dict(
        os.environ,
        {
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/mock/credentials.json",
            "GOOGLE_CLOUD_PROJECT_ID": "mock-project-id",
        },
    ):
        yield


@pytest.fixture(autouse=True)
def mock_google_auth_default() -> Generator[None, None, None]:
    """Mock the google.auth.default function for testing."""
    mock_credentials = MagicMock(spec=Credentials)
    mock_project = "mock-project-id"

    with patch("google.auth.default", return_value=(mock_credentials, mock_project)):
        yield


@pytest.fixture
def sample_input_chat() -> InputChat:
    """
    Fixture to create a sample input chat for testing.
    """
    return InputChat(
        messages=[HumanMessage(content="What is the meaning of life?")],
    )


def test_redirect_root_to_docs() -> None:
    """
    Test that the root endpoint (/) redirects to the Swagger UI documentation.
    """
    # Mock the agent module before importing server
    mock_agent = MagicMock()
    with patch.dict(sys.modules, {"app.agent": mock_agent}):
        # Now import server after the mock is in place
        from app.server import app

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "Swagger UI" in response.text


@pytest.mark.asyncio
async def test_stream_chat_events() -> None:
    """
    Test the stream endpoint to ensure it correctly handles
    streaming responses and generates the expected events.
    """
    input_data = {
        "input": {
            "messages": [
                {"type": "human", "content": "Hello, AI!"},
                {"type": "ai", "content": "Hello!"},
                {"type": "human", "content": "What cooking recipes do you suggest?"},
            ],
        },
        "config": {"metadata": {"user_id": "test-user", "session_id": "test-session"}},
    }

    mock_events = [{"content": "Mocked response"}, {"content": "Additional response"}]

    # Create a mock agent module
    mock_agent_module = MagicMock()
    mock_agent_module.agent = MagicMock()
    mock_agent_module.agent.stream.return_value = mock_events

    # Patch the module import
    with patch.dict(sys.modules, {"app.agent": mock_agent_module}):
        # Import server after the mock is in place
        from app.server import app

        client = TestClient(app)
        response = client.post("/stream_messages", json=input_data)

        assert response.status_code == 200

        events = []
        for line in response.iter_lines():
            if line:
                events.append(json.loads(line))

        assert len(events) == 2
        assert events[0]["content"] == "Mocked response"
        assert events[1]["content"] == "Additional response"
