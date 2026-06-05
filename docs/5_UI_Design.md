# UI Design Specification
## Offside AI — 2026 FIFA World Cup Intelligence Companion
**Version:** 1.0  
**Date:** April 2026

---

## 1. Design Principles

| Principle | Application |
|---|---|
| Intelligence-forward | AI outputs are the hero of every view. Data is subordinate to insight. |
| State clarity | A user should always know whether they're looking at a preview, live match, or completed match — at a glance, without reading. |
| Casual-friendly | No jargon. Insights are explained, not assumed. |
| Desktop-first | Designed for 1280px+ viewport. Mobile deferred to v2. |

---

## 2. Design Language

### 2.1 Color System

| Token | Usage | Value |
|---|---|---|
| `--surface-base` | Page background | Near-black `#0D0F12` |
| `--surface-card` | Card backgrounds | `#161A20` |
| `--surface-elevated` | Hover states, selected cards | `#1E242D` |
| `--accent-primary` | Primary action, live indicator | Electric green `#00FF87` |
| `--accent-secondary` | Links, info highlights | `#4F9EFF` |
| `--text-primary` | Body text | `#F0F2F5` |
| `--text-muted` | Labels, metadata | `#6B7280` |
| `--border-subtle` | Card borders | `rgba(255,255,255,0.06)` |
| `--state-live` | LIVE badge | `#FF4545` |
| `--state-preview` | PREVIEW badge | `#4F9EFF` |
| `--state-fulltime` | FULL TIME badge | `#6B7280` |

### 2.2 Typography

| Element | Font | Size | Weight |
|---|---|---|---|
| Wordmark | Bebas Neue | 22px | 400 |
| Section headers | DM Sans | 18px | 600 |
| Team names (large) | DM Sans | 28px | 700 |
| Score display | Bebas Neue | 48px | 400 |
| Body / narrative | DM Sans | 15px | 400 |
| Labels / metadata | DM Sans | 12px | 400 |
| Chat bubbles | DM Sans | 14px | 400 |

### 2.3 Component Tokens

| Component | Style |
|---|---|
| Cards | `border-radius: 12px`, `border: 1px solid var(--border-subtle)`, `background: var(--surface-card)` |
| State badges | Pill shape, `border-radius: 100px`, uppercase, 11px |
| Primary buttons | `background: var(--accent-primary)`, dark text, `border-radius: 8px` |
| Ghost buttons | Transparent bg, `border: 1px solid var(--border-subtle)`, light text |
| Input fields | `background: rgba(255,255,255,0.04)`, subtle border, `border-radius: 8px` |

---

## 3. Layout Structure

### 3.1 Global Shell

```
┌─────────────────────────────────────────────────────────────┐
│  TOPNAV (56px)                                              │
│  [⚽ OFFSIDE AI]           [Fixtures]    [About]            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MAIN CONTENT AREA                                          │
│  (fills remaining viewport)                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Fixture Hub Layout

```
┌─────────────────────────────────────────────────────────────┐
│  TOPNAV                                                     │
├─────────────────────────────────────────────────────────────┤
│  HERO BANNER — Today's matches count + tournament info      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [TODAY]  [UPCOMING]  [COMPLETED]   ← Tab filter           │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ FIXTURE CARD │  │ FIXTURE CARD │  │ FIXTURE CARD │      │
│  │              │  │              │  │              │      │
│  │ 🇧🇷  vs  🇦🇷  │  │ 🏴󠁧󠁢󠁥󠁮󠁧󠁿  vs  🇫🇷 │  │ 🇩🇪  vs  🇵🇹  │      │
│  │  Brazil  ARG │  │  ENG   FRA  │  │  GER   POR  │      │
│  │  June 14     │  │  June 14    │  │  June 15    │      │
│  │  [LIVE]      │  │  [PREVIEW]  │  │  [UPCOMING] │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  (3-column card grid, scrollable)                           │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Match View Layout (PREVIEW State)

