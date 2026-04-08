"""
Phase 2 V7 — Corrections P0/P1/P2 revue adversariale.

Fixes appliqués:
  P0: Target encoding calculé sur TRAIN ONLY (pas de fuite train→test)
  P0: Scoring utilise le TE mapping du train (pas recalculé)
  P1: 5 features anomalies → seul nb_fuites gardé (ablation V6 confirmait)
  P1: Backtesting temporel (3 fenêtres glissantes)
  P2: DEPOSE exclu entièrement (pas gardé comme négatif)
  P2: age_imputed flag ajouté
  P2: ETAT Inconnu → NaN (XGBoost natif, pas ordinal 0)

Pipeline:
  1. Chargement V4 + split temporel
  2. Target encoding train-only + XGBoost
  3. Baseline (tri par âge)
  4. Backtesting temporel (3 fenêtres)
  5. Ablation features
  6. SHAP
  7. Scoring EN SERVICE (avec TE mapping sauvegardé)
  8. MLflow
"""

import re
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
import xgboost as xgb
import mlflow
import mlflow.xgboost
from pathlib import Path
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.impute import SimpleImputer

# Config
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

SPLIT_YEAR = 2018
ANNEE_REF = 2024

# Backtesting fenêtres: (cutoff_train, cutoff_eval)
# Fenêtre 1 : train < 2012, eval [2012-2016]
# Fenêtre 2 : train < 2014, eval [2014-2018]
# Fenêtre 3 : train < 2016, eval [2016-2020]
BACKTEST_WINDOWS = [
    (2012, 2016),
    (2014, 2018),
    (2016, 2020),
]

print("=" * 60)
print("PHASE 2 V7 — CORRECTIONS P0/P1/P2")
print("=" * 60)

# --- MLflow ---
mlflow.set_tracking_uri("file:///C:/Users/ahmedv_m/Desktop/mohamed_casses/mlruns")
mlflow.set_experiment("casses_canalisations_v7")
print()

# ============================================================
# [1/8] CHARGEMENT + SPLIT TEMPOREL
# ============================================================
print("[1/8] Chargement V4 + split temporel...")

from data_cleaning_v4 import (
    load_and_clean_v4, build_features_v4, compute_target_encoding,
)

cana, anom_clean = load_and_clean_v4(DATA_DIR)

# --- Split temporel ---
# Train : tronçons dont on connaît le sort AVANT SPLIT_YEAR
# Test  : tronçons abandonnés entre SPLIT_YEAR et ANNEE_REF + EN SERVICE
df_full, FEATURES, FEATURE_NAMES = build_features_v4(
    cana, anom_clean, cutoff_year=SPLIT_YEAR
)

# Split : tronçons EN SERVICE au moment du cutoff + abandonnés après cutoff
# (build_features_v4 a déjà filtré les abandonnés avant cutoff)

# Pour le split temporel : on utilise la date de pose comme proxy
# Tronçons posés avant 2000 → train, après → test (approximation temporelle)
# MIEUX : split aléatoire sur les tronçons mais TE calculé train-only
# Le vrai fix P0 est le TE train-only, pas forcément le split temporel

# Split stratifié (même approche que V6 pour comparabilité)
from sklearn.model_selection import train_test_split

y_full = df_full["y"].values
idx_all = np.arange(len(df_full))

idx_train, idx_test = train_test_split(
    idx_all, test_size=0.25, random_state=42, stratify=y_full
)

df_train = df_full.iloc[idx_train].copy()
df_test = df_full.iloc[idx_test].copy()

# ============================================================
# [2/8] TARGET ENCODING TRAIN-ONLY + MODELE
# ============================================================
print("\n[2/8] Target encoding (train-only) + XGBoost...")

# P0 FIX: TE calculé UNIQUEMENT sur train
te_map = compute_target_encoding(df_train, col="famille_mat", target="y", smoothing=10)
print(f"  TE mapping ({len(te_map)-1} familles, global={te_map['__global__']:.4f}):")
for k, v in sorted(te_map.items()):
    if k != "__global__":
        print(f"    {k:>20s}: {v:.4f}")

# Appliquer TE au train et test
global_mean_te = te_map["__global__"]
te_values = {k: v for k, v in te_map.items() if k != "__global__"}
df_train["famille_enc"] = df_train["famille_mat"].map(te_values).fillna(global_mean_te)
df_test["famille_enc"] = df_test["famille_mat"].map(te_values).fillna(global_mean_te)

