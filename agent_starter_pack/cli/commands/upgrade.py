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

"""Upgrade command for upgrading existing projects to newer ASP versions."""

import difflib
import logging
import pathlib
import shlex
import shutil
import subprocess
import tempfile

import click
from rich.console import Console
from rich.prompt import Prompt

from ..utils.generation_metadata import metadata_to_cli_args
from ..utils.language import (
    get_language_config,
    update_asp_version,
)
from ..utils.logging import handle_cli_error
from ..utils.upgrade import (
    DependencyChange,
    FileCompareResult,
    compare_all_files,
    group_results_by_action,
    merge_pyproject_dependencies,
    write_merged_dependencies,
)
from ..utils.version import get_current_version
from .enhance import get_project_asp_config

console = Console()

# Maximum characters to display when showing diffs
MAX_DIFF_DISPLAY_CHARS = 2000


def _ensure_uvx_available() -> bool:
    """Check if uvx is available."""
    try:
        subprocess.run(["uvx", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _run_create_command(
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


def _display_version_header(old_version: str, new_version: str) -> None:
    """Display the upgrade version header."""
    console.print()
    console.print(f"[bold blue]📦 Upgrading {old_version} → {new_version}[/bold blue]")
    console.print()


def _display_results(
    groups: dict[str, list[FileCompareResult]],
    dep_changes: list[DependencyChange],
    dry_run: bool = False,
) -> None:
    """Display the upgrade results grouped by action."""
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
            "[bold cyan]Preserving (you modified, ASP unchanged):[/bold cyan]"
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
        console.print("[bold yellow]New files in ASP:[/bold yellow]")
        for result in groups["new"]:
            console.print(f"  [yellow]+[/yellow] {result.path}")
        console.print()

    if groups["removed"]:
        console.print("[bold yellow]Removed in ASP:[/bold yellow]")
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


def _handle_conflict(
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
                    tofile=f"New ASP version: {result.path}",
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


def _copy_file(src: pathlib.Path, dst: pathlib.Path) -> bool:
    """Copy a file, creating parent directories as needed."""
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _apply_changes(
    groups: dict[str, list[FileCompareResult]],
    project_dir: pathlib.Path,
    new_template_dir: pathlib.Path,
    auto_approve: bool,
    dry_run: bool,
) -> dict[str, int]:
    """Apply the upgrade changes to the project."""
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
        if _copy_file(new_template_dir / result.path, project_dir / result.path):
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
            if _copy_file(new_template_dir / result.path, project_dir / result.path):
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
        action = _handle_conflict(result, project_dir, new_template_dir, auto_approve)
        if action == "updated":
            if _copy_file(new_template_dir / result.path, project_dir / result.path):
                counts["conflicts_updated"] += 1
        elif action == "kept":
            counts["conflicts_kept"] += 1
        else:
            counts["skipped"] += 1

    return counts


@click.command()
@click.argument(
    "project_path",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
    required=False,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without applying them",
)
@click.option(
    "--auto-approve",
    "-y",
    is_flag=True,
    help="Auto-apply non-conflicting changes without prompts",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
@handle_cli_error
def upgrade(
    project_path: pathlib.Path,
    dry_run: bool,
    auto_approve: bool,
    debug: bool,
) -> None:
    """Upgrade project to newer agent-starter-pack version.

    Compares your project against both old and new template versions to
    intelligently apply updates while preserving your customizations.

    Uses 3-way comparison:
    - If you didn't modify a file, it's auto-updated
    - If ASP didn't change a file, your modifications are preserved
    - If both changed, you're prompted to resolve the conflict
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG, force=True)
        console.print("[dim]Debug mode enabled[/dim]")

    # Resolve project path
    project_dir = project_path.resolve()

    metadata = get_project_asp_config(project_dir)
    if not metadata:
        console.print(
            "[bold red]Error:[/bold red] No agent-starter-pack metadata found."
        )
        console.print(
            "Ensure pyproject.toml has \\[tool.agent-starter-pack] section "
            "or .asp.toml has \\[project] section."
        )
        raise SystemExit(1)

    # Get language from metadata for language-aware operations
    language = metadata.get("language", "python")

    old_version = metadata.get("asp_version")
    if not old_version:
        console.print(
            "[bold red]Error:[/bold red] No asp_version found in project metadata."
        )
        lang_config = get_language_config(language)
        config_file = lang_config.get("config_file", "pyproject.toml")
        version_key = lang_config.get("version_key", "asp_version")
        console.print(
            f"The project metadata is missing the version. "
            f"Please ensure {config_file} has {version_key} set."
        )
        raise SystemExit(1)

    new_version = get_current_version()

    # Check if upgrade is needed
    if old_version == new_version:
        console.print(
            f"[bold green]✅[/bold green] Project is already at version {new_version}"
        )
        return

    # Check if uvx is available for re-templating old version
    if not _ensure_uvx_available():
        console.print(
            "[bold red]Error:[/bold red] 'uvx' is required for upgrade but not installed."
        )
        console.print(
            "[dim]Install uv to enable upgrade: curl -LsSf https://astral.sh/uv/install.sh | sh[/dim]"
        )
        raise SystemExit(1)

    _display_version_header(old_version, new_version)

    # Get project name and CLI args from metadata
    project_name = metadata.get("name", project_dir.name)
    agent_directory = metadata.get("agent_directory", "app")
    cli_args = metadata_to_cli_args(metadata)

    # Create temp directories for re-templating
    temp_base = pathlib.Path(tempfile.mkdtemp(prefix="asp_upgrade_"))
    old_template_dir = temp_base / "old"
    new_template_dir = temp_base / "new"

    try:
        console.print("[dim]Generating template versions for comparison...[/dim]")

        # Re-template old version
        console.print(f"[dim]  - Old template (v{old_version})...[/dim]")
        if not _run_create_command(
            cli_args, old_template_dir, project_name, old_version
        ):
            console.print(
                f"[bold red]Error:[/bold red] Failed to generate old template (v{old_version})"
            )
            console.print(
                "[dim]This version may not be available. Try upgrading from a more recent version.[/dim]"
            )
            raise SystemExit(1)

        # Re-template new version
        console.print(f"[dim]  - New template (v{new_version})...[/dim]")
        if not _run_create_command(cli_args, new_template_dir, project_name):
            console.print(
                f"[bold red]Error:[/bold red] Failed to generate new template (v{new_version})"
            )
            raise SystemExit(1)

        # The templates are created in subdirectories named after the project
        old_template_project = old_template_dir / project_name
        new_template_project = new_template_dir / project_name

        console.print()

        # Compare all files
        console.print("[dim]Comparing files...[/dim]")
        results = compare_all_files(
            project_dir,
            old_template_project,
            new_template_project,
            agent_directory,
        )

        # Group by action
        groups = group_results_by_action(results)

        # Handle dependency merging (only for languages that strip dependencies)
        lang_config = get_language_config(language)
        dep_result = None
        if lang_config.get("strip_dependencies", True):
            dep_result = merge_pyproject_dependencies(
                project_dir / "pyproject.toml",
                old_template_project / "pyproject.toml",
                new_template_project / "pyproject.toml",
            )

        console.print()

        # Display results
        _display_results(groups, dep_result.changes if dep_result else [], dry_run)

        # Check if there's anything to do
        total_changes = (
            len(groups["auto_update"])
            + len(groups["new"])
            + len(groups["removed"])
            + len(groups["conflict"])
        )

        has_dep_changes = dep_result and dep_result.changes
        if total_changes == 0 and not has_dep_changes:
            console.print("[bold green]✅[/bold green] No changes needed!")
            return

        # Confirm before applying
        if not auto_approve and not dry_run:
            prompt_text = "\nProceed with upgrade?"
            if groups["conflict"]:
                prompt_text = "\nProceed? (you'll resolve conflicts next)"
            proceed = Prompt.ask(
                prompt_text,
                choices=["y", "n"],
                default="y",
            )
            if proceed != "y":
                console.print("[yellow]Upgrade cancelled.[/yellow]")
                return

        # Apply changes
        counts = _apply_changes(
            groups,
            project_dir,
            new_template_project,
            auto_approve,
            dry_run,
        )

        # Apply dependency changes (Python only)
        if not dry_run and dep_result and dep_result.changes:
            write_merged_dependencies(
                project_dir / "pyproject.toml",
                dep_result.merged_deps,
            )

        # Update metadata version using language-aware utility
        if not dry_run:
            update_asp_version(project_dir, language, new_version)

        # Summary
        console.print()
        if dry_run:
            console.print(
                "[bold yellow]Dry run complete.[/bold yellow] "
                "Run without --dry-run to apply changes."
            )
        else:
            console.print(f"  Updated: {counts['updated']} files")
            console.print(f"  Added: {counts['added']} files")
            console.print(f"  Removed: {counts['removed']} files")
            if counts["conflicts_kept"] or counts["conflicts_updated"]:
                console.print(
                    f"  Conflicts: {counts['conflicts_updated']} updated, "
                    f"{counts['conflicts_kept']} kept yours"
                )
            console.print()
            console.print("[bold green]✅ Upgrade complete![/bold green]")

    finally:
        # Cleanup temp directories
        shutil.rmtree(temp_base, ignore_errors=True)
