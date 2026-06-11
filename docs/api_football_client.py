"""
API-Football v3 – Programmatic Client Template
===============================================
Base URL : https://v3.football.api-sports.io
Auth     : x-apisports-key header (every request)
Methods  : GET only – no POST / PUT / DELETE

Response envelope (every endpoint):
    {
        "get":        "<endpoint path>",
        "parameters": { ...echoed query params... },
        "errors":     []  | { "field": "message" },
        "results":    <int – items in current page>,
        "paging":     { "current": 1, "total": N },
        "response":   [ ...data objects... ]
    }

Rate-limit headers returned on every response:
    x-ratelimit-requests-limit      – daily quota
    x-ratelimit-requests-remaining  – daily remaining
    X-RateLimit-Limit               – per-minute cap
    X-RateLimit-Remaining           – per-minute remaining

HTTP status codes:
    200  OK (check `errors` field – 200 can still carry errors)
    204  No Content
    429  Rate limit exceeded → retry after back-off
    499  Request timeout    → safe to retry once
    500  Server error       → safe to retry once
"""

from __future__ import annotations

import time
import logging
from typing import Any

import httpx
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_football_key: str
    api_football_base_url: str = "https://v3.football.api-sports.io"
    request_timeout: int = 10          # seconds
    max_retries: int = 3
    retry_backoff_base: float = 2.0    # exponential: base ^ attempt


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class Paging(BaseModel):
    current: int
    total: int


class APIFootballResponse(BaseModel):
    get: str
    parameters: dict[str, Any]
    errors: list[Any] | dict[str, str]
    results: int
    paging: Paging
    response: list[Any]

    @property
    def has_errors(self) -> bool:
        if isinstance(self.errors, dict):
            return len(self.errors) > 0
        return len(self.errors) > 0

    @property
    def has_more_pages(self) -> bool:
        return self.paging.current < self.paging.total


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class APIFootballClient:
    """Thin, stateless HTTP client for API-Football v3.

    Usage
    -----
    settings = Settings()
    client   = APIFootballClient(settings)

    # Single call
    data = client.get("fixtures", {"league": 39, "season": 2024, "round": "Regular Season - 1"})

    # Paginated call (auto-fetches all pages)
    all_items = client.get_all_pages("players", {"league": 39, "season": 2024})
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._headers = {
            "x-apisports-key": settings.api_football_key,
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> APIFootballResponse:
        """Make a single GET request and return a validated response envelope."""
        url = f"{self._settings.api_football_base_url}/{endpoint.lstrip('/')}"
        attempts = 0

        while attempts < self._settings.max_retries:
            attempts += 1
            try:
                resp = httpx.get(
                    url,
                    params=params,
                    headers=self._headers,
                    timeout=self._settings.request_timeout,
                )
                self._log_rate_limit_headers(resp.headers)

                if resp.status_code == 429:
                    wait = self._settings.retry_backoff_base ** attempts
                    logger.warning("Rate limited. Retrying in %.1fs (attempt %d).", wait, attempts)
                    time.sleep(wait)
                    continue

                if resp.status_code in (499, 500):
                    wait = self._settings.retry_backoff_base ** attempts
                    logger.warning(
                        "Server error %d. Retrying in %.1fs (attempt %d).",
                        resp.status_code, wait, attempts,
                    )
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                parsed = APIFootballResponse.model_validate(resp.json())

                if parsed.has_errors:
                    logger.error("API errors for %s: %s", endpoint, parsed.errors)

                return parsed

            except httpx.TimeoutException:
                wait = self._settings.retry_backoff_base ** attempts
                logger.warning("Request timed out. Retrying in %.1fs (attempt %d).", wait, attempts)
                time.sleep(wait)

        raise RuntimeError(f"All {self._settings.max_retries} attempts failed for endpoint '{endpoint}'.")

    # ------------------------------------------------------------------
    # Pagination helper
    # ------------------------------------------------------------------

    def get_all_pages(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Fetch every page for an endpoint and return a flat list of items."""
        params = dict(params or {})
        all_items: list[Any] = []
        page = 1

        while True:
            params["page"] = page
            result = self.get(endpoint, params)
            all_items.extend(result.response)

            if not result.has_more_pages:
                break

            page += 1
            # Polite delay between page requests
            time.sleep(0.5)

        return all_items

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _log_rate_limit_headers(headers: httpx.Headers) -> None:
        remaining_day = headers.get("x-ratelimit-requests-remaining", "?")
        remaining_min = headers.get("X-RateLimit-Remaining", "?")
        logger.debug(
            "Rate limits – daily remaining: %s | per-minute remaining: %s",
            remaining_day,
            remaining_min,
        )


