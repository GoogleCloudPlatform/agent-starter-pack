# Makefile Template Test Suite

Regression tests for `agent-starter-pack/base_template/Makefile` template refactoring. Ensures changes don't alter generated output across agent types, deployment targets, and feature combinations.

## Coverage

Tests 9 configurations: ADK Base/Live (Cloud Run/Agent Engine), Agentic RAG (Vertex AI/Vector Search), LangGraph, Custom Commands, Agent Garden.

## Running Tests

```bash
# All tests
uv run pytest tests/unit/test_makefile_template.py -v

# Specific categories (use -k filter)
uv run pytest tests/unit/test_makefile_template.py -v -k "test_makefile_hash"  # Fastest
uv run pytest tests/unit/test_makefile_template.py -v -k "test_makefile_snapshot"  # With diffs
uv run pytest tests/unit/test_makefile_template.py -v -k "test_adk_live"  # Specific feature
```

## Refactoring Workflow

1. Run tests before changes (verify baseline)
2. Make incremental changes to `agent-starter-pack/base_template/Makefile`
3. Run tests frequently to catch issues
4. Verify all tests pass after refactoring

## Test Failures

**Snapshot failure**: Generated Makefile changed. Review diff with `git diff tests/fixtures/makefile_snapshots/<config>.makefile`. If intentional, delete snapshot and rerun.

**Hash failure**: Content changed. If intentional, delete `tests/fixtures/makefile_hashes.json` and rerun.

**Feature failure**: Required target missing. Check Jinja2 conditionals in template.

## Updating Baselines

```bash
# All baselines
rm -rf tests/fixtures/makefile_snapshots/*.makefile tests/fixtures/makefile_hashes.json
uv run pytest tests/unit/test_makefile_template.py -v

# Specific config
rm tests/fixtures/makefile_snapshots/<config>.makefile
uv run pytest tests/unit/test_makefile_template.py::TestMakefileGeneration::test_makefile_snapshot[<config>] -v
```

## Test Types

- **Snapshot**: Full output diffs (`tests/fixtures/makefile_snapshots/`) - for debugging
- **Hash**: SHA256 comparison (`tests/fixtures/makefile_hashes.json`) - for CI/CD speed
- **Feature**: Target presence validation - for functionality verification

## Adding Configurations

1. Add to `TEST_CONFIGURATIONS` in `test_makefile_template.py`
2. Run tests to generate baseline: `uv run pytest tests/unit/test_makefile_template.py -v`
3. Verify snapshot: `cat tests/fixtures/makefile_snapshots/<config>.makefile`

## CI/CD

```yaml
- name: Test Makefile Template
  run: uv run pytest tests/unit/test_makefile_template.py -v
```

## Refactoring Tips

- Make small, incremental changes
- Run tests frequently
- Use Jinja2 variables for reusability
- Document complex conditionals
- Group related targets by agent/deployment type

## Troubleshooting

- **Slow tests**: Use hash tests (`-k "test_makefile_hash"`)
- **Need diffs**: Use snapshot tests (`-k "test_makefile_snapshot"`)
- **Jinja2 errors**: Check error message for line number
- **Missing variables**: `StrictUndefined` is already enabled
