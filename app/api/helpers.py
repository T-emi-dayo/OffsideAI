"""
Shared helpers for translating football-data.org API responses into the
internal MatchInput format consumed by all agents.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.views.schemas import FixtureItem, FixtureScore, FixtureTeam

# ---------------------------------------------------------------------------
# Stage / status mapping tables
# ---------------------------------------------------------------------------

# football-data.org stage → human-readable stage used in agents and responses
STAGE_MAP: dict[str, str] = {
    "GROUP_STAGE":         "Group Stage",
    "LAST_16":             "Round of 16",
    "QUARTER_FINALS":      "Quarter Final",
    "SEMI_FINALS":         "Semi Final",
    "THIRD_PLACE":         "Third Place",
    "FINAL":               "Final",
    "PRELIMINARY_ROUND":   "Preliminary Round",
    "QUALIFICATION":       "Qualification",
    "PLAYOFF_ROUND_1":     "Playoff Round 1",
    "PLAYOFF_ROUND_2":     "Playoff Round 2",
    "PLAYOFFS":            "Playoffs",
    "REGULAR_SEASON":      "Regular Season",
}

# football-data.org status → internal match_state
STATUS_MAP: dict[str, str] = {
    "SCHEDULED":          "pre",
    "TIMED":              "pre",
    "IN_PLAY":            "live",
    "PAUSED":             "live",
    "EXTRA_TIME":         "live",
    "PENALTY_SHOOTOUT":   "live",
    "FINISHED":           "post",
    "SUSPENDED":          "pre",
    "POSTPONED":          "pre",
    "CANCELLED":          "pre",
    "AWARDED":            "post",
    "LIVE":               "live",
}


# ---------------------------------------------------------------------------
# Match-to-MatchInput translation
# ---------------------------------------------------------------------------

def match_state_from_status(status: str) -> str:
    """Map a football-data.org status string to "pre" | "live" | "post"."""
    return STATUS_MAP.get(status, "pre")


def stage_label(stage: str) -> str:
    """Map a football-data.org stage code to a human-readable label."""
    return STAGE_MAP.get(stage, stage.replace("_", " ").title())


def build_match_input(match: dict) -> dict:
    """
    Translate a football-data.org match object into a MatchInput-compatible dict.

    Parameters
    ----------
    match : dict
        Raw match object from football-data.org API.

    Returns
    -------
    dict
        Dict with all required MatchInput keys populated.
    """
    match_id = str(match["id"])
    home_team = match["homeTeam"]["name"]
    away_team = match["awayTeam"]["name"]
    utc_date: str = match.get("utcDate", "")
    match_date = utc_date[:10] if utc_date else ""
    stage = stage_label(match.get("stage", ""))
    match_state = match_state_from_status(match.get("status", "SCHEDULED"))

    score_raw = match.get("score", {}).get("fullTime", {})

    return {
        "match_id": match_id,
        "competition_type": "world_cup",
        "home_team": home_team,
        "away_team": away_team,
        "match_date": match_date,
        "stage": stage,
        "match_state": match_state,
        "errors": [],
        "_score": score_raw,   # internal — used by callers to build final_score
        "_group": match.get("group"),
    }


def normalize_events(match: dict, match_id: str) -> list[dict]:
    """
    Normalize unfolded football-data.org match data into our MatchEvent format.

    Handles goals and bookings (yellow/red cards). Sorts by minute.

    Parameters
    ----------
    match : dict
        Full match object with unfolded goals and bookings.
    match_id : str
        String match ID to embed in each event.

    Returns
    -------
    list[dict]
        Sorted list of normalized MatchEvent dicts.
    """
    events: list[dict] = []

    for goal in match.get("goals", []) or []:
        minute_obj = goal.get("minute") or {}
        reg = minute_obj.get("regular") or 0
        inj = minute_obj.get("injury") or 0
        minute = reg + inj

        scorer = goal.get("scorer") or {}
        assist = goal.get("assist") or {}
        team = goal.get("team") or {}

        events.append({
            "match_id": match_id,
            "minute": minute,
            "event_type": "goal",
            "team": team.get("name", ""),
            "player": scorer.get("name", ""),
            "detail": f"Assist: {assist.get('name', '')}" if assist.get("name") else "",
        })

    for booking in match.get("bookings", []) or []:
        minute_obj = booking.get("minute") or {}
        reg = minute_obj.get("regular") or 0
        inj = minute_obj.get("injury") or 0
        minute = reg + inj

        card = booking.get("card", "YELLOW")
        event_type = "red_card" if "RED" in card else "yellow_card"
        team = booking.get("team") or {}
        player = booking.get("player") or {}

        events.append({
            "match_id": match_id,
            "minute": minute,
            "event_type": event_type,
            "team": team.get("name", ""),
            "player": player.get("name", ""),
            "detail": card,
        })

    events.sort(key=lambda e: e["minute"])
    return events


def to_fixture_item(match: dict) -> FixtureItem:
    """Convert a football-data.org match object to a FixtureItem response model."""
    score_raw = match.get("score", {}).get("fullTime", {})
    return FixtureItem(
        id=match["id"],
        stage=stage_label(match.get("stage", "")),
        group=match.get("group"),
        utc_date=match.get("utcDate", ""),
        match_state=match_state_from_status(match.get("status", "SCHEDULED")),
        home_team=FixtureTeam(name=match["homeTeam"]["name"]),
        away_team=FixtureTeam(name=match["awayTeam"]["name"]),
        score=FixtureScore(
            home=score_raw.get("home"),
            away=score_raw.get("away"),
        ),
    )


def now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
