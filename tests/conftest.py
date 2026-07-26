"""Fixtures partagées — rend les packages du dépôt importables sans installation."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from domain import DEFAULT_CONFIG  # noqa: E402
from domain.repository import CsvTronconRepository  # noqa: E402

# Les tests s'appuient sur une ville de référence ; les autres partagent
# strictement le même générateur, le même pipeline et le même domaine.
VILLE_TEST = "marseille"
DATA_DIR = ROOT / "data" / "synthetic" / VILLE_TEST


@pytest.fixture(scope="session")
def config() -> dict:
    return DEFAULT_CONFIG


@pytest.fixture(scope="session")
def troncons_scores(config) -> pd.DataFrame:
    """Jeu synthétique complet enrichi par le domaine (typologie, conséquence, notes)."""
    from domain import compute_notes

    repo = CsvTronconRepository(DATA_DIR)
    df = repo.get_troncons_scores()
    return compute_notes(df, config)


@pytest.fixture(scope="session")
def mini_troncons() -> pd.DataFrame:
    """Petit patrimoine contrôlé pour les tests unitaires (indépendant du CSV)."""
    return pd.DataFrame(
        {
            "id_troncon": ["T1", "T2", "T3", "T4"],
            "famille_materiau": ["Fonte", "Plastique", "Fonte", "Plastique"],
            "materiau": ["Fonte grise", "PVC", "Fonte ductile", "PEHD"],
            "diametre_mm": [400, 60, 150, 110],
            "longueur_m": [500.0, 30.0, 200.0, 120.0],
            "annee_pose": [1955, 1978, 1995, 2015],
            "nb_abonne": [0, 3, 40, 25],
            "nb_abonne_sensible": [0, 0, 2, 0],
            "nb_abonne_tres_sensible": [0, 0, 1, 0],
            "score_h3": [0.30, 0.25, 0.10, 0.02],
        }
    )
