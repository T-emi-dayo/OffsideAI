# Offside AI — Frontend Implementation Plan

**Stack:** Vite + React 18 + TypeScript + React Router v6  
**Target:** Desktop-first (1280px+), deployed on Vercel  
**Backend:** FastAPI at `http://localhost:8000` (dev) / `VITE_API_URL` env var (prod)

---

## 1. Project Setup

```bash
npm create vite@latest offside-ai-frontend -- --template react-ts
cd offside-ai-frontend
npm install react-router-dom
npm install -D @types/react-router-dom
```

### Directory structure

```
offside-ai-frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── .env.example              # VITE_API_URL=http://localhost:8000
├── src/
│   ├── main.tsx
│   ├── App.tsx               # Router setup: / and /match/:id
│   ├── styles/
│   │   └── globals.css       # CSS variables + resets + base typography
│   ├── api/
│   │   └── client.ts         # Typed fetch wrapper for all endpoints
│   ├── types/
│   │   └── index.ts          # TypeScript types mirroring API schemas
│   ├── components/
│   │   ├── NavBar.tsx
│   │   ├── StateBadge.tsx
│   │   ├── FixtureCard.tsx
│   │   ├── PredictionWidget.tsx
│   │   ├── ChatPanel.tsx
│   │   ├── EventTimeline.tsx
│   │   ├── SkeletonLoader.tsx
│   │   └── ErrorCard.tsx
│   └── pages/
│       ├── FixtureHub.tsx
│       └── MatchView.tsx
```

---

## 2. Design Tokens (CSS Variables)

Define in `src/styles/globals.css` and use everywhere via `var()`:

```css
:root {
  --surface-base:     #0D0F12;
  --surface-card:     #161A20;
  --surface-elevated: #1E242D;
  --accent-primary:   #00FF87;   /* electric green — primary CTA, live indicator */
  --accent-secondary: #4F9EFF;   /* blue — links, info highlights */
  --text-primary:     #F0F2F5;
  --text-muted:       #6B7280;
  --border-subtle:    rgba(255,255,255,0.06);
  --state-live:       #FF4545;
  --state-preview:    #4F9EFF;
  --state-fulltime:   #6B7280;
}
```

**Fonts** (Google Fonts, load in `index.html`):
```html
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Bebas+Neue&display=swap" rel="stylesheet">
```

- Wordmark / scores / large display: `Bebas Neue`
- All other text: `DM Sans`

---

## 3. TypeScript Types (`src/types/index.ts`)

Mirror the Pydantic schemas exactly:

```ts
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

export type MatchState = "pre" | "live" | "post";

export interface FixtureTeam { name: string; }
export interface FixtureScore { home: number | null; away: number | null; }

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

export interface PreMatchData {
  prediction: {
    p_home: number;
    p_draw: number;
    p_away: number;
    lambda_home: number;
    lambda_away: number;
  } | null;
  report_narrative: string | null;
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

export interface ChatMessage { role: "user" | "assistant"; content: string; }

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
```

---

## 4. API Client (`src/api/client.ts`)

Single typed fetch wrapper. Base URL from env var.

```ts
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// Fixture endpoints
export const api = {
  getFixtures:      () => get<DataResponse<FixtureListData>>("/api/fixtures"),
  getFixturesToday: () => get<DataResponse<FixtureListData>>("/api/fixtures/today"),
  getFixturesLive:  () => get<DataResponse<FixtureListData>>("/api/fixtures/live"),

  // Match endpoints
  getMatch:      (id: number) => get<DataResponse<MatchMetadata>>(`/api/match/${id}`),
  getPreview:    (id: number) => get<AgentResponse<PreMatchData>>(`/api/match/${id}/preview`),
  getNarrative:  (id: number) => get<AgentResponse<LiveData>>(`/api/match/${id}/narrative`),
  getReport:     (id: number) => get<AgentResponse<PostMatchData>>(`/api/match/${id}/report`),
  getPrediction: (id: number) => get<AgentResponse<PredictionData>>(`/api/match/${id}/prediction`),
  postChat:      (id: number, body: ChatRequest) =>
                   post<AgentResponse<ChatData>>(`/api/match/${id}/chat`, body),
};
```

---

