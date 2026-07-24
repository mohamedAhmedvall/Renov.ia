"""Modèle de comptage : XGBoost Poisson + offset d'exposition, calibration isotonique.

Choix de modélisation (identiques au produit) :
- **Poisson + offset log(longueur_km × horizon)** : le modèle apprend un TAUX
  de casse par km et par an, pas une probabilité brute — sinon la longueur du
  tronçon (qui mécaniquement augmente le nombre de casses observées) polluerait
  les features et biaiserait le classement.
- **Probabilité d'au moins une casse** : P = 1 − exp(−μ) où μ est le comptage
  attendu sur l'horizon.
- **Calibration isotonique** ajustée out-of-fold : les scores deviennent de
  vraies probabilités (une proba de 0,2 ⇒ ~20 % de casse observée), condition
  nécessaire pour que l'optimiseur puisse sommer des « fuites évitées ».
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import KFold


def train_poisson_model(
    X: pd.DataFrame,
    y: pd.Series,
    exposition: pd.Series,
    n_estimators: int = 200,
    seed: int = 42,
) -> dict:
    """Entraîne le booster Poisson puis calibre isotoniquement en out-of-fold.

    Renvoie un dict {booster, calibrator} — le « modèle » complet.
    """
    params = dict(
        objective="count:poisson",
        n_estimators=n_estimators,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=seed,
        base_score=1.0,
    )
    offset = np.log(exposition.clip(lower=1e-6))

    # Prédictions out-of-fold pour ajuster la calibration sans fuite.
    oof_mu = np.zeros(len(X))
    for tr_idx, va_idx in KFold(n_splits=3, shuffle=True, random_state=seed).split(X):
        m = xgb.XGBRegressor(**params)
        m.fit(X.iloc[tr_idx], y.iloc[tr_idx], base_margin=offset.iloc[tr_idx])
        oof_mu[va_idx] = m.predict(X.iloc[va_idx], base_margin=offset.iloc[va_idx])
    p_brut = 1.0 - np.exp(-np.clip(oof_mu, 0, None))
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    calibrator.fit(p_brut, (y > 0).astype(int))

    booster = xgb.XGBRegressor(**params)
    booster.fit(X, y, base_margin=offset)
    return {"booster": booster, "calibrator": calibrator}


def predict_proba_horizon(model: dict, X: pd.DataFrame, exposition: pd.Series) -> np.ndarray:
    """Probabilité calibrée d'au moins une casse sur l'horizon d'exposition."""
    offset = np.log(exposition.clip(lower=1e-6))
    mu = model["booster"].predict(X, base_margin=offset)
    p_brut = 1.0 - np.exp(-np.clip(mu, 0, None))
    return np.asarray(model["calibrator"].predict(p_brut))