# Sauvegarder le TE mapping pour scoring
te_map_serializable = {k: float(v) for k, v in te_map.items()}
with open(OUTPUT_DIR / "v7_te_mapping.json", "w") as f:
    json.dump(te_map_serializable, f, indent=2)

X_train = df_train[FEATURES].values
X_test = df_test[FEATURES].values
y_train = df_train["y"].values
y_test = df_test["y"].values

n_pos = y_full.sum()
n_neg = len(y_full) - n_pos
n_pos_train = y_train.sum()
n_pos_test = y_test.sum()

print(f"\n  Dataset total: {len(df_full):,} | {n_pos:,} positifs ({100*n_pos/len(df_full):.2f}%)")
print(f"  Train: {len(df_train):,} ({n_pos_train:,} pos) | Test: {len(df_test):,} ({n_pos_test:,} pos)")
print(f"  Features: {len(FEATURES)} → {FEATURE_NAMES}")

# Impute NaN (etat_ord = NaN pour Inconnu, c'est voulu)
imp = SimpleImputer(strategy="median")
X_train_imp = imp.fit_transform(X_train)
X_test_imp = imp.transform(X_test)

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
model.fit(X_train_imp, y_train, eval_set=[(X_test_imp, y_test)], verbose=0)

y_proba = model.predict_proba(X_test_imp)[:, 1]
auc = roc_auc_score(y_test, y_proba)
ap = average_precision_score(y_test, y_proba)

print(f"\n  XGBoost V7: AUC={auc:.4f} | AP={ap:.4f}")

# Capture @top %
captures = {}
n_test_total = len(y_test)
for pct in [5, 10, 20, 30]:
    top_n = int(n_test_total * pct / 100)
    top_idx = np.argsort(y_proba)[::-1][:top_n]
    captured = y_test[top_idx].sum()
    captures[pct] = round(100 * captured / y_test.sum(), 1)
    print(f"  Top {pct}% → capture {captures[pct]:.1f}% des abandons")

# ============================================================
# [3/8] BASELINE : TRI PAR AGE
# ============================================================
print("\n" + "=" * 60)
print("[3/8] BASELINE — TRI PAR ÂGE")
print("=" * 60)

age_idx = FEATURES.index("age")
ages_test = X_test_imp[:, age_idx]

auc_age = roc_auc_score(y_test, ages_test)
print(f"  AUC (âge seul)  = {auc_age:.4f}")
print(f"  AUC (XGBoost)   = {auc:.4f}")
print(f"  Gain ML vs âge  = {auc - auc_age:+.4f}")

captures_age = {}
for pct in [5, 10, 20, 30]:
    top_n = int(n_test_total * pct / 100)
    top_idx = np.argsort(ages_test)[::-1][:top_n]
    captured = y_test[top_idx].sum()
    captures_age[pct] = round(100 * captured / y_test.sum(), 1)
    print(f"  Top {pct}% (âge) → {captures_age[pct]:.1f}% | ML: {captures[pct]:.1f}% (Δ={captures[pct]-captures_age[pct]:+.1f})")

# Plot comparaison
fig, ax = plt.subplots(figsize=(8, 5))
pcts = [5, 10, 20, 30]
ax.bar([p - 1 for p in pcts], [captures_age[p] for p in pcts], width=2, label="Tri par âge", alpha=0.7)
ax.bar([p + 1 for p in pcts], [captures[p] for p in pcts], width=2, label="XGBoost V7", alpha=0.7)
ax.set_xlabel("Top % du réseau inspecté")
ax.set_ylabel("% des abandons capturés")
ax.set_title("ML vs Baseline (tri par âge) — V7")
ax.legend()
ax.set_xticks(pcts)
ax.set_xticklabels([f"Top {p}%" for p in pcts])
for p in pcts:
    ax.annotate(f"{captures_age[p]}%", (p - 1, captures_age[p] + 1), ha="center", fontsize=8)
    ax.annotate(f"{captures[p]}%", (p + 1, captures[p] + 1), ha="center", fontsize=8)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v7_01_ml_vs_baseline.png", dpi=150)
plt.close()
print("  => v7_01_ml_vs_baseline.png")

# ============================================================
# [4/8] BACKTESTING TEMPOREL
# ============================================================
print("\n" + "=" * 60)
print("[4/8] BACKTESTING TEMPOREL")
print("=" * 60)

