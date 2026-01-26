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

"""3-way file comparison and dependency merging for upgrade command."""

import fnmatch
import hashlib
import logging
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Literal

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Patterns use {agent_directory} placeholder replaced at runtime
FILE_CATEGORIES = {
    "agent_code": [  # Never modified
        # Python agent code
        "{agent_directory}/agent.py",
        "{agent_directory}/tools/**/*.py",
        "{agent_directory}/prompts/**/*.py",
        # Go agent code
        "{agent_directory}/agent.go",
        "{agent_directory}/**/*.go",
    ],
    "config_files": [  # Never overwritten
        "deployment/vars/*.tfvars",
        ".env",
        "*.env",
    ],
    "dependencies": [  # Special merge handling
        # Python dependencies
        "pyproject.toml",
        # Go dependencies
        "go.mod",
        "go.sum",
        # Go ASP config
        ".asp.toml",
    ],
    # Everything else is "scaffolding" (3-way compare)
}


# Preserve type literals for type-safe reason matching
PreserveType = Literal["asp_unchanged", "already_current", "unchanged_both", None]


@dataclass
class FileCompareResult:
    """Result of comparing a file across three versions."""

    path: str
    category: str
    action: Literal["auto_update", "preserve", "skip", "conflict", "new", "removed"]
    reason: str
    # For preserve actions, indicates why preserved
    preserve_type: PreserveType = None
    # For conflicts, store the content hashes
    current_hash: str | None = None
    old_template_hash: str | None = None
    new_template_hash: str | None = None


@dataclass
class DependencyChange:
    """A single dependency change."""

    name: str
    change_type: Literal["updated", "added", "removed", "kept"]
    old_version: str | None = None
    new_version: str | None = None


@dataclass
class DependencyMergeResult:
    """Result of merging dependencies."""

    changes: list[DependencyChange] = field(default_factory=list)
    merged_deps: list[str] = field(default_factory=list)
    has_conflicts: bool = False


def _expand_patterns(patterns: list[str], agent_directory: str) -> list[str]:
    """Expand {agent_directory} placeholder in patterns."""
    return [p.replace("{agent_directory}", agent_directory) for p in patterns]


def _matches_any_pattern(path: str, patterns: list[str]) -> bool:
    """Check if path matches any glob pattern, including ** recursive patterns."""
    path = path.replace("\\", "/")

    for pattern in patterns:
        pattern = pattern.replace("\\", "/")

        if fnmatch.fnmatch(path, pattern):
            return True

        if "**" in pattern:
            regex = re.escape(pattern)
            regex = regex.replace(r"\*\*/", "(?:.*/)?")  # **/ = zero or more dirs
            regex = regex.replace(r"\*\*", ".*")
            regex = regex.replace(r"\*", "[^/]*")
            if re.match(f"^{regex}$", path):
                return True

    return False


def categorize_file(path: str, agent_directory: str = "app") -> str:
    """Return category: agent_code, config_files, dependencies, or scaffolding."""
    for category, patterns in FILE_CATEGORIES.items():
        expanded = _expand_patterns(patterns, agent_directory)
        if _matches_any_pattern(path, expanded):
            return category
    return "scaffolding"


def _file_hash(file_path: pathlib.Path) -> str | None:
    """Calculate SHA256 hash of a file's contents."""
    if not file_path.exists():
        return None
    try:
        content = file_path.read_bytes()
        return hashlib.sha256(content).hexdigest()
    except Exception as e:
        logging.warning(f"Could not hash file {file_path}: {e}")
        return None


