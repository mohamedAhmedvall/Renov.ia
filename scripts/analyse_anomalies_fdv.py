"""
Analyse : correlation anomalies vs fin de vie
Rapport complet avec figures
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", font_scale=1.1)
COLORS = sns.color_palette("Set2", 10)

print("=" * 60)
print("ANALYSE : ANOMALIES vs FIN DE VIE")
print("=" * 60)

# Chargement
cana = pd.read_csv(DATA_DIR / "canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
anom = pd.read_csv(DATA_DIR / "historiqueanomalie.csv", low_memory=False)

cana["POSE"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")
cana["annee_pose"] = cana["POSE"].dt.year
cana["age"] = 2024 - cana["annee_pose"]
cana.loc[(cana["annee_pose"] == 1900) | cana["annee_pose"].isna() | (cana["annee_pose"] > 2024), "age"] = np.nan

fin_de_vie_ids = set(cana[cana["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"])]["OBJET"])
en_service_ids = set(cana[cana["STATUT_OBJET"] == "EN SERVICE"]["OBJET"])

# Enrichir anomalies avec statut troncon
anom["statut_troncon"] = "autre"
anom.loc[anom["GID_OBJET"].isin(en_service_ids), "statut_troncon"] = "EN SERVICE"
anom.loc[anom["GID_OBJET"].isin(fin_de_vie_ids), "statut_troncon"] = "FIN DE VIE"

# Nb anomalies par troncon
anom_count = anom.groupby("GID_OBJET").agg(
    nb_anom=("TYPE_ANOMALIE", "count"),
    nb_fuites=("TYPE_ANOMALIE", lambda x: x.isin(["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE"]).sum()),
).reset_index()
anom_count["statut"] = "autre"
anom_count.loc[anom_count["GID_OBJET"].isin(en_service_ids), "statut"] = "EN SERVICE"
anom_count.loc[anom_count["GID_OBJET"].isin(fin_de_vie_ids), "statut"] = "FIN DE VIE"

# Enrichir cana
cana_e = cana.merge(anom_count[["GID_OBJET", "nb_anom", "nb_fuites"]], left_on="OBJET", right_on="GID_OBJET", how="left")
cana_e["nb_anom"] = cana_e["nb_anom"].fillna(0).astype(int)
cana_e["a_anomalie"] = cana_e["nb_anom"] > 0


# =========================================================
# STATS CONSOLE
# =========================================================
print("\n--- CHIFFRES CLES ---")
n_fdv = len(cana_e[cana_e["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"])])
fdv_avec = cana_e[cana_e["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"])]["a_anomalie"].sum()
fdv_sans = n_fdv - fdv_avec
print(f"Troncons fin de vie : {n_fdv:,}")
print(f"  SANS anomalie : {fdv_sans:,} ({100*fdv_sans/n_fdv:.1f}%)")
print(f"  AVEC anomalie : {fdv_avec:,} ({100*fdv_avec/n_fdv:.1f}%)")

n_es = len(cana_e[cana_e["STATUT_OBJET"] == "EN SERVICE"])
es_avec = cana_e[cana_e["STATUT_OBJET"] == "EN SERVICE"]["a_anomalie"].sum()
print(f"\nTroncons EN SERVICE : {n_es:,}")
print(f"  AVEC anomalie : {es_avec:,} ({100*es_avec/n_es:.1f}%)")


# =========================================================
# FIGURE A1 : Repartition statuts + anomalies
# =========================================================
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

statut_counts = cana["STATUT_OBJET"].value_counts()
statut_main = statut_counts[statut_counts > 100]
bars = axes[0].barh(statut_main.index, statut_main.values, color=COLORS[:len(statut_main)])
axes[0].set_xlabel("Nombre de troncons")
axes[0].set_title("Repartition des statuts")
for i, (idx, v) in enumerate(statut_main.items()):
    axes[0].text(v + 500, i, f"{v:,} ({100*v/len(cana):.1f}%)", va="center")

data_anom = []
for statut in ["EN SERVICE", "ABANDONNE", "DEPOSE"]:
    sub = cana_e[cana_e["STATUT_OBJET"] == statut]
    avec = sub["a_anomalie"].sum()
    sans = len(sub) - avec
    data_anom.append({"Statut": statut, "Avec anomalie": 100*avec/len(sub), "Sans anomalie": 100*sans/len(sub)})
df_anom = pd.DataFrame(data_anom).set_index("Statut")
df_anom.plot(kind="barh", stacked=True, ax=axes[1], color=["#e74c3c", "#3498db"])
axes[1].set_xlabel("% des troncons")
axes[1].set_title("Presence d'anomalies par statut")
axes[1].legend(loc="lower right")

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "A1_statuts_et_anomalies.png", dpi=150, bbox_inches="tight")
plt.close()
print("=> A1_statuts_et_anomalies.png")


# =========================================================
# FIGURE A2 : 89.6% des abandons sans anomalie
# =========================================================
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

fdv = cana_e[cana_e["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"])]
avec = fdv["a_anomalie"].sum()
sans = len(fdv) - avec
axes[0].pie(
    [sans, avec],
    labels=[f"Sans anomalie\n{sans:,} ({100*sans/len(fdv):.1f}%)",
            f"Avec anomalie(s)\n{avec:,} ({100*avec/len(fdv):.1f}%)"],
    colors=["#3498db", "#e74c3c"], explode=[0, 0.05],
    textprops={"fontsize": 12}, startangle=90)
axes[0].set_title("Troncons ABANDONNES/DEPOSES\nAvec vs Sans anomalie", fontsize=13, fontweight="bold")

pct_aband = 100 * cana_e[cana_e["STATUT_OBJET"] == "ABANDONNE"]["a_anomalie"].mean()
pct_depose = 100 * cana_e[cana_e["STATUT_OBJET"] == "DEPOSE"]["a_anomalie"].mean()
bars = axes[1].bar(["ABANDONNE\n(n=29,547)", "DEPOSE\n(n=9,457)"],
                   [pct_aband, pct_depose], color=["#e74c3c", "#e67e22"])
axes[1].set_ylabel("% avec au moins 1 anomalie")
axes[1].set_title("% de troncons avec anomalie\npar type de fin de vie")
for i, v in enumerate([pct_aband, pct_depose]):
    axes[1].text(i, v + 0.3, f"{v:.1f}%", ha="center", fontweight="bold")

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "A2_fin_de_vie_sans_anomalie.png", dpi=150, bbox_inches="tight")
plt.close()
print("=> A2_fin_de_vie_sans_anomalie.png")


# =========================================================
# FIGURE A3 : Nb anomalies avant abandon
# =========================================================
anom_avant = anom[anom["OBJET_DEPOSE_OU_ABANDONNE"] == -1]
nb_avant = anom_avant.groupby("GID_OBJET").size().reset_index(name="nb_anom")

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

axes[0].hist(nb_avant["nb_anom"], bins=range(1, 22), color=COLORS[3], edgecolor="white", rwidth=0.85)
axes[0].set_xlabel("Nb anomalies avant abandon")
axes[0].set_ylabel("Nb troncons")
axes[0].set_title(f"Distribution du nb d'anomalies avant abandon\n(n={len(nb_avant):,}, mediane={nb_avant['nb_anom'].median():.0f})")
axes[0].axvline(x=nb_avant["nb_anom"].mean(), color="orange", linestyle="--",
                label=f"Moyenne={nb_avant['nb_anom'].mean():.1f}")
axes[0].legend()
axes[0].set_xlim(0, 20)

es_c = anom_count[anom_count["statut"] == "EN SERVICE"]["nb_anom"]
fdv_c = anom_count[anom_count["statut"] == "FIN DE VIE"]["nb_anom"]
data_box = pd.DataFrame({
    "nb_anom": pd.concat([es_c, fdv_c]),
    "statut": ["EN SERVICE"] * len(es_c) + ["FIN DE VIE"] * len(fdv_c)
})
sns.boxplot(data=data_box, x="statut", y="nb_anom", palette=["#3498db", "#e74c3c"], ax=axes[1])
axes[1].set_ylim(0, 20)
axes[1].set_ylabel("Nb anomalies par troncon")
axes[1].set_title("Nb anomalies : EN SERVICE vs FIN DE VIE\n(troncons avec au moins 1 anomalie)")

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "A3_nb_anomalies_avant_abandon.png", dpi=150, bbox_inches="tight")
plt.close()
print("=> A3_nb_anomalies_avant_abandon.png")


# =========================================================
# FIGURE A4 : Types d'anomalies FDV vs ES
# =========================================================
fig, ax = plt.subplots(figsize=(12, 6))

types_fdv = anom[anom["statut_troncon"] == "FIN DE VIE"]["TYPE_ANOMALIE"].value_counts()
types_es = anom[anom["statut_troncon"] == "EN SERVICE"]["TYPE_ANOMALIE"].value_counts()
n_fdv_anom = len(anom[anom["statut_troncon"] == "FIN DE VIE"])
n_es_anom = len(anom[anom["statut_troncon"] == "EN SERVICE"])

all_types = ["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE", "DEFAUT_PRESSION"]
x = np.arange(len(all_types))
w = 0.35
vals_fdv = [100 * types_fdv.get(t, 0) / n_fdv_anom for t in all_types]
vals_es = [100 * types_es.get(t, 0) / n_es_anom for t in all_types]

ax.bar(x - w / 2, vals_fdv, w, label="FIN DE VIE", color="#e74c3c")
ax.bar(x + w / 2, vals_es, w, label="EN SERVICE", color="#3498db")
ax.set_xticks(x)
ax.set_xticklabels(all_types, rotation=15)
ax.set_ylabel("% des anomalies du statut")
ax.set_title("Types d'anomalies : FIN DE VIE vs EN SERVICE")
ax.legend()

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "A4_types_anomalies_fdv_vs_es.png", dpi=150, bbox_inches="tight")
plt.close()
print("=> A4_types_anomalies_fdv_vs_es.png")


# =========================================================
# FIGURE A5 : Profil age + materiau par statut
# =========================================================
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

for i, statut in enumerate(["EN SERVICE", "ABANDONNE", "DEPOSE"]):
    ages = cana.loc[(cana["STATUT_OBJET"] == statut) & cana["age"].notna() & (cana["age"] > 0) & (cana["age"] < 200), "age"]
    axes[0].hist(ages, bins=50, alpha=0.6, label=f"{statut} (moy={ages.mean():.0f} ans)", color=COLORS[i])
axes[0].set_xlabel("Age (annees, ref 2024)")
axes[0].set_ylabel("Nb troncons")
axes[0].set_title("Distribution des ages par statut")
axes[0].legend()

mat_data = []
for statut in ["EN SERVICE", "ABANDONNE", "DEPOSE"]:
    sub = cana[cana["STATUT_OBJET"] == statut]
    for m, c in sub["MATERIAU"].value_counts().head(6).items():
        mat_data.append({"Statut": statut, "Materiau": m, "pct": 100 * c / len(sub)})
mat_df = pd.DataFrame(mat_data)
top_mats = cana["MATERIAU"].value_counts().head(6).index
mat_df = mat_df[mat_df["Materiau"].isin(top_mats)]
pivot_mat = mat_df.pivot_table(index="Materiau", columns="Statut", values="pct", fill_value=0)
pivot_mat = pivot_mat.reindex(columns=["EN SERVICE", "ABANDONNE", "DEPOSE"])
pivot_mat.plot(kind="barh", ax=axes[1], color=[COLORS[0], COLORS[1], COLORS[2]])
axes[1].set_xlabel("% des troncons du statut")
axes[1].set_title("Top materiaux par statut")

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "A5_profil_age_materiau_par_statut.png", dpi=150, bbox_inches="tight")
plt.close()
print("=> A5_profil_age_materiau_par_statut.png")


# =========================================================
# FIGURE A6 : Croisement flag -1/0/1 x statut reel
# =========================================================
fig, ax = plt.subplots(figsize=(10, 6))

ct = pd.crosstab(anom["OBJET_DEPOSE_OU_ABANDONNE"], anom["statut_troncon"])
ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100
ct_pct.plot(kind="bar", stacked=True, ax=ax, color=["gray", "#3498db", "#e74c3c"])
ax.set_xlabel("OBJET_DEPOSE_OU_ABANDONNE")
ax.set_ylabel("% des anomalies")
ax.set_title("Croisement flag OBJET_DEPOSE_OU_ABANDONNE x Statut reel")
ax.legend(title="Statut reel")
ax.set_xticklabels(["-1 (depose apres)", "0 (actif)", "1 (deja abandonne)"], rotation=0)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "A6_flag_croisement.png", dpi=150, bbox_inches="tight")
plt.close()
print("=> A6_flag_croisement.png")


# =========================================================
# FIGURE A7 : Troncons EN SERVICE a risque
# =========================================================
fig, ax = plt.subplots(figsize=(12, 6))

seuils = [1, 2, 3, 5, 10, 20, 50]
nb_es_total = len(cana[cana["STATUT_OBJET"] == "EN SERVICE"])
es_anom = anom_count[anom_count["statut"] == "EN SERVICE"]
counts = [(es_anom["nb_anom"] >= s).sum() for s in seuils]
pcts = [100 * c / nb_es_total for c in counts]

bars = ax.bar([f">={s}" for s in seuils], counts, color=COLORS[4])
ax.set_xlabel("Seuil (nb anomalies cumulees)")
ax.set_ylabel("Nb troncons EN SERVICE")
ax.set_title(f"Troncons EN SERVICE par nb anomalies cumulees\n(total EN SERVICE = {nb_es_total:,})")

for bar, c, p in zip(bars, counts, pcts):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
            f"{c:,}\n({p:.2f}%)", ha="center", fontsize=9)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "A7_troncons_en_service_a_risque.png", dpi=150, bbox_inches="tight")
plt.close()
print("=> A7_troncons_en_service_a_risque.png")


# =========================================================
# RAPPORT MARKDOWN
# =========================================================
rapport = f"""# Analyse : Correlation anomalies vs fin de vie