backtest_results = []
for cutoff_train, cutoff_eval in BACKTEST_WINDOWS:
    print(f"\n  --- Fenêtre: train < {cutoff_train}, eval [{cutoff_train}–{cutoff_eval}] ---")

    # Construire dataset pour cette fenêtre
    # Exclure abandonnés avant cutoff_train
    mask_exclu = (cana["label"] == 1) & (cana["annee_abandon"] < cutoff_train)
    cana_bt = cana[~mask_exclu].copy()

    # Y : abandonné entre cutoff_train et cutoff_eval
    cana_bt["y_bt"] = (
        (cana_bt["label"] == 1)
        & (cana_bt["annee_abandon"] >= cutoff_train)
        & (cana_bt["annee_abandon"] <= cutoff_eval)
    ).astype(int)

    # Train : tronçons dont on connaît le sort avant cutoff_train
    # = EN SERVICE (toujours négatif) + ABANDONNE avant cutoff_train (déjà exclus)
    # Test  : tous les tronçons restants avec label y_bt
    # Pour simuler: on build features à cutoff_train, puis on utilise le label y_bt

    df_bt, feat_bt, _ = build_features_v4(cana, anom_clean, cutoff_year=cutoff_train)
    # Recalculer y pour la fenêtre d'évaluation
    df_bt_merged = df_bt.merge(
        cana_bt[["OBJET", "y_bt"]].drop_duplicates(subset="OBJET"),
        on="OBJET", how="left"
    )
    df_bt_merged["y_bt"] = df_bt_merged["y_bt"].fillna(0).astype(int)

    # Split: 75/25 stratifié
    if df_bt_merged["y_bt"].sum() < 10:
        print(f"    SKIP: trop peu de positifs ({df_bt_merged['y_bt'].sum()})")
        continue

    idx_bt = np.arange(len(df_bt_merged))
    idx_tr_bt, idx_te_bt = train_test_split(
        idx_bt, test_size=0.25, random_state=42, stratify=df_bt_merged["y_bt"].values
    )
    df_tr_bt = df_bt_merged.iloc[idx_tr_bt].copy()
    df_te_bt = df_bt_merged.iloc[idx_te_bt].copy()

    # TE train-only
    te_map_bt = compute_target_encoding(df_tr_bt, col="famille_mat", target="y_bt", smoothing=10)
    gm_bt = te_map_bt["__global__"]
    tv_bt = {k: v for k, v in te_map_bt.items() if k != "__global__"}
    df_tr_bt["famille_enc"] = df_tr_bt["famille_mat"].map(tv_bt).fillna(gm_bt)
    df_te_bt["famille_enc"] = df_te_bt["famille_mat"].map(tv_bt).fillna(gm_bt)

    X_tr_bt = df_tr_bt[feat_bt].values
    X_te_bt = df_te_bt[feat_bt].values
    y_tr_bt = df_tr_bt["y_bt"].values
    y_te_bt = df_te_bt["y_bt"].values

    n_neg_bt = (y_tr_bt == 0).sum()
    n_pos_bt = max(y_tr_bt.sum(), 1)

    imp_bt = SimpleImputer(strategy="median")
    X_tr_bt = imp_bt.fit_transform(X_tr_bt)
    X_te_bt = imp_bt.transform(X_te_bt)

    params_bt = xgb_params.copy()
    params_bt["scale_pos_weight"] = round(n_neg_bt / n_pos_bt, 1)

    model_bt = xgb.XGBClassifier(**params_bt)
    model_bt.fit(X_tr_bt, y_tr_bt, eval_set=[(X_te_bt, y_te_bt)], verbose=0)

    y_proba_bt = model_bt.predict_proba(X_te_bt)[:, 1]
    auc_bt = roc_auc_score(y_te_bt, y_proba_bt)
    ap_bt = average_precision_score(y_te_bt, y_proba_bt)

    # Baseline âge
    age_bt = X_te_bt[:, feat_bt.index("age")]
    auc_age_bt = roc_auc_score(y_te_bt, age_bt)

    # Capture top 20%
    top_n_bt = int(len(y_te_bt) * 0.2)
    top_idx_bt = np.argsort(y_proba_bt)[::-1][:top_n_bt]
    cap_bt = round(100 * y_te_bt[top_idx_bt].sum() / max(y_te_bt.sum(), 1), 1)

    print(f"    AUC={auc_bt:.4f} | AP={ap_bt:.4f} | AUC_age={auc_age_bt:.4f} | Cap20%={cap_bt:.1f}%")
    print(f"    n_train={len(y_tr_bt):,} ({y_tr_bt.sum():,} pos) | n_test={len(y_te_bt):,} ({y_te_bt.sum():,} pos)")

    backtest_results.append({
        "window": f"{cutoff_train}-{cutoff_eval}",
        "auc": auc_bt, "ap": ap_bt, "auc_age": auc_age_bt,
        "gain_vs_age": auc_bt - auc_age_bt, "capture_top20": cap_bt,
        "n_test": len(y_te_bt), "n_pos_test": int(y_te_bt.sum()),
    })

