"""
V8 — Modèle 2 : Prédiction de fuites/casses.
Pipeline complet : entraînement, évaluation, backtesting, scoring.

Complémentaire à V7 (Modèle 1 — abandon/fin de vie).

Pipeline :
  1. Chargement + construction dataset (3 horizons : 1, 3, 5 ans)
  2. Split temporel (train < 2018, test ≥ 2018)
  3. TE train-only + XGBoost
  4. Baseline (âge seul)
  5. Backtesting (3 fenêtres)
  6. SHAP
  7. Scoring EN SERVICE (probabilités horizon 1/3/5 ans)
  8. MLflow
"""

import re
import json
import sys
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
from sklearn.model_selection import train_test_split

# Ajouter le dossier parent pour importer V8/
sys.path.insert(0, str(Path(__file__).parent))
from data_cleaning import load_data, build_dataset, compute_target_encoding, ANNEE_REF

# Config
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

OBSERVATION_YEAR = 2018  # Train observe avant 2018
HORIZONS = [1, 3, 5]     # Prédire fuites sur 1, 3, 5 ans

# Backtesting : (observation_year, horizon) — on fixe horizon=3 pour comparer
BACKTEST_WINDOWS = [
    (2012, 3),  # observe avant 2012, prédit 2012-2014
    (2015, 3),  # observe avant 2015, prédit 2015-2017
    (2018, 3),  # observe avant 2018, prédit 2018-2020
]

print("=" * 60)
print("V8 — MODÈLE 2 : PRÉDICTION DE FUITES/CASSES")
print("=" * 60)

# --- MLflow ---
mlflow.set_tracking_uri("file:///" + str(Path(__file__).parent.parent / "mlruns").replace("\\", "/"))
mlflow.set_experiment("fuites_canalisations_v8")
print()

# ============================================================
# [1/8] CHARGEMENT
# ============================================================
print("[1/8] Chargement des données...")
cana, fuites = load_data(DATA_DIR)

# ============================================================
# [2/8] MULTI-HORIZON : ENTRAÎNEMENT SUR HORIZON 1, 3, 5 ANS
# ============================================================
results_all = {}

for horizon in HORIZONS:
    print("\n" + "=" * 60)
    print(f"[2/8] HORIZON = {horizon} AN(S) — observation {OBSERVATION_YEAR}")
    print("=" * 60)

    # Build dataset
    df, FEATURES, FEATURE_NAMES = build_dataset(
        cana, fuites, observation_year=OBSERVATION_YEAR, horizon=horizon
    )

    # Split stratifié (les tronçons sont tous "observés" à la même date)
    y_full = df["y"].values
    idx_all = np.arange(len(df))
    idx_train, idx_test = train_test_split(
        idx_all, test_size=0.25, random_state=42, stratify=y_full
    )

    df_train = df.iloc[idx_train].copy()
    df_test = df.iloc[idx_test].copy()

    # TE train-only
    te_map = compute_target_encoding(df_train, col="famille_mat", target="y", smoothing=10)
    gm = te_map["__global__"]
    tv = {k: v for k, v in te_map.items() if k != "__global__"}
    df_train["famille_enc"] = df_train["famille_mat"].map(tv).fillna(gm)
    df_test["famille_enc"] = df_test["famille_mat"].map(tv).fillna(gm)

    X_train = df_train[FEATURES].values
    X_test = df_test[FEATURES].values
    y_train = df_train["y"].values
    y_test = df_test["y"].values

    n_pos = y_full.sum()
    n_neg = len(y_full) - n_pos

    print(f"  Train: {len(df_train):,} ({y_train.sum():,} pos) | Test: {len(df_test):,} ({y_test.sum():,} pos)")
    print(f"  TE mapping: {', '.join(f'{k}={v:.4f}' for k, v in sorted(tv.items()))}")

    # Impute
    imp = SimpleImputer(strategy="median")
    X_train_imp = imp.fit_transform(X_train)
    X_test_imp = imp.transform(X_test)

    # XGBoost
    xgb_params = {
        "n_estimators": 500,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": round(n_neg / max(n_pos, 1), 1),
        "eval_metric": "auc",
        "random_state": 42,
        "n_jobs": -1,
    }

    model = xgb.XGBClassifier(**xgb_params)
    model.fit(X_train_imp, y_train, eval_set=[(X_test_imp, y_test)], verbose=0)

    y_proba = model.predict_proba(X_test_imp)[:, 1]
    auc = roc_auc_score(y_test, y_proba)
    ap = average_precision_score(y_test, y_proba)

    print(f"\n  XGBoost H={horizon}: AUC={auc:.4f} | AP={ap:.4f}")

    # Capture @top %
    captures = {}
    for pct in [5, 10, 20, 30]:
        top_n = int(len(y_test) * pct / 100)
        top_idx = np.argsort(y_proba)[::-1][:top_n]
        captured = y_test[top_idx].sum()
        captures[pct] = round(100 * captured / max(y_test.sum(), 1), 1)
        print(f"  Top {pct}% → capture {captures[pct]:.1f}% des fuites")

    # ============================================================
    # [3/8] BASELINE AGE
    # ============================================================
    age_idx = FEATURES.index("age")
    ages_test = X_test_imp[:, age_idx]
    auc_age = roc_auc_score(y_test, ages_test)

    captures_age = {}
    for pct in [5, 10, 20, 30]:
        top_n = int(len(y_test) * pct / 100)
        top_idx = np.argsort(ages_test)[::-1][:top_n]
        captured = y_test[top_idx].sum()
        captures_age[pct] = round(100 * captured / max(y_test.sum(), 1), 1)

    print(f"\n  Baseline âge : AUC={auc_age:.4f}")
    print(f"  Gain ML vs âge : {auc - auc_age:+.4f}")
    for pct in [5, 10, 20]:
        print(f"  Top {pct}%: ML={captures[pct]}% vs Âge={captures_age[pct]}% (Δ={captures[pct]-captures_age[pct]:+.1f})")

    results_all[horizon] = {
        "auc": auc, "ap": ap, "auc_age": auc_age,
        "captures": captures, "captures_age": captures_age,
        "model": model, "imp": imp, "te_map": te_map,
        "xgb_params": xgb_params,
        "n_train": len(df_train), "n_test": len(df_test),
        "n_pos": int(n_pos), "y_test": y_test, "y_proba": y_proba,
        "X_test_imp": X_test_imp,
        "df_test": df_test,
    }

