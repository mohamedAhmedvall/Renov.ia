"""Générateur des réseaux synthétiques — AUCUNE donnée réelle de réseau.

Simule un réseau d'eau potable FICTIF par ville, écrit dans
`data/synthetic/<ville>/` :

- `troncons.csv`  : patrimoine (matériau, diamètre, longueur, année de pose, tracé)
- `abonnes.csv`   : population desservie par tronçon (dont abonnés sensibles)
- `casses.csv`    : historique de casses simulé par un processus de Poisson
                    dont l'intensité dépend du matériau, de l'âge et du diamètre

Le tracé suit une **trame de rues** : une grille orientée selon la direction
dominante du bâti de la ville, avec des nœuds bruités et des mailles ajourées.
Les coordonnées restent LOCALES (mètres autour du centre-ville) ; c'est l'API
qui les projette en WGS84 pour l'affichage sur fond de carte. Le centre réel de
la ville sert uniquement d'ancrage cartographique : la géométrie du réseau,
elle, est entièrement simulée.

Chaque ville a un âge médian de patrimoine différent (`villes.json`) et le
centre est plus ancien que la périphérie — d'où des profils de risque
distincts d'une ville à l'autre.

Le processus générateur est CONNU (contrairement au réel) : il sert de vérité
terrain pour vérifier que le pipeline ML retrouve bien les facteurs injectés
(fonte grise ancienne plus fragile, petits diamètres plus cassants, etc.).

Usage :
    python data/synthetic/generate.py              # les 4 villes
    python data/synthetic/generate.py --ville lyon # une seule
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ICI = Path(__file__).parent
ANNEE_OBS_DEBUT, ANNEE_OBS_FIN = 2005, 2024  # fenêtre d'observation des casses
PROBA_MAILLE_ABSENTE = 0.12                  # trame ajourée : toutes les rues n'ont pas de conduite

# (famille, matériau, part du linéaire, période de pose plausible, fragilité κ, biais d'âge)
# Le biais d'âge décale la pose par rapport à la médiane de la ville : la fonte
# grise appartient aux campagnes anciennes, le PEHD aux plus récentes. C'est ce
# qui crée la corrélation matériau ↔ âge que le modèle doit retrouver.
MATERIAUX = [
    ("Fonte", "Fonte grise", 0.22, (1930, 1975), 3.0, -22),
    ("Fonte", "Fonte ductile", 0.30, (1970, 2015), 0.8, 18),
    ("Plastique", "PVC collé", 0.15, (1960, 1985), 2.2, -4),
    ("Plastique", "PVC", 0.13, (1980, 2020), 0.9, 10),
    ("Plastique", "PEHD", 0.12, (1995, 2024), 0.5, 28),
    ("Acier", "Acier", 0.05, (1950, 1990), 1.6, -6),
    ("Ciment", "Amiante-ciment", 0.03, (1955, 1980), 2.5, -14),
]

DIAMETRES_BRANCHEMENT = [32, 40, 50, 63]
DIAMETRES_DISTRIBUTION = [80, 100, 125, 150, 200, 250]
DIAMETRES_TRANSPORT = [300, 400, 500, 600]


def charger_villes() -> dict:
    """Paramètres des villes (centre réel, orientation de la trame, âge médian)."""
    return json.loads((ICI / "villes.json").read_text(encoding="utf-8"))["villes"]


def _graine(cle: str) -> int:
    """Graine déterministe dérivée du nom de la ville.

    `hash()` de Python est randomisé entre processus : on calcule la graine à la
    main pour que la régénération donne strictement le même réseau.
    """
    return sum((i + 1) * ord(c) for i, c in enumerate(cle)) * 7919 % (2**31)


def _trame(v: dict, rng: np.random.Generator) -> np.ndarray:
    """Nœuds de la trame : grille régulière bruitée, puis pivotée sur `angle_deg`.

    Renvoie un tableau (nx, ny, 2) de coordonnées locales en mètres.
    """
    nx, ny = v["mailles"]
    px, py = v["pas_m"]
    theta = math.radians(v["angle_deg"])
    cos_t, sin_t = math.cos(theta), math.sin(theta)

    i = np.arange(nx)[:, None] - (nx - 1) / 2.0
    j = np.arange(ny)[None, :] - (ny - 1) / 2.0
    # Bruit sur les nœuds : une trame parfaitement régulière ne ressemble pas
    # à un réseau, elle ressemble à du papier millimétré.
    x = i * px + rng.uniform(-0.35, 0.35, (nx, ny)) * px
    y = j * py + rng.uniform(-0.35, 0.35, (nx, ny)) * py
    return np.stack([x * cos_t - y * sin_t, x * sin_t + y * cos_t], axis=-1)


def _tirer_troncons(cle: str, v: dict, rng: np.random.Generator) -> pd.DataFrame:
    """Un tronçon par maille conservée, entre deux nœuds voisins de la trame."""
    noeuds = _trame(v, rng)
    nx, ny = v["mailles"]
    rayon = math.hypot(nx * v["pas_m"][0], ny * v["pas_m"][1]) / 2.0
    prefixe = cle[:3].upper()
    parts = np.array([m[2] for m in MATERIAUX])
    parts = parts / parts.sum()

    lignes = []
    for i in range(nx):
        for j in range(ny):
            for vi, vj in ((i + 1, j), (i, j + 1)):
                if vi >= nx or vj >= ny:
                    continue
                if rng.random() < PROBA_MAILLE_ABSENTE:
                    continue
                a, b = noeuds[i, j], noeuds[vi, vj]
                longueur = float(np.round(math.dist(a, b), 1))

                # 0 au centre-ville → 1 en limite d'emprise : pilote l'âge,
                # le calibre et la densité d'abonnés.
                milieu = (a + b) / 2.0
                dist = min(1.0, float(np.hypot(*milieu)) / rayon)

                fam, mat, _, (a0, a1), _, biais = MATERIAUX[rng.choice(len(MATERIAUX), p=parts)]
                # Le centre a été posé en premier : l'âge décroît vers la périphérie.
                annee = v["annee_mediane"] + biais + dist * 34 + rng.normal(0, 18)
                annee = int(np.clip(round(annee), a0, a1))

                # Les feeders sont au centre, les branchements en périphérie.
                r = rng.random()
                if r < 0.10 + 0.16 * dist:
                    diam = int(rng.choice(DIAMETRES_BRANCHEMENT))
                elif r > 1.0 - (0.16 - 0.10 * dist):
                    diam = int(rng.choice(DIAMETRES_TRANSPORT))
                else:
                    diam = int(rng.choice(DIAMETRES_DISTRIBUTION))

                lignes.append(
                    {
                        "id": f"{prefixe}{len(lignes):05d}",
                        "materiau_famille": fam,
                        "materiau": mat,
                        "diametre": diam,
                        "longueur": longueur,
                        "annee_pose": annee,
                        "x1": round(float(a[0]), 1), "y1": round(float(a[1]), 1),
                        "x2": round(float(b[0]), 1), "y2": round(float(b[1]), 1),
                        "dist_centre": round(dist, 4),
                    }
                )
    return pd.DataFrame(lignes)


def _taux_annuel(df: pd.DataFrame, annee: int) -> np.ndarray:
    """Vérité terrain : λ(casses/an) = κ_matériau × f(âge) × g(diamètre) × longueur_km."""
    kappa = df["materiau"].map({m[1]: m[4] for m in MATERIAUX}).to_numpy()
    age = np.clip(annee - df["annee_pose"].to_numpy(), 0, None)
    f_age = 0.3 + (age / 50.0) ** 1.5                     # vieillissement convexe
    g_diam = np.where(df["diametre"] < 80, 1.6, np.where(df["diametre"] >= 300, 0.6, 1.0))
    base_km_an = 0.08                                      # ordre de grandeur réaliste
    return base_km_an * kappa * f_age * g_diam * (df["longueur"].to_numpy() / 1000.0)


def _simuler_casses(troncons: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for annee in range(ANNEE_OBS_DEBUT, ANNEE_OBS_FIN + 1):
        n_casses = rng.poisson(_taux_annuel(troncons, annee))
        for tid, n in zip(troncons["id"], n_casses, strict=True):
            for _ in range(int(n)):
                rows.append(
                    {
                        "id_troncon": tid,
                        "annee": annee,
                        "jour": int(rng.integers(1, 366)),
                        "type": "casse",
                    }
                )
    if not rows:
        return pd.DataFrame(columns=["id_troncon", "annee", "jour", "type"])
    return pd.DataFrame(rows).sort_values(["annee", "jour"]).reset_index(drop=True)


def _tirer_abonnes(troncons: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Population desservie : dense au centre, nulle sur les feeders de transport."""
    n = len(troncons)
    densite = 0.6 + 0.9 * (1.0 - troncons["dist_centre"].to_numpy())
    diam = troncons["diametre"].to_numpy()
    nb = np.where(
        diam < 80, rng.poisson(2 * densite),
        np.where(diam >= 300, 0, rng.poisson(25 * densite)),
    )
    sens = rng.binomial(1, 0.03, n) * rng.integers(1, 3, n)
    tres = rng.binomial(1, 0.01, n)
    return pd.DataFrame(
        {
            "id_troncon": troncons["id"],
            "nb_abonne": nb,
            "nb_abonne_sensible": np.minimum(sens, nb),
            "nb_abonne_tres_sensible": np.minimum(tres, nb),
        }
    )


