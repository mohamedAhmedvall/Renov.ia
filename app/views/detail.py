"""Vue détail tronçon — fiche complète d'un tronçon avec diagnostic."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _normalize_id(value) -> str:
    """Normalise un ID tronçon pour comparaison robuste (gère NaN→float→'.0')."""
    if value is None:
        return ""
    s = str(value).strip()
    # pandas peut promouvoir int en float si la colonne contient des NaN → "1234.0"
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _get_troncon_data(df_scoring, troncon_id, config):
    """Récupère la ligne du tronçon dans le scoring (matching robuste)."""
    col_id = config["column_mapping"]["id_troncon"]
    target = _normalize_id(troncon_id)
    if not target:
        return None
    ids_normalized = df_scoring[col_id].map(_normalize_id)
    mask = ids_normalized == target
    if mask.sum() == 0:
        return None
    return df_scoring[mask].iloc[0]


# ────────────────────────────────────────────────────────
# En-tête : diagnostic visuel
# ────────────────────────────────────────────────────────

def _render_diagnostic(row, config, horizon):
    """Bandeau diagnostic coloré + KPIs clés."""
    labels = config["risk_labels"]
    colors = config["risk_colors"]
    score = row.get(f"score_h{horizon}", 0)
    classe = row.get(f"classe_h{horizon}", "faible")
    color = colors.get(classe, "#999")
    label = labels.get(classe, classe)

    # Bandeau coloré
    st.markdown(
        f'<div style="background-color:{color}; color:white; padding:12px 20px; '
        f'border-radius:8px; font-size:18px; font-weight:bold;">'
        f'Diagnostic : {label} — Score {score * 100:.1f} %'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("")

    # Messages d'aide à la décision
    if classe == "critique":
        st.error("Ce tronçon présente un risque très élevé de défaillance. **Renouvellement à planifier en priorité.**")
    elif classe == "eleve":
        st.warning("Ce tronçon est à surveiller de près. **À inclure dans le prochain programme de renouvellement.**")
    elif classe == "modere":
        st.info("Risque modéré. Surveillance normale, pas d'action immédiate requise.")
    else:
        st.success("Ce tronçon est en bon état. Aucune intervention nécessaire à court terme.")


# ────────────────────────────────────────────────────────
# Fiche d'identité
# ────────────────────────────────────────────────────────

def _render_fiche_identite(row, config):
    """Fiche d'identité du tronçon."""
    st.subheader("Fiche d'identité")

    materiau = row.get("MATERIAU", row.get("famille_mat", "—"))
    diametre = row.get("DIAMETRE", None)
    age = row.get("age", None)
    longueur = row.get("LONGUEUR", None)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matériau", str(materiau))
    c2.metric("Diamètre", f"{int(diametre)} mm" if pd.notna(diametre) else "—")
    c3.metric("Âge", f"{int(age)} ans" if pd.notna(age) else "—")

    if longueur is not None and pd.notna(longueur):
        try:
            long_val = float(str(longueur).replace(",", "."))
            c4.metric("Longueur", f"{long_val:.0f} m")
        except (ValueError, TypeError):
            c4.metric("Longueur", "—")
    else:
        c4.metric("Longueur", "—")


# ────────────────────────────────────────────────────────
# Évolution du risque sur les 3 horizons
# ────────────────────────────────────────────────────────

