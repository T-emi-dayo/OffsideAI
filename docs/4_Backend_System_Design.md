# Backend System Design
## Offside AI — 2026 FIFA World Cup Intelligence Companion
**Version:** 1.0  
**Date:** April 2026

---

## 1. Overview

The backend consists of five components. The FastAPI Gateway is the only externally-facing service. All other components are internal, consumed by the gateway or by each other.

| Component | Type | Externally Facing |
|---|---|---|
| FastAPI Gateway | REST API | Yes |
| Data Ingestion Service | Background + ETL | No |
| RAG Service | Vector store + interface | No |
| ML Prediction Service | Model artifact + wrapper | No |
| LangGraph Agent Service | Graph invocation layer | No |

---

## 2. FastAPI Gateway

### 2.1 Responsibility
Single HTTP entry point for the React frontend. Routes requests to the appropriate internal component. No business logic.

### 2.2 Endpoints

#### Fixtures
```
GET /fixtures
  Returns: List of all World Cup fixtures with match_id, teams, date, status
  Source: Data Ingestion Service (semi-static, refreshed daily)

GET /fixtures/today
  Returns: Fixtures scheduled for today

GET /fixtures/live
  Returns: Currently live fixtures
```

#### Match Data
```
GET /match/{match_id}
  Returns: Match metadata + current state (pre | live | post), current score, event log
  Source: Redis cache (live) or persistent match store (completed)
```

#### Agent Endpoints
```
GET /match/{match_id}/preview
  Invokes: PreMatchAgent graph
  Returns: Full pre-match report JSON
  Cache: Store output in persistent match store after first generation

GET /match/{match_id}/narrative
  Invokes: LiveAgent graph
  Requires: match_state == "live"
  Returns: On-demand narrative + key moments

GET /match/{match_id}/report
  Invokes: PostMatchAgent graph
  Requires: match_state == "post"
  Returns: Full post-match report JSON

POST /match/{match_id}/chat
  Invokes: ChatAgent graph
  Body: {user_message: str, conversation_history: List, scope: "fixture" | "global"}
  Returns: {response: str, sources_used: List[str]}

GET /match/{match_id}/prediction
  Invokes: PredictionAgent tool (via PreMatchAgent or direct wrapper)
  Returns: Prediction probabilities + reasoning
```

### 2.3 Response Format (Standard)
```python
{
    "status": "success" | "error",
    "data": dict | None,
    "error_message": str | None,
    "match_id": str,
    "generated_at": str  # ISO timestamp
}
```

### 2.4 Error Handling
- Agent invocation failures return a structured error response — frontend never sees a raw 500
- Live match requests against a non-live fixture return a 400 with a clear message
- All agent timeouts are caught and surfaced as error responses

---

## 3. Data Ingestion Service

### 3.1 Sub-Components

#### A. Live Poller
Polls API-Football every 60–90 seconds during active matches.

**Responsibilities:**
- Detect active matches from the fixture schedule
- Fetch match events (goals, cards, substitutions, lineups)
- Normalise events into the internal `MatchEvent` schema
- Write to Redis cache (key: `match:{match_id}:events`)
- Write to persistent match store (append-only during live match)

**Polling Schedule:**
- Inactive periods: no polling
- Pre-match window (60 min before kickoff): poll for lineups
- Active match: poll every 60–90 seconds
- Post-match: final poll for full event log, then stop

**Internal Event Schema:**
```python
class MatchEvent(TypedDict):
    match_id: str
    minute: int
    event_type: str        # "goal" | "yellow_card" | "red_card" | "substitution" | "var"
    team: str
    player: str
    detail: str | None     # e.g. assist, substituted player
    timestamp: str         # ISO
```

#### B. Historical Loader
One-time ETL pipeline. Runs offline before system launch.

**Input Sources:**
- Kaggle World Cup dataset (1930–2022): match results, goalscorers, team stats
- football-data.org: international match results, FIFA rankings

**Processing Steps:**
1. Load raw CSVs
2. Normalise team names (handle name variants across datasets)
3. Engineer features for ML training
4. Generate text summaries for RAG ingestion
5. Output to two destinations:
   - RAG ingestion pipeline (text summaries + metadata)
   - ML feature store (structured dataframes saved as Parquet)

### 3.2 Persistent Match Store
Stores the full lifecycle data for each fixture. Used by PostMatchAgent.

**Structure (per match):**
```
match_store/
  {match_id}/
    pre_match_report.json    # PreMatchAgent output, written at first preview generation
    events.jsonl             # Append-only event log written by live poller
    post_match_report.json   # PostMatchAgent output, written after full time
```

**Storage:** Local filesystem on Render (persistent disk) or object storage. Build-time decision.

### 3.3 Fallback Strategy
API-Football is the primary live data source. Fallback sources are evaluated at build time. The Data Ingestion Service should abstract the data source behind an interface so swapping providers does not require agent-level changes.

---

## 4. RAG Service

### 4.1 Responsibility
Owns the ChromaDB vector store. Provides a retrieval interface consumed by agents as a tool.

### 4.2 Ingestion Pipeline (Offline)

```
Historical Loader output (text summaries + metadata)
   ↓
Text chunking (by document type)
   ↓
Embedding generation (Gemini text-embedding or sentence-transformers)
   ↓
ChromaDB upsert with metadata filters
```

**Chunking Strategy by Document Type:**

