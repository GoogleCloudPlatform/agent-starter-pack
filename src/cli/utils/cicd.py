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

"""Utilities for CI/CD setup and management."""

import json
import re
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import backoff
import click
from rich.console import Console
from rich.prompt import IntPrompt, Prompt

console = Console()


def setup_git_provider(non_interactive: bool = False) -> str:
    """Interactive selection of git provider."""
    if non_interactive:
        return "github"  # Default to GitHub in non-interactive mode

    console.print("\n> Git Provider Configuration", style="bold blue")
    providers = [
        ("github", "GitHub"),
        # Add more providers here in the future
        # ("gitlab", "GitLab (Coming soon)"),
        # ("bitbucket", "Bitbucket (Coming soon)"),
    ]

    console.print("Available Git providers:")
    for i, (id, name) in enumerate(providers, 1):
        if id == "github":
            console.print(f"{i}. {name}")
        else:
            console.print(f"{i}. {name}", style="dim")

    choice = IntPrompt.ask("Select your Git provider", default=1)

    git_provider = providers[choice - 1][0]
    if git_provider != "github":
        console.print("⚠️  Only GitHub is currently supported.", style="bold yellow")
        raise ValueError("Unsupported git provider")

    return git_provider


def setup_repository_name(
    default_prefix: str = "genai-app", non_interactive: bool = False
) -> tuple[str, str]:
    """Interactive setup of repository name and owner."""
    if non_interactive:
        timestamp = int(time.time())
        # Return empty string instead of None to match return type
        return f"{default_prefix}-{timestamp}", ""

    console.print("\n> Repository Configuration", style="bold blue")

    # Get current GitHub username
    result = run_command(["gh", "api", "user", "--jq", ".login"], capture_output=True)
    github_username = result.stdout.strip()

    # Get repository name
    repo_name = Prompt.ask(
        "Enter repository name", default=f"{default_prefix}-{int(time.time())}"
    )

    # Get repository owner (default to current user)
    repo_owner = Prompt.ask(
        "Enter repository owner (organization or username)", default=github_username
    )

    return repo_name, repo_owner


