"""
Script rapide : log les résultats V5 dans MLflow à partir des CSV/images déjà produits.
(Pas besoin de relancer tout le pipeline)
"""
import re
import pandas as pd
import numpy as np
from pathlib import Path
import mlflow
import mlflow.xgboost

OUTPUT_DIR = Path("output")
SPLIT_YEAR = 2018
TOP_PCT = 0.30
W_CLASSIF = 0.6
W_SURVIE = 0.4

# --- Charger les résultats ---
shap_imp = pd.read_csv(OUTPUT_DIR / "v5_shap_importance.csv")
abl_df = pd.read_csv(OUTPUT_DIR / "v5_ablation_features.csv")
scoring = pd.read_csv(OUTPUT_DIR / "v5_scoring_troncons.csv")

# Métriques extraites de la sortie console V5
auc = 0.8485
ap = 0.3092
f1 = 0.3605
prec = 0.2942
rec = 0.4653
tp, fp, fn, tn = 1383, 3318, 1589, 42201
captures = {5: 30.5, 10: 47.3, 20: 68.5, 30: 80.7}
auc_classif_full = 0.8962
auc_cascade_full = 0.8938

n_test = tp + fp + fn + tn
n_pos = 11887
n_total = 193962

xgb_params = {
    "n_estimators": 500,
    "max_depth": 8,
    "learning_rate": 0.03,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "scale_pos_weight": round((n_total - n_pos) / n_pos, 1),
    "eval_metric": "auc",
}

# KM résultats
km_results = {
    "Fonte": {"median": 68},
    "Fonte_grise": {"median": 113},
    "Plastique": {"median": 73},
    "Acier": {"median": 68},
    "Beton": {"median": 66},
    "Amiante_ciment": {"median": float("inf")},
}

def safe_metric_name(name):
    return re.sub(r"[^a-zA-Z0-9_\-. /]", "", name.replace("/", "_per_"))

# --- MLflow ---
mlflow.set_tracking_uri("file:///C:/Users/ahmedv_m/Desktop/mohamed_casses/mlruns")
mlflow.set_experiment("casses_canalisations_v5")

print("Logging V5 dans MLflow...")
with mlflow.start_run(run_name=f"V5_XGBoost_cutoff{SPLIT_YEAR}") as run:
    # Params
    mlflow.log_param("version", "V5")
    mlflow.log_param("cible", "abandon_depose")
    mlflow.log_param("cutoff_year", SPLIT_YEAR)
    mlflow.log_param("n_features", 20)
    mlflow.log_param("n_test", n_test)
    mlflow.log_param("n_positifs", n_pos)
    mlflow.log_param("pct_positifs", round(100 * n_pos / n_total, 2))
    mlflow.log_param("top_pct_survie", TOP_PCT)
    mlflow.log_param("w_classif", W_CLASSIF)
    mlflow.log_param("w_survie", W_SURVIE)
    for k, v in xgb_params.items():
        mlflow.log_param(f"xgb_{k}", v)

    # Métriques
    mlflow.log_metric("auc_test", auc)
    mlflow.log_metric("ap_test", ap)
    mlflow.log_metric("f1_test", f1)
    mlflow.log_metric("precision_test", prec)
    mlflow.log_metric("recall_test", rec)
    mlflow.log_metric("tp", tp)
    mlflow.log_metric("fp", fp)
    mlflow.log_metric("fn", fn)
    mlflow.log_metric("tn", tn)
    mlflow.log_metric("auc_classif_full", auc_classif_full)
    mlflow.log_metric("auc_cascade_full", auc_cascade_full)
    for pct in [5, 10, 20, 30]:
        mlflow.log_metric(f"capture_top{pct}pct", captures[pct])

    # SHAP
    for i, (_, row) in enumerate(shap_imp.head(5).iterrows()):
        sn = safe_metric_name(row["feature"])
        mlflow.log_metric(f"shap_top{i+1}_{sn}", row["mean_abs_shap"])

    # Ablation
    for _, row in abl_df.iterrows():
        sn = safe_metric_name(row["feature"])
        mlflow.log_metric(f"ablation_{sn}", row["delta_auc"])

    # KM
    for fam, info in km_results.items():
        med = info["median"]
        if np.isinf(med):
            med = 999  # MLflow ne gère pas inf
        mlflow.log_metric(f"km_median_{fam}", med)

    # Artifacts (images + CSV)
    for f in OUTPUT_DIR.glob("v5_*.png"):
        mlflow.log_artifact(str(f))
    for f in OUTPUT_DIR.glob("v5_*.csv"):
        mlflow.log_artifact(str(f))

    print(f"  Run ID: {run.info.run_id}")
    print(f"  => http://localhost:5000 pour voir les résultats")

print("DONE")