| Document Type | Chunk Strategy |
|---|---|
| Match summaries | One chunk per match |
| Team profiles | One chunk per section (history, style, records) |
| Head-to-head records | One chunk per country pair |
| Player profiles | One chunk per player |
| Tournament records | One chunk per year/tournament |

### 4.3 ChromaDB Collections

| Collection Name | Metadata Fields | Indexed |
|---|---|---|
| `team_profiles` | `team_name`, `confederation` | Yes |
| `match_summaries` | `home_team`, `away_team`, `year`, `tournament` | Yes |
| `head_to_head` | `team_a`, `team_b` | Yes |
| `player_profiles` | `player_name`, `nationality` | Yes |
| `tournament_records` | `year`, `host_country` | Yes |

### 4.4 Retrieval Interface

```python
def retrieve(
    query: str,
    collection: str,
    filters: dict = None,
    top_k: int = 5
) -> List[RetrievedChunk]:
    """
    Semantic search over specified ChromaDB collection.
    filters: ChromaDB metadata filter dict
    Returns ranked chunks with content and metadata.
    """

class RetrievedChunk(TypedDict):
    content: str
    metadata: dict
    score: float
```

### 4.5 Notes
- ChromaDB persistence on Render requires a persistent disk attachment — addressed at deployment
- Embedding model choice (Gemini vs. sentence-transformers) is a build-time decision based on cost and latency

---

## 5. ML Prediction Service

### 5.1 Responsibility
Provide match outcome predictions. Self-contained — trained offline, loaded as an artifact at runtime.

### 5.2 Models

**Model 1: Poisson Regression (Primary)**
- Predicts expected goals for each team independently
- Standard approach for football prediction — interpretable and explainable
- Output: `home_goals_expected`, `away_goals_expected`

**Model 2: XGBoost Classifier (Secondary)**
- Classifies match outcome as home win / draw / away win
- Trained on the same feature set
- Output: `home_win_prob`, `draw_prob`, `away_win_prob`

Both models are trained offline and saved as artifacts. PredictionAgent loads them at runtime.

### 5.3 Feature Set

| Feature | Description | Source |
|---|---|---|
| `home_team_avg_goals_scored` | Last 10 matches average | Historical data |
| `home_team_avg_goals_conceded` | Last 10 matches average | Historical data |
| `away_team_avg_goals_scored` | Last 10 matches average | Historical data |
| `away_team_avg_goals_conceded` | Last 10 matches average | Historical data |
| `h2h_home_wins` | Historical head-to-head wins | Historical data |
| `h2h_draws` | Historical head-to-head draws | Historical data |
| `h2h_away_wins` | Historical head-to-head away wins | Historical data |
| `home_fifa_ranking` | Current FIFA ranking | API-Football |
| `away_fifa_ranking` | Current FIFA ranking | API-Football |
| `tournament_stage` | Encoded: Group / R16 / QF / SF / F | Fixture metadata |
| `neutral_venue` | Boolean — all World Cup matches are neutral | Static: True |

### 5.4 Training Pipeline (Offline)

```
ML Feature Store (Parquet)
   ↓
Feature engineering script
   ↓
Train-test split (temporal — train on pre-2018, test on 2018+2022)
   ↓
Train Poisson model (statsmodels)
   ↓
Train XGBoost classifier
   ↓
Evaluate on test set
   ↓
Save artifacts:
  models/poisson_model.pkl
  models/xgboost_model.pkl
  models/feature_scaler.pkl
```

### 5.5 Prediction Interface (Runtime)

```python
def predict_match(
    home_team: str,
    away_team: str,
    features: dict
) -> PredictionOutput:
    ...

class PredictionOutput(TypedDict):
    home_goals_expected: float
    away_goals_expected: float
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
```

The PredictionAgent tool calls this function, receives the output, and passes it to an LLM call that generates the `reasoning` paragraph.

---

## 6. Redis Cache

**Purpose:** Buffer live match events during active matches. Consumed by LiveAgent and ChatAgent (for live context).

**Key Schema:**
```
match:{match_id}:events        → List of MatchEvent JSON (appended by live poller)
match:{match_id}:score         → {home: int, away: int}
match:{match_id}:status        → "pre" | "live" | "post"
fixtures:today                 → List of fixture metadata (refreshed daily)
```

**TTL Policy:**
- Match event keys: 48 hours after match end
- Fixture lists: 24 hours

---

## 7. Project Structure

```
offside-ai/
├── api/
│   ├── main.py                 # FastAPI app entry point
│   ├── routers/
│   │   ├── fixtures.py
│   │   ├── match.py
│   │   └── chat.py
│   └── schemas.py              # Pydantic request/response models
├── agents/
│   ├── pre_match_agent.py
│   ├── live_agent.py
│   ├── post_match_agent.py
│   ├── chat_agent.py
│   └── tools/
│       ├── rag_tool.py
│       └── prediction_tool.py
├── ingestion/
│   ├── live_poller.py
│   └── historical_loader.py
├── rag/
│   ├── ingest.py
│   └── retriever.py
├── ml/
│   ├── train.py
│   ├── features.py
│   └── predict.py
├── models/                     # Saved ML artifacts
│   ├── poisson_model.pkl
│   ├── xgboost_model.pkl
│   └── feature_scaler.pkl
├── match_store/                # Persistent per-match data
├── state/                      # Redis config + helpers
├── config.py
└── requirements.txt
```
