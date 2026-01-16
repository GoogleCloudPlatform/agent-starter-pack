"""
Test suite for Makefile template generation.

This ensures that refactoring the Makefile doesn't change the generated output
across different agent types, deployment targets, and feature combinations.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pytest import TempPathFactory


class MakefileRenderer:
    """Helper class to render Makefile templates with Jinja2."""

    def __init__(self) -> None:
        template_dir = (
            Path(__file__).parent.parent.parent
            / "agent_starter_pack"
            / "base_templates"
            / "python"
        )
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        # Add Jinja2 extensions that Cookiecutter uses
        self.env.add_extension("jinja2.ext.do")

    def render(self, context: dict[str, Any]) -> str:
        """Render the Makefile template with the given context."""
        template = self.env.get_template("Makefile")
        return template.render(cookiecutter=context)


# Define test configurations covering major templating journeys
TEST_CONFIGURATIONS = {
    "adk_cloud_run_no_data": {
        "project_name": "test-adk-base",
        "agent_directory": "test_adk",
        "deployment_target": "cloud_run",
        "cicd_runner": "google_cloud_build",
        "is_adk": True,
        "is_adk_live": False,
        "is_a2a": False,
        "data_ingestion": False,
        "agent_garden": False,
        "example_question": "What can you help me with?",
        "settings": {},
        "package_version": "0.20.0",
    },
    "adk_agent_engine_no_data": {
        "project_name": "test-adk-base",
        "agent_directory": "test_adk",
        "deployment_target": "agent_engine",
        "cicd_runner": "google_cloud_build",
        "is_adk": True,
        "is_adk_live": False,
        "is_a2a": False,
        "data_ingestion": False,
        "agent_garden": False,
        "example_question": "What can you help me with?",
        "settings": {},
        "package_version": "0.20.0",
    },
    "adk_live_cloud_run": {
        "project_name": "test-adk-live",
        "agent_directory": "test_adk_live",
        "deployment_target": "cloud_run",
        "cicd_runner": "google_cloud_build",
        "is_adk": False,
        "is_adk_live": True,
        "is_a2a": False,
        "data_ingestion": False,
        "agent_garden": False,
        "example_question": "Tell me about your capabilities",
        "settings": {},
        "package_version": "0.20.0",
    },
    "adk_live_agent_engine": {
        "project_name": "test-adk-live",
        "agent_directory": "test_adk_live",
        "deployment_target": "agent_engine",
        "cicd_runner": "google_cloud_build",
        "is_adk": False,
        "is_adk_live": True,
        "is_a2a": False,
        "data_ingestion": False,
        "agent_garden": False,
        "example_question": "Tell me about your capabilities",
        "settings": {},
        "package_version": "0.20.0",
    },
    "agentic_rag_cloud_run_vertex_search": {
        "project_name": "test-rag",
        "agent_directory": "test_rag",
        "deployment_target": "cloud_run",
        "cicd_runner": "google_cloud_build",
        "is_adk": False,
        "is_adk_live": False,
        "is_a2a": False,
        "data_ingestion": True,
        "datastore_type": "vertex_ai_search",
        "agent_garden": False,
        "example_question": "What's in the knowledge base?",
        "settings": {},
        "package_version": "0.20.0",
    },
    "agentic_rag_cloud_run_vector_search": {
        "project_name": "test-rag",
        "agent_directory": "test_rag",
        "deployment_target": "cloud_run",
        "cicd_runner": "google_cloud_build",
        "is_adk": False,
        "is_adk_live": False,
        "is_a2a": False,
        "data_ingestion": True,
        "datastore_type": "vertex_ai_vector_search",
        "agent_garden": False,
        "example_question": "What's in the knowledge base?",
        "settings": {},
        "package_version": "0.20.0",
    },
    "langgraph_cloud_run": {
        "project_name": "test-langgraph",
        "agent_directory": "test_langgraph",
        "agent_name": "langgraph",
        "deployment_target": "cloud_run",
        "cicd_runner": "google_cloud_build",
        "is_adk": False,
        "is_adk_live": False,
        "is_a2a": True,
        "data_ingestion": False,
        "agent_garden": False,
        "example_question": "How can you help?",
        "settings": {},
        "package_version": "0.20.0",
    },
    "langgraph_agent_engine": {
        "project_name": "test-langgraph",
        "agent_directory": "test_langgraph",
        "agent_name": "langgraph",
        "deployment_target": "agent_engine",
        "cicd_runner": "google_cloud_build",
        "is_adk": False,
        "is_adk_live": False,
        "is_a2a": True,
        "data_ingestion": False,
        "agent_garden": False,
        "example_question": "How can you help?",
        "settings": {},
        "package_version": "0.20.0",
    },
    "agent_with_custom_commands": {
        "project_name": "test-custom",
        "agent_directory": "test_custom",
        "deployment_target": "cloud_run",
        "cicd_runner": "google_cloud_build",
        "is_adk": False,
        "is_adk_live": False,
        "is_a2a": False,
        "data_ingestion": False,
        "agent_garden": False,
        "example_question": "Custom agent question",
        "settings": {
            "commands": {
                "extra": {
                    "custom-task": {
                        "description": "Run a custom task",
                        "command": "echo 'Running custom task'",
                    },
                    "env-specific-task": {
                        "description": "Task with deployment-specific commands",
                        "command": {
                            "cloud_run": "echo 'Cloud Run task'",
                            "agent_engine": "echo 'Agent Engine task'",
                        },
                    },
                },
                "override": {
                    "install": "echo 'Custom install command'",
                    "playground": "echo 'Custom playground'",
                },
            }
        },
        "package_version": "0.20.0",
    },
    "agent_with_agent_garden": {
        "project_name": "test-garden",
        "agent_directory": "test_garden",
        "deployment_target": "cloud_run",
        "cicd_runner": "skip",
        "is_adk": True,
        "is_adk_live": False,
        "is_a2a": False,
        "data_ingestion": False,
        "agent_garden": True,
        "agent_sample_id": "sample-123",
        "agent_sample_publisher": "google",
        "example_question": "Agent garden question",
        "settings": {},
        "package_version": "0.20.0",
    },
    "adk_a2a_cloud_run": {
        "project_name": "test-a2a",
        "agent_directory": "test_a2a",
        "deployment_target": "cloud_run",
        "cicd_runner": "google_cloud_build",
        "is_adk": True,
        "is_adk_live": False,
        "is_a2a": True,
        "data_ingestion": False,
        "agent_garden": False,
        "example_question": "What can you help me with?",
        "settings": {},
        "package_version": "0.20.0",
    },
    "adk_a2a_agent_engine": {
        "project_name": "test-a2a",
        "agent_directory": "test_a2a",
        "deployment_target": "agent_engine",
        "cicd_runner": "google_cloud_build",
        "is_adk": True,
        "is_adk_live": False,
        "is_a2a": True,
        "data_ingestion": False,
        "agent_garden": False,
        "example_question": "What can you help me with?",
        "settings": {},
        "package_version": "0.20.0",
    },
}


@pytest.fixture
def makefile_renderer() -> MakefileRenderer:
    """Fixture to create a MakefileRenderer instance."""
    return MakefileRenderer()


class TestMakefileGeneration:
    """Test Makefile generation across different configurations."""

    @pytest.mark.parametrize("config_name", TEST_CONFIGURATIONS.keys())
    def test_makefile_renders_without_errors(
        self, makefile_renderer: MakefileRenderer, config_name: str
    ) -> None:
        """Test that Makefile renders without Jinja2 errors."""
        config = TEST_CONFIGURATIONS[config_name]

        # This should not raise any Jinja2 errors
        output = makefile_renderer.render(config)

        # Basic sanity checks
        assert output, f"Makefile should not be empty for {config_name}"
        assert "install:" in output, (
            f"Makefile should have install target for {config_name}"
        )
        assert "playground:" in output, (
            f"Makefile should have playground target for {config_name}"
        )

    @pytest.mark.parametrize("config_name", TEST_CONFIGURATIONS.keys())
    def test_makefile_snapshot(
        self, makefile_renderer: MakefileRenderer, config_name: str, snapshot_dir: Path
    ) -> None:
        """Test that Makefile output matches expected snapshot."""
        config = TEST_CONFIGURATIONS[config_name]
        output = makefile_renderer.render(config)

        snapshot_file = snapshot_dir / f"{config_name}.makefile"

        # On first run or with --update-snapshots flag, save the output
        if not snapshot_file.exists():
            snapshot_file.write_text(output)
            pytest.skip(f"Created new snapshot for {config_name}")

        # Compare with saved snapshot
        expected = snapshot_file.read_text()
        assert output == expected, (
            f"Makefile output changed for {config_name}.\n"
            f"To update snapshots, delete {snapshot_file} and rerun tests."
        )

    @pytest.mark.parametrize("config_name", TEST_CONFIGURATIONS.keys())
    def test_makefile_hash(
        self, makefile_renderer: MakefileRenderer, config_name: str, hash_file: Path
    ) -> None:
        """Test that Makefile output hash matches expected hash."""
        config = TEST_CONFIGURATIONS[config_name]
        output = makefile_renderer.render(config)

        # Calculate hash of output
        output_hash = hashlib.sha256(output.encode()).hexdigest()

        # Load or create hash registry
        if hash_file.exists():
            hashes = json.loads(hash_file.read_text())
        else:
            hashes = {}

        if config_name not in hashes:
            # Save new hash
            hashes[config_name] = output_hash
            hash_file.write_text(json.dumps(hashes, indent=2, sort_keys=True))
            pytest.skip(f"Created new hash for {config_name}")

        # Compare hashes
        expected_hash = hashes[config_name]
        assert output_hash == expected_hash, (
            f"Makefile output changed for {config_name}.\n"
            f"Expected hash: {expected_hash}\n"
            f"Actual hash:   {output_hash}\n"
            f"To update hashes, delete {hash_file} and rerun tests."
        )

    def test_adk_live_has_frontend_targets(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test that ADK Live configurations include frontend-related targets."""
        config = TEST_CONFIGURATIONS["adk_live_cloud_run"]
        output = makefile_renderer.render(config)

        assert "build-frontend:" in output
        assert "build-frontend-if-needed:" in output

    def test_adk_live_agent_engine_has_remote_playground(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test that ADK Live + Agent Engine has playground-remote target and dev targets."""
        config = TEST_CONFIGURATIONS["adk_live_agent_engine"]
        output = makefile_renderer.render(config)

        assert "playground-remote:" in output
        assert "Connecting to REMOTE agent" in output
        # Agent Engine also has dev mode targets
        assert "ui:" in output
        assert "playground-dev:" in output

    def test_data_ingestion_target_present(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test that data ingestion configurations include data-ingestion target."""
        config = TEST_CONFIGURATIONS["agentic_rag_cloud_run_vertex_search"]
        output = makefile_renderer.render(config)

        assert "data-ingestion:" in output
        assert "data-store-id" in output

    def test_data_ingestion_vertex_search_config(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test that Vertex AI Search config uses correct parameters."""
        config = TEST_CONFIGURATIONS["agentic_rag_cloud_run_vertex_search"]
        output = makefile_renderer.render(config)

        assert "--data-store-id" in output
        assert "--data-store-region" in output
        assert "--vector-search-index" not in output

    def test_data_ingestion_vector_search_config(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test that Vector Search config uses correct parameters."""
        config = TEST_CONFIGURATIONS["agentic_rag_cloud_run_vector_search"]
        output = makefile_renderer.render(config)

        assert "--vector-search-index" in output
        assert "--vector-search-index-endpoint" in output
        assert "--vector-search-data-bucket-name" in output
        assert "--data-store-id" not in output

    def test_custom_commands_override(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test that custom command overrides work correctly."""
        config = TEST_CONFIGURATIONS["agent_with_custom_commands"]
        output = makefile_renderer.render(config)

        # Should use custom install command
        assert "Custom install command" in output
        assert "uv sync" not in output or output.index("Custom install") < output.index(
            "uv sync"
        )

    def test_custom_commands_extra(self, makefile_renderer: MakefileRenderer) -> None:
        """Test that extra custom commands are included."""
        config = TEST_CONFIGURATIONS["agent_with_custom_commands"]
        output = makefile_renderer.render(config)

        assert "custom-task:" in output
        assert "Run a custom task" in output
        assert "env-specific-task:" in output

    def test_deployment_specific_custom_command(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test that deployment-specific custom commands use correct variant."""
        config = TEST_CONFIGURATIONS["agent_with_custom_commands"]
        output = makefile_renderer.render(config)

        # Should use cloud_run variant
        assert "Cloud Run task" in output
        assert "Agent Engine task" not in output

    def test_agent_garden_labels(self, makefile_renderer: MakefileRenderer) -> None:
        """Test that Agent Garden configurations include proper labels."""
        config = TEST_CONFIGURATIONS["agent_with_agent_garden"]
        output = makefile_renderer.render(config)

        assert "deployed-with=agent-garden" in output
        assert "vertex-agent-sample-id=sample-123" in output
        assert "vertex-agent-sample-publisher=google" in output

    def test_cloud_run_backend_command(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test Cloud Run backend target uses gcloud run deploy."""
        config = TEST_CONFIGURATIONS["langgraph_cloud_run"]
        output = makefile_renderer.render(config)

        assert "gcloud beta run deploy" in output
        assert "--source ." in output
        assert "--no-allow-unauthenticated" in output

    def test_agent_engine_backend_command(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test Agent Engine backend target uses requirements export."""
        config = TEST_CONFIGURATIONS["adk_agent_engine_no_data"]
        output = makefile_renderer.render(config)

        # Should export requirements
        assert "uv export" in output
        assert ".requirements.txt" in output
        assert "agent_engine_app" in output
        assert "uv run -m" in output

    def test_all_configs_have_required_targets(
        self, makefile_renderer: MakefileRenderer
    ) -> None:
        """Test that all configurations have the required common targets."""
        required_targets = [
            "install:",
            "playground:",
            "backend:",
            "test:",
            "lint:",
        ]

        for config_name, config in TEST_CONFIGURATIONS.items():
            output = makefile_renderer.render(config)

            for target in required_targets:
                assert target in output, (
                    f"Required target '{target}' missing in {config_name}"
                )

            # setup-dev-env is only present when cicd_runner != 'skip'
            if config.get("cicd_runner") != "skip":
                assert "setup-dev-env:" in output, (
                    f"setup-dev-env target missing in {config_name}"
                )
            else:
                assert "setup-dev-env:" not in output, (
                    f"setup-dev-env should not be present in prototype mode ({config_name})"
                )


@pytest.fixture
def snapshot_dir(tmp_path_factory: TempPathFactory) -> Path:
    """Create a directory for storing Makefile snapshots."""
    # Use a persistent directory for snapshots (not tmp)
    snapshot_dir = (
        Path(__file__).parent.parent.parent
        / "tests"
        / "fixtures"
        / "makefile_snapshots"
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    return snapshot_dir


@pytest.fixture
def hash_file(tmp_path_factory: TempPathFactory) -> Path:
    """Create a file for storing Makefile hashes."""
    hash_file = (
        Path(__file__).parent.parent.parent
        / "tests"
        / "fixtures"
        / "makefile_hashes.json"
    )
    hash_file.parent.mkdir(parents=True, exist_ok=True)
    return hash_file
