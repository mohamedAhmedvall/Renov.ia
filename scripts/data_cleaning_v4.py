"""
Module de nettoyage V4 — Corrections P0/P1/P2 de la revue adversariale.

Corrections vs V3:
  P0: Target encoding NON calculé ici (sera fait train-only dans le modèle)
  P0: Scoring utilise le mapping TE du train (pas recalculé)
  P1: Features anomalies réduites (nb_fuites seul, les autres inutiles)
  P2: DEPOSE exclu entièrement (pas gardé comme négatif faux)
  P2: age_imputed flag ajouté (17k tronçons avec date 1900)
  P2: ETAT Inconnu encodé séparément (pas 0 dans l'ordinal)
"""

import pandas as pd
import numpy as np

ANNEE_REF = 2024

# --- ETAT: 16 valeurs brutes → 4 catégories ---
ETAT_MAP = {
    "Bon": "Bon", "BON": "Bon", "bon": "Bon",
    "Moyen": "Moyen",
    "Vétuste": "Mauvais", "VETUSTE": "Mauvais",
    "Sature": "Mauvais", "SATURE": "Mauvais",
    "FUITES MULTIPLES": "Mauvais",
    "Inconnu": "Inconnu", "INCONNU": "Inconnu", "inconnu": "Inconnu",
    "SANS OBJET": "Inconnu", "0": "Inconnu", ".": "Inconnu",
}
# P2 fix : Inconnu = NaN pour l'ordinal (XGBoost gère les NaN nativement)
ETAT_ORDINAL = {"Bon": 1, "Moyen": 2, "Mauvais": 3}  # Inconnu → NaN

# --- MATERIAU → familles ---
FAMILLE_MAP = {
    "FT": "Fonte", "FTG": "Fonte_grise",
    "FTVI": "Fonte", "FTBLU": "Fonte", "FTTT": "Fonte", "FTTTVI": "Fonte",
    "PVC": "Plastique", "PEHD": "Plastique", "PEBD": "Plastique", "POLY": "Plastique",
    "A.C": "Amiante_ciment", "AC": "Amiante_ciment",
    "ACIE": "Acier", "FER": "Acier", "GALV": "Acier", "INOX": "Acier", "AFCO": "Acier",
    "BTM": "Beton", "BA": "Beton", "CENT": "Beton",
    "AUTRE": "Autre", "BIOR": "Autre", "PB": "Autre", "PRV": "Autre",
    "VP": "Autre", "COMP": "Autre", "GRES": "Autre", "CUIT": "Autre", "GALERIE": "Autre",
}