# ---------------------------------------------------------------------------
# Endpoint wrappers  (add / extend as needed for Offside AI)
# ---------------------------------------------------------------------------

class FootballAPI:
    """High-level wrappers around each API-Football v3 endpoint group.

    All methods return the raw `response` list from the envelope so callers
    work directly with the data objects rather than the envelope boilerplate.
    """

    def __init__(self, client: APIFootballClient) -> None:
        self._c = client

    # --- Meta / Reference -------------------------------------------------

    def get_countries(self, *, name: str | None = None, code: str | None = None) -> list[Any]:
        params = _clean(name=name, code=code)
        return self._c.get("countries", params).response

    def get_leagues(
        self,
        *,
        id: int | None = None,
        country: str | None = None,
        season: int | None = None,
        current: bool | None = None,
    ) -> list[Any]:
        params = _clean(id=id, country=country, season=season, current=current)
        return self._c.get("leagues", params).response

    def get_seasons(self) -> list[Any]:
        return self._c.get("leagues/seasons").response

    # --- Teams ------------------------------------------------------------

    def get_teams(
        self,
        *,
        id: int | None = None,
        league: int | None = None,
        season: int | None = None,
        country: str | None = None,
        name: str | None = None,
    ) -> list[Any]:
        params = _clean(id=id, league=league, season=season, country=country, name=name)
        return self._c.get("teams", params).response

    def get_team_statistics(self, *, league: int, season: int, team: int) -> dict[str, Any]:
        params = _clean(league=league, season=season, team=team)
        result = self._c.get("teams/statistics", params)
        return result.response[0] if result.response else {}

    def get_standings(self, *, league: int, season: int) -> list[Any]:
        params = _clean(league=league, season=season)
        return self._c.get("standings", params).response

    # --- Fixtures ---------------------------------------------------------

    def get_fixtures(
        self,
        *,
        id: int | None = None,
        ids: str | None = None,          # "id1-id2-id3"
        live: str | None = None,         # "all" or "league_id-league_id"
        date: str | None = None,         # "YYYY-MM-DD"
        league: int | None = None,
        season: int | None = None,
        team: int | None = None,
        round: str | None = None,
        status: str | None = None,       # "NS", "1H", "HT", "2H", "FT", etc.
        from_date: str | None = None,
        to_date: str | None = None,
        timezone: str | None = None,
    ) -> list[Any]:
        params = _clean(
            id=id, ids=ids, live=live, date=date, league=league,
            season=season, team=team, round=round, status=status,
            **{"from": from_date, "to": to_date},
            timezone=timezone,
        )
        return self._c.get("fixtures", params).response

    def get_fixture_rounds(self, *, league: int, season: int) -> list[str]:
        params = _clean(league=league, season=season)
        return self._c.get("fixtures/rounds", params).response

    def get_fixture_statistics(self, *, fixture: int, team: int | None = None) -> list[Any]:
        params = _clean(fixture=fixture, team=team)
        return self._c.get("fixtures/statistics", params).response

    def get_fixture_events(self, *, fixture: int) -> list[Any]:
        return self._c.get("fixtures/events", {"fixture": fixture}).response

    def get_fixture_lineups(self, *, fixture: int) -> list[Any]:
        return self._c.get("fixtures/lineups", {"fixture": fixture}).response

    def get_fixture_player_stats(self, *, fixture: int) -> list[Any]:
        return self._c.get("fixtures/players", {"fixture": fixture}).response

    def get_head_to_head(self, *, h2h: str, season: int | None = None) -> list[Any]:
        """h2h format: "team_id_1-team_id_2" """
        params = _clean(h2h=h2h, season=season)
        return self._c.get("fixtures/headtohead", params).response

    # --- Players ----------------------------------------------------------

    def get_players(
        self,
        *,
        id: int | None = None,
        team: int | None = None,
        league: int | None = None,
        season: int | None = None,
        search: str | None = None,
        page: int = 1,
    ) -> list[Any]:
        params = _clean(id=id, team=team, league=league, season=season, search=search, page=page)
        return self._c.get("players", params).response

    def get_players_all_pages(
        self,
        *,
        team: int | None = None,
        league: int | None = None,
        season: int,
    ) -> list[Any]:
        params = _clean(team=team, league=league, season=season)
        return self._c.get_all_pages("players", params)

    def get_top_scorers(self, *, league: int, season: int) -> list[Any]:
        return self._c.get("players/topscorers", {"league": league, "season": season}).response

    def get_top_assists(self, *, league: int, season: int) -> list[Any]:
        return self._c.get("players/topassists", {"league": league, "season": season}).response

    def get_injuries(
        self,
        *,
        fixture: int | None = None,
        league: int | None = None,
        season: int | None = None,
        team: int | None = None,
        date: str | None = None,
    ) -> list[Any]:
        params = _clean(fixture=fixture, league=league, season=season, team=team, date=date)
        return self._c.get("injuries", params).response

    # --- Predictions / Odds -----------------------------------------------

    def get_predictions(self, *, fixture: int) -> list[Any]:
        return self._c.get("predictions", {"fixture": fixture}).response

    def get_odds(
        self,
        *,
        fixture: int | None = None,
        league: int | None = None,
        season: int | None = None,
        date: str | None = None,
        bookmaker: int | None = None,
        bet: int | None = None,
    ) -> list[Any]:
        params = _clean(
            fixture=fixture, league=league, season=season,
            date=date, bookmaker=bookmaker, bet=bet,
        )
        return self._c.get("odds", params).response

    # --- Transfers / Sidelined / Trophies ---------------------------------

    def get_transfers(self, *, player: int | None = None, team: int | None = None) -> list[Any]:
        params = _clean(player=player, team=team)
        return self._c.get("transfers", params).response

    def get_sidelined(self, *, player: int | None = None, coach: int | None = None) -> list[Any]:
        params = _clean(player=player, coach=coach)
        return self._c.get("sidelined", params).response

    def get_trophies(self, *, player: int | None = None, coach: int | None = None) -> list[Any]:
        params = _clean(player=player, coach=coach)
        return self._c.get("trophies", params).response

    # --- Coaches ----------------------------------------------------------

    def get_coaches(
        self,
        *,
        id: int | None = None,
        team: int | None = None,
        search: str | None = None,
    ) -> list[Any]:
        params = _clean(id=id, team=team, search=search)
        return self._c.get("coachs", params).response

    # --- Venues -----------------------------------------------------------

    def get_venues(
        self,
        *,
        id: int | None = None,
        city: str | None = None,
        country: str | None = None,
        search: str | None = None,
    ) -> list[Any]:
        params = _clean(id=id, city=city, country=country, search=search)
        return self._c.get("venues", params).response

    # --- Account ----------------------------------------------------------

    def get_account_status(self) -> dict[str, Any]:
        """Returns subscription info, daily quota, and requests remaining."""
        result = self._c.get("status")
        return result.response[0] if result.response else {}


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _clean(**kwargs: Any) -> dict[str, Any]:
    """Drop None values so they're never sent as query params."""
    return {k: v for k, v in kwargs.items() if v is not None}


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    settings = Settings()          # reads API_FOOTBALL_KEY from .env
    client   = APIFootballClient(settings)
    api      = FootballAPI(client)

    # 1. Verify account / quota
    status = api.get_account_status()
    print("Account:", status)

    # 2. World Cup 2026 league coverage check
    leagues = api.get_leagues(id=1, season=2026)
    if leagues:
        coverage = leagues[0].get("seasons", [{}])[0].get("coverage", {})
        print("WC 2026 coverage:", coverage)

    # 3. Today's fixtures
    from datetime import date
    fixtures = api.get_fixtures(date=str(date.today()))
    print(f"Fixtures today: {len(fixtures)}")
