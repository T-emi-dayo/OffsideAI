# ML Model Design Document
## Offside AI — 2026 FIFA World Cup Intelligence Companion
**Version:** 1.0  
**Status:** Locked  
**Date:** April 2026

---

## 1. Overview

The Offside AI prediction system consists of two components:

| Component | Type | Purpose |
|---|---|---|
| Bivariate Poisson + Dixon-Coles | Trained ML model | Predict scoreline distribution and match outcome probabilities for any fixture |
| Monte Carlo Tournament Simulator | Simulation logic | Use the match model as an engine to simulate the full World Cup bracket and output per-team tournament probabilities |

These two components form one unified prediction system. There is one trained model. The simulator is not trained — it is deterministic logic that calls the match model repeatedly.

---

## 2. Match Prediction Model

### 2.1 Model Type

**Bivariate Poisson Regression with Dixon-Coles Low-Score Correction**

The model trains two Poisson regression heads simultaneously:
- **Head 1** — predicts λ_home: expected goals for the home/first-named team
- **Head 2** — predicts λ_away: expected goals for the away/second-named team

A Dixon-Coles correction layer adjusts the joint probability distribution for low-scoring outcomes, correcting a known systematic bias in independent Poisson models.

### 2.2 Why Bivariate Poisson

Football goals are rare, discrete, count events — precisely the domain Poisson distributions are designed to model. Goals scored by two teams in the same match are not fully independent; the Dixon-Coles correction handles the statistical dependence that arises specifically in low-scoring outcomes without requiring a fundamentally different model architecture.

This approach is the validated standard in academic football prediction literature and produces the scoreline distributions required by the tournament simulator.

### 2.3 The Dixon-Coles Correction

Independent Poisson systematically underestimates the frequency of 0-0, 1-0, and 0-1 results, and slightly overestimates 1-1 results. This matters because these scorelines constitute a significant proportion of all football matches.

The correction introduces one additional parameter — **ρ (rho)** — which modifies the joint probability of four specific scorelines only:

| Scoreline | Correction Direction |
|---|---|
| 0 — 0 | Adjusted upward |
| 1 — 0 | Adjusted upward |
| 0 — 1 | Adjusted upward |
| 1 — 1 | Adjusted downward |

All other scorelines (any match where at least one team scores 2+) are unchanged from the raw Poisson output. ρ is estimated from training data via maximum likelihood estimation — it is one scalar value, estimated once during training, applied at every inference call.

**The correction does not change the model architecture.** It is an adjustment layer applied to the joint probability distribution after both Poisson heads produce their expected goals values.

### 2.4 Model Outputs

From λ_home and λ_away, the model derives:

```
Primary outputs:
- λ_home              Expected goals, Team A
- λ_away              Expected goals, Team B

Derived outputs (from joint score distribution):
- P(home win)         Sum of P(i > j) across all scoreline combinations
- P(draw)             Sum of P(i = j) across all scoreline combinations
- P(away win)         Sum of P(i < j) across all scoreline combinations
- Most likely score   argmax of joint probability matrix
- Score distribution  Full P(i — j) matrix up to e.g. 8 goals per team
```

The score distribution matrix is what the tournament simulator consumes.

### 2.5 Model Interface

```python
class MatchPrediction(TypedDict):
    home_team: str
    away_team: str
    lambda_home: float          # Expected goals, home team
    lambda_away: float          # Expected goals, away team
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    most_likely_score: tuple    # e.g. (1, 0)
    score_distribution: dict    # {(i, j): probability}

def predict_match(home_team: str, away_team: str, features: dict) -> MatchPrediction:
    ...
```

---

## 3. Training Data

### 3.1 Scope

All senior international football matches from **2010 to 2025** including:
- FIFA World Cup matches
- FIFA World Cup qualifying matches
- Continental qualifying matches (UEFA, CONMEBOL, CAF, AFC, CONCACAF, OFC)
- UEFA Nations League
- International friendlies

