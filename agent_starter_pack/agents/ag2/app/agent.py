# ruff: noqa
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

"""AG2 multi-agent implementation with tool use."""

import os
from typing import Annotated

from dotenv import load_dotenv

from autogen import AssistantAgent, UserProxyAgent, LLMConfig

load_dotenv()
{%- if not cookiecutter.use_google_api_key %}

import google.auth

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

llm_config = LLMConfig(
    {
        "model": "gemini-2.5-flash",
        "api_type": "google",
        "project_id": os.environ["GOOGLE_CLOUD_PROJECT"],
        "location": os.environ["GOOGLE_CLOUD_LOCATION"],
    }
)
{%- else %}

llm_config = LLMConfig(
    {
        "model": "gemini-2.5-flash",
        "api_key": os.environ.get("GOOGLE_API_KEY", ""),
        "api_type": "google",
    }
)
{%- endif %}


# --- Agent Setup ---

assistant = AssistantAgent(
    name="Assistant",
    system_message=(
        "You are a helpful AI assistant. Use the available tools to answer "
        "questions accurately. Reply TERMINATE when the task is complete."
    ),
    llm_config=llm_config,
)

user_proxy = UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=5,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config=False,
)


# --- Tool Definitions ---


@user_proxy.register_for_execution()
@assistant.register_for_llm(description="Get the current weather for a given location")
def get_weather(
    location: Annotated[str, "The city name to get weather for"],
) -> str:
    """Simulates a web search. Use it get information on weather."""
    if "sf" in location.lower() or "san francisco" in location.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


# --- Entry Point ---


def run_agent(message: str) -> str:
    """Run the AG2 agent with the given user message.

    Args:
        message: The user's input message.

    Returns:
        The assistant's final response text.
    """
    assistant.reset()
    user_proxy.reset()

    response = user_proxy.run(assistant, message=message)
    response.process()

    # Extract the summary or last assistant message
    if response.summary:
        return response.summary.replace("TERMINATE", "").strip()

    for msg in reversed(response.messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            return content.replace("TERMINATE", "").strip()

    return "No response generated."


if __name__ == "__main__":
    response = run_agent("What's the weather in San Francisco?")
    print(response)
