"""
Football-Data.org v4 – Programmatic Client Template
=====================================================
Docs     : https://docs.football-data.org/general/v4/index.html
Base URL : https://api.football-data.org/v4
Auth     : X-Auth-Token header (every request)
Methods  : GET only

Key design notes
----------------
* Resources vs Sub-resources
  - Main resources: Area, Competition, Match, Team, Person
  - Sub-resources always hang off a parent, e.g.
      /competitions/{id}/standings
      /competitions/{id}/matches
      /competitions/{id}/teams
      /competitions/{id}/scorers
      /teams/{id}/matches
      /persons/{id}/matches
      /matches/{id}/head2head

* Automatic folding (v4 behaviour)
  Match lists fold lineups / bookings / substitutions / goals by default
  to save bandwidth. Unfold selectively via request headers:
      X-Unfold-Lineups   : true | false
      X-Unfold-Bookings  : true | false
      X-Unfold-Subs      : true | false
      X-Unfold-Goals     : true | false

* Date defaults
  Calling /v4/matches/ with no filters returns today's matches (UTC).
  /v4/teams/{id} returns the squad for the current season.

* Pagination
  Use `limit` (1–500) and `offset` query params.
  List responses include a `count` or `resultSet.count` field.

* Rate limits (per plan)
  Free     : 10 req/min
  Standard : 30 req/min
  Premium+ : 60 req/min
  Response headers:
      X-RequestsAvailable    – remaining requests before block
      X-RequestCounter-Reset – seconds until counter resets

* HTTP status codes
  200  OK
  400  Bad request / invalid filter
  403  Restricted resource (plan tier)
  404  Resource not found
  429  Rate limit exceeded → back off and retry

* Competition codes (use instead of numeric ids)
  WC=2000, CL=2001, PL=2021, BL1=2002, SA=2019, PD=2014,
  FL1=2015, DED=2003, PPL=2017, EC=2018, EL=2146, ...
  Full list: https://docs.football-data.org/general/v4/lookup_tables.html
"""

from __future__ import annotations

import time
import logging
from typing import Any, Literal

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums (from lookup tables — useful for type-safe filter values)
# ---------------------------------------------------------------------------

