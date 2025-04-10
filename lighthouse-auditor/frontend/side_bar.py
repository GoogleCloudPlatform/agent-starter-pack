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

# ruff: noqa: RUF015
import json
import os
import uuid
from typing import Any

from frontend.utils.chat_utils import save_chat
from frontend.utils.multimodal_utils import (
    HELP_GCS_CHECKBOX,
    HELP_MESSAGE_MULTIMODALITY,
    upload_files_to_gcs,
)

EMPTY_CHAT_NAME = "Empty chat"
NUM_CHAT_IN_RECENT = 3
DEFAULT_BASE_URL = "http://localhost:8000/"

DEFAULT_REMOTE_AGENT_ENGINE_ID = "N/A"
if os.path.exists("deployment_metadata.json"):
    with open("deployment_metadata.json") as f:
        DEFAULT_REMOTE_AGENT_ENGINE_ID = json.load(f)["remote_agent_engine_id"]
DEFAULT_AGENT_CALLABLE_PATH = "app.agent_engine_app.AgentEngineApp"


class SideBar:
    """Manages the sidebar components of the Streamlit application."""

    def __init__(self, st: Any) -> None:
        """
        Initialize the SideBar.

        Args:
            st (Any): The Streamlit object for rendering UI components.
        """
        self.st = st

    def init_side_bar(self) -> None:
        """Initialize and render the sidebar components."""
        with self.st.sidebar:
            default_agent_type = (
                "Remote URL" if os.path.exists("Dockerfile") else "Local Agent"
            )
            use_agent_path = self.st.selectbox(
                "Select Agent Type",
                ["Local Agent", "Remote Agent Engine ID", "Remote URL"],
                index=["Local Agent", "Remote Agent Engine ID", "Remote URL"].index(
                    default_agent_type
                ),
                help="'Local Agent' uses a local implementation, 'Remote Agent Engine ID' connects to a deployed Vertex AI agent, and 'Remote URL' connects to a custom endpoint.",
            )

            if use_agent_path == "Local Agent":
                self.agent_callable_path = self.st.text_input(
                    label="Agent Callable Path",
                    value=os.environ.get(
                        "AGENT_CALLABLE_PATH", DEFAULT_AGENT_CALLABLE_PATH
                    ),
                )
                self.remote_agent_engine_id = None
                self.url_input_field = None
                self.should_authenticate_request = False
            elif use_agent_path == "Remote Agent Engine ID":
                self.remote_agent_engine_id = self.st.text_input(
                    label="Remote Agent Engine ID",
                    value=os.environ.get(
                        "REMOTE_AGENT_ENGINE_ID", DEFAULT_REMOTE_AGENT_ENGINE_ID
                    ),
                )
                self.agent_callable_path = None
                self.url_input_field = None
                self.should_authenticate_request = False
            else:
                self.url_input_field = self.st.text_input(
                    label="Service URL",
                    value=os.environ.get("SERVICE_URL", DEFAULT_BASE_URL),
                )
                self.should_authenticate_request = self.st.checkbox(
                    label="Authenticate request",
                    value=False,
                    help="If checked, any request to the server will contain an"
                    "Identity token to allow authentication. "
                    "See the Cloud Run documentation to know more about authentication:"
                    "https://cloud.google.com/run/docs/authenticating/service-to-service",
                )
                self.agent_callable_path = None
                self.remote_agent_engine_id = None

            col1, col2, col3 = self.st.columns(3)
            with col1:
                if self.st.button("+ New chat"):
                    if (
                        len(
                            self.st.session_state.user_chats[
                                self.st.session_state["session_id"]
                            ]["messages"]
                        )
                        > 0
                    ):
                        self.st.session_state.run_id = None

                        self.st.session_state["session_id"] = str(uuid.uuid4())
                        self.st.session_state.session_db.get_session(
                            session_id=self.st.session_state["session_id"],
                        )
                        self.st.session_state.user_chats[
                            self.st.session_state["session_id"]
                        ] = {
                            "title": EMPTY_CHAT_NAME,
                            "messages": [],
                        }

            with col2:
                if self.st.button("Delete chat"):
                    self.st.session_state.run_id = None
                    self.st.session_state.session_db.clear()
                    self.st.session_state.user_chats.pop(
                        self.st.session_state["session_id"]
                    )
                    if len(self.st.session_state.user_chats) > 0:
                        chat_id = list(self.st.session_state.user_chats.keys())[0]
                        self.st.session_state["session_id"] = chat_id
                        self.st.session_state.session_db.get_session(
                            session_id=self.st.session_state["session_id"],
                        )
                    else:
                        self.st.session_state["session_id"] = str(uuid.uuid4())
                        self.st.session_state.user_chats[
                            self.st.session_state["session_id"]
                        ] = {
                            "title": EMPTY_CHAT_NAME,
                            "messages": [],
                        }
            with col3:
                if self.st.button("Save chat"):
                    save_chat(self.st)

            self.st.subheader("Recent")  # Style the heading

            all_chats = list(reversed(self.st.session_state.user_chats.items()))
            for chat_id, chat in all_chats[:NUM_CHAT_IN_RECENT]:
                if self.st.button(chat["title"], key=chat_id):
                    self.st.session_state.run_id = None
                    self.st.session_state["session_id"] = chat_id
                    self.st.session_state.session_db.get_session(
                        session_id=self.st.session_state["session_id"],
                    )

            with self.st.expander("Other chats"):
                for chat_id, chat in all_chats[NUM_CHAT_IN_RECENT:]:
                    if self.st.button(chat["title"], key=chat_id):
                        self.st.session_state.run_id = None
                        self.st.session_state["session_id"] = chat_id
                        self.st.session_state.session_db.get_session(
                            session_id=self.st.session_state["session_id"],
                        )

            self.st.divider()
            self.st.header("Upload files from local")
            bucket_name = self.st.text_input(
                label="GCS Bucket for upload",
                value=os.environ.get("BUCKET_NAME", "gs://your-bucket-name"),
            )
            if "checkbox_state" not in self.st.session_state:
                self.st.session_state.checkbox_state = True

            self.st.session_state.checkbox_state = self.st.checkbox(
                "Upload to GCS first (suggested)", value=False, help=HELP_GCS_CHECKBOX
            )

            self.uploaded_files = self.st.file_uploader(
                label="Send files from local",
                accept_multiple_files=True,
                key=f"uploader_images_{self.st.session_state.uploader_key}",
                type=[
                    "png",
                    "jpg",
                    "jpeg",
                    "txt",
                    "docx",
                    "pdf",
                    "rtf",
                    "csv",
                    "tsv",
                    "xlsx",
                ],
            )
            if self.uploaded_files and self.st.session_state.checkbox_state:
                upload_files_to_gcs(self.st, bucket_name, self.uploaded_files)

            self.st.divider()

            self.st.header("Upload files from GCS")
            self.gcs_uris = self.st.text_area(
                "GCS uris (comma-separated)",
                value=self.st.session_state["gcs_uris_to_be_sent"],
                key=f"upload_text_area_{self.st.session_state.uploader_key}",
                help=HELP_MESSAGE_MULTIMODALITY,
            )

            self.st.caption(f"Note: {HELP_MESSAGE_MULTIMODALITY}")
