"""Logique de filtrage combiné multi-critères."""

import numpy as np
import pandas as pd


def apply_filters(df: pd.DataFrame, filtres: dict, config: dict, horizon: int) -> pd.DataFrame:
    """Applique les filtres combinés (intersection) sur le DataFrame.

    Utilise un masque booléen unique au lieu de copies successives.

    Args:
        df: DataFrame scoring complet
        filtres: dict avec clés optionnelles: materiaux, score_min, age_min, age_max, diametre_min, diametre_max
        config: configuration app
        horizon: horizon actif (1, 3 ou 5)

    Returns:
        DataFrame filtré (vue, pas copie)
    """
    col_map = config["column_mapping"]
    score_col = f"score_h{horizon}"
    mask = np.ones(len(df), dtype=bool)

    # Filtre matériaux
    materiaux = filtres.get("materiaux", [])
    if materiaux:
        mask &= df[col_map["famille_materiau"]].isin(materiaux).values

    # Filtre score min
    score_min = filtres.get("score_min")
    if score_min is not None and score_min > 0:
        mask &= (df[score_col] >= score_min).values

    # Filtre âge
    age_min = filtres.get("age_min")
    age_max = filtres.get("age_max")
    if age_min is not None:
        mask &= (df[col_map["age"]] >= age_min).values
    if age_max is not None:
        mask &= (df[col_map["age"]] <= age_max).values

    # Filtre diamètre
    diametre_min = filtres.get("diametre_min")
    diametre_max = filtres.get("diametre_max")
    if diametre_min is not None:
        mask &= (df[col_map["diametre"]] >= diametre_min).values
    if diametre_max is not None:
        mask &= (df[col_map["diametre"]] <= diametre_max).values

    return df[mask]
