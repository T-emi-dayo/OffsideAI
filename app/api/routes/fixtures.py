"""
Fixture listing endpoints.

GET /fixtures           — all 2026 World Cup fixtures
GET /fixtures/today     — fixtures scheduled for today
GET /fixtures/live      — currently live fixtures
"""

from __future__ import annotations

import logging
import time
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.api.helpers import now_iso, to_fixture_item
from app.services.DataService import DataService, get_data_service
from app.views.schemas import DataResponse, FixtureListData, ResponseMeta

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_ds() -> DataService:
    """Ensure the DataService client is initialised before each request."""
    service = get_data_service()
    await service.initialize()
    return service


@router.get(
    "/fixtures",
    response_model=DataResponse[FixtureListData],
    summary="List all 2026 World Cup fixtures",
)
async def list_fixtures(
    ds: DataService = Depends(_get_ds),
) -> DataResponse[FixtureListData]:
    start = time.perf_counter()
    try:
        matches = await ds.get_world_cup_matches()
    except Exception as exc:
        logger.exception("fixtures | DataService failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Data service unavailable: {exc}")

    fixtures = [to_fixture_item(m) for m in matches]
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("fixtures | returned %d fixtures in %.0fms", len(fixtures), duration_ms)

    return DataResponse(
        data=FixtureListData(count=len(fixtures), fixtures=fixtures),
        meta=ResponseMeta(timestamp=now_iso(), duration_ms=round(duration_ms, 2)),
    )


@router.get(
    "/fixtures/today",
    response_model=DataResponse[FixtureListData],
    summary="List fixtures scheduled for today",
)
async def list_today_fixtures(
    ds: DataService = Depends(_get_ds),
) -> DataResponse[FixtureListData]:
    start = time.perf_counter()
    today = date.today().isoformat()

    try:
        matches = await ds.get_world_cup_matches(date_from=today, date_to=today)
    except Exception as exc:
        logger.exception("fixtures/today | DataService failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Data service unavailable: {exc}")

    fixtures = [to_fixture_item(m) for m in matches]
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("fixtures/today | %d fixtures for %s in %.0fms", len(fixtures), today, duration_ms)

    return DataResponse(
        data=FixtureListData(count=len(fixtures), fixtures=fixtures),
        meta=ResponseMeta(timestamp=now_iso(), duration_ms=round(duration_ms, 2)),
    )


@router.get(
    "/fixtures/live",
    response_model=DataResponse[FixtureListData],
    summary="List currently live fixtures",
)
async def list_live_fixtures(
    ds: DataService = Depends(_get_ds),
) -> DataResponse[FixtureListData]:
    start = time.perf_counter()

    try:
        # football-data.org uses LIVE and IN_PLAY for live matches
        matches = await ds.get_world_cup_matches(status="IN_PLAY")
    except Exception as exc:
        logger.exception("fixtures/live | DataService failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Data service unavailable: {exc}")

    fixtures = [to_fixture_item(m) for m in matches]
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("fixtures/live | %d live fixtures in %.0fms", len(fixtures), duration_ms)

    return DataResponse(
        data=FixtureListData(count=len(fixtures), fixtures=fixtures),
        meta=ResponseMeta(timestamp=now_iso(), duration_ms=round(duration_ms, 2)),
    )
