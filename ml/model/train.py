"""Modèle de comptage : XGBoost Poisson + offset d'exposition, score calibré.

Choix de modélisation (identiques au produit) :
- **Poisson + offset log(longueur_km × horizon)** : le modèle apprend un TAUX
  de casse par km et par an, pas une probabilité brute — sinon la longueur du
  tronçon (qui mécaniquement augmente le nombre de casses observées) polluerait
  les features et biaiserait le classement.
- **Probabilité d'au moins une casse** : P = 1 − exp(−μ) où μ est le comptage
  attendu sur l'horizon.
- **Calibration ajustée out-of-fold** : les scores deviennent de vraies
  probabilités (une proba de 0,2 ⇒ ~20 % de casse observée), condition
  nécessaire pour que l'optimiseur puisse sommer des « casses évitées ».

Choix de la méthode de calibration
----------------------------------
La calibration isotonique est la référence, mais sa résolution est gouvernée
par le nombre d'ÉVÉNEMENTS (tronçons ayant cassé), pas par le nombre de lignes.
L'algorithme PAV fusionne les points en blocs constants : sous quelques
centaines de casses observées, il ne reste qu'une poignée de paliers, et tous
les tronçons d'un même palier reçoivent la probabilité identique. Le niveau
reste juste, mais l'ORDRE disparaît — or c'est l'ordre qui pilote la
priorisation. Sur ce jeu (≈130 casses dans la fenêtre d'entraînement), on
tombait à 20 valeurs distinctes pour 2 180 tronçons, dont 105 ex æquo en tête.

Sous le seuil, on bascule donc sur une calibration logistique (Platt), lisse et
strictement monotone : elle préserve intégralement le classement du modèle.
C'est la recommandation classique en régime de faible effectif
(Niculescu-Mizil & Caruana, 2005). Au-dessus du seuil, l'isotonique reprend la
main : plus souple, elle épouse mieux une courbe de fiabilité non logistique.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

# En dessous de ce nombre de casses observées, l'isotonique dégénère en escalier.
MIN_EVENEMENTS_ISOTONIQUE = 500


def _logit(p: np.ndarray) -> np.ndarray:
    q = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(q / (1 - q))


class PlattCalibrator:
    """Calibration logistique : P_calibrée = σ(a · logit(P_brute) + b).

    Même interface que `IsotonicRegression` (`fit`, `predict`) pour rester
    interchangeable avec elle dans le pipeline.
    """

    def __init__(self) -> None:
        self.lr = LogisticRegression(solver="lbfgs")

    def fit(self, p_brut: np.ndarray, y: np.ndarray) -> "PlattCalibrator":
        self.lr.fit(_logit(np.asarray(p_brut)).reshape(-1, 1), np.asarray(y))
        return self

    def predict(self, p_brut: np.ndarray) -> np.ndarray:
        proba = self.lr.predict_proba(_logit(np.asarray(p_brut)).reshape(-1, 1))
        return np.asarray(proba[:, 1])


def train_poisson_model(
    X: pd.DataFrame,
    y: pd.Series,
    exposition: pd.Series,
    n_estimators: int = 200,
    seed: int = 42,
) -> dict:
    """Entraîne le booster Poisson puis calibre en out-of-fold.

    Renvoie un dict {booster, calibrator, calibration} — le « modèle » complet.
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
    cible = (y > 0).astype(int).to_numpy()

    calibrator: IsotonicRegression | PlattCalibrator
    if int(cible.sum()) >= MIN_EVENEMENTS_ISOTONIQUE:
        calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        nom = "isotonique"
    else:
        calibrator = PlattCalibrator()
        nom = "logistique (Platt)"
    calibrator.fit(p_brut, cible)

    booster = xgb.XGBRegressor(**params)
    booster.fit(X, y, base_margin=offset)
    return {"booster": booster, "calibrator": calibrator, "calibration": nom}


def predict_proba_horizon(model: dict, X: pd.DataFrame, exposition: pd.Series) -> np.ndarray:
    """Probabilité calibrée d'au moins une casse sur l'horizon d'exposition."""
    offset = np.log(exposition.clip(lower=1e-6))
    mu = model["booster"].predict(X, base_margin=offset)
    p_brut = 1.0 - np.exp(-np.clip(mu, 0, None))
    return np.asarray(model["calibrator"].predict(p_brut))
