"""
Shared utilities for all query tools.
Provides team name normalisation, flexible DataFrame row matching,
WC group assignments, and tournament date ranges.
"""
from __future__ import annotations

import difflib
import unicodedata
from functools import lru_cache

import pandas as pd

from src.data.store import get_store

# ---------------------------------------------------------------------------
# Team name alias table — maps common/colloquial variants to canonical names.
# Canonical names are those used in national_teams.csv (country_name field).
# ---------------------------------------------------------------------------
ALIAS_TABLE: dict[str, str] = {
    # United States
    "usa": "United States",
    "us": "United States",
    "united states of america": "United States",
    "u.s.a.": "United States",
    "u.s.": "United States",
    # Iran
    "iran": "IR Iran",
    "islamic republic of iran": "IR Iran",
    # Korea
    "south korea": "Korea Republic",
    "korea": "Korea Republic",
    "republic of korea": "Korea Republic",
    "north korea": "Korea DPR",
    "dprk": "Korea DPR",
    "democratic peoples republic of korea": "Korea DPR",
    # Netherlands
    "holland": "Netherlands",
    "the netherlands": "Netherlands",
    # Côte d'Ivoire
    "ivory coast": "Côte d'Ivoire",
    "cote divoire": "Côte d'Ivoire",
    "cote d'ivoire": "Côte d'Ivoire",
    "côte d'ivoire": "Côte d'Ivoire",
    # Czech Republic
    "czechia": "Czech Republic",
    "czech": "Czech Republic",
    # Bosnia
    "bosnia": "Bosnia and Herzegovina",
    "bosnia herzegovina": "Bosnia and Herzegovina",
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    # Trinidad
    "trinidad": "Trinidad and Tobago",
    "t&t": "Trinidad and Tobago",
    # UAE
    "uae": "United Arab Emirates",
    "emirates": "United Arab Emirates",
    # DR Congo
    "drc": "DR Congo",
    "congo dr": "DR Congo",
    "democratic republic of congo": "DR Congo",
    "democratic republic of the congo": "DR Congo",
    "congo democratic republic": "DR Congo",
    # Cape Verde
    "cape verde": "Cape Verde Islands",
    # North Macedonia
    "north macedonia": "North Macedonia",
    "macedonia": "North Macedonia",
    # Others
    "republic of ireland": "Republic of Ireland",
    "eire": "Republic of Ireland",
    "russia": "Russia",
    "chinese taipei": "Chinese Taipei",
    "taiwan": "Chinese Taipei",
    "kyrgyzstan": "Kyrgyz Republic",
    "kyrgyz": "Kyrgyz Republic",
    "palestine": "Palestine",
    "saint lucia": "St. Lucia",
    "saint kitts": "St. Kitts and Nevis",
    "saint vincent": "St. Vincent and the Grenadines",
    "curacao": "Curaçao",
}


@lru_cache(maxsize=1)
def _canonical_names() -> list[str]:
    """All team names from national_teams.csv — the canonical name set."""
    df = get_store()["national_teams"]
    return df["name"].dropna().tolist()


def _strip(s: str) -> str:
    """Lowercase, strip whitespace, collapse internal spaces."""
    return " ".join(s.lower().strip().split())


def _remove_accents(s: str) -> str:
    """Remove diacritics for fallback accent-insensitive matching."""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii")


def normalise_team_name(name: str) -> str:
    """
    Resolve any team name variant to its canonical form.

    Lookup order:
    1. ALIAS_TABLE (exact colloquial variants)
    2. Case-insensitive exact match against canonical names
    3. Accent-stripped exact match
    4. Substring containment match (canonical in input OR input in canonical)
    5. difflib fuzzy match (cutoff 0.70)

    Raises ValueError with suggestions if no match is found.
    """
    if not name or not isinstance(name, str):
        raise ValueError("team name must be a non-empty string")

    key = _strip(name)

    # 1. Alias table
    if key in ALIAS_TABLE:
        return ALIAS_TABLE[key]

    canonicals = _canonical_names()
    lower_canon = {c.lower(): c for c in canonicals}

    # 2. Case-insensitive exact
    if key in lower_canon:
        return lower_canon[key]

    # 3. Accent-stripped exact
    stripped_key = _remove_accents(key)
    stripped_canon = {_remove_accents(c.lower()): c for c in canonicals}
    if stripped_key in stripped_canon:
        return stripped_canon[stripped_key]

    # 4. Substring containment
    matches = [c for c in canonicals if key in c.lower() or c.lower() in key]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # Prefer shortest (most specific) match
        return min(matches, key=len)

    # 5. Fuzzy
    suggestions = difflib.get_close_matches(key, [c.lower() for c in canonicals], n=3, cutoff=0.70)
    readable = [lower_canon[s] for s in suggestions]
    msg = f"Unknown team '{name}'."
    if readable:
        msg += f" Did you mean: {', '.join(readable)}?"
    raise ValueError(msg)


def find_team_rows(df: pd.DataFrame, col: str | list[str], team: str) -> pd.DataFrame:
    """
    Return rows where any of the given column(s) contains the team name.
    Tries: exact → case-insensitive exact → substring containment.
    Never raises; returns empty DataFrame on no match.
    """
    cols = [col] if isinstance(col, str) else col
    key = team.strip()
    key_lower = key.lower()

    for c in cols:
        series = df[c].fillna("")

        # Exact
        mask = series == key
        if mask.any():
            return df[mask]

        # Case-insensitive exact
        mask = series.str.lower() == key_lower
        if mask.any():
            return df[mask]

    # Substring containment across all listed columns
    combined = pd.Series(False, index=df.index)
    for c in cols:
        series = df[c].fillna("")
        combined |= series.str.lower().str.contains(key_lower, regex=False, na=False)
        combined |= series.apply(lambda v: key_lower in str(v).lower())
    if combined.any():
        return df[combined]

    return df.iloc[0:0]  # empty, same columns


