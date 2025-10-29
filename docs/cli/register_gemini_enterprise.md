# `register-gemini-enterprise`

Register a deployed Agent Engine to Gemini Enterprise, making it available as a tool within the Gemini Enterprise application.

## Overview

The `register-gemini-enterprise` command registers your deployed Agent Engine with Gemini Enterprise, allowing users to interact with your agent directly through the Gemini Enterprise interface. The command automatically handles both new registrations and updates to existing agents.

## Usage

```bash
uvx --from agent-starter-pack agent-starter-pack-register-gemini-enterprise [OPTIONS]
```

Or if you have agent-starter-pack installed:

```bash
agent-starter-pack-register-gemini-enterprise [OPTIONS]
```

Or via the Makefile (from your generated agent project):

```bash
ID="projects/.../engines/xxx" make register-gemini-enterprise
```

## Quick Start

The simplest usage requires only the Gemini Enterprise app ID, while the agent engine ID is automatically read from `deployment_metadata.json` (created after deploying your agent):

```bash
ID="projects/123456/locations/global/collections/default_collection/engines/my-engine" \
  make register-gemini-enterprise
```

This will:
1. Read the agent engine ID from `deployment_metadata.json`
2. Automatically fetch the agent's display name and description from the deployed Agent Engine
3. Register or update the agent in Gemini Enterprise

## Prerequisites

1. **Deployed Agent Engine**: Your agent must be deployed to Agent Engine first. This creates the `deployment_metadata.json` file.
2. **Gemini Enterprise App**: You need a Gemini Enterprise application configured in Google Cloud.
3. **Authentication**: Ensure you're authenticated with Google Cloud:
   ```bash
   gcloud auth application-default login
   ```

## Required Parameters

### `--gemini-enterprise-app-id`

The full resource name of your Gemini Enterprise application.

**Format:**
```
projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}
```

**Example:**
```bash
agent-starter-pack-register-gemini-enterprise \
  --gemini-enterprise-app-id "projects/123456789/locations/global/collections/default_collection/engines/my-engine"
```

**Environment variable alternatives:**
- `ID` (shorthand, used in Makefile)
- `GEMINI_ENTERPRISE_APP_ID`

**How to find it:**
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to Discovery Engine > Apps
3. Select your Gemini Enterprise application
4. The resource name is in the app details

## Optional Parameters

### `--agent-engine-id`

The Agent Engine resource name to register.

**Format:**
```
projects/{project}/locations/{location}/reasoningEngines/{id}
```

**Default behavior:** If not provided, the command reads the agent engine ID from `deployment_metadata.json` in the current directory.

**Example:**
```bash
agent-starter-pack-register-gemini-enterprise \
  --agent-engine-id "projects/my-project/locations/us-central1/reasoningEngines/1234567890" \
  --gemini-enterprise-app-id "projects/123456789/locations/global/collections/default_collection/engines/my-engine"
```

**Environment variable:** `AGENT_ENGINE_ID`

### `--metadata-file`

Path to the deployment metadata file.

**Default:** `deployment_metadata.json`

**Example:**
```bash
agent-starter-pack-register-gemini-enterprise \
  --metadata-file "path/to/custom_metadata.json" \
  --gemini-enterprise-app-id "projects/.../engines/xxx"
```

### `--display-name`

The display name for your agent in Gemini Enterprise.

**Default behavior:** Automatically fetched from the deployed Agent Engine. If not available, defaults to "My Agent".

**Example:**
```bash
agent-starter-pack-register-gemini-enterprise \
  --display-name "Customer Support Agent" \
  --gemini-enterprise-app-id "projects/.../engines/xxx"
```

**Environment variable:** `GEMINI_DISPLAY_NAME`

### `--description`

Description of what your agent does.

**Default behavior:** Automatically fetched from the deployed Agent Engine. If not available, defaults to "AI Agent".

