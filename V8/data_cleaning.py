"""
V8 — Modèle 2 : Prédiction de fuites/casses.
Module de nettoyage et construction des features.

Objectif : prédire si un tronçon va avoir ≥1 fuite dans les H prochaines années.
Complémentaire à V7 (prédiction d'abandon/fin de vie).

Features (5, par choix métier) :
  1. materiau (famille, target-encoded)
  2. diametre
  3. longueur
  4. age (corrigé, dates 1900 → imputation)
  5. historique_casses (nb fuites avant la date d'observation)

Cible : binaire, ≥1 fuite dans [observation_date, observation_date + horizon]
Horizons : 1, 3, 5 ans
"""

import pandas as pd
import numpy as np

ANNEE_REF = 2024

# --- MATERIAU → familles (identique V4) ---
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


def load_data(data_dir):
    """Charge les deux CSV bruts."""
    cana = pd.read_csv(data_dir / "canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
    anomalies = pd.read_csv(data_dir / "historiqueanomalie.csv", low_memory=False)

    # Parse dates
    cana["POSE_dt"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")
    cana["annee_pose"] = cana["POSE_dt"].dt.year

    # Fiabilité de la date de pose
    cana["date_fiable"] = True
    cana.loc[cana["annee_pose"] == 1900, "date_fiable"] = False
    cana.loc[cana["annee_pose"].isna(), "date_fiable"] = False
    cana.loc[cana["annee_pose"] > ANNEE_REF, "date_fiable"] = False

    # Matériau → famille
    cana["MATERIAU"] = cana["MATERIAU"].fillna("INCONNU")
    cana["famille_mat"] = cana["MATERIAU"].map(FAMILLE_MAP).fillna("Autre")

    # Diamètre : 0 = inconnu
    cana.loc[cana["DIAMETRE"] == 0, "DIAMETRE"] = np.nan

    # Anomalies : garder uniquement les fuites
    anomalies["DATE_DETECTION_parsed"] = pd.to_datetime(
        anomalies["DATE_DETECTION_parsed"], errors="coerce"
    )
    anomalies["annee_Anomalie"] = anomalies["annee_Anomalie"].astype("Int64")

    fuites = anomalies[
        anomalies["TYPE_ANOMALIE"].isin(["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE"])
    ].copy()

    # Exclure anomalies sur tronçons inexistants dans le référentiel
    gids_valides = set(cana["OBJET"].unique())
    fuites = fuites[fuites["GID_OBJET"].isin(gids_valides)].copy()

    # Exclure flag=1 (tronçon déjà abandonné au moment de la fuite)
    fuites = fuites[fuites["OBJET_DEPOSE_OU_ABANDONNE"] != 1].copy()

    # Exclure dates futures
    fuites = fuites[fuites["annee_Anomalie"] <= ANNEE_REF].copy()

    n_es = (cana["STATUT_OBJET"] == "EN SERVICE").sum()
    print(f"  Canalisations: {len(cana):,} | EN SERVICE: {n_es:,}")
    print(f"  Fuites valides: {len(fuites):,} | Tronçons touchés: {fuites['GID_OBJET'].nunique():,}")

    return cana, fuites


def build_dataset(cana, fuites, observation_year, horizon, te_map=None):
    """
    Construit le dataset pour un horizon donné.

    observation_year : année à laquelle on observe (ex: 2018)
    horizon : nombre d'années à prédire (1, 3, ou 5)

    Cible : ≥1 fuite dans [observation_year, observation_year + horizon)
    Features : basées sur l'info disponible AVANT observation_year

    Retourne: df, feature_cols, feature_names
    """
    # On ne garde que les tronçons EN SERVICE ou qui étaient encore actifs à observation_year
    # Simplification : on prend les EN SERVICE + ABANDONNE après observation_year
    cana_obs = cana.copy()
    cana_obs["ABANDON_dt"] = pd.to_datetime(cana_obs["ABANDON"], format="mixed", dayfirst=True, errors="coerce")
    cana_obs["annee_abandon"] = cana_obs["ABANDON_dt"].dt.year

    # Garder : EN SERVICE (toujours actifs) + ABANDONNE après observation_year (actifs au moment d'observation)
    mask_actif = (
        (cana_obs["STATUT_OBJET"] == "EN SERVICE")
        | (
            (cana_obs["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"]))
            & (cana_obs["annee_abandon"] >= observation_year)
        )
    )
    df = cana_obs[mask_actif].copy()

    # --- Cible : ≥1 fuite dans [observation_year, observation_year + horizon) ---
    fuites_horizon = fuites[
        (fuites["annee_Anomalie"] >= observation_year)
        & (fuites["annee_Anomalie"] < observation_year + horizon)
    ]
    troncons_avec_fuite = set(fuites_horizon["GID_OBJET"].unique())
    df["y"] = df["OBJET"].isin(troncons_avec_fuite).astype(int)

    # --- Feature 1 : age (corrigé) ---
    df["age"] = observation_year - df["annee_pose"]
    df.loc[~df["date_fiable"], "age"] = np.nan
    df.loc[df["age"] < 0, "age"] = np.nan

    # Imputation âge par famille matériau
    age_med = df.groupby("famille_mat")["age"].median()
    for fam in df["famille_mat"].unique():
        mask = (df["famille_mat"] == fam) & df["age"].isna()
        if mask.sum() > 0:
            df.loc[mask, "age"] = age_med.get(fam, df["age"].median())
    df["age"] = df["age"].fillna(df["age"].median())

    # --- Feature 2 : diametre ---
    diam_med = df.groupby("famille_mat")["DIAMETRE"].median()
    for fam in df["famille_mat"].unique():
        mask = (df["famille_mat"] == fam) & df["DIAMETRE"].isna()
        if mask.sum() > 0:
            df.loc[mask, "DIAMETRE"] = diam_med.get(fam, df["DIAMETRE"].median())
    df["DIAMETRE"] = df["DIAMETRE"].fillna(df["DIAMETRE"].median())

    # --- Feature 3 : longueur ---
    df.loc[df["LONGUEUR"] == 0, "LONGUEUR"] = np.nan
    df["LONGUEUR"] = df["LONGUEUR"].fillna(df["LONGUEUR"].median())

    # --- Feature 3 : nb_fuites_avant (historique casses avant observation_year) ---
    fuites_avant = fuites[fuites["annee_Anomalie"] < observation_year]
    hist_agg = fuites_avant.groupby("GID_OBJET").agg(
        nb_fuites_avant=("TYPE_ANOMALIE", "count"),
    ).reset_index()
    df = df.merge(hist_agg, left_on="OBJET", right_on="GID_OBJET", how="left")
    df["nb_fuites_avant"] = df["nb_fuites_avant"].fillna(0).astype(int)

    # --- Feature 4 : famille matériau (target-encoded, externe) ---
    if te_map is not None:
        global_mean = te_map.get("__global__", 0.01)
        tv = {k: v for k, v in te_map.items() if k != "__global__"}
        df["famille_enc"] = df["famille_mat"].map(tv).fillna(global_mean)
    else:
        df["famille_enc"] = np.nan

    feature_cols = ["age", "DIAMETRE", "LONGUEUR", "nb_fuites_avant", "famille_enc"]
    feature_names = ["Age", "Diametre", "Longueur", "Nb_fuites_historique", "Famille_materiau"]

    n_pos = df["y"].sum()
    print(f"  Observation={observation_year}, Horizon={horizon}ans")
    print(f"  Tronçons: {len(df):,} | Positifs: {n_pos:,} ({100*n_pos/len(df):.2f}%)")

    return df, feature_cols, feature_names


def compute_target_encoding(df, col="famille_mat", target="y", smoothing=10):
    """TE bayésien sur train uniquement."""
    global_mean = df[target].mean()
    agg = df.groupby(col)[target].agg(["mean", "count"])
    agg["te"] = (agg["count"] * agg["mean"] + smoothing * global_mean) / (agg["count"] + smoothing)
    te_map = agg["te"].to_dict()
    te_map["__global__"] = global_mean
    return te_map