# ============================================================
# [4/8] PLOT COMPARAISON HORIZONS
# ============================================================
print("\n" + "=" * 60)
print("[4/8] COMPARAISON DES 3 HORIZONS")
print("=" * 60)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# AUC par horizon
aucs_ml = [results_all[h]["auc"] for h in HORIZONS]
aucs_age = [results_all[h]["auc_age"] for h in HORIZONS]
x = np.arange(len(HORIZONS))
axes[0].bar(x - 0.2, aucs_age, 0.4, label="Baseline (âge)", alpha=0.7)
axes[0].bar(x + 0.2, aucs_ml, 0.4, label="XGBoost V8", alpha=0.7)
axes[0].set_xticks(x)
axes[0].set_xticklabels([f"{h} an(s)" for h in HORIZONS])
axes[0].set_ylabel("AUC")
axes[0].set_title("AUC par horizon")
axes[0].legend()
for i, h in enumerate(HORIZONS):
    axes[0].annotate(f"{aucs_ml[i]:.3f}", (i + 0.2, aucs_ml[i] + 0.005), ha="center", fontsize=8)
    axes[0].annotate(f"{aucs_age[i]:.3f}", (i - 0.2, aucs_age[i] + 0.005), ha="center", fontsize=8)

# Capture @20% par horizon
caps_ml = [results_all[h]["captures"][20] for h in HORIZONS]
caps_age = [results_all[h]["captures_age"][20] for h in HORIZONS]
axes[1].bar(x - 0.2, caps_age, 0.4, label="Baseline (âge)", alpha=0.7)
axes[1].bar(x + 0.2, caps_ml, 0.4, label="XGBoost V8", alpha=0.7)
axes[1].set_xticks(x)
axes[1].set_xticklabels([f"{h} an(s)" for h in HORIZONS])
axes[1].set_ylabel("Capture Top 20% (%)")
axes[1].set_title("Capture@20% par horizon")
axes[1].legend()
for i, h in enumerate(HORIZONS):
    axes[1].annotate(f"{caps_ml[i]}%", (i + 0.2, caps_ml[i] + 1), ha="center", fontsize=8)
    axes[1].annotate(f"{caps_age[i]}%", (i - 0.2, caps_age[i] + 1), ha="center", fontsize=8)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v8_01_horizons_comparison.png", dpi=150)
plt.close()
print("  => v8_01_horizons_comparison.png")

