## ⚙️ CI/CD Setup (Experimental)

This starter pack provides an *experimental* command to automate the setup of a basic CI/CD pipeline. This pipeline connects your agent to a GitHub repository and uses Google Cloud Build for automated testing and deployment.

**⚠️ Important Notes:**

*   **Experimental Feature:** The `setup-cicd` command is under active development. Expect potential changes and report any issues you encounter.
*   **Production Readiness:** For production deployments, we *strongly* recommend following the manual setup instructions in the `deployment/README.md` file. The manual approach provides greater control over security, customization, and environment-specific configurations. This automated setup is primarily intended for development and testing purposes.
*   **Git Provider:** Currently, only GitHub is supported. Support for other Git providers may be added in the future.

### Quick CI/CD Setup (Automated)

This command streamlines the CI/CD setup process. It handles:

1.  **GitHub Repository:** Creates a new GitHub repository or connects to an existing one (prompts for confirmation if the existing repository is not empty).
2.  **Cloud Build Connection:** Establishes a connection between your GitHub repository and Google Cloud Build.
3.  **Development Environment:** Sets up the infrastructure for your development environment using Terraform (optional, requires `--dev-project`).
4.  **CI/CD Triggers:** Configures basic Cloud Build triggers for pull request checks and deployments.
5.  **Terraform State:** By default, configures remote Terraform state management using a Google Cloud Storage (GCS) bucket. You can opt for local state management using `--local-state`.

**Prerequisites:**

*   Run this command from the root directory of your `agent-starter-pack` project (the directory containing `pyproject.toml`).
*   Install the `gh` CLI and authenticate with GitHub (`gh auth login`).
*   Authenticate with Google Cloud (`gcloud auth application-default login`).
*   Install Terraform.

**Command Usage:**
```bash
agent-starter-pack setup-cicd \
    --staging-project <YOUR_STAGING_PROJECT_ID> \
    --prod-project <YOUR_PROD_PROJECT_ID> \
    --cicd-project <YOUR_CICD_PROJECT_ID> \
    [--dev-project <YOUR_DEV_PROJECT_ID>] \
    [--region <GCP_REGION>] \
    [--repository-name <GITHUB_REPO_NAME>] \
    [--repository-owner <GITHUB_USERNAME_OR_ORG>] \
    [--host-connection-name <CONNECTION_NAME>] \
    [--github-pat <YOUR_GITHUB_PAT>] \
    [--github-app-installation-id <YOUR_GITHUB_APP_INSTALLATION_ID>] \
    [--local-state] \
    [--debug] \
    [--auto-approve]
```

**Options:**

*   `--staging-project`: **Required.** The Google Cloud project ID for your staging environment.
*   `--prod-project`: **Required.** The Google Cloud project ID for your production environment.
*   `--cicd-project`: **Required.** The Google Cloud project ID where your CI/CD resources (Cloud Build, Secret Manager, etc.) will reside. This can be the same as your staging or production project.
*   `--dev-project`: (Optional) The Google Cloud project ID for your development environment. If provided, the setup will also configure a development environment via Terraform.
*   `--region`: The GCP region to use for resources (default: `us-central1`).
*   `--repository-name`: (Optional) The name for the GitHub repository. If omitted in interactive mode, you will be prompted, or a name will be generated (e.g., `genai-app-1678886400`). Required in programmatic mode if the repository doesn't exist.
*   `--repository-owner`: (Optional) Your GitHub username or organization name where the repository resides or will be created. If omitted in interactive mode, it defaults to your authenticated GitHub user, and you will be prompted. Required in programmatic mode if the repository doesn't exist.
*   `--host-connection-name`: (Optional) The name for the Cloud Build connection to GitHub (default: `github-connection`).
*   `--github-pat`: (Optional) Your GitHub Personal Access Token (PAT) with repository access. Required for programmatic mode. If provided, you must also provide `--github-app-installation-id`.
*   `--github-app-installation-id`: (Optional) The installation ID of the Google Cloud Build GitHub App on your repository. Required if using `--github-pat` (programmatic mode).
*   `--local-state`: Use local Terraform state instead of a remote GCS bucket. This is generally *not* recommended for collaborative projects or production environments.
*   `--debug`: Enable debug logging for more verbose output.
*   `--auto-approve`: Skip interactive confirmation prompts (e.g., for using a non-empty repository). Use with caution!

**Project Requirements:**

You need at least *two* Google Cloud projects: one for staging and one for production. The CI/CD project can be the same as either the staging or production project, or a separate third project. A separate development project is optional but recommended for isolating development infrastructure.

**Interactive Mode vs. Programmatic Mode:**

The command operates in two modes:

*   **Interactive Mode (Default):** If you *don't* provide `--github-pat` and `--github-app-installation-id`, the command runs interactively. It will:
    *   Prompt you to choose between creating a new repository or using an existing one.
    *   Prompt for repository details (name, owner) if not provided via flags.
    *   Guide you through authenticating with GitHub via OAuth to create the Cloud Build connection.
    *   Create the GitHub repository if requested.
