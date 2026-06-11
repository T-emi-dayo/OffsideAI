from __future__ import annotations

import json
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.agents.BaseAgent import BaseAgent
from src.schemas.responses import MatchAnalysis, PostMatchReport
from src.schemas.state import PostMatchState

logger = logging.getLogger(__name__)


class PostMatchAgent(BaseAgent):
    """
    LangGraph agent that generates a complete post-match report.

    Graph
    -----
    analyse_match → generate_report

    Nodes
    -----
    analyse_match   : Extracts key moments and player highlights from events;
                      LLM produces a match summary and tactical analysis.
    generate_report : LLM synthesises all analysis into the full report narrative.

    Input
    -----
    Receives a PostMatchState (extends MatchInput). The gateway populates:
    - `events`            — full event log from the API
    - `final_score`       — {"home": int, "away": int}
    - `pre_match_analysis`— cached pre-match output (may be empty {})
    """

    @staticmethod
    def _fallback_analysis(state: PostMatchState, key_moments: list[str], player_highlights: list[str]) -> dict:
        """Build useful post-match analysis when the LLM is unavailable."""
        score = state.get("final_score") or {"home": 0, "away": 0}
        home_team = state["home_team"]
        away_team = state["away_team"]
        scoreline = f"{home_team} {score['home']} - {score['away']} {away_team}"
        moments = "; ".join(key_moments[:4]) if key_moments else "No major events were recorded."
        standouts = "; ".join(player_highlights[:3]) if player_highlights else "No individual highlights were recorded."

        return {
            "match_summary": (
                f"{scoreline} finished with a clear event trail: {moments} "
                f"The decisive pattern came through the goal sequence and the timing of the major incidents."
            ),
            "tactical_analysis": (
                f"The match swung around momentum after each scoring action. {standouts} "
                "The event log points to a game shaped by transition moments, set-piece pressure, "
                "and how each side reacted after conceding."
            ),
        }

    @staticmethod
    def _fallback_report(state: PostMatchState) -> str:
        """Build a complete article-style report when the LLM is unavailable."""
        score = state.get("final_score") or {"home": 0, "away": 0}
        home_team = state["home_team"]
        away_team = state["away_team"]
        summary = state.get("match_summary") or ""
        tactical = state.get("tactical_analysis") or ""
        key_moments = state.get("key_moments") or []
        player_highlights = state.get("player_highlights") or []

        moments_text = " ".join(key_moments) if key_moments else "The official event feed recorded no major moments."
        highlights_text = " ".join(player_highlights) if player_highlights else "No individual player highlights were recorded."

        return (
            f"{home_team} {score['home']} - {score['away']} {away_team}: {summary}\n\n"
            f"Key moments: {moments_text}\n\n"
            f"Tactical view: {tactical}\n\n"
            f"Player notes: {highlights_text}"
        )

    # --- node: analyse_match --------------------------------------------

    def _analyse_match(self, state: PostMatchState) -> dict:
        """
        Extract structured data from events and generate LLM analysis.

        Parameters
        ----------
        state : PostMatchState
            Current graph state.

        Returns
        -------
        dict
            State update with `key_moments`, `player_highlights`,
            `match_summary`, and `tactical_analysis`.
        """
        logger.info(
            "PostMatchAgent.analyse_match | %s vs %s",
            state["home_team"],
            state["away_team"],
        )
        events = state.get("events") or []
        score = state.get("final_score") or {"home": 0, "away": 0}
        pre_match = state.get("pre_match_analysis") or {}

        # deterministic extraction from event log
        key_moments: list[str] = []
        player_performances: dict[str, list[str]] = {}

        for event in events:
            event_type = event.get("event_type", "").lower()
            player = event.get("player", "Unknown")
            team = event.get("team", "")
            minute = event.get("minute", 0)
            detail = event.get("detail", "")

            if event_type == "goal":
                key_moments.append(f"{minute}' GOAL — {player} ({team}): {detail}")
                player_performances.setdefault(player, []).append(f"Scored ({minute}')")
            elif event_type == "red_card":
                key_moments.append(f"{minute}' RED CARD — {player} ({team}): {detail}")
                player_performances.setdefault(player, []).append(f"Red card ({minute}')")
            elif event_type == "assist":
                player_performances.setdefault(player, []).append(f"Assist ({minute}')")

        player_highlights = [
            f"{player}: {', '.join(actions)}"
            for player, actions in player_performances.items()
        ]

        logger.info(
            "PostMatchAgent.analyse_match | %d key moments, %d player highlights",
            len(key_moments),
            len(player_highlights),
        )

        system = self.get_prompt("postmatch_analyse")
        user_msg = (
            f"Analyse this World Cup match: "
            f"{state['home_team']} {score['home']} — {score['away']} {state['away_team']}.\n\n"
            f"<key_moments>\n{json.dumps(key_moments, indent=2)}\n</key_moments>\n\n"
            f"<player_highlights>\n{json.dumps(player_highlights, indent=2)}\n</player_highlights>\n\n"
            f"<pre_match_context>\n{json.dumps(pre_match, default=str, indent=2)}\n</pre_match_context>"
        )
        messages = self.ai_service.build_messages(user=user_msg, system=system)

        try:
            result = self.ai_service.invoke_structured(
                messages=messages,
                schema=MatchAnalysis,
                temperature=0.3,
            )
            analysis: MatchAnalysis = result.parsed
            logger.info("PostMatchAgent.analyse_match | analysis generated successfully")
            return {
                "key_moments": key_moments,
                "player_highlights": player_highlights,
                "match_summary": analysis.match_summary,
                "tactical_analysis": analysis.tactical_analysis,
            }
        except Exception as exc:
            logger.warning("PostMatchAgent.analyse_match | LLM fallback used: %s", exc)
            return {
                "key_moments": key_moments,
                "player_highlights": player_highlights,
                **self._fallback_analysis(state, key_moments, player_highlights),
            }

    # --- node: generate_report ------------------------------------------

    def _generate_report(self, state: PostMatchState) -> dict:
        """
        Synthesise match analysis into the full post-match report.

        Parameters
        ----------
        state : PostMatchState
            Current graph state. Expects `match_summary`, `key_moments`,
            and `player_highlights` populated by `analyse_match`.

        Returns
        -------
        dict
            State update with `full_report` key.
        """
        logger.info("PostMatchAgent.generate_report | invoking LLM")
        system = self.get_prompt("postmatch_generate_report")
        score = state.get("final_score") or {"home": 0, "away": 0}

        user_msg = (
            f"Write the complete post-match report for "
            f"{state['home_team']} {score['home']} — {score['away']} {state['away_team']}.\n\n"
            f"<match_summary>\n{state.get('match_summary', '')}\n</match_summary>\n\n"
            f"<tactical_analysis>\n{state.get('tactical_analysis', '')}\n</tactical_analysis>\n\n"
            f"<key_moments>\n{json.dumps(state.get('key_moments') or [], indent=2)}\n</key_moments>\n\n"
            f"<player_highlights>\n{json.dumps(state.get('player_highlights') or [], indent=2)}\n</player_highlights>"
        )
        messages = self.ai_service.build_messages(user=user_msg, system=system)

        try:
            result = self.ai_service.invoke_structured(
                messages=messages,
                schema=PostMatchReport,
                temperature=0.3,
            )
            report: PostMatchReport = result.parsed
            logger.info("PostMatchAgent.generate_report | report generated successfully")
            return {"full_report": report.full_report}
        except Exception as exc:
            logger.warning("PostMatchAgent.generate_report | LLM fallback used: %s", exc)
            return {"full_report": self._fallback_report(state)}

    # --- graph builder --------------------------------------------------

    def build(self) -> CompiledStateGraph:
        """
        Compile the PostMatchAgent LangGraph graph.

        Returns
        -------
        CompiledStateGraph
            Compiled graph ready for invocation.
        """
        graph = StateGraph(PostMatchState)

        graph.add_node("analyse_match", self._analyse_match)
        graph.add_node("generate_report", self._generate_report)

        graph.add_edge(START, "analyse_match")
        graph.add_edge("analyse_match", "generate_report")
        graph.add_edge("generate_report", END)

        return graph.compile()
