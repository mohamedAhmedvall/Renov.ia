"""
Phase 2 V6 — Classification propre sur ABANDONNE seul
Dataset V3 nettoyé, 12 features, pas de redondance, pas de fuite.

Pipeline:
  1. Chargement V3 + XGBoost
  2. Baseline : tri par âge seul (pour prouver que ML apporte quelque chose)
  3. Analyse erreurs
  4. Ablation features
  5. SHAP
  6. Scoring EN SERVICE
  7. MLflow

Cible : ABANDONNE = 1 vs (EN SERVICE + DEPOSE) = 0
"""

import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
import xgboost as xgb
import shap
import mlflow
import mlflow.xgboost

# Config
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

SPLIT_YEAR = 2018
ANNEE_REF = 2024

# ============================================================
print("=" * 60)
print("PHASE 2 V6 — CLASSIFICATION ABANDONNE (dataset V3)")
print("=" * 60)

# --- MLflow ---
mlflow.set_tracking_uri("file:///C:/Users/ahmedv_m/Desktop/mohamed_casses/mlruns")
mlflow.set_experiment("casses_canalisations_v6")
print()

# ============================================================
# [1/7] CHARGEMENT + MODELE
# ============================================================
print("[1/7] Chargement V3 + XGBoost...")

from data_cleaning_v3 import load_and_clean_v3, build_features_v3

cana, anom_clean = load_and_clean_v3(DATA_DIR)
df, FEATURES, FEATURE_NAMES = build_features_v3(cana, anom_clean, cutoff_year=SPLIT_YEAR)

X = df[FEATURES].values
y = df["y"].values
n_pos = y.sum()
n_neg = len(y) - n_pos
print(f"  Dataset: {len(df):,} tronçons | {n_pos:,} positifs ({100*n_pos/len(df):.2f}%)")
print(f"  Features: {len(FEATURES)}")

# Train/test split temporel (données déjà filtrées par cutoff)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

# Impute NaN
imp = SimpleImputer(strategy="median")
X_train = imp.fit_transform(X_train)
X_test = imp.transform(X_test)

# XGBoost
xgb_params = {
    "n_estimators": 500,
    "max_depth": 7,
    "learning_rate": 0.03,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "scale_pos_weight": round(n_neg / n_pos, 1),
    "eval_metric": "auc",
    "random_state": 42,
    "n_jobs": -1,
}

model = xgb.XGBClassifier(**xgb_params)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=0)

y_proba = model.predict_proba(X_test)[:, 1]
y_pred = (y_proba >= 0.5).astype(int)

auc = roc_auc_score(y_test, y_proba)
ap = average_precision_score(y_test, y_proba)
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()

print(f"\n  XGBoost: AUC={auc:.4f} | AP={ap:.4f}")
print(f"  F1={f1_score(y_test, y_pred):.4f} | Prec={precision_score(y_test, y_pred):.4f} | Rec={recall_score(y_test, y_pred):.4f}")
print(f"  TP={tp:,} FP={fp:,} FN={fn:,} TN={tn:,}")

# Capture @ top %
captures = {}
n_test_total = len(y_test)
for pct in [5, 10, 20, 30]:
    top_n = int(n_test_total * pct / 100)
    top_idx = np.argsort(y_proba)[::-1][:top_n]
    captured = y_test[top_idx].sum()
    captures[pct] = round(100 * captured / y_test.sum(), 1)
    print(f"  Top {pct}% -> capture {captures[pct]:.1f}% des abandons")

# ============================================================
# [2/7] BASELINE : TRI PAR AGE
# ============================================================
print("\n" + "=" * 60)
print("[2/7] BASELINE — TRI PAR AGE DESCENDANT")
print("=" * 60)

# Reconstruire l'âge du test set
age_idx = FEATURES.index("age")
ages_test = X_test[:, age_idx]

# AUC de l'âge seul
auc_age = roc_auc_score(y_test, ages_test)
print(f"  AUC (âge seul) = {auc_age:.4f}")
print(f"  AUC (XGBoost)  = {auc:.4f}")
print(f"  Gain ML vs âge = {auc - auc_age:+.4f}")

