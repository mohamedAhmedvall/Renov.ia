"""
Phase 1 - EDA & Etat des lieux patrimonial
Projet : Prediction de casses de canalisations d'eau

Annee de reference : 2024 (derniere annee de donnees reelles)
Utilise le module data_cleaning pour un pipeline reproductible.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from data_cleaning import load_and_clean, ANNEE_REF

# --- Config ---
import os
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", font_scale=1.1)
COLORS = sns.color_palette("Set2", 10)

print("=" * 60)
print(f"PHASE 1 - EDA & ETAT DES LIEUX PATRIMONIAL (ref={ANNEE_REF})")
print("=" * 60)


# ============================================================
# 1. CHARGEMENT VIA DATA_CLEANING
# ============================================================
print("\n[1/8] Chargement et nettoyage des donnees...")

cana_es, anom_actives = load_and_clean(DATA_DIR)

# Aussi charger le brut pour stats globales
cana_brut = pd.read_csv(DATA_DIR / "canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
anomalies_brut = pd.read_csv(DATA_DIR / "historiqueanomalie.csv", low_memory=False)

n_total = len(cana_brut)
n_es = len(cana_es)

print(f"  Canalisations total : {n_total:,}")
print(f"  Anomalies total     : {len(anomalies_brut):,}")
print(f"  Troncons EN SERVICE : {n_es:,}")
print(f"  Anomalies retenues  : {len(anom_actives):,} (exclu OBJET_DEPOSE_OU_ABANDONNE=1 et annee>2024)")

# Stats dates
n_1900 = (cana_es["annee_pose"] == 1900).sum()  # flagged non fiable
n_fiable = cana_es["date_fiable"].sum()
n_non_fiable = n_es - n_fiable
print(f"\n  Dates de pose (troncons EN SERVICE) :")
print(f"    Fiables   : {n_fiable:,} ({100*n_fiable/n_es:.1f}%)")
print(f"    Non fiables: {n_non_fiable:,} ({100*n_non_fiable/n_es:.1f}%)")
print(f"      dont 1900 (placeholder) : {n_1900:,}")

# OBJET_DEPOSE_OU_ABANDONNE breakdown
print(f"\n  OBJET_DEPOSE_OU_ABANDONNE dans les anomalies brutes :")
for val, cnt in anomalies_brut["OBJET_DEPOSE_OU_ABANDONNE"].value_counts().sort_index().items():
    print(f"    {val:>5} : {cnt:>6,}")
print(f"  → On garde 0 (actif) et -1 (depose apres anomalie), on exclut 1")


# ============================================================
# 2. PROFIL PATRIMONIAL - MATERIAUX
# ============================================================
print("\n[2/8] Profil patrimonial - Materiaux...")

mat_stats = cana_es.groupby("MATERIAU").agg(
    nb_troncons=("OBJET", "count"),
    longueur_totale=("LONGUEUR", "sum"),
    age_moyen=("age", "mean"),
    age_median=("age", "median"),
    diametre_moyen=("DIAMETRE", "mean"),
).sort_values("longueur_totale", ascending=False)

mat_stats["pct_troncons"] = 100 * mat_stats["nb_troncons"] / n_es
mat_stats["pct_longueur"] = 100 * mat_stats["longueur_totale"] / mat_stats["longueur_totale"].sum()

print("\n  Repartition par materiau :")
for mat, row in mat_stats.iterrows():
    print(f"    {mat:>6s} : {row['nb_troncons']:>6,.0f} troncons ({row['pct_troncons']:5.1f}%) | "
          f"{row['longueur_totale']/1000:>8,.1f} km ({row['pct_longueur']:5.1f}%) | "
          f"age moyen: {row['age_moyen']:>5.1f} ans")

longueur_totale_km = cana_es["LONGUEUR"].sum() / 1000
print(f"\n  Longueur totale du reseau EN SERVICE : {longueur_totale_km:,.1f} km")

# --- Figure 1 : Repartition materiaux ---
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

mat_plot = mat_stats.head(8)
axes[0].barh(mat_plot.index, mat_plot["pct_longueur"], color=COLORS[:len(mat_plot)])
axes[0].set_xlabel("% du lineaire total")
axes[0].set_title("Repartition du lineaire par materiau")
axes[0].invert_yaxis()

axes[1].barh(mat_plot.index, mat_plot["pct_troncons"], color=COLORS[:len(mat_plot)])
axes[1].set_xlabel("% des troncons")
axes[1].set_title("Repartition des troncons par materiau")
axes[1].invert_yaxis()

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "01_materiaux_repartition.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure sauvee : 01_materiaux_repartition.png")


# ============================================================
# 3. COHORTES AGE x MATERIAU
# ============================================================
print("\n[3/8] Cohortes age x materiau...")

cana_fiable = cana_es[cana_es["date_fiable"]].copy()

cohorte = cana_fiable.groupby(["MATERIAU", "decennie_pose"]).agg(
    nb_troncons=("OBJET", "count"),
    longueur_km=("LONGUEUR", lambda x: x.sum() / 1000),
).reset_index()

top_mats = mat_stats.head(6).index.tolist()
cohorte_top = cohorte[cohorte["MATERIAU"].isin(top_mats)]

# --- Figure 2 : Cohortes ---
fig, ax = plt.subplots(figsize=(16, 7))
pivot = cohorte_top.pivot_table(
    index="decennie_pose", columns="MATERIAU", values="longueur_km", fill_value=0
)
pivot = pivot.reindex(columns=top_mats)
pivot.plot(kind="bar", stacked=True, ax=ax, color=COLORS[:len(top_mats)], width=0.8)
ax.set_xlabel("Decennie de pose")
ax.set_ylabel("Lineaire (km)")
ax.set_title(f"Cohortes : lineaire pose par decennie et materiau (ref {ANNEE_REF})")
ax.legend(title="Materiau", bbox_to_anchor=(1.02, 1), loc="upper left")
ax.set_xticklabels([str(int(x)) for x in pivot.index], rotation=45)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "02_cohortes_age_materiau.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure sauvee : 02_cohortes_age_materiau.png")

# Cohortes a risque
print("\n  Cohortes a risque (FTG, FT avant 1980) :")
risque = cohorte_top[
    (cohorte_top["MATERIAU"].isin(["FTG", "FT", "A.C"])) &
    (cohorte_top["decennie_pose"] <= 1980)
].sort_values("longueur_km", ascending=False)
for _, row in risque.head(10).iterrows():
    age_cohorte = ANNEE_REF - row["decennie_pose"] - 5  # milieu de decennie
    print(f"    {row['MATERIAU']} {int(row['decennie_pose'])}s : "
          f"{row['longueur_km']:,.1f} km ({row['nb_troncons']:,} troncons) — ~{age_cohorte:.0f} ans")


# ============================================================
# 4. ANALYSE DES ANOMALIES
# ============================================================
print("\n[4/8] Analyse des anomalies...")

print(f"\n  Types d'anomalies (sur anomalies retenues) :")
for t, c in anom_actives["TYPE_ANOMALIE"].value_counts().items():
    print(f"    {t} : {c:,} ({100*c/len(anom_actives):.1f}%)")

# Evolution des anomalies par an
anom_par_an = anom_actives.groupby("annee_Anomalie").size().reset_index(name="nb_anomalies")
anom_par_an = anom_par_an[anom_par_an["annee_Anomalie"].between(1990, ANNEE_REF)]

# --- Figure 3 : Evolution anomalies ---
fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(anom_par_an["annee_Anomalie"], anom_par_an["nb_anomalies"], color=COLORS[3])
ax.set_xlabel("Annee")
ax.set_ylabel("Nombre d'anomalies")
ax.set_title(f"Evolution du nombre d'anomalies par an (1990-{ANNEE_REF})")
ax.axhline(y=anom_par_an["nb_anomalies"].mean(), color="red", linestyle="--",
           label=f"Moyenne : {anom_par_an['nb_anomalies'].mean():.0f}/an")
ax.legend()
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "03_evolution_anomalies.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure sauvee : 03_evolution_anomalies.png")

# Evolution par type
anom_type_an = anom_actives.groupby(["annee_Anomalie", "TYPE_ANOMALIE"]).size().reset_index(name="nb")
anom_type_an = anom_type_an[anom_type_an["annee_Anomalie"].between(1990, ANNEE_REF)]

fig, ax = plt.subplots(figsize=(14, 5))
for i, t in enumerate(anom_actives["TYPE_ANOMALIE"].value_counts().head(5).index):
    sub = anom_type_an[anom_type_an["TYPE_ANOMALIE"] == t]
    ax.plot(sub["annee_Anomalie"], sub["nb"], marker="o", markersize=3, label=t, color=COLORS[i])
ax.set_xlabel("Annee")
ax.set_ylabel("Nombre d'anomalies")
ax.set_title("Evolution des anomalies par type")
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "04_anomalies_par_type.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure sauvee : 04_anomalies_par_type.png")


# ============================================================
# 5. JOINTURE & TAUX DE CASSE PAR MATERIAU
# ============================================================
print("\n[5/8] Taux de casse par materiau...")

n_avec_anomalie = cana_es["a_casse"].sum()
print(f"  Troncons EN SERVICE avec au moins 1 anomalie : {n_avec_anomalie:,} ({100*n_avec_anomalie/n_es:.1f}%)")
print(f"  Troncons EN SERVICE sans anomalie             : {n_es - n_avec_anomalie:,} ({100*(n_es-n_avec_anomalie)/n_es:.1f}%)")

mat_casse = cana_es.groupby("MATERIAU").agg(
    nb_troncons=("OBJET", "count"),
    nb_avec_casse=("a_casse", "sum"),
    nb_anomalies_total=("nb_anomalies", "sum"),
    longueur_totale_km=("LONGUEUR", lambda x: x.sum() / 1000),
).reset_index()
mat_casse["taux_casse_pct"] = 100 * mat_casse["nb_avec_casse"] / mat_casse["nb_troncons"]
mat_casse["anomalies_par_km"] = mat_casse["nb_anomalies_total"] / mat_casse["longueur_totale_km"]
mat_casse = mat_casse.sort_values("anomalies_par_km", ascending=False)

print(f"\n  Taux de casse et densite d'anomalies par materiau :")
for _, row in mat_casse.iterrows():
    if row["nb_troncons"] >= 50:
        print(f"    {row['MATERIAU']:>6s} : {row['taux_casse_pct']:5.1f}% des troncons ont casse | "
              f"{row['anomalies_par_km']:5.2f} anomalies/km")

# --- Figure 5 : Taux de casse par materiau ---
mat_casse_sig = mat_casse[mat_casse["nb_troncons"] >= 50].sort_values("taux_casse_pct", ascending=True)
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

axes[0].barh(mat_casse_sig["MATERIAU"], mat_casse_sig["taux_casse_pct"], color=COLORS[1])
axes[0].set_xlabel("% des troncons ayant eu au moins 1 anomalie")
axes[0].set_title("Taux de casse par materiau")

axes[1].barh(mat_casse_sig["MATERIAU"], mat_casse_sig["anomalies_par_km"], color=COLORS[4])
axes[1].set_xlabel("Anomalies / km")
axes[1].set_title("Densite d'anomalies par materiau")

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "05_taux_casse_materiau.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure sauvee : 05_taux_casse_materiau.png")


# ============================================================
# 6. DISTRIBUTION DES AGES ET ETAT
# ============================================================
print("\n[6/8] Distribution des ages et etat...")

# --- Figure 6 : Distribution age par materiau ---
fig, ax = plt.subplots(figsize=(14, 6))
mat_for_box = cana_es[cana_es["date_fiable"] & cana_es["MATERIAU"].isin(top_mats)]
order = mat_for_box.groupby("MATERIAU")["age"].median().sort_values(ascending=False).index
sns.boxplot(data=mat_for_box, x="MATERIAU", y="age", order=order, palette="Set2", ax=ax)
ax.set_xlabel("Materiau")
ax.set_ylabel(f"Age (annees, ref {ANNEE_REF})")
ax.set_title("Distribution des ages par materiau (dates fiables uniquement)")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "06_distribution_age_materiau.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure sauvee : 06_distribution_age_materiau.png")

# --- ETAT normalise ---
print(f"\n  Etat des troncons EN SERVICE (normalise) :")
for e, c in cana_es["ETAT_CLEAN"].value_counts().items():
    print(f"    {e:>10s} : {c:,} ({100*c/n_es:.1f}%)")

# --- Figure 7 : Etat par materiau ---
etat_mat = cana_es[cana_es["MATERIAU"].isin(top_mats)].groupby(
    ["MATERIAU", "ETAT_CLEAN"]
).size().reset_index(name="count")

fig, ax = plt.subplots(figsize=(14, 6))
pivot_etat = etat_mat.pivot_table(index="MATERIAU", columns="ETAT_CLEAN", values="count", fill_value=0)
pivot_etat_pct = pivot_etat.div(pivot_etat.sum(axis=1), axis=0) * 100
# Ordre logique des etats
etat_order = [c for c in ["Bon", "Moyen", "Vetuste", "Inconnu"] if c in pivot_etat_pct.columns]
pivot_etat_pct[etat_order].plot(kind="barh", stacked=True, ax=ax, colormap="RdYlGn_r")
ax.set_xlabel("% des troncons")
ax.set_title("Etat des troncons par materiau (normalise)")
ax.legend(title="Etat", bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "07_etat_par_materiau.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure sauvee : 07_etat_par_materiau.png")


# ============================================================
# 7. QUALITE DES DONNEES
# ============================================================
print("\n[7/8] Rapport de qualite des donnees...")

print("\n  Taux de completude par champ :")
for col in ["POSE", "MATERIAU", "DIAMETRE", "ETAT", "LONGUEUR", "TERRAIN",
            "PROFONDEUR", "PRESSION_MAX", "PRESSION_MINI", "QUALITE_GEOMETRIE"]:
    if col not in cana_es.columns:
        continue
    n_non_null = cana_es[col].notna().sum()
    if cana_es[col].dtype == "object":
        n_non_vide = (cana_es[col].notna() & (cana_es[col].str.strip() != "")).sum()
    else:
        n_non_vide = n_non_null
    pct = 100 * n_non_vide / n_es
    print(f"    {col:>25s} : {pct:5.1f}% ({n_es - n_non_vide:,} manquants)")

# --- Figure 8 : Completude ---
completude = {}
for col in ["POSE", "MATERIAU", "DIAMETRE", "ETAT", "LONGUEUR", "TERRAIN",
            "PROFONDEUR", "PRESSION_MAX", "PRESSION_MINI", "QUALITE_GEOMETRIE"]:
    if col in cana_es.columns:
        if cana_es[col].dtype == "object":
            completude[col] = 100 * (cana_es[col].notna() & (cana_es[col].str.strip() != "")).sum() / n_es
        else:
            completude[col] = 100 * cana_es[col].notna().sum() / n_es

fig, ax = plt.subplots(figsize=(12, 5))
bars = ax.barh(list(completude.keys()), list(completude.values()), color=COLORS[2])
ax.set_xlabel("% de completude")
ax.set_title("Completude des champs - Troncons EN SERVICE")
ax.axvline(x=80, color="orange", linestyle="--", label="Seuil 80%")
ax.axvline(x=95, color="green", linestyle="--", label="Seuil 95%")
ax.legend()
for bar, val in zip(bars, completude.values()):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f"{val:.1f}%", va="center", fontsize=9)
ax.set_xlim(0, 110)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "08_completude_champs.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure sauvee : 08_completude_champs.png")


# ============================================================
# 8. SYNTHESE & TOP SINISTRES
# ============================================================
print("\n[8/8] Synthese...")

# Top sinistres
top_sinistres = cana_es.nlargest(10, "nb_anomalies")[
    ["OBJET", "MATERIAU", "annee_pose", "DIAMETRE", "nb_anomalies", "LONGUEUR", "ETAT_CLEAN"]
]

print(f"\n  TOP 10 TRONCONS LES PLUS SINISTRES :")
for _, row in top_sinistres.iterrows():
    dn = f"DN{row['DIAMETRE']:.0f}" if pd.notna(row["DIAMETRE"]) else "DN?"
    pose = f"{row['annee_pose']:.0f}" if pd.notna(row["annee_pose"]) else "?"
    print(f"    {row['OBJET']} : {row['MATERIAU']} {dn} "
          f"pose {pose} | {row['nb_anomalies']} anomalies | "
          f"etat: {row['ETAT_CLEAN']} | {row['LONGUEUR']:.0f}m")


# ============================================================
# SYNTHESE FINALE
# ============================================================
age_moyen = cana_es.loc[cana_es['date_fiable'], 'age'].mean()
print("\n" + "=" * 60)
print(f"SYNTHESE - ETAT DES LIEUX PATRIMONIAL (ref {ANNEE_REF})")
print("=" * 60)

print(f"""
RESEAU :
  - {n_es:,} troncons EN SERVICE
  - {longueur_totale_km:,.1f} km de lineaire total
  - {len(mat_stats)} materiaux presents

