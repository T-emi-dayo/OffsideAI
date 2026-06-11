from __future__ import annotations

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    pass


# ---------------------------------------------------------------------------
# Pre-match agent output schemas
# ---------------------------------------------------------------------------


class PreMatchReport(BaseModel):
    """Structured LLM output for the PreMatchAgent — six discrete sections."""

    match_overview: str = Field(
        description="2-3 sentence scene-setter: what this fixture means in the tournament."
    )
    team_analysis: str = Field(
        description="Side-by-side breakdown of both teams: current form, FIFA ranking, key strengths and weaknesses."
    )
    head_to_head: str = Field(
        description="Historical H2H record and what the pattern tells us about this fixture."
    )
    prediction_reasoning: str = Field(
        description="Contextual explanation of the ML model's win/draw/loss probabilities and expected goals."
    )
    verdict: str = Field(
        description="1-2 sentence final prediction summarising the most likely outcome and margin."
    )

# ---------------------------------------------------------------------------
# Live agent output schemas
# ---------------------------------------------------------------------------


class ParsedEvents(BaseModel):
    """Structured input for the LiveAgent event parsing node."""

    key_moment: list[str] = Field(default_factory=list, description="Formatted strings for key match events such as goals, red cards, and penalties.")
    history: list[str] = Field(default_factory=list, description="The list of all generated narratives for each event, in chronological order.")
    home_score: int = Field(default=0, description="Current score for the home team.")
    away_score: int = Field(default=0, description="Current score for the away team.")


class LiveNarrative(BaseModel):
    """Structured output for the LiveAgent narrative generation node."""

    narrative: str = Field(default="The generated story-so-far narrative that captures the unfolding drama of the match, based on the current events and scoreline.")


# ---------------------------------------------------------------------------
# Post-match agent output schemas
# ---------------------------------------------------------------------------


class MatchAnalysis(BaseModel):
    """Structured output for the PostMatchAgent match analysis node."""

    match_summary: str
    tactical_analysis: str


class PostMatchReport(BaseModel):
    """Structured output for the PostMatchAgent report generation node."""

    full_report: str


# ---------------------------------------------------------------------------
# Chat agent output schemas
# ---------------------------------------------------------------------------


class ChatResponse(BaseModel):
    """Structured output for the ChatAgent response node."""

    response: str
