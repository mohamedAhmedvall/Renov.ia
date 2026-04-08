"""Vue dashboard — tableau de bord opérationnel, KPIs patrimoine, risques, courbe Lift."""

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ────────────────────────────────────────────────────────
# Linéaire installé par matériau et par an
# ────────────────────────────────────────────────────────
def _extract_year(val):
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip()
    # Format ISO YYYY-... ou YYYY
    if len(s) >= 4 and s[:4].isdigit():
        return int(s[:4])
    # Format français DD/MM/YYYY ou DD-MM-YYYY
    for sep in ("/", "-", "."):
        if sep in s:
            parts = s.split(sep)
            if len(parts) >= 3 and parts[-1][:4].isdigit():
                return int(parts[-1][:4])
    return None


def _impute_by_family(df, mat_col, target_col):
    # Impute les valeurs manquantes de target_col par la moyenne de la famille (mat_col)
    df = df.copy()
    if df[target_col].isna().any():
        means = df.groupby(mat_col)[target_col].transform("mean")
        df[target_col] = df[target_col].fillna(means)
    return df


def _render_lineaire_materiau_annee(df, config, df_referentiel=None):
    """Barres empilées : km installés par matériau et par année de pose."""
    col_map = config["column_mapping"]
    mat_col = col_map.get("famille_materiau", "famille_mat")
    annee_col = col_map.get("annee_pose") or col_map.get("annee") or "POSE"
    longueur_col = "LONGUEUR"
    # Si colonnes manquantes dans df, tente df_referentiel
    if (
        mat_col not in df.columns
        or annee_col not in df.columns
        or longueur_col not in df.columns
    ):
        # Si famille_mat absent, tente MATERIAU
        if df_referentiel is not None:
            if (
                mat_col not in df_referentiel.columns
                and "MATERIAU" in df_referentiel.columns
            ):
                mat_col = "MATERIAU"
            if all(
                c in df_referentiel.columns for c in [mat_col, annee_col, longueur_col]
            ):
                df = df_referentiel
            else:
                st.info(
                    "Colonnes nécessaires manquantes pour le graphique linéaire par matériau/année."
                )
                return
        else:
            st.info(
                "Colonnes nécessaires manquantes pour le graphique linéaire par matériau/année."
            )
            return
    df_temp = df[[mat_col, annee_col, longueur_col]].copy()
    # Extraction année
    df_temp["_annee"] = df_temp[annee_col].apply(_extract_year)
    # Conversion longueur
    df_temp["_longueur"] = (
        df_temp[longueur_col].astype(str).str.replace(",", ".").astype(float)
    )
    # Imputation par famille
    df_temp = _impute_by_family(df_temp, mat_col, "_annee")
    df_temp = _impute_by_family(df_temp, mat_col, "_longueur")
    df_temp = df_temp[df_temp["_annee"].notna() & (df_temp["_annee"] > 1900)]
    df_temp = df_temp[df_temp["_longueur"] > 0]
    grouped = (
        df_temp.groupby(["_annee", mat_col])["_longueur"].sum().unstack(fill_value=0)
        / 1000
    )  # km
    if grouped.empty:
        st.info("Pas de données exploitables pour ce graphique.")
        return
    fig = go.Figure()
    for mat in grouped.columns:
        fig.add_trace(
            go.Bar(
                x=grouped.index.astype(int),
                y=grouped[mat],
                name=str(mat),
            )
        )
    fig.update_layout(
        barmode="stack",
        height=380,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Année de pose",
        yaxis_title="Linéaire installé (km)",
        legend_title="Matériau",
    )
    st.subheader("Linéaire installé par matériau et par an")
    st.plotly_chart(fig, use_container_width=True)


