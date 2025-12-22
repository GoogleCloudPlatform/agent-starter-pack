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

from __future__ import annotations

from a2a.types import (
    FilePart,
    FileWithBytes,
    FileWithUri,
    Message,
    Part,
    Role,
    TaskState,
    TextPart,
)
from langchain_core.messages import AIMessage, ToolMessage


class LangGraphTaskResultAggregator:
    """Aggregates streaming LangGraph messages into a final consolidated result."""

    def __init__(self) -> None:
        self._task_state = TaskState.working
        self._accumulated_content = ""  # Accumulate text content across chunks
        self._task_status_message: Message | None = None
        self._media_parts: list[Part] = []  # Track media parts from tool responses

    def process_message(self, message: AIMessage | ToolMessage) -> None:
        """Process a streaming message chunk from LangGraph."""

        # Handle tool responses to extract media
        if isinstance(message, ToolMessage):
            self._extract_media_from_tool_response(message)
            return

        if not message.content:
            return

        if isinstance(message.content, str):
            self._accumulated_content += message.content

        elif isinstance(message.content, list):
            for item in message.content:
                if isinstance(item, str):
                    self._accumulated_content += item
                elif isinstance(item, dict) and item.get("type") == "text":
                    self._accumulated_content += item.get("text", "")

        # Update the task status message with current accumulated content
        if self._accumulated_content or self._media_parts:
            parts = []
            if self._accumulated_content:
                parts.append(Part(root=TextPart(text=self._accumulated_content)))
            parts.extend(self._media_parts)

            self._task_status_message = Message(
                message_id="aggregated",
                role=Role.agent,
                parts=parts,
            )

    def _extract_media_from_tool_response(self, message: ToolMessage) -> None:
        """Extract media parts from a ToolMessage."""

        if not message.content:
            return

        if isinstance(message.content, list):
            for item in message.content:
                if isinstance(item, dict):
                    content_type = item.get("type")
                    if content_type == "image":
                        self._media_parts.append(
                            self._convert_media_to_a2a_part(item, "image")
                        )
                    elif content_type == "audio":
                        self._media_parts.append(
                            self._convert_media_to_a2a_part(item, "audio")
                        )
                    elif content_type == "video":
                        self._media_parts.append(
                            self._convert_media_to_a2a_part(item, "video")
                        )

    def _convert_media_to_a2a_part(
        self, content: dict[str, str], media_type: str
    ) -> Part:
        """Convert a media content block to an A2A Part."""

        mime_type = content.get("mime_type")

        if "url" in content:
            return Part(
                root=FilePart(file=FileWithUri(uri=content["url"], mime_type=mime_type))
            )
        elif "base64" in content:
            return Part(
                root=FilePart(
                    file=FileWithBytes(bytes=content["base64"], mime_type=mime_type)
                )
            )
        elif "file_id" in content:
            # For now, store file_id as a URI
            return Part(
                root=FilePart(
                    file=FileWithUri(
                        uri=f"file://{content['file_id']}", mime_type=mime_type
                    )
                )
            )

        # Fallback to empty text part
        return Part(root=TextPart(text=f"[{media_type} content]"))

    def get_final_parts(self) -> list[Part]:
        """Get the final consolidated parts for the artifact."""

        parts = []
        if self._accumulated_content:
            parts.append(Part(root=TextPart(text=self._accumulated_content)))
        parts.extend(self._media_parts)
        return parts if parts else []

    @property
    def task_state(self) -> TaskState:
        """Get the current task state."""
        return self._task_state

    @property
    def task_status_message(self) -> Message | None:
        """Get the current task status message with accumulated content."""
        return self._task_status_message

    def set_failed(self, error_message: str) -> None:
        """Set the task state to failed."""
        self._task_state = TaskState.failed
        self._task_status_message = Message(
            message_id="error",
            role=Role.agent,
            parts=[Part(root=TextPart(text=error_message))],
        )
