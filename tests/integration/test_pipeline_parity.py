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

"""Tests to ensure Cloud Build and GitHub Actions pipeline configurations stay in sync using Gemini AI."""

import json
import os
import time
from pathlib import Path

import google.auth
import pytest
from google import genai
from google.genai import types
from google.genai.types import HttpOptions

# Set up default authentication and environment
try:
    _, project_id = google.auth.default()
    if project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
except Exception:
    # Fall back if auth is not available
    pass


class GeminiPipelineComparator:
    """Compares Cloud Build and GitHub Actions pipeline configurations using Gemini 2.5 Flash."""

    def __init__(self, base_template_path: Path):
        self.base_template_path = base_template_path
        self.cloudbuild_dir = (
            base_template_path
            / "{% if cookiecutter.cicd_runner == 'google_cloud_build' %}.cloudbuild{% else %}unused_.cloudbuild{% endif %}"
        )
        self.github_dir = (
            base_template_path
            / "{% if cookiecutter.cicd_runner == 'github_actions' %}.github{% else %}unused_github{% endif %}"
            / "workflows"
        )

        # Use Vertex AI with default authentication
        self.client = genai.Client(http_options=HttpOptions(api_version="v1"))

    def read_file_content(self, file_path: Path) -> str:
        """Read and return file content."""
        with open(file_path, encoding="utf-8") as f:
            return f.read()

    def create_comparison_prompt(
        self, cb_content: str, gh_content: str, pipeline_type: str
    ) -> str:
        """Create a detailed prompt for Gemini to compare pipeline configurations."""
        return f"""
You are comparing two CI/CD pipeline configurations that should functionally be equivalent:

1. **Cloud Build configuration** (Google Cloud Build YAML)
2. **GitHub Actions configuration** (GitHub Actions workflow YAML)

These are template files that use Jinja2 templating with cookiecutter variables. They should perform the same deployment steps but with different syntax for their respective platforms.

**Pipeline Type**: {pipeline_type}

**Cloud Build Configuration:**
```yaml
{cb_content}
```

**GitHub Actions Configuration:**
```yaml
{gh_content}
```

**Your Task:**
Compare these two pipeline configurations and determine if they are functionally equivalent, accounting for:

1. **Different syntax patterns**:
   - Cloud Build uses `${{_VAR_NAME}}` for substitution variables
   - GitHub Actions uses `${{{{ vars.VAR_NAME }}}}` or `${{{{ secrets.VAR_NAME }}}}`
   - Environment variable handling differs between platforms

2. **Variable equivalences** (treat these as the same):
   - `$PROJECT_ID` (Cloud Build) = `${{{{ vars.CICD_PROJECT_ID }}}}` (GitHub Actions)
   - Both refer to the same project where CI/CD infrastructure runs

3. **Jinja2 templating**: Both files use the same cookiecutter conditionals like:
   - `{{% if cookiecutter.deployment_target == 'cloud_run' %}}`
   - `{{% if cookiecutter.data_ingestion %}}`

4. **Deployment steps**: The core deployment logic should be the same:
   - Docker build/push steps
   - Cloud Run deployments
   - Agent Engine deployments
   - Data ingestion pipeline steps
   - Load testing
   - Authentication/token handling

5. **Expected platform differences** (IGNORE these - they are acceptable):
   - Authentication methods (Cloud Build uses service account, GitHub Actions uses Workload Identity)
   - Variable access patterns
   - Step organization and naming
   - Environment and concurrency features (GitHub Actions `environment` and `concurrency` fields vs Cloud Build's external configuration)
   - Trigger definitions (GitHub Actions `on:` triggers vs Cloud Build's external trigger configuration)
   - Deployment trigger mechanisms (Cloud Build triggering other builds vs GitHub Actions calling workflows)
   - ID token generation for load testing (Cloud Build uses its default service account, while GitHub Actions impersonates a specific service account)
   - Explicit `PATH` environment variable settings in Cloud Build.

6. **Important differences to FLAG**:
   - Different image push locations/destinations
   - Missing or different deployment steps
   - Different container names or artifact paths
   - Inconsistent environment variables or substitutions
   - Missing environment variables (e.g., DATA_STORE_ID in one pipeline but not the other)

**Response Format:**
Respond with a JSON object containing:
```json
{{
    "are_equivalent": true/false,
    "differences": [
        {{
            "type": "missing_step|extra_step|different_logic|missing_conditional|syntax_difference",
            "description": "Clear description of the difference",
            "severity": "critical|moderate|minor",
            "cloud_build_section": "relevant section from cloud build",
            "github_actions_section": "relevant section from github actions"
        }}
    ]
}}
```

**IMPORTANT**: Focus ONLY on functional differences that would affect deployment behavior.

**IGNORE these specific patterns** (mark as "minor" severity or don't report at all):
- Missing `environment:` or `concurrency:` fields in Cloud Build (these are managed externally)
- Missing `on:` trigger definitions in Cloud Build (triggers are configured externally)
- Authentication step differences (Workload Identity vs service account)
- Different mechanisms for triggering subsequent deployments (gcloud builds triggers vs workflow calls)
- Cross-project deployment patterns where both platforms push images to CI/CD project but deploy to target project
- Missing substitution variables in Cloud Build that would be provided externally
- Usage of `$PROJECT_ID` vs `${{{{ vars.CICD_PROJECT_ID }}}}` (these refer to the same project)
- Different commit SHA access patterns (COMMIT_SHA environment variable vs github.sha)
- Missing explicit checkout/setup steps in Cloud Build (Cloud Build handles repository access differently)
- Different Python installation methods between platforms

**FLAG these as critical/moderate**:
- Different Docker image push destinations (different projects/registries)
- Missing core deployment steps
- Different container names or service names
- Inconsistent artifact paths
- Missing environment variables (e.g., DATA_STORE_ID in one pipeline but not the other)
"""

    def compare_pipelines(
        self, cb_file: Path, gh_file: Path, pipeline_type: str
    ) -> dict:
        """Compare pipeline files using Gemini AI with retry logic."""
        cb_content = self.read_file_content(cb_file)
        gh_content = self.read_file_content(gh_file)

        prompt = self.create_comparison_prompt(cb_content, gh_content, pipeline_type)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Define JSON schema for the expected response
                comparison_schema = {
                    "type": "object",
                    "properties": {
                        "are_equivalent": {
                            "type": "boolean",
                            "description": "Whether the two pipeline configurations are functionally equivalent",
                        },
                        "differences": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": [
                                            "missing_step",
                                            "extra_step",
                                            "different_logic",
                                            "missing_conditional",
                                            "syntax_difference",
                                        ],
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Clear description of the difference",
                                    },
                                    "severity": {
                                        "type": "string",
                                        "enum": ["critical", "moderate", "minor"],
                                    },
                                },
                                "required": ["type", "description", "severity"],
                            },
                        },
                    },
                    "required": ["are_equivalent", "differences"],
                }

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        max_output_tokens=65000,
                        thinking_config=types.ThinkingConfig(thinking_budget=4000),
                        response_mime_type="application/json",
                        response_schema=comparison_schema,
                    ),
                )

                # With JSON schema, response should be properly formatted JSON
                response_text = (response.text or "").strip()

                # Fallback: Extract JSON from markdown code blocks if needed
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

                return json.loads(response_text)

            except (json.JSONDecodeError, Exception) as e:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(2)
                    continue
                else:
                    raise e

        # This should never be reached due to the exception handling above
        raise RuntimeError("All retry attempts failed")


