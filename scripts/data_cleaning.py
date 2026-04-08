"""
Module de nettoyage des donnees - Pipeline reproductible
Chaque transformation est une hypothese documentee.

Annee de reference : 2024 (derniere annee de donnees reelles)
"""

import pandas as pd
import numpy as np

ANNEE_REF = 2024


def load_and_clean(data_dir):
    """Charge et nettoie les donnees canalisations + anomalies.

    Retourne: cana_es (troncons EN SERVICE enrichis), anomalies_clean

    Hypotheses documentees:
    - H1: Dates 1900 = placeholder SIG, flaggees comme non fiables
    - H2: ETAT normalise en 4 categories (Bon/Moyen/Vetuste/Inconnu)
    - H3: Anomalies filtrees — on garde OBJET_DEPOSE_OU_ABANDONNE in (0, -1)
          0 = troncon actif, -1 = troncon depose APRES l'anomalie (historiquement valide)
          1 = troncon deja abandonne au moment de l'anomalie (exclu)
    - H4: Age calcule uniquement sur dates fiables, reference = 2024
    - H5: Cohorte materiau-epoque = decennie de pose x materiau (sur dates fiables)
    - H6: DIAMETRE = 0 traite comme NaN (DN0 = diametre inconnu)
    - H7: Anomalies avec annee > 2024 exclues (1 record a 2033 = erreur)
    - H8: Pression et vitesse ecartees (demande referent metier)
    """

    # --- Chargement ---
    cana = pd.read_csv(data_dir / "canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
    anomalies = pd.read_csv(data_dir / "historiqueanomalie.csv", low_memory=False)

    # --- Dates de pose (H1, H4) ---
    cana["POSE"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")
    cana["annee_pose"] = cana["POSE"].dt.year

    cana["date_fiable"] = True
    cana.loc[cana["annee_pose"] == 1900, "date_fiable"] = False
    cana.loc[cana["annee_pose"].isna(), "date_fiable"] = False
    cana.loc[cana["annee_pose"] > ANNEE_REF, "date_fiable"] = False

    cana["age"] = ANNEE_REF - cana["annee_pose"]
    cana.loc[~cana["date_fiable"], "age"] = np.nan

    # --- DIAMETRE : DN0 = inconnu (H6) ---
    cana.loc[cana["DIAMETRE"] == 0, "DIAMETRE"] = np.nan

    # --- ETAT normalisation (H2) ---
    etat_map = {
        "Bon": "Bon", "BON": "Bon", "bon": "Bon",
        "Moyen": "Moyen",
        "Vétuste": "Vetuste", "VETUSTE": "Vetuste",
        "Sature": "Vetuste", "SATURE": "Vetuste",
        "Inconnu": "Inconnu", "INCONNU": "Inconnu", "inconnu": "Inconnu",
        "SANS OBJET": "Inconnu",
        "0": "Inconnu", ".": "Inconnu",
    }
    cana["ETAT_CLEAN"] = cana["ETAT"].map(etat_map).fillna("Inconnu")

    # --- Filtrer EN SERVICE ---
    cana_es = cana[cana["STATUT_OBJET"] == "EN SERVICE"].copy()

    # --- Materiau : regroupement familles ---
    famille_map = {
        "FT": "Fonte", "FTG": "Fonte_grise", "FTVI": "Fonte",
        "FTBLU": "Fonte", "FTTT": "Fonte", "FTTTVI": "Fonte",
        "PVC": "Plastique", "PEHD": "Plastique", "PEBD": "Plastique",
        "POLY": "Plastique",
        "A.C": "Amiante_ciment", "AC": "Amiante_ciment",
        "ACIE": "Acier", "FER": "Acier", "GALV": "Acier", "INOX": "Acier",
        "BTM": "Beton", "BA": "Beton",
    }
    cana_es["FAMILLE_MATERIAU"] = cana_es["MATERIAU"].map(famille_map).fillna("Autre")

    # --- Cohorte materiau-epoque (H5) ---
    cana_es["decennie_pose"] = (cana_es["annee_pose"] // 10) * 10
    cana_es["cohorte"] = cana_es["MATERIAU"].astype(str) + "_" + cana_es["decennie_pose"].astype(str)
    cana_es.loc[~cana_es["date_fiable"], "cohorte"] = cana_es.loc[~cana_es["date_fiable"], "MATERIAU"].astype(str) + "_inconnu"

    # --- ETAT ordinal ---
    etat_ordinal = {"Bon": 1, "Moyen": 2, "Vetuste": 3, "Inconnu": np.nan}
    cana_es["ETAT_ORD"] = cana_es["ETAT_CLEAN"].map(etat_ordinal)

    # --- Anomalies nettoyage (H3, H7) ---
    anomalies["DATE_DETECTION_parsed"] = pd.to_datetime(
        anomalies["DATE_DETECTION_parsed"], errors="coerce"
    )
    anomalies["annee_Anomalie"] = anomalies["annee_Anomalie"].astype("Int64")

    # Exclure anomalies futures (H7) : 1 record a 2033
    anomalies = anomalies[
        anomalies["annee_Anomalie"].isna() | (anomalies["annee_Anomalie"] <= ANNEE_REF)
    ].copy()

    # H3 : garder 0 (actif) et -1 (depose apres anomalie), exclure 1 (deja abandonne)
    anom_actives = anomalies[anomalies["OBJET_DEPOSE_OU_ABANDONNE"] != 1].copy()

    # --- Enrichissement : features d'anomalies par troncon ---
    anom_features = anom_actives.groupby("GID_OBJET").agg(
        nb_anomalies=("TYPE_ANOMALIE", "count"),
        nb_fuites=("TYPE_ANOMALIE", lambda x: x.isin(["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE"]).sum()),
        premiere_anomalie=("annee_Anomalie", "min"),
        derniere_anomalie=("annee_Anomalie", "max"),
    ).reset_index()

    # Temps depuis derniere anomalie
    anom_features["temps_depuis_derniere"] = ANNEE_REF - anom_features["derniere_anomalie"]

    # Intervalle moyen entre anomalies (acceleration)
    def calc_interval(group):
        dates = sorted(group["annee_Anomalie"].dropna().unique())
        if len(dates) < 2:
            return np.nan
        intervals = [dates[i+1] - dates[i] for i in range(len(dates)-1)]
        return np.mean(intervals)

    anom_intervals = anom_actives.groupby("GID_OBJET").apply(calc_interval, include_groups=False).reset_index()
    anom_intervals.columns = ["GID_OBJET", "intervalle_moyen_ans"]
    anom_features = anom_features.merge(anom_intervals, on="GID_OBJET", how="left")

    # --- Jointure ---
    cana_es = cana_es.merge(anom_features, left_on="OBJET", right_on="GID_OBJET", how="left")
    cana_es["nb_anomalies"] = cana_es["nb_anomalies"].fillna(0).astype(int)
    cana_es["nb_fuites"] = cana_es["nb_fuites"].fillna(0).astype(int)
    cana_es["a_casse"] = (cana_es["nb_anomalies"] > 0).astype(int)
    cana_es["temps_depuis_derniere"] = cana_es["temps_depuis_derniere"].fillna(999)

    # --- Densite reparations par ml ---
    cana_es["densite_anomalies_ml"] = np.where(
        cana_es["LONGUEUR"] > 0,
        cana_es["nb_anomalies"] / cana_es["LONGUEUR"],
        0
    )

    return cana_es, anom_actives
