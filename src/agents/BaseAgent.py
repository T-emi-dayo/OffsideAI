from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from langgraph.graph.state import CompiledStateGraph

from src.prompts.templates import get_prompt
from src.services.AIService import AIService

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all LangGraph agents in the Offside AI system.

    Each subclass builds a self-contained LangGraph graph via `build()`.
    The compiled graph is the public interface — callers invoke it directly.

    Attributes
    ----------
    ai_service : AIService
        Shared AI service instance for all LLM calls within this agent.
    """

    def __init__(self) -> None:
        self.ai_service = AIService()

    @abstractmethod
    def build(self) -> CompiledStateGraph:
        """
        Compile and return this agent's LangGraph graph.

        Returns
        -------
        CompiledStateGraph
            A ready-to-invoke compiled LangGraph graph.
        """
        pass

    def get_prompt(self, prompt_name: str) -> str:
        """
        Retrieve a named prompt template.

        Parameters
        ----------
        prompt_name : str
            Key identifying the prompt in the PROMPTS registry.

        Returns
        -------
        str
            The prompt string.
        """
        return get_prompt(prompt_name)
