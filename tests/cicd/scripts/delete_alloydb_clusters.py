#!/usr/bin/env python3

# mypy: ignore-errors
"""
Script to force delete all AlloyDB clusters, instances, and related network resources from specified projects.

This script deletes all AlloyDB clusters, their instances, and associated network resources 
(VPC networks, subnets, and peering connections) from projects specified via environment variables.

Environment Variables:
- PROJECT_IDS: Comma-separated list of project IDs (e.g., "proj1,proj2,proj3")
- Alternative: Individual variables CICD_PROJECT_ID, E2E_PR_PROJECT_ID, E2E_ST_PROJECT_ID

Example usage:
    export PROJECT_IDS="my-project-1,my-project-2,my-project-3"
    python delete_alloydb_clusters.py
"""

import logging
import os
import ssl
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.api_core import exceptions
from google.cloud import alloydb_v1
from googleapiclient import discovery
import subprocess

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


def delete_vpc_peering_connections(compute_client, project_id: str, retry_count: int = 0) -> tuple[int, int]:
    """
    Delete all VPC peering connections in a project.
    
    Args:
        compute_client: The Compute client
        project_id: The GCP project ID
        retry_count: Current retry attempt number
        
    Returns:
        Tuple of (deleted_peerings, total_peerings)
    """
    try:
        logger.info(f"🔍 Listing VPC peering connections in project {project_id}...")
        
        # List all networks first to find peering connections
        request = compute_client.networks().list(project=project_id)
        response = request.execute()
        networks = response.get('items', [])
        
        total_peerings = 0
        deleted_peerings = 0
        
        for network in networks:
            network_name = network['name']
            peerings = network.get('peerings', [])
            
            if peerings:
                logger.info(f"🎯 Found {len(peerings)} peering connection(s) in network {network_name}")
                total_peerings += len(peerings)
                
                for peering in peerings:
                    peering_name = peering['name']
                    try:
                        logger.info(f"🗑️ Deleting VPC peering: {peering_name} in network {network_name}")
                        
                        operation = compute_client.networks().removePeering(
                            project=project_id,
                            network=network_name,
                            body={'name': peering_name}
                        ).execute()
                        
                        # Wait for operation to complete
                        if wait_for_compute_operation(compute_client, project_id, operation):
                            logger.info(f"✅ Successfully deleted VPC peering: {peering_name}")
                            deleted_peerings += 1
                        else:
                            logger.error(f"❌ Failed to delete VPC peering: {peering_name}")
                            
                    except exceptions.NotFound:
                        logger.info(f"✅ VPC peering {peering_name} not found (already deleted)")
                        deleted_peerings += 1
                    except Exception as e:
                        logger.error(f"❌ Error deleting VPC peering {peering_name}: {e}")
        
        if total_peerings == 0:
            logger.info(f"✅ No VPC peering connections found in {project_id}")
            
        return deleted_peerings, total_peerings
        
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"⏱️ Error listing VPC peerings, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return delete_vpc_peering_connections(compute_client, project_id, retry_count + 1)
        else:
            logger.error(f"❌ Failed to delete VPC peerings after {MAX_RETRIES} retries: {e}")
            return 0, 0