```
┌─────────────────────────────────────────────────────────────┐
│  TOPNAV                                                     │
├─────────────────────────────────────────────────────────────┤
│  MATCH HEADER                                               │
│  [PREVIEW badge]   Brazil vs Argentina   June 14, 2026      │
│  Group Stage — Group C                                      │
├───────────────────────────────────┬─────────────────────────┤
│                                   │                         │
│  MAIN PANEL (70%)                 │  SIDEBAR (30%)          │
│                                   │                         │
│  ┌─────────────────────────────┐  │  ┌───────────────────┐  │
│  │ TEAM COMPARISON STRIP       │  │  │ PREDICTION WIDGET │  │
│  │ Brazil ————|———— Argentina  │  │  │                   │  │
│  │ Form | Rank | Goals         │  │  │ Brazil    54%     │  │
│  └─────────────────────────────┘  │  │ Draw      22%     │  │
│                                   │  │ Argentina 24%     │  │
│  ┌─────────────────────────────┐  │  │                   │  │
│  │ AI PREVIEW REPORT           │  │  │ Expected: 1.4–0.9 │  │
│  │                             │  │  │                   │  │
│  │ [Team previews section]     │  │  │ "Brazil's attack  │  │
│  │ [Head-to-head section]      │  │  │  edge narrows on  │  │
│  │ [Form analysis section]     │  │  │  neutral ground…" │  │
│  │                             │  │  └───────────────────┘  │
│  └─────────────────────────────┘  │                         │
│                                   │  ┌───────────────────┐  │
│                                   │  │ KEY STATS         │  │
│                                   │  │ H2H: 37 meetings  │  │
│                                   │  │ BRA wins: 16      │  │
│                                   │  │ ARG wins: 14      │  │
│                                   │  └───────────────────┘  │
├───────────────────────────────────┴─────────────────────────┤
│  CHAT PANEL (collapsible — default collapsed)               │
│  [Ask anything about this match...]        [Send ↗]        │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Match View Layout (LIVE State)

```
┌─────────────────────────────────────────────────────────────┐
│  TOPNAV                                                     │
├─────────────────────────────────────────────────────────────┤
│  MATCH HEADER                                               │
│  [● LIVE badge]   Brazil 2 — 1 Argentina   67'             │
├───────────────────────────────────┬─────────────────────────┤
│                                   │                         │
│  MAIN PANEL (70%)                 │  SIDEBAR (30%)          │
│                                   │                         │
│  ┌─────────────────────────────┐  │  ┌───────────────────┐  │
│  │ SCOREBOARD                  │  │  │ CHAT PANEL        │  │
│  │  Brazil  2 — 1  Argentina   │  │  │ (Expanded in LIVE)│  │
│  │  67'                        │  │  │                   │  │
│  └─────────────────────────────┘  │  │ User: Who scored? │  │
│                                   │  │                   │  │
│  ┌─────────────────────────────┐  │  │ AI: Vinicius Jr.  │  │
│  │ EVENT TIMELINE              │  │  │ opened scoring    │  │
│  │                             │  │  │ in the 23rd min…  │  │
│  │  ⚽ 23' Vinicius Jr (BRA)   │  │  │                   │  │
│  │  ⚽ 41' Messi (ARG) pen     │  │  │ [input field]     │  │
│  │  🟨 54' Otamendi (ARG)      │  │  └───────────────────┘  │
│  │  ⚽ 67' Rodrygo (BRA)       │  │                         │
│  └─────────────────────────────┘  │                         │
│                                   │                         │
│  ┌─────────────────────────────┐  │                         │
│  │ AI NARRATIVE                │  │                         │
│  │ [Generate Narrative ↗]      │  │                         │
│  │                             │  │                         │
│  │ (narrative text appears     │  │                         │
│  │  here on demand)            │  │                         │
│  └─────────────────────────────┘  │                         │
└───────────────────────────────────┴─────────────────────────┘
```

### 3.5 Match View Layout (FULL TIME State)

```
┌─────────────────────────────────────────────────────────────┐
│  MATCH HEADER                                               │
│  [FULL TIME badge]   Brazil 2 — 1 Argentina   FT           │
├───────────────────────────────────┬─────────────────────────┤
│  MAIN PANEL (70%)                 │  SIDEBAR (30%)          │
│                                   │                         │
│  ┌─────────────────────────────┐  │  ┌───────────────────┐  │
│  │ FINAL SCORE CARD            │  │  │ KEY STATS         │  │
│  │  Brazil  2 — 1  Argentina   │  │  │ Possession        │  │
│  └─────────────────────────────┘  │  │ BRA 54% | ARG 46% │  │
│                                   │  │                   │  │
│  ┌─────────────────────────────┐  │  │ Shots on target   │  │
│  │ POST-MATCH AI REPORT        │  │  │ BRA 5  | ARG 3    │  │
│  │                             │  │  └───────────────────┘  │
│  │ [Match Summary]             │  │                         │
│  │ [Key Moments]               │  │  ┌───────────────────┐  │
│  │ [Player Highlights]         │  │  │ PLAYER OF MATCH   │  │
│  │ [Tactical Observations]     │  │  │ Vinicius Jr.      │  │
│  └─────────────────────────────┘  │  │ 1G 1A             │  │
│                                   │  └───────────────────┘  │
├───────────────────────────────────┴─────────────────────────┤
│  CHAT PANEL                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specifications

### 4.1 Fixture Card

| Element | Spec |
|---|---|
| Size | Fixed height 140px, fluid width (3-col grid) |
| Teams | Flag emoji + team name, left and right aligned |
| Score | Center, Bebas Neue 28px — shown only if LIVE or FULL TIME |
| Date/time | Below teams, muted 12px |
| State badge | Top-right corner pill |
| Hover | Background shifts to `--surface-elevated`, cursor pointer |
| Click | Navigates to Match View for that fixture |

### 4.2 State Badges

| State | Color | Label |
|---|---|---|
| PREVIEW | Blue accent | PREVIEW |
| LIVE | Red with pulse dot | ● LIVE |
| FULL TIME | Muted gray | FULL TIME |

### 4.3 Prediction Widget

| Element | Spec |
|---|---|
| Container | Sidebar card, fixed width |
| Probability bars | Three horizontal bars, color-coded (home / draw / away) |
| Goal expectancy | "Expected: X.X — X.X" in muted text below bars |
| Reasoning | Italicised AI text, max 3 lines, truncated with expand |
| Visibility | Pre-match only |

### 4.4 Chat Panel

| State | Behavior |
|---|---|
| PREVIEW | Collapsed by default. Click to expand as bottom drawer. |
| LIVE | Expanded by default in sidebar. |
| FULL TIME | Collapsed by default. Click to expand as bottom drawer. |
| Scope indicator | Small toggle: "This match" / "All matches" |
| Input | Full-width text input with Send button |
| History | Scrollable message thread, user right / AI left |

---

## 5. Navigation

| Element | Behaviour |
|---|---|
| Wordmark | Always links back to Fixture Hub |
| Fixtures tab | Active on Fixture Hub |
| Browser back | Returns to Fixture Hub from Match View |
| Match state | URL reflects fixture: `/match/{match_id}` |

---

## 6. States and Empty States

| Scenario | UI Behaviour |
|---|---|
| No matches today | "No matches scheduled today" with next match countdown |
| AI report loading | Skeleton loader in report panel |
| API data unavailable | Inline error message with retry button |
| Chat no response | Error bubble with retry option |
| Narrative not yet generated | Placeholder card with "Generate Narrative" CTA |
