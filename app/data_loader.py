"""Chargement des données CSV/GeoJSON, validation souple et cache Streamlit."""

import os

import pandas as pd
import streamlit as st
import yaml

from data_schemas import (
    BACKTESTING_REQUIRED_COLUMNS,
    ICP_FIELDS,
    REFERENTIEL_DTYPES,
    REFERENTIEL_REQUIRED_COLUMNS,
    SCORING_DTYPES,
    SCORING_REQUIRED_COLUMNS,
    SHAP_REQUIRED_COLUMNS,
)


def load_config(config_path: str = None) -> dict:
    """Charge la configuration depuis config.yaml."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_path(relative_path: str) -> str:
    """Résout un chemin relatif par rapport au dossier app/."""
    base = os.path.dirname(__file__)
    return os.path.normpath(os.path.join(base, relative_path))


def _validate_columns(df: pd.DataFrame, required: list, file_label: str) -> list:
    """Vérifie la présence des colonnes requises. Retourne la liste des colonnes manquantes."""
    missing = [col for col in required if col not in df.columns]
    return missing


def _cast_numeric(df: pd.DataFrame, dtypes: dict) -> tuple[pd.DataFrame, dict]:
    """Caste les colonnes numériques avec errors='coerce'. Retourne (df, warnings_dict)."""
    warnings = {}
    for col, dtype in dtypes.items():
        if col not in df.columns:
            continue
        if dtype == "float":
            original_notna = df[col].notna().sum()
            series = df[col]
            if series.dtype == object:
                series = series.astype(str).str.strip().str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(series, errors="coerce")
            new_notna = df[col].notna().sum()
            lost = original_notna - new_notna
            if lost > 0:
                warnings[col] = lost
        elif dtype == "int":
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(0).astype(int)
        elif dtype == "str":
            df[col] = df[col].fillna("").astype(str)
            df[col] = df[col].replace({"nan": "", "None": "", "none": ""})
    return df, warnings


def _classify_risk(score: float, thresholds: dict) -> str:
    """Retourne la classe de risque pour un score donné."""
    if score >= thresholds["critique"]:
        return "critique"
    elif score >= thresholds["eleve"]:
        return "eleve"
    elif score >= thresholds["modere"]:
        return "modere"
    else:
        return "faible"


def _compute_icp(df: pd.DataFrame) -> pd.Series:
    """Calcule l'Indice de Connaissance Patrimoniale par tronçon (0-100%)."""
    icp_cols = [col for col in ICP_FIELDS if col in df.columns]
    if not icp_cols:
        return pd.Series(0.0, index=df.index)
    filled = df[icp_cols].notna().sum(axis=1)
    # Pour les colonnes string, "" compte aussi comme manquant
    for col in icp_cols:
        if df[col].dtype == object:
            filled = filled - (df[col].isin(["", "nan", "None"])).astype(int)
    return (filled / len(icp_cols) * 100).round(1)


@st.cache_data(show_spinner="Chargement des données de scoring…")
def load_scoring(config: dict) -> pd.DataFrame | None:
    """Charge et valide le fichier scoring CSV."""
    path = _resolve_path(config["data_paths"]["scoring"])

    if not os.path.exists(path):
        st.error(f"Fichier de scoring introuvable. Vérifiez le chemin dans config.yaml.\n\nChemin configuré : `{path}`")
        return None

    try:
        df = pd.read_csv(path)
    except Exception:
        st.error("Impossible de lire le fichier de scoring. Vérifiez que le format CSV est correct.")
        return None

    # Validation colonnes
    missing = _validate_columns(df, SCORING_REQUIRED_COLUMNS, "scoring")
    if missing:
        st.error(f"Colonnes requises manquantes dans le fichier scoring : {', '.join(missing)}")
        return None

    # Casting types
    df, cast_warnings = _cast_numeric(df, SCORING_DTYPES)
    for col, count in cast_warnings.items():
        st.warning(f"{count} valeurs non numériques dans la colonne '{col}', converties en NaN.")

    # Classification risque par quantiles (scores V9 calibrés ⇒ pas de seuils absolus)
    quants = config.get("risk_quantiles")
    if quants:
        for horizon in ["h1", "h3", "h5"]:
            score_col = f"score_{horizon}"
            classe_col = f"classe_{horizon}"
            if score_col not in df.columns:
                continue
            s = pd.to_numeric(df[score_col], errors="coerce")
            q_crit = s.quantile(quants["critique"])
            q_elev = s.quantile(quants["eleve"])
            q_mod = s.quantile(quants["modere"])
            cls = pd.Series("faible", index=df.index)
            cls[s >= q_mod] = "modere"
            cls[s >= q_elev] = "eleve"
            cls[s >= q_crit] = "critique"
            df[classe_col] = cls
    else:
        thresholds = config["risk_thresholds"]
        for horizon in ["h1", "h3", "h5"]:
            score_col = f"score_{horizon}"
            classe_col = f"classe_{horizon}"
            if score_col in df.columns:
                df[classe_col] = df[score_col].apply(lambda s: _classify_risk(s, thresholds) if pd.notna(s) else "faible")

    # ICP scoring (basé sur les colonnes de scoring disponibles)
    df["icp"] = _compute_icp(df)

    # Enrichir avec LONGUEUR du référentiel si disponible (pour SHAP local)
    ref_path = _resolve_path(config["data_paths"]["referentiel"])
    if os.path.exists(ref_path):
        try:
            df_ref = pd.read_csv(ref_path, usecols=["OBJET", "LONGUEUR"])
            df_ref["OBJET"] = df_ref["OBJET"].astype(str)
            df["OBJET"] = df["OBJET"].astype(str)
            if "LONGUEUR" not in df.columns:
                df = df.merge(df_ref[["OBJET", "LONGUEUR"]], on="OBJET", how="left")
        except Exception:
            pass

    return df


