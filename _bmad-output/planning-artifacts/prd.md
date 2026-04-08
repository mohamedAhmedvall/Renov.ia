---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - '_bmad-output/brainstorming/brainstorming-session-2026-04-01-001.md'
  - 'project-distillate/_index.md'
  - 'project-distillate/01-dataset-data-quality.md'
  - 'project-distillate/02-feature-engineering.md'
  - 'project-distillate/03-model-results-validation.md'
  - 'project-distillate/04-v8-roadmap.md'
  - 'V8/data_cleaning.py'
  - 'V8/model.py'
  - 'V8/analyse_resultats.py'
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 1
  projectDocs: 9
workflowType: 'prd'
classification:
  projectType: 'web_app'
  domain: 'utilities_asset_management'
  complexity: 'high'
  projectContext: 'brownfield'
  productName: 'Plateforme de Gestion Patrimoniale Réseau Eau'
  mvpStack: 'Streamlit'
  clientInitial: 'V2S'
  architecture: 'modulaire_multi_collectivites'
  trajectory:
    - 'Phase 1: Ciblage fuites (V8) — carte risques, priorisation terrain'
    - 'Phase 2: Optimiseur renouvellement (V7+V8) — plan 3 ans sous contraintes'
    - 'Phase 3: Plateforme KPIs patrimoine — dashboard stratégique'
  mlScope: 'hors_prd (V7 + V8 existants)'
---

# Product Requirements Document - mohamed_casses

**Author:** mohamed
**Date:** 2026-04-03

## Executive Summary

Les réseaux d'eau potable français vieillissent silencieusement. Aujourd'hui, la gestion patrimoniale repose sur l'intuition des ingénieurs, des tableurs Excel et la réaction aux urgences. Les tronçons à renouveler sont choisis au feeling, les budgets de renouvellement sont défendus avec des discours vagues, et le curatif — plus coûteux — reste invisible dans les lignes budgétaires. Le réseau se dégrade sans signal d'alerte jusqu'à la crise.

La **Plateforme de Gestion Patrimoniale Réseau Eau** transforme ce pilotage à l'aveugle en anticipation chiffrée. Construite sur deux modèles de machine learning validés (prédiction d'abandon AUC=0.84, prédiction de fuites AUC=0.83), elle délivre une vision opérationnelle du réseau en trois couches progressives :

1. **Ciblage fuites** — Carte des risques par tronçon, priorisation des tournées terrain, scoring objectif remplaçant l'intuition
2. **Optimiseur renouvellement** — Plan de renouvellement tri-annuel sous contraintes (budget, réglementation 1% linéaire/an, capacité), scénarios budgétaires chiffrés pour la décision politique
3. **Tableau de bord patrimoine** — KPIs stratégiques : rendement réseau, dette de renouvellement, coût curatif vs préventif, projections

Le MVP est une application web Streamlit déployée pour V2S. L'architecture est conçue générique dès le départ pour être proposée à d'autres collectivités et délégataires. Les modèles ML sont des inputs opérationnels existants, hors périmètre de ce PRD.

**Utilisateurs cibles :** Ingénieur réseau (granularité tronçon, carte terrain, drill-down SHAP), Directeur technique (scénarios budget, KPIs, argumentaire élus), Équipes terrain (priorisation tournées fuites).

### Ce qui rend ce produit spécial

**Le moment carte rouge** — L'ingénieur ouvre la carte, découvre des tronçons à risque qu'il ne soupçonnait pas, vérifie sur le terrain, et constate que le modèle a raison. C'est la bascule de "encore un gadget" à "ça m'aide vraiment". L'outil détecte ce que l'humain seul ne peut pas voir.

**L'argumentaire imparable** — Le directeur passe de "il faut investir dans le réseau" à "X€ investis cette année = Y fuites évitées". Des chiffres précis au lieu d'un discours vague. C'est ce qui débloque les budgets de renouvellement.

**L'insight fondamental** — Le réseau se dégrade silencieusement. La plateforme rend visible l'invisible : elle transforme la dégradation silencieuse en signal d'action et en argumentaire décisionnel.

## Classification Projet

