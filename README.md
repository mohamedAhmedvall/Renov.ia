# Renov.ia — démonstration publique

**Aide à la décision patrimoniale pour les réseaux d'eau potable** : chaque tronçon de
canalisation reçoit une **probabilité calibrée de casse à 1, 3 et 5 ans** (machine learning),
croisée avec ses **conséquences** (typologie, diamètre, population desservie) pour produire une
**Note patrimoniale 1–5**, puis un **scénario de renouvellement optimisé sous contrainte de
budget**.

> ⚠️ **Démonstration sur données 100 % synthétiques.** Le réseau, les abonnés et l'historique de
> casses sont générés par simulation (`data/synthetic/generate.py`) : **aucune donnée réelle**
> (client, Veolia ou autre) n'est présente dans ce dépôt. Le processus générateur étant connu, il
> sert de vérité terrain : on vérifie que le pipeline ML retrouve les facteurs de risque injectés.
>
> Ce dépôt accompagne le mémoire RNCP40573 (Expert en informatique et systèmes d'information) —
> il illustre l'architecture et les choix techniques du produit Renov.ia, sans son périmètre
> industriel (multi-client, authentification, SIG réel).

## Architecture

```
data/synthetic ──► ml/ (features → XGBoost Poisson+offset → calibration → SHAP → backtest)
                        │  scores.csv (probabilités calibrées 1/3/5 ans)
                        ▼
                   domain/ (typologie, conséquence, Note 1–5 — patterns Strategy/Factory/Adapter/Repository)
                        │
     optimizer/ ◄───────┤  (greedy risque/coût sous budget, formulation Poisson)
                        ▼
                   backend/ (FastAPI — passerelle REST, contrats DTO pydantic)
                        ▼
                   frontend/ (React 18 + TS + Vite — carte MapLibre, Note 1–5, socle RGAA)
```

- **`domain/`** — logique métier **pure** (aucun framework) : la matrice de risque
  P × C → Note 1–5. Quatre patterns structurent le code : *Strategy* (composantes de conséquence
  interchangeables), *Factory* (assemblage piloté par la config), *Adapter* (mapping des sources
  de données), *Repository* (accès aux tronçons abstrait).
- **`ml/`** — pipeline data science : feature engineering anti-fuite (split temporel strict,
  `fit_state` train→test), **XGBoost Poisson avec offset d'exposition** (log longueur×horizon :
  le modèle apprend un taux de casse /km/an), **calibration isotonique** out-of-fold (les scores
  sont de vraies probabilités), explicabilité **SHAP**, **backtesting temporel glissant**
  (métrique métier : capture linéaire @ 20 %).
- **`optimizer/`** — knapsack **glouton par ratio (risque évité × conséquence) / coût**,
  déterministe ; bénéfice en espérance de casses évitées Δμ = −ln(1−P) − μ_neuf, IC 95 %.
- **`backend/`** — API FastAPI sans logique métier : Repository → domaine → DTO.
- **`frontend/`** — React : carte du risque, tableau priorisé, simulateur budgétaire.
  Socle **RGAA** : lien d'évitement, landmarks, étiquettes, `aria-live`, contrastes AA, la
  couleur toujours doublée d'un texte, lint `eslint-plugin-jsx-a11y` en CI.
- **`.ua/`** — graphe de connaissances du code (généré par l'outil *Understand Anything*),
  visualisable pour explorer l'architecture.

## Installation & exécution

Prérequis : Python ≥ 3.11, Node ≥ 20.

```bash
# 1. Dépendances Python
pip install -e ".[dev]"

# 2. (Re)générer le réseau synthétique puis les scores ML
python data/synthetic/generate.py
python ml/run_pipeline.py

# 3. API (port 8000)
uvicorn backend.app.main:app --port 8000

# 4. Front (port 5173, proxy /api → 8000)
cd frontend && npm install && npm run dev
```

Vérifications qualité (les mêmes gates que la CI, cf. `.github/workflows/ci.yml`) :

```bash
ruff check .          # style PEP 8, imports, bugbear
mypy domain optimizer backend ml
pytest                # unitaires + contrat + e2e (24 tests)
```

## Correspondance code ↔ blocs de compétences (RNCP40573)

| Bloc | Compétence illustrée | Où dans ce dépôt |
|---|---|---|
| **BC01** — Cadrage, conception et architecture SI | Architecture en couches (domaine pur / passerelle / UI), patterns GoF, contrats d'interface | `domain/` (Strategy, Factory, Adapter, Repository), `backend/app/dto.py`, ce README |
| **BC02** — Développement et intégration | Développement Python/TypeScript typé, API REST, front React accessible | `backend/`, `frontend/`, `optimizer/` |
| **BC03** — Industrialisation, qualité, sécurité | CI lint + typage + tests, pyramide de tests (unitaires → contrat → e2e, raccord Tab. 16), config PEP 8/ESLint | `.github/workflows/ci.yml` (raccord §8.5), `tests/`, `pyproject.toml`, `frontend/.eslintrc.cjs` |
| **BC05** — Big Data & Intelligence artificielle (option) | Modèle de comptage Poisson + offset, calibration, explicabilité SHAP, protocole de backtesting temporel (raccord chap. 9), optimisation sous contrainte | `ml/features/`, `ml/model/`, `ml/explain/`, `ml/backtest/`, `optimizer/` |

## Résultats sur le jeu synthétique

Le générateur injecte des facteurs de risque connus (fonte grise ancienne fragile, vieillissement
convexe, petits diamètres plus cassants). Le pipeline les **retrouve** :

- Importance SHAP : `âge` > `matériau (encodage)` > `diamètre` — conforme au processus simulé ;
- Backtest glissant (2014/2017/2020, horizon 3 ans) : **capture linéaire @ 20 % ≈ 0,40–0,43**,
  soit le double d'une priorisation aléatoire (0,20) ;
- Les probabilités calibrées permettent à l'optimiseur d'annoncer des « casses évitées » en
  espérance, avec IC 95 %.

## Licence

[MIT](LICENSE) — © 2026 Mohamed Ahmed Vall. Démo pédagogique ; le produit industriel Renov.ia
(SOMEI) n'est pas couvert par ce dépôt.
