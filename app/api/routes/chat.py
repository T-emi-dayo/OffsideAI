"""
Conversational Q&A endpoint.

POST /api/chat
    Runs the ChatAgent graph and returns the AI reply plus updated history.

    The API is stateless — the caller owns conversation history and sends
    the full `history` list on every request. The response returns an
    updated `history` ready for the next call.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from app.views.schemas import (
    AgentResponse,
    ChatData,
    ChatMessage,
    ChatRequest,
    ResponseMeta,
)
from src.graph import build_chat_graph
from src.schemas.state import MatchState

logger = logging.getLogger(__name__)

router = APIRouter()


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


def _updated_history(
    history: list[ChatMessage], new_message: str, reply: str
) -> list[ChatMessage]:
    """Append the new user turn and AI reply to the conversation history."""
    return [
        *history,
        ChatMessage(role="user", content=new_message),
        ChatMessage(role="assistant", content=reply),
    ]


@router.post(
    "/chat",
    response_model=AgentResponse[ChatData],
    summary="Conversational Q&A about a World Cup fixture",
    description=(
        "Runs the ChatAgent: answers user questions about the fixture using "
        "historical data, rankings, form, and WC records. The caller manages "
        "session state by storing and re-sending `data.history` each request."
    ),
)
async def run_chat(request: ChatRequest) -> AgentResponse[ChatData]:
    """
    Parameters
    ----------
    request : ChatRequest
        The new user message plus full conversation history and match context.

    Returns
    -------
    AgentResponse[ChatData]
        Unified envelope with the AI reply, sources used, and updated history.
    """
    logger.info(
        "chat | %s vs %s | match_id=%s | state=%s | history_len=%d",
        request.home_team,
        request.away_team,
        request.match_id,
        request.match_state,
        len(request.history),
    )
    start = time.perf_counter()

    graph = build_chat_graph()
    lc_messages = _build_lc_messages(request.history, request.message)

    state = {
        "match_id": request.match_id,
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
    history = _updated_history(request.history, request.message, reply)

    data = ChatData(
        reply=reply,
        sources_used=sources_used,
        history=history,
    )

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
        match_id=request.match_id,
        data=data,
        errors=errors,
        meta=ResponseMeta(
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=round(duration_ms, 2),
        ),
    )
