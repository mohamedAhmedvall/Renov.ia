"""Pattern **Adapter** — adapte une source brute au modèle attendu par le domaine.

Le domaine attend des colonnes canoniques (`diametre_mm`, `famille_materiau`,
`longueur_m`, `annee_pose`…). Chaque source (CSV synthétique ici ; SIG client,
base Oracle… dans le produit) a son adaptateur qui isole le renommage et les
casts — le domaine ne voit jamais les noms de colonnes d'origine.
"""

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

# Colonnes canoniques minimales attendues par le domaine.
CANONICAL_COLUMNS = ["id_troncon", "famille_materiau", "diametre_mm", "longueur_m", "annee_pose"]


class SourceAdapter(ABC):
    """Interface : produit un DataFrame aux colonnes canoniques."""

    @abstractmethod
    def load(self) -> pd.DataFrame: ...

    @staticmethod
    def validate(df: pd.DataFrame) -> pd.DataFrame:
        """Validation souple : colonnes requises présentes, types castés."""
        missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Colonnes canoniques manquantes : {missing}")
        df = df.copy()
        for col in ("diametre_mm", "longueur_m", "annee_pose"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df


class SyntheticCsvAdapter(SourceAdapter):
    """Adapte le jeu synthétique (data/synthetic/) au modèle canonique.

    Le générateur écrit déjà des noms proches du canonique — l'adaptateur
    matérialise malgré tout le mapping pour montrer où brancherait une vraie
    source (ex. référentiel SIG avec DIAMETRE/MATERIAU/DATEPOSE).
    """

    MAPPING = {
        "id": "id_troncon",
        "materiau_famille": "famille_materiau",
        "diametre": "diametre_mm",
        "longueur": "longueur_m",
        "annee_pose": "annee_pose",
    }

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        df = pd.read_csv(self.path)
        df = df.rename(columns=self.MAPPING)
        return self.validate(df)
