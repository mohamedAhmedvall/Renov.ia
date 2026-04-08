"""Moteur d'optimisation — sélection greedy par ratio risque/coût.

Pourquoi pas CP-SAT : sur 180 000 tronçons, le knapsack est trop grand pour
solver exact en quelques secondes. Le greedy par ratio (score × longueur / coût)
est l'approximation classique du knapsack et donne un résultat à <1% de l'optimal
sur des instances de cette taille — instantané et déterministe.

KPI 'fuites évitées' :
  Les scores V9 sont calibrés (isotonic) → vraies probabilités.
  Donc sum(score_h{horizon} des tronçons sélectionnés) = espérance directe
  du nombre de fuites évitées sur l'horizon. Pas besoin de coefficient magique.
"""

import numpy as np
import pandas as pd


def optimize_renewal(df: pd.DataFrame, config: dict, params: dict) -> dict:
    col_map = config["column_mapping"]
    horizon = params.get("horizon", 3)
    budget = params.get("budget", 500_000)
    mat_remplacement = params.get("materiau_remplacement", "fonte_ductile")
    type_chantier = params.get("type_chantier", "urbain_standard")
    troncons_forces = {str(t) for t in params.get("troncons_forces", set())}
    troncons_exclus = {str(t) for t in params.get("troncons_exclus", set())}
    contrainte_1pct = params.get("contrainte_1pct", False)

    score_col = f"score_h{horizon}"
    id_col = col_map["id_troncon"]

    if score_col not in df.columns:
        return _fail(f"Colonne {score_col} absente du scoring.")

    # ───────────────────────────────────────────────────
    # 1. Préparation du dataset (longueurs depuis le scoring ou ref)
    # ───────────────────────────────────────────────────
    df_referentiel = params.get("df_referentiel")
    cols_needed = [id_col, score_col]
    if col_map["diametre"] in df.columns:
        cols_needed.append(col_map["diametre"])
    if col_map["age"] in df.columns:
        cols_needed.append(col_map["age"])

    df_opt = df[cols_needed].dropna(subset=[score_col]).copy()

    if "LONGUEUR" in df.columns:
        df_opt["longueur_ml"] = pd.to_numeric(
            df["LONGUEUR"].astype(str).str.replace(",", "."), errors="coerce"
        ).fillna(50.0)
    elif df_referentiel is not None and "LONGUEUR" in df_referentiel.columns:
        df_opt = df_opt.merge(df_referentiel[[id_col, "LONGUEUR"]], on=id_col, how="left")
        df_opt["longueur_ml"] = pd.to_numeric(
            df_opt["LONGUEUR"].astype(str).str.replace(",", "."), errors="coerce"
        ).fillna(50.0)
    else:
        df_opt["longueur_ml"] = 50.0

    df_opt[id_col] = df_opt[id_col].astype(str).map(lambda s: s[:-2] if s.endswith(".0") else s)
    df_opt = df_opt.reset_index(drop=True)

    # ───────────────────────────────────────────────────
    # 2. Calcul du coût unitaire par tronçon
    # ───────────────────────────────────────────────────
    cout_ml_chantier = config.get("couts_remplacement", {}).get(type_chantier, 300)
    majorant = (
        config.get("materiaux_remplacement", {})
              .get(mat_remplacement, {})
              .get("cout_majorant", 1.0)
    )
    cout_ml_effectif = cout_ml_chantier * majorant

    df_opt["cout"] = df_opt["longueur_ml"] * cout_ml_effectif
    df_opt["risque"] = df_opt[score_col] * df_opt["longueur_ml"]  # impact = proba × linéaire
    df_opt["ratio"] = df_opt["risque"] / df_opt["cout"].clip(lower=1.0)

    # ───────────────────────────────────────────────────
    # 3. Forçages : ces tronçons sont sélectionnés d'office
    # ───────────────────────────────────────────────────
    df_opt["selected"] = False
    if troncons_forces:
        mask_force = df_opt[id_col].isin(troncons_forces)
        df_opt.loc[mask_force, "selected"] = True

    # ───────────────────────────────────────────────────
    # 4. Exclusions
    # ───────────────────────────────────────────────────
    if troncons_exclus:
        df_opt = df_opt[~df_opt[id_col].isin(troncons_exclus)].reset_index(drop=True)

    # Vérification budget des forcés
    cout_forces = df_opt.loc[df_opt["selected"], "cout"].sum()
    if cout_forces > budget:
        return _fail(
            f"Les tronçons forcés coûtent {cout_forces:,.0f} € > budget {budget:,.0f} €. "
            "Augmentez le budget ou retirez des forçages."
        )

    # ───────────────────────────────────────────────────
    # 5. Greedy par ratio risque/coût sur le reste
    # ───────────────────────────────────────────────────
    budget_restant = budget - cout_forces
    df_candidats = df_opt[~df_opt["selected"]].sort_values("ratio", ascending=False)

    cumul_cout = df_candidats["cout"].cumsum()
    mask_take = cumul_cout <= budget_restant
    df_opt.loc[df_candidats.index[mask_take], "selected"] = True

    # Variante Best-fit : si on a encore du budget et qu'on peut caser un tronçon
    # plus petit en ratio mais qui rentre, on l'ajoute (améliore légèrement le résultat)
    cout_actuel = df_opt.loc[df_opt["selected"], "cout"].sum()
    reste = budget - cout_actuel
    if reste > 0:
        non_pris = df_opt[~df_opt["selected"]].sort_values("ratio", ascending=False)
        for idx in non_pris.index:
            c = df_opt.at[idx, "cout"]
            if c <= reste:
                df_opt.at[idx, "selected"] = True
                reste -= c
                if reste < df_opt["cout"].min():
                    break

    df_selected = df_opt[df_opt["selected"]].copy()

    # ───────────────────────────────────────────────────
    # 6. Contrainte 1% du linéaire (vérifiée a posteriori)
    # ───────────────────────────────────────────────────
    km_total_reseau = config.get("km_total_reseau", 100)
    seuil_1pct_m = km_total_reseau * 1000 * 0.01
    km_selected = df_selected["longueur_ml"].sum()

    if contrainte_1pct and km_selected < seuil_1pct_m:
        # Tenter d'ajouter par longueur décroissante (au lieu de ratio)
        deja = set(df_selected[id_col])
        candidats_long = df_opt[~df_opt[id_col].isin(deja)].sort_values("longueur_ml", ascending=False)
        for idx in candidats_long.index:
            if cout_actuel + df_opt.at[idx, "cout"] > budget:
                continue
            df_opt.at[idx, "selected"] = True
            cout_actuel += df_opt.at[idx, "cout"]
            km_selected += df_opt.at[idx, "longueur_ml"]
            if km_selected >= seuil_1pct_m:
                break
        df_selected = df_opt[df_opt["selected"]].copy()
        if km_selected < seuil_1pct_m:
            return _fail(
                f"Contrainte « 1 % du réseau » inatteignable avec ce budget "
                f"({km_selected/1000:.2f} km / {seuil_1pct_m/1000:.2f} km requis). "
                "Augmentez le budget ou décochez l'option."
            )

    # ───────────────────────────────────────────────────
    # 7. Sortie + KPIs
    # ───────────────────────────────────────────────────
    df_selected = df_selected.sort_values(score_col, ascending=False).reset_index(drop=True)
    df_selected["cout_unitaire"] = df_selected["cout"]
    df_selected["priorite"] = range(1, len(df_selected) + 1)

    if df_selected.empty:
        return _fail("Aucun tronçon sélectionné — budget trop faible ?")

    budget_utilise = float(df_selected["cout"].sum())
    km_renouvel = float(df_selected["longueur_ml"].sum() / 1000)

    # Espérance de fuites évitées = somme directe des probas calibrées
    fuites_evitees = float(df_selected[score_col].sum())

    # Risque éliminé en % du risque total du réseau
    risque_total_reseau = float((df_opt[score_col] * df_opt["longueur_ml"]).sum())
    risque_elimine = float(df_selected["risque"].sum())
    risque_pct = (risque_elimine / max(risque_total_reseau, 1e-9)) * 100

    kpis = {
        "budget_utilise": budget_utilise,
        "budget_pct": budget_utilise / budget * 100 if budget > 0 else 0,
        "km_renouveles": km_renouvel,
        "nb_troncons": len(df_selected),
        "risque_elimine_pct": risque_pct,
        "fuites_evitees": fuites_evitees,
        "cout_par_fuite": budget_utilise / max(fuites_evitees, 0.01),
        "cout_ml_effectif": cout_ml_effectif,
    }

    return {
        "success": True,
        "message": f"Plan calculé en greedy ({len(df_selected):,} tronçons).".replace(",", " "),
        "troncons_selectionnes": df_selected,
        "kpis": kpis,
    }


def _fail(msg: str) -> dict:
    return {
        "success": False,
        "message": msg,
        "troncons_selectionnes": pd.DataFrame(),
        "kpis": {},
    }
