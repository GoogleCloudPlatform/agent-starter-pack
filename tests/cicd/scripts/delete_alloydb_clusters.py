#!/usr/bin/env python3

# mypy: ignore-errors
"""
Script to force delete all AlloyDB clusters and instances from specified projects.

This script deletes all AlloyDB clusters and their instances from projects specified via environment variables.

Environment Variables:
- PROJECT_IDS: Comma-separated list of project IDs (e.g., "proj1,proj2,proj3")
- Alternative: Individual variables CICD_PROJECT_ID, E2E_PR_PROJECT_ID, E2E_ST_PROJECT_ID

Example usage:
    export PROJECT_IDS="my-project-1,my-project-2,my-project-3"
    python delete_alloydb_clusters.py
"""

import logging
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.api_core import exceptions
from google.cloud import alloydb_v1

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


def delete_single_instance(client, instance_name: str, retry_count: int = 0) -> bool:
    """
    Delete a single AlloyDB instance with retry logic and force deletion.

    Args:
        client: The AlloyDB client
        instance_name: Full resource name of the instance
        retry_count: Current retry attempt number

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        logger.info(f"🗑️ Deleting AlloyDB instance: {instance_name}")

        # Create delete request
        request = alloydb_v1.DeleteInstanceRequest(
            name=instance_name,
            request_id=str(uuid.uuid4())
        )

        operation = client.delete_instance(request=request)
        
        if wait_for_operation(operation):
            logger.info(f"✅ Successfully deleted AlloyDB instance: {instance_name}")
            return True
        else:
            logger.error(f"❌ Failed to delete AlloyDB instance: {instance_name}")
            return False

    except exceptions.TooManyRequests as e:
        # Handle rate limiting
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Rate limit hit for {instance_name}, waiting {RATE_LIMIT_DELAY} seconds before retry {retry_count + 1}/{MAX_RETRIES}..."
            )
            time.sleep(RATE_LIMIT_DELAY)
            return delete_single_instance(client, instance_name, retry_count + 1)
        else:
            logger.error(f"❌ Rate limit exceeded max retries for {instance_name}: {e}")
            return False

    except exceptions.NotFound:
        logger.info(f"✅ AlloyDB instance {instance_name} not found (already deleted)")
        return True

    except Exception as e:
        # Handle other errors with retry logic
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Error deleting {instance_name}, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_instance(client, instance_name, retry_count + 1)
        else:
            logger.error(
                f"❌ Failed to delete {instance_name} after {MAX_RETRIES} retries: {e}"
            )
            return False


def delete_single_cluster(client, cluster_name: str, retry_count: int = 0) -> bool:
    """
    Delete a single AlloyDB cluster with retry logic and force deletion.

    Args:
        client: The AlloyDB client
        cluster_name: Full resource name of the cluster
        retry_count: Current retry attempt number

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        logger.info(f"🗑️ Deleting AlloyDB cluster: {cluster_name}")

        # Create delete request
        request = alloydb_v1.DeleteClusterRequest(
            name=cluster_name,
            request_id=str(uuid.uuid4()),
            force=True  # Force delete even if cluster has instances
        )

        operation = client.delete_cluster(request=request)
        
        if wait_for_operation(operation):
            logger.info(f"✅ Successfully deleted AlloyDB cluster: {cluster_name}")
            return True
        else:
            logger.error(f"❌ Failed to delete AlloyDB cluster: {cluster_name}")
            return False

    except exceptions.TooManyRequests as e:
        # Handle rate limiting
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Rate limit hit for {cluster_name}, waiting {RATE_LIMIT_DELAY} seconds before retry {retry_count + 1}/{MAX_RETRIES}..."
            )
            time.sleep(RATE_LIMIT_DELAY)
            return delete_single_cluster(client, cluster_name, retry_count + 1)
        else:
            logger.error(f"❌ Rate limit exceeded max retries for {cluster_name}: {e}")
            return False

    except exceptions.NotFound:
        logger.info(f"✅ AlloyDB cluster {cluster_name} not found (already deleted)")
        return True

    except Exception as e:
        # Handle other errors with retry logic
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Error deleting {cluster_name}, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_cluster(client, cluster_name, retry_count + 1)
        else:
            logger.error(
                f"❌ Failed to delete {cluster_name} after {MAX_RETRIES} retries: {e}"
            )
            return False


