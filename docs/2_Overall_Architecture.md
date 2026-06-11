# Overall System Architecture
## Offside AI — 2026 FIFA World Cup Intelligence Companion
**Version:** 1.0  
**Date:** April 2026

---

## 1. Architecture Overview

Offside AI is a five-layer system. Each layer has a single, well-defined responsibility and communicates with adjacent layers through explicit interfaces.

```
┌─────────────────────────────────────────────┐
│              FRONTEND (React)               │
│        Dashboard + Chat — Desktop First     │
└────────────────────┬────────────────────────┘
                     │ REST (HTTP)
┌────────────────────▼────────────────────────┐
│           FASTAPI GATEWAY                   │
│     Single entry point for all requests     │
└──┬──────────────┬──────────────┬────────────┘
   │              │              │
┌──▼──────┐ ┌────▼──────┐ ┌────▼────────────┐
│LangGraph│ │    ML     │ │  Data Ingestion  │
│ Agents  │ │Prediction │ │    Service       │
│ Service │ │  Service  │ │                  │
└──┬──────┘ └───────────┘ └─────────────────┘
   │
┌──▼──────┐
│   RAG   │
│ Service │
│(ChromaDB)│
└─────────┘
```

---

## 2. Layer Descriptions

### Layer 1 — Frontend (React)
The user-facing application. Desktop-first. Three primary surfaces:
- **Fixture Hub** — landing page, match discovery
- **Match View** — adaptive single view per fixture (PREVIEW / LIVE / FULL TIME)
- **Chat Panel** — collapsible right panel, persistent across all match states

Communicates with the FastAPI Gateway exclusively via REST HTTP calls.

### Layer 2 — FastAPI Gateway
The single entry point for the frontend. Owns all HTTP routing. Responsible for:
- Serving fixture list and match data from the Data Ingestion Service
- Invoking the appropriate LangGraph agent graph based on request type
- Routing chat messages to the ChatAgent
- No business logic — pure routing and response marshalling

### Layer 3 — LangGraph Agent Service
A set of independent LangGraph graphs, one per agent. Invoked by the FastAPI Gateway. The gateway performs all routing — there is no supervisor agent. Each graph is stateless at the graph level; state concerns are handled at the agent level during build.

Agents: PreMatchAgent, LiveAgent, PostMatchAgent, ChatAgent, PredictionAgent (tool within PreMatchAgent).

### Layer 4 — Supporting Services
Three independent services consumed by the agent layer:

| Service | Responsibility |
|---|---|
| ML Prediction Service | Offline-trained model artifact, loaded at runtime. Produces goal expectancy + win/draw/loss probabilities. |
| Data Ingestion Service | Live match event polling (API-Football) + historical data ETL. Writes to Redis cache and persistent match event store. |
| RAG Service | ChromaDB vector store. Ingests historical content. Exposes retrieval interface consumed by agents as a tool. |

### Layer 5 — Data Sources
| Source | Type | Content |
|---|---|---|
| API-Football | Live / Real-time | Match events, lineups, scores, fixtures |
| football-data.org | Historical | International match results |
| Kaggle World Cup datasets | Historical | World Cup records 1930–2022 |
| Redis | Cache | Live match event buffer during active matches |
| Persistent Match Store | Storage | Accumulated pre-match + live data per fixture, consumed by PostMatchAgent |

---

## 3. Request Routing

The FastAPI Gateway maps each endpoint to a specific agent invocation:

| Endpoint | Method | Agent Invoked |
|---|---|---|
| `/fixtures` | GET | No agent — Data Ingestion Service direct |
| `/match/{id}/preview` | GET | PreMatchAgent graph |
| `/match/{id}/narrative` | GET | LiveAgent graph |
| `/match/{id}/report` | GET | PostMatchAgent graph |
| `/match/{id}/chat` | POST | ChatAgent graph |
| `/match/{id}/prediction` | GET | PredictionAgent (via PreMatchAgent or direct) |

---

## 4. Data Flow — Pre-Match Request

```
Frontend
  → GET /match/{id}/preview
  → FastAPI Gateway
  → Invokes PreMatchAgent graph with {match_id, match_state: "pre"}
  → PreMatchAgent queries RAG Service (head-to-head, team profiles)
  → PreMatchAgent calls PredictionAgent tool
      → PredictionAgent calls ML Prediction Service
      → Returns goal expectancy + probabilities
  → PreMatchAgent assembles full preview report
  → Returns structured response to Gateway
  → Gateway returns JSON to Frontend
  → Frontend renders PREVIEW match view
```

---

## 5. Data Flow — Live Match Request

```
Frontend
  → GET /match/{id}/narrative (on user trigger)
  → FastAPI Gateway
  → Invokes LiveAgent graph with {match_id, match_state: "live"}
  → LiveAgent reads cached events from Redis (populated by live poller)
  → LiveAgent generates narrative from accumulated events
  → Returns narrative text to Gateway
  → Gateway returns JSON to Frontend
  → Frontend renders narrative panel
```

---

## 6. Data Flow — Historical Ingestion (Offline)

```
Kaggle + football-data.org datasets
  → Historical Loader (one-time ETL)
  → Cleans + normalises data
  → Two outputs:
      1. RAG Service — embeds and stores in ChromaDB
      2. ML Feature Store — structured data for model training
  → ML model trained offline → artifact saved
  → Artifact loaded by ML Prediction Service at runtime
```

---

## 7. Technology Stack

| Concern | Technology |
|---|---|
| Frontend | React |
| Backend gateway | FastAPI |
| Agent orchestration | LangGraph |
| LLM | Gemini via `langchain_google_genai` |
| Vector store | ChromaDB |
| ML models | scikit-learn (Poisson), XGBoost |
| Live data | API-Football |
| Historical data | football-data.org, Kaggle |
| Cache | Redis |
| Frontend deployment | Vercel |
| Backend deployment | Render |

---

## 8. Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| No supervisor/orchestrator agent | Gateway does routing | Routing is fully deterministic — no LLM reasoning needed to decide which agent to call |
| WebSocket dropped from v1 | REST only | Live narrative is on-demand in v1; WebSocket adds infrastructure cost with no v1 benefit |
| PredictionAgent is a tool, not a service | Direct function call within PreMatchAgent | No HTTP overhead needed; ML artifact loaded in-process |
| Each agent is an independent graph | No monolithic graph | Cleaner separation of concerns, easier to debug and extend independently |
