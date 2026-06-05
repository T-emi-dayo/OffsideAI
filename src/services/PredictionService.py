from scipy.stats import poisson
import pickle
import numpy as np

ml_model = "src/data/models/dixon_coles_model.pkl"

class PredictionService:
    def __init__(self, model):
        with open(ml_model, 'rb') as file:
            model = pickle.load(file)
        self.model = model

    def predict_neutral(self, home_team, away_team, params, max_goals=8):
        """
        Predict match outcome probabilities for a neutral venue.
        Computes expected goals directly from team ratings without the home_advantage term.
        Valid for all World Cup fixtures (all played at neutral venues).
        """
        try:
            atk_h = params[f'attack_{home_team}']
            def_h = params[f'defence_{home_team}']
            atk_a = params[f'attack_{away_team}']
            def_a = params[f'defence_{away_team}']
        except KeyError as e:
            raise ValueError(f'Team not in training data: {e}')

        rho = params.get('rho', 0)

        # No home_advantage applied — neutral venue
        lambda_home = np.exp(atk_h + def_a)
        lambda_away = np.exp(atk_a + def_h)

        def dc_tau(i, j):
            if   i == 0 and j == 0: return 1 - lambda_home * lambda_away * rho
            elif i == 1 and j == 0: return 1 + lambda_away * rho
            elif i == 0 and j == 1: return 1 + lambda_home * rho
            elif i == 1 and j == 1: return 1 - rho
            return 1.0

        matrix = np.zeros((max_goals + 1, max_goals + 1))
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                matrix[i, j] = (poisson.pmf(i, lambda_home) *
                                poisson.pmf(j, lambda_away) *
                                dc_tau(i, j))
        matrix /= matrix.sum()

        return {
            'p_home':      float(np.sum(np.tril(matrix, -1))),
            'p_draw':      float(np.trace(matrix)),
            'p_away':      float(np.sum(np.triu(matrix, 1))),
        }


# ── Validation: manual prediction WITH home_advantage must match model.predict() ──
# This confirms the parameter naming convention before we rely on it for WC predictions.

    def _predict_with_ha(self, home_team, away_team):
        model = self.model
        try:
            predictions = model.predict(home_team, away_team)
            pb_home = float(predictions.home_win)
            pb_draw = float(predictions.draw)
            pb_away = float(predictions.away_win)
        except Exception as e:
            raise ValueError(f"Error during model prediction: {e}")
        
        return {
            'p_home': pb_home,
            'p_draw': pb_draw,
            'p_away': pb_away,
        }
    
    def predict_results(self, home_team, away_team, neutral=True):
        """Public method to predict match outcome probabilities for a neutral venue."""
        
        model_params = self.model.get_params()
        if neutral:
            return PredictionService.predict_neutral(home_team, away_team, model_params)
        if not neutral:
            return PredictionService._predict_with_ha(home_team, away_team, model_params)
        else:
            raise ValueError("Invalid value for 'neutral' parameter. Must be True or False.")