# Capture avec tri par âge
captures_age = {}
for pct in [5, 10, 20, 30]:
    top_n = int(n_test_total * pct / 100)
    top_idx = np.argsort(ages_test)[::-1][:top_n]
    captured = y_test[top_idx].sum()
    captures_age[pct] = round(100 * captured / y_test.sum(), 1)
    print(f"  Top {pct}% (âge) -> capture {captures_age[pct]:.1f}% | ML: {captures[pct]:.1f}% (delta={captures[pct]-captures_age[pct]:+.1f})")

# Plot comparaison
fig, ax = plt.subplots(figsize=(8, 5))
pcts = [5, 10, 20, 30]
ax.bar([p - 1 for p in pcts], [captures_age[p] for p in pcts], width=2, label="Tri par âge", alpha=0.7)
ax.bar([p + 1 for p in pcts], [captures[p] for p in pcts], width=2, label="XGBoost V6", alpha=0.7)
ax.set_xlabel("Top % du réseau inspecté")
ax.set_ylabel("% des abandons capturés")
ax.set_title("ML vs Baseline (tri par âge)")
ax.legend()
ax.set_xticks(pcts)
ax.set_xticklabels([f"Top {p}%" for p in pcts])
for p in pcts:
    ax.annotate(f"{captures_age[p]}%", (p - 1, captures_age[p] + 1), ha="center", fontsize=8)
    ax.annotate(f"{captures[p]}%", (p + 1, captures[p] + 1), ha="center", fontsize=8)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v6_01_ml_vs_baseline.png", dpi=150)
plt.close()
print("  => v6_01_ml_vs_baseline.png")

# ============================================================
# [3/7] ANALYSE DES ERREURS
# ============================================================
print("\n" + "=" * 60)
print("[3/7] ANALYSE DES ERREURS (FP + FN)")
print("=" * 60)

# Reconstruire un DataFrame test avec colonnes originales
test_df = df.iloc[0:0]  # vide, juste pour le schéma
# Plus simple : recréer depuis les indices
idx_all = np.arange(len(df))
_, idx_test = train_test_split(idx_all, test_size=0.25, random_state=42, stratify=y)
test_df = df.iloc[idx_test].copy()
test_df["y_proba"] = y_proba
test_df["y_pred"] = y_pred

fp_df = test_df[(test_df["y_pred"] == 1) & (test_df["y"] == 0)]
fn_df = test_df[(test_df["y_pred"] == 0) & (test_df["y"] == 1)]

print(f"\n  FAUX POSITIFS : {len(fp_df):,}")
print(f"  Score moyen FP : {fp_df['y_proba'].mean():.3f}")
print(f"  Âge moyen FP   : {fp_df['age'].mean():.0f} ans (global: {test_df['age'].mean():.0f})")

print(f"  Matériaux FP :")
mat_fp = fp_df["famille_mat"].value_counts()
mat_global = test_df["famille_mat"].value_counts(normalize=True)
for mat, n in mat_fp.head(6).items():
    pct_fp = 100 * n / len(fp_df)
    pct_gl = 100 * mat_global.get(mat, 0)
    print(f"    {mat:>15s}: {n:>5,} ({pct_fp:5.1f}% FP vs {pct_gl:5.1f}% global)")

print(f"\n  FAUX NEGATIFS : {len(fn_df):,}")
print(f"  Score moyen FN : {fn_df['y_proba'].mean():.3f}")
print(f"  Âge moyen FN   : {fn_df['age'].mean():.0f} ans")
print(f"  Matériaux FN :")
mat_fn = fn_df["famille_mat"].value_counts()
for mat, n in mat_fn.head(6).items():
    print(f"    {mat:>15s}: {n:>5,} ({100*n/len(fn_df):5.1f}%)")

print(f"  État FN :")
etat_fn = fn_df["etat_clean"].value_counts()
for etat, n in etat_fn.items():
    print(f"    {etat:>10s}: {n:>5,} ({100*n/len(fn_df):5.1f}%)")

