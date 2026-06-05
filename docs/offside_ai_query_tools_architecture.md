# Offside AI — Query Tools Architecture

**Version:** 0.1  
**Purpose:** Define the scope, parameters, and return contracts for all structured query tools available to agents. Use this document to cross-reference against available dataset features and determine which tools are buildable.

---

## Design Principles

- Every tool is a thin, stateless function over a preloaded pandas DataFrame
- All team name inputs pass through a shared `normalise_team_name()` utility before querying
- All tools return a plain `dict` — no DataFrames, no Series, no raw row dumps
- Empty results return `{"found": False, ...}` — never raise, never return `None`
- Lists in return payloads are capped to avoid bloating agent context (max ~20 records unless summary is requested)
- Tools are grouped into domains; agents receive only the tools relevant to their function

---

## Domain Map

| Domain | Module | Primary Agents |
|---|---|---|
| Match History | `match_tools.py` | PreMatchAgent, PostMatchAgent, ChatAgent |
| Team Profile | `team_tools.py` | PreMatchAgent, ChatAgent |
| Tournament | `tournament_tools.py` | PostMatchAgent, ChatAgent |
| FIFA Rankings | `ranking_tools.py` | PreMatchAgent, ChatAgent |
| Player | `player_tools.py` | ChatAgent |

---

## Domain 1 — Match History (`match_tools.py`)

Core dataset: international matches (your `df_filtered`, 15,781 rows).

---

### `get_h2h_record`

Returns the head-to-head record between two national teams.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `team_a` | `str` | Yes | First team, FIFA standard name |
| `team_b` | `str` | Yes | Second team, FIFA standard name |
| `competition_filter` | `str` | No | One of `"all"`, `"world_cup"`, `"wc_qualifying"`, `"friendly"` — default `"all"` |
| `from_year` | `int` | No | Filter matches from this year onwards — default `2000` |

**Returns**

```python
{
    "found": bool,
    "team_a": str,
    "team_b": str,
    "total_matches": int,
    "team_a_wins": int,
    "team_b_wins": int,
    "draws": int,
    "team_a_goals_scored": int,
    "team_b_goals_scored": int,
    "last_5_meetings": [
        {
            "date": str,
            "home_team": str,
            "away_team": str,
            "home_score": int,
            "away_score": int,
            "tournament": str,
            "winner": str   # team name or "Draw"
        }
    ]
}
```

**Data dependency:** `home_team`, `away_team`, `home_score`, `away_score`, `date`, `tournament` columns in `df_filtered`.

---

### `get_team_recent_form`

Returns the last N matches for a team with outcomes.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `team` | `str` | Yes | Team name |
| `n` | `int` | No | Number of recent matches to return — default `10` |
| `competition_filter` | `str` | No | Same filter options as above — default `"all"` |

**Returns**

```python
{
    "found": bool,
    "team": str,
    "matches_returned": int,
    "wins": int,
    "draws": int,
    "losses": int,
    "goals_scored": int,
    "goals_conceded": int,
    "matches": [
        {
            "date": str,
            "opponent": str,
            "venue": str,           # "home" | "away" | "neutral"
            "score": str,           # "2-1"
            "result": str,          # "W" | "D" | "L"
            "tournament": str
        }
    ]
}
```

**Data dependency:** `home_team`, `away_team`, `home_score`, `away_score`, `neutral`, `date`, `tournament`.

---

### `get_match_result`

Looks up the result of a specific match.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `team_a` | `str` | Yes | One team in the match |
| `team_b` | `str` | Yes | The other team |
| `date` | `str` | Yes | Match date in `YYYY-MM-DD` format |

**Returns**

```python
{
    "found": bool,
    "date": str,
    "home_team": str,
    "away_team": str,
    "home_score": int,
    "away_score": int,
    "winner": str,          # team name or "Draw"
    "tournament": str,
    "neutral_venue": bool
}
```

**Data dependency:** `date`, `home_team`, `away_team`, `home_score`, `away_score`, `tournament`, `neutral`.

---

## Domain 2 — Team Profile (`team_tools.py`)

Core dataset: `df_filtered` + `world_cup_df`.

---

### `get_team_wc_history`

Returns a team's complete World Cup participation history.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `team` | `str` | Yes | Team name |

**Returns**

