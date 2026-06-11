"""
Live match narrative endpoint.

POST /api/live
    Runs the LiveAgent graph on the current event list and returns a
    running score, key moments, and a flowing narrative of the match so far.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.views.schemas import (
    AgentResponse,
    LiveData,
    LiveRequest,
    ResponseMeta,
)
from src.graph import build_live_graph

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/live",
    response_model=AgentResponse[LiveData],
    summary="Generate a live match narrative",
    description=(
        "Runs the LiveAgent: parses the event list to derive the current "
        "score and key moments, then produces an LLM-generated narrative "
        "of the match as it stands. Call on each event update."
    ),
)
async def run_live(request: LiveRequest) -> AgentResponse[LiveData]:
    """
    Parameters
    ----------
    request : LiveRequest
        Current match state including all events that have occurred so far.

    Returns
    -------
    AgentResponse[LiveData]
        Unified envelope with current score, key moments, and narrative.
    """
    logger.info(
        "live | %s vs %s | match_id=%s | events=%d",
        request.home_team,
        request.away_team,
        request.match_id,
        len(request.events),
    )
    start = time.perf_counter()

    graph = build_live_graph()
    state = {
        "match_id": request.match_id,
        "competition_type": request.competition_type,
        "home_team": request.home_team,
        "away_team": request.away_team,
        "events": [e.model_dump() for e in request.events],
        "narrative": [],
        "errors": [],
    }

    try:
        result: dict = await asyncio.to_thread(graph.invoke, state)
    except Exception as exc:
        logger.exception("live | graph failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    errors: list[str] = result.get("errors") or []
    current_score = result.get("current_score") or {"home": 0, "away": 0}
    key_moments = result.get("key_moments") or []

    # LiveState.narrative is typed List[str] but the node writes a bare str.
    # Handle both to stay robust against future agent refactors.
    raw_narrative = result.get("narrative", "")
    if isinstance(raw_narrative, list):
        narrative = raw_narrative[-1] if raw_narrative else ""
    else:
        narrative = raw_narrative or ""

    data = LiveData(
        current_score=current_score,
        key_moments=key_moments,
        narrative=narrative,
    )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("live | completed in %.0fms | errors=%d", duration_ms, len(errors))

    return AgentResponse(
        success=bool(narrative),
        agent="live",
        match_id=request.match_id,
        data=data,
        errors=errors,
        meta=ResponseMeta(
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration_ms, 2),
        ),
    )
