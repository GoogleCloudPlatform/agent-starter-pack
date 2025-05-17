# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import backoff
import click
from rich.console import Console

from src.cli.utils.cicd import (
    E2EDeployment,
    ProjectConfig,
    create_github_connection,
    create_github_repository,
    ensure_apis_enabled,
    handle_github_authentication,
    is_github_authenticated,
    print_cicd_summary,
    run_command,
)

console = Console()


def display_intro_message() -> None:
    """Display introduction and warning messages about the setup-cicd command."""
    console.print(
        "\n⚠️  WARNING: The setup-cicd command is experimental and may have unexpected behavior.",
        style="bold yellow",
    )
    console.print("Please report any issues you encounter.\n")

    console.print("\n📋 About this command:", style="bold blue")
    console.print(
        "This command helps set up a basic CI/CD pipeline for development and testing purposes."
    )
    console.print("It will:")
    console.print("- Create a GitHub repository and connect it to Cloud Build")
    console.print("- Set up development environment infrastructure")
    console.print("- Configure basic CI/CD triggers for PR checks and deployments")
    console.print(
        "- Configure remote Terraform state in GCS (use --local-state to use local state instead)"
    )


def display_production_note() -> None:
    """Display important note about production setup."""
    console.print("\n⚡ Setup Note:", style="bold yellow")
    console.print("For maximum flexibility, we recommend following")
    console.print("the manual setup instructions in deployment/README.md")
    console.print("This will give you more control over:")
    console.print("- Security configurations")
    console.print("- Custom deployment workflows")
    console.print("- Environment-specific settings")
    console.print("- Advanced CI/CD pipeline customization\n")


