"""
Aggregated API router.

Route structure (all prefixed /api):
  GET  /fixtures                    — list all WC fixtures
  GET  /fixtures/today              — today's fixtures
  GET  /fixtures/live               — currently live fixtures
  GET  /match/{id}                  — match metadata
  GET  /match/{id}/preview          — PreMatchAgent report
  GET  /match/{id}/narrative        — LiveAgent narrative
  GET  /match/{id}/report           — PostMatchAgent report
  GET  /match/{id}/prediction       — ML outcome probabilities
  POST /match/{id}/chat             — ChatAgent Q&A
"""

from fastapi import APIRouter

from app.api.routes import fixtures, match

api_router = APIRouter(prefix="/api")

api_router.include_router(fixtures.router, tags=["Fixtures"])
api_router.include_router(match.router, tags=["Match"])