AGES (reference {ANNEE_REF}) :
  - {100*n_fiable/n_es:.0f}% des dates de pose sont fiables
  - Age moyen (dates fiables) : {age_moyen:.0f} ans

ANOMALIES :
  - {len(anom_actives):,} anomalies retenues (0 + -1, exclu 1 et annee>{ANNEE_REF})
  - {n_avec_anomalie:,} troncons ont eu au moins 1 anomalie ({100*n_avec_anomalie/n_es:.1f}%)
  - Moyenne : {anom_par_an['nb_anomalies'].mean():.0f} anomalies/an (1990-{ANNEE_REF})

1% DU LINEAIRE (objectif renouvellement minimum) :
  = {longueur_totale_km * 0.01:,.1f} km / an
""")

print(f"Figures sauvegardees dans : {OUTPUT_DIR}/")
print("=" * 60)

# Sauvegarder les stats en CSV
mat_stats.to_csv(OUTPUT_DIR / "stats_materiaux.csv")
mat_casse.to_csv(OUTPUT_DIR / "stats_casse_materiau.csv", index=False)
top_sinistres.to_csv(OUTPUT_DIR / "top_sinistres.csv", index=False)
anom_par_an.to_csv(OUTPUT_DIR / "anomalies_par_an.csv", index=False)
print("CSV de stats sauvegardes dans output/")


# ============================================================
# RAPPORT MARKDOWN
# ============================================================
rapport = f"""# Rapport EDA - Etat des lieux patrimonial

