# Copyright 2026 Google LLC
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

from {{cookiecutter.agent_directory}}.agent import architect, pattern

from autogen.agentchat import initiate_group_chat


def test_architect_responds() -> None:
    """Test that the architect agent processes a message and returns a response."""
    result = architect.run(
        message="Design a key-value store API",
        max_turns=3,
    )

    # Consume events to populate messages
    for _ in result.events:
        pass

    assert result is not None
    assert len(result.messages) > 0

    has_content = any(msg.get("content") for msg in result.messages)
    assert has_content, "Expected at least one message with content"


def test_multi_agent_pipeline() -> None:
    """Test the full architect -> coder -> reviewer pipeline."""
    result, final_context, last_agent = initiate_group_chat(
        pattern=pattern,
        messages="Design and implement a simple key-value store with get, set, and delete operations",
        max_rounds=20,
    )

    assert result is not None
    # Verify we got messages from the pipeline
    assert len(result.chat_history) > 0, "Expected conversation history from the pipeline"
