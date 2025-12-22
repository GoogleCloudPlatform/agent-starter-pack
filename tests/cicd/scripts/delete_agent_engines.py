#!/usr/bin/env python3

"""
Script to delete all Agent Engine services and Cloud Run services from specified projects.

This script deletes all Agent Engine services and Cloud Run services (with test-/myagent prefix)
from projects specified via environment variables.

Environment Variables:
- PROJECT_IDS: Comma-separated list of project IDs (e.g., "proj1,proj2,proj3")
- Alternative: Individual variables CICD_PROJECT_ID, E2E_PR_PROJECT_ID, E2E_ST_PROJECT_ID

Example usage:
    export PROJECT_IDS="my-project-1,my-project-2,my-project-3"
    python delete_agent_engines.py

Based on the cleanup logic from tests/cicd/test_e2e_deployment.py
"""

import json
import logging
import os
import subprocess
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


# Regions to clean up
REGIONS = ["us-central1", "europe-west4", "europe-west1"]

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
    project_id: str, region: str
) -> tuple[int, int]:
    """
    Delete Agent Engine services in a specific project and region.

    Args:
        project_id: The GCP project ID
        region: The GCP region

    Returns:
        Tuple of (successful_deletions, total_engines_found)
    """
    logger.info(f"🔍 Checking for Agent Engine services in {project_id} ({region})...")

    try:
        # Initialize Vertex AI for this project
        vertexai.init(project=project_id, location=region)

        # List all Agent Engine services in the project
        logger.info(f"📋 Listing all Agent Engine services in {project_id} ({region})...")
        all_engines = list(agent_engines.AgentEngine.list())

        # Delete ALL agent engines (no filtering by prefix)
        engines = all_engines

        if not engines:
            logger.info(f"✅ No Agent Engine services found in {project_id} ({region})")
            return 0, 0

        logger.info(f"🎯 Found {len(engines)} Agent Engine service(s) in {project_id} ({region})")

        # Delete each engine with improved error handling
        deleted_count = 0
        for i, engine in enumerate(engines, 1):
            logger.info(f"📋 Processing engine {i}/{len(engines)} in {project_id} ({region})")

            if delete_single_agent_engine(engine):
                deleted_count += 1

            # Small delay between deletions to avoid overwhelming the API
            if i < len(engines):  # Don't sleep after the last engine
                time.sleep(1)

        logger.info(
            f"🎉 Deleted {deleted_count}/{len(engines)} Agent Engine service(s) in {project_id} ({region})"
        )
        return deleted_count, len(engines)

    except Exception as e:
        logger.error(f"❌ Error processing {project_id} ({region}): {e}")
        return 0, 0