**Projet :** Prediction de casses de canalisations d'eau
**Date :** {ANNEE_REF}
**Annee de reference :** {ANNEE_REF}
**Phase :** 1 - Analyse exploratoire et etat des lieux

---

## 1. Perimetre des donnees

| Indicateur | Valeur |
|-----------|--------|
| Troncons total | {n_total:,} |
| Troncons EN SERVICE | {n_es:,} |
| Lineaire total EN SERVICE | {longueur_totale_km:,.1f} km |
| Anomalies retenues | {len(anom_actives):,} |
| Periode couverte | 1990 - {ANNEE_REF} |
| Dates de pose fiables | {100*n_fiable/n_es:.0f}% |

**Filtre anomalies :** OBJET_DEPOSE_OU_ABANDONNE != 1 (garde 0=actif et -1=depose apres anomalie). Annee > {ANNEE_REF} exclue.

## 2. Profil patrimonial — Materiaux

| Materiau | Troncons | % troncons | Lineaire (km) | % lineaire | Age moyen |
|----------|---------|-----------|--------------|-----------|----------|
"""

for mat, row in mat_stats.head(10).iterrows():
    rapport += f"| {mat} | {row['nb_troncons']:,.0f} | {row['pct_troncons']:.1f}% | {row['longueur_totale']/1000:,.1f} km | {row['pct_longueur']:.1f}% | {row['age_moyen']:.0f} ans |\n"

rapport += f"""
## 3. Anomalies

- {n_avec_anomalie:,} troncons EN SERVICE avec au moins 1 anomalie ({100*n_avec_anomalie/n_es:.1f}%)
- Moyenne : {anom_par_an['nb_anomalies'].mean():.0f} anomalies/an
- Evenement rare → adapte au modele de survie

## 4. Chiffres cles

| Indicateur | Valeur |
|-----------|--------|
| Lineaire total | {longueur_totale_km:,.1f} km |
| 1% reglementaire minimum | {longueur_totale_km * 0.01:,.1f} km/an |
| Age moyen du reseau | {age_moyen:.0f} ans |
| Troncons sinistres | {100*n_avec_anomalie/n_es:.1f}% |

---
*Rapport genere automatiquement — Phase 1 (ref {ANNEE_REF})*
"""

with open(OUTPUT_DIR / "rapport_eda_phase1.md", "w", encoding="utf-8") as f:
    f.write(rapport)
print("Rapport markdown sauvegarde : rapport_eda_phase1.md")
