# Data Preprocessing Plan
## Offside AI — 2026 FIFA World Cup Intelligence Companion
**Version:** 1.0
**Status:** In Progress
**Date:** April 2026

---

## Overview

This document covers the complete data preprocessing pipeline for the Offside AI match prediction model. It tracks every step from raw data loading through to a model-ready feature matrix, including decisions made, issues encountered, and resolutions applied.

**Final output:** A clean feature matrix `X`, target vectors `y_home` and `y_away`, and a sample weight vector `w` — all split into train, validation, and test sets, ready for Bivariate Poisson model training.

---

## Datasets

| Dataset | Variable | Source | Coverage | Rows |
|---|---|---|---|---|
| International matches | `df_filtered` | Kaggle | 2010–2025 | 15,781 (post-clean) |
| World Cup results | `world_cup_df` | Kaggle | 1930–2022 | — |
| FIFA rankings | `fifa_df` | Kaggle | Pre-2000–2025 | — |

---

## Stage 1 — Data Loading and Filtering ✅

### What Was Done
- International matches dataset loaded. Filtered to 2010–2025 to ensure recency signal dominates and remove noise from pre-modern football.
- World Cup dataset loaded with full historical coverage (1930–2022) — kept unfiltered intentionally for `wc_avg_stage` and `wc_titles` computation.
- FIFA rankings dataset loaded with full historical coverage.

### Columns — International Matches (`df_filtered`)
```
date, home_team, away_team, home_score, away_score,
tournament, country, neutral, date_column
```

**Note:** `date` was type `str`. `date_column` was the converted `datetime64[us]` version. `date_column` was renamed to `date` and the original string column dropped.

### Columns — FIFA Rankings (`fifa_df`)
```
rank, country_full, country_abrv, total_points,
previous_points, rank_change, confederation, rank_date
```

### Columns — World Cup (`world_cup_df`)
```
44 columns including: home_team, away_team, home_score, away_score,
Round, date, home_penalty, away_penalty, home_xg, away_xg, home_manager, ...
```

### Key Decision
World Cup dataset was **not** filtered to 2010. It retains full history because `wc_avg_stage` and `wc_titles` are historical aggregate features — more history produces more accurate team pedigree signals.

---

## Stage 2 — Team Name Normalisation ✅

### Problem
The same nation appeared under multiple name variants across the three datasets, which would silently break all joins and rolling calculations.

### Audit Results
- **45 teams** in international matches not found in FIFA rankings
- **25 teams** in FIFA rankings not found in international matches

### Resolution Categories

**Category 1 — Direct name mapping (FIFA uses different official name):**

| Matches Name | FIFA Name |
|---|---|
| West Germany | Germany |
| China | China PR |
| DR Congo | Congo DR |
| East Timor | Timor-Leste |
| Gambia | The Gambia |
| Hong Kong | Hong Kong, China |
| Iran | IR Iran |
| Ireland | Republic of Ireland |
| Ivory Coast | Côte d'Ivoire |
| Kyrgyzstan | Kyrgyz Republic |
| Macao | Macau |
| Macedonia | North Macedonia |
| North Korea | Korea DPR |
| Saint Kitts and Nevis | St Kitts and Nevis |
| Saint Lucia | St Lucia |
| Sao Tome and Principe | São Tomé and Príncipe |
| São Tome and Principe | São Tomé and Príncipe |
| South Korea | Korea Republic |
| St Vincent & Grenadines | St Vincent and the Grenadines |
| Swaziland | Eswatini |
| Taiwan | Chinese Taipei |
| Turkey | Türkiye |
| United States | USA |
| Brunei | Brunei Darussalam |
| Cape Verde | Cabo Verde |

**Category 2 — Non-FIFA entities (21 teams):**
Not FIFA members. Will never have rankings. Produce nulls in FIFA features by design. These are correct nulls, not data errors.