# ---------------------------------------------------------------------------
# WC tournament date ranges  (used to slice game_events by year)
# ---------------------------------------------------------------------------
WC_DATE_RANGES: dict[int, tuple[str, str]] = {
    2010: ("2010-06-11", "2010-07-11"),
    2014: ("2014-06-12", "2014-07-13"),
    2018: ("2018-06-14", "2018-07-15"),
    2022: ("2022-11-20", "2022-12-18"),
}

# ---------------------------------------------------------------------------
# WC group assignments (hardcoded — no group letter in indepth_match_data.csv)
# Team names match the spellings used in indepth_match_data.csv where known,
# with fallback to canonical names for flexible matching.
# ---------------------------------------------------------------------------
WC_GROUPS: dict[int, dict[str, list[str]]] = {
    2022: {
        "A": ["Qatar", "Ecuador", "Senegal", "Netherlands"],
        "B": ["England", "IR Iran", "United States", "Wales"],
        "C": ["Argentina", "Saudi Arabia", "Mexico", "Poland"],
        "D": ["France", "Australia", "Denmark", "Tunisia"],
        "E": ["Spain", "Costa Rica", "Germany", "Japan"],
        "F": ["Belgium", "Canada", "Morocco", "Croatia"],
        "G": ["Brazil", "Serbia", "Switzerland", "Cameroon"],
        "H": ["Portugal", "Ghana", "Uruguay", "Korea Republic"],
    },
    2018: {
        "A": ["Russia", "Saudi Arabia", "Egypt", "Uruguay"],
        "B": ["Portugal", "Spain", "Morocco", "IR Iran"],
        "C": ["France", "Australia", "Peru", "Denmark"],
        "D": ["Argentina", "Iceland", "Croatia", "Nigeria"],
        "E": ["Brazil", "Switzerland", "Costa Rica", "Serbia"],
        "F": ["Germany", "Mexico", "Sweden", "Korea Republic"],
        "G": ["Belgium", "Panama", "Tunisia", "England"],
        "H": ["Poland", "Senegal", "Colombia", "Japan"],
    },
    2014: {
        "A": ["Brazil", "Croatia", "Mexico", "Cameroon"],
        "B": ["Spain", "Netherlands", "Chile", "Australia"],
        "C": ["Colombia", "Greece", "Côte d'Ivoire", "Japan"],
        "D": ["Uruguay", "Costa Rica", "England", "Italy"],
        "E": ["Switzerland", "Ecuador", "France", "Honduras"],
        "F": ["Argentina", "Bosnia and Herzegovina", "IR Iran", "Nigeria"],
        "G": ["Germany", "Portugal", "Ghana", "United States"],
        "H": ["Belgium", "Algeria", "Russia", "Korea Republic"],
    },
    2010: {
        "A": ["South Africa", "Mexico", "Uruguay", "France"],
        "B": ["Argentina", "Nigeria", "Korea Republic", "Greece"],
        "C": ["England", "United States", "Algeria", "Slovenia"],
        "D": ["Germany", "Australia", "Serbia", "Ghana"],
        "E": ["Netherlands", "Denmark", "Japan", "Cameroon"],
        "F": ["Italy", "Paraguay", "New Zealand", "Slovakia"],
        "G": ["Brazil", "Korea DPR", "Côte d'Ivoire", "Portugal"],
        "H": ["Spain", "Switzerland", "Honduras", "Chile"],
    },
}

# ---------------------------------------------------------------------------
# Stage rank ordering for deriving best stage reached.
# Keys are lowercase-normalised for case-insensitive lookup via get_stage_rank().
# ---------------------------------------------------------------------------
_STAGE_RANK_LOWER: dict[str, int] = {
    "group stage": 1,
    "first round": 1,
    "first group stage": 1,
    "second group stage": 1,
    "group stage play-off": 1,
    "final stage": 1,
    "second round": 2,
    "round of 16": 2,
    "quarter-finals": 3,
    "semi-finals": 4,
    "third-place match": 4,
    "final": 5,
}

# Public alias kept for any direct dict access elsewhere
STAGE_RANK = _STAGE_RANK_LOWER


def get_stage_rank(round_val: str) -> int:
    """Return the numeric rank for a Round value (case-insensitive). Unknown → 0."""
    return _STAGE_RANK_LOWER.get(str(round_val).strip().lower(), 0)


# Group stage round labels — any of these counts as "group stage" for filtering
GROUP_STAGE_ROUNDS = {
    "group stage", "first round", "first group stage",
    "second group stage", "group stage play-off", "final stage",
}

STAGE_PARAM_MAP: dict[str, str] = {
    "group_stage": "group stage",
    "r16": "Round of 16",
    "round_of_16": "Round of 16",
    "quarter_final": "Quarter-finals",
    "quarter_finals": "Quarter-finals",
    "qf": "Quarter-finals",
    "semi_final": "Semi-finals",
    "semi_finals": "Semi-finals",
    "sf": "Semi-finals",
    "final": "Final",
}