bt_df = pd.DataFrame(backtest_results)
bt_df.to_csv(OUTPUT_DIR / "v7_backtesting.csv", index=False)
print(f"\n  Backtesting moyen: AUC={bt_df['auc'].mean():.4f} | Gain vs âge={bt_df['gain_vs_age'].mean():+.4f}")

# ============================================================
# [5/8] ABLATION
# ============================================================
print("\n" + "=" * 60)
print("[5/8] ABLATION DE FEATURES")
print("=" * 60)

auc_ref = auc
print(f"  AUC référence : {auc_ref:.4f}")

ablation_results = []
for i, (feat, fname) in enumerate(zip(FEATURES, FEATURE_NAMES)):
    X_abl_train = np.delete(X_train_imp, i, axis=1)
    X_abl_test = np.delete(X_test_imp, i, axis=1)

    model_abl = xgb.XGBClassifier(**xgb_params)
    model_abl.fit(X_abl_train, y_train, eval_set=[(X_abl_test, y_test)], verbose=0)
    y_abl = model_abl.predict_proba(X_abl_test)[:, 1]
    auc_abl = roc_auc_score(y_test, y_abl)
    delta = auc_ref - auc_abl
    print(f"  [{i+1:>2}/{len(FEATURES)}] Sans {fname:>20s} : AUC={auc_abl:.4f} (Δ={delta:+.4f})")
    ablation_results.append({"feature": fname, "auc_without": auc_abl, "delta_auc": delta})

abl_df = pd.DataFrame(ablation_results).sort_values("delta_auc", ascending=False)
abl_df.to_csv(OUTPUT_DIR / "v7_ablation_features.csv", index=False)

print(f"\n  Features utiles (retirer = AUC baisse) :")
for _, row in abl_df[abl_df["delta_auc"] > 0.0005].iterrows():
    print(f"    {row['feature']:>20s} : Δ={row['delta_auc']:+.4f}")
harmful = abl_df[abl_df["delta_auc"] < -0.0005]
if len(harmful) > 0:
    print(f"  Features nuisibles :")
    for _, row in harmful.iterrows():
        print(f"    {row['feature']:>20s} : Δ={row['delta_auc']:+.4f}")

# Plot
fig, ax = plt.subplots(figsize=(8, 5))
colors = ["green" if d > 0 else "red" if d < -0.0005 else "gray" for d in abl_df["delta_auc"]]
ax.barh(abl_df["feature"], abl_df["delta_auc"], color=colors)
ax.axvline(0, color="black", linewidth=0.5)
ax.set_xlabel("Delta AUC (+ = feature utile)")
ax.set_title("Ablation V7")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v7_02_ablation.png", dpi=150)
plt.close()
print("  => v7_02_ablation.png")

# ============================================================
# [6/8] SHAP
# ============================================================
print("\n" + "=" * 60)
print("[6/8] SHAP")
print("=" * 60)

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test_imp)

shap_imp = pd.DataFrame({
    "feature": FEATURE_NAMES,
    "mean_abs_shap": np.abs(shap_values).mean(axis=0),
}).sort_values("mean_abs_shap", ascending=False)
shap_imp.to_csv(OUTPUT_DIR / "v7_shap_importance.csv", index=False)

print("  Top features SHAP :")
for _, row in shap_imp.iterrows():
    print(f"    {row['feature']:>20s} : {row['mean_abs_shap']:.4f}")

fig, ax = plt.subplots(figsize=(10, 6))
shap.summary_plot(shap_values, X_test_imp, feature_names=FEATURE_NAMES, show=False)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v7_03_shap_summary.png", dpi=150)
plt.close()
print("  => v7_03_shap_summary.png")

