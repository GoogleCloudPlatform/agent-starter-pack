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

  # Gemini Enterprise related files - these have their own dedicated trigger
  gemini_enterprise_files = [
    "agent_starter_pack/cli/commands/register_gemini_enterprise.py",
    "tests/cicd/test_gemini_enterprise_registration.py",
    ".cloudbuild/cd/test_gemini_enterprise.yaml",
  ]

  common_included_files = [
    "agent_starter_pack/agents/**",
    "agent_starter_pack/cli/**",
    "tests/**",
    "agent_starter_pack/data_ingestion/**",
    "pyproject.toml",
    "uv.lock",
    ".cloudbuild/**",
  ]

  lint_templated_agents_included_files = [
    "agent_starter_pack/cli/**",
    "agent_starter_pack/base_templates/**",
    "agent_starter_pack/data_ingestion/**",
    "agent_starter_pack/deployment_targets/**",
    "tests/integration/test_template_linting.py",
    "tests/integration/test_templated_patterns.py",
    "agent_starter_pack/resources/locks/**",
    "pyproject.toml",
    "uv.lock",
    ".cloudbuild/**",
  ]

  makefile_usability_included_files = [
    "agent_starter_pack/cli/**",
    "agent_starter_pack/base_templates/**",
    "agent_starter_pack/deployment_targets/**",
    "tests/integration/test_makefile_usability.py",
    "pyproject.toml",
    "uv.lock",
    ".cloudbuild/**",
  ]

  # Define a local variable for agent/deployment combinations
  agent_testing_combinations = [
    {
      name  = "adk-agent_engine"
      value = "adk,agent_engine"
    },
    {
      name  = "adk-cloud_run"
      value = "adk,cloud_run"
    },
    {
      name  = "langgraph-agent_engine"
      value = "langgraph,agent_engine"
    },
    {
      name  = "langgraph-cloud_run"
      value = "langgraph,cloud_run,-dir,tag"
    },
    {
      name  = "agentic_rag-agent_engine-vertex_ai_search"
      value = "agentic_rag,agent_engine,--include-data-ingestion,--datastore,vertex_ai_search"
    },
    {
      name  = "agentic_rag-cloud_run-vertex_ai_vector_search"
      value = "agentic_rag,cloud_run,--include-data-ingestion,--datastore,vertex_ai_vector_search"
    },
    {
      name  = "adk_live-agent_engine"
      value = "adk_live,agent_engine"
    },
    {
      name  = "adk_live-cloud_run"
      value = "adk_live,cloud_run"
    },
    {
      name  = "adk-cloud_run-cloud_sql"
      value = "adk,cloud_run,--session-type,cloud_sql"
    },
    {
      name  = "adk_b-cr-agent_engine"
      value = "adk,cloud_run,--session-type,agent_engine"
    },
    {
      name  = "adk_a2a-agent_engine"
      value = "adk_a2a,agent_engine"
    },
    {
      name  = "adk_a2a-cloud_run"
      value = "adk_a2a,cloud_run"
    },
    {
      name  = "adk_go-cloud_run"
      value = "adk_go,cloud_run"
    },
  ]

  # Go-specific included files (different paths from Python)
  # Only triggers when Go-specific template files change
  go_agent_testing_included_files = {
    "adk_go-cloud_run" = [
      # Go agent-specific files
      "agent_starter_pack/agents/adk_go/**",
      # Shared base template (affects all languages)
      "agent_starter_pack/base_templates/_shared/**",
      # Go base template
      "agent_starter_pack/base_templates/go/**",
      # Go deployment target (Cloud Run only for Go)
      "agent_starter_pack/deployment_targets/cloud_run/_shared/**",
      "agent_starter_pack/deployment_targets/cloud_run/go/**",
      # Common files
      "agent_starter_pack/cli/**",
      "tests/integration/test_template_linting.py",
      "tests/integration/test_templated_patterns.py",
      "agent_starter_pack/resources/locks/**",
      "pyproject.toml",
      "uv.lock",
    ]
  }

  agent_testing_included_files = {
    # Python agents use Python-specific paths only
    for combo in local.agent_testing_combinations :
    combo.name => endswith(split(",", combo.value)[0], "_go") ? local.go_agent_testing_included_files[combo.name] : [
      # Only include files for the specific agent being tested
      "agent_starter_pack/agents/${split(",", combo.value)[0]}/**",
      # Common files that affect all agents
      "agent_starter_pack/cli/**",
      # Shared and Python base templates only (not Go)
      "agent_starter_pack/base_templates/_shared/**",
      "agent_starter_pack/base_templates/python/**",
      # Python deployment targets only (not Go)
      "agent_starter_pack/deployment_targets/agent_engine/_shared/**",
      "agent_starter_pack/deployment_targets/agent_engine/python/**",
      "agent_starter_pack/deployment_targets/cloud_run/_shared/**",
      "agent_starter_pack/deployment_targets/cloud_run/python/**",
      "tests/integration/test_template_linting.py",
      "tests/integration/test_templated_patterns.py",
      "agent_starter_pack/resources/locks/**",
      "pyproject.toml",
      "uv.lock",
    ]
  }
  e2e_agent_deployment_combinations = [
    {
      name  = "adk-agent_engine-github"
      value = "adk,agent_engine,--cicd-runner,github_actions"
    },
    {
      name  = "adk-cloud_run-github"
      value = "adk,cloud_run,--cicd-runner,github_actions"
    },
    {
      name  = "agentic_rag-agent_engine-vertex_ai_search-github"
      value = "agentic_rag,agent_engine,--include-data-ingestion,--datastore,vertex_ai_search,--cicd-runner,github_actions"
    },
    {
      name  = "adk_live-agent_engine-github"
      value = "adk_live,agent_engine,--cicd-runner,github_actions"
    },
    {
      name  = "adk-agent_engine"
      value = "adk,agent_engine,-dir,tag"
    },
    {
      name  = "adk-cloud_run"
      value = "adk,cloud_run,-dir,tag"
    },
    {
      name  = "langgraph-agent_engine"
      value = "langgraph,agent_engine"
    },
    {
      name  = "agentic_rag-agent_engine-vertex_ai_search"
      value = "agentic_rag,agent_engine,--include-data-ingestion,--datastore,vertex_ai_search"
    },
    {
      name  = "agentic_rag-cloud_run-vertex_ai_vector_search"
      value = "agentic_rag,cloud_run,--include-data-ingestion,--datastore,vertex_ai_vector_search"
    },
    {
      name  = "adk_live-agent_engine"
      value = "adk_live,agent_engine"
    },
    {
      name  = "adk_live-cloud_run"
      value = "adk_live,cloud_run"
    },
    {
      name  = "adk-cloud_run-cloud_sql"
      value = "adk,cloud_run,--session-type,cloud_sql"
    },
    {
      name  = "adk_a2a-agent_engine"
      value = "adk_a2a,agent_engine"
    },
    {
      name  = "adk_a2a-cloud_run"
      value = "adk_a2a,cloud_run"
    },
    {
      name  = "adk_go-cloud_run"
      value = "adk_go,cloud_run"
    },
  ]

  # Go-specific E2E included files
  # Only triggers when Go-specific template files change
  go_e2e_agent_deployment_included_files = {
    "adk_go-cloud_run" = [
      # Go agent-specific files
      "agent_starter_pack/agents/adk_go/**",
      # Shared base template
      "agent_starter_pack/base_templates/_shared/**",
      # Go base template
      "agent_starter_pack/base_templates/go/**",
      # Go deployment target (Cloud Run only for Go)
      "agent_starter_pack/deployment_targets/cloud_run/_shared/**",
      "agent_starter_pack/deployment_targets/cloud_run/go/**",
      # Common files
      "agent_starter_pack/cli/**",
      "tests/cicd/test_e2e_deployment.py",
      "agent_starter_pack/resources/locks/**",
      "pyproject.toml",
      "uv.lock",
      ".cloudbuild/**",
    ]
  }

  # Create a safe trigger name by replacing underscores with hyphens and dots with hyphens
  # This ensures we have valid trigger names that don't exceed character limits
  trigger_name_safe = { for combo in local.agent_testing_combinations :
    combo.name => replace(replace(combo.name, "_", "-"), ".", "-")
  }

  # Create safe trigger names for e2e deployment combinations
  e2e_trigger_name_safe = { for combo in local.e2e_agent_deployment_combinations :
    combo.name => replace(replace(combo.name, "_", "-"), ".", "-")
  }

  e2e_agent_deployment_included_files = { for combo in local.e2e_agent_deployment_combinations :
    combo.name => endswith(split(",", combo.value)[0], "_go") ? local.go_e2e_agent_deployment_included_files[combo.name] : (
      combo.name == "adk-cloud_run-cloud_sql" ? [
        # Cloud SQL is Python Cloud Run only
        "agent_starter_pack/deployment_targets/cloud_run/_shared/**",
        "agent_starter_pack/deployment_targets/cloud_run/python/**",
        "pyproject.toml",
        ] : substr(combo.name, 0, 11) == "agentic_rag" ? [
        "agent_starter_pack/agents/agentic_rag/**",
        "agent_starter_pack/data_ingestion/**",
        "pyproject.toml",
        ] : substr(combo.name, 0, 8) == "adk_live" ? [
        "agent_starter_pack/agents/adk_live/**",
        "pyproject.toml",
        ] : [
        # Only include files for the specific agent being tested
        "agent_starter_pack/agents/${split(",", combo.value)[0]}/**",
        # Common files that affect all agents
        "agent_starter_pack/cli/**",
        # Shared and Python base templates only (not Go)
        "agent_starter_pack/base_templates/_shared/**",
        "agent_starter_pack/base_templates/python/**",
        "agent_starter_pack/data_ingestion/**",
        # Python deployment targets only (not Go)
        "agent_starter_pack/deployment_targets/agent_engine/_shared/**",
        "agent_starter_pack/deployment_targets/agent_engine/python/**",
        "agent_starter_pack/deployment_targets/cloud_run/_shared/**",
        "agent_starter_pack/deployment_targets/cloud_run/python/**",
        "tests/cicd/test_e2e_deployment.py",
        "agent_starter_pack/resources/locks/**",
        "pyproject.toml",
        "uv.lock",
        ".cloudbuild/**",
      ]
    )
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

  filename           = ".cloudbuild/ci/build_use_wheel.yaml"
  included_files     = local.common_included_files
  ignored_files      = local.common_ignored_files
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

  filename           = ".cloudbuild/ci/test.yaml"
  included_files     = local.common_included_files
  ignored_files      = local.common_ignored_files
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

  filename           = ".cloudbuild/ci/lint.yaml"
  included_files     = local.common_included_files
  ignored_files      = local.common_ignored_files
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

  filename           = ".cloudbuild/ci/lint_templated_agents.yaml"
  included_files     = local.agent_testing_included_files[each.key]
  ignored_files      = local.common_ignored_files
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

  filename           = ".cloudbuild/ci/test_templated_agents.yaml"
  included_files     = local.agent_testing_included_files[each.key]
  ignored_files      = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  substitutions = {
    _TEST_AGENT_COMBINATION = each.value.value
  }
}

