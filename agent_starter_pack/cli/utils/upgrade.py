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

"""3-way file comparison and dependency merging for upgrade command."""

import fnmatch
import hashlib
import logging
import pathlib
import re
import subprocess
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
        # Java agent code
        "{agent_directory}/**/*.java",
        # TypeScript agent code
        "{agent_directory}/agent.ts",
        "{agent_directory}/**/*.ts",
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
        # Go / TypeScript ASP config
        ".asp.toml",
        # Java dependencies (ASP config is in pom.xml properties)
        "pom.xml",
        # TypeScript dependencies
        "package.json",
        "package-lock.json",
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

    # File only in current project (user-added, not part of ASP template)
    if current_hash is not None and old_hash is None and new_hash is None:
        return FileCompareResult(
            path=relative_path,
            category=category,
            action="skip",
            reason="User-added file (not part of ASP template)",
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
            "starter_pack_*",
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


def _parse_dependency(dep_str: str) -> tuple[str, str, str]:
    """Parse a dependency string into (base_name, extras, version_spec).

    Extras are separated from the package name so that packages with
    different extras brackets (e.g., ``pkg[a]`` vs ``pkg[a,b]``) are
    keyed by the same base name.

    Examples:
        "google-adk>=0.2.0" -> ("google-adk", "", ">=0.2.0")
        "google-cloud-aiplatform[evaluation]>=1.0" -> ("google-cloud-aiplatform", "[evaluation]", ">=1.0")
        "requests==2.31.0" -> ("requests", "", "==2.31.0")
        "pytest" -> ("pytest", "", "")
    """
    # Match base package name, optional extras in brackets, optional version spec
    match = re.match(r"^([a-zA-Z0-9_-]+)(\[[^\]]+\])?(.*)", dep_str.strip())
    if match:
        base_name = match.group(1).lower()
        extras = match.group(2) or ""
        version = match.group(3).strip()
        return base_name, extras, version
    return dep_str.lower(), "", ""


def _load_dependencies_from_pyproject(
    pyproject_path: pathlib.Path,
) -> dict[str, tuple[str, str]]:
    """Load dependencies as {base_name: (extras, version_spec)} dict."""
    if not pyproject_path.exists():
        return {}

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        deps = data.get("project", {}).get("dependencies", [])
        result: dict[str, tuple[str, str]] = {}
        for dep in deps:
            name, extras, version = _parse_dependency(dep)
            result[name] = (extras, version)
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
    merged: dict[str, tuple[str, str]] = {}
    user_added = set(current_deps.keys()) - set(old_deps.keys())
    asp_managed = set(old_deps.keys())

    for name, (new_extras, new_version) in new_deps.items():
        merged[name] = (new_extras, new_version)

        if name in old_deps:
            old_extras, old_version = old_deps[name]
            old_spec = f"{old_extras}{old_version}"
            new_spec = f"{new_extras}{new_version}"
            if old_spec != new_spec:
                changes.append(
                    DependencyChange(
                        name=name,
                        change_type="updated",
                        old_version=old_spec,
                        new_version=new_spec,
                    )
                )
        else:
            changes.append(
                DependencyChange(
                    name=name,
                    change_type="added",
                    new_version=f"{new_extras}{new_version}",
                )
            )

    for name in user_added:
        user_extras, user_version = current_deps[name]
        merged[name] = (user_extras, user_version)
        user_spec = f"{user_extras}{user_version}"
        changes.append(
            DependencyChange(
                name=name,
                change_type="kept",
                old_version=user_spec,
                new_version=user_spec,
            )
        )

    for name in asp_managed:
        if name not in new_deps and name not in user_added:
            old_extras, old_version = old_deps[name]
            changes.append(
                DependencyChange(
                    name=name,
                    change_type="removed",
                    old_version=f"{old_extras}{old_version}",
                )
            )

    merged_list = [
        f"{name}{extras}{version}" for name, (extras, version) in sorted(merged.items())
    ]

    return DependencyMergeResult(
        changes=changes,
        merged_deps=merged_list,
        has_conflicts=False,
    )


def write_merged_dependencies(
    pyproject_path: pathlib.Path,
    merged_deps: list[str],
) -> bool:
    """Write merged dependencies to pyproject.toml using uv CLI.

    Uses ``uv add --frozen`` and ``uv remove --frozen`` so the lockfile
    and virtualenv are left untouched — only pyproject.toml is modified.

    Args:
        pyproject_path: Path to pyproject.toml
        merged_deps: List of dependency strings to write

    Returns:
        True if successful, False otherwise
    """
    if not pyproject_path.exists():
        return False

    project_dir = pyproject_path.parent

    try:
        # Determine which deps to remove (in current but not in merged)
        current_deps = _load_dependencies_from_pyproject(pyproject_path)
        merged_names: set[str] = set()
        for dep in merged_deps:
            name, _, _ = _parse_dependency(dep)
            merged_names.add(name)

        to_remove = [n for n in current_deps if n not in merged_names]

        if to_remove:
            result = subprocess.run(
                ["uv", "remove", "--frozen", *to_remove],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logging.warning(f"uv remove failed: {result.stderr}")

        # Add / update all merged deps
        if merged_deps:
            result = subprocess.run(
                ["uv", "add", "--frozen", *merged_deps],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logging.warning(f"uv add failed: {result.stderr}")
                return False

        return True
    except FileNotFoundError:
        logging.warning("uv not found — cannot write merged dependencies")
        return False
    except Exception as e:
        logging.warning(f"Could not write dependencies to {pyproject_path}: {e}")
        return False


def update_asp_metadata(
    project_dir: pathlib.Path,
    create_params: dict[str, str],
    asp_version: str | None = None,
    language: str = "python",
    remove_keys: list[str] | None = None,
) -> bool:
    """Update specific keys in ASP metadata for any supported language.

    Handles all config formats:
    - Python: ``pyproject.toml`` under ``[tool.agent-starter-pack]``
    - Go / TypeScript: ``.asp.toml`` under ``[project]``
    - Java: ``pom.xml`` ``<properties>`` with ``asp.*`` prefix

    Args:
        project_dir: Path to the project directory
        create_params: Dict of keys to update
            (e.g., ``{"deployment_target": "cloud_run"}``)
        asp_version: If provided, update the ASP version field
        language: Project language (``"python"``, ``"go"``, ``"java"``,
            ``"typescript"``)
        remove_keys: List of keys to remove from create_params section

    Returns:
        True if successful, False otherwise
    """
    from .language import LANGUAGE_CONFIGS

    lang_config = LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS["python"])
    config_file = lang_config.get("config_file")
    config_format = lang_config.get("config_format", "toml")
    version_key = lang_config.get("version_key", "asp_version")

    if not config_file:
        return False

    config_path = project_dir / config_file
    if not config_path.exists():
        return False

    try:
        if config_format == "maven_properties":
            return _update_maven_asp_metadata(
                config_path, create_params, asp_version, version_key, remove_keys
            )

        # TOML format (Python, Go, TypeScript)
        content = config_path.read_text(encoding="utf-8")

        # Update version field if provided
        if asp_version:
            pattern = rf'({re.escape(version_key)}\s*=\s*)"[^"]*"'
            content = re.sub(pattern, f'\\1"{asp_version}"', content)

        # Update individual keys
        for key, value in create_params.items():
            pattern = rf'({re.escape(key)}\s*=\s*)"[^"]*"'
            replacement = f'\\1"{value}"'
            content = re.sub(pattern, replacement, content)

        # Remove stale keys
        if remove_keys:
            for key in remove_keys:
                content = re.sub(rf'\n{re.escape(key)}\s*=\s*"[^"]*"', "", content)

        config_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logging.warning(f"Could not update ASP metadata in {config_path}: {e}")
        return False


def _update_maven_asp_metadata(
    pom_path: pathlib.Path,
    create_params: dict[str, str],
    asp_version: str | None,
    version_key: str,
    remove_keys: list[str] | None = None,
) -> bool:
    """Update ASP metadata in a Maven pom.xml file."""
    try:
        content = pom_path.read_text(encoding="utf-8")

        if asp_version:
            pattern = rf"(<{re.escape(version_key)}>)[^<]*(</)"
            content = re.sub(pattern, rf"\g<1>{asp_version}\g<2>", content)

        for key, value in create_params.items():
            prop_name = f"asp.{key}"
            pattern = rf"(<{re.escape(prop_name)}>)[^<]*(</)"
            content = re.sub(pattern, rf"\g<1>{value}\g<2>", content)

        if remove_keys:
            for key in remove_keys:
                prop_name = f"asp.{key}"
                content = re.sub(
                    rf"\s*<{re.escape(prop_name)}>[^<]*</{re.escape(prop_name)}>",
                    "",
                    content,
                )

        pom_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logging.warning(f"Could not update Maven ASP metadata in {pom_path}: {e}")
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
