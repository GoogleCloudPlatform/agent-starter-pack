from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class TaskOntology:
    intent: str
    required_capabilities: list[str]
    energy_budget: float


class KineticResolver:
    def __init__(
        self,
        vector_store: "VectorStore",
        audit_ledger: "AuditLedger",
        experts: Mapping[str, "ExpertFn"] | None = None,
    ) -> None:
        self.memory = vector_store
        self.ledger = audit_ledger
        self.experts: dict[str, ExpertFn] = dict(experts or {})

    def register_expert(self, expert_id: str, execute_fn: "ExpertFn") -> None:
        self.experts[expert_id] = execute_fn

    def resolve_and_execute(
        self,
        task: TaskOntology,
        current_state: Sequence[float],
    ) -> dict:
        decision = "HALT"
        selected_expert: ExpertFn | None = None
        energy_cost: float | None = None

        for expert_id, execute_fn in self.experts.items():
            projected_state = self._simulate_outcome(expert_id, current_state)
            energy_cost = self._calculate_lyapunov_drift(current_state, projected_state)

            if energy_cost <= task.energy_budget:
                decision = "EXECUTE"
                selected_expert = execute_fn
                break

        if decision == "EXECUTE" and selected_expert:
            result = selected_expert(task)
            self.ledger.record(task, "SUCCESS", energy_cost)
            return result

        self.ledger.record(task, "BLOCKED", energy_cost)
        raise RuntimeError(
            "Invariant violation: no expert met energy budget "
            f"{task.energy_budget}"
        )

    def _simulate_outcome(self, expert_id: str, current_state: Sequence[float]) -> list[float]:
        expert_profile = self.memory.get_expert_profile(expert_id)
        weights = expert_profile.weights
        if len(weights) != len(current_state):
            return list(current_state)
        return [value * weight for value, weight in zip(current_state, weights)]

    @staticmethod
    def _calculate_lyapunov_drift(start: Sequence[float], end: Sequence[float]) -> float:
        if len(start) != len(end) or not start:
            return 1.0
        dot = sum(a * b for a, b in zip(start, end))
        norm_start = sum(a * a for a in start) ** 0.5
        norm_end = sum(b * b for b in end) ** 0.5
        if norm_start == 0.0 or norm_end == 0.0:
            return 1.0
        cosine_similarity = dot / (norm_start * norm_end)
        return 1.0 - cosine_similarity


@dataclass(frozen=True)
class ExpertProfile:
    expert_id: str
    weights: list[float]


class VectorStore:
    def __init__(self, profiles: Iterable[ExpertProfile]) -> None:
        self._profiles = {profile.expert_id: profile for profile in profiles}

    def get_expert_profile(self, expert_id: str) -> ExpertProfile:
        return self._profiles.get(
            expert_id,
            ExpertProfile(expert_id=expert_id, weights=[1.0]),
        )


class AuditLedger:
    def record(self, task: TaskOntology, verdict: str, energy_cost: float | None) -> None:
        raise NotImplementedError


ExpertFn = Callable[[TaskOntology], dict]
