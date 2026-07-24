"""Protocole de backtesting temporel (chap. 9 du mémoire).

On se place à une année passée N (comme si on y était : features < N,
encodages fit sur < N), on prédit [N, N+horizon), puis on compare aux casses
réellement « survenues » — ici simulées. Répété sur des fenêtres glissantes,
c'est la seule estimation honnête de la performance future : un simple split
aléatoire mélangerait passé et futur et surestimerait le modèle.

Métrique métier : **capture linéaire @ 20 %** — part des casses futures
concentrée dans les 20 % du LINÉAIRE (km, pas nombre de tronçons) les mieux
classés. C'est la métrique décisionnelle : « si je renouvelle les 20 % de
réseau les plus risqués selon le modèle, quelle part des casses ai-je évitée ? »
"""

import numpy as np
import pandas as pd

from ml.features import build_features
from ml.model import predict_proba_horizon, train_poisson_model


def capture_lineaire_at(scores: np.ndarray, y: pd.Series, longueur_km: pd.Series, pct: float = 0.20) -> float:
    """Part des casses captée par les tronçons les mieux classés couvrant `pct` du linéaire."""
    ordre = np.argsort(-scores)
    km_cum = longueur_km.to_numpy()[ordre].cumsum()
    seuil_km = pct * longueur_km.sum()
    dans_budget = km_cum <= seuil_km
    casses_totales = float(y.sum())
    if casses_totales == 0:
        return 0.0
    return float(y.to_numpy()[ordre][dans_budget].sum() / casses_totales)


def backtest_temporel(
    troncons: pd.DataFrame,
    casses: pd.DataFrame,
    fenetres: list[int],
    horizon: int = 3,
    n_estimators: int = 120,
) -> pd.DataFrame:
    """Pour chaque année d'observation N : train sur < N, prédit [N, N+h), mesure la capture.

    Le train utilise la fenêtre précédente (N−horizon) pour disposer d'une
    cible complète sans empiéter sur la fenêtre de test.
    """
    lignes = []
    for annee_obs in fenetres:
        annee_train = annee_obs - horizon
        X_tr, y_tr, exp_tr, fit_state = build_features(troncons, casses, annee_train, horizon)
        model = train_poisson_model(X_tr, y_tr, exp_tr, n_estimators=n_estimators)

        X_te, y_te, exp_te, _ = build_features(troncons, casses, annee_obs, horizon, fit_state)
        p = predict_proba_horizon(model, X_te, exp_te)
        lignes.append(
            {
                "annee_observation": annee_obs,
                "horizon": horizon,
                "casses_fenetre": int(y_te.sum()),
                "capture_lineaire_20pct": round(
                    capture_lineaire_at(p, y_te, troncons["longueur"] / 1000.0), 3
                ),
                "part_lineaire_aleatoire": 0.20,  # référence : un tirage aléatoire capte ~20 %
            }
        )
    return pd.DataFrame(lignes)
