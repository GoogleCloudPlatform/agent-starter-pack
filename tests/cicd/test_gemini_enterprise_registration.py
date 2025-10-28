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

"""
Integration test for Gemini Enterprise registration.

This test validates the full workflow of:
1. Templating a sample agent
2. Installing dependencies
3. Deploying to Agent Engine (uses gcloud default project)
4. Registering with Gemini Enterprise
5. Cleaning up (deleting Gemini Enterprise registration and Agent Engine)

Environment variables required:
- ID: The Gemini Enterprise app resource name (or GEMINI_ENTERPRISE_APP_ID for backward compatibility)

Prerequisites:
- Authenticated with gcloud (gcloud auth application-default login)
- Default project set (gcloud config set project <PROJECT_ID>)
"""

import json
import logging
import os
import subprocess
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
import requests
import vertexai
from google.auth import default
from google.auth.transport.requests import Request as GoogleAuthRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_REGION = "europe-west1"
TARGET_DIR = "target"


def run_command(
    cmd: list[str],
    capture_output: bool = False,
    check: bool = True,
    cwd: str | None = None,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run a shell command with enhanced error handling"""
    cmd_str = " ".join(cmd)
    logger.info(f"\n▶ Running command: {cmd_str}")

    # Merge environment variables
    command_env = os.environ.copy()
    if env:
        command_env.update(env)

    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                cwd=cwd,
                env=command_env,
            )
        else:
            result = subprocess.run(
                cmd, check=check, cwd=cwd, env=command_env, text=True
            )

        return result

    except subprocess.CalledProcessError as e:
        error_msg = (
            f"\n❌ Command failed with exit code {e.returncode}\nCommand: {cmd_str}"
        )
        logger.error(error_msg)
        raise
    except Exception as e:
        error_msg = (
            f"\n❌ Unexpected error running command\nCommand: {cmd_str}\nError: {e!s}"
        )
        logger.error(error_msg)
        raise


@pytest.mark.skipif(
    not os.environ.get("RUN_GEMINI_ENTERPRISE_TEST"),
    reason="Gemini Enterprise test is skipped by default. Set RUN_GEMINI_ENTERPRISE_TEST=1 to run.",
)
class TestGeminiEnterpriseRegistration:
    """Test class for Gemini Enterprise registration workflow"""

    @pytest.fixture
    def registered_agent(self) -> Generator[tuple[str, str | None, Path], None, None]:
        """
        Fixture that creates, deploys, and registers an agent with Gemini Enterprise.

        Yields:
            Tuple of (agent_engine_id, agent_resource_name, project_path)

        Cleanup is guaranteed to run even if the test fails.
        """
        # Get required environment variables
        gemini_app_id = os.environ.get("ID") or os.environ.get(
            "GEMINI_ENTERPRISE_APP_ID"
        )
        if not gemini_app_id:
            pytest.skip(
                "ID or GEMINI_ENTERPRISE_APP_ID environment variable is required for this test"
            )

        logger.info("\n" + "=" * 80)
        logger.info("🚀 Starting Gemini Enterprise Registration Test Setup")
        logger.info("=" * 80)

        # Initialize variables for cleanup
        agent_engine_id = None
        agent_resource_name = None
        project_path = None

        try:
            # Create target directory if it doesn't exist
            os.makedirs(TARGET_DIR, exist_ok=True)

            # Step 1: Create agent from template
            timestamp = datetime.now().strftime("%H%M%S%f")[:8]
            project_name = f"gemini-test-{timestamp}"
            project_path = Path(TARGET_DIR) / project_name

            logger.info(f"\n📦 Step 1: Creating agent project: {project_name}")
            run_command(
                [
                    "uv",
                    "run",
                    "agent-starter-pack",
                    "create",
                    project_name,
                    "--agent",
                    "adk_base",
                    "--deployment-target",
                    "agent_engine",
                    "--output-dir",
                    TARGET_DIR,
                    "--auto-approve",
                    "--skip-checks",
                ]
            )

            # Verify project was created
            assert project_path.exists(), (
                f"Project directory {project_path} was not created"
            )
            logger.info(f"✅ Project created at {project_path}")

            # Step 2: Install dependencies
            logger.info("\n📥 Step 2: Installing dependencies")
            run_command(["make", "install"], cwd=str(project_path))
            logger.info("✅ Dependencies installed")

            # Step 3: Deploy to Agent Engine (uses gcloud default project)
            logger.info("\n🚀 Step 3: Deploying to Agent Engine")
            run_command(
                ["make", "deploy"],
                cwd=str(project_path),
            )

            # Read deployment metadata
            metadata_file = project_path / "deployment_metadata.json"
            assert metadata_file.exists(), "deployment_metadata.json was not created"

            with open(metadata_file) as f:
                metadata = json.load(f)

            agent_engine_id = metadata.get("remote_agent_engine_id")
            assert agent_engine_id, "Agent Engine ID not found in deployment metadata"
            logger.info(f"✅ Agent deployed to Agent Engine: {agent_engine_id}")

            # Step 4: Register with Gemini Enterprise
            logger.info("\n🔗 Step 4: Registering with Gemini Enterprise")
            register_result = run_command(
                ["uv", "run", "agent-starter-pack-register-gemini-enterprise"],
                cwd=str(project_path),
                env={"ID": gemini_app_id},
                capture_output=True,
            )

            # Extract the registered agent resource name from the output
            # Look for "Agent Name: projects/..." in the output
            for line in register_result.stdout.splitlines():
                if "Agent Name:" in line:
                    agent_resource_name = line.split("Agent Name:")[-1].strip()
                    break

            logger.info("✅ Agent successfully registered with Gemini Enterprise")
            if agent_resource_name:
                logger.info(f"   Agent Resource Name: {agent_resource_name}")

            # Yield to test - cleanup will run after the test completes
            yield agent_engine_id, agent_resource_name, project_path

        finally:
            # Cleanup - guaranteed to run even if test fails
            logger.info("\n🧹 Cleanup: Deleting deployed resources")

            # First, delete the Gemini Enterprise registration
            if agent_resource_name:
                try:
                    logger.info(
                        f"Deleting Gemini Enterprise registration: {agent_resource_name}"
                    )

                    # Get access token for authentication
                    credentials, _ = default()
                    auth_req = GoogleAuthRequest()
                    credentials.refresh(auth_req)
                    access_token = credentials.token

                    # Extract project ID from agent_engine_id for billing header
                    if agent_engine_id:
                        project_id = agent_engine_id.split("/")[1]
                    else:
                        # Fallback: extract from agent_resource_name
                        project_id = agent_resource_name.split("/")[1]

                    # Delete the registration using Discovery Engine API
                    url = f"https://discoveryengine.googleapis.com/v1alpha/{agent_resource_name}"
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "X-Goog-User-Project": project_id,
                    }

                    response = requests.delete(url, headers=headers, timeout=30)
                    response.raise_for_status()

                    logger.info(
                        "✅ Gemini Enterprise registration deleted successfully"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to delete Gemini Enterprise registration: {e}"
                    )

            # Then, delete the Agent Engine
            if agent_engine_id:
                try:
                    # Extract agent engine ID components
                    parts = agent_engine_id.split("/")
                    if len(parts) >= 6:
                        project_id = parts[1]
                        location = parts[3]

                        # Initialize Vertex AI client
                        client = vertexai.Client(project=project_id, location=location)

                        # Delete the agent engine
                        logger.info(f"Deleting Agent Engine: {agent_engine_id}")
                        client.agent_engines.delete(name=agent_engine_id)
                        logger.info("✅ Agent Engine deleted successfully")
                    else:
                        logger.warning(
                            f"Could not parse Agent Engine ID: {agent_engine_id}"
                        )

                except Exception as e:
                    logger.error(f"Failed to cleanup Agent Engine: {e}")

            logger.info("\n" + "=" * 80)
            logger.info("✅ Cleanup Completed")
            logger.info("=" * 80)

    def test_full_registration_workflow(
        self, registered_agent: tuple[str, str | None, Path]
    ) -> None:
        """
        Test the full workflow of agent registration with Gemini Enterprise.

        The fixture handles:
        1. Templating a sample agent
        2. Installing dependencies
        3. Deploying to Agent Engine
        4. Registering with Gemini Enterprise
        5. Cleanup (guaranteed via fixture teardown)

        This test validates that all steps completed successfully.
        """
        agent_engine_id, agent_resource_name, project_path = registered_agent

        # Verify Agent Engine was created
        assert agent_engine_id, "Agent Engine ID should not be empty"
        assert "/" in agent_engine_id, "Agent Engine ID should be a resource path"
        logger.info(f"✅ Verified Agent Engine ID: {agent_engine_id}")

        # Verify Gemini Enterprise registration succeeded
        assert agent_resource_name, "Agent resource name should not be empty"
        assert "projects/" in agent_resource_name, (
            "Agent resource name should be a resource path"
        )
        logger.info(
            f"✅ Verified Gemini Enterprise registration: {agent_resource_name}"
        )

        # Verify project directory exists
        assert project_path.exists(), "Project directory should exist"
        logger.info(f"✅ Verified project directory: {project_path}")

        # Verify deployment metadata file exists
        metadata_file = project_path / "deployment_metadata.json"
        assert metadata_file.exists(), "deployment_metadata.json should exist"
        logger.info("✅ Verified deployment metadata file exists")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Gemini Enterprise Registration Test Passed")
        logger.info("=" * 80)