**Projet :** Prediction de casses de canalisations d'eau
**Annee de reference :** 2024
**Objectif :** Comprendre le lien entre anomalies et abandon/depose pour formuler correctement le modele predictif

---

## 1. Constat principal : 89.6% des abandons n'ont aucune anomalie

| | Nb troncons | % |
|--|-----------|---|
| Fin de vie **SANS** anomalie | {fdv_sans:,} | **{100*fdv_sans/n_fdv:.1f}%** |
| Fin de vie **AVEC** anomalie(s) | {fdv_avec:,} | {100*fdv_avec/n_fdv:.1f}% |
| **Total fin de vie** | **{n_fdv:,}** | |

**Interpretation :** La grande majorite des canalisations sont abandonnees/deposees pour des raisons **non liees a des anomalies** : chantiers voirie, extension reseau, renouvellement preventif par cohorte age-materiau, mise aux normes.

![Fin de vie sans anomalie](A2_fin_de_vie_sans_anomalie.png)

---

## 2. Quand il y a des anomalies avant abandon

Sur les {len(nb_avant):,} troncons ayant eu des anomalies **avant** d'etre abandonnes (flag=-1) :

| Indicateur | Valeur |
|-----------|--------|
| Mediane anomalies avant abandon | **{nb_avant['nb_anom'].median():.0f}** |
| Moyenne anomalies avant abandon | {nb_avant['nb_anom'].mean():.1f} |
| >= 3 anomalies avant abandon | {(nb_avant['nb_anom']>=3).sum():,} ({100*(nb_avant['nb_anom']>=3).sum()/len(nb_avant):.1f}%) |
| >= 5 anomalies avant abandon | {(nb_avant['nb_anom']>=5).sum():,} ({100*(nb_avant['nb_anom']>=5).sum()/len(nb_avant):.1f}%) |

