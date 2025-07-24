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

from pathlib import Path

import pytest
import yaml

from frontend.utils.local_chat_history import LocalChatMessageHistory


@pytest.fixture
def chat_history(tmp_path: Path) -> LocalChatMessageHistory:
    """Create a temporary chat history instance"""
    return LocalChatMessageHistory(
        user_id="test_user", session_id="test_session", base_dir=str(tmp_path)
    )


def test_init_creates_directory(tmp_path: Path) -> None:
    """Test directory creation on initialization"""
    user_dir = tmp_path / "test_user"
    assert not user_dir.exists()

    LocalChatMessageHistory(
        user_id="test_user", session_id="test_session", base_dir=str(tmp_path)
    )

    assert user_dir.exists()


def test_get_session(chat_history: LocalChatMessageHistory) -> None:
    """Test session ID and file path update"""
    chat_history.get_session("new_session")
    assert chat_history.session_id == "new_session"
    assert chat_history.session_file.endswith("new_session.yaml")


def test_upsert_session(chat_history: LocalChatMessageHistory) -> None:
    """Test session update/insert"""
    session = {
        "title": "Test Chat",
        "messages": [
            {"type": "human", "content": "Hello"},
            {"type": "ai", "content": "Hi there"},
        ],
    }

    chat_history.upsert_session(session)

    # Verify file was created
    assert Path(chat_history.session_file).exists()

    # Verify content
    with open(chat_history.session_file, encoding="utf-8") as f:
        saved_data = yaml.safe_load(f)
    assert len(saved_data) == 1
    assert saved_data[0]["title"] == "Test Chat"
    assert len(saved_data[0]["messages"]) == 2


def test_get_all_conversations(chat_history: LocalChatMessageHistory) -> None:
    """Test retrieving all conversations"""
    # Create some test conversations
    sessions = {
        "session1": {"title": "Chat 1", "messages": []},
        "session2": {"title": "Chat 2", "messages": []},
    }

    for session_id, session in sessions.items():
        chat_history.get_session(session_id)
        chat_history.upsert_session(session)

    conversations = chat_history.get_all_conversations()
    assert len(conversations) == 2
    assert "session1" in conversations
    assert "session2" in conversations
