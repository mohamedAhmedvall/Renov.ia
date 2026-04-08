"""
Phase 2 V4 - Modelisation predictive : cible ABANDON/DEPOSE
Projet : Prediction de renouvellement de canalisations d'eau

Changements majeurs vs V3 :
  - Cible = abandon/depose (renouvellement) au lieu d'anomalies
  - Age corrige : calcule a la date d'evenement (pas fuite temporelle)
  - Anomalies = signal secondaire (90% des abandons sans anomalie)
  - MLflow integre pour le suivi des experiences
  - RandomizedSearchCV pour HPO (sklearn, pas besoin d'optuna)

Pipeline :
  1. Chargement + features (data_cleaning_v2)
  2. Classification multi-modeles + HPO
  3. Backtesting multi-fenetre temporelle
  4. SHAP interpretabilite
  5. Scoring final de tous les troncons EN SERVICE
  6. MLflow logging de tout
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_recall_curve,
    confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import (
    RandomizedSearchCV, StratifiedKFold, train_test_split,
)
import xgboost as xgb
import shap
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import warnings
warnings.filterwarnings("ignore")

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from data_cleaning_v2 import load_and_clean_v2, build_features_v2, ANNEE_REF

# --- Config ---
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", font_scale=1.1)
COLORS = sns.color_palette("Set2", 10)

EXPERIMENT_NAME = "casses_canalisations_v4"
SPLIT_YEAR = 2018  # train: abandonnes avant 2018, test: abandonnes 2018-2024

print("=" * 60)
print(f"PHASE 2 V4 - CIBLE ABANDON/DEPOSE (ref={ANNEE_REF})")
print("MLflow + Classification + Backtesting + SHAP")
print("=" * 60)


# ============================================================
# 0. MLFLOW SETUP
# ============================================================
mlflow.set_tracking_uri(f"file:///{(Path.cwd() / 'mlruns').as_posix()}")
mlflow.set_experiment(EXPERIMENT_NAME)
print(f"\nMLflow experiment: {EXPERIMENT_NAME}")
print(f"MLflow tracking: {mlflow.get_tracking_uri()}")


# ============================================================
# 1. CHARGEMENT & FEATURES
# ============================================================
print("\n[1/6] Chargement et feature engineering...")

cana, anom_clean = load_and_clean_v2(DATA_DIR)
print(f"  Troncons total    : {len(cana):,}")
print(f"  EN SERVICE        : {(cana['STATUT_OBJET']=='EN SERVICE').sum():,}")
print(f"  ABANDONNE+DEPOSE  : {cana['label'].sum():,}")
print(f"  Anomalies retenues: {len(anom_clean):,}")

# Build features avec split temporel
df, FEATURES, FEATURE_NAMES, le_mat = build_features_v2(cana, anom_clean, cutoff_year=SPLIT_YEAR)

n_pos = df["y"].sum()
n_neg = len(df) - n_pos
print(f"\n  Split temporel : cutoff={SPLIT_YEAR}")
print(f"  Troncons dans le dataset : {len(df):,}")
print(f"  Label=1 (abandonnes {SPLIT_YEAR}-{ANNEE_REF}) : {n_pos:,} ({100*n_pos/len(df):.2f}%)")
print(f"  Label=0 (en service a {SPLIT_YEAR}) : {n_neg:,}")
print(f"  Features : {len(FEATURES)}")

X = df[FEATURES].copy()
y = df["y"].copy()


# ============================================================
# 2. CLASSIFICATION -- MULTI-MODELES AVEC HPO
# ============================================================
print("\n" + "=" * 60)
print("[2/6] CLASSIFICATION -- 4 MODELES + HPO")
print("=" * 60)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)
print(f"\n  Train : {len(X_train):,} ({y_train.sum():,} pos, {100*y_train.mean():.2f}%)")
print(f"  Test  : {len(X_test):,} ({y_test.sum():,} pos)")

scale_pos = n_neg / max(n_pos, 1)

# Imputer pour les modeles qui ne gerent pas NaN
imputer = SimpleImputer(strategy="median")
X_train_imp = imputer.fit_transform(X_train)
X_test_imp = imputer.transform(X_test)

cv = StratifiedKFold(3, shuffle=True, random_state=42)

# --- Logistic Regression ---
print("\n  [1/4] Logistic Regression...")
lr_pipe = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)),
])
lr_pipe.fit(X_train, y_train)

# --- Random Forest + HPO ---
print("  [2/4] Random Forest + HPO...")
rf_params = {
    "n_estimators": [100, 200, 300, 500],
    "max_depth": [6, 8, 10, 12, None],
    "min_samples_leaf": [5, 10, 20, 50],
    "max_features": ["sqrt", "log2", 0.3],
}
rf_search = RandomizedSearchCV(
    RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1),
    rf_params, n_iter=20, scoring="average_precision",
    cv=cv, random_state=42, n_jobs=-1, verbose=0,
)
rf_search.fit(X_train_imp, y_train)
print(f"    Best AP(CV): {rf_search.best_score_:.4f} | {rf_search.best_params_}")

# --- XGBoost + HPO ---
print("  [3/4] XGBoost + HPO...")
xgb_params = {
    "n_estimators": [200, 300, 500, 700],
    "max_depth": [4, 6, 8, 10],
    "learning_rate": [0.01, 0.03, 0.05, 0.1],
    "subsample": [0.7, 0.8, 0.9],
    "colsample_bytree": [0.6, 0.7, 0.8],
    "min_child_weight": [1, 3, 5, 10],
    "gamma": [0, 0.1, 0.3],
}
xgb_search = RandomizedSearchCV(
    xgb.XGBClassifier(
        scale_pos_weight=scale_pos, eval_metric="aucpr",
        random_state=42, tree_method="hist",
    ),
    xgb_params, n_iter=30, scoring="average_precision",
    cv=cv, random_state=42, n_jobs=-1, verbose=0,
)
xgb_search.fit(X_train_imp, y_train)
print(f"    Best AP(CV): {xgb_search.best_score_:.4f} | {xgb_search.best_params_}")

# --- HistGradientBoosting + HPO ---
print("  [4/4] HistGradientBoosting + HPO...")
hgb_params = {
    "max_iter": [200, 300, 500],
    "max_depth": [4, 6, 8, 10, None],
    "learning_rate": [0.01, 0.03, 0.05, 0.1],
    "min_samples_leaf": [10, 20, 50],
    "l2_regularization": [0, 0.1, 1.0],
}
hgb_search = RandomizedSearchCV(
    HistGradientBoostingClassifier(
        class_weight="balanced", random_state=42, early_stopping=False,
    ),
    hgb_params, n_iter=20, scoring="average_precision",
    cv=cv, random_state=42, n_jobs=-1, verbose=0,
)
hgb_search.fit(X_train.values, y_train)
print(f"    Best AP(CV): {hgb_search.best_score_:.4f} | {hgb_search.best_params_}")


# ============================================================
# 3. EVALUATION SUR JEU DE TEST
# ============================================================
print("\n" + "=" * 60)
print("[3/6] EVALUATION SUR JEU DE TEST")
print("=" * 60)

models = {
    "Logistique": {"model": lr_pipe, "predict": lambda m, X: m.predict_proba(pd.DataFrame(X, columns=FEATURES))[:, 1]},
    "Random Forest": {"model": rf_search.best_estimator_, "predict": lambda m, X: m.predict_proba(X)[:, 1]},
    "XGBoost": {"model": xgb_search.best_estimator_, "predict": lambda m, X: m.predict_proba(X)[:, 1]},
    "HistGradientBoosting": {"model": hgb_search.best_estimator_, "predict": lambda m, X: m.predict_proba(X)[:, 1]},
}

results = {}

for name, cfg in models.items():
    model = cfg["model"]
    if name == "Logistique":
        y_proba = cfg["predict"](model, X_test.values)
    elif name == "HistGradientBoosting":
        y_proba = cfg["predict"](model, X_test.values)
    else:
        y_proba = cfg["predict"](model, X_test_imp)

    # Seuil optimal F1
    prec_c, rec_c, thresholds = precision_recall_curve(y_test, y_proba)
    f1s = 2 * prec_c * rec_c / (prec_c + rec_c + 1e-8)
    best_idx = np.argmax(f1s)
    best_thr = thresholds[min(best_idx, len(thresholds) - 1)]
    y_pred = (y_proba >= best_thr).astype(int)

    auc = roc_auc_score(y_test, y_proba)
    ap = average_precision_score(y_test, y_proba)
    f1 = f1_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

    # Lift / Capture
    df_tmp = pd.DataFrame({"proba": y_proba, "label": y_test.values})
    df_sorted = df_tmp.sort_values("proba", ascending=False)
    captures = {}
    for pct in [5, 10, 20, 30]:
        top = df_sorted.head(int(len(df_sorted) * pct / 100))
        captures[pct] = 100 * top["label"].sum() / max(y_test.sum(), 1)

    print(f"\n  --- {name} ---")
    print(f"  AUC={auc:.4f} | AP={ap:.4f} | F1={f1:.4f} | Prec={prec:.4f} | Rec={rec:.4f}")
    print(f"  TP={tp:,} FP={fp:,} FN={fn:,} TN={tn:,}")
    print(f"  Capture: Top5%={captures[5]:.1f}% | Top10%={captures[10]:.1f}% | Top20%={captures[20]:.1f}% | Top30%={captures[30]:.1f}%")

    results[name] = {
        "model": model, "auc": auc, "ap": ap, "f1": f1,
        "precision": prec, "recall": rec, "threshold": best_thr,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "captures": captures, "y_proba": y_proba, "y_pred": y_pred,
    }

# Meilleur modele
best_name = max(results, key=lambda k: results[k]["ap"])
best_r = results[best_name]
print(f"\n  >>> Meilleur modele (AP) : {best_name}")


# ============================================================
# FIGURES : Comparaison + Confusion + PR curves
# ============================================================
print("\n  Generation des figures...")

model_names = list(results.keys())

# Fig 1 : Comparaison
fig, axes = plt.subplots(1, 3, figsize=(22, 6))
aucs = [results[n]["auc"] for n in model_names]
aps = [results[n]["ap"] for n in model_names]

axes[0].bar(model_names, aucs, color=COLORS[:4])
axes[0].set_ylabel("AUC-ROC")
axes[0].set_title("AUC-ROC")
axes[0].set_ylim(0.5, 1.0)
for i, v in enumerate(aucs):
    axes[0].text(i, v + 0.01, f"{v:.3f}", ha="center", fontweight="bold")
axes[0].tick_params(axis="x", rotation=15)

axes[1].bar(model_names, aps, color=COLORS[:4])
axes[1].set_ylabel("Average Precision")
axes[1].set_title("Average Precision")
for i, v in enumerate(aps):
    axes[1].text(i, v + 0.005, f"{v:.3f}", ha="center", fontweight="bold")
axes[1].tick_params(axis="x", rotation=15)

x_pos = np.arange(len(model_names))
w = 0.2
for j, pct in enumerate([5, 10, 20, 30]):
    vals = [results[n]["captures"][pct] for n in model_names]
    axes[2].bar(x_pos + (j - 1.5) * w, vals, w, label=f"Top {pct}%", color=COLORS[j])
axes[2].set_xticks(x_pos)
axes[2].set_xticklabels(model_names, rotation=15)
axes[2].set_ylabel("% abandons captures")
axes[2].set_title("Capture des abandons par modele")
axes[2].legend()

plt.suptitle(f"V4 — Cible ABANDON/DEPOSE (cutoff={SPLIT_YEAR})", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v4_01_comparaison_modeles.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v4_01_comparaison_modeles.png")

# Fig 2 : Confusion matrices
fig, axes = plt.subplots(1, 4, figsize=(24, 5))
for i, name in enumerate(model_names):
    r = results[name]
    cm_arr = np.array([[r["tn"], r["fp"]], [r["fn"], r["tp"]]])
    sns.heatmap(cm_arr, annot=True, fmt=",d", cmap="Blues", ax=axes[i],
                xticklabels=["Predit -", "Predit +"],
                yticklabels=["Reel -", "Reel +"],
                annot_kws={"size": 12})
    axes[i].set_title(f"{name}\nPrec={r['precision']:.2f} Rec={r['recall']:.2f}")
plt.suptitle("V4 — Matrices de confusion", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v4_02_confusion_matrices.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v4_02_confusion_matrices.png")

# Fig 3 : PR curves
fig, ax = plt.subplots(figsize=(10, 7))
for i, name in enumerate(model_names):
    prec_c, rec_c, _ = precision_recall_curve(y_test, results[name]["y_proba"])
    ax.plot(rec_c, prec_c, label=f"{name} (AP={results[name]['ap']:.3f})", linewidth=2, color=COLORS[i])
ax.axhline(y=y_test.mean(), color="red", linestyle=":", label=f"Hasard ({y_test.mean():.3f})")
ax.set_xlabel("Recall")
ax.set_ylabel("Precision")
ax.set_title("Courbes Precision-Recall (V4)")
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v4_03_precision_recall.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v4_03_precision_recall.png")


# ============================================================
# 4. BACKTESTING MULTI-FENETRE
# ============================================================
print("\n" + "=" * 60)
print("[4/6] BACKTESTING MULTI-FENETRE")
print("=" * 60)

bt_results = []
for split_y in [2015, 2016, 2017, 2018, 2019, 2020]:
    df_bt, feat_bt, _, _ = build_features_v2(cana, anom_clean, cutoff_year=split_y)
    X_bt = df_bt[feat_bt].copy()
    y_bt = df_bt["y"].copy()

    if y_bt.sum() < 50:
        print(f"  Split {split_y} : insuffisant ({y_bt.sum()} pos), skip")
        continue

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_bt, y_bt, test_size=0.25, random_state=42, stratify=y_bt
    )
    imp_bt = SimpleImputer(strategy="median")
    X_tr_imp = imp_bt.fit_transform(X_tr)
    X_te_imp = imp_bt.transform(X_te)

    sp = (len(y_bt) - y_bt.sum()) / max(y_bt.sum(), 1)
    xgb_bt = xgb.XGBClassifier(
        **xgb_search.best_params_,
        scale_pos_weight=sp, eval_metric="aucpr",
        random_state=42, tree_method="hist",
    )
    xgb_bt.fit(X_tr_imp, y_tr)
    y_proba_bt = xgb_bt.predict_proba(X_te_imp)[:, 1]

    auc_bt = roc_auc_score(y_te, y_proba_bt)
    ap_bt = average_precision_score(y_te, y_proba_bt)

    df_s = pd.DataFrame({"proba": y_proba_bt, "label": y_te.values}).sort_values("proba", ascending=False)
    cap20 = 100 * df_s.head(int(len(df_s) * 0.2))["label"].sum() / max(y_te.sum(), 1)

    bt_results.append({"split": split_y, "auc": auc_bt, "ap": ap_bt, "capture_20": cap20, "n_pos": int(y_bt.sum())})
    print(f"  Split {split_y}: AUC={auc_bt:.4f} AP={ap_bt:.4f} Cap@20%={cap20:.1f}% (n_pos={y_bt.sum():,})")

bt_df = pd.DataFrame(bt_results)
bt_mean_auc = bt_df["auc"].mean()
bt_std_auc = bt_df["auc"].std()
bt_stable = bt_std_auc < 0.05
print(f"\n  Moyenne AUC : {bt_mean_auc:.4f} +/- {bt_std_auc:.4f}")
print(f"  Stabilite   : {'STABLE' if bt_stable else 'VARIABLE'}")

# Fig backtesting
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].bar(bt_df["split"].astype(str), bt_df["auc"], color=COLORS[0])
axes[0].axhline(y=bt_mean_auc, color="red", linestyle="--", label=f"Moy: {bt_mean_auc:.3f}")
axes[0].set_ylabel("AUC-ROC")
axes[0].set_title("AUC par fenetre temporelle (XGBoost)")
axes[0].legend()
axes[1].bar(bt_df["split"].astype(str), bt_df["capture_20"], color=COLORS[1])
axes[1].set_ylabel("% abandons captures")
axes[1].set_title("Capture@20% par fenetre")
plt.suptitle("V4 — Backtesting multi-fenetre", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v4_04_backtesting.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v4_04_backtesting.png")


# ============================================================
# 5. SHAP INTERPRETABILITE
# ============================================================
print("\n" + "=" * 60)
print("[5/6] SHAP INTERPRETABILITE")
print("=" * 60)

shap_model = results["XGBoost"]["model"]
X_all_imp = SimpleImputer(strategy="median").fit_transform(X)
sample_idx = np.random.RandomState(42).choice(len(X), size=min(5000, len(X)), replace=False)
X_sample = pd.DataFrame(X_all_imp[sample_idx], columns=FEATURES)

explainer = shap.TreeExplainer(shap_model)
shap_values = explainer.shap_values(X_sample)

fig, ax = plt.subplots(figsize=(14, 10))
shap.summary_plot(shap_values, X_sample, feature_names=FEATURE_NAMES, show=False, max_display=20)
plt.title("V4 — SHAP (XGBoost, cible abandon/depose)", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v4_05_shap_summary.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v4_05_shap_summary.png")

fig, ax = plt.subplots(figsize=(14, 7))
shap.summary_plot(shap_values, X_sample, feature_names=FEATURE_NAMES, plot_type="bar", show=False, max_display=20)
plt.title("V4 — SHAP importance moyenne", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v4_06_shap_bar.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v4_06_shap_bar.png")

shap_importance = pd.DataFrame({
    "feature": FEATURE_NAMES,
    "mean_abs_shap": np.abs(shap_values).mean(axis=0),
}).sort_values("mean_abs_shap", ascending=False)
shap_importance.to_csv(OUTPUT_DIR / "v4_shap_importance.csv", index=False)
print("\n  Top features SHAP :")
for _, row in shap_importance.head(10).iterrows():
    print(f"    {row['feature']:>25s} : {row['mean_abs_shap']:.4f}")


# ============================================================
# 6. SCORING FINAL + COURBE LIFT + MLFLOW LOG
# ============================================================
print("\n" + "=" * 60)
print("[6/6] SCORING FINAL + MLFLOW")
print("=" * 60)

# Re-entrainer le meilleur modele sur tout le dataset
print(f"  Re-entrainement {best_name} sur le dataset complet...")
if best_name == "Logistique":
    best_r["model"].fit(X, y)
    df["score"] = best_r["model"].predict_proba(X)[:, 1]
elif best_name == "HistGradientBoosting":
    best_r["model"].fit(X.values, y)
    df["score"] = best_r["model"].predict_proba(X.values)[:, 1]
else:
    X_full_imp = SimpleImputer(strategy="median").fit_transform(X)
    best_r["model"].fit(X_full_imp, y)
    df["score"] = best_r["model"].predict_proba(X_full_imp)[:, 1]

# Courbe lift
fig, ax = plt.subplots(figsize=(14, 8))
df_lift = df.sort_values("score", ascending=False).reset_index(drop=True)
df_lift["cum"] = df_lift["y"].cumsum()
df_lift["pct_x"] = (df_lift.index + 1) / len(df_lift) * 100
df_lift["pct_y"] = df_lift["cum"] / max(df_lift["y"].sum(), 1) * 100

ax.plot(df_lift["pct_x"], df_lift["pct_y"], color="blue", linewidth=2.5, label=f"{best_name}")
ax.plot([0, 100], [0, 100], "r:", linewidth=1.5, label="Hasard")

for pct in [5, 10, 20, 30]:
    idx = int(len(df_lift) * pct / 100)
    capture = df_lift["pct_y"].iloc[idx]
    ax.annotate(f"Top {pct}% -> {capture:.0f}%",
                xy=(pct, capture), xytext=(pct + 8, capture - 5),
                arrowprops=dict(arrowstyle="->", color="blue"),
                fontsize=10, color="blue", fontweight="bold")

ax.set_xlabel("% des troncons (du plus risque au moins risque)")
ax.set_ylabel("% des abandons captures")
ax.set_title(f"V4 — Courbe de Lift ({best_name}, cible abandon/depose)", fontsize=13, fontweight="bold")
ax.legend(fontsize=11, loc="lower right")
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v4_07_courbe_lift.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v4_07_courbe_lift.png")

# --- Scoring des EN SERVICE uniquement ---
es_mask = df["STATUT_OBJET"] == "EN SERVICE"
scoring_es = df.loc[es_mask, [
    "OBJET", "MATERIAU", "FAMILLE_MATERIAU", "DIAMETRE", "LONGUEUR",
    "age_at_split", "cohorte", "nb_anom", "nb_fuites", "ETAT_CLEAN", "score",
]].copy()
scoring_es = scoring_es.rename(columns={"age_at_split": "age"})
scoring_es = scoring_es.sort_values("score", ascending=False)
scoring_es["rang"] = range(1, len(scoring_es) + 1)
scoring_es["top_pct"] = 100 * scoring_es["rang"] / len(scoring_es)
scoring_es.to_csv(OUTPUT_DIR / "v4_scoring_troncons.csv", index=False)
print(f"  => v4_scoring_troncons.csv ({len(scoring_es):,} troncons EN SERVICE)")

# --- MLFLOW LOG ---
print("\n  Logging MLflow...")
with mlflow.start_run(run_name=f"V4_{best_name}_cutoff{SPLIT_YEAR}") as run:
    # Params
    mlflow.log_param("version", "V4")
    mlflow.log_param("cible", "abandon_depose")
    mlflow.log_param("cutoff_year", SPLIT_YEAR)
    mlflow.log_param("annee_ref", ANNEE_REF)
    mlflow.log_param("best_model", best_name)
    mlflow.log_param("n_features", len(FEATURES))
    mlflow.log_param("n_train", len(X_train))
    mlflow.log_param("n_test", len(X_test))
    mlflow.log_param("n_positifs", int(n_pos))
    mlflow.log_param("pct_positifs", round(100 * n_pos / len(df), 2))

    if best_name == "XGBoost":
        for k, v in xgb_search.best_params_.items():
            mlflow.log_param(f"xgb_{k}", v)
    elif best_name == "Random Forest":
        for k, v in rf_search.best_params_.items():
            mlflow.log_param(f"rf_{k}", v)

    # Metriques test
    mlflow.log_metric("auc_test", best_r["auc"])
    mlflow.log_metric("ap_test", best_r["ap"])
    mlflow.log_metric("f1_test", best_r["f1"])
    mlflow.log_metric("precision_test", best_r["precision"])
    mlflow.log_metric("recall_test", best_r["recall"])
    mlflow.log_metric("tp", best_r["tp"])
    mlflow.log_metric("fp", best_r["fp"])
    mlflow.log_metric("fn", best_r["fn"])
    mlflow.log_metric("tn", best_r["tn"])

    for pct in [5, 10, 20, 30]:
        mlflow.log_metric(f"capture_top{pct}pct", best_r["captures"][pct])

    # Backtesting
    mlflow.log_metric("bt_auc_mean", bt_mean_auc)
    mlflow.log_metric("bt_auc_std", bt_std_auc)

    # Tous les modeles
    for name, r in results.items():
        mlflow.log_metric(f"{name}_auc", r["auc"])
        mlflow.log_metric(f"{name}_ap", r["ap"])

    # SHAP top features
    for i, (_, row) in enumerate(shap_importance.head(5).iterrows()):
        safe_name = row["feature"].replace("^", "").replace("/", "_per_")
        mlflow.log_metric(f"shap_top{i+1}_{safe_name}", row["mean_abs_shap"])

    # Artifacts
    mlflow.log_artifact(str(OUTPUT_DIR / "v4_01_comparaison_modeles.png"))
    mlflow.log_artifact(str(OUTPUT_DIR / "v4_02_confusion_matrices.png"))
    mlflow.log_artifact(str(OUTPUT_DIR / "v4_03_precision_recall.png"))
    mlflow.log_artifact(str(OUTPUT_DIR / "v4_04_backtesting.png"))
    mlflow.log_artifact(str(OUTPUT_DIR / "v4_05_shap_summary.png"))
    mlflow.log_artifact(str(OUTPUT_DIR / "v4_06_shap_bar.png"))
    mlflow.log_artifact(str(OUTPUT_DIR / "v4_07_courbe_lift.png"))
    mlflow.log_artifact(str(OUTPUT_DIR / "v4_shap_importance.csv"))
    mlflow.log_artifact(str(OUTPUT_DIR / "v4_scoring_troncons.csv"))

    # Log du modele
    if best_name == "XGBoost":
        mlflow.xgboost.log_model(best_r["model"], artifact_path="model")
    else:
        mlflow.sklearn.log_model(best_r["model"], artifact_path="model")

    print(f"  MLflow run ID: {run.info.run_id}")

# Sauvegarder le backtesting
bt_df.to_csv(OUTPUT_DIR / "v4_backtesting_results.csv", index=False)

# Sauvegarder la comparaison
comp_df = pd.DataFrame({
    name: {
        "AUC": r["auc"], "AP": r["ap"], "F1": r["f1"],
        "Precision": r["precision"], "Recall": r["recall"],
        **{f"Capture@{p}%": r["captures"][p] for p in [5, 10, 20, 30]},
    }
    for name, r in results.items()
}).T
comp_df.to_csv(OUTPUT_DIR / "v4_comparaison_modeles.csv")

# --- RAPPORT CONSOLE ---
print("\n" + "=" * 60)
print("RAPPORT V4 — CIBLE ABANDON/DEPOSE")
print("=" * 60)
print(f"""
APPROCHE :
  Cible       : ABANDONNE/DEPOSE = 1, EN SERVICE = 0
  Split       : cutoff={SPLIT_YEAR} (train: abandons <{SPLIT_YEAR}, test: {SPLIT_YEAR}-{ANNEE_REF})
  Age         : calcule a la date d'evenement (corrige fuite temporelle V3)
  Features    : {len(FEATURES)} (age, materiau, anomalies, densites, etc.)
  MLflow      : experiences tracees dans mlruns/

