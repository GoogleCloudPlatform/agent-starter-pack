#!/bin/bash
set -e

# 1. Validate input
if [ -z "$1" ]; then
  read -p "Enter the project base name: " PROJECT_BASE_NAME
  if [ -z "$PROJECT_BASE_NAME" ]; then
      echo "Error: Project base name cannot be empty."
      exit 1
  fi
else
  PROJECT_BASE_NAME="$1"
fi

# 2. Validate project existence in GCP
echo "Checking for existing GCP projects..."
DEV_PROJECT_NAME="${PROJECT_BASE_NAME}-dev"
UAT_PROJECT_NAME="${PROJECT_BASE_NAME}-uat"
PROD_PROJECT_NAME="${PROJECT_BASE_NAME}-prod"

EXISTING_PROJECTS=$(gcloud projects list --filter="name=($DEV_PROJECT_NAME, $UAT_PROJECT_NAME, $PROD_PROJECT_NAME)" --format="value(projectId, name)")
if [ -n "$EXISTING_PROJECTS" ]; then
    echo "Warning: The following projects already exist:"
    echo "$EXISTING_PROJECTS"
    read -p "Do you want to continue (this may require importing existing resources into Terraform)? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting."
        exit 1
    fi
    echo "Continuing..."
else
    echo "No existing projects found. Proceeding..."
fi

# 3. Get GCP configuration
echo "Retrieving billing and organization information..."
CURRENT_PROJECT=$(gcloud config get-value project)
if [ -z "$CURRENT_PROJECT" ]; then
  echo "Error: No active GCP project configured. Please run 'gcloud config set project <your-project-id>'."
  exit 1
fi

BILLING_ACCOUNT_NAME=$(gcloud billing projects describe "$CURRENT_PROJECT" --format="value(billingAccountName)")
if [ -z "$BILLING_ACCOUNT_NAME" ] || [ "$BILLING_ACCOUNT_NAME" == "null" ]; then
  echo "Error: Could not determine billing account for project '$CURRENT_PROJECT'. Make sure the project is linked to a billing account."
  exit 1
fi
BILLING_ACCOUNT_ID=$(basename "$BILLING_ACCOUNT_NAME")

ORG_ID=$(gcloud projects get-ancestors "$CURRENT_PROJECT" --format='get(id)' | tail -n1)
if [ -z "$ORG_ID" ]; then
    echo "Error: Could not determine organization ID for project '$CURRENT_PROJECT'."
    exit 1
fi

echo "-> Billing Account ID: $BILLING_ACCOUNT_ID"
echo "-> Organization ID: $ORG_ID"

# 4. Run Terraform
echo "Initializing and applying Terraform..."
cd project

terraform init
terraform plan -out tf.plan

read -p "Do you want to proceed with the apply? (y/N) " -n 1 -r
echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Exiting."
      exit 1
  fi

echo "Applying..."
terraform apply -auto-approve \
  -var="project_base_name=${PROJECT_BASE_NAME}" \
  -var="billing_account=${BILLING_ACCOUNT_ID}" \
  -var="org_id=${ORG_ID}"

echo "Terraform apply complete."

# 5. Extract Project IDs and update .env file
echo "Extracting project IDs..."
DEV_PROJECT_ID=$(terraform output -raw dev_project_id)
UAT_PROJECT_ID=$(terraform output -raw uat_project_id)
PROD_PROJECT_ID=$(terraform output -raw prod_project_id)

# Go back to the setup directory to update the .env file
cd ..

ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo "Updating existing ${ENV_FILE} file..."
else
    echo "Creating new ${ENV_FILE} file..."
fi

# Use a temporary file to safely update the variables, preserving other content.
TMP_FILE=$(mktemp)

# If the original file exists, copy everything except the variables we're about to set.
if [ -f "$ENV_FILE" ]; then
    grep -v -e "^DEV_PROJECT_ID=" -e "^UAT_PROJECT_ID=" -e "^PROD_PROJECT_ID=" "$ENV_FILE" > "$TMP_FILE"
fi

# Append the new/updated variables.
echo "DEV_PROJECT_ID=${DEV_PROJECT_ID}" >> "$TMP_FILE"
echo "UAT_PROJECT_ID=${UAT_PROJECT_ID}" >> "$TMP_FILE"
echo "PROD_PROJECT_ID=${PROD_PROJECT_ID}" >> "$TMP_FILE"

# Atomically replace the old file with the new one.
mv "$TMP_FILE" "$ENV_FILE"

echo -e "
✅ Success! Project IDs have been saved to setup/.env"
echo "To use them in your current shell, run:"
echo "source setup/.env"
