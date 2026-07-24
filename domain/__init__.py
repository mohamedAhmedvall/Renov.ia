"""Domaine métier Renov.ia — logique pure, sans framework.

Calcule la matrice de risque patrimonial : typologie du tronçon, score de
conséquence [0,1], puis Note patrimoniale 1–5 (probabilité × conséquence,
binée par quantiles). Organisé autour de quatre patterns :

- **Strategy** (`strategies`) : chaque composante de la conséquence est une
  stratégie interchangeable (typologie, diamètre, population desservie).
- **Factory** (`factory`) : construit le calculateur de conséquence à partir
  de la configuration (poids), sans que l'appelant connaisse les classes.
- **Adapter** (`adapters`) : adapte une source brute (CSV synthétique) au
  modèle du domaine, en isolant les noms de colonnes.
- **Repository** (`repository`) : abstrait l'accès aux tronçons ; le domaine
  ne sait pas si les données viennent d'un CSV, d'une base ou d'une API.
"""

from domain.models import DEFAULT_CONFIG
from domain.note import compute_note, compute_notes

__all__ = ["compute_note", "compute_notes", "DEFAULT_CONFIG"]
