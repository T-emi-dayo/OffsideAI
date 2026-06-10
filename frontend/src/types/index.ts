export type MatchState = "pre" | "live" | "post";

export interface ResponseMeta {
  timestamp: string;
  duration_ms: number;
}

export interface DataResponse<T> {
  data: T;
  meta: ResponseMeta;
}

export interface AgentResponse<T> {
  success: boolean;
  agent: "prematch" | "live" | "postmatch" | "chat" | "prediction";
  match_id: string;
  data: T;
  errors: string[];
  meta: ResponseMeta;
}

export interface FixtureTeam {
  name: string;
}

export interface FixtureScore {
  home: number | null;
  away: number | null;
}

export interface FixtureItem {
  id: number;
  stage: string;
  group: string | null;
  utc_date: string;
  match_state: MatchState;
  home_team: FixtureTeam;
  away_team: FixtureTeam;
  score: FixtureScore;
}

export interface FixtureListData {
  count: number;
  fixtures: FixtureItem[];
}

export interface MatchMetadata {
  match_id: string;
  home_team: string;
  away_team: string;
  match_date: string;
  stage: string;
  group: string | null;
  match_state: MatchState;
  score: FixtureScore;
}

export interface MatchPrediction {
  p_home: number;
  p_draw: number;
  p_away: number;
  lambda_home: number;
  lambda_away: number;
}

export interface PreMatchData {
  prediction: MatchPrediction | null;
  match_overview: string | null;
  team_analysis: string | null;
  head_to_head: string | null;
  prediction_reasoning: string | null;
  verdict: string | null;
}

export interface LiveData {
  current_score: { home: number; away: number };
  key_moments: string[];
  narrative: string;
}

export interface PostMatchData {
  key_moments: string[];
  player_highlights: string[];
  match_summary: string | null;
  tactical_analysis: string | null;
  full_report: string | null;
}

export interface PredictionData {
  home_team: string;
  away_team: string;
  p_home: number | null;
  p_draw: number | null;
  p_away: number | null;
  lambda_home: number | null;
  lambda_away: number | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatData {
  reply: string;
  sources_used: string[];
  history: ChatMessage[];
}

export interface ChatRequest {
  home_team: string;
  away_team: string;
  match_state: MatchState;
  message: string;
  history: ChatMessage[];
  live_context?: Record<string, unknown> | null;
}
