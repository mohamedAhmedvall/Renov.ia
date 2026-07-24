"""Générateur du réseau synthétique — AUCUNE donnée réelle.

Simule un petit réseau d'eau potable fictif (« Aquaville ») :
- `troncons.csv`  : patrimoine (matériau, diamètre, longueur, année de pose, tracé)
- `abonnes.csv`   : population desservie par tronçon (dont abonnés sensibles)
- `casses.csv`    : historique de casses simulé par un processus de Poisson
                    dont l'intensité dépend du matériau, de l'âge et du diamètre

Le processus générateur est CONNU (contrairement au réel) : il sert de vérité
terrain pour vérifier que le pipeline ML retrouve bien les facteurs injectés
(fonte grise ancienne plus fragile, petits diamètres plus cassants, etc.).

Usage : python data/synthetic/generate.py  (déterministe, graine fixée)
"""

from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
N_TRONCONS = 3000
ANNEE_OBS_DEBUT, ANNEE_OBS_FIN = 2005, 2024  # fenêtre d'observation des casses

# (famille, matériau, part du linéaire, période de pose typique, fragilité de base κ)
MATERIAUX = [
    ("Fonte", "Fonte grise", 0.22, (1930, 1975), 3.0),
    ("Fonte", "Fonte ductile", 0.30, (1970, 2015), 0.8),
    ("Plastique", "PVC collé", 0.15, (1960, 1985), 2.2),
    ("Plastique", "PVC", 0.13, (1980, 2020), 0.9),
    ("Plastique", "PEHD", 0.12, (1995, 2024), 0.5),
    ("Acier", "Acier", 0.05, (1950, 1990), 1.6),
    ("Ciment", "Amiante-ciment", 0.03, (1955, 1980), 2.5),
]


def _tirer_troncons() -> pd.DataFrame:
    parts = np.array([m[2] for m in MATERIAUX])
    idx = RNG.choice(len(MATERIAUX), size=N_TRONCONS, p=parts / parts.sum())
    rows = []
    # Tracé : marche aléatoire sur une grille pseudo-urbaine (coordonnées locales, mètres)
    x, y = 0.0, 0.0
    for i, k in enumerate(idx):
        fam, mat, _, (a0, a1), _ = MATERIAUX[k]
        annee = int(RNG.integers(a0, a1 + 1))
        # Diamètre : branchements et distribution dominent, quelques feeders
        r = RNG.random()
        if r < 0.15:
            diam = int(RNG.choice([32, 40, 50, 63]))
        elif r < 0.9:
            diam = int(RNG.choice([80, 100, 125, 150, 200, 250]))
        else:
            diam = int(RNG.choice([300, 400, 500, 600]))
        longueur = float(np.round(RNG.lognormal(mean=4.0, sigma=0.8), 1))  # médiane ~55 m
        longueur = min(longueur, 2000.0)
        ang = RNG.uniform(0, 2 * np.pi)
        x2, y2 = x + longueur * np.cos(ang), y + longueur * np.sin(ang)
        rows.append(
            {
                "id": f"SYN{i:06d}",
                "materiau_famille": fam,
                "materiau": mat,
                "diametre": diam,
                "longueur": longueur,
                "annee_pose": annee,
                "x1": round(x, 1), "y1": round(y, 1), "x2": round(x2, 1), "y2": round(y2, 1),
            }
        )
        # Repart du bout du tronçon 70 % du temps (réseau connexe), sinon saute ailleurs
        if RNG.random() < 0.7:
            x, y = x2, y2
        else:
            x, y = RNG.uniform(-4000, 4000), RNG.uniform(-4000, 4000)
    return pd.DataFrame(rows)


def _taux_annuel(df: pd.DataFrame, annee: int) -> np.ndarray:
    """Vérité terrain : λ(casses/an) = κ_matériau × f(âge) × g(diamètre) × longueur_km."""
    kappa = df["materiau"].map({m[1]: m[4] for m in MATERIAUX}).to_numpy()
    age = np.clip(annee - df["annee_pose"].to_numpy(), 0, None)
    f_age = 0.3 + (age / 50.0) ** 1.5                     # vieillissement convexe
    g_diam = np.where(df["diametre"] < 80, 1.6, np.where(df["diametre"] >= 300, 0.6, 1.0))
    base_km_an = 0.08                                      # ordre de grandeur réaliste
    return base_km_an * kappa * f_age * g_diam * (df["longueur"].to_numpy() / 1000.0)


def _simuler_casses(troncons: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for annee in range(ANNEE_OBS_DEBUT, ANNEE_OBS_FIN + 1):
        lam = _taux_annuel(troncons, annee)
        n_casses = RNG.poisson(lam)
        for tid, n in zip(troncons["id"], n_casses, strict=True):
            for _ in range(int(n)):
                jour = int(RNG.integers(1, 366))
                rows.append({"id_troncon": tid, "annee": annee, "jour": jour, "type": "casse"})
    return pd.DataFrame(rows).sort_values(["annee", "jour"]).reset_index(drop=True)


def _tirer_abonnes(troncons: pd.DataFrame) -> pd.DataFrame:
    typo_proxy = troncons["diametre"]
    nb = np.where(
        typo_proxy < 80, RNG.poisson(2, N_TRONCONS),
        np.where(typo_proxy >= 300, 0, RNG.poisson(25, N_TRONCONS)),
    )
    sens = RNG.binomial(1, 0.03, N_TRONCONS) * RNG.integers(1, 3, N_TRONCONS)
    tres = RNG.binomial(1, 0.01, N_TRONCONS)
    return pd.DataFrame(
        {
            "id_troncon": troncons["id"],
            "nb_abonne": nb,
            "nb_abonne_sensible": np.minimum(sens, nb),
            "nb_abonne_tres_sensible": np.minimum(tres, nb),
        }
    )


def main() -> None:
    out = Path(__file__).parent
    troncons = _tirer_troncons()
    casses = _simuler_casses(troncons)
    abonnes = _tirer_abonnes(troncons)
    troncons.to_csv(out / "troncons.csv", index=False)
    casses.to_csv(out / "casses.csv", index=False)
    abonnes.to_csv(out / "abonnes.csv", index=False)
    km = troncons["longueur"].sum() / 1000
    print(
        f"Réseau synthétique : {len(troncons)} tronçons ({km:.0f} km), "
        f"{len(casses)} casses simulées sur {ANNEE_OBS_FIN - ANNEE_OBS_DEBUT + 1} ans "
        f"({len(casses) / km / (ANNEE_OBS_FIN - ANNEE_OBS_DEBUT + 1):.3f} casse/km/an)"
    )


if __name__ == "__main__":
    main()
