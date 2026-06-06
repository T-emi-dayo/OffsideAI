"""
Match endpoints — metadata and agent invocations per fixture.

GET  /match/{id}            — match metadata + current state
GET  /match/{id}/preview    — PreMatchAgent: pre-match intelligence report
GET  /match/{id}/narrative  — LiveAgent: on-demand live match narrative
GET  /match/{id}/report     — PostMatchAgent: full post-match report
GET  /match/{id}/prediction — PredictionAgent: ML outcome probabilities
POST /match/{id}/chat       — ChatAgent: conversational Q&A
"""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from app.api.helpers import (
    build_match_input,
    normalize_events,
    now_iso,
    to_fixture_item,
)
from app.services.DataService import DataService, get_data_service
from app.views.schemas import (
    AgentResponse,
    ChatData,
    ChatMessage,
    ChatRequest,
    DataResponse,
    LiveData,
    MatchMetadata,
    PostMatchData,
    PreMatchData,
    PredictionData,
    ResponseMeta,
    FixtureScore,
)
from src.graph import (
    build_chat_graph,
    build_live_graph,
    build_postmatch_graph,
    build_prematch_graph,
)
from src.schemas.state import MatchState
from src.services.PredictionService import PredictionService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared dependency
# ---------------------------------------------------------------------------

async def _get_ds() -> DataService:
    service = get_data_service()
    await service.initialize()
    return service


# ---------------------------------------------------------------------------
# GET /match/{match_id}  — match metadata
# ---------------------------------------------------------------------------

@router.get(
    "/match/{match_id}",
    response_model=DataResponse[MatchMetadata],
    summary="Get match metadata and current lifecycle state",
)
async def get_match(
    match_id: int,
    ds: DataService = Depends(_get_ds),
) -> DataResponse[MatchMetadata]:
    start = time.perf_counter()

    try:
        match = await ds.get_match(match_id)
    except Exception as exc:
        logger.exception("match/%d | DataService failed: %s", match_id, exc)
        raise HTTPException(status_code=503, detail=f"Data service unavailable: {exc}")

    mi = build_match_input(match)
    score_raw = mi.pop("_score", {})
    group = mi.pop("_group", None)

    duration_ms = (time.perf_counter() - start) * 1000
    return DataResponse(
        data=MatchMetadata(
            match_id=mi["match_id"],
            home_team=mi["home_team"],
            away_team=mi["away_team"],
            match_date=mi["match_date"],
            stage=mi["stage"],
            group=group,
            match_state=mi["match_state"],
            score=FixtureScore(
                home=score_raw.get("home"),
                away=score_raw.get("away"),
            ),
        ),
        meta=ResponseMeta(timestamp=now_iso(), duration_ms=round(duration_ms, 2)),
    )


# ---------------------------------------------------------------------------
# GET /match/{match_id}/preview  — PreMatchAgent
# ---------------------------------------------------------------------------