# Check: combien de FN étaient DEPOSE dans le dataset original ?
fn_depose = fn_df[fn_df["STATUT_OBJET"] == "DEPOSE"]
print(f"\n  FN qui sont des DEPOSE (label=0 par design): {len(fn_depose)}")
print(f"  => Ces FN ne sont PAS des erreurs, le modèle ne devrait pas les prédire")

# Plots erreurs
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
# Âge
for label, sub, color in [("FP", fp_df, "orange"), ("FN", fn_df, "red"), ("TP", test_df[(test_df["y_pred"]==1) & (test_df["y"]==1)], "green")]:
    axes[0].hist(sub["age"].dropna(), bins=30, alpha=0.5, label=f"{label} (n={len(sub):,})", color=color, density=True)
axes[0].set_xlabel("Âge")
axes[0].set_title("Distribution d'âge par catégorie")
axes[0].legend()
# Matériau
cats = ["Fonte", "Fonte_grise", "Plastique", "Acier", "Beton", "Autre"]
fp_mat = fp_df["famille_mat"].value_counts().reindex(cats, fill_value=0)
fn_mat = fn_df["famille_mat"].value_counts().reindex(cats, fill_value=0)
x = np.arange(len(cats))
axes[1].bar(x - 0.2, fp_mat.values, 0.4, label="FP", color="orange")
axes[1].bar(x + 0.2, fn_mat.values, 0.4, label="FN", color="red")
axes[1].set_xticks(x)
axes[1].set_xticklabels(cats, rotation=45, ha="right")
axes[1].set_title("Matériaux FP vs FN")
axes[1].legend()
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v6_02_analyse_erreurs.png", dpi=150)
plt.close()
print("  => v6_02_analyse_erreurs.png")

# ============================================================
# [4/7] ABLATION
# ============================================================
print("\n" + "=" * 60)
print("[4/7] ABLATION DE FEATURES")
print("=" * 60)

auc_ref = auc
print(f"  AUC référence : {auc_ref:.4f}")

ablation_results = []
for i, (feat, fname) in enumerate(zip(FEATURES, FEATURE_NAMES)):
    X_abl = np.delete(X_test, i, axis=1)
    X_abl_train = np.delete(X_train, i, axis=1)

    model_abl = xgb.XGBClassifier(**xgb_params)
    model_abl.fit(X_abl_train, y_train, eval_set=[(X_abl, y_test)], verbose=0)
    y_abl = model_abl.predict_proba(X_abl)[:, 1]
    auc_abl = roc_auc_score(y_test, y_abl)
    delta = auc_ref - auc_abl
    sign = "+" if delta > 0 else "-"
    print(f"  [{i+1:>2}/{len(FEATURES)}] Sans {fname:>25s} : AUC={auc_abl:.4f} (delta={delta:+.4f} {sign})")
    ablation_results.append({"feature": fname, "auc_without": auc_abl, "delta_auc": delta})

abl_df = pd.DataFrame(ablation_results).sort_values("delta_auc", ascending=False)
abl_df.to_csv(OUTPUT_DIR / "v6_ablation_features.csv", index=False)

helpful = abl_df[abl_df["delta_auc"] > 0.0005]
harmful = abl_df[abl_df["delta_auc"] < -0.0005]

print(f"\n  Features les plus utiles (retirer fait baisser AUC) :")
for _, row in helpful.iterrows():
    print(f"    {row['feature']:>25s} : delta={row['delta_auc']:+.4f}")
if len(harmful) > 0:
    print(f"  Features potentiellement nuisibles :")
    for _, row in harmful.iterrows():
        print(f"    {row['feature']:>25s} : delta={row['delta_auc']:+.4f}")

# Plot ablation
fig, ax = plt.subplots(figsize=(10, 6))
colors = ["green" if d > 0 else "red" if d < -0.0005 else "gray" for d in abl_df["delta_auc"]]
ax.barh(abl_df["feature"], abl_df["delta_auc"], color=colors)
ax.axvline(0, color="black", linewidth=0.5)
ax.set_xlabel("Delta AUC (+ = feature utile)")
ax.set_title("Ablation : impact de chaque feature")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v6_03_ablation.png", dpi=150)
plt.close()
print("  => v6_03_ablation.png")

