"""Vue carte — Folium interactif (clic réel sur tronçon, popup, navigation Détail)."""

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Fullscreen
from streamlit_folium import st_folium


CLASSE_HEX = {
    "critique": "#d32f2f",
    "eleve": "#ff9800",
    "modere": "#fdd835",
    "faible": "#4caf50",
}

CLASSE_WIDTH = {
    "critique": 6,
    "eleve": 4,
    "modere": 3,
    "faible": 2,
}

CLASSE_ORDER = ["critique", "eleve", "modere", "faible"]

# Plafond pour garder la carte fluide (Folium souffre au-delà)
MAX_FEATURES = 4000


@st.cache_data(show_spinner="Préparation de la carte…")
def _prepare_map_data(_gdf, _df_scoring, _score_col, _classe_col, _col_map):
    gdf_j = _gdf.copy()
    gdf_j["GID"] = gdf_j["GID"].astype(str)
    df_j = _df_scoring.copy()
    df_j[_col_map["id_troncon"]] = df_j[_col_map["id_troncon"]].astype(str)
    cols_keep = [
        _col_map["id_troncon"],
        _score_col,
        _classe_col,
        _col_map["famille_materiau"],
        _col_map["age"],
    ]
    for opt in ("LONGUEUR", "alea_argile", "nb_fuites_historique"):
        if opt in df_j.columns:
            cols_keep.append(opt)
    merged = gdf_j.merge(
        df_j[cols_keep], left_on="GID", right_on=_col_map["id_troncon"], how="inner"
    )
    if merged.empty:
        return None, None
    bnds = merged.total_bounds
    return merged, bnds


def _coords_from_geom(g):
    """LineString/MultiLineString → liste de listes [(lat, lon)]."""
    if g is None:
        return []
    if g.geom_type == "LineString":
        return [[(c[1], c[0]) for c in g.coords]]
    if g.geom_type == "MultiLineString":
        return [[(c[1], c[0]) for c in part.coords] for part in g.geoms]
    return []


def _popup_html(row, score_col, classe_col, col_map, base_rate):
    score = float(row[score_col])
    score_pct = score * 100
    multiple = score / base_rate if base_rate > 0 else 1.0
    rows = [
        f"<b>Tronçon {row['GID']}</b>",
        f"<b>Risque :</b> {row[classe_col]}  (×{multiple:.1f} le réseau moyen)",
        f"<b>Probabilité de fuite :</b> {score_pct:.2f} %",
        f"<b>Matériau :</b> {row[col_map['famille_materiau']]}",
        f"<b>Âge :</b> {int(row[col_map['age']]) if pd.notna(row[col_map['age']]) else '—'} ans",
    ]
    if "LONGUEUR" in row and pd.notna(row["LONGUEUR"]):
        rows.append(f"<b>Longueur :</b> {float(row['LONGUEUR']):.0f} m")
    if "alea_argile" in row and pd.notna(row["alea_argile"]):
        rows.append(f"<b>Aléa argile :</b> {row['alea_argile']}")
    if "nb_fuites_historique" in row and pd.notna(row["nb_fuites_historique"]):
        rows.append(f"<b>Fuites passées :</b> {int(row['nb_fuites_historique'])}")
    return (
        "<div style='font-family:sans-serif;font-size:12px;line-height:1.5;min-width:180px;'>"
        + "<br/>".join(rows)
        + "</div>"
    )


