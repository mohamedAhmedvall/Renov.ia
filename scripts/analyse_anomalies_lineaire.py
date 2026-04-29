"""
Analyse statistique complète — anomalies, abandons, fin de vie, risque.
Tout en LINEAIRE (m, km), avec quantiles et taux normalisés par exposition.

Sortie : CR/analyse/*.png + CR/analyse/rapport_anomalies_lineaire.md
"""

from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "CR" / "analyse"
OUT.mkdir(parents=True, exist_ok=True)

ANNEE_REF = 2024
FENETRE_LAMBDA = 10  # années pour le calcul de λ = fuites/km/an

# --- Style commun ---
plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 140,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
})
COL_ABDN = "#c0392b"
COL_DEP = "#7f8c8d"
COL_ES = "#27ae60"
COL_FU = "#e67e22"

FAM = {
    "FT": "Fonte", "FTG": "FonteGrise", "FTVI": "Fonte", "FTBLU": "Fonte",
    "FTTT": "Fonte", "FTTTVI": "Fonte",
    "PVC": "Plastique", "PEHD": "Plastique", "PEBD": "Plastique", "POLY": "Plastique",
    "A.C": "AmianteCiment", "AC": "AmianteCiment",
    "ACIE": "Acier", "FER": "Acier", "GALV": "Acier", "INOX": "Acier", "AFCO": "Acier",
    "BTM": "Beton", "BA": "Beton", "CENT": "Beton",
}

# ============================================================
# CHARGEMENT
# ============================================================
print("[1] Chargement…")
cana = pd.read_csv(DATA / "canalisation_sem_3_1_.csv", decimal=",", low_memory=False)
ano = pd.read_csv(DATA / "historiqueanomalie.csv", low_memory=False)

