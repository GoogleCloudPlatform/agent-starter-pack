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

import logging
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class RemoteTemplateSpec:
    """Parsed remote template specification."""

    repo_url: str
    template_path: str
    git_ref: str
    is_adk_samples: bool = False


def parse_agent_spec(agent_spec: str) -> RemoteTemplateSpec | None:
    """Parse agent specification to determine if it's a remote template.

    Args:
        agent_spec: Agent specification string

    Returns:
        RemoteTemplateSpec if remote template, None if local template
    """
    # Check for local@ prefix
    if agent_spec.startswith("local@"):
        return None

    # Check for adk@ shortcut
    if agent_spec.startswith("adk@"):
        sample_name = agent_spec[4:]  # Remove "adk@" prefix
        return RemoteTemplateSpec(
            repo_url="https://github.com/google/adk-samples",
            template_path=f"python/agents/{sample_name}",
            git_ref="main",
            is_adk_samples=True,
        )

    # GitHub /tree/ URL pattern
    tree_pattern = r"^(https?://[^/]+/[^/]+/[^/]+)/tree/([^/]+)/(.*)$"
    match = re.match(tree_pattern, agent_spec)
    if match:
        repo_url = match.group(1)
        git_ref = match.group(2)
        template_path = match.group(3)
        return RemoteTemplateSpec(
            repo_url=repo_url,
            template_path=template_path.strip("/"),
            git_ref=git_ref,
        )

    # General remote pattern: <repo_url>[/<path>][@<ref>]
    # Handles github.com, gitlab.com, etc.
    remote_pattern = r"^(https?://[^/]+/[^/]+/[^/]+)(?:/(.*?))?(?:@([^/]+))?/?$"
    match = re.match(remote_pattern, agent_spec)
    if match:
        repo_url = match.group(1)
        template_path_with_ref = match.group(2) or ""
        git_ref_from_url = match.group(3)

        # Separate path and ref if ref is part of the path
        template_path = template_path_with_ref
        git_ref = git_ref_from_url or "main"

        if "@" in template_path:
            path_parts = template_path.split("@")
            template_path = path_parts[0]
            git_ref = path_parts[1]

        return RemoteTemplateSpec(
            repo_url=repo_url,
            template_path=template_path.strip("/"),
            git_ref=git_ref,
        )

    # GitHub shorthand: <org>/<repo>[/<path>][@<ref>]
    github_shorthand_pattern = r"^([^/]+)/([^/]+)(?:/(.*?))?(?:@([^/]+))?/?$"
    match = re.match(github_shorthand_pattern, agent_spec)
    if match and "/" in agent_spec:  # Ensure it has at least one slash
        org = match.group(1)
        repo = match.group(2)
        template_path = match.group(3) or ""
        git_ref = match.group(4) or "main"
        return RemoteTemplateSpec(
            repo_url=f"https://github.com/{org}/{repo}",
            template_path=template_path,
            git_ref=git_ref,
        )

    return None


def fetch_remote_template(spec: RemoteTemplateSpec) -> pathlib.Path:
    """Fetch remote template and return path to template directory.

    Uses Git to clone the remote repository.

    Args:
        spec: Remote template specification

    Returns:
        Path to the fetched template directory
    """
    temp_dir = tempfile.mkdtemp(prefix="asp_remote_template_")
    temp_path = pathlib.Path(temp_dir)
    repo_path = temp_path / "repo"

    # Attempt Git Clone
    try:
        clone_url = spec.repo_url
        clone_cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            spec.git_ref,
            clone_url,
            str(repo_path),
        ]
        logging.debug(
            f"Attempting to clone remote template with Git: {' '.join(clone_cmd)}"
        )
        # GIT_TERMINAL_PROMPT=0 prevents git from prompting for credentials
        subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        logging.debug("Git clone successful.")
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise RuntimeError(f"Git clone failed: {e.stderr.strip()}") from e

    # Process the successfully fetched template
    try:
        if spec.template_path:
            template_dir = repo_path / spec.template_path
        else:
            template_dir = repo_path

        if not template_dir.exists():
            raise FileNotFoundError(
                f"Template path not found in the repository: {spec.template_path}"
            )

        # Exclude Makefile and README.md from remote template to avoid conflicts
        makefile_path = template_dir / "Makefile"
        if makefile_path.exists():
            logging.debug(f"Removing Makefile from remote template: {makefile_path}")
            makefile_path.unlink()

        readme_path = template_dir / "README.md"
        if readme_path.exists():
            logging.debug(f"Removing README.md from remote template: {readme_path}")
            readme_path.unlink()

        return template_dir
    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_path, ignore_errors=True)
        raise RuntimeError(
            f"An unexpected error occurred after fetching remote template: {e}"
        ) from e


def load_remote_template_config(template_dir: pathlib.Path) -> dict[str, Any]:
    """Load template configuration from remote template.

    Args:
        template_dir: Path to template directory

    Returns:
        Template configuration dictionary
    """
    config_path = template_dir / ".template" / "templateconfig.yaml"

    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config if config else {}
    except Exception as e:
        logging.error(f"Error loading remote template config: {e}")
        return {}


def get_base_template_name(config: dict[str, Any]) -> str:
    """Get base template name from remote template config.

    Args:
        config: Template configuration dictionary

    Returns:
        Base template name (defaults to "adk_base")
    """
    return config.get("base_template", "adk_base")


def merge_template_configs(
    base_config: dict[str, Any], remote_config: dict[str, Any]
) -> dict[str, Any]:
    """Merge base template config with remote template config using a deep merge.

    Args:
        base_config: Base template configuration
        remote_config: Remote template configuration

    Returns:
        Merged configuration with remote overriding base
    """
    import copy

    def deep_merge(d1: dict[str, Any], d2: dict[str, Any]) -> dict[str, Any]:
        """Recursively merges d2 into d1."""
        for k, v in d2.items():
            if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                d1[k] = deep_merge(d1[k], v)
            else:
                d1[k] = v
        return d1

    # Start with a deep copy of the base to avoid modifying it
    merged_config = copy.deepcopy(base_config)

    # Perform the deep merge
    return deep_merge(merged_config, remote_config)