def create_github_connection(
    project_id: str, region: str, connection_name: str
) -> tuple[str, str]:
    """Create and verify GitHub connection using gcloud command.

    Args:
        project_id: GCP project ID
        region: GCP region
        connection_name: Name for the GitHub connection

    Returns:
        tuple[str, str]: The OAuth token secret ID and the app installation ID
    """
    console.print("\n🔗 Creating GitHub connection...")

    def try_create_connection() -> subprocess.CompletedProcess[str]:
        cmd = [
            "gcloud",
            "builds",
            "connections",
            "create",
            "github",
            connection_name,
            f"--region={region}",
            f"--project={project_id}",
        ]

        # Display the command being run
        console.print(f"\n🔄 Running command: {' '.join(cmd)}")

        # Use Popen to get control over stdin
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Send 'y' followed by enter key to handle both the API enablement prompt and any other prompts
        stdout, stderr = process.communicate(input="y\n")

        # Create a CompletedProcess-like object for compatibility
        return subprocess.CompletedProcess(
            args=cmd, returncode=process.returncode, stdout=stdout, stderr=stderr
        )

    # Try initial connection creation
    result = try_create_connection()

    if result.returncode == 0:
        console.print("✅ GitHub connection created successfully")
    else:
        stderr = str(result.stderr)
        console.print(stderr)

        if "ALREADY_EXISTS" in stderr:
            console.print("✅ Using existing GitHub connection")
        else:
            console.print(
                f"❌ Failed to create GitHub connection: {stderr}", style="bold red"
            )
            raise subprocess.CalledProcessError(
                result.returncode, result.args, result.stdout, stderr
            )

    console.print("\n⚠️ Important:", style="bold yellow")
    console.print(
        "1. Please visit the URL below to authorize Cloud Build (if not already authorized)"
    )
    console.print("2. After authorization, the setup will continue automatically")
    console.print("\nChecking connection status...")

    # Poll for connection readiness
    max_retries = 30  # 5 minutes total with 10s sleep
    for attempt in range(max_retries):
        try:
            result = run_command(
                [
                    "gcloud",
                    "builds",
                    "connections",
                    "describe",
                    connection_name,
                    f"--region={region}",
                    f"--project={project_id}",
                    "--format=json",
                ],
                capture_output=True,
            )

            status = json.loads(result.stdout).get("installationState", {}).get("stage")

            if status == "COMPLETE":
                console.print("✅ GitHub connection is authorized and ready")

                # Get the secret version and app installation ID
                connection_data = json.loads(result.stdout)
                github_config = connection_data.get("githubConfig", {})

                oauth_token_secret_version = github_config.get(
                    "authorizerCredential", {}
                ).get("oauthTokenSecretVersion")
                app_installation_id = github_config.get("appInstallationId")

                if not oauth_token_secret_version or not app_installation_id:
                    raise ValueError(
                        "Could not find OAuth token secret version or app installation ID in connection details"
                    )

                # Extract just the secret ID from the full path
                # Format: "projects/PROJECT_ID/secrets/SECRET_ID/versions/VERSION"
                secret_id = oauth_token_secret_version.split("/secrets/")[1].split(
                    "/versions/"
                )[0]

                console.print(f"✅ Retrieved OAuth token secret ID: {secret_id}")
                console.print(
                    f"✅ Retrieved app installation ID: {app_installation_id}"
                )

                return secret_id, app_installation_id
            elif status == "PENDING_USER_OAUTH" or status == "PENDING_INSTALL_APP":
                if attempt < max_retries - 1:  # Don't print waiting on last attempt
                    console.print("⏳ Waiting for GitHub authorization...")
                    # Extract and print the action URI for user authentication
                    try:
                        action_uri = (
                            json.loads(result.stdout)
                            .get("installationState", {})
                            .get("actionUri")
                        )
                        if action_uri:
                            console.print(
                                "\n🔑 Authentication Required:", style="bold yellow"
                            )
                            console.print(
                                f"Please visit [link={action_uri}]this page[/link] to authenticate Cloud Build with GitHub:"
                            )
                            console.print(f"{action_uri}", style="bold blue")
                            console.print(
                                "(Copy and paste the link into your browser if clicking doesn't work)"
                            )
                            console.print(
                                "After completing authentication, return here to continue the setup.\n"
                            )
                    except (json.JSONDecodeError, KeyError) as e:
                        console.print(
                            f"⚠️ Could not extract authentication link: {e}",
                            style="yellow",
                        )
                    time.sleep(10)
                continue
            else:
                raise Exception(f"Unexpected connection status: {status}")

        except subprocess.CalledProcessError as e:
            console.print(
                f"❌ Failed to check connection status: {e}", style="bold red"
            )
            raise

    raise TimeoutError("GitHub connection authorization timed out after 5 minutes")


@dataclass
class ProjectConfig:
    staging_project_id: str
    prod_project_id: str
    cicd_project_id: str
    agent: str
    deployment_target: str
    region: str = "us-central1"
    dev_project_id: str | None = None
    project_name: str | None = None
    repository_name: str | None = None
    repository_owner: str | None = None
    repository_exists: bool | None = None
    host_connection_name: str | None = None
    github_pat: str | None = None
    github_app_installation_id: str | None = None
    git_provider: str = "github"


def print_cicd_summary(
    config: ProjectConfig, github_username: str, repo_url: str, cloud_build_url: str
) -> None:
    """Print a summary of the CI/CD setup."""
    console.print("\n🎉 CI/CD Infrastructure Setup Complete!", style="bold green")
    console.print("====================================")
    console.print("\n📊 Resource Summary:")
    console.print(f"   • Development Project: {config.dev_project_id}")
    console.print(f"   • Staging Project: {config.staging_project_id}")
    console.print(f"   • Production Project: {config.prod_project_id}")
    console.print(f"   • CICD Project: {config.cicd_project_id}")
    console.print(f"   • Repository: {config.repository_name}")
    console.print(f"   • Region: {config.region}")

    console.print("\n🔗 Important Links:")
    console.print(f"   • GitHub Repository: {repo_url}")
    console.print(f"   • Cloud Build Console: {cloud_build_url}")

    console.print("\n📝 Next Steps:", style="bold blue")
    console.print("1. Push your code to the repository")
    console.print("2. Create and merge a pull request to trigger CI/CD pipelines")
    console.print("3. Monitor builds in the Cloud Build console")
    console.print(
        "4. After successful staging deployment, approve production deployment in Cloud Build"
    )
    console.print(
        "\n🌟 Enjoy building your new Agent! Happy coding! 🚀", style="bold green"
    )


