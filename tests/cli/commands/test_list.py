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

from click.testing import CliRunner
from pytest_mock import MockerFixture

from agent_starter_pack.cli.commands.list import list_agents


def test_list_agents_local(mocker: MockerFixture) -> None:
    """Test the list command with local agents."""
    mock_get_agents = mocker.patch(
        "agent_starter_pack.cli.commands.list.get_available_agents",
        return_value={
            "agent1": {"name": "Agent One", "description": "Description one"},
            "agent2": {"name": "Agent Two", "description": "Description two"},
        },
    )

    runner = CliRunner()
    result = runner.invoke(list_agents)

    assert result.exit_code == 0
    assert "Available built-in agents" in result.output
    assert "Agent One" in result.output
    assert "Description one" in result.output
    assert "Agent Two" in result.output
    assert "Description two" in result.output
    mock_get_agents.assert_called_once()