| Attribut | Valeur |
|---|---|
| Type | Application web (Streamlit MVP) |
| Domaine | Gestion patrimoniale réseau eau potable (Utilities) |
| Complexité | Haute — réglementaire, multi-parties prenantes, optimisation sous contraintes |
| Contexte | Brownfield — modèles ML V7+V8 existants et validés |
| Client initial | V2S |
| Architecture | Modulaire, générique multi-collectivités |
| Trajectoire | Ciblage fuites → Optimiseur renouvellement → Plateforme KPIs |

## Critères de Succès

### Succès Utilisateur

| Critère | Métrique | Seuil |
|---|---|---|
| Confiance modèle | Capture@20% (fuites réelles dans le top 20% scoré) | ≥ 60% minimum, cible 70%+ |
| Time-to-value | Temps entre ouverture de l'outil et premier "aha" (carte → clic tronçon → SHAP) | < 5 minutes |
| Adoption ciblage fuites | Équipes terrain utilisent la carte pour orienter les tournées | Utilisé pour 100% des campagnes de recherche de fuites |
| Adoption renouvellement | Plan de renouvellement annuel produit via l'outil | Intégré dans le processus de décision formel |
| Couverture utilisateurs | Ingénieurs réseau + responsable patrimoine + directeur technique actifs | 5 utilisateurs actifs chez V2S |

### Succès Métier

| Critère | Métrique | Baseline → Cible |
|---|---|---|
| Efficacité terrain | Nb fuites trouvées / km inspecté | Méthode actuelle → +30% avec ciblage modèle |
| Fuites évitées | Nb fuites évitées grâce au renouvellement préventif ciblé | À mesurer sur 12 mois post-déploiement |
| Rendement réseau | Indice linéaire de pertes (ILP) ou rendement % | Tendance stable ou en amélioration |
| Argumentaire budget | Budget renouvellement validé par les élus avec chiffrage outil | Au moins 1 arbitrage budgétaire appuyé par l'outil |
| Coût curatif vs préventif | Ratio interventions curatives / préventives | Tendance à la baisse du ratio |

**KPIs audit patrimoine :**

| KPI | Description |
|---|---|
| Indice de connaissance patrimoniale (ICP) | % de tronçons avec données fiables (matériau, date pose, diamètre) |
| Taux de renouvellement effectif | km renouvelés / km total réseau / an (cible réglementaire : 1%) |
| Âge moyen pondéré du réseau | Évolution année après année — indicateur de vieillissement |
| Dette de renouvellement | Coût estimé pour remettre le réseau à niveau (km × coût unitaire par matériau-diamètre) |
| Taux de casses linéaire | Nb casses / 100 km / an — indicateur ONEMA standard |
| Durée de vie résiduelle moyenne | Estimée par le modèle, par secteur ou matériau |
| Précision prédictive rétrospective | Backtesting : % de casses de l'année passée qui étaient dans le top scoré |

### Succès Technique

| Critère | Métrique | Seuil |
|---|---|---|
| Performance | Chargement carte + scoring < 3 secondes | P95 < 3s |
| Disponibilité | Uptime pendant heures ouvrées | > 99% |
| Scalabilité | Nombre de tronçons supportés | ≥ 100k (multi-collectivités) |
| Reproductibilité ML | Scoring identique entre exécutions | Déterministe à 100% |
| Généricité | Déploiement sur nouveau réseau | < 1 jour de configuration |

### Résultats Mesurables

- **Mois 1-3 :** Carte des risques opérationnelle, première campagne terrain ciblée, mesure du nb fuites/km inspecté vs baseline
- **Mois 3-6 :** Plan renouvellement produit via l'outil, premier argumentaire budget présenté aux élus
- **Mois 6-12 :** KPIs patrimoine suivis, mesure d'impact (fuites évitées, rendement), validation réplicabilité sur un second réseau

## Périmètre Produit

### MVP — Minimum Viable Product

- **Carte des risques fuites (V8)** — Tronçons colorés par score de risque, filtres matériau/secteur/âge, clic → détail SHAP
- **Scoring tronçons** — Import données réseau, exécution modèle V8, export scoring CSV
- **Dashboard KPIs de base** — Nb tronçons par classe de risque, distribution matériaux, top tronçons à risque
- **Time-to-value < 5 min** — L'ingénieur voit la carte, clique, comprend pourquoi