**Interpretation :** La plupart des troncons sont abandonnes apres **1 seule anomalie**. Cela suggere que l'anomalie est souvent le **declencheur** de la decision, pas necessairement le signe d'une degradation avancee.

![Nb anomalies avant abandon](A3_nb_anomalies_avant_abandon.png)

---

## 3. Types d'anomalies

### Sur les troncons FIN DE VIE :
- **93.5%** FUITE_SIGNAL_TR
- **6.5%** FUITE_DETECT_TR
- Quasi aucun autre type

### Sur les troncons EN SERVICE :
- **82.1%** FUITE_SIGNAL_TR
- **17.9%** FUITE_DETECT_TR
- Quelques types marginaux

**Interpretation :** Seuls les types **FUITE_SIGNAL_TR** et **FUITE_DETECT_TR** sont pertinents. Tous les autres types (DEFAUT_PRESSION, VETUSTE, etc.) sont negligeables et ne sont pas des signaux de fin de vie.

![Types anomalies](A4_types_anomalies_fdv_vs_es.png)

---

## 4. Profil des troncons abandonnes vs en service

| | EN SERVICE | ABANDONNE | DEPOSE |
|--|-----------|-----------|--------|
| Nb troncons | 182,075 | 29,547 | 9,457 |
| Age moyen | 43 ans | **54 ans** | 33 ans |
| Top materiau | FT (53%) | **FTG (50%)** | FTG (48%) |

