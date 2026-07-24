"""Tests unitaires de l'optimiseur : budget, formulation Poisson, déterminisme."""

import numpy as np
import pytest

from optimizer import optimize_renewal


@pytest.fixture()
def df_opt(mini_troncons, config):
    from domain import compute_notes

    return compute_notes(mini_troncons, config)


def test_budget_respecte(df_opt):
    res = optimize_renewal(df_opt, budget=50_000)
    assert res["cout_total"] <= 50_000


def test_budget_nul_selection_vide(df_opt):
    res = optimize_renewal(df_opt, budget=1)
    assert res["nb_troncons"] == 0 and res["casses_evitees"] == 0


def test_benefice_poisson_positif_et_ic(df_opt):
    res = optimize_renewal(df_opt, budget=10_000_000)
    assert res["casses_evitees"] > 0
    attendu = 1.96 * np.sqrt(res["casses_evitees"])
    assert res["casses_evitees_ic95"] == pytest.approx(attendu, abs=0.02)


def test_deterministe(df_opt):
    r1 = optimize_renewal(df_opt, budget=100_000)
    r2 = optimize_renewal(df_opt, budget=100_000)
    assert r1["ids"] == r2["ids"]


def test_score_manquant_leve(mini_troncons):
    with pytest.raises(ValueError, match="score_h5"):
        optimize_renewal(mini_troncons, budget=1000, params={"horizon": 5})


def test_priorise_meilleur_ratio(df_opt):
    # Avec un budget serré, l'optimiseur doit préférer le meilleur ratio
    # bénéfice/coût — pas simplement le score le plus élevé.
    res = optimize_renewal(df_opt, budget=30_000)
    assert res["nb_troncons"] >= 1
    assert "T1" not in res["ids"]  # le feeder de 500 m coûte bien plus que 30 k€