### Growth (Post-MVP)

- **Optimiseur renouvellement** — Moteur sous contraintes (budget, 1% linéaire, capacité), plan tri-annuel glissant
- **Scénarios budgétaires** — Simulation "si on investit X€" avec impact projeté, export fiche élus PDF
- **Mode what-if** — Forçage ingénieur (inclusion/exclusion tronçons) + re-optimisation
- **Intégration modèle V7** — Scoring abandon/fin de vie combiné au scoring fuites
- **KPIs patrimoine avancés** — ICP, dette renouvellement, taux casses linéaire, durée vie résiduelle

### Vision (Futur)

- **Intégration SIG** — Carte interactive connectée au SIG collectivité (GeoJSON, WMS)
- **Multi-collectivités** — Architecture multi-tenant, onboarding nouveau réseau en < 1 jour
- **Re-entraînement automatisé** — Pipeline annuel avec nouvelles données
- **Feedback loop** — Les décisions terrain (forçages, retours) alimentent le modèle
- **Simulation Monte Carlo** — Enveloppes d'incertitude sur les projections
- **Benchmark inter-réseaux** — Comparaison anonymisée entre collectivités

## Parcours Utilisateur

**Persona unique MVP : Karim — Ingénieur Patrimoine Réseau**

**Profil :** Ingénieur patrimoine chez V2S, 10+ ans d'expérience réseau eau. Connaît ses secteurs par cœur, utilise Excel et sa mémoire pour prioriser. Sceptique envers les outils "gadgets" mais pragmatique — si ça marche, il adopte. Bureau + terrain. PC fixe au bureau, pas d'usage mobile pour l'instant.

### Parcours 1 : Découverte — "C'est quoi ce tronçon rouge ?"

**Scène d'ouverture :** Lundi matin, Karim ouvre la plateforme pour la première fois. Il a entendu parler du modèle ML mais n'y croit pas vraiment. "Mon réseau, je le connais mieux qu'un algorithme."

**Action montante :** Il voit sa carte. Les tronçons sont colorés du vert au rouge. Il zoome sur son secteur habituel — les rouges correspondent à peu près à ce qu'il sait. Puis il remarque un tronçon rouge dans un quartier qu'il pensait tranquille. Il clique.

**Climax :** Le détail SHAP s'affiche : fonte grise, posé en 1962, 4 fuites en 8 ans, diamètre 100mm. Karim reconnaît le profil — c'est exactement le type de tronçon qui casse. Il ne l'avait pas sur son radar parce qu'il n'y a pas eu de plainte récente. Le modèle a vu ce que lui avait oublié.

**Résolution :** Karim note le tronçon, vérifiera sur le terrain cette semaine. Il commence à comprendre que l'outil ne remplace pas son expertise — il l'augmente. Il garde l'onglet ouvert.

**Exigences révélées :** Carte colorée par score, zoom/pan, clic tronçon → détail SHAP, filtres secteur/matériau, chargement < 3s.

### Parcours 2 : Usage régulier — Préparer une campagne de recherche de fuites

**Scène d'ouverture :** Karim doit planifier les tournées de recherche de fuites du trimestre. Avant, il faisait une liste au feeling + historique.

**Action montante :** Il ouvre la plateforme, filtre par score de risque > seuil, sélectionne un secteur géographique. Il voit les 50 tronçons les plus à risque de fuite dans les 3 prochaines années. Il trie par score, vérifie quelques-uns qu'il connaît — ça colle.

**Climax :** Il exporte la liste en CSV avec les colonnes : identifiant tronçon, adresse/secteur, score risque, matériau, âge, nb fuites historiques, facteurs SHAP principaux. Il envoie le fichier au chef d'exploitation pour orienter les tournées.

**Résolution :** En fin de trimestre, les équipes terrain ont trouvé 30% de fuites en plus par km inspecté par rapport à la méthode précédente. Karim a des chiffres pour le prouver.

**Exigences révélées :** Filtre par score/seuil, sélection secteur, tri multi-critères, export CSV avec colonnes configurables, historique des exports.

### Parcours 3 : Argumentaire — Préparer le budget renouvellement pour le directeur

