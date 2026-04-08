"""
Module de nettoyage V3 — Cible : ABANDONNE seul (exclure DEPOSE)
Nettoyage rigoureux de chaque variable. Zéro redondance, zéro fuite.

Changements vs V2:
  - DEPOSE exclu de la cible (profil chantier, non prédictible)
  - ETAT: nettoyage exhaustif (16 valeurs brutes -> 4 catégories propres)
  - MATERIAU: regroupement en familles cohérentes, micro-catégories -> Autre
  - Suppression des features redondantes (Age², Log(Age) inutiles per ablation V5)
  - Suppression de Famille_mat (nuisible per ablation V5)
  - DIAMETRE/LONGUEUR: nettoyage des zéros/outliers
  - MATERIAU encodé en Target Encoding (pas LabelEncoder arbitraire)
  - Vérification jointure anomalies (1503 orphelins exclus)
"""

import pandas as pd
import numpy as np

ANNEE_REF = 2024

# --- ETAT: 16 valeurs brutes → 4 catégories ---
# Bon, BON, bon → Bon
# Moyen → Moyen
# Vétuste, VETUSTE, Sature, SATURE, FUITES MULTIPLES → Mauvais
# Inconnu, INCONNU, inconnu, SANS OBJET, 0, ., NaN → Inconnu
ETAT_MAP = {
    "Bon": "Bon",
    "BON": "Bon",
    "bon": "Bon",
    "Moyen": "Moyen",
    "Vétuste": "Mauvais",
    "VETUSTE": "Mauvais",
    "Sature": "Mauvais",
    "SATURE": "Mauvais",
    "FUITES MULTIPLES": "Mauvais",
    "Inconnu": "Inconnu",
    "INCONNU": "Inconnu",
    "inconnu": "Inconnu",
    "SANS OBJET": "Inconnu",
    "0": "Inconnu",
    ".": "Inconnu",
}
ETAT_ORDINAL = {"Inconnu": 0, "Bon": 1, "Moyen": 2, "Mauvais": 3}

# --- MATERIAU: 29 valeurs → familles cohérentes ---
FAMILLE_MAP = {
    # Fonte
    "FT": "Fonte",
    "FTG": "Fonte_grise",
    "FTVI": "Fonte",
    "FTBLU": "Fonte",
    "FTTT": "Fonte",
    "FTTTVI": "Fonte",
    # Plastique
    "PVC": "Plastique",
    "PEHD": "Plastique",
    "PEBD": "Plastique",
    "POLY": "Plastique",
    # Amiante-ciment
    "A.C": "Amiante_ciment",
    "AC": "Amiante_ciment",
    # Acier/Métal
    "ACIE": "Acier",
    "FER": "Acier",
    "GALV": "Acier",
    "INOX": "Acier",
    "AFCO": "Acier",
    # Béton
    "BTM": "Beton",
    "BA": "Beton",
    "CENT": "Beton",
    # Reste → Autre
    "AUTRE": "Autre",
    "BIOR": "Autre",
    "PB": "Autre",
    "PRV": "Autre",
    "VP": "Autre",
    "COMP": "Autre",
    "GRES": "Autre",
    "CUIT": "Autre",
    "GALERIE": "Autre",
}


