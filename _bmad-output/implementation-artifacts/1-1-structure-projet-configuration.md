# Story 1.1 : Structure projet & Configuration

## Story

As a **développeur**,
I want **initialiser la structure app/ avec config.yaml, .streamlit/config.toml et main.py**,
So that **l'application ait une base structurée conforme à l'architecture définie.**

## Status

review

## Acceptance Criteria

- AC1: Les fichiers suivants existent : `app/config.yaml`, `app/.streamlit/config.toml`, `app/main.py`, `app/data_loader.py`, `app/data_schemas.py`, `app/filters.py`, `app/export.py`, `app/optimizer.py`, `app/views/` (5 fichiers)
- AC2: `config.yaml` contient chemins fichiers, mapping colonnes, seuils risque (0.8/0.6/0.3), couleurs (#d32f2f/#ff9800/#fdd835/#4caf50), coûts par défaut
- AC3: `.streamlit/config.toml` contient `layout = "wide"` et le thème couleurs
- AC4: `requirements.txt` contient les 8 dépendances (streamlit, pandas, folium, streamlit-folium, plotly, pyyaml, openpyxl, ortools)
- AC5: `streamlit run app/main.py` lance sans erreur (page vide OK)

## Tasks/Subtasks

- [x] Task 1: Créer `app/config.yaml` avec configuration complète
  - [x] Chemins fichiers données (scoring, référentiel, SHAP, backtesting, GeoJSON, TE mappings)
  - [x] Mapping colonnes V8 → App
  - [x] Seuils de risque et couleurs
  - [x] Coûts remplacement et paramètres réseau
- [x] Task 2: Créer `app/.streamlit/config.toml` avec thème et layout
- [x] Task 3: Créer `app/data_schemas.py` — schémas colonnes requises
- [x] Task 4: Créer `app/data_loader.py` — squelette avec import
- [x] Task 5: Créer `app/filters.py` — squelette module filtrage
- [x] Task 6: Créer `app/export.py` — squelette module export
- [x] Task 7: Créer `app/optimizer.py` — squelette module optimiseur
- [x] Task 8: Créer `app/views/` avec 5 fichiers (carte, tableau, detail, dashboard, optimiseur)
- [x] Task 9: Créer `app/main.py` — point d'entrée minimal
- [x] Task 10: Mettre à jour `requirements.txt` avec les 8 dépendances
- [x] Task 11: Valider `streamlit run app/main.py` démarre sans erreur

## Dev Notes

### Architecture Requirements
- Python 3.14+ (venv existant)
- Chaque vue expose une fonction `render(df_scoring, df_referentiel, config)`
- `data_loader.py` = unique porte d'entrée fichiers
- `filters.py` applique filtres, vues reçoivent DataFrame prétraité
- Convention snake_case partout (sauf classes)
- Aucune valeur en dur — tout dans config.yaml
- `@st.cache_data` pour chargement fichiers
- Session state initialisé dans main.py

### Données V8 existantes
- `V8/output/v8_scoring_fuites.csv` : OBJET, MATERIAU, DIAMETRE, famille_mat, age, score_h1, score_h3, score_h5, rang, top_pct
- `V8/output/v8_shap_importance.csv` : feature, mean_abs_shap
- `V8/output/v8_backtesting.csv` : window, auc, ap, auc_age, gain_vs_age, capture_top20, n_test, n_pos_test
- `V8/output/v8_te_mapping_h{1,3,5}.json` : target encoding par horizon

## Dev Agent Record

### Implementation Plan
- Création de la structure app/ conforme à l'architecture : 11 fichiers Python + config.yaml + .streamlit/config.toml
- config.yaml : chemins vers V8/output/, mapping colonnes, seuils risque, couleurs, coûts, paramètres réseau
- main.py : set_page_config wide, session_state init avec DEFAULTS, sidebar radio 5 vues, routing vers render()
- Chaque vue expose render(df_scoring, df_referentiel, config) avec message placeholder
- data_schemas.py : colonnes requises et types pour scoring, référentiel, SHAP, backtesting

### Debug Log
- Aucun problème rencontré. Imports OK, Streamlit démarre proprement (HTTP 200).

### Completion Notes
- 13 fichiers créés dans app/ (voir File List)
- requirements.txt mis à jour avec 7 nouvelles dépendances (streamlit, folium, streamlit-folium, plotly, pyyaml, openpyxl, ortools)
- `streamlit run app/main.py` lance sans erreur, HTTP 200 confirmé
- Sidebar avec navigation 5 vues fonctionnelle
- Session state initialisé avec toutes les clés requises par l'architecture

## File List
- CRÉÉ: app/config.yaml
- CRÉÉ: app/.streamlit/config.toml
- CRÉÉ: app/main.py
- CRÉÉ: app/data_loader.py
- CRÉÉ: app/data_schemas.py
- CRÉÉ: app/filters.py
- CRÉÉ: app/export.py
- CRÉÉ: app/optimizer.py
- CRÉÉ: app/views/tableau.py
- CRÉÉ: app/views/carte.py
- CRÉÉ: app/views/detail.py
- CRÉÉ: app/views/dashboard.py
- CRÉÉ: app/views/optimiseur.py
- MODIFIÉ: requirements.txt (ajout 7 dépendances Streamlit)

## Change Log
- 2026-04-03: Story 1.1 implémentée — structure app/ complète avec config.yaml, 11 modules Python, .streamlit/config.toml, requirements.txt mis à jour