```python
{
    "found": bool,
    "team": str,
    "total_appearances": int,
    "titles": int,
    "finals_reached": int,
    "semifinal_appearances": int,
    "group_stage_exits": int,
    "tournaments": [
        {
            "year": int,
            "host": str,
            "stage_reached": str,   # "Group Stage" | "R16" | "QF" | "SF" | "Final" | "Winner"
            "matches_played": int,
            "goals_scored": int,
            "goals_conceded": int
        }
    ]
}
```

**Data dependency:** `world_cup_df` — `year`, `team`, `stage`, `goals_scored`, `goals_conceded`.

---

### `get_team_wc_stage_record`

Returns a team's win/loss record at a specific tournament stage across all WC editions.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `team` | `str` | Yes | Team name |
| `stage` | `str` | Yes | One of `"group_stage"`, `"r16"`, `"quarter_final"`, `"semi_final"`, `"final"` |

**Returns**

```python
{
    "found": bool,
    "team": str,
    "stage": str,
    "appearances_at_stage": int,
    "record": {
        "wins": int,
        "draws": int,
        "losses": int
    },
    "matches": [
        {
            "year": int,
            "opponent": str,
            "score": str,
            "result": str       # "W" | "D" | "L"
        }
    ]
}
```

**Data dependency:** `world_cup_df` — stage mapping columns from your Stage 4 preprocessing.

---

### `get_confederation_teams`

Returns all teams from a given confederation with basic WC qualification context.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `confederation` | `str` | Yes | One of `"UEFA"`, `"CONMEBOL"`, `"CONCACAF"`, `"CAF"`, `"AFC"`, `"OFC"` |

**Returns**

```python
{
    "confederation": str,
    "team_count": int,
    "teams": [str]
}
```

**Data dependency:** Confederation encoding from your Stage 7 preprocessing.

---

## Domain 3 — Tournament (`tournament_tools.py`)

Core dataset: `world_cup_df`.

---

### `get_tournament_results`

Returns full results for a specific World Cup edition.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `year` | `int` | Yes | WC year — e.g. `2022` |
| `stage_filter` | `str` | No | Filter to a specific stage — default `"all"` |

**Returns**

```python
{
    "found": bool,
    "year": int,
    "host": str,
    "winner": str,
    "runner_up": str,
    "third_place": str,
    "total_matches": int,
    "total_goals": int,
    "matches": [
        {
            "stage": str,
            "home_team": str,
            "away_team": str,
            "score": str,
            "winner": str
        }
    ]
}
```

**Data dependency:** `world_cup_df` — full stage and result columns.

---

### `get_tournament_top_scorers`

Returns the top scorers for a World Cup edition.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `year` | `int` | Yes | WC year |
| `top_n` | `int` | No | Number of scorers to return — default `10` |

**Returns**

```python
{
    "found": bool,
    "year": int,
    "top_scorers": [
        {
            "player": str,
            "team": str,
            "goals": int
        }
    ]
}
```

**Data dependency:** Player goals per tournament data — **verify this is present in your datasets before building.**

---

### `get_wc_group_results`

Returns standings and results for a specific group in a WC edition.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `year` | `int` | Yes | WC year |
| `group` | `str` | Yes | Group letter — e.g. `"A"`, `"B"` |

**Returns**

```python
{
    "found": bool,
    "year": int,
    "group": str,
    "standings": [
        {
            "position": int,
            "team": str,
            "played": int,
            "wins": int,
            "draws": int,
            "losses": int,
            "goals_for": int,
            "goals_against": int,
            "goal_difference": int,
            "points": int,
            "advanced": bool
        }
    ],
    "matches": [
        {
            "home_team": str,
            "away_team": str,
            "score": str
        }
    ]
}
```

**Data dependency:** Group stage mapping from `world_cup_df` — **verify group letter field is present.**

---

## Domain 4 — FIFA Rankings (`ranking_tools.py`)

Core dataset: `fifa_df`.

---

### `get_fifa_ranking`

Returns the FIFA ranking for a team at a specific point in time.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `team` | `str` | Yes | Team name |
| `date` | `str` | Yes | Date for ranking lookup in `YYYY-MM-DD` — will use closest preceding ranking date |

**Returns**

```python
{
    "found": bool,
    "team": str,
    "ranking_date": str,    # actual date of the ranking record used
    "rank": int,
    "total_points": float
}
```