def three_way_compare(
    relative_path: str,
    project_dir: pathlib.Path,
    old_template_dir: pathlib.Path,
    new_template_dir: pathlib.Path,
    agent_directory: str = "app",
) -> FileCompareResult:
    """Compare file across current, old template, and new template.

    Returns action based on:
    - current == old -> auto-update (user didn't modify)
    - old == new -> preserve (ASP didn't change)
    - all differ -> conflict
    """
    category = categorize_file(relative_path, agent_directory)

    if category == "agent_code":
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="skip",
            reason="Agent code (never modified by upgrade)",
        )

    if category == "config_files":
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="skip",
            reason="Config file (user's environment settings)",
        )

    if category == "dependencies":
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="preserve",
            reason="Dependencies (requires merge handling)",
        )

    current_file = project_dir / relative_path
    old_template_file = old_template_dir / relative_path
    new_template_file = new_template_dir / relative_path

    current_hash = _file_hash(current_file)
    old_hash = _file_hash(old_template_file)
    new_hash = _file_hash(new_template_file)

    # New file in ASP
    if current_hash is None and old_hash is None and new_hash is not None:
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="new",
            reason="New file in ASP",
            new_template_hash=new_hash,
        )

    # File removed in new template
    if current_hash is not None and old_hash is not None and new_hash is None:
        if current_hash == old_hash:
            return FileCompareResult(
                path=relative_path,
                category=category,
                action="removed",
                reason="File removed in ASP (you didn't modify it)",
                current_hash=current_hash,
                old_template_hash=old_hash,
            )
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="conflict",
            reason="File removed in ASP but you modified it",
            current_hash=current_hash,
            old_template_hash=old_hash,
        )

    # File doesn't exist anywhere relevant
    if current_hash is None and new_hash is None:
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="skip",
            reason="File not present",
        )

    # User didn't modify (current == old)
    if current_hash == old_hash and new_hash is not None:
        if old_hash == new_hash:
            return FileCompareResult(
                path=relative_path,
                category=category,
                action="preserve",
                reason="Unchanged in both project and ASP",
                preserve_type="unchanged_both",
                current_hash=current_hash,
                old_template_hash=old_hash,
                new_template_hash=new_hash,
            )
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="auto_update",
            reason="You didn't modify this file",
            current_hash=current_hash,
            old_template_hash=old_hash,
            new_template_hash=new_hash,
        )

    # ASP didn't change (old == new)
    if old_hash == new_hash and current_hash is not None:
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="preserve",
            reason="ASP didn't change this file",
            preserve_type="asp_unchanged",
            current_hash=current_hash,
            old_template_hash=old_hash,
            new_template_hash=new_hash,
        )

    # Already up to date (current == new)
    if current_hash == new_hash:
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="preserve",
            reason="Already up to date",
            preserve_type="already_current",
            current_hash=current_hash,
            old_template_hash=old_hash,
            new_template_hash=new_hash,
        )

    # All three differ -> conflict
    return FileCompareResult(
        path=relative_path,
        category=category,
        action="conflict",
        reason="Both you and ASP modified this file",
        current_hash=current_hash,
        old_template_hash=old_hash,
        new_template_hash=new_hash,
    )


def collect_all_files(
    project_dir: pathlib.Path,
    old_template_dir: pathlib.Path,
    new_template_dir: pathlib.Path,
    exclude_patterns: list[str] | None = None,
) -> set[str]:
    """Collect all unique relative file paths from all three directories."""
    if exclude_patterns is None:
        exclude_patterns = [
            ".git/**",
            ".venv/**",
            "venv/**",
            "__pycache__/**",
            "*.pyc",
            ".DS_Store",
            "*.egg-info/**",
            "uv.lock",
            ".uv/**",
        ]

    all_files: set[str] = set()

    for base_dir in [project_dir, old_template_dir, new_template_dir]:
        if not base_dir.exists():
            continue
        for file_path in base_dir.rglob("*"):
            if file_path.is_file():
                relative = str(file_path.relative_to(base_dir))
                # Check exclusions using _matches_any_pattern for ** support
                if not _matches_any_pattern(relative, exclude_patterns):
                    all_files.add(relative)

    return all_files


def _parse_dependency(dep_str: str) -> tuple[str, str]:
    """Parse a dependency string into (name, version_spec).

    Examples:
        "google-adk>=0.2.0" -> ("google-adk", ">=0.2.0")
        "requests==2.31.0" -> ("requests", "==2.31.0")
        "pytest" -> ("pytest", "")
    """
    # Match package name followed by optional version spec
    match = re.match(r"^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)(.*)", dep_str.strip())
    if match:
        return match.group(1).lower(), match.group(2).strip()
    return dep_str.lower(), ""


