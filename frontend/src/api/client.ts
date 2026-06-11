import type {
  AgentResponse,
  ChatData,
  ChatRequest,
  DataResponse,
  FixtureListData,
  LiveData,
  MatchMetadata,
  PostMatchData,
  PreMatchData,
  PredictionData,
} from "../types";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getFixtures:      () => get<DataResponse<FixtureListData>>("/api/fixtures"),
  getFixturesToday: () => get<DataResponse<FixtureListData>>("/api/fixtures/today"),
  getFixturesLive:  () => get<DataResponse<FixtureListData>>("/api/fixtures/live"),

  getMatch:      (id: number) => get<DataResponse<MatchMetadata>>(`/api/match/${id}`),
  getPreview:    (id: number) => get<AgentResponse<PreMatchData>>(`/api/match/${id}/preview`),
  getNarrative:  (id: number) => get<AgentResponse<LiveData>>(`/api/match/${id}/narrative`),
  getReport:     (id: number) => get<AgentResponse<PostMatchData>>(`/api/match/${id}/report`),
  getPrediction: (id: number) => get<AgentResponse<PredictionData>>(`/api/match/${id}/prediction`),
  postChat:      (id: number, body: ChatRequest) =>
                   post<AgentResponse<ChatData>>(`/api/match/${id}/chat`, body),
};
