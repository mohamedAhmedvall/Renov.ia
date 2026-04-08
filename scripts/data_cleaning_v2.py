"""
Module de nettoyage des donnees V2 - Refonte cible ABANDON/DEPOSE
Pipeline reproductible. Chaque transformation est une hypothese documentee.

Changement majeur vs V1 :
  - Cible = ABANDONNE/DEPOSE (renouvellement) vs EN SERVICE
  - On utilise TOUS les troncons (pas seulement EN SERVICE)
  - Age calcule a la date d'abandon (pas a 2024) pour eviter la fuite temporelle
  - Anomalies filtrees avant la date d'evenement uniquement
"""

import pandas as pd
import numpy as np

ANNEE_REF = 2024

FAMILLE_MAP = {
    "FT": "Fonte", "FTG": "Fonte_grise", "FTVI": "Fonte",
    "FTBLU": "Fonte", "FTTT": "Fonte", "FTTTVI": "Fonte",
    "PVC": "Plastique", "PEHD": "Plastique", "PEBD": "Plastique",
    "POLY": "Plastique",
    "A.C": "Amiante_ciment", "AC": "Amiante_ciment",
    "ACIE": "Acier", "FER": "Acier", "GALV": "Acier", "INOX": "Acier",
    "BTM": "Beton", "BA": "Beton",
}

ETAT_MAP = {
    "Bon": "Bon", "BON": "Bon", "bon": "Bon",
    "Moyen": "Moyen",
    "Vétuste": "Vetuste", "VETUSTE": "Vetuste",
    "Sature": "Vetuste", "SATURE": "Vetuste",
    "Inconnu": "Inconnu", "INCONNU": "Inconnu", "inconnu": "Inconnu",
    "SANS OBJET": "Inconnu",
    "0": "Inconnu", ".": "Inconnu",
}

ETAT_ORDINAL = {"Bon": 1, "Moyen": 2, "Vetuste": 3, "Inconnu": np.nan}