def _load_dependencies_from_pyproject(
    pyproject_path: pathlib.Path,
) -> dict[str, str]:
    """Load dependencies as {name: version_spec} dict."""
    if not pyproject_path.exists():
        return {}

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        deps = data.get("project", {}).get("dependencies", [])
        result = {}
        for dep in deps:
            name, version = _parse_dependency(dep)
            result[name] = version
        return result
    except Exception as e:
        logging.warning(f"Error loading dependencies from {pyproject_path}: {e}")
        return {}


def merge_pyproject_dependencies(
    current_pyproject: pathlib.Path,
    old_template_pyproject: pathlib.Path,
    new_template_pyproject: pathlib.Path,
) -> DependencyMergeResult:
    """Merge deps: new_template + user_added, where user_added = current - old."""
    current_deps = _load_dependencies_from_pyproject(current_pyproject)
    old_deps = _load_dependencies_from_pyproject(old_template_pyproject)
    new_deps = _load_dependencies_from_pyproject(new_template_pyproject)

    changes: list[DependencyChange] = []
    merged: dict[str, str] = {}
    user_added = set(current_deps.keys()) - set(old_deps.keys())
    asp_managed = set(old_deps.keys())

    for name, new_version in new_deps.items():
        merged[name] = new_version

        if name in old_deps:
            old_version = old_deps[name]
            if old_version != new_version:
                changes.append(
                    DependencyChange(
                        name=name,
                        change_type="updated",
                        old_version=old_version,
                        new_version=new_version,
                    )
                )
        else:
            changes.append(
                DependencyChange(
                    name=name,
                    change_type="added",
                    new_version=new_version,
                )
            )

    for name in user_added:
        user_version = current_deps[name]
        merged[name] = user_version
        changes.append(
            DependencyChange(
                name=name,
                change_type="kept",
                old_version=user_version,
                new_version=user_version,
            )
        )

    for name in asp_managed:
        if name not in new_deps and name not in user_added:
            changes.append(
                DependencyChange(
                    name=name,
                    change_type="removed",
                    old_version=old_deps[name],
                )
            )

    merged_list = [f"{name}{version}" for name, version in sorted(merged.items())]

    return DependencyMergeResult(
        changes=changes,
        merged_deps=merged_list,
        has_conflicts=False,
    )


def write_merged_dependencies(
    pyproject_path: pathlib.Path,
    merged_deps: list[str],
) -> bool:
    """Write merged dependencies back to pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml
        merged_deps: List of dependency strings to write

    Returns:
        True if successful, False otherwise
    """
    if not pyproject_path.exists():
        return False

    try:
        content = pyproject_path.read_text(encoding="utf-8")

        # Format dependencies as a TOML array
        if merged_deps:
            deps_formatted = ",\n    ".join(f'"{dep}"' for dep in merged_deps)
            new_deps_section = f"dependencies = [\n    {deps_formatted},\n]"
        else:
            new_deps_section = "dependencies = []"

        # Replace the dependencies array using regex
        # Match: dependencies = [...] (potentially multiline)
        pattern = r"dependencies\s*=\s*\[[^\]]*\]"
        content = re.sub(pattern, new_deps_section, content, flags=re.DOTALL)

        pyproject_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logging.warning(f"Could not write dependencies to {pyproject_path}: {e}")
        return False


def compare_all_files(
    project_dir: pathlib.Path,
    old_template_dir: pathlib.Path,
    new_template_dir: pathlib.Path,
    agent_directory: str = "app",
) -> list[FileCompareResult]:
    """Compare all files using 3-way comparison."""
    all_files = collect_all_files(project_dir, old_template_dir, new_template_dir)

    results = []
    for relative_path in sorted(all_files):
        result = three_way_compare(
            relative_path,
            project_dir,
            old_template_dir,
            new_template_dir,
            agent_directory,
        )
        results.append(result)

    return results


def group_results_by_action(
    results: list[FileCompareResult],
) -> dict[str, list[FileCompareResult]]:
    """Group results by action type."""
    groups: dict[str, list[FileCompareResult]] = {
        "auto_update": [],
        "preserve": [],
        "skip": [],
        "conflict": [],
        "new": [],
        "removed": [],
    }

    for result in results:
        groups[result.action].append(result)

    return groups
