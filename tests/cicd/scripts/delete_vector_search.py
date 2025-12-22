#!/usr/bin/env python3

"""
Script to force delete all Vector Search indexes, endpoints, and instances from specified projects.

This script deletes all Vector Search resources from projects specified via environment variables.

Environment Variables:
- PROJECT_IDS: Comma-separated list of project IDs (e.g., "proj1,proj2,proj3")
- Alternative: Individual variables CICD_PROJECT_ID, E2E_PR_PROJECT_ID, E2E_ST_PROJECT_ID

Example usage:
    export PROJECT_IDS="my-project-1,my-project-2,my-project-3"
    python delete_vector_search.py
"""

import logging
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.api_core import exceptions
from google.cloud import aiplatform

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
OPERATION_TIMEOUT = 600  # seconds to wait for long-running operations


def wait_for_operation(operation, timeout: int = OPERATION_TIMEOUT) -> bool:
    """
    Wait for a long-running operation to complete.

    Args:
        operation: The operation to wait for
        timeout: Maximum time to wait in seconds

    Returns:
        True if operation completed successfully, False otherwise
    """
    logger.info(f"⏳ Waiting for operation to complete...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Check if operation is done
            if operation.done():
                if operation.exception():
                    logger.error(f"❌ Operation failed: {operation.exception()}")
                    return False
                else:
                    logger.info("✅ Operation completed successfully")
                    return True
            
            time.sleep(5)  # Wait 5 seconds before checking again
            
        except Exception as e:
            logger.error(f"❌ Error checking operation status: {e}")
            return False
    
    logger.error(f"❌ Operation timed out after {timeout} seconds")
    return False


def delete_single_index(resource_name: str, retry_count: int = 0) -> bool:
    """
    Delete a single Vector Search index with retry logic and force deletion.

    Args:
        resource_name: Full resource name of the index
        retry_count: Current retry attempt number

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        logger.info(f"🗑️ Deleting Vector Search index: {resource_name}")

        # Use the aiplatform client to delete the index
        index = aiplatform.MatchingEngineIndex(index_name=resource_name)
        operation = index.delete()
        
        if wait_for_operation(operation):
            logger.info(f"✅ Successfully deleted Vector Search index: {resource_name}")
            return True
        else:
            logger.error(f"❌ Failed to delete Vector Search index: {resource_name}")
            return False

    except exceptions.TooManyRequests as e:
        # Handle rate limiting
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Rate limit hit for {resource_name}, waiting {RATE_LIMIT_DELAY} seconds before retry {retry_count + 1}/{MAX_RETRIES}..."
            )
            time.sleep(RATE_LIMIT_DELAY)
            return delete_single_index(resource_name, retry_count + 1)
        else:
            logger.error(f"❌ Rate limit exceeded max retries for {resource_name}: {e}")
            return False

    except exceptions.NotFound:
        logger.info(f"✅ Vector Search index {resource_name} not found (already deleted)")
        return True

    except Exception as e:
        # Handle other errors with retry logic
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Error deleting {resource_name}, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_index(resource_name, retry_count + 1)
        else:
            logger.error(
                f"❌ Failed to delete {resource_name} after {MAX_RETRIES} retries: {e}"
            )
            return False


def delete_single_endpoint(resource_name: str, retry_count: int = 0) -> bool:
    """
    Delete a single Vector Search endpoint with retry logic and force deletion.

    Args:
        resource_name: Full resource name of the endpoint
        retry_count: Current retry attempt number

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        logger.info(f"🗑️ Deleting Vector Search endpoint: {resource_name}")

        # Use the aiplatform client to delete the endpoint
        endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=resource_name)
        
        # First, try to undeploy all indexes from the endpoint
        try:
            deployed_indexes = endpoint.deployed_indexes
            if deployed_indexes:
                logger.info(f"📤 Undeploying {len(deployed_indexes)} index(es) from endpoint {resource_name}")
                for deployed_index in deployed_indexes:
                    try:
                        endpoint.undeploy_index(deployed_index_id=deployed_index.id)
                        logger.info(f"✅ Undeployed index {deployed_index.id} from endpoint")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to undeploy index {deployed_index.id}: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Error checking deployed indexes: {e}")

        operation = endpoint.delete(force=True)
        
        if wait_for_operation(operation):
            logger.info(f"✅ Successfully deleted Vector Search endpoint: {resource_name}")
            return True
        else:
            logger.error(f"❌ Failed to delete Vector Search endpoint: {resource_name}")
            return False

    except exceptions.TooManyRequests as e:
        # Handle rate limiting
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Rate limit hit for {resource_name}, waiting {RATE_LIMIT_DELAY} seconds before retry {retry_count + 1}/{MAX_RETRIES}..."
            )
            time.sleep(RATE_LIMIT_DELAY)
            return delete_single_endpoint(resource_name, retry_count + 1)
        else:
            logger.error(f"❌ Rate limit exceeded max retries for {resource_name}: {e}")
            return False

    except exceptions.NotFound:
        logger.info(f"✅ Vector Search endpoint {resource_name} not found (already deleted)")
        return True

    except Exception as e:
        # Handle other errors with retry logic
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Error deleting {resource_name}, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_endpoint(resource_name, retry_count + 1)
        else:
            logger.error(
                f"❌ Failed to delete {resource_name} after {MAX_RETRIES} retries: {e}"
            )
            return False


