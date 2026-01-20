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

"""Utilities for converting project metadata to CLI arguments."""

from typing import Any


def metadata_to_cli_args(metadata: dict[str, Any]) -> list[str]:
    """Convert metadata to CLI arguments for re-creating a project.

    Maps [tool.agent-starter-pack] metadata back to CLI arguments.
    Used by upgrade command to re-template old/new versions.
    """
    args: list[str] = []

    if "base_template" in metadata:
        args.extend(["--agent", metadata["base_template"]])

    if "agent_directory" in metadata and metadata["agent_directory"] != "app":
        args.extend(["--agent-directory", metadata["agent_directory"]])

    create_params = metadata.get("create_params", {})
    for key, value in create_params.items():
        if (
            value is None
            or value is False
            or str(value).lower() == "none"
            or value == ""
        ):
            continue

        arg_name = f"--{key.replace('_', '-')}"
        if value is True:
            args.append(arg_name)
        else:
            args.extend([arg_name, str(value)])

    return args
