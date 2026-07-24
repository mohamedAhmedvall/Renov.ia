"""Pattern **Strategy** — composantes interchangeables du score de conséquence.

Chaque stratégie transforme le DataFrame des tronçons en une contribution
[0,1]. Le calculateur (`ConsequenceCalculator`) les combine sans connaître
leur logique interne ; en ajouter une nouvelle (ex. proximité d'un hôpital,
voirie structurante) ne modifie aucun code existant (ouvert/fermé).
"""

from abc import ABC, abstractmethod

import pandas as pd


class ConsequenceStrategy(ABC):
    """Interface commune : une composante pondérée de la conséquence."""

    def __init__(self, weight: float):
        self.weight = weight

    @abstractmethod
    def score(self, df: pd.DataFrame, config: dict) -> pd.Series:
        """Contribution brute [0,1] de la composante (avant pondération)."""


class TypologieStrategy(ConsequenceStrategy):
    """Criticité structurelle : un feeder de transport casse → tout un secteur privé d'eau."""

    def score(self, df: pd.DataFrame, config: dict) -> pd.Series:
        score_map = config["consequence"].get("typologie_score", {})
        typo = df.get("typologie")
        if typo is None:
            return pd.Series(0.3, index=df.index)
        return typo.map(score_map).fillna(0.3)


class DiametreStrategy(ConsequenceStrategy):
    """Proxy du débit transité : normalisé par un diamètre de référence."""

    def score(self, df: pd.DataFrame, config: dict) -> pd.Series:
        col = config["column_mapping"]["diametre"]
        diam_ref = config["consequence"].get("diametre_ref_mm", 300) or 300
        diam = pd.to_numeric(df.get(col), errors="coerce")
        return (diam / diam_ref).clip(upper=1.0).fillna(0.3)


class AbonnesStrategy(ConsequenceStrategy):
    """Population desservie (donnée externe) : boost additif, jamais pénalisant.

    Les abonnés sensibles (écoles, EHPAD…) et très sensibles (hôpitaux, dialyse)
    reçoivent un surpoids. Renvoie 0 quand la donnée est absente : un feeder
    sans abonné direct tire déjà sa criticité de sa typologie.
    """

    def score(self, df: pd.DataFrame, config: dict) -> pd.Series:
        c = config["consequence"].get("abonnes", {})
        ref = float(c.get("ref_abonnes", 100)) or 100.0
        w_sens = float(c.get("poids_sensible", 3.0))
        w_tres = float(c.get("poids_tres_sensible", 6.0))
        if "nb_abonne" not in df.columns:
            return pd.Series(0.0, index=df.index)
        nb = pd.to_numeric(df["nb_abonne"], errors="coerce")

        def _col(name: str) -> pd.Series:
            if name in df.columns:
                return pd.to_numeric(df[name], errors="coerce").fillna(0)
            return pd.Series(0.0, index=df.index)

        sens = _col("nb_abonne_sensible")
        tres = _col("nb_abonne_tres_sensible")
        # Les sensibles sont déjà comptés dans nb_abonne : surpoids, pas doublon.
        pondere = nb.fillna(0) + (w_sens - 1) * sens + (w_tres - w_sens) * tres
        score = (pondere / ref).clip(upper=1.0)
        return score.where(nb.notna(), 0.0)


class ConsequenceCalculator:
    """Combine des stratégies pondérées en un score de conséquence [0,1].

    Les composantes « socle » (typologie, diamètre) sont normalisées entre
    elles ; les composantes « boost » (abonnés) s'ajoutent puis le tout est
    plafonné à 1. Un facteur multiplicatif final par typologie dé-pondère les
    branchements (pris en charge séparément par le gestionnaire).
    """

    def __init__(self, base: list[ConsequenceStrategy], boosts: list[ConsequenceStrategy]):
        self.base = base
        self.boosts = boosts

    def compute(self, df: pd.DataFrame, config: dict) -> pd.Series:
        total_w = sum(s.weight for s in self.base) or 1.0
        cons = pd.Series(0.0, index=df.index)
        for strat in self.base:
            cons = cons + (strat.weight * strat.score(df, config)) / total_w
        for strat in self.boosts:
            cons = (cons + strat.weight * strat.score(df, config)).clip(upper=1.0)

        fac_map = config["consequence"].get("typologie_facteur", {})
        typo = df.get("typologie")
        if typo is not None and fac_map:
            facteur = typo.map(fac_map).fillna(1.0)
        else:
            facteur = pd.Series(1.0, index=df.index)
        return (cons * facteur).clip(0, 1)
