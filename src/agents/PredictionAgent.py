from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.agents.BaseAgent import BaseAgent
from src.schemas.state import MatchInput
from src.services.PredictionService import PredictionService

logger = logging.getLogger(__name__)


class PredictionAgent(BaseAgent):
    """
    Thin LangGraph agent that wraps the PredictionService.

    Can be used standalone via GET /match/{id}/prediction.
    Also called as a node inside PreMatchAgent.

    Graph
    -----
    predict → END

    Input
    -----
    MatchInput with home_team, away_team, and competition_type populated.

    Output
    ------
    Adds `prediction` to state:
        {"p_home": float, "p_draw": float, "p_away": float,
         "lambda_home": float, "lambda_away": float}
    """

    def _predict(self, state: MatchInput) -> dict:
        """
        Call the Dixon-Coles model and return outcome probabilities.

        World Cup fixtures always use neutral-venue mode.

        Parameters
        ----------
        state : MatchInput
            Current graph state.

        Returns
        -------
        dict
            State update with `prediction` key.
        """
        home = state["home_team"]
        away = state["away_team"]
        neutral = state.get("competition_type", "world_cup") == "world_cup"

        logger.info(
            "PredictionAgent.predict | %s vs %s | neutral=%s",
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
            logger.info("PredictionAgent.predict | result: %s", prediction)
            return {"prediction": prediction}
        except Exception as exc:
            logger.error("PredictionAgent.predict | model failed: %s", exc)
            return {
                "prediction": None,
                "errors": [f"prediction failed: {exc}"],
            }

    def build(self) -> CompiledStateGraph:
        """
        Compile the PredictionAgent LangGraph graph.

        Returns
        -------
        CompiledStateGraph
            Compiled graph ready for invocation.
        """
        graph = StateGraph(MatchInput)

        graph.add_node("predict", self._predict)
        graph.add_edge(START, "predict")
        graph.add_edge("predict", END)

        return graph.compile()
