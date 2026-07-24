"""Modèle du domaine : configuration par défaut et typologie des tronçons.

Aucune valeur métier n'est en dur dans les calculs : tout vit dans la
configuration (même philosophie que le `config.yaml` du produit).
"""

import pandas as pd

# Configuration par défaut de la matrice de risque (surchargeables par l'appelant).
DEFAULT_CONFIG: dict = {
    "column_mapping": {
        "diametre": "diametre_mm",
        "famille_materiau": "famille_materiau",
    },
    "typologie": {
        "seuil_branchement_plastique": 63,  # PE ≤ 63 mm → branchement
        "seuil_branchement_absolu": 50,     # ≤ 50 mm → branchement quel que soit le matériau
        "seuil_transport": 300,             # ≥ 300 mm → transport (feeder)
    },
    "consequence": {
        "poids": {"typologie": 0.6, "diametre": 0.4, "abonnes": 0.3},
        "typologie_score": {"transport": 1.0, "distribution": 0.6, "branchement": 0.2},
        "typologie_facteur": {"branchement": 0.25},  # branchements gérés à part : dé-pondérés
        "diametre_ref_mm": 300,
        "abonnes": {"ref_abonnes": 100, "poids_sensible": 3.0, "poids_tres_sensible": 6.0},
    },
    "note_patrimoniale": {"quantiles": [0.50, 0.75, 0.90, 0.97]},
    "priorisation": {"note_max_branchement": 3},
}


def compute_typologie(df: pd.DataFrame, config: dict) -> pd.Series:
    """Classe chaque tronçon : transport / distribution / branchement / indéterminé.

    Heuristique diamètre + famille de matériau, seuils dans config['typologie'].
    """
    col_map = config["column_mapping"]
    s = config.get("typologie", {})
    s_bp = s.get("seuil_branchement_plastique", 63)
    s_ba = s.get("seuil_branchement_absolu", 50)
    s_tr = s.get("seuil_transport", 300)
    diam = pd.to_numeric(df.get(col_map["diametre"]), errors="coerce")
    fam = df.get(col_map["famille_materiau"])
    typo = pd.Series("distribution", index=df.index)
    typo[diam >= s_tr] = "transport"
    is_plast = fam.eq("Plastique") if fam is not None else pd.Series(False, index=df.index)
    branch = ((diam <= s_bp) & is_plast) | (diam <= s_ba)
    typo[branch.fillna(False)] = "branchement"
    typo[diam.isna()] = "indetermine"
    return typo