```
Bonaire, Chagos Islands, Eastern Samoa, Falkland Islands,
French Guiana, Greenland, Guadeloupe, Kiribati, Kurdistan,
Marshall Islands, Martinique, Mayotte, Northern Cyprus,
Northern Mariana Islands, Reunion, Saint Barthelemy,
Saint Martin, Saint Pierre and Miquelon, Sint Maarten,
Tuvalu, Zanzibar
```

**Category 3 — Historical teams (no longer exist):**
Present in FIFA dataset, will never match 2010–2025 matches. No action required.
```
Czechoslovakia, Yugoslavia, Zaire, Serbia and Montenegro
```

### Outcome
After applying `TEAM_NAME_MAP` to both `df_filtered` and `world_cup_df`, exactly 21 teams remain unmatched — all confirmed non-FIFA entities.

---

## Stage 3 — Duplicate Removal ✅

### Problem
Source data contained duplicate match rows that would corrupt rolling window calculations.

### Diagnosis
Three types of duplication were found:

**Type 1 — True source duplicates (same match stored multiple times):**
Anguilla, Bahamas, Montserrat, and others had identical match rows duplicated 2–3 times in the raw source data.

**Type 2 — Home/away swapped duplicates:**
Some matches were stored twice with home and away teams reversed (e.g. British Virgin Islands vs Cayman Islands AND Cayman Islands vs British Virgin Islands on the same date).

**Type 3 — São Tomé and Príncipe triplicated matches:**
All matches involving São Tomé and Príncipe were stored three times. Resolved by exact duplicate removal on `date + team + opponent` in the team history long-format table.

### Resolution
- Initial dedup on `home_team + away_team + date` — insufficient, missed Type 2 swapped duplicates
- Final dedup on `match_key + date` — `match_key` is an alphabetically sorted team pair key, order-independent
- 441 rows removed total
- Shape integrity assertion implemented and passing

### Genuine Two-Match Days (Preserved)
8 teams legitimately played two different matches on the same date in tournament scheduling. These were identified and kept:

```
Chile (2010-05-30), Guatemala (2010-09-07), Comoros (2025-06-09),
Mozambique (2025-06-10), South Africa (2025-06-10), Zimbabwe (2025-06-10),
Saudi Arabia (2010-10-12), St Kitts and Nevis (2025-05-25)
```

### Outcome
- **15,781 clean rows** confirmed
- Zero duplicates on `match_key + date`
- Shape integrity check passing

---

## Stage 4 — World Cup Stage Mapping ✅

### What Was Done
The `Round` column in `world_cup_df` contained 12 distinct string values covering all tournament formats from 1930 to 2022. These were mapped to an ordinal `stage` encoding.

### Mapping

| Round Value | Stage | Notes |
|---|---|---|
| First round | 1 | Pre-1954 group stage equivalent |
| First group stage | 1 | 1974/1978 two-group format |
| Group stage | 1 | Modern standard group stage |
| Group stage play-off | 1 | Tiebreaker within group |
| Second round | 2 | Pre-1974 knockout |
| Second group stage | 2 | 1974/1978 second group stage |
| Round of 16 | 2 | Modern R16 |
| Quarter-finals | 3 | Standard QF |
| Semi-finals | 4 | Standard SF |
| Third-place match | 4 | Third place playoff |
| Final stage | 4 | 1950 final group stage — no knockout final played |
| Final | 5 | Tournament final |

### Outcome
- Zero unmapped Round values confirmed
- `tournament_stage` joined onto `df_filtered`
- Non-WC matches assigned `tournament_stage = 1`
- 62 knockout matches confirmed with `stage > 1`

---

## Stage 5 — World Cup Derived Features ✅

### Features Computed

**`wc_avg_stage`** — average maximum stage reached per team across all World Cup tournaments in their history.

**`wc_titles`** — total World Cup titles won per team.

### Winner Detection
Penalty shootout finals handled explicitly using `home_penalty` and `away_penalty` columns. Three penalty finals correctly resolved:

| Year | Match | Score | Penalties | Winner |
|---|---|---|---|---|
| 2022 | Argentina vs France | 3–3 | 4–2 | Argentina |
| 2006 | Italy vs France | 1–1 | 5–3 | Italy |
| 1994 | Brazil vs Italy | 0–0 | 3–2 | Brazil |

