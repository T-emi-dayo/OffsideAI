"""Aggregated API router — mounts all agent routes under /api."""

from fastapi import APIRouter

from app.api.routes import chat, live, postmatch, prematch

api_router = APIRouter(prefix="/api")

api_router.include_router(prematch.router, tags=["Pre-Match"])
api_router.include_router(live.router, tags=["Live"])
api_router.include_router(postmatch.router, tags=["Post-Match"])
api_router.include_router(chat.router, tags=["Chat"])
