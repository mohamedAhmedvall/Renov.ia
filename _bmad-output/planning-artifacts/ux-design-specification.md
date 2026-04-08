---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-core-experience', 'step-04-emotional-response', 'step-05-inspiration', 'step-06-design-system', 'step-07-defining-experience', 'step-08-visual-foundation', 'step-09-design-directions', 'step-10-user-journeys', 'step-11-component-strategy', 'step-12-ux-patterns', 'step-13-responsive-accessibility', 'step-14-complete']
status: 'complete'
completedAt: '2026-04-03'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
---

# UX Design Specification mohamed_casses

**Author:** mohamed
**Date:** 2026-04-03

---

<!-- UX design content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

### Project Vision

Transformer le scoring ML de prédiction de fuites et d'abandon en outil décisionnel visuel pour l'ingénieur patrimoine réseau eau. L'enjeu UX n'est pas technique — c'est la confiance. L'outil doit convaincre un ingénieur sceptique en moins de 5 minutes que le modèle voit ce que lui ne peut pas voir.

### Target Users

**Persona unique MVP : Karim — Ingénieur Patrimoine Réseau**

- Profil : 10+ ans d'expérience, connaît son réseau, sceptique pragmatique
- Contexte d'usage : PC fixe bureau, usage épisodique (campagnes terrain, cycle budgétaire)
- Compétences digitales : Excel avancé, pas de culture data science
- Critère d'adoption : comprendre le "pourquoi" d'un score, pas juste le score
- Workflow : découvrir → filtrer → exporter CSV → envoyer au terrain

### Key Design Challenges

1. **Confiance et transparence** — SHAP traduit en langage métier, pas en jargon ML
2. **Densité vs clarté** — 5 vues riches dans un framework minimaliste
3. **Navigation contextuelle** — Passage fluide carte/tableau → détail sans perte d'état
4. **Complexité optimiseur** — Interface de paramétrage avec progressive disclosure

### Design Opportunities

1. **Code couleur universel** — 4 classes de risque (rouge/orange/jaune/vert) cohérentes sur toutes les vues
2. **SHAP en langage naturel** — Barres visuelles + texte métier au lieu de valeurs numériques
3. **Progressive disclosure** — Mode simple/avancé pour l'optimiseur
4. **ICP comme signal de confiance** — Transparence sur la fiabilité des données par tronçon

## Core User Experience

### Defining Experience

L'action core est : **voir un tronçon coloré → cliquer → comprendre pourquoi il est à risque**. Tout le produit gravite autour de ce moment. Les filtres, l'export, l'optimiseur sont des extensions de cette boucle fondamentale.

Le succès se mesure au "moment SHAP" — quand Karim lit l'explication d'un tronçon rouge et reconnaît un profil qu'il connaît. C'est la bascule de scepticisme à adoption.

### Platform Strategy

- Application Streamlit desktop — navigateur Chrome/Edge sur PC fixe Windows 10+
- Souris/clavier uniquement — pas de tactile, pas de mobile
- Données locales — pas de dépendance réseau
- Démarrage sans configuration — `streamlit run main.py` → navigateur s'ouvre → données chargées

### Effortless Interactions

| Interaction | Pattern UX |
|---|---|
| Démarrage | Zéro config — ouverture → carte/tableau coloré en < 5s |
| Compréhension score | Clic → SHAP en langage métier, pas en valeurs numériques |
| Filtrage | Sidebar réactive — pas de bouton "Appliquer", mise à jour instantanée |
| Changement horizon | Toggle 1/3/5 ans — tout se met à jour (couleurs, scores, tri) |
| Export | 1 clic → CSV téléchargé avec filtres et colonnes appliqués |
| Navigation | Clic tronçon sur carte/tableau → bascule automatique vers vue détail |

### Critical Success Moments

1. **Premier contact (< 30s)** — Carte/tableau coloré visible immédiatement → "je vois mon réseau"
2. **Moment carte rouge (< 5 min)** — Tronçon inattendu + SHAP convaincant → "le modèle voit ce que j'avais oublié"
3. **Export terrain (< 2 min)** — Filtrer + exporter le top N → envoi au chef d'exploitation
4. **Argumentaire budget** — Dashboard + optimiseur → chiffres précis pour les élus
5. **Transparence limites** — ICP signale "données incomplètes" → confiance renforcée sur les scores fiables

### Experience Principles

1. **Transparence d'abord** — Chaque score accompagné de son explication. Jamais de boîte noire. L'ICP signale les limites.
2. **Zéro friction au démarrage** — Pas de config, pas de login. Ouvrir → voir → comprendre en < 30s.
3. **Langage métier, pas ML** — Vocabulaire de l'ingénieur réseau : matériau, âge, fuites. Pas de jargon data science.
4. **Progressive disclosure** — Simple par défaut, avancé sur demande. L'optimiseur a deux modes.
5. **Code couleur comme langage** — Rouge/orange/jaune/vert cohérent sur toutes les vues.

## Desired Emotional Response

### Primary Emotional Goals

1. **Confiance** — L'outil est honnête. Il explique ses scores (SHAP), signale ses limites (ICP), et prouve sa valeur (backtesting). Karim fait confiance parce que l'outil ne bluff pas.
2. **Maîtrise** — Karim contrôle l'outil. Filtres, forçages, horizon, export — tout est à sa main. L'outil augmente son expertise, ne la remplace pas.
3. **Efficacité** — Ce qui prenait une demi-journée sous Excel prend 2 minutes. Le gain est tangible et immédiat.

### Emotional Journey Mapping

| Phase | Émotion | Déclencheur |
|---|---|---|
| Découverte (1ère ouverture) | Curiosité → Clarté | Carte/tableau coloré immédiat, pas de setup |
| Exploration (5 premières minutes) | Surprise constructive | Tronçon rouge inattendu + SHAP convaincant |
| Usage régulier | Maîtrise + Efficacité | Filtrer → exporter → envoyer en < 2 min |
| Argumentation budget | Empowerment | Chiffres précis : X€ → Y fuites évitées |
| Erreur / limite modèle | Honnêteté rassurante | ICP signale "données incomplètes", pas de fausse certitude |
| Retour après absence | Familiarité | Même interface, même logique, reprise immédiate |

### Micro-Emotions

