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

"""Discover and load vertical skill plugins for agent-starter-pack.

This module enables agent-starter-pack to discover and load vertical skills
(domain-specific agent templates) that are installed as plugins via Python
entry points.

Vertical skills extend agent-starter-pack with specialized use cases like:
- Product search agents (e-commerce)
- Customer support agents
- Data science agents
- And more...

Installation:
    pip install vertical-skills

Usage:
    from agent_starter_pack.cli.utils.plugin_discovery import load_vertical_skill_plugins

    skills = load_vertical_skill_plugins()
    for skill_name, skill_config in skills.items():
        print(f"Found skill: {skill_config['display_name']}")
"""

import importlib.metadata
import logging
from typing import Dict, Any, List
from pathlib import Path
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def load_vertical_skill_plugins() -> Dict[str, Any]:
    """Discover and load vertical skill plugins via Python entry points.

    Discovers plugins registered under the 'agent_starter_pack.skills' entry point.
    Each plugin must implement the VerticalSkill protocol providing:
    - name: Unique skill identifier
    - display_name: Human-readable name
    - description: Brief description
    - template_path: Path to cookiecutter templates
    - get_interview_questions(): Domain-specific interview questions
    - process_interview_responses(): Convert responses to template variables

    Returns:
        Dictionary mapping skill names to skill configurations with:
        - name: Skill identifier
        - display_name: Display name
        - description: Description
        - template_path: Path to templates
        - interview_questions: List of questions
        - is_vertical_skill: True (flag for vertical skills)
        - plugin_name: Entry point name
        - skill_instance: Plugin instance

    Example:
        >>> skills = load_vertical_skill_plugins()
        >>> if 'product_search' in skills:
        ...     skill = skills['product_search']
        ...     print(skill['display_name'])  # "Product Search Agent"
        ...     questions = skill['interview_questions']
        ...     instance = skill['skill_instance']
    """
    skills = {}

    try:
        # Get all entry points for agent_starter_pack.skills
        entry_points = importlib.metadata.entry_points()

        # Python 3.10+ uses select(), Python 3.9 uses get()
        if hasattr(entry_points, 'select'):
            skill_entry_points = entry_points.select(group="agent_starter_pack.skills")
        else:
            # Python 3.9 fallback
            skill_entry_points = entry_points.get("agent_starter_pack.skills", [])

        logger.debug(f"Discovered {len(list(skill_entry_points))} skill entry points")

        for entry_point in skill_entry_points:
            try:
                logger.debug(f"Loading plugin: {entry_point.name}")

                # Load the register function from the entry point
                register_func = entry_point.load()

                # Call register() to get the skill instance
                skill = register_func()

                # Validate skill has required attributes
                required_attrs = ['name', 'display_name', 'description', 'template_path']
                for attr in required_attrs:
                    if not hasattr(skill, attr):
                        raise AttributeError(f"Skill missing required attribute: {attr}")

                # Load interview questions
                try:
                    interview_questions = skill.get_interview_questions()
                except Exception as e:
                    logger.warning(f"Failed to load questions for {skill.name}: {e}")
                    interview_questions = []

                # Add to available skills
                skills[skill.name] = {
                    "name": skill.name,
                    "display_name": skill.display_name,
                    "description": skill.description,
                    "template_path": skill.template_path,
                    "interview_questions": interview_questions,
                    "is_vertical_skill": True,
                    "plugin_name": entry_point.name,
                    "skill_instance": skill,  # Keep reference for later use
                    "language": "python",  # Vertical skills are Python-based
                }

                logger.info(f"✓ Loaded vertical skill plugin: {skill.name}")
                console.print(
                    f"  Loaded vertical skill: [cyan]{skill.display_name}[/]",
                    style="dim"
                )

            except Exception as e:
                console.print(
                    f"  Warning: Failed to load skill plugin '{entry_point.name}': {e}",
                    style="yellow"
                )
                logger.warning(f"Plugin load failed: {entry_point.name}", exc_info=True)

    except Exception as e:
        logger.warning(f"Failed to discover skill plugins: {e}", exc_info=True)

    if skills:
        logger.info(f"Loaded {len(skills)} vertical skill plugin(s)")

    return skills


def get_vertical_skill_by_name(skill_name: str) -> Any:
    """Get a specific vertical skill plugin by name.

    Args:
        skill_name: Name of the skill to load

    Returns:
        Skill instance or None if not found

    Example:
        >>> skill = get_vertical_skill_by_name('product_search')
        >>> if skill:
        ...     questions = skill.get_interview_questions()
    """
    skills = load_vertical_skill_plugins()
    if skill_name in skills:
        return skills[skill_name]['skill_instance']
    return None


def list_vertical_skills() -> List[Dict[str, str]]:
    """List all available vertical skills with their metadata.

    Returns:
        List of dictionaries with name, display_name, and description

    Example:
        >>> for skill in list_vertical_skills():
        ...     print(f"{skill['display_name']}: {skill['description']}")
    """
    skills = load_vertical_skill_plugins()
    return [
        {
            "name": config["name"],
            "display_name": config["display_name"],
            "description": config["description"],
        }
        for config in skills.values()
    ]


def is_vertical_skill(agent_name: str) -> bool:
    """Check if an agent name corresponds to a vertical skill plugin.

    Args:
        agent_name: Name of the agent to check

    Returns:
        True if agent is a vertical skill plugin, False otherwise

    Example:
        >>> if is_vertical_skill('product_search'):
        ...     print("This is a vertical skill")
    """
    skills = load_vertical_skill_plugins()
    return agent_name in skills
