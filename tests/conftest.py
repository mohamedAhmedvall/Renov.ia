"""Fixtures partagées pour les tests."""

import sys
import os

import numpy as np
import pandas as pd
import pytest

# Ajouter app/ au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


@pytest.fixture
def sample_config():
    """Configuration minimale pour les tests."""
    return {
        "data_paths": {
            "scoring": "../V8/output/v8_scoring_fuites.csv",
            "referentiel": "../data/canalisation_sem_3_1_.csv",
            "shap_importance": "../V8/output/v8_shap_importance.csv",
            "backtesting": "../V8/output/v8_backtesting.csv",
            "geodata": "../data/troncons.gpkg",
        },
        "column_mapping": {
            "id_troncon": "OBJET",
            "materiau": "MATERIAU",
            "diametre": "DIAMETRE",
            "famille_materiau": "famille_mat",
            "age": "age",
        },
        "risk_thresholds": {"critique": 0.8, "eleve": 0.6, "modere": 0.3},
        "risk_colors": {"critique": "#d32f2f", "eleve": "#ff9800", "modere": "#fdd835", "faible": "#4caf50"},
        "risk_labels": {"critique": "Critique", "eleve": "Élevé", "modere": "Modéré", "faible": "Faible"},
        "couts_remplacement": {"urbain_dense": 450, "urbain_standard": 300, "rural": 180},
        "materiaux_remplacement": {"fonte_ductile": {"cout_majorant": 1.0, "duree_vie_estimee": 80}},
        "km_total_reseau": 100,
        "export": {"encoding": "utf-8", "separator": ";"},
    }


@pytest.fixture
def sample_scoring_df():
    """DataFrame scoring de test avec 20 tronçons."""
    rng = np.random.RandomState(42)
    n = 20
    return pd.DataFrame({
        "OBJET": [f"T{i:04d}" for i in range(n)],
        "MATERIAU": rng.choice(["Fonte", "AC", "PVC", "PEHD"], n),
        "DIAMETRE": rng.choice([100, 150, 200, 300], n).astype(float),
        "famille_mat": rng.choice(["Fonte_grise", "Amiante_ciment", "PVC", "PEHD"], n),
        "age": rng.randint(5, 80, n).astype(float),
        "LONGUEUR": rng.uniform(10, 500, n),
        "score_h1": rng.uniform(0, 1, n),
        "score_h3": rng.uniform(0, 1, n),
        "score_h5": rng.uniform(0, 1, n),
        "classe_h1": rng.choice(["critique", "eleve", "modere", "faible"], n),
        "classe_h3": rng.choice(["critique", "eleve", "modere", "faible"], n),
        "classe_h5": rng.choice(["critique", "eleve", "modere", "faible"], n),
        "rang": list(range(1, n + 1)),
        "top_pct": np.linspace(0, 100, n),
        "icp": rng.uniform(50, 100, n),
    })


@pytest.fixture
def sample_referentiel_df():
    """DataFrame référentiel de test."""
    rng = np.random.RandomState(42)
    n = 20
    return pd.DataFrame({
        "OBJET": [f"T{i:04d}" for i in range(n)],
        "STATUT_OBJET": "en_service",
        "MATERIAU": rng.choice(["Fonte", "AC", "PVC", "PEHD"], n),
        "DIAMETRE": rng.choice([100, 150, 200, 300], n).astype(float),
        "LONGUEUR": rng.uniform(10, 500, n),
        "POSE": rng.choice(["1960", "1970", "1980", "1990", "2000"], n),
    })


@pytest.fixture
def sample_backtesting_df():
    """DataFrame backtesting de test."""
    return pd.DataFrame({
        "window": ["obs2012_h3", "obs2015_h3", "obs2018_h3"],
        "auc": [0.885, 0.865, 0.825],
        "capture_top20": [80.4, 76.2, 68.6],
        "n_test": [50048, 49228, 48104],
        "n_pos_test": [367, 428, 439],
        "ap": [0.24, 0.15, 0.11],
    })
