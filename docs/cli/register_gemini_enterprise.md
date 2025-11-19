# `register-gemini-enterprise`

Register a deployed agent to Gemini Enterprise, making it available as a tool within Gemini Enterprise.

Supports:
- **ADK agents** deployed to Agent Engine
- **A2A agents** deployed to Cloud Run

> **Note:** A2A agents deployed to Agent Engine are not yet supported for Gemini Enterprise registration. This feature will be available in a future release.

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

### For ADK Agents

After deploying your ADK agent to Agent Engine:

```bash
make deploy
make register-gemini-enterprise  # Interactive prompts guide you
```

The command automatically:
- Detects Agent Engine ID from `deployment_metadata.json`
- Prompts for Gemini Enterprise app details step-by-step
- Fetches display name and description from the deployed Agent Engine
- Constructs the full Gemini Enterprise resource name
- Creates or updates the registration in Gemini Enterprise

### For A2A Agents

For A2A agents deployed to Cloud Run:

```bash
make deploy
make register-gemini-enterprise  # Auto-detects A2A agent and Cloud Run URL
```

**Auto-detection:** The Makefile automatically constructs the agent card URL from your Cloud Run service.

**Manual specification:**
```bash
AGENT_CARD_URL="https://your-service.run.app/a2a/app/.well-known/agent-card.json" \
  make register-gemini-enterprise
```

### Interactive Prompts


#### For ADK Agents:
1. **Agent Engine ID** - Auto-detected from `deployment_metadata.json`
2. **Project number** - Defaults to the project from Agent Engine ID
3. **Location** - Defaults to `global` (options: global, us, eu)
4. **Gemini Enterprise ID** - The short ID from the Gemini Enterprise Apps table

#### For A2A Agents:
1. **Agent card URL** - Auto-constructed from your Cloud Run service URL
2. **Gemini Enterprise app details** - Same as ADK agents

## Prerequisites

**For ADK Agents:**
- Deployed Agent Engine (creates `deployment_metadata.json`)
- Gemini Enterprise application configured in Google Cloud
- Authentication: `gcloud auth application-default login`

**For A2A Agents:**
- Deployed agent with accessible agent card endpoint
- Gemini Enterprise application configured in Google Cloud
- **(Optional)** OAuth 2.0 authorization configured for accessing Google Cloud resources on behalf of users
- Authentication: `gcloud auth login` (for identity token)

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
| `--agent-card-url` | `AGENT_CARD_URL` | None | Agent card URL for A2A agents. If provided, registers as A2A agent |
| `--deployment-target` | `DEPLOYMENT_TARGET` | Auto-detected | Deployment target: `agent_engine` or `cloud_run` |
| `--project-number` | `PROJECT_NUMBER` | Auto-detected | GCP project number (for smart defaults) |
| `--agent-engine-id` | `AGENT_ENGINE_ID` | From `deployment_metadata.json` | Agent Engine resource name (ADK agents only) |
| `--metadata-file` | - | `deployment_metadata.json` | Path to deployment metadata file |
| `--display-name` | `GEMINI_DISPLAY_NAME` | From agent or "My Agent" | Display name in Gemini Enterprise |
| `--description` | `GEMINI_DESCRIPTION` | From agent or "AI Agent" | Agent description |
| `--tool-description` | `GEMINI_TOOL_DESCRIPTION` | Same as `--description` | Tool description (ADK agents only) |
| `--project-id` | `GOOGLE_CLOUD_PROJECT` | Extracted from context | GCP project ID for billing |
| `--authorization-id` | `GEMINI_AUTHORIZATION_ID` | None | Optional: Pre-configured OAuth authorization resource name (e.g., projects/{project_number}/locations/global/authorizations/{auth_id}) |

## Examples

### ADK Agent Examples

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

### A2A Agent Examples

**Interactive mode (recommended):**
```bash
make register-gemini-enterprise
# Makefile auto-constructs agent card URL from Cloud Run service
# Follow prompts for Gemini Enterprise configuration
```

**Non-interactive mode:**
```bash
AGENT_CARD_URL="https://my-agent-abc123-uc.a.run.app/a2a/app/.well-known/agent-card.json" \
  ID="projects/123456789/locations/global/collections/default_collection/engines/my-engine" \
  make register-gemini-enterprise
```

## Troubleshooting

### General Issues

**Interactive prompts not showing**
- Make sure you're running the command without providing all parameters
- If you set `GEMINI_ENTERPRISE_APP_ID` or `ID` environment variable, the command skips some prompts

**Can't find Gemini Enterprise ID**
- Go to: Cloud Console > Gemini Enterprise > Apps
- Copy the value from the **ID** column (e.g., `gemini-enterprise-123456_1234567890`)

### ADK-Specific Issues

**"Invalid Agent Engine ID format"**
- Ensure format: `projects/{project_number}/locations/{location}/reasoningEngines/{engine_id}`
- Check that you're using the correct resource name from `deployment_metadata.json` or Agent Builder Console

**Authentication errors (ADK)**
- Run: `gcloud auth application-default login`

### A2A-Specific Issues

**"Failed to fetch agent card"**
- Verify the agent card URL is correct and accessible
- Ensure the Cloud Run service is deployed and running

**Authentication errors**
- Run: `gcloud auth login`
- Ensure you have permission to invoke the Cloud Run service

## See Also

- [Agent Engine Deployment Guide](../guide/deployment.md)
- [Gemini Enterprise Integration](https://cloud.google.com/discovery-engine/docs)
- [CLI Reference](index.md)
