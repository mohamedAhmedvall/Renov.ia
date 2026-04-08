"""Audit complet du dataset brut pour identifier tous les problèmes."""
import pandas as pd
import numpy as np

cana = pd.read_csv("data/canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
anom = pd.read_csv("data/historiqueanomalie.csv", low_memory=False)

print("=== COLONNES CANA ===")
print(list(cana.columns))
print()

print("=== ETAT BRUT (toutes valeurs) ===")
print(cana["ETAT"].value_counts(dropna=False))
print()

print("=== STATUT_OBJET ===")
print(cana["STATUT_OBJET"].value_counts(dropna=False))
print()

print("=== MATERIAU (toutes valeurs) ===")
print(cana["MATERIAU"].value_counts(dropna=False))
print()

print("=== DIAMETRE ===")
d = cana["DIAMETRE"]
print(f"Min={d.min()}, Max={d.max()}, NaN={d.isna().sum()}, Zero={(d==0).sum()}")
print(d.describe())
print()

print("=== LONGUEUR ===")
lo = cana["LONGUEUR"]
print(f"Min={lo.min()}, Max={lo.max()}, NaN={lo.isna().sum()}, Zero={(lo==0).sum()}, Neg={(lo<0).sum()}")
print()

cana["POSE_dt"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")
cana["annee_pose"] = cana["POSE_dt"].dt.year
print("=== ANNEE POSE ===")
print(cana["annee_pose"].describe())
annee = cana["annee_pose"]
print(f"NaN: {annee.isna().sum()}")
print(f"1900: {(annee == 1900).sum()}")
print(f">2024: {(annee > 2024).sum()}")
print()

# Dates ABANDON
cana["ABANDON_dt"] = pd.to_datetime(cana["ABANDON"], format="mixed", dayfirst=True, errors="coerce")
cana["annee_abandon"] = cana["ABANDON_dt"].dt.year
ab = cana[cana["STATUT_OBJET"] == "ABANDONNE"]
print("=== ANNEE ABANDON (ABANDONNE seul) ===")
print(ab["annee_abandon"].describe())
print(f"NaN: {ab['annee_abandon'].isna().sum()}")
print()

# Anomalies
print("=== ANOMALIES COLONNES ===")
print(list(anom.columns))
print()
print("=== OBJET_DEPOSE_OU_ABANDONNE flag ===")
print(anom["OBJET_DEPOSE_OU_ABANDONNE"].value_counts(dropna=False))
print()

# Combien d'anomalies par type pour les ABANDONNES seulement
gids_ab = set(ab["OBJET"].unique())
anom_ab = anom[anom["GID_OBJET"].isin(gids_ab)]
print(f"=== ANOMALIES sur troncons ABANDONNES (n={len(anom_ab)}) ===")
print(anom_ab["TYPE_ANOMALIE"].value_counts().head(10))
print()

# Jointure : regarder si GID_OBJET == OBJET
print("=== JOINTURE CHECK ===")
gids_cana = set(cana["OBJET"].unique())
gids_anom = set(anom["GID_OBJET"].unique())
print(f"Troncons cana: {len(gids_cana)}")
print(f"Troncons dans anomalies: {len(gids_anom)}")
print(f"Intersection: {len(gids_cana & gids_anom)}")
print(f"Anomalies sans troncon: {len(gids_anom - gids_cana)}")

# Vérifier les EN SERVICE + date ABANDON remplie (fuite possible)
es = cana[cana["STATUT_OBJET"] == "EN SERVICE"]
print()
print(f"EN SERVICE avec date ABANDON remplie: {es['annee_abandon'].notna().sum()}")
print(f"ABANDONNE avec date ABANDON manquante: {ab['annee_abandon'].isna().sum()}")
