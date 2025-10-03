cicd_runner_project_id = "agent-starter-pack-cicd"

region = "europe-west4"

host_connection_name = "git-connection"

repository_name = "GoogleCloudPlatform-agent-starter-pack"

e2e_test_project_mapping = {
  dev     = "agent-starter-pack-e2e-dev"
  staging = "agent-starter-pack-e2e-st"
  prod    = "agent-starter-pack-e2e-pr"
}