**Scène d'ouverture :** Septembre — cycle budgétaire. Le directeur technique demande à Karim de préparer l'argumentaire pour le programme de renouvellement de l'année prochaine.

**Action montante :** Karim ouvre le dashboard KPIs : taux de casses linéaire, âge moyen par matériau, répartition des scores de risque. Il regarde les tronçons en classe de risque "critique" et "élevé". Il prépare un top 100 trié par score.

**Climax :** Il exporte un PDF/Excel synthétique : "Sur les 100 km de réseau, 12 km sont en risque critique. Si on renouvelle les 3 km les plus critiques (budget estimé : X€), on réduit le risque de Y fuites sur 3 ans." Des chiffres, pas du feeling. Le directeur peut montrer ça aux élus.

**Résolution :** Le budget est voté. Pour la première fois, l'argumentaire renouvellement s'appuie sur des données prédictives et pas sur "il faut investir parce que c'est vieux".

**Exigences révélées :** Dashboard KPIs agrégés, classement par risque, estimation impact, export PDF/Excel synthétique, données chiffrées pour argumentaire.

### Parcours 4 : Échec et récupération — Le modèle se trompe

**Scène d'ouverture :** Karim a ciblé un tronçon rouge pour inspection prioritaire. Sur le terrain, le tronçon est en bon état. Un tronçon vert dans le quartier d'à côté a cassé la semaine dernière.

**Action montante :** Karim revient sur la plateforme, vérifie les données du tronçon vert qui a cassé : date de pose manquante (imputée), 0 fuites historiques, matériau "Autre". Le modèle n'avait pas assez de signal.

**Climax :** Karim comprend les limites : le modèle prédit la dégradation, pas les accidents (travaux tiers, surpression ponctuelle). Il note mentalement les secteurs où les données sont faibles (ICP bas).

**Résolution :** Il fait confiance au modèle pour ce qu'il fait bien (tendances, cohortes), et garde son expertise pour les cas hors modèle. L'outil affiche clairement le niveau de confiance des données par tronçon.

**Exigences révélées :** Indicateur de fiabilité données par tronçon (ICP local), transparence limites modèle, distinction "risque prédit" vs "données insuffisantes".

### Synthèse des exigences révélées par les parcours

| Capacité | Parcours source |
|---|---|
| Carte interactive colorée par score de risque | 1, 2 |
| Détail tronçon avec explication SHAP | 1, 4 |
| Filtres (secteur, matériau, âge, score) | 2, 3 |
| Tri et sélection multi-critères | 2, 3 |
| Export CSV configurable | 2 |
| Export PDF/Excel synthétique (argumentaire) | 3 |
| Dashboard KPIs agrégés | 3 |
| Indicateur fiabilité données (ICP par tronçon) | 4 |
| Chargement < 3 secondes | 1 |
| Estimation d'impact (X€ → Y fuites évitées) | 3 |

## Exigences Spécifiques au Domaine

### Conformité & Réglementaire

- **Décret rendement réseau** — Obligation de suivi du rendement (seuils ONEMA), reporting annuel
- **Réglementation 1% linéaire/an** — Plancher de renouvellement imposé par l'État, contrainte dure dans l'optimiseur
- **Amiante-ciment** — Réglementation spécifique pour les tronçons AC (manipulation, élimination), impact sur les coûts de remplacement
- **RPQS** — Rapport annuel sur le prix et la qualité du service, KPIs normalisés

### Contraintes Techniques

- **Données patrimoniales imparfaites** — 17% de dates de pose non fiables (placeholder 1900), matériaux parfois inconnus, diamètres à 0. L'outil doit fonctionner avec ces imperfections et les signaler (ICP)
- **Pas de géolocalisation fine pour le MVP** — Données tabulaires, pas de coordonnées SIG dans V1. Architecture SIG-ready mais carte symbolique au départ
- **Scoring déterministe** — Même données = même score. Reproductibilité garantie pour la confiance utilisateur
- **Volume** — ~100k tronçons pour V2S, scalable à 500k+ pour multi-collectivités

### Contraintes Métier

