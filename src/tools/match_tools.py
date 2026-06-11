"""
Match history query tools.

Dataset: international_matches.csv
Columns used: date, home_team, away_team, home_score, away_score, tournament, neutral
"""
from __future__ import annotations

import pandas as pd
from langchain_core.tools import tool

from src.data.store import get_store
from src.tools.utils import find_team_rows, normalise_team_name

# ---------------------------------------------------------------------------
# Competition filter helpers
# ---------------------------------------------------------------------------

def _apply_competition_filter(df: pd.DataFrame, competition_filter: str) -> pd.DataFrame:
    t = df["tournament"]
    if competition_filter == "world_cup":
        mask = t.str.contains("FIFA World Cup", case=False, na=False) & \
               ~t.str.contains("Qual", case=False, na=False)
    elif competition_filter == "wc_qualifying":
        mask = t.str.contains("World Cup", case=False, na=False) & \
               t.str.contains("Qual", case=False, na=False)
    elif competition_filter == "friendly":
        mask = t.str.contains("Friendly", case=False, na=False)
    else:  # "all"
        return df
    return df[mask]


def _winner_from_row(row: pd.Series, team_a: str, team_b: str) -> str:
    if row["home_score"] > row["away_score"]:
        return row["home_team"]
    if row["home_score"] < row["away_score"]:
        return row["away_team"]
    return "Draw"


def _venue(row: pd.Series, team: str) -> str:
    if str(row.get("neutral", "")).lower() in ("true", "1", "yes"):
        return "neutral"
    if row["home_team"].strip().lower() == team.strip().lower():
        return "home"
    return "away"


def _result(row: pd.Series, team: str) -> str:
    is_home = row["home_team"].strip().lower() == team.strip().lower()
    scored = row["home_score"] if is_home else row["away_score"]
    conceded = row["away_score"] if is_home else row["home_score"]
    if scored > conceded:
        return "W"
    if scored < conceded:
        return "L"
    return "D"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def get_h2h_record(
    team_a: str,
    team_b: str,
    competition_filter: str = "all",
    from_year: int = 2000,
) -> dict:
    """
    Return the head-to-head record between two national teams.

    Args:
        team_a: First team name (any common variant accepted).
        team_b: Second team name (any common variant accepted).
        competition_filter: One of 'all', 'world_cup', 'wc_qualifying', 'friendly'. Default 'all'.
        from_year: Only include matches from this year onwards. Default 2000.

    Returns a dict with total_matches, wins/draws/losses for each side,
    goals scored, and last 5 meetings.
    """
    try:
        canon_a = normalise_team_name(team_a)
        canon_b = normalise_team_name(team_b)
    except ValueError as e:
        return {"found": False, "error": str(e)}

    df = get_store()["international_matches"].copy()

    # Match rows involving both teams (either side)
    mask_ab = (
        df["home_team"].str.lower().str.contains(canon_a.lower(), regex=False, na=False) &
        df["away_team"].str.lower().str.contains(canon_b.lower(), regex=False, na=False)
    )
    mask_ba = (
        df["home_team"].str.lower().str.contains(canon_b.lower(), regex=False, na=False) &
        df["away_team"].str.lower().str.contains(canon_a.lower(), regex=False, na=False)
    )

    # Broaden: also check canonical contains dataset value
    rows_a = find_team_rows(df, "home_team", canon_a)
    rows_a_idx = set(rows_a.index)
    rows_b_away = find_team_rows(df, "away_team", canon_b)
    rows_b_away_idx = set(rows_b_away.index)

    rows_b_home = find_team_rows(df, "home_team", canon_b)
    rows_b_home_idx = set(rows_b_home.index)
    rows_a_away = find_team_rows(df, "away_team", canon_a)
    rows_a_away_idx = set(rows_a_away.index)

    combined_idx = (rows_a_idx & rows_b_away_idx) | (rows_b_home_idx & rows_a_away_idx)

    if not combined_idx:
        return {"found": False, "team_a": canon_a, "team_b": canon_b,
                "total_matches": 0, "team_a_wins": 0, "team_b_wins": 0, "draws": 0,
                "team_a_goals_scored": 0, "team_b_goals_scored": 0, "last_5_meetings": []}

    h2h = df.loc[list(combined_idx)].copy()

    # Year filter
    h2h = h2h[h2h["date"].dt.year >= from_year]

    # Competition filter
    h2h = _apply_competition_filter(h2h, competition_filter)

    if h2h.empty:
        return {"found": False, "team_a": canon_a, "team_b": canon_b,
                "total_matches": 0, "team_a_wins": 0, "team_b_wins": 0, "draws": 0,
                "team_a_goals_scored": 0, "team_b_goals_scored": 0, "last_5_meetings": []}

    h2h = h2h.sort_values("date", ascending=False)

    a_wins = draws = b_wins = 0
    a_goals = b_goals = 0

    for _, row in h2h.iterrows():
        hs, as_ = int(row["home_score"]), int(row["away_score"])
        # Determine which side is team_a
        a_is_home = canon_a.lower() in str(row["home_team"]).lower()
        if a_is_home:
            a_g, b_g = hs, as_
        else:
            a_g, b_g = as_, hs
        a_goals += a_g
        b_goals += b_g
        if hs == as_:
            draws += 1
        elif a_is_home == (hs > as_):
            a_wins += 1
        else:
            b_wins += 1

    last_5 = []
    for _, row in h2h.head(5).iterrows():
        winner = _winner_from_row(row, canon_a, canon_b)
        last_5.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_score": int(row["home_score"]),
            "away_score": int(row["away_score"]),
            "tournament": row["tournament"],
            "winner": winner,
        })

    return {
        "found": True,
        "team_a": canon_a,
        "team_b": canon_b,
        "total_matches": len(h2h),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals_scored": a_goals,
        "team_b_goals_scored": b_goals,
        "last_5_meetings": last_5,
    }