@pytest.fixture
def comparator() -> GeminiPipelineComparator:
    """Create a GeminiPipelineComparator instance."""
    base_path = Path(__file__).parent.parent.parent / "src" / "base_template"
    return GeminiPipelineComparator(base_path)


def assert_pipelines_equivalent(comparison_result: dict, pipeline_name: str) -> None:
    """Assert that pipelines are equivalent based on Gemini analysis."""
    if not comparison_result["are_equivalent"]:
        # Filter only critical and moderate differences
        critical_diffs = [
            d
            for d in comparison_result["differences"]
            if d.get("severity") in ["critical", "moderate"]
        ]

        if critical_diffs:
            diff_summary = "\n".join(
                [f"- {d['type']}: {d['description']}" for d in critical_diffs]
            )
            pytest.fail(
                f"{pipeline_name} pipelines are not equivalent according to Gemini analysis.\n"
                f"Critical/Moderate Differences:\n{diff_summary}"
            )


def test_deploy_to_prod_parity(comparator: GeminiPipelineComparator) -> None:
    """Test that deploy-to-prod configurations are functionally equivalent."""
    cb_file = comparator.cloudbuild_dir / "deploy-to-prod.yaml"
    gh_file = comparator.github_dir / "deploy-to-prod.yaml"

    assert cb_file.exists(), f"Cloud Build deploy-to-prod.yaml not found at {cb_file}"
    assert gh_file.exists(), (
        f"GitHub Actions deploy-to-prod.yaml not found at {gh_file}"
    )

    comparison = comparator.compare_pipelines(cb_file, gh_file, "Production Deployment")
    assert_pipelines_equivalent(comparison, "Deploy-to-prod")


def test_staging_parity(comparator: GeminiPipelineComparator) -> None:
    """Test that staging configurations are functionally equivalent."""
    cb_file = comparator.cloudbuild_dir / "staging.yaml"
    gh_file = comparator.github_dir / "staging.yaml"

    assert cb_file.exists(), f"Cloud Build staging.yaml not found at {cb_file}"
    assert gh_file.exists(), f"GitHub Actions staging.yaml not found at {gh_file}"

    comparison = comparator.compare_pipelines(cb_file, gh_file, "Staging Deployment")
    assert_pipelines_equivalent(comparison, "Staging")


def test_pr_checks_parity(comparator: GeminiPipelineComparator) -> None:
    """Test that PR checks configurations are functionally equivalent."""
    cb_file = comparator.cloudbuild_dir / "pr_checks.yaml"
    gh_file = comparator.github_dir / "pr_checks.yaml"

    assert cb_file.exists(), f"Cloud Build pr_checks.yaml not found at {cb_file}"
    assert gh_file.exists(), f"GitHub Actions pr_checks.yaml not found at {gh_file}"

    comparison = comparator.compare_pipelines(cb_file, gh_file, "Pull Request Checks")
    assert_pipelines_equivalent(comparison, "PR Checks")


if __name__ == "__main__":
    # Allow running the test directly
    pytest.main([__file__, "-v"])