def load_and_clean_v3(data_dir):
    """
    Charge, nettoie, et prépare les données.
    Cible = ABANDONNE seul (DEPOSE exclu de la cible).

    Retourne: cana (tous tronçons nettoyés), anom_clean (anomalies filtrées)

    Hypothèses:
      H1: DEPOSE = chantier/reconfiguration (âge médian 20 ans, 60% < 30 ans, état Bon)
          → exclu de la cible, inclus comme EN SERVICE dans le train
      H2: Dates 1900 = placeholder SIG → date_fiable=False, âge imputé par médiane matériau
      H3: ETAT normalisé en 4 niveaux (Bon/Moyen/Mauvais/Inconnu), NaN → Inconnu
      H4: DIAMETRE=0 → NaN → imputé par médiane du matériau
      H5: LONGUEUR=0 → imputé par médiane globale
      H6: MATERIAU NaN → 'INCONNU', micro-catégories → familles
      H7: Anomalies flag=1 exclues (tronçon déjà abandonné au moment de l'anomalie)
      H8: Anomalies orphelines (GID_OBJET absent de cana) exclues
      H9: Exclure PROJET/POSE/CHANTIER (n<900)
    """

    # --- Chargement ---
    cana = pd.read_csv(data_dir / "canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
    anomalies = pd.read_csv(data_dir / "historiqueanomalie.csv", low_memory=False)

    # --- H9: Garder EN SERVICE + ABANDONNE + DEPOSE ---
    cana = cana[cana["STATUT_OBJET"].isin(["EN SERVICE", "ABANDONNE", "DEPOSE"])].copy()

    # --- Dates ---
    cana["POSE_dt"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")
    cana["ABANDON_dt"] = pd.to_datetime(cana["ABANDON"], format="mixed", dayfirst=True, errors="coerce")
    cana["annee_pose"] = cana["POSE_dt"].dt.year
    cana["annee_abandon"] = cana["ABANDON_dt"].dt.year

    # --- H1: Label = ABANDONNE seul ---
    # DEPOSE est requalifié EN SERVICE (on le garde dans le dataset mais label=0)
    cana["label"] = (cana["STATUT_OBJET"] == "ABANDONNE").astype(int)

    # --- H2: Date fiable ---
    cana["date_fiable"] = True
    cana.loc[cana["annee_pose"] == 1900, "date_fiable"] = False
    cana.loc[cana["annee_pose"].isna(), "date_fiable"] = False
    cana.loc[cana["annee_pose"] > ANNEE_REF, "date_fiable"] = False

    # --- H3: ETAT nettoyé ---
    cana["etat_clean"] = cana["ETAT"].map(ETAT_MAP).fillna("Inconnu")
    cana["etat_ord"] = cana["etat_clean"].map(ETAT_ORDINAL)

    # --- H6: MATERIAU nettoyé ---
    cana["MATERIAU"] = cana["MATERIAU"].fillna("INCONNU")
    cana["famille_mat"] = cana["MATERIAU"].map(FAMILLE_MAP).fillna("Autre")

    # --- H4: DIAMETRE ---
    cana.loc[cana["DIAMETRE"] == 0, "DIAMETRE"] = np.nan

    # --- H5: LONGUEUR ---
    cana.loc[cana["LONGUEUR"] == 0, "LONGUEUR"] = np.nan

    # --- Décennie de pose ---
    cana["decennie_pose"] = (cana["annee_pose"] // 10) * 10

    # --- Anomalies nettoyage (H7, H8) ---
    anomalies["annee_Anomalie"] = anomalies["annee_Anomalie"].astype("Int64")

    # H8: Exclure orphelins
    gids_valides = set(cana["OBJET"].unique())
    anomalies = anomalies[anomalies["GID_OBJET"].isin(gids_valides)].copy()

    # Exclure anomalies futures
    anomalies = anomalies[
        anomalies["annee_Anomalie"].isna() | (anomalies["annee_Anomalie"] <= ANNEE_REF)
    ].copy()

    # H7: Exclure flag=1
    anom_clean = anomalies[anomalies["OBJET_DEPOSE_OU_ABANDONNE"] != 1].copy()

    n_total = len(cana)
    n_es = (cana["STATUT_OBJET"] == "EN SERVICE").sum()
    n_ab = (cana["label"] == 1).sum()
    n_dep = (cana["STATUT_OBJET"] == "DEPOSE").sum()
    print(f"  Données: {n_total:,} tronçons | {n_es:,} EN SERVICE | {n_ab:,} ABANDONNE | {n_dep:,} DEPOSE (label=0)")
    print(f"  Anomalies: {len(anom_clean):,} (après filtre flag/orphelins)")

    return cana, anom_clean


def build_features_v3(cana, anom_clean, cutoff_year=None):
    """
    Construit features + label pour un split temporel.

    Si cutoff_year:
      - Train: prédire les abandons entre cutoff et ANNEE_REF
      - Features: anomalies avant cutoff, âge au cutoff
      - ABANDONNE avant cutoff → exclus
    Si None:
      - Mode scoring: toutes données

    Features (12 au lieu de 20 en V5):
      - age : âge au cutoff (ou à la date d'abandon pour les positifs)
      - diametre, longueur : nettoyés
      - etat_ord : ordinal 0-3
      - famille_enc : target encoding de famille_mat
      - decennie_pose : numérique
      - nb_anom, nb_fuites : comptage avant cutoff
      - a_deja_fuite : binaire
      - densite_fuites_km : fuites / longueur en km
      - age_x_famille : interaction
      - temps_depuis_dern_fuite : années depuis dernière fuite
    """

    if cutoff_year is not None:
        # Exclure les ABANDONNE avant cutoff (déjà partis)
        mask_exclu = (cana["label"] == 1) & (cana["annee_abandon"] < cutoff_year)
        df = cana[~mask_exclu].copy()

        # Label = abandonné entre cutoff et ANNEE_REF
        df["y"] = (
            (df["label"] == 1)
            & (df["annee_abandon"] >= cutoff_year)
            & (df["annee_abandon"] <= ANNEE_REF)
        ).astype(int)

        # Âge au cutoff (PAS à la date d'abandon → fuite temporelle)
        df["age"] = cutoff_year - df["annee_pose"]
        df.loc[~df["date_fiable"], "age"] = np.nan
        df.loc[df["age"] < 0, "age"] = np.nan

        # Anomalies avant cutoff
        anom_period = anom_clean[
            anom_clean["annee_Anomalie"].notna()
            & (anom_clean["annee_Anomalie"] < cutoff_year)
        ]
        ref_year = cutoff_year
    else:
        df = cana.copy()
        df["y"] = df["label"]

        # Âge à ANNEE_REF pour EN SERVICE/DEPOSE, à annee_abandon pour ABANDONNE
        df["age"] = np.where(
            df["label"] == 1,
            df["annee_abandon"] - df["annee_pose"],
            ANNEE_REF - df["annee_pose"],
        )
        df.loc[~df["date_fiable"], "age"] = np.nan
        df.loc[df["age"] < 0, "age"] = np.nan

        anom_period = anom_clean.copy()
        ref_year = ANNEE_REF

    # --- Imputation âge par médiane famille/matériau ---
    age_median_famille = df.groupby("famille_mat")["age"].median()
    for fam in df["famille_mat"].unique():
        mask = (df["famille_mat"] == fam) & df["age"].isna()
        if mask.sum() > 0:
            df.loc[mask, "age"] = age_median_famille.get(fam, df["age"].median())
    # Fallback global
    df["age"] = df["age"].fillna(df["age"].median())

    # --- Imputation DIAMETRE par médiane matériau ---
    diam_median_mat = df.groupby("famille_mat")["DIAMETRE"].median()
    for fam in df["famille_mat"].unique():
        mask = (df["famille_mat"] == fam) & df["DIAMETRE"].isna()
        if mask.sum() > 0:
            df.loc[mask, "DIAMETRE"] = diam_median_mat.get(fam, df["DIAMETRE"].median())
    df["DIAMETRE"] = df["DIAMETRE"].fillna(df["DIAMETRE"].median())

    # --- Imputation LONGUEUR par médiane globale ---
    df["LONGUEUR"] = df["LONGUEUR"].fillna(df["LONGUEUR"].median())

    # --- Features anomalies ---
    anom_fuites = anom_period[
        anom_period["TYPE_ANOMALIE"].isin(["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE"])
    ]

    anom_agg = anom_period.groupby("GID_OBJET").agg(
        nb_anom=("TYPE_ANOMALIE", "count"),
    ).reset_index()

    fuites_agg = anom_fuites.groupby("GID_OBJET").agg(
        nb_fuites=("TYPE_ANOMALIE", "count"),
        derniere_fuite=("annee_Anomalie", "max"),
    ).reset_index()

    anom_agg = anom_agg.merge(fuites_agg, on="GID_OBJET", how="left")
    anom_agg["temps_depuis_dern_fuite"] = ref_year - anom_agg["derniere_fuite"]

    # Jointure
    df = df.merge(anom_agg, left_on="OBJET", right_on="GID_OBJET", how="left")
    df["nb_anom"] = df["nb_anom"].fillna(0).astype(int)
    df["nb_fuites"] = df["nb_fuites"].fillna(0).astype(int)
    df["a_deja_fuite"] = (df["nb_fuites"] > 0).astype(int)
    df["temps_depuis_dern_fuite"] = df["temps_depuis_dern_fuite"].fillna(99)

    # Densité fuites / km
    longueur_km = df["LONGUEUR"].clip(lower=0.001) / 1000
    df["densite_fuites_km"] = df["nb_fuites"] / longueur_km

    # --- Target Encoding pour famille_mat ---
    # Sur train uniquement si cutoff, sinon global (sera recalculé en mode split)
    global_mean = df["y"].mean()
    te = df.groupby("famille_mat")["y"].mean()
    df["famille_enc"] = df["famille_mat"].map(te).fillna(global_mean)

    # --- Interaction ---
    df["age_x_famille"] = df["age"] * df["famille_enc"]

    # --- Decennie pose numérique ---
    df["decennie_pose"] = df["decennie_pose"].fillna(1970)

    # --- Liste de features (12, pas 20) ---
    feature_cols = [
        "age",
        "DIAMETRE",
        "LONGUEUR",
        "etat_ord",
        "famille_enc",
        "decennie_pose",
        "nb_anom",
        "nb_fuites",
        "a_deja_fuite",
        "densite_fuites_km",
        "age_x_famille",
        "temps_depuis_dern_fuite",
    ]

    feature_names = [
        "Age",
        "Diametre",
        "Longueur",
        "Etat",
        "Famille_materiau",
        "Decennie_pose",
        "Nb_anomalies",
        "Nb_fuites",
        "A_deja_fuite",
        "Densite_fuites_km",
        "Age_x_famille",
        "Temps_depuis_fuite",
    ]

    return df, feature_cols, feature_names
