---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
status: 'complete'
completedAt: '2026-04-03'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - 'project-distillate/_index.md'
  - 'project-distillate/01-dataset-data-quality.md'
  - 'project-distillate/02-feature-engineering.md'
  - 'project-distillate/03-model-results-validation.md'
  - 'project-distillate/04-v8-roadmap.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-04-01-001.md'
  - 'V8/data_cleaning.py'
  - 'V8/model.py'
  - 'V8/analyse_resultats.py'
  - 'V8/output/v8_scoring_fuites.csv'
  - 'V8/output/v8_backtesting.csv'
  - 'V8/output/v8_shap_importance.csv'
  - 'V8/output/v8_te_mapping_h1.json'
  - 'V8/output/v8_te_mapping_h3.json'
  - 'V8/output/v8_te_mapping_h5.json'
workflowType: 'architecture'
project_name: 'mohamed_casses'
user_name: 'mohamed'
date: '2026-04-03'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
32 FR organisées en 6 domaines :
- Visualisation réseau (FR1-6) : dualité carte/tableau, détection auto GeoJSON, mode dégradé gracieux
- Détail tronçon & explicabilité (FR7-12) : SHAP par feature, ICP fiabilité, multi-horizon
- Filtrage & recherche (FR13-19) : 5 filtres combinables, tri libre, sélection horizon
- Export (FR20-22) : CSV configurable avec scores + SHAP
- Dashboard & KPIs (FR23-28) : distribution risques, top N, KPIs patrimoine, vue cohorte matériau×décennie, courbe Lift
- Chargement & données (FR29-32) : CSV pré-calculés, validation au chargement, état de session persistant

**Non-Functional Requirements:**
20 NFR sur 5 axes :
- Performance : démarrage < 5s, carte < 3s, filtres < 1s, export < 2s, RAM < 2 Go
- Sécurité : déploiement local uniquement, zéro télémétrie, pas de credentials en dur
- Fiabilité : scoring déterministe, validation sans crash, messages d'erreur lisibles
- Maintenabilité : code modulaire, config externalisée, indépendance données/code, < 15 dépendances
- Portabilité : format CSV standardisé, déploiement nouveau réseau < 1 jour, Windows 10+

**Scale & Complexity:**
- Primary domain: Application data/analytics Streamlit mono-utilisateur
- Complexity level: Moyenne (données complexes, application simple)
- Estimated architectural components: 6-8 modules

### Technical Constraints & Dependencies

- **Stack imposé** : Streamlit (Python), même langage que les modèles ML
- **Pas de BDD** : CSV/Parquet en fichiers, chargés en mémoire Pandas
- **Monoposte** : pas d'auth, pas de serveur, déploiement local Windows
- **Données V8 existantes** : scoring CSV (58k+ tronçons, 10 colonnes), SHAP CSV (5 features), TE mappings JSON (3 fichiers par horizon), backtesting CSV (3 fenêtres)
- **GeoJSON optionnel** : à demander au SIG V2S, non bloquant
- **Mise à jour annuelle** : scoring recalculé post re-entraînement, pas de pipeline temps réel
- **Données imparfaites** : 17% dates de pose non fiables, matériaux parfois inconnus

### Cross-Cutting Concerns

1. **Configuration centralisée** — Chemins fichiers, seuils classes de risque, couleurs, colonnes affichées. Un seul point de vérité (fichier YAML/TOML).
2. **Validation & qualité données** — Schéma d'entrée formalisé (colonnes, types, encodage). Validation au chargement + ICP par tronçon partagé entre loader et visu.
3. **Cache & state management** — `@st.cache_data` pour le chargement lourd, `st.session_state` pour l'état filtres/vue. Pattern critique pour respecter les NFR performance.
4. **Abstraction visualisation** — Mode carte (Folium) / mode tabulaire (DataFrame) interchangeables. Détection auto du GeoJSON, fallback transparent.
5. **Contrat de données ML → App** — Interface formalisée entre le pipeline V8 et l'application : schéma CSV scoring, schéma SHAP, schéma GeoJSON. Permet le multi-réseau sans modification code.

