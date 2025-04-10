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

# mypy: disable-error-code="union-attr"
from app.agent import agent


def test_agent_stream() -> None:
    """
    Integration test for the agent stream functionality.
    Tests that the agent returns valid streaming responses.
    """
    input_dict = {
        "messages": [
            {"type": "human", "content": "Hi"},
            {"type": "ai", "content": "Hi there!"},
            {"type": "human", "content": "What's the weather in NY?"},
        ]
    }

    events = [
        message for message, _ in agent.stream(input_dict, stream_mode="messages")
    ]

    # Verify we get a reasonable number of messages
    assert len(events) > 0, "Expected at least one message"

    # First message should be an AI message
    assert events[0].type == "AIMessageChunk"

    # At least one message should have content
    has_content = False
    for event in events:
        if hasattr(event, "content") and event.content:
            has_content = True
            break
    assert has_content, "Expected at least one message with content"
