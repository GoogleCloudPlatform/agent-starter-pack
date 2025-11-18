# `register-gemini-enterprise`

Register a deployed Agent Engine to Gemini Enterprise, making it available as a tool within the Gemini Enterprise application.

## Usage

```bash
# Via Makefile (recommended) - Interactive mode
make register-gemini-enterprise

# Direct command (installed)
agent-starter-pack register-gemini-enterprise [OPTIONS]

# Or with uvx (no install required)
uvx agent-starter-pack@latest register-gemini-enterprise [OPTIONS]
```

## Quick Start

After deploying your agent, simply run the interactive command:

```bash
make deploy
make register-gemini-enterprise  # Interactive prompts guide you
```

The command automatically:
- Detects Agent Engine ID from `deployment_metadata.json` (with confirmation)
- Prompts for Gemini Enterprise app details step-by-step
- Fetches display name and description from the deployed Agent Engine
- Constructs the full Gemini Enterprise resource name
- Creates or updates the registration in Gemini Enterprise

### Interactive Prompts

When you run the command, you'll be prompted for:

1. **Agent Engine ID** - Auto-detected from `deployment_metadata.json`, you can confirm or provide a different one
2. **Project number** - Defaults to the project from Agent Engine ID
3. **Location** - Defaults to `global` (options: global, us, eu)
4. **Gemini Enterprise ID** - The short ID from the Gemini Enterprise Apps table (e.g., `gemini-enterprise-1762980_1762980842627`)

The command constructs the full resource name and asks for confirmation before proceeding.

## Prerequisites

- Deployed Agent Engine (creates `deployment_metadata.json`)
- Gemini Enterprise application configured in Google Cloud
- Authentication: `gcloud auth application-default login`

## Non-Interactive Mode

For CI/CD or scripting, you can provide all parameters via environment variables or command-line options:

```bash
# Using environment variables
ID="projects/123456/locations/global/collections/default_collection/engines/my-engine" \
  make register-gemini-enterprise

# Or provide the full Gemini Enterprise app ID
GEMINI_ENTERPRISE_APP_ID="projects/123456/locations/global/collections/default_collection/engines/my-engine" \
  agent-starter-pack register-gemini-enterprise
```

## Parameters

### Optional

**`--gemini-enterprise-app-id`** (env: `ID`, `GEMINI_ENTERPRISE_APP_ID`)

Gemini Enterprise app resource name. If not provided, the command runs in interactive mode.

Format: `projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}`

Note: Use project **number** (numeric), not project ID (string).

Find the Gemini Enterprise ID: Cloud Console > Gemini Enterprise > Apps > ID column

### Other Options

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

**Interactive mode (recommended):**
```bash
make register-gemini-enterprise
# Follow the prompts to provide:
# - Agent Engine ID (auto-detected)
# - Project number (auto-filled)
# - Location (defaults to 'global')
# - Gemini Enterprise ID
```

**Non-interactive with environment variables:**
```bash
ID="projects/123456789/locations/global/collections/default_collection/engines/my-engine" \
  make register-gemini-enterprise
```

**With custom metadata:**
```bash
ID="projects/123456789/locations/global/collections/default_collection/engines/my-engine" \
  GEMINI_DISPLAY_NAME="Support Agent" \
  GEMINI_DESCRIPTION="Customer support assistant" \
  make register-gemini-enterprise
```

## Troubleshooting

**Interactive prompts not showing**
- Make sure you're running the command without providing all parameters
- If you set `GEMINI_ENTERPRISE_APP_ID` or `ID` environment variable, the command skips interactive mode

**"Invalid Agent Engine ID format"**
- Ensure format: `projects/{project_number}/locations/{location}/reasoningEngines/{engine_id}`
- Check that you're using the correct resource name from `deployment_metadata.json` or Agent Builder Console

**Can't find Gemini Enterprise ID**
- Go to: Cloud Console > Gemini Enterprise > Apps
- Copy the value from the **ID** column (e.g., `gemini-enterprise-1762980_1762980842627`)

**Authentication errors**
- Run: `gcloud auth application-default login`

## See Also

- [Agent Engine Deployment Guide](../guide/deployment.md)
- [Gemini Enterprise Integration](https://cloud.google.com/discovery-engine/docs)
- [CLI Reference](index.md)
