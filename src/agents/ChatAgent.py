from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.agents.BaseAgent import BaseAgent
from src.schemas.state import ChatState
from src.tools import CHAT_TOOLS

logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    """
    LangGraph agent that handles conversational Q&A grounded in match and historical data.

    Graph
    -----
    respond ↔ tools (loop until no tool calls) → extract_sources → END

    Nodes
    -----
    respond         : LLM with all CHAT_TOOLS bound — generates answers and issues tool calls.
    tools           : LangGraph ToolNode that executes any pending tool calls.
    extract_sources : Records which tools were called for response transparency.
    """

    def __init__(self) -> None:
        super().__init__()
        self._tools = CHAT_TOOLS
        # Bind tools once at init — model config is stable for the lifetime of this agent.
        self._llm_with_tools = self.ai_service.get_chat_model(
            temperature=0.7
        ).bind_tools(self._tools)

    # --- node: respond --------------------------------------------------

    def _respond(self, state: ChatState) -> dict:
        """
        Invoke the LLM with conversation history and bound tools.

        The system prompt is prepended on every call so it is always present
        even after tool messages are appended to the message list.

        Parameters
        ----------
        state : ChatState
            Current graph state including full message history.

        Returns
        -------
        dict
            State update appending the LLM's response message.
        """
        logger.info(
            "ChatAgent.respond | match=%s, messages=%d",
            state.get("match_id"),
            len(state.get("messages", [])),
        )
        system = self.get_prompt("chat_respond")
        messages = [SystemMessage(content=system)] + state["messages"]

        try:
            response = self._llm_with_tools.invoke(messages)
            logger.info(
                "ChatAgent.respond | tool_calls=%d",
                len(getattr(response, "tool_calls", []) or []),
            )
            return {"messages": [response]}
        except Exception as exc:
            logger.error("ChatAgent.respond | LLM call failed: %s", exc)
            return {"errors": [f"respond failed: {exc}"]}

    # --- node: extract_sources ------------------------------------------

    def _extract_sources(self, state: ChatState) -> dict:
        """
        Collect the names of all tools invoked during this response loop.

        Deduplicates while preserving call order so the client can display
        which data sources informed the answer.

        Parameters
        ----------
        state : ChatState
            Current graph state with completed message history.

        Returns
        -------
        dict
            State update with `sources_used` list.
        """
        sources = [
            msg.name
            for msg in state["messages"]
            if isinstance(msg, ToolMessage) and msg.name
        ]
        # dict.fromkeys preserves insertion order while deduplicating.
        deduplicated = list(dict.fromkeys(sources))
        logger.info(
            "ChatAgent.extract_sources | tools used: %s", deduplicated
        )
        return {"sources_used": deduplicated}

    # --- graph builder --------------------------------------------------

    def build(self) -> CompiledStateGraph:
        """
        Compile the ChatAgent LangGraph graph.

        The tool-calling loop runs until the LLM produces a response with
        no pending tool calls, at which point extract_sources runs and the
        graph terminates.

        Returns
        -------
        CompiledStateGraph
            Compiled graph ready for invocation.
        """
        graph = StateGraph(ChatState)

        graph.add_node("respond", self._respond)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_node("extract_sources", self._extract_sources)

        graph.add_edge(START, "respond")
        # When LLM has no tool calls, tools_condition returns END — redirect to extract_sources.
        graph.add_conditional_edges(
            "respond",
            tools_condition,
            {"tools": "tools", END: "extract_sources"},
        )
        graph.add_edge("tools", "respond")
        graph.add_edge("extract_sources", END)

        return graph.compile()