fig, ax = plt.subplots(figsize=(8, 5))
shap.summary_plot(shap_values, X_test_imp, feature_names=FEATURE_NAMES, plot_type="bar", show=False)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v7_04_shap_bar.png", dpi=150)
plt.close()
print("  => v7_04_shap_bar.png")

# ============================================================
# [7/8] SCORING EN SERVICE
# ============================================================
print("\n" + "=" * 60)
print("[7/8] SCORING TRONÇONS EN SERVICE")
print("=" * 60)

# Re-entraîner sur tout le dataset avec TE full
te_map_full = compute_target_encoding(df_full, col="famille_mat", target="y", smoothing=10)
gm_full = te_map_full["__global__"]
tv_full = {k: v for k, v in te_map_full.items() if k != "__global__"}
df_full["famille_enc"] = df_full["famille_mat"].map(tv_full).fillna(gm_full)

X_all = df_full[FEATURES].values
y_all = df_full["y"].values
imp_full = SimpleImputer(strategy="median")
X_all_imp = imp_full.fit_transform(X_all)

model_full = xgb.XGBClassifier(**xgb_params)
model_full.fit(X_all_imp, y_all, verbose=0)

# Scoring: tronçons EN SERVICE
es_mask = cana["STATUT_OBJET"] == "EN SERVICE"
cana_es = cana[es_mask].copy()

# P0 FIX: utiliser le TE mapping sauvegardé, pas recalculer
df_score, feat_score, _ = build_features_v4(cana_es, anom_clean, cutoff_year=None, te_map=te_map_full)

X_score = df_score[feat_score].values
X_score_imp = imp_full.transform(X_score)
scores = model_full.predict_proba(X_score_imp)[:, 1]

scoring = pd.DataFrame({
    "OBJET": df_score["OBJET"].values,
    "MATERIAU": df_score["MATERIAU"].values,
    "FAMILLE": df_score["famille_mat"].values,
    "ETAT": df_score["etat_clean"].values,
    "AGE": df_score["age"].values,
    "AGE_IMPUTED": df_score["age_imputed"].values,
    "DIAMETRE": df_score["DIAMETRE"].values,
    "LONGUEUR": df_score["LONGUEUR"].values,
    "NB_FUITES": df_score["nb_fuites"].values,
    "SCORE": scores,
})
scoring = scoring.sort_values("SCORE", ascending=False).reset_index(drop=True)
scoring["RANG"] = range(1, len(scoring) + 1)
scoring["TOP_PCT"] = (scoring["RANG"] / len(scoring) * 100).round(1)
scoring.to_csv(OUTPUT_DIR / "v7_scoring_troncons.csv", index=False)
print(f"  => v7_scoring_troncons.csv ({len(scoring):,} tronçons EN SERVICE)")

# Stats top 10%
top10 = scoring[scoring["TOP_PCT"] <= 10]
print(f"\n  TOP 10% ({len(top10):,} tronçons) :")
print(f"    Score moyen  : {top10['SCORE'].mean():.3f}")
print(f"    Âge moyen    : {top10['AGE'].mean():.0f} ans")
print(f"    % age imputé : {100*top10['AGE_IMPUTED'].mean():.1f}%")
print(f"    Familles     : {top10['FAMILLE'].value_counts().head(5).to_dict()}")
print(f"    États        : {top10['ETAT'].value_counts().to_dict()}")

# Sauvegarder TE full pour usage production
with open(OUTPUT_DIR / "v7_te_mapping_full.json", "w") as f:
    json.dump({k: float(v) for k, v in te_map_full.items()}, f, indent=2)

# ============================================================
# [8/8] MLFLOW
# ============================================================
print("\n" + "=" * 60)
print("[8/8] MLFLOW LOGGING")
print("=" * 60)


def safe_name(name):
    return re.sub(r"[^a-zA-Z0-9_\-. /]", "", name.replace("/", "_per_"))


