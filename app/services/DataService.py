"""
Football-Data.org v4 Data Service for Offside AI.

Docs     : https://docs.football-data.org/general/v4/index.html
Base URL : https://api.football-data.org/v4
Auth     : X-Auth-Token header (every request)
Methods  : GET only

Resources & sub-resources
--------------------------
Main resources : Area, Competition, Match, Team, Person
Sub-resources always hang off a parent:
    /competitions/{id}/standings
    /competitions/{id}/matches
    /competitions/{id}/teams
    /competitions/{id}/scorers
    /teams/{id}/matches
    /persons/{id}/matches
    /matches/{id}/head2head

Automatic folding (v4 behaviour)
----------------------------------
Match lists fold lineups / bookings / substitutions / goals by default
to save bandwidth. Unfold selectively via request headers:
    X-Unfold-Lineups   : true | false
    X-Unfold-Bookings  : true | false
    X-Unfold-Subs      : true | false
    X-Unfold-Goals     : true | false

Pagination
----------
Use `limit` (1–500) and `offset` query params.
List responses include a `count` or `resultSet.count` field.

Rate limits (per plan)
-----------------------
Free     : 10 req/min
Standard : 30 req/min
Premium+ : 60 req/min
Response headers:
    X-RequestsAvailable    – remaining requests before block
    X-RequestCounter-Reset – seconds until counter resets

HTTP status codes
-----------------
200  OK
400  Bad request / invalid filter
403  Restricted resource (plan tier)
404  Resource not found
429  Rate limit exceeded → back-off and retry
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Literal

import httpx

from app.services.mock_world_cup_data import filter_mock_matches, get_mock_match
from src.config.settings import settings
from src.services.base_service import BaseService, ServiceError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://api.football-data.org/v4"

# Competition codes for named lookups (use instead of numeric IDs where possible)
COMPETITION_CODES: dict[str, int] = {
    "WC":   2000,  # FIFA World Cup
    "CL":   2001,  # UEFA Champions League
    "BL1":  2002,  # Bundesliga
    "DED":  2003,  # Eredivisie
    "EC":   2018,  # European Championship
    "SA":   2019,  # Serie A
    "PL":   2021,  # Premier League
    "PD":   2014,  # Primera Division (La Liga)
    "FL1":  2015,  # Ligue 1
    "BSA":  2013,  # Campeonato Brasileiro Série A
    "CA":   2080,  # Copa América
    "EL":   2146,  # UEFA Europa League
    "MLS":  2145,  # MLS
    "CLI":  2152,  # Copa Libertadores
}

WC_CODE = "WC"


# ---------------------------------------------------------------------------
# Type aliases (match the lookup tables in the Football-Data docs)
# ---------------------------------------------------------------------------

MatchStatus = Literal[
    "SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "EXTRA_TIME",
    "PENALTY_SHOOTOUT", "FINISHED", "SUSPENDED", "POSTPONED",
    "CANCELLED", "AWARDED", "LIVE",
]

MatchStage = Literal[
    "FINAL", "THIRD_PLACE", "SEMI_FINALS", "QUARTER_FINALS",
    "LAST_16", "LAST_32", "LAST_64", "ROUND_4", "ROUND_3", "ROUND_2",
    "ROUND_1", "GROUP_STAGE", "PRELIMINARY_ROUND", "QUALIFICATION",
    "QUALIFICATION_ROUND_1", "QUALIFICATION_ROUND_2", "QUALIFICATION_ROUND_3",
    "PLAYOFF_ROUND_1", "PLAYOFF_ROUND_2", "PLAYOFFS", "REGULAR_SEASON",
    "CLAUSURA", "APERTURA", "CHAMPIONSHIP_ROUND", "RELEGATION_ROUND",
]

MatchGroup = Literal[
    "GROUP_A", "GROUP_B", "GROUP_C", "GROUP_D", "GROUP_E", "GROUP_F",
    "GROUP_G", "GROUP_H", "GROUP_I", "GROUP_J", "GROUP_K", "GROUP_L",
]

Venue = Literal["HOME", "AWAY"]

LineupPosition = Literal["STARTING", "BENCH"]

PersonEvent = Literal["GOAL", "ASSIST", "SUB_IN", "SUB_OUT"]


# ---------------------------------------------------------------------------
# Cache TTLs (seconds)
# ---------------------------------------------------------------------------

class CacheTTL:
    LIVE      = 15       # live match events
    SHORT     = 60       # scorers, live standings
    MEDIUM    = 300      # match lists (upcoming/finished)
    LONG      = 3_600    # team profiles, standings snapshots
    REFERENCE = 86_400   # areas, competition lists


# ---------------------------------------------------------------------------
# In-memory TTL cache
# ---------------------------------------------------------------------------

class _TTLCache:
    """Simple dict-backed cache with per-entry TTL.

    Designed for single-threaded asyncio use — no locking required.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    @staticmethod
    def _key(path: str, params: dict[str, Any], headers: dict[str, str]) -> str:
        raw = json.dumps({"p": path, "q": params, "h": headers}, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, path: str, params: dict[str, Any], headers: dict[str, str]) -> Any | None:
        """Return cached value if still valid, else None."""
        key = self._key(path, params, headers)
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(
        self,
        path: str,
        params: dict[str, Any],
        headers: dict[str, str],
        value: Any,
        ttl: int,
    ) -> None:
        """Store a value with an expiry TTL (seconds from now)."""
        key = self._key(path, params, headers)
        self._store[key] = (value, time.monotonic() + ttl)

    def clear(self) -> None:
        """Evict all cached entries."""
        self._store.clear()