### Validated Title Counts

| Team | Expected | Got |
|---|---|---|
| Brazil | 5 | 5 ✅ |
| Germany | 4 | 4 ✅ |
| Italy | 4 | 4 ✅ |
| Argentina | 3 | 3 ✅ |
| France | 2 | 2 ✅ |

### Outcome
- Zero nulls in `home/away_wc_avg_stage` and `home/away_wc_titles`
- Teams with no WC history assigned 0 — correct

---

## Stage 6 — FIFA Rankings Join ✅

### What Was Done
An as-of join was implemented: for each match, the most recent FIFA ranking snapshot on or before the match date was retrieved for both home and away teams.

### Features Added
```
home_fifa_ranking    away_fifa_ranking
home_fifa_points     away_fifa_points
```

### Key Decision
`previous_points`, `rank_change`, and `country_abrv` were excluded — only current rank and points are informative at prediction time.

### Outcome
- All FIFA-ranked nations joined successfully
- 21 non-FIFA entities produce nulls — correct, handled in imputation

---

## Stage 7 — Confederation Features ✅

### What Was Done
Confederation extracted from FIFA rankings dataset using the most recent snapshot per team. Label encoded for model input.

### Encoding Map
```
AFC      → 0
CAF      → 1
CONCACAF → 2
CONMEBOL → 3
OFC      → 4
UEFA     → 5
```

### Features Added
```
home_confederation       away_confederation       (string — for reference)
home_confederation_enc   away_confederation_enc   (encoded — model input)
```

### Outcome
- 276 home / 364 away nulls — all 21 non-FIFA entities confirmed
- Home confederation distribution: UEFA 4651, CAF 3771, AFC 3618, CONCACAF 2252, CONMEBOL 960, OFC 298

---

## Stage 8 — Rolling Window Features ✅

### Design Decisions
- **Window size:** 10 matches — sufficient history without overfitting to distant form
- **`shift(1)` mandatory** — prevents data leakage. Rolling average for match N uses only matches 1 through N-1
- **`min_periods=1`** — gracefully handles teams with fewer than 10 prior matches
- Long-format team history built by stacking home and away perspectives

### Features Computed

| Feature | Computation |
|---|---|
| `home/away_avg_goals_scored` | Rolling mean of goals scored, last 10 matches |
| `home/away_avg_goals_conceded` | Rolling mean of goals conceded, last 10 matches |
| `home/away_form_points` | Rolling mean of points per game (W=3, D=1, L=0), last 10 matches |
| `days_rest_home/away` | Days since team's previous match |

### Two-Match Day Handling
Teams that played two matches on the same date receive the same pre-match rolling values for both fixtures — correct, since both matches share identical prior history. Handled by deduplicating on `date + team` before the rolling features merge.

### Outcome
- 113–119 nulls in rolling features — first appearances per team, correct and expected
- Shape integrity check passing after join

---

## Stage 9 — H2H Features ✅

### What Was Done
For each match, all prior meetings between the same two teams were identified using `match_key`. Features computed from prior meetings only — `date < current match date` strictly enforced.

### Features Computed

| Feature | Description |
|---|---|
| `h2h_home_win_rate` | Win rate for the home team in prior H2H meetings |
| `h2h_draw_rate` | Draw rate in prior H2H meetings |
| `h2h_avg_total_goals` | Average total goals (home + away) in prior H2H meetings |

### Outcome
- 5,162 nulls — first-time matchups between teams. Correct and expected (~33% of fixtures)
- These nulls are handled in imputation with neutral prior values

---

## Stage 10 — Imputation 🔲

### Null Categories and Strategies

**Critical rule:** All median and global imputation values must be computed from the **training set only** (2010–2017 data). Computing from the full dataset leaks future information into validation and test sets.

#### Category 1 — Cold-Start Rolling Nulls (113–119 rows)

Cause: First match per team in the dataset — no prior history to compute rolling window from.