MatchStatus = Literal[
    "SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "EXTRA_TIME",
    "PENALTY_SHOOTOUT", "FINISHED", "SUSPENDED", "POSTPONED",
    "CANCELLED", "AWARDED", "LIVE",  # LIVE = IN_PLAY + PAUSED shortcut
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

CompetitionCode = Literal[
    "WC", "CL", "PL", "BL1", "SA", "PD", "FL1", "DED", "PPL", "EC",
    "EL", "UCL", "MLS", "BSA", "CLI", "CA", "FA",  # common codes
]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    football_data_token: str
    football_data_base_url: str = "https://api.football-data.org/v4"
    request_timeout: int = 10
    max_retries: int = 3
    retry_backoff_base: float = 2.0  # exponential: base ^ attempt


# ---------------------------------------------------------------------------
# Low-level HTTP client
# ---------------------------------------------------------------------------

class FootballDataClient:
    """Thin, stateless HTTP client for Football-Data.org v4.

    Usage
    -----
    settings = Settings()                  # reads FOOTBALL_DATA_TOKEN from .env
    client   = FootballDataClient(settings)

    # Simple call
    data = client.get("competitions/PL/standings")

    # Call with filters + unfold headers
    data = client.get(
        "competitions/PL/matches",
        params={"status": "FINISHED", "matchday": 30},
        unfold={"lineups": True, "goals": True},
    )
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_headers = {
            "X-Auth-Token": settings.football_data_token,
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        unfold: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Make a single GET request.

        Parameters
        ----------
        path:
            Endpoint path relative to base URL, e.g. "competitions/PL/matches"
        params:
            Query parameters / filters.
        unfold:
            Dict controlling automatic-folding headers. Keys: lineups, bookings,
            subs, goals. Values: True/False.
            e.g. {"lineups": True, "goals": True}
        """
        url = f"{self._settings.football_data_base_url}/{path.lstrip('/')}"
        headers = {**self._base_headers, **self._build_unfold_headers(unfold or {})}
        params = _clean(params or {})
        attempts = 0

        while attempts < self._settings.max_retries:
            attempts += 1
            try:
                resp = httpx.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self._settings.request_timeout,
                )
                self._log_rate_limit_headers(resp.headers)

                if resp.status_code == 429:
                    reset_in = int(resp.headers.get("X-RequestCounter-Reset", 60))
                    wait = max(reset_in, self._settings.retry_backoff_base ** attempts)
                    logger.warning("Rate limited. Retrying in %.1fs (attempt %d).", wait, attempts)
                    time.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    wait = self._settings.retry_backoff_base ** attempts
                    logger.warning("Server error %d. Retrying in %.1fs (attempt %d).", resp.status_code, wait, attempts)
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.TimeoutException:
                wait = self._settings.retry_backoff_base ** attempts
                logger.warning("Request timed out. Retrying in %.1fs (attempt %d).", wait, attempts)
                time.sleep(wait)

        raise RuntimeError(f"All {self._settings.max_retries} attempts failed for path '{path}'.")

    # ------------------------------------------------------------------
    # Pagination helper
    # ------------------------------------------------------------------

    def get_paginated(
        self,
        path: str,
        list_key: str,
        params: dict[str, Any] | None = None,
        page_size: int = 100,
        unfold: dict[str, bool] | None = None,
    ) -> list[Any]:
        """Fetch all pages for an endpoint and return flat list.

        Parameters
        ----------
        list_key:
            The JSON key that holds the list in the response, e.g. "matches".
        page_size:
            Number of items per page (maps to the `limit` param, max 500).
        """
        params = dict(params or {})
        params["limit"] = page_size
        all_items: list[Any] = []
        offset = 0

        while True:
            params["offset"] = offset
            result = self.get(path, params=params, unfold=unfold)
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
            time.sleep(0.5)  # polite pacing

        return all_items

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_unfold_headers(unfold: dict[str, bool]) -> dict[str, str]:
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

    @staticmethod
    def _log_rate_limit_headers(headers: httpx.Headers) -> None:
        remaining = headers.get("X-RequestsAvailable", "?")
        reset_in  = headers.get("X-RequestCounter-Reset", "?")
        logger.debug("Requests available: %s | reset in: %ss", remaining, reset_in)


# ---------------------------------------------------------------------------
# High-level API wrappers
# ---------------------------------------------------------------------------

