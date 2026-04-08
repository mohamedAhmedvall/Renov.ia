"""
Phase 2 V5 - Classification + Analyse erreurs + Ablation features + Cascade Survie
Projet : Prediction de renouvellement de canalisations d'eau

Pipeline :
  1. Classification rapide (XGBoost params fixes, pas de HPO lourd)
  2. Analyse des erreurs (FP, FN) : qui sont-ils ?
  3. Ablation de features : effet de chaque feature
  4. Cascade : ranking classification -> survie sur le top
  5. Scoring final des EN SERVICE
  6. MLflow logging complet

Cible : ABANDONNE/DEPOSE = 1 vs EN SERVICE = 0
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
    roc_auc_score, average_precision_score, precision_recall_curve,
    confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
import xgboost as xgb
from lifelines import KaplanMeierFitter, CoxPHFitter
import shap
import mlflow
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

SPLIT_YEAR = 2018
EXPERIMENT_NAME = "casses_canalisations_v5"

print("=" * 60)
print("PHASE 2 V5 — CLASSIFICATION + ERREURS + ABLATION + SURVIE")
print("=" * 60)


# ============================================================
# 0. MLFLOW
# ============================================================
mlflow.set_tracking_uri(f"file:///{(Path.cwd() / 'mlruns').as_posix()}")
mlflow.set_experiment(EXPERIMENT_NAME)
print(f"MLflow: {EXPERIMENT_NAME} -> {mlflow.get_tracking_uri()}")


# ============================================================
# 1. CHARGEMENT + MODELE PRINCIPAL (XGBoost, params raisonnables)
# ============================================================
print("\n[1/6] Chargement + XGBoost (params fixes)...")

cana, anom_clean = load_and_clean_v2(DATA_DIR)
df, FEATURES, FEATURE_NAMES, le_mat = build_features_v2(cana, anom_clean, cutoff_year=SPLIT_YEAR)

X = df[FEATURES].copy()
y = df["y"].copy()
n_pos = y.sum()
n_neg = len(y) - n_pos
scale_pos = n_neg / max(n_pos, 1)

print(f"  Dataset: {len(df):,} troncons | {n_pos:,} positifs ({100*n_pos/len(df):.2f}%)")
print(f"  Features: {len(FEATURES)}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

imputer = SimpleImputer(strategy="median")
X_train_imp = imputer.fit_transform(X_train)
X_test_imp = imputer.transform(X_test)

# XGBoost avec des params solides (pas de HPO, rapide)
xgb_params = {
    "n_estimators": 500,
    "max_depth": 8,
    "learning_rate": 0.03,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
    "min_child_weight": 5,
    "gamma": 0.1,
    "scale_pos_weight": scale_pos,
    "eval_metric": "aucpr",
    "random_state": 42,
    "tree_method": "hist",
}

model = xgb.XGBClassifier(**xgb_params)
model.fit(X_train_imp, y_train)
y_proba = model.predict_proba(X_test_imp)[:, 1]

auc = roc_auc_score(y_test, y_proba)
ap = average_precision_score(y_test, y_proba)

# Seuil optimal F1
prec_c, rec_c, thresholds = precision_recall_curve(y_test, y_proba)
f1s = 2 * prec_c * rec_c / (prec_c + rec_c + 1e-8)
best_thr = thresholds[np.argmax(f1s)]
y_pred = (y_proba >= best_thr).astype(int)
tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

# Captures
captures = {}
df_eval = pd.DataFrame({"proba": y_proba, "label": y_test.values})
df_sorted = df_eval.sort_values("proba", ascending=False)
for pct in [5, 10, 20, 30]:
    top = df_sorted.head(int(len(df_sorted) * pct / 100))
    captures[pct] = 100 * top["label"].sum() / max(y_test.sum(), 1)

print(f"\n  XGBoost: AUC={auc:.4f} | AP={ap:.4f}")
print(f"  F1={f1_score(y_test, y_pred):.4f} | Prec={precision_score(y_test, y_pred):.4f} | Rec={recall_score(y_test, y_pred):.4f}")
print(f"  TP={tp:,} FP={fp:,} FN={fn:,} TN={tn:,}")
for pct in [5, 10, 20, 30]:
    print(f"  Top {pct}% -> capture {captures[pct]:.1f}% des abandons")


# ============================================================
# 2. ANALYSE DES ERREURS
# ============================================================
print("\n" + "=" * 60)
print("[2/6] ANALYSE DES ERREURS (FP + FN)")
print("=" * 60)

# Reconstruire un df d'evaluation avec les infos troncons
df_test = df.loc[X_test.index].copy()
df_test["y_proba"] = y_proba
df_test["y_pred"] = y_pred

# --- Faux Positifs : predits comme abandons mais EN SERVICE ---
fp_mask = (df_test["y_pred"] == 1) & (df_test["y"] == 0)
fp_df = df_test[fp_mask]

print(f"\n  FAUX POSITIFS : {len(fp_df):,}")
print(f"  Score moyen FP : {fp_df['y_proba'].mean():.3f}")
print(f"  Age moyen FP   : {fp_df['age_at_split'].mean():.0f} ans (global: {df_test['age_at_split'].mean():.0f})")
print(f"  Materiaux FP :")
for mat, cnt in fp_df["MATERIAU"].value_counts().head(8).items():
    pct_fp = 100 * cnt / len(fp_df)
    pct_all = 100 * (df_test["MATERIAU"] == mat).sum() / len(df_test)
    print(f"    {mat:>8s}: {cnt:>5,} ({pct_fp:>5.1f}% des FP vs {pct_all:.1f}% global)")
print(f"  Etat FP :")
for etat, cnt in fp_df["ETAT_CLEAN"].value_counts().items():
    print(f"    {etat:>10s}: {cnt:>5,} ({100*cnt/len(fp_df):.1f}%)")
print(f"  Nb fuites moyen FP : {fp_df['nb_fuites'].mean():.2f} (global: {df_test['nb_fuites'].mean():.2f})")

# --- Faux Negatifs : abandonnes mais predits EN SERVICE ---
fn_mask = (df_test["y_pred"] == 0) & (df_test["y"] == 1)
fn_df = df_test[fn_mask]

print(f"\n  FAUX NEGATIFS : {len(fn_df):,}")
print(f"  Score moyen FN : {fn_df['y_proba'].mean():.3f}")
print(f"  Age moyen FN   : {fn_df['age_at_split'].mean():.0f} ans")
print(f"  Materiaux FN :")
for mat, cnt in fn_df["MATERIAU"].value_counts().head(8).items():
    print(f"    {mat:>8s}: {cnt:>5,} ({100*cnt/len(fn_df):.1f}%)")
print(f"  Etat FN :")
for etat, cnt in fn_df["ETAT_CLEAN"].value_counts().items():
    print(f"    {etat:>10s}: {cnt:>5,} ({100*cnt/len(fn_df):.1f}%)")
print(f"  Nb fuites moyen FN : {fn_df['nb_fuites'].mean():.2f}")

# Interpretation
print(f"\n  INTERPRETATION :")
print(f"  - FP = troncons vieux/fragiles pas encore abandonnes -> candidats futurs au renouvellement")
print(f"  - FN = abandons sur troncons jeunes/bons -> probablement chantiers/opportunites (non predictibles)")

# --- Figure erreurs ---
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Age distribution FP vs FN vs TP vs TN
for label, mask, color, ax_idx in [
    ("Vrais Positifs (TP)", (df_test["y_pred"] == 1) & (df_test["y"] == 1), "#2ecc71", 0),
    ("Faux Positifs (FP)", fp_mask, "#e74c3c", 1),
    ("Faux Negatifs (FN)", fn_mask, "#e67e22", 2),
    ("Vrais Negatifs (TN)", (df_test["y_pred"] == 0) & (df_test["y"] == 0), "#3498db", 3),
]:
    ax = axes[ax_idx // 2][ax_idx % 2]
    ages = df_test.loc[mask, "age_at_split"].dropna()
    ax.hist(ages, bins=40, color=color, edgecolor="white", alpha=0.8)
    ax.set_title(f"{label} (n={mask.sum():,}, age moy={ages.mean():.0f} ans)", fontsize=11)
    ax.set_xlabel("Age")
    ax.set_ylabel("Nb troncons")
    ax.axvline(x=ages.mean(), color="red", linestyle="--", alpha=0.7)

plt.suptitle("V5 — Distribution des ages par type de prediction", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v5_01_analyse_erreurs_age.png", dpi=150, bbox_inches="tight")
plt.close()
print("\n  => v5_01_analyse_erreurs_age.png")

# Materiau FP vs FN
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
for ax, subset, title, color in [
    (axes[0], fp_df, "Faux Positifs (FP)", "#e74c3c"),
    (axes[1], fn_df, "Faux Negatifs (FN)", "#e67e22"),
]:
    mat_counts = subset["MATERIAU"].value_counts().head(8)
    ax.barh(mat_counts.index, mat_counts.values, color=color)
    ax.set_xlabel("Nb troncons")
    ax.set_title(f"{title} — Top materiaux")
plt.suptitle("V5 — Materiaux des erreurs", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v5_02_analyse_erreurs_materiau.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v5_02_analyse_erreurs_materiau.png")

# Score distribution FP vs FN
fig, ax = plt.subplots(figsize=(12, 6))
ax.hist(fp_df["y_proba"], bins=50, alpha=0.6, label=f"FP (n={len(fp_df):,})", color="#e74c3c")
ax.hist(fn_df["y_proba"], bins=50, alpha=0.6, label=f"FN (n={len(fn_df):,})", color="#e67e22")
ax.axvline(x=best_thr, color="black", linestyle="--", label=f"Seuil F1={best_thr:.3f}")
ax.set_xlabel("Score (probabilite)")
ax.set_ylabel("Nb troncons")
ax.set_title("V5 — Distribution des scores : FP vs FN")
ax.legend()
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v5_03_scores_fp_fn.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v5_03_scores_fp_fn.png")


# ============================================================
# 3. ABLATION DE FEATURES
# ============================================================
print("\n" + "=" * 60)
print("[3/6] ABLATION DE FEATURES")
print("=" * 60)

# AUC de reference (toutes features)
auc_ref = auc
print(f"  AUC reference (toutes features) : {auc_ref:.4f}")

# Retirer chaque feature une par une et mesurer l'impact
ablation_results = []
for i, (feat, fname) in enumerate(zip(FEATURES, FEATURE_NAMES)):
    feats_without = [f for f in FEATURES if f != feat]
    X_tr_abl = imputer.fit_transform(X_train[feats_without])
    X_te_abl = imputer.transform(X_test[feats_without])

    model_abl = xgb.XGBClassifier(**xgb_params)
    model_abl.fit(X_tr_abl, y_train)
    y_proba_abl = model_abl.predict_proba(X_te_abl)[:, 1]
    auc_abl = roc_auc_score(y_test, y_proba_abl)
    ap_abl = average_precision_score(y_test, y_proba_abl)

    delta = auc_ref - auc_abl  # positif = la feature aide
    ablation_results.append({
        "feature": fname, "feature_col": feat,
        "auc_without": auc_abl, "ap_without": ap_abl,
        "delta_auc": delta,
    })
    direction = "+" if delta > 0 else "-"
    print(f"  [{i+1:>2}/{len(FEATURES)}] Sans {fname:>25s} : AUC={auc_abl:.4f} (delta={delta:+.4f} {direction})")

abl_df = pd.DataFrame(ablation_results).sort_values("delta_auc", ascending=False)
abl_df.to_csv(OUTPUT_DIR / "v5_ablation_features.csv", index=False)

# Features qui NUISENT au modele (delta < 0 = retirer ameliore)
harmful = abl_df[abl_df["delta_auc"] < -0.001]
helpful = abl_df[abl_df["delta_auc"] > 0.001]

print(f"\n  Features les plus utiles (retirer fait baisser AUC) :")
for _, row in helpful.head(5).iterrows():
    print(f"    {row['feature']:>25s} : delta={row['delta_auc']:+.4f}")

if len(harmful) > 0:
    print(f"\n  Features potentiellement nuisibles (retirer ameliore AUC) :")
    for _, row in harmful.iterrows():
        print(f"    {row['feature']:>25s} : delta={row['delta_auc']:+.4f}")
else:
    print(f"\n  Aucune feature nuisible detectee.")

# Figure ablation
fig, ax = plt.subplots(figsize=(14, 8))
abl_sorted = abl_df.sort_values("delta_auc", ascending=True)
colors_abl = ["#d32f2f" if d < 0 else "#388e3c" for d in abl_sorted["delta_auc"]]
ax.barh(abl_sorted["feature"], abl_sorted["delta_auc"], color=colors_abl)
ax.axvline(x=0, color="black", linewidth=0.8)
ax.set_xlabel("Delta AUC (positif = feature utile)")
ax.set_title(f"V5 — Ablation de features (AUC ref = {auc_ref:.4f})", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v5_04_ablation_features.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v5_04_ablation_features.png")


# ============================================================
# 4. CASCADE : RANKING CLASSIFICATION -> SURVIE SUR LE TOP
# ============================================================
print("\n" + "=" * 60)
print("[4/6] CASCADE : CLASSIFICATION -> SURVIE")
print("=" * 60)

# Scorer TOUT le dataset
X_all_imp = SimpleImputer(strategy="median").fit_transform(X)
model_full = xgb.XGBClassifier(**xgb_params)
model_full.fit(X_all_imp, y)
df["score_classif"] = model_full.predict_proba(X_all_imp)[:, 1]

# Ranking
df["rang_classif"] = df["score_classif"].rank(ascending=False, method="first").astype(int)
df["top_pct_classif"] = 100 * df["rang_classif"] / len(df)

TOP_PCT = 30
n_top = int(len(df) * TOP_PCT / 100)
top_ids = set(df.nsmallest(n_top, "rang_classif")["OBJET"])
print(f"  Top {TOP_PCT}% = {n_top:,} troncons")
print(f"  Abandons dans le top : {df[df['OBJET'].isin(top_ids)]['y'].sum():,} / {df['y'].sum():,}")

# --- Survie sur le top ---
surv = df[df["OBJET"].isin(top_ids) & df["date_fiable"]].copy()
surv["duration"] = surv["age_at_split"].clip(lower=1)
surv["event"] = surv["y"]
surv = surv[surv["duration"].notna() & (surv["duration"] > 0)].copy()
print(f"  Troncons pour survie : {len(surv):,} (events={surv['event'].sum():,})")

# Kaplan-Meier par famille materiau
fig, ax = plt.subplots(figsize=(14, 8))
kmf = KaplanMeierFitter()
km_results = {}
top_fams = surv["FAMILLE_MATERIAU"].value_counts().head(6).index.tolist()

for i, fam in enumerate(top_fams):
    mask = surv["FAMILLE_MATERIAU"] == fam
    if mask.sum() < 50:
        continue
    kmf.fit(surv.loc[mask, "duration"], event_observed=surv.loc[mask, "event"], label=fam)
    kmf.plot_survival_function(ax=ax, color=COLORS[i], linewidth=2)
    med = kmf.median_survival_time_
    km_results[fam] = {"median": med, "n": int(mask.sum()), "events": int(surv.loc[mask, "event"].sum())}
    print(f"    {fam:>20s}: n={mask.sum():>5,} | events={surv.loc[mask,'event'].sum():>4,} | survie mediane={med:.0f} ans")

ax.set_xlabel("Age (annees)")
ax.set_ylabel("P(survie)")
ax.set_title(f"V5 — Kaplan-Meier sur le TOP {TOP_PCT}% par famille materiau", fontsize=13, fontweight="bold")
ax.set_xlim(0, 120)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v5_05_kaplan_meier_top.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v5_05_kaplan_meier_top.png")

# Cox PH pour re-ordonner le top
print("\n  Cox PH sur le TOP pour re-ordonner...")
cox_feats = ["MATERIAU_ENC", "DIAMETRE", "LONGUEUR", "ETAT_ORD", "nb_fuites", "acceleration"]
cox_df = surv[["duration", "event"] + cox_feats].dropna()

cph = CoxPHFitter(penalizer=0.01)
cph.fit(cox_df, duration_col="duration", event_col="event")
print("\n  Hazard Ratios :")
for idx, row in cph.summary[["exp(coef)", "p"]].iterrows():
    sig = "***" if row["p"] < 0.001 else "**" if row["p"] < 0.01 else "*" if row["p"] < 0.05 else "ns"
    print(f"    {idx:>15s}: HR={row['exp(coef)']:.4f} {sig}")

# Score Cox
cox_risk = cph.predict_partial_hazard(cox_df[cox_feats])
surv.loc[cox_risk.index, "cox_risk"] = cox_risk.values

# Score cascade : normaliser et combiner
df["cox_risk"] = np.nan
df.loc[cox_risk.index, "cox_risk"] = cox_risk.values

sc_min, sc_max = df["score_classif"].min(), df["score_classif"].max()
df["score_classif_norm"] = (df["score_classif"] - sc_min) / (sc_max - sc_min + 1e-8)

cox_vals = df["cox_risk"].dropna()
if len(cox_vals) > 0:
    cr_min, cr_max = cox_vals.min(), cox_vals.max()
    df["cox_risk_norm"] = (df["cox_risk"] - cr_min) / (cr_max - cr_min + 1e-8)
else:
    df["cox_risk_norm"] = 0
df["cox_risk_norm"] = df["cox_risk_norm"].fillna(0)

W_CLASSIF, W_SURVIE = 0.7, 0.3
df["score_cascade"] = df["score_classif_norm"]
in_top = df["OBJET"].isin(top_ids)
df.loc[in_top, "score_cascade"] = (
    W_CLASSIF * df.loc[in_top, "score_classif_norm"] +
    W_SURVIE * df.loc[in_top, "cox_risk_norm"]
)

# Comparer AUC classif vs cascade
auc_classif_full = roc_auc_score(y, df["score_classif"])
auc_cascade_full = roc_auc_score(y, df["score_cascade"])
print(f"\n  AUC Classification seule : {auc_classif_full:.4f}")
print(f"  AUC Cascade (classif+survie) : {auc_cascade_full:.4f}")

# Courbe lift comparaison
fig, ax = plt.subplots(figsize=(14, 8))
for score_col, label, color, ls in [
    ("score_cascade", "Cascade (classif + survie)", "blue", "-"),
    ("score_classif", "Classification seule", "green", "--"),
]:
    df_s = df.sort_values(score_col, ascending=False).reset_index(drop=True)
    df_s["cum"] = df_s["y"].cumsum()
    df_s["pct_x"] = (df_s.index + 1) / len(df_s) * 100
    df_s["pct_y"] = df_s["cum"] / max(df_s["y"].sum(), 1) * 100
    ax.plot(df_s["pct_x"], df_s["pct_y"], color=color, linestyle=ls, linewidth=2.5, label=label)

ax.plot([0, 100], [0, 100], "r:", linewidth=1.5, label="Hasard")
for pct in [5, 10, 20, 30]:
    df_h = df.sort_values("score_cascade", ascending=False).reset_index(drop=True)
    df_h["cum"] = df_h["y"].cumsum()
    idx = int(len(df_h) * pct / 100)
    cap = 100 * df_h["cum"].iloc[idx] / max(df_h["y"].sum(), 1)
    ax.annotate(f"Top {pct}% -> {cap:.0f}%", xy=(pct, cap), xytext=(pct + 8, cap - 5),
                arrowprops=dict(arrowstyle="->", color="blue"), fontsize=10, color="blue", fontweight="bold")

ax.set_xlabel("% des troncons")
ax.set_ylabel("% des abandons captures")
ax.set_title("V5 — Courbe de Lift : Cascade vs Classification", fontsize=13, fontweight="bold")
ax.legend(fontsize=11, loc="lower right")
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v5_06_courbe_lift_cascade.png", dpi=150, bbox_inches="tight")
plt.close()
print("  => v5_06_courbe_lift_cascade.png")


# ============================================================
# 5. SHAP
# ============================================================
print("\n" + "=" * 60)
print("[5/6] SHAP")
print("=" * 60)

sample_idx = np.random.RandomState(42).choice(len(X), size=min(5000, len(X)), replace=False)
X_sample = pd.DataFrame(X_all_imp[sample_idx], columns=FEATURES)

explainer = shap.TreeExplainer(model_full)
shap_values = explainer.shap_values(X_sample)

fig, ax = plt.subplots(figsize=(14, 10))
shap.summary_plot(shap_values, X_sample, feature_names=FEATURE_NAMES, show=False, max_display=20)
plt.title("V5 — SHAP (XGBoost, cible abandon/depose)", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v5_07_shap_summary.png", dpi=150, bbox_inches="tight")
plt.close()

fig, ax = plt.subplots(figsize=(14, 7))
shap.summary_plot(shap_values, X_sample, feature_names=FEATURE_NAMES, plot_type="bar", show=False, max_display=20)
plt.title("V5 — SHAP importance", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "v5_08_shap_bar.png", dpi=150, bbox_inches="tight")
plt.close()

shap_imp = pd.DataFrame({
    "feature": FEATURE_NAMES,
    "mean_abs_shap": np.abs(shap_values).mean(axis=0),
}).sort_values("mean_abs_shap", ascending=False)
shap_imp.to_csv(OUTPUT_DIR / "v5_shap_importance.csv", index=False)

print("  Top features SHAP :")
for _, row in shap_imp.head(10).iterrows():
    print(f"    {row['feature']:>25s} : {row['mean_abs_shap']:.4f}")
print("  => v5_07_shap_summary.png, v5_08_shap_bar.png")


# ============================================================
# 6. SCORING FINAL + MLFLOW
# ============================================================
print("\n" + "=" * 60)
print("[6/6] SCORING + MLFLOW")
print("=" * 60)

# Scoring EN SERVICE
es_mask = df["STATUT_OBJET"] == "EN SERVICE"
scoring = df.loc[es_mask, [
    "OBJET", "MATERIAU", "FAMILLE_MATERIAU", "DIAMETRE", "LONGUEUR",
    "age_at_split", "cohorte", "nb_anom", "nb_fuites", "ETAT_CLEAN",
    "score_classif", "score_cascade",
]].copy()
scoring = scoring.rename(columns={"age_at_split": "age"})
scoring = scoring.sort_values("score_cascade", ascending=False)
scoring["rang"] = range(1, len(scoring) + 1)
scoring["top_pct"] = (100 * scoring["rang"] / len(scoring)).round(2)
scoring.to_csv(OUTPUT_DIR / "v5_scoring_troncons.csv", index=False)
print(f"  => v5_scoring_troncons.csv ({len(scoring):,} troncons EN SERVICE)")

# --- MLflow ---
print("\n  Logging MLflow...")
with mlflow.start_run(run_name=f"V5_XGBoost_cutoff{SPLIT_YEAR}") as run:
    # Params
    mlflow.log_param("version", "V5")
    mlflow.log_param("cible", "abandon_depose")
    mlflow.log_param("cutoff_year", SPLIT_YEAR)
    mlflow.log_param("n_features", len(FEATURES))
    mlflow.log_param("n_train", len(X_train))
    mlflow.log_param("n_test", len(X_test))
    mlflow.log_param("n_positifs", int(n_pos))
    mlflow.log_param("pct_positifs", round(100 * n_pos / len(df), 2))
    mlflow.log_param("top_pct_survie", TOP_PCT)
    mlflow.log_param("w_classif", W_CLASSIF)
    mlflow.log_param("w_survie", W_SURVIE)
    for k, v in xgb_params.items():
        mlflow.log_param(f"xgb_{k}", v)

    # Metriques
    mlflow.log_metric("auc_test", auc)
    mlflow.log_metric("ap_test", ap)
    mlflow.log_metric("f1_test", f1_score(y_test, y_pred))
    mlflow.log_metric("precision_test", precision_score(y_test, y_pred))
    mlflow.log_metric("recall_test", recall_score(y_test, y_pred))
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
        safe_name = re.sub(r"[^a-zA-Z0-9_\-. /]", "", row["feature"].replace("/", "_per_"))
        mlflow.log_metric(f"shap_top{i+1}_{safe_name}", row["mean_abs_shap"])

    # Ablation
    for _, row in abl_df.iterrows():
        safe_name = re.sub(r"[^a-zA-Z0-9_\-. /]", "", row["feature"].replace("/", "_per_"))
        mlflow.log_metric(f"ablation_{safe_name}", row["delta_auc"])

    # Kaplan-Meier
    for fam, info in km_results.items():
        safe_fam = fam.replace(" ", "_")
        mlflow.log_metric(f"km_median_{safe_fam}", info["median"])

    # Artifacts
    for f in OUTPUT_DIR.glob("v5_*.png"):
        mlflow.log_artifact(str(f))
    for f in OUTPUT_DIR.glob("v5_*.csv"):
        mlflow.log_artifact(str(f))

    # Modele
    mlflow.xgboost.log_model(model_full, artifact_path="model")

    print(f"  MLflow run ID: {run.info.run_id}")
    print(f"  => Ouvrez http://localhost:5000 pour voir les resultats")

# --- RAPPORT CONSOLE ---
print("\n" + "=" * 60)
print("RAPPORT V5")
print("=" * 60)
print(f"""
MODELE : XGBoost (params fixes, pas de HPO)
CIBLE  : ABANDONNE/DEPOSE = 1 vs EN SERVICE = 0
SPLIT  : cutoff={SPLIT_YEAR}

