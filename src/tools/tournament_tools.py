"""
Tournament query tools.

Datasets:
  - indepth_match_data.csv  (WC match details 2010-2022)
  - world_historical_general_data.csv  (WC edition summaries)
  - game_events.csv  (goal / card / sub events — WC matches)
  - players.csv  (player name lookup by player_id)
"""
from __future__ import annotations

import pandas as pd
from langchain_core.tools import tool

from src.data.store import get_store
from src.tools.utils import GROUP_STAGE_ROUNDS, WC_DATE_RANGES, WC_GROUPS, find_team_rows


def _third_place_team(df: pd.DataFrame, year: int) -> str:
    """Return the third-place team for a given WC year."""
    third = df[(df["Year"] == year) & (df["Round"].fillna("").str.lower() == "third-place match")]
    if third.empty:
        return ""
    row = third.iloc[0]
    hs, as_ = int(row["home_score"]), int(row["away_score"])
    if hs > as_:
        return row["home_team"]
    if as_ > hs:
        return row["away_team"]
    return ""


def _score_str(row: pd.Series) -> str:
    return f"{int(row['home_score'])}-{int(row['away_score'])}"


def _winner_str(row: pd.Series) -> str:
    hs, as_ = int(row["home_score"]), int(row["away_score"])
    if hs > as_:
        return row["home_team"]
    if as_ > hs:
        return row["away_team"]
    return "Draw"


@tool
def get_tournament_results(year: int, stage_filter: str = "all") -> dict:
    """
    Return results for a specific FIFA World Cup edition.

    Args:
        year: World Cup year (e.g. 2022, 2018, 2014, 2010).
        stage_filter: Filter to a specific stage — one of 'all', 'Group Stage',
                      'Round of 16', 'Quarter-finals', 'Semi-finals', 'Final'.
                      Default 'all'.

    Returns host, champion, runner-up, third-place, total goals,
    and a capped list of matches (max 20).
    """
    store = get_store()
    hist = store["world_historical"]
    indepth = store["indepth_match_data"].copy()

    hist_row = hist[hist["Year"] == year]
    if hist_row.empty:
        return {"found": False, "year": year, "error": f"No World Cup data found for {year}."}

    h = hist_row.iloc[0]
    year_matches = indepth[indepth["Year"] == year].copy()

    if stage_filter != "all":
        year_matches = year_matches[
            year_matches["Round"].fillna("").str.lower() == stage_filter.lower()
        ]

    total_goals = int(year_matches["home_score"].sum() + year_matches["away_score"].sum())
    third = _third_place_team(indepth, year)

    match_list = []
    for _, row in year_matches.sort_values("Date").head(20).iterrows():
        match_list.append({
            "stage": row.get("Round", ""),
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "score": _score_str(row),
            "winner": _winner_str(row),
        })

    return {
        "found": True,
        "year": int(year),
        "host": str(h["Host"]),
        "winner": str(h["Champion"]),
        "runner_up": str(h["Runner-Up"]),
        "third_place": third,
        "total_matches": len(year_matches),
        "total_goals": total_goals,
        "matches": match_list,
    }


@tool
def get_tournament_top_scorers(year: int, top_n: int = 10) -> dict:
    """
    Return the top scorers for a FIFA World Cup edition.

    Args:
        year: World Cup year (e.g. 2022, 2018, 2014, 2010).
        top_n: Number of top scorers to return. Default 10, max 20.

    Returns a ranked list of players with their goal tally and team.
    Falls back to the golden boot entry from historical data if
    goal-event data is unavailable for the requested year.
    """
    top_n = min(max(1, top_n), 20)
    store = get_store()

    if year not in WC_DATE_RANGES:
        # Fallback: return historical golden boot entry only
        hist = store["world_historical"]
        row = hist[hist["Year"] == year]
        if row.empty:
            return {"found": False, "year": year, "error": f"No data for World Cup {year}."}
        entry = str(row.iloc[0]["TopScorrer"])
        return {
            "found": True,
            "year": year,
            "note": "Detailed per-player data unavailable; returning Golden Boot winner only.",
            "top_scorers": [{"player": entry, "team": "", "goals": None}],
        }

    start, end = WC_DATE_RANGES[year]
    events = store["game_events"].copy()
    goals = events[
        (events["date"] >= start) &
        (events["date"] <= end) &
        (events["type"].str.lower() == "goals")
    ]

    if goals.empty:
        return {"found": False, "year": year, "error": "No goal events found for this tournament."}

    # Aggregate goals per player
    agg = (
        goals.groupby("player_id")
        .agg(goals_count=("player_id", "count"), team=("club_name", "first"))
        .reset_index()
        .sort_values("goals_count", ascending=False)
        .head(top_n)
    )

    # Attempt player name lookup
    players_df = store["players"]
    pid_to_name: dict = {}
    if not players_df.empty and "player_id" in players_df.columns:
        p_sub = players_df[["player_id", "name"]].dropna(subset=["name"])
        pid_to_name = dict(zip(p_sub["player_id"], p_sub["name"]))

    scorers = []
    for _, row in agg.iterrows():
        pid = row["player_id"]
        name = pid_to_name.get(pid, f"Player #{int(pid)}")
        scorers.append({
            "player": name,
            "team": row["team"],
            "goals": int(row["goals_count"]),
        })

    return {
        "found": True,
        "year": year,
        "top_scorers": scorers,
    }


