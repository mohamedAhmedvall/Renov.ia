"""Pattern **Repository** — accès aux tronçons abstrait derrière une interface.

L'API et l'optimiseur demandent « les tronçons scorés » au repository sans
savoir d'où ils viennent. L'implémentation fournie lit les CSV synthétiques
(via l'Adapter) et joint les scores ML ; une implémentation base de données
ou API SIG se substituerait sans toucher les appelants (inversion de
dépendance : le domaine définit le port, l'infrastructure l'implémente).
"""

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from domain.adapters import SyntheticCsvAdapter


class TronconRepository(ABC):
    """Port du domaine : fournit le patrimoine, avec ou sans scores."""

    @abstractmethod
    def get_troncons(self) -> pd.DataFrame: ...

    @abstractmethod
    def get_troncons_scores(self) -> pd.DataFrame:
        """Tronçons + colonnes score_h1/score_h3/score_h5 si disponibles."""


class CsvTronconRepository(TronconRepository):
    """Implémentation fichier : CSV synthétiques + scores produits par ml/."""

    def __init__(self, data_dir: str | Path, scores_path: str | Path | None = None):
        self.data_dir = Path(data_dir)
        self.scores_path = Path(scores_path) if scores_path else self.data_dir / "scores.csv"

    def get_troncons(self) -> pd.DataFrame:
        adapter = SyntheticCsvAdapter(self.data_dir / "troncons.csv")
        df = adapter.load()
        abonnes_path = self.data_dir / "abonnes.csv"
        if abonnes_path.exists():
            abonnes = pd.read_csv(abonnes_path)
            df = df.merge(abonnes, left_on="id_troncon", right_on="id_troncon", how="left")
        return df

    def get_troncons_scores(self) -> pd.DataFrame:
        df = self.get_troncons()
        if self.scores_path.exists():
            scores = pd.read_csv(self.scores_path)
            df = df.merge(scores, on="id_troncon", how="left")
        return df
