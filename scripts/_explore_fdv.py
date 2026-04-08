"""Exploration rapide des dates abandon/depose pour la refonte."""
import pandas as pd
import numpy as np

cana = pd.read_csv("data/canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
anom = pd.read_csv("data/historiqueanomalie.csv", low_memory=False)

cana["ABANDON_dt"] = pd.to_datetime(cana["ABANDON"], format="mixed", dayfirst=True, errors="coerce")
cana["DEPOSE_dt"] = pd.to_datetime(cana["DEPOSE"], format="mixed", dayfirst=True, errors="coerce")
cana["POSE_dt"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")

cana["date_fdv"] = cana["ABANDON_dt"].fillna(cana["DEPOSE_dt"])
cana["annee_fdv"] = cana["date_fdv"].dt.year
cana["annee_pose"] = cana["POSE_dt"].dt.year

for s in ["ABANDONNE", "DEPOSE", "EN SERVICE"]:
    sub = cana[cana["STATUT_OBJET"] == s]
    fdv = sub["annee_fdv"].dropna()
    print(f"\n{s}: n={len(sub):,}, date_fdv remplie={len(fdv):,} ({100*len(fdv)/len(sub):.1f}%)")
    if len(fdv) > 0:
        print(f"  annee fdv: min={fdv.min():.0f} max={fdv.max():.0f} median={fdv.median():.0f}")
    pose = sub["annee_pose"].dropna()
    pose = pose[(pose > 1850) & (pose < 2025)]
    if len(pose) > 0:
        print(f"  annee pose: min={pose.min():.0f} max={pose.max():.0f} median={pose.median():.0f}")

# Age a la date abandon
fdv = cana[cana["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"])].copy()
fdv["age_at_fdv"] = fdv["annee_fdv"] - fdv["annee_pose"]
valid = fdv[(fdv["age_at_fdv"] > 0) & (fdv["age_at_fdv"] < 200) & (fdv["annee_pose"] != 1900)]
print(f"\nAge a la date abandon (n={len(valid):,}):")
print(f"  moy={valid['age_at_fdv'].mean():.1f} med={valid['age_at_fdv'].median():.0f}")
print(f"  q25={valid['age_at_fdv'].quantile(0.25):.0f} q75={valid['age_at_fdv'].quantile(0.75):.0f}")

# Distribution annee abandon
print("\nDistribution annee abandon/depose:")
print(fdv["annee_fdv"].value_counts().sort_index().tail(20))

# Anomalies : colonnes utiles
print("\n=== COLONNES ANOMALIES ===")
print(list(anom.columns))
print(f"\nTypes anomalies:")
print(anom["TYPE_ANOMALIE"].value_counts())

# Nb anomalies par type sur troncons EN SERVICE
es_ids = set(cana[cana["STATUT_OBJET"] == "EN SERVICE"]["OBJET"])
anom_es = anom[anom["GID_OBJET"].isin(es_ids)]
print(f"\nAnomalies sur EN SERVICE: {len(anom_es):,}")
print(anom_es["TYPE_ANOMALIE"].value_counts())

# TERRAIN, PROFONDEUR, etc.
print("\n=== FEATURES SUPPLEMENTAIRES ===")
for col in ["TERRAIN", "PROFONDEUR", "COTE_VOIE_DESSERVI", "QUALITE_GEOMETRIE"]:
    print(f"\n{col}: {cana[col].notna().sum():,} non-null ({100*cana[col].notna().sum()/len(cana):.1f}%)")
    if cana[col].dtype == "object":
        print(cana[col].value_counts().head(5))
    else:
        print(f"  min={cana[col].min()}, max={cana[col].max()}, median={cana[col].median()}")