class FootballDataAPI:
    """Named wrappers for every Football-Data.org v4 endpoint.

    Accepts competition codes (e.g. "PL", "WC") or numeric ids interchangeably
    wherever the API supports them.

    All methods return the raw parsed JSON dict or the relevant list within it,
    so callers work with data rather than HTTP boilerplate.
    """

    def __init__(self, client: FootballDataClient) -> None:
        self._c = client

    # ------------------------------------------------------------------
    # Areas
    # ------------------------------------------------------------------

    def list_areas(self) -> list[dict]:
        return self._c.get("areas").get("areas", [])

    def get_area(self, area_id: int) -> dict:
        return self._c.get(f"areas/{area_id}")

    # ------------------------------------------------------------------
    # Competitions
    # ------------------------------------------------------------------

    def list_competitions(self, *, areas: str | None = None) -> list[dict]:
        """List available competitions.

        Parameters
        ----------
        areas:
            Comma-separated area ids to filter, e.g. "2072,2224".
        """
        params = _clean({"areas": areas})
        return self._c.get("competitions", params=params).get("competitions", [])

    def get_competition(self, competition: str | int) -> dict:
        """Get a single competition by id or code (e.g. "PL", 2021)."""
        return self._c.get(f"competitions/{competition}")

    # --- Competition sub-resources ------------------------------------

    def get_standings(
        self,
        competition: str | int,
        *,
        season: int | None = None,
        matchday: int | None = None,
        date: str | None = None,
    ) -> dict:
        """Standings for a competition.

        Returns TOTAL, HOME, AWAY tables for leagues.
        Returns 404 for CUP and PLAYOFFS competitions.

        Parameters
        ----------
        season:
            4-digit year, e.g. 2023 (refers to season starting that year).
        date:
            Snapshot standings as of a specific date (yyyy-MM-dd).
        """
        params = _clean({"season": season, "matchday": matchday, "date": date})
        return self._c.get(f"competitions/{competition}/standings", params=params)

    def get_competition_matches(
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
        """Matches for a competition, optionally filtered.

        Note: dateTo is exclusive — dateTo=2024-03-15 returns matches
        up to and including 2024-03-14.
        """
        params = _clean({
            "season": season,
            "matchday": matchday,
            "status": status,
            "stage": stage,
            "group": group,
            "dateFrom": date_from,
            "dateTo": date_to,
        })
        result = self._c.get(
            f"competitions/{competition}/matches",
            params=params,
            unfold=unfold,
        )
        return result.get("matches", [])

    def get_competition_teams(
        self,
        competition: str | int,
        *,
        season: int | None = None,
    ) -> list[dict]:
        """Teams participating in a competition for a given season."""
        params = _clean({"season": season})
        return self._c.get(f"competitions/{competition}/teams", params=params).get("teams", [])

    def get_top_scorers(
        self,
        competition: str | int,
        *,
        season: int | None = None,
        matchday: int | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Top scorers for a competition season."""
        params = _clean({"season": season, "matchday": matchday, "limit": limit})
        return self._c.get(f"competitions/{competition}/scorers", params=params).get("scorers", [])

    # ------------------------------------------------------------------
    # Matches
    # ------------------------------------------------------------------

    def list_matches(
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
        """Global match list, defaulting to today's matches if no filters set.

        Parameters
        ----------
        ids:
            Comma-separated match ids, e.g. "333,3303,3213".
        competitions:
            Comma-separated competition codes/ids, e.g. "PL,BL1".
        """
        params = _clean({
            "ids": ids,
            "date": date,
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": status,
            "competitions": competitions,
        })
        return self._c.get("matches", params=params, unfold=unfold).get("matches", [])

    def get_match(
        self,
        match_id: int,
        *,
        unfold: dict[str, bool] | None = None,
    ) -> dict:
        """Single match with full detail (score, goals, bookings, lineups, subs)."""
        return self._c.get(f"matches/{match_id}", unfold=unfold)

    def get_head_to_head(
        self,
        match_id: int,
        *,
        limit: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        competitions: str | None = None,
    ) -> dict:
        """Head-to-head history for the two teams in a given match."""
        params = _clean({
            "limit": limit,
            "dateFrom": date_from,
            "dateTo": date_to,
            "competitions": competitions,
        })
        return self._c.get(f"matches/{match_id}/head2head", params=params)

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    def list_teams(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        """List all available teams (paginated)."""
        params = _clean({"limit": limit, "offset": offset})
        return self._c.get("teams", params=params).get("teams", [])

    def get_team(self, team_id: int) -> dict:
        """Full team resource: profile, squad, running competitions, staff."""
        return self._c.get(f"teams/{team_id}")

    def get_team_matches(
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
        """Matches for a team. Defaults to the current season."""
        params = _clean({
            "dateFrom": date_from,
            "dateTo": date_to,
            "season": season,
            "status": status,
            "venue": venue,
            "limit": limit,
        })
        return self._c.get(
            f"teams/{team_id}/matches",
            params=params,
            unfold=unfold,
        ).get("matches", [])

    def get_all_team_matches(
        self,
        team_id: int,
        *,
        season: int | None = None,
        status: MatchStatus | None = None,
        venue: Venue | None = None,
        unfold: dict[str, bool] | None = None,
    ) -> list[dict]:
        """Fetch all pages of team matches and return a flat list."""
        params = _clean({"season": season, "status": status, "venue": venue})
        return self._c.get_paginated(
            f"teams/{team_id}/matches",
            list_key="matches",
            params=params,
            unfold=unfold,
        )

    # ------------------------------------------------------------------
    # Persons
    # ------------------------------------------------------------------

    def get_person(self, person_id: int) -> dict:
        """Player / coach / referee profile."""
        return self._c.get(f"persons/{person_id}")

    def get_person_matches(
        self,
        person_id: int,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        status: MatchStatus | None = None,
        competitions: str | None = None,
        limit: int | None = None,
        lineup: Literal["STARTING", "BENCH"] | None = None,
        e: str | None = None,  # event filter: GOAL | ASSIST | SUB_IN | SUB_OUT
        unfold: dict[str, bool] | None = None,
    ) -> list[dict]:
        """Matches involving a specific person.

        Parameters
        ----------
        lineup:
            "STARTING" or "BENCH" — filter by how the person appeared.
        e:
            Event filter: GOAL, ASSIST, SUB_IN, SUB_OUT.
        """
        params = _clean({
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": status,
            "competitions": competitions,
            "limit": limit,
            "lineup": lineup,
            "e": e,
        })
        return self._c.get(
            f"persons/{person_id}/matches",
            params=params,
            unfold=unfold,
        ).get("matches", [])


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _clean(params: dict[str, Any]) -> dict[str, Any]:
    """Strip None values so they're not sent as query params."""
    return {k: v for k, v in params.items() if v is not None}


# ---------------------------------------------------------------------------
# Competition code reference (for quick lookup in code)
# ---------------------------------------------------------------------------

COMPETITION_CODES: dict[str, int] = {
    "WC":   2000,  # FIFA World Cup
    "CL":   2001,  # UEFA Champions League
    "BL1":  2002,  # Bundesliga
    "DED":  2003,  # Eredivisie
    "BL2":  2004,  # 2. Bundesliga
    "DJL":  2005,  # Eerste Divisie
    "QCAF": 2006,  # WC Qualification CAF
    "QUFA": 2007,  # WC Qualification UEFA
    "AAL":  2008,  # A League
    "BJL":  2009,  # Jupiler Pro League
    "DFB":  2011,  # DFB-Pokal
    "ABL":  2012,  # Austrian Bundesliga
    "BSA":  2013,  # Campeonato Brasileiro Série A
    "PD":   2014,  # Primera Division (La Liga)
    "FL1":  2015,  # Ligue 1
    "ELC":  2016,  # Championship
    "PPL":  2017,  # Primeira Liga
    "EC":   2018,  # European Championship
    "SA":   2019,  # Serie A
    "FAC":  2055,  # FA Cup
    "PL":   2021,  # Premier League
    "EL":   2146,  # UEFA Europa League
    "UCL":  2154,  # UEFA Conference League
    "MLS":  2145,  # MLS
    "CLI":  2152,  # Copa Libertadores
    "CA":   2080,  # Copa America
}


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    settings = Settings()                    # reads FOOTBALL_DATA_TOKEN from .env
    client   = FootballDataClient(settings)
    api      = FootballDataAPI(client)

    # 1. Today's matches
    today = api.list_matches()
    print(f"Matches today: {len(today)}")

    # 2. Premier League standings (current season)
    standings = api.get_standings("PL")
    total_table = next(
        (s["table"] for s in standings.get("standings", []) if s["type"] == "TOTAL"),
        [],
    )
    print(f"PL standings rows: {len(total_table)}")
    if total_table:
        leader = total_table[0]
        print(f"League leader: {leader['team']['name']} – {leader['points']} pts")

    # 3. World Cup 2026 – upcoming matches, goals unfolded
    wc_matches = api.get_competition_matches(
        "WC",
        season=2026,
        status="SCHEDULED",
        unfold={"goals": True},
    )
    print(f"WC 2026 scheduled matches: {len(wc_matches)}")

    # 4. Top scorers – Serie A current season
    scorers = api.get_top_scorers("SA", limit=5)
    for s in scorers:
        print(f"{s['player']['name']} ({s['team']['shortName']}) – {s['goals']} goals")
