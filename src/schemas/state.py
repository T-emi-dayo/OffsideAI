from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Optional

from typing_extensions import NotRequired, TypedDict
from langgraph.graph import MessagesState


class MatchState(str, Enum):
    """Valid lifecycle states for a World Cup fixture."""

    PRE = "pre"
    LIVE = "live"
    POST = "post"


# ---------------------------------------------------------------------------
# Unified match input — shared by PreMatchAgent, LiveAgent, PostMatchAgent
# ---------------------------------------------------------------------------

class MatchInput(TypedDict):
    """
    Unified input state accepted by all match agents (except ChatAgent).

    The gateway populates this from the football-data.org API response before
    invoking any agent graph. Optional fields are only populated when relevant
    to the specific agent being invoked.

    Fields
    ------
    match_id : str
        football-data.org integer match ID as a string.
    competition_type : str
        "world_cup" for all World Cup fixtures.
    home_team : str
        Home (first-named) team — canonical FIFA name.
    away_team : str
        Away (second-named) team — canonical FIFA name.
    match_date : str
        Match date in YYYY-MM-DD format.
    stage : str
        Tournament stage string e.g. "Group Stage", "Quarter Final".
    match_state : str
        Current lifecycle phase: "pre" | "live" | "post".
    events : list[dict]
        Normalised match events — populated for live and post requests.
        Each event: {match_id, minute, event_type, team, player, detail}.
    final_score : dict
        Final scoreline {"home": int, "away": int} — populated for post requests.
    pre_match_analysis : dict
        Cached PreMatchAgent output for this fixture — populated for post requests.
    errors : list[str]
        Accumulates non-fatal errors across nodes without overwriting.
    """

    match_id: str
    competition_type: str
    home_team: str
    away_team: str
    match_date: str
    stage: str
    match_state: str

    # optional — only populated when relevant
    events: NotRequired[list[dict]]
    final_score: NotRequired[dict]
    pre_match_analysis: NotRequired[dict]

    errors: NotRequired[Annotated[list[str], operator.add]]


# ---------------------------------------------------------------------------
# Per-agent graph states — extend MatchInput with output fields
# ---------------------------------------------------------------------------

class PreMatchState(MatchInput):
    """
    Graph state for PreMatchAgent.

    Output fields populated by agent nodes:
    context          — raw tool results (h2h, form, rankings, WC history)
    prediction       — ML model output dict from PredictionService
    report_narrative — final LLM-synthesised pre-match report
    """

    context: NotRequired[Optional[dict]]
    prediction: NotRequired[Optional[dict]]
    report_narrative: NotRequired[Optional[str]]


class LiveState(MatchInput):
    """
    Graph state for LiveAgent.

    Input: events populated from MatchInput.
    Output fields populated by agent nodes:
    current_score — running score derived from goal events
    key_moments   — formatted strings for goals, red cards, penalties
    narrative     — LLM-generated story-so-far prose
    """

    current_score: NotRequired[Optional[dict]]
    key_moments: NotRequired[Optional[list[str]]]
    narrative: NotRequired[Optional[str]]


class PostMatchState(MatchInput):
    """
    Graph state for PostMatchAgent.

    Input: events and final_score populated from MatchInput.
    Output fields populated by agent nodes:
    key_moments       — extracted key moments from event log
    player_highlights — per-player performance strings
    match_summary     — concise LLM match summary
    tactical_analysis — tactical observations from analysis node
    full_report       — final synthesised post-match report narrative
    """

    key_moments: NotRequired[Optional[list[str]]]
    player_highlights: NotRequired[Optional[list[str]]]
    match_summary: NotRequired[Optional[str]]
    tactical_analysis: NotRequired[Optional[str]]
    full_report: NotRequired[Optional[str]]


# ---------------------------------------------------------------------------
# Chat agent state — MessagesState-based, separate from MatchInput
# ---------------------------------------------------------------------------

class ChatState(MessagesState):
    """
    State for the ChatAgent graph.

    Extends MessagesState to support the LangGraph tool-calling loop.

    Fields
    ------
    match_id : str
        Fixture the conversation is anchored to.
    home_team : str
        Home team name.
    away_team : str
        Away team name.
    match_state : MatchState
        Current lifecycle phase of the fixture.
    live_context : dict | None
        Current match events when match_state is LIVE.
    errors : list[str]
        Accumulates non-fatal errors across nodes.
    sources_used : list[str] | None
        Tool names called during the response loop, for transparency.
    """

    match_id: str
    home_team: str
    away_team: str
    match_state: MatchState
    live_context: Optional[dict]
    errors: Annotated[list[str], operator.add]
    sources_used: Optional[list[str]]
