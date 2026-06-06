from __future__ import annotations

import logging
import pickle

import numpy as np
from scipy.stats import poisson

logger = logging.getLogger(__name__)

_MODEL_PATH = "src/data/models/dixon_coles_model.pkl"


class PredictionService:
    """
    Wraps the trained Dixon-Coles Bivariate Poisson model.

    Loads the model artifact once at init. Provides two prediction modes:
    - neutral venue (World Cup — no home advantage applied)
    - with home advantage (non-neutral fixtures)
    """

    def __init__(self) -> None:
        with open(_MODEL_PATH, "rb") as fh:
            self.model = pickle.load(fh)
        logger.info("PredictionService: model loaded from %s", _MODEL_PATH)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def predict_results(
        self,
        home_team: str,
        away_team: str,
        neutral: bool = True,
    ) -> dict:
        """
        Return win/draw/loss probabilities for a fixture.

        Parameters
        ----------
        home_team : str
            Home (or first-named) team — must match training data names.
        away_team : str
            Away (or second-named) team.
        neutral : bool
            True for neutral venues (all World Cup matches).
            False applies the home advantage parameter from the model.

        Returns
        -------
        dict
            {"p_home": float, "p_draw": float, "p_away": float}
        """
        if neutral:
            params = self.model.get_params()
            return self._predict_neutral(home_team, away_team, params)
        return self._predict_with_ha(home_team, away_team)

    # -----------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------

    def _predict_neutral(
        self,
        home_team: str,
        away_team: str,
        params: dict,
        max_goals: int = 8,
    ) -> dict:
        """
        Predict at a neutral venue — no home advantage term applied.

        Valid for all World Cup fixtures.
        """
        try:
            atk_h = params[f"attack_{home_team}"]
            def_h = params[f"defence_{home_team}"]
            atk_a = params[f"attack_{away_team}"]
            def_a = params[f"defence_{away_team}"]
        except KeyError as exc:
            raise ValueError(f"Team not found in model training data: {exc}") from exc

        rho = params.get("rho", 0.0)

        lambda_home = float(np.exp(atk_h + def_a))
        lambda_away = float(np.exp(atk_a + def_h))

        def dc_tau(i: int, j: int) -> float:
            if i == 0 and j == 0:
                return 1 - lambda_home * lambda_away * rho
            if i == 1 and j == 0:
                return 1 + lambda_away * rho
            if i == 0 and j == 1:
                return 1 + lambda_home * rho
            if i == 1 and j == 1:
                return 1 - rho
            return 1.0

        matrix = np.zeros((max_goals + 1, max_goals + 1))
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                matrix[i, j] = (
                    poisson.pmf(i, lambda_home)
                    * poisson.pmf(j, lambda_away)
                    * dc_tau(i, j)
                )
        matrix /= matrix.sum()

        return {
            "p_home": float(np.sum(np.tril(matrix, -1))),
            "p_draw": float(np.trace(matrix)),
            "p_away": float(np.sum(np.triu(matrix, 1))),
            "lambda_home": lambda_home,
            "lambda_away": lambda_away,
        }

    def _predict_with_ha(self, home_team: str, away_team: str) -> dict:
        """Predict using the model's built-in predict (includes home advantage)."""
        try:
            result = self.model.predict(home_team, away_team)
            return {
                "p_home": float(result.home_win),
                "p_draw": float(result.draw),
                "p_away": float(result.away_win),
            }
        except Exception as exc:
            raise ValueError(f"Model prediction failed: {exc}") from exc
