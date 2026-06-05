"""
Offside AI — FastAPI application entry point.

Start the server:
    uvicorn main:app --reload --port 8000

Or via the project script:
    uv run start
"""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from src.config.settings import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Offside AI",
    description=(
        "2026 FIFA World Cup Intelligence Companion. "
        "Pre-match reports, live narratives, post-match analysis, "
        "and conversational Q&A — all powered by LangGraph agents."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(api_router)


@app.get("/health", tags=["System"])
async def health() -> dict:
    """Liveness probe — returns 200 when the server is running."""
    return {"status": "ok", "app": settings.app_name, "version": settings.version}


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------

def main() -> None:
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    main()
