#!/usr/bin/env python3

"""
Script to delete all Cloud SQL instances from specified projects.

This script deletes all Cloud SQL instances from projects specified via environment variables.

Environment Variables:
- PROJECT_IDS: Comma-separated list of project IDs (e.g., "proj1,proj2,proj3")
- Alternative: Individual variables CICD_PROJECT_ID, E2E_PR_PROJECT_ID, E2E_ST_PROJECT_ID

Example usage:
    export PROJECT_IDS="my-project-1,my-project-2,my-project-3"
    python delete_cloud_sql_instances.py
"""

import logging
import os
import sys
import time
import googleapiclient.discovery
from googleapiclient.errors import HttpError

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


def delete_cloud_sql_instances_in_project(project_id: str) -> tuple[int, int]:
    """
    Delete Cloud SQL instances starting with 'test-' or 'myagent' in a specific project.

    Args:
        project_id: The GCP project ID

    Returns:
        Tuple of (successful_deletions, total_instances_found)
    """
    logger.info(f"🔍 Checking for Cloud SQL instances in project {project_id}...")

    try:
        service = googleapiclient.discovery.build('sqladmin', 'v1beta4')
        
        # List all instances
        request = service.instances().list(project=project_id)
        response = request.execute()
        all_instances = response.get('items', [])

        # Filter instances
        instances = [
            inst for inst in all_instances
            if (inst['name'].startswith("test-") or inst['name'].startswith("myagent"))
        ]

        if not instances:
            logger.info(f"✅ No Cloud SQL instances starting with 'test-' or 'myagent' found in {project_id}")
            return 0, 0

        logger.info(f"🎯 Found {len(instances)} Cloud SQL instance(s) starting with 'test-' or 'myagent' in {project_id}")

        deleted_count = 0
        for i, instance in enumerate(instances, 1):
            instance_name = instance['name']
            logger.info(f"📋 Processing instance {i}/{len(instances)}: {instance_name}")

            try:
                logger.info(f"🗑️ Deleting Cloud SQL instance: {instance_name}")
                delete_request = service.instances().delete(project=project_id, instance=instance_name)
                delete_request.execute()
                logger.info(f"✅ Triggered deletion for Cloud SQL instance: {instance_name}")
                deleted_count += 1
            except HttpError as e:
                logger.error(f"❌ Failed to delete {instance_name}: {e}")
            except Exception as e:
                logger.error(f"❌ Unexpected error deleting {instance_name}: {e}")

            # Small delay to avoid rate limits
            if i < len(instances):
                time.sleep(1)

        logger.info(
            f"🎉 Triggered deletion for {deleted_count}/{len(instances)} Cloud SQL instance(s) in {project_id}"
        )
        return deleted_count, len(instances)

    except Exception as e:
        logger.error(f"❌ Error processing project {project_id}: {e}")
        return 0, 0


def main():
    """Main function to delete Cloud SQL instances from all specified projects."""
    logger.info("🚀 Starting Cloud SQL cleanup across multiple projects...")

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
            deleted_count, found_count = delete_cloud_sql_instances_in_project(project_id)
            total_deleted += deleted_count
            total_found += found_count
        except Exception as e:
            logger.error(f"❌ Failed to process project {project_id}: {e}")
            failed_projects.append(project_id)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"🎯 Total Cloud SQL instances found: {total_found}")
    logger.info(f"✅ Total Cloud SQL instances deletion triggered: {total_deleted}")
    logger.info(f"❌ Failed deletions: {total_found - total_deleted}")
    logger.info(
        f"📁 Projects processed: {len(project_ids) - len(failed_projects)}/{len(project_ids)}"
    )

    if failed_projects:
        logger.warning(f"⚠️ Failed to process projects: {', '.join(failed_projects)}")
        sys.exit(1)
    elif total_found > total_deleted:
        logger.warning(
            f"⚠️ Some Cloud SQL instances could not be deleted ({total_found - total_deleted} failures)"
        )
        sys.exit(1)
    else:
        logger.info("🎉 All projects processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
