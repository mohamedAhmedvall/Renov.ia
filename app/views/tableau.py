"""Vue tableau — liste explorable des tronçons, triée par risque."""

import pandas as pd
import streamlit as st

from export import export_csv, get_export_filename


CLASSE_ORDER = ["critique", "eleve", "modere", "faible"]


def _get_score_col(horizon: int) -> str:
    return f"score_h{horizon}"


def _get_classe_col(horizon: int) -> str:
    return f"classe_h{horizon}"


def _fmt_id(v):
    if pd.isna(v):
        return "—"
    s = str(v).strip()
    return s[:-2] if s.endswith(".0") else s


def _render_kpis(df: pd.DataFrame, config: dict, horizon: int):
    """KPI cards orientées métier (langage exploitant)."""
    classe_col = _get_classe_col(horizon)
    score_col = _get_score_col(horizon)
    col_map = config["column_mapping"]
    total = len(df)

    n_crit = int((df[classe_col] == "critique").sum()) if classe_col in df.columns else 0
    n_elev = int((df[classe_col] == "eleve").sum()) if classe_col in df.columns else 0
    n_surv = n_crit + n_elev

    if "LONGUEUR" in df.columns and classe_col in df.columns:
        long_m = pd.to_numeric(df["LONGUEUR"].astype(str).str.replace(",", "."), errors="coerce")
        km_risque = long_m[df[classe_col].isin(["critique", "eleve"])].sum() / 1000
    else:
        km_risque = 0

    # Espérance de fuites = somme des probas calibrées sur l'horizon
    fuites_att = pd.to_numeric(df[score_col], errors="coerce").sum() if score_col in df.columns else 0
    age_moy = df[col_map["age"]].mean() if col_map["age"] in df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "À surveiller en priorité",
        f"{n_surv:,}".replace(",", " ") + " tronçons",
        delta=f"dont {n_crit:,} critiques".replace(",", " "),
        delta_color="off",
    )
    c2.metric(
        "Linéaire à risque",
        f"{km_risque:,.0f} km".replace(",", " "),
        delta=f"sur {total:,} tronçons filtrés".replace(",", " "),
        delta_color="off",
    )
    c3.metric(
        f"Fuites attendues ({horizon} ans)",
        f"≈ {fuites_att:,.0f}".replace(",", " "),
        delta="estimation modèle V9",
        delta_color="off",
    )
    c4.metric("Âge moyen", f"{age_moy:.0f} ans")


def _build_display_df(df: pd.DataFrame, config: dict, horizon: int) -> pd.DataFrame:
    """Prépare un DataFrame typé (pas de strings) pour exploiter le tri natif et ProgressColumn."""
    score_col = _get_score_col(horizon)
    classe_col = _get_classe_col(horizon)
    labels = config["risk_labels"]
    col_map = config["column_mapping"]

    out = pd.DataFrame()
    out["Tronçon"] = df[col_map["id_troncon"]].map(_fmt_id)
    out["Matériau"] = df[col_map["famille_materiau"]] if col_map["famille_materiau"] in df.columns else df.get(col_map["materiau"], "—")
    out["Âge"] = pd.to_numeric(df[col_map["age"]], errors="coerce")
    out["Diamètre"] = pd.to_numeric(df[col_map["diametre"]], errors="coerce")
    if "LONGUEUR" in df.columns:
        out["Longueur"] = pd.to_numeric(df["LONGUEUR"].astype(str).str.replace(",", "."), errors="coerce")
    # Indice 0-100 basé sur le rang ABSOLU dans le réseau complet (100 = pire)
    # top_pct vient du scoring V9 (rang sur tout le réseau), 0 = pire → on inverse
    score_raw = pd.to_numeric(df[score_col], errors="coerce").fillna(0)
    if "top_pct" in df.columns:
        out["Score"] = (100 - pd.to_numeric(df["top_pct"], errors="coerce").fillna(100)).clip(0, 100)
    else:
        out["Score"] = score_raw.rank(pct=True, method="average") * 100
    out["_score_raw"] = score_raw
    out["Niveau"] = df[classe_col].map(labels) if classe_col in df.columns else "—"
    if "alea_argile" in df.columns:
        out["Aléa argile"] = df["alea_argile"].fillna("—")
    if "nb_fuites_historique" in df.columns:
        out["Fuites passées"] = pd.to_numeric(df["nb_fuites_historique"], errors="coerce").fillna(0).astype(int)
    out["_classe"] = df[classe_col] if classe_col in df.columns else "faible"
    return out


