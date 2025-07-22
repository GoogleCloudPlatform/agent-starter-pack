# `setup-cicd`

The `setup-cicd` command is a powerful utility that automates the deployment of your complete CI/CD infrastructure, configuring your Google Cloud projects and GitHub repository in a single operation. It intelligently adapts to your project's configuration, supporting both **Google Cloud Build** and **GitHub Actions** as CI/CD runners.

**⚡️ Quick Start Example:**

Getting started is straightforward. From the root of your generated agent project, run the following command. The tool will guide you through the process.

You can use the `pip` workflow for a traditional setup, or `uvx` to create a project in a single command without a permanent install.

```bash [uvx]
uvx agent-starter-pack setup-cicd
```

```bash [pip]
agent-starter-pack setup-cicd
```

*(You will be prompted for Staging and Production project IDs)*

Alternatively, you can provide the project IDs and other details directly as flags:

```bash
uvx agent-starter-pack setup-cicd \
  --staging-project your-staging-project-id \
  --prod-project your-prod-project-id \
  --repository-name my-awesome-agent
```


**⚠️ Important Considerations:**

*   **Run from Project Root:** This command must be executed from the root directory of your generated agent project (the directory containing `pyproject.toml`).
*   **Production Use:** This command is designed to set up a production-ready CI/CD pipeline. However, for highly customized or complex production environments, you may want to review the generated Terraform configuration in `deployment/terraform` before applying.

## Prerequisites

1.  **Required Tools:**
    *   **`uvx` or `agent-starter-pack`:** The command is part of the starter pack CLI.
    *   **Terraform:** Required for infrastructure provisioning.
    *   **`gh` CLI (GitHub CLI):** The tool uses the GitHub CLI to interact with your repository.
        *   **Authentication:** You must be authenticated. Run `gh auth login`.
        *   **Required Scopes:** Your GitHub token needs the **`repo`** and **`workflow`** scopes to create repositories and set up CI/CD. The tool will check for these scopes and guide you if they are missing.
    *   **`gcloud` CLI (Google Cloud SDK):** Required for interacting with Google Cloud.
        *   **Authentication:** You must be authenticated. Run `gcloud auth application-default login`.

2.  **Google Cloud Projects:** You need at least two Google Cloud projects: one for `staging` and one for `production`. You also need a project to host the CI/CD resources (e.g., Cloud Build, Artifact Registry, Terraform state). You can specify this using `--cicd-project`. If omitted, the production project will be used for CI/CD resources.

3.  **Permissions:** The user or service account running this command must have the `Owner` role on the specified Google Cloud projects. This is necessary for creating resources and assigning IAM roles.

## How it Works

The `setup-cicd` command performs the following steps automatically:

1.  **CI/CD Runner Detection:** It inspects your project's structure to automatically detect whether you are using **Google Cloud Build** or **GitHub Actions**.
2.  **GitHub Integration:** It prompts you to create a new private GitHub repository or connect to an existing one.
3.  **Project ID Confirmation:** It prompts for Staging and Production project IDs if they are not provided as flags.
4.  **Infrastructure Setup (Terraform):**
    *   It configures and applies the Terraform scripts located in `deployment/terraform`.
    *   **For Google Cloud Build:** It sets up a Cloud Build connection to your GitHub repository, either interactively or programmatically (if a GitHub PAT is provided).
    *   **For GitHub Actions:** It configures Workload Identity Federation (WIF) to allow GitHub Actions to securely authenticate with Google Cloud without service account keys. It also creates the necessary secrets and variables in your GitHub repository.
    *   By default, it sets up remote Terraform state management using a Google Cloud Storage (GCS) bucket. Use `--local-state` to opt-out.
5.  **Resource Deployment:** It runs `terraform apply` to create all the necessary resources in your Google Cloud projects.
6.  **Local Git Setup:** It initializes a Git repository locally (if needed) and adds your GitHub repository as the `origin` remote.

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
*   `--cicd-project`: (Optional) Project ID for hosting CI/CD resources. If omitted, defaults to the production project ID.
*   `--dev-project`: (Optional) Project ID for a dedicated development environment.
*   `--region`: (Optional) GCP region for resources (default: `us-central1`).
*   `--repository-name`, `--repository-owner`: (Optional) Details for your GitHub repository. If omitted, you'll be prompted.
*   `--local-state`: (Optional) Use local files for Terraform state instead of the default GCS backend.
*   `--auto-approve`: (Optional) Skip all interactive prompts.
*   `--debug`: (Optional) Enable verbose logging for troubleshooting.

*(For advanced programmatic use with Google Cloud Build, see options like `--github-pat`, `--github-app-installation-id`, and `--host-connection-name` by running `uvx agent-starter-pack setup-cicd --help`)*

## After Running the Command

To trigger your new CI/CD pipeline, you need to commit and push your code:

```bash
git add .
git commit -m "Initial commit of agent starter pack"
git push -u origin main
```

After pushing, you can verify the created resources and running pipelines in your GitHub repository and Google Cloud projects.