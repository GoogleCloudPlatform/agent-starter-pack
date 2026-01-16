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
from jinja2 import StrictUndefined, Template

from .lock_utils import get_agent_configs, get_lock_filename

# Path to Go base template
GO_BASE_TEMPLATE = pathlib.Path("agent_starter_pack/base_templates/go")


def ensure_lock_dir() -> pathlib.Path:
    """Ensure the locks directory exists and is empty.

    Returns:
        Path to the locks directory
    """
    lock_dir = pathlib.Path("agent_starter_pack/resources/locks")

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
        template = Template(f.read(), trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)

    # Convert list to proper format for template
    tags = list(config.get("tags", []))
    context = {
        "cookiecutter": {
            "project_name": "locked-template",
            "deployment_target": deployment_target,
            "extra_dependencies": list(config.get("extra_dependencies", [])),
            "tags": tags,
            "is_adk": "adk" in tags,
            "is_adk_live": "adk_live" in tags,
            "agent_directory": config.get("agent_directory", "app"),
            "agent_name": config.get("agent_name", ""),
            "agent_description": config.get("description", ""),
            "generated_at": "",
            "package_version": "",
            "session_type": "",
            "cicd_runner": "skip",
            "data_ingestion": "false",
            "datastore_type": "",
            "frontend_type": "",
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
        # Explicitly use PyPI to ensure consistent lock files
        subprocess.run(
            ["uv", "lock", "--default-index", "https://pypi.org/simple"],
            cwd=tmp_dir,
            check=True,
        )
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


def generate_go_lock_file() -> None:
    """Generate go.sum and go.mod for Go base template.

    Creates a temporary Go project using the CLI, runs go mod tidy,
    then copies go.sum and go.mod back to the template (with project name
    replaced by the Jinja variable).
    """
    go_mod_path = GO_BASE_TEMPLATE / "go.mod"
    go_sum_path = GO_BASE_TEMPLATE / "go.sum"

    if not go_mod_path.exists():
        print("Skipping Go lock generation: go.mod template not found")
        return

    print("Generating go.sum for Go base template...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = pathlib.Path(tmpdir)
        project_name = "go-lock-gen"

        # Generate a Go project using the CLI
        subprocess.run(
            [
                "uv", "run", "agent-starter-pack", "create", project_name,
                "-p", "-s", "-y",
                "-a", "adk_go",
                "-d", "cloud_run",
                "--output-dir", str(tmp_dir),
            ],
            check=True,
            capture_output=True,
        )

        project_dir = tmp_dir / project_name

        # Run go mod tidy in the generated project
        subprocess.run(
            ["go", "mod", "tidy"],
            cwd=project_dir,
            check=True,
        )

        # Copy go.sum back to template
        generated_sum = project_dir / "go.sum"
        if generated_sum.exists():
            shutil.copy2(generated_sum, go_sum_path)
            print(f"Generated {go_sum_path}")

        # Copy go.mod back to template (replace project name with Jinja var)
        generated_mod = project_dir / "go.mod"
        if generated_mod.exists():
            with open(generated_mod, encoding="utf-8") as f:
                go_mod_content = f.read()
            go_mod_content = go_mod_content.replace(
                project_name, "{{cookiecutter.project_name}}"
            )
            with open(go_mod_path, "w", encoding="utf-8") as f:
                f.write(go_mod_content)
            print(f"Updated {go_mod_path} with indirect dependencies")


@click.command()
@click.option(
    "--template",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default="agent_starter_pack/base_templates/python/pyproject.toml",
    help="Path to template pyproject.toml",
)
def main(template: pathlib.Path) -> None:
    """Generate lock files for all agent and deployment target combinations."""
    lock_dir = ensure_lock_dir()
    agent_configs = get_agent_configs()

    # Generate Python lock files
    for agent_name, config in agent_configs.items():
        # Skip Go agents (they use go.sum, not uv.lock)
        if config.get("language") == "go":
            continue

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

    # Generate Go lock file (go.sum)
    generate_go_lock_file()


if __name__ == "__main__":
    main()