# ────────────────────────────────────────────────────────
# Histogramme période de pose
# ────────────────────────────────────────────────────────
def _render_hist_periode_pose(df, config, df_referentiel=None):
    """Histogramme du nombre de tronçons par année de pose."""
    col_map = config["column_mapping"]
    annee_col = col_map.get("annee_pose") or col_map.get("annee") or "POSE"
    longueur_col = "LONGUEUR"
    if annee_col not in df.columns or longueur_col not in df.columns:
        if df_referentiel is not None and all(
            c in df_referentiel.columns for c in [annee_col, longueur_col]
        ):
            df = df_referentiel
        else:
            st.info(
                "Colonnes nécessaires manquantes pour l'histogramme période de pose."
            )
            return
    df_temp = df[[annee_col, longueur_col]].copy()
    # Extraction année
    df_temp["_annee"] = df_temp[annee_col].apply(_extract_year)
    # Conversion longueur
    df_temp["_longueur"] = (
        df_temp[longueur_col].astype(str).str.replace(",", ".").astype(float)
    )
    # Imputation par famille si possible
    mat_col = config["column_mapping"].get("famille_materiau", "famille_mat")
    if mat_col not in df_temp.columns and "MATERIAU" in df.columns:
        mat_col = "MATERIAU"
        df_temp[mat_col] = df[mat_col]
    if mat_col in df_temp.columns:
        df_temp = _impute_by_family(df_temp, mat_col, "_annee")
        df_temp = _impute_by_family(df_temp, mat_col, "_longueur")
    df_temp = df_temp[df_temp["_annee"].notna() & (df_temp["_annee"] > 1900)]
    df_temp = df_temp[df_temp["_longueur"] > 0]
    grouped = df_temp.groupby("_annee")["_longueur"].sum() / 1000  # km
    if grouped.empty:
        st.info("Pas de données exploitables pour cet histogramme.")
        return
    fig = go.Figure(
        go.Bar(
            x=grouped.index.astype(int),
            y=grouped.values,
            marker_color="#1976d2",
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Année de pose",
        yaxis_title="Linéaire installé (km)",
    )
    st.subheader("Histogramme de la période de pose")
    st.plotly_chart(fig, use_container_width=True)


# ────────────────────────────────────────────────────────
# KPIs
# ────────────────────────────────────────────────────────


def _render_kpis(df, df_referentiel, config, horizon):
    """KPI cards parlantes en en-tête."""
    score_col = f"score_h{horizon}"
    classe_col = f"classe_h{horizon}"
    col_map = config["column_mapping"]
    total = len(df)

    # Compteurs par classe
    n_crit = (df[classe_col] == "critique").sum() if classe_col in df.columns else 0
    n_elev = (df[classe_col] == "eleve").sum() if classe_col in df.columns else 0
    n_mod = (df[classe_col] == "modere").sum() if classe_col in df.columns else 0
    n_faib = (df[classe_col] == "faible").sum() if classe_col in df.columns else 0

    # Longueurs depuis le scoring (enrichi avec LONGUEUR du référentiel)
    if "LONGUEUR" in df.columns:
        longueurs = pd.to_numeric(
            df["LONGUEUR"].astype(str).str.replace(",", "."), errors="coerce"
        )
        km_total = longueurs.sum() / 1000
        km_crit = longueurs[df[classe_col] == "critique"].sum() / 1000
        km_elev = longueurs[df[classe_col] == "eleve"].sum() / 1000
        km_prioritaire = km_crit + km_elev
    elif df_referentiel is not None and "LONGUEUR" in df_referentiel.columns:
        ref = df_referentiel[
            df_referentiel[col_map["id_troncon"]].isin(df[col_map["id_troncon"]])
        ].copy()
        ref = ref.merge(
            df[[col_map["id_troncon"], classe_col]],
            on=col_map["id_troncon"],
            how="left",
        )
        km_total = ref["LONGUEUR"].sum() / 1000
        km_crit = ref.loc[ref[classe_col] == "critique", "LONGUEUR"].sum() / 1000
        km_elev = ref.loc[ref[classe_col] == "eleve", "LONGUEUR"].sum() / 1000
        km_prioritaire = km_crit + km_elev
    else:
        km_total = km_prioritaire = km_crit = 0

    age_moy = df["age"].mean() if "age" in df.columns else 0

    # --- Ligne 1 : Vue d'ensemble ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Réseau analysé",
        f"{km_total:,.0f} km".replace(",", " "),
        delta=f"{total:,} tronçons".replace(",", " "),
        delta_color="off",
    )
    c2.metric(
        "À renouveler en priorité",
        f"{n_crit + n_elev:,}".replace(",", " ") + " tronçons",
        delta=f"{km_prioritaire:,.0f} km critiques + élevés".replace(",", " "),
        delta_color="off",
    )
    c3.metric(
        "Situation urgente",
        f"{n_crit:,}".replace(",", " ") + " tronçons",
        delta=f"{km_crit:,.0f} km en état critique".replace(",", " "),
        delta_color="off",
    )
    c4.metric(
        "Âge moyen",
        f"{age_moy:.0f} ans",
        delta="réseau vieillissant"
        if age_moy > 40
        else "réseau jeune"
        if age_moy < 25
        else "réseau mature",
        delta_color="off",
    )


