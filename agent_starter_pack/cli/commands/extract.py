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

"""Extract command for creating minimal, shareable agents from scaffolded projects."""

import logging
import pathlib
import re
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
    from datetime import UTC
else:
    from datetime import timezone

    import tomli as tomllib

    UTC = timezone.utc  # noqa: UP017 - Required for Python 3.10 compatibility

import click
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from rich.console import Console

from ..utils.language import (
    LANGUAGE_CONFIGS,
    detect_language,
    get_asp_config_for_language,
)
from ..utils.logging import handle_cli_error

# Path to base templates directory
BASE_TEMPLATES_DIR = pathlib.Path(__file__).parent.parent.parent / "base_templates"

console = Console()

# =============================================================================
# Scaffolding Configuration
# =============================================================================

SCAFFOLDING_DIRS = {
    "deployment",
    ".github",
    ".cloudbuild",
    "data_ingestion",
    "frontend",
    "tools",
    "notebooks",
}

SCAFFOLDING_FILES_IN_AGENT_DIR = {
    "app_utils",
    "fast_api_app.py",
    "agent_engine_app.py",
}

SCAFFOLDING_DEPENDENCIES = {
    "fastapi",
    "uvicorn",
    "asyncpg",
    "protobuf",
    "opentelemetry-exporter-otlp-proto-http",
    "opentelemetry-instrumentation-google-genai",
    "google-cloud-logging",
    "gcsfs",
    "google-cloud-aiplatform",
}

CORE_DEPENDENCIES = {
    "google-adk",
    "google-genai",
    "langchain",
    "langgraph",
}


def get_asp_config(project_dir: pathlib.Path) -> dict[str, Any] | None:
    """Read agent-starter-pack config from project's pyproject.toml.

    Args:
        project_dir: Path to the project directory

    Returns:
        The [tool.agent-starter-pack] config dict if found, None otherwise
    """
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        return pyproject_data.get("tool", {}).get("agent-starter-pack")
    except Exception as e:
        logging.debug(f"Could not read config from pyproject.toml: {e}")
        return None


def detect_agent_directory(
    project_dir: pathlib.Path, asp_config: dict[str, Any] | None
) -> str:
    """Detect the agent directory from config or heuristics.

    Args:
        project_dir: Path to the project directory
        asp_config: The ASP config from pyproject.toml

    Returns:
        The agent directory name (e.g., 'app')
    """
    # First, try to get from ASP config
    if asp_config and asp_config.get("agent_directory"):
        return asp_config["agent_directory"]

    # Try common patterns
    for candidate in ["app", "agent", "src"]:
        candidate_path = project_dir / candidate
        if candidate_path.is_dir() and (candidate_path / "agent.py").exists():
            return candidate

    # Fallback: look for any directory with agent.py
    for item in project_dir.iterdir():
        if (
            item.is_dir()
            and not item.name.startswith(".")
            and (item / "agent.py").exists()
        ):
            return item.name

    return "app"  # Default fallback


def copy_project_files(
    source_dir: pathlib.Path,
    output_dir: pathlib.Path,
    language: str,
) -> list[str]:
    """Copy language-specific project files using LANGUAGE_CONFIGS.

    Args:
        source_dir: Source project directory
        output_dir: Output directory
        language: Language key (e.g., 'python', 'go')

    Returns:
        List of copied file names
    """
    lang_config = LANGUAGE_CONFIGS.get(language, {})
    project_files = lang_config.get("project_files", [])
    copied = []

    for filename in project_files:
        source_file = source_dir / filename
        if source_file.exists():
            console.print(f"  • Copying {filename}...")
            shutil.copy2(source_file, output_dir / filename)
            copied.append(filename)

    return copied


