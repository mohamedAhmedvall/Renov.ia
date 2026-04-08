---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
status: 'complete'
completedAt: '2026-04-03'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
---

# mohamed_casses - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for mohamed_casses, decomposing the requirements from the PRD, UX Design and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: L'ingénieur peut voir l'ensemble des tronçons du réseau avec un code couleur par niveau de risque (classes : critique, élevé, modéré, faible)

FR2: L'ingénieur peut visualiser les tronçons sur une carte géographique interactive si les données géo sont disponibles (mode carte)

FR3: L'ingénieur peut visualiser les tronçons dans un tableau interactif trié par score (mode tabulaire, toujours disponible)

FR4: L'ingénieur peut basculer entre le mode carte et le mode tabulaire

FR5: L'ingénieur peut zoomer, se déplacer et naviguer sur la carte

FR6: L'application détecte automatiquement la présence du fichier GeoJSON et active le mode carte sans configuration manuelle

FR7: L'ingénieur peut sélectionner un tronçon (clic carte ou clic ligne tableau) pour voir son détail complet

FR8: Le détail tronçon affiche les caractéristiques patrimoniales : matériau, diamètre, longueur, date de pose, âge, statut

FR9: Le détail tronçon affiche le score de risque pour chaque horizon (1 an, 3 ans, 5 ans)

FR10: Le détail tronçon affiche l'explication SHAP : contribution de chaque feature au score, avec indication du sens (augmente/diminue le risque)

FR11: Le détail tronçon affiche l'historique des fuites passées du tronçon (nombre, dates)

FR12: Le détail tronçon affiche un indicateur de fiabilité des données (ICP local) distinguant "risque prédit" de "données insuffisantes"

FR13: L'ingénieur peut filtrer les tronçons par famille de matériau

FR14: L'ingénieur peut filtrer les tronçons par classe de risque (seuil de score configurable)

FR15: L'ingénieur peut filtrer les tronçons par tranche d'âge

FR16: L'ingénieur peut filtrer les tronçons par diamètre

FR17: L'ingénieur peut combiner plusieurs filtres simultanément

FR18: L'ingénieur peut sélectionner l'horizon de prédiction à afficher (1, 3 ou 5 ans)

FR19: L'ingénieur peut trier les résultats par n'importe quelle colonne (score, âge, matériau, nb fuites...)

FR20: L'ingénieur peut exporter la liste des tronçons filtrés en CSV

FR21: L'ingénieur peut choisir les colonnes à inclure dans l'export CSV

FR22: L'export CSV inclut les scores de risque, les features et les valeurs SHAP principales

FR23: L'ingénieur peut voir la répartition des tronçons par classe de risque (graphique)

FR24: L'ingénieur peut voir la distribution des matériaux du réseau

FR25: L'ingénieur peut voir le top N des tronçons les plus à risque

FR26: L'ingénieur peut voir les KPIs patrimoine de base : nombre total de tronçons, km total, âge moyen, ICP global

FR27: L'ingénieur peut voir une vue cohorte matériau × décennie de pose avec les statistiques de risque agrégées

FR28: L'ingénieur peut voir la courbe Lift du modèle démontrant visuellement la valeur ajoutée du scoring prédictif

FR29: L'application charge les données de scoring pré-calculées au démarrage depuis des fichiers CSV

FR30: L'application charge les données patrimoniales de référence depuis un fichier CSV séparé

FR31: L'application valide la cohérence des données au chargement et signale les anomalies (colonnes manquantes, formats incorrects)

FR32: L'application conserve l'état des filtres et de la vue pendant la session

### NonFunctional Requirements

NFR1: Démarrage de l'application < 5 secondes jusqu'à l'affichage de la vue principale

NFR2: Chargement carte (si GeoJSON) < 3 secondes pour ~100k tronçons

NFR3: Réponse filtre/tri < 1 seconde après modification d'un filtre

NFR4: Export CSV < 2 secondes pour un jeu filtré

NFR5: Mémoire RAM < 2 Go pour le dataset complet en mémoire

NFR6: Déploiement local uniquement — Aucune donnée patrimoniale transmise à un serveur externe

NFR7: Pas de télémétrie — Aucune donnée collectée vers l'extérieur

NFR8: Fichiers données stockés sur le poste local, accès contrôlé par les droits OS

NFR9: Pas de credentials en dur — Aucun mot de passe, token ou secret dans le code source

NFR10: Scoring déterministe — Mêmes données d'entrée = mêmes scores affichés

NFR11: Validation données au chargement — L'application détecte et signale les fichiers corrompus ou incomplets sans crash

NFR12: Aucune perte d'état en session — Les filtres et la vue sont conservés tant que l'onglet navigateur est ouvert