@st.cache_data(show_spinner="Chargement du référentiel patrimonial…")
def load_referentiel(config: dict) -> pd.DataFrame | None:
    """Charge et valide le fichier référentiel CSV."""
    path = _resolve_path(config["data_paths"]["referentiel"])

    if not os.path.exists(path):
        st.error(f"Fichier référentiel introuvable. Vérifiez le chemin dans config.yaml.\n\nChemin configuré : `{path}`")
        return None

    try:
        df = pd.read_csv(path)
    except Exception:
        st.error("Impossible de lire le fichier référentiel. Vérifiez que le format CSV est correct.")
        return None

    # Validation colonnes
    missing = _validate_columns(df, REFERENTIEL_REQUIRED_COLUMNS, "referentiel")
    if missing:
        st.warning(f"Colonnes manquantes dans le fichier référentiel : {', '.join(missing)}")

    # Casting types
    df, cast_warnings = _cast_numeric(df, REFERENTIEL_DTYPES)
    for col, count in cast_warnings.items():
        st.warning(f"Référentiel : {count} valeurs non numériques dans '{col}', converties en NaN.")

    return df


@st.cache_data(show_spinner="Chargement SHAP…")
def load_shap(config: dict) -> pd.DataFrame | None:
    """Charge le fichier SHAP importance."""
    path = _resolve_path(config["data_paths"]["shap_importance"])

    if not os.path.exists(path):
        st.info("Fichier SHAP importance non trouvé — explicabilité désactivée.")
        return None

    try:
        df = pd.read_csv(path)
    except Exception:
        st.warning("Impossible de lire le fichier SHAP importance.")
        return None

    missing = _validate_columns(df, SHAP_REQUIRED_COLUMNS, "shap")
    if missing:
        st.warning(f"Colonnes manquantes dans SHAP : {', '.join(missing)}")
        return None

    return df


@st.cache_data(show_spinner="Chargement backtesting…")
def load_backtesting(config: dict) -> pd.DataFrame | None:
    """Charge le fichier backtesting."""
    path = _resolve_path(config["data_paths"]["backtesting"])

    if not os.path.exists(path):
        st.info("Fichier backtesting non trouvé — courbe Lift désactivée.")
        return None

    try:
        df = pd.read_csv(path)
    except Exception:
        st.warning("Impossible de lire le fichier backtesting.")
        return None

    missing = _validate_columns(df, BACKTESTING_REQUIRED_COLUMNS, "backtesting")
    if missing:
        st.warning(f"Colonnes manquantes dans backtesting : {', '.join(missing)}")
        return None

    return df


@st.cache_data(show_spinner="Chargement des géométries…")
def load_geodata(config: dict):
    """Charge les géométries depuis geo.csv (WKT en EPSG:3944) ou GeoPackage. Retourne un GeoDataFrame ou None."""
    import geopandas as gpd
    from shapely import wkt

    # Priorité 1 : geo.csv (WKT + CRS connu)
    geo_csv_path = _resolve_path(config["data_paths"].get("geo_csv", "../data/geo.csv"))
    if os.path.exists(geo_csv_path):
        try:
            df_geo = pd.read_csv(geo_csv_path)
            df_geo["geometry"] = df_geo["WKT_GEOM"].apply(wkt.loads)
            gdf = gpd.GeoDataFrame(df_geo[["GID", "geometry"]], geometry="geometry", crs="EPSG:3944")
            gdf = gdf.to_crs(epsg=4326)
            return gdf
        except Exception as e:
            st.warning(f"Erreur lecture geo.csv : {e}")

    # Priorité 2 : GeoPackage / GeoJSON (fallback)
    path = _resolve_path(config["data_paths"].get("geodata", ""))
    if not os.path.exists(path):
        return None

    try:
        gdf = gpd.read_file(path)
        if gdf.crs and not gdf.crs.is_geographic:
            gdf = gdf.to_crs(epsg=4326)
        return gdf
    except Exception:
        return None
