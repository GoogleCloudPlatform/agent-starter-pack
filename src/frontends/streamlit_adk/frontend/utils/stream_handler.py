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

# mypy: disable-error-code="unreachable"
import importlib
import json
from collections.abc import Generator
from typing import Any
from urllib.parse import urljoin

import google.auth
import google.auth.transport.requests
import google.oauth2.id_token
import requests
import streamlit as st
import vertexai
from google.adk.events.event import Event
from google.auth.exceptions import DefaultCredentialsError
from vertexai import agent_engines

from frontend.utils.multimodal_utils import format_content

st.cache_resource.clear()


@st.cache_resource
def get_remote_agent(remote_agent_engine_id: str) -> Any:
    """Get cached remote agent instance."""
    # Extract location and engine ID from the full resource ID.
    parts = remote_agent_engine_id.split("/")
    project_id = parts[1]
    location = parts[3]
    vertexai.init(project=project_id, location=location)
    return agent_engines.AgentEngine(remote_agent_engine_id)


@st.cache_resource
def get_remote_url_config(url: str, authenticate_request: bool) -> dict[str, Any]:
    """Get cached remote URL agent configuration."""
    stream_url = urljoin(url, "stream_messages")
    creds, _ = google.auth.default()
    id_token = None
    if authenticate_request:
        auth_req = google.auth.transport.requests.Request()
        try:
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, stream_url)
        except DefaultCredentialsError:
            creds.refresh(auth_req)
            id_token = creds.id_token
    return {
        "url": stream_url,
        "authenticate_request": authenticate_request,
        "creds": creds,
        "id_token": id_token,
    }


@st.cache_resource()
def get_local_agent(agent_callable_path: str) -> Any:
    """Get cached local agent instance."""
    module_path, class_name = agent_callable_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    agent = getattr(module, class_name)()
    agent.set_up()
    return agent


class Client:
    """A client for streaming events from a server."""

    def __init__(
        self,
        agent_callable_path: str | None = None,
        remote_agent_engine_id: str | None = None,
        url: str | None = None,
        authenticate_request: bool = False,
    ) -> None:
        """Initialize the Client with appropriate configuration.

        Args:
            agent_callable_path: Path to local agent class
            remote_agent_engine_id: ID of remote Agent engine
            url: URL for remote service
            authenticate_request: Whether to authenticate requests to remote URL
        """
        if url:
            remote_config = get_remote_url_config(url, authenticate_request)
            self.url = remote_config["url"]
            self.authenticate_request = remote_config["authenticate_request"]
            self.creds = remote_config["creds"]
            self.id_token = remote_config["id_token"]
            self.agent = None
        elif remote_agent_engine_id:
            self.agent = get_remote_agent(remote_agent_engine_id)
            self.url = None
        else:
            self.url = None
            if agent_callable_path is None:
                raise ValueError("agent_callable_path cannot be None")
            self.agent = get_local_agent(agent_callable_path)

    def log_feedback(self, feedback_dict: dict[str, Any], invocation_id: str) -> None:
        """Log user feedback for a specific run."""
        score = feedback_dict["score"]
        if score == "😞":
            score = 0.0
        elif score == "🙁":
            score = 0.25
        elif score == "😐":
            score = 0.5
        elif score == "🙂":
            score = 0.75
        elif score == "😀":
            score = 1.0
        feedback_dict["score"] = score
        feedback_dict["invocation_id"] = invocation_id
        feedback_dict["log_type"] = "feedback"
        # Ensure text field is not None
        if feedback_dict.get("text") is None:
            feedback_dict["text"] = ""
        feedback_dict.pop("type")
        url = urljoin(self.url, "feedback")
        headers = {
            "Content-Type": "application/json",
        }
        if self.url:
            url = urljoin(self.url, "feedback")
            headers = {
                "Content-Type": "application/json",
            }
            if self.authenticate_request:
                headers["Authorization"] = f"Bearer {self.id_token}"
            requests.post(
                url, data=json.dumps(feedback_dict), headers=headers, timeout=10
            )
        elif self.agent is not None:
            self.agent.register_feedback(feedback=feedback_dict)
        else:
            raise ValueError("No agent or URL configured for feedback logging")

    def stream_messages(
        self, data: dict[str, Any]
    ) -> Generator[dict[str, Any], None, None]:
        """Stream events from the server, yielding parsed event data."""
        if self.url:
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
            if self.authenticate_request:
                headers["Authorization"] = f"Bearer {self.id_token}"
            with requests.post(
                self.url, json=data, headers=headers, stream=True, timeout=60
            ) as response:
                for line in response.iter_lines():
                    if line:
                        try:
                            event = json.loads(line.decode("utf-8"))
                            yield event
                        except json.JSONDecodeError:
                            print(f"Failed to parse event: {line.decode('utf-8')}")
        elif self.agent is not None:
            yield from self.agent.stream_query(**data)