def generer_ville(cle: str, v: dict) -> None:
    rng = np.random.default_rng(_graine(cle))
    troncons = _tirer_troncons(cle, v, rng)
    casses = _simuler_casses(troncons, rng)
    abonnes = _tirer_abonnes(troncons, rng)

    dossier = ICI / cle
    dossier.mkdir(exist_ok=True)
    # dist_centre n'est qu'un intermédiaire de génération : il ne sort pas du
    # générateur, sinon le modèle apprendrait une variable que le SIG réel
    # n'aurait pas sous cette forme.
    troncons.drop(columns=["dist_centre"]).to_csv(dossier / "troncons.csv", index=False)
    casses.to_csv(dossier / "casses.csv", index=False)
    abonnes.to_csv(dossier / "abonnes.csv", index=False)

    km = troncons["longueur"].sum() / 1000
    ans = ANNEE_OBS_FIN - ANNEE_OBS_DEBUT + 1
    print(
        f"{v['nom']:<10} {len(troncons):>5} tronçons  {km:>6.0f} km  "
        f"âge moyen {ANNEE_OBS_FIN - troncons['annee_pose'].mean():>4.0f} ans  "
        f"{len(casses):>5} casses sur {ans} ans ({len(casses) / km / ans:.3f} casse/km/an)"
    )


def main() -> None:
    villes = charger_villes()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ville", choices=sorted(villes), help="ne générer qu'une ville")
    args = parser.parse_args()

    for cle in [args.ville] if args.ville else list(villes):
        generer_ville(cle, villes[cle])


if __name__ == "__main__":
    main()