| Feature | Strategy | Value |
|---|---|---|
| `home/away_avg_goals_scored` | Global median from training set | Computed at fit time |
| `home/away_avg_goals_conceded` | Global median from training set | Computed at fit time |
| `home/away_form_points` | Global median from training set | Computed at fit time |
| `days_rest_home/away` | Global median from training set | Computed at fit time |

#### Category 2 — No H2H History (5,162 rows)

Cause: Teams meeting for the first time — no prior meetings to compute from.

| Feature | Strategy | Value |
|---|---|---|
| `h2h_home_win_rate` | Fixed neutral prior | 0.33 |
| `h2h_draw_rate` | Fixed neutral prior | 0.33 |
| `h2h_avg_total_goals` | Global median from training set | Computed at fit time |

Rationale: 0.33 represents equal probability across win/draw/loss for a team with no H2H history. Using median here would imply historical dominance — not appropriate for first-time matchups.

#### Category 3 — Non-FIFA Entity Nulls

Cause: 21 non-FIFA territories have no FIFA rankings.

| Feature | Strategy | Value |
|---|---|---|
| `home/away_fifa_ranking` | Fixed worst-case | 210 (bottom of rankings) |
| `home/away_fifa_points` | Global median from training set | Computed at fit time |
| `home/away_confederation_enc` | Fixed indicator | -1 (unknown confederation) |

Rationale: Non-FIFA entities are genuinely weaker than ranked nations — assigning median ranking would overstate their quality. Rank 210 is the honest lower bound.

### Implementation Pattern
```python
# Fit imputation values on training set only
train_mask = df_filtered['date'].dt.year <= 2017

imputation_values = {
    'home_avg_goals_scored':   df_filtered[train_mask]['home_avg_goals_scored'].median(),
    'away_avg_goals_scored':   df_filtered[train_mask]['away_avg_goals_scored'].median(),
    # ... all rolling features
    'h2h_avg_total_goals':     df_filtered[train_mask]['h2h_avg_total_goals'].median(),
    'home_fifa_points':        df_filtered[train_mask]['home_fifa_points'].median(),
    'away_fifa_points':        df_filtered[train_mask]['away_fifa_points'].median(),
    'home_fifa_ranking':       210,
    'away_fifa_ranking':       210,
    'h2h_home_win_rate':       0.33,
    'h2h_draw_rate':           0.33,
    'home_confederation_enc':  -1,
    'away_confederation_enc':  -1,
}

# Apply to full dataset
df_filtered.fillna(imputation_values, inplace=True)

# Save imputation values for inference time
import json
json.dump(
    {k: float(v) for k, v in imputation_values.items()},
    open('models/imputation_values.json', 'w')
)
```

---

## Stage 11 — Match Weight Computation 🔲

### Importance Weight
Derived from the `tournament` column using a mapping.

```python
IMPORTANCE_WEIGHT_MAP = {
    'FIFA World Cup':                    1.00,
    'FIFA World Cup qualification':      0.75,
    'UEFA Euro qualification':           0.70,
    'CAF Africa Cup of Nations':         0.70,
    'Copa América':                      0.70,
    'UEFA Nations League':               0.60,
    'Friendly':                          0.30,
    # All other tournaments → 0.50 default
}
```

**Note:** The `tournament` column will have many distinct values. A full audit of unique tournament names is required to build the complete mapping. Any unmapped tournament defaults to 0.50.

### Recency Weight
Exponential decay relative to end of training period (2017-12-31).

```python
import numpy as np

DECAY_RATE = 0.1  # Tune so 5-year-old match carries ~60% weight

reference_date = pd.Timestamp('2017-12-31')
years_before   = (reference_date - df_filtered['date']).dt.days / 365.25
recency_weight = np.exp(-DECAY_RATE * years_before)
```

### Combined Match Weight
```python
df_filtered['importance_weight'] = df_filtered['tournament'].map(
    IMPORTANCE_WEIGHT_MAP
).fillna(0.50)

df_filtered['recency_weight'] = recency_weight
df_filtered['match_weight']   = (
    df_filtered['importance_weight'] * df_filtered['recency_weight']
)
```

