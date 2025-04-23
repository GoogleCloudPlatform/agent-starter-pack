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
# mypy: disable-error-code="return-value"

"""
End-to-end deployment tests for CICD pipelines.

These tests should be run manually as the time to test all patterns would be above an hour.
They cover the full deployment lifecycle, including:
- Project creation using the CLI
- CICD setup using the CLI
- Triggering deployments via Git
- Verification of deployed services

The tests are parameterized using a test matrix defined in `CICD_TEST_MATRIX`.
Each entry in the matrix represents a combination of:
- Agent type
- Deployment target

The tests require the following environment variables to be set:
- GITHUB_PAT: GitHub Personal Access Token with repo and workflow scopes
- GITHUB_APP_INSTALLATION_ID: GitHub App Installation ID

Note:
    The tests create and manage Google Cloud projects and repositories.
    Ensure you have sufficient permissions and quota before running these tests.
    The tests also clean up any existing test repositories before starting.
"""

import hashlib
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import backoff
import pytest
import vertexai
from vertexai import agent_engines

DEFAULT_REGION = "europe-west1"


@dataclass
class CICDTestConfig:
    """Configuration for CICD test cases"""

    agent: str
    deployment_target: str
    extra_params: str


def get_test_matrix() -> list[CICDTestConfig]:
    """
    Get the test matrix to run, either from environment or predefined combinations.

    If _TEST_AGENT_COMBINATION environment variable is set with format "agent,deployment_target[,extra_params]",
    returns a matrix with just that combination. Otherwise returns the full test matrix.
    """
    if os.environ.get("_TEST_AGENT_COMBINATION"):
        env_combo_parts = os.environ.get("_TEST_AGENT_COMBINATION", "").split(",")
        if len(env_combo_parts) >= 2:
            extra_params = ""
            if len(env_combo_parts) > 2:
                extra_params = ",".join(env_combo_parts[2:])

            env_combo = CICDTestConfig(
                agent=env_combo_parts[0],
                deployment_target=env_combo_parts[1],
                extra_params=extra_params,
            )
            logging.info(f"Running test for combination from environment: {env_combo}")
            return [env_combo]
        else:
            logging.warning(
                f"Invalid environment combination format: {env_combo_parts}"
            )

    # Define default test matrix with different agent and deployment target combinations
    return [
        # CICDTestConfig(
        #     agent="langgraph_base_react",
        #     deployment_target="agent_engine",
        # ),
        # CICDTestConfig(
        #     agent="langgraph_base_react",
        #     deployment_target="cloud_run",
        # ),
        # CICDTestConfig(
        #     agent="crewai_coding_crew",
        #     deployment_target="cloud_run",
        # ),
        # CICDTestConfig(
        #     agent="crewai_coding_crew",
        #     deployment_target="agent_engine",
        # ),
        CICDTestConfig(
            agent="agentic_rag",
            deployment_target="agent_engine",
            extra_params="--include-data-ingestion,--datastore,vertex_ai_vector_search",
        ),
        # CICDTestConfig(
        #     agent="agentic_rag",
        #     deployment_target="cloud_run",
        # ),
        # CICDTestConfig(
        #     agent="live_api",
        #     deployment_target="cloud_run",
        # ),
    ]


# Get the test matrix based on environment or defaults
CICD_TEST_MATRIX: list[CICDTestConfig] = get_test_matrix()