def regenerate_lock_file(output_dir: pathlib.Path, language: str) -> bool:
    """Regenerate the lock file for the given language.

    Uses LANGUAGE_CONFIGS to determine the appropriate command.

    Args:
        output_dir: Output directory where to run the command
        language: Language key (e.g., 'python', 'go')

    Returns:
        True if successful, False otherwise
    """
    lang_config = LANGUAGE_CONFIGS.get(language, {})
    lock_command = lang_config.get("lock_command")
    lock_command_name = lang_config.get("lock_command_name", str(lock_command))

    if not lock_command:
        return True  # No lock command needed

    console.print(f"  • Running {lock_command_name}...")
    try:
        subprocess.run(
            lock_command,
            cwd=output_dir,
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        console.print(
            f"⚠️  [yellow]Warning:[/yellow] Failed to run {lock_command_name}: {e}"
        )
        console.print(f"   You may need to run '{lock_command_name}' manually.")
        return False
    except FileNotFoundError:
        tool_name = lock_command[0] if lock_command else "tool"
        console.print(
            f"⚠️  [yellow]Warning:[/yellow] {tool_name} not found. "
            f"Skipping {lock_command_name}."
        )
        return False


def render_makefile_template(
    language: str,
    context: dict[str, Any],
) -> str:
    """Render the Makefile template for the given language with extracted=True.

    Args:
        language: 'python' or 'go'
        context: Template context (cookiecutter variables)

    Returns:
        Rendered Makefile content
    """
    template_dir = BASE_TEMPLATES_DIR / language
    if not template_dir.exists():
        raise ValueError(f"No base template found for language: {language}")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    env.add_extension("jinja2.ext.do")

    template = env.get_template("Makefile")
    render_context = {"extracted": True, "cookiecutter": context}
    return template.render(**render_context)


def render_readme_template(
    language: str,
    context: dict[str, Any],
) -> str:
    """Render the README template for the given language with extracted=True.

    Args:
        language: 'python' or 'go'
        context: Template context (cookiecutter variables)

    Returns:
        Rendered README content
    """
    template_dir = BASE_TEMPLATES_DIR / language
    if not template_dir.exists():
        raise ValueError(f"No base template found for language: {language}")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    env.add_extension("jinja2.ext.do")

    template = env.get_template("README.md")
    render_context = {"extracted": True, "cookiecutter": context}
    return template.render(**render_context)


def is_scaffolding_dependency(dep: str) -> bool:
    """Check if a dependency string matches a scaffolding dependency.

    Args:
        dep: Dependency string (e.g., 'fastapi~=0.115.8')

    Returns:
        True if this is a scaffolding dependency
    """
    # Extract base package name (before version specifiers or extras)
    dep_name = re.split(r"[\s\[><~=]", dep)[0].strip()
    return dep_name.lower() in {d.lower() for d in SCAFFOLDING_DEPENDENCIES}


def is_core_dependency(dep: str) -> bool:
    """Check if a dependency string matches a core dependency.

    Args:
        dep: Dependency string

    Returns:
        True if this is a core dependency that must be kept
    """
    # Extract base package name (before version specifiers or extras)
    dep_name = re.split(r"[\s\[><~=]", dep)[0].strip().lower()
    for core in CORE_DEPENDENCIES:
        core_lower = core.lower()
        # Exact match or extension package (e.g., langchain-google-genai for langchain)
        if dep_name == core_lower or dep_name.startswith(core_lower + "-"):
            return True
    return False


def process_pyproject_toml(
    source_path: pathlib.Path,
    dest_path: pathlib.Path,
) -> None:
    """Process pyproject.toml: strip scaffolding deps, add extracted metadata.

    Args:
        source_path: Path to source pyproject.toml
        dest_path: Path to write processed pyproject.toml
    """
    content = source_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    output_lines = []
    in_dependencies = False
    skip_section = False
    in_optional_deps = False
    wrote_optional_deps_header = False

    # Sections to skip entirely (tests/notebooks are always removed)
    skip_section_headers = {"[dependency-groups]", "[tool.pytest.ini_options]"}

    # Optional deps subsections to keep
    keep_optional_deps = {"lint"}

    for line in lines:
        stripped = line.strip()

        # Detect section headers
        if stripped.startswith("[") and not stripped.startswith("[["):
            if stripped in skip_section_headers:
                skip_section = True
                continue
            elif stripped == "[project.optional-dependencies]":
                in_optional_deps = True
                skip_section = True
                wrote_optional_deps_header = False
                continue
            else:
                in_optional_deps = False
                skip_section = False

        # Handle optional-dependencies subsections
        if in_optional_deps:
            if stripped.startswith("["):
                in_optional_deps = False
                skip_section = False
            elif "= [" in stripped:
                subsection_name = stripped.split("=")[0].strip()
                if subsection_name in keep_optional_deps:
                    if not wrote_optional_deps_header:
                        output_lines.append("[project.optional-dependencies]")
                        wrote_optional_deps_header = True
                    skip_section = False
                else:
                    skip_section = True
                    continue
            elif skip_section:
                continue

        if skip_section:
            continue

        # Detect start of dependencies array
        if stripped == "dependencies = [" or stripped.startswith("dependencies = ["):
            in_dependencies = True
            output_lines.append(line)
            continue

        # Detect end of dependencies array or start of new section
        if in_dependencies:
            if stripped == "]" or stripped.startswith("["):
                in_dependencies = False
            elif stripped.startswith('"') or stripped.startswith("'"):
                dep = stripped.strip("\",' ")
                if is_scaffolding_dependency(dep) and not is_core_dependency(dep):
                    logging.debug(f"Removing scaffolding dependency: {dep}")
                    continue

        output_lines.append(line)

    output_content = "\n".join(output_lines)

    if "[tool.agent-starter-pack]" in output_content:
        asp_section_end = output_content.find(
            "\n[", output_content.find("[tool.agent-starter-pack]") + 1
        )
        if asp_section_end == -1:
            asp_section_end = len(output_content)

        extracted_metadata = (
            f'\n\nextracted = true\nextracted_at = "{datetime.now(UTC).isoformat()}"'
        )

        if asp_section_end == len(output_content):
            output_content = output_content.rstrip() + extracted_metadata + "\n"
        else:
            output_content = (
                output_content[:asp_section_end]
                + extracted_metadata
                + "\n"
                + output_content[asp_section_end:]
            )

    dest_path.write_text(output_content, encoding="utf-8")


def copy_agent_directory(
    source_dir: pathlib.Path,
    dest_dir: pathlib.Path,
) -> list[str]:
    """Copy agent directory, excluding scaffolding files.

    Args:
        source_dir: Source agent directory
        dest_dir: Destination agent directory

    Returns:
        List of copied files (relative paths)
    """
    copied_files = []
    dest_dir.mkdir(parents=True, exist_ok=True)

    for item in source_dir.iterdir():
        # Skip scaffolding files
        if item.name in SCAFFOLDING_FILES_IN_AGENT_DIR:
            logging.debug(f"Skipping scaffolding: {item.name}")
            continue

        # Skip __pycache__ and other hidden files
        if item.name.startswith("__pycache__") or item.name.startswith("."):
            continue

        dest_item = dest_dir / item.name
        if item.is_dir():
            # Recursively copy subdirectories (but not scaffolding)
            if item.name not in SCAFFOLDING_FILES_IN_AGENT_DIR:
                shutil.copytree(item, dest_item, dirs_exist_ok=True)
                copied_files.append(f"{item.name}/")
        else:
            shutil.copy2(item, dest_item)
            copied_files.append(item.name)

    return copied_files


def display_extraction_summary(
    source_dir: pathlib.Path,
    output_dir: pathlib.Path,
    removed_dirs: list[str],
    language: str = "python",
) -> None:
    """Display a summary of the extraction operation.

    Args:
        source_dir: Source project directory
        output_dir: Output directory
        removed_dirs: List of scaffolding directories that were removed
        language: Project language key (e.g., 'python', 'go')
    """
    lang_config = LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS["python"])

    console.print("\n[bold green]✅ Success![/] Your extracted agent is ready.\n")

    console.print("[bold cyan]📋 Summary[/]")
    console.print(f"   Source:   [dim]{source_dir}[/]")
    console.print(f"   Output:   [cyan]{output_dir}[/]")
    console.print(f"   Language: {lang_config.get('display_name', language)}")

    if removed_dirs:
        console.print(f"   Removed:  {', '.join(f'{d}/' for d in removed_dirs)}")

    console.print("\n[bold cyan]💡 Tip[/]")
    console.print("   When ready for production: [cyan]agent-starter-pack enhance[/]")

    console.print("\n[bold cyan]🚀 Get Started[/]")
    console.print(
        f"   [bold bright_green]cd {output_dir.name} && make install && make playground[/]"
    )


