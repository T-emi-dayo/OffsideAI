"""
Player query tools.

Datasets:
  - players.csv       (player profiles with current market value)
  - transfers.csv     (transfer history with market value at time of move)
  - national_teams.csv (for squad value via total_market_value column)
"""
from __future__ import annotations

import pandas as pd
from langchain_core.tools import tool

from src.data.store import get_store
from src.tools.utils import find_team_rows, normalise_team_name


def _find_player(players_df: pd.DataFrame, name: str) -> pd.DataFrame:
    """
    Search players by full name, first name, or last name.
    Priority: exact full-name match > case-insensitive exact > substring.
    Returns all matching rows (may be multiple players with similar names).
    """
    key = name.strip().lower()

    # Exact full name (case-insensitive)
    mask_exact = players_df["name"].str.lower() == key
    if mask_exact.any():
        return players_df[mask_exact]

    # First-name or last-name exact
    mask_first = players_df["first_name"].fillna("").str.lower() == key
    mask_last = players_df["last_name"].fillna("").str.lower() == key
    if (mask_first | mask_last).any():
        return players_df[mask_first | mask_last]

    # Substring in full name
    mask_contains = players_df["name"].str.lower().str.contains(key, regex=False, na=False)
    if mask_contains.any():
        return players_df[mask_contains]

    # Part of the input is in the full name (handles "Messi" → "Lionel Messi")
    parts = key.split()
    for part in parts:
        if len(part) >= 3:
            mask_part = players_df["name"].str.lower().str.contains(part, regex=False, na=False)
            if mask_part.any():
                return players_df[mask_part]

    return players_df.iloc[0:0]


@tool
def get_player_value_history(player: str) -> dict:
    """
    Return a player's market value history over time, derived from transfer records.

    Args:
        player: Player name or partial name (e.g. 'Messi', 'Ronaldo', 'Kylian Mbappé').

    Returns nationality, current value, peak value + date, and a time series
    of market values at each recorded transfer date.
    """
    store = get_store()
    players_df = store["players"]
    transfers_df = store["transfers"]

    matches = _find_player(players_df, player)

    if matches.empty:
        return {"found": False, "player": player,
                "error": f"No player found matching '{player}'."}

    # If multiple matches, use the first (highest market value as tiebreak)
    if len(matches) > 1 and "market_value_in_eur" in matches.columns:
        matches = matches.sort_values("market_value_in_eur", ascending=False)

    row = matches.iloc[0]
    player_id = row["player_id"]
    full_name = row["name"]
    nationality = row.get("country_of_citizenship", "")
    current_value = row.get("market_value_in_eur", None)
    highest_value = row.get("highest_market_value_in_eur", None)

    # Build value history from transfers
    player_transfers = transfers_df[transfers_df["player_id"] == player_id].copy()
    player_transfers = player_transfers.sort_values("transfer_date")

    values = []
    for _, t in player_transfers.iterrows():
        mv = t.get("market_value_in_eur", None)
        if pd.notna(mv) and mv > 0:
            values.append({
                "date": t["transfer_date"].strftime("%Y-%m-%d"),
                "market_value_eur": float(mv),
            })

    # Derive peak from history or fallback to highest_market_value_in_eur
    if values:
        peak_entry = max(values, key=lambda v: v["market_value_eur"])
        peak_value = peak_entry["market_value_eur"]
        peak_date = peak_entry["date"]
    elif pd.notna(highest_value):
        peak_value = float(highest_value)
        peak_date = None
    else:
        peak_value = None
        peak_date = None

    return {
        "found": True,
        "player": full_name,
        "nationality": nationality if pd.notna(nationality) else "",
        "values": values,
        "peak_value_eur": peak_value,
        "peak_value_date": peak_date,
        "current_value_eur": float(current_value) if pd.notna(current_value) else None,
    }


@tool
def get_team_squad_value(team: str, date: str = "") -> dict:
    """
    Return the aggregate market value of a national team's squad.

    When no date is given, uses the pre-aggregated value from national_teams.csv
    (fastest path). When a date is provided, aggregates from player records.

    Args:
        team: Team name (any common variant accepted).
        date: Optional point-in-time snapshot in YYYY-MM-DD format. Default latest.

    Returns total squad value, average player value, and player count.
    """
    try:
        canon = normalise_team_name(team)
    except ValueError as e:
        return {"found": False, "error": str(e)}

    store = get_store()
    national_teams_df = store["national_teams"]

    team_row = find_team_rows(national_teams_df, "name", canon)
    if team_row.empty:
        team_row = find_team_rows(national_teams_df, "country_name", canon)

    if date:
        # Point-in-time: aggregate from players table
        try:
            target = pd.Timestamp(date)
        except Exception:
            return {"found": False, "error": f"Invalid date format '{date}'. Use YYYY-MM-DD."}

        if team_row.empty:
            return {"found": False, "team": canon, "error": "Team not found."}

        team_id = int(team_row.iloc[0]["national_team_id"])
        players_df = store["players"]
        squad = players_df[players_df["current_national_team_id"] == team_id].copy()

        if squad.empty:
            return {"found": False, "team": canon,
                    "error": "No player records linked to this national team."}

        values = squad["market_value_in_eur"].dropna()
        total = float(values.sum())
        avg = float(values.mean()) if len(values) > 0 else 0.0

        return {
            "found": True,
            "team": canon,
            "date": date,
            "total_squad_value_eur": total,
            "average_player_value_eur": round(avg, 2),
            "player_count": len(squad),
        }

    # No date: use pre-aggregated national_teams value
    if team_row.empty:
        return {"found": False, "team": canon, "error": "Team not found in national teams dataset."}

    nt = team_row.iloc[0]
    total_mv = nt.get("total_market_value", None)
    squad_size = nt.get("squad_size", None)

    if pd.notna(total_mv) and float(total_mv) > 0:
        avg = float(total_mv) / int(squad_size) if squad_size and int(squad_size) > 0 else 0.0
        return {
            "found": True,
            "team": canon,
            "date": "latest",
            "total_squad_value_eur": float(total_mv),
            "average_player_value_eur": round(avg, 2),
            "player_count": int(squad_size) if pd.notna(squad_size) else None,
        }

    # total_market_value missing: aggregate from player records
    team_id_val = nt.get("national_team_id", None)
    if pd.isna(team_id_val):
        return {"found": False, "team": canon, "error": "Market value data not available for this team."}

    players_df = store["players"]
    squad = players_df[players_df["current_national_team_id"] == int(team_id_val)].copy()
    values = squad["market_value_in_eur"].dropna()
    if values.empty:
        return {"found": False, "team": canon, "error": "No player market value data found for this team."}

    total = float(values.sum())
    avg = float(values.mean())
    return {
        "found": True,
        "team": canon,
        "date": "latest",
        "total_squad_value_eur": total,
        "average_player_value_eur": round(avg, 2),
        "player_count": len(squad),
    }
