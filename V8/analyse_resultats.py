"""
V8 — Analyse détaillée des résultats : scores réels, explicabilité, fuites détectées/ratées.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data_cleaning import load_data, build_dataset, compute_target_encoding

from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, average_precision_score, precision_recall_curve
import xgboost as xgb
import shap

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"

HORIZON = 3
OBS_YEAR = 2018

print("=" * 70)
print(f"V8 — ANALYSE DÉTAILLÉE (horizon={HORIZON} ans, obs={OBS_YEAR})")
print("=" * 70)

# --- Load & build ---
cana, fuites = load_data(DATA_DIR)
df, FEATURES, FNAMES = build_dataset(cana, fuites, observation_year=OBS_YEAR, horizon=HORIZON)

idx_all = np.arange(len(df))
idx_train, idx_test = train_test_split(idx_all, test_size=0.25, random_state=42, stratify=df["y"].values)
df_train = df.iloc[idx_train].copy()
df_test = df.iloc[idx_test].copy()

te_map = compute_target_encoding(df_train, col="famille_mat", target="y", smoothing=10)
gm = te_map["__global__"]
tv = {k: v for k, v in te_map.items() if k != "__global__"}
df_train["famille_enc"] = df_train["famille_mat"].map(tv).fillna(gm)
df_test["famille_enc"] = df_test["famille_mat"].map(tv).fillna(gm)

X_train = df_train[FEATURES].values
X_test = df_test[FEATURES].values
y_train = df_train["y"].values
y_test = df_test["y"].values

imp = SimpleImputer(strategy="median")
X_train_imp = imp.fit_transform(X_train)
X_test_imp = imp.transform(X_test)

n_neg = (y_train == 0).sum()
n_pos = max(y_train.sum(), 1)

model = xgb.XGBClassifier(
    n_estimators=500, max_depth=6, learning_rate=0.03,
    subsample=0.8, colsample_bytree=0.8,
    scale_pos_weight=round(n_neg / n_pos, 1),
    eval_metric="auc", random_state=42, n_jobs=-1,
)
model.fit(X_train_imp, y_train, eval_set=[(X_test_imp, y_test)], verbose=0)
y_proba = model.predict_proba(X_test_imp)[:, 1]

df_test = df_test.copy()
df_test["score"] = y_proba

# ============================================================
# 1. VRAIS SCORES — Exemples concrets
# ============================================================
print("\n" + "=" * 70)
print("1. EXEMPLES DE TRONÇONS SCORÉS (test set)")
print("=" * 70)

df_test_sorted = df_test.sort_values("score", ascending=False).reset_index(drop=True)

print("\n  --- TOP 15 : tronçons les plus à risque ---")
print(f"  {'Rang':>4} {'OBJET':>10} {'Score':>6} {'Fuite?':>6} {'Âge':>4} {'Diam':>5} {'Matériau':>16} {'Nb_fuites_hist':>14}")
for i, (_, row) in enumerate(df_test_sorted.head(15).iterrows()):
    fuite = "OUI" if row["y"] == 1 else "non"
    print(f"  {i+1:>4} {str(row['OBJET'])[:10]:>10} {row['score']:>6.3f} {fuite:>6} {row['age']:>4.0f} {row['DIAMETRE']:>5.0f} {row['famille_mat']:>16} {row['nb_fuites_avant']:>14.0f}")

print("\n  --- BOTTOM 15 : tronçons les moins à risque ---")
for i, (_, row) in enumerate(df_test_sorted.tail(15).iterrows()):
    rang = len(df_test_sorted) - 14 + i
    fuite = "OUI" if row["y"] == 1 else "non"
    print(f"  {rang:>4} {str(row['OBJET'])[:10]:>10} {row['score']:>6.3f} {fuite:>6} {row['age']:>4.0f} {row['DIAMETRE']:>5.0f} {row['famille_mat']:>16} {row['nb_fuites_avant']:>14.0f}")

print("\n  --- EXEMPLES FAUX NÉGATIFS (fuites ratées) ---")
fn = df_test_sorted[(df_test_sorted["y"] == 1) & (df_test_sorted["score"] < 0.5)]
fn_sorted = fn.sort_values("score", ascending=True)
print(f"  Total fuites ratées (score < 0.5) : {len(fn)}")
print(f"  {'Rang':>4} {'OBJET':>10} {'Score':>6} {'Âge':>4} {'Diam':>5} {'Matériau':>16} {'Nb_fuites_hist':>14}")
for i, (_, row) in enumerate(fn_sorted.head(10).iterrows()):
    rang = (df_test_sorted["OBJET"] == row["OBJET"]).idxmax() + 1
    print(f"  {rang:>4} {str(row['OBJET'])[:10]:>10} {row['score']:>6.3f} {row['age']:>4.0f} {row['DIAMETRE']:>5.0f} {row['famille_mat']:>16} {row['nb_fuites_avant']:>14.0f}")

# ============================================================
# 2. COMPTAGE FUITES DÉTECTÉES / RATÉES par seuil
# ============================================================
print("\n" + "=" * 70)
print("2. FUITES DÉTECTÉES vs RATÉES — PAR SEUIL D'INSPECTION")
print("=" * 70)

total_fuites = y_test.sum()
total_troncons = len(y_test)

print(f"\n  Total tronçons test : {total_troncons:,}")
print(f"  Total fuites réelles (horizon {HORIZON} ans) : {total_fuites:,}")
print(f"  Taux de base : {100*total_fuites/total_troncons:.2f}%\n")

print(f"  {'Budget inspection':>20} {'Tronçons inspectés':>20} {'Fuites trouvées':>16} {'Fuites ratées':>14} {'% détecté':>10} {'Précision':>10}")
print(f"  {'-'*20} {'-'*20} {'-'*16} {'-'*14} {'-'*10} {'-'*10}")

for pct in [1, 2, 5, 10, 15, 20, 30, 50]:
    top_n = int(total_troncons * pct / 100)
    top_idx = np.argsort(y_proba)[::-1][:top_n]
    detectees = y_test[top_idx].sum()
    ratees = total_fuites - detectees
    precision = detectees / top_n if top_n > 0 else 0
    print(f"  Top {pct:>2}% ({top_n:>6,} inspectés) {' ':>5}{detectees:>6,} trouvées {ratees:>8,} ratées {100*detectees/total_fuites:>8.1f}% {100*precision:>8.1f}%")

# Seuil opérationnel recommandé
print(f"\n  >>> RECOMMANDATION :")
print(f"      Inspecter le Top 10% ({int(total_troncons*0.1):,} tronçons)")
top10_idx = np.argsort(y_proba)[::-1][:int(total_troncons*0.1)]
det10 = y_test[top10_idx].sum()
print(f"      → Détecte {det10} fuites sur {total_fuites} ({100*det10/total_fuites:.1f}%)")
print(f"      → Rate {total_fuites-det10} fuites ({100*(total_fuites-det10)/total_fuites:.1f}%)")
print(f"      → 1 fuite trouvée tous les {int(total_troncons*0.1)//det10} tronçons inspectés")

# ============================================================
# 3. PROFIL DES FUITES DÉTECTÉES vs RATÉES
# ============================================================
print("\n" + "=" * 70)
print("3. PROFIL : FUITES DÉTECTÉES vs RATÉES (seuil Top 20%)")
print("=" * 70)

top20_n = int(total_troncons * 0.2)
top20_idx = np.argsort(y_proba)[::-1][:top20_n]
is_top20 = np.zeros(len(y_test), dtype=bool)
is_top20[top20_idx] = True

detectees_mask = (y_test == 1) & is_top20
ratees_mask = (y_test == 1) & ~is_top20

df_det = df_test.iloc[np.where(detectees_mask)[0]]
df_rat = df_test.iloc[np.where(ratees_mask)[0]]

print(f"\n  Fuites détectées : {len(df_det):,}")
print(f"  Fuites ratées    : {len(df_rat):,}")

for label, sub in [("DÉTECTÉES", df_det), ("RATÉES", df_rat)]:
    print(f"\n  --- {label} ---")
    print(f"    Score moyen      : {sub['score'].mean():.3f} (min={sub['score'].min():.3f}, max={sub['score'].max():.3f})")
    print(f"    Âge moyen        : {sub['age'].mean():.0f} ans (min={sub['age'].min():.0f}, max={sub['age'].max():.0f})")
    print(f"    Diamètre moyen   : {sub['DIAMETRE'].mean():.0f} mm")
    print(f"    Nb fuites hist   : {sub['nb_fuites_avant'].mean():.1f} (médiane={sub['nb_fuites_avant'].median():.0f})")
    print(f"    Matériaux :")
    mat_counts = sub["famille_mat"].value_counts()
    for mat, n in mat_counts.head(6).items():
        print(f"      {mat:>16s} : {n:>4} ({100*n/len(sub):5.1f}%)")

# ============================================================
# 4. EXPLICABILITÉ — SHAP détaillé
# ============================================================
print("\n" + "=" * 70)
print("4. EXPLICABILITÉ SHAP — POURQUOI le modèle donne ces scores")
print("=" * 70)

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test_imp)
base_value = explainer.expected_value

print(f"\n  Base value (log-odds) : {base_value:.4f}")
print(f"  = probabilité de base : {1/(1+np.exp(-base_value)):.4f} ({100/(1+np.exp(-base_value)):.2f}%)")

print(f"\n  --- DÉCOMPOSITION DES 5 TRONÇONS LES PLUS À RISQUE ---")
top5_global_idx = np.argsort(y_proba)[::-1][:5]
for rank, gi in enumerate(top5_global_idx):
    row = df_test.iloc[gi]
    print(f"\n  #{rank+1} — OBJET={row['OBJET']} | Score={y_proba[gi]:.3f} | Fuite réelle: {'OUI' if row['y']==1 else 'NON'}")
    print(f"       Âge={row['age']:.0f}an | Diam={row['DIAMETRE']:.0f}mm | Matériau={row['famille_mat']} | Hist={row['nb_fuites_avant']:.0f} fuites")
    print(f"       Contributions SHAP :")
    for j, fname in enumerate(FNAMES):
        sv = shap_values[gi, j]
        direction = "↑ risque" if sv > 0 else "↓ risque"
        print(f"         {fname:>25s} = {sv:+.4f} ({direction})")

print(f"\n  --- DÉCOMPOSITION D'UNE FUITE RATÉE (score le plus bas parmi les vraies fuites) ---")
fuites_idx = np.where(y_test == 1)[0]
worst_fuite_pos = fuites_idx[np.argmin(y_proba[fuites_idx])]
row = df_test.iloc[worst_fuite_pos]
print(f"  OBJET={row['OBJET']} | Score={y_proba[worst_fuite_pos]:.3f} | FUITE RÉELLE")
print(f"  Âge={row['age']:.0f}an | Diam={row['DIAMETRE']:.0f}mm | Matériau={row['famille_mat']} | Hist={row['nb_fuites_avant']:.0f} fuites")
print(f"  Contributions SHAP :")
for j, fname in enumerate(FNAMES):
    sv = shap_values[worst_fuite_pos, j]
    direction = "↑ risque" if sv > 0 else "↓ risque"
    print(f"    {fname:>25s} = {sv:+.4f} ({direction})")
print(f"  → Le modèle n'a pas pu prédire cette fuite : profil atypique (jeune, peu d'historique)")

# ============================================================
# 5. TAUX DE FUITE PAR MATÉRIAU — RÉEL vs PRÉDIT
# ============================================================
print("\n" + "=" * 70)
print("5. TAUX DE FUITE PAR MATÉRIAU — RÉEL vs PRÉDIT (horizon 3 ans)")
print("=" * 70)

print(f"\n  {'Matériau':>16} {'N tronçons':>10} {'Fuites réelles':>15} {'Taux réel':>10} {'Score moyen':>12} {'Fuites > p50':>12}")
print(f"  {'-'*16} {'-'*10} {'-'*15} {'-'*10} {'-'*12} {'-'*12}")

median_score = np.median(y_proba)
for mat in sorted(df_test["famille_mat"].unique()):
    mask = df_test["famille_mat"] == mat
    n = mask.sum()
    if n < 10:
        continue
    fuites_r = df_test.loc[mask, "y"].sum()
    taux = 100 * fuites_r / n
    score_moy = y_proba[mask.values].mean()
    above_median = (y_proba[mask.values] > median_score).sum()
    print(f"  {mat:>16} {n:>10,} {fuites_r:>15,} {taux:>9.2f}% {score_moy:>11.4f} {above_median:>12,}")

# ============================================================
# 6. DISTRIBUTION DES SCORES
# ============================================================
print("\n" + "=" * 70)
print("6. DISTRIBUTION DES SCORES")
print("=" * 70)

percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
print(f"\n  Percentiles du score (tous tronçons test) :")
for p in percentiles:
    v = np.percentile(y_proba, p)
    print(f"    P{p:>2} = {v:.4f}")

print(f"\n  Score moyen — avec fuite    : {y_proba[y_test==1].mean():.4f} (médiane={np.median(y_proba[y_test==1]):.4f})")
print(f"  Score moyen — sans fuite    : {y_proba[y_test==0].mean():.4f} (médiane={np.median(y_proba[y_test==0]):.4f})")
print(f"  Ratio séparation            : {y_proba[y_test==1].mean() / y_proba[y_test==0].mean():.1f}x")

# ============================================================
# 7. PLOTS
# ============================================================
print("\n" + "=" * 70)
print("7. GRAPHIQUES")
print("=" * 70)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 7a. Distribution scores avec/sans fuite
axes[0, 0].hist(y_proba[y_test == 0], bins=50, alpha=0.6, label=f"Sans fuite (n={int((y_test==0).sum()):,})", density=True, color="green")
axes[0, 0].hist(y_proba[y_test == 1], bins=50, alpha=0.6, label=f"Avec fuite (n={int(y_test.sum()):,})", density=True, color="red")
axes[0, 0].set_xlabel("Score de risque")
axes[0, 0].set_ylabel("Densité")
axes[0, 0].set_title("Distribution des scores")
axes[0, 0].legend()

# 7b. Courbe de capture (lift)
pcts_range = np.arange(1, 101)
captures_curve = []
for p in pcts_range:
    top_n = int(len(y_test) * p / 100)
    top_idx = np.argsort(y_proba)[::-1][:top_n]
    captured = y_test[top_idx].sum()
    captures_curve.append(100 * captured / total_fuites)

# Même chose baseline âge
ages_test = X_test_imp[:, FEATURES.index("age")]
captures_age_curve = []
for p in pcts_range:
    top_n = int(len(y_test) * p / 100)
    top_idx = np.argsort(ages_test)[::-1][:top_n]
    captured = y_test[top_idx].sum()
    captures_age_curve.append(100 * captured / total_fuites)

axes[0, 1].plot(pcts_range, captures_curve, "b-", linewidth=2, label="XGBoost V8")
axes[0, 1].plot(pcts_range, captures_age_curve, "r--", linewidth=1.5, label="Baseline (âge)")
axes[0, 1].plot(pcts_range, pcts_range, "k:", linewidth=1, label="Aléatoire")
axes[0, 1].set_xlabel("% du réseau inspecté")
axes[0, 1].set_ylabel("% des fuites détectées")
axes[0, 1].set_title("Courbe de capture (Lift)")
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].axvline(20, color="gray", linestyle="--", alpha=0.5)
axes[0, 1].annotate(f"@20%: {captures_curve[19]:.0f}%", (22, captures_curve[19]), fontsize=9)

# 7c. Precision-Recall
prec, rec, thresholds = precision_recall_curve(y_test, y_proba)
axes[1, 0].plot(rec, prec, "b-", linewidth=2)
axes[1, 0].axhline(total_fuites / total_troncons, color="r", linestyle="--", label=f"Baseline ({100*total_fuites/total_troncons:.2f}%)")
axes[1, 0].set_xlabel("Recall (% fuites détectées)")
axes[1, 0].set_ylabel("Precision (% vrais parmi alertes)")
axes[1, 0].set_title("Courbe Precision-Recall")
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

# 7d. SHAP waterfall pour le tronçon #1
shap_order = np.argsort(np.abs(shap_values).mean(axis=0))[::-1]
mean_shap = np.abs(shap_values).mean(axis=0)
axes[1, 1].barh([FNAMES[i] for i in shap_order], [mean_shap[i] for i in shap_order], color=["#ff6b6b", "#ffa07a", "#87ceeb", "#90ee90"])
axes[1, 1].set_xlabel("Mean |SHAP value|")
axes[1, 1].set_title("Importance des features")

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v8_04_analyse_detaillee.png", dpi=150)
plt.close()
print("  => v8_04_analyse_detaillee.png")

# ============================================================
# RÉSUMÉ OPÉRATIONNEL
# ============================================================
print("\n" + "=" * 70)
print("RÉSUMÉ OPÉRATIONNEL — V8 MODÈLE FUITES")
print("=" * 70)

top20_det = y_test[np.argsort(y_proba)[::-1][:int(total_troncons*0.2)]].sum()
top10_det = y_test[np.argsort(y_proba)[::-1][:int(total_troncons*0.1)]].sum()
top5_det = y_test[np.argsort(y_proba)[::-1][:int(total_troncons*0.05)]].sum()

print(f"""
Sur {total_troncons:,} tronçons testés, {total_fuites:,} ont eu ≥1 fuite en {HORIZON} ans.