NFR13: Gestion des erreurs — Aucun stacktrace Python affiché à l'utilisateur — messages d'erreur lisibles

NFR14: Code lisible — Structure modulaire, fonctions documentées, noms explicites

NFR15: Configuration externalisée — Chemins fichiers, seuils de risque, couleurs → fichier de config, pas en dur

NFR16: Indépendance données/code — Changement de dataset sans modification du code source

NFR17: Dépendances minimales — Nombre de packages Python < 15, toutes open source

NFR18: Format d'entrée standardisé — Spécification documentée du format CSV attendu

NFR19: Déploiement sur nouveau réseau < 1 jour de configuration

NFR20: Compatibilité OS — Fonctionne sur Windows 10+

### Additional Requirements

**Project Structure (Architecture) :**
- Python 3.14+ (venv existant), stack Python pur
- 11 modules Python : main.py, data_loader.py, data_schemas.py, filters.py, optimizer.py, export.py, views/ (carte.py, tableau.py, detail.py, dashboard.py, optimiseur.py)
- Configuration centralisée : config.yaml (chemins, mapping colonnes, seuils, couleurs, coûts)
- .streamlit/config.toml (thème, layout wide)

**Dépendances (8 packages) :**
- streamlit, pandas, folium, streamlit-folium, plotly, pyyaml, openpyxl, ortools

**Data Schemas & Validation :**
- scoring_troncons.csv : ID tronçon, scores H1/H3/H5, features, SHAP
- referentiel_troncons.csv : matériau, diamètre, longueur, date pose, statut
- shap_importance.csv : SHAP mean_abs par feature
- backtesting.csv : AUC, capture, gain
- troncons.geojson : tracés géographiques (OPTIONNEL)
- te_mappings/ : target encoding par horizon (3 JSON)
- Mapping configurable colonnes sources → colonnes app dans config.yaml
- Validation souple : colonnes requises, cast avec coerce, warnings NaN, calcul ICP

**Frontières architecturales :**
- data_loader.py = unique porte d'entrée fichiers
- filters.py applique filtres, vues reçoivent DataFrame prétraité
- optimizer.py = module pur Python sans Streamlit (testable indépendamment)
- main.py initialise TOUS les session_state

**Patterns clés :**
- @st.cache_data sur chargement fichiers
- session_state pour filtres/vue/sélection/horizon
- OR-Tools CP-SAT : maximiser Σ(score×longueur), contraintes budget/forçages/exclusions
- Locale française : scores %, âge "ans", longueur "m", coûts "€", dates dd/mm/yyyy
- Zéro stacktrace Python → messages métier

### UX Design Requirements