for h in HORIZONS:
    r = results_all[h]
    print(f"  H={h}an: AUC={r['auc']:.4f} (âge={r['auc_age']:.4f}, gain={r['auc']-r['auc_age']:+.4f}) | Cap20%={r['captures'][20]}%")

# ============================================================
# [5/8] BACKTESTING (horizon=3 fixe)
# ============================================================
print("\n" + "=" * 60)
print("[5/8] BACKTESTING TEMPOREL (horizon=3)")
print("=" * 60)

backtest_results = []
for obs_year, bt_horizon in BACKTEST_WINDOWS:
    print(f"\n  --- Fenêtre: observation={obs_year}, prédit [{obs_year}–{obs_year+bt_horizon}) ---")

    df_bt, feat_bt, _ = build_dataset(cana, fuites, observation_year=obs_year, horizon=bt_horizon)

    if df_bt["y"].sum() < 10:
        print(f"    SKIP: trop peu de positifs ({df_bt['y'].sum()})")
        continue

    idx_bt = np.arange(len(df_bt))
    idx_tr_bt, idx_te_bt = train_test_split(
        idx_bt, test_size=0.25, random_state=42, stratify=df_bt["y"].values
    )
    df_tr_bt = df_bt.iloc[idx_tr_bt].copy()
    df_te_bt = df_bt.iloc[idx_te_bt].copy()

    te_bt = compute_target_encoding(df_tr_bt, col="famille_mat", target="y", smoothing=10)
    gm_bt = te_bt["__global__"]
    tv_bt = {k: v for k, v in te_bt.items() if k != "__global__"}
    df_tr_bt["famille_enc"] = df_tr_bt["famille_mat"].map(tv_bt).fillna(gm_bt)
    df_te_bt["famille_enc"] = df_te_bt["famille_mat"].map(tv_bt).fillna(gm_bt)

    X_tr_bt = df_tr_bt[feat_bt].values
    X_te_bt = df_te_bt[feat_bt].values
    y_tr_bt = df_tr_bt["y"].values
    y_te_bt = df_te_bt["y"].values

    n_neg_bt = (y_tr_bt == 0).sum()
    n_pos_bt = max(y_tr_bt.sum(), 1)

    imp_bt = SimpleImputer(strategy="median")
    X_tr_bt = imp_bt.fit_transform(X_tr_bt)
    X_te_bt = imp_bt.transform(X_te_bt)

    params_bt = results_all[3]["xgb_params"].copy()
    params_bt["scale_pos_weight"] = round(n_neg_bt / n_pos_bt, 1)

    model_bt = xgb.XGBClassifier(**params_bt)
    model_bt.fit(X_tr_bt, y_tr_bt, eval_set=[(X_te_bt, y_te_bt)], verbose=0)

    y_proba_bt = model_bt.predict_proba(X_te_bt)[:, 1]
    auc_bt = roc_auc_score(y_te_bt, y_proba_bt)
    ap_bt = average_precision_score(y_te_bt, y_proba_bt)

    age_bt = X_te_bt[:, feat_bt.index("age")]
    auc_age_bt = roc_auc_score(y_te_bt, age_bt)

    top_n_bt = int(len(y_te_bt) * 0.2)
    top_idx_bt = np.argsort(y_proba_bt)[::-1][:top_n_bt]
    cap_bt = round(100 * y_te_bt[top_idx_bt].sum() / max(y_te_bt.sum(), 1), 1)

    print(f"    AUC={auc_bt:.4f} | AP={ap_bt:.4f} | AUC_age={auc_age_bt:.4f} | Cap20%={cap_bt:.1f}%")
    print(f"    n_train={len(y_tr_bt):,} ({y_tr_bt.sum():,} pos) | n_test={len(y_te_bt):,} ({y_te_bt.sum():,} pos)")

    backtest_results.append({
        "window": f"obs{obs_year}_h{bt_horizon}",
        "auc": auc_bt, "ap": ap_bt, "auc_age": auc_age_bt,
        "gain_vs_age": auc_bt - auc_age_bt, "capture_top20": cap_bt,
        "n_test": len(y_te_bt), "n_pos_test": int(y_te_bt.sum()),
    })

bt_df = pd.DataFrame(backtest_results)
bt_df.to_csv(OUTPUT_DIR / "v8_backtesting.csv", index=False)
if len(bt_df) > 0:
    print(f"\n  Backtesting moyen: AUC={bt_df['auc'].mean():.4f} ± {bt_df['auc'].std():.4f}")

