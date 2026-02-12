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

"""Shared backup utility for project directories."""

import datetime
import pathlib
import shutil

import click
from rich.console import Console

BACKUP_BASE_DIR = pathlib.Path.home() / ".agent-starter-pack" / "backups"

# Directories/files to exclude from backups
_BACKUP_IGNORE_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".DS_Store",
    ".vscode",
    ".idea",
    "*.egg-info",
    ".mypy_cache",
    ".ty",
    ".coverage",
    "htmlcov",
    ".tox",
    ".cache",
}


def _backup_ignore_patterns(dir: str, files: list[str]) -> list[str]:
    """Return files to ignore when creating a backup."""
    return [f for f in files if f in _BACKUP_IGNORE_NAMES]


def create_project_backup(
    project_dir: pathlib.Path,
    console: Console | None = None,
    auto_approve: bool = False,
) -> pathlib.Path | None:
    """Create a backup of the project directory.

    Backs up to ~/.agent-starter-pack/backups/<project-name>_<timestamp>/.

    Args:
        project_dir: Path to the project directory to back up.
        console: Rich console for output. Created if not provided.
        auto_approve: If True, skip confirmation prompts on failure.

    Returns:
        Path to the backup directory on success, None if backup failed
        but user chose to continue.

    Raises:
        click.Abort: If backup failed and user chose to cancel.
    """
    if console is None:
        console = Console()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_BASE_DIR / f"{project_dir.name}_{timestamp}"

    console.print("📦 [blue]Creating backup before modification...[/blue]")

    try:
        BACKUP_BASE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copytree(project_dir, backup_dir, ignore=_backup_ignore_patterns)
        console.print(f"Backup created: [cyan]{backup_dir}[/cyan]")
        return backup_dir
    except Exception as e:
        console.print(f"⚠️  [yellow]Warning: Could not create backup: {e}[/yellow]")
        if not auto_approve:
            if not click.confirm("Continue without backup?", default=True):
                raise click.Abort() from e
        return None