def delete_single_subnet(compute_client, project_id: str, subnet: dict, region: str, retry_count: int = 0) -> bool:
    """
    Delete a single subnet with error handling and retry logic.
    
    Args:
        compute_client: The Compute client
        project_id: The GCP project ID
        subnet: The subnet resource
        region: The region of the subnet
        retry_count: Current retry attempt number
        
    Returns:
        True if deleted successfully, False otherwise
    """
    subnet_name = subnet['name']
    try:
        logger.info(f"🗑️ Deleting subnet: {subnet_name} in region {region}")
        
        operation = compute_client.subnetworks().delete(
            project=project_id,
            region=region,
            subnetwork=subnet_name
        ).execute()
        
        # Wait for operation to complete
        if wait_for_compute_operation(compute_client, project_id, operation, region=region):
            logger.info(f"✅ Successfully deleted subnet: {subnet_name}")
            return True
        else:
            logger.error(f"❌ Failed to delete subnet: {subnet_name}")
            return False
            
    except exceptions.NotFound:
        logger.info(f"✅ Subnet {subnet_name} not found (already deleted)")
        return True
    except (ssl.SSLError, ConnectionError, OSError) as e:
        # Handle SSL and connection errors with retry logic
        if retry_count < MAX_RETRIES:
            logger.warning(
                f"⏱️ Network error deleting {subnet_name}, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES}): {e}"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_subnet(compute_client, project_id, subnet, region, retry_count + 1)
        else:
            logger.error(f"❌ Failed to delete {subnet_name} after {MAX_RETRIES} retries due to network errors: {e}")
            return False
    except Exception as e:
        # Handle other errors with retry logic
        if retry_count < MAX_RETRIES and ("IncompleteRead" in str(e) or "SSL" in str(e) or "Connection" in str(e)):
            logger.warning(
                f"⏱️ Network-related error deleting {subnet_name}, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES}): {e}"
            )
            time.sleep(RETRY_DELAY)
            return delete_single_subnet(compute_client, project_id, subnet, region, retry_count + 1)
        elif "resourceInUseByAnotherResource" in str(e) and "serverless" in str(e).lower():
            logger.warning(f"⚠️ Skipping subnet {subnet_name} - in use by serverless service (requires manual cleanup)")
            return False
        else:
            logger.error(f"❌ Error deleting subnet {subnet_name}: {e}")
            return False


def delete_cloud_run_services(project_id: str, region: str = DEFAULT_REGION) -> tuple[int, int]:
    """
    Delete all Cloud Run services in a project and region using gcloud CLI.
    
    Args:
        project_id: The GCP project ID
        region: The GCP region
        
    Returns:
        Tuple of (deleted_services, total_services)
    """
    try:
        logger.info(f"🔍 Listing Cloud Run services in project {project_id}, region {region}...")
        
        # List all Cloud Run services using gcloud CLI
        list_cmd = [
            "gcloud", "run", "services", "list",
            f"--project={project_id}",
            f"--region={region}",
            "--format=value(metadata.name)"
        ]
        
        result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"❌ Failed to list Cloud Run services: {result.stderr}")
            return 0, 0
        
        services = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
        
        if not services:
            logger.info(f"✅ No Cloud Run services found in {project_id}")
            return 0, 0
            
        logger.info(f"🎯 Found {len(services)} Cloud Run service(s) in {project_id}")
        total_services = len(services)
        deleted_services = 0
        
        for service_name in services:
            try:
                logger.info(f"🗑️ Deleting Cloud Run service: {service_name}")
                
                delete_cmd = [
                    "gcloud", "run", "services", "delete", service_name,
                    f"--project={project_id}",
                    f"--region={region}",
                    "--quiet"
                ]
                
                result = subprocess.run(delete_cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    logger.info(f"✅ Successfully deleted Cloud Run service: {service_name}")
                    deleted_services += 1
                else:
                    logger.error(f"❌ Failed to delete Cloud Run service {service_name}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"❌ Timeout deleting Cloud Run service: {service_name}")
            except Exception as e:
                logger.error(f"❌ Error deleting Cloud Run service {service_name}: {e}")
        
        return deleted_services, total_services
        
    except Exception as e:
        logger.error(f"❌ Failed to delete Cloud Run services: {e}")
        return 0, 0


def delete_reserved_addresses(compute_client, project_id: str) -> tuple[int, int]:
    """
    Delete all reserved IP addresses in a project.
    
    Args:
        compute_client: The Compute client
        project_id: The GCP project ID
        
    Returns:
        Tuple of (deleted_addresses, total_addresses)
    """
    try:
        logger.info(f"🔍 Listing reserved IP addresses in project {project_id}...")
        
        # List all addresses across all regions
        request = compute_client.addresses().aggregatedList(project=project_id)
        response = request.execute()
        
        all_addresses = []
        for zone, zone_data in response.get('items', {}).items():
            if 'addresses' in zone_data:
                for address in zone_data['addresses']:
                    # Extract region from zone (e.g., "regions/us-central1" -> "us-central1")
                    region = zone.split('/')[-1] if '/' in zone else zone.replace('regions/', '')
                    all_addresses.append((address, region))
        
        if not all_addresses:
            logger.info(f"✅ No reserved IP addresses found in {project_id}")
            return 0, 0
            
        logger.info(f"🎯 Found {len(all_addresses)} reserved IP address(es) in {project_id}")
        total_addresses = len(all_addresses)
        deleted_addresses = 0
        
        for address, region in all_addresses:
            address_name = address['name']
            try:
                logger.info(f"🗑️ Deleting reserved IP address: {address_name} in region {region}")
                
                if region == 'global':
                    # Use global operations for global addresses
                    operation = compute_client.globalAddresses().delete(
                        project=project_id,
                        address=address_name
                    ).execute()
                    success = wait_for_compute_operation(compute_client, project_id, operation)
                else:
                    # Use regional operations for regional addresses
                    operation = compute_client.addresses().delete(
                        project=project_id,
                        region=region,
                        address=address_name
                    ).execute()
                    success = wait_for_compute_operation(compute_client, project_id, operation, region=region)
                
                if success:
                    logger.info(f"✅ Successfully deleted reserved IP address: {address_name}")
                    deleted_addresses += 1
                else:
                    logger.error(f"❌ Failed to delete reserved IP address: {address_name}")
                    
            except exceptions.NotFound:
                logger.info(f"✅ Reserved IP address {address_name} not found (already deleted)")
                deleted_addresses += 1
            except Exception as e:
                if "resourceInUseByAnotherResource" in str(e) and "serverless" in str(e).lower():
                    logger.warning(f"⚠️ Skipping address {address_name} - in use by serverless service (will retry after service cleanup)")
                else:
                    logger.error(f"❌ Error deleting reserved IP address {address_name}: {e}")
        
        return deleted_addresses, total_addresses
        
    except Exception as e:
        logger.error(f"❌ Failed to delete reserved IP addresses: {e}")
        return 0, 0


def delete_subnets(compute_client, project_id: str, retry_count: int = 0) -> tuple[int, int]:
    """
    Delete all subnets in a project in parallel.
    
    Args:
        compute_client: The Compute client
        project_id: The GCP project ID
        retry_count: Current retry attempt number
        
    Returns:
        Tuple of (deleted_subnets, total_subnets)
    """
    try:
        logger.info(f"🔍 Listing subnets in project {project_id}...")
        
        # List all subnets across all regions
        request = compute_client.subnetworks().aggregatedList(project=project_id)
        response = request.execute()
        
        all_subnets = []
        for zone, zone_data in response.get('items', {}).items():
            if 'subnetworks' in zone_data:
                for subnet in zone_data['subnetworks']:
                    # Extract region from zone (e.g., "regions/us-central1" -> "us-central1")
                    region = zone.split('/')[-1] if '/' in zone else zone.replace('regions/', '')
                    all_subnets.append((subnet, region))
        
        if not all_subnets:
            logger.info(f"✅ No subnets found in {project_id}")
            return 0, 0
            
        logger.info(f"🎯 Found {len(all_subnets)} subnet(s) in {project_id}")
        total_subnets = len(all_subnets)
        deleted_subnets = 0
        
        # Delete subnets in parallel with reduced concurrency to avoid network issues
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit all subnet deletion tasks
            future_to_subnet = {
                executor.submit(delete_single_subnet, compute_client, project_id, subnet, region): (subnet['name'], region)
                for subnet, region in all_subnets
            }
            
            # Wait for all deletions to complete
            for future in as_completed(future_to_subnet):
                subnet_name, region = future_to_subnet[future]
                try:
                    if future.result():
                        deleted_subnets += 1
                        logger.info(f"✅ Subnet deletion completed: {subnet_name} in {region}")
                    else:
                        logger.error(f"❌ Subnet deletion failed: {subnet_name} in {region}")
                except Exception as exc:
                    logger.error(f"❌ Subnet deletion raised exception {subnet_name} in {region}: {exc}")
        
        return deleted_subnets, total_subnets
        
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"⏱️ Error listing subnets, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return delete_subnets(compute_client, project_id, retry_count + 1)
        else:
            logger.error(f"❌ Failed to delete subnets after {MAX_RETRIES} retries: {e}")
            return 0, 0


def delete_vpc_networks(compute_client, project_id: str, retry_count: int = 0) -> tuple[int, int]:
    """
    Delete all VPC networks in a project (excluding default network).
    
    Args:
        compute_client: The Compute client
        project_id: The GCP project ID
        retry_count: Current retry attempt number
        
    Returns:
        Tuple of (deleted_networks, total_networks)
    """
    try:
        logger.info(f"🔍 Listing VPC networks in project {project_id}...")
        
        request = compute_client.networks().list(project=project_id)
        response = request.execute()
        networks = response.get('items', [])
        
        # Filter out default network (usually shouldn't be deleted)
        custom_networks = [net for net in networks if net['name'] != 'default']
        
        if not custom_networks:
            logger.info(f"✅ No custom VPC networks found in {project_id}")
            return 0, 0
            
        logger.info(f"🎯 Found {len(custom_networks)} custom VPC network(s) in {project_id}")
        total_networks = len(custom_networks)
        deleted_networks = 0
        
        for network in custom_networks:
            network_name = network['name']
            try:
                logger.info(f"🗑️ Deleting VPC network: {network_name}")
                
                operation = compute_client.networks().delete(
                    project=project_id,
                    network=network_name
                ).execute()
                
                # Wait for operation to complete
                if wait_for_compute_operation(compute_client, project_id, operation):
                    logger.info(f"✅ Successfully deleted VPC network: {network_name}")
                    deleted_networks += 1
                else:
                    logger.error(f"❌ Failed to delete VPC network: {network_name}")
                    
            except exceptions.NotFound:
                logger.info(f"✅ VPC network {network_name} not found (already deleted)")
                deleted_networks += 1
            except Exception as e:
                logger.error(f"❌ Error deleting VPC network {network_name}: {e}")
        
        return deleted_networks, total_networks
        
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"⏱️ Error listing VPC networks, retrying in {RETRY_DELAY} seconds... (attempt {retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return delete_vpc_networks(compute_client, project_id, retry_count + 1)
        else:
            logger.error(f"❌ Failed to delete VPC networks after {MAX_RETRIES} retries: {e}")
            return 0, 0


def wait_for_compute_operation(compute_client, project_id: str, operation: dict, region: str = None, timeout: int = OPERATION_TIMEOUT) -> bool:
    """
    Wait for a Compute Engine operation to complete.
    
    Args:
        compute_client: The Compute client
        project_id: The GCP project ID
        operation: The operation to wait for
        region: The region for regional operations (None for global operations)
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if operation completed successfully, False otherwise
    """
    operation_name = operation['name']
    logger.info(f"⏳ Waiting for compute operation {operation_name} to complete...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if region:
                # Regional operation
                result = compute_client.regionOperations().get(
                    project=project_id,
                    region=region,
                    operation=operation_name
                ).execute()
            else:
                # Global operation
                result = compute_client.globalOperations().get(
                    project=project_id,
                    operation=operation_name
                ).execute()
            
            if result['status'] == 'DONE':
                if 'error' in result:
                    logger.error(f"❌ Compute operation failed: {result['error']}")
                    return False
                else:
                    logger.info(f"✅ Compute operation {operation_name} completed successfully")
                    return True
            
            time.sleep(5)  # Wait 5 seconds before checking again
            
        except Exception as e:
            logger.error(f"❌ Error checking compute operation status: {e}")
            return False
    
    logger.error(f"❌ Compute operation {operation_name} timed out after {timeout} seconds")
    return False


def delete_alloydb_and_network_resources_in_project(
    project_id: str, region: str = DEFAULT_REGION
) -> tuple[int, int, int, int, int, int, int, int]:
    """
    Delete all AlloyDB clusters, instances, and network resources in a specific project.

    Args:
        project_id: The GCP project ID
        region: The GCP region (default: europe-west1)

    Returns:
        Tuple of (deleted_instances, total_instances, deleted_clusters, total_clusters, 
                 deleted_peerings, total_peerings, deleted_subnets, total_subnets, 
                 deleted_networks, total_networks)
    """
    logger.info(f"🔍 Checking for AlloyDB and network resources in project {project_id}...")

    try:
        # Initialize clients
        alloydb_client = alloydb_v1.AlloyDBAdminClient()
        compute_client = discovery.build('compute', 'v1')
        parent = f"projects/{project_id}/locations/{region}"

        # List all clusters in the project
        logger.info(f"📋 Listing all AlloyDB clusters in {project_id}...")
        clusters = list(alloydb_client.list_clusters(parent=parent))

        if not clusters:
            logger.info(f"✅ No AlloyDB clusters found in {project_id}")
            # Still need to clean up network resources even if no AlloyDB clusters
            
            # First delete Cloud Run services as they may hold serverless address reservations
            deleted_services, total_services = delete_cloud_run_services(project_id, region)
            
            # Then delete reserved IP addresses as they may block subnet deletion
            deleted_addresses, total_addresses = delete_reserved_addresses(compute_client, project_id)
            
            # Run VPC peering and subnet deletion in parallel since they are independent
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both tasks
                peering_future = executor.submit(delete_vpc_peering_connections, compute_client, project_id)
                subnet_future = executor.submit(delete_subnets, compute_client, project_id)
                
                # Wait for both to complete
                deleted_peerings, total_peerings = peering_future.result()
                deleted_subnets, total_subnets = subnet_future.result()
            
            # Delete VPC networks after subnets are deleted (dependency requirement)
            deleted_networks, total_networks = delete_vpc_networks(compute_client, project_id)
            return 0, 0, 0, 0, deleted_peerings, total_peerings, deleted_subnets, total_subnets, deleted_networks, total_networks

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
                instances = list(alloydb_client.list_instances(parent=cluster_name))
                cluster_total_instances = len(instances)
                
                if instances:
                    logger.info(f"🎯 Found {len(instances)} instance(s) in cluster {cluster_name}")
                    
                    # Delete instances in parallel
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        # Submit all instance deletion tasks
                        future_to_instance = {
                            executor.submit(delete_single_instance, alloydb_client, instance.name): instance.name
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
            if delete_single_cluster(alloydb_client, cluster_name):
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
        
        # Delete network resources after AlloyDB cleanup
        logger.info(f"🌐 Starting network cleanup in project {project_id}...")
        
        # First delete Cloud Run services as they may hold serverless address reservations
        deleted_services, total_services = delete_cloud_run_services(project_id, region)
        
        # Then delete reserved IP addresses as they may block subnet deletion
        deleted_addresses, total_addresses = delete_reserved_addresses(compute_client, project_id)
        
        # Run VPC peering and subnet deletion in parallel since they are independent
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            peering_future = executor.submit(delete_vpc_peering_connections, compute_client, project_id)
            subnet_future = executor.submit(delete_subnets, compute_client, project_id)
            
            # Wait for both to complete
            deleted_peerings, total_peerings = peering_future.result()
            deleted_subnets, total_subnets = subnet_future.result()
        
        # Delete VPC networks after subnets are deleted (dependency requirement)
        deleted_networks, total_networks = delete_vpc_networks(compute_client, project_id)
        
        logger.info(
            f"🌐 Network cleanup completed: {deleted_peerings}/{total_peerings} peerings, "
            f"{deleted_subnets}/{total_subnets} subnets, {deleted_networks}/{total_networks} networks deleted"
        )
        
        return (deleted_instances, total_instances, deleted_clusters, len(clusters), 
                deleted_peerings, total_peerings, deleted_subnets, total_subnets, 
                deleted_networks, total_networks)

    except Exception as e:
        logger.error(f"❌ Error processing project {project_id}: {e}")
        return 0, 0, 0, 0, 0, 0, 0, 0, 0, 0


def main():
    """Main function to delete AlloyDB and network resources from all specified projects."""
    logger.info("🚀 Starting AlloyDB and network cleanup across multiple projects...")

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
    total_deleted_peerings = 0
    total_found_peerings = 0
    total_deleted_subnets = 0
    total_found_subnets = 0
    total_deleted_networks = 0
    total_found_networks = 0
    failed_projects = []

    for project_id in project_ids:
        try:
            (deleted_instances, found_instances, deleted_clusters, found_clusters,
             deleted_peerings, found_peerings, deleted_subnets, found_subnets,
             deleted_networks, found_networks) = delete_alloydb_and_network_resources_in_project(project_id)
            
            total_deleted_instances += deleted_instances
            total_found_instances += found_instances
            total_deleted_clusters += deleted_clusters
            total_found_clusters += found_clusters
            total_deleted_peerings += deleted_peerings
            total_found_peerings += found_peerings
            total_deleted_subnets += deleted_subnets
            total_found_subnets += found_subnets
            total_deleted_networks += deleted_networks
            total_found_networks += found_networks
        except Exception as e:
            logger.error(f"❌ Failed to process project {project_id}: {e}")
            failed_projects.append(project_id)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 CLEANUP SUMMARY")
    logger.info("=" * 80)
    logger.info("🔴 ALLOYDB RESOURCES:")
    logger.info(f"  🎯 Total AlloyDB instances found: {total_found_instances}")
    logger.info(f"  ✅ Total AlloyDB instances deleted: {total_deleted_instances}")
    logger.info(f"  🎯 Total AlloyDB clusters found: {total_found_clusters}")
    logger.info(f"  ✅ Total AlloyDB clusters deleted: {total_deleted_clusters}")
    logger.info(f"  ❌ Failed instance deletions: {total_found_instances - total_deleted_instances}")
    logger.info(f"  ❌ Failed cluster deletions: {total_found_clusters - total_deleted_clusters}")
    logger.info("")
    logger.info("🌐 NETWORK RESOURCES:")
    logger.info(f"  🎯 Total VPC peering connections found: {total_found_peerings}")
    logger.info(f"  ✅ Total VPC peering connections deleted: {total_deleted_peerings}")
    logger.info(f"  🎯 Total subnets found: {total_found_subnets}")
    logger.info(f"  ✅ Total subnets deleted: {total_deleted_subnets}")
    logger.info(f"  🎯 Total VPC networks found: {total_found_networks}")
    logger.info(f"  ✅ Total VPC networks deleted: {total_deleted_networks}")
    logger.info(f"  ❌ Failed peering deletions: {total_found_peerings - total_deleted_peerings}")
    logger.info(f"  ❌ Failed subnet deletions: {total_found_subnets - total_deleted_subnets}")
    logger.info(f"  ❌ Failed network deletions: {total_found_networks - total_deleted_networks}")
    logger.info("")
    logger.info(
        f"📁 Projects processed: {len(project_ids) - len(failed_projects)}/{len(project_ids)}"
    )

    if failed_projects:
        logger.warning(f"⚠️ Failed to process projects: {', '.join(failed_projects)}")
        sys.exit(1)
    elif ((total_found_instances > total_deleted_instances) or 
          (total_found_clusters > total_deleted_clusters) or
          (total_found_peerings > total_deleted_peerings) or
          (total_found_subnets > total_deleted_subnets) or
          (total_found_networks > total_deleted_networks)):
        logger.warning(
            f"⚠️ Some AlloyDB or network resources could not be deleted"
        )
        sys.exit(1)
    else:
        logger.info("🎉 All projects processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
