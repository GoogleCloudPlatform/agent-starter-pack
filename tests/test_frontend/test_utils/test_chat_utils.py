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
from typing import Any

import pytest
import yaml

from frontend.utils.chat_utils import clean_text, sanitize_messages, save_chat


def test_clean_text() -> None:
    """Test text cleaning functionality"""
    test_cases = [
        ("", ""),
        ("\ntest\n", "test"),
        ("test", "test"),
        ("\n\ntest\n\n", "\ntest\n"),
    ]
    for input_text, expected in test_cases:
        assert clean_text(input_text) == expected


def test_sanitize_messages() -> None:
    """Test message sanitization"""
    # Test messages with string content
    string_messages = [
        {"content": "\ntest1\n", "type": "human"},
        {"content": "\ntest2\n", "type": "ai"},
    ]
    sanitized = sanitize_messages(string_messages)
    assert all(msg["content"] == f"test{i + 1}" for i, msg in enumerate(sanitized))

    # Test messages with list content
    list_message = [
        {
            "content": [
                {"type": "text", "text": "\ntest1\n"},
                {"type": "text", "text": "\ntest2\n"},
            ],
            "type": "human",
        }
    ]
    sanitized = sanitize_messages(list_message)
    assert all(
        part["text"] == f"test{i + 1}" for i, part in enumerate(sanitized[0]["content"])
    )


class MockStreamlit:
    """Mock Streamlit class for testing"""

    class SessionState(dict):
        def __init__(self, messages: list | None = None) -> None:
            super().__init__()
            self.user_chats = {"test_session": {"messages": messages or []}}

    def __init__(self, messages: list | None = None) -> None:
        self.session_state = self.SessionState(messages)
        self.session_state["session_id"] = "test_session"

    def toast(self, message: str) -> None:
        pass


@pytest.fixture
def mock_st() -> Any:
    return lambda messages=None: MockStreamlit(messages)


def test_save_chat(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mock_st: Any
) -> None:
    """Test chat saving functionality"""
    test_messages = [{"content": "\ntest message\n", "type": "human"}]
    st = mock_st(test_messages)

    monkeypatch.setattr("frontend.utils.chat_utils.SAVED_CHAT_PATH", str(tmp_path))
    save_chat(st)

    saved_file = tmp_path / "test_session.yaml"
    assert saved_file.exists()

    with open(saved_file, encoding="utf-8") as f:
        saved_data = yaml.safe_load(f)
    assert len(saved_data) == 1
    assert saved_data[0]["messages"][0]["content"] == "test message"


def test_save_chat_empty_messages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mock_st: Any
) -> None:
    """Test saving chat with empty messages"""
    st = mock_st()
    monkeypatch.setattr("frontend.utils.chat_utils.SAVED_CHAT_PATH", str(tmp_path))
    save_chat(st)

    saved_file = tmp_path / "test_session.yaml"
    assert not saved_file.exists()
