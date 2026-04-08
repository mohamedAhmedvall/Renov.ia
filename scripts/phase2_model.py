"""
Phase 2 - Modelisation predictive (V3 - approche rigoureuse)
Projet : Prediction de casses de canalisations d'eau

Annee de reference : 2024 (via data_cleaning.ANNEE_REF)

Pipeline :
  1. FEATURE ENGINEERING avance
  2. CLASSIFICATION multi-modeles avec tuning + SMOTE
  3. BACKTESTING multi-fenetre temporelle
  4. CASCADE : classification (recall max) -> top N% -> survie pour re-ordonner
  5. SHAP interpretabilite
  6. Rapport complet avec confusion matrices

Features : pression et vitesse ecartees (demande referent metier)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_recall_curve,
    confusion_matrix, f1_score, precision_score, recall_score
)
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
import xgboost as xgb
from lifelines import KaplanMeierFitter, CoxPHFitter
import shap
import warnings
warnings.filterwarnings('ignore')

from data_cleaning import load_and_clean, ANNEE_REF

# --- Config ---
import os
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(exist_ok=True)

sns.set_theme(style="whitegrid", font_scale=1.1)
COLORS = sns.color_palette("Set2", 10)

print("=" * 60)
print(f"PHASE 2 V3 - MODELISATION (ref={ANNEE_REF})")
print("CLASSIFICATION + TUNING + BACKTESTING + CASCADE SURVIE")
print("=" * 60)


# ============================================================
# 1. CHARGEMENT & FEATURE ENGINEERING
# ============================================================
print("\n[1/7] Chargement et feature engineering...")

cana_es, anom_actives = load_and_clean(DATA_DIR)
print(f"  Troncons EN SERVICE : {len(cana_es):,}")
print(f"  Anomalies retenues  : {len(anom_actives):,}")


def build_features(cana_es, anom_actives, split_year):
    """Construit features + label pour un split temporel donne.
    Features basees sur anomalies < split_year.
    Label = a casse entre split_year et ANNEE_REF.
    """
    anom_train = anom_actives[anom_actives["annee_Anomalie"] < split_year]
    anom_test = anom_actives[
        (anom_actives["annee_Anomalie"] >= split_year) &
        (anom_actives["annee_Anomalie"] <= ANNEE_REF)
    ]

    # Features d'anomalies par troncon (periode train uniquement)
    anom_feat = anom_train.groupby("GID_OBJET").agg(
        nb_anom=("TYPE_ANOMALIE", "count"),
        nb_fuites=("TYPE_ANOMALIE", lambda x: x.isin(
            ["FUITE_SIGNAL_TR", "FUITE_DETECT_TR", "FUITE"]).sum()),
        premiere_anom=("annee_Anomalie", "min"),
        derniere_anom=("annee_Anomalie", "max"),
    ).reset_index()
    anom_feat["temps_depuis_derniere"] = split_year - anom_feat["derniere_anom"]

    # Intervalle moyen (acceleration)
    def calc_interval(group):
        dates = sorted(group["annee_Anomalie"].dropna().unique())
        if len(dates) < 2:
            return np.nan
        return np.mean([dates[i+1] - dates[i] for i in range(len(dates)-1)])

    intervals = anom_train.groupby("GID_OBJET").apply(
        calc_interval, include_groups=False).reset_index()
    intervals.columns = ["GID_OBJET", "intervalle_moyen"]
    anom_feat = anom_feat.merge(intervals, on="GID_OBJET", how="left")

    # Troncons casses dans la periode test
    troncons_casse = set(anom_test["GID_OBJET"].unique())

    # Dataset
    df = cana_es[["OBJET", "MATERIAU", "FAMILLE_MATERIAU", "DIAMETRE", "LONGUEUR",
                  "ETAT_CLEAN", "ETAT_ORD", "age", "date_fiable", "annee_pose",
                  "decennie_pose", "cohorte"]].copy()

    df = df.merge(anom_feat, left_on="OBJET", right_on="GID_OBJET", how="left")

    for col in ["nb_anom", "nb_fuites"]:
        df[col] = df[col].fillna(0).astype(int)
    df["temps_depuis_derniere"] = df["temps_depuis_derniere"].fillna(99)
    df["intervalle_moyen"] = df["intervalle_moyen"].fillna(99)

    # Encodages
    le_mat = LabelEncoder()
    df["MATERIAU_ENC"] = le_mat.fit_transform(df["MATERIAU"].fillna("INCONNU"))
    le_fam = LabelEncoder()
    df["FAMILLE_ENC"] = le_fam.fit_transform(df["FAMILLE_MATERIAU"])

    # --- FEATURE ENGINEERING AVANCE ---
    # Age non-lineaire
    df["age2"] = df["age"] ** 2
    df["log_age"] = np.log1p(df["age"].clip(lower=0))

    # Interactions materiau x age
    df["age_x_materiau"] = df["age"].fillna(0) * df["MATERIAU_ENC"]

    # Densites
    df["densite_anom_ml"] = np.where(
        df["LONGUEUR"] > 0, df["nb_anom"] / df["LONGUEUR"], 0)
    df["densite_fuites_ml"] = np.where(
        df["LONGUEUR"] > 0, df["nb_fuites"] / df["LONGUEUR"], 0)

    # Anomalies par annee d'age (taux d'usure)
    df["anom_par_an_age"] = np.where(
        df["age"] > 0, df["nb_anom"] / df["age"], 0)

    # A deja casse (binaire)
    df["a_deja_casse"] = (df["nb_anom"] > 0).astype(int)

    # Acceleration : intervalle qui diminue = acceleration
    df["acceleration"] = np.where(
        df["intervalle_moyen"] < 5, 1,  # interval < 5 ans = acceleration
        np.where(df["intervalle_moyen"] < 10, 0.5, 0))

    df["date_fiable_int"] = df["date_fiable"].astype(int)

    # Label
    df["label"] = df["OBJET"].isin(troncons_casse).astype(int)

    return df, le_mat


# Build principal (split 2020)
SPLIT_YEAR = 2020
df, le_mat = build_features(cana_es, anom_actives, SPLIT_YEAR)

n_pos = df["label"].sum()
n_neg = len(df) - n_pos
print(f"  Split principal : train < {SPLIT_YEAR}, test >= {SPLIT_YEAR}")
print(f"  Label : {n_pos:,} positifs ({100*n_pos/len(df):.2f}%) | {n_neg:,} negatifs")

FEATURES = [
    "age", "age2", "log_age",
    "DIAMETRE", "LONGUEUR",
    "MATERIAU_ENC", "FAMILLE_ENC", "ETAT_ORD",
    "date_fiable_int", "decennie_pose",
    "nb_anom", "nb_fuites", "a_deja_casse",
    "temps_depuis_derniere", "intervalle_moyen", "acceleration",
    "densite_anom_ml", "densite_fuites_ml", "anom_par_an_age",
    "age_x_materiau",
]
FEATURE_NAMES = [
    "Age", "Age^2", "Log(Age)",
    "Diametre", "Longueur",
    "Materiau", "Famille_mat", "Etat",
    "Date_fiable", "Decennie_pose",
    "Nb_anom_hist", "Nb_fuites_hist", "A_deja_casse",
    "Temps_depuis_dern", "Intervalle_moyen", "Acceleration",
    "Densite_anom/ml", "Densite_fuites/ml", "Anom_par_an_age",
    "Age_x_materiau",
]

X = df[FEATURES].copy()
y = df["label"].copy()
print(f"  Features : {len(FEATURES)} (sans pression ni vitesse)")


# ============================================================
# 2. CLASSIFICATION -- MULTI-MODELES AVEC TUNING
# ============================================================
print("\n" + "=" * 60)
print("ETAPE 1 : CLASSIFICATION -- 4 MODELES AVEC TUNING")
print("=" * 60)

from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y)

print(f"\n  Train : {len(X_train):,} ({y_train.sum():,} pos)")
print(f"  Test  : {len(X_test):,} ({y_test.sum():,} pos)")

scale_pos = n_neg / n_pos

# --- SMOTE sur le train ---
try:
    from imblearn.over_sampling import SMOTE
    smote = SMOTE(random_state=42, sampling_strategy=0.1)  # 10% ratio
    X_train_res, y_train_res = smote.fit_resample(
        SimpleImputer(strategy="median").fit_transform(X_train), y_train)
    print(f"  SMOTE applique : {y_train_res.sum():,} pos / {len(y_train_res):,} total")
    USE_SMOTE = True
except ImportError:
    print("  imblearn non disponible, on continue sans SMOTE")
    X_train_res, y_train_res = X_train.values, y_train.values
    USE_SMOTE = False

# Imputer pour les modeles qui ne gerent pas les NaN
imputer = SimpleImputer(strategy="median")
X_train_imp = imputer.fit_transform(X_train)
X_test_imp = imputer.transform(X_test)

# --- Modeles avec tuning ---
models_configs = {
    "Logistique": {
        "model": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42))
        ]),
        "use_smote": False,  # pipeline interne
    },
    "Random Forest": {
        "model": None,  # sera cree apres tuning
        "use_smote": USE_SMOTE,
    },
    "XGBoost": {
        "model": None,
        "use_smote": False,  # scale_pos_weight suffit
    },
    "HistGradientBoosting": {
        "model": None,
        "use_smote": USE_SMOTE,
    },
}

# --- Tuning Random Forest ---
print("\n  Tuning Random Forest...")
rf_params = {
    "n_estimators": [100, 200, 300, 500],
    "max_depth": [6, 8, 10, 12, None],
    "min_samples_leaf": [5, 10, 20, 50],
    "max_features": ["sqrt", "log2", 0.3],
}
rf_base = RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1)
rf_search = RandomizedSearchCV(
    rf_base, rf_params, n_iter=20, scoring="average_precision",
    cv=StratifiedKFold(3, shuffle=True, random_state=42),
    random_state=42, n_jobs=-1, verbose=0)

if USE_SMOTE:
    rf_search.fit(X_train_res, y_train_res)
else:
    rf_search.fit(X_train_imp, y_train)

print(f"    Best params : {rf_search.best_params_}")
print(f"    Best AP (CV) : {rf_search.best_score_:.4f}")
models_configs["Random Forest"]["model"] = rf_search.best_estimator_

# --- Tuning XGBoost ---
print("\n  Tuning XGBoost...")
xgb_params = {
    "n_estimators": [200, 300, 500, 700],
    "max_depth": [4, 6, 8, 10],
    "learning_rate": [0.01, 0.03, 0.05, 0.1],
    "subsample": [0.7, 0.8, 0.9],
    "colsample_bytree": [0.6, 0.7, 0.8],
    "min_child_weight": [1, 3, 5, 10],
    "gamma": [0, 0.1, 0.3],
}
xgb_base = xgb.XGBClassifier(
    scale_pos_weight=scale_pos, eval_metric="aucpr",
    random_state=42, tree_method="hist", enable_categorical=False)
xgb_search = RandomizedSearchCV(
    xgb_base, xgb_params, n_iter=30, scoring="average_precision",
    cv=StratifiedKFold(3, shuffle=True, random_state=42),
    random_state=42, n_jobs=-1, verbose=0)
xgb_search.fit(X_train_imp, y_train)
print(f"    Best params : {xgb_search.best_params_}")
print(f"    Best AP (CV) : {xgb_search.best_score_:.4f}")
models_configs["XGBoost"]["model"] = xgb_search.best_estimator_

# --- HistGradientBoosting (gere NaN nativement) ---
print("\n  Tuning HistGradientBoosting...")
hgb_params = {
    "max_iter": [200, 300, 500],
    "max_depth": [4, 6, 8, 10, None],
    "learning_rate": [0.01, 0.03, 0.05, 0.1],
    "min_samples_leaf": [10, 20, 50],
    "l2_regularization": [0, 0.1, 1.0],
}
hgb_base = HistGradientBoostingClassifier(
    class_weight="balanced", random_state=42, early_stopping=False)
hgb_search = RandomizedSearchCV(
    hgb_base, hgb_params, n_iter=20, scoring="average_precision",
    cv=StratifiedKFold(3, shuffle=True, random_state=42),
    random_state=42, n_jobs=-1, verbose=0)

if USE_SMOTE:
    hgb_search.fit(X_train_res, y_train_res)
else:
    hgb_search.fit(X_train.values, y_train)

print(f"    Best params : {hgb_search.best_params_}")
print(f"    Best AP (CV) : {hgb_search.best_score_:.4f}")
models_configs["HistGradientBoosting"]["model"] = hgb_search.best_estimator_


# ============================================================
# 3. EVALUATION DES MODELES
# ============================================================
print("\n" + "=" * 60)
print("EVALUATION DES 4 MODELES SUR LE JEU DE TEST")
print("=" * 60)

results = {}

for name, cfg in models_configs.items():
    model = cfg["model"]
    print(f"\n  --- {name} ---")

    # Prediction
    if name == "Logistique":
        model.fit(X_train, y_train)
        y_proba = model.predict_proba(X_test)[:, 1]
    elif name == "HistGradientBoosting":
        if USE_SMOTE:
            y_proba = model.predict_proba(X_test.values)[:, 1]
        else:
            y_proba = model.predict_proba(X_test.values)[:, 1]
    elif name == "XGBoost":
        y_proba = model.predict_proba(X_test_imp)[:, 1]
    else:  # RF
        if USE_SMOTE:
            y_proba = model.predict_proba(X_test_imp)[:, 1]
        else:
            y_proba = model.predict_proba(X_test_imp)[:, 1]

    # Seuil optimal par F1
    precisions, recalls, thresholds = precision_recall_curve(y_test, y_proba)
    f1s = 2 * precisions * recalls / (precisions + recalls + 1e-8)
    best_idx = np.argmax(f1s)
    best_threshold = thresholds[min(best_idx, len(thresholds)-1)]
    y_pred = (y_proba >= best_threshold).astype(int)

    auc = roc_auc_score(y_test, y_proba)
    ap = average_precision_score(y_test, y_proba)
    f1 = f1_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    # Lift
    df_tmp = pd.DataFrame({"proba": y_proba, "label": y_test.values})
    df_sorted = df_tmp.sort_values("proba", ascending=False)
    lift_20, capture_5, capture_10, capture_20 = 0, 0, 0, 0
    for pct in [5, 10, 20]:
        top = df_sorted.head(int(len(df_sorted) * pct / 100))
        capture = 100 * top["label"].sum() / max(y_test.sum(), 1)
        lift = top["label"].mean() / max(y_test.mean(), 1e-8)
        if pct == 5: capture_5 = capture
        if pct == 10: capture_10 = capture
        if pct == 20:
            lift_20 = lift
            capture_20 = capture

    print(f"  AUC-ROC    : {auc:.4f}")
    print(f"  Avg Prec   : {ap:.4f}")
    print(f"  F1         : {f1:.4f} (seuil={best_threshold:.3f})")
    print(f"  Precision  : {prec:.4f}")
    print(f"  Recall     : {rec:.4f}")
    print(f"")
    print(f"  Matrice de confusion :")
    print(f"               Predit -    Predit +")
    print(f"    Reel -   {tn:>8,}    {fp:>8,}  (FP)")
    print(f"    Reel +   {fn:>8,}    {tp:>8,}  (TP)")
    print(f"")
    print(f"  Lift@5%  : capture {capture_5:.1f}%")
    print(f"  Lift@10% : capture {capture_10:.1f}%")
    print(f"  Lift@20% : capture {capture_20:.1f}% ({lift_20:.2f}x)")

    results[name] = {
        "model": model, "auc": auc, "ap": ap, "f1": f1,
        "precision": prec, "recall": rec, "threshold": best_threshold,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "lift_20": lift_20, "capture_5": capture_5,
        "capture_10": capture_10, "capture_20": capture_20,
        "y_proba": y_proba, "y_pred": y_pred,
    }

# --- FIGURES ---

# Figure 1 : Comparaison AUC + AP
fig, axes = plt.subplots(1, 3, figsize=(22, 6))
model_names = list(results.keys())
aucs = [results[n]["auc"] for n in model_names]
aps = [results[n]["ap"] for n in model_names]

bars1 = axes[0].bar(model_names, aucs, color=COLORS[:4])
axes[0].set_ylabel("AUC-ROC")
axes[0].set_title("AUC-ROC")
axes[0].set_ylim(0.5, 1.0)
for i, v in enumerate(aucs):
    axes[0].text(i, v + 0.01, f"{v:.3f}", ha="center", fontweight="bold")
axes[0].tick_params(axis='x', rotation=15)

bars2 = axes[1].bar(model_names, aps, color=COLORS[:4])
axes[1].set_ylabel("Average Precision")
axes[1].set_title("Average Precision")
for i, v in enumerate(aps):
    axes[1].text(i, v + 0.003, f"{v:.3f}", ha="center", fontweight="bold")
axes[1].tick_params(axis='x', rotation=15)

# Capture@5,10,20
x_pos = np.arange(len(model_names))
w = 0.25
for j, pct in enumerate([5, 10, 20]):
    vals = [results[n][f"capture_{pct}"] for n in model_names]
    axes[2].bar(x_pos + (j-1)*w, vals, w, label=f"Top {pct}%", color=COLORS[j])
axes[2].set_xticks(x_pos)
axes[2].set_xticklabels(model_names, rotation=15)
axes[2].set_ylabel("% casses capturees")
axes[2].set_title("Capture des casses par modele")
axes[2].legend()

plt.suptitle(f"Comparaison des modeles (ref {ANNEE_REF}, split {SPLIT_YEAR})", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "09_comparaison_modeles.png", dpi=150, bbox_inches="tight")
plt.close()
print("\n  => Figure 09_comparaison_modeles.png")

# Figure 2 : Confusion matrices
fig, axes = plt.subplots(1, 4, figsize=(24, 5))
for i, name in enumerate(model_names):
    r = results[name]
    cm_arr = np.array([[r["tn"], r["fp"]], [r["fn"], r["tp"]]])
    sns.heatmap(cm_arr, annot=True, fmt=",d", cmap="Blues", ax=axes[i],
                xticklabels=["Predit -", "Predit +"],
                yticklabels=["Reel -", "Reel +"],
                annot_kws={"size": 12})
    axes[i].set_title(f"{name}\nPrec={r['precision']:.2f} Rec={r['recall']:.2f}\n"
                      f"FP={r['fp']:,} FN={r['fn']:,}", fontsize=10)
plt.suptitle("Matrices de confusion detaillees", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "10_confusion_matrices.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure 10_confusion_matrices.png")

# Figure 3 : Courbes Precision-Recall
fig, ax = plt.subplots(figsize=(10, 7))
for i, name in enumerate(model_names):
    prec_curve, rec_curve, _ = precision_recall_curve(y_test, results[name]["y_proba"])
    ax.plot(rec_curve, prec_curve, label=f"{name} (AP={results[name]['ap']:.3f})",
            linewidth=2, color=COLORS[i])
ax.axhline(y=y_test.mean(), color="red", linestyle=":", label=f"Hasard ({y_test.mean():.3f})")
ax.set_xlabel("Recall")
ax.set_ylabel("Precision")
ax.set_title("Courbes Precision-Recall")
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "11_precision_recall_curves.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure 11_precision_recall_curves.png")

# Tableau recap
print("\n  TABLEAU RECAPITULATIF :")
print(f"  {'Modele':<22} {'AUC':>7} {'AP':>7} {'F1':>7} {'Prec':>7} {'Rec':>7} {'FP':>7} {'FN':>7} {'Cap@5':>7} {'Cap@10':>7} {'Cap@20':>7}")
print(f"  {'-'*105}")
for name in model_names:
    r = results[name]
    print(f"  {name:<22} {r['auc']:>7.4f} {r['ap']:>7.4f} {r['f1']:>7.4f} "
          f"{r['precision']:>7.4f} {r['recall']:>7.4f} {r['fp']:>7,} {r['fn']:>7,} "
          f"{r['capture_5']:>6.1f}% {r['capture_10']:>6.1f}% {r['capture_20']:>6.1f}%")

best_model_name = max(results, key=lambda k: results[k]["ap"])
print(f"\n  >>> Meilleur modele (AP) : {best_model_name}")
best_r = results[best_model_name]
best_model = best_r["model"]


# ============================================================
# 4. BACKTESTING MULTI-FENETRE
# ============================================================
print("\n" + "=" * 60)
print("BACKTESTING -- VALIDATION TEMPORELLE MULTI-FENETRE")
print("=" * 60)

bt_results = []
for split_y in [2017, 2018, 2019, 2020, 2021]:
    df_bt, _ = build_features(cana_es, anom_actives, split_y)
    X_bt = df_bt[FEATURES].copy()
    y_bt = df_bt["label"].copy()

    if y_bt.sum() < 10:
        print(f"  Split {split_y} : pas assez de positifs ({y_bt.sum()}), skip")
        continue

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_bt, y_bt, test_size=0.3, random_state=42, stratify=y_bt)

    imp = SimpleImputer(strategy="median")
    X_tr_imp = imp.fit_transform(X_tr)
    X_te_imp = imp.transform(X_te)

    # Re-entrainer XGBoost avec les meilleurs hyperparametres
    xgb_bt = xgb.XGBClassifier(
        **xgb_search.best_params_,
        scale_pos_weight=(len(y_bt) - y_bt.sum()) / max(y_bt.sum(), 1),
        eval_metric="aucpr", random_state=42,
        tree_method="hist", enable_categorical=False)
    xgb_bt.fit(X_tr_imp, y_tr)
    y_proba_bt = xgb_bt.predict_proba(X_te_imp)[:, 1]

    auc_bt = roc_auc_score(y_te, y_proba_bt)
    ap_bt = average_precision_score(y_te, y_proba_bt)

    # Capture
    df_tmp = pd.DataFrame({"proba": y_proba_bt, "label": y_te.values})
    df_s = df_tmp.sort_values("proba", ascending=False)
    cap20 = 100 * df_s.head(int(len(df_s) * 0.2))["label"].sum() / max(y_te.sum(), 1)

    bt_results.append({
        "split": split_y, "auc": auc_bt, "ap": ap_bt,
        "capture_20": cap20, "n_pos": y_bt.sum(), "n_total": len(y_bt)
    })
    print(f"  Split {split_y} : AUC={auc_bt:.4f} AP={ap_bt:.4f} Cap@20%={cap20:.1f}% "
          f"(n_pos={y_bt.sum():,})")

bt_df = pd.DataFrame(bt_results)
print(f"\n  Moyenne AUC : {bt_df['auc'].mean():.4f} +/- {bt_df['auc'].std():.4f}")
print(f"  Moyenne AP  : {bt_df['ap'].mean():.4f} +/- {bt_df['ap'].std():.4f}")
print(f"  Stabilite   : {'STABLE' if bt_df['auc'].std() < 0.05 else 'VARIABLE'}")

# Figure backtesting
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].bar(bt_df["split"].astype(str), bt_df["auc"], color=COLORS[0])
axes[0].set_ylabel("AUC-ROC")
axes[0].set_title("AUC par fenetre temporelle")
axes[0].axhline(y=bt_df["auc"].mean(), color="red", linestyle="--",
                label=f"Moyenne: {bt_df['auc'].mean():.3f}")
axes[0].legend()

axes[1].bar(bt_df["split"].astype(str), bt_df["capture_20"], color=COLORS[1])
axes[1].set_ylabel("% casses capturees")
axes[1].set_title("Capture@20% par fenetre")
axes[1].axhline(y=bt_df["capture_20"].mean(), color="red", linestyle="--",
                label=f"Moyenne: {bt_df['capture_20'].mean():.0f}%")
axes[1].legend()

plt.suptitle("Backtesting multi-fenetre (XGBoost)", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "12_backtesting.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure 12_backtesting.png")


# ============================================================
# 5. CASCADE : CLASSIFICATION -> TOP -> SURVIE
# ============================================================
print("\n" + "=" * 60)
print("ETAPE 3 : CASCADE -- CLASSIFICATION -> TOP -> SURVIE")
print("=" * 60)

# Re-entrainer le meilleur modele sur tout le dataset
if best_model_name == "Logistique":
    best_model.fit(X, y)
    df["score_classif"] = best_model.predict_proba(X)[:, 1]
elif best_model_name == "HistGradientBoosting":
    best_model.fit(X.values, y)
    df["score_classif"] = best_model.predict_proba(X.values)[:, 1]
else:
    X_all_imp = SimpleImputer(strategy="median").fit_transform(X)
    best_model.fit(X_all_imp, y)
    df["score_classif"] = best_model.predict_proba(X_all_imp)[:, 1]

# TOP 30% les plus a risque selon la classification
top_pct = 30
n_top = int(len(df) * top_pct / 100)
df_ranked = df.sort_values("score_classif", ascending=False)
top_ids = set(df_ranked.head(n_top)["OBJET"])
print(f"  Classification -> Top {top_pct}% = {n_top:,} troncons")
print(f"  Casses dans le top : {df_ranked.head(n_top)['label'].sum():,} / {df['label'].sum():,} "
      f"({100*df_ranked.head(n_top)['label'].sum()/max(df['label'].sum(),1):.1f}%)")

# --- Survie sur le TOP uniquement ---
surv_top = df[df["OBJET"].isin(top_ids) & df["date_fiable"]].copy()
surv_top["event"] = (surv_top["nb_anom"] > 0).astype(int)
surv_top["duration"] = surv_top["age"].clip(lower=1)
surv_top = surv_top[surv_top["duration"].notna()].copy()

print(f"  Troncons pour survie (top + dates fiables) : {len(surv_top):,}")
print(f"  Evenements dans le top : {surv_top['event'].sum():,}")

# --- Kaplan-Meier sur le TOP par famille ---
fig, ax = plt.subplots(figsize=(14, 8))
kmf = KaplanMeierFitter()
survival_medians = {}

top_familles = surv_top["FAMILLE_MATERIAU"].value_counts().head(6).index.tolist()
for i, fam in enumerate(top_familles):
    mask = surv_top["FAMILLE_MATERIAU"] == fam
    if mask.sum() < 30:
        continue
    kmf.fit(surv_top.loc[mask, "duration"], event_observed=surv_top.loc[mask, "event"], label=fam)
    kmf.plot_survival_function(ax=ax, color=COLORS[i], linewidth=2)
    med = kmf.median_survival_time_
    survival_medians[fam] = med
    print(f"    {fam:>20s} : n={mask.sum():>5,} | events={surv_top.loc[mask,'event'].sum():>4,} | "
          f"survie mediane={med:.0f} ans")

ax.set_xlabel("Age (annees)")
ax.set_ylabel("P(survie)")
ax.set_title(f"Kaplan-Meier sur le TOP {top_pct}% (classification)\npar famille de materiau", fontsize=13, fontweight="bold")
ax.set_xlim(0, 120)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "13_kaplan_meier_top.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure 13_kaplan_meier_top.png")

# --- Kaplan-Meier par materiau ---
top_mats_surv = surv_top["MATERIAU"].value_counts().head(6).index.tolist()
fig, ax = plt.subplots(figsize=(14, 8))
for i, mat in enumerate(top_mats_surv):
    mask = surv_top["MATERIAU"] == mat
    if mask.sum() < 30:
        continue
    kmf.fit(surv_top.loc[mask, "duration"], event_observed=surv_top.loc[mask, "event"], label=mat)
    kmf.plot_survival_function(ax=ax, color=COLORS[i], linewidth=2)
    med = kmf.median_survival_time_
    print(f"    {mat:>8s} : survie mediane = {med:.0f} ans")

ax.set_xlabel("Age (annees)")
ax.set_ylabel("P(survie)")
ax.set_title(f"Kaplan-Meier sur le TOP {top_pct}% par materiau", fontsize=13, fontweight="bold")
ax.set_xlim(0, 120)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "14_kaplan_meier_top_materiau.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure 14_kaplan_meier_top_materiau.png")

# --- Cox sur le TOP pour re-ordonner ---
print("\n  Cox Proportional Hazards sur le TOP...")
cox_features = ["MATERIAU_ENC", "DIAMETRE", "LONGUEUR", "ETAT_ORD", "nb_anom"]
cox_df = surv_top[["duration", "event"] + cox_features].dropna()

if len(cox_df) > 100:
    cph = CoxPHFitter(penalizer=0.01)
    cph.fit(cox_df, duration_col="duration", event_col="event")

    print("\n  Hazard Ratios :")
    cox_summary = cph.summary[["coef", "exp(coef)", "p"]].copy()
    cox_summary.columns = ["Coefficient", "Hazard Ratio", "p-value"]
    for idx, row in cox_summary.iterrows():
        sig = "***" if row["p-value"] < 0.001 else "**" if row["p-value"] < 0.01 else "*" if row["p-value"] < 0.05 else "ns"
        print(f"    {idx:>15s} : HR={row['Hazard Ratio']:.4f} {sig}")

    # Hazard ratios figure
    fig, ax = plt.subplots(figsize=(10, 5))
    hr = cox_summary.sort_values("Hazard Ratio", ascending=True)
    colors_hr = ["#d32f2f" if v > 1 else "#388e3c" for v in hr["Hazard Ratio"]]
    ax.barh(hr.index, hr["Hazard Ratio"], color=colors_hr)
    ax.axvline(x=1.0, color="black", linestyle="--")
    ax.set_xlabel("Hazard Ratio (>1 = risque)")
    ax.set_title(f"Cox PH -- Hazard Ratios (TOP {top_pct}%)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "15_cox_hazard_ratios.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  => Figure 15_cox_hazard_ratios.png")

    # Score Cox pour re-ordonner le TOP
    cox_risk = cph.predict_partial_hazard(cox_df[cox_features])
    surv_top.loc[cox_risk.index, "cox_risk"] = cox_risk.values

    # Score cascade : classification (normalise) + survie (normalise)
    df["cox_risk"] = np.nan
    df.loc[cox_risk.index, "cox_risk"] = cox_risk.values

    # Normalisation
    sc_min, sc_max = df["score_classif"].min(), df["score_classif"].max()
    df["score_classif_norm"] = (df["score_classif"] - sc_min) / (sc_max - sc_min)

    cox_vals = df["cox_risk"].dropna()
    if len(cox_vals) > 0:
        cr_min, cr_max = cox_vals.min(), cox_vals.max()
        df["cox_risk_norm"] = (df["cox_risk"] - cr_min) / (cr_max - cr_min)
    else:
        df["cox_risk_norm"] = 0

    df["cox_risk_norm"] = df["cox_risk_norm"].fillna(0)

    # Score cascade : pour le TOP, combiner classif + cox. Pour le reste, classif seul.
    W_CLASSIF = 0.6
    W_SURVIE = 0.4
    df["score_cascade"] = df["score_classif_norm"]
    in_top = df["OBJET"].isin(top_ids)
    df.loc[in_top, "score_cascade"] = (
        W_CLASSIF * df.loc[in_top, "score_classif_norm"] +
        W_SURVIE * df.loc[in_top, "cox_risk_norm"]
    )

    # Evaluation
    auc_classif = roc_auc_score(y, df["score_classif"])
    auc_cascade = roc_auc_score(y, df["score_cascade"])
    print(f"\n  AUC Classification seule : {auc_classif:.4f}")
    print(f"  AUC Cascade (classif+survie) : {auc_cascade:.4f}")

    cox_summary.to_csv(OUTPUT_DIR / "cox_summary.csv")
else:
    print("  Pas assez de donnees pour Cox, on garde la classification seule")
    df["score_cascade"] = df["score_classif"]
    auc_classif = roc_auc_score(y, df["score_classif"])
    auc_cascade = auc_classif

# Lift comparaison finale
print(f"\n  Comparaison des scores :")
for score_name, score_col in [("Classification", "score_classif"),
                               ("Cascade", "score_cascade")]:
    df_s = df.sort_values(score_col, ascending=False)
    for pct in [5, 10, 20]:
        top = df_s.head(int(len(df) * pct / 100))
        capture = 100 * top["label"].sum() / max(y.sum(), 1)
        lift = top["label"].mean() / max(y.mean(), 1e-8)
        print(f"  {score_name:>15s} -- Top {pct}% : capture {capture:.1f}% (lift {lift:.2f}x)")


# ============================================================
# 6. SHAP
# ============================================================
print("\n" + "=" * 60)
print("SHAP -- INTERPRETABILITE")
print("=" * 60)

# Utiliser XGBoost pour SHAP
shap_model = results["XGBoost"]["model"]
X_all_imp = SimpleImputer(strategy="median").fit_transform(X)
sample_idx = np.random.RandomState(42).choice(len(X), size=min(5000, len(X)), replace=False)
X_sample = pd.DataFrame(X_all_imp[sample_idx], columns=FEATURES)

explainer = shap.TreeExplainer(shap_model)
shap_values = explainer.shap_values(X_sample)

fig, ax = plt.subplots(figsize=(14, 10))
shap.summary_plot(shap_values, X_sample, feature_names=FEATURE_NAMES,
                  show=False, max_display=20)
plt.title(f"SHAP -- Importance des features (XGBoost tune, ref {ANNEE_REF})", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "16_shap_global.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure 16_shap_global.png")

fig, ax = plt.subplots(figsize=(14, 7))
shap.summary_plot(shap_values, X_sample, feature_names=FEATURE_NAMES,
                  plot_type="bar", show=False, max_display=20)
plt.title(f"SHAP -- Importance moyenne (XGBoost tune)", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "17_shap_bar.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure 17_shap_bar.png")

shap_importance = pd.DataFrame({
    "feature": FEATURE_NAMES,
    "mean_abs_shap": np.abs(shap_values).mean(axis=0)
}).sort_values("mean_abs_shap", ascending=False)

print("\n  Top features SHAP :")
for _, row in shap_importance.iterrows():
    print(f"    {row['feature']:>25s} : {row['mean_abs_shap']:.4f}")

shap_importance.to_csv(OUTPUT_DIR / "shap_importance.csv", index=False)


# ============================================================
# 7. COURBE LIFT FINALE + ANALYSE FP + RAPPORT
# ============================================================
print("\n" + "=" * 60)
print("COURBE LIFT FINALE + ANALYSE DES FAUX POSITIFS")
print("=" * 60)

# Courbe lift
fig, ax = plt.subplots(figsize=(14, 8))
for score_name, score_col, color, ls in [
    ("Cascade (classif+survie)", "score_cascade", "blue", "-"),
    (f"Classification ({best_model_name})", "score_classif", "green", "--"),
]:
    df_s = df.sort_values(score_col, ascending=False).reset_index(drop=True)
    df_s["cum"] = df_s["label"].cumsum()
    df_s["pct_x"] = (df_s.index + 1) / len(df_s) * 100
    df_s["pct_y"] = df_s["cum"] / max(df_s["label"].sum(), 1) * 100
    ax.plot(df_s["pct_x"], df_s["pct_y"], color=color, linestyle=ls, linewidth=2.5, label=score_name)

ax.plot([0, 100], [0, 100], "r:", linewidth=1.5, label="Hasard")

df_h = df.sort_values("score_cascade", ascending=False).reset_index(drop=True)
df_h["cum"] = df_h["label"].cumsum()
for pct in [5, 10, 20, 30]:
    idx = int(len(df_h) * pct / 100)
    capture = 100 * df_h["cum"].iloc[idx] / max(df_h["label"].sum(), 1)
    ax.annotate(f"Top {pct}% -> {capture:.0f}%",
                xy=(pct, capture), xytext=(pct + 8, capture - 5),
                arrowprops=dict(arrowstyle="->", color="blue"),
                fontsize=10, color="blue", fontweight="bold")

ax.set_xlabel("% des troncons (du plus risque au moins risque)")
ax.set_ylabel("% des casses capturees")
ax.set_title(f"Courbe de Lift -- Score cascade (ref {ANNEE_REF})", fontsize=13, fontweight="bold")
ax.legend(fontsize=11, loc="lower right")
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "18_courbe_lift_finale.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => Figure 18_courbe_lift_finale.png")

# --- Analyse FP du meilleur modele ---
print(f"\n  Analyse des faux positifs ({best_model_name}) :")
df_eval = X_test.copy()
df_eval["y_true"] = y_test.values
df_eval["y_proba"] = best_r["y_proba"]
df_eval["y_pred"] = best_r["y_pred"]
df_eval["OBJET"] = df.loc[X_test.index, "OBJET"].values
df_eval["MATERIAU"] = df.loc[X_test.index, "MATERIAU"].values

fp_mask = (df_eval["y_pred"] == 1) & (df_eval["y_true"] == 0)
fp_df = df_eval[fp_mask]
print(f"  {len(fp_df):,} faux positifs")
print(f"  Materiaux :")
for mat, cnt in fp_df["MATERIAU"].value_counts().head(8).items():
    print(f"    {mat:>8s} : {cnt:>5,} ({100*cnt/len(fp_df):>5.1f}%)")
print(f"  Age moyen FP : {fp_df['age'].mean():.0f} ans (vs {df_eval['age'].mean():.0f} global)")
print(f"  => FP = troncons a risque pas encore casses, pas forcement des erreurs")

# Capture finale
print(f"\n  PERFORMANCES FINALES (score cascade) :")
for pct in [5, 10, 20, 30]:
    idx = int(len(df_h) * pct / 100)
    capture = 100 * df_h["cum"].iloc[idx] / max(df_h["label"].sum(), 1)
    print(f"  Top {pct}% -> capture {capture:.0f}% des casses")


# --- RAPPORT ---
print("\n" + "=" * 60)
print(f"RAPPORT DE CONFIANCE -- PHASE 2 V3 (ref {ANNEE_REF})")
print("=" * 60)

print(f"""
APPROCHE :
  1. Feature engineering : {len(FEATURES)} features (age, age2, log_age, interactions, densites, acceleration)
  2. 4 modeles compares avec tuning (RandomizedSearchCV)
  3. Backtesting multi-fenetre ({len(bt_df)} fenetres)
  4. CASCADE : classification (top {top_pct}%) -> survie (Cox) pour re-ordonner
  Pression et vitesse ECARTEES (referent metier)
  {'SMOTE applique sur le train' if USE_SMOTE else 'Sans SMOTE'}