# ---------------------------------------------------------------------------
# DataService
# ---------------------------------------------------------------------------

class DataService(BaseService):
    """Async HTTP client for Football-Data.org v4.

    Covers all main resources (Areas, Competitions, Matches, Teams, Persons)
    and their sub-resources. Adds two-tier TTL caching, rate-limit back-off,
    transient-error retries, and unfold-header support.

    Usage
    -----
    service = DataService()
    await service.initialize()

    matches = await service.get_competition_matches("WC", season=2026)

    await service.close()

    Notes
    -----
    Prefer `get_data_service()` so the HTTP client and cache are shared
    across all callers in the same process.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._cache = _TTLCache()

    # -----------------------------------------------------------------------
    # Lifecycle — BaseService interface
    # -----------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create the underlying async HTTP client.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=_BASE_URL,
                headers={
                    "X-Auth-Token": settings.FOOTBALL_DATA_ORG_KEY,
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
            logger.info("DataService initialised — base URL: %s", _BASE_URL)

    async def close(self) -> None:
        """Release the underlying HTTP client.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("DataService HTTP client closed.")

    async def health_check(self) -> bool:
        """Return True if the API is reachable and the token is valid.

        Parameters
        ----------
        None

        Returns
        -------
        bool
            True when /competitions returns a non-empty response.
        """
        try:
            result = await self._get("competitions")
            return bool(result.get("competitions"))
        except Exception as exc:
            logger.warning("DataService health check failed: %s", exc)
            return False

    # -----------------------------------------------------------------------
    # Core HTTP layer (private)
    # -----------------------------------------------------------------------

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        unfold: dict[str, bool] | None = None,
        cache_ttl: int | None = None,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ) -> dict[str, Any]:
        """Execute a single authenticated GET request.

        Parameters
        ----------
        path : str
            Endpoint path relative to the base URL (e.g. "competitions/WC/matches").
        params : dict[str, Any] | None
            Query parameters — None values are stripped automatically.
        unfold : dict[str, bool] | None
            Controls automatic folding. Keys: lineups, bookings, subs, goals.
        cache_ttl : int | None
            Seconds to cache the response. None disables caching.
        max_retries : int
            Maximum retry attempts for transient errors.
        backoff_base : float
            Exponential back-off base: sleep = base ^ attempt seconds.

        Returns
        -------
        dict[str, Any]
            Parsed JSON response body.

        Raises
        ------
        ServiceError
            On HTTP errors or when all retry attempts are exhausted.
        """
        if self._client is None or self._client.is_closed:
            await self.initialize()

        clean_params = _drop_none(params or {})
        unfold_headers = _build_unfold_headers(unfold or {})

        if cache_ttl is not None:
            hit = self._cache.get(path, clean_params, unfold_headers)
            if hit is not None:
                logger.debug("Cache hit — %s %s", path, clean_params)
                return hit

        url = f"/{path.lstrip('/')}"
        attempts = 0

        while attempts < max_retries:
            attempts += 1
            try:
                resp = await self._client.get(
                    url,
                    params=clean_params,
                    headers=unfold_headers,
                )
                self._log_rate_limits(resp.headers)

                if resp.status_code == 429:
                    reset_in = int(resp.headers.get("X-RequestCounter-Reset", 60))
                    wait = max(float(reset_in), backoff_base ** attempts)
                    logger.warning(
                        "Rate limited — retrying in %.1fs (attempt %d/%d).",
                        wait, attempts, max_retries,
                    )
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    wait = backoff_base ** attempts
                    logger.warning(
                        "Server error %d — retrying in %.1fs (attempt %d/%d).",
                        resp.status_code, wait, attempts, max_retries,
                    )
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code == 403:
                    raise ServiceError(
                        f"Access denied for '{path}' — resource may require a higher plan tier."
                    )

                resp.raise_for_status()
                data: dict[str, Any] = resp.json()

                if cache_ttl is not None:
                    self._cache.set(path, clean_params, unfold_headers, data, cache_ttl)

                return data

            except httpx.TimeoutException:
                wait = backoff_base ** attempts
                logger.warning(
                    "Request timed out — retrying in %.1fs (attempt %d/%d).",
                    wait, attempts, max_retries,
                )
                await asyncio.sleep(wait)

            except ServiceError:
                raise

            except httpx.HTTPStatusError as exc:
                raise ServiceError(
                    f"HTTP {exc.response.status_code} for '{path}'."
                ) from exc

        raise ServiceError(f"All {max_retries} attempts failed for '{path}'.")

    async def _get_paginated(
        self,
        path: str,
        list_key: str,
        params: dict[str, Any] | None = None,
        *,
        unfold: dict[str, bool] | None = None,
        page_size: int = 100,
        cache_ttl: int | None = None,
    ) -> list[Any]:
        """Fetch all pages for an endpoint and return a flat list.

        Parameters
        ----------
        path : str
            Endpoint path.
        list_key : str
            JSON key that holds the list in the response (e.g. "matches").
        params : dict[str, Any] | None
            Query parameters.
        unfold : dict[str, bool] | None
            Unfold headers for match detail.
        page_size : int
            Items per page (maps to `limit`, max 500).
        cache_ttl : int | None
            Per-page cache TTL in seconds.

        Returns
        -------
        list[Any]
            All items across every page, as a flat list.
        """
        params = dict(params or {})
        params["limit"] = page_size
        all_items: list[Any] = []
        offset = 0

        while True:
            params["offset"] = offset
            result = await self._get(path, params, unfold=unfold, cache_ttl=cache_ttl)
            page_items = result.get(list_key, [])
            all_items.extend(page_items)

            total = (
                result.get("resultSet", {}).get("count")
                or result.get("count")
                or 0
            )

            if len(all_items) >= total or len(page_items) < page_size:
                break

            offset += page_size
            await asyncio.sleep(0.4)  # polite inter-page delay

        return all_items

    # -----------------------------------------------------------------------
    # Areas
    # -----------------------------------------------------------------------

    async def list_areas(self) -> list[dict]:
        """Return all areas (countries / confederations).

        Returns
        -------
        list[dict]
            Area objects with id, name, code, and flag.
        """
        result = await self._get("areas", cache_ttl=CacheTTL.REFERENCE)
        return result.get("areas", [])

    async def get_area(self, area_id: int) -> dict[str, Any]:
        """Fetch a single area by ID.

        Parameters
        ----------
        area_id : int
            Area ID.

        Returns
        -------
        dict[str, Any]
            Area object.
        """
        return await self._get(f"areas/{area_id}", cache_ttl=CacheTTL.REFERENCE)

    # -----------------------------------------------------------------------
    # Competitions
    # -----------------------------------------------------------------------

    async def list_competitions(self, *, areas: str | None = None) -> list[dict]:
        """List all available competitions.

        Parameters
        ----------
        areas : str | None
            Comma-separated area IDs to filter (e.g. "2072,2224").

        Returns
        -------
        list[dict]
            Competition objects.
        """
        params = _drop_none(areas=areas)
        result = await self._get("competitions", params, cache_ttl=CacheTTL.REFERENCE)
        return result.get("competitions", [])

    async def get_competition(self, competition: str | int) -> dict[str, Any]:
        """Fetch a single competition by code or ID.

        Parameters
        ----------
        competition : str | int
            Competition code (e.g. "WC", "PL") or numeric ID.

        Returns
        -------
        dict[str, Any]
            Competition object with current season info.
        """
        return await self._get(f"competitions/{competition}", cache_ttl=CacheTTL.LONG)

    async def get_standings(
        self,
        competition: str | int,
        *,
        season: int | None = None,
        matchday: int | None = None,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Fetch standings for a competition.

        Parameters
        ----------
        competition : str | int
            Competition code or ID.
        season : int | None
            4-digit start year (e.g. 2026).
        matchday : int | None
            Snapshot standings as of a specific matchday.
        date : str | None
            Snapshot standings as of a specific date "yyyy-MM-dd".

        Returns
        -------
        dict[str, Any]
            Full standings response including TOTAL, HOME, and AWAY tables.

        Notes
        -----
        Returns 404 for CUP and PLAYOFFS competition types.
        """
        params = _drop_none(season=season, matchday=matchday, date=date)
        return await self._get(
            f"competitions/{competition}/standings", params, cache_ttl=CacheTTL.LONG
        )

    async def get_competition_matches(
        self,
        competition: str | int,
        *,
        season: int | None = None,
        matchday: int | None = None,
        status: MatchStatus | None = None,
        stage: MatchStage | None = None,
        group: MatchGroup | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        unfold: dict[str, bool] | None = None,
    ) -> list[dict]:
        """Fetch matches for a competition.

        Parameters
        ----------
        competition : str | int
            Competition code or ID.
        season : int | None
            4-digit start year.
        matchday : int | None
            Specific matchday number.
        status : MatchStatus | None
            Match status filter.
        stage : MatchStage | None
            Tournament stage filter (e.g. "GROUP_STAGE", "FINAL").
        group : MatchGroup | None
            Group filter (e.g. "GROUP_A").
        date_from : str | None
            Start of date range "yyyy-MM-dd".
        date_to : str | None
            End of date range "yyyy-MM-dd" (exclusive — dateTo=2024-03-15
            returns matches up to and including 2024-03-14).
        unfold : dict[str, bool] | None
            Unfold headers. Keys: lineups, bookings, subs, goals.

        Returns
        -------
        list[dict]
            Match objects.
        """
        params = _drop_none(
            season=season, matchday=matchday, status=status,
            stage=stage, group=group,
            dateFrom=date_from, dateTo=date_to,
        )
        result = await self._get(
            f"competitions/{competition}/matches",
            params,
            unfold=unfold,
            cache_ttl=CacheTTL.MEDIUM,
        )
        return result.get("matches", [])

    async def get_competition_teams(
        self,
        competition: str | int,
        *,
        season: int | None = None,
    ) -> list[dict]:
        """Fetch teams participating in a competition.

        Parameters
        ----------
        competition : str | int
            Competition code or ID.
        season : int | None
            Season year (defaults to current season).

        Returns
        -------
        list[dict]
            Team objects.
        """
        params = _drop_none(season=season)
        result = await self._get(
            f"competitions/{competition}/teams", params, cache_ttl=CacheTTL.LONG
        )
        return result.get("teams", [])

    async def get_top_scorers(
        self,
        competition: str | int,
        *,
        season: int | None = None,
        matchday: int | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Fetch top scorers for a competition season.

        Parameters
        ----------
        competition : str | int
            Competition code or ID.
        season : int | None
            Season year.
        matchday : int | None
            Scorers up to a specific matchday.
        limit : int | None
            Number of scorers to return.

        Returns
        -------
        list[dict]
            Scorer objects with player, team, and goals fields.
        """
        params = _drop_none(season=season, matchday=matchday, limit=limit)
        result = await self._get(
            f"competitions/{competition}/scorers", params, cache_ttl=CacheTTL.SHORT
        )
        return result.get("scorers", [])

    # -----------------------------------------------------------------------
    # Matches
    # -----------------------------------------------------------------------

    async def list_matches(
        self,
        *,
        ids: str | None = None,
        date: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        status: MatchStatus | None = None,
        competitions: str | None = None,
        unfold: dict[str, bool] | None = None,
    ) -> list[dict]:
        """Fetch global match list (defaults to today's matches if no filters).

        Parameters
        ----------
        ids : str | None
            Comma-separated match IDs (e.g. "333,3303").
        date : str | None
            Exact date "yyyy-MM-dd".
        date_from : str | None
            Start of date range "yyyy-MM-dd".
        date_to : str | None
            End of date range "yyyy-MM-dd".
        status : MatchStatus | None
            Match status filter.
        competitions : str | None
            Comma-separated competition codes or IDs.
        unfold : dict[str, bool] | None
            Unfold headers. Keys: lineups, bookings, subs, goals.

        Returns
        -------
        list[dict]
            Match objects.
        """
        params = _drop_none(
            ids=ids, date=date,
            dateFrom=date_from, dateTo=date_to,
            status=status, competitions=competitions,
        )
        result = await self._get("matches", params, unfold=unfold, cache_ttl=CacheTTL.MEDIUM)
        return result.get("matches", [])

    async def get_match(
        self,
        match_id: int,
        *,
        unfold: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Fetch full detail for a single match.

        Parameters
        ----------
        match_id : int
            Match ID.
        unfold : dict[str, bool] | None
            Unfold headers. Keys: lineups, bookings, subs, goals.

        Returns
        -------
        dict[str, Any]
            Match object with score, goals, bookings, lineups, and substitutions.
        """
        if mock_match := get_mock_match(match_id):
            logger.info("DataService mock match served - match_id=%d", match_id)
            return mock_match

        return await self._get(f"matches/{match_id}", unfold=unfold, cache_ttl=CacheTTL.LIVE)

    async def get_head_to_head(
        self,
        match_id: int,
        *,
        limit: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        competitions: str | None = None,
    ) -> dict[str, Any]:
        """Fetch head-to-head history for the two teams in a match.

        Parameters
        ----------
        match_id : int
            Match ID (determines which two teams are compared).
        limit : int | None
            Max number of H2H matches to return.
        date_from : str | None
            Start of date range "yyyy-MM-dd".
        date_to : str | None
            End of date range "yyyy-MM-dd".
        competitions : str | None
            Comma-separated competition codes/IDs to scope the H2H history.

        Returns
        -------
        dict[str, Any]
            H2H response with aggregates and match list.
        """
        params = _drop_none(
            limit=limit, dateFrom=date_from, dateTo=date_to, competitions=competitions
        )
        return await self._get(
            f"matches/{match_id}/head2head", params, cache_ttl=CacheTTL.LONG
        )

    # -----------------------------------------------------------------------
    # Teams
    # -----------------------------------------------------------------------

    async def list_teams(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        """List all available teams (single page).

        Parameters
        ----------
        limit : int | None
            Page size (max 500).
        offset : int | None
            Pagination offset.

        Returns
        -------
        list[dict]
            Team objects.
        """
        params = _drop_none(limit=limit, offset=offset)
        result = await self._get("teams", params, cache_ttl=CacheTTL.REFERENCE)
        return result.get("teams", [])

    async def get_team(self, team_id: int) -> dict[str, Any]:
        """Fetch full team resource: profile, squad, competitions, staff.

        Parameters
        ----------
        team_id : int
            Team ID.

        Returns
        -------
        dict[str, Any]
            Team object including current-season squad.
        """
        return await self._get(f"teams/{team_id}", cache_ttl=CacheTTL.LONG)

    async def get_team_matches(
        self,
        team_id: int,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        season: int | None = None,
        status: MatchStatus | None = None,
        venue: Venue | None = None,
        limit: int | None = None,
        unfold: dict[str, bool] | None = None,
    ) -> list[dict]:
        """Fetch matches for a team (defaults to the current season).

        Parameters
        ----------
        team_id : int
            Team ID.
        date_from : str | None
            Start of date range "yyyy-MM-dd".
        date_to : str | None
            End of date range "yyyy-MM-dd".
        season : int | None
            Season year.
        status : MatchStatus | None
            Match status filter.
        venue : Venue | None
            "HOME" or "AWAY".
        limit : int | None
            Max results to return.
        unfold : dict[str, bool] | None
            Unfold headers. Keys: lineups, bookings, subs, goals.

        Returns
        -------
        list[dict]
            Match objects.
        """
        params = _drop_none(
            dateFrom=date_from, dateTo=date_to,
            season=season, status=status, venue=venue, limit=limit,
        )
        result = await self._get(
            f"teams/{team_id}/matches", params, unfold=unfold, cache_ttl=CacheTTL.MEDIUM
        )
        return result.get("matches", [])

    async def get_all_team_matches(
        self,
        team_id: int,
        *,
        season: int | None = None,
        status: MatchStatus | None = None,
        venue: Venue | None = None,
        unfold: dict[str, bool] | None = None,
    ) -> list[dict]:
        """Fetch all pages of matches for a team.

        Parameters
        ----------
        team_id : int
            Team ID.
        season : int | None
            Season year.
        status : MatchStatus | None
            Match status filter.
        venue : Venue | None
            "HOME" or "AWAY".
        unfold : dict[str, bool] | None
            Unfold headers. Keys: lineups, bookings, subs, goals.

        Returns
        -------
        list[dict]
            All match objects across all pages.
        """
        params = _drop_none(season=season, status=status, venue=venue)
        return await self._get_paginated(
            f"teams/{team_id}/matches",
            list_key="matches",
            params=params,
            unfold=unfold,
            cache_ttl=CacheTTL.MEDIUM,
        )

    # -----------------------------------------------------------------------
    # Persons
    # -----------------------------------------------------------------------

    async def get_person(self, person_id: int) -> dict[str, Any]:
        """Fetch a player, coach, or referee profile.

        Parameters
        ----------
        person_id : int
            Person ID.

        Returns
        -------
        dict[str, Any]
            Person object with biographical and career data.
        """
        return await self._get(f"persons/{person_id}", cache_ttl=CacheTTL.LONG)

    async def get_person_matches(
        self,
        person_id: int,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        status: MatchStatus | None = None,
        competitions: str | None = None,
        limit: int | None = None,
        lineup: LineupPosition | None = None,
        event: PersonEvent | None = None,
        unfold: dict[str, bool] | None = None,
    ) -> list[dict]:
        """Fetch matches involving a specific person.

        Parameters
        ----------
        person_id : int
            Person ID.
        date_from : str | None
            Start of date range "yyyy-MM-dd".
        date_to : str | None
            End of date range "yyyy-MM-dd".
        status : MatchStatus | None
            Match status filter.
        competitions : str | None
            Comma-separated competition codes/IDs.
        limit : int | None
            Max results to return.
        lineup : LineupPosition | None
            "STARTING" or "BENCH".
        event : PersonEvent | None
            Event filter: "GOAL", "ASSIST", "SUB_IN", "SUB_OUT".
        unfold : dict[str, bool] | None
            Unfold headers. Keys: lineups, bookings, subs, goals.

        Returns
        -------
        list[dict]
            Match objects where the person appeared.
        """
        params = _drop_none(
            dateFrom=date_from, dateTo=date_to,
            status=status, competitions=competitions,
            limit=limit, lineup=lineup, e=event,
        )
        result = await self._get(
            f"persons/{person_id}/matches", params, unfold=unfold, cache_ttl=CacheTTL.LONG
        )
        return result.get("matches", [])

    # -----------------------------------------------------------------------
    # World Cup 2026 convenience methods
    # -----------------------------------------------------------------------

    async def get_world_cup_matches(
        self,
        *,
        status: MatchStatus | None = None,
        stage: MatchStage | None = None,
        group: MatchGroup | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        unfold: dict[str, bool] | None = None,
    ) -> list[dict]:
        """Fetch 2026 World Cup matches.

        Parameters
        ----------
        status : MatchStatus | None
            Match status filter (e.g. "SCHEDULED", "IN_PLAY", "FINISHED").
        stage : MatchStage | None
            Tournament stage (e.g. "GROUP_STAGE", "FINAL").
        group : MatchGroup | None
            Group filter (e.g. "GROUP_A").
        date_from : str | None
            Start of date range "yyyy-MM-dd".
        date_to : str | None
            End of date range "yyyy-MM-dd".
        unfold : dict[str, bool] | None
            Unfold headers. Keys: lineups, bookings, subs, goals.

        Returns
        -------
        list[dict]
            World Cup 2026 match objects.
        """
        mock_matches = filter_mock_matches(
            status=status,
            stage=stage,
            group=group,
            date_from=date_from,
            date_to=date_to,
        )

        try:
            real_matches = await self.get_competition_matches(
                WC_CODE,
                season=2026,
                status=status,
                stage=stage,
                group=group,
                date_from=date_from,
                date_to=date_to,
                unfold=unfold,
            )
        except Exception:
            if mock_matches:
                logger.exception("DataService real WC fixtures failed; returning mock fixtures.")
                return mock_matches
            raise

        mock_ids = {match["id"] for match in mock_matches}
        return [*mock_matches, *[match for match in real_matches if match.get("id") not in mock_ids]]

    async def get_world_cup_standings(self) -> dict[str, Any]:
        """Fetch 2026 World Cup group stage standings.

        Returns
        -------
        dict[str, Any]
            Full standings response (TOTAL table per group).
        """
        return await self.get_standings(WC_CODE, season=2026)

    async def get_world_cup_teams(self) -> list[dict]:
        """Fetch all teams participating in the 2026 World Cup.

        Returns
        -------
        list[dict]
            Team objects.
        """
        return await self.get_competition_teams(WC_CODE, season=2026)

    async def get_world_cup_top_scorers(self, *, limit: int | None = None) -> list[dict]:
        """Fetch 2026 World Cup top goalscorers.

        Parameters
        ----------
        limit : int | None
            Number of scorers to return.

        Returns
        -------
        list[dict]
            Scorer objects ranked by goals.
        """
        return await self.get_top_scorers(WC_CODE, season=2026, limit=limit)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _log_rate_limits(headers: httpx.Headers) -> None:
        remaining = headers.get("X-RequestsAvailable", "?")
        reset_in = headers.get("X-RequestCounter-Reset", "?")
        logger.debug(
            "Rate limits — requests available: %s | reset in: %ss",
            remaining, reset_in,
        )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _drop_none(params: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Strip None values so they are never sent as query parameters."""
    merged = {**(params or {}), **kwargs}
    return {k: v for k, v in merged.items() if v is not None}


def _build_unfold_headers(unfold: dict[str, bool]) -> dict[str, str]:
    """Convert an unfold dict into the X-Unfold-* request headers."""
    mapping = {
        "lineups":  "X-Unfold-Lineups",
        "bookings": "X-Unfold-Bookings",
        "subs":     "X-Unfold-Subs",
        "goals":    "X-Unfold-Goals",
    }
    return {
        header: str(value).lower()
        for key, header in mapping.items()
        if (value := unfold.get(key)) is not None
    }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_instance: DataService | None = None


def get_data_service() -> DataService:
    """Return (or create) the shared DataService singleton.

    Returns
    -------
    DataService
        Shared instance. Call `await service.initialize()` before first use.
    """
    global _instance
    if _instance is None:
        _instance = DataService()
    return _instance