@router.get(
    "/match/{match_id}/preview",
    response_model=AgentResponse[PreMatchData],
    summary="Generate a pre-match intelligence report",
    description=(
        "Fetches match metadata from football-data.org, then runs the "
        "PreMatchAgent: gathers H2H records, recent form, FIFA rankings, "
        "and WC history, runs the Dixon-Coles ML model, and synthesises a "
        "full pre-match report narrative."
    ),
)
async def get_preview(
    match_id: int,
    ds: DataService = Depends(_get_ds),
) -> AgentResponse[PreMatchData]:
    start = time.perf_counter()

    try:
        match = await ds.get_match(match_id)
    except Exception as exc:
        logger.exception("preview/%d | DataService failed: %s", match_id, exc)
        raise HTTPException(status_code=503, detail=f"Data service unavailable: {exc}")

    mi = build_match_input(match)
    mi.pop("_score", None)
    mi.pop("_group", None)

    logger.info(
        "preview | %s vs %s | match_id=%d",
        mi["home_team"],
        mi["away_team"],
        match_id,
    )

    graph = build_prematch_graph()
    try:
        result: dict = await asyncio.to_thread(graph.invoke, mi)
    except Exception as exc:
        logger.exception("preview | graph failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    errors: list[str] = result.get("errors") or []
    prediction = result.get("prediction")
    report_narrative = result.get("report_narrative")

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("preview | completed in %.0fms | errors=%d", duration_ms, len(errors))

    return AgentResponse(
        success=report_narrative is not None,
        agent="prematch",
        match_id=str(match_id),
        data=PreMatchData(prediction=prediction, report_narrative=report_narrative),
        errors=errors,
        meta=ResponseMeta(timestamp=now_iso(), duration_ms=round(duration_ms, 2)),
    )


# ---------------------------------------------------------------------------
# GET /match/{match_id}/narrative  — LiveAgent
# ---------------------------------------------------------------------------

@router.get(
    "/match/{match_id}/narrative",
    response_model=AgentResponse[LiveData],
    summary="Generate a live match narrative",
    description=(
        "Fetches live match events from football-data.org, then runs the "
        "LiveAgent to produce a story-so-far narrative. Must be called while "
        "the match is in progress."
    ),
)
async def get_narrative(
    match_id: int,
    ds: DataService = Depends(_get_ds),
) -> AgentResponse[LiveData]:
    start = time.perf_counter()

    try:
        match = await ds.get_match(
            match_id,
            unfold={"goals": True, "bookings": True},
        )
    except Exception as exc:
        logger.exception("narrative/%d | DataService failed: %s", match_id, exc)
        raise HTTPException(status_code=503, detail=f"Data service unavailable: {exc}")

    mi = build_match_input(match)
    mi.pop("_score", None)
    mi.pop("_group", None)

    if mi["match_state"] != "live":
        raise HTTPException(
            status_code=400,
            detail=f"Match {match_id} is not currently live (state: {mi['match_state']}).",
        )

    events = normalize_events(match, str(match_id))
    mi["events"] = events

    logger.info(
        "narrative | %s vs %s | events=%d | match_id=%d",
        mi["home_team"],
        mi["away_team"],
        len(events),
        match_id,
    )

    graph = build_live_graph()
    try:
        result: dict = await asyncio.to_thread(graph.invoke, mi)
    except Exception as exc:
        logger.exception("narrative | graph failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    errors: list[str] = result.get("errors") or []
    narrative: str = result.get("narrative") or ""

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("narrative | completed in %.0fms | errors=%d", duration_ms, len(errors))

    return AgentResponse(
        success=bool(narrative),
        agent="live",
        match_id=str(match_id),
        data=LiveData(
            current_score=result.get("current_score") or {"home": 0, "away": 0},
            key_moments=result.get("key_moments") or [],
            narrative=narrative,
        ),
        errors=errors,
        meta=ResponseMeta(timestamp=now_iso(), duration_ms=round(duration_ms, 2)),
    )


# ---------------------------------------------------------------------------
# GET /match/{match_id}/report  — PostMatchAgent
# ---------------------------------------------------------------------------

@router.get(
    "/match/{match_id}/report",
    response_model=AgentResponse[PostMatchData],
    summary="Generate a post-match report",
    description=(
        "Fetches completed match data from football-data.org, then runs the "
        "PostMatchAgent to produce key moments, player highlights, tactical "
        "analysis, and a full report narrative. Only valid for finished matches."
    ),
)
async def get_report(
    match_id: int,
    ds: DataService = Depends(_get_ds),
) -> AgentResponse[PostMatchData]:
    start = time.perf_counter()

    try:
        match = await ds.get_match(
            match_id,
            unfold={"goals": True, "bookings": True},
        )
    except Exception as exc:
        logger.exception("report/%d | DataService failed: %s", match_id, exc)
        raise HTTPException(status_code=503, detail=f"Data service unavailable: {exc}")

    mi = build_match_input(match)
    score_raw = mi.pop("_score", {})
    mi.pop("_group", None)

    if mi["match_state"] != "post":
        raise HTTPException(
            status_code=400,
            detail=f"Match {match_id} is not finished (state: {mi['match_state']}).",
        )

    events = normalize_events(match, str(match_id))
    mi["events"] = events
    mi["final_score"] = {
        "home": score_raw.get("home") or 0,
        "away": score_raw.get("away") or 0,
    }
    mi["pre_match_analysis"] = {}  # not persisted in v1 — PostMatchAgent degrades gracefully

    logger.info(
        "report | %s vs %s | events=%d | score=%s | match_id=%d",
        mi["home_team"],
        mi["away_team"],
        len(events),
        mi["final_score"],
        match_id,
    )

    graph = build_postmatch_graph()
    try:
        result: dict = await asyncio.to_thread(graph.invoke, mi)
    except Exception as exc:
        logger.exception("report | graph failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    errors: list[str] = result.get("errors") or []
    full_report = result.get("full_report")

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("report | completed in %.0fms | errors=%d", duration_ms, len(errors))

    return AgentResponse(
        success=full_report is not None,
        agent="postmatch",
        match_id=str(match_id),
        data=PostMatchData(
            key_moments=result.get("key_moments") or [],
            player_highlights=result.get("player_highlights") or [],
            match_summary=result.get("match_summary"),
            tactical_analysis=result.get("tactical_analysis"),
            full_report=full_report,
        ),
        errors=errors,
        meta=ResponseMeta(timestamp=now_iso(), duration_ms=round(duration_ms, 2)),
    )


# ---------------------------------------------------------------------------
# GET /match/{match_id}/prediction  — PredictionService (no agent overhead)
# ---------------------------------------------------------------------------

@router.get(
    "/match/{match_id}/prediction",
    response_model=AgentResponse[PredictionData],
    summary="Get ML outcome probabilities for a fixture",
    description=(
        "Fetches team names from football-data.org, then runs the Dixon-Coles "
        "model to return win/draw/loss probabilities and expected goals."
    ),
)
async def get_prediction(
    match_id: int,
    ds: DataService = Depends(_get_ds),
) -> AgentResponse[PredictionData]:
    start = time.perf_counter()

    try:
        match = await ds.get_match(match_id)
    except Exception as exc:
        logger.exception("prediction/%d | DataService failed: %s", match_id, exc)
        raise HTTPException(status_code=503, detail=f"Data service unavailable: {exc}")

    mi = build_match_input(match)
    mi.pop("_score", None)
    mi.pop("_group", None)

    home_team = mi["home_team"]
    away_team = mi["away_team"]
    neutral = mi["competition_type"] == "world_cup"

    logger.info(
        "prediction | %s vs %s | neutral=%s | match_id=%d",
        home_team,
        away_team,
        neutral,
        match_id,
    )

    try:
        pred = await asyncio.to_thread(
            PredictionService().predict_results,
            home_team,
            away_team,
            neutral,
        )
        errors: list[str] = []
        data = PredictionData(
            home_team=home_team,
            away_team=away_team,
            p_home=pred.get("p_home"),
            p_draw=pred.get("p_draw"),
            p_away=pred.get("p_away"),
            lambda_home=pred.get("lambda_home"),
            lambda_away=pred.get("lambda_away"),
        )
    except Exception as exc:
        logger.error("prediction | model failed: %s", exc)
        errors = [str(exc)]
        data = PredictionData(home_team=home_team, away_team=away_team)

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("prediction | completed in %.0fms", duration_ms)

    return AgentResponse(
        success=data.p_home is not None,
        agent="prediction",
        match_id=str(match_id),
        data=data,
        errors=errors,
        meta=ResponseMeta(timestamp=now_iso(), duration_ms=round(duration_ms, 2)),
    )


# ---------------------------------------------------------------------------
# POST /match/{match_id}/chat  — ChatAgent
# ---------------------------------------------------------------------------

def _build_lc_messages(history: list[ChatMessage], new_message: str) -> list:
    """Convert API history + new message into LangChain message objects."""
    messages = []
    for msg in history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))
    messages.append(HumanMessage(content=new_message))
    return messages


def _extract_reply(messages: list) -> str:
    """Return the content of the last AIMessage in the message list."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    return ""


@router.post(
    "/match/{match_id}/chat",
    response_model=AgentResponse[ChatData],
    summary="Conversational Q&A about a World Cup fixture",
    description=(
        "Runs the ChatAgent: answers questions about the fixture using "
        "historical data, rankings, form, and World Cup records. "
        "The caller manages session state by storing and re-sending "
        "`data.history` on every request."
    ),
)
async def post_chat(
    match_id: int,
    request: ChatRequest,
) -> AgentResponse[ChatData]:
    start = time.perf_counter()

    logger.info(
        "chat | %s vs %s | match_id=%d | state=%s | history_len=%d",
        request.home_team,
        request.away_team,
        match_id,
        request.match_state,
        len(request.history),
    )

    graph = build_chat_graph()
    lc_messages = _build_lc_messages(request.history, request.message)

    state = {
        "match_id": str(match_id),
        "home_team": request.home_team,
        "away_team": request.away_team,
        "match_state": MatchState(request.match_state),
        "live_context": request.live_context,
        "messages": lc_messages,
        "errors": [],
    }

    try:
        result: dict = await asyncio.to_thread(graph.invoke, state)
    except Exception as exc:
        logger.exception("chat | graph failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    errors: list[str] = result.get("errors") or []
    reply = _extract_reply(result.get("messages", []))
    sources_used: list[str] = result.get("sources_used") or []

    updated_history = [
        *request.history,
        ChatMessage(role="user", content=request.message),
        ChatMessage(role="assistant", content=reply),
    ]

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "chat | completed in %.0fms | sources=%s | errors=%d",
        duration_ms,
        sources_used,
        len(errors),
    )

    return AgentResponse(
        success=bool(reply),
        agent="chat",
        match_id=str(match_id),
        data=ChatData(reply=reply, sources_used=sources_used, history=updated_history),
        errors=errors,
        meta=ResponseMeta(timestamp=now_iso(), duration_ms=round(duration_ms, 2)),
    )
