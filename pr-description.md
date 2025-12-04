## Summary
- Add `--prototype` / `-p` flag for creating minimal projects
- Add "None" option to CI/CD runner interactive prompt
- Add version locking for `enhance` command
- Restructure `pyproject.toml` metadata with nested `create_params` section
- Default Agent Garden mode to prototype
- Add quick testing commands to GEMINI.md

## Prototype Mode

Skips:
- `.github/workflows/` or `.cloudbuild/`
- `deployment/` (Terraform)
- `tests/load_test/`
- Makefile `setup-dev-env` target

## Version Locking

The `enhance` command reads `asp_version` and `create_params` from the project's `pyproject.toml`, then re-executes with the locked version:

```
uvx agent-starter-pack@0.25.0 enhance --base-template adk_base --deployment-target cloud_run ...
```

## Usage
```bash
# Prototype mode
agent-starter-pack create my-project -p -d agent_engine

# Quick testing
uv run agent-starter-pack create test -p -s -y -d agent_engine --output-dir target
```

## Test Plan
- [x] `--prototype` creates minimal project
- [x] Regular mode still includes full infrastructure
- [x] Enhance version lock reads `create_params` correctly
- [x] All metadata tests pass with new structure
