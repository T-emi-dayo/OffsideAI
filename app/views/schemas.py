"""
Unified request and response schemas for all Offside AI API endpoints.

Design contract
---------------
`AgentResponse[T]` is the envelope for all agent endpoints.
`DataResponse[T]`  is the envelope for all data/fixture endpoints.
Each has a typed `data` payload — the only part that varies per endpoint.
"""

from __future__ import annotations

from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Response envelopes
# ---------------------------------------------------------------------------

class ResponseMeta(BaseModel):
    """Execution metadata attached to every response."""

    timestamp: str = Field(description="ISO 8601 UTC timestamp of response creation.")
    duration_ms: float = Field(description="Total execution time in milliseconds.")


class AgentResponse(BaseModel, Generic[T]):
    """
    Unified envelope for all agent endpoints (preview, narrative, report, chat).

    success=False only when the agent could not produce any output at all.
    Partial results with non-fatal errors return success=True with a non-empty
    `errors` list.
    """

    success: bool
    agent: Literal["prematch", "live", "postmatch", "chat", "prediction"]
    match_id: str
    data: T
    errors: list[str] = Field(default_factory=list)
    meta: ResponseMeta


class DataResponse(BaseModel, Generic[T]):
    """Envelope for data endpoints (fixtures, match metadata)."""

    data: T
    meta: ResponseMeta


# ---------------------------------------------------------------------------
# Fixture data models
# ---------------------------------------------------------------------------

class FixtureScore(BaseModel):
    home: Optional[int] = None
    away: Optional[int] = None


class FixtureTeam(BaseModel):
    name: Optional[str] = None


class FixtureItem(BaseModel):
    """A single fixture as returned by GET /fixtures."""

    id: int
    stage: str
    group: Optional[str] = None
    utc_date: str
    match_state: str = Field(description="pre | live | post")
    home_team: FixtureTeam
    away_team: FixtureTeam
    score: FixtureScore


class FixtureListData(BaseModel):
    count: int
    fixtures: list[FixtureItem]


# ---------------------------------------------------------------------------
# Match metadata model
# ---------------------------------------------------------------------------

class MatchMetadata(BaseModel):
    """Match metadata returned by GET /match/{id}."""

    match_id: str
    home_team: str
    away_team: str
    match_date: str
    stage: str
    group: Optional[str] = None
    match_state: str = Field(description="pre | live | post")
    score: FixtureScore


# ---------------------------------------------------------------------------
# Agent data payloads
# ---------------------------------------------------------------------------

class MatchPrediction(BaseModel):
    """Dixon-Coles ML model output for a fixture."""

    p_home: float = Field(description="Home win probability.")
    p_draw: float = Field(description="Draw probability.")
    p_away: float = Field(description="Away win probability.")
    lambda_home: float = Field(description="Expected goals, home team.")
    lambda_away: float = Field(description="Expected goals, away team.")


class PreMatchData(BaseModel):
    """
    Output payload for GET /match/{id}/preview.

    Contains the ML prediction and six structured LLM report sections.
    All fields are Optional — partial results are returned on non-fatal errors.
    """

    prediction: Optional[MatchPrediction] = None
    match_overview: Optional[str] = None
    team_analysis: Optional[str] = None
    head_to_head: Optional[str] = None
    prediction_reasoning: Optional[str] = None
    verdict: Optional[str] = None


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


class PredictionData(BaseModel):
    """Output payload for GET /match/{id}/prediction."""

    home_team: str
    away_team: str
    p_home: Optional[float] = Field(default=None, description="Home win probability.")
    p_draw: Optional[float] = Field(default=None, description="Draw probability.")
    p_away: Optional[float] = Field(default=None, description="Away win probability.")
    lambda_home: Optional[float] = Field(default=None, description="Expected goals, home team.")
    lambda_away: Optional[float] = Field(default=None, description="Expected goals, away team.")


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

class ChatRequest(BaseModel):
    """
    Request body for POST /match/{id}/chat.

    The API is stateless — the caller owns conversation history and sends
    the full `history` list on every request.
    """

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