## Starter Template Evaluation

### Primary Technology Domain

Application data/analytics Python mono-utilisateur — stack imposé par l'écosystème ML existant.

### Starter Options Considered

Pas de starter template CLI applicable. Le projet est une application Streamlit Python pure — le scaffolding est une structure de répertoires + `pip install`. Les starters Streamlit existants (streamlit-template, cookiecutter-streamlit) n'apportent pas de valeur ajoutée par rapport à une structure sur mesure alignée avec les 32 FR.

### Selected Approach: Structure projet sur mesure

**Rationale:**
- Stack entièrement défini par le PRD (Streamlit + Pandas + Folium)
- Aucun framework de scaffolding ne couvre le cas d'usage spécifique (scoring ML + carte + SHAP)
- La structure modulaire sur mesure garantit l'alignement exact avec les FR et NFR

**Initialization Command:**

```bash
pip install streamlit pandas folium streamlit-folium plotly pyyaml openpyxl
```

**Architectural Decisions — Language & Runtime:**
- Python 3.14+ (venv existant)
- Pas de TypeScript, pas de bundler — Python pur

**Styling Solution:**
- Streamlit natif (theming via `.streamlit/config.toml`)
- Plotly pour les graphiques interactifs (distribution risques, cohorte, Lift)
- Folium pour la carte géographique

**Build Tooling:**
- Aucun build step — `streamlit run main.py`
- `requirements.txt` pour la reproductibilité