@tool
def get_wc_group_results(year: int, group: str) -> dict:
    """
    Return standings and match results for a specific group in a World Cup edition.

    Args:
        year: World Cup year (2010, 2014, 2018, or 2022).
        group: Group letter, e.g. 'A', 'B', 'C' ... 'H'.

    Returns a standings table (sorted by points, GD, GF) and list of group matches.
    The 'advanced' flag marks the top-2 teams in final standings.
    """
    group_upper = group.strip().upper()

    if year not in WC_GROUPS:
        available = sorted(WC_GROUPS.keys())
        return {"found": False, "error": f"Group data not available for {year}. Available: {available}"}

    year_groups = WC_GROUPS[year]
    if group_upper not in year_groups:
        available = sorted(year_groups.keys())
        return {"found": False, "year": year, "error": f"Group '{group}' not found. Available groups: {available}"}

    group_teams = year_groups[group_upper]

    df = get_store()["indepth_match_data"].copy()
    year_gs = df[
        (df["Year"] == year) &
        (df["Round"].fillna("").str.lower().isin(GROUP_STAGE_ROUNDS))
    ]

    # Collect all matches where both home and away are in this group
    match_rows = []
    for _, row in year_gs.iterrows():
        home = str(row["home_team"])
        away = str(row["away_team"])

        home_in = any(t.lower() in home.lower() or home.lower() in t.lower() for t in group_teams)
        away_in = any(t.lower() in away.lower() or away.lower() in t.lower() for t in group_teams)

        if home_in and away_in:
            match_rows.append(row)

    # Build standings initialised from canonical group_teams list
    standings: dict[str, dict] = {
        t: {"team": t, "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0}
        for t in group_teams
    }

    match_list = []
    for row in match_rows:
        hs, as_ = int(row["home_score"]), int(row["away_score"])
        home_name = str(row["home_team"])
        away_name = str(row["away_team"])

        # Map dataset names to canonical group team names
        home_canon = next((t for t in group_teams if t.lower() in home_name.lower() or home_name.lower() in t.lower()), home_name)
        away_canon = next((t for t in group_teams if t.lower() in away_name.lower() or away_name.lower() in t.lower()), away_name)

        for canon in (home_canon, away_canon):
            if canon not in standings:
                standings[canon] = {"team": canon, "played": 0, "wins": 0, "draws": 0, "losses": 0,
                                    "goals_for": 0, "goals_against": 0}

        standings[home_canon]["played"] += 1
        standings[away_canon]["played"] += 1
        standings[home_canon]["goals_for"] += hs
        standings[home_canon]["goals_against"] += as_
        standings[away_canon]["goals_for"] += as_
        standings[away_canon]["goals_against"] += hs

        if hs > as_:
            standings[home_canon]["wins"] += 1
            standings[away_canon]["losses"] += 1
        elif as_ > hs:
            standings[away_canon]["wins"] += 1
            standings[home_canon]["losses"] += 1
        else:
            standings[home_canon]["draws"] += 1
            standings[away_canon]["draws"] += 1

        match_list.append({
            "home_team": home_canon,
            "away_team": away_canon,
            "score": f"{hs}-{as_}",
        })

    # Sort standings: points → GD → GF
    table = list(standings.values())
    for entry in table:
        entry["points"] = entry["wins"] * 3 + entry["draws"]
        entry["goal_difference"] = entry["goals_for"] - entry["goals_against"]

    table.sort(key=lambda x: (-x["points"], -x["goal_difference"], -x["goals_for"]))

    for i, entry in enumerate(table):
        entry["position"] = i + 1
        entry["advanced"] = i < 2

    if not match_rows:
        return {"found": False, "year": year, "group": group_upper,
                "error": "No group stage match data found. Data covers WC 2010-2022."}

    return {
        "found": True,
        "year": year,
        "group": group_upper,
        "standings": table,
        "matches": match_list,
    }