**Data dependency:** `fifa_df` — your existing as-of join logic from Stage 6 preprocessing.

---

### `get_top_ranked_teams`

Returns the top N ranked teams at a point in time.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `date` | `str` | Yes | Date for snapshot |
| `top_n` | `int` | No | Number of teams — default `20` |
| `confederation` | `str` | No | Filter by confederation — default `None` (global) |

**Returns**

```python
{
    "ranking_date": str,
    "teams": [
        {
            "rank": int,
            "team": str,
            "confederation": str,
            "total_points": float
        }
    ]
}
```

**Data dependency:** `fifa_df` + confederation mapping.

---

### `get_ranking_trajectory`

Returns how a team's ranking has changed over time. Useful for ChatAgent narrative context.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `team` | `str` | Yes | Team name |
| `from_year` | `int` | No | Start year — default `2010` |
| `to_year` | `int` | No | End year — default current year |

**Returns**

```python
{
    "found": bool,
    "team": str,
    "snapshots": [
        {
            "date": str,
            "rank": int,
            "total_points": float
        }
    ],
    "peak_rank": int,
    "peak_rank_date": str,
    "current_rank": int
}
```

**Data dependency:** `fifa_df` — multiple temporal records per team.

---

## Domain 5 — Player (`player_tools.py`)

Core dataset: Player transfer values CSV.

> **Note:** This is the thinnest domain. Verify column coverage in your player values CSV before committing to all tools below. Tools marked ⚠️ depend on data that may not be present.

---

### `get_player_value_history`

Returns a player's market value over time.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `player` | `str` | Yes | Player name |

**Returns**

```python
{
    "found": bool,
    "player": str,
    "nationality": str,
    "values": [
        {
            "date": str,
            "market_value_eur": float
        }
    ],
    "peak_value_eur": float,
    "peak_value_date": str,
    "current_value_eur": float
}
```

**Data dependency:** Player transfer values CSV — date, value columns.

---

### `get_team_squad_value` ⚠️

Returns aggregate market value of a national team squad.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `team` | `str` | Yes | Team name |
| `date` | `str` | No | Point-in-time snapshot — default latest |

**Returns**

```python
{
    "found": bool,
    "team": str,
    "date": str,
    "total_squad_value_eur": float,
    "average_player_value_eur": float,
    "player_count": int
}
```

**Data dependency:** Requires `nationality` or `team` field on player records — verify this exists.

---

## Shared Utility — `utils.py`

Not a tool. Internal utility used by all domains.

### `normalise_team_name(name: str) -> str`

Maps any known variant to the canonical FIFA name before querying.

- Wraps your existing 25 FIFA variant mapping + 21 non-FIFA entity list from Stage 2
- Returns the canonical name if found, raises a clean `ValueError` with suggestions if not
- All tool functions call this on every team name input before touching a DataFrame

---

## Agent Tool Assignment

| Agent | Tools |
|---|---|
| **PreMatchAgent** | `get_h2h_record`, `get_team_recent_form`, `get_team_wc_history`, `get_team_wc_stage_record`, `get_fifa_ranking`, `get_top_ranked_teams` |
| **LiveAgent** | None — relies entirely on search + scraper tools |
| **PostMatchAgent** | `get_tournament_results`, `get_wc_group_results`, `get_team_wc_history`, `get_match_result` |
| **ChatAgent** | All tools |

---

## Build Priority

| Priority | Tool | Rationale |
|---|---|---|
| P0 | `get_h2h_record` | Core PreMatch feature |
| P0 | `get_team_recent_form` | Core PreMatch feature |
| P0 | `get_fifa_ranking` | Already built as-of join logic in pipeline |
| P0 | `get_team_wc_history` | Core PostMatch + Chat feature |
| P1 | `get_tournament_results` | PostMatch narrative |
| P1 | `get_wc_group_results` | PostMatch + Chat |
| P1 | `get_top_ranked_teams` | Chat context |
| P2 | `get_team_wc_stage_record` | Deep Chat Q&A |
| P2 | `get_ranking_trajectory` | Chat narrative |
| P2 | `get_match_result` | Specific lookup |
| P3 | `get_player_value_history` | Data coverage dependent |
| P3 | `get_team_squad_value` | Data coverage dependent |
| P3 | `get_tournament_top_scorers` | Data coverage dependent |
| P3 | `get_confederation_teams` | Low query frequency |
