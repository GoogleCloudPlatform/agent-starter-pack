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

"""Version checking utilities for the CLI."""

import logging
from importlib.metadata import PackageNotFoundError, version

import requests
from packaging import version as pkg_version
from rich.console import Console

console = Console()

PACKAGE_NAME = "agent-starter-pack"


def get_current_version() -> str:
    """Get the current installed version of the package."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        # For development environments where package isn't installed
        return "0.0.0"  # Default if version can't be determined


def get_latest_version() -> str:
    """Get the latest version available on PyPI."""
    try:
        response = requests.get(f"https://pypi.org/pypi/{PACKAGE_NAME}/json", timeout=2)
        if response.status_code == 200:
            return response.json()["info"]["version"]
        return "0.0.0"
    except Exception:
        return "0.0.0"  # Default if PyPI can't be reached


def check_for_updates() -> tuple[bool, str, str]:
    """Check if a newer version of the package is available.

    Returns:
        Tuple of (needs_update, current_version, latest_version)
    """
    current = get_current_version()
    latest = get_latest_version()

    needs_update = pkg_version.parse(latest) > pkg_version.parse(current)

    return needs_update, current, latest


def display_update_message() -> None:
    """Check for updates and display a message if an update is available."""
    try:
        needs_update, current, latest = check_for_updates()

        if needs_update:
            console.print(
                f"\n[yellow]⚠️  Update available: {current} → {latest}[/]",
                highlight=False,
            )
            console.print(
                f"[yellow]Run `pip install --upgrade {PACKAGE_NAME}` to update.",
                highlight=False,
            )
            console.print(
                f"[yellow]Or, if you used pipx: `pipx upgrade {PACKAGE_NAME}`",
                highlight=False,
            )
            console.print(
                f"[yellow]Or, if you used uv: `uv pip install --upgrade {PACKAGE_NAME}`",
                highlight=False,
            )
    except Exception as e:
        # Don't let version checking errors affect the CLI
        logging.debug(f"Error checking for updates: {e}")