def delete_alloydb_resources_in_project(
    project_id: str, region: str = DEFAULT_REGION
) -> tuple[int, int, int, int]:
    """
    Delete all AlloyDB clusters and instances in a specific project.

    Args:
        project_id: The GCP project ID
        region: The GCP region (default: europe-west1)

    Returns:
        Tuple of (deleted_instances, total_instances, deleted_clusters, total_clusters)
    """
    logger.info(f"🔍 Checking for AlloyDB resources in project {project_id}...")

    try:
        # Initialize AlloyDB client
        client = alloydb_v1.AlloyDBAdminClient()
        parent = f"projects/{project_id}/locations/{region}"

        # List all clusters in the project
        logger.info(f"📋 Listing all AlloyDB clusters in {project_id}...")
        clusters = list(client.list_clusters(parent=parent))

        if not clusters:
            logger.info(f"✅ No AlloyDB clusters found in {project_id}")
            return 0, 0, 0, 0

        logger.info(f"🎯 Found {len(clusters)} AlloyDB cluster(s) in {project_id}")

        total_instances = 0
        deleted_instances = 0
        deleted_clusters = 0

        def process_cluster(cluster):
            """Process a single cluster and its instances."""
            cluster_name = cluster.name
            logger.info(f"📋 Processing cluster: {cluster_name}")
            
            cluster_deleted_instances = 0
            cluster_total_instances = 0
            cluster_deleted_clusters = 0

            # List and delete instances in this cluster
            try:
                instances = list(client.list_instances(parent=cluster_name))
                cluster_total_instances = len(instances)
                
                if instances:
                    logger.info(f"🎯 Found {len(instances)} instance(s) in cluster {cluster_name}")
                    
                    # Delete instances in parallel
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        # Submit all instance deletion tasks
                        future_to_instance = {
                            executor.submit(delete_single_instance, client, instance.name): instance.name
                            for instance in instances
                        }
                        
                        # Wait for all deletions to complete
                        for future in as_completed(future_to_instance):
                            instance_name = future_to_instance[future]
                            try:
                                if future.result():
                                    cluster_deleted_instances += 1
                                    logger.info(f"✅ Instance deletion completed: {instance_name}")
                                else:
                                    logger.error(f"❌ Instance deletion failed: {instance_name}")
                            except Exception as exc:
                                logger.error(f"❌ Instance deletion raised exception {instance_name}: {exc}")
                else:
                    logger.info(f"✅ No instances found in cluster {cluster_name}")

            except Exception as e:
                logger.error(f"❌ Error processing instances in cluster {cluster_name}: {e}")

            # Delete the cluster itself (force=True will delete any remaining instances)
            if delete_single_cluster(client, cluster_name):
                cluster_deleted_clusters = 1

            return cluster_deleted_instances, cluster_total_instances, cluster_deleted_clusters

        # Process all clusters in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all cluster processing tasks
            future_to_cluster = {
                executor.submit(process_cluster, cluster): cluster.name
                for cluster in clusters
            }
            
            # Wait for all cluster processing to complete
            for future in as_completed(future_to_cluster):
                cluster_name = future_to_cluster[future]
                try:
                    cluster_deleted_instances, cluster_total_instances, cluster_deleted_clusters = future.result()
                    deleted_instances += cluster_deleted_instances
                    total_instances += cluster_total_instances
                    deleted_clusters += cluster_deleted_clusters
                    logger.info(f"✅ Cluster processing completed: {cluster_name}")
                except Exception as exc:
                    logger.error(f"❌ Cluster processing raised exception {cluster_name}: {exc}")

        logger.info(
            f"🎉 Deleted {deleted_instances}/{total_instances} instance(s) and {deleted_clusters}/{len(clusters)} cluster(s) in {project_id}"
        )
        return deleted_instances, total_instances, deleted_clusters, len(clusters)

    except Exception as e:
        logger.error(f"❌ Error processing project {project_id}: {e}")
        return 0, 0, 0, 0


def main():
    """Main function to delete AlloyDB resources from all specified projects."""
    logger.info("🚀 Starting AlloyDB cleanup across multiple projects...")

    try:
        project_ids = get_project_ids()
        logger.info(f"🎯 Target projects: {', '.join(project_ids)}")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

    total_deleted_instances = 0
    total_found_instances = 0
    total_deleted_clusters = 0
    total_found_clusters = 0
    failed_projects = []

    for project_id in project_ids:
        try:
            deleted_instances, found_instances, deleted_clusters, found_clusters = delete_alloydb_resources_in_project(project_id)
            total_deleted_instances += deleted_instances
            total_found_instances += found_instances
            total_deleted_clusters += deleted_clusters
            total_found_clusters += found_clusters
        except Exception as e:
            logger.error(f"❌ Failed to process project {project_id}: {e}")
            failed_projects.append(project_id)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"🎯 Total AlloyDB instances found: {total_found_instances}")
    logger.info(f"✅ Total AlloyDB instances deleted: {total_deleted_instances}")
    logger.info(f"🎯 Total AlloyDB clusters found: {total_found_clusters}")
    logger.info(f"✅ Total AlloyDB clusters deleted: {total_deleted_clusters}")
    logger.info(f"❌ Failed instance deletions: {total_found_instances - total_deleted_instances}")
    logger.info(f"❌ Failed cluster deletions: {total_found_clusters - total_deleted_clusters}")
    logger.info(
        f"📁 Projects processed: {len(project_ids) - len(failed_projects)}/{len(project_ids)}"
    )

    if failed_projects:
        logger.warning(f"⚠️ Failed to process projects: {', '.join(failed_projects)}")
        sys.exit(1)
    elif (total_found_instances > total_deleted_instances) or (total_found_clusters > total_deleted_clusters):
        logger.warning(
            f"⚠️ Some AlloyDB resources could not be deleted"
        )
        sys.exit(1)
    else:
        logger.info("🎉 All projects processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()