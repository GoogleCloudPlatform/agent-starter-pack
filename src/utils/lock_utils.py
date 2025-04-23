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

"""Utilities for managing uv lock files and dependencies."""

import pathlib
from pathlib import Path
from typing import NamedTuple

import yaml


class AgentConfig(NamedTuple):
    """Configuration for an agent template."""

    targets: set[str]
    dependencies: list[str]


def get_agent_configs(
    agents_dir: pathlib.Path = pathlib.Path("agents"),
) -> dict[str, AgentConfig]:
    """Get all agents and their supported deployment targets.

    Args:
        agents_dir: Path to the agents directory

    Returns:
        Dictionary mapping agent names to their configuration
    """
    agent_configs = {}

    for agent_dir in agents_dir.iterdir():
        if not agent_dir.is_dir():
            continue

        config_file = agent_dir / "template" / ".templateconfig.yaml"
        if not config_file.exists():
            continue

        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        agent_name = agent_dir.name
        settings = config.get("settings", {})

        agent_configs[agent_name] = settings

    return agent_configs


def get_lock_filename(agent_name: str, deployment_target: str) -> str:
    """Generate the lock filename for a given agent and deployment target.

    Args:
        agent_name: Name of the agent
        deployment_target: Target deployment platform

    Returns:
        Formatted lock filename
    """
    return f"uv-{agent_name}-{deployment_target}.lock"


def get_lock_path(agent_name: str, deployment_target: str) -> Path:
    """Get the path to the appropriate lock file."""
    lock_filename = get_lock_filename(agent_name, deployment_target)
    return Path("src/resources/locks") / lock_filename
