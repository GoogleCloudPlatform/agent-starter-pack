#!/usr/bin/env python3
"""
env_probe.py
A tiny, corridor-grade environment probe.

Prints:
  • resolved path of the `validation` package
  • active Python interpreter
  • workspace root (cwd)
  • module search path (sys.path)
"""

import importlib.util
import os
import sys


def resolve_validation_path() -> str:
    """Return the resolved filesystem path of the `validation` package, or a note if missing."""
    spec = importlib.util.find_spec("validation")
    if spec and spec.origin:
        return os.path.abspath(spec.origin)
    return "<validation package not found>"


def main() -> None:
    print("\n=== Corridor Environment Probe ===\n")

    print("Validation package path:")
    print(f"  {resolve_validation_path()}\n")

    print("Active Python interpreter:")
    print(f"  {sys.executable}\n")

    print("Workspace root (cwd):")
    print(f"  {os.getcwd()}\n")

    print("Module search path (sys.path):")
    for path_entry in sys.path:
        print(f"  {path_entry}")

    print("\n=== Probe Complete ===\n")


if __name__ == "__main__":
    main()
