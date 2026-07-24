"""Note patrimoniale 1–5 : Score de risque (Probabilité × Conséquence) biné par quantiles.

5 = priorité maximale de renouvellement. Le binning par quantiles (plutôt que
par seuils absolus) garantit une distribution stable des classes quel que soit
le niveau moyen de risque du réseau. Les branchements sont plafonnés (gérés
séparément par le gestionnaire, ils ne peuvent pas être « critiques » dans la
priorisation patrimoniale).
"""

import pandas as pd

from domain.factory import build_consequence_calculator
from domain.models import compute_typologie


def compute_note(proba: pd.Series, consequence: pd.Series, config: dict) -> pd.Series:
    """Note 1–5 = P × C binée par les quantiles de config['note_patrimoniale']."""
    p = pd.to_numeric(proba, errors="coerce").fillna(0)
    c = pd.to_numeric(consequence, errors="coerce").fillna(0)
    risk = p * c
    qs = config.get("note_patrimoniale", {}).get("quantiles", [0.50, 0.75, 0.90, 0.97])
    edges = [risk.quantile(q) for q in qs]
    note = pd.Series(1, index=risk.index, dtype=int)
    for e in edges:
        note = note + (risk > e).astype(int)
    return note  # 1..5


def compute_notes(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Pipeline domaine complet : typologie → conséquence → notes 1–5 par horizon.

    Requiert des colonnes `score_h*` (probabilités calibrées du modèle ML).
    Pur : renvoie une copie enrichie (typologie, consequence, note_h*).
    """
    df = df.copy()
    df["typologie"] = compute_typologie(df, config)
    calculator = build_consequence_calculator(config)
    df["consequence"] = calculator.compute(df, config)

    for h in ("h1", "h3", "h5"):
        if f"score_{h}" in df.columns:
            df[f"note_{h}"] = compute_note(df[f"score_{h}"], df["consequence"], config)

    note_cap = config.get("priorisation", {}).get("note_max_branchement")
    if note_cap:
        mask_br = df["typologie"] == "branchement"
        for h in ("h1", "h3", "h5"):
            col = f"note_{h}"
            if col in df.columns:
                df.loc[mask_br, col] = df.loc[mask_br, col].clip(upper=int(note_cap))
    return df