World Cup data alone (~900 matches across 22 tournaments) is insufficient for reliable parameter estimation. The broader international dataset provides thousands of matches while the weighting scheme (Section 3.2) ensures World Cup and recent competitive matches dominate the model's learning.

### 3.2 Data Sources

| Source | Content | Usage |
|---|---|---|
| football-data.org | International results 2010–2025 | Primary historical match results |
| Kaggle World Cup datasets | World Cup results 1930–2022 | World Cup match records |
| API-Football | Team statistics, FIFA rankings, recent form | Feature engineering at inference time |
| FIFA public rankings | Official FIFA ranking points and positions | Feature input |

### 3.3 Training Weight Scheme

Each training match carries a composite weight:

```
match_weight = importance_weight × recency_weight
```

**Importance weights:**

| Match Type | Weight |
|---|---|
| World Cup match | 1.00 |
| World Cup qualifier | 0.75 |
| Continental qualifier | 0.70 |
| Nations League | 0.60 |
| International friendly | 0.30 |

**Recency weights** (exponential decay):

```python
recency_weight = exp(-decay_rate × years_before_present)
# decay_rate tuned so a match 5 years ago carries ~50% weight
# a match 10 years ago carries ~25% weight
```

**Combined example:**

| Match | Importance | Recency | Final Weight |
|---|---|---|---|
| 2022 World Cup final | 1.00 | ~0.85 | ~0.85 |
| 2024 qualifier | 0.75 | ~0.95 | ~0.71 |
| 2018 World Cup match | 1.00 | ~0.65 | ~0.65 |
| 2015 friendly | 0.30 | ~0.40 | ~0.12 |

### 3.4 Team Name Normalisation

Across datasets, the same nation appears under multiple name variants (e.g. "Ivory Coast", "Côte d'Ivoire", "CIV"). A normalisation map must be built and applied before any feature engineering. This is a data cleaning step, not a modelling step, but it is a known time cost that must be planned for.

### 3.5 Train / Validation / Test Split

**Temporal split — never random:**

| Split | Period | Purpose |
|---|---|---|
| Training | 2010 – 2017 | Model fitting |
| Validation | 2018 World Cup | Hyperparameter tuning, ρ estimation |
| Test | 2022 World Cup | Final held-out evaluation |

The test set is exclusively World Cup matches to validate model performance specifically in tournament conditions, which differ from qualifier and friendly football. Random splitting is not used — it would leak future information into training.

---

## 4. Feature Set

### 4.1 Design Constraint

Every feature must be computable at inference time from data available before the match is played. Features requiring in-match data (xG, possession, press intensity) are excluded because they are not available at prediction time from the data sources confirmed for this project.

### 4.2 Feature Definitions

| Feature | Description | Source | Notes |
|---|---|---|---|
| `home_fifa_ranking` | FIFA ranking position, home team | FIFA public / API-Football | Lower = stronger |
| `away_fifa_ranking` | FIFA ranking position, away team | FIFA public / API-Football | Lower = stronger |
| `home_fifa_points` | FIFA ranking points, home team | FIFA public | Continuous strength measure |
| `away_fifa_points` | FIFA ranking points, away team | FIFA public | Continuous strength measure |
| `home_avg_goals_scored` | Average goals scored, last 10 internationals | football-data.org | Attacking strength |
| `home_avg_goals_conceded` | Average goals conceded, last 10 internationals | football-data.org | Defensive strength |
| `away_avg_goals_scored` | Average goals scored, last 10 internationals | football-data.org | Attacking strength |
| `away_avg_goals_conceded` | Average goals conceded, last 10 internationals | football-data.org | Defensive strength |
| `home_form_points` | Points per game, last 10 internationals (W=3, D=1, L=0) | football-data.org | Recent momentum |
| `away_form_points` | Points per game, last 10 internationals | football-data.org | Recent momentum |
| `h2h_home_win_rate` | Home team win rate in last 10 H2H meetings | API-Football | Historical dominance |
| `h2h_draw_rate` | Draw rate in last 10 H2H meetings | API-Football | H2H pattern |
| `h2h_avg_total_goals` | Average total goals in last 10 H2H meetings | API-Football | H2H scoring pattern |
| `tournament_stage` | Current stage of competition | Fixture metadata | Encoded ordinally |
| `neutral_venue` | Whether match is at a neutral venue | Static: True for all WC | Boolean |
| `days_rest_home` | Days since home team's last match | Fixture schedule | Fatigue proxy |
| `days_rest_away` | Days since away team's last match | Fixture schedule | Fatigue proxy |
| `home_wc_avg_stage` | Average World Cup stage reached, last 5 tournaments | Kaggle WC dataset | Tournament pedigree |
| `away_wc_avg_stage` | Average World Cup stage reached, last 5 tournaments | Kaggle WC dataset | Tournament pedigree |
| `home_wc_titles` | Number of World Cup titles won | Kaggle WC dataset | Historical prestige |
| `away_wc_titles` | Number of World Cup titles won | Kaggle WC dataset | Historical prestige |