def delete_vector_search_resources_in_project(
    project_id: str, region: str = DEFAULT_REGION
) -> tuple[int, int, int, int]:
    """
    Delete all Vector Search indexes and endpoints in a specific project.

    Args:
        project_id: The GCP project ID
        region: The GCP region (default: europe-west1)

    Returns:
        Tuple of (deleted_indexes, total_indexes, deleted_endpoints, total_endpoints)
    """
    logger.info(f"🔍 Checking for Vector Search resources in project {project_id}...")

    try:
        # Initialize AI Platform with the specific project and region
        aiplatform.init(project=project_id, location=region)

        # List all indexes in the project
        logger.info(f"📋 Listing all Vector Search indexes in {project_id}...")
        try:
            all_indexes = aiplatform.MatchingEngineIndex.list(
                filter=None,
                order_by=None
            )
            # Filter indexes that start with 'test-' or 'myagent'
            indexes = [
                idx for idx in all_indexes
                if idx.display_name and (idx.display_name.startswith("test-") or idx.display_name.startswith("myagent"))
            ]
        except Exception as e:
            logger.warning(f"⚠️ Error listing indexes in {project_id}: {e}")
            indexes = []

        # List all endpoints in the project
        logger.info(f"📋 Listing all Vector Search endpoints in {project_id}...")
        try:
            all_endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
                filter=None,
                order_by=None
            )
            # Filter endpoints that start with 'test-' or 'myagent'
            endpoints = [
                ep for ep in all_endpoints
                if ep.display_name and (ep.display_name.startswith("test-") or ep.display_name.startswith("myagent"))
            ]
        except Exception as e:
            logger.warning(f"⚠️ Error listing endpoints in {project_id}: {e}")
            endpoints = []

        total_indexes = len(indexes)
        total_endpoints = len(endpoints)

        if total_indexes == 0 and total_endpoints == 0:
            logger.info(f"✅ No Vector Search resources starting with 'test-' or 'myagent' found in {project_id}")
            return 0, 0, 0, 0

        logger.info(f"🎯 Found {total_indexes} Vector Search index(es) and {total_endpoints} endpoint(s) starting with 'test-' or 'myagent' in {project_id}")

        deleted_indexes = 0
        deleted_endpoints = 0

        # Delete endpoints first (they may depend on indexes)
        if endpoints:
            logger.info(f"🗑️ Deleting {total_endpoints} Vector Search endpoint(s)...")
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all endpoint deletion tasks
                future_to_endpoint = {
                    executor.submit(delete_single_endpoint, endpoint.resource_name): endpoint.resource_name
                    for endpoint in endpoints
                }
                
                # Wait for all deletions to complete
                for future in as_completed(future_to_endpoint):
                    endpoint_name = future_to_endpoint[future]
                    try:
                        if future.result():
                            deleted_endpoints += 1
                            logger.info(f"✅ Endpoint deletion completed: {endpoint_name}")
                        else:
                            logger.error(f"❌ Endpoint deletion failed: {endpoint_name}")
                    except Exception as exc:
                        logger.error(f"❌ Endpoint deletion raised exception {endpoint_name}: {exc}")

        # Delete indexes
        if indexes:
            logger.info(f"🗑️ Deleting {total_indexes} Vector Search index(es)...")
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all index deletion tasks
                future_to_index = {
                    executor.submit(delete_single_index, index.resource_name): index.resource_name
                    for index in indexes
                }
                
                # Wait for all deletions to complete
                for future in as_completed(future_to_index):
                    index_name = future_to_index[future]
                    try:
                        if future.result():
                            deleted_indexes += 1
                            logger.info(f"✅ Index deletion completed: {index_name}")
                        else:
                            logger.error(f"❌ Index deletion failed: {index_name}")
                    except Exception as exc:
                        logger.error(f"❌ Index deletion raised exception {index_name}: {exc}")

        logger.info(
            f"🎉 Deleted {deleted_indexes}/{total_indexes} index(es) and {deleted_endpoints}/{total_endpoints} endpoint(s) in {project_id}"
        )
        return deleted_indexes, total_indexes, deleted_endpoints, total_endpoints

    except Exception as e:
        logger.error(f"❌ Error processing project {project_id}: {e}")
        return 0, 0, 0, 0


