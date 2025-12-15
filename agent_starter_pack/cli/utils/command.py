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

"""Utilities for running shell commands with cross-platform compatibility."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# Cache for gcloud command path (resolved once for performance)
_gcloud_cmd_cache: str | None = None


def get_gcloud_cmd() -> str:
    """Get the gcloud command path, with caching for performance.

    Uses shutil.which() to find the full path to gcloud on all platforms.
    On Windows, also checks common installation paths if shutil.which() fails
    (which can happen when PATH contains directories with spaces).
    Falls back to "gcloud" if not found anywhere.

    Returns:
        Full path to gcloud executable, or "gcloud" as fallback
    """
    global _gcloud_cmd_cache
    if _gcloud_cmd_cache is not None:
        return _gcloud_cmd_cache

    # Try shutil.which() first (works on most systems)
    gcloud_cmd = shutil.which("gcloud")
    if gcloud_cmd:
        _gcloud_cmd_cache = gcloud_cmd
        return _gcloud_cmd_cache

    # On Windows, manually check common installation paths
    # (shutil.which can fail when PATH has spaces in directory names)
    # Use environment variables for robustness (Windows may not be on C:/)
    if os.name == "nt":
        local_app_data = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        program_files_x86 = Path(
            os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")
        )

        possible_paths = [
            local_app_data
            / "Google"
            / "Cloud SDK"
            / "google-cloud-sdk"
            / "bin"
            / "gcloud.cmd",
            program_files_x86
            / "Google"
            / "Cloud SDK"
            / "google-cloud-sdk"
            / "bin"
            / "gcloud.cmd",
            program_files
            / "Google"
            / "Cloud SDK"
            / "google-cloud-sdk"
            / "bin"
            / "gcloud.cmd",
        ]
        for path in possible_paths:
            if path.exists():
                _gcloud_cmd_cache = str(path)
                return _gcloud_cmd_cache

    # Fallback to just "gcloud" and hope it works
    _gcloud_cmd_cache = "gcloud"
    return _gcloud_cmd_cache


def run_gcloud_command(
    args: list[str],
    check: bool = True,
    capture_output: bool = False,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    """Run a gcloud command with Windows compatibility.

    Automatically handles:
    - Resolving the full path to gcloud executable
    - Using shell=True on Windows for .cmd files

    Args:
        args: Command arguments (without 'gcloud' prefix, e.g., ['config', 'get-value', 'account'])
        check: If True, raise CalledProcessError on non-zero exit
        capture_output: If True, capture stdout and stderr
        timeout: Optional timeout in seconds

    Returns:
        CompletedProcess instance
    """
    cmd = [get_gcloud_cmd(), *args]
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
        shell=(os.name == "nt"),
    )
