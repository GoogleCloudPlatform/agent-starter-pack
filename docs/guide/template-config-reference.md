# `templateconfig.yaml` Reference

This document provides a detailed reference for all the available fields in the `templateconfig.yaml` file. This file is used to configure both the built-in agents provided by the starter pack and your own remote templates.

## Top-Level Fields

| Field               | Type   | Required | Description                                                                                             |
| ------------------- | ------ | -------- | ------------------------------------------------------------------------------------------------------- |
| `base_template`     | string | Yes (for remote agents only)      | The name of the built-in agent that the remote template will inherit from (e.g., `adk_base`, `agentic_rag`). |
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
| `frontend_type`             | string         | Specifies the frontend to use. Examples: `streamlit`, `live_api_react`. Defaults to `streamlit`.                                             |
| `requires_data_ingestion`   | boolean        | If `true`, the user will be prompted to configure a datastore.                                                                              |
| `requires_session`          | boolean        | If `true`, the user will be prompted to choose a session storage type (e.g., `alloydb`) when using the `cloud_run` target.                    |
| `interactive_command`       | string         | The `make` command to run for starting the agent, after the agent code is being created (e.g., `make playground`, `make dev`). Defaults to `playground`. |
| `extra_dependencies`        | list(string)   | **Note:** This field is ignored by remote templates. It is used internally by the starter pack's built-in templates. Your `pyproject.toml` is the single source of truth for dependencies. |
