"""Mock 2026 World Cup fixtures for exercising live and post-match flows.

The objects intentionally follow the football-data.org match shape used by
DataService, so routes and agents keep using the same normalization path.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


MOCK_MATCHES: list[dict[str, Any]] = [
    {
        "id": 990001,
        "utcDate": "2026-06-11T20:00:00Z",
        "status": "IN_PLAY",
        "minute": 68,
        "stage": "GROUP_STAGE",
        "group": "GROUP_D",
        "matchday": 2,
        "competition": {"id": 2000, "name": "FIFA World Cup", "code": "WC"},
        "venue": "MetLife Stadium, New York/New Jersey",
        "homeTeam": {"id": 764, "name": "United States", "shortName": "USA", "tla": "USA"},
        "awayTeam": {"id": 759, "name": "Japan", "shortName": "Japan", "tla": "JPN"},
        "score": {
            "winner": None,
            "duration": "REGULAR",
            "fullTime": {"home": 2, "away": 1},
            "halfTime": {"home": 1, "away": 1},
        },
        "goals": [
            {
                "minute": {"regular": 14, "injury": 0},
                "team": {"name": "Japan"},
                "scorer": {"name": "Takefusa Kubo"},
                "assist": {"name": "Kaoru Mitoma"},
            },
            {
                "minute": {"regular": 32, "injury": 0},
                "team": {"name": "United States"},
                "scorer": {"name": "Christian Pulisic"},
                "assist": {"name": "Tim Weah"},
            },
            {
                "minute": {"regular": 61, "injury": 0},
                "team": {"name": "United States"},
                "scorer": {"name": "Folarin Balogun"},
                "assist": {"name": "Weston McKennie"},
            },
        ],
        "bookings": [
            {
                "minute": {"regular": 28, "injury": 0},
                "team": {"name": "United States"},
                "player": {"name": "Tyler Adams"},
                "card": "YELLOW_CARD",
            },
            {
                "minute": {"regular": 55, "injury": 0},
                "team": {"name": "Japan"},
                "player": {"name": "Wataru Endo"},
                "card": "YELLOW_CARD",
            },
        ],
    },
    {
        "id": 990002,
        "utcDate": "2026-06-11T23:00:00Z",
        "status": "PAUSED",
        "minute": 45,
        "stage": "GROUP_STAGE",
        "group": "GROUP_E",
        "matchday": 2,
        "competition": {"id": 2000, "name": "FIFA World Cup", "code": "WC"},
        "venue": "Estadio Azteca, Mexico City",
        "homeTeam": {"id": 762, "name": "Mexico", "shortName": "Mexico", "tla": "MEX"},
        "awayTeam": {"id": 760, "name": "Germany", "shortName": "Germany", "tla": "GER"},
        "score": {
            "winner": None,
            "duration": "REGULAR",
            "fullTime": {"home": 1, "away": 1},
            "halfTime": {"home": 1, "away": 1},
        },
        "goals": [
            {
                "minute": {"regular": 8, "injury": 0},
                "team": {"name": "Germany"},
                "scorer": {"name": "Jamal Musiala"},
                "assist": {"name": "Florian Wirtz"},
            },
            {
                "minute": {"regular": 43, "injury": 2},
                "team": {"name": "Mexico"},
                "scorer": {"name": "Santiago Gimenez"},
                "assist": {"name": "Hirving Lozano"},
            },
        ],
        "bookings": [
            {
                "minute": {"regular": 36, "injury": 0},
                "team": {"name": "Mexico"},
                "player": {"name": "Edson Alvarez"},
                "card": "YELLOW_CARD",
            },
        ],
    },
    {
        "id": 990101,
        "utcDate": "2026-06-11T19:00:00Z",
        "status": "FINISHED",
        "stage": "GROUP_STAGE",
        "group": "GROUP_B",
        "matchday": 1,
        "competition": {"id": 2000, "name": "FIFA World Cup", "code": "WC"},
        "venue": "BMO Field, Toronto",
        "homeTeam": {"id": 815, "name": "Canada", "shortName": "Canada", "tla": "CAN"},
        "awayTeam": {"id": 779, "name": "Croatia", "shortName": "Croatia", "tla": "CRO"},
        "score": {
            "winner": "AWAY_TEAM",
            "duration": "REGULAR",
            "fullTime": {"home": 1, "away": 3},
            "halfTime": {"home": 1, "away": 1},
        },
        "goals": [
            {
                "minute": {"regular": 11, "injury": 0},
                "team": {"name": "Canada"},
                "scorer": {"name": "Jonathan David"},
                "assist": {"name": "Alphonso Davies"},
            },
            {
                "minute": {"regular": 39, "injury": 0},
                "team": {"name": "Croatia"},
                "scorer": {"name": "Andrej Kramaric"},
                "assist": {"name": "Luka Modric"},
            },
            {
                "minute": {"regular": 58, "injury": 0},
                "team": {"name": "Croatia"},
                "scorer": {"name": "Luka Modric"},
                "assist": {"name": "Mateo Kovacic"},
            },
            {
                "minute": {"regular": 83, "injury": 0},
                "team": {"name": "Croatia"},
                "scorer": {"name": "Josko Gvardiol"},
                "assist": {"name": "Marcelo Brozovic"},
            },
        ],
        "bookings": [
            {
                "minute": {"regular": 52, "injury": 0},
                "team": {"name": "Canada"},
                "player": {"name": "Stephen Eustaquio"},
                "card": "YELLOW_CARD",
            },
            {
                "minute": {"regular": 74, "injury": 0},
                "team": {"name": "Canada"},
                "player": {"name": "Kamal Miller"},
                "card": "RED_CARD",
            },
        ],
    },
    {
        "id": 990102,
        "utcDate": "2026-06-11T22:00:00Z",
        "status": "FINISHED",
        "stage": "GROUP_STAGE",
        "group": "GROUP_C",
        "matchday": 1,
        "competition": {"id": 2000, "name": "FIFA World Cup", "code": "WC"},
        "venue": "SoFi Stadium, Los Angeles",
        "homeTeam": {"id": 764, "name": "Argentina", "shortName": "Argentina", "tla": "ARG"},
        "awayTeam": {"id": 773, "name": "Morocco", "shortName": "Morocco", "tla": "MAR"},
        "score": {
            "winner": "DRAW",
            "duration": "REGULAR",
            "fullTime": {"home": 2, "away": 2},
            "halfTime": {"home": 0, "away": 1},
        },
        "goals": [
            {
                "minute": {"regular": 24, "injury": 0},
                "team": {"name": "Morocco"},
                "scorer": {"name": "Youssef En-Nesyri"},
                "assist": {"name": "Achraf Hakimi"},
            },
            {
                "minute": {"regular": 50, "injury": 0},
                "team": {"name": "Argentina"},
                "scorer": {"name": "Julian Alvarez"},
                "assist": {"name": "Alexis Mac Allister"},
            },
            {
                "minute": {"regular": 71, "injury": 0},
                "team": {"name": "Morocco"},
                "scorer": {"name": "Hakim Ziyech"},
                "assist": {"name": "Sofyan Amrabat"},
            },
            {
                "minute": {"regular": 90, "injury": 4},
                "team": {"name": "Argentina"},
                "scorer": {"name": "Lautaro Martinez"},
                "assist": {"name": "Lionel Messi"},
            },
        ],
        "bookings": [
            {
                "minute": {"regular": 66, "injury": 0},
                "team": {"name": "Morocco"},
                "player": {"name": "Sofyan Amrabat"},
                "card": "YELLOW_CARD",
            },
            {
                "minute": {"regular": 89, "injury": 0},
                "team": {"name": "Argentina"},
                "player": {"name": "Nicolas Otamendi"},
                "card": "YELLOW_CARD",
            },
        ],
    },
]


def list_mock_matches() -> list[dict[str, Any]]:
    """Return all mock matches as defensive copies."""
    return deepcopy(MOCK_MATCHES)


def get_mock_match(match_id: int) -> dict[str, Any] | None:
    """Return a mock match by ID, or None if the ID is not mocked."""
    for match in MOCK_MATCHES:
        if match["id"] == match_id:
            return deepcopy(match)
    return None


def filter_mock_matches(
    *,
    status: str | None = None,
    stage: str | None = None,
    group: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    """Apply the subset of DataService filters used by fixture routes."""
    matches = list_mock_matches()

    if status is not None:
        live_statuses = {"IN_PLAY", "PAUSED", "EXTRA_TIME", "PENALTY_SHOOTOUT", "LIVE"}
        if status in live_statuses:
            matches = [m for m in matches if m.get("status") in live_statuses]
        else:
            matches = [m for m in matches if m.get("status") == status]

    if stage is not None:
        matches = [m for m in matches if m.get("stage") == stage]

    if group is not None:
        matches = [m for m in matches if m.get("group") == group]

    if date_from is not None:
        matches = [m for m in matches if (m.get("utcDate") or "")[:10] >= date_from]

    if date_to is not None:
        matches = [m for m in matches if (m.get("utcDate") or "")[:10] <= date_to]

    return matches