# ============================================================
# [6/8] SHAP (horizon=3, modèle principal)
# ============================================================
print("\n" + "=" * 60)
print("[6/8] SHAP (horizon=3)")
print("=" * 60)

r3 = results_all[3]
explainer = shap.TreeExplainer(r3["model"])
shap_values = explainer.shap_values(r3["X_test_imp"])

shap_imp = pd.DataFrame({
    "feature": FEATURE_NAMES,
    "mean_abs_shap": np.abs(shap_values).mean(axis=0),
}).sort_values("mean_abs_shap", ascending=False)
shap_imp.to_csv(OUTPUT_DIR / "v8_shap_importance.csv", index=False)

print("  Top features SHAP (horizon=3) :")
for _, row in shap_imp.iterrows():
    print(f"    {row['feature']:>25s} : {row['mean_abs_shap']:.4f}")

fig, ax = plt.subplots(figsize=(8, 5))
shap.summary_plot(shap_values, r3["X_test_imp"], feature_names=FEATURE_NAMES, show=False)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v8_02_shap_summary.png", dpi=150)
plt.close()
print("  => v8_02_shap_summary.png")

fig, ax = plt.subplots(figsize=(8, 4))
shap.summary_plot(shap_values, r3["X_test_imp"], feature_names=FEATURE_NAMES, plot_type="bar", show=False)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v8_03_shap_bar.png", dpi=150)
plt.close()
print("  => v8_03_shap_bar.png")

# ============================================================
# [7/8] SCORING EN SERVICE (3 horizons)
# ============================================================
print("\n" + "=" * 60)
print("[7/8] SCORING EN SERVICE (horizons 1, 3, 5 ans)")
print("=" * 60)

# Ré-entraîner sur tout le dataset pour chaque horizon, scorer les EN SERVICE
es_mask = cana["STATUT_OBJET"] == "EN SERVICE"
cana_es = cana[es_mask].copy()

scoring_frames = []
for horizon in HORIZONS:
    r = results_all[horizon]

    # Re-build full dataset et re-train
    df_full, feat_full, _ = build_dataset(
        cana, fuites, observation_year=OBSERVATION_YEAR, horizon=horizon
    )
    te_full = compute_target_encoding(df_full, col="famille_mat", target="y", smoothing=10)
    gm_f = te_full["__global__"]
    tv_f = {k: v for k, v in te_full.items() if k != "__global__"}
    df_full["famille_enc"] = df_full["famille_mat"].map(tv_f).fillna(gm_f)

    X_full = df_full[feat_full].values
    y_all = df_full["y"].values
    imp_full = SimpleImputer(strategy="median")
    X_full_imp = imp_full.fit_transform(X_full)

    model_full = xgb.XGBClassifier(**r["xgb_params"])
    model_full.fit(X_full_imp, y_all, verbose=0)

    # Scorer les EN SERVICE actuels à observation_year=ANNEE_REF (2024)
    df_score, feat_score, _ = build_dataset(
        cana_es.copy(), fuites, observation_year=ANNEE_REF, horizon=horizon, te_map=te_full
    )
    X_score = df_score[feat_score].values
    X_score_imp = imp_full.transform(X_score)
    scores = model_full.predict_proba(X_score_imp)[:, 1]

    df_score[f"score_h{horizon}"] = scores
    scoring_frames.append(df_score[["OBJET", f"score_h{horizon}"]])

    # Sauvegarder TE
    with open(OUTPUT_DIR / f"v8_te_mapping_h{horizon}.json", "w") as f:
        json.dump({k: float(v) for k, v in te_full.items()}, f, indent=2)

# Merge all horizons
scoring = cana_es[["OBJET", "MATERIAU", "DIAMETRE"]].copy()
scoring["famille_mat"] = cana_es["famille_mat"]
scoring["age"] = ANNEE_REF - cana_es["annee_pose"]
scoring.loc[~cana_es["date_fiable"], "age"] = np.nan

for sf in scoring_frames:
    scoring = scoring.merge(sf, on="OBJET", how="left")

# Rang principal sur horizon 3 ans
scoring = scoring.sort_values("score_h3", ascending=False).reset_index(drop=True)
scoring["rang"] = range(1, len(scoring) + 1)
scoring["top_pct"] = (scoring["rang"] / len(scoring) * 100).round(1)

scoring.to_csv(OUTPUT_DIR / "v8_scoring_fuites.csv", index=False)
print(f"  => v8_scoring_fuites.csv ({len(scoring):,} tronçons)")