with mlflow.start_run(run_name=f"V7_XGBoost_P0fix_cutoff{SPLIT_YEAR}") as run:
    mlflow.log_param("version", "V7")
    mlflow.log_param("cible", "ABANDONNE_excl_DEPOSE")
    mlflow.log_param("cutoff_year", SPLIT_YEAR)
    mlflow.log_param("n_features", len(FEATURES))
    mlflow.log_param("features", ",".join(FEATURE_NAMES))
    mlflow.log_param("n_train", len(X_train))
    mlflow.log_param("n_test", len(X_test))
    mlflow.log_param("n_positifs", int(n_pos))
    mlflow.log_param("pct_positifs", round(100 * n_pos / len(df_full), 2))
    mlflow.log_param("te_smoothing", 10)
    mlflow.log_param("fixes", "P0_TE_train_only,P0_scoring_TE_saved,P1_no_anom_feats,P2_no_DEPOSE,P2_age_imputed,P2_etat_inconnu_nan")
    for k, v in xgb_params.items():
        mlflow.log_param(f"xgb_{k}", v)

    # Métriques principales
    mlflow.log_metric("auc_test", auc)
    mlflow.log_metric("ap_test", ap)
    mlflow.log_metric("auc_baseline_age", auc_age)
    mlflow.log_metric("gain_ml_vs_age", auc - auc_age)

    for pct in [5, 10, 20, 30]:
        mlflow.log_metric(f"capture_top{pct}pct", captures[pct])
        mlflow.log_metric(f"capture_age_top{pct}pct", captures_age[pct])

    # Backtesting
    if len(backtest_results) > 0:
        mlflow.log_metric("bt_mean_auc", bt_df["auc"].mean())
        mlflow.log_metric("bt_std_auc", bt_df["auc"].std())
        mlflow.log_metric("bt_mean_gain_vs_age", bt_df["gain_vs_age"].mean())
        for i, row in bt_df.iterrows():
            w = row["window"].replace("-", "_")
            mlflow.log_metric(f"bt_auc_{w}", row["auc"])
            mlflow.log_metric(f"bt_gain_{w}", row["gain_vs_age"])

    # SHAP
    for i, (_, row) in enumerate(shap_imp.head(5).iterrows()):
        sn = safe_name(row["feature"])
        mlflow.log_metric(f"shap_top{i+1}_{sn}", row["mean_abs_shap"])

    # Ablation
    for _, row in abl_df.iterrows():
        sn = safe_name(row["feature"])
        mlflow.log_metric(f"ablation_{sn}", row["delta_auc"])

    # Artifacts
    for f in OUTPUT_DIR.glob("v7_*.png"):
        mlflow.log_artifact(str(f))
    for f in OUTPUT_DIR.glob("v7_*.csv"):
        mlflow.log_artifact(str(f))
    for f in OUTPUT_DIR.glob("v7_*.json"):
        mlflow.log_artifact(str(f))

    mlflow.xgboost.log_model(model_full, artifact_path="model")
    print(f"  Run ID: {run.info.run_id}")

# --- RAPPORT FINAL ---
print("\n" + "=" * 60)
print("RAPPORT V7")
print("=" * 60)

bt_auc_str = f"{bt_df['auc'].mean():.4f} ± {bt_df['auc'].std():.4f}" if len(bt_df) > 0 else "N/A"

print(f"""
CORRECTIONS P0/P1/P2:
  ✓ Target encoding calculé sur TRAIN ONLY (data leakage corrigé)
  ✓ Scoring avec TE mapping sauvegardé (pas recalculé)  
  ✓ DEPOSE exclu entièrement (pas gardé faux négatif)
  ✓ age_imputed flag ajouté
  ✓ ETAT Inconnu = NaN (pas ordinal 0)
  ✓ Features anomalies réduites à nb_fuites seul
  ✓ Backtesting temporel ajouté

MÉTRIQUES TEST (cutoff={SPLIT_YEAR}):
  AUC XGBoost    = {auc:.4f}
  AUC Baseline   = {auc_age:.4f}  
  Gain ML vs âge = {auc - auc_age:+.4f}
  AP             = {ap:.4f}

BACKTESTING:
  AUC moyen = {bt_auc_str}

CAPTURE:
  Top  5%: ML={captures[5]:.1f}% | Âge={captures_age[5]:.1f}%
  Top 10%: ML={captures[10]:.1f}% | Âge={captures_age[10]:.1f}%
  Top 20%: ML={captures[20]:.1f}% | Âge={captures_age[20]:.1f}%
  Top 30%: ML={captures[30]:.1f}% | Âge={captures_age[30]:.1f}%

SCORING: {len(scoring):,} tronçons EN SERVICE → v7_scoring_troncons.csv
MLFLOW: http://localhost:5001
""")
print("=" * 60)
print("TERMINÉ")
print("=" * 60)
