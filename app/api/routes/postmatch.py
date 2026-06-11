"""
Post-match report endpoint.

POST /api/postmatch
    Runs the PostMatchAgent graph and returns key moments, player highlights,
    tactical analysis, and a full match report narrative.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.views.schemas import (
    AgentResponse,
    PostMatchData,
    PostMatchRequest,
    ResponseMeta,
)
from src.graph import build_postmatch_graph

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/postmatch",
    response_model=AgentResponse[PostMatchData],
    summary="Generate a post-match report",
    description=(
        "Runs the PostMatchAgent: extracts key moments and player highlights "
        "from the event log, produces a tactical analysis, and synthesises "
        "a full post-match report narrative."
    ),
)
async def run_postmatch(request: PostMatchRequest) -> AgentResponse[PostMatchData]:
    """
    Parameters
    ----------
    request : PostMatchRequest
        Completed match data including final score and full event log.

    Returns
    -------
    AgentResponse[PostMatchData]
        Unified envelope with analysis, highlights, and full report.
    """
    logger.info(
        "postmatch | %s vs %s | match_id=%s | events=%d",
        request.home_team,
        request.away_team,
        request.match_id,
        len(request.match_events),
    )
    start = time.perf_counter()

    graph = build_postmatch_graph()
    state = {
        "match_id": request.match_id,
        "competition_type": request.competition_type,
        "home_team": request.home_team,
        "away_team": request.away_team,
        "final_score": request.final_score,
        "match_events": [e.model_dump() for e in request.match_events],
        "pre_match_analysis": request.pre_match_analysis,
        "errors": [],
    }

    try:
        result: dict = await asyncio.to_thread(graph.invoke, state)
    except Exception as exc:
        logger.exception("postmatch | graph failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    errors: list[str] = result.get("errors") or []
    full_report = result.get("full_report")

    data = PostMatchData(
        key_moments=result.get("key_moments") or [],
        player_highlights=result.get("player_highlights") or [],
        match_summary=result.get("match_summary"),
        tactical_analysis=result.get("tactical_analysis"),
        full_report=full_report,
    )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("postmatch | completed in %.0fms | errors=%d", duration_ms, len(errors))

    return AgentResponse(
        success=full_report is not None,
        agent="postmatch",
        match_id=request.match_id,
        data=data,
        errors=errors,
        meta=ResponseMeta(
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration_ms, 2),
        ),
    )