### 4.3 Tournament Stage Encoding

```python
STAGE_ENCODING = {
    "Group Stage":      1,
    "Round of 16":      2,
    "Quarter Final":    3,
    "Semi Final":       4,
    "Third Place":      4,
    "Final":            5
}
```

### 4.4 Features Explicitly Excluded

| Feature | Reason |
|---|---|
| xG (expected goals) | Not available from confirmed data sources |
| Possession percentage | No reliable historical source |
| Press intensity / defensive line | Proprietary, unavailable |
| Player-level fitness / injury status | Inconsistent availability, not reliable at inference time |
| In-match events (goals scored so far, cards) | Requires dynamic in-match model — v2 |

---

## 5. Training Pipeline

### 5.1 Pipeline Steps

```
1. Data ingestion
   Load raw CSVs from football-data.org and Kaggle
   Fetch FIFA rankings and team stats from API-Football

2. Team name normalisation
   Apply normalisation map across all datasets
   Resolve all country name variants to canonical names

3. Feature engineering
   Compute all features per match from raw data
   Compute match weights (importance × recency)
   Output: feature matrix X, target matrix y (home_goals, away_goals), weights w

4. Train / validation / test split
   Temporal split: train 2010–2017, val 2018 WC, test 2022 WC

5. Model fitting
   Fit Poisson regression Head 1 (λ_home) on training set with weights
   Fit Poisson regression Head 2 (λ_away) on training set with weights
   Estimate ρ via maximum likelihood on validation set

6. Evaluation
   Evaluate on 2022 World Cup test set
   Metrics: Ranked Probability Score (primary), log-loss, accuracy

7. Artifact saving
   Save: poisson_home.pkl, poisson_away.pkl, rho.pkl, feature_scaler.pkl
```

### 5.2 Evaluation Metrics

| Metric | Why |
|---|---|
| Ranked Probability Score (RPS) | Primary metric. Standard for probabilistic football prediction. Penalises predictions that are confident and wrong more than predictions that are uncertain. Lower is better. |
| Log-loss | Measures calibration of win/draw/loss probabilities |
| Accuracy | Simple outcome prediction accuracy — used for comparison only, not for model selection |

Accuracy alone is insufficient as an evaluation metric for probabilistic models. A model that always predicts the favourite wins will have reasonable accuracy but terrible calibration — it would be useless for tournament simulation where uncertainty compounds across rounds.

### 5.3 Saved Artifacts

```
models/
  poisson_home.pkl       # Fitted Poisson regression, λ_home
  poisson_away.pkl       # Fitted Poisson regression, λ_away
  rho.pkl                # Dixon-Coles correction parameter
  feature_scaler.pkl     # Feature scaler (if normalisation applied)
  feature_columns.json   # Ordered feature list for inference consistency
```

---

## 6. Inference Pipeline

At prediction time, for a given fixture:

