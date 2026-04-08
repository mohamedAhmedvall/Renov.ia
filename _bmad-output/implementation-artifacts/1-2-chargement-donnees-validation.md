# Story 1.2 : Chargement données & Validation

## Story

As a **ingénieur patrimoine**,
I want **que l'application charge automatiquement les fichiers CSV de scoring et de référentiel au démarrage**,
So that **je puisse voir mes données sans configuration manuelle.**

## Status

review

## Acceptance Criteria

- AC1: Les données sont chargées en < 5s via `@st.cache_data` (NFR1)
- AC2: Les colonnes requises sont validées selon `data_schemas.py` et le mapping `config.yaml`
- AC3: Les types sont castés avec `errors='coerce'` (pas de crash sur données invalides)
- AC4: Un ICP (Indice de Connaissance Patrimoniale) est calculé par tronçon
- AC5: Si un fichier est manquant → `st.error("Fichier de scoring introuvable...")` lisible
- AC6: Si des colonnes sont manquantes → `st.warning()` lisible avec les colonnes absentes
- AC7: Aucun stacktrace Python n'est visible (NFR13)
- AC8: RAM < 2 Go pour le dataset complet (NFR5)

## Tasks/Subtasks

- [x] Task 1: Enrichir `data_schemas.py` avec schéma référentiel complet
- [x] Task 2: Implémenter `load_scoring()` dans `data_loader.py`
  - [x] Chargement CSV avec `@st.cache_data`
  - [x] Validation colonnes requises
  - [x] Casting types avec `errors='coerce'`
  - [x] Calcul classe de risque par troncon
- [x] Task 3: Implémenter `load_referentiel()` dans `data_loader.py`
  - [x] Chargement CSV référentiel
  - [x] Validation et casting
- [x] Task 4: Implémenter `compute_icp()` dans `data_loader.py`
  - [x] Calcul ICP par troncon (% données renseignées)
- [x] Task 5: Implémenter gestion erreurs métier
  - [x] Fichier manquant → st.error lisible
  - [x] Colonnes manquantes → st.warning
  - [x] Aucun stacktrace visible
- [x] Task 6: Intégrer le chargement dans `main.py`
  - [x] Appeler load_scoring et load_referentiel au démarrage
  - [x] Passer les DataFrames aux vues
- [x] Task 7: Tester le chargement complet et valider les AC

## Dev Notes

### Données existantes
- scoring: V8/output/v8_scoring_fuites.csv (182,075 lignes, 10 cols: OBJET, MATERIAU, DIAMETRE, famille_mat, age, score_h1/h3/h5, rang, top_pct)
- référentiel: data/canalisation_sem_3_1_.csv (221,957 lignes, 17 cols: STATUT_OBJET, OBJET, ABANDON, DEPOSE, POSE, DIAMETRE, MATERIAU, ETAT, LONGUEUR, TERRAIN, PROFONDEUR, etc.)
- historique anomalies: data/historiqueanomalie.csv (30,775 lignes: GID_OBJET, TYPE_ANOMALIE, DATE_DETECTION_parsed, etc.)
- SHAP: V8/output/v8_shap_importance.csv (feature, mean_abs_shap)
- Backtesting: V8/output/v8_backtesting.csv (window, auc, ap, capture_top20, etc.)

### Architecture
- `@st.cache_data` sur toutes les fonctions de chargement
- Validation souple : errors='coerce', warnings si NaN post-cast
- ICP = % de champs clés renseignés par tronçon
- data_loader.py = unique porte d'entrée données

## Dev Agent Record

### Implementation Plan
- data_loader.py : 8 fonctions (load_config, _resolve_path, _validate_columns, _cast_numeric, _classify_risk, _compute_icp, load_scoring, load_referentiel + load_shap/load_backtesting)
- Validation souple : colonnes requises vérifiées, types castés avec coerce, warnings pour NaN post-cast
- ICP calculé sur 5 champs clés (MATERIAU, DIAMETRE, LONGUEUR, POSE, age)
- Classification risque automatique pour les 3 horizons (classe_h1/h3/h5)
- main.py mis à jour : chargement au démarrage, st.stop() si scoring absent, compteur sidebar

### Debug Log
- Tests unitaires Python : scoring 182,075 lignes, 0 colonnes manquantes, 0 warnings cast
- Classes h3 : 117,433 faible / 39,676 modéré / 17,543 élevé / 7,423 critique
- ICP moyen : 95.8%
- Référentiel : 221,957 lignes, 0 colonnes manquantes
- RAM peak : 134.8 MB (bien sous 2 Go NFR5)
- Streamlit HTTP 200 sur localhost:8510

### Completion Notes
- AC1 ✅ : @st.cache_data sur load_scoring/load_referentiel/load_shap/load_backtesting
- AC2 ✅ : Validation colonnes requises depuis data_schemas.py
- AC3 ✅ : _cast_numeric avec errors='coerce', virgules FR gérées (str.replace)
- AC4 ✅ : ICP calculé sur 5 champs clés, moyenne 95.8%
- AC5 ✅ : st.error lisible si fichier manquant + st.stop()
- AC6 ✅ : st.warning avec liste colonnes manquantes
- AC7 ✅ : try/except autour de pd.read_csv, messages métier uniquement
- AC8 ✅ : RAM peak 134.8 MB

## File List
- MODIFIÉ: app/data_loader.py (de squelette → implémentation complète avec 8 fonctions)
- MODIFIÉ: app/data_schemas.py (ajout schéma référentiel, ICP_FIELDS, REFERENTIEL_DTYPES)
- MODIFIÉ: app/main.py (ajout chargement données, compteur sidebar, st.stop)

## Change Log
- 2026-04-03: Story 1.2 implémentée — data_loader complet avec validation souple, ICP, classification risque, gestion erreurs métier. RAM 134 MB.
