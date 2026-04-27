from abc import ABC, abstractmethod
from src.schemas.state import AgentState


class BaseNode(ABC):

    @abstractmethod
    def run(self, state: AgentState) -> dict:
        """Execute node logic. Return a dict of state keys to update."""
        pass

    def __call__(self, state: AgentState) -> dict:
        return self.run(state)