# ────────────────────────────────────────────────────────
# Répartition risque — donut + barres km
# ────────────────────────────────────────────────────────


def _render_risk_distribution(df, config, horizon):
    """Donut répartition par classe de risque + barres km."""
    st.subheader("Répartition du réseau par niveau de risque")
    classe_col = f"classe_h{horizon}"
    labels = config["risk_labels"]
    colors = config["risk_colors"]
    order = ["critique", "eleve", "modere", "faible"]

    if classe_col not in df.columns:
        st.info("Données de classification non disponibles.")
        return

    counts = df[classe_col].value_counts().reindex(order, fill_value=0)

    # Donut chart
    fig = go.Figure(
        go.Pie(
            labels=[labels.get(k, k) for k in counts.index],
            values=counts.values,
            hole=0.5,
            marker_colors=[colors.get(k, "#999") for k in counts.index],
            textinfo="label+percent",
            textposition="outside",
            hovertemplate="<b>%{label}</b><br>%{value:,} tronçons<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        annotations=[
            dict(
                text=f"<b>{len(df):,}</b><br>tronçons".replace(",", " "),
                x=0.5,
                y=0.5,
                font_size=16,
                showarrow=False,
            )
        ],
    )
    st.plotly_chart(fig, use_container_width=True)


# ────────────────────────────────────────────────────────
# Matériaux — barres colorées par risque dominant
# ────────────────────────────────────────────────────────


def _render_materiau_distribution(df, config, horizon):
    """Distribution matériaux colorée par proportion de risque."""
    st.subheader("Matériaux les plus représentés")
    col = config["column_mapping"]["famille_materiau"]
    classe_col = f"classe_h{horizon}"
    colors_map = config["risk_colors"]

    if col not in df.columns:
        st.info("Données matériaux non disponibles.")
        return

    # Stacked bar : pour chaque matériau, répartition par classe
    top_mats = df[col].value_counts().head(8).index.tolist()
    df_top = df[df[col].isin(top_mats)]

    cross = pd.crosstab(df_top[col], df_top[classe_col])
    cross = cross.reindex(
        columns=["critique", "eleve", "modere", "faible"], fill_value=0
    )
    cross = cross.loc[top_mats]  # garder l'ordre du count

    labels = config["risk_labels"]
    fig = go.Figure()
    for classe_key in ["critique", "eleve", "modere", "faible"]:
        if classe_key in cross.columns:
            fig.add_trace(
                go.Bar(
                    y=cross.index,
                    x=cross[classe_key],
                    name=labels.get(classe_key, classe_key),
                    orientation="h",
                    marker_color=colors_map.get(classe_key, "#999"),
                )
            )

    fig.update_layout(
        barmode="stack",
        height=380,
        margin=dict(l=0, r=20, t=10, b=20),
        xaxis_title="Nombre de tronçons",
        yaxis=dict(autorange="reversed"),
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig, use_container_width=True)


# ────────────────────────────────────────────────────────
# Top N tronçons
# ────────────────────────────────────────────────────────


def _render_top_n(df, config, horizon, n=10):
    """Top N tronçons les plus à risque, cliquable vers détail."""
    st.subheader(f"🚨 Top {n} — Tronçons les plus à risque")
    score_col = f"score_h{horizon}"
    classe_col = f"classe_h{horizon}"
    labels = config["risk_labels"]
    col_map = config["column_mapping"]

    top = df.nlargest(n, score_col)

    display = pd.DataFrame()
    display["Rang"] = range(1, len(top) + 1)
    display["Tronçon"] = top[col_map["id_troncon"]].values
    display["Matériau"] = (
        top[col_map["famille_materiau"]].values
        if col_map["famille_materiau"] in top.columns
        else "—"
    )
    display["Âge"] = (
        top[col_map["age"]]
        .apply(lambda x: f"{int(x)} ans" if pd.notna(x) else "—")
        .values
    )
    display["Score"] = top[score_col].apply(lambda x: f"{x * 100:.1f} %").values
    display["Classe"] = (
        top[classe_col].map(labels).values if classe_col in top.columns else "—"
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="dashboard_top_selection",
    )

    # Clic → navigation détail
    selection = st.session_state.get("dashboard_top_selection", {})
    rows = selection.get("selection", {}).get("rows", [])
    if rows:
        idx = rows[0]
        troncon_id = str(display.iloc[idx]["Tronçon"]).strip()
        if troncon_id.endswith(".0"):
            troncon_id = troncon_id[:-2]
        if (
            st.session_state.get("troncon_selectionne") != troncon_id
            or st.session_state.get("vue_active") != "Détail"
        ):
            st.session_state.troncon_selectionne = troncon_id
            st.session_state.vue_active = "Détail"
            st.rerun()


