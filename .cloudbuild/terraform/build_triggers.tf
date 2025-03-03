# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Define local variables for reuse
locals {
  repository_path = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"
  
  common_included_files = [
    "agents/**",
    "src/cli/**",
    "tests/**",
    "src/data_ingestion/**",
    "src/frontends/streamlit/**",
    "pyproject.toml",
    "uv.lock",
    ".cloudbuild/**",
  ]
  
  lint_templated_agents_included_files = [
    "src/cli/**",
    "src/base_template/**",
    "src/data_ingestion/**",
    "src/deployment_targets/**",
    "tests/integration/test_template_linting.py",
    "tests/integration/test_templated_patterns.py",
    "src/resources/locks/**",
    "pyproject.toml",
    "uv.lock",
    ".cloudbuild/**",
  ]
}

# a. Create PR Tests checks trigger
resource "google_cloudbuild_trigger" "pr_tests" {
  name            = "pr-tests"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename       = ".cloudbuild/ci/test.yaml"
  included_files = local.common_included_files
}

# b. Create Lint trigger
resource "google_cloudbuild_trigger" "pr_lint" {
  name            = "pr-lint"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename       = ".cloudbuild/ci/lint.yaml"
  included_files = local.common_included_files
}
# Define a local variable for agent/deployment combinations
locals {
  agent_deployment_combinations = [
    "langgraph_base_react,agent_engine",
    "langgraph_base_react,cloud_run",
    "crewai_coding_crew,agent_engine",
    "crewai_coding_crew,cloud_run",
    "agentic_rag_vertexai_search,agent_engine",
    "agentic_rag_vertexai_search,cloud_run",
    "multimodal_live_api,cloud_run",
  ]
  
  templated_agent_included_files = { for combo in local.agent_deployment_combinations:
    combo => [
      # Only include files for the specific agent being tested
      "agents/${split(",", combo)[0]}/**",
      # Common files that affect all agents
      "src/cli/**",
      "src/base_template/**",
      "src/data_ingestion/**",
      "src/deployment_targets/**",
      "tests/integration/test_template_linting.py",
      "tests/integration/test_templated_patterns.py",
      "src/resources/locks/**",
      "pyproject.toml",
      "uv.lock",
      ".cloudbuild/**",
    ]
  }
}

# c. Create Templated Agents Lint trigger for PRs - one for each agent/deployment combination:
resource "google_cloudbuild_trigger" "pr_templated_agents_lint" {
  for_each = toset(local.agent_deployment_combinations)
  
  name            = "lint-${replace(replace(each.key, ",", "-"), "_", "-")}"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR lint checks on templated agents: ${each.key}"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename       = ".cloudbuild/ci/lint_templated_agents.yaml"
  included_files = local.templated_agent_included_files[each.key]
  
  substitutions = {
    _TEST_AGENT_COMBINATION = each.key
  }
}

# d. Create Templated Agents Integration Test triggers for PRs - one for each agent/deployment combination
resource "google_cloudbuild_trigger" "pr_templated_agents_test" {
  for_each = toset(local.agent_deployment_combinations)
  
  name            = "test-${replace(replace(each.key, ",", "-"), "_", "-")}"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks on templated agents tests: ${each.key}"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename       = ".cloudbuild/ci/test_templated_agents.yaml"
  included_files = local.templated_agent_included_files[each.key]
  
  substitutions = {
    _TEST_AGENT_COMBINATION = each.key
  }
}
