## Summary
- Add Windows compatibility for template creation
- Replace Jinja2 conditionals in filenames with Python-based logic
- Add GitHub Actions workflow to test on Windows (runs on push to main)

## Problem
Windows users cannot use the Agent Starter Pack because:
1. Git cannot checkout the repo - filenames with Jinja2 syntax (`{% if ... %}`) exceed Windows' 260 character MAX_PATH limit
2. The `%` character in filenames is interpreted as environment variable syntax on Windows

## Solution
- Add `CONDITIONAL_FILES` dict mapping file paths to Python condition functions
- Add `apply_conditional_files()` function to handle file inclusion/exclusion post-copy
- Rename 11 files/directories from Jinja2 syntax to simple names
- Files are filtered after copying based on config values, then cleaned up by existing `unused_*` logic

## Additional Fixes
- Add `**/.venv/*` to `_copy_without_render` to exclude nested `.venv` directories from Jinja2 parsing
- Fix lint error: use list unpacking instead of concatenation (RUF005)
- Set UTF-8 encoding env vars for Windows CI to handle emoji output

## Changed Files
- `agent_starter_pack/cli/utils/template.py` - Add conditional files logic
- `agent_starter_pack/base_template/` - Rename 7 conditional files/directories
- `agent_starter_pack/deployment_targets/agent_engine/` - Rename 4 conditional files
- `.github/workflows/test-windows.yml` - Add Windows CI workflow