**Example:**
```bash
agent-starter-pack-register-gemini-enterprise \
  --description "An AI agent that helps customers with product inquiries and troubleshooting" \
  --gemini-enterprise-app-id "projects/.../engines/xxx"
```

**Environment variable:** `GEMINI_DESCRIPTION`

### `--tool-description`

Description of what the tool does when invoked from Gemini Enterprise.

**Default behavior:** Uses the same value as `--description`.

**Example:**
```bash
agent-starter-pack-register-gemini-enterprise \
  --tool-description "Ask this agent about product features, troubleshooting, and support" \
  --gemini-enterprise-app-id "projects/.../engines/xxx"
```

**Environment variable:** `GEMINI_TOOL_DESCRIPTION`

### `--project-id`

GCP project ID for billing purposes.

**Default behavior:** Extracted from the `agent-engine-id` if not provided.

**Example:**
```bash
agent-starter-pack-register-gemini-enterprise \
  --project-id "my-project-id" \
  --gemini-enterprise-app-id "projects/.../engines/xxx"
```

**Environment variable:** `GOOGLE_CLOUD_PROJECT`

### `--authorization-id`

OAuth authorization resource name for secure agent invocation.

**Format:**
```
projects/{project_number}/locations/global/authorizations/{auth_id}
```

**Example:**
```bash
agent-starter-pack-register-gemini-enterprise \
  --authorization-id "projects/123456789/locations/global/authorizations/my-auth" \
  --gemini-enterprise-app-id "projects/.../engines/xxx"
```

**Environment variable:** `GEMINI_AUTHORIZATION_ID`

## Complete Example

```bash
# Set environment variables
export GEMINI_ENTERPRISE_APP_ID="projects/123456789/locations/global/collections/default_collection/engines/my-engine"
export AGENT_ENGINE_ID="projects/my-project/locations/us-central1/reasoningEngines/1234567890"
export GEMINI_DISPLAY_NAME="Product Support Agent"
export GEMINI_DESCRIPTION="An intelligent agent that assists customers with product information and support"
export GEMINI_TOOL_DESCRIPTION="Get help with product features, troubleshooting, and technical support"

# Register the agent
agent-starter-pack-register-gemini-enterprise
```

Or using the Makefile from your agent project:

```bash
# After deploying your agent
make deploy

# Register to Gemini Enterprise
ID="projects/123456789/locations/global/collections/default_collection/engines/my-engine" \
  GEMINI_DISPLAY_NAME="Product Support Agent" \
  GEMINI_DESCRIPTION="An intelligent agent for product support" \
  make register-gemini-enterprise
```

## Updating an Existing Registration

The command automatically detects if an agent is already registered and performs an update instead of creating a duplicate:

```bash
# This will update the existing registration if the same reasoning engine is already registered
ID="projects/.../engines/xxx" make register-gemini-enterprise
```

The update operation preserves the agent resource name while updating the display name, description, and other metadata.

## Troubleshooting

### Error: "No agent engine ID provided and deployment_metadata.json not found"

**Solution:** Either provide `--agent-engine-id` explicitly or ensure you've deployed your agent first (which creates the metadata file):

```bash
make deploy  # This creates deployment_metadata.json
ID="projects/.../engines/xxx" make register-gemini-enterprise
```

### Error: "Invalid GEMINI_ENTERPRISE_APP_ID format"

**Solution:** Ensure your app ID follows the correct format:
```
projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}
```

Note: Use the **project number** (numeric), not the project ID (string).

### Error: "Could not access secret with service account"

**Solution:** Ensure the Cloud Build service account has the `secretmanager.secretAccessor` role if using OAuth authorization.

### Authentication Error

**Solution:** Authenticate with Google Cloud:
```bash
gcloud auth application-default login
```

## See Also

- [Agent Engine Deployment Guide](../guide/deployment.md)
- [Gemini Enterprise Integration](https://cloud.google.com/discovery-engine/docs)
- [Agent Starter Pack CLI Reference](index.md)
