"""Orchestrateur du pipeline ML de démonstration.

Enchaîne : features (split temporel) → modèle Poisson calibré → scores de
production aux horizons 1/3/5 ans → importance SHAP → backtest glissant.
Écrit `data/synthetic/scores.csv` (lu par l'API) et `ml/output/*.csv`.

Usage : python ml/run_pipeline.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # exécutable sans installation

from ml.backtest import backtest_temporel  # noqa: E402
from ml.explain import shap_importance  # noqa: E402
from ml.features import build_features, load_sources  # noqa: E402
from ml.model import predict_proba_horizon, train_poisson_model  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "synthetic"
OUT_DIR = ROOT / "ml" / "output"
ANNEE_TRAIN, ANNEE_REF = 2018, 2024  # train observe 2018 (cible complète), score en 2024


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    troncons, casses = load_sources(DATA_DIR)

    # 1) Entraînement avec split temporel strict (features < 2018, cible 2018-2021)
    X_tr, y_tr, exp_tr, fit_state = build_features(troncons, casses, ANNEE_TRAIN, horizon=3)
    model = train_poisson_model(X_tr, y_tr, exp_tr)

    # 2) Scoring de production à l'année de référence, horizons 1/3/5
    scores = pd.DataFrame({"id_troncon": troncons["id"]})
    for h in (1, 3, 5):
        X, _, exp, _ = build_features(troncons, casses, ANNEE_REF, horizon=h, fit_state=fit_state)
        scores[f"score_h{h}"] = predict_proba_horizon(model, X, exp).round(5)
    scores.to_csv(DATA_DIR / "scores.csv", index=False)

    # 3) Explicabilité globale
    imp = shap_importance(model, X_tr)
    imp.to_csv(OUT_DIR / "shap_importance.csv", index=False)

    # 4) Backtest temporel glissant (protocole chap. 9)
    bt = backtest_temporel(troncons, casses, fenetres=[2014, 2017, 2020], horizon=3)
    bt.to_csv(OUT_DIR / "backtesting.csv", index=False)

    print(f"Scores écrits : {DATA_DIR / 'scores.csv'} ({len(scores)} tronçons)")
    print("Importance SHAP :", ", ".join(f"{r.feature}={r.importance:.3f}" for r in imp.itertuples()))
    print(bt.to_string(index=False))


if __name__ == "__main__":
    main()
