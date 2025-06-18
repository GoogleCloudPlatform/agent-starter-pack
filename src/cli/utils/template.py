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
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any

import yaml
from cookiecutter.main import cookiecutter
from rich.console import Console
from rich.prompt import Prompt

from src.cli.utils.version import get_current_version

from .datastores import DATASTORES

ADK_FILES = ["app/__init__.py"]
NON_ADK_FILES: list[str] = []


@dataclass
class TemplateConfig:
    name: str
    description: str
    settings: dict[str, bool | list[str]]

    @classmethod
    def from_file(cls, config_path: pathlib.Path) -> "TemplateConfig":
        """Load template config from file with validation"""
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ValueError(f"Invalid template config format in {config_path}")

            required_fields = ["name", "description", "settings"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                raise ValueError(
                    f"Missing required fields in template config: {missing_fields}"
                )

            return cls(
                name=data["name"],
                description=data["description"],
                settings=data["settings"],
            )
        except yaml.YAMLError as err:
            raise ValueError(f"Invalid YAML in template config: {err}") from err
        except Exception as err:
            raise ValueError(f"Error loading template config: {err}") from err


OVERWRITE_FOLDERS = ["app", "frontend", "tests", "notebooks"]
TEMPLATE_CONFIG_FILE = ".templateconfig.yaml"
DEPLOYMENT_FOLDERS = ["cloud_run", "agent_engine"]
DEFAULT_FRONTEND = "streamlit"


def get_available_agents(deployment_target: str | None = None) -> dict:
    """Dynamically load available agents from the agents directory.

    Args:
        deployment_target: Optional deployment target to filter agents
    """
    # Define priority agents that should appear first
    PRIORITY_AGENTS = [
        "adk_base",
        "adk_gemini_fullstack",
        "agentic_rag",
        "langgraph_base_react",
    ]

    agents_list = []
    priority_agents_dict = dict.fromkeys(PRIORITY_AGENTS)  # Track priority agents
    agents_dir = pathlib.Path(__file__).parent.parent.parent.parent / "agents"

    for agent_dir in agents_dir.iterdir():
        if agent_dir.is_dir() and not agent_dir.name.startswith("__"):
            template_config_path = agent_dir / "template" / ".templateconfig.yaml"
            if template_config_path.exists():
                try:
                    with open(template_config_path) as f:
                        config = yaml.safe_load(f)
                    agent_name = agent_dir.name

                    # Skip if deployment target specified and agent doesn't support it
                    if deployment_target:
                        targets = config.get("settings", {}).get(
                            "deployment_targets", []
                        )
                        if isinstance(targets, str):
                            targets = [targets]
                        if deployment_target not in targets:
                            continue

                    description = config.get("description", "No description available")
                    agent_info = {"name": agent_name, "description": description}

                    # Add to priority list or regular list based on agent name
                    if agent_name in PRIORITY_AGENTS:
                        priority_agents_dict[agent_name] = agent_info
                    else:
                        agents_list.append(agent_info)
                except Exception as e:
                    logging.warning(f"Could not load agent from {agent_dir}: {e}")

    # Sort the non-priority agents
    agents_list.sort(key=lambda x: x["name"])

    # Create priority agents list in the exact order specified
    priority_agents = [
        info for name, info in priority_agents_dict.items() if info is not None
    ]

    # Combine priority agents with regular agents
    combined_agents = priority_agents + agents_list

    # Convert to numbered dictionary starting from 1
    agents = {i + 1: agent for i, agent in enumerate(combined_agents)}

    return agents


def load_template_config(template_dir: pathlib.Path) -> dict[str, Any]:
    """Read .templateconfig.yaml file to get agent configuration."""
    config_file = template_dir / TEMPLATE_CONFIG_FILE
    if not config_file.exists():
        return {}

    try:
        with open(config_file) as f:
            config = yaml.safe_load(f)
            return config if config else {}
    except Exception as e:
        logging.error(f"Error loading template config: {e}")
        return {}


def get_deployment_targets(agent_name: str) -> list:
    """Get available deployment targets for the selected agent."""
    template_path = (
        pathlib.Path(__file__).parent.parent.parent.parent
        / "agents"
        / agent_name
        / "template"
    )
    config = load_template_config(template_path)

    if not config:
        return []

    targets = config.get("settings", {}).get("deployment_targets", [])
    return targets if isinstance(targets, list) else [targets]


def prompt_deployment_target(agent_name: str) -> str:
    """Ask user to select a deployment target for the agent."""
    targets = get_deployment_targets(agent_name)

    # Define deployment target friendly names and descriptions
    TARGET_INFO = {
        "agent_engine": {
            "display_name": "Vertex AI Agent Engine",
            "description": "Vertex AI Managed platform for scalable agent deployments",
        },
        "cloud_run": {
            "display_name": "Cloud Run",
            "description": "GCP Serverless container execution",
        },
    }

    if not targets:
        return ""

    console = Console()
    console.print("\n> Please select a deployment target:")
    for idx, target in enumerate(targets, 1):
        info = TARGET_INFO.get(target, {})
        display_name = info.get("display_name", target)
        description = info.get("description", "")
        console.print(f"{idx}. [bold]{display_name}[/] - [dim]{description}[/]")

    from rich.prompt import IntPrompt

    choice = IntPrompt.ask(
        "\nEnter the number of your deployment target choice",
        default=1,
        show_default=True,
    )
    return targets[choice - 1]


def prompt_datastore_selection(
    agent_name: str, from_cli_flag: bool = False
) -> str | None:
    """Ask user to select a datastore type if the agent supports data ingestion.

    Args:
        agent_name: Name of the agent
        from_cli_flag: Whether this is being called due to explicit --include-data-ingestion flag
    """
    console = Console()

    # If this is from CLI flag, skip the "would you like to include" prompt
    if from_cli_flag:
        console.print("\n> Please select a datastore type for your data:")

        # Display options with descriptions
        for i, (_key, info) in enumerate(DATASTORES.items(), 1):
            console.print(
                f"{i}. [bold]{info['name']}[/] - [dim]{info['description']}[/]"
            )

        choice = Prompt.ask(
            "\nEnter the number of your choice",
            choices=[str(i) for i in range(1, len(DATASTORES) + 1)],
            default="1",
        )

        # Convert choice number to datastore type
        datastore_type = list(DATASTORES.keys())[int(choice) - 1]
        return datastore_type

    # Otherwise, proceed with normal flow
    template_path = (
        pathlib.Path(__file__).parent.parent.parent.parent
        / "agents"
        / agent_name
        / "template"
    )
    config = load_template_config(template_path)

    if config:
        # If requires_data_ingestion is true, prompt for datastore type without asking if they want it
        if config.get("settings", {}).get("requires_data_ingestion"):
            console.print("\n> This agent includes a data ingestion pipeline.")
            console.print("> Please select a datastore type for your data:")

            # Display options with descriptions
            for i, (_key, info) in enumerate(DATASTORES.items(), 1):
                console.print(
                    f"{i}. [bold]{info['name']}[/] - [dim]{info['description']}[/]"
                )
            choice = Prompt.ask(
                "\nEnter the number of your choice",
                choices=[str(i) for i in range(1, len(DATASTORES) + 1)],
                default="1",
            )

            # Convert choice number to datastore type
            datastore_type = list(DATASTORES.keys())[int(choice) - 1]
            return datastore_type

        # Only prompt if the agent has optional data ingestion support
        if "requires_data_ingestion" in config.get("settings", {}):
            include = (
                Prompt.ask(
                    "\n> This agent supports data ingestion. Would you like to include a data pipeline?",
                    choices=["y", "n"],
                    default="n",
                ).lower()
                == "y"
            )

            if include:
                console.print("\n> Please select a datastore type for your data:")

                # Display options with descriptions
                for i, (_key, info) in enumerate(DATASTORES.items(), 1):
                    console.print(
                        f"{i}. [bold]{info['name']}[/] - [dim]{info['description']}[/]"
                    )

                choice = Prompt.ask(
                    "\nEnter the number of your choice",
                    choices=[str(i) for i in range(1, len(DATASTORES) + 1)],
                    default="1",
                )

                # Convert choice number to datastore type
                datastore_type = list(DATASTORES.keys())[int(choice) - 1]
                return datastore_type

    # If we get here, we need to prompt for datastore selection for explicit --include-data-ingestion flag
    console.print(
        "\n> Please select a datastore type for your data ingestion pipeline:"
    )
    # Display options with descriptions
    for i, (_key, info) in enumerate(DATASTORES.items(), 1):
        console.print(f"{i}. [bold]{info['name']}[/] - [dim]{info['description']}[/]")

    choice = Prompt.ask(
        "\nEnter the number of your choice",
        choices=[str(i) for i in range(1, len(DATASTORES) + 1)],
        default="1",
    )

    # Convert choice number to datastore type
    datastore_type = list(DATASTORES.keys())[int(choice) - 1]
    return datastore_type


def get_template_path(agent_name: str, debug: bool = False) -> pathlib.Path:
    """Get the absolute path to the agent template directory."""
    current_dir = pathlib.Path(__file__).parent.parent.parent.parent
    template_path = current_dir / "agents" / agent_name / "template"
    if debug:
        logging.debug(f"Looking for template in: {template_path}")
        logging.debug(f"Template exists: {template_path.exists()}")
        if template_path.exists():
            logging.debug(f"Template contents: {list(template_path.iterdir())}")

    if not template_path.exists():
        raise ValueError(f"Template directory not found at {template_path}")

    return template_path


def copy_data_ingestion_files(
    project_template: pathlib.Path, datastore_type: str
) -> None:
    """Copy data processing files to the project template for cookiecutter templating.

    Args:
        project_template: Path to the project template directory
        datastore_type: Type of datastore to use for data ingestion
    """
    data_ingestion_src = pathlib.Path(__file__).parent.parent.parent / "data_ingestion"
    data_ingestion_dst = project_template / "data_ingestion"

    if data_ingestion_src.exists():
        logging.debug(
            f"Copying data processing files from {data_ingestion_src} to {data_ingestion_dst}"
        )

        copy_files(data_ingestion_src, data_ingestion_dst, overwrite=True)

        logging.debug(f"Data ingestion files prepared for datastore: {datastore_type}")
    else:
        logging.warning(
            f"Data processing source directory not found at {data_ingestion_src}"
        )


def process_template(
    agent_name: str,
    template_dir: pathlib.Path,
    project_name: str,
    deployment_target: str | None = None,
    include_data_ingestion: bool = False,
    datastore: str | None = None,
    output_dir: pathlib.Path | None = None,
) -> None:
    """Process the template directory and create a new project.

    Args:
        agent_name: Name of the agent template to use
        template_dir: Directory containing the template files
        project_name: Name of the project to create
        deployment_target: Optional deployment target (agent_engine or cloud_run)
        include_data_ingestion: Whether to include data pipeline components
        output_dir: Optional output directory path, defaults to current directory
    """
    logging.debug(f"Processing template from {template_dir}")
    logging.debug(f"Project name: {project_name}")
    logging.debug(f"Include pipeline: {datastore}")
    logging.debug(f"Output directory: {output_dir}")

    # Get paths
    agent_path = template_dir.parent  # Get parent of template dir
    logging.debug(f"agent path: {agent_path}")
    logging.debug(f"agent path exists: {agent_path.exists()}")
    logging.debug(
        f"agent path contents: {list(agent_path.iterdir()) if agent_path.exists() else 'N/A'}"
    )

    base_template_path = pathlib.Path(__file__).parent.parent.parent / "base_template"

    # Use provided output_dir or current directory
    destination_dir = output_dir if output_dir else pathlib.Path.cwd()

    # Create output directory if it doesn't exist
    if not destination_dir.exists():
        destination_dir.mkdir(parents=True)

    # Create a new temporary directory and use it as our working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)

        # Important: Store the original working directory
        original_dir = pathlib.Path.cwd()

        try:
            os.chdir(temp_path)  # Change to temp directory

            # Create the cookiecutter template structure
            cookiecutter_template = temp_path / "template"
            cookiecutter_template.mkdir(parents=True)
            project_template = cookiecutter_template / "{{cookiecutter.project_name}}"
            project_template.mkdir(parents=True)

            # 1. First copy base template files
            base_template_path = (
                pathlib.Path(__file__).parent.parent.parent / "base_template"
            )
            copy_files(base_template_path, project_template, agent_name, overwrite=True)
            logging.debug(f"1. Copied base template from {base_template_path}")

            # 2. Process deployment target if specified
            if deployment_target and deployment_target in DEPLOYMENT_FOLDERS:
                deployment_path = (
                    pathlib.Path(__file__).parent.parent.parent
                    / "deployment_targets"
                    / deployment_target
                )
                if deployment_path.exists():
                    copy_files(
                        deployment_path,
                        project_template,
                        agent_name=agent_name,
                        overwrite=True,
                    )
                    logging.debug(
                        f"2. Processed deployment files for target: {deployment_target}"
                    )

            # 3. Copy data ingestion files if needed
            if include_data_ingestion and datastore:
                logging.debug(
                    f"3. Including data processing files with datastore: {datastore}"
                )
                copy_data_ingestion_files(project_template, datastore)

            # 4. Process frontend files
            # Load template config
            template_config = load_template_config(pathlib.Path(template_dir))
            frontend_type = template_config.get("settings", {}).get(
                "frontend_type", DEFAULT_FRONTEND
            )
            copy_frontend_files(frontend_type, project_template)
            logging.debug(f"4. Processed frontend files for type: {frontend_type}")

            # 5. Finally, copy agent-specific files to override everything else
            if agent_path.exists():
                for folder in OVERWRITE_FOLDERS:
                    agent_folder = agent_path / folder
                    project_folder = project_template / folder
                    if agent_folder.exists():
                        logging.debug(f"5. Copying agent folder {folder} with override")
                        copy_files(
                            agent_folder, project_folder, agent_name, overwrite=True
                        )

            # Copy agent README.md if it exists
            agent_readme = agent_path / "README.md"
            if agent_readme.exists():
                agent_readme_dest = project_template / "agent_README.md"
                shutil.copy2(agent_readme, agent_readme_dest)
                logging.debug(
                    f"Copied agent README from {agent_readme} to {agent_readme_dest}"
                )

            # Load and validate template config first
            template_path = pathlib.Path(template_dir)
            config = load_template_config(template_path)
            if not config:
                raise ValueError(f"Could not load template config from {template_path}")

            # Validate deployment target
            available_targets = config.get("settings", {}).get("deployment_targets", [])
            if isinstance(available_targets, str):
                available_targets = [available_targets]

            if deployment_target and deployment_target not in available_targets:
                raise ValueError(
                    f"Invalid deployment target '{deployment_target}'. Available targets: {available_targets}"
                )

            # Load template config
            template_config = load_template_config(pathlib.Path(template_dir))

            # Check if data processing should be included
            if include_data_ingestion and datastore:
                logging.debug(
                    f"Including data processing files with datastore: {datastore}"
                )
                copy_data_ingestion_files(project_template, datastore)

            # Create cookiecutter.json in the template root
            # Get settings from template config
            settings = template_config.get("settings", {})
            extra_deps = settings.get("extra_dependencies", [])
            frontend_type = settings.get("frontend_type", DEFAULT_FRONTEND)
            tags = settings.get("tags", ["None"])

            cookiecutter_config = {
                "project_name": "my-project",
                "agent_name": agent_name,
                "package_version": get_current_version(),
                "agent_description": template_config.get("description", ""),
                "example_question": template_config.get("example_question", "").ljust(
                    61
                ),
                "settings": settings,
                "tags": tags,
                "deployment_target": deployment_target or "",
                "frontend_type": frontend_type,
                "extra_dependencies": [extra_deps],
                "data_ingestion": include_data_ingestion,
                "datastore_type": datastore if datastore else "",
                "_copy_without_render": [
                    "*.ipynb",  # Don't render notebooks
                    "*.json",  # Don't render JSON files
                    "frontend/*",  # Don't render frontend directory
                    # "tests/*",  # Don't render tests directory
                    "notebooks/*",  # Don't render notebooks directory
                    ".git/*",  # Don't render git directory
                    "__pycache__/*",  # Don't render cache
                    "**/__pycache__/*",
                    ".pytest_cache/*",
                    ".venv/*",
                    "*templates.py",  # Don't render templates files
                    "!*.py",  # render Python files
                    "!Makefile",  # DO render Makefile
                    "!README.md",  # DO render README.md
                ],
            }

            with open(cookiecutter_template / "cookiecutter.json", "w") as f:
                import json

                json.dump(cookiecutter_config, f, indent=4)

            logging.debug(f"Template structure created at {cookiecutter_template}")
            logging.debug(
                f"Directory contents: {list(cookiecutter_template.iterdir())}"
            )

            # Process the template
            cookiecutter(
                str(cookiecutter_template),
                no_input=True,
                extra_context={
                    "project_name": project_name,
                    "agent_name": agent_name,
                },
            )
            logging.debug("Template processing completed successfully")

            # Move the generated project to the final destination
            output_dir = temp_path / project_name
            final_destination = destination_dir / project_name

            logging.debug(f"Moving project from {output_dir} to {final_destination}")

            if output_dir.exists():
                if final_destination.exists():
                    shutil.rmtree(final_destination)
                shutil.copytree(output_dir, final_destination, dirs_exist_ok=True)
                logging.debug(f"Project successfully created at {final_destination}")

                # Delete appropriate files based on ADK tag
                if "adk" in tags:
                    files_to_delete = [final_destination / f for f in NON_ADK_FILES]
                else:
                    files_to_delete = [final_destination / f for f in ADK_FILES]

                for file_path in files_to_delete:
                    if file_path.exists():
                        file_path.unlink()
                        logging.debug(f"Deleted {file_path}")

                # After copying template files, handle the lock file
                if deployment_target:
                    # Get the source lock file path
                    lock_path = (
                        pathlib.Path(__file__).parent.parent.parent.parent
                        / "src"
                        / "resources"
                        / "locks"
                        / f"uv-{agent_name}-{deployment_target}.lock"
                    )
                    logging.debug(f"Looking for lock file at: {lock_path}")
                    logging.debug(f"Lock file exists: {lock_path.exists()}")
                    if not lock_path.exists():
                        raise FileNotFoundError(f"Lock file not found: {lock_path}")
                    # Copy and rename to uv.lock in the project directory
                    shutil.copy2(lock_path, final_destination / "uv.lock")
                    logging.debug(
                        f"Copied lock file from {lock_path} to {final_destination}/uv.lock"
                    )

                    # Replace cookiecutter project name with actual project name in lock file
                    lock_file_path = final_destination / "uv.lock"
                    with open(lock_file_path, "r+", encoding="utf-8") as f:
                        content = f.read()
                        f.seek(0)
                        f.write(
                            content.replace(
                                "{{cookiecutter.project_name}}", project_name
                            )
                        )
                        f.truncate()
                    logging.debug(
                        f"Updated project name in lock file at {lock_file_path}"
                    )
            else:
                logging.error(f"Generated project directory not found at {output_dir}")
                raise FileNotFoundError(
                    f"Generated project directory not found at {output_dir}"
                )

        except Exception as e:
            logging.error(f"Failed to process template: {e!s}")
            raise

        finally:
            # Always restore the original working directory
            os.chdir(original_dir)


def should_exclude_path(path: pathlib.Path, agent_name: str) -> bool:
    """Determine if a path should be excluded based on the agent type."""
    if agent_name == "live_api":
        # Exclude the unit test utils folder and app/utils folder for live_api
        if "tests/unit/test_utils" in str(path) or "app/utils" in str(path):
            logging.debug(f"Excluding path for live_api: {path}")
            return True
    return False


def copy_files(
    src: pathlib.Path,
    dst: pathlib.Path,
    agent_name: str | None = None,
    overwrite: bool = False,
) -> None:
    """
    Copy files with configurable behavior for exclusions and overwrites.

    Args:
        src: Source path
        dst: Destination path
        agent_name: Name of the agent (for agent-specific exclusions)
        overwrite: Whether to overwrite existing files (True) or skip them (False)
    """

    def should_skip(path: pathlib.Path) -> bool:
        """Determine if a file/directory should be skipped during copying."""
        if path.suffix in [".pyc"]:
            return True
        if "__pycache__" in str(path) or path.name == "__pycache__":
            return True
        if agent_name is not None and should_exclude_path(path, agent_name):
            return True
        return False

    if src.is_dir():
        if not dst.exists():
            dst.mkdir(parents=True)
        for item in src.iterdir():
            if should_skip(item):
                logging.debug(f"Skipping file/directory: {item}")
                continue
            d = dst / item.name
            if item.is_dir():
                copy_files(item, d, agent_name, overwrite)
            else:
                if overwrite or not d.exists():
                    logging.debug(f"Copying file: {item} -> {d}")
                    shutil.copy2(item, d)
                else:
                    logging.debug(f"Skipping existing file: {d}")
    else:
        if not should_skip(src):
            if overwrite or not dst.exists():
                shutil.copy2(src, dst)


def copy_frontend_files(frontend_type: str, project_template: pathlib.Path) -> None:
    """Copy files from the specified frontend folder directly to project root."""
    # Skip copying if frontend_type is "None"
    if frontend_type == "None":
        logging.debug("Frontend type is 'None', skipping frontend files")
        return

    # Use default frontend if none specified
    frontend_type = frontend_type or DEFAULT_FRONTEND

    # Get the frontends directory path
    frontends_path = (
        pathlib.Path(__file__).parent.parent.parent / "frontends" / frontend_type
    )

    if frontends_path.exists():
        logging.debug(f"Copying frontend files from {frontends_path}")
        # Copy frontend files directly to project root instead of a nested frontend directory
        copy_files(frontends_path, project_template, overwrite=True)
    else:
        logging.warning(f"Frontend type directory not found: {frontends_path}")
        if frontend_type != DEFAULT_FRONTEND:
            logging.info(f"Falling back to default frontend: {DEFAULT_FRONTEND}")
            copy_frontend_files(DEFAULT_FRONTEND, project_template)


def copy_deployment_files(
    deployment_target: str, agent_name: str, project_template: pathlib.Path
) -> None:
    """Copy files from the specified deployment target folder."""
    if not deployment_target:
        return

    deployment_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "deployment_targets"
        / deployment_target
    )

    if deployment_path.exists():
        logging.debug(f"Copying deployment files from {deployment_path}")
        # Pass agent_name to respect agent-specific exclusions
        copy_files(
            deployment_path, project_template, agent_name=agent_name, overwrite=True
        )
    else:
        logging.warning(f"Deployment target directory not found: {deployment_path}")
