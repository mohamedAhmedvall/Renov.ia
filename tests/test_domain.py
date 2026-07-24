"""Tests unitaires du domaine : typologie, conséquence (patterns), Note 1–5."""

import pandas as pd

from domain import compute_notes
from domain.factory import build_consequence_calculator
from domain.models import compute_typologie
from domain.note import compute_note


def test_typologie_seuils(mini_troncons, config):
    typo = compute_typologie(mini_troncons, config)
    assert typo.tolist() == ["transport", "branchement", "distribution", "distribution"]


def test_typologie_diametre_manquant(config):
    df = pd.DataFrame({"diametre_mm": [None], "famille_materiau": ["Fonte"]})
    assert compute_typologie(df, config).iloc[0] == "indetermine"


def test_consequence_bornee_et_ordonnee(mini_troncons, config):
    df = mini_troncons.copy()
    df["typologie"] = compute_typologie(df, config)
    cons = build_consequence_calculator(config).compute(df, config)
    assert ((cons >= 0) & (cons <= 1)).all()
    # Le feeder de transport domine le branchement dé-pondéré.
    assert cons.iloc[0] > cons.iloc[1]


def test_factory_desactive_composante_poids_nul(config):
    cfg = {**config, "consequence": {**config["consequence"], "poids": {"typologie": 1.0}}}
    calc = build_consequence_calculator(cfg)
    assert len(calc.base) == 1 and not calc.boosts


def test_note_quantiles_et_bornes(config):
    proba = pd.Series([0.01 * i for i in range(100)])
    cons = pd.Series([0.5] * 100)
    note = compute_note(proba, cons, config)
    assert note.min() == 1 and note.max() == 5
    # Monotonie : un risque plus élevé ne peut pas avoir une note plus basse.
    assert (note.diff().dropna() >= 0).all()


def test_plafond_note_branchement(mini_troncons, config):
    df = mini_troncons.copy()
    # Force le branchement au risque max : sans plafond il serait note 5.
    df.loc[df["diametre_mm"] == 60, "score_h3"] = 0.99
    out = compute_notes(df, config)
    cap = config["priorisation"]["note_max_branchement"]
    assert (out.loc[out["typologie"] == "branchement", "note_h3"] <= cap).all()