| Micro-émotion | Critique pour nous | Pattern design |
|---|---|---|
| Confiance vs Scepticisme | ⭐ LA plus critique | SHAP lisible + ICP + backtesting |
| Accomplissement vs Frustration | Haute | Export fluide, pas de dead-ends |
| Contrôle vs Impuissance | Haute | Forçages, filtres, choix horizon |
| Calme vs Surcharge | Moyenne | Progressive disclosure, hiérarchie visuelle |

### Design Implications

- **Confiance → Transparence systématique** : tout score a une explication, tout indicateur a un niveau de fiabilité
- **Maîtrise → Contrôles utilisateur** : pas d'automatismes cachés, chaque action est un choix explicite de Karim
- **Efficacité → Zéro friction** : pas de bouton « Appliquer » sur les filtres, pas de modal inutile, export direct
- **Honnêteté → Mode dégradé explicite** : si le GeoJSON manque → "Carte indisponible, mode tabulaire actif" (pas d'erreur cryptique)
- **Prévisibilité → Cohérence totale** : même code couleur, même structure sidebar, même logique de navigation sur toutes les vues

### Emotional Design Principles

1. **Ne jamais bluffer** — Si le modèle ne sait pas, l'interface le dit. La confiance vient de l'honnêteté, pas de la certitude.
2. **L'utilisateur décide** — L'outil propose, Karim dispose. Chaque automatisme a un override.
3. **Récompenser l'exploration** — Chaque clic apporte une info utile. Pas d'impasse, pas d'écran vide.
4. **Rester prévisible** — Même patterns partout. Apprendre une vue = savoir utiliser toutes les vues.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

| Produit | Pattern clé | Leçon UX |
|---|---|---|
| Streamlit Data Apps | Sidebar filtres + contenu réactif | Convention familière, pas besoin de réinventer |
| Google Maps / Géoportail | Clic entité → panneau contextuel | Le détail vient à l'utilisateur, pas l'inverse |
| Tableau / Power BI | KPI cards → graphiques → table | Hiérarchie visuelle : du macro au micro |
| Excel | Tri libre, filtres, sélection → export | Le tabulaire est l'interface naturelle de Karim |

### Transferable UX Patterns

| Pattern | Application |
|---|---|
| Sidebar filtres globaux | Sidebar permanente Streamlit avec filtres combinés réactifs |
| KPI cards en haut de vue | Résumé contextuel sur chaque vue (nb tronçons filtrés, score moyen, etc.) |
| Clic → bascule détail | Clic tronçon sur carte/tableau → session_state → vue détail |
| Code couleur heatmap | 4 classes (critique/élevé/modéré/faible) cohérentes sur toutes les vues |
| Barres SHAP horizontales | SHAP features en barres colorées + texte métier, pas de valeurs numériques brutes |
| Progressive disclosure | Optimiseur : paramètres simples visibles, "Options avancées" rétractable |
| Export 1 clic | Bouton "Exporter CSV" toujours visible quand un jeu filtré existe |

### Anti-Patterns to Avoid

- ❌ Modal de bienvenue / tutorial → données visibles immédiatement
- ❌ Bouton "Appliquer" sur les filtres → filtres réactifs instantanés
- ❌ Graphiques 3D / animations → graphiques 2D simples et lisibles
- ❌ Jargon ML ("SHAP value", "AUC") → langage métier ("Facteurs de risque", "Fiabilité")
- ❌ Carte seule sans alternative → tableau toujours disponible, carte = bonus
- ❌ Couleurs non accessibles → palette daltonisme-safe + formes complémentaires

### Design Inspiration Strategy

**Adopter :** Convention Streamlit sidebar, KPI cards (Tableau), heatmap couleur, export direct
**Adapter :** Clic carte → bascule vue détail (pas popup), SHAP → barres métier simplifiées, optimiseur en progressive disclosure
**Éviter :** Onboarding modal, jargon ML, sur-design, graphiques 3D

## Design System Foundation

### Design System Choice

**Streamlit natif + thème personnalisé** — Pas de design system externe. Streamlit impose ses propres composants et patterns de mise en page. Le design system est la combinaison du thème Streamlit, de la palette de risque, et des conventions de mise en page.

### Rationale

- Streamlit ne supporte pas de design system CSS externe (Material, Tailwind, etc.)
- Les composants natifs (`st.metric`, `st.dataframe`, `st.plotly_chart`) couvrent 100% des besoins
- L'objectif est un outil métier fonctionnel — la cohérence visuelle vient de la palette et des conventions, pas d'un framework design
- Dev solo → simplicité maximale, pas de couche d'abstraction supplémentaire

### Color Palette

| Usage | Nom | Hex | Contexte |
|---|---|---|---|
| Risque critique | Rouge | `#d32f2f` | Score ≥ seuil critique |
| Risque élevé | Orange | `#ff9800` | Score ≥ seuil élevé |
| Risque modéré | Jaune | `#fdd835` | Score ≥ seuil modéré |
| Risque faible | Vert | `#4caf50` | Score < seuil modéré |
| Primaire app | Bleu | `#1976d2` | Boutons, liens, accents |
| Fond principal | Blanc | `#ffffff` | Background |
| Fond secondaire | Gris clair | `#f5f5f5` | Sidebar, cards |
| Texte | Gris foncé | `#212121` | Corps de texte |

Accessibilité : couleurs de risque avec contraste luminosité suffisant pour daltonisme. Texte de classe (Critique/Élevé/Modéré/Faible) toujours présent en complément.

### Component Library

| Pattern | Composant Streamlit | Usage récurrent |
|---|---|---|
| KPI card | `st.metric(label, value, delta)` | En-tête de chaque vue — contexte rapide |
| Tableau interactif | `st.dataframe()` | Vue tableau, listes, résultats optimiseur |
| Graphique interactif | `st.plotly_chart()` | Distribution, cohorte, Lift, barres SHAP |
| Carte | `st_folium()` | Vue carte interactive |
| Filtre select | `st.sidebar.multiselect()` | Matériau, diamètre |
| Filtre slider | `st.sidebar.slider()` | Score min, âge min, budget |
| Toggle | `st.sidebar.radio()` | Horizon, vue active |
| Séparateur | `st.divider()` | Entre blocs de contenu |
| Message contextuel | `st.info()` / `st.warning()` / `st.error()` | ICP, mode dégradé, erreurs |
| Export | `st.download_button()` | CSV configurable |
| Expansion | `st.expander()` | Options avancées optimiseur |

### Layout Convention

Chaque vue suit la même structure verticale :
1. **KPI cards** (via `st.columns` + `st.metric`) — résumé contextuel en haut
2. **Contenu principal** — carte, tableau, graphiques, ou résultats optimiseur
3. **Détails / actions** — export, options avancées, informations secondaires

## Defining Experience

### Core Interaction

"Je vois mon réseau coloré, je clique un tronçon, je comprends pourquoi il est à risque."

C'est l'interaction qui résume le produit. Le tableau/carte coloré accroche l'attention, le clic déclenche le détail, le SHAP en langage métier construit la confiance.

### User Mental Model

**Aujourd'hui :** Excel + mémoire terrain. Tri par âge ou nb casses. Pas de scoring prédictif, pas de combinaison de features.

**Attendu :** Un "Excel amélioré" avec une carte. Retrouver ses tronçons familiers. Comprendre la logique derrière chaque score.

**Risques de confusion :**
- Score de risque → clarifier : "% de probabilité de fuite sur l'horizon sélectionné"
- Horizon 1/3/5 ans → clarifier : "Risque de fuite dans les X prochaines années"
- SHAP → ne jamais utiliser le mot "SHAP" dans l'interface → "Facteurs de risque"

### Success Criteria

1. Karim identifie un tronçon à risque qu'il ne connaissait pas en < 5 min
2. Karim comprend POURQUOI ce tronçon est à risque sans formation
3. Karim exporte une liste et l'envoie au terrain en < 2 min
4. Karim revient utiliser l'outil de lui-même la semaine suivante

### Experience Mechanics

**Initiation (< 5s) :** App s'ouvre → tableau trié par score, lignes colorées. Ou carte colorée si GeoJSON. Pas de setup.

**Interaction — Clic tronçon :**
- Depuis tableau : clic ligne → bascule vue Détail
- Depuis carte : clic tronçon → popup résumé + bouton "Voir détail" → bascule vue Détail

**Feedback — Vue Détail :**
1. KPI cards : score, âge, matériau, classe risque, ICP
2. Caractéristiques patrimoniales (tableau simple)
3. Scores par horizon (1/3/5 ans) avec code couleur
4. "Facteurs de risque" : barres horizontales en langage métier (Longueur +fort, Âge +fort, etc.)
5. Historique fuites (nombre, dates)
6. Indicateur ICP : ✅ Données fiables / ⚠️ Données incomplètes

**Traduction SHAP → métier :**
- Pas de "SHAP value = 1.45"
- Barres horizontales colorées (rouge = augmente le risque, bleu = diminue)
- Texte : "Longueur (142 m) — augmente fortement le risque"

**Continuation :** Retour au tableau avec mêmes filtres, ou switch vers optimiseur pour forcer/exclure le tronçon.

### UX Pattern Classification

| Pattern | Type | Source |
|---|---|---|
| Tableau trié par score | Établi | Excel — modèle mental familier |
| Carte heatmap | Établi | Cartographie standard |
| Master-detail (clic → détail) | Établi | Pattern universel |
| SHAP barres métier | Adapté | Force plot → barres + texte métier |
| ICP ✅/⚠️ | Nouveau | Honnêteté proactive sur les données |
| Progressive disclosure optimiseur | Établi | Mode simple/avancé |

## Visual Design Foundation

### Color System

**Palette risque (sémantique métier) :**

| Classe | Hex | Usage | Seuil |
|---|---|---|---|
| Critique | `#d32f2f` | Tronçons à risque maximal | score ≥ 0.8 |
| Élevé | `#ff9800` | Risque significatif | score ≥ 0.6 |
| Modéré | `#fdd835` | Risque modéré | score ≥ 0.3 |
| Faible | `#4caf50` | Risque faible | score < 0.3 |

**Palette application :**

| Rôle | Hex | Usage |
|---|---|---|
| Primaire | `#1976d2` | Boutons, liens, accents, titre |
| Fond principal | `#ffffff` | Zone de contenu |
| Fond secondaire | `#f5f5f5` | Sidebar, cards info |
| Texte principal | `#212121` | Corps de texte |
| SHAP positif | `#d32f2f` | Feature qui augmente le risque |
| SHAP négatif | `#1976d2` | Feature qui diminue le risque |

### Typography System

**Imposé par Streamlit :** Source Sans Pro (système)

| Niveau | Composant Streamlit | Usage |
|---|---|---|
| H1 | `st.title()` | Titre de l'application (1 seul) |
| H2 | `st.header()` | Titre de vue (Tableau, Carte, Dashboard...) |
| H3 | `st.subheader()` | Sous-sections dans une vue |
| Body | `st.write()` / `st.markdown()` | Texte courant, descriptions |
| Metric | `st.metric()` | KPI cards en en-tête |
| Caption | `st.caption()` | Notes, sources, avertissements |

### Spacing & Layout Foundation

**Layout global :** Sidebar (filtres + navigation) à gauche, contenu principal à droite. Convention Streamlit standard.

**Structure de chaque vue :**
1. KPI cards via `st.columns()` + `st.metric()` — résumé en haut
2. Contenu principal (tableau, carte, graphiques) — au milieu
3. Actions / détails secondaires — en bas

**Sidebar layout :**
1. Navigation (radio buttons) — en haut
2. Séparateur
3. Filtres (multiselect, sliders) — au milieu
4. Séparateur
5. Résumé filtrage ("X tronçons filtrés sur Y") — en bas

### Accessibility Considerations

- Contraste texte/fond : ratio 15.4:1 (`#212121` sur `#ffffff`) — WCAG AAA
- Couleurs de risque : contraste luminosité suffisant pour daltonisme red-green
- Texte label TOUJOURS présent avec la couleur : "CRITIQUE 🔴", "ÉLEVÉ 🟠", etc.
- Pas de couleur seule comme vecteur d'information — toujours texte + couleur
- Taille police Streamlit par défaut : lisible sans ajustement

## Design Direction Decision

### Direction choisie : Streamlit natif — Densité informative, navigation sidebar

**Principe :** Interface utilisateur dense mais lisible, exploitant 100% des composants natifs Streamlit. Navigation par sidebar radio, filtres globaux persistants, code couleur risque omniprésent. Aucun CSS custom, aucun composant externe sauf Folium et Plotly.

### Wireframes des 5 vues

#### Vue Tableau (vue par défaut)

```
┌─────────────────────────────────────────────────────────────────┐
│ SIDEBAR                │  📊 Vue Tableau                        │
│                        │                                        │
│ ○ Tableau ← actif      │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│ ○ Carte                │  │ 1247 │ │ 23%  │ │ 0.42 │ │ 85%  │ │
│ ○ Détail               │  │tronç.│ │crit. │ │moy.  │ │ICP OK│ │
│ ○ Dashboard            │  └──────┘ └──────┘ └──────┘ └──────┘ │
│ ○ Optimiseur           │                                        │
│                        │  ┌────────────────────────────────────┐│
│ ──────────────         │  │ OBJET  MAT   AGE  SCORE  CLASSE  ││
│ Horizon:               │  │ TR-001 Fonte  62  0.91   🔴 CRIT ││
│ ○ 1 an ○ 3 ans ○ 5 ans│  │ TR-042 PVC    35  0.78   🟠 ÉLEV ││
│                        │  │ TR-103 PEHD   18  0.45   🟡 MOD  ││
│ Matériau: [▼ multi]    │  │ TR-205 Fonte  28  0.22   🟢 FAIB ││
│ Score min: [===○===]   │  │ ...                               ││
│ Âge min:   [===○===]   │  └────────────────────────────────────┘│
│                        │                                        │
│ ──────────────         │  [⬇ Exporter CSV]                     │
│ 847 / 1247 tronçons    │                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Interactions clés :**
- Clic sur une ligne → `session_state.troncon_selectionne` → bascule automatique vers vue Détail
- Tri natif par colonne (score par défaut DESC)
- Filtres sidebar = mise à jour instantanée du tableau
- KPI cards reflètent le jeu filtré

#### Vue Carte

```
┌─────────────────────────────────────────────────────────────────┐
│ SIDEBAR                │  🗺️ Vue Carte                          │
│                        │                                        │
│ ○ Tableau              │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│ ○ Carte ← actif        │  │ 1247 │ │ 23%  │ │ 0.42 │ │ 85%  │ │
│ ○ Détail               │  │tronç.│ │crit. │ │moy.  │ │ICP OK│ │
│ ○ Dashboard            │  └──────┘ └──────┘ └──────┘ └──────┘ │
│ ○ Optimiseur           │                                        │
│                        │  ┌────────────────────────────────────┐│
│ ──────────────         │  │                                    ││
│ Horizon:               │  │    ═══🔴═══                        ││
│ ○ 1 an ○ 3 ans ○ 5 ans│  │   /         \   ══🟢══            ││
│                        │  │  ══🟠══     ══🟡══                 ││
│ Matériau: [▼ multi]    │  │        \   /                       ││
│ Score min: [===○===]   │  │    [Popup: TR-001                  ││
│ Âge min:   [===○===]   │  │     Score: 0.91 🔴                ││
│                        │  │     Fonte, 62 ans                  ││
│ ──────────────         │  │     [Voir détail →]]               ││
│ 847 / 1247 tronçons    │  └────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Interactions clés :**
- Tronçons colorés par classe de risque (même palette que tableau)
- Clic tronçon → popup Folium (résumé : score, matériau, âge, classe)
- Bouton "Voir détail →" dans le popup → bascule vue Détail
- Si GeoJSON absent → message `st.warning("Fichier GeoJSON non trouvé. Mode tabulaire uniquement.")`

#### Vue Détail (tronçon sélectionné)

```
┌─────────────────────────────────────────────────────────────────┐
│ SIDEBAR                │  🔍 Détail — TR-001                    │
│                        │                                        │
│ ○ Tableau              │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│ ○ Carte                │  │ 0.91 │ │ 62   │ │Fonte │ │✅ ICP │ │
│ ○ Détail ← actif       │  │score │ │ ans  │ │grise │ │fiable│ │
│ ○ Dashboard            │  └──────┘ └──────┘ └──────┘ └──────┘ │
│ ○ Optimiseur           │                                        │
│                        │  Caractéristiques patrimoniales        │
│ [← Retour tableau]     │  ┌────────────────────────────────────┐│
│                        │  │ Longueur: 142 m  │ Diamètre: 100mm││
│                        │  │ Pose: 1962       │ Fuites: 4       ││
│                        │  └────────────────────────────────────┘│
│                        │                                        │
│                        │  Scores par horizon                    │
│                        │  ┌────────────────────────────────────┐│
│                        │  │ 1 an: 0.85 🟠  3 ans: 0.91 🔴    ││
│                        │  │ 5 ans: 0.96 🔴                    ││
│                        │  └────────────────────────────────────┘│
│                        │                                        │
│                        │  Facteurs de risque                    │
│                        │  ┌────────────────────────────────────┐│
│                        │  │ Longueur (142m)  ████████░ +fort   ││
│                        │  │ Âge (62 ans)     ███████░░ +fort   ││
│                        │  │ Nb fuites (4)    █████░░░░ +moyen  ││
│                        │  │ Diamètre (100)   ██░░░░░░░ +faible││
│                        │  │ Matériau (Fonte) ████░░░░░ +moyen  ││
│                        │  └────────────────────────────────────┘│
│                        │  ⬆ augmente risque  ⬇ diminue risque  │
└─────────────────────────────────────────────────────────────────┘
```

**Interactions clés :**
- Barres SHAP en langage métier (jamais le mot "SHAP")
- Couleurs barres : rouge = augmente risque, bleu = diminue risque
- ICP : ✅ Données fiables ou ⚠️ Données incomplètes (avec détail au hover)
- Bouton "← Retour tableau" pour revenir avec filtres préservés
- Pas de navigation vers tronçon suivant pour le MVP

#### Vue Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│ SIDEBAR                │  📈 Dashboard                          │
│                        │                                        │
│ ○ Tableau              │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│ ○ Carte                │  │ 1247 │ │ 38   │ │ 4.2  │ │ 23%  │ │
│ ○ Détail               │  │tronç.│ │âge ⌀ │ │c/km/a│ │crit. │ │
│ ○ Dashboard ← actif    │  └──────┘ └──────┘ └──────┘ └──────┘ │
│ ○ Optimiseur           │                                        │
│                        │  ┌─────────────────┐┌────────────────┐│
│ ──────────────         │  │  Distribution    ││ Top 10         ││
│ Horizon:               │  │  risques         ││ tronçons       ││
│ ○ 1 an ○ 3 ans ○ 5 ans│  │  ██              ││ 1. TR-001 0.96 ││
│                        │  │  ██ ██           ││ 2. TR-042 0.91 ││
│ Matériau: [▼ multi]    │  │  ██ ██ ██        ││ 3. TR-103 0.89 ││
│                        │  │  ██ ██ ██ ██     ││ ...            ││
│                        │  │  C  É  M  F     ││                ││
│                        │  └─────────────────┘└────────────────┘│
│                        │                                        │
│                        │  ┌─────────────────┐┌────────────────┐│
│                        │  │ Vue Cohorte      ││ Courbe Lift    ││
│                        │  │ Matériau×Décennie││                ││
│                        │  │ Fonte 60s ████   ││     ╱──────   ││
│                        │  │ Fonte 70s ███    ││   ╱            ││
│                        │  │ PVC  80s  ██     ││  ╱             ││
│                        │  │ PEHD 90s  █      ││ ╱              ││
│                        │  └─────────────────┘└────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Interactions clés :**
- Filtres sidebar s'appliquent aussi au dashboard (cohérence globale)
- Distribution risques : histogramme Plotly avec 4 classes colorées
- Vue cohorte : heatmap matériau × décennie de pose → score moyen
- Courbe Lift : cumul % fuites vs % réseau priorisé
- Top 10 cliquable → bascule vue Détail

#### Vue Optimiseur

```
┌─────────────────────────────────────────────────────────────────┐
│ SIDEBAR                │  🎯 Optimiseur de Renouvellement       │
│                        │                                        │
│ ○ Tableau              │  Paramètres                            │
│ ○ Carte                │  ┌────────────────────────────────────┐│
│ ○ Détail               │  │ Budget max (€): [1 500 000    ]   ││
│ ○ Dashboard            │  │ Horizon:  ○ 1 an  ● 3 ans  ○ 5 ans│
│ ○ Optimiseur ← actif   │  │                                    ││
│                        │  │ ▶ Options avancées                 ││
│ (filtres masqués       │  │   Forçages: [TR-001, TR-042]       ││
│  sur cette vue)        │  │   Exclusions: [TR-205]             ││
│                        │  │   What-if matériau: Fonte → PEHD   ││
│                        │  └────────────────────────────────────┘│
│                        │  [🚀 Lancer l'optimisation]            │
│                        │                                        │
│                        │  Résultats                             │
│                        │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│                        │  │ 847k€│ │ 3.2km│ │ -12  │ │ 2.1x │ │
│                        │  │budget│ │renouv│ │fuites│ │ROI   │ │
│                        │  └──────┘ └──────┘ └──────┘ └──────┘ │
│                        │                                        │
│                        │  ┌────────────────────────────────────┐│
│                        │  │ OBJET  SCORE  COÛT    PRIORITÉ    ││
│                        │  │ TR-001 0.91   125k€   1 ⭐        ││
│                        │  │ TR-042 0.78   98k€    2           ││
│                        │  │ TR-103 0.45   67k€    3           ││
│                        │  └────────────────────────────────────┘│
│                        │  [⬇ Exporter plan renouvellement CSV] │
└─────────────────────────────────────────────────────────────────┘
```

**Interactions clés :**
- Progressive disclosure : "Options avancées" dans `st.expander()`
- Forçages : tronçons à inclure obligatoirement dans le plan
- Exclusions : tronçons à exclure
- What-if matériau : simuler l'impact d'un changement de matériau
- OR-Tools CP-SAT résout en arrière-plan → spinner → résultats
- KPI résultats : budget utilisé, km renouvelés, fuites évitées, ROI
- Tableau résultat cliquable → vue Détail
- Export CSV du plan de renouvellement

### Justification de la direction

| Critère | Décision |
|---|---|
| Framework | 100% composants natifs Streamlit — zéro CSS custom |
| Navigation | Sidebar radio — simple, prévisible, compatible session_state |
| Filtres | Sidebar permanente, réactifs, communs à 4 vues (masqués sur optimiseur) |
| Layout | Structure verticale constante : KPI cards → contenu → actions |
| Progressive disclosure | `st.expander()` pour options avancées optimiseur |
| Cohérence | Même palette couleur, même structure, même patterns d'interaction |
| Mode dégradé | `st.warning()` / `st.info()` pour signaler limites gracieusement |

### Notes d'implémentation

- Chaque vue = 1 fichier Python dans `views/` (sauf optimiseur dans `optimizer.py` racine)
- `st.session_state` gère : vue active, tronçon sélectionné, filtres, horizon, résultats optimiseur
- Navigation clic tronçon : `st.session_state.troncon_selectionne = id` + `st.session_state.vue = "detail"` + `st.rerun()`
- Filtres : fonctions partagées dans `filters.py`, appliquées dans `main.py` avant dispatch vers la vue
- Export : `export.py` reçoit le DataFrame filtré + config colonnes

## User Journey Flows

### Parcours 1 : Découverte — "C'est quoi ce tronçon rouge ?"

**Entrée :** Karim ouvre l'app pour la première fois.

**Flux :**
1. App s'ouvre → GeoJSON détecté ? → Vue Carte (sinon Vue Tableau + `st.info` carte indisponible)
2. Carte/tableau coloré par score de risque — visible en < 5s
3. Karim zoome sur son secteur (carte) ou trie par score DESC (tableau)
4. Remarque un tronçon rouge inattendu → clic
5. → Bascule automatique Vue Détail (`session_state.vue = "detail"`)
6. Lit KPI cards : score, âge, matériau, classe risque, ICP ✅
7. Lit "Facteurs de risque" : barres horizontales en langage métier
8. Reconnaît le profil typique de tronçon à risque → moment confiance
9. ← Retour tableau (filtres préservés) ou continue l'exploration

**Points de feedback :**
- Chargement < 5s → carte/tableau visible immédiatement
- Code couleur immédiat → compréhension visuelle sans lire de nombre
- Barres facteurs de risque + texte métier → "Longueur (142m) — augmente fortement le risque"
- ICP ✅/⚠️ → honnêteté sur la fiabilité

**Gestion d'erreur :** Si ICP ⚠️ → Karim comprend que le modèle manque de données, calibre sa confiance.

### Parcours 2 : Campagne terrain — Préparer une liste de fuites

**Entrée :** Karim doit planifier les tournées de recherche de fuites du trimestre.

**Flux :**
1. Vue Tableau (défaut)
2. Sidebar : sélectionne Horizon = 3 ans
3. Sidebar : filtre Matériau = Fonte, PVC
4. Sidebar : slider Score min = 0.6
5. Tableau se met à jour instantanément (filtres réactifs)
6. KPI cards : "84 tronçons filtrés, 67% critiques"
7. Vérifie quelques tronçons connus — ça colle
8. Clic ⬇ Exporter CSV
9. CSV téléchargé : OBJET, adresse, score, matériau, âge, facteurs principaux
10. Envoie au chef d'exploitation → Campagne préparée en < 5 min

**Gestion d'erreur :** Aucun tronçon après filtrage → `st.info("Aucun tronçon ne correspond aux filtres.")` + KPI "0 tronçons" + compteur sidebar.

### Parcours 3 : Argumentaire budget — Chiffres pour le directeur

**Entrée :** Cycle budgétaire septembre. Le directeur demande un argumentaire renouvellement.

**Flux :**
1. Vue Dashboard
2. Lit KPI cards : nb tronçons, âge moyen, taux casse linéaire
3. Distribution risques : 23% critique, 31% élevé (histogramme Plotly)
4. Vue Cohorte : heatmap matériau × décennie → Fonte 1960s = zone rouge
5. Courbe Lift : top 10% réseau = 45% des fuites
6. Bascule → Vue Optimiseur
7. Saisit budget max : 1 500 000 €, Horizon : 3 ans
8. 🚀 Lance l'optimisation → spinner → résultats en < 5s
9. KPI résultats : 847k€ budget utilisé, 3.2 km renouvelés, -12 fuites évitées, ROI 2.1x
10. Tableau priorisé : tronçons à renouveler par ordre de priorité
11. ⬇ Exporter plan renouvellement CSV
12. Chiffres précis pour le directeur / élus → Argumentaire en < 10 min

**Points de décision :**
- Options avancées (expander) : forçages, exclusions, what-if matériau
- Budget insuffisant → résultats partiels + KPI "budget utilisé à 100%"
- Clic tronçon dans résultat → vue Détail pour approfondir

### Parcours 4 : Récupération erreur — Le modèle se trompe

**Entrée :** Un tronçon vert a cassé sur le terrain. Karim veut comprendre.

**Flux :**
1. Vue Tableau → cherche le tronçon par identifiant
2. Trouve le tronçon — score faible, classe Vert
3. Clic → Vue Détail
4. Lit les caractéristiques patrimoniales
5. Vérifie ICP du tronçon :
   - ⚠️ Données incomplètes → date de pose manquante, matériau "Autre" → le modèle n'avait pas assez de signal
   - ✅ Données fiables → cas hors modèle (travaux tiers, surpression ponctuelle)
6. Karim calibre sa confiance : modèle fiable pour tendances, expertise terrain pour cas hors modèle
7. Confiance renforcée par l'honnêteté de l'outil

**Points de feedback :**
- ICP ⚠️ clairement visible → pas de surprise
- Facteurs de risque montrent les features manquant de données
- Pas de fausse certitude → le modèle ne bluff pas

### Patterns de navigation communs

| Pattern | Implémentation |
|---|---|
| Clic tronçon → Détail | `session_state.troncon = id` + `session_state.vue = "detail"` + `st.rerun()` |
| Retour avec filtres | `session_state` préserve tous les filtres, bouton "← Retour" change juste la vue |
| Switch vue | Sidebar radio → change `session_state.vue`, filtres persistent |
| Feedback filtre | Compteur "X / Y tronçons" en bas sidebar, KPI cards reflètent le jeu filtré |
| Mode dégradé | GeoJSON absent → `st.warning()`, carte masquée, tableau par défaut |

### Principes d'optimisation des flux

1. **Aucun dead-end** — Chaque vue a une action suivante naturelle (clic, export, retour)
2. **Feedback instantané** — Filtres réactifs, KPI cards dynamiques, 0 bouton "Appliquer"
3. **Contexte préservé** — Filtres + sélection persistent dans `session_state` entre les vues
4. **Erreur = information** — ICP ⚠️, `st.warning()`, compteur "0 tronçons" — toujours explicite
5. **2 min max par parcours** — Découverte < 5 min, Campagne < 5 min, Budget < 10 min

## Component Strategy

### Composants Streamlit natifs (couverture existante)

| Composant | Usage dans l'app | Couverture |
|---|---|---|
| `st.metric()` | KPI cards en-tête de chaque vue | ✅ Natif |
| `st.dataframe()` | Vue Tableau, listes résultats optimiseur | ✅ Natif |
| `st.plotly_chart()` | Distribution, cohorte, Lift, barres facteurs de risque | ✅ Natif |
| `st_folium()` | Vue Carte interactive | ✅ Via streamlit-folium |
| `st.sidebar.radio()` | Navigation entre vues | ✅ Natif |
| `st.sidebar.multiselect()` | Filtres matériau, diamètre | ✅ Natif |
| `st.sidebar.slider()` | Score min, âge min, budget | ✅ Natif |
| `st.download_button()` | Export CSV | ✅ Natif |
| `st.expander()` | Options avancées optimiseur | ✅ Natif |
| `st.columns()` | Layout KPI cards, grilles | ✅ Natif |
| `st.info()` / `st.warning()` / `st.error()` | Messages contextuels, mode dégradé | ✅ Natif |
| `st.spinner()` | Chargement optimisation | ✅ Natif |
| `st.caption()` | Notes, sources, avertissements | ✅ Natif |
| `st.divider()` | Séparateurs visuels | ✅ Natif |

**Résultat : 100% de couverture fonctionnelle** — aucun composant custom CSS requis.

### Composants composites (assemblages natifs)

#### 1. Barre Facteurs de risque (SHAP métier)

**Objectif :** Afficher les 5 features SHAP en langage métier sans jargon ML.

**Assemblage :**
- `st.subheader("Facteurs de risque")`
- Pour chaque feature : `st.markdown()` pour le label + `st.plotly_chart()` barre horizontale
- Couleur : rouge (`#d32f2f`) = augmente risque, bleu (`#1976d2`) = diminue risque
- Texte : "Longueur (142 m) — augmente fortement le risque"

**États :**
- Normal : 5 barres + texte
- Données manquantes : barre grisée + "Donnée non disponible"

#### 2. Indicateur ICP (confiance données)

**Objectif :** Signaler la fiabilité des données par tronçon.

**Assemblage :**
- ICP bon : `st.success("✅ Données fiables")`
- ICP faible : `st.warning("⚠️ Données incomplètes — [détail manquant]")`

**États :**
- ✅ Fiable (ICP ≥ seuil) — vert
- ⚠️ Incomplètes (ICP < seuil) — orange avec détail

#### 3. Carte risque tronçon (résumé coloré)

**Objectif :** Résumé visuel d'un tronçon — utilisé dans la vue Détail header.

**Assemblage :**
- `st.columns(4)` + `st.metric()` pour : Score, Âge, Matériau, Classe risque
- Couleur de la classe via `st.markdown()` avec emoji coloré (🔴🟠🟡🟢)

#### 4. Résultats optimiseur (KPI + tableau)

**Objectif :** Afficher les résultats OR-Tools de manière lisible.

**Assemblage :**
- `st.columns(4)` + `st.metric()` : budget utilisé, km renouvelés, fuites évitées, ROI
- `st.dataframe()` : tableau priorisé (tronçons sélectionnés par l'optimiseur)
- `st.download_button()` : export plan CSV

**États :**
- En attente : formulaire paramètres visible, pas de résultats
- Calcul : `st.spinner("Optimisation en cours...")`
- Résultat : KPI + tableau + export
- Erreur : `st.error("Impossible d'optimiser avec ces contraintes")`

#### 5. Compteur filtrage sidebar

**Objectif :** Feedback permanent sur l'impact des filtres.

**Assemblage :**
- `st.sidebar.caption(f"{n_filtré} / {n_total} tronçons")`
- Se met à jour à chaque changement de filtre

### Stratégie d'implémentation composants

| Priorité | Composant | Raison |
|---|---|---|
| P0 — Core | KPI cards (`st.metric` × 4 cols) | Utilisé sur TOUTES les vues |
| P0 — Core | Navigation sidebar (`st.radio`) | Structure de l'app entière |
| P0 — Core | Filtres sidebar (multiselect + slider) | 4 vues sur 5 en dépendent |
| P0 — Core | Tableau interactif (`st.dataframe`) | Vue par défaut |
| P1 — Critique | Barres facteurs de risque | Cœur de la confiance — parcours 1 |
| P1 — Critique | Indicateur ICP | Honnêteté — parcours 4 |
| P1 — Critique | Carte Folium (`st_folium`) | Vue Carte — parcours 1 |
| P2 — Important | Graphiques Dashboard (Plotly) | Distribution, cohorte, Lift — parcours 3 |
| P2 — Important | Résultats optimiseur | Parcours 3 — argumentaire budget |
| P3 — Support | Export CSV / plan renouvellement | Parcours 2, 3 — Actions de sortie |
| P3 — Support | Compteur filtrage | Feedback — toutes vues |

### Feuille de route implémentation

**Phase 1 — Squelette fonctionnel :**
- `main.py` : navigation sidebar, session_state, dispatch vues
- `data_loader.py` : chargement CSV, cache, validation
- `filters.py` : filtres globaux
- Vue Tableau : KPI cards + `st.dataframe` + export

**Phase 2 — Vues enrichies :**
- Vue Détail : KPI tronçon + caractéristiques + barres facteurs de risque + ICP
- Vue Carte : Folium + popup + mode dégradé
- Vue Dashboard : distribution + cohorte + Lift

**Phase 3 — Optimiseur :**
- Vue Optimiseur : formulaire + OR-Tools + résultats + export plan

## UX Consistency Patterns

### Hiérarchie d'actions

| Type | Composant Streamlit | Usage | Exemple |
|---|---|---|---|
| **Action primaire** | `st.button()` (pleine largeur) | Action principale de la vue | "🚀 Lancer l'optimisation" |
| **Action secondaire** | `st.download_button()` | Export, action de sortie | "⬇ Exporter CSV" |
| **Navigation** | `st.sidebar.radio()` | Switch entre vues | Tableau / Carte / Détail / Dashboard / Optimiseur |
| **Lien contextuel** | Session_state + `st.rerun()` | Clic tronçon → Détail | Clic ligne tableau ou popup carte |
| **Retour** | `st.button("← Retour")` | Revenir à la vue précédente | "← Retour tableau" sur vue Détail |

**Règle :** Maximum 1 action primaire par vue. Les exports sont toujours secondaires.

### Patterns de feedback

| Situation | Composant | Message type | Couleur |
|---|---|---|---|
| **Succès / données fiables** | `st.success()` | "✅ Données fiables" | Vert |
| **Avertissement / limite** | `st.warning()` | "⚠️ Données incomplètes — date de pose manquante" | Orange |
| **Erreur bloquante** | `st.error()` | "Impossible d'optimiser avec ces contraintes" | Rouge |
| **Information contexte** | `st.info()` | "Carte indisponible — fichier GeoJSON non trouvé" | Bleu |
| **Compteur filtrage** | `st.sidebar.caption()` | "847 / 1247 tronçons" | Gris |
| **Chargement** | `st.spinner()` | "Optimisation en cours..." | — |
| **État vide** | `st.info()` | "Aucun tronçon ne correspond aux filtres. Élargissez les critères." | Bleu |

**Règle :** Jamais de message technique (stack trace, code erreur). Toujours en langage métier.

### Patterns de formulaire (Optimiseur)

| Pattern | Implémentation | Comportement |
|---|---|---|
| **Champ numérique** | `st.number_input()` | Validation min/max, pas de saisie libre |
| **Sélection horizon** | `st.radio()` horizontal | 1 an / 3 ans / 5 ans — même pattern que sidebar |
| **Liste tronçons (forçages)** | `st.multiselect()` | Recherche par identifiant tronçon |
| **Options avancées** | `st.expander("▶ Options avancées")` | Masqué par défaut, ouvert au clic |
| **Soumission** | `st.button("🚀 Lancer l'optimisation")` | Spinner → résultats dans la même page |

**Règle :** Pas de formulaire multi-page. Tout sur une seule vue, progressive disclosure via `st.expander()`.

### Patterns de navigation

| Pattern | Déclencheur | Implémentation |
|---|---|---|
| **Switch vue** | Sidebar radio | `session_state.vue = "tableau"` → contenu se met à jour |
| **Clic tronçon → Détail** | Clic ligne tableau ou popup carte | `session_state.troncon = id` + `session_state.vue = "detail"` + `st.rerun()` |
| **Retour** | Bouton "← Retour" | `session_state.vue = session_state.vue_precedente` + `st.rerun()` |
| **Filtres globaux** | Sidebar multiselect/slider | Pas de bouton "Appliquer" — filtres réactifs instantanés |
| **Horizon** | Sidebar radio | Change les scores affichés (H1/H3/H5), tout se met à jour |

**Règle :** Les filtres et l'horizon persistent entre toutes les vues sauf l'optimiseur (qui a ses propres paramètres).

### Pattern états vides et chargement

| État | Composant | Message |
|---|---|---|
| **Aucun tronçon filtré** | `st.info()` + KPI "0" | "Aucun tronçon ne correspond aux filtres. Essayez d'élargir les critères." |
| **GeoJSON absent** | `st.warning()` + masquer carte | "Fichier GeoJSON non trouvé. Mode tabulaire uniquement." |
| **Fichier CSV manquant** | `st.error()` + stop | "Fichier de scoring introuvable. Vérifiez le chemin dans config.yaml." |
| **Tronçon non sélectionné** | `st.info()` sur vue Détail | "Sélectionnez un tronçon depuis le tableau ou la carte." |
| **Optimiseur pas encore lancé** | Formulaire seul | Pas de section résultats affichée |
| **Chargement données** | `st.spinner()` | "Chargement des données..." |

### Pattern code couleur (cohérence totale)

| Classe risque | Hex | Emoji | Label | Seuil |
|---|---|---|---|---|
| Critique | `#d32f2f` | 🔴 | CRITIQUE | score ≥ 0.8 |
| Élevé | `#ff9800` | 🟠 | ÉLEVÉ | score ≥ 0.6 |
| Modéré | `#fdd835` | 🟡 | MODÉRÉ | score ≥ 0.3 |
| Faible | `#4caf50` | 🟢 | FAIBLE | score < 0.3 |

**Règle :** Ce mapping est utilisé PARTOUT — tableau, carte, détail, dashboard, optimiseur. Défini 1 seule fois dans `config.yaml`, lu par tous les modules.

### Règles de cohérence globales

1. **Structure verticale identique** — KPI cards → contenu principal → actions/export (toutes les vues)
2. **Sidebar identique** — Navigation + filtres + compteur (masqué seulement pour optimiseur)
3. **Même police, même espacement** — Streamlit natif = cohérence automatique
4. **Même vocabulaire** — "Facteurs de risque" (pas SHAP), "Classe de risque" (pas "catégorie"), "Tronçon" (pas "segment")
5. **Pas de modal** — Tout est inline. Pas de popup sauf le popup Folium carte (natif)
6. **Pas de pagination** — Scroll natif Streamlit. Filtres = moyen de réduire le volume
7. **Export toujours visible** — Si un jeu filtré existe, le bouton export est présent

## Responsive Design & Accessibility

### Stratégie responsive

**Plateforme cible unique : Desktop (PC fixe bureau)**

| Critère | Décision |
|---|---|
| Appareils | PC fixe Windows 10+, écran ≥ 1280×720 |
| Navigateurs | Chrome / Edge (Chromium) — seuls navigateurs testés |
| Input | Souris + clavier uniquement |
| Mobile / tablette | Hors scope MVP — usage bureau exclusif |
| Orientation | Paysage uniquement (écran fixe) |

### Stratégie breakpoints

| Breakpoint | Largeur | Comportement Streamlit |
|---|---|---|
| Desktop standard | ≥ 1280px | Layout optimal — sidebar visible, 4 colonnes KPI, carte/tableau pleine largeur |
| Desktop étroit | 1024–1279px | Sidebar repliable, colonnes s'adaptent automatiquement |
| Minimum supporté | < 1024px | `st.warning("Résolution minimale recommandée : 1280×720")` — pas de blocage |

**Note :** Mode wide activé dans `.streamlit/config.toml` pour maximiser la zone de contenu.

### Stratégie accessibilité

**Niveau cible : WCAG 2.1 AA**

| Critère WCAG | Implémentation | Statut |
|---|---|---|
| 1.1 Alternatives texte | Emoji couleur TOUJOURS accompagné de texte (🔴 CRITIQUE) | ✅ By design |
| 1.3 Adaptable | Structure sémantique Streamlit (H1/H2/H3 natifs) | ✅ Natif |
| 1.4.1 Utilisation couleur | Couleur jamais seule — toujours texte label + couleur | ✅ By design |
| 1.4.3 Contraste | Texte `#212121` sur `#ffffff` = ratio 15.4:1 (AAA) | ✅ Vérifié |
| 1.4.11 Contraste non-texte | Barres Plotly colorées + labels textuels | ✅ By design |
| 2.1 Clavier | Navigation Streamlit native au clavier (Tab, Enter) | ✅ Natif |
| 2.4 Navigable | Titres H1/H2/H3 structurés, sidebar = navigation | ✅ Natif |
| 3.1 Lisible | Langage métier, pas de jargon ML, vocabulaire constant | ✅ By design |
| 3.3 Aide saisie | Erreurs en langage clair, pas de stack trace | ✅ UX Pattern |
| 4.1 Compatible | HTML sémantique généré par Streamlit | ✅ Natif |

### Daltonisme — stratégie spécifique

| Type daltonisme | Problème potentiel | Solution |
|---|---|---|
| Protanopie (rouge) | Rouge/vert confondus | Label texte TOUJOURS présent : "CRITIQUE", "FAIBLE" |
| Deutéranopie (vert) | Rouge/vert confondus | Même solution — label texte obligatoire |
| Tritanopie (bleu) | Bleu/jaune confondus | Pas d'impact — bleu utilisé pour app, pas pour risque |

**Règle fondamentale :** La couleur est un renforcement visuel, jamais le seul vecteur d'information.

### Stratégie de test

**Tests accessibilité :**
- Contraste : Lighthouse audit Chrome DevTools
- Clavier : navigation Tab complète dans chaque vue
- Daltonisme : Chrome DevTools → Rendering → Emulate vision deficiency
- Lecteur d'écran : test basique avec NVDA

**Tests responsive :**
- Résolution 1280×720 (minimum) et 1920×1080 (standard)
- Chrome et Edge uniquement

### Directives d'implémentation

1. **`.streamlit/config.toml`** — `layout = "wide"` pour maximiser la zone de contenu
2. **Pas de CSS custom** — Streamlit natif gère l'accessibilité HTML automatiquement
3. **Labels texte systématiques** — Chaque `st.metric()`, chaque ligne de tableau, chaque barre graphique a un texte lisible
4. **`alt` text sur les graphiques Plotly** — `fig.update_layout(title="Distribution des classes de risque")`
5. **Messages d'erreur explicites** — Langage métier, action corrective suggérée
