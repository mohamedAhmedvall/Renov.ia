"""Feature engineering — construit la matrice X pour une année d'observation donnée.

Principe anti-fuite central (identique au produit) : pour une année
d'observation N, les features ne regardent que le passé (< N) et la cible
compte les casses de [N, N+horizon). Les statistiques apprises (encodage du
matériau) sont ajustées sur le train uniquement et transmises au test via
`fit_state`, jamais recalculées sur le test.
"""

from pathlib import Path

import pandas as pd


def load_sources(data_dir: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge le patrimoine et l'historique de casses synthétiques."""
    data_dir = Path(data_dir)
    troncons = pd.read_csv(data_dir / "troncons.csv")
    casses = pd.read_csv(data_dir / "casses.csv")
    return troncons, casses


def build_features(
    troncons: pd.DataFrame,
    casses: pd.DataFrame,
    observation_year: int,
    horizon: int,
    fit_state: dict | None = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, dict]:
    """Construit (X, y, exposition, fit_state) pour une année d'observation.

    - X : âge, diamètre, encodage matériau (taux de casse historique du
      matériau, appris sur le train), casses passées du tronçon
    - y : nombre de casses dans [observation_year, observation_year + horizon)
    - exposition : longueur_km × horizon — offset du modèle de comptage
    - fit_state : état ajusté sur le train (None → fit ; fourni → transform)
    """
    df = troncons.copy()
    df["age"] = observation_year - df["annee_pose"]
    df["longueur_km"] = df["longueur"] / 1000.0

    passe = casses[casses["annee"] < observation_year]
    casses_passees = passe.groupby("id_troncon").size()
    df["nb_casses_passees"] = df["id"].map(casses_passees).fillna(0).astype(int)
    df["taux_casses_passe"] = df["nb_casses_passees"] / df["longueur_km"].clip(lower=0.01)

    if fit_state is None:
        # Encodage du matériau appris sur CE périmètre (le train) : taux de
        # casse historique par matériau, lissé vers la moyenne globale (m=20).
        expo_hist = df.groupby("materiau")["longueur_km"].sum()
        casses_mat = (
            passe.merge(df[["id", "materiau"]], left_on="id_troncon", right_on="id")
            .groupby("materiau").size()
        )
        global_rate = float(len(passe)) / float(df["longueur_km"].sum()) if len(df) else 0.0
        m = 20.0
        te = ((casses_mat.reindex(expo_hist.index).fillna(0) + m * global_rate)
              / (expo_hist + m)).to_dict()
        fit_state = {"te_materiau": te, "te_default": global_rate}

    df["te_materiau"] = df["materiau"].map(fit_state["te_materiau"]).fillna(fit_state["te_default"])

    fenetre = casses[
        (casses["annee"] >= observation_year) & (casses["annee"] < observation_year + horizon)
    ]
    y = df["id"].map(fenetre.groupby("id_troncon").size()).fillna(0).astype(int)

    features = ["age", "diametre", "te_materiau", "nb_casses_passees", "taux_casses_passe"]
    X = df[features].astype(float)
    exposition = df["longueur_km"] * horizon
    return X, y, exposition, fit_state