```
1. Fetch current feature values for both teams
   (FIFA rankings, recent form, H2H, fixture metadata)

2. Engineer feature vector in the same order as training
   (use feature_columns.json to guarantee column order)

3. Load model artifacts

4. Predict:
   λ_home = poisson_home.predict(features)
   λ_away = poisson_away.predict(features)

5. Compute joint score distribution:
   For i in range(0, max_goals):
     For j in range(0, max_goals):
       P(i, j) = poisson_pmf(i, λ_home) × poisson_pmf(j, λ_away)
       Apply Dixon-Coles correction for (0,0), (1,0), (0,1), (1,1)

6. Derive outputs:
   P(home win) = sum of P(i,j) where i > j
   P(draw)     = sum of P(i,j) where i = j
   P(away win) = sum of P(i,j) where i < j
   Most likely score = argmax of P(i,j) matrix

7. Pass to PredictionAgent for natural language reasoning
```

---

## 7. Monte Carlo Tournament Simulator

### 7.1 What It Is

A deterministic simulation engine that uses the match prediction model as its engine. It is not trained. It simulates the full World Cup bracket 10,000 times and aggregates outcomes into per-team probability distributions.

### 7.2 Simulation Logic

```python
def simulate_tournament(bracket: dict, n_simulations: int = 10_000) -> dict:
    results = defaultdict(lambda: defaultdict(int))

    for sim in range(n_simulations):
        bracket_copy = deepcopy(bracket)

        for round in ["Group Stage", "Round of 16", "Quarter Final",
                      "Semi Final", "Final"]:
            for fixture in bracket_copy[round]:
                # Get current features for both teams at this point in sim
                features = build_features(fixture.home_team, fixture.away_team)

                # Get score distribution from match model
                score_dist = predict_match(fixture.home_team,
                                           fixture.away_team,
                                           features).score_distribution

                # Sample one outcome from the distribution
                outcome = sample_outcome(score_dist)

                # Advance winner to next round in this simulation
                advance_winner(bracket_copy, fixture, outcome)

                # Record stage reached for each team
                results[fixture.loser]["stage_reached"] += round

        results[bracket_copy["Final"].winner]["winner"] += 1

    return aggregate_results(results, n_simulations)
```

### 7.3 Simulator Outputs

Per team, across 10,000 simulations:

| Output | Description |
|---|---|
| `win_probability` | % of simulations where team wins tournament |
| `final_probability` | % of simulations where team reaches final |
| `semi_probability` | % of simulations where team reaches semi-final |
| `quarter_probability` | % of simulations where team reaches quarter-final |
| `expected_stage` | Average stage of exit across all simulations |
| `confidence_interval` | 90% CI on win probability |

### 7.4 Uncertainty Handling

Tournament win probabilities carry compounding uncertainty — each round's prediction error multiplies into the next. The UI must surface confidence intervals, not just point estimates, to represent this honestly. A team shown as "14% to win the tournament" with a 90% CI of 8%–21% is a more honest representation than a single number.

---

## 8. Key Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| Model type | Bivariate Poisson + Dixon-Coles | Industry standard, produces scoreline distributions, interpretable, validated in literature |
| Dixon-Coles vs. independent Poisson | Dixon-Coles | Independent Poisson systematically mispredicts low-scoring results — unacceptable given their frequency |
| XGBoost | Dropped from v1 | Cannot produce scoreline distributions; creates contradictory outputs with Poisson; deferred to v2 |
| Training data scope | All internationals 2010–2025 | WC-only data (~900 matches) too thin; broader dataset with weighting gives richer signal |
| Weighting scheme | Importance × recency | Recent competitive matches should dominate; old friendly data should carry near-zero weight |
| Train/val/test split | Temporal only | Random split leaks future data; test set is 2022 WC exclusively to validate on tournament conditions |
| Evaluation metric | RPS (primary) | Standard for probabilistic football prediction; accuracy alone is insufficient for a probabilistic model |
| Dynamic in-match model | Deferred to v2 | Requires match-state inference pipeline; significant architecture change; maps to v2 live features |
| Tournament predictor | Monte Carlo simulation | Cannot train a WC winner classifier on 22 tournaments; simulation correctly propagates uncertainty through bracket |
| Confidence intervals | Shown in UI | Compounding uncertainty across rounds must be surfaced honestly |
