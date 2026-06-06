from __future__ import annotations

import json
import logging
from typing import Optional

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.agents.BaseAgent import BaseAgent
from src.schemas.responses import PreMatchReport
from src.schemas.state import PreMatchState
from src.tools.match_tools import get_h2h_record, get_team_recent_form
from src.tools.ranking_tools import get_fifa_ranking
from src.tools.team_tools import get_team_wc_history
from src.tools.web_search_tool import get_search_tool
from src.services.PredictionService import PredictionService

logger = logging.getLogger(__name__)


class PreMatchAgent(BaseAgent):
    """
    LangGraph agent that produces a pre-match intelligence report.

    Graph
    -----
    gather_context → get_prediction → generate_report

    Nodes
    -----
    gather_context  : Calls query tools to collect h2h, form, rankings, WC history.
    get_prediction  : Calls PredictionService (Dixon-Coles model) for outcome probabilities.
    generate_report : LLM synthesises all context into a structured report narrative.
    """

    # --- node: gather_context -------------------------------------------

    def _gather_context(self, state: PreMatchState) -> dict:
        """
        Call each data tool and assemble the context dict.

        Partial failures are caught per-tool and logged — the node continues
        with whatever data was successfully retrieved.

        Parameters
        ----------
        state : PreMatchState
            Current graph state.

        Returns
        -------
        dict
            State update with populated `context` key.
        """
        logger.info(
            "PreMatchAgent.gather_context | %s vs %s",
            state["home_team"],
            state["away_team"],
        )
        home = state["home_team"]
        away = state["away_team"]
        date = state["match_date"]

        context: dict = {}

        context["head_to_head"] = _safe_tool_call(
            get_h2h_record, {"team_a": home, "team_b": away}, "h2h", state
        )
        context["home_recent_form"] = _safe_tool_call(
            get_team_recent_form, {"team": home}, f"{home}_form", state
        )
        context["away_recent_form"] = _safe_tool_call(
            get_team_recent_form, {"team": away}, f"{away}_form", state
        )
        context["home_wc_history"] = _safe_tool_call(
            get_team_wc_history, {"team": home}, f"{home}_wc_history", state
        )
        context["away_wc_history"] = _safe_tool_call(
            get_team_wc_history, {"team": away}, f"{away}_wc_history", state
        )
        context["home_ranking"] = _safe_tool_call(
            get_fifa_ranking, {"team": home, "date": date}, f"{home}_ranking", state
        )
        context["away_ranking"] = _safe_tool_call(
            get_fifa_ranking, {"team": away, "date": date}, f"{away}_ranking", state
        )

        logger.info("PreMatchAgent.gather_context | context assembled")
        return {"context": context}

    # --- node: get_prediction -------------------------------------------

    def _get_prediction(self, state: PreMatchState) -> dict:
        """
        Run the Dixon-Coles ML model and return outcome probabilities.

        World Cup fixtures always use neutral-venue prediction (no home advantage).
        Non-WC fixtures use the model's built-in home advantage term.

        Parameters
        ----------
        state : PreMatchState
            Current graph state.

        Returns
        -------
        dict
            State update with populated `prediction` key.
        """
        home = state["home_team"]
        away = state["away_team"]
        neutral = state.get("competition_type", "world_cup") == "world_cup"

        logger.info(
            "PreMatchAgent.get_prediction | %s vs %s | neutral=%s",
            home,
            away,
            neutral,
        )

        try:
            prediction = PredictionService().predict_results(
                home_team=home,
                away_team=away,
                neutral=neutral,
            )
            logger.info("PreMatchAgent.get_prediction | prediction: %s", prediction)
            return {"prediction": prediction}
        except Exception as exc:
            logger.warning("PreMatchAgent.get_prediction | model failed: %s", exc)
            return {
                "prediction": None,
                "errors": [f"prediction failed: {exc}"],
            }

    # --- node: generate_report ------------------------------------------

    def _generate_report(self, state: PreMatchState) -> dict:
        """
        Synthesise gathered context and prediction into a full report narrative.

        Uses structured output to guarantee the LLM returns the expected schema.

        Parameters
        ----------
        state : PreMatchState
            Current graph state.

        Returns
        -------
        dict
            State update with populated `report_narrative` key.
        """
        logger.info("PreMatchAgent.generate_report | invoking LLM")
        system = self.get_prompt("prematch_generate_report")
        context = state.get("context") or {}
        prediction = state.get("prediction") or {}

        user_message = (
            f"Generate a complete pre-match intelligence report for "
            f"{state['home_team']} vs {state['away_team']} "
            f"({state['stage']}, {state['match_date']}).\n\n"
            f"<context>\n{json.dumps(context, default=str, indent=2)}\n</context>\n\n"
            f"<prediction>\n{json.dumps(prediction, default=str, indent=2)}\n</prediction>"
        )

        messages = self.ai_service.build_messages(user=user_message, system=system)
        web_search_tool = get_search_tool()

        try:
            result = self.ai_service.invoke_structured(
                messages=messages,
                tools=[web_search_tool],
                schema=PreMatchReport,
                temperature=0.3,
            )
            report: PreMatchReport = result.parsed
            logger.info("PreMatchAgent.generate_report | report generated successfully")
            return {"report_narrative": report.report_narrative}
        except Exception as exc:
            logger.error("PreMatchAgent.generate_report | LLM call failed: %s", exc)
            return {"errors": [f"generate_report failed: {exc}"]}

    # --- graph builder --------------------------------------------------

    def build(self) -> CompiledStateGraph:
        """
        Compile the PreMatchAgent LangGraph graph.

        Returns
        -------
        CompiledStateGraph
            Compiled graph ready for invocation.
        """
        graph = StateGraph(PreMatchState)

        graph.add_node("gather_context", self._gather_context)
        graph.add_node("get_prediction", self._get_prediction)
        graph.add_node("generate_report", self._generate_report)

        graph.add_edge(START, "gather_context")
        graph.add_edge("gather_context", "get_prediction")
        graph.add_edge("get_prediction", "generate_report")
        graph.add_edge("generate_report", END)

        return graph.compile()


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------


def _safe_tool_call(tool, args: dict, label: str, state: dict) -> Optional[dict]:
    """
    Invoke a LangChain tool and absorb failures into state errors.

    Parameters
    ----------
    tool : BaseTool
        The LangChain tool to call.
    args : dict
        Arguments to pass to the tool.
    label : str
        Human-readable label used in log and error messages.
    state : dict
        Current graph state — errors are appended here on failure.

    Returns
    -------
    Optional[dict]
        Tool result dict, or None if the call failed.
    """
    try:
        return tool.invoke(args)
    except Exception as exc:
        logger.warning("PreMatchAgent | tool %r failed: %s", label, exc)
        state.setdefault("errors", []).append(f"{label} tool failed: {exc}")
        return None