---

## Stage 12 — Feature Finalisation 🔲

### Columns to Drop
Used during engineering but not model inputs:

```python
cols_to_drop = [
    'tournament',           # used for importance weight — not a model feature
    'country',              # not a model feature
    'match_key',            # engineering artifact
    'home_confederation',   # string version — encoded version is the feature
    'away_confederation',   # string version
    'importance_weight',    # component of match_weight
    'recency_weight',       # component of match_weight
]
```

### Final Feature List (23 features)

```python
feature_cols = [
    # FIFA strength
    'home_fifa_ranking',        'away_fifa_ranking',
    'home_fifa_points',         'away_fifa_points',
    # Rolling form
    'home_avg_goals_scored',    'away_avg_goals_scored',
    'home_avg_goals_conceded',  'away_avg_goals_conceded',
    'home_form_points',         'away_form_points',
    # H2H
    'h2h_home_win_rate',        'h2h_draw_rate',
    'h2h_avg_total_goals',
    # Match context
    'tournament_stage',         'neutral',
    'days_rest_home',           'days_rest_away',
    # WC pedigree
    'home_wc_avg_stage',        'away_wc_avg_stage',
    'home_wc_titles',           'away_wc_titles',
    # Confederation
    'home_confederation_enc',   'away_confederation_enc',
]
```

### Save Feature Column Order
```python
import json
json.dump(feature_cols, open('models/feature_columns.json', 'w'))
```

This is mandatory. Inference time must use identical column order or model outputs will be incorrect.

---

## Stage 13 — Train / Validation / Test Split 🔲

### Split Design
Temporal split only — random splitting is never used as it leaks future information into training.

| Split | Period | Filter | Purpose | Approx Rows |
|---|---|---|---|---|
| Training | 2010–2017 | All matches | Model fitting | ~7,000 |
| Validation | 2018 | World Cup matches only | ρ estimation, hyperparameter tuning | 64 |
| Test | 2022 | World Cup matches only | Final held-out evaluation | 64 |

**Note:** 2019–2021 and 2023–2025 matches exist in `df_filtered` but are excluded from val and test. They are part of the training-adjacent window and serve as implicit out-of-sample signal but are not used for formal evaluation.

```python
train = df_filtered[df_filtered['date'].dt.year <= 2017].copy()

val = df_filtered[
    (df_filtered['date'].dt.year == 2018) &
    (df_filtered['tournament'].str.contains('World Cup', na=False))
].copy()

test = df_filtered[
    (df_filtered['date'].dt.year == 2022) &
    (df_filtered['tournament'].str.contains('World Cup', na=False))
].copy()

print(f"Train: {train.shape[0]} rows")
print(f"Val:   {val.shape[0]} rows")
print(f"Test:  {test.shape[0]} rows")
```

---

## Stage 14 — Target Variable Preparation 🔲

```python
# Targets — what the Poisson model predicts
y_train_home = train['home_score'].values
y_train_away = train['away_score'].values

y_val_home   = val['home_score'].values
y_val_away   = val['away_score'].values

y_test_home  = test['home_score'].values
y_test_away  = test['away_score'].values

# Features
X_train = train[feature_cols].copy()
X_val   = val[feature_cols].copy()
X_test  = test[feature_cols].copy()

# Sample weights — training only
w_train = train['match_weight'].values
```

---

## Stage 15 — Feature Scaling 🔲

Poisson regression is sensitive to feature scale. Features on vastly different scales cause convergence issues and biased coefficient estimates.

### Strategy
- **StandardScaler** applied to continuous features only
- Fit on training set only — transform val and test using training statistics
- Boolean and ordinal features left unscaled

### Continuous Features to Scale
```python
continuous_features = [
    'home_fifa_ranking',        'away_fifa_ranking',
    'home_fifa_points',         'away_fifa_points',
    'home_avg_goals_scored',    'away_avg_goals_scored',
    'home_avg_goals_conceded',  'away_avg_goals_conceded',
    'home_form_points',         'away_form_points',
    'h2h_avg_total_goals',
    'days_rest_home',           'days_rest_away',
    'home_wc_avg_stage',        'away_wc_avg_stage',
]
```

