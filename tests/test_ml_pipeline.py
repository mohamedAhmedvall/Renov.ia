"""Tests du pipeline ML : anti-fuite, offset d'exposition, calibration, backtest."""

import numpy as np
import pytest

from ml.features import build_features, load_sources
from ml.model import predict_proba_horizon, train_poisson_model
from tests.conftest import DATA_DIR


@pytest.fixture(scope="module")
def sources():
    return load_sources(DATA_DIR)


def test_features_anti_fuite(sources):
    """Les features à l'année N n'utilisent que des casses < N."""
    troncons, casses = sources
    X, y, expo, _ = build_features(troncons, casses, observation_year=2015, horizon=3)
    total_passe = (casses["annee"] < 2015).sum()
    assert X["nb_casses_passees"].sum() == total_passe
    # La cible ne compte que la fenêtre [2015, 2018)
    fenetre = casses[(casses["annee"] >= 2015) & (casses["annee"] < 2018)]
    assert y.sum() == len(fenetre)


def test_fit_state_transmis_sans_refit(sources):
    """L'encodage matériau du test provient du train (fit_state), pas d'un re-fit."""
    troncons, casses = sources
    _, _, _, fit_state = build_features(troncons, casses, 2015, 3)
    X_te, _, _, state_out = build_features(troncons, casses, 2020, 3, fit_state)
    assert state_out is fit_state
    valeurs_train = set(fit_state["te_materiau"].values()) | {fit_state["te_default"]}
    assert set(X_te["te_materiau"].round(9)) <= {round(v, 9) for v in valeurs_train}


def test_probas_calibrees_bornees(sources):
    troncons, casses = sources
    X, y, expo, fs = build_features(troncons, casses, 2015, 3)
    model = train_poisson_model(X, y, expo, n_estimators=30)
    p = predict_proba_horizon(model, X, expo)
    assert ((p >= 0) & (p <= 1)).all()


def test_offset_monotone_en_longueur(sources):
    """À features égales, doubler l'exposition doit augmenter la probabilité."""
    troncons, casses = sources
    X, y, expo, _ = build_features(troncons, casses, 2015, 3)
    model = train_poisson_model(X, y, expo, n_estimators=30)
    p1 = predict_proba_horizon(model, X.head(50), expo.head(50))
    p2 = predict_proba_horizon(model, X.head(50), expo.head(50) * 2)
    assert (p2 >= p1 - 1e-9).all()


@pytest.mark.slow
def test_backtest_bat_l_aleatoire(sources):
    """Sur données synthétiques au processus connu, le modèle doit battre le hasard."""
    from ml.backtest import backtest_temporel

    troncons, casses = sources
    bt = backtest_temporel(troncons, casses, fenetres=[2017, 2020], horizon=3, n_estimators=60)
    assert (bt["capture_lineaire_20pct"] > 0.25).all()  # nettement > 20 % aléatoire


def test_capture_lineaire_parfaite():
    """Cas contrôlé : si le score ordonne parfaitement, la capture est maximale."""
    import pandas as pd

    from ml.backtest import capture_lineaire_at

    y = pd.Series([5, 0, 0, 0, 0])
    km = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0])
    scores = np.array([0.9, 0.1, 0.1, 0.1, 0.1])
    assert capture_lineaire_at(scores, y, km, pct=0.20) == 1.0
