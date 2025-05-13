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

from unittest.mock import MagicMock, patch

import pytest

from frontend.side_bar import SideBar


@pytest.fixture
def mock_streamlit() -> MagicMock:
    st = MagicMock()
    st.sidebar = MagicMock()
    st.session_state = MagicMock()
    st.session_state.session_id = "test-session"
    st.session_state.user_chats = {
        "test-session": {"messages": [], "title": "Test Chat"}
    }
    st.session_state.uploader_key = 0
    st.session_state.checkbox_state = True
    st.session_state.gcs_uris_to_be_sent = ""
    # Mock columns to return list of 3 MagicMocks
    st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

    # Configure session_state getitem to return values
    def getitem(key: str) -> str:
        if key == "session_id":
            return "test-session"
        if key == "gcs_uris_to_be_sent":
            return ""
        raise KeyError(key)

    st.session_state.__getitem__.side_effect = getitem

    return st


def test_sidebar_initialization(mock_streamlit: MagicMock) -> None:
    """Test SideBar initialization"""
    sidebar = SideBar(mock_streamlit)
    assert sidebar.st == mock_streamlit


@patch("os.path.exists")
def test_init_side_bar_local_agent(
    mock_exists: MagicMock, mock_streamlit: MagicMock
) -> None:
    """Test sidebar initialization with local agent"""
    mock_exists.return_value = False
    sidebar = SideBar(mock_streamlit)

    mock_streamlit.sidebar.__enter__ = MagicMock(return_value=mock_streamlit.sidebar)
    mock_streamlit.sidebar.__exit__ = MagicMock(return_value=None)

    mock_streamlit.selectbox.return_value = "Local Agent"
    mock_streamlit.text_input.return_value = "app.agent_engine_app.AgentEngineApp"

    sidebar.init_side_bar()

    assert sidebar.agent_callable_path == "app.agent_engine_app.AgentEngineApp"
    assert sidebar.remote_agent_engine_id is None
    assert sidebar.url_input_field is None
    assert sidebar.should_authenticate_request is False


@patch("os.path.exists")
def test_init_side_bar_remote_engine_id(
    mock_exists: MagicMock, mock_streamlit: MagicMock
) -> None:
    """Test sidebar initialization with remote agent engine ID"""
    mock_exists.return_value = False
    sidebar = SideBar(mock_streamlit)

    mock_streamlit.sidebar.__enter__ = MagicMock(return_value=mock_streamlit.sidebar)
    mock_streamlit.sidebar.__exit__ = MagicMock(return_value=None)

    mock_streamlit.selectbox.return_value = "Remote Agent Engine ID"
    mock_streamlit.text_input.return_value = "test-engine-id"

    sidebar.init_side_bar()

    assert sidebar.remote_agent_engine_id == "test-engine-id"
    assert sidebar.agent_callable_path is None
    assert sidebar.url_input_field is None
    assert sidebar.should_authenticate_request is False


@patch("os.path.exists")
def test_init_side_bar_remote_url_no_auth(
    mock_exists: MagicMock, mock_streamlit: MagicMock
) -> None:
    """Test sidebar initialization with remote URL without authentication"""
    mock_exists.return_value = True
    sidebar = SideBar(mock_streamlit)

    mock_streamlit.sidebar.__enter__ = MagicMock(return_value=mock_streamlit.sidebar)
    mock_streamlit.sidebar.__exit__ = MagicMock(return_value=None)

    mock_streamlit.selectbox.return_value = "Remote URL"
    mock_streamlit.text_input.return_value = "http://test.url"
    mock_streamlit.checkbox.return_value = False

    sidebar.init_side_bar()

    assert sidebar.url_input_field == "http://test.url"
    assert sidebar.agent_callable_path is None
    assert sidebar.remote_agent_engine_id is None
    assert sidebar.should_authenticate_request is False


@patch("os.path.exists")
def test_init_side_bar_remote_url_with_auth(
    mock_exists: MagicMock, mock_streamlit: MagicMock
) -> None:
    """Test sidebar initialization with remote URL with authentication"""
    mock_exists.return_value = True
    sidebar = SideBar(mock_streamlit)

    mock_streamlit.sidebar.__enter__ = MagicMock(return_value=mock_streamlit.sidebar)
    mock_streamlit.sidebar.__exit__ = MagicMock(return_value=None)

    mock_streamlit.selectbox.return_value = "Remote URL"
    mock_streamlit.text_input.return_value = "http://test.url"
    mock_streamlit.checkbox.return_value = True

    sidebar.init_side_bar()

    assert sidebar.url_input_field == "http://test.url"
    assert sidebar.agent_callable_path is None
    assert sidebar.remote_agent_engine_id is None
    assert sidebar.should_authenticate_request is True
