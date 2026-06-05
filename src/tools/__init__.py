from src.tools.match_tools import get_h2h_record, get_match_result, get_team_recent_form
from src.tools.player_tools import get_player_value_history, get_team_squad_value
from src.tools.ranking_tools import (
    get_fifa_ranking,
    get_ranking_trajectory,
    get_top_ranked_teams,
)
from src.tools.team_tools import (
    get_confederation_teams,
    get_team_wc_history,
    get_team_wc_stage_record,
)
from src.tools.tournament_tools import (
    get_tournament_results,
    get_tournament_top_scorers,
    get_wc_group_results,
)

PRE_MATCH_TOOLS = [
    get_h2h_record,
    get_team_recent_form,
    get_team_wc_history,
    get_team_wc_stage_record,
    get_fifa_ranking,
    get_top_ranked_teams,
]

POST_MATCH_TOOLS = [
    get_tournament_results,
    get_wc_group_results,
    get_team_wc_history,
    get_match_result,
]

CHAT_TOOLS = [
    get_h2h_record,
    get_team_recent_form,
    get_match_result,
    get_team_wc_history,
    get_team_wc_stage_record,
    get_confederation_teams,
    get_tournament_results,
    get_tournament_top_scorers,
    get_wc_group_results,
    get_fifa_ranking,
    get_top_ranked_teams,
    get_ranking_trajectory,
    get_player_value_history,
    get_team_squad_value,
]

__all__ = [
    "get_h2h_record",
    "get_team_recent_form",
    "get_match_result",
    "get_team_wc_history",
    "get_team_wc_stage_record",
    "get_confederation_teams",
    "get_tournament_results",
    "get_tournament_top_scorers",
    "get_wc_group_results",
    "get_fifa_ranking",
    "get_top_ranked_teams",
    "get_ranking_trajectory",
    "get_player_value_history",
    "get_team_squad_value",
    "PRE_MATCH_TOOLS",
    "POST_MATCH_TOOLS",
    "CHAT_TOOLS",
]
