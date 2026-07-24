"""Optimisation du renouvellement sous contrainte de budget (knapsack glouton).

Pourquoi un greedy et pas un solveur exact (CP-SAT/PLNE) : sur un réseau réel
(~180 000 tronçons), le knapsack exact est impraticable dans un temps
interactif ; le tri par ratio (risque évité / coût) est l'approximation
classique du knapsack, avec une borne de qualité connue, et il est
DÉTERMINISTE (tri stable avec départage explicite) — indispensable pour la
reproductibilité des scénarios présentés au client.

Formulation Poisson (identique au produit) :
- le score calibré P(≥1 casse) est reconverti en comptage attendu
  μ = −ln(1 − P) — additif, contrairement aux probabilités ;
- renouveler un tronçon ne supprime pas tout le risque : un tuyau neuf garde
  un hasard résiduel (hasard_neuf_km_an), le bénéfice est Δμ = μ − μ_neuf ;
- les « casses évitées » attendues d'un scénario = Σ Δμ des tronçons retenus.
"""

import numpy as np
import pandas as pd

DEFAULT_PARAMS: dict = {
    "cout_ml_base": 300.0,           # €/ml de base
    "facteur_materiau": {"Fonte": 1.15, "Acier": 1.2, "Ciment": 1.3},  # majorations pose
    "hasard_neuf_km_an": 0.02,       # casses/km/an résiduelles d'un tuyau neuf
    "horizon": 3,
}


def _cout_remplacement(df: pd.DataFrame, params: dict) -> pd.Series:
    """Coût = €/ml de base × majoration matériau × facteur diamètre × longueur."""
    base = float(params.get("cout_ml_base", 300.0))
    fac_mat = df["famille_materiau"].map(params.get("facteur_materiau", {})).fillna(1.0)
    fac_diam = (df["diametre_mm"] / 150.0).clip(lower=0.7, upper=3.0)
    return base * fac_mat * fac_diam * df["longueur_m"]


def optimize_renewal(df: pd.DataFrame, budget: float, params: dict | None = None) -> dict:
    """Sélectionne les tronçons à renouveler sous `budget` (greedy ratio bénéfice/coût).

    `df` doit contenir : id_troncon, famille_materiau, diametre_mm, longueur_m,
    consequence [0,1] et score_h{horizon} (probabilité calibrée).
    Renvoie le scénario : sélection, coût, casses évitées (±IC95), linéaire.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    horizon = int(p["horizon"])
    score_col = f"score_h{horizon}"
    if score_col not in df.columns:
        raise ValueError(f"Colonne {score_col} absente : lancer le pipeline ML d'abord.")

    df = df.copy()
    proba = pd.to_numeric(df[score_col], errors="coerce").fillna(0).clip(0, 0.999999)
    mu = -np.log(1.0 - proba)                                   # comptage attendu sur l'horizon
    mu_neuf = p["hasard_neuf_km_an"] * (df["longueur_m"] / 1000.0) * horizon
    delta_mu = (mu - mu_neuf).clip(lower=0)                     # bénéfice : casses évitées
    benefice = delta_mu * df.get("consequence", pd.Series(1.0, index=df.index))
    cout = _cout_remplacement(df, p)

    ratio = benefice / cout.replace(0, np.nan)
    # Tri déterministe : ratio décroissant, départage par id (reproductibilité).
    ordre = (
        pd.DataFrame({"ratio": ratio, "id": df["id_troncon"]})
        .sort_values(["ratio", "id"], ascending=[False, True], kind="mergesort")
        .index
    )

    selection: list[int] = []
    cout_total = 0.0
    for i in ordre:
        c = float(cout.loc[i])
        if np.isnan(ratio.loc[i]) or benefice.loc[i] <= 0:
            continue
        if cout_total + c <= budget:
            selection.append(i)
            cout_total += c

    sel = df.loc[selection]
    casses_evitees = float(delta_mu.loc[selection].sum())
    # IC 95 % d'une somme de Poisson : ±1.96 √(Σμ)
    ic95 = 1.96 * float(np.sqrt(delta_mu.loc[selection].sum()))
    return {
        "horizon": horizon,
        "budget": budget,
        "cout_total": round(cout_total, 0),
        "nb_troncons": len(sel),
        "lineaire_km": round(float(sel["longueur_m"].sum()) / 1000.0, 2),
        "casses_evitees": round(casses_evitees, 2),
        "casses_evitees_ic95": round(ic95, 2),
        "ids": sel["id_troncon"].tolist(),
    }