@click.command()
@click.argument(
    "output_path",
    type=click.Path(path_type=pathlib.Path),
    required=True,
)
@click.option(
    "--source",
    "-s",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
    help="Source project directory (default: current directory)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be extracted without making changes",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite output directory if it exists",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@handle_cli_error
def extract(
    output_path: pathlib.Path,
    source: pathlib.Path,
    dry_run: bool,
    force: bool,
    debug: bool,
) -> None:
    """Extract a minimal, shareable agent from a full scaffolded project.

    Creates a stripped-down version of your agent suitable for sharing,
    removing deployment infrastructure while preserving core agent logic.

    The extracted agent can later be enhanced with `agent-starter-pack enhance`.

    Example:
        agent-starter-pack extract ../my-agent-share
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Debug mode enabled")

    source_dir = source.resolve()
    output_dir = output_path.resolve()

    console.print(
        "\n=== Google Cloud Agent Starter Pack 🚀===",
        style="bold blue",
    )
    console.print("Extracting a minimal, shareable agent from your project.\n")

    # Detect project language first (needed for validation)
    language = detect_language(source_dir)
    lang_config = LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS["python"])

    # Validate source project based on language
    config_file = lang_config.get("config_file", "pyproject.toml")
    config_path = source_dir / config_file
    if not config_path.exists():
        # Check if any language's config file exists
        found_config = False
        for _, check_config in LANGUAGE_CONFIGS.items():
            check_file = source_dir / check_config.get("config_file", "")
            if check_file.exists():
                found_config = True
                break

        if not found_config:
            console.print(
                f"❌ [bold red]Error:[/bold red] No project config file found in "
                f"{source_dir}",
            )
            console.print(
                "   Make sure you're running from an agent-starter-pack project."
            )
            console.print(
                f"   Expected one of: {', '.join(c.get('config_file', '') for c in LANGUAGE_CONFIGS.values())}"
            )
            raise SystemExit(1)

    asp_config = get_asp_config_for_language(source_dir, language)
    if not asp_config and language == "python":
        asp_config = get_asp_config(source_dir)  # backward compatibility

    if not asp_config:
        console.print(
            f"⚠️  [yellow]Warning:[/yellow] No ASP config found in {config_file}.",
        )
        console.print(
            "   This project may not have been created with agent-starter-pack."
        )
        if not click.confirm("Continue anyway?", default=False):
            raise SystemExit(0)

    agent_directory = detect_agent_directory(source_dir, asp_config)
    agent_dir_path = source_dir / agent_directory

    if not agent_dir_path.exists():
        console.print(
            f"❌ [bold red]Error:[/bold red] Agent directory '{agent_directory}' not found.",
        )
        raise SystemExit(1)

    agent_py_path = agent_dir_path / "agent.py"
    if not agent_py_path.exists():
        console.print(
            f"⚠️  [yellow]Warning:[/yellow] No agent.py found in {agent_directory}/",
        )

    if output_dir.exists():
        if force:
            console.print(f"🗑️  Removing existing directory: {output_dir}")
            if not dry_run:
                shutil.rmtree(output_dir)
        else:
            console.print(
                f"❌ [bold red]Error:[/bold red] Output directory already exists: {output_dir}",
            )
            console.print("   Use --force to overwrite.")
            raise SystemExit(1)

    existing_scaffolding = [d for d in SCAFFOLDING_DIRS if (source_dir / d).exists()]
    if (source_dir / "tests").exists():
        existing_scaffolding.append("tests")

    # Detect ADK from config or agent.py imports
    is_adk = False
    if asp_config:
        base_template = asp_config.get("base_template", "")
        is_adk = "adk" in base_template.lower()
    else:
        # Try to detect from agent.py imports (Python only)
        if language == "python" and agent_py_path.exists():
            agent_content = agent_py_path.read_text(encoding="utf-8")
            is_adk = "google.adk" in agent_content or "from adk" in agent_content

    if dry_run:
        console.print("[bold cyan]DRY RUN - No changes will be made[/bold cyan]")
        console.print()
        console.print(
            f"[bold]Language:[/bold] {lang_config.get('display_name', language)}"
        )
        console.print()
        console.print("[bold]Would extract:[/bold]")
        console.print(f"  • {agent_directory}/ (agent code)")
        for project_file in lang_config.get("project_files", []):
            if (source_dir / project_file).exists():
                note = (
                    " (stripped of scaffolding deps)"
                    if lang_config.get("strip_dependencies")
                    and project_file.endswith(".toml")
                    else ""
                )
                console.print(f"  • {project_file}{note}")
        console.print("  • Makefile (minimal version)")
        console.print("  • README.md")
        console.print("  • .gitignore")
        if (source_dir / "GEMINI.md").exists():
            console.print("  • GEMINI.md")
        console.print()

        if existing_scaffolding:
            console.print("[bold]Would remove:[/bold]")
            for d in existing_scaffolding:
                console.print(f"  • {d}/")
        console.print()
        console.print(f"[bold]Output:[/bold] {output_dir}")
        return

    console.print(f"📦 Creating extracted agent at: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"  • Copying {agent_directory}/...")
    agent_dest = output_dir / agent_directory
    copied_files = copy_agent_directory(agent_dir_path, agent_dest)
    logging.debug(f"Copied files: {copied_files}")

    if lang_config.get("strip_dependencies"):
        console.print("  • Processing pyproject.toml...")
        process_pyproject_toml(
            source_dir / "pyproject.toml",
            output_dir / "pyproject.toml",
        )
    else:
        copy_project_files(source_dir, output_dir, language)

    console.print("  • Generating minimal Makefile...")
    template_context = {
        "agent_directory": agent_directory,
        "project_name": asp_config.get("name", "agent") if asp_config else "agent",
        "is_adk": is_adk,
        "is_adk_live": asp_config.get("is_adk_live", False) if asp_config else False,
        "is_a2a": asp_config.get("is_a2a", False) if asp_config else False,
        "deployment_target": (
            asp_config.get("deployment_target", "cloud_run")
            if asp_config
            else "cloud_run"
        ),
        "settings": {},  # Required by template for command overrides
    }
    try:
        makefile_content = render_makefile_template(language, template_context)
    except Exception as e:
        console.print(
            f"❌ [bold red]Error:[/bold red] Failed to generate Makefile: {e}"
        )
        raise SystemExit(1)
    (output_dir / "Makefile").write_text(makefile_content, encoding="utf-8")

    console.print("  • Generating README.md...")
    readme_context = {
        **template_context,
        "package_version": (
            asp_config.get("asp_version", "unknown") if asp_config else "unknown"
        ),
        "agent_description": (asp_config.get("description", "") if asp_config else ""),
    }
    try:
        readme_content = render_readme_template(language, readme_context)
    except Exception as e:
        console.print(f"❌ [bold red]Error:[/bold red] Failed to generate README: {e}")
        raise SystemExit(1)
    (output_dir / "README.md").write_text(readme_content, encoding="utf-8")

    gitignore_path = source_dir / ".gitignore"
    if gitignore_path.exists():
        console.print("  • Copying .gitignore...")
        shutil.copy2(gitignore_path, output_dir / ".gitignore")

    gemini_path = source_dir / "GEMINI.md"
    if gemini_path.exists():
        console.print("  • Copying GEMINI.md...")
        shutil.copy2(gemini_path, output_dir / "GEMINI.md")

    regenerate_lock_file(output_dir, language)

    display_extraction_summary(
        source_dir,
        output_dir,
        existing_scaffolding,
        language,
    )
