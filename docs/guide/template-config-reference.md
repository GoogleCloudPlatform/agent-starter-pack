# Template Configuration Reference

This document provides a detailed reference for template configuration options.

## Configuration Files

- **Built-in templates**: Use `templateconfig.yaml` files
- **Remote templates**: Configure settings in `pyproject.toml` under the `[tool.agent-starter-pack.settings]` section

The configuration fields are the same for both types of templates.

## Top-Level Fields

| Field               | Type   | Required | Description                                                                                             |
| ------------------- | ------ | -------- | ------------------------------------------------------------------------------------------------------- |
| `base_template`     | string | Yes (for remote agents only)      | The name of the built-in agent that the remote template will inherit from (e.g., `adk`, `agentic_rag`). |
| `name`              | string | Yes      | The display name of your template, shown in the `list` command.                                         |
| `description`       | string | Yes      | A brief description of your template, also shown in the `list` command.                                 |
| `example_question`  | string | No       | An example question or prompt that will be included in the generated project's `README.md`.             |
| `settings`          | object | No       | A nested object containing detailed configuration for the template. See `settings` section below.       |

## The `settings` Object

This object contains fields that control the generated project's features and behavior.

| Field                       | Type           | Description                                                                                                                                 |
| --------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `deployment_targets`        | list(string)   | A list of deployment targets your template supports. Options: `agent_engine`, `cloud_run`.                                                  |
| `tags`                      | list(string)   | A list of tags for categorization. The `adk` tag enables special integrations with the Agent Development Kit.                                 |
| `frontend_type`             | string         | Specifies the frontend to use. Examples: `adk_live_react`, `inspector`. Defaults to `None` (no frontend).                                    |
| `agent_directory`           | string         | The name of the directory where agent code will be placed. Defaults to `app`. Can be overridden by the CLI `--agent-directory` parameter.    |
| `requires_data_ingestion`   | boolean        | If `true`, the user will be prompted to configure a datastore.                                                                              |
| `requires_session`          | boolean        | If `true`, the user will be prompted to choose a session storage type (e.g., `cloud_sql`) when using the `cloud_run` target.                    |
| `interactive_command`       | string         | The `make` command to run for starting the agent, after the agent code is being created (e.g., `make playground`, `make dev`). Defaults to `playground`. |
| `extra_dependencies`        | list(string)   | **Note:** This field is ignored by remote templates. It is used internally by the starter pack's built-in templates. Your `pyproject.toml` is the single source of truth for dependencies. |
