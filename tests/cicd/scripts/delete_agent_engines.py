#!/usr/bin/env python3

# mypy: ignore-errors
"""
Script to delete all Agent Engine services from specified projects.

This script deletes all Agent Engine services from projects specified via environment variables.

Environment Variables:
- PROJECT_IDS: Comma-separated list of project IDs (e.g., "proj1,proj2,proj3")
- Alternative: Individual variables CICD_PROJECT_ID, E2E_PR_PROJECT_ID, E2E_ST_PROJECT_ID

Example usage:
    export PROJECT_IDS="my-project-1,my-project-2,my-project-3"
    python delete_agent_engines.py

Based on the cleanup logic from tests/cicd/test_e2e_deployment.py
"""

import logging
import os
import sys
import time

import vertexai
from google.api_core import exceptions
from vertexai import agent_engines

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Project IDs to clean up - loaded from environment variables
def get_project_ids() -> list[str]:
    """Get project IDs from environment variables."""
    project_ids = []

    # Try to get from comma-separated env var first
    env_projects = os.getenv("PROJECT_IDS")
    if env_projects:
        project_ids = [pid.strip() for pid in env_projects.split(",") if pid.strip()]
    else:
        # Fallback to individual env vars for backward compatibility
        for env_var in ["CICD_PROJECT_ID", "E2E_PR_PROJECT_ID", "E2E_ST_PROJECT_ID"]:
            project_id = os.getenv(env_var)
            if project_id:
                project_ids.append(project_id.strip())

    if not project_ids:
        raise ValueError(
            "No project IDs found. Please set either:\n"
            "- PROJECT_IDS environment variable with comma-separated project IDs, or\n"
            "- Individual env vars: CICD_PROJECT_ID, E2E_PR_PROJECT_ID, E2E_ST_PROJECT_ID"
        )

    return project_ids


# Default region
DEFAULT_REGION = "europe-west1"

# Rate limiting configuration
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 60  # seconds to wait when hitting rate limits
RETRY_DELAY = 5  # seconds to wait between retries


def delete_single_agent_engine(engine, retry_count: int = 0) -> bool:
    """
    Delete a single Agent Engine with retry logic and force deletion.

    Args:
        engine: The AgentEngine instance to delete
        retry_count: Current retry attempt number

    Returns:
        True if deleted successfully, False otherwise
    """
    engine_name = engine.display_name or engine.resource_name

    try:
        logger.info(f"🗑️ Deleting Agent Engine: {engine_name}")
        logger.info(f"   Resource name: {engine.resource_name}")

        # Try normal deletion first
        engine.delete()
        logger.info(f"✅ Successfully deleted Agent Engine: {engine_name}")
        return True

    except exceptions.BadRequest as e:
        # Handle child resources error by using force deletion
        if "contains child resources" in str(e):
            logger.warning(
                f"⚠️ Agent Engine {engine_name} has child resources, attempting force deletion..."
            )
            try:
                # Force delete with child resources
                engine.delete(force=True)
                logger.info(
                    f"✅ Force deleted Agent Engine with child resources: {engine_name}"
                )
                return True
            except Exception as force_e:
                logger.error(f"❌ Force deletion failed for {engine_name}: {force_e}")
                return False
        else:
            logger.error(f"❌ Bad request error for {engine_name}: {e}")
            return False

    except exceptions.TooManyRequests as e:
        # Handle rate limiting
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Rate limit hit for {engine_name}, waiting {RATE_LIMIT_DELAY} seconds before retry {retry_count + 1}/{MAX_RETRIES}..."
            )
            time.sleep(RATE_LIMIT_DELAY)
            return delete_single_agent_engine(engine, retry_count + 1)
        else:
            logger.error(f"❌ Rate limit exceeded max retries for {engine_name}: {e}")
            return False

    except Exception as e:
        # Handle other errors with retry logic
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Error deleting {engine_name}, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_agent_engine(engine, retry_count + 1)
        else:
            logger.error(
                f"❌ Failed to delete {engine_name} after {MAX_RETRIES} retries: {e}"
            )
            return False


def delete_agent_engines_in_project(
    project_id: str, region: str = DEFAULT_REGION
) -> tuple[int, int]:
    """
    Delete all Agent Engine services in a specific project.

    Args:
        project_id: The GCP project ID
        region: The GCP region (default: europe-west1)

    Returns:
        Tuple of (successful_deletions, total_engines_found)
    """
    logger.info(f"🔍 Checking for Agent Engine services in project {project_id}...")

    try:
        # Initialize Vertex AI for this project
        vertexai.init(project=project_id, location=region)

        # List all Agent Engine services in the project
        logger.info(f"📋 Listing all Agent Engine services in {project_id}...")
        engines = list(agent_engines.AgentEngine.list())

        if not engines:
            logger.info(f"✅ No Agent Engine services found in {project_id}")
            return 0, 0

        logger.info(f"🎯 Found {len(engines)} Agent Engine service(s) in {project_id}")

        # Delete each engine with improved error handling
        deleted_count = 0
        for i, engine in enumerate(engines, 1):
            logger.info(f"📋 Processing engine {i}/{len(engines)} in {project_id}")

            if delete_single_agent_engine(engine):
                deleted_count += 1

            # Small delay between deletions to avoid overwhelming the API
            if i < len(engines):  # Don't sleep after the last engine
                time.sleep(1)

        logger.info(
            f"🎉 Deleted {deleted_count}/{len(engines)} Agent Engine service(s) in {project_id}"
        )
        return deleted_count, len(engines)

    except Exception as e:
        logger.error(f"❌ Error processing project {project_id}: {e}")
        return 0, 0


def main():
    """Main function to delete Agent Engine services from all specified projects."""
    logger.info("🚀 Starting Agent Engine cleanup across multiple projects...")

    try:
        project_ids = get_project_ids()
        logger.info(f"🎯 Target projects: {', '.join(project_ids)}")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

    total_deleted = 0
    total_found = 0
    failed_projects = []

    for project_id in project_ids:
        try:
            deleted_count, found_count = delete_agent_engines_in_project(project_id)
            total_deleted += deleted_count
            total_found += found_count
        except Exception as e:
            logger.error(f"❌ Failed to process project {project_id}: {e}")
            failed_projects.append(project_id)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"🎯 Total Agent Engine services found: {total_found}")
    logger.info(f"✅ Total Agent Engine services deleted: {total_deleted}")
    logger.info(f"❌ Failed deletions: {total_found - total_deleted}")
    logger.info(
        f"📁 Projects processed: {len(project_ids) - len(failed_projects)}/{len(project_ids)}"
    )

    if failed_projects:
        logger.warning(f"⚠️ Failed to process projects: {', '.join(failed_projects)}")
        sys.exit(1)
    elif total_found > total_deleted:
        logger.warning(
            f"⚠️ Some Agent Engine services could not be deleted ({total_found - total_deleted} failures)"
        )
        sys.exit(1)
    else:
        logger.info("🎉 All projects processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
