# Troubleshooting

This guide helps resolve common issues with the Agent Starter Pack.

## Authentication Issues

For detailed information on authentication with Vertex AI, visit the [official documentation](https://cloud.google.com/vertex-ai/docs/authentication).

### "Could not find credentials" or "Could not find project" Error

**Problem**: Missing credentials error with Vertex AI.

**Solution**:

1.  Log in to Google Cloud: `gcloud auth login --update-adc`
2.  Set the correct project:
    ```bash
    gcloud config set project YOUR_PROJECT_ID
    gcloud auth application-default set-quota-project YOUR_PROJECT_ID
    ```

### Vertex AI API Not Enabled

**Problem**: Operations fail because the Vertex AI API is not enabled in your project.

**Solution**:

1. Enable the Vertex AI API:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

2. Verify the API is enabled:
   ```bash
   gcloud services list --filter=aiplatform.googleapis.com
   ```

### Permission Denied Errors
**Problem**: "Permission denied" errors with Google Cloud APIs.

**Solution**: Ensure your user or service account has the necessary IAM roles.  For example, for Vertex AI, you often need `roles/aiplatform.user`.  Grant roles using the `gcloud projects add-iam-policy-binding` command or the Cloud Console.

### Command Not Found: agent-starter-pack

**Problem**: "Command not found" error after installation.

**Solution**:

1. Verify installation:
   ```bash
   pip list | grep agent-starter-pack
   ```
2. Check PATH:
   ```bash
   echo $PATH
   ```
3. Reinstall if needed:
   ```bash
   pip install --user agent-starter-pack
   ```
4. For pipx:
   ```bash
   pipx ensurepath
   source ~/.bashrc  # or ~/.zshrc
   ```

## Project Creation Issues

### Project Creation Fails

**Problem**: `agent-starter-pack create` fails.

**Solution**:

1.  **Check Error Messages:** Examine output for clues.
2.  **Write Permissions:** Ensure write access to the directory.
3.  **Project Name:** Use lowercase letters, numbers and hyphens only.
4.  **Debug Mode:** Consider using debug mode to get more detailed error information:
    ```bash
    agent-starter-pack create my-project-name --debug
    ```

### Issues with Agent Engine

Consider leveraging the [public product documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/troubleshooting/set-up)

## Getting More Help

If issues persist:

1.  **Check GitHub Issues:** Search for existing Github issues in the `agent-starter-pack` Github repository.
2.  **File a New Issue:** Provide:

    *   Problem description.
    *   Steps to reproduce.
    *   Error messages (preferably run with `--debug` flag for detailed logs).
    *   Environment: OS, Python version, `agent-starter-pack` version, installation method, shell.
