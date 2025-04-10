# Project name used for resource naming
project_name = "lighthouse-auditor"

# Your Production Google Cloud project id
prod_project_id = "capstone-455820"

# Your Staging / Test Google Cloud project id
staging_project_id = "capstone-staging"

# Your Google Cloud project ID that will be used to host the Cloud Build pipelines.
cicd_runner_project_id = "capstone-455820"

# Name of the host connection you created in Cloud Build
host_connection_name = "git-lighthouse-auditor"

# Name of the repository you added to Cloud Build
repository_name = "lighthouse-auditor"

# The Google Cloud region you will use to deploy the infrastructure
region = "us-central1"

telemetry_logs_filter = "jsonPayload.attributes.\"traceloop.association.properties.log_type\"=\"tracing\" jsonPayload.resource.attributes.\"service.name\"=\"lighthouse-auditor\""

feedback_logs_filter = "jsonPayload.log_type=\"feedback\""
repository_owner = "westkevin12"
github_app_installation_id = "39943572"
github_pat_secret_id = "git-lighthouse-auditor-github-oauthtoken-8e55bc"
connection_exists = true
repository_exists = true
