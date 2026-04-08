"""Vue optimiseur — planification de renouvellement sous contrainte budgétaire."""

from datetime import datetime
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from optimizer import optimize_renewal


def _popup_html_opt(gid, info, kind):
    """HTML popup riche pour un tronçon sur la carte de l'optimiseur."""
    rows = [f"<b>Tronçon {gid}</b>", f"<i>{kind}</i>"]
    if info is not None:
        if "famille_mat" in info and pd.notna(info.get("famille_mat")):
            rows.append(f"<b>Matériau :</b> {info['famille_mat']}")
        if "age" in info and pd.notna(info.get("age")):
            rows.append(f"<b>Âge :</b> {int(info['age'])} ans")
        if "LONGUEUR" in info and pd.notna(info.get("LONGUEUR")):
            try:
                rows.append(f"<b>Longueur :</b> {float(str(info['LONGUEUR']).replace(',', '.')):.0f} m")
            except (ValueError, TypeError):
                pass
        for h in (1, 3, 5):
            sc = f"score_h{h}"
            if sc in info and pd.notna(info.get(sc)):
                rows.append(f"<b>Proba {h} an{'s' if h>1 else ''} :</b> {float(info[sc])*100:.2f} %")
        if "alea_argile" in info and pd.notna(info.get("alea_argile")):
            rows.append(f"<b>Aléa argile :</b> {info['alea_argile']}")
        if "nb_fuites_historique" in info and pd.notna(info.get("nb_fuites_historique")):
            rows.append(f"<b>Fuites passées :</b> {int(info['nb_fuites_historique'])}")
    return (
        "<div style='font-family:sans-serif;font-size:12px;line-height:1.5;min-width:200px;'>"
        + "<br/>".join(rows) + "</div>"
    )


