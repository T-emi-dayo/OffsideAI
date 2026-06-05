"""
Unified request and response schemas for all Offside AI API endpoints.

Design contract
---------------
`AgentResponse` is the single, stable envelope every endpoint returns.
The `data` field is the only part that varies — each agent has its own
typed payload (PreMatchData, LiveData, etc.).

Adding new fields to an agent ONLY requires updating its data model here.
The envelope shape, error handling, and route structure are unchanged.
"""

from __future__ import annotations

from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Response envelope
# ---------------------------------------------------------------------------

class ResponseMeta(BaseModel):
    """Execution metadata attached to every response."""

    timestamp: str = Field(description="ISO 8601 UTC timestamp of response creation.")
    duration_ms: float = Field(description="Total agent execution time in milliseconds.")


class AgentResponse(BaseModel, Generic[T]):
    """
    Unified response envelope for all Offside AI agent endpoints.

    Fields
    ------
    success : bool
        False only when the agent could not produce any output.
        Partial results with non-fatal errors return success=True with
        a non-empty `errors` list.
    agent : str
        Which agent produced this response.
    match_id : str
        Fixture this response is anchored to.
    data : T
        Agent-specific payload. See the typed variants below.
    errors : list[str]
        Non-fatal errors accumulated during the run. Partial output is
        still available in `data` when errors are present.
    meta : ResponseMeta
        Timing and execution metadata.
    """

    success: bool
    agent: Literal["prematch", "live", "postmatch", "chat"]
    match_id: str
    data: T
    errors: list[str] = Field(default_factory=list)
    meta: ResponseMeta


# ---------------------------------------------------------------------------
# Per-agent data payloads
# ---------------------------------------------------------------------------

class PreMatchData(BaseModel):
    """Output payload for the PreMatchAgent."""

    prediction: Optional[dict] = Field(
        default=None,
        description="ML model outcome probabilities: {home_win, draw, away_win}.",
    )
    report_narrative: Optional[str] = Field(
        default=None,
        description="LLM-generated pre-match analysis narrative.",
    )


class LiveData(BaseModel):
    """Output payload for the LiveAgent."""

    current_score: dict = Field(
        default_factory=lambda: {"home": 0, "away": 0},
        description="Running score derived from goal events.",
    )
    key_moments: list[str] = Field(
        default_factory=list,
        description="Formatted strings for goals, red cards, and penalties.",
    )
    narrative: str = Field(
        default="",
        description="LLM-generated live match narrative.",
    )


class PostMatchData(BaseModel):
    """Output payload for the PostMatchAgent."""

    key_moments: list[str] = Field(default_factory=list)
    player_highlights: list[str] = Field(default_factory=list)
    match_summary: Optional[str] = None
    tactical_analysis: Optional[str] = None
    full_report: Optional[str] = Field(
        default=None,
        description="Full synthesised post-match report narrative.",
    )


class ChatMessage(BaseModel):
    """A single turn in a conversation."""

    role: Literal["user", "assistant"]
    content: str


class ChatData(BaseModel):
    """Output payload for the ChatAgent."""

    reply: str = Field(description="The AI assistant's response.")
    sources_used: list[str] = Field(
        default_factory=list,
        description="Data tools called to inform the answer.",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description=(
            "Updated conversation history including the new reply. "
            "Store this and pass it back as `history` on the next request."
        ),
    )


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PreMatchRequest(BaseModel):
    """Request body for POST /api/prematch."""

    match_id: str
    home_team: str
    away_team: str
    competition_type: str = Field(default="world_cup")
    stage: str = Field(default="Group Stage")
    match_date: str = Field(description="Match date in YYYY-MM-DD format.")


class MatchEvent(BaseModel):
    """A single match event used by both Live and PostMatch requests."""

    minute: int
    event_type: str = Field(
        description="goal | red_card | penalty | assist | yellow_card | subst"
    )
    team: str
    player: str
    detail: str = ""


class LiveRequest(BaseModel):
    """Request body for POST /api/live."""

    match_id: str
    home_team: str
    away_team: str
    competition_type: str = Field(default="world_cup")
    events: list[MatchEvent]


class PostMatchRequest(BaseModel):
    """Request body for POST /api/postmatch."""

    match_id: str
    home_team: str
    away_team: str
    competition_type: str = Field(default="world_cup")
    final_score: dict = Field(
        description='Final scoreline: {"home": int, "away": int}.'
    )
    match_events: list[MatchEvent]
    pre_match_analysis: dict = Field(
        default_factory=dict,
        description="Output from the pre-match agent run for this fixture.",
    )


class ChatRequest(BaseModel):
    """Request body for POST /api/chat.

    The API is stateless — the caller owns the conversation history and
    sends the full `history` list on every request. The response includes
    an updated `history` ready for the next call.
    """

    match_id: str
    home_team: str
    away_team: str
    match_state: Literal["pre", "live", "post"]
    message: str = Field(description="The new user message.")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Full conversation history prior to this message.",
    )
    live_context: Optional[dict] = Field(
        default=None,
        description="Current match events — supply when match_state is 'live'.",
    )
