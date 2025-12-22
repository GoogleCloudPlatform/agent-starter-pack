#!/usr/bin/env python3

"""
Script to delete service accounts starting with 'test-' from specified projects.

This script deletes all service accounts starting with 'test-' prefix from multiple projects.

Environment Variables:
- E2E_PROJECT_IDS: Comma-separated list of E2E project IDs
- CICD_PROJECT_ID: CICD project ID

Example usage:
    export E2E_PROJECT_IDS="e2e-dev,e2e-st,e2e-pr"
    export CICD_PROJECT_ID="cicd-project"
    python delete_service_accounts.py
"""

import json
import logging
import os
import subprocess
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Project IDs to clean up - loaded from environment variables
def get_project_prefix_mapping() -> dict[str, list[str]]:
    """
    Get project IDs and their corresponding prefixes from environment variables.

    Returns:
        Dictionary mapping project_id -> list of prefixes
    """
    project_prefix_map = {}

    # Try to get from comma-separated env var first (for 'test-' and 'myagent' prefixes)
    env_projects = os.getenv("PROJECT_IDS")
    if env_projects:
        for pid in env_projects.split(","):
            if pid.strip():
                project_prefix_map[pid.strip()] = ["test-", "myagent"]
    else:
        # Get E2E project IDs (use 'test-' and 'myagent' prefixes)
        e2e_projects = os.getenv("E2E_PROJECT_IDS")
        if e2e_projects:
            for pid in e2e_projects.split(","):
                if pid.strip():
                    project_prefix_map[pid.strip()] = ["test-", "myagent"]

        # Get CICD project ID (use 'test-' and 'myagent' prefixes)
        cicd_project = os.getenv("CICD_PROJECT_ID")
        if cicd_project:
            project_prefix_map[cicd_project.strip()] = ["test-", "myagent"]

    if not project_prefix_map:
        raise ValueError(
            "No project IDs found. Please set:\n"
            "- PROJECT_IDS: Comma-separated project IDs (for 'test-' and 'myagent' prefixes)\n"
            "- E2E_PROJECT_IDS: Comma-separated E2E project IDs (for 'test-' and 'myagent' prefixes)\n"
            "- CICD_PROJECT_ID: CICD project ID (for 'test-' and 'myagent' prefixes)"
        )

    return project_prefix_map


# Rate limiting configuration
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 60  # seconds to wait when hitting rate limits
RETRY_DELAY = 5  # seconds to wait between retries


