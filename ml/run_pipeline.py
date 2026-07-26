"""Orchestrateur du pipeline ML de démonstration.

Enchaîne, POUR CHAQUE VILLE : features (split temporel) → modèle Poisson
calibré → scores de production aux horizons 1/3/5 ans → importance SHAP →
backtest glissant. Écrit `data/synthetic/<ville>/scores.csv` (lu par l'API) et
`ml/output/<ville>/*.csv`.

Un modèle est entraîné par ville : les patrimoines ont des âges et des mix
matériaux différents, et un modèle unique masquerait ces écarts. C'est aussi ce
que fait le produit, où chaque collectivité a son propre historique de casses.

Usage :
    python ml/run_pipeline.py                # les 4 villes
    python ml/run_pipeline.py --ville lyon   # une seule
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # exécutable sans installation

from ml.backtest import backtest_temporel  # noqa: E402
from ml.explain import shap_importance  # noqa: E402
from ml.features import build_features, load_sources  # noqa: E402
from ml.model import predict_proba_horizon, train_poisson_model  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "synthetic"
OUT_ROOT = ROOT / "ml" / "output"
ANNEE_TRAIN, ANNEE_REF = 2018, 2024  # train observe 2018 (cible complète), score en 2024


def charger_villes() -> dict:
    return json.loads((DATA_ROOT / "villes.json").read_text(encoding="utf-8"))["villes"]


def traiter_ville(cle: str, nom: str) -> None:
    data_dir, out_dir = DATA_ROOT / cle, OUT_ROOT / cle
    out_dir.mkdir(parents=True, exist_ok=True)
    troncons, casses = load_sources(data_dir)

    # 1) Entraînement avec split temporel strict (features < 2018, cible 2018-2021)
    X_tr, y_tr, exp_tr, fit_state = build_features(troncons, casses, ANNEE_TRAIN, horizon=3)
    model = train_poisson_model(X_tr, y_tr, exp_tr)

    # 2) Scoring de production à l'année de référence, horizons 1/3/5
    scores = pd.DataFrame({"id_troncon": troncons["id"]})
    for h in (1, 3, 5):
        X, _, exp, _ = build_features(troncons, casses, ANNEE_REF, horizon=h, fit_state=fit_state)
        scores[f"score_h{h}"] = predict_proba_horizon(model, X, exp).round(5)
    scores.to_csv(data_dir / "scores.csv", index=False)

    # 3) Explicabilité globale
    imp = shap_importance(model, X_tr)
    imp.to_csv(out_dir / "shap_importance.csv", index=False)

    # 4) Backtest temporel glissant (protocole chap. 9)
    bt = backtest_temporel(troncons, casses, fenetres=[2014, 2017, 2020], horizon=3)
    bt.to_csv(out_dir / "backtesting.csv", index=False)

    distinctes = scores["score_h3"].nunique()
    print(f"\n=== {nom} ({len(scores)} tronçons) ===")
    print(
        f"Calibration : {model['calibration']} — "
        f"{distinctes} probabilités distinctes à 3 ans (ex æquo = priorisation arbitraire)"
    )
    print("Importance SHAP :", ", ".join(f"{r.feature}={r.importance:.3f}" for r in imp.itertuples()))
    print(bt.to_string(index=False))


def main() -> None:
    villes = charger_villes()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ville", choices=sorted(villes), help="ne traiter qu'une ville")
    args = parser.parse_args()

    for cle in [args.ville] if args.ville else list(villes):
        traiter_ville(cle, villes[cle]["nom"])


if __name__ == "__main__":
    main()