def check_gh_cli_installed() -> bool:
    """Check if GitHub CLI is installed.

    Returns:
        bool: True if GitHub CLI is installed, False otherwise
    """
    try:
        run_command(["gh", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def prompt_gh_cli_installation() -> None:
    """Display instructions for installing GitHub CLI and exit."""
    console.print("\n❌ GitHub CLI not found", style="bold red")
    console.print("This command requires the GitHub CLI (gh) to be installed.")
    console.print("\nPlease install GitHub CLI from: https://cli.github.com/")
    console.print("\nAfter installation, run this command again.")
    sys.exit(1)


def setup_git_repository(config: ProjectConfig) -> str:
    """Set up Git repository and remote.

    Args:
        config: Project configuration containing repository details

    Returns:
        str: GitHub username of the authenticated user
    """
    console.print("\n🔧 Setting up Git repository...")

    # Initialize git if not already initialized
    if not (Path.cwd() / ".git").exists():
        run_command(["git", "init", "-b", "main"])
        console.print("✅ Git repository initialized")

    # Get current GitHub username for the remote URL
    result = run_command(["gh", "api", "user", "--jq", ".login"], capture_output=True)
    github_username = result.stdout.strip()

    # Add remote if it doesn't exist
    try:
        run_command(
            ["git", "remote", "get-url", "origin"], capture_output=True, check=True
        )
        console.print("✅ Git remote already configured")
    except subprocess.CalledProcessError:
        remote_url = (
            f"https://github.com/{github_username}/{config.repository_name}.git"
        )
        run_command(["git", "remote", "add", "origin", remote_url])
        console.print(f"✅ Added git remote: {remote_url}")

    console.print(
        "\n💡 Tip: Don't forget to commit and push your changes to the repository!"
    )
    return github_username


def prompt_for_git_provider() -> str:
    """Interactively prompt user for git provider selection."""
    providers = ["github"]  # Currently only GitHub is supported
    console.print("\n🔄 Git Provider Selection", style="bold blue")
    for i, provider in enumerate(providers, 1):
        console.print(f"{i}. {provider}")

    while True:
        choice = click.prompt(
            "\nSelect git provider",
            type=click.Choice(["1"]),  # Only allow '1' since GitHub is the only option
            default="1",
        )
        return providers[int(choice) - 1]


def validate_working_directory() -> None:
    """Ensure we're in the project root directory."""
    if not Path("pyproject.toml").exists():
        raise click.UsageError(
            "This command must be run from the project root directory containing pyproject.toml. "
            "Make sure you are in the folder created by agent-starter-pack."
        )


def update_build_triggers(tf_dir: Path) -> None:
    """Update build triggers configuration."""
    build_triggers_path = tf_dir / "build_triggers.tf"
    if build_triggers_path.exists():
        with open(build_triggers_path) as f:
            content = f.read()

        # Add repository dependency to all trigger resources
        modified_content = content.replace(
            "depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]",
            "depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services, google_cloudbuildv2_repository.repo]",
        )

        # Update repository reference in all triggers
        modified_content = modified_content.replace(
            'repository = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"',
            "repository = google_cloudbuildv2_repository.repo.id",
        )

        with open(build_triggers_path, "w") as f:
            f.write(modified_content)

        console.print("✅ Updated build triggers with repository dependency")


def prompt_for_repository_details(
    repository_name: str | None = None, repository_owner: str | None = None
) -> tuple[str, str, bool]:
    """Interactive prompt for repository details with option to use existing repo."""
    # Get current GitHub username as default owner
    result = run_command(["gh", "api", "user", "--jq", ".login"], capture_output=True)
    default_owner = result.stdout.strip()
    repository_exists = False

    if not (repository_name and repository_owner):
        console.print("\n📦 Repository Configuration", style="bold blue")
        console.print("Choose an option:")
        console.print("1. Create new repository")
        console.print("2. Use existing empty repository")

        choice = click.prompt(
            "Select option", type=click.Choice(["1", "2"]), default="1"
        )
        if choice == "1":
            # New repository
            if not repository_name:
                # Get project name from pyproject.toml
                with open("pyproject.toml") as f:
                    for line in f:
                        if line.strip().startswith("name ="):
                            default_name = line.split("=")[1].strip().strip("\"'")
                            break
                    else:
                        default_name = f"genai-app-{int(time.time())}"
                repository_name = click.prompt(
                    "Enter new repository name", default=default_name
                )
            if not repository_owner:
                repository_owner = click.prompt(
                    "Enter repository owner", default=default_owner
                )
        else:
            # Existing repository
            repository_exists = True
            while True:
                repo_url = click.prompt(
                    "Enter existing repository URL (e.g., https://github.com/owner/repo)"
                )
                # Extract owner and repo name from URL
                match = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
                if match:
                    repository_owner = match.group(1)
                    # Remove .git suffix if present
                    repository_name = match.group(2).rstrip(".git")
                    break
                else:
                    console.print(
                        "❌ Invalid repository URL format. Please use https://github.com/owner/repo",
                        style="bold red",
                    )

    if repository_name is None or repository_owner is None:
        raise ValueError("Repository name and owner must be provided")
    return repository_name, repository_owner, repository_exists


def setup_terraform_backend(
    tf_dir: Path, project_id: str, region: str, repository_name: str
) -> None:
    """Setup terraform backend configuration with GCS bucket"""
    console.print("\n🔧 Setting up Terraform backend...")

    bucket_name = f"{project_id}-terraform-state"

    # Ensure bucket exists
    try:
        result = run_command(
            ["gsutil", "ls", "-b", f"gs://{bucket_name}"],
            check=False,
            capture_output=True,
        )

        if result.returncode != 0:
            console.print(f"\n📦 Creating Terraform state bucket: {bucket_name}")
            # Create bucket
            run_command(
                ["gsutil", "mb", "-p", project_id, "-l", region, f"gs://{bucket_name}"]
            )

            # Enable versioning
            run_command(["gsutil", "versioning", "set", "on", f"gs://{bucket_name}"])
    except subprocess.CalledProcessError as e:
        console.print(f"\n❌ Failed to setup state bucket: {e}")
        raise

    # Create backend.tf in both root and dev directories
    tf_dirs = [
        tf_dir,  # Root terraform directory
        tf_dir / "dev",  # Dev terraform directory
    ]

    for dir_path in tf_dirs:
        if dir_path.exists():
            # Use different state prefixes for dev and prod
            is_dev_dir = str(dir_path).endswith("/dev")
            state_prefix = f"{repository_name}/{(is_dev_dir and 'dev') or 'prod'}"

            backend_file = dir_path / "backend.tf"
            backend_content = f'''terraform {{
  backend "gcs" {{
    bucket = "{bucket_name}"
    prefix = "{state_prefix}"
  }}
}}
'''
            with open(backend_file, "w") as f:
                f.write(backend_content)

            console.print(
                f"✅ Terraform backend configured in {dir_path} to use bucket: {bucket_name} with prefix: {state_prefix}"
            )


def create_or_update_secret(secret_id: str, secret_value: str, project_id: str) -> None:
    """Create or update a secret in Google Cloud Secret Manager.

    Args:
        secret_id: The ID of the secret to create/update
        secret_value: The value to store in the secret
        project_id: The Google Cloud project ID

    Raises:
        subprocess.CalledProcessError: If secret creation/update fails
    """
    with tempfile.NamedTemporaryFile(mode="w") as temp_file:
        temp_file.write(secret_value)
        temp_file.flush()

        # First try to add a new version to existing secret
        try:
            run_command(
                [
                    "gcloud",
                    "secrets",
                    "versions",
                    "add",
                    secret_id,
                    "--data-file",
                    temp_file.name,
                    f"--project={project_id}",
                ]
            )
            console.print("✅ Updated existing GitHub PAT secret")
        except subprocess.CalledProcessError:
            # If adding version fails (secret doesn't exist), try to create it
            try:
                run_command(
                    [
                        "gcloud",
                        "secrets",
                        "create",
                        secret_id,
                        "--data-file",
                        temp_file.name,
                        f"--project={project_id}",
                        "--replication-policy",
                        "automatic",
                    ]
                )
                console.print("✅ Created new GitHub PAT secret")
            except subprocess.CalledProcessError as e:
                console.print(
                    f"❌ Failed to create/update GitHub PAT secret: {e!s}",
                    style="bold red",
                )
                raise


console = Console()


@click.command()
@click.option("--dev-project", help="Development project ID")
@click.option("--staging-project", help="Staging project ID")
@click.option("--prod-project", help="Production project ID")
@click.option(
    "--cicd-project", help="CICD project ID (defaults to prod project if not specified)"
)
@click.option("--region", default="us-central1", help="GCP region")
@click.option("--repository-name", help="Repository name (optional)")
@click.option(
    "--repository-owner",
    help="Repository owner (optional, defaults to current GitHub user)",
)
@click.option("--host-connection-name", help="Host connection name (optional)")
@click.option("--github-pat", help="GitHub Personal Access Token for programmatic auth")
@click.option(
    "--github-app-installation-id",
    help="GitHub App Installation ID for programmatic auth",
)
@click.option(
    "--git-provider",
    type=click.Choice(["github"]),
    help="Git provider to use (currently only GitHub is supported)",
)
@click.option(
    "--local-state",
    is_flag=True,
    default=False,
    help="Use local Terraform state instead of remote GCS backend (defaults to remote)",
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--auto-approve",
    is_flag=True,
    help="Skip confirmation prompts and proceed automatically",
)
@click.option(
    "--repository-exists",
    is_flag=True,
    default=False,
    help="Flag indicating if the repository already exists",
)
@backoff.on_exception(
    backoff.expo,
    (subprocess.CalledProcessError, click.ClickException),
    max_tries=3,
    jitter=backoff.full_jitter,
)
def setup_cicd(
    dev_project: str | None,
    staging_project: str | None,
    prod_project: str | None,
    cicd_project: str | None,
    region: str,
    repository_name: str | None,
    repository_owner: str | None,
    host_connection_name: str | None,
    github_pat: str | None,
    github_app_installation_id: str | None,
    git_provider: str | None,
    local_state: bool,
    debug: bool,
    auto_approve: bool,
    repository_exists: bool,
) -> None:
    """Set up CI/CD infrastructure using Terraform."""

    # Check if we're in the root folder by looking for pyproject.toml
    if not Path("pyproject.toml").exists():
        raise click.UsageError(
            "This command must be run from the project root directory containing pyproject.toml. "
            "Make sure you are in the folder created by agent-starter-pack."
        )

    # Prompt for staging and prod projects if not provided
    if staging_project is None:
        staging_project = click.prompt(
            "Enter your staging project ID (where tests will be run)", type=str
        )

    if prod_project is None:
        prod_project = click.prompt("Enter your production project ID", type=str)

    # If cicd_project is not provided, default to prod_project
    if cicd_project is None:
        cicd_project = prod_project
        console.print(f"Using production project '{prod_project}' for CI/CD resources")

    console.print(
        "\n⚠️  WARNING: The setup-cicd command is experimental and may have unexpected behavior.",
        style="bold yellow",
    )
    console.print("Please report any issues you encounter.\n")

    console.print("\n📋 About this command:", style="bold blue")
    console.print(
        "This command helps set up a basic CI/CD pipeline for development and testing purposes."
    )
    console.print("It will:")
    console.print("- Create a GitHub repository and connect it to Cloud Build")
    console.print("- Set up development environment infrastructure")
    console.print("- Configure basic CI/CD triggers for PR checks and deployments")
    console.print(
        "- Configure remote Terraform state in GCS (use --local-state to use local state instead)"
    )

    console.print("\n⚡ Production Setup Note:", style="bold yellow")
    console.print(
        "For production deployments and maximum flexibility, we recommend following"
    )
    console.print("the manual setup instructions in deployment/README.md")
    console.print("This will give you more control over:")
    console.print("- Security configurations")
    console.print("- Custom deployment workflows")
    console.print("- Environment-specific settings")
    console.print("- Advanced CI/CD pipeline customization\n")

    # Add the confirmation prompt
    if not auto_approve:
        if not click.confirm("\nDo you want to continue with the setup?", default=True):
            console.print("\n🛑 Setup cancelled by user", style="bold yellow")
            return

    console.print(
        "This command helps set up a basic CI/CD pipeline for development and testing purposes."
    )
    console.print("It will:")
    console.print("- Create a GitHub repository and connect it to Cloud Build")
    console.print("- Set up development environment infrastructure")
    console.print("- Configure basic CI/CD triggers for PR checks and deployments")
    console.print(
        "- Configure remote Terraform state in GCS (use --local-state to use local state instead)"
    )

    console.print("\n⚡ Production Setup Note:", style="bold yellow")
    console.print(
        "For production deployments and maximum flexibility, we recommend following"
    )
    console.print("the manual setup instructions in deployment/README.md")
    console.print("This will give you more control over:")
    console.print("- Security configurations")
    console.print("- Custom deployment workflows")
    console.print("- Environment-specific settings")
    console.print("- Advanced CI/CD pipeline customization\n")

    if debug:
        logging.basicConfig(level=logging.DEBUG)
        console.print("> Debug mode enabled")

    # Set git provider through prompt if not provided
    if not git_provider:
        git_provider = prompt_for_git_provider()

    # Check GitHub authentication if GitHub is selected
    if git_provider == "github" and not (github_pat and github_app_installation_id):
        # Check if GitHub CLI is installed
        if git_provider == "github" or git_provider is None:
            if not check_gh_cli_installed():
                prompt_gh_cli_installation()
        if not is_github_authenticated():
            console.print("\n⚠️ Not authenticated with GitHub CLI", style="yellow")
            handle_github_authentication()
        else:
            console.print("✅ GitHub CLI authentication verified")

    # Only prompt for repository details if not provided via CLI
    if not (repository_name and repository_owner):
        repository_name, repository_owner, repository_exists = (
            prompt_for_repository_details(repository_name, repository_owner)
        )
    # Set default host connection name if not provided
    if not host_connection_name:
        host_connection_name = f"git-{repository_name}"
    # Check and enable required APIs regardless of auth method
    required_apis = ["secretmanager.googleapis.com", "cloudbuild.googleapis.com"]
    ensure_apis_enabled(cicd_project, required_apis)

    # Create GitHub connection and repository if not using PAT authentication
    oauth_token_secret_id = None

    # Determine if we're in programmatic or interactive mode based on provided credentials
    detected_mode = (
        "programmatic" if github_pat and github_app_installation_id else "interactive"
    )

    if git_provider == "github" and detected_mode == "interactive":
        # First create the repository since we're in interactive mode
        if not repository_exists:
            create_github_repository(repository_owner, repository_name)

        # Then create the connection
        oauth_token_secret_id, github_app_installation_id = create_github_connection(
            project_id=cicd_project, region=region, connection_name=host_connection_name
        )
        repository_exists = True
    elif git_provider == "github" and detected_mode == "programmatic":
        oauth_token_secret_id = "github-pat"

        if github_pat is None:
            raise ValueError("GitHub PAT is required for programmatic mode")

        # Create the GitHub PAT secret if provided
        console.print("\n🔐 Creating/updating GitHub PAT secret...")
        create_or_update_secret(
            secret_id=oauth_token_secret_id,
            secret_value=github_pat,
            project_id=cicd_project,
        )

    else:
        # Unsupported git provider
        console.print("⚠️  Only GitHub is currently supported.", style="bold yellow")
        raise ValueError("Unsupported git provider")

    console.print("\n📦 Starting CI/CD Infrastructure Setup", style="bold blue")
    console.print("=====================================")

    config = ProjectConfig(
        dev_project_id=dev_project,
        staging_project_id=staging_project,
        prod_project_id=prod_project,
        cicd_project_id=cicd_project,
        region=region,
        repository_name=repository_name,
        repository_owner=repository_owner,
        host_connection_name=host_connection_name,
        agent="",  # Not needed for CICD setup
        deployment_target="",  # Not needed for CICD setup
        github_pat=github_pat,
        github_app_installation_id=github_app_installation_id,
        git_provider=git_provider,
        repository_exists=repository_exists,
    )

    tf_dir = Path("deployment/terraform")

    # Copy CICD terraform files
    cicd_utils_path = Path(__file__).parent.parent.parent / "resources" / "setup_cicd"

    for tf_file in cicd_utils_path.glob("*.tf"):
        shutil.copy2(tf_file, tf_dir)
    console.print("✅ Copied CICD terraform files")

    # Setup Terraform backend if not using local state
    if not local_state:
        console.print("\n🔧 Setting up remote Terraform backend...")
        setup_terraform_backend(
            tf_dir=tf_dir,
            project_id=cicd_project,
            region=region,
            repository_name=repository_name,
        )
        console.print("✅ Remote Terraform backend configured")
    else:
        console.print("\n📝 Using local Terraform state (remote backend disabled)")

    # Update terraform variables using existing function
    deployment = E2EDeployment(config)
    deployment.update_terraform_vars(
        Path.cwd(), is_dev=False
    )  # is_dev=False for prod/staging setup

    # Update env.tfvars with additional variables
    env_vars_path = tf_dir / "vars" / "env.tfvars"

    # Read existing content
    existing_content = ""
    if env_vars_path.exists():
        with open(env_vars_path) as f:
            existing_content = f.read()

    # Prepare new variables
    new_vars = {}
    if not config.repository_owner:
        result = run_command(
            ["gh", "api", "user", "--jq", ".login"], capture_output=True
        )
        new_vars["repository_owner"] = result.stdout.strip()
    else:
        new_vars["repository_owner"] = config.repository_owner

    # Use the app installation ID from the connection if available, otherwise use the provided one
    new_vars["github_app_installation_id"] = github_app_installation_id
    # Use the OAuth token secret ID if available, otherwise use default PAT secret ID
    new_vars["github_pat_secret_id"] = oauth_token_secret_id
    # Set connection_exists based on whether we created a new connection
    new_vars["connection_exists"] = (
        "true" if detected_mode == "interactive" else "false"
    )
    new_vars["repository_exists"] = "true" if config.repository_exists else "false"

    # Update or append variables
    with open(env_vars_path, "w") as f:
        # Write existing content excluding lines with variables we're updating
        for line in existing_content.splitlines():
            if not any(line.startswith(f"{var} = ") for var in new_vars.keys()):
                f.write(line + "\n")

        # Write new/updated variables
        for var_name, var_value in new_vars.items():
            if var_value in ("true", "false"):  # For boolean values
                f.write(f"{var_name} = {var_value}\n")
            else:  # For string values
                f.write(f'{var_name} = "{var_value}"\n')

    console.print("✅ Updated env.tfvars with additional variables")

    # Update dev environment vars
    dev_tf_vars_path = tf_dir / "dev" / "vars" / "env.tfvars"
    if (
        dev_tf_vars_path.exists() and dev_project
    ):  # Only update if dev_project is provided
        with open(dev_tf_vars_path) as f:
            dev_content = f.read()

        # Update dev project ID
        dev_content = re.sub(
            r'dev_project_id\s*=\s*"[^"]*"',
            f'dev_project_id = "{dev_project}"',
            dev_content,
        )

        with open(dev_tf_vars_path, "w") as f:
            f.write(dev_content)

        console.print("✅ Updated dev env.tfvars with project configuration")

    # Update build triggers configuration
    update_build_triggers(tf_dir)

    # First initialize and apply dev terraform
    dev_tf_dir = tf_dir / "dev"
    if dev_tf_dir.exists() and dev_project:  # Only deploy if dev_project is provided
        with console.status("[bold blue]Setting up dev environment..."):
            if local_state:
                run_command(["terraform", "init", "-backend=false"], cwd=dev_tf_dir)
            else:
                run_command(["terraform", "init"], cwd=dev_tf_dir)

            try:
                run_command(
                    [
                        "terraform",
                        "apply",
                        "-auto-approve",
                        "--var-file",
                        "vars/env.tfvars",
                    ],
                    cwd=dev_tf_dir,
                )
            except subprocess.CalledProcessError as e:
                if "Error acquiring the state lock" in str(e):
                    console.print(
                        "[yellow]State lock error detected, retrying without lock...[/yellow]"
                    )
                    run_command(
                        [
                            "terraform",
                            "apply",
                            "-auto-approve",
                            "--var-file",
                            "vars/env.tfvars",
                            "-lock=false",
                        ],
                        cwd=dev_tf_dir,
                    )
                else:
                    raise

            console.print("✅ Dev environment Terraform configuration applied")
    elif dev_tf_dir.exists():
        console.print("ℹ️ Skipping dev environment setup (no dev project provided)")

    # Then apply prod terraform to create GitHub repo
    with console.status(
        "[bold blue]Setting up Prod/Staging Terraform configuration..."
    ):
        if local_state:
            run_command(["terraform", "init", "-backend=false"], cwd=tf_dir)
        else:
            run_command(["terraform", "init"], cwd=tf_dir)

        try:
            run_command(
                [
                    "terraform",
                    "apply",
                    "-auto-approve",
                    "--var-file",
                    "vars/env.tfvars",
                ],
                cwd=tf_dir,
            )
        except subprocess.CalledProcessError as e:
            if "Error acquiring the state lock" in str(e):
                console.print(
                    "[yellow]State lock error detected, retrying without lock...[/yellow]"
                )
                run_command(
                    [
                        "terraform",
                        "apply",
                        "-auto-approve",
                        "--var-file",
                        "vars/env.tfvars",
                        "-lock=false",
                    ],
                    cwd=tf_dir,
                )
            else:
                raise

        console.print("✅ Prod/Staging Terraform configuration applied")

    # Now we can set up git since the repo exists
    if git_provider == "github":
        console.print("\n🔧 Setting up Git repository...")

        # Initialize git if not already initialized
        if not (Path.cwd() / ".git").exists():
            run_command(["git", "init", "-b", "main"])
            console.print("✅ Git repository initialized")

        # Get current GitHub username for the remote URL
        result = run_command(
            ["gh", "api", "user", "--jq", ".login"], capture_output=True
        )
        github_username = result.stdout.strip()

        # Add remote if it doesn't exist
        try:
            run_command(
                ["git", "remote", "get-url", "origin"], capture_output=True, check=True
            )
            console.print("✅ Git remote already configured")
        except subprocess.CalledProcessError:
            remote_url = (
                f"https://github.com/{github_username}/{config.repository_name}.git"
            )
            run_command(["git", "remote", "add", "origin", remote_url])
            console.print(f"✅ Added git remote: {remote_url}")

        console.print(
            "\n💡 Tip: Don't forget to commit and push your changes to the repository!"
        )

    console.print("\n✅ CICD infrastructure setup complete!")
    if not local_state:
        console.print(
            f"📦 Using remote Terraform state in bucket: {cicd_project}-terraform-state"
        )
    else:
        console.print("📝 Using local Terraform state")

    try:
        # Print success message with useful links
        result = run_command(
            ["gh", "api", "user", "--jq", ".login"], capture_output=True
        )
        github_username = result.stdout.strip()

        repo_url = f"https://github.com/{github_username}/{config.repository_name}"
        cloud_build_url = f"https://console.cloud.google.com/cloud-build/builds?project={config.cicd_project_id}"
        # Sleep to allow resources to propagate
        console.print("\n⏳ Waiting for resources to propagate...")
        time.sleep(10)

        # Print final summary
        print_cicd_summary(config, github_username, repo_url, cloud_build_url)

    except Exception as e:
        if debug:
            logging.exception("An error occurred:")
        console.print(f"\n❌ Error: {e!s}", style="bold red")
        sys.exit(1)
