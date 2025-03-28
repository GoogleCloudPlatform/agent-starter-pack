import os

from rich.console import Console

from src.cli.utils.template import get_available_agents, get_deployment_targets

console = Console()


def get_test_combinations() -> list[tuple[str, str]]:
    """Generate all valid agent and deployment target combinations for testing."""
    combinations = []
    agents = get_available_agents()

    for agent_info in agents.values():
        agent_name = agent_info["name"]
        # Get available deployment targets for this agent
        targets = get_deployment_targets(agent_name)

        # Add each valid combination
        for target in targets:
            combinations.append((agent_name, target))

    return combinations


def get_test_combinations_to_run() -> list[tuple[str, str, list[str] | None]]:
    """Get the test combinations to run, either from environment or all available."""
    if os.environ.get("_TEST_AGENT_COMBINATION"):
        env_combo_parts = os.environ.get("_TEST_AGENT_COMBINATION", "").split(",")
        if len(env_combo_parts) >= 2:
            agent = env_combo_parts[0]
            deployment_target = env_combo_parts[1]
            extra_params_env = None
            if len(env_combo_parts) > 2:
                extra_params_env = env_combo_parts[2:]
            env_combo = (agent, deployment_target, extra_params_env)
            console.print(
                f"[bold blue]Running test for combination from environment:[/] {env_combo}"
            )
            return [env_combo]
        else:
            console.print(
                f"[bold red]Invalid environment combination format:[/] {env_combo_parts}"
            )

    combos: list[tuple[str, str, list[str] | None]] = []
    for agent, deployment_target in get_test_combinations():
        params: list[str] | None = None
        if agent == "agentic_rag":
            # Add vertex_ai_search variant
            params = [
                "--include-data-ingestion",
                "--datastore",
                "vertex_ai_search",
            ]
            combos.append((agent, deployment_target, params))

            # Add vertex_ai_vector_search variant
            params = [
                "--include-data-ingestion",
                "--datastore",
                "vertex_ai_vector_search",
            ]
            combos.append((agent, deployment_target, params))
        else:
            combos.append((agent, deployment_target, params))

    console.print(f"[bold blue]Running tests for all combinations:[/] {combos}")
    return combos
