from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Optional, List

from pydantic import BaseModel, Field
from typing_extensions import TypedDict, NotRequired
from langgraph.graph import MessagesState


class MatchState(str, Enum):
    """Valid lifecycle states for a World Cup fixture."""

    PRE = "pre"
    LIVE = "live"
    POST = "post"
    
# class MatchPrediction(TypedDict):
#     home_team: str
#     away_team: str
#     lambda_home: float          # Expected goals, home team
#     lambda_away: float          # Expected goals, away team
#     home_win_prob: float
#     draw_prob: float
#     away_win_prob: float
#     most_likely_score: tuple    # e.g. (1, 0)
#     score_distribution: dict    # {(i, j): probability}


class BaseMatchState(TypedDict):
    """
    Common state fields shared across all match agents.

    Fields
    ------
    match_id : str
        Unique fixture identifier.
    home_team : str
        Home team name.
    away_team : str
        Away team name.
    errors : list[str]
        Accumulates non-fatal errors across nodes without overwriting.
    """

    match_id: str
    competition_type: str
    home_team: str
    away_team: str
    errors: Annotated[list[str], operator.add]
    
    
class ReportNarrative(BaseModel):
    """
    Structured output schema for the final report narrative.

    Fields
    ------
    introduction : str
        Opening summary of the match.
    key_moments_section : str
        Narrative description of key moments.
    player_highlights_section : str
        Commentary on standout player performances.
    tactical_analysis_section : str
        Insights into tactical battles and strategies.
    conclusion : str
        Closing thoughts and implications for future matches.
    """

    introduction: str = Field(..., description="Opening summary of the match.")
    match_context : str = Field(default="The background context of the match, including h2h, form, rankings, and WC history")
    head_to_head_section: str = Field(..., description="Narrative description of head-to-head encounters.")
    player_highlights_section: str = Field(..., description="Commentary on standout player performances.")
    tactical_analysis_section: str = Field(..., description="Insights into tactical battles and strategies.")
    conclusion: str = Field(..., description="Closing thoughts and implications for future matches.")

    
class PreMatchInput(TypedDict):
    """
    Full state schema for the PreMatchAgent graph.

    Required fields are supplied by the caller at invocation time.
    Optional fields are populated by graph nodes during execution.
    """

    # --- caller-supplied ---
    match_id: str
    competition_type: str
    home_team: str
    away_team: str
    match_date: str
    stage: str

    # --- populated by nodes ---
    context: NotRequired[Optional[dict]]
    prediction: NotRequired[Optional[dict]]
    report_narrative: NotRequired[Optional[str]]
    errors: NotRequired[Annotated[list[str], operator.add]]


class PreMatchState(BaseMatchState):
    prediction: Optional[dict]
    report_narrative: Optional[ReportNarrative]


class LiveState(BaseMatchState):
    """
    State for the LiveAgent graph.

    Fields
    ------
    events : list[dict]
        Ordered list of match events. Each event must include keys:
        minute, event_type, team, player, detail.
    narrative : Optional[str]
        Generated story-so-far narrative.
    key_moments : Optional[list[str]]
        Formatted strings for goal, red card, and penalty events.
    current_score : Optional[dict]
        Running score derived from goal events: {"home": int, "away": int}.
    """
    home_team: str 
    away_team: str
    events: List[dict]
    narrative: List[str]
    key_moments: Optional[list[str]]
    current_score: Optional[dict]

class PostMatchState(BaseMatchState):
    """
    State for the PostMatchAgent graph.

    Fields
    ------
    final_score : dict
        Final scoreline: {"home": int, "away": int}.
    pre_match_analysis : dict
        Stored output from the PreMatchAgent run for this fixture.
    match_events : list[dict]
        Full event log from the persistent match store.
    match_summary : Optional[str]
        LLM-generated match summary from the analysis node.
    key_moments : Optional[list[str]]
        Extracted key moments from event parsing.
    player_highlights : Optional[list[str]]
        Per-player performance strings.
    tactical_analysis : Optional[str]
        Tactical observations from the analysis node.
    full_report : Optional[str]
        Final synthesised post-match report narrative.
    """

    final_score: dict
    pre_match_analysis: dict
    match_events: list[dict]
    match_summary: Optional[str]
    key_moments: Optional[list[str]]
    player_highlights: Optional[list[str]]
    tactical_analysis: Optional[str]
    full_report: Optional[str]


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
    live_context : Optional[dict]
        Current match events when match_state is LIVE.
    errors : list[str]
        Accumulates non-fatal errors across nodes.
    sources_used : Optional[list[str]]
        Tool names called during the response loop, for transparency.
    """

    match_id: str
    home_team: str
    away_team: str
    match_state: MatchState
    live_context: Optional[dict]
    errors: Annotated[list[str], operator.add]
    sources_used: Optional[list[str]]