- **Cycle budgétaire annuel** — L'outil doit produire ses livrables (argumentaire, plan) en phase avec le calendrier budgétaire collectivité (sept-nov)
- **Boucle déléguant/délégataire** — SOMEI (délégataire) propose, la collectivité (déléguant) valide et finance. L'outil sert les deux côtés
- **Deux gammes de remplacement** — Bas-gamme vs haut-gamme, coûts unitaires différents par matériau × diamètre
- **Scepticisme terrain** — Précédents négatifs avec des outils "gadgets". L'adoption passe par la preuve (SHAP, backtesting), pas par l'obligation

### Risques & Mitigations

| Risque | Impact | Mitigation |
|---|---|---|
| Modèle pas fiable (faux positifs excessifs) | Perte de confiance, abandon de l'outil | Backtesting systématique, capture@20% > 60% comme go/no-go |
| Données trop incomplètes sur un réseau | Scoring non exploitable | ICP par tronçon, seuil minimum de qualité données pour le scoring |
| Résistance au changement | Non-adoption malgré outil fonctionnel | Quick wins (carte + SHAP), formation intégrée, time-to-value < 5min |
| Biais de surveillance | Tronçons surveillés = plus de casses détectées | Documenté dans les limites du modèle, transparence dans l'interface |
| Dépendance au format données source | Blocage sur un nouveau réseau | Format d'import standardisé, validation automatique à l'import |

## Innovation & Positionnement

### Innovation métier

