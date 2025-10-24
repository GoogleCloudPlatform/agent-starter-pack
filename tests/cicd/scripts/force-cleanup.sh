#!/bin/bash

# Force cleanup script for all test resources
# This script deletes Agent Engines, AlloyDB clusters, Service Accounts, and Vector Search resources

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting comprehensive cleanup...${NC}"

# Project configuration
export PROJECT_IDS="agent-starter-pack-e2e-dev,agent-starter-pack-e2e-st,agent-starter-pack-e2e-pr,asp-starter-dev,asp-starter-prod,asp-starter-staging"
export E2E_PROJECT_IDS="agent-starter-pack-e2e-dev,agent-starter-pack-e2e-st,agent-starter-pack-e2e-pr,asp-starter-dev,asp-starter-prod,asp-starter-staging"
export CICD_PROJECT_ID="agent-starter-pack-e2e-dev"

echo -e "${YELLOW}📋 Target projects: ${PROJECT_IDS}${NC}"
echo ""

# Function to run cleanup with retry
run_with_retry() {
    local script_name=$1
    local description=$2
    local max_attempts=5
    local attempt=1

    echo -e "${GREEN}▶ ${description}${NC}"

    while [ $attempt -le $max_attempts ]; do
        echo -e "${YELLOW}  Attempt ${attempt}/${max_attempts}...${NC}"

        if uv run --with google-cloud-alloydb --with google-api-python-client python "tests/cicd/scripts/${script_name}" 2>&1; then
            echo -e "${GREEN}  ✅ Completed successfully${NC}"
            echo ""
            return 0
        else
            exit_code=$?
            echo -e "${RED}  ⚠️  Attempt ${attempt} failed (exit code: ${exit_code})${NC}"

            if [ $attempt -lt $max_attempts ]; then
                # Exponential backoff: 60s, 120s, 180s, 240s
                wait_time=$((60 * attempt))
                echo -e "${YELLOW}  ⏱️  Waiting ${wait_time} seconds before retry (rate limit cooldown)...${NC}"
                sleep $wait_time
            fi

            attempt=$((attempt + 1))
        fi
    done

    echo -e "${RED}  ❌ Failed after ${max_attempts} attempts${NC}"
    echo ""
    return 1
}

# Cleanup operations in sequence
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  CLEANUP SEQUENCE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""

# 1. Delete Agent Engines (most likely to hit rate limits)
run_with_retry "delete_agent_engines.py" "1/4 Deleting Agent Engines"

# 2. Delete Vector Search resources
run_with_retry "delete_vector_search.py" "2/4 Deleting Vector Search resources"

# 3. Delete AlloyDB clusters
run_with_retry "delete_alloydb_clusters.py" "3/4 Deleting AlloyDB clusters"

# 4. Delete Service Accounts
run_with_retry "delete_service_accounts.py" "4/4 Deleting Service Accounts"

echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ CLEANUP COMPLETE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