*   **Programmatic Mode:** If you provide *both* `--github-pat` and `--github-app-installation-id`, the command runs non-interactively using these credentials. This is suitable for automation scripts.
    *   It assumes the GitHub repository and the Cloud Build GitHub App installation already exist.
    *   It will create/update a secret in Google Cloud Secret Manager (`github-pat` in the CICD project) to store the provided PAT.

**Authentication:**

*   **Interactive Mode:** Uses OAuth for the Cloud Build connection to GitHub. You'll be prompted in your browser to authorize the Google Cloud Build application. Requires `gh` CLI authentication.
*   **Programmatic Mode:** Uses the provided GitHub Personal Access Token (PAT) and GitHub App installation ID. The PAT is stored securely in Google Cloud Secret Manager.

**Steps Performed (High-Level):**

1.  **Validation & Setup:**
    *   Validates that the command is run from the project root.
    *   Prompts for Git provider (currently only GitHub).
    *   Handles GitHub authentication (`gh auth login` check).
    *   Ensures required Google Cloud APIs (e.g., `secretmanager.googleapis.com`, `cloudbuild.googleapis.com`, `cloudresourcemanager.googleapis.com`) are enabled in the relevant projects.
2.  **Repository & Connection Setup (Mode Dependent):**
    *   **Interactive:** Prompts for repository details, creates the GitHub repository (if requested), and creates the Cloud Build connection via OAuth flow.
    *   **Programmatic:** Creates/updates the GitHub PAT secret in Secret Manager. Assumes repository and connection pre-exist configuration-wise but Terraform will manage them.
3.  **Terraform Configuration:**
    *   Copies necessary Terraform files (`cloudbuild_cicd.tf`, `github_repo.tf`, etc.) into `deployment/terraform/`.
    *   Sets up the Terraform backend configuration (`backend.tf`) in `deployment/terraform/` and `deployment/terraform/dev/` to use a GCS bucket (unless `--local-state` is used). The bucket name will be `<CICD_PROJECT_ID>-terraform-state`.
    *   Updates `deployment/terraform/vars/env.tfvars` with project IDs, region, repository details (`repository_name`, `repository_owner`), connection details (`host_connection_name`), and authentication/mode flags (`github_pat_secret_id`, `github_app_installation_id`, `connection_exists`, `repository_exists`).
    *   Updates `deployment/terraform/dev/vars/env.tfvars` with the development project ID (if provided).
    *   Updates `deployment/terraform/build_triggers.tf` to correctly reference the Terraform-managed GitHub repository resource.
4.  **Terraform Apply:**
    *   Runs `terraform init` and `terraform apply` for the development environment (`deployment/terraform/dev/`) if `--dev-project` was provided.
    *   Runs `terraform init` and `terraform apply` for the main CI/CD and prod/staging configuration (`deployment/terraform/`). This step creates/manages the GitHub repository (if not existing), Cloud Build connection, triggers, IAM bindings, and potentially other resources defined in the Terraform files.
5.  **Git Setup:**
    *   Initializes a Git repository (`git init -b main`) in the current directory if one doesn't exist.
    *   Adds a Git remote named `origin` pointing to the configured GitHub repository URL if the remote doesn't already exist.

**After Running the Command:**

*   **Commit and Push:** You *must* commit your project files and push them to the `main` branch of your configured GitHub repository to activate the CI/CD pipeline. The command will remind you to do this.
    ```bash
    git add .
    git commit -m "Initial commit of agent starter pack"
    git push -u origin main
    ```
*   **Cloud Build Triggers:** Cloud Build triggers will be active. Pushes to `main` will typically trigger a deployment pipeline, and pull requests against `main` will trigger a PR check pipeline. View them in the Google Cloud Console under Cloud Build > Triggers in your CICD project.
*   **Terraform State:** Your Terraform state, which tracks the infrastructure created, will be stored either locally in `deployment/terraform/terraform.tfstate` and `deployment/terraform/dev/terraform.tfstate` (if `--local-state` was used) or remotely in the GCS bucket named `<YOUR_CICD_PROJECT_ID>-terraform-state`.
*   **Review Resources:** Check your Google Cloud projects (CICD, Dev, Staging, Prod) and your GitHub repository to see the created resources (Cloud Build triggers, connections, secrets, IAM bindings, potentially Cloud Run services, etc.).
*   **Manual Steps:** Remember that this provides a *basic* setup. For production environments, review and enhance security, monitoring, and deployment strategies by consulting the manual setup instructions.

### Manual CI/CD Setup

For fine-grained control, enhanced security, and production-grade deployments, refer to the detailed instructions in `deployment/README.md`. The manual approach allows for:

*   **Enhanced Security:** Configure stricter IAM permissions, network policies, and VPC Service Controls.
*   **Custom Workflows:** Implement complex build, test, approval, and deployment steps tailored to your needs.
*   **Environment-Specific Settings:** Precisely manage configurations (e.g., secrets, resource sizes) for each environment.
*   **Advanced CI/CD:** Integrate with artifact registries, security scanning tools, monitoring systems, and other advanced CI/CD practices.