BUDGET INSPECTION → FUITES TROUVÉES :
  Inspecter   5% du réseau ({int(total_troncons*0.05):>6,} tronçons) → trouve {top5_det:>3} fuites sur {total_fuites} ({100*top5_det/total_fuites:.0f}%) — rate {total_fuites-top5_det}
  Inspecter  10% du réseau ({int(total_troncons*0.1):>6,} tronçons) → trouve {top10_det:>3} fuites sur {total_fuites} ({100*top10_det/total_fuites:.0f}%) — rate {total_fuites-top10_det}
  Inspecter  20% du réseau ({int(total_troncons*0.2):>6,} tronçons) → trouve {top20_det:>3} fuites sur {total_fuites} ({100*top20_det/total_fuites:.0f}%) — rate {total_fuites-top20_det}

SÉPARATION DES SCORES :
  Tronçons avec fuite : score moyen {y_proba[y_test==1].mean():.3f}
  Tronçons sans fuite : score moyen {y_proba[y_test==0].mean():.3f}
  Le modèle sépare bien les deux populations ({y_proba[y_test==1].mean()/y_proba[y_test==0].mean():.1f}x plus élevé)

POUR LES ÉLUS :
  "En ciblant 20% du réseau avec notre modèle, on détecte {100*top20_det/total_fuites:.0f}% des futures fuites.
   Sans modèle (tri par âge), on n'en détecte que {100*y_test[np.argsort(ages_test)[::-1][:int(total_troncons*0.2)]].sum()/total_fuites:.0f}%.
   Le modèle est {top20_det/max(y_test[np.argsort(ages_test)[::-1][:int(total_troncons*0.2)]].sum(),1):.1f}x plus efficace que le tri par âge seul."
""")
print("=" * 70)
print("TERMINÉ")
