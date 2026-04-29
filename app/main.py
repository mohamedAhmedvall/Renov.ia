"""Point d'entrée de l'application Streamlit — sidebar, session_state, routing vues."""

import streamlit as st

from data_loader import (
    load_backtesting,
    load_config,
    load_geodata,
    load_referentiel,
    load_scoring,
    load_shap,
)
from filters import apply_filters
from views import carte, dashboard, detail, optimiseur, tableau

# --- Configuration de la page ---
st.set_page_config(
    page_title="Scoring Canalisations",
    page_icon="🔧",
    layout="wide",
)


# --- Chargement de la configuration ---
config = load_config()

# --- Fonction de rechargement des données ---

# --- Gestion du rechargement des données ---
if "reload_flag" not in st.session_state:
    st.session_state["reload_flag"] = False


def reload_data():
    st.session_state["reload_flag"] = not st.session_state["reload_flag"]
    st.session_state["filtres"] = DEFAULTS["filtres"].copy()
    st.session_state["horizon"] = DEFAULTS["horizon"]
    st.session_state["troncon_selectionne"] = DEFAULTS["troncon_selectionne"]
    st.session_state["vue_active"] = DEFAULTS["vue_active"]
    st.session_state["budget_enveloppe"] = DEFAULTS["budget_enveloppe"]
    st.session_state["taux_renouvellement"] = DEFAULTS["taux_renouvellement"]
    st.session_state["materiau_remplacement"] = DEFAULTS["materiau_remplacement"]
    st.session_state["type_chantier"] = DEFAULTS["type_chantier"]
    st.session_state["troncons_forces"] = set()
    st.session_state["troncons_exclus"] = set()
    st.session_state["contrainte_1pct"] = True