- **ML prédictif appliqué à la gestion patrimoniale eau en France** — Secteur encore largement géré au tableur et à l'intuition. Le scoring prédictif par tronçon avec explication SHAP est une rupture dans les pratiques du domaine.
- **Combinaison scoring + optimisation sous contraintes** — Le scoring prédictif seul existe (bureaux d'études). L'intégration dans un optimiseur sous contraintes budget/réglementaire pour produire un plan actionnable est le saut de valeur.
- **Explicabilité comme condition d'adoption** — SHAP intégré dès la conception, pas en bonus. Choix produit dicté par la réalité terrain : sans transparence, pas d'adoption.

### Nature de l'innovation

Excellente exécution d'un concept ML appliqué à un domaine sous-digitalisé. L'innovation réside dans l'application métier et l'approche produit (preuve par le terrain, time-to-value, explicabilité), pas dans un algorithme nouveau.

### Validation

- Backtesting sur données historiques (3 fenêtres temporelles, AUC stable 0.83-0.89)
- Capture@20% > 60% comme critère go/no-go
- Validation terrain par l'ingénieur (vérification des tronçons rouges)
- Mesure d'efficacité : nb fuites trouvées / km inspecté vs méthode précédente

## Exigences Techniques Web App

### Architecture MVP

| Composant | Choix | Justification |
|---|---|---|
| Stack front+back | Streamlit (Python) | Même langage que les modèles ML, prototypage rapide, composants data intégrés |
| Déploiement | Local (poste ingénieur) | Données patrimoniales sensibles, pas de cloud pour le MVP |
| Données scoring | CSV pré-calculé, chargé au démarrage | Mise à jour annuelle post re-entraînement |
| Carte | Folium ou Pydeck via Streamlit | Si données géo disponibles (GeoJSON SIG) |
| Utilisateurs | Monoposte, pas d'authentification | MVP = 1 ingénieur patrimoine |
| Base de données | Aucune — CSV/Parquet en fichiers | Suffisant pour ~100k tronçons, chargement < 3s |

### Structure de données

**Fichiers d'entrée :**
- `scoring_troncons.csv` — Pré-calculé par le pipeline V8 : ID tronçon, score risque H1/H3/H5, features, valeurs SHAP
- `referentiel_troncons.csv` — Données patrimoniales : matériau, diamètre, longueur, date pose, statut
- `troncons.geojson` (optionnel MVP, recommandé) — Tracés géographiques pour la carte, jointure sur ID tronçon

**Action préalable :** Demander au SIG V2S un export GeoJSON des tronçons avec l'identifiant OBJET comme clé de jointure. Effort estimé : ~1h côté SIG.

**Exports :**
- CSV configurable (sélection colonnes, filtres appliqués)
- PDF/Excel synthétique pour argumentaire budget (post-MVP)

### Contraintes techniques Streamlit

| Contrainte | Impact | Mitigation |
|---|---|---|
| Pas de state persistant natif | Perte de filtres au rechargement | `st.session_state` pour conserver l'état |
| Rechargement complet à chaque interaction | Lenteur si données lourdes | Cache `@st.cache_data` pour le chargement CSV/GeoJSON |
| Carte interactive limitée | Clic tronçon difficile nativement | `streamlit-folium` avec popup on click |
| Monothread | Un seul utilisateur à la fois | OK pour MVP monoposte |
| Pas de gestion utilisateurs | Pas d'auth, pas de rôles | OK pour MVP, à adresser en Growth |

### Performance MVP

| Métrique | Cible | Approche |
|---|---|---|
| Démarrage app | < 5s | Cache données au premier chargement |
| Chargement carte | < 3s | GeoJSON simplifié (Douglas-Peucker si > 100k points) |
| Filtre/tri | < 1s | Pandas en mémoire, index sur colonnes fréquentes |
| Export CSV | < 2s | Écriture directe depuis DataFrame filtré |

### Évolution technique (Growth)

| Étape | Changement |
|---|---|
| Multi-utilisateurs | Déploiement serveur interne + authentification LDAP/AD |
| Persistance | SQLite ou PostgreSQL pour historique décisions |
| API scoring | FastAPI pour découpler scoring/interface |
| Carte avancée | Migration vers Mapbox/Leaflet avec couches SIG complètes |

## Scoping & Développement Phasé

### Stratégie MVP

**Approche :** MVP problem-solving — résoudre un problème concret (ciblage fuites) avec le minimum qui prouve la valeur.

**Développeur :** mohamed, solo. Stack Python identique aux modèles ML → pas de montée en compétence.

**Dépendances :**

| Dépendance | Statut | Impact |
|---|---|---|
| Données nettoyées | Prêt | Aucun blocage |
| Scoring V8 (CSV) | Prêt | Aucun blocage |
| Environnement Python | Prêt | Aucun blocage |
| GeoJSON tronçons (SIG) | À demander en parallèle | Non bloquant — mode tabulaire par défaut, carte ajoutée dès réception |

### MVP Feature Set (Phase 1)

**Stratégie carte :** Mode dégradé gracieux — tableau interactif par défaut, carte Folium activée automatiquement si `troncons.geojson` est présent. Le GeoJSON est un accélérateur d'adoption, pas un prérequis.

**Parcours utilisateur supportés :** Parcours 1 (découverte), Parcours 2 (campagne fuites), Parcours 4 (limites modèle)

**Must-have MVP :**

| Fonctionnalité | Justification | Sans ça ? |
|---|---|---|
| Vue tronçons avec scoring coloré (tableau ou carte) | C'est le produit. Le "moment carte rouge" | Pas de produit |
| Détail tronçon + SHAP | Condition d'adoption (#70 brainstorming) | Gadget sans transparence |
| Filtres (matériau, score, âge) | Parcours 2 — ciblage campagne | Inutilisable pour le terrain |
| Export CSV | Parcours 2 — envoi au chef d'exploitation | Pas de workflow opérationnel |
| KPIs de base (distribution risques, top tronçons) | Parcours 3 simplifié — premier aperçu | OK sans, mais perte d'impact |
| Vue cohorte matériau × décennie | Identification visuelle des cohortes problématiques (#34 brainstorming) | Perte d'un levier d'analyse puissant |
| Courbe Lift du modèle | Preuve visuelle de la valeur ajoutée du scoring (#83 brainstorming) — données déjà dans V8 | Pas de preuve tangible pour convaincre |
| ICP par tronçon (indicateur fiabilité données) | Parcours 4 — transparence limites | Faux sentiment de certitude |

**Explicitement hors MVP :**
- Export PDF/Excel argumentaire (Parcours 3 complet)
- Estimation impact €/fuites
- Optimiseur renouvellement
- Multi-utilisateurs / authentification
- Intégration SIG native

### Phase 2 — Growth

**Déclencheur :** MVP validé par Valentin + adoption pour au moins 1 campagne terrain

| Fonctionnalité | Dépendance |
|---|---|
| Optimiseur renouvellement sous contraintes | Moteur à développer (scipy/PuLP) |
| Scénarios budgétaires + export fiche élus | Matrice coûts unitaires matériau×diamètre nécessaire |
| Mode what-if (forçage + re-optimisation) | Optimiseur fonctionnel |
| Intégration V7 (scoring abandon) | Pipeline V7 scoring CSV |
| KPIs patrimoine avancés (dette, taux casses, durée vie résiduelle) | Données coûts + formules métier |
| Vue "surprises" — tronçons scorés différemment par le modèle vs intuition expert | Scoring expert de référence à construire (#119 brainstorming) |
| Multi-utilisateurs | Déploiement serveur + auth |

### Phase 3 — Vision

| Fonctionnalité | Condition |
|---|---|
| Multi-collectivités (multi-tenant) | Architecture validée sur V2S |
| Intégration SIG complète (WMS, couches) | Partenariat SIG collectivité |
| Re-entraînement automatisé | Pipeline MLflow stabilisé |
| Feedback loop terrain → modèle | Volume de retours suffisant |
| Simulation Monte Carlo | Besoin validé par le métier |
| Benchmark inter-réseaux | ≥ 2 collectivités opérationnelles |

### Risques de scoping

| Risque | Probabilité | Mitigation |
|---|---|---|
| GeoJSON jamais livré par le SIG | Moyenne | Mode tabulaire fonctionnel, carte = bonus intégrable à tout moment |
| Scope creep pendant le dev solo | Haute | MVP = ces 8 fonctionnalités, rien de plus. Tout le reste est Phase 2+ |
| Karim ne comprend pas l'interface | Moyenne | Session de 15 min avec lui dès le premier prototype, itérer sur le feedback |
| Dev solo = bus factor 1 | Haute | Code documenté, architecture simple, pas de sur-ingénierie |

## Exigences Fonctionnelles

### Visualisation du réseau

- **FR1 :** L'ingénieur peut voir l'ensemble des tronçons du réseau avec un code couleur par niveau de risque (classes : critique, élevé, modéré, faible)
- **FR2 :** L'ingénieur peut visualiser les tronçons sur une carte géographique interactive si les données géo sont disponibles (mode carte)
- **FR3 :** L'ingénieur peut visualiser les tronçons dans un tableau interactif trié par score (mode tabulaire, toujours disponible)
- **FR4 :** L'ingénieur peut basculer entre le mode carte et le mode tabulaire
- **FR5 :** L'ingénieur peut zoomer, se déplacer et naviguer sur la carte
- **FR6 :** L'application détecte automatiquement la présence du fichier GeoJSON et active le mode carte sans configuration manuelle

### Détail tronçon & explicabilité

- **FR7 :** L'ingénieur peut sélectionner un tronçon (clic carte ou clic ligne tableau) pour voir son détail complet
- **FR8 :** Le détail tronçon affiche les caractéristiques patrimoniales : matériau, diamètre, longueur, date de pose, âge, statut
- **FR9 :** Le détail tronçon affiche le score de risque pour chaque horizon (1 an, 3 ans, 5 ans)
- **FR10 :** Le détail tronçon affiche l'explication SHAP : contribution de chaque feature au score, avec indication du sens (augmente/diminue le risque)
- **FR11 :** Le détail tronçon affiche l'historique des fuites passées du tronçon (nombre, dates)
- **FR12 :** Le détail tronçon affiche un indicateur de fiabilité des données (ICP local) distinguant "risque prédit" de "données insuffisantes"

### Filtrage & recherche

- **FR13 :** L'ingénieur peut filtrer les tronçons par famille de matériau
- **FR14 :** L'ingénieur peut filtrer les tronçons par classe de risque (seuil de score configurable)
- **FR15 :** L'ingénieur peut filtrer les tronçons par tranche d'âge
- **FR16 :** L'ingénieur peut filtrer les tronçons par diamètre
- **FR17 :** L'ingénieur peut combiner plusieurs filtres simultanément
- **FR18 :** L'ingénieur peut sélectionner l'horizon de prédiction à afficher (1, 3 ou 5 ans)
- **FR19 :** L'ingénieur peut trier les résultats par n'importe quelle colonne (score, âge, matériau, nb fuites...)

### Export de données

- **FR20 :** L'ingénieur peut exporter la liste des tronçons filtrés en CSV
- **FR21 :** L'ingénieur peut choisir les colonnes à inclure dans l'export CSV
- **FR22 :** L'export CSV inclut les scores de risque, les features et les valeurs SHAP principales

### Dashboard & KPIs

- **FR23 :** L'ingénieur peut voir la répartition des tronçons par classe de risque (graphique)
- **FR24 :** L'ingénieur peut voir la distribution des matériaux du réseau
- **FR25 :** L'ingénieur peut voir le top N des tronçons les plus à risque
- **FR26 :** L'ingénieur peut voir les KPIs patrimoine de base : nombre total de tronçons, km total, âge moyen, ICP global
- **FR27 :** L'ingénieur peut voir une vue cohorte matériau × décennie de pose avec les statistiques de risque agrégées (score moyen, nb tronçons, nb fuites) pour identifier les cohortes problématiques
- **FR28 :** L'ingénieur peut voir la courbe Lift du modèle (gain cumulé vs sélection aléatoire) démontrant visuellement la valeur ajoutée du scoring prédictif

### Chargement & données

- **FR29 :** L'application charge les données de scoring pré-calculées au démarrage depuis des fichiers CSV
- **FR30 :** L'application charge les données patrimoniales de référence depuis un fichier CSV séparé
- **FR31 :** L'application valide la cohérence des données au chargement et signale les anomalies (colonnes manquantes, formats incorrects)
- **FR32 :** L'application conserve l'état des filtres et de la vue pendant la session (pas de perte au rechargement interne)

## Exigences Non-Fonctionnelles

### Performance

| NFR | Critère | Mesure |
|---|---|---|
| NFR1 | Démarrage de l'application | < 5 secondes jusqu'à l'affichage de la vue principale |
| NFR2 | Chargement carte (si GeoJSON) | < 3 secondes pour ~100k tronçons |
| NFR3 | Réponse filtre/tri | < 1 seconde après modification d'un filtre |
| NFR4 | Export CSV | < 2 secondes pour un jeu filtré |
| NFR5 | Mémoire RAM | < 2 Go pour le dataset complet V2S en mémoire |

### Sécurité & confidentialité des données

| NFR | Critère | Mesure |
|---|---|---|
| NFR6 | Déploiement local uniquement | Aucune donnée patrimoniale transmise à un serveur externe |
| NFR7 | Pas de télémétrie | Aucune donnée collectée par Streamlit ou librairies tierces vers l'extérieur |
| NFR8 | Fichiers données | Stockés sur le poste local, accès contrôlé par les droits OS |
| NFR9 | Pas de credentials en dur | Aucun mot de passe, token ou secret dans le code source |

### Fiabilité & reproductibilité

| NFR | Critère | Mesure |
|---|---|---|
| NFR10 | Scoring déterministe | Mêmes données d'entrée = mêmes scores affichés, à chaque exécution |
| NFR11 | Validation données au chargement | L'application détecte et signale les fichiers corrompus ou incomplets sans crash |
| NFR12 | Aucune perte d'état en session | Les filtres et la vue sont conservés tant que l'onglet navigateur est ouvert |
| NFR13 | Gestion des erreurs | Aucun stacktrace Python affiché à l'utilisateur — messages d'erreur lisibles |

### Maintenabilité

| NFR | Critère | Mesure |
|---|---|---|
| NFR14 | Code lisible | Structure modulaire, fonctions documentées, noms explicites |
| NFR15 | Configuration externalisée | Chemins fichiers, seuils de risque, couleurs → fichier de config, pas en dur |
| NFR16 | Indépendance données/code | Changement de dataset (nouveau réseau) sans modification du code source |
| NFR17 | Dépendances minimales | Nombre de packages Python < 15, toutes open source |

### Portabilité (multi-collectivités)

| NFR | Critère | Mesure |
|---|---|---|
| NFR18 | Format d'entrée standardisé | Spécification documentée du format CSV attendu (colonnes, types, encodage) |
| NFR19 | Déploiement sur nouveau réseau | < 1 jour de configuration (changement des fichiers données uniquement) |
| NFR20 | Compatibilité OS | Fonctionne sur Windows 10+ (environnement V2S) |