# ────────────────────────────────────────────────────────
# Cohorte matériau × décennie
# ────────────────────────────────────────────────────────


def _render_cohorte(df, config, horizon):
    """Heatmap cohorte matériau × décennie de pose."""
    st.subheader("Où se concentre le risque ? Matériau × décennie de pose")
    score_col = f"score_h{horizon}"
    col_map = config["column_mapping"]
    mat_col = col_map["famille_materiau"]
    age_col = col_map["age"]

    if mat_col not in df.columns or age_col not in df.columns:
        st.info("Données insuffisantes pour la vue cohorte.")
        return

    current_year = datetime.now().year
    df_temp = df[[mat_col, age_col, score_col]].dropna().copy()
    df_temp["decennie"] = ((current_year - df_temp[age_col]) // 10 * 10).astype(int)

    pivot = df_temp.pivot_table(
        values=score_col, index=mat_col, columns="decennie", aggfunc="mean"
    )

    if pivot.empty:
        st.info("Pas assez de données pour construire la heatmap.")
        return

    fig = px.imshow(
        pivot.values * 100,
        x=[str(int(c)) for c in pivot.columns],
        y=pivot.index.tolist(),
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
        labels={
            "x": "Décennie de pose",
            "y": "Famille matériau",
            "color": "Risque moyen (%)",
        },
    )
    fig.update_layout(height=400, margin=dict(l=0, r=20, t=10, b=20))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Plus la case est **rouge**, plus les tronçons de ce matériau posés cette décennie sont à risque."
    )


# ────────────────────────────────────────────────────────
# Courbe Lift
# ────────────────────────────────────────────────────────


# ────────────────────────────────────────────────────────
# Render principal
# ────────────────────────────────────────────────────────


def render(
    df_scoring: pd.DataFrame, df_referentiel: pd.DataFrame, config: dict, **kwargs
):
    """Point d'entrée de la vue Dashboard."""
    df_backtesting = kwargs.get("df_backtesting")

    if df_scoring is None or df_scoring.empty:
        st.info("Aucun tronçon ne correspond aux filtres appliqués.")
        return

    horizon = st.session_state.get("horizon", 3)
    score_col = f"score_h{horizon}"
    classe_col = f"classe_h{horizon}"

    # Fallback: créer la colonne de classe si absente (pour pallier un éventuel cache)
    if classe_col not in df_scoring.columns:
        quants = config.get("risk_quantiles")
        if quants and score_col in df_scoring.columns:
            s = pd.to_numeric(df_scoring[score_col], errors="coerce")
            q_crit = s.quantile(quants["critique"])
            q_elev = s.quantile(quants["eleve"])
            q_mod = s.quantile(quants["modere"])
            cls = pd.Series("faible", index=df_scoring.index)
            cls[s >= q_mod] = "modere"
            cls[s >= q_elev] = "eleve"
            cls[s >= q_crit] = "critique"
            df_scoring[classe_col] = cls
        else:
            df_scoring[classe_col] = "faible"

    st.title("Tableau de bord — État du réseau")
    st.caption(
        f"Horizon de prédiction : **{horizon} an{'s' if horizon > 1 else ''}** • Données filtrées"
    )

    # KPIs
    _render_kpis(df_scoring, df_referentiel, config, horizon)
    st.divider()

    # Nouveaux graphiques : linéaire par matériau/année et histogramme période de pose
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        _render_lineaire_materiau_annee(df_scoring, config, df_referentiel)
    with col_g2:
        _render_hist_periode_pose(df_scoring, config, df_referentiel)
    st.divider()

    # Distribution risque + matériaux côte à côte
    col_left, col_right = st.columns(2)
    with col_left:
        _render_risk_distribution(df_scoring, config, horizon)
    with col_right:
        _render_materiau_distribution(df_scoring, config, horizon)

    st.divider()

    # Top 10 + Cohorte côte à côte
    col_left2, col_right2 = st.columns([1, 1])
    with col_left2:
        _render_top_n(df_scoring, config, horizon)
    with col_right2:
        _render_cohorte(df_scoring, config, horizon)

    st.divider()

    # ...section Courbe Lift supprimée...
