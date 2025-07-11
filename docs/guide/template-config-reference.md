# `templateconfig.yaml` Reference

This document provides a detailed reference for all the available fields in the `templateconfig.yaml` file. This file is used to configure both the built-in agents provided by the starter pack and your own remote templates.

## Top-Level Fields

| Field               | Type   | Required | Description                                                                                             |
| ------------------- | ------ | -------- | ------------------------------------------------------------------------------------------------------- |
| `base_template`     | string | Yes      | The name of the built-in agent that the remote template will inherit from (e.g., `adk_base`, `agentic_rag`). |
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
| `extra_dependencies`        | list(string)   | **Note:** This field is ignored by remote templates. It is used internally by the starter pack's built-in templates. Your `pyproject.toml` is the single source of truth for dependencies. |
| `commands`                  | object         | Allows for customizing the `Makefile` in the generated project. See `commands` section below.                                               |

## The `commands` Object

This object allows you to add new `make` commands or override existing ones.

### `override`
Use this to change the behavior of a default command.

```yaml
settings:
  commands:
    override:
      # Replaces the default 'make install' command
      install: "uv sync --dev --extra jupyter && npm --prefix frontend install"
```

### `extra`
Use this to add new commands to the `Makefile`.

-   **Simple Command**:
    ```yaml
    settings:
      commands:
        extra:
          # Adds 'make custom-lint'
          custom-lint:
            command: "ruff check ."
            description: "Run a custom lint check."
    ```

-   **Deployment-Specific Command**:
    You can provide different versions of a command based on the chosen `deployment_target`.

    ```yaml
    settings:
      commands:
        extra:
          dev-backend:
            command:
              # Command for 'make dev-backend' if target is 'agent_engine'
              agent_engine: 'uv run adk api_server app --allow_origins="*"'
              # Command for 'make dev-backend' if target is 'cloud_run'
              cloud_run: 'ALLOW_ORIGINS="*" uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload'
            description: "Start the backend development server."
    ```