COMPARAISON MODELES :""")

print(f"  {'Modele':<22} {'AUC':>7} {'AP':>7} {'Rec':>7} {'Cap@20':>8}")
for name in model_names:
    r = results[name]
    print(f"  {name:<22} {r['auc']:>7.4f} {r['ap']:>7.4f} {r['recall']:>7.4f} {r['capture_20']:>7.1f}%")

print(f"""
BACKTESTING :
  AUC moyen  : {bt_df['auc'].mean():.4f} +/- {bt_df['auc'].std():.4f}
  Stabilite  : {'STABLE' if bt_df['auc'].std() < 0.05 else 'VARIABLE'}

SCORE CASCADE :
  AUC Classification : {auc_classif:.4f}
  AUC Cascade        : {auc_cascade:.4f}

RECOMMANDATION : {"GO" if auc_cascade > 0.7 else "PRUDENT -- a ameliorer"}
""")

# Sauvegarder
df[["OBJET", "MATERIAU", "FAMILLE_MATERIAU", "DIAMETRE", "LONGUEUR", "age",
    "cohorte", "nb_anom", "ETAT_CLEAN", "score_classif", "score_cascade",
    "label", "decennie_pose"]].to_csv(OUTPUT_DIR / "scoring_troncons.csv", index=False)

comp_df = pd.DataFrame(results).T[["auc", "ap", "f1", "precision", "recall", "fp", "fn",
                                     "capture_5", "capture_10", "capture_20"]]
comp_df.to_csv(OUTPUT_DIR / "comparaison_modeles.csv")
bt_df.to_csv(OUTPUT_DIR / "backtesting_results.csv", index=False)

print(f"\n  Fichiers sauvegardes dans output/")
print("=" * 60)