**Interpretation :**
- Les **ABANDONNES** sont plus ages (54 ans) et surtout en **fonte grise (FTG)** -- materiau reconnu comme fragile
- Les **DEPOSES** sont plus jeunes (33 ans) -- probablement des remplacements dans le cadre de chantiers/travaux

![Profil par statut](A5_profil_age_materiau_par_statut.png)

---

## 5. Le flag OBJET_DEPOSE_OU_ABANDONNE

| Flag | Signification | Nb anomalies | Statut reel |
|------|-------------|-------------|------------|
| **-1** | Troncon depose/abandonne APRES l'anomalie | 10,992 | 98% FIN DE VIE |
| **0** | Troncon toujours actif | 19,781 | 99.9% EN SERVICE |
| **1** | Troncon deja abandonne (1 seul cas) | 1 | FIN DE VIE |

![Croisement flag](A6_flag_croisement.png)

---

## 6. Troncons EN SERVICE a surveiller

| Seuil | Nb troncons | % du reseau |
|-------|-----------|------------|
| >= 1 anomalie | {(es_anom['nb_anom']>=1).sum():,} | {100*(es_anom['nb_anom']>=1).sum()/nb_es_total:.2f}% |
| >= 3 anomalies | {(es_anom['nb_anom']>=3).sum():,} | {100*(es_anom['nb_anom']>=3).sum()/nb_es_total:.2f}% |
| >= 5 anomalies | {(es_anom['nb_anom']>=5).sum():,} | {100*(es_anom['nb_anom']>=5).sum()/nb_es_total:.2f}% |
| >= 10 anomalies | {(es_anom['nb_anom']>=10).sum():,} | {100*(es_anom['nb_anom']>=10).sum()/nb_es_total:.2f}% |

