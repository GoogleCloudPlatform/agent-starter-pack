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

"""Shared language configuration and utilities for CLI commands.

This module centralizes language-specific configuration (Python, Go) used by
extract, enhance, and upgrade commands. It provides:

- LANGUAGE_CONFIGS: Configuration dict for each supported language
- detect_language(): Detect project language from files
- get_asp_config_for_language(): Read ASP config based on language
- get_language_config(): Get config dict for a language
- update_asp_version(): Update version in appropriate config file
"""

import logging
import pathlib
import re
import sys
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# =============================================================================
# Language Configuration
# =============================================================================
# To add a new language, add an entry with the required keys.

LANGUAGE_CONFIGS: dict[str, dict[str, Any]] = {
    "python": {
        "detection_files": ["pyproject.toml"],
        "config_file": "pyproject.toml",
        "config_path": ["tool", "agent-starter-pack"],
        "version_key": "asp_version",
        "project_files": ["pyproject.toml"],
        "lock_file": "uv.lock",
        "lock_command": ["uv", "lock"],
        "lock_command_name": "uv lock",
        "strip_dependencies": True,
        "display_name": "Python",
    },
    "go": {
        "detection_files": ["go.mod"],
        "config_file": ".asp.toml",
        "config_path": ["project"],
        "version_key": "version",
        "project_files": ["go.mod", "go.sum", ".asp.toml"],
        "lock_file": "go.sum",
        "lock_command": ["go", "mod", "tidy"],
        "lock_command_name": "go mod tidy",
        "strip_dependencies": False,
        "display_name": "Go",
    },
}


def detect_language(project_dir: pathlib.Path) -> str:
    """Detect the project language using LANGUAGE_CONFIGS.

    Detection order:
    1. Check .asp.toml for explicit language field
    2. Check for language-specific detection files (go.mod, pyproject.toml, etc.)
    3. Default to Python

    Args:
        project_dir: Path to the project directory

    Returns:
        Language key (e.g., 'python', 'go')
    """
    # First, check .asp.toml for explicit language declaration
    asp_toml_path = project_dir / ".asp.toml"
    if asp_toml_path.exists():
        try:
            with open(asp_toml_path, "rb") as f:
                asp_data = tomllib.load(f)
            language = asp_data.get("project", {}).get("language")
            if language and language in LANGUAGE_CONFIGS:
                return language
        except Exception:
            pass

    # Check each language's detection files (non-Python first to avoid false positives)
    # Python has pyproject.toml which is common, so check other languages first
    for lang in ["go", "python"]:  # Order matters: more specific first
        config = LANGUAGE_CONFIGS.get(lang)
        if config:
            for detection_file in config.get("detection_files", []):
                if (project_dir / detection_file).exists():
                    # For Python, also need to check it's not just a pyproject.toml
                    # for a Go project (Go projects don't have pyproject.toml)
                    if lang == "python":
                        # Only return python if no other language indicators exist
                        return lang
                    return lang

    # Default to Python
    return "python"


def get_asp_config_for_language(
    project_dir: pathlib.Path, language: str
) -> dict[str, Any] | None:
    """Read ASP config based on language configuration.

    Uses LANGUAGE_CONFIGS to determine where to look for config.

    Args:
        project_dir: Path to the project directory
        language: Language key (e.g., 'python', 'go')

    Returns:
        The ASP config dict if found, None otherwise
    """
    lang_config = LANGUAGE_CONFIGS.get(language)
    if not lang_config:
        return None

    config_file = lang_config.get("config_file")
    config_path = lang_config.get("config_path", [])

    if not config_file:
        return None

    config_file_path = project_dir / config_file
    if not config_file_path.exists():
        return None

    try:
        with open(config_file_path, "rb") as f:
            data = tomllib.load(f)

        # Navigate to the config path (e.g., ["tool", "agent-starter-pack"])
        result = data
        for key in config_path:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
            if result is None:
                return None

        return result if isinstance(result, dict) else None
    except Exception as e:
        logging.debug(f"Could not read config from {config_file}: {e}")
        return None


def get_language_config(language: str) -> dict[str, Any]:
    """Get the configuration dict for a language.

    Args:
        language: Language key (e.g., 'python', 'go')

    Returns:
        The language configuration dict, or Python config as fallback
    """
    return LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS["python"])


def update_asp_version(
    project_dir: pathlib.Path,
    language: str,
    new_version: str,
) -> bool:
    """Update the ASP version in the appropriate config file.

    For Python: Updates asp_version in pyproject.toml [tool.agent-starter-pack]
    For Go: Updates version in .asp.toml [project]

    Args:
        project_dir: Path to project directory
        language: Language key (e.g., 'python', 'go')
        new_version: New ASP version string

    Returns:
        True if successful, False otherwise
    """
    lang_config = get_language_config(language)
    config_file = lang_config.get("config_file")
    version_key = lang_config.get("version_key", "asp_version")

    if not config_file:
        return False

    config_path = project_dir / config_file
    if not config_path.exists():
        return False

    try:
        content = config_path.read_text(encoding="utf-8")

        # Use regex to update the version key
        # Pattern matches: version_key = "value" or version_key = 'value'
        pattern = rf'({version_key}\s*=\s*")[^"]*(")'
        replacement = rf"\g<1>{new_version}\g<2>"
        updated_content = re.sub(pattern, replacement, content)

        # If no match with double quotes, try single quotes
        if updated_content == content:
            pattern = rf"({version_key}\s*=\s*')[^']*(')"
            replacement = rf"\g<1>{new_version}\g<2>"
            updated_content = re.sub(pattern, replacement, content)

        if updated_content != content:
            config_path.write_text(updated_content, encoding="utf-8")
            return True
        else:
            logging.warning(f"Could not find {version_key} in {config_file}")
            return False

    except Exception as e:
        logging.warning(f"Could not update {version_key} in {config_file}: {e}")
        return False