def delete_single_service_account(
    project_id: str,
    sa_email: str,
    retry_count: int = 0
) -> bool:
    """
    Delete a single service account with retry logic.

    Args:
        project_id: The GCP project ID
        sa_email: Email address of the service account
        retry_count: Current retry attempt number

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        logger.info(f"🗑️ Deleting service account: {sa_email}")

        # Delete the service account using gcloud
        result = subprocess.run(
            ["gcloud", "iam", "service-accounts", "delete", sa_email,
             "--project", project_id, "--quiet"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            logger.info(f"✅ Successfully deleted service account: {sa_email}")
            return True
        elif "NOT_FOUND" in result.stderr or "does not exist" in result.stderr:
            logger.info(f"✅ Service account {sa_email} not found (already deleted)")
            return True
        else:
            logger.error(f"❌ Failed to delete {sa_email}: {result.stderr}")

            # Retry on certain errors
            if retry_count < MAX_RETRIES and ("RESOURCE_EXHAUSTED" in result.stderr or "quota" in result.stderr.lower()):
                logger.warning(
                    f"⏱️ Rate limit hit for {sa_email}, waiting {RATE_LIMIT_DELAY} seconds before retry {retry_count + 1}/{MAX_RETRIES}..."
                )
                time.sleep(RATE_LIMIT_DELAY)
                return delete_single_service_account(project_id, sa_email, retry_count + 1)

            return False

    except subprocess.TimeoutExpired:
        logger.error(f"❌ Timeout deleting service account: {sa_email}")
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_service_account(project_id, sa_email, retry_count + 1)
        return False

    except Exception as e:
        # Handle other errors with retry logic
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Error deleting {sa_email}, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_service_account(project_id, sa_email, retry_count + 1)
        else:
            logger.error(
                f"❌ Failed to delete {sa_email} after {MAX_RETRIES} retries: {e}"
            )
            return False


def delete_service_accounts_in_project(project_id: str, sa_prefixes: list[str]) -> tuple[int, int]:
    """
    Delete all service accounts starting with specified prefixes in a specific project.

    Args:
        project_id: The GCP project ID
        sa_prefixes: List of prefixes to filter service accounts

    Returns:
        Tuple of (successful_deletions, total_service_accounts_found)
    """
    logger.info(f"🔍 Checking for service accounts with prefixes {sa_prefixes} in project {project_id}...")

    try:
        # List all service accounts in the project using gcloud
        logger.info(f"📋 Listing all service accounts in {project_id}...")

        result = subprocess.run(
            ["gcloud", "iam", "service-accounts", "list",
             "--project", project_id, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"❌ Failed to list service accounts in {project_id}: {result.stderr}")
            return 0, 0

        service_accounts = json.loads(result.stdout)

        # Filter service accounts that start with any of the prefixes
        filtered_accounts = [
            sa for sa in service_accounts
            if any(sa.get("email", "").startswith(prefix) for prefix in sa_prefixes)
        ]

        if not filtered_accounts:
            logger.info(f"✅ No service accounts starting with {sa_prefixes} found in {project_id}")
            return 0, 0

        logger.info(f"🎯 Found {len(filtered_accounts)} service account(s) starting with {sa_prefixes} in {project_id}")

        # Delete each service account with improved error handling
        deleted_count = 0
        for i, sa in enumerate(filtered_accounts, 1):
            logger.info(f"📋 Processing service account {i}/{len(filtered_accounts)} in {project_id}")
            sa_email = sa.get("email", "")

            if delete_single_service_account(project_id, sa_email):
                deleted_count += 1

            # Small delay between deletions to avoid overwhelming the API
            if i < len(filtered_accounts):  # Don't sleep after the last service account
                time.sleep(1)

        logger.info(
            f"🎉 Deleted {deleted_count}/{len(filtered_accounts)} service account(s) in {project_id}"
        )
        return deleted_count, len(filtered_accounts)

    except Exception as e:
        logger.error(f"❌ Error processing project {project_id}: {e}")
        return 0, 0


def main():
    """Main function to delete service accounts from all specified projects."""
    logger.info(f"🚀 Starting service account cleanup across multiple projects...")

    try:
        project_prefix_map = get_project_prefix_mapping()
        logger.info(f"🎯 Target projects:")
        for project_id, prefixes in project_prefix_map.items():
            logger.info(f"   - {project_id} (prefixes: {prefixes})")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

    total_deleted = 0
    total_found = 0
    failed_projects = []

    for project_id, sa_prefixes in project_prefix_map.items():
        try:
            deleted_count, found_count = delete_service_accounts_in_project(project_id, sa_prefixes)
            total_deleted += deleted_count
            total_found += found_count
        except Exception as e:
            logger.error(f"❌ Failed to process project {project_id}: {e}")
            failed_projects.append(project_id)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"🎯 Total service accounts found: {total_found}")
    logger.info(f"✅ Total service accounts deleted: {total_deleted}")
    logger.info(f"❌ Failed deletions: {total_found - total_deleted}")
    logger.info(
        f"📁 Projects processed: {len(project_prefix_map) - len(failed_projects)}/{len(project_prefix_map)}"
    )

    if failed_projects:
        logger.warning(f"⚠️ Failed to process projects: {', '.join(failed_projects)}")
        sys.exit(1)
    elif total_found > total_deleted:
        logger.warning(
            f"⚠️ Some service accounts could not be deleted ({total_found - total_deleted} failures)"
        )
        sys.exit(1)
    else:
        logger.info("🎉 All projects processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
