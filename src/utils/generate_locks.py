#!/usr/bin/env python3
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

"""Utility script to generate lock files for all agent and deployment target combinations."""

import logging
import pathlib
import shutil
import subprocess
import tempfile

import click
from jinja2 import Template
from lock_utils import get_agent_configs, get_lock_filename


def ensure_lock_dir() -> pathlib.Path:
    """Ensure the locks directory exists and is empty.

    Returns:
        Path to the locks directory
    """
    lock_dir = pathlib.Path("src/resources/locks")

    # Remove if exists
    if lock_dir.exists():
        shutil.rmtree(lock_dir)

    # Create fresh directory
    lock_dir.mkdir(parents=True)

    return lock_dir


def generate_pyproject(
    template_path: pathlib.Path, deployment_target: str, config: dict
) -> str:
    """Generate pyproject.toml content from template.

    Args:
        template_path: Path to the pyproject.toml template
        deployment_target: Target deployment platform
        extra_dependencies: List of additional dependencies from .templateconfig.yaml
    """
    with open(template_path, encoding="utf-8") as f:
        template = Template(f.read(), trim_blocks=True, lstrip_blocks=True)

    # Convert list to proper format for template
    context = {
        "cookiecutter": {
            "project_name": "locked-template",
            "deployment_target": deployment_target,
            "extra_dependencies": list(config.get("extra_dependencies",[])),
            "tags": list(config.get("tags",[])),
        }
    }

    # Add debug logging
    logging.debug(f"Template context: {context}")
    result = template.render(context)
    logging.debug(f"Generated pyproject.toml:\n{result}")

    return result


def generate_lock_file(pyproject_content: str, output_path: pathlib.Path) -> None:
    """Generate uv.lock file from pyproject content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = pathlib.Path(tmpdir)

        # Write temporary pyproject.toml
        with open(tmp_dir / "pyproject.toml", "w", encoding="utf-8") as f:
            f.write(pyproject_content)

        # Run uv pip compile to generate lock file
        subprocess.run(["uv", "lock"], cwd=tmp_dir, check=True)
        # Replace locked-template with {{cookiecutter.project_name}} in generated lock file
        lock_file_path = tmp_dir / "uv.lock"
        with open(lock_file_path, "r+", encoding="utf-8") as f:
            lock_content = f.read()
            f.seek(0)
            f.write(
                lock_content.replace("locked-template", "{{cookiecutter.project_name}}")
            )
            f.truncate()

        # Copy the generated lock file to output location
        shutil.copy2(lock_file_path, output_path)


@click.command()
@click.option(
    "--template",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default="src/base_template/pyproject.toml",
    help="Path to template pyproject.toml",
)
def main(template: pathlib.Path) -> None:
    """Generate lock files for all agent and deployment target combinations."""
    lock_dir = ensure_lock_dir()
    agent_configs = get_agent_configs()

    for agent_name, config in agent_configs.items():
        for target in config["deployment_targets"]:
            print(f"Generating lock file for {agent_name} with {target}...")

            # Generate pyproject content
            content = generate_pyproject(
                template,
                deployment_target=target,
                config=config,
            )

            # Generate lock file
            output_path = lock_dir / get_lock_filename(agent_name, target)
            generate_lock_file(content, output_path)
            print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
