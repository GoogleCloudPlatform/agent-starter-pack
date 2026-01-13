# Implementation Plan - Fix TOML Parsing Error in Base Template

The `pyproject.toml` file in `agent-starter-pack/agent_starter_pack/base_templates/python/` contains Jinja2 templating syntax, which causes TOML parsing errors in environments that automatically scan for TOML files. This plan renames the file to `pyproject.toml.template` to avoid these errors and updates the toolchain to handle the new name.

## Proposed Changes

### 1. Rename Template File
- Move `agent_starter_pack/base_templates/python/pyproject.toml` to `agent_starter_pack/base_templates/python/pyproject.toml.template`.

### 2. Update `agent_starter_pack/cli/utils/template.py`
- Modify `process_template` to check for `pyproject.toml.template` in the temporary template directory.
- Rename it to `pyproject.toml` before invoking `cookiecutter`.

### 3. Update `agent_starter_pack/utils/generate_locks.py`
- Update the default value for the `--template` option in `main` to `agent_starter_pack/base_templates/python/pyproject.toml.template`.

## Verification Plan

### Automated Tests
- Run `uv run agent-starter-pack create test-project -p -s -y -d agent_engine --output-dir target` to verify project generation.
- Verify that `target/test-project/pyproject.toml` is created and correctly rendered.

### Manual Verification
- Confirm that the TOML parsing warning for the base template file is no longer present in the logs.