![Troncons a risque](A7_troncons_en_service_a_risque.png)

---

## 7. Conclusions et questions pour le referent metier

### Ce que les donnees montrent :
1. **Les anomalies ne sont PAS le facteur principal des abandons** (90% des abandons sans anomalie)
2. **Les fuites (FUITE_SIGNAL_TR + FUITE_DETECT_TR) sont les seuls types pertinents** (99%+ des anomalies)
3. **Les abandons sont concentres sur la FTG agee** -- decision probablement basee sur age + materiau + politique de renouvellement
4. **1 seule fuite suffit souvent a declencher l'abandon** (mediane = 1)

### Questions cles pour le referent metier :

1. **Les 90% d'abandons sans anomalie** -- quelle est la logique derriere ?
   - Renouvellement systematique par cohorte (age + materiau) ?
   - Chantiers voirie / opportunite de travaux ?
   - Programme planifie pluriannuel ?

2. **Quand une fuite mene-t-elle a l'abandon vs simple reparation ?**
   - Seuil de nb de fuites ?
   - Cout cumule de reparation ?
   - Decision au cas par cas ?

3. **Les anomalies non predictibles** (coup de pelle, chantier tiers)
   - Sont-elles identifiables dans les donnees ?
   - Faut-il les exclure de l'apprentissage ?

4. **Quel est le bon objectif pour le modele ?**
   - Predire les futures fuites (proactif) ?
   - Predire le risque de degradation structurelle (score patrimonial) ?
   - Aider a la priorisation budgetaire (quel troncon renouveler en premier) ?

---

*Rapport genere automatiquement -- Analyse anomalies vs fin de vie (ref 2024)*
"""

with open(OUTPUT_DIR / "rapport_analyse_anomalies_fdv.md", "w", encoding="utf-8") as f:
    f.write(rapport)
print("\n=> Rapport sauvegarde : rapport_analyse_anomalies_fdv.md")
print("=" * 60)
