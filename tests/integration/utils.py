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

import pathlib
import subprocess

from rich.console import Console

console = Console()


def run_command(
    cmd: list[str],
    cwd: pathlib.Path | None,
    message: str,
    stream_output: bool = True,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Helper function to run commands and stream output"""
    console.print(f"\n[bold blue]{message}...[/]")
    try:
        # Using Popen to stream output
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            bufsize=1,  # Line-buffered
            env=env,
            encoding="utf-8",
        ) as process:
            if stream_output:
                # Stream stdout
                if process.stdout:
                    for line in process.stdout:
                        console.print(line.strip())

                # Stream stderr
                if process.stderr:
                    for line in process.stderr:
                        console.print("[bold red]" + line.strip())
            else:
                # Consume the output but don't print it
                if process.stdout:
                    for _ in process.stdout:
                        pass
                if process.stderr:
                    for _ in process.stderr:
                        pass

            # Wait for the process to complete and get the return code
            returncode = process.wait()

        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, cmd)

        console.print(f"[green]✓[/] {message} completed successfully")
        return subprocess.CompletedProcess(cmd, returncode, "", "")

    except subprocess.CalledProcessError:
        console.print(f"[bold red]Error: {message}[/]")
        raise
