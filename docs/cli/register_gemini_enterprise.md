# `register-gemini-enterprise`

Register a deployed Agent Engine to Gemini Enterprise, making it available as a tool within the Gemini Enterprise application.

## Usage

```bash
# Via Makefile (recommended)
ID="projects/.../engines/xxx" make register-gemini-enterprise

# Direct command
uvx --from agent-starter-pack agent-starter-pack-register-gemini-enterprise [OPTIONS]
```

## Quick Start

After deploying your agent, register it with just the Gemini Enterprise app ID. The agent engine ID is automatically read from `deployment_metadata.json`:

```bash
make deploy  # Creates deployment_metadata.json

ID="projects/123456/locations/global/collections/default_collection/engines/my-engine" \
  make register-gemini-enterprise
```

The command automatically:
- Reads agent engine ID from `deployment_metadata.json`
- Fetches display name and description from the deployed Agent Engine
- Creates or updates the registration in Gemini Enterprise

## Prerequisites

- Deployed Agent Engine (creates `deployment_metadata.json`)
- Gemini Enterprise application configured in Google Cloud
- Authentication: `gcloud auth application-default login`

## Parameters

### Required

**`--gemini-enterprise-app-id`** (env: `ID`, `GEMINI_ENTERPRISE_APP_ID`)

Gemini Enterprise app resource name.

Format: `projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}`

Note: Use project **number** (numeric), not project ID (string).

Find it: Cloud Console > Discovery Engine > Apps > [Your App] > Details

### Optional

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `--agent-engine-id` | `AGENT_ENGINE_ID` | From `deployment_metadata.json` | Agent Engine resource name |
| `--metadata-file` | - | `deployment_metadata.json` | Path to deployment metadata file |
| `--display-name` | `GEMINI_DISPLAY_NAME` | From Agent Engine or "My Agent" | Display name in Gemini Enterprise |
| `--description` | `GEMINI_DESCRIPTION` | From Agent Engine or "AI Agent" | Agent description |
| `--tool-description` | `GEMINI_TOOL_DESCRIPTION` | Same as `--description` | Tool description for Gemini Enterprise |
| `--project-id` | `GOOGLE_CLOUD_PROJECT` | Extracted from agent-engine-id | GCP project ID for billing |
| `--authorization-id` | `GEMINI_AUTHORIZATION_ID` | None | OAuth authorization resource name |

## Examples

**Basic registration:**
```bash
ID="projects/123456789/locations/global/collections/default_collection/engines/my-engine" \
  make register-gemini-enterprise
```

**With custom metadata:**
```bash
ID="projects/.../engines/xxx" \
  GEMINI_DISPLAY_NAME="Support Agent" \
  GEMINI_DESCRIPTION="Customer support assistant" \
  make register-gemini-enterprise
```

**Using environment variables:**
```bash
export GEMINI_ENTERPRISE_APP_ID="projects/.../engines/xxx"
export GEMINI_DISPLAY_NAME="Product Support Agent"
export GEMINI_DESCRIPTION="AI agent for product support"

agent-starter-pack-register-gemini-enterprise
```

## Troubleshooting

**"No agent engine ID provided and deployment_metadata.json not found"**
- Run `make deploy` first to create the metadata file, or provide `--agent-engine-id` explicitly

**"Invalid GEMINI_ENTERPRISE_APP_ID format"**
- Ensure format: `projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}`
- Use project **number** (numeric), not project ID

**"Could not access secret with service account"**
- Grant Cloud Build service account the `secretmanager.secretAccessor` role

**Authentication errors**
- Run: `gcloud auth application-default login`

## See Also

- [Agent Engine Deployment Guide](../guide/deployment.md)
- [Gemini Enterprise Integration](https://cloud.google.com/discovery-engine/docs)
- [CLI Reference](index.md)