## 5. Routing (`src/App.tsx`)

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import FixtureHub from "./pages/FixtureHub";
import MatchView from "./pages/MatchView";

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<FixtureHub />} />
        <Route path="/match/:id" element={<MatchView />} />
      </Routes>
    </BrowserRouter>
  );
}
```

---

## 6. Component Specifications

### 6.1 `NavBar`
- Height: 56px, `border-bottom: 1px solid var(--border-subtle)`, semi-transparent bg
- Left: Wordmark "OFFSIDE AI" in `Bebas Neue`, green `--accent-primary`, links to `/`
- Right: "Fixtures" nav link (active indicator = green underline), "About" link
- Sticky at top

### 6.2 `StateBadge` — props: `state: "pre" | "live" | "post"`
- Shape: pill `border-radius: 100px`, uppercase, 11px, letter-spacing 0.5px
- `pre` → blue bg `rgba(79,158,255,0.15)`, text `--state-preview`, label "PREVIEW"
- `live` → red bg `rgba(255,69,69,0.15)`, text `--state-live`, label "● LIVE" (● has CSS `animation: pulse 1.4s infinite`)
- `post` → muted bg `rgba(107,114,128,0.15)`, text `--state-fulltime`, label "FULL TIME"

### 6.3 `FixtureCard` — props: `fixture: FixtureItem, onClick: () => void`
- Fixed height 140px, `border-radius: 12px`, card bg, subtle border
- Top-right: `<StateBadge state={fixture.match_state} />`
- Center: flag emoji + team name (left) | score or "vs" (center, Bebas Neue 26px) | flag emoji + team name (right)
- Bottom strip: date/time (left, muted 11px) | stage (right, muted 11px)
- Score shown only if `match_state !== "pre"`
- Hover: bg shifts to `--surface-elevated`
- Click: `onClick()` → navigate to `/match/{fixture.id}`

**Flag emoji lookup:** Map common World Cup nation names to flag emojis. A static `COUNTRY_FLAGS: Record<string, string>` table is sufficient. Example:
```ts
const COUNTRY_FLAGS: Record<string, string> = {
  "Brazil": "🇧🇷", "Argentina": "🇦🇷", "France": "🇫🇷",
  "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Germany": "🇩🇪", "Portugal": "🇵🇹",
  "Spain": "🇪🇸", "Netherlands": "🇳🇱", "Italy": "🇮🇹",
  "USA": "🇺🇸", "Mexico": "🇲🇽", "Morocco": "🇲🇦",
  "Japan": "🇯🇵", "South Korea": "🇰🇷", "Senegal": "🇸🇳",
  // ... extend as needed
};
```

### 6.4 `SkeletonLoader` — props: `lines?: number, height?: string`
- Animated shimmer placeholder while AI reports are loading
- `background: linear-gradient(90deg, var(--surface-card), var(--surface-elevated), var(--surface-card))`
- `animation: shimmer 1.6s infinite`

### 6.5 `ErrorCard` — props: `message: string, onRetry?: () => void`
- Muted red border, error icon, message, optional retry button
- Inline component — does NOT replace the entire page

### 6.6 `PredictionWidget` — props: `data: PredictionData, homeTeam: string, awayTeam: string`
- Sidebar card
- Three probability bars: Home / Draw / Away
  - Home bar: `--accent-primary` (green)
  - Draw bar: `--text-muted` (gray)
  - Away bar: `--accent-secondary` (blue)
  - Width = `${prob * 100}%`, animated with CSS transition
- Expected goals line: "Expected: {lambda_home:.1f} — {lambda_away:.1f}"
- Only visible in `pre` state

### 6.7 `EventTimeline` — props: `events: string[]` (formatted strings from `key_moments`)
- Vertical list of match events
- Icons by event type prefix: ⚽ for goals, 🟨 for yellow cards, 🟥 for red cards
- Each row: minute bubble + icon + event text
- Used in `live` and `post` states

### 6.8 `ChatPanel`
- **Props:** `matchId: number, homeTeam: string, awayTeam: string, matchState: MatchState, liveContext?: object`
- **State:** `expanded: boolean`, `history: ChatMessage[]`, `input: string`, `loading: boolean`
- Behavior by match state:
  - `pre` / `post`: collapsed by default, expands as a bottom drawer on click
  - `live`: always expanded in sidebar
- Layout: scrollable message thread (user right / AI left) + input row
- Sends full `history` with each request (stateless API)
- Shows `SkeletonLoader` while awaiting reply
- On error: red error bubble with retry

---

## 7. Pages

### 7.1 `FixtureHub` (`/`)

**State:** `tab: "today" | "upcoming" | "completed"`, fixture list from API

**On mount:** call `api.getFixturesToday()` for "TODAY" tab by default.  
**Tab switching:**
- TODAY → `api.getFixturesToday()`
- UPCOMING → `api.getFixtures()` then filter `match_state === "pre"` excluding today
- COMPLETED → `api.getFixtures()` then filter `match_state === "post"`

**Layout:**
```
┌──────────────────────────────────────────────┐
│ HERO: "2026 FIFA WORLD CUP" + today's count  │
├──────────────────────────────────────────────┤
│ [TODAY] [UPCOMING] [COMPLETED] ← tab bar     │
├──────────────────────────────────────────────┤
│ 3-col CSS grid of <FixtureCard> components   │
│ (or empty state message)                     │
└──────────────────────────────────────────────┘
```

**Empty state:** "No matches scheduled today" — show next upcoming match date.

### 7.2 `MatchView` (`/match/:id`)

**On mount:** `api.getMatch(id)` → populates `match: MatchMetadata`  
Then based on `match.match_state`:
- `pre` → also call `api.getPreview(id)` and `api.getPrediction(id)` (in parallel)
- `live` → user triggers narrative via button → `api.getNarrative(id)`
- `post` → also call `api.getReport(id)`

**Layout (70/30 split):**

```
┌────────────────────────────────────────────────┐
│ ← Back   [StateBadge]  Team A vs Team B        │
│           Stage • Date                         │
├───────────────────────────┬────────────────────┤
│ MAIN PANEL (70%)          │ SIDEBAR (30%)      │
│                           │                    │
│  [state-specific content] │ [state-specific    │
│                           │  widgets]          │
├───────────────────────────┴────────────────────┤
│ CHAT PANEL (collapsed drawer / expanded)       │
└────────────────────────────────────────────────┘
```

**PRE state main panel:**
- Team comparison strip (team names + "vs" center)
- AI Preview Report card (skeleton while loading, then narrative text rendered as paragraphs)

**PRE state sidebar:**
- `<PredictionWidget>` (skeleton while loading)
- Key stats card (from prediction: expected goals)

**LIVE state main panel:**
- Scoreboard card: `HomeTeam N — N AwayTeam` in Bebas Neue 48px
- Event timeline (from `key_moments`)
- AI Narrative card with "Generate Narrative ↗" button (triggers `getNarrative`)

**LIVE state sidebar:**
- `<ChatPanel>` (expanded by default)

**POST state main panel:**
- Final score card
- Post-match AI report (sections: match summary, key moments, player highlights, tactical analysis)

**POST state sidebar:**
- Key stats (extracted from `player_highlights`)
- Player of the match (first `player_highlights` entry)

**All states:**
- Chat panel at bottom (collapsed for pre/post, uses `<ChatPanel>`)
- Loading states use `<SkeletonLoader>`
- Errors use `<ErrorCard onRetry={...}>`

---

## 8. Environment Variables

```
# .env.example
VITE_API_URL=http://localhost:8000
```

For Vercel: set `VITE_API_URL` to the Render backend URL.

---

## 9. Build & Deploy

```bash
# dev
npm run dev

# production build
npm run build
npm run preview
```

**Vercel config (`vercel.json`):**
```json
{
  "rewrites": [{ "source": "/((?!api/).*)", "destination": "/index.html" }]
}
```

This ensures React Router handles client-side navigation (SPA fallback).

---

## 10. Implementation Order

1. Project scaffold + install deps
2. `src/styles/globals.css` — design tokens, resets, base styles
3. `src/types/index.ts` — all TypeScript interfaces
4. `src/api/client.ts` — typed API functions
5. `src/App.tsx` + `src/main.tsx` — router setup
6. `NavBar`, `StateBadge`, `SkeletonLoader`, `ErrorCard` — shared primitives
7. `FixtureCard` — with flag emoji map
8. `FixtureHub` page — the entry point
9. `PredictionWidget`, `EventTimeline` — match view widgets
10. `ChatPanel` — the interactive AI component
11. `MatchView` page — wires everything together
12. `vercel.json` — SPA fallback
13. End-to-end test: run backend + frontend locally, verify all 3 match states work
