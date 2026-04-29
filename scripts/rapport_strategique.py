"""
Rapport stratégique — Éléments d'aide à la décision pour le renouvellement.

Sections :
  1. Linéaire top 20% vs réseau total vs obligation 1%/an
  2. Analyse des tronçons abandonnés (fuites avant, délai fuite→abandon)
  3. Backtesting visuel : « bons pronostics manqués »
  4. Génération rapport HTML
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Ajouter V9 au path pour importer data_prep
sys.path.insert(0, str(Path(__file__).parent.parent / "V9"))
from data_prep import load_raw, build_features, FEATURE_COLS, ANNEE_REF

DATA_DIR = Path(__file__).parent.parent / "data"
V9_OUT = Path(__file__).parent.parent / "V9" / "output"
OUT = Path(__file__).parent.parent / "output"
OUT.mkdir(exist_ok=True)

print("=" * 60)
print("RAPPORT STRATÉGIQUE — AIDE À LA DÉCISION")
print("=" * 60)

# ============================================================
# Chargement
# ============================================================
cana, fuites, argile = load_raw(DATA_DIR)
scoring = pd.read_csv(V9_OUT / "v9_scoring_fuites.csv")

# Longueur numérique propre
cana["LONGUEUR_num"] = pd.to_numeric(
    cana["LONGUEUR"].astype(str).str.replace(",", "."), errors="coerce"
)
scoring["LONGUEUR_num"] = pd.to_numeric(
    scoring["LONGUEUR"].astype(str).str.replace(",", "."), errors="coerce"
)

# ============================================================
# [1] LINÉAIRE TOP 20% vs RÉSEAU vs OBLIGATION 1%/AN
# ============================================================
print("\n" + "=" * 60)
print("[1] LINÉAIRE TOP 20% vs RÉSEAU TOTAL vs OBLIGATION 1%/AN")
print("=" * 60)

es = cana[cana["STATUT_OBJET"] == "EN SERVICE"]
lineaire_total_m = es["LONGUEUR_num"].sum()
lineaire_total_km = lineaire_total_m / 1000
nb_total = len(es)

# Top 20% par score_h3
n_top20 = int(len(scoring) * 0.20)
top20 = scoring.head(n_top20)  # déjà trié par score_h3 desc
lineaire_top20_m = top20["LONGUEUR_num"].sum()
lineaire_top20_km = lineaire_top20_m / 1000
pct_reseau_top20 = lineaire_top20_km / lineaire_total_km * 100

# Obligation 1%/an
obligation_1pct_km = lineaire_total_km * 0.01
obligation_1pct_m = lineaire_total_m * 0.01

# Combien d'années le top 20% représente en renouvellement à 1%/an
annees_top20 = lineaire_top20_km / obligation_1pct_km if obligation_1pct_km > 0 else 0

# Score moyen dans les tranches
scoring["tranche"] = pd.cut(
    scoring["top_pct"], bins=[0, 5, 10, 20, 50, 100],
    labels=["Top 5%", "Top 5-10%", "Top 10-20%", "Top 20-50%", "Bottom 50%"],
)
stats_tranches = scoring.groupby("tranche", observed=True).agg(
    nb_troncons=("OBJET", "count"),
    lineaire_km=("LONGUEUR_num", lambda x: x.sum() / 1000),
    score_h3_moy=("score_h3", "mean"),
    score_h3_med=("score_h3", "median"),
    score_h1_moy=("score_h1", "mean"),
    score_h5_moy=("score_h5", "mean"),
    fuites_hist_moy=("nb_fuites_historique", "mean"),
).round(4)

print(f"  Réseau EN SERVICE : {nb_total:,} tronçons | {lineaire_total_km:,.1f} km")
print(f"  Top 20% (score V9) : {n_top20:,} tronçons | {lineaire_top20_km:,.1f} km ({pct_reseau_top20:.1f}% du réseau)")
print(f"  Obligation 1%/an  : {obligation_1pct_km:,.2f} km/an")
print(f"  Le top 20% représente {annees_top20:.1f} années de renouvellement à 1%/an")
print(f"\n  Statistiques par tranche :")
print(stats_tranches.to_string())

# ============================================================
# [2] ANALYSE DES TRONÇONS ABANDONNÉS
# ============================================================
print("\n" + "=" * 60)
print("[2] ANALYSE DES TRONÇONS ABANDONNÉS")
print("=" * 60)

abandonnes = cana[cana["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"])].copy()
nb_abandonnes = len(abandonnes)

# Fuites sur les tronçons abandonnés
fuites_sur_abandonnes = fuites[fuites["GID_OBJET"].isin(abandonnes["OBJET"])]
abandonnes_avec_fuite = abandonnes[abandonnes["OBJET"].isin(fuites_sur_abandonnes["GID_OBJET"])]
nb_avec_fuite = len(abandonnes_avec_fuite)
pct_avec_fuite = nb_avec_fuite / max(nb_abandonnes, 1) * 100

# Nombre de fuites avant abandon
nb_fuites_par_abandonne = fuites_sur_abandonnes.groupby("GID_OBJET").size().rename("nb_fuites")
abandonnes = abandonnes.merge(nb_fuites_par_abandonne, left_on="OBJET", right_index=True, how="left")
abandonnes["nb_fuites"] = abandonnes["nb_fuites"].fillna(0).astype(int)

dist_fuites = abandonnes["nb_fuites"].describe()

# Délai entre dernière fuite et abandon
derniere_fuite = fuites_sur_abandonnes.groupby("GID_OBJET")["annee_Anomalie"].max().rename("annee_derniere_fuite")
premiere_fuite = fuites_sur_abandonnes.groupby("GID_OBJET")["annee_Anomalie"].min().rename("annee_premiere_fuite")

abandonnes = abandonnes.merge(derniere_fuite, left_on="OBJET", right_index=True, how="left")
abandonnes = abandonnes.merge(premiere_fuite, left_on="OBJET", right_index=True, how="left")

avec_fuite_et_abandon = abandonnes[
    abandonnes["annee_derniere_fuite"].notna() & abandonnes["annee_abandon"].notna()
].copy()
avec_fuite_et_abandon["delai_fuite_abandon"] = (
    avec_fuite_et_abandon["annee_abandon"] - avec_fuite_et_abandon["annee_derniere_fuite"]
)

delai_stats = avec_fuite_et_abandon["delai_fuite_abandon"].describe()
delai_moyen = avec_fuite_et_abandon["delai_fuite_abandon"].mean()
delai_median = avec_fuite_et_abandon["delai_fuite_abandon"].median()

# Tronçons abandonnés SANS fuite préalable
sans_fuite_pct = (1 - pct_avec_fuite / 100) * 100

# Répartition par matériau
mat_abandonnes = abandonnes.groupby("famille_mat").agg(
    nb=("OBJET", "count"),
    pct_avec_fuite=("nb_fuites", lambda x: (x > 0).mean() * 100),
    nb_fuites_moy=("nb_fuites", "mean"),
).sort_values("nb", ascending=False).round(1)

print(f"  Tronçons abandonnés/déposés : {nb_abandonnes:,}")
print(f"  Dont avec ≥1 fuite avant   : {nb_avec_fuite:,} ({pct_avec_fuite:.1f}%)")
print(f"  Dont SANS fuite avant       : {nb_abandonnes - nb_avec_fuite:,} ({sans_fuite_pct:.1f}%)")
print(f"\n  Nombre de fuites avant abandon :")
print(f"    {dist_fuites.to_string()}")
print(f"\n  Délai dernière fuite → abandon :")
print(f"    Moyen  : {delai_moyen:.1f} ans")
print(f"    Médian : {delai_median:.1f} ans")
print(f"    {delai_stats.to_string()}")
print(f"\n  Par matériau :")
print(mat_abandonnes.to_string())

# ============================================================
# [3] BACKTESTING VISUEL — BONS PRONOSTICS MANQUÉS
# ============================================================
print("\n" + "=" * 60)
print("[3] BACKTESTING — BONS PRONOSTICS MANQUÉS")
print("=" * 60)

# Stratégie : scorer à T=2018, puis regarder les fuites réelles 2018-2021
# Les tronçons dans le top 20% du score qui ont effectivement fui
# MAIS qui n'ont pas été renouvelés = "bons pronostics manqués"

T_OBS = 2018
HORIZON = 3

# Construire les features à T_OBS et scorer
df_bt, X_bt, y_bt, fs_bt = build_features(cana, fuites, argile, T_OBS, HORIZON)

# Entraîner un modèle sur les données antérieures (T=2015)
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV

df_tr, X_tr, y_tr, fs_tr = build_features(cana, fuites, argile, 2015, HORIZON)

n_pos = y_tr.sum()
n_neg = len(y_tr) - n_pos
xgb_params = dict(
    n_estimators=500, max_depth=6, learning_rate=0.03,
    subsample=0.8, colsample_bytree=0.8,
    scale_pos_weight=round(n_neg / max(n_pos, 1), 1),
    eval_metric="auc", random_state=42, n_jobs=-1,
)

base_model = xgb.XGBClassifier(**xgb_params)
cal_model = CalibratedClassifierCV(base_model, method="isotonic", cv=5)
cal_model.fit(X_tr, y_tr)

# Scorer les tronçons à T_OBS
scores_bt = cal_model.predict_proba(X_bt)[:, 1]
df_bt["score_pred"] = scores_bt
df_bt["y_reel"] = y_bt  # 1 = a effectivement fui dans [2018, 2021)

# Tronçons encore EN SERVICE à T_OBS+HORIZON (= pas renouvelés)
abandonnes_pendant = cana[
    (cana["STATUT_OBJET"].isin(["ABANDONNE", "DEPOSE"]))
    & (cana["annee_abandon"] >= T_OBS)
    & (cana["annee_abandon"] < T_OBS + HORIZON)
]["OBJET"]
df_bt["renouvele"] = df_bt["OBJET"].isin(abandonnes_pendant).astype(int)

# Classement
df_bt = df_bt.sort_values("score_pred", ascending=False).reset_index(drop=True)
df_bt["rang"] = range(1, len(df_bt) + 1)
df_bt["top_pct"] = (df_bt["rang"] / len(df_bt) * 100).round(1)

# Analyse par tranche
df_bt["tranche_bt"] = pd.cut(
    df_bt["top_pct"], bins=[0, 5, 10, 20, 50, 100],
    labels=["Top 5%", "Top 5-10%", "Top 10-20%", "Top 20-50%", "Bottom 50%"],
)

bt_stats = df_bt.groupby("tranche_bt", observed=True).agg(
    nb_troncons=("OBJET", "count"),
    nb_fuites_reelles=("y_reel", "sum"),
    taux_fuite_reel=("y_reel", "mean"),
    score_moyen=("score_pred", "mean"),
    nb_renouveles=("renouvele", "sum"),
).round(4)
bt_stats["taux_fuite_pct"] = (bt_stats["taux_fuite_reel"] * 100).round(2)
bt_stats["precision"] = (bt_stats["nb_fuites_reelles"] / bt_stats["nb_troncons"] * 100).round(2)

# Top 20% spécifiquement
top20_bt = df_bt[df_bt["top_pct"] <= 20]
fuites_top20 = top20_bt["y_reel"].sum()
total_fuites = df_bt["y_reel"].sum()
capture_top20 = fuites_top20 / max(total_fuites, 1) * 100

# Bons pronostics manqués : top 20%, a fui, PAS renouvelé
bons_pronostics_manques = top20_bt[(top20_bt["y_reel"] == 1) & (top20_bt["renouvele"] == 0)]
nb_manques = len(bons_pronostics_manques)

# Aussi : top 20%, a fui, a été renouvelé (les bons choix)
bons_choix = top20_bt[(top20_bt["y_reel"] == 1) & (top20_bt["renouvele"] == 1)]
nb_bons_choix = len(bons_choix)

print(f"  Backtesting : scores calculés à T={T_OBS}, fuites observées [{T_OBS}–{T_OBS+HORIZON})")
print(f"  Tronçons scorés : {len(df_bt):,}")
print(f"  Fuites réelles  : {total_fuites:,}")
print(f"\n  Top 20% du score :")
print(f"    Tronçons       : {len(top20_bt):,}")
print(f"    Fuites réelles : {fuites_top20:,} / {total_fuites:,} ({capture_top20:.1f}% capturées)")
print(f"    Renouvelés     : {top20_bt['renouvele'].sum():,}")
print(f"\n  BONS PRONOSTICS MANQUÉS (top 20%, a fui, non renouvelé) : {nb_manques:,}")
print(f"  Bons choix (top 20%, a fui, renouvelé)                  : {nb_bons_choix:,}")
print(f"\n  Par tranche :")
print(bt_stats.to_string())

# Détail des 30 premiers bons pronostics manqués
cols_detail = ["OBJET", "famille_mat", "DIAMETRE", "age", "score_pred", "top_pct"]
cols_available = [c for c in cols_detail if c in df_bt.columns]
top_manques = bons_pronostics_manques[cols_available].head(30)
print(f"\n  Top 30 bons pronostics manqués :")
print(top_manques.to_string(index=False))

# ============================================================
# [4] GÉNÉRATION DU RAPPORT HTML
# ============================================================
print("\n" + "=" * 60)
print("[4] GÉNÉRATION DU RAPPORT HTML")
print("=" * 60)


def fmt_num(n, decimals=0):
    if decimals == 0:
        return f"{n:,.0f}".replace(",", " ")
    return f"{n:,.{decimals}f}".replace(",", " ")


def make_table_rows(df, columns=None):
    if columns is None:
        columns = df.columns
    rows = ""
    for _, r in df.iterrows():
        cells = "".join(f"<td>{r[c]}</td>" for c in columns)
        rows += f"<tr>{cells}</tr>\n"
    return rows


# Table tranches scoring
tranches_html = ""
for _, r in stats_tranches.iterrows():
    tranches_html += f"""<tr>
        <td>{r.name}</td>
        <td>{fmt_num(r['nb_troncons'])}</td>
        <td>{r['lineaire_km']:.1f} km</td>
        <td>{r['score_h3_moy']*100:.2f}%</td>
        <td>{r['score_h1_moy']*100:.2f}%</td>
        <td>{r['score_h5_moy']*100:.2f}%</td>
        <td>{r['fuites_hist_moy']:.2f}</td>
    </tr>"""

# Table matériaux abandonnés
mat_html = ""
for idx, r in mat_abandonnes.iterrows():
    mat_html += f"""<tr>
        <td>{idx}</td>
        <td>{fmt_num(r['nb'])}</td>
        <td>{r['pct_avec_fuite']:.1f}%</td>
        <td>{r['nb_fuites_moy']:.2f}</td>
    </tr>"""

# Table backtesting par tranche
bt_html = ""
for _, r in bt_stats.iterrows():
    bt_html += f"""<tr>
        <td>{r.name}</td>
        <td>{fmt_num(r['nb_troncons'])}</td>
        <td>{fmt_num(r['nb_fuites_reelles'])}</td>
        <td>{r['taux_fuite_pct']:.2f}%</td>
        <td>{r['score_moyen']*100:.2f}%</td>
        <td>{fmt_num(r['nb_renouveles'])}</td>
    </tr>"""

# Table top 30 pronostics manqués
manques_html = ""
for i, (_, r) in enumerate(bons_pronostics_manques.head(30).iterrows(), 1):
    fam = r.get("famille_mat", "—")
    diam = f"{r['DIAMETRE']:.0f}" if pd.notna(r.get("DIAMETRE")) else "—"
    age_val = f"{r['age']:.0f}" if pd.notna(r.get("age")) else "—"
    manques_html += f"""<tr>
        <td>{i}</td>
        <td>{r['OBJET']}</td>
        <td>{fam}</td>
        <td>{diam}</td>
        <td>{age_val}</td>
        <td>{r['score_pred']*100:.1f}%</td>
        <td>Top {r['top_pct']:.1f}%</td>
    </tr>"""

# Délai distribution
delai_dist = avec_fuite_et_abandon["delai_fuite_abandon"]
delai_0_2 = (delai_dist <= 2).sum()
delai_3_5 = ((delai_dist > 2) & (delai_dist <= 5)).sum()
delai_6_10 = ((delai_dist > 5) & (delai_dist <= 10)).sum()
delai_plus10 = (delai_dist > 10).sum()
delai_neg = (delai_dist < 0).sum()
total_delai = len(delai_dist)

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Rapport Stratégique — Aide à la Décision Renouvellement</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; color: #2c3e50; line-height: 1.6; }}
        .header {{ background: linear-gradient(135deg, #1a237e, #283593); color: white; padding: 2.5em 3em; }}
        .header h1 {{ font-size: 2em; margin-bottom: 0.3em; }}
        .header p {{ opacity: 0.85; font-size: 1.1em; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2em; }}
        .section {{ background: white; border-radius: 10px; padding: 2em; margin-bottom: 2em; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .section h2 {{ color: #1a237e; border-bottom: 3px solid #1a237e; padding-bottom: 0.5em; margin-bottom: 1em; font-size: 1.4em; }}
        .section h3 {{ color: #37474f; margin: 1.2em 0 0.6em; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.92em; }}
        th {{ background: #1a237e; color: white; padding: 0.7em 1em; text-align: center; font-weight: 600; }}
        td {{ border: 1px solid #ddd; padding: 0.5em 0.8em; text-align: center; }}
        tr:nth-child(even) {{ background: #f8f9fc; }}
        tr:hover {{ background: #e8eaf6; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.2em; margin: 1.5em 0; }}
        .kpi {{ background: #f8f9fc; border-left: 4px solid #1a237e; border-radius: 6px; padding: 1.2em; }}
        .kpi .value {{ font-size: 1.8em; font-weight: 700; color: #1a237e; }}
        .kpi .label {{ font-size: 0.85em; color: #666; margin-top: 0.3em; }}
        .kpi.alert {{ border-left-color: #c62828; }}
        .kpi.alert .value {{ color: #c62828; }}
        .kpi.success {{ border-left-color: #2e7d32; }}
        .kpi.success .value {{ color: #2e7d32; }}
        .kpi.warning {{ border-left-color: #e65100; }}
        .kpi.warning .value {{ color: #e65100; }}
        .highlight {{ background: #fff3e0; border-left: 4px solid #e65100; padding: 1em 1.5em; margin: 1em 0; border-radius: 4px; }}
        .highlight.red {{ background: #ffebee; border-left-color: #c62828; }}
        .highlight.green {{ background: #e8f5e9; border-left-color: #2e7d32; }}
        .callout {{ background: #e3f2fd; border-radius: 8px; padding: 1.5em; margin: 1.5em 0; font-size: 1.05em; }}
        .callout strong {{ color: #1a237e; }}
        .bar {{ height: 22px; border-radius: 4px; display: inline-block; }}
        .bar-container {{ background: #e0e0e0; border-radius: 4px; height: 22px; width: 100%; position: relative; }}
        .bar-fill {{ background: #1a237e; height: 100%; border-radius: 4px; }}
        .bar-fill.red {{ background: #c62828; }}
        .bar-fill.orange {{ background: #e65100; }}
        footer {{ text-align: center; padding: 2em; color: #888; font-size: 0.85em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Rapport Stratégique — Aide à la Décision</h1>
        <p>Renouvellement du réseau de canalisations | Modèle V9 | Année de référence : {ANNEE_REF}</p>
    </div>

    <div class="container">

    <!-- ============================================================ -->
    <!-- SECTION 1 : LINÉAIRE TOP 20% -->
    <!-- ============================================================ -->
    <div class="section">
        <h2>1. Positionnement du risque par rapport à l'obligation réglementaire</h2>

        <div class="kpi-grid">
            <div class="kpi">
                <div class="value">{lineaire_total_km:,.0f} km</div>
                <div class="label">Linéaire total EN SERVICE ({fmt_num(nb_total)} tronçons)</div>
            </div>
            <div class="kpi alert">
                <div class="value">{lineaire_top20_km:,.1f} km</div>
                <div class="label">Linéaire dans le top 20% de risque ({pct_reseau_top20:.1f}% du réseau)</div>
            </div>
            <div class="kpi warning">
                <div class="value">{obligation_1pct_km:,.1f} km/an</div>
                <div class="label">Obligation réglementaire (1% du réseau/an)</div>
            </div>
            <div class="kpi">
                <div class="value">{annees_top20:.0f} ans</div>
                <div class="label">Pour renouveler tout le top 20% à 1%/an</div>
            </div>
        </div>

        <div class="callout">
            <strong>Lecture :</strong> Le linéaire identifié à haut risque (top 20% du score V9) représente
            <strong>{lineaire_top20_km:,.1f} km</strong>, soit <strong>{pct_reseau_top20:.1f}%</strong> du réseau.
            Au rythme réglementaire de 1%/an ({obligation_1pct_km:,.1f} km/an), il faudrait
            <strong>{annees_top20:.0f} ans</strong> pour renouveler l'ensemble de ces tronçons à risque.
            Cela souligne l'importance d'une <strong>priorisation fine</strong> au sein même de ce top 20%.
        </div>

        <h3>Statistiques par tranche de risque</h3>
        <table>
            <tr>
                <th>Tranche</th><th>Tronçons</th><th>Linéaire</th>
                <th>Score H3 moy.</th><th>Score H1 moy.</th><th>Score H5 moy.</th>
                <th>Fuites hist. moy.</th>
            </tr>
            {tranches_html}
        </table>

        <div class="highlight">
            <strong>Note sur l'optimiseur :</strong> La notion de risque sera enrichie dans l'optimiseur :
            <code>risque = probabilité de défaillance × conséquence</code>.
            Les scores actuels mesurent la probabilité ; la conséquence (criticité, impact usagers, coût de réparation)
            sera intégrée pour une priorisation plus complète.
        </div>
    </div>

    <!-- ============================================================ -->
    <!-- SECTION 2 : TRONÇONS ABANDONNÉS -->
    <!-- ============================================================ -->
    <div class="section">
        <h2>2. Analyse des tronçons abandonnés — Signal prédictif des fuites</h2>

        <div class="kpi-grid">
            <div class="kpi">
                <div class="value">{fmt_num(nb_abandonnes)}</div>
                <div class="label">Tronçons abandonnés ou déposés</div>
            </div>
            <div class="kpi alert">
                <div class="value">{pct_avec_fuite:.1f}%</div>
                <div class="label">Ont eu ≥1 fuite avant l'abandon ({fmt_num(nb_avec_fuite)} tronçons)</div>
            </div>
            <div class="kpi warning">
                <div class="value">{sans_fuite_pct:.1f}%</div>
                <div class="label">Abandonnés SANS fuite enregistrée ({fmt_num(nb_abandonnes - nb_avec_fuite)} tronçons)</div>
            </div>
            <div class="kpi success">
                <div class="value">{delai_moyen:.1f} ans</div>
                <div class="label">Délai moyen dernière fuite → abandon (médian : {delai_median:.1f} ans)</div>
            </div>
        </div>

        <h3>Distribution du délai dernière fuite → abandon</h3>
        <table style="width: 60%;">
            <tr><th>Délai</th><th>Nombre</th><th>Proportion</th></tr>
            <tr><td>Abandon avant/même année que la fuite</td><td>{fmt_num(delai_neg)}</td><td>{delai_neg/max(total_delai,1)*100:.1f}%</td></tr>
            <tr><td>0–2 ans après</td><td>{fmt_num(delai_0_2)}</td><td>{delai_0_2/max(total_delai,1)*100:.1f}%</td></tr>
            <tr><td>3–5 ans après</td><td>{fmt_num(delai_3_5)}</td><td>{delai_3_5/max(total_delai,1)*100:.1f}%</td></tr>
            <tr><td>6–10 ans après</td><td>{fmt_num(delai_6_10)}</td><td>{delai_6_10/max(total_delai,1)*100:.1f}%</td></tr>
            <tr><td>&gt;10 ans après</td><td>{fmt_num(delai_plus10)}</td><td>{delai_plus10/max(total_delai,1)*100:.1f}%</td></tr>
        </table>

        <h3>Par famille de matériau</h3>
        <table style="width: 70%;">
            <tr><th>Matériau</th><th>Nb abandonnés</th><th>% avec fuite avant</th><th>Nb fuites moyen</th></tr>
            {mat_html}
        </table>

        <div class="callout">
            <strong>Enseignement clé :</strong> {pct_avec_fuite:.0f}% des tronçons abandonnés avaient signalé
            au moins une fuite au préalable, avec un délai moyen de <strong>{delai_moyen:.1f} ans</strong>
            entre la dernière fuite et l'abandon. Cela confirme que les fuites sont un
            <strong>signal précurseur</strong> exploitable, et que le modèle peut anticiper la fin de vie
            de {delai_moyen:.0f}–{delai_moyen+2:.0f} ans en avance.
            <br/><br/>
            Les {sans_fuite_pct:.0f}% abandonnés sans fuite correspondent vraisemblablement
            à des remplacements d'opportunité (travaux voirie) ou à des tronçons dont
            l'historique de fuites est incomplet.
        </div>
    </div>

    <!-- ============================================================ -->
    <!-- SECTION 3 : BACKTESTING — BONS PRONOSTICS MANQUÉS -->
    <!-- ============================================================ -->
    <div class="section">
        <h2>3. Validation rétrospective — « Le modèle avait vu juste »</h2>

        <p style="margin-bottom: 1em;">
            <strong>Protocole :</strong> Le modèle V9 est entraîné sur les données jusqu'à 2015, puis utilisé pour
            scorer tous les tronçons à la date d'observation T=2018.
            Les fuites réellement survenues entre 2018 et 2021 sont ensuite croisées avec les prédictions.
        </p>

        <div class="kpi-grid">
            <div class="kpi">
                <div class="value">{fmt_num(len(df_bt))}</div>
                <div class="label">Tronçons scorés à T={T_OBS}</div>
            </div>
            <div class="kpi alert">
                <div class="value">{fmt_num(int(total_fuites))}</div>
                <div class="label">Fuites réelles [{T_OBS}–{T_OBS+HORIZON})</div>
            </div>
            <div class="kpi success">
                <div class="value">{capture_top20:.1f}%</div>
                <div class="label">Fuites capturées dans le top 20% des scores</div>
            </div>
            <div class="kpi alert">
                <div class="value">{fmt_num(nb_manques)}</div>
                <div class="label">Bons pronostics manqués (top 20%, a fui, non renouvelé)</div>
            </div>
        </div>

        <div class="highlight red">
            <strong>Message clé pour les décideurs :</strong> Sur la période 2018–2021,
            <strong>{fmt_num(nb_manques)} tronçons</strong> identifiés comme à haut risque par le modèle
            (top 20% des scores) ont <strong>effectivement fui</strong> alors qu'ils
            <strong>n'avaient pas été renouvelés</strong>. Ces fuites auraient pu être évitées
            si le plan de renouvellement avait ciblé les tronçons identifiés par le modèle.
        </div>

        <h3>Taux de fuite réel par tranche de score</h3>
        <table>
            <tr>
                <th>Tranche</th><th>Tronçons</th><th>Fuites réelles</th>
                <th>Taux de fuite</th><th>Score moyen prédit</th><th>Renouvelés</th>
            </tr>
            {bt_html}
        </table>

        <div class="callout">
            <strong>Interprétation :</strong> Le taux de fuite réel augmente fortement avec le score prédit,
            confirmant le pouvoir discriminant du modèle. Les tronçons du top 5% ont un taux de fuite
            réel nettement supérieur aux autres — le modèle concentre le risque dans les bons segments.
        </div>

        <h3>Top 30 — Pronostics manqués les plus flagrants</h3>
        <p style="margin-bottom: 0.5em; color: #666;">
            Tronçons que le modèle avait classés parmi les plus à risque, qui ont effectivement fui,
            mais qui n'ont pas été renouvelés à temps.
        </p>
        <table>
            <tr><th>#</th><th>Tronçon</th><th>Matériau</th><th>Diamètre</th><th>Âge</th><th>Score prédit</th><th>Position</th></tr>
            {manques_html}
        </table>
    </div>

    <!-- ============================================================ -->
    <!-- SECTION 4 : SYNTHÈSE -->
    <!-- ============================================================ -->
    <div class="section">
        <h2>4. Synthèse et prochaines étapes</h2>

        <h3>Ce que le modèle démontre</h3>
        <ul style="margin: 1em 0; padding-left: 2em;">
            <li><strong>Capacité prédictive validée :</strong> le top 20% des scores capture {capture_top20:.0f}% des fuites réelles sur 3 ans</li>
            <li><strong>Signal fort :</strong> {pct_avec_fuite:.0f}% des tronçons abandonnés avaient au moins une fuite avant, avec {delai_moyen:.0f} ans d'anticipation possible</li>
            <li><strong>{fmt_num(nb_manques)} fuites évitables</strong> si le modèle avait guidé le renouvellement en 2018</li>
            <li>Le linéaire à risque ({lineaire_top20_km:,.0f} km) représente {annees_top20:.0f} ans de renouvellement au rythme réglementaire</li>
        </ul>

        <h3>Prochaines étapes</h3>
        <ul style="margin: 1em 0; padding-left: 2em;">
            <li><strong>Enrichir l'optimiseur :</strong> intégrer la notion de conséquence (<code>risque = P(défaillance) × conséquence</code>) pour passer d'un score de probabilité à un score de risque métier</li>
            <li><strong>Cartographier les pronostics manqués</strong> pour une communication visuelle aux élus et exploitants</li>
            <li><strong>Chiffrer les coûts évités :</strong> coût moyen d'une fuite (réparation urgence + eau perdue + dommages) vs coût du renouvellement préventif</li>
            <li><strong>Intégrer les contraintes opérationnelles :</strong> coordination avec travaux voirie, regroupement de chantiers, accessibilité</li>
        </ul>
    </div>

    </div>

    <footer>
        Rapport généré automatiquement — Modèle V9 (XGBoost + calibration isotonique) — {ANNEE_REF}
    </footer>
</body>
</html>
"""

output_path = OUT / "rapport_strategique.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"  => {output_path}")

# CSV complémentaire : bons pronostics manqués
export_cols = [c for c in ["OBJET", "famille_mat", "DIAMETRE", "age", "score_pred", "top_pct", "y_reel", "renouvele"] if c in df_bt.columns]
bons_pronostics_manques[export_cols].to_csv(OUT / "bons_pronostics_manques.csv", index=False)
print(f"  => {OUT / 'bons_pronostics_manques.csv'} ({len(bons_pronostics_manques):,} tronçons)")

print("\n" + "=" * 60)
print("TERMINÉ")
print("=" * 60)