def _render_evolution_risque(row, config):
    """Graphique évolution du score sur les 3 horizons + jauge."""
    st.subheader("Évolution du risque dans le temps")

    labels_risk = config["risk_labels"]
    colors = config["risk_colors"]
    # Compat V9 : on utilise risk_quantiles si dispo, sinon fallback risk_thresholds
    if "risk_thresholds" in config:
        thresholds = config["risk_thresholds"]
    else:
        # Seuils dérivés du max observé sur les 3 horizons (proba calibrée)
        all_scores = [row.get(f"score_h{h}", 0) or 0 for h in (1, 3, 5)]
        smax = max(max(all_scores) * 1.5, 0.05)
        thresholds = {"modere": smax * 0.3, "eleve": smax * 0.6, "critique": smax * 0.85}

    horizons = [1, 3, 5]
    scores = [row.get(f"score_h{h}", 0) for h in horizons]
    classes = [row.get(f"classe_h{h}", "faible") for h in horizons]

    # Taux de base réseau (moyenne du scoring)
    df_full = st.session_state.get("_df_scoring_full_ref")
    base_rates = {}
    if df_full is not None:
        for h in horizons:
            sc = f"score_h{h}"
            if sc in df_full.columns:
                base_rates[h] = float(pd.to_numeric(df_full[sc], errors="coerce").mean()) or 1e-6

    # Cards : proba + multiple par rapport au réseau
    cols = st.columns(3)
    for col_st, h, s, c in zip(cols, horizons, scores, classes):
        mult = (s / base_rates[h]) if h in base_rates and base_rates[h] > 0 else None
        delta_txt = f"{labels_risk.get(c, c)}"
        if mult is not None:
            delta_txt += f" • ×{mult:.1f} la moyenne"
        col_st.metric(
            f"À {h} an{'s' if h > 1 else ''}",
            f"{s * 100:.2f} %",
            delta=delta_txt,
            delta_color="off",
        )

    # Graphique barres avec zones colorées
    fig = go.Figure()

    # Échelle Y adaptative (scores V9 calibrés ⇒ valeurs typiquement faibles)
    y_max = max(max(s * 100 for s in scores), thresholds["critique"] * 100) * 1.25
    y_max = max(y_max, 0.5)

    # Zones de seuils en fond
    fig.add_hrect(y0=0, y1=thresholds["modere"] * 100, fillcolor=colors["faible"], opacity=0.15, line_width=0)
    fig.add_hrect(y0=thresholds["modere"] * 100, y1=thresholds["eleve"] * 100, fillcolor=colors["modere"], opacity=0.15, line_width=0)
    fig.add_hrect(y0=thresholds["eleve"] * 100, y1=thresholds["critique"] * 100, fillcolor=colors["eleve"], opacity=0.15, line_width=0)
    fig.add_hrect(y0=thresholds["critique"] * 100, y1=y_max, fillcolor=colors["critique"], opacity=0.15, line_width=0)

    fig.add_trace(go.Bar(
        x=[f"{h} an{'s' if h > 1 else ''}" for h in horizons],
        y=[s * 100 for s in scores],
        marker_color=[colors.get(c, "#999") for c in classes],
        text=[f"{s * 100:.2f} %" for s in scores],
        textposition="outside",
        width=0.5,
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=10, b=20),
        yaxis=dict(range=[0, y_max], title="Probabilité de fuite (%)"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tendance
    if scores[2] > scores[0] * 1.2:
        st.warning("Le risque **augmente significativement** avec le temps. Action préventive recommandée.")
    elif scores[2] < scores[0] * 0.8:
        st.info("Le risque est **stable ou en diminution** sur les horizons prédits.")


# ────────────────────────────────────────────────────────
# Facteurs de risque (SHAP local)
# ────────────────────────────────────────────────────────

def _compute_local_shap(row, df_shap, df_scoring_full, config):
    """Calcule une approximation SHAP locale par z-score pondéré."""
    feature_mapping = {
        "Age": ("age", "ans"),
        "Longueur": ("LONGUEUR", "m"),
        "Famille_materiau": ("famille_mat", ""),
        "Diametre": ("DIAMETRE", "mm"),
        "Nb_fuites_historique": ("nb_fuites", ""),
    }

    # Noms métier pour les features
    feature_labels = {
        "Age": "Âge de la canalisation",
        "Longueur": "Longueur du tronçon",
        "Famille_materiau": "Type de matériau",
        "Diametre": "Diamètre",
        "Nb_fuites_historique": "Fuites passées",
    }

    results = []
    for _, shap_row in df_shap.iterrows():
        feat = shap_row["feature"]
        global_imp = shap_row["mean_abs_shap"]

        col_name = None
        unit = ""
        label = feat
        for key, (col, u) in feature_mapping.items():
            if key.lower() in feat.lower():
                col_name = col
                unit = u
                label = feature_labels.get(key, feat)
                break

        troncon_val = None
        local_shap = global_imp
        direction = 1

        if col_name and col_name in row.index and col_name in df_scoring_full.columns:
            v = row[col_name]
            if pd.notna(v) and np.issubdtype(type(v), np.number):
                col_data = pd.to_numeric(df_scoring_full[col_name], errors="coerce")
                mean_val = col_data.mean()
                std_val = col_data.std()
                if std_val > 0:
                    z = (v - mean_val) / std_val
                    local_shap = global_imp * min(abs(z), 3) / 1.5
                    direction = 1 if z > 0 else -1
                troncon_val = v
        elif col_name and col_name in row.index:
            troncon_val = row[col_name]

        results.append({
            "label": label,
            "local_shap": local_shap * direction,
            "abs_shap": abs(local_shap),
            "troncon_val": troncon_val,
            "unit": unit,
        })

    results.sort(key=lambda r: r["abs_shap"], reverse=True)
    return results


def _render_facteurs_risque(row, df_shap, config, df_scoring_full=None):
    """Barres facteurs de risque avec langage clair."""
    st.subheader("Pourquoi ce niveau de risque ?")

    if df_shap is None or df_shap.empty:
        st.info("Données d'explicabilité non disponibles.")
        return
    if df_scoring_full is None:
        st.info("Données de scoring complètes non disponibles.")
        return

    local_shap = _compute_local_shap(row, df_shap, df_scoring_full, config)

    bar_labels = []
    bar_values = []
    bar_colors = []

    for item in local_shap:
        label = item["label"]
        val = item["local_shap"]
        troncon_val = item["troncon_val"]
        unit = item["unit"]

        # Valeur du tronçon entre parenthèses
        if troncon_val is not None and pd.notna(troncon_val):
            if unit and isinstance(troncon_val, (int, float)):
                try:
                    label += f" ({float(str(troncon_val).replace(',', '.')):.0f} {unit})"
                except (ValueError, TypeError):
                    label += f" ({troncon_val})"
            else:
                label += f" ({troncon_val})"

        if val >= 0:
            bar_colors.append("#d32f2f")
        else:
            bar_colors.append("#4caf50")

        bar_labels.append(label)
        bar_values.append(val)

    fig = go.Figure(go.Bar(
        x=bar_values,
        y=bar_labels,
        orientation="h",
        marker_color=bar_colors,
        hovertemplate="%{y}<br>Impact : %{x:+.3f}<extra></extra>",
    ))
    fig.update_layout(
        height=max(220, len(bar_labels) * 55),
        margin=dict(l=0, r=20, t=10, b=10),
        xaxis_title="Impact sur le score",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "**Rouge** = fait augmenter le risque de ce tronçon &nbsp; | &nbsp; "
        "**Vert** = fait diminuer le risque par rapport à la moyenne du réseau"
    )


# ────────────────────────────────────────────────────────
# Fiabilité des données
# ────────────────────────────────────────────────────────

def _render_fiabilite(row):
    """Indicateur ICP avec explication."""
    st.subheader("Fiabilité de la prédiction")
    icp = row.get("icp", 0)

    if icp >= 80:
        st.success(
            f"**Données fiables** (complétude : {icp:.0f} %) — "
            f"Les caractéristiques de ce tronçon sont bien renseignées. Le score est fiable."
        )
    elif icp >= 50:
        st.warning(
            f"**Données partielles** (complétude : {icp:.0f} %) — "
            f"Certaines caractéristiques sont manquantes ou estimées. Le score doit être interprété avec prudence."
        )
    else:
        st.error(
            f"**Données insuffisantes** (complétude : {icp:.0f} %) — "
            f"Trop de caractéristiques manquantes. Le score est peu fiable, une vérification terrain est recommandée."
        )


# ────────────────────────────────────────────────────────
# Render principal
# ────────────────────────────────────────────────────────

def render(df_scoring: pd.DataFrame, df_referentiel: pd.DataFrame, config: dict, **kwargs):
    """Point d'entrée de la vue Détail."""
    df_shap = kwargs.get("df_shap")
    df_scoring_full = kwargs.get("df_scoring_full", df_scoring)
    # Mémoriser pour _render_evolution_risque (calcul du taux de base réseau)
    st.session_state["_df_scoring_full_ref"] = df_scoring_full
    troncon_id = st.session_state.get("troncon_selectionne")

    if troncon_id is None:
        st.info("Sélectionnez un tronçon depuis la vue Détails par tronçons ou la Carte du réseau pour voir sa fiche détaillée.")
        return

    # Bouton retour
    if st.button("← Retour à la vue Détails par tronçons"):
        st.session_state.vue_active = "Détails par tronçons"
        st.session_state.troncon_selectionne = None
        st.rerun()

    row = _get_troncon_data(df_scoring_full, troncon_id, config)
    if row is None:
        st.error(f"Tronçon {troncon_id} introuvable dans les données.")
        return

    horizon = st.session_state.get("horizon", 3)

    st.title(f"Fiche tronçon — {troncon_id}")

    # Diagnostic (bandeau coloré)
    _render_diagnostic(row, config, horizon)
    st.divider()

    # Fiche d'identité + Évolution côte à côte
    col_left, col_right = st.columns([1, 2])
    with col_left:
        _render_fiche_identite(row, config)
    with col_right:
        _render_evolution_risque(row, config)

    st.divider()

    # Facteurs de risque
    _render_facteurs_risque(row, df_shap, config, df_scoring_full=df_scoring_full)
    st.divider()

    # Fiabilité
    _render_fiabilite(row)