def render(df_scoring: pd.DataFrame, df_referentiel: pd.DataFrame, config: dict, **kwargs):
    """Point d'entrée de la vue Tableau."""
    if df_scoring is None or df_scoring.empty:
        st.info("Aucun tronçon ne correspond aux filtres appliqués.")
        return

    horizon = st.session_state.get("horizon", 3)
    labels = config["risk_labels"]

    st.title("Liste des tronçons")
    st.caption(f"Horizon **{horizon} an{'s' if horizon > 1 else ''}** • Triez par n'importe quelle colonne • Cliquez une ligne pour voir le détail")

    _render_kpis(df_scoring, config, horizon)
    st.divider()

    # ──────────────────────────────────────────────
    # Barre d'outils : recherche + filtres rapides
    # ──────────────────────────────────────────────
    classe_col = _get_classe_col(horizon)
    counts = df_scoring[classe_col].value_counts() if classe_col in df_scoring.columns else {}

    col_search, col_class, col_limit = st.columns([2, 2, 1])
    with col_search:
        search = st.text_input(
            "Rechercher un tronçon",
            placeholder="ID complet ou partiel…",
            key="tableau_search",
            label_visibility="collapsed",
        )
    with col_class:
        options = [
            f"{labels.get(c, c)} ({int(counts.get(c, 0))})"
            for c in CLASSE_ORDER if counts.get(c, 0) > 0
        ]
        option_to_classe = {f"{labels.get(c, c)} ({int(counts.get(c, 0))})": c for c in CLASSE_ORDER if counts.get(c, 0) > 0}
        selected_labels = st.multiselect(
            "Filtrer par niveau de risque",
            options,
            default=[],
            placeholder="Tous les niveaux",
            label_visibility="collapsed",
        )
        selected_classes = {option_to_classe[lbl] for lbl in selected_labels}
    with col_limit:
        top_n = st.selectbox("Afficher", [50, 200, 1000, 5000, "Tous"], index=2, label_visibility="collapsed")

    # ──────────────────────────────────────────────
    # Préparation + filtrage
    # ──────────────────────────────────────────────
    display_df = _build_display_df(df_scoring, config, horizon)
    display_df = display_df.sort_values("Score", ascending=False).reset_index(drop=True)

    if selected_classes:
        display_df = display_df[display_df["_classe"].isin(selected_classes)]
    if search:
        s = search.strip().lower()
        display_df = display_df[display_df["Tronçon"].str.lower().str.contains(s, na=False)]

    n_filtered = len(display_df)
    if isinstance(top_n, int):
        display_df = display_df.head(top_n)

    if n_filtered == 0:
        st.info("Aucun tronçon ne correspond à votre recherche.")
        return

    st.caption(f"**{len(display_df):,}** affichés sur **{n_filtered:,}** correspondant aux filtres".replace(",", " "))

    # ──────────────────────────────────────────────
    # Colonnes affichées (sans la colonne technique _classe)
    # ──────────────────────────────────────────────
    visible_cols = ["Tronçon", "Matériau", "Âge", "Diamètre", "Score", "Niveau"]
    if "Longueur" in display_df.columns:
        visible_cols.insert(4, "Longueur")
    if "Aléa argile" in display_df.columns:
        visible_cols.append("Aléa argile")
    if "Fuites passées" in display_df.columns:
        visible_cols.append("Fuites passées")

    column_config = {
        "Tronçon": st.column_config.TextColumn(width="small"),
        "Matériau": st.column_config.TextColumn(width="small"),
        "Âge": st.column_config.NumberColumn(format="%d ans", width="small"),
        "Diamètre": st.column_config.NumberColumn(format="%d mm", width="small"),
        "Score": st.column_config.ProgressColumn(
            "Indice de risque",
            help="Position relative du tronçon sur le périmètre filtré (100 = le plus à risque). Basé sur les probabilités calibrées V9.",
            format="%.0f / 100",
            min_value=0.0,
            max_value=100.0,
            width="medium",
        ),
        "Niveau": st.column_config.TextColumn(width="small"),
    }
    if "Longueur" in visible_cols:
        column_config["Longueur"] = st.column_config.NumberColumn(format="%.0f m", width="small")
    if "Aléa argile" in visible_cols:
        column_config["Aléa argile"] = st.column_config.TextColumn(width="small")
    if "Fuites passées" in visible_cols:
        column_config["Fuites passées"] = st.column_config.NumberColumn(format="%d", width="small")

    # Export
    export_df = display_df[visible_cols].copy()
    export_df["Score"] = (export_df["Score"] * 100).round(1).astype(str) + " %"
    csv_data = export_csv(export_df, visible_cols, config)
    st.download_button(
        "Exporter la liste en CSV",
        csv_data,
        file_name=get_export_filename("troncons"),
        mime="text/csv",
    )

    # ──────────────────────────────────────────────
    # Tableau interactif
    # ──────────────────────────────────────────────
    st.dataframe(
        display_df[visible_cols],
        use_container_width=True,
        height=600,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="tableau_selection",
        column_config=column_config,
    )

    # Clic ligne → navigation vers détail
    selection = st.session_state.get("tableau_selection", {})
    rows = selection.get("selection", {}).get("rows", [])
    if rows:
        idx = rows[0]
        raw_id = display_df.iloc[idx]["Tronçon"]
        troncon_id = str(raw_id).strip()
        if troncon_id.endswith(".0"):
            troncon_id = troncon_id[:-2]
        if st.session_state.get("troncon_selectionne") != troncon_id or st.session_state.get("vue_active") != "Détail":
            st.session_state.troncon_selectionne = troncon_id
            st.session_state.vue_active = "Détail"
            st.rerun()
