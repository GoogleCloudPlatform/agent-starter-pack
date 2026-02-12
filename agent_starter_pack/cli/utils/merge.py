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

"""Shared merge utilities for upgrade and enhance commands.

Functions for generating templates, displaying comparison results,
resolving conflicts, and applying file changes.
"""

import difflib
import logging
import pathlib
import shlex
import shutil
import subprocess

from rich.console import Console
from rich.prompt import Prompt

from .upgrade import DependencyChange, FileCompareResult

console = Console()

# Maximum characters to display when showing diffs
MAX_DIFF_DISPLAY_CHARS = 2000


def run_create_command(
    args: list[str],
    output_dir: pathlib.Path,
    project_name: str,
    version: str | None = None,
) -> bool:
    """Run the create command to generate a template.

    Args:
        args: CLI arguments for create command
        output_dir: Directory to output the template
        project_name: Name for the project
        version: Optional ASP version to use (uses uvx if specified)

    Returns:
        True if successful, False otherwise
    """
    # Build the command
    if version:
        cmd = ["uvx", f"agent-starter-pack@{version}", "create"]
    else:
        cmd = ["agent-starter-pack", "create"]

    cmd.extend([project_name])
    cmd.extend(["--output-dir", str(output_dir)])
    cmd.extend(["--auto-approve", "--skip-deps", "--skip-checks"])
    cmd.extend(args)

    logging.debug(f"Running command: {shlex.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            logging.error(f"Command failed: {result.stderr}")
            return False

        return True
    except subprocess.TimeoutExpired:
        logging.error("Command timed out")
        return False
    except Exception as e:
        logging.error(f"Error running command: {e}")
        return False


def display_results(
    groups: dict[str, list[FileCompareResult]],
    dep_changes: list[DependencyChange] | None = None,
    dry_run: bool = False,
) -> None:
    """Display the comparison results grouped by action."""
    if dep_changes is None:
        dep_changes = []

    if groups["auto_update"]:
        console.print("[bold green]Auto-updating (unchanged by you):[/bold green]")
        for result in groups["auto_update"]:
            console.print(f"  [green]✓[/green] {result.path}")
        console.print()

    preserved_user_modified = [
        r for r in groups["preserve"] if r.preserve_type == "asp_unchanged"
    ]
    if preserved_user_modified:
        console.print(
            "[bold cyan]Preserving (you modified, template unchanged):[/bold cyan]"
        )
        for result in preserved_user_modified:
            console.print(f"  [cyan]✓[/cyan] {result.path}")
        console.print()

    skipped = [
        r for r in groups["skip"] if r.category in ("agent_code", "config_files")
    ]
    if skipped:
        console.print("[dim]Skipping (your code):[/dim]")
        for result in skipped:
            console.print(f"  [dim]-[/dim] {result.path}")
        console.print()

    if groups["new"]:
        console.print("[bold yellow]New files:[/bold yellow]")
        for result in groups["new"]:
            console.print(f"  [yellow]+[/yellow] {result.path}")
        console.print()

    if groups["removed"]:
        console.print("[bold yellow]Removed files:[/bold yellow]")
        for result in groups["removed"]:
            console.print(f"  [yellow]-[/yellow] {result.path}")
        console.print()

    if groups["conflict"]:
        console.print("[bold red]Conflicts (both changed):[/bold red]")
        for result in groups["conflict"]:
            console.print(f"  [red]⚠[/red]  {result.path}")
        if not dry_run:
            console.print("[dim]  You'll be prompted to resolve each conflict.[/dim]")
        console.print()

    if dep_changes:
        console.print("[bold]Dependencies:[/bold]")
        for change in dep_changes:
            if change.change_type == "updated":
                console.print(
                    f"  [green]✓[/green] Updated: {change.name} "
                    f"{change.old_version} → {change.new_version}"
                )
            elif change.change_type == "added":
                console.print(
                    f"  [green]+[/green] Added: {change.name}{change.new_version}"
                )
            elif change.change_type == "kept":
                console.print(
                    f"  [cyan]✓[/cyan] Kept: {change.name}{change.old_version}"
                )
            elif change.change_type == "removed":
                console.print(
                    f"  [yellow]-[/yellow] Removed: {change.name}{change.old_version}"
                )
        console.print()


def handle_conflict(
    result: FileCompareResult,
    project_dir: pathlib.Path,
    new_template_dir: pathlib.Path,
    auto_approve: bool,
) -> str:
    """Handle a file conflict interactively.

    Args:
        result: The conflict result
        project_dir: Path to current project
        new_template_dir: Path to new template
        auto_approve: If True, keep user's version

    Returns:
        Action taken: "kept", "updated", or "skipped"
    """
    if auto_approve:
        console.print(f"  [dim]Keeping your version: {result.path}[/dim]")
        return "kept"

    console.print(f"\n[bold yellow]Conflict: {result.path}[/bold yellow]")
    console.print(f"  Reason: {result.reason}")

    choice = Prompt.ask(
        "  (v)iew diff, (k)eep yours, (u)se new, (s)kip",
        choices=["v", "k", "u", "s"],
        default="k",
    )

    if choice == "v":
        # Show diff using Python's difflib (cross-platform)
        current_file = project_dir / result.path
        new_file = new_template_dir / result.path

        try:
            current_lines = current_file.read_text(encoding="utf-8").splitlines(
                keepends=True
            )
            new_lines = new_file.read_text(encoding="utf-8").splitlines(keepends=True)

            diff_lines = list(
                difflib.unified_diff(
                    current_lines,
                    new_lines,
                    fromfile=f"Your version: {result.path}",
                    tofile=f"New version: {result.path}",
                )
            )
            diff_output = "".join(diff_lines)

            console.print()
            if diff_output:
                # Limit output to a reasonable length
                if len(diff_output) > MAX_DIFF_DISPLAY_CHARS:
                    console.print(diff_output[:MAX_DIFF_DISPLAY_CHARS])
                    console.print("[dim]... (truncated)[/dim]")
                else:
                    console.print(diff_output)
            else:
                console.print("[dim]No differences found[/dim]")
        except Exception as e:
            console.print(f"[red]Could not show diff: {e}[/red]")

        # Ask again after viewing
        choice = Prompt.ask(
            "  (k)eep yours, (u)se new, (s)kip",
            choices=["k", "u", "s"],
            default="k",
        )

    if choice == "k":
        console.print("  [cyan]Keeping your version[/cyan]")
        return "kept"
    elif choice == "u":
        return "updated"
    else:
        return "skipped"


def copy_file(src: pathlib.Path, dst: pathlib.Path) -> bool:
    """Copy a file, creating parent directories as needed."""
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def apply_changes(
    groups: dict[str, list[FileCompareResult]],
    project_dir: pathlib.Path,
    new_template_dir: pathlib.Path,
    auto_approve: bool,
    dry_run: bool,
) -> dict[str, int]:
    """Apply file changes to the project."""
    counts = {
        "updated": 0,
        "added": 0,
        "removed": 0,
        "skipped": 0,
        "conflicts_kept": 0,
        "conflicts_updated": 0,
    }

    if dry_run:
        console.print("[bold yellow]Dry run - no changes made[/bold yellow]")
        return counts

    for result in groups["auto_update"]:
        if copy_file(new_template_dir / result.path, project_dir / result.path):
            counts["updated"] += 1

    for result in groups["new"]:
        should_add = (
            auto_approve
            or Prompt.ask(
                f"  Add new file {result.path}?", choices=["y", "n"], default="y"
            )
            == "y"
        )
        if should_add:
            if copy_file(new_template_dir / result.path, project_dir / result.path):
                counts["added"] += 1
        else:
            counts["skipped"] += 1

    for result in groups["removed"]:
        file_path = project_dir / result.path
        should_remove = (
            auto_approve
            or Prompt.ask(
                f"  Remove file {result.path}?", choices=["y", "n"], default="y"
            )
            == "y"
        )
        if should_remove and file_path.exists():
            file_path.unlink()
            counts["removed"] += 1
        elif not should_remove:
            counts["skipped"] += 1

    if groups["conflict"]:
        console.print()
        console.print("[bold]Resolving conflicts:[/bold]")

    for result in groups["conflict"]:
        action = handle_conflict(result, project_dir, new_template_dir, auto_approve)
        if action == "updated":
            if copy_file(new_template_dir / result.path, project_dir / result.path):
                counts["conflicts_updated"] += 1
        elif action == "kept":
            counts["conflicts_kept"] += 1
        else:
            counts["skipped"] += 1

    return counts