@tool
def get_team_recent_form(
    team: str,
    n: int = 10,
    competition_filter: str = "all",
) -> dict:
    """
    Return the last N matches for a national team with outcomes and a summary.

    Args:
        team: Team name (any common variant accepted).
        n: Number of recent matches to return. Default 10, max 20.
        competition_filter: One of 'all', 'world_cup', 'wc_qualifying', 'friendly'. Default 'all'.

    Returns wins/draws/losses summary plus individual match results.
    """
    try:
        canon = normalise_team_name(team)
    except ValueError as e:
        return {"found": False, "error": str(e)}

    n = min(max(1, n), 20)

    df = get_store()["international_matches"].copy()

    home_rows = find_team_rows(df, "home_team", canon)
    away_rows = find_team_rows(df, "away_team", canon)
    combined = pd.concat([home_rows, away_rows]).drop_duplicates()

    if combined.empty:
        return {"found": False, "team": canon, "matches_returned": 0,
                "wins": 0, "draws": 0, "losses": 0,
                "goals_scored": 0, "goals_conceded": 0, "matches": []}

    combined = _apply_competition_filter(combined, competition_filter)
    combined = combined.sort_values("date", ascending=False).head(n)

    wins = draws = losses = scored = conceded = 0
    matches = []

    for _, row in combined.iterrows():
        is_home = canon.lower() in str(row["home_team"]).lower()
        gs = int(row["home_score"]) if is_home else int(row["away_score"])
        gc = int(row["away_score"]) if is_home else int(row["home_score"])
        scored += gs
        conceded += gc

        res = "W" if gs > gc else ("L" if gs < gc else "D")
        if res == "W":
            wins += 1
        elif res == "L":
            losses += 1
        else:
            draws += 1

        opponent = row["away_team"] if is_home else row["home_team"]
        venue = _venue(row, canon)

        matches.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "opponent": opponent,
            "venue": venue,
            "score": f"{gs}-{gc}",
            "result": res,
            "tournament": row["tournament"],
        })

    return {
        "found": True,
        "team": canon,
        "matches_returned": len(matches),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_scored": scored,
        "goals_conceded": conceded,
        "matches": matches,
    }


@tool
def get_match_result(team_a: str, team_b: str, date: str) -> dict:
    """
    Look up the result of a specific international match.

    Args:
        team_a: One team in the match (any common variant accepted).
        team_b: The other team in the match (any common variant accepted).
        date: Match date in YYYY-MM-DD format.

    Returns score, winner, tournament, and venue details.
    """
    try:
        canon_a = normalise_team_name(team_a)
        canon_b = normalise_team_name(team_b)
    except ValueError as e:
        return {"found": False, "error": str(e)}

    try:
        target_date = pd.Timestamp(date)
    except Exception:
        return {"found": False, "error": f"Invalid date format: '{date}'. Use YYYY-MM-DD."}

    df = get_store()["international_matches"].copy()
    day_df = df[df["date"].dt.date == target_date.date()]

    if day_df.empty:
        return {"found": False, "date": date, "error": "No matches found on that date."}

    a_home = find_team_rows(day_df, "home_team", canon_a)
    result_rows = find_team_rows(a_home, "away_team", canon_b) if not a_home.empty else pd.DataFrame()

    if result_rows.empty:
        b_home = find_team_rows(day_df, "home_team", canon_b)
        result_rows = find_team_rows(b_home, "away_team", canon_a) if not b_home.empty else pd.DataFrame()

    if result_rows.empty:
        return {"found": False, "date": date, "team_a": canon_a, "team_b": canon_b,
                "error": "Match not found. Check team names and date."}

    row = result_rows.iloc[0]
    hs, as_ = int(row["home_score"]), int(row["away_score"])
    winner = row["home_team"] if hs > as_ else (row["away_team"] if as_ > hs else "Draw")

    return {
        "found": True,
        "date": row["date"].strftime("%Y-%m-%d"),
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "home_score": hs,
        "away_score": as_,
        "winner": winner,
        "tournament": row["tournament"],
        "neutral_venue": str(row.get("neutral", "")).lower() in ("true", "1", "yes"),
    }