def ensure_apis_enabled(project_id: str, apis: list[str]) -> None:
    """Check and enable required APIs and set up necessary permissions.

    Args:
        project_id: GCP project ID where APIs should be enabled
        apis: List of API service names to check and enable
    """
    console.print("\n🔍 Checking required APIs...")
    for api in apis:
        try:
            # Check if API is enabled
            result = run_command(
                [
                    "gcloud",
                    "services",
                    "list",
                    f"--project={project_id}",
                    f"--filter=config.name:{api}",
                    "--format=json",
                ],
                capture_output=True,
            )

            services = json.loads(result.stdout)
            if not services:  # API not enabled
                console.print(f"📡 Enabling {api}...")
                run_command(
                    ["gcloud", "services", "enable", api, f"--project={project_id}"]
                )
                console.print(f"✅ Enabled {api}")
            else:
                console.print(f"✅ {api} already enabled")
        except subprocess.CalledProcessError as e:
            console.print(f"❌ Failed to check/enable {api}: {e!s}", style="bold red")
            raise

    # Get the Cloud Build service account
    console.print("\n🔑 Setting up service account permissions...")
    try:
        result = run_command(
            ["gcloud", "projects", "get-iam-policy", project_id, "--format=json"],
            capture_output=True,
        )

        project_number = run_command(
            [
                "gcloud",
                "projects",
                "describe",
                project_id,
                "--format=value(projectNumber)",
            ],
            capture_output=True,
        ).stdout.strip()

        cloudbuild_sa = (
            f"service-{project_number}@gcp-sa-cloudbuild.iam.gserviceaccount.com"
        )

        # Grant Secret Manager Admin role to Cloud Build service account
        console.print(f"📦 Granting Secret Manager Admin role to {cloudbuild_sa}...")
        run_command(
            [
                "gcloud",
                "projects",
                "add-iam-policy-binding",
                project_id,
                f"--member=serviceAccount:{cloudbuild_sa}",
                "--role=roles/secretmanager.admin",
                "--condition=None",
            ]
        )
        console.print("✅ Permissions granted to Cloud Build service account")

    except subprocess.CalledProcessError as e:
        console.print(
            f"❌ Failed to set up service account permissions: {e!s}", style="bold red"
        )
        raise

    # Add a small delay to allow API enablement and IAM changes to propagate
    time.sleep(10)