# e. Create E2E Deployment Test triggers for main branch commits - one for each agent/deployment combination
resource "google_cloudbuild_trigger" "main_e2e_deployment_test" {
  for_each = { for combo in local.e2e_agent_deployment_combinations : combo.name => combo }

  name            = "e2e-deploy-${local.e2e_trigger_name_safe[each.key]}"
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

  filename           = ".cloudbuild/cd/test_e2e.yaml"
  included_files     = local.e2e_agent_deployment_included_files[each.key]
  ignored_files      = concat(local.common_ignored_files, local.gemini_enterprise_files)
  include_build_logs = "INCLUDE_BUILD_LOGS_UNSPECIFIED"

  substitutions = {
    _TEST_AGENT_COMBINATION = each.value.value
    _E2E_DEV_PROJECT        = var.e2e_test_project_mapping.dev
    _E2E_STAGING_PROJECT    = var.e2e_test_project_mapping.staging
    _E2E_PROD_PROJECT       = var.e2e_test_project_mapping.prod
    _SECRETS_PROJECT_ID     = "asp-e2e-vars"
    _COMMIT_MESSAGE         = "$(push.head_commit.message)"
  }
}

# f. Create Remote Template Test trigger for PR requests
resource "google_cloudbuild_trigger" "pr_test_remote_template" {
  name            = "pr-test-remote-template"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks on remote templating"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch          = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename           = ".cloudbuild/ci/test_remote_template.yaml"
  included_files     = local.common_included_files
  ignored_files      = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
}

