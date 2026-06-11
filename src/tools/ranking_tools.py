"""
FIFA rankings query tools.

Dataset: fifa_rankings.csv
Columns: rank, country_full, country_abrv, total_points, previous_points,
         rank_change, confederation, rank_date
"""
from __future__ import annotations

from datetime import date as dt_date

import pandas as pd
from langchain_core.tools import tool

from src.data.store import get_store
from src.tools.utils import find_team_rows, normalise_team_name


def _as_of_snapshot(df: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """
    Return each team's most recent ranking record on or before `as_of`.
    """
    past = df[df["rank_date"] <= as_of].copy()
    if past.empty:
        return past
    idx = past.groupby("country_full")["rank_date"].idxmax()
    return past.loc[idx]


def _find_team_in_rankings(df: pd.DataFrame, canonical_team: str) -> pd.DataFrame:
    """Flexible match against country_full and country_abrv columns."""
    rows = find_team_rows(df, "country_full", canonical_team)
    if rows.empty:
        rows = find_team_rows(df, "country_abrv", canonical_team)
    return rows


@tool
def get_fifa_ranking(team: str, date: str) -> dict:
    """
    Return the FIFA ranking for a team at a specific point in time.

    Uses the most recent ranking record on or before the provided date.

    Args:
        team: Team name (any common variant accepted).
        date: Date for ranking lookup in YYYY-MM-DD format.

    Returns rank, points, and the actual ranking date used.
    """
    try:
        canon = normalise_team_name(team)
    except ValueError as e:
        return {"found": False, "error": str(e)}

    try:
        target = pd.Timestamp(date)
    except Exception:
        return {"found": False, "error": f"Invalid date format '{date}'. Use YYYY-MM-DD."}

    df = get_store()["fifa_rankings"].copy()
    team_rows = _find_team_in_rankings(df, canon)

    if team_rows.empty:
        return {"found": False, "team": canon, "error": "Team not found in FIFA rankings dataset."}

    past = team_rows[team_rows["rank_date"] <= target]
    if past.empty:
        return {"found": False, "team": canon,
                "error": f"No ranking record found for {canon} on or before {date}."}

    row = past.loc[past["rank_date"].idxmax()]

    return {
        "found": True,
        "team": canon,
        "ranking_date": row["rank_date"].strftime("%Y-%m-%d"),
        "rank": int(row["rank"]),
        "total_points": float(row["total_points"]),
    }


@tool
def get_top_ranked_teams(date: str, top_n: int = 20, confederation: str = "") -> dict:
    """
    Return the top N ranked national teams at a point in time.

    Args:
        date: Date for snapshot in YYYY-MM-DD format.
        top_n: Number of teams to return. Default 20, max 50.
        confederation: Filter by confederation — one of 'UEFA', 'CONMEBOL', 'CONCACAF',
                       'CAF', 'AFC', 'OFC'. Leave empty for global ranking.

    Returns a ranked list of teams with their confederation and points.
    """
    top_n = min(max(1, top_n), 50)

    try:
        target = pd.Timestamp(date)
    except Exception:
        return {"found": False, "error": f"Invalid date format '{date}'. Use YYYY-MM-DD."}

    df = get_store()["fifa_rankings"].copy()
    snapshot = _as_of_snapshot(df, target)

    if snapshot.empty:
        return {"ranking_date": date, "teams": [],
                "error": "No ranking data found on or before that date."}

    if confederation:
        conf_upper = confederation.strip().upper()
        snapshot = snapshot[snapshot["confederation"].str.upper() == conf_upper]

    snapshot = snapshot.sort_values("rank").head(top_n)
    actual_date = snapshot["rank_date"].max().strftime("%Y-%m-%d")

    teams = []
    for _, row in snapshot.iterrows():
        teams.append({
            "rank": int(row["rank"]),
            "team": row["country_full"],
            "confederation": row["confederation"],
            "total_points": float(row["total_points"]),
        })

    return {
        "ranking_date": actual_date,
        "teams": teams,
    }


@tool
def get_ranking_trajectory(
    team: str,
    from_year: int = 2010,
    to_year: int = dt_date.today().year,
) -> dict:
    """
    Return how a team's FIFA ranking has changed over time.

    Samples one record per year (earliest in that year) to show trajectory.

    Args:
        team: Team name (any common variant accepted).
        from_year: Start year. Default 2010.
        to_year: End year. Default current year.

    Returns rank snapshots, peak rank + date, and current rank.
    """
    try:
        canon = normalise_team_name(team)
    except ValueError as e:
        return {"found": False, "error": str(e)}

    df = get_store()["fifa_rankings"].copy()
    team_rows = _find_team_in_rankings(df, canon)

    if team_rows.empty:
        return {"found": False, "team": canon, "error": "Team not found in FIFA rankings dataset."}

    filtered = team_rows[
        (team_rows["rank_date"].dt.year >= from_year) &
        (team_rows["rank_date"].dt.year <= to_year)
    ].copy()

    if filtered.empty:
        return {"found": False, "team": canon,
                "error": f"No ranking records for {canon} between {from_year} and {to_year}."}

    # One record per year — take the earliest entry in each year
    filtered["year"] = filtered["rank_date"].dt.year
    yearly = filtered.loc[filtered.groupby("year")["rank_date"].idxmin()].sort_values("rank_date")

    snapshots = []
    for _, row in yearly.iterrows():
        snapshots.append({
            "date": row["rank_date"].strftime("%Y-%m-%d"),
            "rank": int(row["rank"]),
            "total_points": float(row["total_points"]),
        })

    peak_row = filtered.loc[filtered["rank"].idxmin()]
    current_row = filtered.loc[filtered["rank_date"].idxmax()]

    return {
        "found": True,
        "team": canon,
        "snapshots": snapshots,
        "peak_rank": int(peak_row["rank"]),
        "peak_rank_date": peak_row["rank_date"].strftime("%Y-%m-%d"),
        "current_rank": int(current_row["rank"]),
    }
