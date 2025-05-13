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

import importlib.metadata

import click
from rich.console import Console

from .commands.create import create
from .commands.setup_cicd import setup_cicd
from .utils import display_update_message

console = Console()


def print_version(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    try:
        version_str = importlib.metadata.version("agent-starter-pack")
        console.print(f"GCP Agent Starter Pack CLI version: {version_str}")
    except importlib.metadata.PackageNotFoundError:
        console.print("GCP Agent Starter Pack CLI (development version)")
    ctx.exit()


@click.group(help="Production-ready Generative AI Agent templates for Google Cloud")
@click.option(
    "--version",
    "-v",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help="Show the version and exit.",
)
def cli() -> None:
    # Check for updates at startup
    display_update_message()


# Register commands
cli.add_command(create)
cli.add_command(setup_cicd)


if __name__ == "__main__":
    cli()