**Testing Framework:**
- pytest (standard Python, déjà dans l'écosystème)
- Pas de testing UI Streamlit pour le MVP

**Code Organization:**

```
app/
├── config.yaml              # Chemins, seuils risque, couleurs, colonnes (NFR15)
├── main.py                  # Point d'entrée Streamlit, navigation, session state
├── data_loader.py           # Chargement CSV/GeoJSON, validation schéma, cache
├── data_schemas.py          # Schémas d'entrée formalisés (colonnes, types)
├── views/
│   ├── carte.py             # Vue carte Folium (FR2, FR5)
│   ├── tableau.py           # Vue tabulaire interactive (FR3)
│   ├── detail.py            # Détail tronçon + SHAP (FR7-12)
│   └── dashboard.py         # KPIs, cohorte, courbe Lift (FR23-28)
├── filters.py               # Filtrage combiné multi-critères (FR13-19)
└── export.py                # Export CSV configurable (FR20-22)
data/
├── scoring_troncons.csv     # Output V8 — contrat de données
├── referentiel_troncons.csv # Données patrimoniales
├── shap_importance.csv      # SHAP features
├── troncons.geojson         # Optionnel — tracés géographiques
└── te_mappings/             # Target encoding par horizon
```

**Development Experience:**
- Hot reload natif Streamlit (`streamlit run --server.runOnSave true`)
- Debug via IDE (VS Code Python debugger)
- < 15 dépendances Python (NFR17)

**Dependencies (7 packages directs) :**

| Package | Version | Usage |
|---|---|---|
| streamlit | latest | Framework UI |
| pandas | latest | Data manipulation |
| folium | latest | Carte géographique |
| streamlit-folium | latest | Intégration Folium/Streamlit |
| plotly | latest | Graphiques interactifs |
| pyyaml | latest | Configuration |
| openpyxl | latest | Export Excel (post-MVP ready) |

**Note:** L'initialisation du projet (structure + config + data loader) sera la première story d'implémentation.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (bloquent l'implémentation) :**
- Navigation sidebar manuelle
- Validation souple avec warnings
- Mapping configurable colonnes V8 → App
- Moteur d'optimisation OR-Tools CP-SAT

**Important Decisions (structurent l'architecture) :**
- Configuration YAML
- Convention session_state
- Modèle d'optimisation sous contraintes

**Deferred (Post-MVP) :**
- Authentification / rôles utilisateurs
- Base de données (SQLite/PostgreSQL)
- API REST découplée (FastAPI)
- Multi-tenant / multi-collectivités

### Data Architecture

| Décision | Choix | Rationale |
|---|---|---|
| Stockage | CSV/Parquet en fichiers, Pandas en mémoire | PRD — pas de BDD, < 2 Go RAM |
| Validation | Souple avec warnings | Données imparfaites (17% dates non fiables), l'app ne crash pas mais signale |
| Cache | `@st.cache_data` sur les fonctions de chargement | NFR1 — démarrage < 5s, pas de rechargement inutile |
| Contrat ML → App | Mapping configurable dans config.yaml | NFR16/NFR18 — indépendance données/code, multi-réseau |

**Schéma de validation souple :**
1. Vérifier la présence des colonnes requises → erreur lisible si manquantes
2. Caster les types (str→float, etc.) avec `errors='coerce'` → NaN au lieu de crash
3. Afficher warnings Streamlit pour les anomalies (colonnes inattendues, lignes avec NaN post-cast)
4. Calculer l'ICP par tronçon à partir des données manquantes/imputées

**Mapping configurable (config.yaml) :**
```yaml
column_mapping:
  id_troncon: "OBJET"
  materiau: "MATERIAU"
  diametre: "DIAMETRE"
  famille_materiau: "famille_mat"
  age: "age"
  score_h1: "score_h1"
  score_h3: "score_h3"
  score_h5: "score_h5"
  rang: "rang"
  top_pct: "top_pct"
```

### Authentication & Security

| Décision | Choix | Rationale |
|---|---|---|
| Auth MVP | Aucune | Monoposte, déploiement local |
| Données | Fichiers locaux, droits OS | NFR6-8 — pas de transmission externe |
| Télémétrie | Désactivée | NFR7 — `browser.gatherUsageStats = false` dans Streamlit config |
| Secrets | Aucun en dur | NFR9 — config.yaml pour les chemins, pas de credentials |

### Frontend Architecture (Streamlit)

| Décision | Choix | Rationale |
|---|---|---|
| Navigation | Sidebar manuelle (`st.sidebar.radio`) | Contrôle fin du state, passage tronçon sélectionné → vue détail |
| State management | `st.session_state` avec convention nommée | Persistance filtres/vue/sélection intra-session |
| Vues | 5 vues : Carte/Tableau, Détail tronçon, Dashboard, Optimiseur, Export | Alignement FR + optimiseur |
| Graphiques | Plotly (interactif) | Distribution risques, cohorte, Lift |
| Carte | Folium via streamlit-folium | Détection auto GeoJSON, fallback tabulaire |

**Convention session_state :**
```python
# Navigation & filtres
st.session_state.filtres               # dict: {materiau: [...], score_min: 0.5, age_min: 20, ...}
st.session_state.horizon               # int: 1, 3 ou 5
st.session_state.troncon_selectionne   # str: ID OBJET ou None
st.session_state.vue_active            # str: "carte"|"tableau"|"dashboard"|"optimiseur"|"detail"

# Optimiseur
st.session_state.budget_enveloppe      # float: €
st.session_state.taux_renouvellement   # float: 0.01 par défaut
st.session_state.materiau_remplacement # str: "fonte_ductile"|"pehd"
st.session_state.type_chantier         # str: "urbain_dense"|"urbain_standard"|"rural"
st.session_state.troncons_forces       # set: IDs imposés par l'ingénieur
st.session_state.troncons_exclus       # set: IDs exclus par l'ingénieur
st.session_state.contrainte_1pct       # bool: activer contrainte 1%/an ou non
```

### Optimiseur Renouvellement (OR-Tools CP-SAT)

**Moteur :** Google OR-Tools — solver CP-SAT pour programmation par contraintes.

**Modèle d'optimisation :**
```
Maximiser : Σ(score_risque × longueur) pour les tronçons sélectionnés

Sous contraintes :
- Budget : Σ(coût_ml × longueur × type_chantier) ≤ enveloppe
- Taux renouvellement : km renouvelés / km total ≥ seuil (1% ou configurable)
- Forçages : tronçons imposés par l'ingénieur = inclus d'office
- Exclusions : tronçons exclus par l'ingénieur = jamais sélectionnés
```

**Données requises (config.yaml) :**
```yaml
couts_remplacement:
  urbain_dense: 450      # €/ml — sous voirie, réseaux croisés
  urbain_standard: 300   # €/ml — trottoir, accotement
  rural: 180             # €/ml — pleine terre

materiaux_remplacement:
  fonte_ductile:
    cout_majorant: 1.0
    duree_vie_estimee: 80
  pehd:
    cout_majorant: 0.85
    duree_vie_estimee: 50

km_total_reseau: 100     # pour calcul taux renouvellement
```

**What-if matériau :** L'ingénieur choisit le matériau de remplacement (fonte ductile ou PEHD) → le coût par tronçon change → l'optimiseur recalcule le plan optimal dans l'enveloppe.

**Forçage manuel :** L'ingénieur impose/exclut des tronçons. Le budget des forçages est pré-alloué, l'optimiseur optimise le reste.

**KPIs post-optimisation :**

| KPI | Calcul |
|---|---|---|
| Risque éliminé | Σ(score × longueur) sélectionnés / Σ total |
| Fuites évitées | Σ(score_h3 × taux_conversion) pour tronçons remplacés |
| ML renouvelés | Σ(longueur) des tronçons sélectionnés |
| Taux renouvellement | ML renouvelés / km total réseau |
| Budget consommé | Σ(coût effectif) / enveloppe |
| Coût par fuite évitée | Budget / nb fuites évitées |

### Infrastructure & Deployment

| Décision | Choix | Rationale |
|---|---|---|
| Déploiement | `streamlit run app/main.py` sur poste local | PRD — données sensibles |
| OS cible | Windows 10+ | NFR20 — environnement V2S |
| CI/CD | Aucun pour MVP | Dev solo, déploiement manuel |
| Monitoring | Aucun pour MVP | Monoposte |
| Configuration | YAML (`config.yaml`) | Cohérent avec l'écosystème projet existant |

### Decision Impact Analysis

**Structure projet mise à jour :**
```
app/
├── config.yaml              # Chemins, seuils, couleurs, coûts, mapping colonnes
├── main.py                  # Point d'entrée Streamlit, sidebar, session state
├── data_loader.py           # Chargement CSV/GeoJSON, validation schéma, cache
├── data_schemas.py          # Schémas d'entrée formalisés (colonnes, types)
├── optimizer.py             # Moteur OR-Tools CP-SAT
├── views/
│   ├── carte.py             # Vue carte Folium (FR2, FR5)
│   ├── tableau.py           # Vue tabulaire interactive (FR3)
│   ├── detail.py            # Détail tronçon + SHAP (FR7-12)
│   ├── dashboard.py         # KPIs, cohorte, courbe Lift (FR23-28)
│   └── optimiseur.py        # Scénarios, forçages, what-if, KPIs renouvellement
├── filters.py               # Filtrage combiné multi-critères (FR13-19)
└── export.py                # Export CSV configurable (FR20-22)
data/
├── scoring_troncons.csv     # Output V8 — contrat de données
├── referentiel_troncons.csv # Données patrimoniales
├── shap_importance.csv      # SHAP features
├── troncons.geojson         # Optionnel — tracés géographiques
└── te_mappings/             # Target encoding par horizon
```

**Dependencies (8 packages directs) :**

| Package | Usage |
|---|---|
| streamlit | Framework UI |
| pandas | Data manipulation |
| folium | Carte géographique |
| streamlit-folium | Intégration Folium/Streamlit |
| plotly | Graphiques interactifs |
| pyyaml | Configuration |
| openpyxl | Export Excel (post-MVP ready) |
| ortools | Solver CP-SAT optimisation sous contraintes |

**Séquence d'implémentation :**
1. config.yaml + data_schemas.py (fondation)
2. data_loader.py + validation souple (chargement données)
3. main.py + sidebar (5 vues) + session_state (squelette app)
4. views/tableau.py (vue par défaut, toujours disponible)
5. views/carte.py (si GeoJSON)
6. views/detail.py (SHAP, ICP)
7. views/dashboard.py (KPIs, cohorte, Lift)
8. optimizer.py (moteur OR-Tools)
9. views/optimiseur.py (scénarios, forçages, what-if, KPIs renouvellement)
10. export.py (CSV configurable)

**Dépendances inter-composants :**
- `data_loader` → dépend de `config.yaml` (mapping) + `data_schemas` (validation)
- Toutes les `views/` → dépendent de `data_loader` (DataFrame) + `filters` (filtrage)
- `detail.py` → dépend de `session_state.troncon_selectionne` (set par carte ou tableau)
- `optimizer.py` → dépend de `data_loader` (scoring + référentiel) + `config.yaml` (coûts)
- `views/optimiseur.py` → dépend de `optimizer.py` (résultats) + `session_state` (forçages, params)
- `export.py` → dépend de `filters` (DataFrame filtré)

**Note :** Le PRD sera mis à jour pour refléter le déplacement de l'optimiseur de Phase 2 → MVP après finalisation de l'architecture.

## Implementation Patterns & Consistency Rules

### Points de conflit identifiés

8 zones où des agents AI pourraient faire des choix divergents, toutes adressées ci-dessous.

### Naming Patterns

**Convention Python standard — tout en snake_case :**

| Élément | Convention | Exemple |
|---|---|---|
| Fonctions | snake_case | `load_scoring_data()` |
| Variables | snake_case | `df_scoring`, `score_min` |
| Classes | PascalCase | `DataSchema` |
| Constantes | UPPER_SNAKE | `DEFAULT_HORIZON`, `RISK_THRESHOLDS` |
| Fichiers | snake_case.py | `data_loader.py` |
| Clés config | snake_case | `column_mapping`, `couts_remplacement` |
| Session state | snake_case | `st.session_state.troncon_selectionne` |

### Structure Patterns

**Vue Streamlit — chaque fichier views/*.py expose une seule fonction :**
```python
def render(df_scoring: pd.DataFrame, df_referentiel: pd.DataFrame, config: dict):
    """Point d'entrée de la vue, appelé par main.py."""
```

**Règles d'import :**
- Une vue n'importe JAMAIS une autre vue
- Pas d'import circulaire
- Pas de `from module import *`
- `data_loader.py` est le seul point d'accès aux données

**Graphe de dépendances :**
```
config.yaml → data_loader.py → main.py → views/*.py
                    ↑                         ↓
             data_schemas.py            filters.py
                                        optimizer.py → views/optimiseur.py
                                        export.py
```

### Format Patterns

**Affichage des données — locale française :**

| Donnée | Format | Exemple |
|---|---|---|
| Score de risque | Pourcentage 1 décimale | `93.3%` |
| Âge | Entier + "ans" | `54 ans` |
| Longueur | Mètres, 0 décimale | `142 m` |
| Diamètre | mm, entier | `150 mm` |
| Coût | € avec séparateur milliers | `45 000 €` |
| Dates | Format français dd/mm/yyyy | `03/04/2026` |

### Cache & State Patterns

**Cache Streamlit :**
- `@st.cache_data` pour toutes les fonctions de chargement fichier
- Jamais `@st.cache_resource` (pas d'objets mutables partagés)
- Paramètres de la fonction = clé de cache (chemin fichier)

**Session state — initialisation dans main.py :**
```python
DEFAULTS = {
    "filtres": {},
    "horizon": 3,
    "troncon_selectionne": None,
    "vue_active": "tableau",
    "budget_enveloppe": 500_000,
    "taux_renouvellement": 0.01,
    "materiau_remplacement": "fonte_ductile",
    "type_chantier": "urbain_standard",
    "troncons_forces": set(),
    "troncons_exclus": set(),
    "contrainte_1pct": True,
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val
```

### Error Handling Patterns

**Règle absolue :** Aucun stacktrace Python visible par l'utilisateur (NFR13).

| Situation | Pattern |
|---|---|
| Fichier manquant | `st.error("Fichier scoring introuvable : {path}")` + arrêt propre |
| Colonnes manquantes | `st.error("Colonnes requises manquantes : {list}")` + arrêt propre |
| Données castées avec perte | `st.warning("X valeurs non numériques dans la colonne Y, converties en NaN")` |
| GeoJSON absent | `st.info("Carte désactivée — fichier GeoJSON non trouvé")` → mode tabulaire |
| Optimiseur sans solution | `st.warning("Aucune solution trouvée avec ces contraintes. Relâchez le budget ou désactivez la contrainte 1%.")` |

**Try/except limité au chargement de données et à l'optimiseur — pas ailleurs.**

### Configuration Pattern

**Un seul fichier `config.yaml` à la racine de `app/` :**
- Chemins fichiers données (paths)
- Mapping colonnes (column_mapping)
- Seuils de risque (risk_thresholds)
- Couleurs par classe (risk_colors)
- Coûts de remplacement (couts_remplacement)
- Matériaux de remplacement (materiaux_remplacement)
- Paramètre réseau (km_total_reseau)

**Règle :** Aucune valeur en dur dans le code Python. Tout paramètre métier ou chemin → config.yaml.

### Enforcement Guidelines

**Tout agent AI DOIT :**
1. Utiliser snake_case partout (sauf classes)
2. Lire les chemins et paramètres depuis config.yaml, jamais en dur
3. Utiliser `@st.cache_data` pour tout chargement de fichier
4. Afficher `st.error`/`st.warning`/`st.info` — jamais un stacktrace
5. Exposer exactement une fonction `render()` par fichier de vue
6. Ne jamais importer une vue depuis une autre vue
7. Formater les données en locale française (séparateur milliers, €, dates dd/mm/yyyy)
8. Initialiser tout session_state dans main.py avec valeurs par défaut

## Project Structure & Boundaries

### Complete Project Directory Structure

```
app/
├── .streamlit/
│   └── config.toml              # Theme Streamlit, désactivation télémétrie
├── config.yaml                  # Configuration centralisée (chemins, seuils, couleurs, coûts, mapping)
├── main.py                      # Point d'entrée — sidebar, session_state init, routing vues
├── data_loader.py               # Chargement CSV/GeoJSON, validation souple, cache
├── data_schemas.py              # Schémas colonnes requises, types attendus, règles validation
├── filters.py                   # Logique filtrage combiné multi-critères
├── optimizer.py                 # Moteur OR-Tools CP-SAT — optimisation renouvellement
├── export.py                    # Export CSV configurable (sélection colonnes + filtres)
├── views/
│   ├── __init__.py
│   ├── carte.py                 # Vue carte Folium interactive
│   ├── tableau.py               # Vue tabulaire triable/filtrable
│   ├── detail.py                # Détail tronçon + SHAP + ICP
│   ├── dashboard.py             # KPIs, cohorte matériau×décennie, courbe Lift
│   └── optimiseur.py            # Scénarios budget, forçages, what-if, KPIs renouvellement
├── requirements.txt             # Dépendances Python (8 packages)
└── README.md                    # Instructions d'installation et d'usage
data/
├── scoring_troncons.csv         # Output V8 — scoring par tronçon
├── referentiel_troncons.csv     # Données patrimoniales (matériau, diamètre, longueur, date pose)
├── shap_importance.csv          # SHAP mean_abs par feature
├── backtesting.csv              # Résultats backtesting (AUC, capture, gain)
├── troncons.geojson             # OPTIONNEL — tracés géographiques SIG
└── te_mappings/
    ├── v8_te_mapping_h1.json
    ├── v8_te_mapping_h3.json
    └── v8_te_mapping_h5.json
tests/
├── test_data_loader.py          # Validation chargement + schéma
├── test_data_schemas.py         # Validation des règles de schéma
├── test_filters.py              # Logique filtrage combiné
├── test_optimizer.py            # Moteur OR-Tools (contraintes, edge cases)
└── test_export.py               # Export CSV correct
```

### Requirements to Structure Mapping

| Domaine FR | Fichier(s) | FR couvertes |
|---|---|---|
| Visualisation réseau | `views/carte.py`, `views/tableau.py`, `main.py` | FR1-6 |
| Détail & explicabilité | `views/detail.py` | FR7-12 |
| Filtrage & recherche | `filters.py`, sidebar dans `main.py` | FR13-19 |
| Export | `export.py` | FR20-22 |
| Dashboard & KPIs | `views/dashboard.py` | FR23-28 |
| Chargement & données | `data_loader.py`, `data_schemas.py` | FR29-32 |
| Optimiseur renouvellement | `optimizer.py`, `views/optimiseur.py` | Nouveau scope MVP |

### Architectural Boundaries

**Frontière 1 : Données → Application**
```
data/*.csv ──→ data_loader.py ──→ pd.DataFrame en mémoire
                    ↑
              data_schemas.py (validation)
              config.yaml (mapping colonnes)
```
- `data_loader.py` est la seule porte d'entrée vers les fichiers données
- Aucune vue ne lit directement un fichier CSV/GeoJSON
- Le mapping colonnes rend le code indépendant du format source

**Frontière 2 : Filtrage → Vues**
```
st.session_state.filtres ──→ filters.py ──→ df_filtré ──→ views/*.py
```
- `filters.py` applique les filtres et retourne un DataFrame filtré
- Chaque vue reçoit le DataFrame déjà filtré — pas de logique filtre dans les vues

**Frontière 3 : Optimiseur → Vue optimiseur**
```
config.yaml (coûts) ─┐
df_scoring ───────────┼──→ optimizer.py ──→ résultat (dict) ──→ views/optimiseur.py
session_state ────────┘    (OR-Tools)       {troncons_selectionnes,
                                             kpis, budget_utilise}
```
- `optimizer.py` est un module pur Python (pas de Streamlit)
- Reçoit des DataFrames + paramètres, retourne un dict de résultats
- `views/optimiseur.py` gère l'UI : sliders budget, checkboxes forçage, affichage KPIs

**Frontière 4 : Session state (main.py)**
- `main.py` initialise TOUS les session_state avec valeurs par défaut
- Les vues lisent/écrivent session_state directement
- Aucune vue ne crée de nouvelle clé session_state — tout est défini dans main.py

### Data Flow

```
                    config.yaml
                        │
                        ▼
Fichiers CSV/GeoJSON → data_loader.py → DataFrame(s) caché(s)
                                              │
                                              ▼
                              main.py (sidebar + routing)
                              ├── filters.py → df_filtré
                              │       │
                              │       ├── views/tableau.py
                              │       ├── views/carte.py
                              │       ├── views/detail.py (+ SHAP)
                              │       └── views/dashboard.py (+ backtesting)
                              │
                              ├── optimizer.py ← session_state (budget, forçages)
                              │       │
                              │       └── views/optimiseur.py (résultats + KPIs)
                              │
                              └── export.py ← df_filtré
```

### Streamlit Configuration

```toml
# .streamlit/config.toml
[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1976d2"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f5f5f5"
textColor = "#212121"
```

## Architecture Validation Results

### Coherence Validation ✅

| Vérification | Résultat |
|---|---|
| Python + Streamlit + Pandas + Folium + Plotly + OR-Tools | ✅ Toutes librairies Python, compatibles |
| YAML config + PyYAML | ✅ Cohérent avec l'écosystème |
| `@st.cache_data` + CSV en mémoire | ✅ Pattern standard Streamlit |
| Sidebar manuelle + session_state | ✅ Pas de conflit avec le routing |
| OR-Tools CP-SAT module pur Python | ✅ Découplé de Streamlit, testable |
| Mapping configurable + validation souple | ✅ Complémentaires |
| Décisions contradictoires | ✅ Aucune détectée |

### Requirements Coverage ✅

**Exigences fonctionnelles (32 FR) :** 100% couvertes

| FR | Composant | Couvert |
|---|---|---|
| FR1-6 (Visualisation) | `views/carte.py`, `views/tableau.py`, `main.py` | ✅ |
| FR7-12 (Détail + SHAP + ICP) | `views/detail.py` | ✅ |
| FR13-19 (Filtres) | `filters.py`, `main.py` sidebar | ✅ |
| FR20-22 (Export CSV) | `export.py` | ✅ |
| FR23-28 (Dashboard, cohorte, Lift) | `views/dashboard.py` | ✅ |
| FR29-32 (Chargement, validation, state) | `data_loader.py`, `data_schemas.py`, `main.py` | ✅ |
| Optimiseur (nouveau MVP) | `optimizer.py`, `views/optimiseur.py` | ✅ |

**Exigences non-fonctionnelles (20 NFR) :** 100% couvertes

| NFR | Solution architecturale |
|---|---|
| NFR1-5 (Performance) | `@st.cache_data`, Pandas en mémoire, CSV direct |
| NFR6-9 (Sécurité) | Déploiement local, zéro télémétrie, pas de credentials |
| NFR10-13 (Fiabilité) | CSV pré-calculé, validation souple, error handling pattern |
| NFR14-17 (Maintenabilité) | 11 modules, config externalisée, mapping colonnes, 8 deps |
| NFR18-20 (Portabilité) | `data_schemas.py`, config-only onboarding, Windows natif |

### Implementation Readiness ✅

- Décisions complètes avec versions et rationales
- Patterns d'implémentation exhaustifs (8 règles d'enforcement)
- Structure projet détaillée (11 fichiers Python + config + tests)
- Frontières architecturales clairement définies (4)
- Flux de données documenté

### Gap Analysis

**Gaps critiques : AUCUN**

**Gaps importants :**

| Gap | Impact | Action |
|---|---|---|
| PRD pas encore mis à jour (optimiseur dans MVP) | Décalage PRD ↔ Archi | Mettre à jour après finalisation archi |
| `referentiel_troncons.csv` format exact non spécifié | Bloque data loader | Définir schéma dans `data_schemas.py` à partir des données V8 |

**Gaps mineurs :**

| Gap | Impact |
|---|---|
| `taux_conversion` fuites évitées non calibré | Valeur à définir avec données terrain |

### Architecture Completeness Checklist

- [x] Contexte projet analysé (32 FR + 20 NFR)
- [x] Complexité évaluée (moyenne)
- [x] Contraintes techniques identifiées
- [x] Concerns transverses mappés (5)
- [x] 5 décisions critiques documentées
- [x] Stack technique complet (8 packages)
- [x] Optimiseur OR-Tools intégré au MVP
- [x] Naming conventions définies
- [x] Structure vues (`render()` unique)
- [x] Formats d'affichage (locale FR)
- [x] Error handling (st.error/warning/info)
- [x] Cache & state (8 guidelines)
- [x] Arborescence complète
- [x] Boundaries architecturales (4 frontières)
- [x] Mapping FR → fichiers (100%)
- [x] Flux de données documenté

### Architecture Readiness Assessment

**Statut : PRÊT POUR L'IMPLÉMENTATION**

**Niveau de confiance : ÉLEVÉ**

**Forces :**
- Architecture simple et lisible — un dev solo peut tout garder en tête
- Séparation données/logique/UI claire
- Optimiseur découplé (module pur Python) — testable indépendamment
- Portabilité multi-réseau par design (mapping + validation souple)

**À améliorer après le MVP :**
- Tests UI Streamlit (e2e)
- Persistance décisions ingénieur (forçages)
- Migration vers serveur multi-utilisateurs

### Implementation Handoff

**Première priorité d'implémentation :**
```bash
pip install streamlit pandas folium streamlit-folium plotly pyyaml openpyxl ortools
```
Puis créer `config.yaml` + `data_schemas.py` + `data_loader.py` comme fondation.
