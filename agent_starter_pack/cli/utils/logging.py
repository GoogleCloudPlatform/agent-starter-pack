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

import importlib.metadata
import random
import sys
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

MOTTOS = [
    "Your agents are cleared for takeoff.",
    "Launching agents into production, one deploy at a time.",
    "Houston, we have an agent.",
    "To production... and beyond!",
    "One small step for code, one giant leap for agents.",
    "Fueling your AI agents with Google Cloud.",
    "3... 2... 1... Agent deployed!",
    "The sky is not the limit when you have agents.",
]

F = TypeVar("F", bound=Callable[..., Any])


def _get_version() -> str:
    """Get the package version, with fallback to 'dev'."""
    try:
        return importlib.metadata.version("agent-starter-pack")
    except Exception:
        return "dev"


def _build_banner(line1: str, version: str, motto: str) -> Panel:
    """Build a compact banner panel with ASP ASCII art logo."""
    a = "bold blue"
    s = "bold cyan"
    p = "bold magenta"
    logo = (
        f"[{a}]▄▀▄[/] [{s}]█▀▀[/] [{p}]█▀▄[/]\n"
        f"[{a}]█▀█[/] [{s}]▀▀█[/] [{p}]█▀▀[/]\n"
        f"[{s}]▀ ▀[/] [{s}]▀▀▀[/] [{p}]▀[/]  "
    )
    right_text = f' [italic dim]"{motto}"[/]\n\n {line1}'
    table = Table(
        show_header=False,
        show_edge=False,
        show_lines=False,
        padding=0,
        pad_edge=False,
    )
    table.add_column(width=12)
    table.add_column()
    table.add_row(logo, right_text)
    return Panel(
        table,
        title=f"Agent Starter Pack v{version}",
        border_style="blue",
        padding=(1, 2),
    )


def display_welcome_banner(
    agent: str | None = None,
    enhance_mode: bool = False,
    agent_garden: bool = False,
    setup_cicd_mode: bool = False,
    register_mode: bool = False,
    quiet: bool = False,
) -> None:
    """Display the Agent Starter Pack welcome banner.

    Args:
        agent: Optional agent specification to customize the welcome message
        enhance_mode: Whether this is for enhancement mode
        agent_garden: Whether this deployment is from Agent Garden
        setup_cicd_mode: Whether this is for CI/CD setup
        register_mode: Whether this is for Gemini Enterprise registration
        quiet: If True, skip the banner (e.g. in auto-approve/programmatic mode)
    """
    version = _get_version()
    if quiet:
        console.print(f"[bold blue]Agent Starter Pack[/] [dim]v{version}[/]")
        return

    motto = random.choice(MOTTOS)

    if enhance_mode:
        panel = _build_banner(
            line1="Enhancing your project with production-ready capabilities!",
            version=version,
            motto=motto,
        )
    elif setup_cicd_mode:
        panel = _build_banner(
            line1="Setting up CI/CD infrastructure for your agent!",
            version=version,
            motto=motto,
        )
    elif register_mode:
        panel = _build_banner(
            line1="Registering your agent to Gemini Enterprise!",
            version=version,
            motto=motto,
        )
    elif agent_garden:
        panel = _build_banner(
            line1=(
                "Powered by [link=https://goo.gle/agent-starter-pack]"
                "Google Cloud - Agent Starter Pack[/link]"
            ),
            version=version,
            motto=motto,
        )
    elif agent and agent.startswith("adk@"):
        panel = _build_banner(
            line1=(
                "Powered by [link=https://goo.gle/agent-starter-pack]"
                "Google Cloud - Agent Starter Pack[/link]"
            ),
            version=version,
            motto=motto,
        )
    else:
        panel = _build_banner(
            line1="Create production-ready AI agents on Google Cloud!",
            version=version,
            motto=motto,
        )

    console.print()
    console.print(panel)


def handle_cli_error(f: F) -> F:
    """Decorator to handle CLI errors gracefully.

    Wraps CLI command functions to catch any exceptions and display them nicely
    to the user before exiting with a non-zero status code.

    Args:
        f: The CLI command function to wrap

    Returns:
        The wrapped function that handles errors
    """

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\nOperation cancelled by user", style="yellow")
            sys.exit(130)  # Standard exit code for Ctrl+C
        except Exception as e:
            console.print(f"Error: {e!s}", style="bold red")
            sys.exit(1)

    return cast(F, wrapper)
