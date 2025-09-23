# Project name used for resource naming
project_name = "example-agent"

# Your Production Google Cloud project id
prod_project_id = "your-production-project-id"

# Your Staging / Test Google Cloud project id
staging_project_id = "your-staging-project-id"

# Your Google Cloud project ID that will be used to host the Cloud Build pipelines.
cicd_runner_project_id = "your-cicd-project-id"
# Name of the host connection you created in Cloud Build
host_connection_name = "git-example-agent"
github_pat_secret_id = "your-github_pat_secret_id"

repository_owner = "Your GitHub organization or username."

# Name of the repository you added to Cloud Build
repository_name = "example-agent"

# The Google Cloud region you will use to deploy the infrastructure
region = "us-central1"