def load_and_clean_v2(data_dir):
    """Charge et nettoie les donnees pour la cible abandon/depose.

    Retourne: df_all (tous troncons avec label + features), anomalies_clean

    Hypotheses documentees:
    - H1: Dates 1900 = placeholder SIG, flaggees comme non fiables
    - H2: ETAT normalise en 4 categories (Bon/Moyen/Vetuste/Inconnu)
    - H3: Anomalies filtrees — exclure flag=1 (deja abandonne au moment de l'anomalie)
    - H4: ABANDONNE et DEPOSE fusionnes en un seul label "FIN_DE_VIE"
    - H5: Age calcule a la date d'evenement (abandon) ou a ANNEE_REF (en service)
          -> corrige la fuite temporelle de V1
    - H6: DIAMETRE = 0 traite comme NaN
    - H7: Anomalies avec annee > 2024 exclues
    - H8: Pression et vitesse ecartees (demande referent metier)
    - H9: Cohorte materiau-epoque = decennie de pose x materiau
    - H10: Anomalies comptees AVANT la date d'evenement uniquement
           -> pour les EN SERVICE, toutes les anomalies sont avant ANNEE_REF
           -> pour les ABANDONNES, anomalies avant la date d'abandon
    - H11: On exclut PROJET, POSE, CHANTIER (n<900, pas exploitables)
    """

    # --- Chargement ---
    cana = pd.read_csv(data_dir / "canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
    anomalies = pd.read_csv(data_dir / "historiqueanomalie.csv", low_memory=False)

    # --- H11: Garder uniquement EN SERVICE + ABANDONNE + DEPOSE ---
    cana = cana[cana["STATUT_OBJET"].isin(["EN SERVICE", "ABANDONNE", "DEPOSE"])].copy()

    # --- Dates ---
    cana["POSE_dt"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")
    cana["ABANDON_dt"] = pd.to_datetime(cana["ABANDON"], format="mixed", dayfirst=True, errors="coerce")
    cana["DEPOSE_dt"] = pd.to_datetime(cana["DEPOSE"], format="mixed", dayfirst=True, errors="coerce")
    cana["annee_pose"] = cana["POSE_dt"].dt.year

    # --- H4: Label --- ABANDONNE + DEPOSE = 1, EN SERVICE = 0
    cana["label"] = cana["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"]).astype(int)

    # --- Date d'evenement (H5) ---
    # Pour les abandonnes/deposes : date reelle d'abandon/depose
    # Pour les EN SERVICE : ANNEE_REF (observation censuree)
    cana["date_evenement"] = cana["ABANDON_dt"].fillna(cana["DEPOSE_dt"])
    cana["annee_evenement"] = cana["date_evenement"].dt.year
    cana.loc[cana["STATUT_OBJET"] == "EN SERVICE", "annee_evenement"] = ANNEE_REF

    # --- H1: Dates fiables ---
    cana["date_fiable"] = True
    cana.loc[cana["annee_pose"] == 1900, "date_fiable"] = False
    cana.loc[cana["annee_pose"].isna(), "date_fiable"] = False
    cana.loc[cana["annee_pose"] > ANNEE_REF, "date_fiable"] = False

    # --- H5: Age a la date d'evenement (PAS a 2024 pour tous) ---
    cana["age"] = cana["annee_evenement"] - cana["annee_pose"]
    cana.loc[~cana["date_fiable"], "age"] = np.nan
    cana.loc[cana["age"] < 0, "age"] = np.nan  # incoherences

    # --- H6: DIAMETRE ---
    cana.loc[cana["DIAMETRE"] == 0, "DIAMETRE"] = np.nan

    # --- H2: ETAT ---
    cana["ETAT_CLEAN"] = cana["ETAT"].map(ETAT_MAP).fillna("Inconnu")
    cana["ETAT_ORD"] = cana["ETAT_CLEAN"].map(ETAT_ORDINAL)

    # --- Materiau ---
    cana["FAMILLE_MATERIAU"] = cana["MATERIAU"].map(FAMILLE_MAP).fillna("Autre")

    # --- H9: Cohorte ---
    cana["decennie_pose"] = (cana["annee_pose"] // 10) * 10
    cana["cohorte"] = cana["MATERIAU"].astype(str) + "_" + cana["decennie_pose"].astype(str)
    cana.loc[~cana["date_fiable"], "cohorte"] = (
        cana.loc[~cana["date_fiable"], "MATERIAU"].astype(str) + "_inconnu"
    )

    # --- Anomalies nettoyage (H3, H7) ---
    anomalies["DATE_DETECTION_parsed"] = pd.to_datetime(
        anomalies["DATE_DETECTION_parsed"], errors="coerce"
    )
    anomalies["annee_Anomalie"] = anomalies["annee_Anomalie"].astype("Int64")

    # H7: Exclure anomalies futures
    anomalies = anomalies[
        anomalies["annee_Anomalie"].isna() | (anomalies["annee_Anomalie"] <= ANNEE_REF)
    ].copy()

    # H3: Exclure flag=1 (deja abandonne au moment de l'anomalie)
    anom_clean = anomalies[anomalies["OBJET_DEPOSE_OU_ABANDONNE"] != 1].copy()

    return cana, anom_clean


def build_features_v2(cana, anom_clean, cutoff_year=None):
    """Construit les features et le label pour un split temporel.

    Si cutoff_year est fourni :
      - Label = abandonnes ENTRE cutoff_year et ANNEE_REF
      - Features basees sur anomalies < cutoff_year
      - Troncons abandonnes AVANT cutoff_year sont exclus
    Si cutoff_year est None :
      - Mode scoring : utilise tout l'historique jusqu'a ANNEE_REF
      - Label = abandon/depose reel

    Retourne: df avec features + label, liste des noms de features
    """

    if cutoff_year is not None:
        # Exclure les troncons deja abandonnes avant cutoff
        mask_exclu = (cana["label"] == 1) & (cana["annee_evenement"] < cutoff_year)
        df = cana[~mask_exclu].copy()

        # Label = abandonne entre cutoff et ANNEE_REF
        df["label_split"] = (
            (df["label"] == 1) &
            (df["annee_evenement"] >= cutoff_year) &
            (df["annee_evenement"] <= ANNEE_REF)
        ).astype(int)

        # Age a cutoff_year (pas a la date d'abandon)
        df["age_at_split"] = cutoff_year - df["annee_pose"]
        df.loc[~df["date_fiable"], "age_at_split"] = np.nan
        df.loc[df["age_at_split"] < 0, "age_at_split"] = np.nan

        # Anomalies avant cutoff
        anom_period = anom_clean[
            anom_clean["annee_Anomalie"].notna() &
            (anom_clean["annee_Anomalie"] < cutoff_year)
        ]
        ref_year = cutoff_year
        label_col = "label_split"
    else:
        df = cana.copy()
        # Anomalies avant la date d'evenement de chaque troncon (H10)
        # Simplification : on utilise tout l'historique car pour EN SERVICE
        # annee_evenement = ANNEE_REF, et pour les abandonnes les anomalies
        # flag=-1 sont deja marquees comme "avant abandon"
        anom_period = anom_clean.copy()
        ref_year = ANNEE_REF
        label_col = "label"

        # Age : deja calcule dans load_and_clean_v2 (a la date d'evenement)
        df["age_at_split"] = df["age"]

    # --- Features anomalies aggregees par troncon ---
    # Ne garder que FUITE_SIGNAL_TR, FUITE_DETECT_TR, FUITE (les seuls pertinents)
    anom_fuites = anom_period[
        anom_period["TYPE_ANOMALIE"].isin(["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE"])
    ]

    anom_feat = anom_period.groupby("GID_OBJET").agg(
        nb_anom=("TYPE_ANOMALIE", "count"),
    ).reset_index()

    fuites_feat = anom_fuites.groupby("GID_OBJET").agg(
        nb_fuites=("TYPE_ANOMALIE", "count"),
        premiere_fuite=("annee_Anomalie", "min"),
        derniere_fuite=("annee_Anomalie", "max"),
    ).reset_index()

    anom_feat = anom_feat.merge(fuites_feat, on="GID_OBJET", how="left")
    anom_feat["temps_depuis_derniere_fuite"] = ref_year - anom_feat["derniere_fuite"]

    # Intervalle moyen entre fuites
    def calc_interval(group):
        dates = sorted(group["annee_Anomalie"].dropna().unique())
        if len(dates) < 2:
            return np.nan
        return np.mean([dates[i + 1] - dates[i] for i in range(len(dates) - 1)])

    intervals = (
        anom_fuites.groupby("GID_OBJET")
        .apply(calc_interval, include_groups=False)
        .reset_index()
    )
    intervals.columns = ["GID_OBJET", "intervalle_moyen"]
    anom_feat = anom_feat.merge(intervals, on="GID_OBJET", how="left")

    # --- Assemblage ---
    from sklearn.preprocessing import LabelEncoder

    df = df.merge(anom_feat, left_on="OBJET", right_on="GID_OBJET", how="left")

    # Fillna
    df["nb_anom"] = df["nb_anom"].fillna(0).astype(int)
    df["nb_fuites"] = df["nb_fuites"].fillna(0).astype(int)
    df["temps_depuis_derniere_fuite"] = df["temps_depuis_derniere_fuite"].fillna(99)
    df["intervalle_moyen"] = df["intervalle_moyen"].fillna(99)

    # Encodages
    le_mat = LabelEncoder()
    df["MATERIAU_ENC"] = le_mat.fit_transform(df["MATERIAU"].fillna("INCONNU"))
    le_fam = LabelEncoder()
    df["FAMILLE_ENC"] = le_fam.fit_transform(df["FAMILLE_MATERIAU"])

    # --- Features derivees ---
    age = df["age_at_split"]
    df["age2"] = age ** 2
    df["log_age"] = np.log1p(age.clip(lower=0))
    df["age_x_materiau"] = age.fillna(0) * df["MATERIAU_ENC"]

    df["densite_anom_ml"] = np.where(
        df["LONGUEUR"] > 0, df["nb_anom"] / df["LONGUEUR"], 0
    )
    df["densite_fuites_ml"] = np.where(
        df["LONGUEUR"] > 0, df["nb_fuites"] / df["LONGUEUR"], 0
    )
    df["fuites_par_an_age"] = np.where(
        age > 0, df["nb_fuites"] / age, 0
    )
    df["a_deja_fuite"] = (df["nb_fuites"] > 0).astype(int)

    # Acceleration : intervalle qui diminue = degradation acceleree
    df["acceleration"] = np.where(
        df["intervalle_moyen"] < 3, 2,
        np.where(df["intervalle_moyen"] < 5, 1,
                 np.where(df["intervalle_moyen"] < 10, 0.5, 0))
    )

    df["date_fiable_int"] = df["date_fiable"].astype(int)

    # Renommer le label pour coherence
    df["y"] = df[label_col]

    # Liste des features
    feature_cols = [
        "age_at_split", "age2", "log_age",
        "DIAMETRE", "LONGUEUR",
        "MATERIAU_ENC", "FAMILLE_ENC", "ETAT_ORD",
        "date_fiable_int", "decennie_pose",
        "nb_anom", "nb_fuites", "a_deja_fuite",
        "temps_depuis_derniere_fuite", "intervalle_moyen", "acceleration",
        "densite_anom_ml", "densite_fuites_ml", "fuites_par_an_age",
        "age_x_materiau",
    ]

    feature_names = [
        "Age", "Age^2", "Log(Age)",
        "Diametre", "Longueur",
        "Materiau", "Famille_mat", "Etat",
        "Date_fiable", "Decennie_pose",
        "Nb_anom_hist", "Nb_fuites_hist", "A_deja_fuite",
        "Temps_depuis_dern_fuite", "Intervalle_moyen", "Acceleration",
        "Densite_anom/ml", "Densite_fuites/ml", "Fuites_par_an_age",
        "Age_x_materiau",
    ]

    return df, feature_cols, feature_names, le_mat