# g. Create Makefile usability Test trigger for PR requests
resource "google_cloudbuild_trigger" "pr_test_makefile" {
  name            = "pr-test-makefile"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks on Makefile usability"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch          = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename           = ".cloudbuild/ci/test_makefile.yaml"
  included_files     = local.makefile_usability_included_files
  ignored_files      = ["**/*.md"] # Don't ignore Makefiles for this trigger
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
}

# h. Create Pipeline Parity Test trigger for PR requests
resource "google_cloudbuild_trigger" "pr_test_pipeline_parity" {
  name            = "pr-test-pipeline-parity"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks on pipeline parity between GitHub Actions and Cloud Build"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch          = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename = ".cloudbuild/ci/test_pipeline_parity.yaml"
  included_files = [
    "tests/integration/test_pipeline_parity.py",
    "agent_starter_pack/cli/**",
    ".cloudbuild/**",
    "agent_starter_pack/base_templates/**/.github/**",
    "agent_starter_pack/base_templates/**/.cloudbuild/**",
    "pyproject.toml",
    "uv.lock",
  ]
  ignored_files      = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
}

# i. Create Agent Directory Functionality Test trigger for PR requests
resource "google_cloudbuild_trigger" "pr_test_agent_directory" {
  name            = "pr-test-agent-directory"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks on agent directory functionality (YAML agents, custom directories)"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    pull_request {
      branch          = "main"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  filename = ".cloudbuild/ci/test_agent_directory.yaml"
  included_files = [
    "pyproject.toml",
    "uv.lock",
    "tests/integration/test_agent_directory_functionality.py",
    ".cloudbuild/ci/test_agent_directory.yaml",
  ]
  ignored_files      = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
}

# j. Create E2E Gemini Enterprise Registration Test trigger for main branch commits (runs on merge to main)
resource "google_cloudbuild_trigger" "main_e2e_gemini_enterprise_test" {
  name            = "e2e-gemini-enterprise-registration"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "E2E test for Gemini Enterprise registration on main branch (runs when PR merges to main)"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = local.repository_path
    push {
      branch = "main"
    }
  }

  filename = ".cloudbuild/cd/test_gemini_enterprise.yaml"
  included_files = [
    "pyproject.toml",                                                # Triggers on releases
    "agent_starter_pack/cli/commands/register_gemini_enterprise.py", # Registration code changes
    "tests/cicd/test_gemini_enterprise_registration.py",             # Test changes
    ".cloudbuild/cd/test_gemini_enterprise.yaml",                    # Pipeline changes
  ]
  ignored_files      = local.common_ignored_files
  include_build_logs = "INCLUDE_BUILD_LOGS_UNSPECIFIED"

  substitutions = {
    _E2E_DEV_PROJECT = var.e2e_test_project_mapping.dev
    _COMMIT_MESSAGE  = "$(push.head_commit.message)"
  }
}