class StreamHandler:
    """Handles streaming updates to a Streamlit interface."""

    def __init__(self, st: Any, initial_text: str = "") -> None:
        """Initialize the StreamHandler with Streamlit context and initial text."""
        self.st = st
        self.tool_expander = st.expander("Tool Calls:", expanded=False)
        self.container = st.empty()
        self.text = initial_text
        self.tools_logs = initial_text

    def new_token(self, token: str) -> None:
        """Add a new token to the main text display."""
        self.text += token
        self.container.markdown(format_content(self.text), unsafe_allow_html=True)

    def new_status(self, status_update: str) -> None:
        """Add a new status update to the tool calls expander."""
        self.tools_logs += status_update
        self.tool_expander.markdown(status_update)


class EventProcessor:
    """Processes events from the stream and updates the UI accordingly."""

    def __init__(self, st: Any, client: Client, stream_handler: StreamHandler) -> None:
        """Initialize the EventProcessor with Streamlit context, client, and stream handler."""
        self.st = st
        self.client = client
        self.stream_handler = stream_handler
        self.final_content = ""
        self.tool_calls: list[dict[str, Any]] = []
        self.additional_kwargs: dict[str, Any] = {}

    def process_events(self) -> None:
        """Process events from the stream, handling each event type appropriately."""
        messages = self.st.session_state.user_chats[
            self.st.session_state["session_id"]
        ]["messages"]

        session = self.st.session_state["session_id"]
        stream = self.client.stream_messages(
            data={
                "message": messages[-1]["content"],
                "events": messages[:-1],
                "user_id": self.st.session_state["user_id"],
                "session_id": self.st.session_state["session_id"],
            }
        )

        for message in stream:
            event = Event.model_validate(message)

            # Skip processing if event has no content or parts
            if not event.content or not event.content.parts:
                continue

            # Process each part in the event content
            for part in event.content.parts:
                # Case 1: Process function/tool calls
                if part.function_call:
                    # Extract tool call information
                    tool_call = {
                        "name": part.function_call.name,
                        "args": part.function_call.args,
                        "id": part.function_call.id,
                    }

                    # Track tool calls and update UI
                    self.tool_calls.append(event.model_dump())
                    tool_message = (
                        f"\n\nCalling tool: `{tool_call['name']}` "
                        f"with args: `{tool_call['args']}`"
                    )
                    self.stream_handler.new_status(tool_message)

                    # Add to conversation history
                    self.st.session_state.user_chats[session]["messages"].append(
                        event.model_dump(mode="json")
                    )
                # Case 2: Process function/tool responses
                elif part.function_response:
                    # Extract response content
                    content = str(part.function_response.response)

                    # Track responses and update UI
                    self.tool_calls.append(event.model_dump())
                    response_message = f"\n\nTool response: `{content}`"
                    self.stream_handler.new_status(response_message)

                    # Add to conversation history
                    self.st.session_state.user_chats[session]["messages"].append(
                        event.model_dump(mode="json")
                    )
                # Case 3: Process text responses
                elif part.text:
                    if event.is_final_response():
                        # Store the final response in conversation history
                        self.st.session_state.user_chats[session]["messages"].append(
                            event.model_dump(mode="json")
                        )
                        # Save the invocation ID - it might be used by the feedback functionality
                        self.st.session_state["invocation_id"] = event.invocation_id
                    else:
                        # For streaming chunks, accumulate text and update UI
                        self.final_content += part.text
                        self.stream_handler.new_token(part.text)


def get_chain_response(st: Any, client: Client, stream_handler: StreamHandler) -> None:
    """Process the chain response update the Streamlit UI.

    This function initiates the event processing for a chain of operations,
    involving an AI model's response generation and potential tool calls.
    It creates an EventProcessor instance and starts the event processing loop.

    Args:
        st (Any): The Streamlit app instance, used for accessing session state
                 and updating the UI.
        client (Client): An instance of the Client class used to stream events
                        from the server.
        stream_handler (StreamHandler): An instance of the StreamHandler class
                                      used to update the Streamlit UI with
                                      streaming content.

    Returns:
        None

    Side effects:
        - Updates the Streamlit UI with streaming tokens and tool call information.
        - Modifies the session state to include the final AI message and run ID.
        - Handles various events like chain starts/ends, tool calls, and model outputs.
    """
    processor = EventProcessor(st, client, stream_handler)
    processor.process_events()