### Features Left Unscaled (ordinal / boolean / low-cardinality)
```python
unscaled_features = [
    'neutral',                  # boolean
    'tournament_stage',         # ordinal 1–5
    'home_wc_titles',           # count 0–5
    'away_wc_titles',           # count 0–5
    'home_confederation_enc',   # categorical 0–5 or -1
    'away_confederation_enc',   # categorical 0–5 or -1
    'h2h_home_win_rate',        # already 0–1
    'h2h_draw_rate',            # already 0–1
]
```

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_train[continuous_features] = scaler.fit_transform(
    X_train[continuous_features]
)
X_val[continuous_features]   = scaler.transform(X_val[continuous_features])
X_test[continuous_features]  = scaler.transform(X_test[continuous_features])

# Save scaler for inference time
import joblib
joblib.dump(scaler, 'models/feature_scaler.pkl')
```

---

## Stage 16 — Final Integrity Checks 🔲

Before handing data to the model — all assertions must pass:

```python
# 1. Zero nulls in all feature matrices
assert X_train.isna().sum().sum() == 0, "Nulls in X_train"
assert X_val.isna().sum().sum()   == 0, "Nulls in X_val"
assert X_test.isna().sum().sum()  == 0, "Nulls in X_test"

# 2. Zero nulls in all target vectors
assert pd.Series(y_train_home).isna().sum() == 0
assert pd.Series(y_train_away).isna().sum() == 0

# 3. Feature column count matches spec
assert X_train.shape[1] == len(feature_cols), \
    f"Expected {len(feature_cols)} features, got {X_train.shape[1]}"

# 4. No future data in training set
assert train['date'].max().year <= 2017, "Future data in training set"

# 5. Validation set is WC matches only
assert val['tournament'].str.contains('World Cup').all(), \
    "Non-WC matches in validation set"

# 6. Test set is WC matches only
assert test['tournament'].str.contains('World Cup').all(), \
    "Non-WC matches in test set"

# 7. Weight vector is positive and finite
assert (w_train > 0).all(), "Non-positive weights in training set"
assert np.isfinite(w_train).all(), "Non-finite weights in training set"

# 8. Target values are non-negative integers
assert (y_train_home >= 0).all()
assert (y_train_away >= 0).all()

print("All integrity checks passed. Data is ready for model training.")
```

---

## Saved Artifacts

All artifacts saved to `models/` directory for use at inference time:

| Artifact | File | Purpose |
|---|---|---|
| Feature column order | `feature_columns.json` | Ensures inference uses identical column order |
| Imputation values | `imputation_values.json` | Apply same imputation at inference time |
| Feature scaler | `feature_scaler.pkl` | Transform inference features using training statistics |
| Poisson model (home) | `poisson_home.pkl` | Predict λ_home |
| Poisson model (away) | `poisson_away.pkl` | Predict λ_away |
| Dixon-Coles ρ | `rho.pkl` | Low-score correction parameter |

---

## Status Summary

| Stage | Description | Status |
|---|---|---|
| 1 | Data loading and filtering | ✅ Complete |
| 2 | Team name normalisation | ✅ Complete |
| 3 | Duplicate removal | ✅ Complete |
| 4 | World Cup stage mapping | ✅ Complete |
| 5 | World Cup derived features | ✅ Complete |
| 6 | FIFA rankings join | ✅ Complete |
| 7 | Confederation features | ✅ Complete |
| 8 | Rolling window features | ✅ Complete |
| 9 | H2H features | ✅ Complete |
| 10 | Imputation | 🔲 Next |
| 11 | Match weight computation | 🔲 Pending |
| 12 | Feature finalisation | 🔲 Pending |
| 13 | Train / val / test split | 🔲 Pending |
| 14 | Target variable preparation | 🔲 Pending |
| 15 | Feature scaling | 🔲 Pending |
| 16 | Final integrity checks | 🔲 Pending |