top10 = scoring[scoring["top_pct"] <= 10]
print(f"\n  TOP 10% ({len(top10):,} tronçons) :")
print(f"    Score H3 moyen : {top10['score_h3'].mean():.3f}")
print(f"    Âge moyen      : {top10['age'].mean():.0f} ans")
print(f"    Familles       : {top10['famille_mat'].value_counts().head(5).to_dict()}")

# ============================================================
# [8/8] MLFLOW
# ============================================================
print("\n" + "=" * 60)
print("[8/8] MLFLOW LOGGING")
print("=" * 60)


def safe_name(name):
    return re.sub(r"[^a-zA-Z0-9_\-. /]", "", name.replace("/", "_per_"))


with mlflow.start_run(run_name=f"V8_Fuites_obs{OBSERVATION_YEAR}") as run:
    mlflow.log_param("version", "V8")
    mlflow.log_param("objectif", "prediction_fuites_casses")
    mlflow.log_param("observation_year", OBSERVATION_YEAR)
    mlflow.log_param("horizons", "1,3,5")
    mlflow.log_param("n_features", 4)
    mlflow.log_param("features", ",".join(FEATURE_NAMES))
    mlflow.log_param("te_smoothing", 10)

    for h in HORIZONS:
        r = results_all[h]
        mlflow.log_metric(f"auc_h{h}", r["auc"])
        mlflow.log_metric(f"ap_h{h}", r["ap"])
        mlflow.log_metric(f"auc_age_h{h}", r["auc_age"])
        mlflow.log_metric(f"gain_vs_age_h{h}", r["auc"] - r["auc_age"])
        mlflow.log_metric(f"n_train_h{h}", r["n_train"])
        mlflow.log_metric(f"n_test_h{h}", r["n_test"])
        mlflow.log_metric(f"n_pos_h{h}", r["n_pos"])
        for pct in [5, 10, 20, 30]:
            mlflow.log_metric(f"capture_top{pct}pct_h{h}", r["captures"][pct])

    for k, v in results_all[3]["xgb_params"].items():
        mlflow.log_param(f"xgb_{k}", v)

    if len(bt_df) > 0:
        mlflow.log_metric("bt_mean_auc", bt_df["auc"].mean())
        mlflow.log_metric("bt_std_auc", bt_df["auc"].std())

    for _, row in shap_imp.iterrows():
        sn = safe_name(row["feature"])
        mlflow.log_metric(f"shap_{sn}", row["mean_abs_shap"])

    for f in OUTPUT_DIR.glob("v8_*.png"):
        mlflow.log_artifact(str(f))
    for f in OUTPUT_DIR.glob("v8_*.csv"):
        mlflow.log_artifact(str(f))
    for f in OUTPUT_DIR.glob("v8_*.json"):
        mlflow.log_artifact(str(f))

    print(f"  Run ID: {run.info.run_id}")

# --- RAPPORT ---
print("\n" + "=" * 60)
print("RAPPORT V8 — MODÈLE 2 (FUITES/CASSES)")
print("=" * 60)

bt_str = f"{bt_df['auc'].mean():.4f} ± {bt_df['auc'].std():.4f}" if len(bt_df) > 0 else "N/A"

print(f"""
OBJECTIF : Prédire ≥1 fuite/casse par tronçon sur horizon 1/3/5 ans
FEATURES : 4 (matériau, diamètre, âge, historique casses)
OBSERVATION : {OBSERVATION_YEAR}

MÉTRIQUES PAR HORIZON :""")

for h in HORIZONS:
    r = results_all[h]
    print(f"  H={h}an: AUC={r['auc']:.4f} | AP={r['ap']:.4f} | Gain vs âge={r['auc']-r['auc_age']:+.4f} | Cap@20%={r['captures'][20]}%")

print(f"""
BACKTESTING (horizon=3) :
  AUC moyen = {bt_str}

SCORING : {len(scoring):,} tronçons EN SERVICE → v8_scoring_fuites.csv
  Colonnes : score_h1, score_h3, score_h5

USAGE :
  - Ciblage recherche active : top 10-20% par score_h1
  - KPI solver : somme(score_h3) des tronçons renouvelés = fuites évitées
  - Argumentaire élus : "renouveler ces X tronçons évite Y fuites sur 5 ans"

MLFLOW : http://localhost:5001
""")
print("=" * 60)
print("TERMINÉ")
print("=" * 60)
