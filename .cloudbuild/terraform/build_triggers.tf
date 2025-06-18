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

  # Define common ignored files
  common_ignored_files = [
    "**/*.md",
    "**/Makefile",
  ]

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

  # Define a local variable for agent/deployment combinations
  agent_testing_combinations = [
    {
      name  = "adk_base-agent_engine"
      value = "adk_base,agent_engine"
    },
    {
      name  = "adk_base-cloud_run"
      value = "adk_base,cloud_run"
    },
    {
      name  = "langgraph_base_react-agent_engine"
      value = "langgraph_base_react,agent_engine"
    },
    {
      name  = "langgraph_base_react-cloud_run"
      value = "langgraph_base_react,cloud_run"
    },
    {
      name  = "crewai_coding_crew-agent_engine"
      value = "crewai_coding_crew,agent_engine"
    },
    {
      name  = "crewai_coding_crew-cloud_run"
      value = "crewai_coding_crew,cloud_run"
    },
    {
      name = "agentic_rag-agent_engine-vertex_ai_search"
      value = "agentic_rag,agent_engine,--include-data-ingestion,--datastore,vertex_ai_search"
    },
    {
      name = "agentic_rag-cloud_run-vertex_ai_vector_search"
      value = "agentic_rag,cloud_run,--include-data-ingestion,--datastore,vertex_ai_vector_search"
    },
    {
      name  = "live_api-cloud_run"
      value = "live_api,cloud_run"
    },
    {
      name  = "adk_gemini_fullstack-agent_engine"
      value = "adk_gemini_fullstack,agent_engine"
    },
    {
      name  = "adk_gemini_fullstack-cloud_run"
      value = "adk_gemini_fullstack,cloud_run"
    },
  ]

  agent_testing_included_files = { for combo in local.agent_testing_combinations :
    combo.name => [
      # Only include files for the specific agent being tested
      "agents/${split(",", combo.value)[0]}/**",
      # Common files that affect all agents
      "src/cli/**",
      "src/base_template/**",
      "src/deployment_targets/**",
      "tests/integration/test_template_linting.py",
      "tests/integration/test_templated_patterns.py",
      "src/resources/locks/**",
      "pyproject.toml",
      "uv.lock",
    ]
  }
  e2e_agent_deployment_combinations = [
    {
      name  = "adk_base-agent_engine"
      value = "adk_base,agent_engine"
    },
    {
      name  = "adk_base-cloud_run"
      value = "adk_base,cloud_run"
    },
    {
      name = "langgraph_base_react-agent_engine"
      value = "langgraph_base_react,agent_engine"
    },
    {
      name = "agentic_rag-agent_engine-vertex_ai_search"
      value = "agentic_rag,agent_engine,--include-data-ingestion,--datastore,vertex_ai_search"
    },
    {
      name = "agentic_rag-cloud_run-vertex_ai_vector_search"
      value = "agentic_rag,cloud_run,--include-data-ingestion,--datastore,vertex_ai_vector_search"
    },
    {
      name  = "live_api-cloud_run"
      value = "live_api,cloud_run"
    },
    {
      name  = "adk_gemini_fullstack-agent_engine"
      value = "adk_gemini_fullstack,agent_engine"
    },
  ]
  # Create a safe trigger name by replacing underscores with hyphens and dots with hyphens
  # This ensures we have valid trigger names that don't exceed character limits
  trigger_name_safe = { for combo in local.agent_testing_combinations :
      combo.name => replace(replace(combo.name, "_", "-"), ".", "-")
    }

  e2e_agent_deployment_included_files = { for combo in local.agent_testing_combinations :
    combo.name => [
      # Only include files for the specific agent being tested
      "agents/${split(",", combo.value)[0]}/**",
      # Common files that affect all agents
      "src/cli/**",
      "src/base_template/**",
      "src/data_ingestion/**",
      "src/deployment_targets/**",
      "tests/cicd/test_e2e_deployment.py",
      "src/resources/locks/**",
      "pyproject.toml",
      "uv.lock",
      ".cloudbuild"
    ]
  }
}

resource "google_cloudbuild_trigger" "pr_build_use_wheel" {
  name            = "pr-build-use-wheel"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for testing wheel build and installation"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch          = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename       = ".cloudbuild/ci/build_use_wheel.yaml"
  included_files = local.common_included_files
  ignored_files  = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
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
      branch          = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename       = ".cloudbuild/ci/test.yaml"
  included_files = local.common_included_files
  ignored_files  = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
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
      branch          = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename       = ".cloudbuild/ci/lint.yaml"
  included_files = local.common_included_files
  ignored_files  = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
}

# c. Create Templated Agents Lint trigger for PRs - one for each agent/deployment combination:
resource "google_cloudbuild_trigger" "pr_templated_agents_lint" {
  for_each = { for combo in local.agent_testing_combinations : combo.name => combo }
  
  name            = "lint-${local.trigger_name_safe[each.key]}"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR lint checks on templated agents: ${each.value.name}"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch          = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename       = ".cloudbuild/ci/lint_templated_agents.yaml"
  included_files = local.agent_testing_included_files[each.key]
  ignored_files  = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  substitutions = {
    _TEST_AGENT_COMBINATION = each.value.value
  }
}

# d. Create Templated Agents Integration Test triggers for PRs - one for each agent/deployment combination
resource "google_cloudbuild_trigger" "pr_templated_agents_test" {
  for_each = { for combo in local.agent_testing_combinations : combo.name => combo }

  name            = "test-${local.trigger_name_safe[each.key]}"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks on templated agents tests: ${each.value.name}"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch          = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename       = ".cloudbuild/ci/test_templated_agents.yaml"
  included_files = local.agent_testing_included_files[each.key]
  ignored_files  = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  substitutions = {
    _TEST_AGENT_COMBINATION = each.value.value
  }
}

# e. Create E2E Deployment Test triggers for main branch commits - one for each agent/deployment combination
resource "google_cloudbuild_trigger" "main_e2e_deployment_test" {
  for_each = { for combo in local.e2e_agent_deployment_combinations : combo.name => combo }

  name            = "e2e-deploy-${local.trigger_name_safe[each.key]}"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for E2E deployment tests on main branch: ${each.value.name}"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    push {
      branch = "main"
    }
  }

  filename       = ".cloudbuild/cd/test_e2e.yaml"
  included_files = local.e2e_agent_deployment_included_files[each.key]
  ignored_files  = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_UNSPECIFIED"

  substitutions = {
    _TEST_AGENT_COMBINATION = each.value.value
    _E2E_DEV_PROJECT     = var.e2e_test_project_mapping.dev
    _E2E_STAGING_PROJECT = var.e2e_test_project_mapping.staging
    _E2E_PROD_PROJECT    = var.e2e_test_project_mapping.prod
  }
}
