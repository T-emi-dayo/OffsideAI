# AI Agents Architecture
## Offside AI — 2026 FIFA World Cup Intelligence Companion
**Version:** 1.0  
**Date:** April 2026

---

## 1. Overview

Offside AI uses four independent LangGraph agent graphs plus one agent used as an internal tool. There is no supervisor or orchestrator — the FastAPI Gateway performs all routing deterministically based on request context.

Each agent graph is self-contained with its own state schema, tools, and node structure.

---

## 2. Agent Inventory

| Agent | Type | Triggered By | Primary Responsibility |
|---|---|---|---|
| PreMatchAgent | LangGraph graph | Gateway on `GET /match/{id}/preview` | Generate pre-match intelligence report |
| LiveAgent | LangGraph graph | Gateway on `GET /match/{id}/narrative` | Generate on-demand match narrative from live events |
| PostMatchAgent | LangGraph graph | Gateway on `GET /match/{id}/report` | Generate full post-match report |
| ChatAgent | LangGraph graph | Gateway on `POST /match/{id}/chat` | Handle conversational Q&A |
| PredictionAgent | Tool (internal to PreMatchAgent) | Called within PreMatchAgent graph | Wrap ML model, return natural language prediction |

---

## 3. Agent Designs

---

### 3.1 PreMatchAgent

**Purpose:** Produce a complete pre-match intelligence report for a given fixture.

**Input:**
```python
{
    "match_id": str,
    "home_team": str,
    "away_team": str,
    "match_date": str,
    "stage": str  # e.g. "Group Stage", "Quarter Final"
}
```

**Output:**
```python
{
    "team_previews": {
        "home": str,
        "away": str
    },
    "head_to_head_summary": str,
    "form_analysis": {
        "home": str,
        "away": str
    },
    "prediction": {
        "home_goals_expected": float,
        "away_goals_expected": float,
        "home_win_prob": float,
        "draw_prob": float,
        "away_win_prob": float,
        "reasoning": str
    },
    "report_narrative": str  # Full synthesised preview
}
```

**Graph Structure:**
```
[START]
   ↓
[retrieve_context_node]     # Calls RAG tool: fetches head-to-head, team profiles, recent form
   ↓
[get_prediction_node]       # Calls PredictionAgent tool with team context
   ↓
[generate_report_node]      # LLM synthesises all context into full preview report
   ↓
[END]
```

**Tools:**
- `rag_retrieval_tool(query: str, context: dict) → List[str]` — queries ChromaDB, returns ranked chunks
- `prediction_tool(home_team: str, away_team: str, context: dict) → dict` — wraps ML Prediction Service

**Notes:**
- RAG queries are structured per component: one query for head-to-head, one for home team profile, one for away team profile, one for recent form
- PredictionAgent tool is a direct function call — no HTTP boundary

---

### 3.2 LiveAgent

**Purpose:** Generate an on-demand narrative summary of a live match from accumulated events.

**Input:**
```python
{
    "match_id": str,
    "home_team": str,
    "away_team": str,
    "events": List[dict]  # Fetched from Redis cache by Gateway before invocation
    # Each event: {minute: int, type: str, team: str, player: str, detail: str}
}
```

**Output:**
```python
{
    "narrative": str,       # Story-so-far prose narrative
    "key_moments": List[str],
    "current_score": {
        "home": int,
        "away": int
    }
}
```

**Graph Structure:**
```
[START]
   ↓
[parse_events_node]         # Structures raw event list, identifies key moments
   ↓
[generate_narrative_node]   # LLM generates story-so-far narrative
   ↓
[END]
```

**Tools:** None — all input data is passed via graph state. No RAG access in v1 (live context is sufficient).

**Notes:**
- State persistence across multiple on-demand invocations is a build-time implementation concern
- Events are fetched from Redis by the Gateway before graph invocation — the agent receives a clean event list, not a cache reference
- v2 upgrade: auto-pushed narrative via WebSocket, incremental event processing

---

### 3.3 PostMatchAgent

**Purpose:** Generate a complete post-match report from accumulated match data.

**Input:**
```python
{
    "match_id": str,
    "home_team": str,
    "away_team": str,
    "final_score": {"home": int, "away": int},
    "pre_match_data": dict,     # Stored pre-match report output
    "match_events": List[dict]  # Full event log from persistent match store
}
```

**Output:**
```python
{
    "match_summary": str,
    "key_moments": List[str],
    "player_highlights": List[str],
    "tactical_observations": str,
    "full_report": str          # Synthesised narrative report
}
```