# --- Initialisation session_state ---
DEFAULTS = {
    "filtres": {},
    "horizon": config.get("default_horizon", 3),
    "troncon_selectionne": None,
    "vue_active": "Dashboard",  # Dashboard par défaut
    "budget_enveloppe": 500_000,
    "taux_renouvellement": 0.01,
    "materiau_remplacement": "fonte_ductile",
    "type_chantier": "urbain_standard",
    "troncons_forces": set(),
    "troncons_exclus": set(),
    "contrainte_1pct": True,
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# --- Chargement des données ---
@st.cache_data(show_spinner="Chargement des données…")
def get_all_data(config):
    return {
        "df_scoring": load_scoring(config),
        "df_referentiel": load_referentiel(config),
        "df_shap": load_shap(config),
        "df_backtesting": load_backtesting(config),
        "gdf": load_geodata(config),
    }


if st.session_state["reload_flag"]:
    get_all_data.clear()
    st.session_state["reload_flag"] = False
    st.rerun()

data = get_all_data(config)
df_scoring = data["df_scoring"]
df_referentiel = data["df_referentiel"]
df_shap = data["df_shap"]
df_backtesting = data["df_backtesting"]
gdf = data["gdf"]


# Arrêt propre si données critiques manquantes
if df_scoring is None:
    st.error("Erreur critique : données de scoring manquantes ou corrompues.")

    if st.button("Recharger les données"):
        reload_data()
        st.rerun()
    st.stop()


# --- Sidebar : Navigation ---
# On masque la page Détail
VUES = ["Audit patrimoine", "Détails par tronçons", "Carte du réseau", "Optimiseur"]

with st.sidebar:
    # Si on est sur Détail (vue masquée), on garde la radio sur la dernière vue principale
    active = st.session_state.get("vue_active", "Audit patrimoine")
    if active not in VUES and active != "Détail":
        active = "Audit patrimoine"
        st.session_state.vue_active = active
    current_main_vue = (
        active if active in VUES else st.session_state.get("last_main_vue", "Audit patrimoine")
    )
    vue = st.radio("Navigation", VUES, index=VUES.index(current_main_vue))
    # On n'écrase vue_active QUE si l'utilisateur a réellement changé de vue dans la sidebar
    if vue != current_main_vue or active in VUES:
        st.session_state.vue_active = vue
        st.session_state.last_main_vue = vue

    # Bouton rechargement données
    st.button("Recharger les données", on_click=reload_data)

    # Bouton réinitialisation des filtres
    if st.button("Réinitialiser les filtres"):
        st.session_state["filtres"] = DEFAULTS["filtres"].copy()
        st.rerun()

    st.divider()

    # --- Horizon de prédiction ---
    horizon = st.radio(
        "Horizon",
        [1, 3, 5],
        index=[1, 3, 5].index(st.session_state.horizon),
        format_func=lambda x: f"{x} an{'s' if x > 1 else ''}",
        horizontal=True,
    )
    st.session_state.horizon = horizon

    st.divider()

    # --- Filtres réactifs ---
    col_map = config["column_mapping"]

    materiaux_disponibles = sorted(
        df_scoring[col_map["famille_materiau"]].dropna().unique().tolist()
    )
    materiaux = st.multiselect(
        "Matériau",
        materiaux_disponibles,
        default=st.session_state.filtres.get("materiaux", []),
    )

    score_min = st.slider(
        "Score min (%)",
        0,
        100,
        int(st.session_state.filtres.get("score_min", 0) * 100),
        5,
        help="Seuil minimum de score de risque",
    )

    age_vals = df_scoring[col_map["age"]].dropna()
    age_range = st.slider(
        "Âge (ans)",
        int(age_vals.min()),
        int(age_vals.max()),
        (
            st.session_state.filtres.get("age_min", int(age_vals.min())),
            st.session_state.filtres.get("age_max", int(age_vals.max())),
        ),
    )

    diam_vals = df_scoring[col_map["diametre"]].dropna()
    diam_range = st.slider(
        "Diamètre (mm)",
        int(diam_vals.min()),
        int(diam_vals.max()),
        (
            st.session_state.filtres.get("diametre_min", int(diam_vals.min())),
            st.session_state.filtres.get("diametre_max", int(diam_vals.max())),
        ),
    )

    # Mise à jour des filtres dans session_state
    st.session_state.filtres = {
        "materiaux": materiaux,
        "score_min": score_min / 100.0,
        "age_min": age_range[0],
        "age_max": age_range[1],
        "diametre_min": diam_range[0],
        "diametre_max": diam_range[1],
    }

    # Affichage dynamique des filtres actifs
    filtres_actifs = []
    if materiaux:
        filtres_actifs.append(f"Matériau: {', '.join(materiaux)}")
    if score_min > 0:
        filtres_actifs.append(f"Score min: {score_min}%")
    if age_range != (int(age_vals.min()), int(age_vals.max())):
        filtres_actifs.append(f"Âge: {age_range[0]}-{age_range[1]} ans")
    if diam_range != (int(diam_vals.min()), int(diam_vals.max())):
        filtres_actifs.append(f"Diamètre: {diam_range[0]}-{diam_range[1]} mm")
    if filtres_actifs:
        st.info("Filtres actifs : " + ", ".join(filtres_actifs))

    st.divider()

    # Section Aide/À propos
    with st.expander("ℹ️ Aide / À propos", expanded=False):
        st.markdown("""
**Scoring Canalisations**

Ce dashboard permet d'explorer le risque de casse sur le réseau de canalisations.

**Scores** : calculés par modèle prédictif, ils représentent la probabilité de casse sur l'horizon choisi.

**Filtres** : permettent de cibler les tronçons selon matériau, âge, diamètre, etc.

**Méthodologie** : voir documentation technique pour le détail des modèles et des données utilisées.
        """)

    # --- Filtrage ---
    df_filtered = apply_filters(
        df_scoring, st.session_state.filtres, config, st.session_state.horizon
    )

    # Compteur tronçons
    total = len(df_scoring)
    filtered = len(df_filtered)
    st.caption(f"**{filtered:,} / {total:,} tronçons**".replace(",", " "))

# --- Routing des vues ---
VUE_RENDERERS = {
    "Détails par tronçons": tableau.render,
    "Carte du réseau": carte.render,
    "Audit patrimoine": dashboard.render,
    "Optimiseur": optimiseur.render,
    "Détail": detail.render,
}

renderer = VUE_RENDERERS.get(st.session_state.vue_active)
if renderer:
    extra_kwargs = {}
    if st.session_state.vue_active == "Carte du réseau":
        # Passer la sélection de tronçons à la carte pour surlignage
        extra_kwargs["troncons_selectionnes"] = st.session_state.get(
            "troncons_selectionnes", set()
        )
    renderer(
        df_filtered,
        df_referentiel,
        config,
        df_shap=df_shap,
        df_backtesting=df_backtesting,
        df_scoring_full=df_scoring,
        gdf=gdf,
        **extra_kwargs,
    )
