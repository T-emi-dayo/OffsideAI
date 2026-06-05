from __future__ import annotations

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    pass


# ---------------------------------------------------------------------------
# Pre-match agent output schemas
# ---------------------------------------------------------------------------


class PreMatchReport(BaseModel):
    """Structured output for the PreMatchAgent report generation node."""

    prediction : str = Field(default="The explained prediction of the ml model")
    match_context : str = Field(default="The background context of the match, including h2h, form, rankings, and WC history")
    report_narrative : str = Field(default="The final pre-match report narrative synthesised by the LLM, combining the prediction and context into a coherent analysis.")

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
