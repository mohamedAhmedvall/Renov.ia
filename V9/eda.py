"""
V9 — Analyse exploratoire (EDA).
Génère 6 plots interprétables sur le risque de fuite, en intégrant l'aléa argile.
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from data_prep import load_raw, build_features, ANNEE_REF

DATA_DIR = Path(__file__).parent.parent / "data"
OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

print("=" * 60)
print("V9 — EDA")
print("=" * 60)

cana, fuites, argile = load_raw(DATA_DIR)

# On construit un dataset à observation_year=2018 pour avoir 6 ans de recul
df, _, _, _ = build_features(cana, fuites, argile, observation_year=2018, horizon=3)
print(f"\n  Dataset @obs=2018, h=3 : {len(df):,} | taux positif={df['y'].mean()*100:.2f}%")

# ============================================================
# Plot 1 — Taux de fuite par tranche d'âge
# ============================================================
df_age = df[df["age_imputed"] == 0].copy()
df_age["age_bin"] = pd.cut(df_age["age"], bins=[0, 20, 40, 60, 80, 100, 200],
                           labels=["0-20", "20-40", "40-60", "60-80", "80-100", "100+"])
g = df_age.groupby("age_bin", observed=True)["y"].agg(["mean", "count"])
g["mean"] *= 100

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(g.index.astype(str), g["mean"], color="steelblue", alpha=0.8)
ax.set_xlabel("Âge du tronçon (ans)")
ax.set_ylabel("% tronçons avec ≥1 fuite (3 ans)")
ax.set_title("Taux de fuite par tranche d'âge — obs 2018, horizon 3 ans")
for bar, n in zip(bars, g["count"]):
    ax.annotate(f"n={n:,}", (bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05),
                ha="center", fontsize=8)
plt.tight_layout()
plt.savefig(OUT / "eda_01_age.png", dpi=140)
plt.close()
print("  => eda_01_age.png")

# ============================================================
# Plot 2 — Taux de fuite par famille matériau
# ============================================================
g = df.groupby("famille_mat")["y"].agg(["mean", "count"]).sort_values("mean", ascending=True)
g["mean"] *= 100
g = g[g["count"] > 100]  # filtrer familles rares

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(g.index, g["mean"], color="darkred", alpha=0.8)
ax.set_xlabel("% tronçons avec ≥1 fuite (3 ans)")
ax.set_title("Taux de fuite par famille de matériau")
for bar, n in zip(bars, g["count"]):
    ax.annotate(f" n={n:,}", (bar.get_width(), bar.get_y() + bar.get_height()/2),
                va="center", fontsize=8)
plt.tight_layout()
plt.savefig(OUT / "eda_02_famille.png", dpi=140)
plt.close()
print("  => eda_02_famille.png")

# ============================================================
# Plot 3 — Effet de l'aléa argile (la nouvelle feature)
# ============================================================
df_arg = df[df["alea_argile"].notna()].copy()
g = df_arg.groupby("alea_argile")["y"].agg(["mean", "count"]).reindex(["nul", "moyen", "fort"])
g["mean"] *= 100

fig, ax = plt.subplots(figsize=(7, 5))
colors = ["#2ca02c", "#ff7f0e", "#d62728"]
bars = ax.bar(g.index, g["mean"], color=colors, alpha=0.85)
ax.set_xlabel("Aléa retrait-gonflement argile (RGA)")
ax.set_ylabel("% tronçons avec ≥1 fuite (3 ans)")
ax.set_title("Effet de l'aléa argile sur le taux de fuite")
for bar, m, n in zip(bars, g["mean"], g["count"]):
    ax.annotate(f"{m:.2f}%\nn={n:,}",
                (bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02),
                ha="center", fontsize=9)
gain = (g.loc["fort", "mean"] / g.loc["nul", "mean"]) if g.loc["nul", "mean"] > 0 else 0
ax.text(0.5, 0.95, f"Ratio fort/nul = ×{gain:.2f}",
        transform=ax.transAxes, ha="center", fontsize=10,
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.7))
plt.tight_layout()
plt.savefig(OUT / "eda_03_argile.png", dpi=140)
plt.close()
print(f"  => eda_03_argile.png  (ratio fort/nul = ×{gain:.2f})")

# ============================================================
# Plot 4 — Interaction argile × famille (heatmap)
# ============================================================
piv = df_arg.pivot_table(index="famille_mat", columns="alea_argile",
                         values="y", aggfunc="mean") * 100
piv = piv.reindex(columns=["nul", "moyen", "fort"])
piv = piv.dropna(how="all")

fig, ax = plt.subplots(figsize=(7, 5))
im = ax.imshow(piv.values, cmap="YlOrRd", aspect="auto")
ax.set_xticks(range(len(piv.columns)))
ax.set_xticklabels(piv.columns)
ax.set_yticks(range(len(piv.index)))
ax.set_yticklabels(piv.index)
ax.set_title("Taux de fuite (%) — Famille × Aléa argile")
for i in range(len(piv.index)):
    for j in range(len(piv.columns)):
        v = piv.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                    color="white" if v > piv.values[~np.isnan(piv.values)].mean() else "black",
                    fontsize=9)
plt.colorbar(im, label="% fuites")
plt.tight_layout()
plt.savefig(OUT / "eda_04_heatmap_famille_argile.png", dpi=140)
plt.close()
print("  => eda_04_heatmap_famille_argile.png")

# ============================================================
# Plot 5 — Récidive : effet de l'historique de fuites
# ============================================================
df["nb_fuites_bin"] = pd.cut(df["nb_fuites_avant"], bins=[-0.5, 0.5, 1.5, 3.5, 1000],
                              labels=["0", "1", "2-3", "4+"])
g = df.groupby("nb_fuites_bin", observed=True)["y"].agg(["mean", "count"])
g["mean"] *= 100

fig, ax = plt.subplots(figsize=(7, 5))
bars = ax.bar(g.index.astype(str), g["mean"], color="purple", alpha=0.8)
ax.set_xlabel("Nombre de fuites avant 2018")
ax.set_ylabel("% tronçons avec ≥1 fuite (2018-2021)")
ax.set_title("Récidive — l'historique de casses prédit-il l'avenir ?")
for bar, m, n in zip(bars, g["mean"], g["count"]):
    ax.annotate(f"{m:.2f}%\nn={n:,}",
                (bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1),
                ha="center", fontsize=8)
plt.tight_layout()
plt.savefig(OUT / "eda_05_recidive.png", dpi=140)
plt.close()
print("  => eda_05_recidive.png")

# ============================================================
# Plot 6 — Évolution temporelle du nombre de fuites
# ============================================================
fuites_yr = fuites.groupby("annee_Anomalie").size()
fuites_yr = fuites_yr[(fuites_yr.index >= 2000) & (fuites_yr.index <= 2024)]

fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(fuites_yr.index.astype(int), fuites_yr.values, color="steelblue", alpha=0.8)
ax.set_xlabel("Année")
ax.set_ylabel("Nombre de fuites détectées")
ax.set_title("Évolution annuelle des fuites — détection du régime stationnaire")
ax.axvline(2018, color="red", linestyle="--", alpha=0.5, label="obs=2018 (split V9)")
ax.legend()
plt.tight_layout()
plt.savefig(OUT / "eda_06_temporal.png", dpi=140)
plt.close()
print("  => eda_06_temporal.png")

# ============================================================
# Synthèse texte
# ============================================================
print("\n" + "=" * 60)
print("SYNTHÈSE EDA")
print("=" * 60)
print(f"  - Taux de base de fuite (h=3) : {df['y'].mean()*100:.2f}%")
print(f"  - Effet argile fort vs nul    : ×{gain:.2f}")
print(f"  - Familles à risque max       : {g.index.tolist()[-3:] if False else ''}")
top_fam = df.groupby("famille_mat")["y"].mean().sort_values(ascending=False).head(3)
print(f"  - Top 3 familles risquées     : {dict((k, f'{v*100:.1f}%') for k,v in top_fam.items())}")
print(f"  - Couverture argile           : {df['alea_argile'].notna().mean()*100:.1f}% des tronçons")
