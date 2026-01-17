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
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import backoff
import click
from rich.console import Console

from agent_starter_pack.cli.utils.cicd import (
    ProjectConfig,
    create_github_connection,
    handle_github_authentication,
    is_github_authenticated,
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
    console.print("- Create a GitHub repository and connect it to your CI/CD runner")
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


def check_github_scopes(cicd_runner: str) -> None:
    """Check if GitHub CLI has required scopes for the CI/CD runner.

    Args:
        cicd_runner: Either 'github_actions' or 'google_cloud_build'

    Raises:
        click.ClickException: If required scopes are missing
    """
    try:
        # Get scopes from gh auth status
        result = run_command(["gh", "auth", "status"], capture_output=True, check=True)

        # Parse scopes from the output
        scopes = []
        for line in result.stdout.split("\n"):
            if "Token scopes:" in line:
                # Extract scopes from line like "- Token scopes: 'gist', 'read:org', 'repo', 'workflow'"
                scopes_part = line.split("Token scopes:")[1].strip()
                # Remove quotes and split by comma
                scopes = [
                    s.strip().strip("'\"") for s in scopes_part.split(",") if s.strip()
                ]
                break

        # Define required scopes based on CI/CD runner
        if cicd_runner == "github_actions":
            required_scopes = ["repo", "workflow"]
            missing_scopes = [scope for scope in required_scopes if scope not in scopes]

            if missing_scopes:
                console.print(
                    f"❌ Missing required GitHub scopes: {', '.join(missing_scopes)}",
                    style="bold red",
                )
                console.print("To fix this: gh auth login --scopes repo,workflow")
                raise click.ClickException(
                    "GitHub CLI authentication lacks required scopes"
                )

        elif cicd_runner == "google_cloud_build":
            required_scopes = ["repo"]
            missing_scopes = [scope for scope in required_scopes if scope not in scopes]

            if missing_scopes:
                console.print(
                    f"❌ Missing required GitHub scopes: {', '.join(missing_scopes)}",
                    style="bold red",
                )
                console.print("To fix this: gh auth login --scopes repo")
                raise click.ClickException(
                    "GitHub CLI authentication lacks required scopes"
                )

        console.print("✅ GitHub CLI scopes verified")

    except subprocess.CalledProcessError:
        console.print("⚠️ Could not verify GitHub CLI scopes", style="yellow")


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
        str: Repository owner from the config
    """
    console.print("\n🔧 Setting up Git repository...")

    # Initialize git if not already initialized
    if not (Path.cwd() / ".git").exists():
        run_command(["git", "init", "-b", "main"])
        console.print("✅ Git repository initialized")

    # Add remote if it doesn't exist
    remote_url = (
        f"https://github.com/{config.repository_owner}/{config.repository_name}.git"
    )
    try:
        run_command(
            ["git", "remote", "get-url", "origin"], capture_output=True, check=True
        )
        console.print("✅ Git remote already configured")
    except subprocess.CalledProcessError:
        try:
            run_command(
                ["git", "remote", "add", "origin", remote_url],
                capture_output=True,
                check=True,
            )
            console.print(f"✅ Added git remote: {remote_url}")
        except subprocess.CalledProcessError as e:
            console.print(f"❌ Failed to add git remote: {e}", style="bold red")
            raise click.ClickException(f"Failed to add git remote: {e}") from e

    console.print(
        "\n💡 Tip: Don't forget to commit and push your changes to the repository!"
    )
    return config.repository_owner


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
    # Accept either pyproject.toml (Python) or .asp.toml (Go)
    if not Path("pyproject.toml").exists() and not Path(".asp.toml").exists():
        raise click.UsageError(
            "This command must be run from the project root directory containing "
            "pyproject.toml (Python) or .asp.toml (Go). "
            "Make sure you are in the folder created by agent-starter-pack."
        )


def get_project_name_from_config() -> str | None:
    """Get project name from pyproject.toml or .asp.toml.

    Returns:
        Project name if found, None otherwise.
    """
    # Try .asp.toml first (Go projects)
    if Path(".asp.toml").exists():
        try:
            with open(".asp.toml", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("name ="):
                        return line.split("=")[1].strip().strip("\"'")
        except Exception:
            pass

    # Try pyproject.toml (Python projects)
    if Path("pyproject.toml").exists():
        try:
            with open("pyproject.toml", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("name ="):
                        return line.split("=")[1].strip().strip("\"'")
        except Exception:
            pass

    return None


def detect_region_from_terraform_vars() -> str | None:
    """Detect region from Terraform vars file.

    Returns:
        str | None: The detected region, or None if not found or is default
    """
    try:
        tf_vars_path = Path("deployment/terraform/vars/env.tfvars")
        if not tf_vars_path.exists():
            return None

        with open(tf_vars_path, encoding="utf-8") as f:
            content = f.read()

        # Look for region = "value" pattern
        region_match = re.search(r'region\s*=\s*"([^"]+)"', content)
        if region_match:
            detected_region = region_match.group(1)
            # Don't auto-detect if it's the default value
            if detected_region != "us-central1":
                return detected_region

        return None
    except Exception:
        # If any error occurs, return None to use default
        return None


def update_build_triggers(tf_dir: Path) -> None:
    """Update build triggers configuration."""
    build_triggers_path = tf_dir / "build_triggers.tf"
    if build_triggers_path.exists():
        with open(build_triggers_path, encoding="utf-8") as f:
            content = f.read()

        # Add repository dependency to all trigger resources
        modified_content = content.replace(
            "depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]",
            "depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services, google_cloudbuildv2_repository.repo]",
        )

        # Update repository reference in all triggers
        modified_content = modified_content.replace(
            'repository = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"',
            "repository = google_cloudbuildv2_repository.repo.id",
        )

        with open(build_triggers_path, "w", encoding="utf-8") as f:
            f.write(modified_content)

        console.print("✅ Updated build triggers with repository dependency")


def prompt_for_repository_details(
    repository_name: str | None = None,
    repository_owner: str | None = None,
    create_repository: bool = False,
    use_existing_repository: bool = False,
) -> tuple[str, str, bool]:
    """Interactive prompt for repository details with option to use existing repo."""
    # Get current GitHub username as default owner
    result = run_command(["gh", "api", "user", "--jq", ".login"], capture_output=True)
    default_owner = result.stdout.strip()

    # Step 1: Determine create_repository value
    if create_repository and use_existing_repository:
        raise ValueError(
            "Cannot specify both create_repository and use_existing_repository"
        )

    # If neither flag is set, prompt for the choice
    if not create_repository and not use_existing_repository:
        console.print("\n📦 Repository Configuration", style="bold blue")
        console.print("Choose an option:")
        console.print("1. Create new repository")
        console.print("2. Use existing empty repository")

        choice = click.prompt(
            "Select option", type=click.Choice(["1", "2"]), default="1"
        )
        create_repository = choice == "1"
    # If use_existing_repository is True, create_repository should be False
    elif use_existing_repository:
        create_repository = False
    # Otherwise create_repository is already True from the flag

    # Step 2: Get repository name if missing
    if not repository_name:
        # Get project name from config as default
        default_name = get_project_name_from_config() or f"genai-app-{int(time.time())}"

        prompt_text = (
            "Enter new repository name"
            if create_repository
            else "Enter existing repository name"
        )
        repository_name = click.prompt(prompt_text, default=default_name)

    # Step 3: Get repository owner if missing
    if not repository_owner:
        prompt_text = (
            "Enter repository owner"
            if create_repository
            else "Enter existing repository owner"
        )
        repository_owner = click.prompt(prompt_text, default=default_owner)

    if repository_name is None or repository_owner is None:
        raise ValueError("Repository name and owner must be provided")
    return repository_name, repository_owner, create_repository


def setup_terraform_backend(
    tf_dir: Path, project_id: str, region: str, repository_name: str
) -> None:
    """Setup terraform backend configuration with GCS bucket"""
    console.print("\n🔧 Setting up Terraform backend...")

    bucket_name = f"{project_id}-terraform-state"

    # Ensure bucket exists
    try:
        result = run_command(
            ["gcloud", "storage", "buckets", "describe", f"gs://{bucket_name}"],
            check=False,
            capture_output=True,
        )

        if result.returncode != 0:
            console.print(f"\n📦 Creating Terraform state bucket: {bucket_name}")
            # Create bucket
            run_command(
                [
                    "gcloud",
                    "storage",
                    "buckets",
                    "create",
                    f"gs://{bucket_name}",
                    f"--project={project_id}",
                    f"--location={region}",
                ]
            )

            # Enable versioning
            run_command(
                [
                    "gcloud",
                    "storage",
                    "buckets",
                    "update",
                    f"gs://{bucket_name}",
                    "--versioning",
                ]
            )
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
            with open(backend_file, "w", encoding="utf-8") as f:
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
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as temp_file:
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
@click.option(
    "--region", help="GCP region (auto-detects from Terraform vars if not specified)"
)
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
    "--create-repository",
    is_flag=True,
    default=False,
    help="Flag indicating whether to create a new repository",
)
@click.option(
    "--use-existing-repository",
    is_flag=True,
    default=False,
    help="Flag indicating whether to use an existing repository",
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
    region: str | None,
    repository_name: str | None,
    repository_owner: str | None,
    host_connection_name: str | None,
    github_pat: str | None,
    github_app_installation_id: str | None,
    local_state: bool,
    debug: bool,
    auto_approve: bool,
    create_repository: bool,
    use_existing_repository: bool,
) -> None:
    """Set up CI/CD infrastructure using Terraform."""

    # Validate mutually exclusive flags
    if create_repository and use_existing_repository:
        raise click.UsageError(
            "Cannot specify both --create-repository and --use-existing-repository flags"
        )

    # Check if we're in the root folder
    validate_working_directory()

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

    # Auto-detect region if not provided
    if region is None:
        detected_region = detect_region_from_terraform_vars()
        if detected_region:
            region = detected_region
            console.print(f"Auto-detected region from Terraform vars: {region}")
        else:
            region = "us-central1"
            console.print(f"Using default region: {region}")
    else:
        console.print(f"Using provided region: {region}")

    # Auto-detect CI/CD runner based on Terraform files (moved earlier)
    tf_dir = Path("deployment/terraform")
    is_github_actions = (tf_dir / "wif.tf").exists() and (tf_dir / "github.tf").exists()
    cicd_runner = "github_actions" if is_github_actions else "google_cloud_build"

    display_intro_message()

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

    if debug:
        logging.basicConfig(level=logging.DEBUG)
        console.print("> Debug mode enabled")

    # Auto-detect CI/CD runner based on Terraform files
    tf_dir = Path("deployment/terraform")
    is_github_actions = (tf_dir / "wif.tf").exists() and (tf_dir / "github.tf").exists()
    cicd_runner = "github_actions" if is_github_actions else "google_cloud_build"
    if debug:
        logging.debug(f"Detected CI/CD runner: {cicd_runner}")

    # Ensure GitHub CLI is available and authenticated
    if not check_gh_cli_installed():
        prompt_gh_cli_installation()
    if not is_github_authenticated():
        console.print("\n⚠️ Not authenticated with GitHub CLI", style="yellow")
        handle_github_authentication()
    else:
        console.print("✅ GitHub CLI authentication verified")

    # Check if GitHub CLI has required scopes for the CI/CD runner
    console.print("\n🔍 Checking GitHub CLI scopes...")
    check_github_scopes(cicd_runner)

    # Gather repository details
    if auto_approve:
        # Auto-generate repository details when auto-approve is used
        if not repository_owner:
            repository_owner = run_command(
                ["gh", "api", "user", "--jq", ".login"], capture_output=True
            ).stdout.strip()
        if not repository_name:
            # Get project name from config or generate one
            repository_name = (
                get_project_name_from_config() or f"genai-app-{int(time.time())}"
            )
        console.print(
            f"✅ Auto-generated repository: {repository_owner}/{repository_name}"
        )
        # Keep the CLI argument value for create_repository
    else:
        # Use prompt_for_repository_details to fill in any missing information
        repository_name, repository_owner, create_repository = (
            prompt_for_repository_details(
                repository_name,
                repository_owner,
                create_repository,
                use_existing_repository,
            )
        )

    assert repository_name is not None, "Repository name must be provided"
    assert repository_owner is not None, "Repository owner must be provided"

    # Set default host connection name if not provided
    if not host_connection_name:
        host_connection_name = f"git-{repository_name}"

    # For Cloud Build, determine mode and handle connection creation
    oauth_token_secret_id = None
    # Track original repository state for Terraform (before we create it)
    terraform_create_repository = create_repository

    if cicd_runner == "google_cloud_build":
        # Determine if we're in programmatic or interactive mode based on provided credentials
        detected_mode = (
            "programmatic"
            if github_pat and github_app_installation_id
            else "interactive"
        )

        if detected_mode == "interactive":
            console.print(
                "\n🔗 Interactive mode: Creating GitHub connection using gcloud CLI..."
            )

            # Create connection using gcloud CLI (interactive approach)
            try:
                oauth_token_secret_id, github_app_installation_id = (
                    create_github_connection(
                        project_id=cicd_project,
                        region=region,
                        connection_name=host_connection_name,
                    )
                )
                create_cb_connection = (
                    True  # Connection created by gcloud, Terraform will reference it
                )
                console.print("✅ GitHub connection created successfully")
            except Exception as e:
                console.print(
                    f"❌ Failed to create GitHub connection: {e}", style="red"
                )
                raise

        elif detected_mode == "programmatic":
            console.print(
                "\n🔐 Programmatic mode: Creating GitHub PAT secret using gcloud CLI..."
            )

            oauth_token_secret_id = "github-pat"  # Use fixed secret ID like main branch

            if github_pat is None:
                raise ValueError("GitHub PAT is required for programmatic mode")

            # Create GitHub PAT secret using gcloud CLI instead of Terraform
            console.print("📝 Creating GitHub PAT secret using gcloud CLI...")
            create_or_update_secret(oauth_token_secret_id, github_pat, cicd_project)
            create_cb_connection = False  # Terraform will not create connection, will reference existing secret
            console.print("✅ GitHub PAT secret created using gcloud CLI")

    # For GitHub Actions, no connection management needed
    if cicd_runner == "github_actions":
        create_cb_connection = False

    console.print("\n📦 Starting CI/CD Infrastructure Setup", style="bold blue")
    console.print("=====================================")

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

    # Prepare Terraform variables
    env_vars_path = tf_dir / "vars" / "env.tfvars"
    terraform_vars = {
        "staging_project_id": staging_project,
        "prod_project_id": prod_project,
        "cicd_runner_project_id": cicd_project,
        "region": region,
        "repository_name": repository_name,
        "repository_owner": repository_owner
        or run_command(
            ["gh", "api", "user", "--jq", ".login"], capture_output=True
        ).stdout.strip(),
    }

    # Add CI/CD runner specific variables
    if cicd_runner == "google_cloud_build":
        terraform_vars.update(
            {
                "host_connection_name": host_connection_name,
                "create_cb_connection": str(create_cb_connection).lower(),
                "create_repository": str(
                    terraform_create_repository
                ).lower(),  # Use original state
                "github_app_installation_id": github_app_installation_id,
                "github_pat_secret_id": oauth_token_secret_id,
            }
        )
    else:  # github_actions
        terraform_vars["create_repository"] = str(
            terraform_create_repository
        ).lower()  # Use original state

    # Write Terraform variables
    with open(env_vars_path, "w", encoding="utf-8") as f:
        for var_name, var_value in terraform_vars.items():
            if var_value in ("true", "false"):  # Boolean values
                f.write(f"{var_name} = {var_value}\n")
            elif var_value is not None:  # String values
                f.write(f'{var_name} = "{var_value}"\n')

    console.print("✅ Updated env.tfvars with variables")

    # Update dev environment vars if dev project provided
    if dev_project:
        dev_tf_vars_path = tf_dir / "dev" / "vars" / "env.tfvars"
        if dev_tf_vars_path.exists():
            with open(dev_tf_vars_path, "w", encoding="utf-8") as f:
                f.write(f'dev_project_id = "{dev_project}"\n')
            console.print("✅ Updated dev env.tfvars")

    # Apply dev Terraform if dev project is provided
    if dev_project:
        dev_tf_dir = tf_dir / "dev"
        if dev_tf_dir.exists():
            console.print("\n🏗️ Applying dev Terraform configuration...")
            if local_state:
                run_command(["terraform", "init", "-backend=false"], cwd=dev_tf_dir)
            else:
                run_command(["terraform", "init"], cwd=dev_tf_dir)
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
            console.print("✅ Dev environment deployed")
        else:
            console.print("ℹ️ No dev Terraform directory found")

    # Apply prod Terraform
    console.print("\n🚀 Applying prod Terraform configuration...")
    if local_state:
        run_command(["terraform", "init", "-backend=false"], cwd=tf_dir)
    else:
        run_command(["terraform", "init"], cwd=tf_dir)

    # Prepare environment variables for Terraform
    terraform_env_vars = {}
    if (
        cicd_runner == "google_cloud_build"
        and detected_mode == "programmatic"
        and github_pat
    ):
        terraform_env_vars["GITHUB_TOKEN"] = (
            github_pat  # For GitHub provider authentication
        )

    run_command(
        ["terraform", "apply", "-auto-approve", "--var-file", "vars/env.tfvars"],
        cwd=tf_dir,
        env_vars=terraform_env_vars if terraform_env_vars else None,
    )
    console.print("✅ Prod/Staging infrastructure deployed")

    config = ProjectConfig(
        staging_project_id=staging_project,
        prod_project_id=prod_project,
        cicd_project_id=cicd_project,
        agent="",  # Not used in git setup
        deployment_target="",  # Not used in git setup
        region=region,
        repository_name=repository_name,
        repository_owner=repository_owner,
    )

    setup_git_repository(config)

    console.print("\n✅ CI/CD infrastructure setup complete!")

    # Print useful information
    repo_url = f"https://github.com/{repository_owner}/{repository_name}"

    console.print("\n📋 Summary:")
    console.print(f"• Repository: {repo_url}")
    console.print(f"• CI/CD Runner: {cicd_runner.replace('_', ' ').title()}")

    if cicd_runner == "google_cloud_build":
        console.print(
            f"• Cloud Build: https://console.cloud.google.com/cloud-build/builds?project={cicd_project}"
        )
    else:
        console.print(f"• GitHub Actions: {repo_url}/actions")

    if not local_state:
        console.print(f"• Terraform State: gs://{cicd_project}-terraform-state")
    else:
        console.print("• Terraform State: Local")

    console.print("\n💡 Next steps:")
    console.print("1. Commit and push your code to the repository")
    console.print("2. Your CI/CD pipeline will automatically trigger on pushes")