def render(
    df_scoring: pd.DataFrame, df_referentiel: pd.DataFrame, config: dict, **kwargs
):
    """Vue carte interactive Folium."""
    gdf = kwargs.get("gdf")
    horizon = st.session_state.get("horizon", 3)
    score_col = f"score_h{horizon}"
    classe_col = f"classe_h{horizon}"
    labels = config["risk_labels"]
    colors = config["risk_colors"]
    col_map = config["column_mapping"]

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

    if gdf is None:
        st.warning("Fichier géographique non trouvé.")
        return

    if len(df_scoring) == 0:
        st.info("Aucun tronçon ne correspond aux filtres appliqués.")
        return

    st.title("Carte du réseau")

    merged, bounds = _prepare_map_data(gdf, df_scoring, score_col, classe_col, col_map)
    if merged is None:
        st.warning(
            "Aucune correspondance entre les géométries et les données de scoring."
        )
        return

    # ──────────────── KPIs métier ────────────────
    n_crit = (
        (df_scoring[classe_col] == "critique").sum()
        if classe_col in df_scoring.columns
        else 0
    )
    n_elev = (
        (df_scoring[classe_col] == "eleve").sum()
        if classe_col in df_scoring.columns
        else 0
    )
    if "LONGUEUR" in df_scoring.columns and classe_col in df_scoring.columns:
        long_m = pd.to_numeric(
            df_scoring["LONGUEUR"].astype(str).str.replace(",", "."), errors="coerce"
        )
        km_total = long_m.sum() / 1000
        km_risque = (
            long_m[df_scoring[classe_col].isin(["critique", "eleve"])].sum() / 1000
        )
    else:
        km_total = km_risque = 0
    fuites_att = (
        pd.to_numeric(df_scoring[score_col], errors="coerce").sum()
        if score_col in df_scoring.columns
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Réseau affiché",
        f"{km_total:,.0f} km".replace(",", " "),
        delta=f"{len(df_scoring):,} tronçons".replace(",", " "),
        delta_color="off",
    )
    c2.metric(
        "À traiter en priorité",
        f"{n_crit + n_elev:,}".replace(",", " ") + " tronçons",
        delta=f"{km_risque:,.0f} km".replace(",", " "),
        delta_color="off",
    )
    c3.metric(
        "Urgences",
        f"{n_crit:,}".replace(",", " ") + " critiques",
        delta="à inspecter sous 1 an",
        delta_color="off",
    )
    c4.metric(
        f"Fuites attendues ({horizon} ans)",
        f"≈ {fuites_att:,.0f}".replace(",", " "),
        delta="estimation modèle",
        delta_color="off",
    )
    st.divider()

    # ──────────────── Filtres carte ────────────────
    col_classes, col_search = st.columns([3, 2])
    with col_classes:
        st.caption("**Niveaux affichés**")
        chk_cols = st.columns(4)
        show_classes = {}
        defaults = {"critique": True, "eleve": True, "modere": False, "faible": False}
        for i, k in enumerate(CLASSE_ORDER):
            with chk_cols[i]:
                show_classes[k] = st.checkbox(
                    labels.get(k, k), value=defaults[k], key=f"carte_show_{k}"
                )
    with col_search:
        st.caption("**Rechercher un tronçon**")
        search = st.text_input(
            "ID",
            placeholder="ID complet ou partiel",
            label_visibility="collapsed",
            key="carte_search",
        )

    active_classes = {k for k, v in show_classes.items() if v} or set(CLASSE_ORDER)
    df_view = merged[merged[classe_col].isin(active_classes)].copy()

    if search:
        s = search.strip().lower()
        df_view = df_view[df_view["GID"].str.lower().str.contains(s, na=False)]
        if df_view.empty:
            st.warning(f"Aucun tronçon trouvé pour « {search} ».")
            return

    # Plafond : on garde les plus à risque pour rester fluide
    n_total = len(df_view)
    if n_total > MAX_FEATURES:
        df_view = df_view.nlargest(MAX_FEATURES, score_col)
        st.caption(
            f"⚠️ {n_total:,} tronçons correspondent aux filtres → seuls les **{MAX_FEATURES:,} plus à risque** sont affichés sur la carte. Affinez les filtres pour tout voir.".replace(
                ",", " "
            )
        )

    # Légende
    legend_parts = []
    for k in CLASSE_ORDER:
        n = (df_view[classe_col] == k).sum()
        if show_classes.get(k):
            legend_parts.append(
                f'<span style="color:{colors[k]}; font-size:18px;">■</span> '
                f'<b>{labels[k]}</b> <span style="color:#888;">({n:,})</span>'.replace(
                    ",", " "
                )
            )
    st.markdown(" &nbsp;&nbsp;&nbsp; ".join(legend_parts), unsafe_allow_html=True)

    if df_view.empty:
        st.info("Aucun tronçon ne correspond aux filtres carte.")
        return

    # ──────────────── Construction Folium ────────────────
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    fmap = folium.Map(
        location=[center_lat, center_lon], zoom_start=12, tiles="cartodbpositron"
    )
    Fullscreen().add_to(fmap)

    # Taux de base = score moyen sur tout le réseau scoré (référence pour multiple)
    base_rate = float(pd.to_numeric(df_scoring[score_col], errors="coerce").mean()) or 1e-6

    for _, row in df_view.iterrows():
        coords_groups = _coords_from_geom(row.geometry)
        if not coords_groups:
            continue
        cls = row[classe_col] if pd.notna(row[classe_col]) else "faible"
        color = CLASSE_HEX.get(cls, "#999")
        weight = CLASSE_WIDTH.get(cls, 3)
        popup = folium.Popup(
            _popup_html(row, score_col, classe_col, col_map, base_rate), max_width=300
        )
        for coords in coords_groups:
            folium.PolyLine(
                locations=coords,
                color=color,
                weight=weight,
                opacity=0.85,
                popup=popup,
                tooltip=f"Tronçon {row['GID']}",
            ).add_to(fmap)

    st_data = st_folium(
        fmap,
        height=650,
        use_container_width=True,
        returned_objects=["last_object_clicked_tooltip"],
    )

    st.caption(
        "👆 **Cliquez** sur un tronçon pour voir son détail. Molette pour zoomer, clic-glisser pour naviguer."
    )

    # ──────────────── Clic → navigation Détail ────────────────
    clicked = st_data.get("last_object_clicked_tooltip") if st_data else None
    if clicked and isinstance(clicked, str) and clicked.startswith("Tronçon "):
        tid = clicked.replace("Tronçon ", "").strip()
        if tid and st.session_state.get("troncon_selectionne") != tid:
            st.session_state.troncon_selectionne = tid
            st.session_state.vue_active = "Détail"
            st.rerun()