**Graph Structure:**
```
[START]
   ↓
[load_match_data_node]      # Reads from persistent match store (pre-match + live events)
   ↓
[analyse_match_node]        # LLM analyses events, identifies key moments + player performances
   ↓
[generate_report_node]      # LLM synthesises full post-match report narrative
   ↓
[END]
```

**Tools:**
- `rag_retrieval_tool` — optional contextual enrichment (e.g. historical comparison)

**Notes:**
- Data source is the persistent match event store, not Redis (Redis is volatile; the persistent store is written during the match)
- Pre-match report is stored at the time it is generated and passed into this agent at invocation

---

### 3.4 ChatAgent

**Purpose:** Handle conversational Q&A grounded in live match context and historical RAG data.

**Input:**
```python
{
    "match_id": str,
    "match_state": str,         # "pre" | "live" | "post"
    "user_message": str,
    "conversation_history": List[dict],  # Managed by frontend or server-side store
    "live_context": dict | None  # Current match events if match_state is "live"
}
```

**Output:**
```python
{
    "response": str,
    "sources_used": List[str]   # RAG chunks referenced (for transparency)
}
```

**Graph Structure:**
```
[START]
   ↓
[classify_query_node]       # Determines if query needs RAG, live context, or both
   ↓
[retrieve_context_node]     # Conditional: calls RAG tool if historical context needed
   ↓
[generate_response_node]    # LLM generates grounded conversational response
   ↓
[END]
```

**Tools:**
- `rag_retrieval_tool(query: str, context: dict) → List[str]`
- `get_live_context_tool(match_id: str) → dict` — fetches current match state from Redis if in live mode

**Scope Modes:**
- **Fixture-scoped (default):** Chat context anchored to the currently selected match
- **Global toggle:** User can enable global mode — queries span the full tournament

**Notes:**
- Conversation history strategy (frontend-managed vs. server-side checkpointer) is a build-time decision
- Global mode uses broader RAG queries with no match_id filter

---

### 3.5 PredictionAgent (Tool)

**Purpose:** Wrap the ML Prediction Service and return natural language reasoning over model output.

**Not a standalone graph.** Implemented as a LangChain tool called within PreMatchAgent's `get_prediction_node`.

**Tool Signature:**
```python
def prediction_tool(home_team: str, away_team: str, context: dict) -> dict:
    """
    Calls the ML Prediction Service (in-process function call).
    Receives raw model output.
    Uses LLM to generate natural language reasoning.
    Returns structured prediction + reasoning string.
    """
```

**Internal Flow:**
```
prediction_tool called
   ↓
Load ML artifact (Poisson model + XGBoost)
   ↓
Engineer features from team context
   ↓
Run model → {home_goals_exp, away_goals_exp, home_win_prob, draw_prob, away_win_prob}
   ↓
LLM call → generates reasoning paragraph explaining the prediction
   ↓
Return combined output to PreMatchAgent
```

---

## 4. Shared Tool — RAG Retrieval

All agents that access historical data use the same underlying RAG retrieval tool.

```python
def rag_retrieval_tool(query: str, filters: dict = None) -> List[str]:
    """
    Queries ChromaDB vector store.
    filters: optional metadata filters (e.g. team_name, match_year)
    Returns: list of ranked text chunks
    """
```

**ChromaDB Collections:**
| Collection | Content |
|---|---|
| `team_profiles` | Team history, playing style, notable players |
| `match_summaries` | Historical match summaries (World Cup + international) |
| `head_to_head` | Head-to-head records between country pairs |
| `player_profiles` | Key player bios and historical performance |
| `tournament_records` | World Cup records, statistics, notable moments |

---

## 5. Agent State Schema (LangGraph)

Each agent defines its own TypedDict state. Shared fields across agents:

```python
from typing import TypedDict, List, Optional, Annotated
import operator

class BaseMatchState(TypedDict):
    match_id: str
    home_team: str
    away_team: str
    match_state: str            # "pre" | "live" | "post"
    errors: Annotated[List[str], operator.add]
```

Agent-specific states extend BaseMatchState with their own fields.

---

## 6. LLM Configuration

| Parameter | Value |
|---|---|
| Provider | `langchain_google_genai` |
| Model | `gemini-1.5-pro` (or latest available) |
| All agent LLM calls | Must go through `langchain_google_genai` (not native `google.genai`) |
| Temperature | 0.3 for structured report generation; 0.7 for narrative and chat |

---

## 7. Build Sequencing (Recommended)

1. RAG ingestion pipeline + ChromaDB setup
2. ML model training pipeline + artifact
3. PredictionAgent tool
4. PreMatchAgent (first full agent, most complex)
5. ChatAgent
6. LiveAgent
7. PostMatchAgent