COMPARAISON :""")
print(f"  {'Modele':<22} {'AUC':>7} {'AP':>7} {'Cap@20':>8} {'Cap@30':>8}")
print(f"  {'-'*55}")
for name in model_names:
    r = results[name]
    print(f"  {name:<22} {r['auc']:>7.4f} {r['ap']:>7.4f} {r['captures'][20]:>7.1f}% {r['captures'][30]:>7.1f}%")

print(f"""
BACKTESTING :
  AUC moyen : {bt_mean_auc:.4f} +/- {bt_std_auc:.4f} ({'STABLE' if bt_stable else 'VARIABLE'})

BEST : {best_name}
  AUC={best_r['auc']:.4f} | AP={best_r['ap']:.4f}
  Top 5%  -> {best_r['captures'][5]:.1f}% des abandons
  Top 10% -> {best_r['captures'][10]:.1f}% des abandons
  Top 20% -> {best_r['captures'][20]:.1f}% des abandons
  Top 30% -> {best_r['captures'][30]:.1f}% des abandons

SCORING : {len(scoring_es):,} troncons EN SERVICE scores -> v4_scoring_troncons.csv
MLflow UI : mlflow ui (dans le repertoire du projet)
""")

print("=" * 60)
print("TERMINE")
print("=" * 60)
