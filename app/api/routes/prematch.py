"""
Pre-match report endpoint.

POST /api/prematch
    Runs the PreMatchAgent graph and returns a structured intelligence report
    containing ML outcome probabilities and an LLM narrative.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.views.schemas import (
    AgentResponse,
    PreMatchData,
    PreMatchRequest,
    ResponseMeta,
)
from src.graph import build_prematch_graph

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/prematch",
    response_model=AgentResponse[PreMatchData],
    summary="Generate a pre-match intelligence report",
    description=(
        "Runs the PreMatchAgent: gathers head-to-head records, recent form, "
        "FIFA rankings, and World Cup history, then produces ML outcome "
        "probabilities and an LLM-generated narrative report."
    ),
)
async def run_prematch(request: PreMatchRequest) -> AgentResponse[PreMatchData]:
    """
    Parameters
    ----------
    request : PreMatchRequest
        Match details required to run the pre-match analysis.

    Returns
    -------
    AgentResponse[PreMatchData]
        Unified envelope containing prediction probabilities and narrative.
    """
    logger.info(
        "prematch | %s vs %s | match_id=%s",
        request.home_team,
        request.away_team,
        request.match_id,
    )
    start = time.perf_counter()

    graph = build_prematch_graph()
    state = {
        "match_id": request.match_id,
        "competition_type": request.competition_type,
        "home_team": request.home_team,
        "away_team": request.away_team,
        "match_date": request.match_date,
        "stage": request.stage,
        "errors": [],
    }

    try:
        result: dict = await asyncio.to_thread(graph.invoke, state)
    except Exception as exc:
        logger.exception("prematch | graph failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    errors: list[str] = result.get("errors") or []
    prediction = result.get("prediction")
    report_narrative = result.get("report_narrative")

    data = PreMatchData(
        prediction=prediction,
        report_narrative=report_narrative,
    )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("prematch | completed in %.0fms | errors=%d", duration_ms, len(errors))

    return AgentResponse(
        success=report_narrative is not None,
        agent="prematch",
        match_id=request.match_id,
        data=data,
        errors=errors,
        meta=ResponseMeta(
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration_ms, 2),
        ),
    )