cana["POSE_dt"] = pd.to_datetime(cana["POSE"], format="mixed", dayfirst=True, errors="coerce")
cana["ABANDON_dt"] = pd.to_datetime(cana["ABANDON"], format="mixed", dayfirst=True, errors="coerce")
cana["DEPOSE_dt"] = pd.to_datetime(cana["DEPOSE"], format="mixed", dayfirst=True, errors="coerce")
cana["annee_pose"] = cana["POSE_dt"].dt.year
cana["annee_abandon"] = cana["ABANDON_dt"].dt.year
cana["annee_depose"] = cana["DEPOSE_dt"].dt.year
cana["LONGUEUR_m"] = pd.to_numeric(cana["LONGUEUR"], errors="coerce")
cana["DIAMETRE"] = pd.to_numeric(cana["DIAMETRE"], errors="coerce")
cana.loc[cana["DIAMETRE"] == 0, "DIAMETRE"] = np.nan
cana["famille"] = cana["MATERIAU"].map(FAM).fillna("Autre")
cana["decennie"] = (cana["annee_pose"] // 10) * 10

ano["annee_Anomalie"] = pd.to_numeric(ano["annee_Anomalie"], errors="coerce").astype("Int64")
fu = ano[
    ano["TYPE_ANOMALIE"].isin(["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE"])
    & ano["annee_Anomalie"].notna()
    & (ano["annee_Anomalie"] <= ANNEE_REF)
].copy()

km_total = cana["LONGUEUR_m"].sum() / 1000
print(f"  Total : {len(cana):,} tronçons / {km_total:.1f} km")
print(f"  Fuites filtrées : {len(fu):,}")

# ============================================================
# § 1. RÉPARTITION DU RÉSEAU PAR STATUT
# ============================================================
print("[2] Répartition par statut…")
g_stat = (
    cana.groupby("STATUT_OBJET")
    .agg(n=("OBJET", "count"), km=("LONGUEUR_m", lambda s: s.sum() / 1000))
    .sort_values("km", ascending=False)
)
g_stat.to_csv(OUT / "01_repartition_statut.csv")

fig, ax = plt.subplots(figsize=(8, 4.5))
g_stat["km"].plot(kind="barh", ax=ax, color=[COL_ES, COL_ABDN, COL_DEP, "#bdc3c7", "#bdc3c7", "#bdc3c7"])
for i, v in enumerate(g_stat["km"]):
    ax.text(v + 30, i, f"{v:.0f} km", va="center", fontsize=9)
ax.set_xlabel("Linéaire (km)")
ax.set_title(f"Répartition du réseau par statut (total = {km_total:.0f} km)")
plt.tight_layout()
plt.savefig(OUT / "01_repartition_statut.png")
plt.close()

# ============================================================
# § 2. CENSURE — date premier enregistrement vs date abandon
# ============================================================
print("[3] Censure historique…")
fu_yr = fu["annee_Anomalie"].dropna().astype(int)
ab_yr = cana.loc[cana["STATUT_OBJET"] == "ABANDONNE", "annee_abandon"].dropna().astype(int)

fig, ax = plt.subplots(figsize=(10, 4.5))
years = np.arange(1960, 2026)
n_fu = fu_yr.value_counts().reindex(years, fill_value=0)
n_ab = ab_yr.value_counts().reindex(years, fill_value=0)
ax.bar(years - 0.2, n_fu, width=0.4, label="Fuites enregistrées", color=COL_FU)
ax.bar(years + 0.2, n_ab, width=0.4, label="Tronçons abandonnés", color=COL_ABDN)
ax.set_xlabel("Année")
ax.set_ylabel("Nb événements / an")
ax.set_title("Timeline : enregistrements de fuites vs abandons (montée en charge du SI)")
ax.legend()
plt.tight_layout()
plt.savefig(OUT / "02_timeline_capture.png")
plt.close()

# ============================================================
# § 3. ABANDONNE vs DEPOSE — différence sémantique
# ============================================================
print("[4] ABANDONNE vs DEPOSE…")

ab = cana[cana["STATUT_OBJET"] == "ABANDONNE"].copy()
ab["age_evt"] = ab["annee_abandon"] - ab["annee_pose"]
dp = cana[cana["STATUT_OBJET"] == "DEPOSE"].copy()
dp["age_evt"] = dp["annee_depose"] - dp["annee_pose"]

# Distribution âge à l'événement, pondéré linéaire
def weighted_quantiles(values, weights, q):
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    m = ~np.isnan(v) & ~np.isnan(w) & (w > 0)
    v, w = v[m], w[m]
    o = np.argsort(v)
    v, w = v[o], w[o]
    cw = np.cumsum(w)
    return [float(v[np.searchsorted(cw, q_i * cw[-1])]) for q_i in q]

stats_evt = []
for label, df in [("ABANDONNE", ab), ("DEPOSE", dp)]:
    qs = weighted_quantiles(df["age_evt"], df["LONGUEUR_m"], [.05, .25, .5, .75, .95])
    stats_evt.append({
        "statut": label, "n": len(df), "km": df["LONGUEUR_m"].sum() / 1000,
        "age_p5": qs[0], "age_p25": qs[1], "age_med": qs[2], "age_p75": qs[3], "age_p95": qs[4],
    })
df_stats_evt = pd.DataFrame(stats_evt)
df_stats_evt.to_csv(OUT / "03_abandonne_vs_depose.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
for ax, (label, df, color) in zip(axes, [("ABANDONNE", ab, COL_ABDN), ("DEPOSE", dp, COL_DEP)]):
    a = df["age_evt"].dropna()
    a = a[(a >= 0) & (a <= 120)]
    w = df.loc[a.index, "LONGUEUR_m"]
    ax.hist(a, bins=40, weights=w / 1000, color=color, edgecolor="white")
    qs = weighted_quantiles(a, w, [.25, .5, .75])
    for q, lab in zip(qs, ["P25", "médiane", "P75"]):
        ax.axvline(q, color="black", lw=1, ls="--", alpha=0.7)
        ax.text(q, ax.get_ylim()[1] * 0.95, f"{lab}={q:.0f}", ha="center", fontsize=8)
    km = df["LONGUEUR_m"].sum() / 1000
    ax.set_title(f"{label}  —  {len(df):,} tronçons / {km:.0f} km")
    ax.set_xlabel("Âge à l'événement (ans)")
    ax.set_ylabel("Linéaire (km)")
plt.suptitle("Distribution de l'âge au moment de la sortie (pondérée linéaire)", y=1.02)
plt.tight_layout()
plt.savefig(OUT / "03_age_sortie_dist.png", bbox_inches="tight")
plt.close()

# ============================================================
# § 4. ABANDONNE — fuite avant abandon ?
# ============================================================
print("[5] Fuites avant abandon…")
fu_with_ab = fu.merge(
    cana[["OBJET", "annee_abandon", "LONGUEUR_m"]],
    left_on="GID_OBJET", right_on="OBJET", how="left",
)
fu_avant_ab = fu_with_ab[fu_with_ab["annee_Anomalie"] < fu_with_ab["annee_abandon"]]
nb_av = fu_avant_ab.groupby("GID_OBJET").size().rename("nb_fuites_avant")
last_av = fu_avant_ab.groupby("GID_OBJET")["annee_Anomalie"].max().rename("last_fuite")
ab = ab.merge(nb_av, left_on="OBJET", right_index=True, how="left")
ab = ab.merge(last_av, left_on="OBJET", right_index=True, how="left")
ab["nb_fuites_avant"] = ab["nb_fuites_avant"].fillna(0).astype(int)
ab["delai_last_fuite"] = ab["annee_abandon"] - ab["last_fuite"]
ab["a_eu_fuite"] = ab["nb_fuites_avant"] > 0

km_ab_tot = ab["LONGUEUR_m"].sum() / 1000
km_ab_fu = ab.loc[ab["a_eu_fuite"], "LONGUEUR_m"].sum() / 1000
n_ab_fu = int(ab["a_eu_fuite"].sum())

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
# Camembert effectif vs linéaire
labels = ["≥1 fuite avant abandon", "Aucune fuite enregistrée"]
colors = [COL_FU, "#d5dbdb"]
ax1 = axes[0]
ax1.pie([n_ab_fu, len(ab) - n_ab_fu], labels=labels, colors=colors, autopct="%.1f%%",
        startangle=90, wedgeprops=dict(width=0.4))
ax1.set_title(f"Effectif (n={len(ab):,})")
ax2 = axes[1]
ax2.pie([km_ab_fu, km_ab_tot - km_ab_fu], labels=labels, colors=colors, autopct="%.1f%%",
        startangle=90, wedgeprops=dict(width=0.4))
ax2.set_title(f"Linéaire (km={km_ab_tot:.0f})")
plt.suptitle("Tronçons abandonnés : avec / sans fuite enregistrée avant abandon", y=1.02)
plt.tight_layout()
plt.savefig(OUT / "04_abandon_avec_sans_fuite.png", bbox_inches="tight")
plt.close()

# Délai dernière fuite → abandon (parmi ceux qui ont eu une fuite)
fig, ax = plt.subplots(figsize=(9, 4.5))
sub = ab[ab["a_eu_fuite"]].copy()
delais = sub["delai_last_fuite"].dropna()
weights = sub.loc[delais.index, "LONGUEUR_m"] / 1000
ax.hist(delais.clip(upper=40), bins=np.arange(0, 42, 1), weights=weights, color=COL_FU, edgecolor="white")
qs = weighted_quantiles(delais, sub.loc[delais.index, "LONGUEUR_m"], [.25, .5, .75])
for q, lab in zip(qs, ["P25", "médiane", "P75"]):
    ax.axvline(q, ls="--", color="black", lw=1, alpha=0.7)
    ax.text(q, ax.get_ylim()[1] * 0.92, f"{lab}={q:.0f}", ha="center", fontsize=9)
ax.set_xlabel("Années entre dernière fuite et abandon")
ax.set_ylabel("Linéaire abandonné (km)")
ax.set_title(f"Délai dernière fuite → abandon (km abandonné = {km_ab_fu:.0f} km)")
plt.tight_layout()
plt.savefig(OUT / "05_delai_fuite_abandon.png")
plt.close()

# ============================================================
# § 5. EN SERVICE — λ = fuites/km/an par cohorte × matériau
# ============================================================
print("[6] λ fuites/km/an…")
es = cana[cana["STATUT_OBJET"] == "EN SERVICE"].copy()
fu_es = fu[fu["GID_OBJET"].isin(es["OBJET"])]
fu_recent = fu_es[
    (fu_es["annee_Anomalie"] >= ANNEE_REF - FENETRE_LAMBDA)
    & (fu_es["annee_Anomalie"] < ANNEE_REF)
]
nb = fu_recent.groupby("GID_OBJET").size().rename("nb_fu_recent")
es = es.merge(nb, left_on="OBJET", right_index=True, how="left")
es["nb_fu_recent"] = es["nb_fu_recent"].fillna(0)


def agg_lambda(g):
    km = g["LONGUEUR_m"].sum() / 1000
    nb = g["nb_fu_recent"].sum()
    return pd.Series({"km": km, "nb_fuites": nb,
                      "lam": (nb / (km * FENETRE_LAMBDA)) if km > 0 else np.nan})


lam_fam = es.groupby("famille").apply(agg_lambda, include_groups=False).round(4)
lam_fam = lam_fam.sort_values("lam", ascending=False)
lam_fam.to_csv(OUT / "06_lambda_par_famille.csv")

fig, ax = plt.subplots(figsize=(9, 4.5))
colors = ["#c0392b" if l > 0.20 else "#e67e22" if l > 0.10 else "#27ae60" for l in lam_fam["lam"]]
bars = ax.barh(lam_fam.index, lam_fam["lam"], color=colors)
for bar, (fam, row) in zip(bars, lam_fam.iterrows()):
    ax.text(row["lam"] + 0.005, bar.get_y() + bar.get_height() / 2,
            f"{row['lam']:.3f}  ({row['km']:.0f} km, {int(row['nb_fuites'])} fuites)",
            va="center", fontsize=9)
ax.set_xlabel("λ = fuites / km / an")
ax.set_title(f"Taux de fuite normalisé par famille — réseau EN SERVICE, fenêtre {ANNEE_REF - FENETRE_LAMBDA}–{ANNEE_REF - 1}")
plt.tight_layout()
plt.savefig(OUT / "06_lambda_par_famille.png", bbox_inches="tight")
plt.close()

# Cohorte × famille (heatmap)
print("[7] Heatmap cohorte × famille…")
es_ok = es.dropna(subset=["decennie"])
lam_pivot = (
    es_ok.groupby(["decennie", "famille"]).apply(agg_lambda, include_groups=False)["lam"]
    .unstack("famille")
)
km_pivot = (
    es_ok.groupby(["decennie", "famille"]).apply(agg_lambda, include_groups=False)["km"]
    .unstack("famille")
)
# Filtrer cellules avec <2 km exposition (bruit)
mask_lowexp = km_pivot < 2
lam_pivot_show = lam_pivot.where(~mask_lowexp)
lam_pivot.to_csv(OUT / "07_lambda_cohorte_famille.csv")

fig, ax = plt.subplots(figsize=(10, 6))
mat = lam_pivot_show.values
im = ax.imshow(mat, aspect="auto", cmap="OrRd", vmin=0, vmax=0.5)
ax.set_xticks(range(len(lam_pivot_show.columns)))
ax.set_xticklabels(lam_pivot_show.columns, rotation=30, ha="right")
ax.set_yticks(range(len(lam_pivot_show.index)))
ax.set_yticklabels([int(d) for d in lam_pivot_show.index])
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        v = mat[i, j]
        if not np.isnan(v):
            km_v = km_pivot.values[i, j]
            ax.text(j, i, f"{v:.2f}\n{km_v:.0f}km", ha="center", va="center",
                    fontsize=7, color="white" if v > 0.25 else "black")
ax.set_xlabel("Famille matériau")
ax.set_ylabel("Décennie de pose")
ax.set_title("λ fuites/km/an — démêlage âge × matériau (cellules <2 km masquées)")
plt.colorbar(im, ax=ax, label="λ")
plt.tight_layout()
plt.savefig(OUT / "07_lambda_cohorte_famille.png", bbox_inches="tight")
plt.close()

# ============================================================
# § 6. PROXY TRANSPORT vs DISTRIBUTION vs BRANCHEMENTS via diamètre/longueur
# ============================================================
print("[8] Proxy transport/distribution/branchement par diamètre…")


def categorie_dn(dn, longueur):
    if pd.isna(dn):
        return "Inconnu"
    # Branchement présumé : DN<60 ET longueur<30m
    if dn < 60 and longueur is not None and not pd.isna(longueur) and longueur < 30:
        return "Branchement (proxy)"
    if dn < 100:
        return "Petit DN <100"
    if dn < 250:
        return "Distribution 100-249"
    return "Transport ≥250"


cana["categorie_dn"] = cana.apply(lambda r: categorie_dn(r["DIAMETRE"], r["LONGUEUR_m"]), axis=1)
g_cat = (
    cana[cana["STATUT_OBJET"] == "EN SERVICE"]
    .groupby("categorie_dn")
    .agg(n=("OBJET", "count"), km=("LONGUEUR_m", lambda s: s.sum() / 1000))
    .sort_values("km", ascending=False)
)
g_cat.to_csv(OUT / "08_categorie_dn_es.csv")

# λ par catégorie
es["categorie_dn"] = es.apply(lambda r: categorie_dn(r["DIAMETRE"], r["LONGUEUR_m"]), axis=1)
lam_cat = es.groupby("categorie_dn").apply(agg_lambda, include_groups=False).round(4)
lam_cat = lam_cat.sort_values("lam", ascending=False)
lam_cat.to_csv(OUT / "08_lambda_categorie_dn.csv")

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
ax = axes[0]
g_cat["km"].plot(kind="barh", ax=ax, color="#3498db")
for i, v in enumerate(g_cat["km"]):
    ax.text(v + 30, i, f"{v:.0f} km", va="center", fontsize=9)
ax.set_xlabel("Linéaire EN SERVICE (km)")
ax.set_title("Répartition par catégorie DN (proxy transport/distribution/branchement)")

ax = axes[1]
colors = ["#c0392b" if l > 0.20 else "#e67e22" if l > 0.10 else "#27ae60" for l in lam_cat["lam"]]
ax.barh(lam_cat.index, lam_cat["lam"], color=colors)
for i, (cat, r) in enumerate(lam_cat.iterrows()):
    ax.text(r["lam"] + 0.005, i, f"{r['lam']:.3f}", va="center", fontsize=9)
ax.set_xlabel("λ fuites/km/an")
ax.set_title("Taux de fuite par catégorie DN")
plt.tight_layout()
plt.savefig(OUT / "08_categorie_dn.png", bbox_inches="tight")
plt.close()

# ============================================================
# § 7. KAPLAN-MEIER : survie au statut EN SERVICE par famille
# ============================================================
print("[9] Kaplan-Meier survie par famille…")
# Construire dataset survie : durée = année_abandon - année_pose (event=1) OU ANNEE_REF-pose (event=0)
all_ = cana.copy()
all_ = all_[all_["STATUT_OBJET"].isin(["EN SERVICE", "ABANDONNE"])]
all_ = all_[all_["annee_pose"].notna() & (all_["annee_pose"] >= 1900) & (all_["annee_pose"] <= ANNEE_REF)]
all_["duree"] = np.where(
    all_["STATUT_OBJET"] == "ABANDONNE",
    all_["annee_abandon"] - all_["annee_pose"],
    ANNEE_REF - all_["annee_pose"],
)
all_["event"] = (all_["STATUT_OBJET"] == "ABANDONNE").astype(int)
all_ = all_[(all_["duree"] >= 0) & (all_["duree"] <= 130)]

# KM pondéré linéaire — implémentation manuelle
def km_curve(durees, events, weights, t_max=120):
    t = np.arange(0, t_max + 1)
    durees = np.asarray(durees)
    events = np.asarray(events)
    weights = np.asarray(weights)
    surv = np.ones_like(t, dtype=float)
    s = 1.0
    for i, ti in enumerate(t):
        at_risk_mask = durees >= ti
        n_at_risk = weights[at_risk_mask].sum()
        if n_at_risk == 0:
            surv[i:] = s
            break
        die_mask = at_risk_mask & (durees == ti) & (events == 1)
        d = weights[die_mask].sum()
        s = s * (1 - d / n_at_risk) if n_at_risk > 0 else s
        surv[i] = s
    return t, surv

fig, ax = plt.subplots(figsize=(10, 5.5))
familles_plot = ["FonteGrise", "Fonte", "Plastique", "AmianteCiment", "Acier", "Beton"]
palette = {"FonteGrise": "#c0392b", "Fonte": "#2980b9", "Plastique": "#16a085",
           "AmianteCiment": "#8e44ad", "Acier": "#e67e22", "Beton": "#7f8c8d"}
for fam in familles_plot:
    sub = all_[all_["famille"] == fam]
    if len(sub) < 100:
        continue
    t, s = km_curve(sub["duree"].values, sub["event"].values, sub["LONGUEUR_m"].values)
    km_ex = sub["LONGUEUR_m"].sum() / 1000
    ax.plot(t, s, lw=2, color=palette.get(fam), label=f"{fam} ({km_ex:.0f} km)")
ax.axhline(0.5, ls=":", color="grey", lw=0.8)
ax.set_xlabel("Âge du tronçon (ans)")
ax.set_ylabel("Probabilité d'être encore en service (pondérée linéaire)")
ax.set_title("Survie Kaplan-Meier au statut EN SERVICE — par famille matériau")
ax.set_xlim(0, 100)
ax.set_ylim(0, 1.02)
ax.legend(loc="lower left")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "09_kaplan_meier_famille.png")
plt.close()

# ============================================================
# § 8. STATS DE SYNTHÈSE
# ============================================================
print("[10] Stats de synthèse…")

# Sortie JSON pour le rapport
def serial(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    return str(o)


# Vie médiane par famille (50% du linéaire abandonné)
vie_med = {}
for fam in familles_plot:
    sub = all_[all_["famille"] == fam]
    if len(sub) < 100:
        continue
    t, s = km_curve(sub["duree"].values, sub["event"].values, sub["LONGUEUR_m"].values)
    if s.min() <= 0.5:
        idx = np.argmax(s <= 0.5)
        vie_med[fam] = int(t[idx])
    else:
        vie_med[fam] = None  # n'atteint pas 50%

stats = {
    "annee_ref": ANNEE_REF,
    "fenetre_lambda": FENETRE_LAMBDA,
    "km_total": float(km_total),
    "km_par_statut": {k: float(v) for k, v in g_stat["km"].to_dict().items()},
    "n_par_statut": {k: int(v) for k, v in g_stat["n"].to_dict().items()},
    "km_abandonne": float(km_ab_tot),
    "km_abandonne_avec_fuite": float(km_ab_fu),
    "pct_km_abandonne_avec_fuite": float(km_ab_fu / km_ab_tot * 100),
    "pct_n_abandonne_avec_fuite": float(n_ab_fu / len(ab) * 100),
    "delai_last_fuite_abandon_qts": {
        f"P{int(q*100)}": float(v)
        for q, v in zip([.25, .5, .75, .9],
                        weighted_quantiles(ab.loc[ab.a_eu_fuite, "delai_last_fuite"],
                                            ab.loc[ab.a_eu_fuite, "LONGUEUR_m"],
                                            [.25, .5, .75, .9]))
    },
    "lambda_par_famille": {k: float(v) for k, v in lam_fam["lam"].to_dict().items()},
    "lambda_par_categorie_dn": {k: float(v) for k, v in lam_cat["lam"].to_dict().items()},
    "vie_mediane_km_par_famille": vie_med,
    "stats_evt": df_stats_evt.to_dict(orient="records"),
}
(OUT / "stats_synthese.json").write_text(json.dumps(stats, indent=2, default=serial))

print("\n✅ Plots & CSV générés dans", OUT)
print("Fichiers :")
for f in sorted(OUT.iterdir()):
    print(f"   - {f.name}")