def main():
    """Main function to delete Vector Search resources from all specified projects."""
    logger.info("🚀 Starting Vector Search cleanup across multiple projects...")

    try:
        project_ids = get_project_ids()
        logger.info(f"🎯 Target projects: {', '.join(project_ids)}")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

    total_deleted_indexes = 0
    total_found_indexes = 0
    total_deleted_endpoints = 0
    total_found_endpoints = 0
    failed_projects = []

    for project_id in project_ids:
        try:
            deleted_indexes, found_indexes, deleted_endpoints, found_endpoints = delete_vector_search_resources_in_project(project_id)
            total_deleted_indexes += deleted_indexes
            total_found_indexes += found_indexes
            total_deleted_endpoints += deleted_endpoints
            total_found_endpoints += found_endpoints
        except Exception as e:
            logger.error(f"❌ Failed to process project {project_id}: {e}")
            failed_projects.append(project_id)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"🎯 Total Vector Search indexes found: {total_found_indexes}")
    logger.info(f"✅ Total Vector Search indexes deleted: {total_deleted_indexes}")
    logger.info(f"🎯 Total Vector Search endpoints found: {total_found_endpoints}")
    logger.info(f"✅ Total Vector Search endpoints deleted: {total_deleted_endpoints}")
    logger.info(f"❌ Failed index deletions: {total_found_indexes - total_deleted_indexes}")
    logger.info(f"❌ Failed endpoint deletions: {total_found_endpoints - total_deleted_endpoints}")
    logger.info(
        f"📁 Projects processed: {len(project_ids) - len(failed_projects)}/{len(project_ids)}"
    )

    if failed_projects:
        logger.warning(f"⚠️ Failed to process projects: {', '.join(failed_projects)}")
        sys.exit(1)
    elif (total_found_indexes > total_deleted_indexes) or (total_found_endpoints > total_deleted_endpoints):
        logger.warning(
            f"⚠️ Some Vector Search resources could not be deleted"
        )
        sys.exit(1)
    else:
        logger.info("🎉 All projects processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()