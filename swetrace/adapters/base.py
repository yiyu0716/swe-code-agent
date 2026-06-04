from abc import ABC, abstractmethod
from dataclasses import dataclass

from swetrace.artifacts import RunStore
from swetrace.schema import RunReport, TaskSpec, TrajectoryStep


@dataclass(frozen=True)
class RunResult:
    run_id: str
    report: RunReport
    trajectory: list[TrajectoryStep]


class AgentAdapter(ABC):
    name: str

    @abstractmethod
    def run_task(self, task: TaskSpec, store: RunStore) -> RunResult:
        """Run one code-agent task and persist its normalized artifacts."""
