"""
Team profile query tools.

Primary dataset: indepth_match_data.csv (WC matches 2010-2022)
Secondary dataset: national_teams.csv (confederation membership)
"""
from __future__ import annotations

import pandas as pd
from langchain_core.tools import tool

from src.data.store import get_store
from src.tools.utils import (
    GROUP_STAGE_ROUNDS,
    STAGE_PARAM_MAP,
    find_team_rows,
    get_stage_rank,
    normalise_team_name,
)


def _find_wc_rows(df: pd.DataFrame, canonical_team: str) -> pd.DataFrame:
    """Return all indepth_match_data rows where the team appears as home or away."""
    home = find_team_rows(df, "home_team", canonical_team)
    away = find_team_rows(df, "away_team", canonical_team)
    combined = pd.concat([home, away]).drop_duplicates()
    return combined


def _team_score(row: pd.Series, canonical_team: str) -> tuple[int, int]:
    """Return (goals_scored, goals_conceded) for the team from a match row."""
    is_home = canonical_team.lower() in str(row["home_team"]).lower()
    if is_home:
        return int(row["home_score"]), int(row["away_score"])
    return int(row["away_score"]), int(row["home_score"])


def _match_result(row: pd.Series, canonical_team: str) -> str:
    gs, gc = _team_score(row, canonical_team)
    if gs > gc:
        return "W"
    if gs < gc:
        return "L"
    return "D"


def _opponent(row: pd.Series, canonical_team: str) -> str:
    if canonical_team.lower() in str(row["home_team"]).lower():
        return row["away_team"]
    return row["home_team"]


def _stage_label(round_val: str, team: str, row: pd.Series) -> str:
    """Map Round value to architecture stage label; upgrade to 'Winner' if team won the Final."""
    rv_lower = round_val.strip().lower()
    if rv_lower == "final":
        gs, gc = _team_score(row, team)
        if gs > gc:
            return "Winner"
        return "Final"
    if rv_lower in GROUP_STAGE_ROUNDS:
        return "Group Stage"
    stage_map = {
        "round of 16": "R16",
        "second round": "R16",
        "quarter-finals": "QF",
        "semi-finals": "SF",
        "third-place match": "3rd Place",
    }
    return stage_map.get(rv_lower, round_val)


@tool
def get_team_wc_history(team: str) -> dict:
    """
    Return a team's complete World Cup participation history (2010-2022).

    Args:
        team: Team name (any common variant accepted).

    Returns total appearances, titles, finals/semi-final counts,
    and per-tournament breakdown with goals and stage reached.
    """
    try:
        canon = normalise_team_name(team)
    except ValueError as e:
        return {"found": False, "error": str(e)}

    df = get_store()["indepth_match_data"].copy()
    rows = _find_wc_rows(df, canon)

    if rows.empty:
        return {"found": False, "team": canon, "total_appearances": 0,
                "titles": 0, "finals_reached": 0, "semifinal_appearances": 0,
                "group_stage_exits": 0, "tournaments": []}

    titles = finals = semis = group_exits = 0
    tournaments = []

    for year, year_rows in rows.groupby("Year"):
        goals_scored = goals_conceded = 0
        best_stage_rank = 0
        best_stage_label = "Group Stage"

        for _, row in year_rows.iterrows():
            gs, gc = _team_score(row, canon)
            goals_scored += gs
            goals_conceded += gc

            round_val = str(row.get("Round", "Group Stage"))
            rank = get_stage_rank(round_val)

            if rank > best_stage_rank:
                best_stage_rank = rank
                best_stage_label = _stage_label(round_val, canon, row)

        # Count aggregate stats
        if best_stage_label == "Winner":
            titles += 1
            finals += 1
            semis += 1
        elif best_stage_label == "Final":
            finals += 1
            semis += 1
        elif best_stage_label in ("SF", "3rd Place"):
            semis += 1
        elif best_stage_label in ("Group Stage", "R16"):
            # R16 exits are sometimes considered group-stage-era exits in older formats
            if best_stage_label == "Group Stage":
                group_exits += 1

        host_val = year_rows.iloc[0].get("Host", "")
        tournaments.append({
            "year": int(year),
            "host": str(host_val),
            "stage_reached": best_stage_label,
            "matches_played": len(year_rows),
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
        })

    tournaments.sort(key=lambda t: t["year"])

    return {
        "found": True,
        "team": canon,
        "total_appearances": len(tournaments),
        "titles": titles,
        "finals_reached": finals,
        "semifinal_appearances": semis,
        "group_stage_exits": group_exits,
        "tournaments": tournaments,
    }


@tool
def get_team_wc_stage_record(team: str, stage: str) -> dict:
    """
    Return a team's win/loss record at a specific World Cup stage across all editions (2010-2022).

    Args:
        team: Team name (any common variant accepted).
        stage: One of 'group_stage', 'r16', 'quarter_final', 'semi_final', 'final'.

    Returns appearances at that stage, W/D/L record, and list of individual matches.
    """
    try:
        canon = normalise_team_name(team)
    except ValueError as e:
        return {"found": False, "error": str(e)}

    stage_key = stage.lower().replace(" ", "_")
    if stage_key not in STAGE_PARAM_MAP:
        valid = ", ".join(STAGE_PARAM_MAP.keys())
        return {"found": False, "error": f"Invalid stage '{stage}'. Valid options: {valid}"}

    round_value = STAGE_PARAM_MAP[stage_key]

    df = get_store()["indepth_match_data"].copy()
    rows = _find_wc_rows(df, canon)

    if rows.empty:
        return {"found": False, "team": canon, "stage": stage,
                "appearances_at_stage": 0, "record": {"wins": 0, "draws": 0, "losses": 0}, "matches": []}

    stage_rows = rows[rows["Round"].fillna("").str.lower() == round_value.lower()]

    if stage_rows.empty:
        return {"found": False, "team": canon, "stage": round_value,
                "appearances_at_stage": 0, "record": {"wins": 0, "draws": 0, "losses": 0}, "matches": []}

    wins = draws = losses = 0
    matches = []

    for _, row in stage_rows.sort_values("Year").iterrows():
        gs, gc = _team_score(row, canon)
        res = "W" if gs > gc else ("L" if gs < gc else "D")
        if res == "W":
            wins += 1
        elif res == "L":
            losses += 1
        else:
            draws += 1

        opp = _opponent(row, canon)
        matches.append({
            "year": int(row["Year"]),
            "opponent": opp,
            "score": f"{gs}-{gc}",
            "result": res,
        })

    return {
        "found": True,
        "team": canon,
        "stage": round_value,
        "appearances_at_stage": len(matches),
        "record": {"wins": wins, "draws": draws, "losses": losses},
        "matches": matches,
    }


@tool
def get_confederation_teams(confederation: str) -> dict:
    """
    Return all national teams from a given confederation.

    Args:
        confederation: One of 'UEFA', 'CONMEBOL', 'CONCACAF', 'CAF', 'AFC', 'OFC'.

    Returns team count and sorted list of team names.
    """
    valid = {"UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"}
    conf_upper = confederation.strip().upper()

    if conf_upper not in valid:
        return {"found": False, "error": f"Invalid confederation '{confederation}'. Valid: {', '.join(sorted(valid))}"}

    df = get_store()["national_teams"]
    filtered = df[df["confederation"].str.upper() == conf_upper]

    if filtered.empty:
        return {"confederation": conf_upper, "team_count": 0, "teams": []}

    teams = sorted(filtered["name"].dropna().tolist())
    return {
        "confederation": conf_upper,
        "team_count": len(teams),
        "teams": teams,
    }