@backoff.on_exception(
    backoff.expo,
    subprocess.CalledProcessError,
    max_tries=3,
    max_time=60,
    on_backoff=lambda details: console.print(
        f"⚠️ Command failed, retrying in {details['wait']:.1f}s (attempt {details['tries']})"
    ),
)
def run_command(
    cmd: list[str] | str,
    check: bool = True,
    cwd: Path | None = None,
    capture_output: bool = False,
    shell: bool = False,
    input: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a command and display it to the user"""
    # Format command for display
    cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
    print(f"\n🔄 Running command: {cmd_str}")
    if cwd:
        print(f"📂 In directory: {cwd}")

    # Run the command
    result = subprocess.run(
        cmd,
        check=check,
        cwd=cwd,
        capture_output=capture_output,
        text=True,
        shell=shell,
        input=input,
    )

    # Display output if captured
    if capture_output and result.stdout:
        print(f"📤 Output:\n{result.stdout.strip()}")
    if capture_output and result.stderr:
        print(f"⚠️ Error output:\n{result.stderr}")

    return result


def is_github_authenticated() -> bool:
    """Check if the user is authenticated with GitHub CLI.

    Returns:
        bool: True if authenticated, False otherwise
    """
    try:
        # Try to get the current user, which will fail if not authenticated
        result = run_command(["gh", "auth", "status"], check=False, capture_output=True)
        return result.returncode == 0
    except Exception:
        return False


def handle_github_authentication() -> None:
    """Handle GitHub CLI authentication interactively."""
    console.print("\n🔑 GitHub Authentication Required", style="bold yellow")
    console.print("You need to authenticate with GitHub CLI to continue.")
    console.print("Choose an authentication method:")
    console.print("1. Login with browser")
    console.print("2. Login with token")

    choice = click.prompt(
        "Select authentication method", type=click.Choice(["1", "2"]), default="1"
    )

    try:
        if choice == "1":
            # Browser-based authentication
            run_command(["gh", "auth", "login", "--web"])
        else:
            # Token-based authentication
            token = click.prompt(
                "Enter your GitHub Personal Access Token", hide_input=True
            )
            # Use a subprocess with pipe to avoid showing the token in process list
            process = subprocess.Popen(
                ["gh", "auth", "login", "--with-token"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=token + "\n")

            if process.returncode != 0:
                console.print(f"❌ Authentication failed: {stderr}", style="bold red")
                raise subprocess.CalledProcessError(
                    process.returncode, ["gh", "auth", "login"], stdout, stderr
                )

        console.print("✅ Successfully authenticated with GitHub", style="green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Authentication failed: {e}", style="bold red")
        raise click.Abort() from e


def create_github_repository(repository_owner: str, repository_name: str) -> None:
    """Create GitHub repository if it doesn't exist.

    Args:
        repository_owner: Owner of the repository
        repository_name: Name of the repository to create
    """
    try:
        # Check if repo exists
        result = run_command(
            [
                "gh",
                "repo",
                "view",
                f"{repository_owner}/{repository_name}",
                "--json",
                "name",
            ],
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            # Repository doesn't exist, create it
            console.print(
                f"\n📦 Creating GitHub repository: {repository_owner}/{repository_name}"
            )
            run_command(
                [
                    "gh",
                    "repo",
                    "create",
                    f"{repository_owner}/{repository_name}",
                    "--private",
                    "--description",
                    "Repository with goo.gle/agent-starter-pack",
                ]
            )
            console.print("✅ GitHub repository created")
        else:
            console.print("✅ Using existing GitHub repository")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to create/check repository: {e!s}", style="bold red")
        raise


class Environment(Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"
    CICD = "cicd"


class E2EDeployment:
    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        self.projects: dict[Environment, Path] = {}

        # Generate project name if not provided
        if not self.config.project_name:
            # Create a meaningful default project name based on agent and deployment target
            prefix = f"{self.config.agent}-{self.config.deployment_target}"
            # Clean up prefix to be filesystem compatible
            prefix = re.sub(r"[^a-zA-Z0-9-]", "-", prefix.lower())
            timestamp = int(time.time())
            self.config.project_name = f"{prefix}-{timestamp}"

    def update_terraform_vars(self, project_dir: Path, is_dev: bool = False) -> None:
        """Update terraform variables with project configuration"""
        if is_dev:
            # Dev environment only needs one project ID
            tf_vars_path = (
                project_dir / "deployment" / "terraform" / "dev" / "vars" / "env.tfvars"
            )

            with open(tf_vars_path) as f:
                content = f.read()

            # Replace dev project ID
            content = re.sub(
                r'dev_project_id\s*=\s*"[^"]*"',
                f'dev_project_id = "{self.config.dev_project_id}"',
                content,
            )
        else:
            # Path to production needs staging, prod, and CICD project IDs
            tf_vars_path = (
                project_dir / "deployment" / "terraform" / "vars" / "env.tfvars"
            )

            with open(tf_vars_path) as f:
                content = f.read()

            # Replace all project IDs
            content = re.sub(
                r'staging_project_id\s*=\s*"[^"]*"',
                f'staging_project_id = "{self.config.staging_project_id}"',
                content,
            )
            content = re.sub(
                r'prod_project_id\s*=\s*"[^"]*"',
                f'prod_project_id = "{self.config.prod_project_id}"',
                content,
            )
            content = re.sub(
                r'cicd_runner_project_id\s*=\s*"[^"]*"',
                f'cicd_runner_project_id = "{self.config.cicd_project_id}"',
                content,
            )

            # Add host connection and repository name
            content = re.sub(
                r'host_connection_name\s*=\s*"[^"]*"',
                f'host_connection_name = "{self.config.host_connection_name}"',
                content,
            )
            content = re.sub(
                r'repository_name\s*=\s*"[^"]*"',
                f'repository_name = "{self.config.repository_name}"',
                content,
            )

        # Write updated content
        with open(tf_vars_path, "w") as f:
            f.write(content)

    def setup_terraform_state(self, project_dir: Path, env: Environment) -> None:
        """Setup terraform state configuration for dev or prod environment"""
        # Determine terraform directories - we need both for full setup
        tf_dirs = []
        if env == Environment.DEV:
            tf_dirs = [project_dir / "deployment" / "terraform" / "dev"]
        else:
            # For prod/staging, set up both root and dev terraform
            tf_dirs = [
                project_dir / "deployment" / "terraform",
                project_dir / "deployment" / "terraform" / "dev",
            ]

        bucket_name = f"{self.config.cicd_project_id}-terraform-state"

        # Ensure bucket exists and is accessible
        try:
            result = run_command(
                ["gsutil", "ls", "-b", f"gs://{bucket_name}"],
                check=False,
                capture_output=True,
            )

            if result.returncode != 0:
                print(f"\n📦 Creating Terraform state bucket: {bucket_name}")
                run_command(
                    [
                        "gsutil",
                        "mb",
                        "-p",
                        self.config.cicd_project_id,
                        "-l",
                        self.config.region,
                        f"gs://{bucket_name}",
                    ]
                )

                run_command(
                    ["gsutil", "versioning", "set", "on", f"gs://{bucket_name}"]
                )
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Failed to setup state bucket: {e}")
            raise

        # Create backend.tf in each required directory
        for tf_dir in tf_dirs:
            # Use different state prefixes for dev and prod/staging to keep states separate
            is_dev_dir = str(tf_dir).endswith("/dev")
            state_prefix = "dev" if is_dev_dir else "prod"

            backend_file = tf_dir / "backend.tf"
            with open(backend_file, "w") as f:
                f.write(f'''terraform {{
  backend "gcs" {{
    bucket = "{bucket_name}"
    prefix = "{state_prefix}"
  }}
}}
''')
            print(
                f"\n✅ Terraform state configured in {tf_dir} to use bucket: {bucket_name} with prefix: {state_prefix}"
            )

    def setup_terraform(
        self, project_dir: Path, env: Environment, local_state: bool = False
    ) -> None:
        """Initialize and apply Terraform for the given environment"""
        print(f"\n🏗️ Setting up Terraform for {env.value} environment")

        # Setup state configuration for all required directories if using remote state
        if not local_state:
            self.setup_terraform_state(project_dir, env)

        # Determine which directories to process and their corresponding var files
        tf_configs = []
        if env == Environment.DEV:
            tf_configs = [
                (project_dir / "deployment" / "terraform" / "dev", "vars/env.tfvars")
            ]
        else:
            # For prod/staging, we need both directories but with their own var files
            tf_configs = [
                (
                    project_dir / "deployment" / "terraform",
                    "vars/env.tfvars",
                ),  # Prod vars
                (
                    project_dir / "deployment" / "terraform" / "dev",
                    "vars/env.tfvars",
                ),  # Dev vars
            ]

        # Initialize and apply Terraform for each directory
        for tf_dir, var_file in tf_configs:
            print(f"\n🔧 Initializing Terraform in {tf_dir}...")
            if local_state:
                run_command(["terraform", "init", "-backend=false"], cwd=tf_dir)
            else:
                run_command(["terraform", "init"], cwd=tf_dir)

            print(f"\n🚀 Applying Terraform configuration in {tf_dir}...")
            run_command(
                ["terraform", "apply", f"-var-file={var_file}", "-auto-approve"],
                cwd=tf_dir,
            )