def _build_pdf(kpis, df_result, horizon, budget, id_col):
    """Génère un PDF du plan de renouvellement."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Plan de renouvellement", styles["Title"]))
    story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    kpi_data = [
        ["Indicateur", "Valeur"],
        ["Budget enveloppe", f"{budget:,.0f} €".replace(",", " ")],
        ["Budget consommé", f"{kpis['budget_utilise']:,.0f} € ({kpis['budget_pct']:.0f} %)".replace(",", " ")],
        ["Linéaire renouvelé", f"{kpis['km_renouveles']:.2f} km"],
        ["Nombre de tronçons", f"{kpis['nb_troncons']}"],
        [f"Fuites évitées ({horizon} ans)", f"≈ {kpis['fuites_evitees']:.1f}"],
        ["Coût unitaire effectif", f"{kpis.get('cout_ml_effectif', 0):.0f} €/ml"],
    ]
    t = Table(kpi_data, colWidths=[7*cm, 7*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d32f2f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.6*cm))

    story.append(Paragraph("Tronçons sélectionnés (top 50)", styles["Heading2"]))
    score_col = f"score_h{horizon}"
    head = ["Priorité", "Tronçon", "Score", "Longueur (m)", "Coût (€)"]
    rows = [head]
    for _, r in df_result.head(50).iterrows():
        rows.append([
            int(r["priorite"]),
            str(r[id_col]),
            f"{float(r[score_col])*100:.1f} %",
            f"{float(r.get('longueur_ml', 0)):.0f}",
            f"{float(r['cout_unitaire']):,.0f}".replace(",", " "),
        ])
    t2 = Table(rows, colWidths=[2*cm, 4*cm, 2.5*cm, 3*cm, 3*cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#424242")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t2)
    doc.build(story)
    return buf.getvalue()


# Couleurs du plan sur la carte
COLOR_PLAN = [211, 47, 47, 220]      # rouge vif = à renouveler
COLOR_FORCE = [33, 150, 243, 220]    # bleu = forcé manuellement
COLOR_EXCLU = [120, 120, 120, 60]    # gris = exclu
COLOR_OTHER = [200, 200, 200, 50]    # gris clair = reste du réseau


def _normalize_id(v) -> str:
    if v is None or pd.isna(v):
        return ""
    s = str(v).strip()
    return s[:-2] if s.endswith(".0") else s


@st.cache_data(show_spinner=False)
def _prepare_paths(_gdf):
    """Extrait les paths une seule fois (caché)."""
    gdf = _gdf.copy()

    def geom_to_coords(g):
        if g is None:
            return []
        if g.geom_type == "LineString":
            return [list(c) for c in g.coords]
        if g.geom_type == "MultiLineString":
            coords = []
            for part in g.geoms:
                coords.extend([list(c) for c in part.coords])
            return coords
        return []

    gdf["path"] = gdf["geometry"].apply(geom_to_coords)
    gdf["GID_str"] = gdf["GID"].map(_normalize_id)
    bounds = gdf.total_bounds
    return gdf[["GID_str", "path"]], bounds


def render(df_scoring: pd.DataFrame, df_referentiel: pd.DataFrame, config: dict, **kwargs):
    """Point d'entrée de la vue Optimiseur."""
    df_scoring_full = kwargs.get("df_scoring_full", df_scoring)
    col_map = config["column_mapping"]
    id_col = col_map["id_troncon"]

    st.title("Planifier le renouvellement")
    st.caption(
        "Définissez votre budget et vos contraintes. L'optimiseur sélectionne "
        "les tronçons à renouveler en priorité pour **maximiser la réduction du risque**."
    )

    if df_scoring_full is None or df_scoring_full.empty:
        st.warning("Aucune donnée de scoring disponible.")
        return

    # ────────────────────────────────────────────────────
    # Paramètres principaux
    # ────────────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        budget = st.number_input(
            "Enveloppe budgétaire (€)",
            min_value=10_000, max_value=50_000_000,
            value=st.session_state.get("budget_enveloppe", 500_000),
            step=50_000, format="%d",
            help="Budget total disponible pour le renouvellement",
        )
        st.session_state.budget_enveloppe = budget

    with col2:
        horizon = st.radio(
            "Horizon",
            [1, 3, 5],
            index=[1, 3, 5].index(st.session_state.get("horizon", 3)),
            format_func=lambda x: f"{x} an{'s' if x > 1 else ''}",
            horizontal=True,
        )

    # ────────────────────────────────────────────────────
    # Options avancées
    # ────────────────────────────────────────────────────
    with st.expander("Options avancées"):
        materiau = st.radio(
            "Matériau de remplacement",
            ["fonte_ductile", "pehd"],
            format_func={"fonte_ductile": "Fonte ductile (durable)", "pehd": "PEHD (économique)"}.get,
            horizontal=True,
        )
        st.session_state.materiau_remplacement = materiau

        contrainte_1pct = st.checkbox(
            "Renouveler au moins 1% du réseau",
            value=st.session_state.get("contrainte_1pct", True),
            help=f"Garantir le remplacement d'au moins {config.get('km_total_reseau', 100) * 0.01:.0f} km",
        )
        st.session_state.contrainte_1pct = contrainte_1pct

    st.divider()

    # ────────────────────────────────────────────────────
    # Auto-recalcul à chaque changement de paramètre
    # ────────────────────────────────────────────────────
    troncons_forces = st.session_state.get("troncons_forces_user", set())
    troncons_exclus = st.session_state.get("troncons_exclus_user", set())

    conflict = troncons_forces & troncons_exclus
    if conflict:
        st.error(f"**Conflit** — {len(conflict)} tronçons sont à la fois inclus et exclus.")
        return

    sig = (budget, horizon, materiau, contrainte_1pct,
           tuple(sorted(troncons_forces)), tuple(sorted(troncons_exclus)))
    if st.session_state.get("opt_sig") != sig:
        df_backtesting = kwargs.get("df_backtesting")
        params = {
            "budget": budget, "horizon": horizon,
            "materiau_remplacement": materiau,
            "df_referentiel": df_referentiel,
            "df_backtesting": df_backtesting,
            "troncons_forces": troncons_forces,
            "troncons_exclus": troncons_exclus,
            "contrainte_1pct": contrainte_1pct,
        }
        with st.spinner("Calcul du plan…"):
            result = optimize_renewal(df_scoring_full, config, params)
        if not result["success"]:
            st.error(f"**Optimisation impossible** — {result['message']}")
            return
        st.session_state["opt_result"] = result
        st.session_state["opt_horizon"] = horizon
        st.session_state["opt_budget"] = budget
        st.session_state["opt_sig"] = sig

    result = st.session_state.get("opt_result")
    if result is None:
        st.info("Ajustez les paramètres pour générer un plan.")
        return

    horizon = st.session_state.get("opt_horizon", horizon)
    budget = st.session_state.get("opt_budget", budget)
    kpis = result["kpis"]
    df_result = result["troncons_selectionnes"]
    plan_ids = set(df_result[id_col].map(_normalize_id))

    st.success("Plan de renouvellement calculé.")

    # ────────────────────────────────────────────────
    # KPIs métier (langage exploitant, tout en linéaire)
    # ────────────────────────────────────────────────
    score_col = f"score_h{horizon}"
    km_total_reseau = config.get("km_total_reseau", 100)
    km_plan = kpis["km_renouveles"]
    pct_reseau = km_plan / max(km_total_reseau, 1) * 100
    cycle_ans = (km_total_reseau / km_plan) if km_plan > 0 else float("inf")

    # Fuites évitées sur tout le réseau si on ne fait rien (référence)
    if score_col in df_scoring_full.columns:
        fuites_si_rien = float(pd.to_numeric(df_scoring_full[score_col], errors="coerce").sum())
    else:
        fuites_si_rien = 0
    fuites_evitees = kpis["fuites_evitees"]
    pct_fuites_evitees = (fuites_evitees / fuites_si_rien * 100) if fuites_si_rien > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Linéaire renouvelé",
        f"{km_plan:.2f} km",
        delta=f"{kpis['nb_troncons']} tronçons • {pct_reseau:.2f} % du réseau",
        delta_color="off",
    )
    c2.metric(
        "Budget consommé",
        f"{kpis['budget_utilise']:,.0f} €".replace(",", " "),
        delta=f"{kpis['budget_pct']:.0f} % de l'enveloppe ({kpis.get('cout_ml_effectif', 0):.0f} €/ml)",
        delta_color="off",
    )
    c3.metric(
        f"Fuites évitées ({horizon} ans)",
        f"≈ {fuites_evitees:.1f}",
        delta=f"sur ≈ {fuites_si_rien:.0f} attendues si rien fait ({pct_fuites_evitees:.1f} %)",
        delta_color="off",
    )
    c4.metric(
        "Cycle de renouvellement",
        f"{cycle_ans:.0f} ans" if cycle_ans < 9999 else "—",
        delta="durée pour renouveler tout le réseau à ce rythme",
        delta_color="off",
    )

    st.divider()

    # ────────────────────────────────────────────────
    # Carte interactive du plan
    # ────────────────────────────────────────────────
    st.subheader("Carte du plan de renouvellement")
    st.caption(
        "**Rouge** = tronçons sélectionnés par l'optimiseur • "
        "**Bleu** = forcés manuellement • "
        "**Gris foncé** = exclus • "
        "**Gris clair** = reste du réseau"
    )

    gdf = kwargs.get("gdf")
    if gdf is None or gdf.empty:
        st.info("Carte indisponible — `data/geo.csv` manquant.")
    else:
        import folium
        from streamlit_folium import st_folium
        from folium.plugins import Fullscreen

        gdf_local = gdf.copy()
        gdf_local["GID_str"] = gdf_local["GID"].astype(str).map(_normalize_id)

        # On affiche : tronçons du plan (rouge) + forcés (bleu) + UNE COUCHE LÉGÈRE
        # de fond (max 1500 tronçons aléatoires) pour le contexte → rapide
        gdf_plan = gdf_local[gdf_local["GID_str"].isin(plan_ids)]
        gdf_force = gdf_local[gdf_local["GID_str"].isin(troncons_forces)]
        rest = gdf_local[~gdf_local["GID_str"].isin(plan_ids | troncons_forces)]
        gdf_bg = rest.sample(min(4000, len(rest)), random_state=0) if len(rest) else rest

        if gdf_plan.empty and gdf_force.empty:
            st.warning("Aucun tronçon du plan n'a de géométrie connue.")
        else:
            bnds = gdf_local.total_bounds
            center_lat = (bnds[1] + bnds[3]) / 2
            center_lon = (bnds[0] + bnds[2]) / 2
            fmap = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="cartodbpositron")
            Fullscreen().add_to(fmap)

            # Index scoring sur GID normalisé pour enrichir les popups
            df_info = df_scoring_full.copy()
            df_info["_gid"] = df_info[id_col].map(_normalize_id)
            df_info = df_info.drop_duplicates("_gid").set_index("_gid")

            def add_lines(gdf_subset, color, weight, kind, with_popup=True):
                for _, r in gdf_subset.iterrows():
                    g = r.geometry
                    if g is None:
                        continue
                    gid = r["GID_str"]
                    parts = [g] if g.geom_type == "LineString" else list(g.geoms) if g.geom_type == "MultiLineString" else []
                    info = df_info.loc[gid] if gid in df_info.index else None
                    popup = None
                    if with_popup:
                        popup = folium.Popup(_popup_html_opt(gid, info, kind), max_width=320)
                    for part in parts:
                        coords = [(c[1], c[0]) for c in part.coords]
                        pl = folium.PolyLine(
                            locations=coords, color=color, weight=weight, opacity=0.9,
                            tooltip=f"Tronçon {gid}",
                        )
                        if popup is not None:
                            pl.add_child(popup)
                        pl.add_to(fmap)

            add_lines(gdf_bg, "#9aa0a6", 2, "Réseau (contexte)", with_popup=True)
            add_lines(gdf_plan, "#d32f2f", 5, "Sélectionné par l'optimiseur")
            add_lines(gdf_force, "#1976d2", 6, "Forcé manuellement")

            st_data = st_folium(
                fmap, height=550, use_container_width=True,
                returned_objects=["last_object_clicked_tooltip"],
            )
            st.caption(f"Affichage : **{len(gdf_plan)}** tronçons du plan + **{len(gdf_bg)}** tronçons de contexte (échantillon).")

            # Clic → boutons inclure / exclure
            clicked = st_data.get("last_object_clicked_tooltip") if st_data else None
            if clicked and isinstance(clicked, str) and clicked.startswith("Tronçon "):
                tid = clicked.replace("Tronçon ", "").strip()
                st.markdown(f"**Tronçon sélectionné : `{tid}`**")
                bcol1, bcol2, bcol3 = st.columns(3)
                with bcol1:
                    if st.button("➕ Inclure dans le plan", key=f"inc_{tid}"):
                        s = set(st.session_state.get("troncons_forces_user", set()))
                        s.add(tid)
                        st.session_state["troncons_forces_user"] = s
                        st.session_state.get("troncons_exclus_user", set()).discard(tid)
                        st.rerun()
                with bcol2:
                    if st.button("➖ Exclure du plan", key=f"exc_{tid}"):
                        s = set(st.session_state.get("troncons_exclus_user", set()))
                        s.add(tid)
                        st.session_state["troncons_exclus_user"] = s
                        st.session_state.get("troncons_forces_user", set()).discard(tid)
                        st.rerun()
                with bcol3:
                    if st.button("↺ Retirer la contrainte", key=f"clr_{tid}"):
                        st.session_state.get("troncons_forces_user", set()).discard(tid)
                        st.session_state.get("troncons_exclus_user", set()).discard(tid)
                        st.rerun()

        # ────────────────────────────────────────────────
        # Ajustement interactif du plan
        # ────────────────────────────────────────────────
        st.markdown("**Ajuster le plan manuellement**")
        st.caption("Saisissez les IDs séparés par des virgules. Relancez l'optimisation pour recalculer avec ces contraintes.")

        col_inc, col_exc = st.columns(2)
        with col_inc:
            inc_text = st.text_area(
                "Tronçons à inclure obligatoirement",
                value=", ".join(sorted(troncons_forces)),
                height=80,
                key="opt_inc_text",
            )
        with col_exc:
            exc_text = st.text_area(
                "Tronçons à exclure",
                value=", ".join(sorted(troncons_exclus)),
                height=80,
                key="opt_exc_text",
            )

        if st.button("Appliquer la sélection manuelle"):
            new_inc = {x.strip() for x in inc_text.split(",") if x.strip()}
            new_exc = {x.strip() for x in exc_text.split(",") if x.strip()}
            if new_inc & new_exc:
                st.error("Certains tronçons sont à la fois inclus et exclus.")
            else:
                st.session_state["troncons_forces_user"] = new_inc
                st.session_state["troncons_exclus_user"] = new_exc
                st.info("Sélection mise à jour. Cliquez sur **Lancer l'optimisation** pour recalculer.")

    st.divider()

    # ────────────────────────────────────────────────
    # Résultats — Tableau + Répartition budget
    # ────────────────────────────────────────────────
    if not df_result.empty:
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.subheader("Plan de renouvellement priorisé")
            display = pd.DataFrame()
            display["Priorité"] = df_result["priorite"].values
            display["Tronçon"] = df_result[id_col].map(_normalize_id).values
            if col_map["famille_materiau"] in df_result.columns:
                display["Matériau"] = df_result[col_map["famille_materiau"]].values
            display["Score"] = df_result[score_col].apply(lambda x: f"{x * 100:.1f} %").values
            if "longueur_ml" in df_result.columns:
                display["Longueur"] = df_result["longueur_ml"].apply(lambda x: f"{x:.0f} m").values
            display["Coût estimé"] = df_result["cout_unitaire"].apply(lambda x: f"{x:,.0f} €".replace(",", " ")).values
            st.dataframe(display, use_container_width=True, hide_index=True, height=400)

        with col_right:
            st.subheader("Répartition du budget")
            budget_restant = budget - kpis["budget_utilise"]
            fig = go.Figure(go.Pie(
                labels=["Budget consommé", "Budget restant"],
                values=[kpis["budget_utilise"], max(0, budget_restant)],
                hole=0.6,
                marker_colors=["#d32f2f", "#e0e0e0"],
                textinfo="label+percent",
                textposition="outside",
            ))
            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                annotations=[dict(
                    text=f"<b>{kpis['budget_utilise']:,.0f} €</b>".replace(",", " "),
                    x=0.5, y=0.5, font_size=14, showarrow=False,
                )],
            )
            st.plotly_chart(fig, use_container_width=True)

            # Histogramme des scores du plan
            if score_col in df_result.columns:
                st.markdown("**Distribution des scores du plan**")
                fig2 = go.Figure(go.Histogram(
                    x=df_result[score_col] * 100,
                    nbinsx=15,
                    marker_color="#d32f2f",
                ))
                fig2.update_layout(
                    height=200,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_title="Score (%)",
                    yaxis_title="Tronçons",
                    showlegend=False,
                )
                st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # Export
        exp_c1, exp_c2 = st.columns(2)
        csv_data = display.to_csv(index=False, sep=";", encoding="utf-8")
        with exp_c1:
            st.download_button(
                "Exporter le plan en CSV",
                csv_data,
                file_name=f"plan_renouvellement_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with exp_c2:
            try:
                pdf_bytes = _build_pdf(kpis, df_result, horizon, budget, id_col)
                st.download_button(
                    "Exporter le plan en PDF",
                    pdf_bytes,
                    file_name=f"plan_renouvellement_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.caption(f"Export PDF indisponible : {e}")