def delete_single_cloud_run_service(
    project_id: str, region: str, service_name: str, retry_count: int = 0
) -> bool:
    """
    Delete a single Cloud Run service with retry logic.

    Args:
        project_id: The GCP project ID
        region: The GCP region
        service_name: Name of the Cloud Run service
        retry_count: Current retry attempt number

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        logger.info(f"🗑️ Deleting Cloud Run service: {service_name}")

        result = subprocess.run(
            [
                "gcloud", "run", "services", "delete", service_name,
                "--region", region,
                "--project", project_id,
                "--quiet"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info(f"✅ Successfully deleted Cloud Run service: {service_name}")
            return True
        elif "could not be found" in result.stderr or "NOT_FOUND" in result.stderr:
            logger.info(f"✅ Cloud Run service {service_name} not found (already deleted)")
            return True
        else:
            logger.error(f"❌ Failed to delete {service_name}: {result.stderr}")

            if retry_count < MAX_RETRIES and ("RESOURCE_EXHAUSTED" in result.stderr or "quota" in result.stderr.lower()):
                logger.warning(
                    f"⏱️ Rate limit hit for {service_name}, waiting {RATE_LIMIT_DELAY} seconds before retry {retry_count + 1}/{MAX_RETRIES}..."
                )
                time.sleep(RATE_LIMIT_DELAY)
                return delete_single_cloud_run_service(project_id, region, service_name, retry_count + 1)

            return False

    except subprocess.TimeoutExpired:
        logger.error(f"❌ Timeout deleting Cloud Run service: {service_name}")
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_cloud_run_service(project_id, region, service_name, retry_count + 1)
        else:
            logger.error(
                f"❌ Failed to delete {service_name} after {MAX_RETRIES} retries due to timeout"
            )
            return False

    except Exception as e:
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Error deleting {service_name}, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_cloud_run_service(project_id, region, service_name, retry_count + 1)
        else:
            logger.error(
                f"❌ Failed to delete {service_name} after {MAX_RETRIES} retries: {e}"
            )
            return False


def delete_cloud_run_services_in_project(
    project_id: str, region: str
) -> tuple[int, int]:
    """
    Delete Cloud Run services with test-/myagent prefix in a specific project and region.

    Args:
        project_id: The GCP project ID
        region: The GCP region

    Returns:
        Tuple of (successful_deletions, total_services_found)
    """
    logger.info(f"🔍 Checking for Cloud Run services in {project_id} ({region})...")

    try:
        # List all Cloud Run services in the project/region
        result = subprocess.run(
            [
                "gcloud", "run", "services", "list",
                "--region", region,
                "--project", project_id,
                "--format", "json"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"❌ Failed to list Cloud Run services in {project_id} ({region}): {result.stderr}")
            return 0, 0

        all_services = json.loads(result.stdout) if result.stdout.strip() else []

        # Filter services that start with 'test-' or 'myagent'
        services = [
            svc for svc in all_services
            if svc.get("metadata", {}).get("name", "").startswith(("test-", "myagent"))
        ]

        if not services:
            logger.info(f"✅ No Cloud Run services with test-/myagent prefix found in {project_id} ({region})")
            return 0, 0

        logger.info(f"🎯 Found {len(services)} Cloud Run service(s) with test-/myagent prefix in {project_id} ({region})")

        deleted_count = 0
        for i, svc in enumerate(services, 1):
            service_name = svc.get("metadata", {}).get("name", "")
            logger.info(f"📋 Processing Cloud Run service {i}/{len(services)} in {project_id} ({region})")

            if delete_single_cloud_run_service(project_id, region, service_name):
                deleted_count += 1

            if i < len(services):
                time.sleep(1)

        logger.info(
            f"🎉 Deleted {deleted_count}/{len(services)} Cloud Run service(s) in {project_id} ({region})"
        )
        return deleted_count, len(services)

    except Exception as e:
        logger.error(f"❌ Error processing Cloud Run in {project_id} ({region}): {e}")
        return 0, 0


def main():
    """Main function to delete Agent Engine and Cloud Run services from all specified projects."""
    logger.info("🚀 Starting Agent Engine and Cloud Run cleanup across multiple projects and regions...")

    try:
        project_ids = get_project_ids()
        logger.info(f"🎯 Target projects: {', '.join(project_ids)}")
        logger.info(f"🌍 Target regions: {', '.join(REGIONS)}")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

    # Define cleanup tasks: (name, prefix, icon, function)
    cleanup_tasks = [
        ("Agent Engine", "ae", "🤖", delete_agent_engines_in_project),
        ("Cloud Run", "cr", "☁️", delete_cloud_run_services_in_project),
    ]

    failed_locations: list[str] = []
    stats: dict[str, dict[str, int]] = {}

    for name, prefix, icon, cleanup_func in cleanup_tasks:
        logger.info("\n" + "=" * 60)
        logger.info(f"{icon} {name.upper()} CLEANUP")
        logger.info("=" * 60)

        total_deleted = 0
        total_found = 0

        for project_id in project_ids:
            for region in REGIONS:
                try:
                    deleted_count, found_count = cleanup_func(project_id, region)
                    total_deleted += deleted_count
                    total_found += found_count
                except Exception as e:
                    logger.error(f"❌ Failed to process {name} in {project_id} ({region}): {e}")
                    failed_locations.append(f"{prefix}:{project_id}/{region}")

        stats[prefix] = {"deleted": total_deleted, "found": total_found}

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"🤖 Agent Engine services found: {stats['ae']['found']}")
    logger.info(f"✅ Agent Engine services deleted: {stats['ae']['deleted']}")
    logger.info(f"☁️ Cloud Run services found: {stats['cr']['found']}")
    logger.info(f"✅ Cloud Run services deleted: {stats['cr']['deleted']}")
    total_failed = sum(s["found"] - s["deleted"] for s in stats.values())
    logger.info(f"❌ Total failed deletions: {total_failed}")
    total_locations = len(project_ids) * len(REGIONS) * len(cleanup_tasks)
    logger.info(
        f"📁 Locations processed: {total_locations - len(failed_locations)}/{total_locations}"
    )

    if failed_locations:
        logger.warning(f"⚠️ Failed to process locations: {', '.join(failed_locations)}")
        sys.exit(1)
    elif total_failed > 0:
        logger.warning(
            f"⚠️ Some services could not be deleted ({total_failed} failures)"
        )
        sys.exit(1)
    else:
        logger.info("🎉 All projects and regions processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
