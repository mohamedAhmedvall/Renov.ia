"""
V9 — Préparation des données pour la prédiction de fuites/casses.

Différences clés vs V8 (corrections de l'audit) :
  - Aléa argile (RGA) intégré comme feature catégorielle ordinale
  - Imputeurs FIT sur train uniquement (passés explicitement)
  - Flag age_imputed conservé
  - Aucune fuite train→test : tout transformer prend `fit_state` en argument

API :
  load_raw(data_dir)                       → cana, fuites, argile
  build_features(cana, fuites, argile,
                 observation_year, horizon,
                 fit_state=None)            → df, X, y, fit_state
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path

ANNEE_REF = 2024

FAMILLE_MAP = {
    "FT": "Fonte", "FTG": "Fonte_grise", "FTVI": "Fonte", "FTBLU": "Fonte",
    "FTTT": "Fonte", "FTTTVI": "Fonte",
    "PVC": "Plastique", "PEHD": "Plastique", "PEBD": "Plastique", "POLY": "Plastique",
    "A.C": "Amiante_ciment", "AC": "Amiante_ciment",
    "ACIE": "Acier", "FER": "Acier", "GALV": "Acier", "INOX": "Acier", "AFCO": "Acier",
    "BTM": "Beton", "BA": "Beton", "CENT": "Beton",
}
ARGILE_ORD = {"nul": 0, "moyen": 1, "fort": 2}

FEATURE_COLS = [
    "age", "age_imputed",
    "DIAMETRE", "LONGUEUR",
    "decennie_pose",
    "nb_fuites_avant", "annees_depuis_derniere_fuite",
    "famille_enc",
    "alea_argile_ord",
]
FEATURE_NAMES = [
    "Age", "Age_imputed",
    "Diametre", "Longueur",
    "Decennie_pose",
    "Nb_fuites_historique", "Annees_depuis_derniere_fuite",
    "Famille_materiau_TE",
    "Alea_argile",
]


def load_raw(data_dir: Path):
    """Charge les 3 sources brutes et renvoie cana, fuites, argile."""
    cana = pd.read_csv(data_dir / "canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
    anomalies = pd.read_csv(data_dir / "historiqueanomalie.csv", low_memory=False)
    argile = pd.read_csv(data_dir / "troncons_alea_argile (1).csv")

    # --- Cana ---
    cana["POSE_dt"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")
    cana["ABANDON_dt"] = pd.to_datetime(cana["ABANDON"], format="mixed", dayfirst=True, errors="coerce")
    cana["annee_pose"] = cana["POSE_dt"].dt.year
    cana["annee_abandon"] = cana["ABANDON_dt"].dt.year

    cana["date_fiable"] = (
        cana["annee_pose"].notna()
        & (cana["annee_pose"] != 1900)
        & (cana["annee_pose"] <= ANNEE_REF)
    )

    cana["MATERIAU"] = cana["MATERIAU"].fillna("INCONNU")
    cana["famille_mat"] = cana["MATERIAU"].map(FAMILLE_MAP).fillna("Autre")
    cana.loc[cana["DIAMETRE"] == 0, "DIAMETRE"] = np.nan
    cana.loc[cana["LONGUEUR"] == 0, "LONGUEUR"] = np.nan

    # --- Fuites ---
    anomalies["annee_Anomalie"] = pd.to_numeric(anomalies["annee_Anomalie"], errors="coerce").astype("Int64")
    fuites = anomalies[
        anomalies["TYPE_ANOMALIE"].isin(["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE"])
        & (anomalies["OBJET_DEPOSE_OU_ABANDONNE"] != 1)
        & (anomalies["GID_OBJET"].isin(cana["OBJET"]))
        & (anomalies["annee_Anomalie"].notna())
        & (anomalies["annee_Anomalie"] <= ANNEE_REF)
    ].copy()

    # --- Argile ---
    argile["alea_argile_ord"] = argile["alea_argile"].map(ARGILE_ORD).astype("Int64")

    print(f"  Cana: {len(cana):,} | EN SERVICE: {(cana['STATUT_OBJET']=='EN SERVICE').sum():,}")
    print(f"  Fuites: {len(fuites):,} sur {fuites['GID_OBJET'].nunique():,} tronçons")
    print(f"  Argile: {len(argile):,} ({argile['alea_argile'].value_counts().to_dict()})")
    return cana, fuites, argile


def _compute_te(df, col, target, smoothing=10):
    gm = df[target].mean()
    agg = df.groupby(col)[target].agg(["mean", "count"])
    agg["te"] = (agg["count"] * agg["mean"] + smoothing * gm) / (agg["count"] + smoothing)
    out = agg["te"].to_dict()
    out["__global__"] = gm
    return out


def build_features(cana, fuites, argile, observation_year, horizon, fit_state=None):
    """
    Construit (X, y) à un instant d'observation donné.

    fit_state : None → mode FIT (calcule médianes/TE sur ce df). Renvoyé.
                dict → mode TRANSFORM (utilise les stats fournies, pas de fuite).

    Renvoie : df_meta, X (np.array), y (np.array), fit_state
    """
    # 1. Sélection des tronçons actifs au moment de l'observation
    actif = (
        (cana["STATUT_OBJET"] == "EN SERVICE")
        | ((cana["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"]))
           & (cana["annee_abandon"] >= observation_year))
    )
    df = cana.loc[actif].copy()

    # 2. Cible : ≥1 fuite dans [obs, obs+horizon)
    fut = fuites[
        (fuites["annee_Anomalie"] >= observation_year)
        & (fuites["annee_Anomalie"] < observation_year + horizon)
    ]
    df["y"] = df["OBJET"].isin(fut["GID_OBJET"]).astype(int)

    # 3. Age (uniquement avec dates fiables)
    df["age"] = observation_year - df["annee_pose"]
    df.loc[~df["date_fiable"], "age"] = np.nan
    df.loc[df["age"] < 0, "age"] = np.nan
    df["age_imputed"] = df["age"].isna().astype(int)
    df["decennie_pose"] = (df["annee_pose"] // 10) * 10

    # 4. Historique fuites AVANT observation (causalité respectée)
    past = fuites[fuites["annee_Anomalie"] < observation_year]
    hist = past.groupby("GID_OBJET").agg(
        nb_fuites_avant=("annee_Anomalie", "count"),
        derniere_fuite=("annee_Anomalie", "max"),
    ).reset_index()
    df = df.merge(hist, left_on="OBJET", right_on="GID_OBJET", how="left")
    df["nb_fuites_avant"] = df["nb_fuites_avant"].fillna(0).astype(int)
    df["annees_depuis_derniere_fuite"] = observation_year - df["derniere_fuite"]
    df["annees_depuis_derniere_fuite"] = df["annees_depuis_derniere_fuite"].fillna(999)

    # 5. Argile (jointure)
    df = df.merge(argile[["GID", "alea_argile_ord", "alea_argile"]],
                  left_on="OBJET", right_on="GID", how="left")
    df["alea_argile_ord"] = df["alea_argile_ord"].astype("float")  # NaN possible

    # 6. FIT vs TRANSFORM
    if fit_state is None:
        # Médianes globales (fallback) + par famille
        med_age_fam = df.groupby("famille_mat")["age"].median().to_dict()
        med_diam_fam = df.groupby("famille_mat")["DIAMETRE"].median().to_dict()
        med_long_global = df["LONGUEUR"].median()
        med_age_global = df["age"].median()
        med_diam_global = df["DIAMETRE"].median()
        med_dec_global = df["decennie_pose"].median()
        te_map = _compute_te(df, "famille_mat", "y", smoothing=10)
        fit_state = {
            "med_age_fam": med_age_fam, "med_age_global": med_age_global,
            "med_diam_fam": med_diam_fam, "med_diam_global": med_diam_global,
            "med_long_global": med_long_global, "med_dec_global": med_dec_global,
            "te_map": te_map,
        }

    # Imputations (transform)
    df["age"] = df.apply(
        lambda r: fit_state["med_age_fam"].get(r["famille_mat"], fit_state["med_age_global"])
        if pd.isna(r["age"]) else r["age"], axis=1)
    df["age"] = df["age"].fillna(fit_state["med_age_global"])
    df["DIAMETRE"] = df.apply(
        lambda r: fit_state["med_diam_fam"].get(r["famille_mat"], fit_state["med_diam_global"])
        if pd.isna(r["DIAMETRE"]) else r["DIAMETRE"], axis=1)
    df["DIAMETRE"] = df["DIAMETRE"].fillna(fit_state["med_diam_global"])
    df["LONGUEUR"] = df["LONGUEUR"].fillna(fit_state["med_long_global"])
    df["decennie_pose"] = df["decennie_pose"].fillna(fit_state["med_dec_global"])

    # TE famille (train-only mapping)
    tv = {k: v for k, v in fit_state["te_map"].items() if k != "__global__"}
    gm = fit_state["te_map"]["__global__"]
    df["famille_enc"] = df["famille_mat"].map(tv).fillna(gm)

    # Argile : NaN laissé (XGBoost gère nativement)
    X = df[FEATURE_COLS].values.astype(float)
    y = df["y"].values.astype(int)

    return df, X, y, fit_state
