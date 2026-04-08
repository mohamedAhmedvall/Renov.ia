"""
V9 — Modèle de prédiction de fuites/casses avec aléa argile.

Corrections appliquées (vs V8) :
  [P0] Vrai split TEMPOREL : train observe avant 2015, test observe 2018
  [P0] Imputeurs & TE fit sur train-only (via fit_state de data_prep.build_features)
  [P0] Scoring production ré-entraîné à observation_year = ANNEE_REF
  [P1] Calibration isotonique (CalibratedClassifierCV) → score = vraie proba
  [P1] Flag age_imputed conservé
  [NEW] Feature `alea_argile_ord` + `annees_depuis_derniere_fuite`

Pipeline :
  1. EDA déjà lancé (eda.py)
  2. Split temporel : train obs=2015, test obs=2018 (horizon=3)
  3. Fit pipeline train-only
  4. Baseline âge
  5. Ablation : mesurer gain argile
  6. Backtesting temporel (3 fenêtres)
  7. Calibration + SHAP
  8. Scoring production (obs=2024, h=1/3/5)
  9. Rapport + plots
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
import xgboost as xgb
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import CalibratedClassifierCV

from data_prep import load_raw, build_features, FEATURE_COLS, FEATURE_NAMES, ANNEE_REF

DATA_DIR = Path(__file__).parent.parent / "data"
OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

TRAIN_OBS = 2015
TEST_OBS = 2018
HORIZON = 3

print("=" * 60)
print("V9 — MODÈLE FUITES (avec aléa argile)")
print("=" * 60)

# ============================================================
# [1] Chargement
# ============================================================
cana, fuites, argile = load_raw(DATA_DIR)

# ============================================================
# [2] SPLIT TEMPOREL RÉEL
# ============================================================
print(f"\n[2] Split temporel : train obs={TRAIN_OBS} / test obs={TEST_OBS} / h={HORIZON}")

df_tr, X_tr, y_tr, fit_state = build_features(
    cana, fuites, argile, observation_year=TRAIN_OBS, horizon=HORIZON, fit_state=None
)
df_te, X_te, y_te, _ = build_features(
    cana, fuites, argile, observation_year=TEST_OBS, horizon=HORIZON, fit_state=fit_state
)
print(f"  Train : {len(df_tr):,} ({y_tr.sum():,} pos, {100*y_tr.mean():.2f}%)")
print(f"  Test  : {len(df_te):,} ({y_te.sum():,} pos, {100*y_te.mean():.2f}%)")
print(f"  Features ({len(FEATURE_COLS)}) : {FEATURE_NAMES}")

# ============================================================
# [3] XGBoost
# ============================================================
n_pos = y_tr.sum()
n_neg = len(y_tr) - n_pos
xgb_params = dict(
    n_estimators=500, max_depth=6, learning_rate=0.03,
    subsample=0.8, colsample_bytree=0.8,
    scale_pos_weight=round(n_neg / max(n_pos, 1), 1),
    eval_metric="auc", random_state=42, n_jobs=-1,
)

model = xgb.XGBClassifier(**xgb_params)
model.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=0)
proba = model.predict_proba(X_te)[:, 1]

auc = roc_auc_score(y_te, proba)
ap = average_precision_score(y_te, proba)
print(f"\n  XGBoost V9 : AUC={auc:.4f} | AP={ap:.4f}")

# Capture @ top %
def capture_at(y, s, pcts=(5, 10, 20, 30)):
    out = {}
    n = len(y)
    pos = max(y.sum(), 1)
    for p in pcts:
        top_n = int(n * p / 100)
        top_idx = np.argsort(s)[::-1][:top_n]
        out[p] = round(100 * y[top_idx].sum() / pos, 1)
    return out

cap_ml = capture_at(y_te, proba)
print("  Capture ML :", {f"top{k}%": f"{v}%" for k, v in cap_ml.items()})

# ============================================================
# [4] Baseline âge
# ============================================================
age_idx = FEATURE_COLS.index("age")
age_te = X_te[:, age_idx]
auc_age = roc_auc_score(y_te, age_te)
cap_age = capture_at(y_te, age_te)
print(f"\n  Baseline âge : AUC={auc_age:.4f} | gain ML = {auc-auc_age:+.4f}")

# ============================================================
# [5] ABLATION — quantifier l'apport de l'argile
# ============================================================
print("\n[5] Ablation de features")
ablation = []
for i, name in enumerate(FEATURE_NAMES):
    X_tr_abl = np.delete(X_tr, i, axis=1)
    X_te_abl = np.delete(X_te, i, axis=1)
    m = xgb.XGBClassifier(**xgb_params)
    m.fit(X_tr_abl, y_tr, eval_set=[(X_te_abl, y_te)], verbose=0)
    p = m.predict_proba(X_te_abl)[:, 1]
    a = roc_auc_score(y_te, p)
    ablation.append({"feature": name, "auc_sans": a, "delta": auc - a})
    print(f"  sans {name:>30s} : AUC={a:.4f}  d={auc-a:+.4f}")
abl_df = pd.DataFrame(ablation).sort_values("delta", ascending=False)
abl_df.to_csv(OUT / "v9_ablation.csv", index=False)

# Plot ablation
fig, ax = plt.subplots(figsize=(9, 5))
colors = ["#d62728" if f == "Alea_argile" else "#1f77b4" for f in abl_df["feature"]]
ax.barh(abl_df["feature"], abl_df["delta"], color=colors)
ax.axvline(0, color="k", lw=0.5)
ax.set_xlabel("Δ AUC (perte si feature retirée)")
ax.set_title("Ablation V9 — contribution de chaque feature (argile en rouge)")
plt.tight_layout()
plt.savefig(OUT / "v9_01_ablation.png", dpi=140)
plt.close()
delta_argile = abl_df.set_index("feature").loc["Alea_argile", "delta"]
print(f"\n  >>> Apport de l'aléa argile : ΔAUC = {delta_argile:+.4f}")

# ============================================================
# [6] BACKTESTING TEMPOREL
# ============================================================
print("\n[6] Backtesting temporel (3 fenêtres)")
windows = [(2012, 2015), (2015, 2018), (2018, 2021)]
bt_rows = []
for tr_y, te_y in windows:
    df_a, Xa, ya, fs = build_features(cana, fuites, argile, tr_y, HORIZON)
    df_b, Xb, yb, _ = build_features(cana, fuites, argile, te_y, HORIZON, fit_state=fs)
    if ya.sum() < 10 or yb.sum() < 10:
        continue
    p_bt = dict(xgb_params)
    p_bt["scale_pos_weight"] = round((len(ya)-ya.sum())/max(ya.sum(),1), 1)
    m = xgb.XGBClassifier(**p_bt)
    m.fit(Xa, ya, eval_set=[(Xb, yb)], verbose=0)
    pb = m.predict_proba(Xb)[:, 1]
    a = roc_auc_score(yb, pb)
    aa = roc_auc_score(yb, Xb[:, age_idx])
    cap20 = capture_at(yb, pb, pcts=(20,))[20]
    bt_rows.append(dict(
        window=f"tr{tr_y}_te{te_y}", auc=a, auc_age=aa,
        gain=a-aa, capture_top20=cap20, n_test=len(yb), n_pos=int(yb.sum()),
    ))
    print(f"  tr={tr_y} te={te_y} : AUC={a:.4f} (âge={aa:.4f}, gain={a-aa:+.4f}) cap20={cap20}%")
bt_df = pd.DataFrame(bt_rows)
bt_df.to_csv(OUT / "v9_backtesting.csv", index=False)
if len(bt_df):
    print(f"  Moyenne AUC : {bt_df['auc'].mean():.4f} ± {bt_df['auc'].std():.4f}")

# ============================================================
# [7] CALIBRATION + SHAP
# ============================================================
print("\n[7] Calibration isotonique")
# Prefit : on passe le modèle déjà entraîné, il calibre sur un set à part
# Ici on re-sépare: train→fit, test→calibrate non-idéal, donc on calibre sur test
# Approche propre : découper train en 80/20 pour calibration
rng = np.random.RandomState(0)
idx = rng.permutation(len(X_tr))
cut = int(0.8 * len(idx))
X_fit, y_fit = X_tr[idx[:cut]], y_tr[idx[:cut]]
X_cal, y_cal = X_tr[idx[cut:]], y_tr[idx[cut:]]

base = xgb.XGBClassifier(**xgb_params)
base.fit(X_fit, y_fit, verbose=0)

p_cal_set = base.predict_proba(X_cal)[:, 1]
iso = IsotonicRegression(out_of_bounds="clip")
iso.fit(p_cal_set, y_cal)
proba_te_raw = base.predict_proba(X_te)[:, 1]
proba_cal = iso.transform(proba_te_raw)

auc_cal = roc_auc_score(y_te, proba_cal)
brier_raw = brier_score_loss(y_te, proba)
brier_cal = brier_score_loss(y_te, proba_cal)
print(f"  AUC calibré={auc_cal:.4f} | Brier brut={brier_raw:.4f} → calibré={brier_cal:.4f}")

# Calibration curve
frac_pos_raw, mean_pred_raw = calibration_curve(y_te, proba, n_bins=10, strategy="quantile")
frac_pos_cal, mean_pred_cal = calibration_curve(y_te, proba_cal, n_bins=10, strategy="quantile")

fig, ax = plt.subplots(figsize=(7, 6))
ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Parfait")
ax.plot(mean_pred_raw, frac_pos_raw, "o-", label=f"Brut (Brier={brier_raw:.3f})")
ax.plot(mean_pred_cal, frac_pos_cal, "s-", label=f"Calibré (Brier={brier_cal:.3f})")
ax.set_xlabel("Probabilité prédite moyenne")
ax.set_ylabel("Fréquence observée")
ax.set_title("Courbe de calibration — V9")
ax.legend()
plt.tight_layout()
plt.savefig(OUT / "v9_02_calibration.png", dpi=140)
plt.close()

# SHAP
print("\n  SHAP (horizon=3)")
expl = shap.TreeExplainer(model)
sv = expl.shap_values(X_te)
shap_imp = pd.DataFrame({
    "feature": FEATURE_NAMES,
    "mean_abs_shap": np.abs(sv).mean(axis=0),
}).sort_values("mean_abs_shap", ascending=False)
shap_imp.to_csv(OUT / "v9_shap_importance.csv", index=False)
print(shap_imp.to_string(index=False))

fig, ax = plt.subplots(figsize=(8, 5))
shap.summary_plot(sv, X_te, feature_names=FEATURE_NAMES, show=False, plot_type="bar")
plt.tight_layout()
plt.savefig(OUT / "v9_03_shap_bar.png", dpi=140)
plt.close()

fig, ax = plt.subplots(figsize=(9, 6))
shap.summary_plot(sv, X_te, feature_names=FEATURE_NAMES, show=False)
plt.tight_layout()
plt.savefig(OUT / "v9_04_shap_summary.png", dpi=140)
plt.close()

# ============================================================
# [8] SCORING PRODUCTION — obs=ANNEE_REF, multi-horizons
# ============================================================
print(f"\n[8] Scoring production à obs={ANNEE_REF} (H=1/3/5)")
# Base enrichie : tout ce dont l'app a besoin (pas besoin de jointure côté app)
_base = cana[cana["STATUT_OBJET"] == "EN SERVICE"].copy()
_base["age"] = ANNEE_REF - _base["annee_pose"]
_base.loc[~_base["date_fiable"], "age"] = np.nan
_base["age_imputed"] = _base["age"].isna().astype(int)
_base["decennie_pose"] = (_base["annee_pose"] // 10) * 10
# Historique fuites avant ANNEE_REF
_hist = fuites[fuites["annee_Anomalie"] < ANNEE_REF].groupby("GID_OBJET").size().rename("nb_fuites_historique")
_base = _base.merge(_hist, left_on="OBJET", right_index=True, how="left")
_base["nb_fuites_historique"] = _base["nb_fuites_historique"].fillna(0).astype(int)
# Argile
_base = _base.merge(argile[["GID", "alea_argile"]], left_on="OBJET", right_on="GID", how="left").drop(columns=["GID"])

scoring = _base[[
    "OBJET", "MATERIAU", "famille_mat", "DIAMETRE", "LONGUEUR",
    "age", "age_imputed", "decennie_pose",
    "nb_fuites_historique", "alea_argile",
]].copy()

for h in (1, 3, 5):
    # Refit sur tout le dataset observé à (ANNEE_REF - h) pour avoir une vraie cible
    obs_fit = ANNEE_REF - h
    df_f, Xf, yf, fs_full = build_features(cana, fuites, argile, obs_fit, h)
    p_full = dict(xgb_params)
    p_full["scale_pos_weight"] = round((len(yf)-yf.sum())/max(yf.sum(),1), 1)

    # Calibration CV=5 : 5 folds, chaque isotonic fit sur 4/5 et prédit sur 1/5,
    # moyenne finale → beaucoup plus robuste aux bins peu peuplés qu'un holdout 20%
    base_h = xgb.XGBClassifier(**p_full)
    cal = CalibratedClassifierCV(base_h, method="isotonic", cv=5)
    cal.fit(Xf, yf)

    # Scorer les EN SERVICE à obs=ANNEE_REF
    df_s, Xs, _, _ = build_features(cana, fuites, argile, ANNEE_REF, h, fit_state=fs_full)
    df_s = df_s[df_s["STATUT_OBJET"] == "EN SERVICE"].copy()
    Xs = df_s[FEATURE_COLS].values.astype(float)
    scores = cal.predict_proba(Xs)[:, 1]

    sub = df_s[["OBJET"]].copy()
    sub[f"score_h{h}"] = scores
    scoring = scoring.merge(sub, on="OBJET", how="left")
    print(f"  H={h} : moyenne={scores.mean():.4f} | p90={np.quantile(scores, 0.9):.4f} | max={scores.max():.4f}")

# ─── Cohérence multi-horizons ────────────────────────────────
# P(fuite dans 5 ans) ≥ P(dans 3 ans) ≥ P(dans 1 an) : on impose la monotonie
# via un max cumulatif, puis on clippe à 0.99 (isotonic peut sortir 1.0 sur bins purs).
for h in (1, 3, 5):
    scoring[f"score_h{h}"] = scoring[f"score_h{h}"].clip(upper=0.99)
scoring["score_h3"] = np.maximum(scoring["score_h1"], scoring["score_h3"])
scoring["score_h5"] = np.maximum(scoring["score_h3"], scoring["score_h5"])
print(f"  Après monotonisation : h1 max={scoring['score_h1'].max():.3f} | "
      f"h3 max={scoring['score_h3'].max():.3f} | h5 max={scoring['score_h5'].max():.3f}")

scoring = scoring.sort_values("score_h3", ascending=False).reset_index(drop=True)
scoring["rang"] = range(1, len(scoring) + 1)
scoring["top_pct"] = (scoring["rang"] / len(scoring) * 100).round(1)
scoring.to_csv(OUT / "v9_scoring_fuites.csv", index=False)
print(f"  => v9_scoring_fuites.csv ({len(scoring):,} tronçons EN SERVICE)")

# ============================================================
# [9] RAPPORT FINAL
# ============================================================
bt_str = f"{bt_df['auc'].mean():.4f} ± {bt_df['auc'].std():.4f}" if len(bt_df) else "N/A"
print("\n" + "=" * 60)
print("RAPPORT V9")
print("=" * 60)
print(f"""
DONNÉES
  Split temporel réel : train obs={TRAIN_OBS}, test obs={TEST_OBS}, horizon={HORIZON} ans
  Features (9)       : {', '.join(FEATURE_NAMES)}
  NEW                : alea_argile_ord (apport ΔAUC={delta_argile:+.4f})

PERFORMANCE TEST (split temporel)
  AUC V9 (non calibré) = {auc:.4f}
  AUC V9 (calibré)     = {auc_cal:.4f}
  AUC baseline âge     = {auc_age:.4f}
  Gain ML vs âge       = {auc - auc_age:+.4f}
  AP                   = {ap:.4f}
  Brier brut → calibré = {brier_raw:.4f} → {brier_cal:.4f}

CAPTURE (test)
  Top  5% : ML={cap_ml[5]}% | âge={cap_age[5]}%
  Top 10% : ML={cap_ml[10]}% | âge={cap_age[10]}%
  Top 20% : ML={cap_ml[20]}% | âge={cap_age[20]}%
  Top 30% : ML={cap_ml[30]}% | âge={cap_age[30]}%

BACKTESTING
  AUC moyen sur 3 fenêtres = {bt_str}

SCORING PRODUCTION → V9/output/v9_scoring_fuites.csv
""")
print("=" * 60)