UX-DR1: Code couleur système universel — 🔴 Critique (#d32f2f, ≥0.8), 🟠 Élevé (#ff9800, ≥0.6), 🟡 Modéré (#fdd835, ≥0.3), 🟢 Faible (#4caf50, <0.3)

UX-DR2: Couleur TOUJOURS accompagnée de texte label (accessibilité daltonisme)

UX-DR3: KPI cards (st.metric × 4 colonnes) en en-tête de CHAQUE vue

UX-DR4: Navigation sidebar radio permanente (5 vues)

UX-DR5: Filtres sidebar réactifs (aucun bouton "Appliquer") — multiselect + sliders

UX-DR6: Compteur filtrage sidebar "X / Y tronçons"

UX-DR7: Vue Tableau par défaut — st.dataframe tri score DESC, clic ligne → Détail

UX-DR8: Vue Carte — tronçons colorés + popup Folium + "Voir détail →"

UX-DR9: Mode failsafe carte — GeoJSON absent → warning + tableau forcé

UX-DR10: Vue Détail — KPI tronçon + caractéristiques + scores H1/H3/H5

UX-DR11: Barres "Facteurs de risque" (SHAP métier) — barres Plotly + texte "Feature (valeur) — augmente/diminue le risque"

UX-DR12: Indicateur ICP ✅/⚠️ avec détail manquant

UX-DR13: Bouton "← Retour tableau" préservant filtres

UX-DR14: Vue Dashboard — distribution + top 10 + cohorte + Lift

UX-DR15: Heatmap cohorte matériau × décennie

UX-DR16: Courbe Lift cumulative

UX-DR17: Vue Optimiseur — budget, horizon, options avancées

UX-DR18: Options avancées optimiseur dans st.expander() — forçages, exclusions, what-if

UX-DR19: Bouton "🚀 Lancer l'optimisation" + spinner

UX-DR20: Résultats optimiseur KPI — budget, km, fuites évitées, ROI

UX-DR21: Résultats optimiseur tableau priorisé cliquable → Détail

UX-DR22: Export CSV universel "⬇ Exporter CSV" toujours visible

UX-DR23: Export CSV avec sélection colonnes

UX-DR24: Export plan renouvellement post-optimiseur

UX-DR25: Messages erreur/warning/info en langage métier, jamais de stacktrace

UX-DR26: État vide — "Aucun tronçon ne correspond aux filtres"

UX-DR27: Traduction ML → métier ("SHAP" → "Facteurs de risque", etc.)

UX-DR28: Langage métier cohérent dans toute l'app

UX-DR29: Progressive disclosure optimiseur

UX-DR30: Session state navigation fluide (clic → detail → retour)

UX-DR31: Sidebar layout : nav → séparateur → filtres → séparateur → compteur

UX-DR32: Structure verticale constante : KPI → contenu → actions

UX-DR33: Desktop ≥ 1280×720 uniquement

UX-DR34: .streamlit/config.toml layout = "wide"

UX-DR35: Contraste WCAG AAA (#212121 sur #ffffff)

UX-DR36: Accessibilité daltonisme — labels texte obligatoires avec couleurs

UX-DR37: Barres SHAP : rouge augmente, bleu diminue risque

UX-DR38: Pas de modals — tout inline

UX-DR39: Pas de pagination — scroll natif + filtres

UX-DR40: Deux chemins vers Détail : tableau (clic ligne) et carte (popup → bouton)

UX-DR41: Feedback instantané filtres sur KPI et compteur

UX-DR42: Emojis ✅⚠️🔴🟠🟡🟢 toujours avec texte label

UX-DR43: Horizon radio 1/3/5 ans change tous les scores sans rechargement

UX-DR44: Démarrage zéro config — ouverture → données chargées < 5s

UX-DR45: Format dates dd/mm/yyyy français

UX-DR46: Export CSV UTF-8 avec nommage horodaté

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 1 | Code couleur risque sur les tronçons |
| FR2 | Epic 5 | Carte géographique interactive |
| FR3 | Epic 1 | Tableau interactif trié par score |
| FR4 | Epic 5 | Bascule carte/tabulaire |
| FR5 | Epic 5 | Zoom/navigation carte |
| FR6 | Epic 5 | Détection auto GeoJSON |
| FR7 | Epic 3 | Sélection tronçon → détail |
| FR8 | Epic 3 | Caractéristiques patrimoniales |
| FR9 | Epic 3 | Scores par horizon |
| FR10 | Epic 3 | Explication SHAP/facteurs de risque |
| FR11 | Epic 3 | Historique fuites |
| FR12 | Epic 3 | Indicateur ICP |
| FR13 | Epic 2 | Filtre par matériau |
| FR14 | Epic 2 | Filtre par classe risque |
| FR15 | Epic 2 | Filtre par âge |
| FR16 | Epic 2 | Filtre par diamètre |
| FR17 | Epic 2 | Combinaison filtres |
| FR18 | Epic 2 | Sélection horizon |
| FR19 | Epic 2 | Tri multi-colonnes |
| FR20 | Epic 4 | Export CSV |
| FR21 | Epic 4 | Choix colonnes export |
| FR22 | Epic 4 | SHAP dans export |
| FR23 | Epic 6 | Distribution classes risque |
| FR24 | Epic 6 | Distribution matériaux |
| FR25 | Epic 6 | Top N tronçons |
| FR26 | Epic 6 | KPIs patrimoine |
| FR27 | Epic 6 | Vue cohorte |
| FR28 | Epic 6 | Courbe Lift |
| FR29 | Epic 1 | Chargement scoring CSV |
| FR30 | Epic 1 | Chargement référentiel CSV |
| FR31 | Epic 1 | Validation données |
| FR32 | Epic 1 | Conservation état session |

## Epic List

### Epic 1 : Fondation & Chargement de données
L'application Streamlit démarre, charge les données CSV de scoring, valide leur cohérence, et affiche la vue tabulaire par défaut avec les tronçons colorés par risque.
**FRs couverts :** FR1, FR3, FR29, FR30, FR31, FR32
**NFRs adressés :** NFR1, NFR5, NFR10, NFR11, NFR13, NFR14, NFR15, NFR16, NFR17, NFR18, NFR20

### Epic 2 : Filtres & Exploration tabulaire
L'ingénieur peut filtrer les tronçons (matériau, score, âge, diamètre), changer d'horizon (1/3/5 ans), trier par colonne, et voir les KPI cards se mettre à jour en temps réel.
**FRs couverts :** FR13, FR14, FR15, FR16, FR17, FR18, FR19
**NFRs adressés :** NFR3, NFR12

### Epic 3 : Détail tronçon & Facteurs de risque
L'ingénieur clique un tronçon et accède au détail complet : caractéristiques patrimoniales, scores par horizon, facteurs de risque en langage métier, et indicateur de fiabilité ICP.
**FRs couverts :** FR7, FR8, FR9, FR10, FR11, FR12

### Epic 4 : Export CSV
L'ingénieur exporte la liste filtrée en CSV avec sélection de colonnes, incluant scores et facteurs de risque.
**FRs couverts :** FR20, FR21, FR22
**NFRs adressés :** NFR4

### Epic 5 : Vue Carte interactive
L'ingénieur visualise les tronçons géolocalisés sur une carte Folium, colorés par risque, avec popup au clic et navigation vers le détail. Mode dégradé si GeoJSON absent.
**FRs couverts :** FR2, FR4, FR5, FR6
**NFRs adressés :** NFR2

### Epic 6 : Dashboard KPIs & Analytics
L'ingénieur accède au dashboard avec distribution des risques, top N tronçons, vue cohorte matériau×décennie, et courbe Lift du modèle.
**FRs couverts :** FR23, FR24, FR25, FR26, FR27, FR28

### Epic 7 : Optimiseur de renouvellement
L'ingénieur paramètre un budget, lance l'optimisation OR-Tools, et obtient un plan de renouvellement priorisé avec KPIs d'impact (fuites évitées, ROI). Forçages, exclusions et what-if matériau disponibles.

## Epic 1 : Fondation & Chargement de données

L'application Streamlit démarre, charge les données CSV de scoring, valide leur cohérence, et affiche la vue tabulaire par défaut avec les tronçons colorés par risque.

### Story 1.1 : Structure projet & Configuration

As a **développeur**,
I want **initialiser la structure app/ avec config.yaml, .streamlit/config.toml et main.py**,
So that **l'application ait une base structurée conforme à l'architecture définie.**

**Acceptance Criteria:**

**Given** le repository existe avec le venv Python
**When** la structure app/ est créée
**Then** les fichiers suivants existent : `app/config.yaml`, `app/.streamlit/config.toml`, `app/main.py`, `app/data_loader.py`, `app/data_schemas.py`, `app/filters.py`, `app/export.py`, `app/optimizer.py`, `app/views/` (5 fichiers vides)
**And** `config.yaml` contient les chemins fichiers, mapping colonnes, seuils risque (0.8/0.6/0.3), couleurs (#d32f2f/#ff9800/#fdd835/#4caf50), coûts par défaut
**And** `.streamlit/config.toml` contient `layout = "wide"` et le thème couleurs
**And** `requirements.txt` contient les 8 dépendances (streamlit, pandas, folium, streamlit-folium, plotly, pyyaml, openpyxl, ortools)
**And** `streamlit run app/main.py` lance sans erreur (page vide OK)

### Story 1.2 : Chargement données & Validation

As a **ingénieur patrimoine**,
I want **que l'application charge automatiquement les fichiers CSV de scoring et de référentiel au démarrage**,
So that **je puisse voir mes données sans configuration manuelle.**

**Acceptance Criteria:**

**Given** les fichiers `scoring_troncons.csv` et `referentiel_troncons.csv` existent dans le dossier configuré
**When** l'application démarre
**Then** les données sont chargées en < 5s via `@st.cache_data` (NFR1)
**And** les colonnes requises sont validées selon `data_schemas.py` et le mapping `config.yaml`
**And** les types sont castés avec `errors='coerce'` (pas de crash sur données invalides)
**And** un ICP (Indice de Connaissance Patrimoniale) est calculé par tronçon
**And** si un fichier est manquant → `st.error("Fichier de scoring introuvable. Vérifiez le chemin dans config.yaml.")`
**And** si des colonnes sont manquantes → `st.warning()` lisible avec les colonnes absentes
**And** aucun stacktrace Python n'est visible (NFR13)
**And** RAM < 2 Go pour le dataset complet (NFR5)

### Story 1.3 : Navigation sidebar & Session state

As a **ingénieur patrimoine**,
I want **une sidebar avec navigation entre les 5 vues et un compteur de tronçons**,
So that **je puisse basculer facilement entre les différentes vues de l'application.**

**Acceptance Criteria:**

**Given** les données sont chargées
**When** l'application est ouverte
**Then** la sidebar affiche 5 radio buttons : Tableau / Carte / Détail / Dashboard / Optimiseur (UX-DR4)
**And** la sidebar suit la structure : navigation → séparateur → (filtres vides pour l'instant) → séparateur → compteur (UX-DR31)
**And** le compteur affiche "X / Y tronçons" (UX-DR6)
**And** `session_state` est initialisé dans `main.py` avec les clés : `vue_active`, `horizon`, `filtres`, `troncon_selectionne`, `budget_enveloppe`, `troncons_forces`, `troncons_exclus`
**And** changer de vue via radio met à jour `session_state.vue_active` et le contenu (FR32)
**And** la vue Détail sans tronçon sélectionné affiche `st.info("Sélectionnez un tronçon depuis le tableau ou la carte.")`

### Story 1.4 : Vue Tableau par défaut

As a **ingénieur patrimoine**,
I want **voir un tableau de tous mes tronçons classés par score de risque avec un code couleur**,
So that **j'identifie immédiatement les tronçons les plus à risque.**

**Acceptance Criteria:**

**Given** les données sont chargées et la vue Tableau est active (défaut)
**When** le tableau s'affiche
**Then** 4 KPI cards en en-tête : nb tronçons, % critique/élevé, score moyen, ICP global (UX-DR3, UX-DR32)
**And** un `st.dataframe` affiche les colonnes : OBJET, Matériau, Âge, Score, Classe risque (FR3)
**And** le tableau est trié par score DESC par défaut (UX-DR7)
**And** chaque ligne est colorée par classe de risque : 🔴 CRITIQUE (≥0.8), 🟠 ÉLEVÉ (≥0.6), 🟡 MODÉRÉ (≥0.3), 🟢 FAIBLE (<0.3) (FR1, UX-DR1)
**And** le texte label accompagne toujours la couleur (UX-DR2, UX-DR36)
**And** les scores sont affichés en % avec 1 décimale, l'âge en "X ans" (locale FR)
**And** le chargement total (démarrage → tableau visible) est < 5s (NFR1)

## Epic 2 : Filtres & Exploration tabulaire

L'ingénieur peut filtrer les tronçons (matériau, score, âge, diamètre), changer d'horizon (1/3/5 ans), trier par colonne, et voir les KPI cards se mettre à jour en temps réel.

### Story 2.1 : Filtres sidebar réactifs

As a **ingénieur patrimoine**,
I want **filtrer les tronçons par matériau, classe de risque, âge et diamètre depuis la sidebar**,
So that **je puisse cibler les tronçons qui m'intéressent pour mes campagnes terrain.**

**Acceptance Criteria:**

**Given** les données sont chargées et la sidebar est affichée
**When** je modifie un filtre dans la sidebar
**Then** un `st.sidebar.multiselect("Matériau")` propose les familles de matériau disponibles (FR13)
**And** un `st.sidebar.slider("Score min")` filtre par seuil de score (FR14)
**And** un `st.sidebar.slider("Âge min")` filtre par tranche d'âge (FR15)
**And** un `st.sidebar.slider("Diamètre")` filtre par diamètre (FR16)
**And** les filtres se combinent (intersection) sans bouton "Appliquer" — mise à jour instantanée (FR17, UX-DR5)
**And** la logique de filtrage est dans `filters.py`, le DataFrame filtré est passé à la vue active
**And** le compteur sidebar "X / Y tronçons" se met à jour en temps réel (UX-DR6, UX-DR41)
**And** les KPI cards en en-tête reflètent le jeu filtré
**And** la réponse filtre est < 1s (NFR3)

### Story 2.2 : Sélection horizon de prédiction

As a **ingénieur patrimoine**,
I want **basculer entre les horizons 1 an, 3 ans et 5 ans**,
So that **je puisse adapter ma vision du risque selon mon horizon de planification.**

**Acceptance Criteria:**

**Given** la sidebar est affichée
**When** je sélectionne un horizon via `st.sidebar.radio("Horizon", [1, 3, 5])`
**Then** `session_state.horizon` est mis à jour (FR18)
**And** le score affiché dans le tableau bascule sur la colonne correspondante (score_h1/h3/h5)
**And** les classes de risque (couleurs) sont recalculées sur le nouveau score
**And** les KPI cards se mettent à jour avec les statistiques de l'horizon sélectionné
**And** le changement est instantané sans rechargement page (UX-DR43)
**And** l'horizon est persisté dans session_state entre les vues (NFR12)

### Story 2.3 : Tri multi-colonnes

As a **ingénieur patrimoine**,
I want **trier le tableau par n'importe quelle colonne**,
So that **je puisse explorer les données selon différents critères (âge, matériau, nb fuites...).**

**Acceptance Criteria:**

**Given** le tableau est affiché dans la vue Tableau
**When** je clique sur un en-tête de colonne
**Then** le tableau se trie par cette colonne (FR19)
**And** un clic secondaire inverse l'ordre (ASC/DESC)
**And** le tri natif `st.dataframe` est utilisé
**And** les filtres restent appliqués pendant le tri (NFR12)

## Epic 3 : Détail tronçon & Facteurs de risque

L'ingénieur clique un tronçon et accède au détail complet : caractéristiques patrimoniales, scores par horizon, facteurs de risque en langage métier, et indicateur de fiabilité ICP.

### Story 3.1 : Navigation clic tronçon → vue Détail

As a **ingénieur patrimoine**,
I want **cliquer sur un tronçon dans le tableau pour basculer vers sa vue détaillée**,
So that **je puisse approfondir l'analyse d'un tronçon qui m'intéresse.**

**Acceptance Criteria:**

**Given** le tableau est affiché avec des tronçons
**When** je clique sur une ligne du tableau
**Then** `session_state.troncon_selectionne` est mis à jour avec l'ID du tronçon (FR7)
**And** `session_state.vue_active` bascule automatiquement vers "detail" (UX-DR30)
**And** `st.rerun()` est appelé pour rafraîchir l'affichage
**And** un bouton "← Retour tableau" est affiché en haut de la vue Détail (UX-DR13)
**And** cliquer "← Retour" restaure la vue précédente avec les filtres préservés (UX-DR46)

### Story 3.2 : Affichage détail patrimonial & scores par horizon

As a **ingénieur patrimoine**,
I want **voir les caractéristiques patrimoniales du tronçon et ses scores par horizon**,
So that **je comprenne le profil complet du tronçon sélectionné.**

**Acceptance Criteria:**

**Given** un tronçon est sélectionné et la vue Détail est active
**When** la vue s'affiche
**Then** 4 KPI cards en en-tête : score actuel, âge, matériau, classe de risque (colorée 🔴🟠🟡🟢 + texte) (UX-DR10)
**And** un bloc "Caractéristiques patrimoniales" affiche : longueur (m), diamètre (mm), date de pose, matériau, nb fuites historiques (FR8)
**And** un bloc "Scores par horizon" affiche les 3 scores (H1/H3/H5) avec code couleur et classe (FR9)
**And** un bloc "Historique fuites" affiche le nombre et dates des fuites passées en format dd/mm/yyyy (FR11, UX-DR45)
**And** les formats respectent la locale française : "142 m", "62 ans", "100 mm"

### Story 3.3 : Barres facteurs de risque (SHAP métier)

As a **ingénieur patrimoine**,
I want **voir les facteurs qui expliquent le score de risque du tronçon en langage compréhensible**,
So that **je comprenne POURQUOI ce tronçon est à risque sans connaître le machine learning.**

**Acceptance Criteria:**

**Given** un tronçon est sélectionné avec des données SHAP disponibles
**When** le bloc "Facteurs de risque" s'affiche
**Then** les 5 features SHAP sont affichées en barres horizontales Plotly (FR10, UX-DR11)
**And** chaque barre a un label texte : "Feature (valeur) — augmente/diminue [fortement/moyennement/faiblement] le risque" (UX-DR27)
**And** barres rouges (#d32f2f) = augmente risque, barres bleues (#1976d2) = diminue risque (UX-DR37)
**And** le mot "SHAP" n'apparaît JAMAIS dans l'interface — remplacé par "Facteurs de risque" (UX-DR27)
**And** si données SHAP manquantes → barre grisée + "Donnée non disponible"
**And** le hover sur une barre affiche la contribution numérique (ex: "+0.32 au score final")

### Story 3.4 : Indicateur ICP (fiabilité données)

As a **ingénieur patrimoine**,
I want **voir si les données du tronçon sont fiables ou incomplètes**,
So that **je puisse calibrer ma confiance dans le score affiché.**

**Acceptance Criteria:**

**Given** un tronçon est sélectionné
**When** la vue Détail s'affiche
**Then** l'indicateur ICP est visible : `st.success("✅ Données fiables")` si ICP ≥ seuil (FR12, UX-DR12)
**And** si ICP < seuil → `st.warning("⚠️ Données incomplètes — [détail]")` avec la liste des colonnes manquantes/imputées (UX-DR42)
**And** le texte du warning est explicite : ex. "Date de pose manquante (imputée 1900), Matériau 'Autre'"
**And** l'indicateur est toujours accompagné de texte + icône (jamais couleur seule) (UX-DR2)

## Epic 4 : Export CSV

L'ingénieur exporte la liste filtrée en CSV avec sélection de colonnes, incluant scores et facteurs de risque.

### Story 4.1 : Export CSV du jeu filtré

As a **ingénieur patrimoine**,
I want **exporter la liste filtrée des tronçons en CSV**,
So that **je puisse envoyer une liste au chef d'exploitation pour les tournées terrain.**

**Acceptance Criteria:**

**Given** des tronçons sont affichés (avec ou sans filtres)
**When** je clique "⬇ Exporter CSV"
**Then** un fichier CSV UTF-8 est téléchargé via `st.download_button` (FR20, UX-DR22)
**And** le nommage du fichier suit le format `troncons_YYYYMMDD.csv` (UX-DR46)
**And** l'export inclut les scores de risque et les valeurs SHAP principales (FR22)
**And** l'export est < 2s (NFR4)
**And** le bouton export est toujours visible quand un jeu filtré existe (UX-DR22)

### Story 4.2 : Sélection des colonnes à exporter

As a **ingénieur patrimoine**,
I want **choisir quelles colonnes inclure dans l'export CSV**,
So that **je puisse adapter le fichier au destinataire (terrain, direction, etc.).**

**Acceptance Criteria:**

**Given** je suis sur la vue Tableau avec des tronçons filtrés
**When** je configure l'export
**Then** un `st.multiselect("Colonnes à exporter")` propose : OBJET, matériau, âge, diamètre, longueur, score, classe, facteurs de risque, nb fuites, ICP (FR21)
**And** les colonnes par défaut sont pré-sélectionnées (OBJET, matériau, âge, score, classe)
**And** l'export CSV contient uniquement les colonnes sélectionnées (UX-DR23)
**And** le CSV respecte l'encodage UTF-8 pour les caractères accentués

## Epic 5 : Vue Carte interactive

L'ingénieur visualise les tronçons géolocalisés sur une carte Folium, colorés par risque, avec popup au clic et navigation vers le détail. Mode dégradé si GeoJSON absent.

### Story 5.1 : Carte Folium avec tronçons colorés

As a **ingénieur patrimoine**,
I want **visualiser les tronçons sur une carte géographique colorés par niveau de risque**,
So that **j'identifie visuellement les zones géographiques à risque.**

**Acceptance Criteria:**

**Given** un fichier GeoJSON est disponible dans le dossier configuré
**When** la vue Carte est active
**Then** une carte Folium `st_folium()` affiche les tronçons colorés par classe de risque (FR2, UX-DR8)
**And** les couleurs correspondent au système universel : 🔴🟠🟡🟢 (UX-DR1)
**And** l'ingénieur peut zoomer, se déplacer et naviguer sur la carte (FR5)
**And** les KPI cards en en-tête sont identiques à la vue Tableau (même 4 métriques) (UX-DR3)
**And** les filtres sidebar s'appliquent aussi à la carte (UX-DR41)
**And** le chargement carte est < 3s pour ~100k tronçons (NFR2)

### Story 5.2 : Popup tronçon & navigation vers Détail

As a **ingénieur patrimoine**,
I want **cliquer un tronçon sur la carte pour voir un résumé et accéder au détail**,
So that **je puisse identifier et analyser un tronçon directement depuis la carte.**

**Acceptance Criteria:**

**Given** la carte Folium est affichée avec des tronçons
**When** je clique sur un tronçon
**Then** un popup Folium affiche : score, matériau, âge, classe risque (UX-DR8)
**And** un bouton "Voir détail →" dans le popup permet la navigation (UX-DR40)
**And** cliquer "Voir détail →" bascule vers la vue Détail avec le tronçon sélectionné (FR7)

### Story 5.3 : Mode dégradé sans GeoJSON

As a **ingénieur patrimoine**,
I want **que l'application fonctionne normalement même sans fichier GeoJSON**,
So that **je puisse utiliser toutes les autres fonctionnalités sans être bloqué.**

**Acceptance Criteria:**

**Given** aucun fichier GeoJSON n'est trouvé
**When** l'application démarre
**Then** la détection est automatique (FR6) — pas d'erreur, pas de crash
**And** `st.warning("Fichier GeoJSON non trouvé. Mode tabulaire uniquement.")` est affiché (UX-DR9)
**And** la vue Carte est masquée ou affiche le warning au lieu de la carte
**And** la navigation sidebar fonctionne normalement (Tableau reste le défaut)
**And** la bascule carte/tabulaire est gérée gracieusement (FR4)

## Epic 6 : Dashboard KPIs & Analytics

L'ingénieur accède au dashboard avec distribution des risques, top N tronçons, vue cohorte matériau×décennie, et courbe Lift du modèle.

### Story 6.1 : Distribution risques & KPIs patrimoine

As a **ingénieur patrimoine**,
I want **voir la répartition des tronçons par classe de risque et les KPIs patrimoine**,
So that **j'aie une vue d'ensemble de l'état de mon réseau.**

**Acceptance Criteria:**

**Given** les données sont chargées et la vue Dashboard est active
**When** le dashboard s'affiche
**Then** 4 KPI cards en en-tête : nb tronçons, km total, âge moyen, ICP global (FR26, UX-DR3)
**And** un histogramme Plotly affiche la distribution par classe de risque (4 barres colorées) (FR23)
**And** un graphique Plotly affiche la distribution des matériaux du réseau (FR24)
**And** les filtres sidebar s'appliquent au dashboard (cohérence globale)

### Story 6.2 : Top N tronçons & Tableau cliquable

As a **ingénieur patrimoine**,
I want **voir les tronçons les plus à risque dans un classement**,
So that **je puisse identifier rapidement les priorités d'intervention.**

**Acceptance Criteria:**

**Given** la vue Dashboard est active
**When** le bloc "Top 10 tronçons" s'affiche
**Then** un tableau liste les 10 tronçons avec le score le plus élevé (FR25, UX-DR14)
**And** chaque ligne est cliquable → bascule vers vue Détail
**And** le rang et le score sont affichés avec code couleur classe

### Story 6.3 : Vue cohorte matériau × décennie

As a **ingénieur patrimoine**,
I want **voir une heatmap croisant matériau et décennie de pose**,
So that **j'identifie les cohortes patrimoniales les plus problématiques.**

**Acceptance Criteria:**

**Given** la vue Dashboard est active
**When** le bloc cohorte s'affiche
**Then** une heatmap Plotly affiche matériau (lignes) × décennie de pose (colonnes) (FR27, UX-DR15)
**And** la couleur représente le score moyen de risque de la cohorte
**And** le hover affiche : nb tronçons, score moyen, nb fuites de la cohorte
**And** les cohortes à haut risque sont visuellement identifiables (rouge intense)

### Story 6.4 : Courbe Lift du modèle

As a **ingénieur patrimoine**,
I want **voir la courbe Lift du modèle de scoring**,
So that **je puisse démontrer visuellement la valeur ajoutée du scoring vs la sélection aléatoire.**

**Acceptance Criteria:**

**Given** les données de backtesting sont disponibles
**When** le bloc Lift s'affiche
**Then** un graphique Plotly affiche : % cumulé de fuites capturées (Y) vs % du réseau priorisé (X) (FR28, UX-DR16)
**And** une ligne diagonale "sélection aléatoire" est affichée en référence
**And** le titre est "Valeur ajoutée du scoring" (pas "Lift curve")
**And** si données backtesting manquantes → `st.info("Données de validation non disponibles")`

## Epic 7 : Optimiseur de renouvellement

L'ingénieur paramètre un budget, lance l'optimisation OR-Tools, et obtient un plan de renouvellement priorisé avec KPIs d'impact (fuites évitées, ROI). Forçages, exclusions et what-if matériau disponibles.

### Story 7.1 : Formulaire paramètres optimiseur

As a **ingénieur patrimoine**,
I want **paramétrer un budget et un horizon pour l'optimisation de renouvellement**,
So that **je puisse définir les contraintes de mon programme de renouvellement.**

**Acceptance Criteria:**

**Given** la vue Optimiseur est active
**When** le formulaire s'affiche
**Then** un `st.number_input("Budget max (€)")` est disponible (UX-DR17)
**And** un `st.radio("Horizon", [1, 3, 5])` est disponible
**And** un `st.expander("▶ Options avancées")` contient : forçages (multiselect ID tronçons), exclusions (multiselect), what-if matériau (radio) (UX-DR18, UX-DR29)
**And** les filtres sidebar sont masqués sur cette vue (UX-DR17)
**And** un bouton "🚀 Lancer l'optimisation" est affiché pleine largeur (UX-DR19)

### Story 7.2 : Moteur OR-Tools & Résultats

As a **ingénieur patrimoine**,
I want **lancer l'optimisation et obtenir un plan de renouvellement priorisé**,
So that **j'aie un argumentaire chiffré pour le budget renouvellement.**

**Acceptance Criteria:**

**Given** les paramètres sont saisis (budget, horizon)
**When** je clique "🚀 Lancer l'optimisation"
**Then** `st.spinner("Optimisation en cours...")` est affiché (UX-DR19)
**And** `optimizer.py` résout le problème : maximiser Σ(score×longueur) sous contrainte budget (Architecture OR-Tools)
**And** les forçages/exclusions sont respectés
**And** 4 KPI résultats en `st.metric` : budget utilisé (€), km renouvelés, fuites évitées, ROI (UX-DR20)
**And** un tableau priorisé liste les tronçons sélectionnés avec score, coût, priorité (UX-DR21)
**And** chaque ligne du tableau est cliquable → vue Détail
**And** si contraintes impossibles → `st.error("Impossible d'optimiser avec ces contraintes")` (UX-DR25)
**And** le calcul est < 5s

### Story 7.3 : Export plan de renouvellement

As a **ingénieur patrimoine**,
I want **exporter le plan de renouvellement optimisé en CSV**,
So that **je puisse présenter un document chiffré au directeur technique.**

**Acceptance Criteria:**

**Given** les résultats de l'optimisation sont affichés
**When** je clique "⬇ Exporter plan renouvellement CSV"
**Then** un CSV est téléchargé via `st.download_button` (UX-DR24)
**And** le fichier contient : OBJET, Score, Coût, Priorité, Horizon
**And** le nommage suit `plan_renouvellement_YYYYMMDD.csv` (UX-DR46)
**And** l'encodage est UTF-8