@backoff.on_exception(backoff.expo, subprocess.CalledProcessError, max_tries=2)
def run_command(
    cmd: list[str],
    check: bool = True,
    cwd: Path | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess:
    """Run a command and display it to the user with enhanced error handling and real-time streaming"""
    # Format command for display
    cmd_str = " ".join(cmd)

    # Mask sensitive information in the displayed command
    display_cmd = cmd_str
    if "GITHUB_PAT" in display_cmd or "--github-pat" in display_cmd:
        # Find the position of the token in the command
        for i, arg in enumerate(cmd):
            if arg == "--github-pat" and i + 1 < len(cmd):
                cmd_str = cmd_str.replace(cmd[i + 1], "[REDACTED]")
            elif "GITHUB_PAT" in arg:
                cmd_str = cmd_str.replace(arg, "[REDACTED]")

    logger.info(f"\n🔄 Running command: {cmd_str}")
    if cwd:
        logger.info(f"📂 In directory: {cwd}")

    try:
        if capture_output:
            # Use subprocess.run with capture_output when specifically requested
            result = subprocess.run(
                cmd,
                check=False,  # Don't check yet, we'll handle errors below
                cwd=cwd,
                capture_output=True,
                text=True,
            )
        else:
            # Stream output in real-time
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=None,  # Use None to inherit parent's stdout/stderr
                stderr=None,
                text=True,
                bufsize=1,
            )

            # Wait for process to complete
            returncode = process.wait()

            # Create a CompletedProcess object to match subprocess.run interface
            result = subprocess.CompletedProcess(
                args=cmd,
                returncode=returncode,
                stdout="",  # We don't capture output in streaming mode
                stderr="",
            )

            # Handle non-zero return code
            if check and returncode != 0:
                raise subprocess.CalledProcessError(returncode, cmd)

        return result

    except subprocess.CalledProcessError as e:
        # Enhanced error reporting for CalledProcessError
        error_msg = (
            f"\n❌ Command failed with exit code {e.returncode}\nCommand: {cmd_str}"
        )
        logger.error(error_msg)
        raise

    except Exception as e:
        # General error handling
        error_msg = (
            f"\n❌ Unexpected error running command\nCommand: {cmd_str}\nError: {e!s}"
        )
        logger.error(error_msg)
        raise


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    not os.environ.get("RUN_E2E_TESTS"),
    reason="E2E tests are skipped by default. Set RUN_E2E_TESTS=1 to run.",
)
class TestE2EDeployment:
    """Test class for E2E deployment using the refactored E2EDeployment class"""

    def get_existing_projects(self) -> tuple[str, str, str, str] | None:
        """Get existing projects from environment variables if they exist"""
        env_vars = {
            "dev": "E2E_DEV_PROJECT",
            "staging": "E2E_STAGING_PROJECT",
            "prod": "E2E_PROD_PROJECT",
            "cicd": "E2E_CICD_PROJECT",
        }

        projects = {}
        for env, var_name in env_vars.items():
            projects[env] = os.environ.get(var_name)

        # Return None if any project is missing
        if not all(projects.values()):
            return None

        logger.info("\n📁 Using existing projects from environment variables:")
        for env, project_id in projects.items():
            logger.info(f"✓ {env.upper()}: {project_id}")

        return (
            projects["dev"],
            projects["staging"],
            projects["prod"],
            projects["cicd"],
        )

    def setup_projects(self, config: CICDTestConfig) -> tuple[str, str, str, str]:
        """Get projects from environment variables"""
        existing_projects = self.get_existing_projects()
        if not existing_projects:
            raise ValueError(
                "Required environment variables not set. Please set:\n"
                "- E2E_DEV_PROJECT\n"
                "- E2E_STAGING_PROJECT\n"
                "- E2E_PROD_PROJECT\n"
                "- E2E_CICD_PROJECT"
            )
        return existing_projects

    def monitor_build_logs(
        self, build_id: str, project_id: str, region: str, environment: str
    ) -> None:
        """Monitor Cloud Build logs and check final status.

        Args:
            build_id: The Cloud Build ID to monitor
            project_id: GCP project ID
            region: GCP region
            environment: Deployment environment name

        Raises:
            Exception: If the build fails
        """
        # Stream logs
        run_command(
            [
                "gcloud",
                "beta",
                "builds",
                "log",
                build_id,
                f"--project={project_id}",
                f"--region={region}",
                "--stream",
            ]
        )

        # Check final status
        build_result = run_command(
            [
                "gcloud",
                "builds",
                "describe",
                build_id,
                f"--project={project_id}",
                f"--region={region}",
                "--format=json",
            ],
            capture_output=True,
        )

        build_info = json.loads(build_result.stdout)
        if build_info.get("status") == "FAILURE":
            failure_info = build_info.get("failureInfo", {})
            failure_detail = failure_info.get("detail", "Unknown failure")
            raise Exception(f"Build {build_id} failed: {failure_detail}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=5)
    def monitor_deployment(
        self,
        project_id: str,
        region: str,
        environment: str,
        max_wait_minutes: int = 1,
        repo_owner: str | None = None,
        repo_name: str | None = None,
    ) -> None:
        """Monitor deployment for either staging or production, handling both running and pending states"""
        logger.info(f"\n🔍 Monitoring {environment} deployment...")

        start_time = time.time()
        build_found = False

        while (time.time() - start_time) < (max_wait_minutes * 60):
            # Check for both WORKING and PENDING builds with source filter if available
            filter_cmd = "status=WORKING OR status=PENDING"

            result = run_command(
                [
                    "gcloud",
                    "builds",
                    "list",
                    f"--project={project_id}",
                    f"--region={region}",
                    "--filter",
                    filter_cmd,
                    "--format=json",
                ],
                capture_output=True,
                check=True,
            )

            builds = json.loads(result.stdout)
            logger.debug(f"Found builds: {json.dumps(builds, indent=2)}")

            active_builds = False
            pending_builds = []
            working_builds = []

            # First sort builds into pending and working
            for build in builds:
                if "id" not in build:
                    continue
                # Filter builds by repository if repo information is provided
                if repo_owner and repo_name:
                    # Check if this build is from our target repository
                    source = build.get("source", {})
                    git_source = source.get("gitSource", {})
                    repo_url = git_source.get("url", "")

                    # Skip builds not from our target repository
                    if f"github.com/{repo_owner}/{repo_name}" not in repo_url:
                        logger.debug(
                            f"Skipping build from different repository: {repo_url}"
                        )
                        continue

                active_builds = True
                build_found = True
                build_id = build["name"]
                build_status = build.get("status")
                trigger_id = build.get("buildTriggerId", "")

                # Log more details about the build
                logger.info(
                    f"\n🔎 Found build: ID={build_id}, Status={build_status}, Trigger={trigger_id}"
                )

                if build_status == "PENDING":
                    pending_builds.append(build)
                else:  # WORKING
                    working_builds.append(build)

            # First process any working builds
            for build in working_builds:
                build_id = build["name"]
                logger.info(
                    f"\n🔎 Found active {environment} deployment build: {build_id}"
                )

                # Stream the build logs until completion
                logger.info(f"⏳ Monitoring {environment} deployment...")
                self.monitor_build_logs(build_id, project_id, region, environment)
                logger.info(f"✅ {environment} deployment completed")

                if environment == "production":
                    return

            # Then process pending builds
            for build in pending_builds:
                build_id = build["name"]
                logger.info(
                    f"\n🔎 Found pending {environment} deployment build: {build_id}"
                )
                # Approve if it's a production deployment
                if environment.lower() == "production":
                    logger.info("🔑 Approving deployment...")
                    run_command(
                        [
                            "gcloud",
                            "alpha",
                            "builds",
                            "approve",
                            build_id,
                            f"--project={project_id}",
                            f'--comment="Automated approval for {environment} deployment from E2E test"',
                            f"--location={region}",
                        ]
                    )
                    logger.info(f"✅ Approved build {build_id}")

                    # Monitor the approved build
                    logger.info(f"⏳ Monitoring approved {environment} deployment...")
                    # self.monitor_build_logs(build_id, project_id, region, environment)
                    logger.info(f"✅ {environment} deployment completed")

            if not active_builds:
                logger.info("⏳ No relevant builds found, waiting...")
                time.sleep(30)  # Wait 30 seconds before checking again

        # If we've waited the maximum time and never found a build, raise an error
        if not build_found:
            raise Exception(
                f"No {environment} deployment builds found after waiting {max_wait_minutes} minutes"
            )

    def cleanup_resources(
        self,
        new_project_dir: Path,
        project_name: str,
        cicd_project: str,
        region: str,
        deployment_target: str = "cloud_run",
    ) -> None:
        """Clean up all resources created during the test"""
        logger.info("\n🧹 Cleaning up resources...")

        try:
            # 1. Try to manually delete Cloud Run service or Agent Engine service based on deployment target
            for env_project in [
                os.environ.get("E2E_DEV_PROJECT"),
                os.environ.get("E2E_STAGING_PROJECT"),
                os.environ.get("E2E_PROD_PROJECT"),
            ]:
                if not env_project:
                    continue

                if deployment_target == "cloud_run":
                    logger.info(
                        f"Checking for Cloud Run service {project_name} in project {env_project}..."
                    )
                    try:
                        # Delete the service with the project name directly
                        logger.info(f"Deleting Cloud Run service: {project_name}")
                        run_command(
                            [
                                "gcloud",
                                "run",
                                "services",
                                "delete",
                                project_name,
                                f"--project={env_project}",
                                f"--region={region}",
                                "--quiet",
                            ],
                            check=False,
                        )
                    except Exception as e:
                        logger.error(
                            f"Error cleaning up Cloud Run service {project_name}: {e}"
                        )
                elif deployment_target == "agent_engine":
                    logger.info(
                        f"Checking for Agent Engine service {project_name} in project {env_project}..."
                    )
                    try:
                        # Initialize Vertex AI
                        vertexai.init(project=env_project, location=region)

                        # List all reasoning engines with the given display name
                        logger.info(
                            f"Listing Agent Engine services with name: {project_name}"
                        )
                        engines = agent_engines.AgentEngine.list(
                            filter=f"display_name={project_name}"
                        )

                        # Delete each matching engine
                        for engine in engines:
                            logger.info(
                                f"Deleting Agent Engine: {engine.resource_name}"
                            )
                            engine.delete()
                            logger.info(
                                f"Successfully deleted Agent Engine: {engine.resource_name}"
                            )

                    except Exception as e:
                        logger.error(
                            f"Error cleaning up Agent Engine service {project_name}: {e}"
                        )

            # 2. Try to manually delete specific BigQuery datasets (feedback and telemetry)
            for env_project in [
                os.environ.get("E2E_DEV_PROJECT"),
                os.environ.get("E2E_STAGING_PROJECT"),
                os.environ.get("E2E_PROD_PROJECT"),
            ]:
                if not env_project:
                    continue

                logger.info(
                    f"Cleaning up specific BigQuery datasets in project {env_project}..."
                )
                try:
                    # Define the specific datasets to delete
                    project_name_underscore = project_name.replace("-", "_").lower()
                    datasets_to_delete = [
                        f"{project_name_underscore}_feedback",
                        f"{project_name_underscore}_telemetry",
                    ]

                    for dataset_name in datasets_to_delete:
                        logger.info(f"Deleting BigQuery dataset: {dataset_name}")
                        # Force delete with the -f flag
                        run_command(
                            [
                                "bq",
                                "rm",
                                "-f",
                                "-r",
                                f"--project_id={env_project}",
                                dataset_name,
                            ],
                            check=False,
                        )
                except Exception as e:
                    logger.error(f"Error cleaning up BigQuery datasets: {e}")
            # 3. Try to manually delete Cloud Build repositories and connection
            logger.info(
                f"Cleaning up Cloud Build repositories and connection in project {cicd_project}..."
            )
            try:
                connection_name = f"git-{project_name}"

                # List all repositories for the connection
                logger.info(f"Listing repositories for connection: {connection_name}")
                repos_result = run_command(
                    [
                        "gcloud",
                        "builds",
                        "repositories",
                        "list",
                        f"--connection={connection_name}",
                        f"--project={cicd_project}",
                        f"--region={region}",
                        "--format=json",
                    ],
                    capture_output=True,
                    check=False,
                )

                # Delete each repository
                if repos_result.returncode == 0 and repos_result.stdout:
                    try:
                        repos = json.loads(repos_result.stdout)
                        for repo in repos:
                            repo_name = repo.get("name", "").split("/")[-1]
                            if repo_name:
                                logger.info(f"Deleting repository: {repo_name}")
                                run_command(
                                    [
                                        "gcloud",
                                        "builds",
                                        "repositories",
                                        "delete",
                                        repo_name,
                                        f"--connection={connection_name}",
                                        f"--project={cicd_project}",
                                        f"--region={region}",
                                        "--quiet",
                                    ],
                                    check=False,
                                )
                    except json.JSONDecodeError:
                        logger.error("Failed to parse repositories JSON output")

                # Delete the connection after repositories are deleted
                logger.info(f"Deleting Cloud Build connection: {connection_name}")
                run_command(
                    [
                        "gcloud",
                        "builds",
                        "connections",
                        "delete",
                        connection_name,
                        f"--project={cicd_project}",
                        f"--region={region}",
                        "--quiet",
                    ],
                    check=False,
                )
            except Exception as e:
                logger.error(
                    f"Error cleaning up Cloud Build repositories and connection: {e}"
                )
            # 4. Delete GitHub repository
            logger.info(f"Deleting GitHub repository: {project_name}")
            try:
                run_command(
                    ["gh", "repo", "delete", project_name, "--yes"], check=False
                )
            except Exception as e:
                logger.error(f"Error deleting GitHub repository: {e}")

            # 5. Finally, destroy terraform resources in dev environment
            logger.info("Destroying dev terraform resources...")
            dev_tf_dir = new_project_dir / "deployment" / "terraform" / "dev"
            if dev_tf_dir.exists():
                try:
                    run_command(
                        [
                            "terraform",
                            "destroy",
                            "-auto-approve",
                            "-var-file=vars/env.tfvars",
                        ],
                        cwd=dev_tf_dir,
                        check=False,  # Don't fail if destroy fails
                    )
                except Exception as e:
                    logger.error(f"Error destroying dev terraform resources: {e}")

            # 6. Then destroy terraform resources in prod/staging environment
            logger.info("Destroying prod/staging terraform resources...")
            prod_tf_dir = new_project_dir / "deployment" / "terraform"
            if prod_tf_dir.exists():
                try:
                    run_command(
                        [
                            "terraform",
                            "destroy",
                            "-auto-approve",
                            "-var-file=vars/env.tfvars",
                        ],
                        cwd=prod_tf_dir,
                        check=False,  # Don't fail if destroy fails
                    )
                except Exception as e:
                    logger.error(
                        f"Error destroying prod/staging terraform resources: {e}"
                    )

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Don't re-raise, as we want to continue with other cleanup steps

    def get_project_root(self) -> Path:
        """Get the project root directory"""
        return Path.cwd()

    def update_datastore_name(self, project_root: Path, project_name: str) -> None:
        """Update datastore name in dev and prod/staging env.tfvars"""
        # Update dev env.tfvars
        dev_vars_path = (
            project_root / "deployment" / "terraform" / "dev" / "vars" / "env.tfvars"
        )
        if dev_vars_path.exists():
            # Read current content
            with open(dev_vars_path) as f:
                content = f.read()

            # Replace sample-datastore with project name
            modified_content = content.replace("sample-datastore", project_name)
            modified_content = modified_content.replace(
                "sample-search-engine", project_name
            )

            # Write back modified content
            with open(dev_vars_path, "w") as f:
                f.write(modified_content)

            logger.info("✅ Updated datastore name in dev env.tfvars")

        # Update prod/staging env.tfvars
        prod_vars_path = (
            project_root / "deployment" / "terraform" / "vars" / "env.tfvars"
        )
        if prod_vars_path.exists():
            # Read current content
            with open(prod_vars_path) as f:
                content = f.read()

            # Replace sample-datastore with project name
            modified_content = content.replace("sample-datastore", project_name)
            modified_content = modified_content.replace(
                "sample-search-engine", project_name
            )

            # Write back modified content
            with open(prod_vars_path, "w") as f:
                f.write(modified_content)

            logger.info("✅ Updated datastore name in prod/staging env.tfvars")

    @pytest.mark.flaky(reruns=2)
    @pytest.mark.parametrize(
        "config",
        get_test_matrix(),
    )
    def test_deployment_pipeline(
        self, config: CICDTestConfig, request: pytest.FixtureRequest
    ) -> None:
        """Test full deployment pipeline using CLI and CICD setup"""
        if (
            request.session.testsfailed
            and request.node.get_closest_marker("flaky") is None
        ):
            pytest.skip("Skipping test: Previous test failed in the session")

        # Set region based on agent type
        region = "us-central1" if config.agent == "live_api" else DEFAULT_REGION
        github_pat = os.environ.get("GITHUB_PAT")
        github_app_installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID")

        if not github_pat or not github_app_installation_id:
            pytest.skip(
                "Skipping test: GITHUB_PAT and GITHUB_APP_INSTALLATION_ID environment variables are required"
            )

        agent_hash = hashlib.sha1(config.agent.encode("utf-8")).hexdigest()[:8]
        unique_id = f"{agent_hash}-{int(time.time())}"
        logger.info(
            f"\n🚀 Starting E2E deployment test for {config.agent} + {config.deployment_target} with ID: {unique_id}"
        )

        # Initialize project variables
        dev_project = None
        staging_project = None
        prod_project = None
        cicd_project = None

        try:
            # Get or create projects
            dev_project, staging_project, prod_project, cicd_project = (
                self.setup_projects(config)
            )

            # Get project root directory
            project_root = self.get_project_root()

            # Create project using CLI with project root as working directory
            logger.info("\n🏗️ Creating project using CLI...")
            project_name = f"test-{unique_id}"
            new_project_dir = project_root / "target" / project_name
            # Create base command
            cmd = [
                "python",
                "-m",
                "src.cli.main",
                "create",
                project_name,
                "--agent",
                config.agent,
                "--deployment-target",
                config.deployment_target,
                "--output-dir",
                "target",
                "--auto-approve",
                "--region",
                region,
                "--skip-checks",
            ]

            # Add any extra parameters if they exist
            if hasattr(config, "extra_params") and config.extra_params:
                extra_params = config.extra_params.split(",")
                cmd.extend(extra_params)

            run_command(
                cmd,
                cwd=project_root,
            )
            # Update datastore name in terraform variables to avoid conflicts
            self.update_datastore_name(new_project_dir, unique_id)
            # Setup CICD using CLI from the newly created project directory
            logger.info("\n🔧 Setting up CICD...")
            # Fetch GitHub username dynamically
            try:
                result = run_command(
                    ["gh", "api", "user", "--jq", ".login"],
                    capture_output=True,
                    check=True,
                    cwd=new_project_dir,
                )
                github_username = result.stdout.strip()
                logger.info(f"Using GitHub username: {github_username}")
            except subprocess.CalledProcessError:
                logger.error("Failed to fetch GitHub username. Using empty string.")
                github_username = ""
            try:
                run_command(
                    [
                        "python",
                        "-m",
                        "src.cli.main",
                        "setup-cicd",
                        "--dev-project",
                        dev_project,
                        "--staging-project",
                        staging_project,
                        "--prod-project",
                        prod_project,
                        "--cicd-project",
                        cicd_project,
                        "--region",
                        region,
                        "--repository-name",
                        project_name,
                        "--repository-owner",
                        github_username,
                        "--host-connection-name",
                        f"git-{project_name}",
                        "--git-provider",
                        "github",
                        "--github-pat",
                        github_pat,
                        "--github-app-installation-id",
                        github_app_installation_id,
                        "--auto-approve",
                    ],
                    capture_output=False,
                    cwd=new_project_dir,
                )
            except subprocess.CalledProcessError as e:
                logger.error("\n❌ CICD setup failed!")
                logger.error(f"Exit code: {e.returncode}")
                logger.error(f"Error output:\n{e.stderr}")
                logger.error(f"Standard output:\n{e.output}")
                raise

            time.sleep(60)

            # Configure git remote with authentication
            logger.info("\n🔄 Setting up git remote with authentication...")
            github_repo_url = f"https://{github_username}:{github_pat}@github.com/{github_username}/{project_name}.git"

            # Initialize git repo if not already initialized
            if not (new_project_dir / ".git").exists():
                run_command(["git", "init"], cwd=new_project_dir)

            # Check if remote exists and remove it if it does
            try:
                run_command(
                    ["git", "remote", "remove", "origin"],
                    cwd=new_project_dir,
                    check=False,
                )
            except subprocess.CalledProcessError:
                pass

            # Add the authenticated remote
            run_command(
                ["git", "remote", "add", "origin", github_repo_url], cwd=new_project_dir
            )

            # Verify remote is set correctly (without printing the token)
            logger.info(
                f"Remote set to: https://{github_username}@github.com/{github_username}/{project_name}.git"
            )
            # Create example commits to test CI/CD
            logger.info("\n📝 Creating example commits to showcase CI/CD...")

            # Initialize git repo and set remote
            logger.info("\n🔄 Initializing git repository...")
            # Configure git identity for the test
            run_command(
                ["git", "config", "user.email", "test@example.com"], cwd=new_project_dir
            )
            run_command(
                ["git", "config", "user.name", "Test User"], cwd=new_project_dir
            )
            # Add remote and push initial commit
            run_command(["git", "add", "."], cwd=new_project_dir)
            run_command(["git", "commit", "-m", "Initial commit"], cwd=new_project_dir)
            run_command(
                ["git", "push", "-u", "origin", "main", "--force"], cwd=new_project_dir
            )

            # Create and push feature branch for PR
            logger.info("\n🔄 Creating feature branch for PR workflow...")
            run_command(
                ["git", "checkout", "-b", "feature/example-change"], cwd=new_project_dir
            )

            # Create dummy file in the app folder
            app_dir = new_project_dir / "app"
            app_dir.mkdir(exist_ok=True)
            dummy_file = app_dir / "dummy.py"
            with open(dummy_file, "w") as f:
                f.write('''"""Example file to demonstrate CI/CD workflows."""

def dummy_function():
    """Just a dummy function."""
    return True''')

            # Commit and push feature branch
            run_command(["git", "add", "."], cwd=new_project_dir)
            run_command(
                ["git", "commit", "-m", "feat: add dummy file"], cwd=new_project_dir
            )
            run_command(
                ["git", "push", "origin", "feature/example-change"], cwd=new_project_dir
            )

            # Create PR
            pr_output = run_command(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    "feat: Add dummy file",
                    "--body",
                    "Example PR to demonstrate CI workflow",
                    "--head",
                    "feature/example-change",
                ],
                cwd=new_project_dir,
                capture_output=True,
            )

            logger.info(f"\n🔍 Created PR: {pr_output.stdout}")

            time.sleep(5)

            # Monitor staging deployment
            self.monitor_deployment(
                project_id=cicd_project,
                region=region,
                environment="staging",
                repo_owner=github_username,
                repo_name=project_name,
            )
            time.sleep(5)
            # Monitor production deployment
            self.monitor_deployment(
                project_id=cicd_project,
                region=region,
                environment="production",
                repo_owner=github_username,
                repo_name=project_name,
            )

            logger.info("\n✅ E2E deployment test completed successfully!")
        except Exception as e:
            logger.error(f"\n❌ Test failed with error: {e}")
            logger.error("See above logs for detailed error information")
            pytest.fail(f"E2E deployment test failed {e}")

        finally:
            logger.info(f"Project Directory: {new_project_dir}")
            logger.info(f"GitHub Repository: {project_name}")

            # Clean up all resources
            try:
                self.cleanup_resources(
                    new_project_dir,
                    project_name,
                    str(cicd_project),
                    region,
                    config.deployment_target,
                )
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