# ============================================================
# [5/7] SHAP
# ============================================================
print("\n" + "=" * 60)
print("[5/7] SHAP")
print("=" * 60)

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

shap_imp = pd.DataFrame({
    "feature": FEATURE_NAMES,
    "mean_abs_shap": np.abs(shap_values).mean(axis=0),
}).sort_values("mean_abs_shap", ascending=False)
shap_imp.to_csv(OUTPUT_DIR / "v6_shap_importance.csv", index=False)

print("  Top features SHAP :")
for _, row in shap_imp.head(8).iterrows():
    print(f"    {row['feature']:>25s} : {row['mean_abs_shap']:.4f}")

# SHAP plots
fig, ax = plt.subplots(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, feature_names=FEATURE_NAMES, show=False)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v6_04_shap_summary.png", dpi=150)
plt.close()
print("  => v6_04_shap_summary.png")

fig, ax = plt.subplots(figsize=(8, 5))
shap.summary_plot(shap_values, X_test, feature_names=FEATURE_NAMES, plot_type="bar", show=False)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v6_05_shap_bar.png", dpi=150)
plt.close()
print("  => v6_05_shap_bar.png")

# ============================================================
# [6/7] SCORING EN SERVICE
# ============================================================
print("\n" + "=" * 60)
print("[6/7] SCORING TRONCONS EN SERVICE")
print("=" * 60)

# Re-entraîner sur tout le dataset
model_full = xgb.XGBClassifier(**xgb_params)
X_all = imp.fit_transform(X)
model_full.fit(X_all, y, verbose=0)

# Scoring : seulement les EN SERVICE actuels
es_mask = cana["STATUT_OBJET"] == "EN SERVICE"
cana_es = cana[es_mask].copy()

# Construire features mode scoring
df_score, feat_cols_s, _ = build_features_v3(cana_es.copy(), anom_clean, cutoff_year=None)
# Attention: rebuild pour EN SERVICE, donc y=0 pour tous (label=0 car pas ABANDONNE)
# On doit utiliser le même imputer
X_score_raw = df_score[FEATURES].values

# Target encoding: recalculer avec les mêmes valeurs que le train
# (on utilise le mapping du train full)
global_mean = df["y"].mean()
te_map = df.groupby("famille_mat")["y"].mean()
df_score["famille_enc"] = df_score["famille_mat"].map(te_map).fillna(global_mean)
df_score["age_x_famille"] = df_score["age"] * df_score["famille_enc"]
X_score_raw = df_score[FEATURES].values

X_score = imp.transform(X_score_raw)
scores = model_full.predict_proba(X_score)[:, 1]

scoring = pd.DataFrame({
    "OBJET": df_score["OBJET"].values,
    "MATERIAU": df_score["MATERIAU"].values,
    "FAMILLE": df_score["famille_mat"].values,
    "ETAT": df_score["etat_clean"].values,
    "AGE": df_score["age"].values,
    "DIAMETRE": df_score["DIAMETRE"].values,
    "LONGUEUR": df_score["LONGUEUR"].values,
    "NB_FUITES": df_score["nb_fuites"].values,
    "SCORE": scores,
})
scoring = scoring.sort_values("SCORE", ascending=False).reset_index(drop=True)
scoring["RANG"] = range(1, len(scoring) + 1)
scoring["TOP_PCT"] = (scoring["RANG"] / len(scoring) * 100).round(1)
scoring.to_csv(OUTPUT_DIR / "v6_scoring_troncons.csv", index=False)
print(f"  => v6_scoring_troncons.csv ({len(scoring):,} tronçons EN SERVICE)")