METRIQUES TEST :
  AUC = {auc:.4f}
  AP  = {ap:.4f}
  Capture :
    Top  5% -> {captures[5]:.1f}%
    Top 10% -> {captures[10]:.1f}%
    Top 20% -> {captures[20]:.1f}%
    Top 30% -> {captures[30]:.1f}%

CASCADE (classif + survie) :
  AUC classif seule : {auc_classif_full:.4f}
  AUC cascade       : {auc_cascade_full:.4f}

ANALYSE ERREURS :
  FP = {fp:,} -> troncons a risque pas encore abandonnes (candidats futurs)
  FN = {fn:,} -> abandons non predictibles (chantiers, opportunites)

ABLATION :
  Features les plus utiles :""")
for _, row in helpful.head(3).iterrows():
    print(f"    {row['feature']:>25s} : delta={row['delta_auc']:+.4f}")
if len(harmful) > 0:
    print(f"  Features a considerer retirer :")
    for _, row in harmful.iterrows():
        print(f"    {row['feature']:>25s} : delta={row['delta_auc']:+.4f}")

print(f"""
SCORING : {len(scoring):,} troncons EN SERVICE -> v5_scoring_troncons.csv
  Colonnes : OBJET, MATERIAU, age, score_classif, score_cascade, rang, top_pct

MLflow : http://localhost:5000
""")
print("=" * 60)
print("TERMINE")
print("=" * 60)
