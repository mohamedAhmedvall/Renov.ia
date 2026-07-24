"""Pattern **Factory** — construit le calculateur de conséquence depuis la config.

L'appelant (API, tests, notebook) ne connaît ni les classes de stratégies ni
leur assemblage : il fournit une configuration de poids, la fabrique décide
quelles stratégies activer (un poids nul ou absent désactive la composante).
"""

from domain.strategies import (
    AbonnesStrategy,
    ConsequenceCalculator,
    ConsequenceStrategy,
    DiametreStrategy,
    TypologieStrategy,
)


def build_consequence_calculator(config: dict) -> ConsequenceCalculator:
    """Fabrique le calculateur : composantes socle + boosts selon les poids config."""
    # Sémantique : si `poids` est fourni, il est EXHAUSTIF (une composante absente
    # est désactivée) ; s'il est absent, on retombe sur les poids par défaut.
    poids = config.get("consequence", {}).get("poids") or {"typologie": 0.6, "diametre": 0.4}
    base: list[ConsequenceStrategy] = []
    boosts: list[ConsequenceStrategy] = []

    w_typo = float(poids.get("typologie", 0.0))
    if w_typo > 0:
        base.append(TypologieStrategy(w_typo))
    w_diam = float(poids.get("diametre", 0.0))
    if w_diam > 0:
        base.append(DiametreStrategy(w_diam))
    w_abo = float(poids.get("abonnes", 0.0))
    if w_abo > 0:
        boosts.append(AbonnesStrategy(w_abo))

    if not base:
        raise ValueError("Configuration invalide : aucune composante socle de conséquence activée.")
    return ConsequenceCalculator(base=base, boosts=boosts)
