# `setup-cicd`

The `setup-cicd` command is a powerful utility provided by `agent-starter-pack` that automates the deployment of your complete Terraform infrastructure and configures your Google Cloud projects in a single operation.

**⚡️ Quick Start Example:**

Getting started is straightforward. We recommend using `uvx` to execute the command, as `uv` (a prerequisite, see below) will handle fetching and running the `agent-starter-pack` for you, even if it's not installed globally:

```bash
uvx agent-starter-pack setup-cicd
```
*(You will be prompted for Staging and Production project IDs)*

Alternatively, you can provide the project IDs directly as flags:

```bash
uvx agent-starter-pack setup-cicd \
  --staging-project=your-staging-project-id \
  --prod-project=your-prod-project-id
```

**💡 Tip:** Using `uvx` (e.g., `uvx agent-starter-pack ...`) ensures you are able to run the command without needing to install the `agent-starter-pack` package globally or in your current environment. `uv` itself must be installed.

**⚠️ Important Considerations:**

*   **Experimental:** This command is under active development. Use it with caution and report any issues.
*   **Production Use:** For production environments, we **strongly recommend** following the detailed instructions in `deployment/README.md`. Manual setup offers greater control over security and configuration. This automated command is best suited for development and testing.
*   **GitHub Only:** Currently, only GitHub is supported as a Git provider.

## Prerequisites

1.  **Run from Project Root:** Execute the command from the root directory of your `agent-starter-pack` project (where `pyproject.toml` is located).
2.  **Install Tools:**
    *   `uv`: The command will be run using `uvx`. Ensure `uv` is installed. (See [uv installation guide](https://github.com/astral-sh/uv#installation))
    *   Terraform
    *   `gh` CLI (GitHub CLI): Install and authenticate using `gh auth login`.
    *   `gcloud` CLI (Google Cloud SDK): Authenticate using `gcloud auth application-default login`.
3.  **Google Cloud Projects:** You need at least two Google Cloud projects: one for staging and one for production. The command will prompt you for their IDs if you don't provide the `--staging-project` and `--prod-project` flags. You also need a project to host the CI/CD resources (Cloud Build, Artifact Registry, Terraform state). You can specify this using `--cicd-project`. If omitted, the production project will be used for CI/CD resources.
4.  **Permissions:** The user or service account running this command must have the `Owner` role on the specified Google Cloud projects (staging, production, CI/CD if specified, development if specified). This is necessary for creating resources and assigning IAM roles.

## How it Works

The `setup-cicd` command automates the following:

1.  **GitHub Integration:** Creates a new private GitHub repository or connects to an existing one (prompting for details if needed).
2.  **Project ID Confirmation:** Prompts for Staging and Production project IDs if they are not provided via flags.
3.  **Cloud Build Connection:** Sets up a Cloud Build connection to your GitHub repository.
4.  **Terraform Setup:**
    *   Configures Terraform to manage your CI/CD infrastructure (Cloud Build triggers, IAM permissions, etc.) and optionally, a development environment (if `--dev-project` is provided).
    *   By default, sets up remote Terraform state management using a Google Cloud Storage (GCS) bucket in your CI/CD project (`<CICD_PROJECT_ID>-terraform-state`). Use `--local-state` to opt-out.
5.  **Resource Deployment:** Runs `terraform apply` to create the necessary resources in Google Cloud and configure the GitHub repository connection.
6.  **Local Git Setup:** Initializes a Git repository locally (if needed) and adds the GitHub repository as the `origin` remote.

## Running the Command

```bash
uvx agent-starter-pack setup-cicd \
    [--staging-project <YOUR_STAGING_PROJECT_ID>] \
    [--prod-project <YOUR_PROD_PROJECT_ID>] \
    [--cicd-project <YOUR_CICD_PROJECT_ID>] \
    [--dev-project <YOUR_DEV_PROJECT_ID>] \
    [--region <GCP_REGION>] \
    [--repository-name <GITHUB_REPO_NAME>] \
    [--repository-owner <GITHUB_USERNAME_OR_ORG>] \
    [--local-state] \
    [--auto-approve] \
    [--debug]
```

**Key Options:**

*   `--staging-project`, `--prod-project`: **Required Information.** Your Google Cloud project IDs for staging and production environments. The command will prompt for these if the flags are omitted.
*   `--cicd-project`: (Optional) Project ID for hosting CI/CD resources (Cloud Build, Artifact Registry, Terraform state bucket). If omitted, defaults to the production project ID (provided via flag or prompt).
*   `--dev-project`: (Optional) Project ID for a dedicated development environment managed by Terraform. If provided, Terraform will also be applied to set up resources in this development project.
*   `--region`: (Optional) GCP region for resources (default: `us-central1`).
*   `--repository-name`: (Optional) Name for the GitHub repository. If omitted, you'll be prompted or a name will be generated.
*   `--repository-owner`: (Optional) Your GitHub username or organization. Defaults to the authenticated `gh` user if omitted.
*   `--local-state`: (Optional) Use local files for Terraform state instead of the default GCS backend. Not recommended for collaboration.
*   `--auto-approve`: (Optional) Skip interactive prompts (including project ID prompts if flags are omitted). Use carefully.
*   `--debug`: (Optional) Enable verbose logging.

*(For advanced/programmatic use with pre-existing connections, see options like `--github-pat`, `--github-app-installation-id`, `--host-connection-name` by running `uvx agent-starter-pack setup-cicd --help`)*

## After Running the Command

1.  **Commit and Push:** This is crucial to trigger the pipeline.
    ```bash
    git add .
    git commit -m "Initial commit of agent starter pack"
    git push -u origin main
    ```
2.  **Verify:** Check your GitHub repository and Google Cloud projects (Cloud Build > Triggers, Secret Manager, IAM) to see the created resources.

## Manual CI/CD Setup (Recommended for Production)

For robust, production-ready deployments with fine-grained control over security, customization, and advanced CI/CD practices, please follow the [manual setup guide](../guide/deployment.md).