# Stats top 10%
top10 = scoring[scoring["TOP_PCT"] <= 10]
print(f"\n  TOP 10% ({len(top10):,} tronçons) :")
print(f"    Score moyen: {top10['SCORE'].mean():.3f}")
print(f"    Âge moyen: {top10['AGE'].mean():.0f} ans")
print(f"    Familles: {top10['FAMILLE'].value_counts().head(5).to_dict()}")

# ============================================================
# [7/7] MLFLOW
# ============================================================
print("\n" + "=" * 60)
print("[7/7] MLFLOW LOGGING")
print("=" * 60)

def safe_name(name):
    return re.sub(r"[^a-zA-Z0-9_\-. /]", "", name.replace("/", "_per_"))

with mlflow.start_run(run_name=f"V6_XGBoost_ABANDON_cutoff{SPLIT_YEAR}") as run:
    mlflow.log_param("version", "V6")
    mlflow.log_param("cible", "ABANDONNE_seul")
    mlflow.log_param("cutoff_year", SPLIT_YEAR)
    mlflow.log_param("n_features", len(FEATURES))
    mlflow.log_param("n_train", len(X_train))
    mlflow.log_param("n_test", len(X_test))
    mlflow.log_param("n_positifs", int(n_pos))
    mlflow.log_param("pct_positifs", round(100 * n_pos / len(df), 2))
    for k, v in xgb_params.items():
        mlflow.log_param(f"xgb_{k}", v)

    mlflow.log_metric("auc_test", auc)
    mlflow.log_metric("ap_test", ap)
    mlflow.log_metric("f1_test", f1_score(y_test, y_pred))
    mlflow.log_metric("precision_test", precision_score(y_test, y_pred))
    mlflow.log_metric("recall_test", recall_score(y_test, y_pred))
    mlflow.log_metric("tp", tp)
    mlflow.log_metric("fp", fp)
    mlflow.log_metric("fn", fn)
    mlflow.log_metric("tn", tn)
    mlflow.log_metric("auc_baseline_age", auc_age)
    mlflow.log_metric("gain_ml_vs_age", auc - auc_age)

    for pct in [5, 10, 20, 30]:
        mlflow.log_metric(f"capture_top{pct}pct", captures[pct])
        mlflow.log_metric(f"capture_age_top{pct}pct", captures_age[pct])

    for i, (_, row) in enumerate(shap_imp.head(5).iterrows()):
        sn = safe_name(row["feature"])
        mlflow.log_metric(f"shap_top{i+1}_{sn}", row["mean_abs_shap"])

    for _, row in abl_df.iterrows():
        sn = safe_name(row["feature"])
        mlflow.log_metric(f"ablation_{sn}", row["delta_auc"])

    for f in OUTPUT_DIR.glob("v6_*.png"):
        mlflow.log_artifact(str(f))
    for f in OUTPUT_DIR.glob("v6_*.csv"):
        mlflow.log_artifact(str(f))

    mlflow.xgboost.log_model(model_full, artifact_path="model")

    print(f"  Run ID: {run.info.run_id}")

# --- RAPPORT ---
print("\n" + "=" * 60)
print("RAPPORT V6")
print("=" * 60)
print(f"""
CHANGEMENT CLE: Cible = ABANDONNE seul (DEPOSE exclu)
DATASET V3: ETAT nettoyé, MATERIAU groupé, 12 features propres

METRIQUES TEST:
  AUC XGBoost = {auc:.4f}
  AUC Baseline (âge) = {auc_age:.4f}
  Gain ML = {auc - auc_age:+.4f}

CAPTURE:
  Top  5%: ML={captures[5]:.1f}% | Âge={captures_age[5]:.1f}%
  Top 10%: ML={captures[10]:.1f}% | Âge={captures_age[10]:.1f}%  
  Top 20%: ML={captures[20]:.1f}% | Âge={captures_age[20]:.1f}%
  Top 30%: ML={captures[30]:.1f}% | Âge={captures_age[30]:.1f}%

SCORING: {len(scoring):,} tronçons -> v6_scoring_troncons.csv
MLFLOW: http://localhost:5001
""")
print("=" * 60)
print("TERMINÉ")
print("=" * 60)
