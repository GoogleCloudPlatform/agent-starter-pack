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

"""Tests for the Google Ads management agent."""

import pytest


def test_agent_imports():
    """Verify agent module can be imported."""
    from app.agent import root_agent, app
    assert root_agent is not None
    assert app is not None


def test_agent_has_tools():
    """Verify agent has the expected tools."""
    from app.agent import root_agent
    tool_names = [t.__name__ for t in root_agent._tools]
    assert "get_account_summary" in tool_names
    assert "list_campaigns" in tool_names
    assert "find_wasted_spend" in tool_names
    assert "get_quality_scores" in tool_names
    assert "get_recommendations" in tool_names


def test_agent_instruction():
    """Verify agent has a system instruction."""
    from app.agent import root_agent
    assert "Google Ads" in root_agent._instruction
    assert "audit" in root_agent._instruction.lower()
