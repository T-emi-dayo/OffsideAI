# Product Requirements Document
## Offside AI — 2026 FIFA World Cup Intelligence Companion
**Version:** 1.0  
**Status:** Draft  
**Author:** Temi  
**Date:** April 2026

---

## 1. Overview

### 1.1 Product Summary
Offside AI is a hybrid dashboard and chat application that delivers a unified AI intelligence layer across the 2026 FIFA World Cup. It serves casual football fans with pre-match previews, live match narratives, post-match reports, and a conversational interface grounded in live and historical data.

### 1.2 Project Purpose
This is a portfolio project designed to demonstrate advanced AI/ML engineering capabilities — specifically multi-agent orchestration, RAG over structured and unstructured data, ML prediction integrated into an LLM pipeline, and a deployed full-stack application. The World Cup window (June–July 2026) provides a high-traffic search context that maximises the project's public visibility.

### 1.3 Non-Goals
- This is not a startup or commercial product
- No user authentication or accounts in v1
- No real-time betting signals
- No fantasy football integration
- No deep tactical breakdowns (analyst-level content)
- No mobile-first layout in v1

---

## 2. Target Audience

**Primary:** Casual football fans who want AI-powered match insights without needing deep tactical knowledge.

**Needs:**
- Quick pre-match context — who's playing, who's in form, who's likely to win
- During a match — a narrative that contextualises key events
- After a match — a concise, intelligent match summary
- An always-available chat to ask anything about the tournament

---

## 3. Core Value Proposition

What Offside AI delivers that Google cannot:
- **Synthesised intelligence** — not raw stats, but contextualised analysis drawn from multi-year historical data and live match events
- **Unified surface** — pre-match, live, and post-match in one adaptive view per fixture
- **Conversational access** — ask anything about any World Cup match or team, grounded in real data
- **AI-generated narratives** — not just event logs but story-driven match coverage

---

## 4. Product Scope — V1

### 4.1 Features In Scope

| Feature | Description |
|---|---|
| Fixture Hub | Landing page showing all World Cup matches grouped by Today / Upcoming / Completed |
| Match View — PREVIEW | Pre-match report: team previews, head-to-head context, form analysis, predicted outcome with reasoning |
| Match View — LIVE | Score + live events feed, on-demand AI narrative, persistent chat |
| Match View — FULL TIME | Auto-generated post-match report covering key moments, player highlights, tactical observations |
| Chat Interface | Fixture-scoped conversational Q&A with global toggle, grounded on RAG + live data |
| Prediction Panel | Compact pre-match widget showing win/draw/loss probabilities with LLM-generated reasoning |

### 4.2 Features Deferred to V2

| Feature | Reason Deferred |
|---|---|
| Auto-pushed live narrative | Token cost management during development |
| Live win probability updates | Requires WebSocket infrastructure not needed in v1 |
| News view | Explicit scope decision |
| Mobile layout | Desktop-first for v1 |
| Observability / LangSmith | Post-launch concern |

### 4.3 Data Coverage
- All 2026 FIFA World Cup matches (group stage through final)
- Historical data: multi-year international and World Cup match records (1930–2022) for RAG and ML model training

---

## 5. User Flows

### 5.1 Pre-Match Flow
1. User lands on Fixture Hub
2. Selects an upcoming fixture
3. Match view loads in PREVIEW state
4. User sees: team previews, head-to-head history, form analysis, prediction widget
5. User can open chat and ask questions about the match

### 5.2 Live Match Flow
1. User selects a live fixture from Fixture Hub
2. Match view loads in LIVE state
3. User sees: live score, event timeline
4. User clicks "Generate Narrative" → LiveAgent produces a story-so-far summary
5. User can chat about ongoing match events

### 5.3 Post-Match Flow
1. User selects a completed fixture
2. Match view loads in FULL TIME state
3. PostMatchAgent report is displayed — key moments, player highlights, observations
4. User can chat about the match

---

## 6. Success Metrics (Portfolio)

| Metric | Target |
|---|---|
| System is live during World Cup | June 11, 2026 |
| All match states functional | PREVIEW, LIVE, FULL TIME all working |
| RAG retrieves accurate historical context | Qualitative validation |
| ML model produces reasonable predictions | Validated against known historical outcomes |
| Public demo accessible | Deployed on Render + Vercel |

---

## 7. Constraints

| Constraint | Detail |
|---|---|
| LLM Provider | Gemini (`langchain_google_genai`) |
| Orchestration | LangGraph |
| Live Data | API-Football (primary), fallback sources TBD |
| Historical Data | football-data.org + Kaggle World Cup datasets |
| Vector Store | ChromaDB |
| Cache | Redis |
| Backend | FastAPI |
| Frontend | React (desktop first) |
| Deployment | Render (backend), Vercel (frontend) |
| Solo build | Single developer — scope must remain achievable |

---

## 8. Open Decisions

| Decision | Status |
|---|---|
| Fallback data sources beyond API-Football | TBD — evaluated at build time |
| ChromaDB persistence on Render | Deferred — addressed at deployment |
| Match event persistent store technology | Deferred — build-time decision |
| ChatAgent conversation history strategy | Deferred — build-time decision |
