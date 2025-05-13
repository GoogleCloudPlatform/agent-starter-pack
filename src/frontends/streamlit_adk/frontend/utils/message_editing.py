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

# fmt: off

from typing import Any

from google.adk.events.event import Event


class MessageEditing:
    """Provides methods for editing, refreshing, and deleting chat messages."""

    @staticmethod
    def edit_message(st: Any, button_idx: int, message_type: str) -> None:
        """Edit a message in the chat history."""
        button_id = f"edit_box_{button_idx}"
        # Handle Event type messages
        message = st.session_state.user_chats[st.session_state["session_id"]]["messages"][button_idx]
        # Convert to Event if it's not already
        event = message if isinstance(message, Event) else Event.model_validate(message)
        # Update the text content in the event
        if hasattr(event.content, 'parts'):
            for part in event.content.parts:
                if hasattr(part, 'text'):
                    part.text = st.session_state[button_id]
                    break
        # Update the message in the session state
        st.session_state.user_chats[st.session_state["session_id"]]["messages"][button_idx] = event.model_dump()

    @staticmethod
    def refresh_message(st: Any, button_idx: int, content: str) -> None:
        """Refresh a message in the chat history."""
        messages = st.session_state.user_chats[st.session_state["session_id"]][
            "messages"
        ]
        st.session_state.user_chats[st.session_state["session_id"]][
            "messages"
        ] = messages[:button_idx]
        st.session_state.modified_prompt = content

    @staticmethod
    def delete_message(st: Any, button_idx: int) -> None:
        """Delete a message from the chat history."""
        messages = st.session_state.user_chats[st.session_state["session_id"]][
            "messages"
        ]
        st.session_state.user_chats[st.session_state["session_id"]][
            "messages"
        ] = messages[:button_idx]
