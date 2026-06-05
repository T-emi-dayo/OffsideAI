from __future__ import annotations

import json
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.agents.BaseAgent import BaseAgent
from src.schemas.responses import LiveNarrative
from src.schemas.state import LiveState

logger = logging.getLogger(__name__)

# Event types that qualify as key moments worth highlighting.
_KEY_EVENT_TYPES = frozenset({"goal", "red_card", "penalty"})


class LiveAgent(BaseAgent):
    """
    LangGraph agent that generates an on-demand live match narrative.

    Graph
    -----
    parse_events → generate_narrative

    Nodes
    -----
    parse_events      : Derives running score and key moments from raw event list.
    generate_narrative: LLM writes the story-so-far as flowing prose.
    """

    # --- node: parse_events ---------------------------------------------

    def _parse_events(self, state: LiveState) -> dict:
        """
        Derive current score and key moments from the raw event list.

        Goal events increment the running score. Goals, red cards, and
        penalties are captured as formatted key-moment strings.

        Parameters
        ----------
        state : LiveState
            Current graph state. `events` must be present.

        Returns
        -------
        dict
            State update with `current_score` and `key_moments`.
        """
        logger.info(
            "LiveAgent.parse_events | %s vs %s — %d events",
            state["home_team"],
            state["away_team"],
            len(state.get("events", [])),
        )
        home = state["home_team"]
        events = state.get("events", [])

        home_score = 0
        away_score = 0
        key_moments: list[str] = []

        for event in events:
            event_type = event.get("event_type", "").lower()
            team = event.get("team", "")
            player = event.get("player", "")
            minute = event.get("minute", 0)
            detail = event.get("detail", "")

            if event_type == "goal":
                if team.lower() == home.lower():
                    home_score += 1
                else:
                    away_score += 1

            if event_type in _KEY_EVENT_TYPES:
                label = event_type.upper().replace("_", " ")
                key_moments.append(f"{minute}' {label} — {player} ({team}): {detail}")

        logger.info(
            "LiveAgent.parse_events | score %d-%d, %d key moments",
            home_score,
            away_score,
            len(key_moments),
        )
        return {
            "current_score": {"home": home_score, "away": away_score},
            "key_moments": key_moments,
        }

    # --- node: generate_narrative ---------------------------------------

    def _generate_narrative(self, state: LiveState) -> dict:
        """
        Generate the live match narrative from parsed state.

        Uses structured output to guarantee the LLM returns the expected schema.

        Parameters
        ----------
        state : LiveState
            Current graph state. Expects `current_score` and `key_moments`
            populated by `parse_events`.

        Returns
        -------
        dict
            State update with `narrative` key.
        """
        logger.info("LiveAgent.generate_narrative | invoking LLM")
        system_prompt = self.get_prompt("live_generate_narrative")
        home_team = state.get("home_team", "Home Team")
        away_team = state.get("away_team", "Away Team")
        score = state.get("current_score") or {"home": 0, "away": 0}
        key_moments = state.get("key_moments") or []
        events = state.get("events") or []
        narrative = state.get("narrative") or []

        user_msg = (
            f"Generate a live narrative for "
            f"{home_team} vs {away_team}.\n\n"
            f"<current_score>"
            f"{home_team} {score} {away_team}"
            f"</current_score>\n\n"
            f"<key_moments>\n{json.dumps(key_moments, indent=2)}\n</key_moments>\n\n"
            f"<all_events>\n{json.dumps(events, default=str, indent=2)}\n</all_events>"
            f"<previous narratives>\n{json.dumps(narrative, default=str, indent=2)}\n</previous narratives>"
        )
        messages = self.ai_service.build_messages(user=user_msg, system=system_prompt)

        try:
            result = self.ai_service.invoke_structured(
                messages=messages,
                schema=LiveNarrative,
                temperature=0.7,
            )
            narrative: LiveNarrative = result.parsed
            logger.info("LiveAgent.generate_narrative | narrative generated successfully")
            return {"narrative": narrative.narrative}
        except Exception as exc:
            logger.error("LiveAgent.generate_narrative | LLM call failed: %s", exc)
            return {"errors": [f"generate_narrative failed: {exc}"]}

    # --- graph builder --------------------------------------------------

    def build(self) -> CompiledStateGraph:
        """
        Compile the LiveAgent LangGraph graph.

        Returns
        -------
        CompiledStateGraph
            Compiled graph ready for invocation.
        """
        graph = StateGraph(LiveState)

        graph.add_node("parse_events", self._parse_events)
        graph.add_node("generate_narrative", self._generate_narrative)

        graph.add_edge(START, "parse_events")
        graph.add_edge("parse_events", "generate_narrative")
        graph.add_edge("generate_narrative", END)

        return graph.compile()