def load_and_clean_v4(data_dir):
    """
    Charge et nettoie. DEPOSE exclu entièrement.
    Cible = ABANDONNE (fin de vie) vs EN SERVICE.
    """
    cana = pd.read_csv(data_dir / "canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
    anomalies = pd.read_csv(data_dir / "historiqueanomalie.csv", low_memory=False)

    # P2: Garder uniquement EN SERVICE + ABANDONNE (DEPOSE exclu)
    cana = cana[cana["STATUT_OBJET"].isin(["EN SERVICE", "ABANDONNE"])].copy()

    # Dates
    cana["POSE_dt"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")
    cana["ABANDON_dt"] = pd.to_datetime(cana["ABANDON"], format="mixed", dayfirst=True, errors="coerce")
    cana["annee_pose"] = cana["POSE_dt"].dt.year
    cana["annee_abandon"] = cana["ABANDON_dt"].dt.year

    # Label
    cana["label"] = (cana["STATUT_OBJET"] == "ABANDONNE").astype(int)

    # Date fiable
    cana["date_fiable"] = True
    cana.loc[cana["annee_pose"] == 1900, "date_fiable"] = False
    cana.loc[cana["annee_pose"].isna(), "date_fiable"] = False
    cana.loc[cana["annee_pose"] > ANNEE_REF, "date_fiable"] = False

    # ETAT
    cana["etat_clean"] = cana["ETAT"].map(ETAT_MAP).fillna("Inconnu")
    # P2: Inconnu → NaN dans l'ordinal (XGBoost gère nativement)
    cana["etat_ord"] = cana["etat_clean"].map(ETAT_ORDINAL)  # Inconnu → NaN automatiquement

    # MATERIAU
    cana["MATERIAU"] = cana["MATERIAU"].fillna("INCONNU")
    cana["famille_mat"] = cana["MATERIAU"].map(FAMILLE_MAP).fillna("Autre")

    # DIAMETRE
    cana.loc[cana["DIAMETRE"] == 0, "DIAMETRE"] = np.nan

    # LONGUEUR
    cana.loc[cana["LONGUEUR"] == 0, "LONGUEUR"] = np.nan

    # Décennie
    cana["decennie_pose"] = (cana["annee_pose"] // 10) * 10

    # Anomalies
    anomalies["annee_Anomalie"] = anomalies["annee_Anomalie"].astype("Int64")
    gids_valides = set(cana["OBJET"].unique())
    anomalies = anomalies[anomalies["GID_OBJET"].isin(gids_valides)].copy()
    anomalies = anomalies[
        anomalies["annee_Anomalie"].isna() | (anomalies["annee_Anomalie"] <= ANNEE_REF)
    ].copy()
    anom_clean = anomalies[anomalies["OBJET_DEPOSE_OU_ABANDONNE"] != 1].copy()

    n_es = (cana["label"] == 0).sum()
    n_ab = (cana["label"] == 1).sum()
    print(f"  Données: {len(cana):,} tronçons | {n_es:,} EN SERVICE | {n_ab:,} ABANDONNE")
    print(f"  Anomalies: {len(anom_clean):,}")

    return cana, anom_clean


def build_features_v4(cana, anom_clean, cutoff_year=None, te_map=None):
    """
    Construit features + label.

    P0 fix: Target encoding via te_map externe (calculé sur train).
    Si te_map=None et cutoff_year fourni → retourne te_map à calculer côté appelant.
    Si te_map fourni → applique directement.

    Features (7 utiles, pas de bruit):
      - age, age_imputed (P2)
      - diametre, longueur
      - etat_ord (Inconnu=NaN, P2)
      - decennie_pose
      - famille_enc (TE externe, P0)
      - nb_fuites (seule feature anomalies utile)
    """
    if cutoff_year is not None:
        mask_exclu = (cana["label"] == 1) & (cana["annee_abandon"] < cutoff_year)
        df = cana[~mask_exclu].copy()

        df["y"] = (
            (df["label"] == 1)
            & (df["annee_abandon"] >= cutoff_year)
            & (df["annee_abandon"] <= ANNEE_REF)
        ).astype(int)

        df["age"] = cutoff_year - df["annee_pose"]
        df.loc[~df["date_fiable"], "age"] = np.nan
        df.loc[df["age"] < 0, "age"] = np.nan

        anom_period = anom_clean[
            anom_clean["annee_Anomalie"].notna()
            & (anom_clean["annee_Anomalie"] < cutoff_year)
        ]
        ref_year = cutoff_year
    else:
        df = cana.copy()
        df["y"] = df["label"]
        df["age"] = np.where(
            df["label"] == 1,
            df["annee_abandon"] - df["annee_pose"],
            ANNEE_REF - df["annee_pose"],
        )
        df.loc[~df["date_fiable"], "age"] = np.nan
        df.loc[df["age"] < 0, "age"] = np.nan
        anom_period = anom_clean.copy()
        ref_year = ANNEE_REF

    # P2: Flag age imputé AVANT imputation
    df["age_imputed"] = df["age"].isna().astype(int)

    # Imputation âge par médiane famille
    age_med = df.groupby("famille_mat")["age"].median()
    for fam in df["famille_mat"].unique():
        mask = (df["famille_mat"] == fam) & df["age"].isna()
        if mask.sum() > 0:
            df.loc[mask, "age"] = age_med.get(fam, df["age"].median())
    df["age"] = df["age"].fillna(df["age"].median())

    # Imputation DIAMETRE par médiane famille
    diam_med = df.groupby("famille_mat")["DIAMETRE"].median()
    for fam in df["famille_mat"].unique():
        mask = (df["famille_mat"] == fam) & df["DIAMETRE"].isna()
        if mask.sum() > 0:
            df.loc[mask, "DIAMETRE"] = diam_med.get(fam, df["DIAMETRE"].median())
    df["DIAMETRE"] = df["DIAMETRE"].fillna(df["DIAMETRE"].median())

    # Imputation LONGUEUR
    df["LONGUEUR"] = df["LONGUEUR"].fillna(df["LONGUEUR"].median())

    # Anomalies : uniquement nb_fuites (les autres features inutiles P1)
    anom_fuites = anom_period[
        anom_period["TYPE_ANOMALIE"].isin(["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE"])
    ]
    fuites_agg = anom_fuites.groupby("GID_OBJET").agg(
        nb_fuites=("TYPE_ANOMALIE", "count"),
    ).reset_index()

    df = df.merge(fuites_agg, left_on="OBJET", right_on="GID_OBJET", how="left")
    df["nb_fuites"] = df["nb_fuites"].fillna(0).astype(int)

    # P0: Target Encoding — externe
    if te_map is not None:
        # Appliquer le mapping fourni (train TE)
        global_mean_te = te_map.get("__global__", 0.05)
        df["famille_enc"] = df["famille_mat"].map(
            {k: v for k, v in te_map.items() if k != "__global__"}
        ).fillna(global_mean_te)
    else:
        # Pas de TE → mettre NaN (sera calculé par l'appelant)
        df["famille_enc"] = np.nan

    # Décennie
    df["decennie_pose"] = df["decennie_pose"].fillna(1970)

    # Features finales (8, pas 12)
    feature_cols = [
        "age", "age_imputed",
        "DIAMETRE", "LONGUEUR",
        "etat_ord",
        "decennie_pose",
        "famille_enc",
        "nb_fuites",
    ]
    feature_names = [
        "Age", "Age_imputed",
        "Diametre", "Longueur",
        "Etat",
        "Decennie_pose",
        "Famille_materiau",
        "Nb_fuites",
    ]

    return df, feature_cols, feature_names


def compute_target_encoding(df, col="famille_mat", target="y", smoothing=10):
    """
    Calcule le target encoding avec lissage bayésien (sur train uniquement).
    Retourne un dict {catégorie: valeur_encodée, "__global__": moyenne_globale}.
    """
    global_mean = df[target].mean()
    agg = df.groupby(col)[target].agg(["mean", "count"])
    # Lissage : TE = (n * mean_cat + smoothing * global_mean) / (n + smoothing)
    agg["te"] = (agg["count"] * agg["mean"] + smoothing * global_mean) / (agg["count"] + smoothing)
    te_map = agg["te"].to_dict()
    te_map["__global__"] = global_mean
    return te_map
