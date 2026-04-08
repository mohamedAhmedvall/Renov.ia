---
stepsCompleted: [1, 2, 3, 4]
session_active: false
workflow_completed: true
inputDocuments: []
session_topic: 'Prediction de casses de canalisations eau + moteur optimisation renouvellement'
session_goals: 'Nettoyage dataset, modele predictif fiable, optimisation sous contraintes, interface plan renouvellement'
selected_approach: 'ai-recommended'
techniques_used: ['morphological-analysis', 'first-principles-thinking', 'constraint-mapping']
ideas_generated: [140]
context_file: ''
---

# Brainstorming Session Results

**Facilitateur:** mohamed
**Date:** 2026-04-01

## Session Overview

**Sujet:** Developpement d'un systeme de prediction de casses de canalisations d'eau et moteur d'optimisation sous contraintes pour les plans de renouvellement
**Objectifs:**
- Nettoyage du dataset
- Developpement d'un modele predictif fiable
- Moteur d'optimisation sous contraintes pour le renouvellement
- Interface utilisateur pour la gestion du plan de renouvellement

### Session Setup

_Approche hybride : recommandations IA + selection utilisateur dans la bibliotheque de techniques_

## Technique Selection

**Approche :** Recommandations IA
**Contexte d'analyse :** Prediction casses canalisations + optimisation renouvellement

**Techniques recommandees :**

- **Morphological Analysis :** Decomposition systematique des axes du systeme (data, modele, optimisation, UI) et exploration des combinaisons
- **First Principles Thinking :** Questionner les hypotheses fondamentales sur les causes de casses et les contraintes reelles du renouvellement
- **Constraint Mapping :** Cartographier toutes les contraintes (budget, reglementation, ressources, criticite) pour le moteur d'optimisation

**Logique IA :** Sequence cadrage -> generation -> robustesse adaptee a un probleme technique multi-composants

## Technique Execution Results

### Technique 1 : Morphological Analysis (100 idees generees)

**Focus interactif :** Decomposition systematique du systeme en 4 axes (donnees, modele, optimisation, interface) puis exploration exhaustive des combinaisons et implications.

**Idees cles par domaine :**

**Donnees & Features (22 idees) :**
- #14 Detection dates pose aberrantes (15-20% a "1900" = placeholder SIG)
- #15 Feature "date_pose_fiable" binaire — l'incertitude comme information
- #25 Imputation par materiau-epoque (logique campagne de pose)
- #26 Variable "age_incertain" explicite pour le modele
- #36 Feature engineering temporel (acceleration casses, saisonnalite, intervalle moyen)
- #37 Encodage hierarchique materiaux (metallique/plastique/composite)
- #38 Ratio diametre/pression comme indicateur de stress mecanique
- #39 Detection casses "en serie" (contagion par surpression)
- #51 Gestion troncons zero-anomalie (biais de surveillance)
- #85 Feature "acceleration de degradation" (derivee du taux)
- #86 Pression relative vs design nominal
- #87 Interaction age x materiau
- #88 Etat descriptif comme feature ordinale
- #93 Pipeline nettoyage reproductible et documente
- #94 Rapport qualite donnees comme livrable
- #95 Detection doublons et incoherences

**Modelisation (18 idees) :**
- #1 Age-Materiau-Survie (approche actuarielle Weibull)
- #2 Frequence-casses-XGBoost
- #7 Courbes de survie Kaplan-Meier par cohorte materiau-age
- #10 OBJET_DEPOSE_OU_ABANDONNE comme signal
- #16 Matrice materiau-degradation differenciee
- #19 Analyse survie stratifiee par materiau
- #40 Validation croisee temporelle stricte
- #52 Biais troncons remplaces recemment
- #53 Desequilibre classes — modele survie comme solution naturelle
- #54 Troncons abandonnes = censure en survie
- #55 Robustesse donnees manquantes (XGBoost natif NaN)
- #56 Modele hybride Survie + ML (interpretabilite + precision)
- #66 Modele survie a risques concurrents
- #67 Modele par famille materiau avec transfert
- #69 Calibration probabilites (Platt/isotonic)
- #70 Interpretabilite SHAP par troncon — CONDITION D'ADOPTION
- #84 Validation temporelle multi-fenetres
- #96 Challenger le ML — modele simple peut suffire

**Optimisation (15 idees) :**
- #3 Survie + Optimisation Pareto (front risque-cout)
- #21 Regroupement spatial des travaux
- #22 Contrainte capacite annuelle
- #23 Cout variable par diametre/materiau
- #24 Scenario "ne rien faire" comme baseline
- #27 Optimisation tri-annuelle glissante (an 1 ferme, ans 2-3 indicatifs)
- #28 Seuil reglementaire rendement comme contrainte dure
- #41 Matrice couts unitaires diametre x materiau remplacement (2 gammes)
- #42 Contrainte 1% lineaire comme plancher, pas cible
- #46 Bi-objectif risque vs cout avec plancher 1%
- #47 Penalite de report dans l'optimiseur
- #64 Cout bas-gamme vs haut-gamme en cycle de vie
- #65 Strategie mixte materiaux dans le plan

**Interface (16 idees) :**
- #5 Score criticite evolutif (proba x impact)
- #6 Double interface cockpit ingenieur + tableau strategique directeur
- #20 Architecture SIG-ready des le depart
- #31 Mode simulation budgetaire interactif (slider)
- #32 Export "fiche elu" PDF automatique
- #33 Alerte troncon critique temps reel
- #34 Vue cohorte dans l'interface
- #57 Score risque decompose en 3 composantes transparentes
- #59 Mode "what-if" ingenieur (forcage + re-optimisation) — BESOIN CLE
- #60 Dashboard performance modele
- #78 Onboarding progressif
- #79 Historique des decisions
- #80 Export multi-format (PDF, Excel, GeoJSON, CSV)
- #81 Rapport SHAP agrege pour le directeur

**Processus & Livraison (14 idees) :**
- #48 Pipeline ML reproductible (MLflow/DVC)
- #49 Architecture 3 modules independants (modele/optimiseur/interface)
- #50 Stack Python end-to-end
- #71 Livraison incrementale 4 phases
- #72 Phase 1 = etat des lieux patrimonial
- #73 Re-entrainement annuel automatise
- #74 Metriques suivi post-deploiement
- #82 Phase 2 = modele + backtesting + rapport de confiance — LIVRABLE CLE
- #83 Courbe Lift comme outil communication
- #97 Plan contingence si modele se trompe
- #99 Formation utilisateur integree au livrable

**Strategie & Argumentaire (15 idees) :**
- #4 Filtrage anomalies degradation naturelle vs causes externes
- #8 Scenarios budgetaires dynamiques (3-5 scenarios)
- #9 Feature temps depuis derniere anomalie
- #11 Integration cycle vie reglementaire
- #13 Plan renouvellement glissant 5-10 ans
- #17 Hierarchie risque AC (sanitaire/reglementaire)
- #29 Cout curatif vs preventif par troncon
- #30 Simulation Monte Carlo trajectoire reseau
- #35 Indicateur "dette de renouvellement"
- #44 Estimation indirecte rendement par casses
- #45 Proxy rendement via densite anomalies
- #58 Backtesting plan renouvellement (preuve par le passe)
- #89 Scenario rattrapage dette patrimoniale
- #90 Projection nombre casses par scenario
- #91 Cout total de possession du reseau
- #92 Point de bascule reglementaire
- #98 Open data et benchmarking
- #100 Vision plateforme patrimoniale reutilisable

**Insights utilisateur :**
- Backtesting = livrable de credibilite, pas nice-to-have
- SHAP = condition d'adoption par l'ingenieur terrain
- Mode what-if = besoin fonctionnel cle (savoir terrain non modelisable)
- Dates 1900 = placeholder SIG identifie en EDA (15-20%)
- 2 materiaux remplacement = bas-gamme vs haut-gamme
- Plan 3 ans, contrainte 1% lineaire (reglementaire etat)
- 2 profils utilisateurs : ingenieur reseau (granularite troncon) + directeur technique (scenarios budget)
- Suivi contractuel delegataire = hors scope pour l'instant

### Technique 2 : First Principles Thinking (20 idees supplementaires, #101-#120)

**Focus interactif :** Deshabiller le probleme jusqu'aux verites fondamentales, questionner chaque hypothese.

**Decouvertes fondamentales :**

- **Materiau-epoque > age brut** (#101) : La cohorte materiau-epoque est la vraie variable. L'age seul est un proxy trompeur.
- **Reparation = mecanisme aggravant** (#102) : Chaque reparation (manchon, raccord) cree un point de fragilite mecanique. Feature positive de risque.
- **Contagion de cohorte** (#103) : Troncons poses ensemble, meme materiau, meme tranchee = meme etat. Signal spatial par genealogie de pose.
- **"Prove it or drop it"** (#104-105) : Pression, terrain, diametre = features suspectes. Tester rigoureusement apres controle materiau+age, dropper si pas de signal.
- **Qualite donnee comme meta-feature** (#106) : Score de completude par troncon — l'incertitude est elle-meme un signal.
- **Modeliser l'irreductible** (#107-109) : Accepter qu'une fraction des casses est non-predictible (causes externes). Communiquer le scope : "prediction de degradation, pas des accidents".
- **Troncon = unite de prediction, agregation pour la decision** (#110) : Confirme par mohamed — aligne avec le SIG et les pratiques terrain.
- **Survie vs classification** (#111) : Duree de vie residuelle > score binaire. Plus riche pour le planificateur.
- **Nettoyage = hypothese, pas preprocessing** (#116-118) : Chaque choix d'imputation/filtrage est testable. Sensibilite a evaluer.
- **Fonction objectif = decision politique** (#113-115) : "Minimiser quoi ?" change le plan radicalement. L'outil eclaire, ne decide pas.
- **Valeur dans les surprises** (#119-120) : Les divergences modele/expert sont le livrable le plus precieux.

**Decisions utilisateur :**
- Troncon comme unite de prediction, agregation ensuite pour la decision
- Baseline humain (scoring ingenieur) = possible mais mis de cote pour l'instant

### Technique 3 : Constraint Mapping (20 idees supplementaires, #121-#140)

**Focus interactif :** Cartographie exhaustive des contraintes reelles, fausses contraintes, et leviers caches.

**Contraintes dures identifiees :**
- 1% lineaire/an (reglementaire Etat) — plancher non-negociable
- Horizon plan 3 ans — fenetre d'optimisation
- Budget annuel collectivite — plafond travaux
- Boucle delegant (collectivite) / delegataire (SOMEI) — SOMEI propose, collectivite valide et finance
- Gap SIG/outil terrain — integration ou mort de l'outil
- Bus factor / maintenabilite — documentation + formation obligatoires
- Valeur visible rapidement — livrables 4-6 semaines par phase

**Contraintes molles :**
- Donnees V1 sans SIG, sol/pression incertains — enrichissement V2
- Forcage politique elu — what-if + tracabilite des impacts
- Scepticisme precedent negatif — quick wins phase 1

**Risque critique :**
- Algo pas fiable = risque #1 identifie par mohamed
- Mitigation : go/no-go par phase, modele simple d'abord, metriques metier parlantes

**Fausses contraintes eliminees :**
- #137 SIG prerequis → V1 tabulaire suffit
- #138 Couts reels prerequis → ratios standards suffisent
- #139 Modele avant optimiseur → parallelisable
- #140 Forcage politique invalide optim → re-optimisation contraint reste meilleur que pas d'optim

**Idees cles :**
- #121 Matrice contraintes dures vs molles dans l'optimiseur
- #126 Interface servant les 2 cotes (delegant + delegataire)
- #127 Outil comme "miroir des compromis" — montre impact des modifications politiques
- #128 Integration SIG = condition de survie
- #130 Fiabilite incrementale — modele simple d'abord
- #131 Criteres go/no-go a chaque phase
- #132 Metriques parlantes pour non-techniques (lift metier, pas AUC)
- #134 Quick wins — valeur visible en 4-6 semaines

### Creative Facilitation Narrative

_Session de brainstorming structuree en 3 techniques complementaires. La Morphological Analysis a couvert l'espace des solutions de maniere exhaustive (100 idees). Le First Principles Thinking a creuse les fondations et revele des verites inconfortables (materiau-epoque > age, reparation aggravante, nettoyage = hypothese). Le Constraint Mapping a cartographie les murs reels et elimine les fausses contraintes. Mohamed a apporte une lucidite terrain remarquable — distinction claire entre ce qu'il sait, ce qu'il suppose, et ce qu'il ne peut pas savoir. Les insights les plus precieux sont venus de ses retours : SHAP comme condition d'adoption, backtesting comme livrable de credibilite, forcage what-if comme besoin fonctionnel cle._

### Session Highlights

**Forces creatives de l'utilisateur :** Vision systeme claire, lucidite sur les limites des donnees, pragmatisme (troncon comme unite, pas de perfection avant action)
**Approche de facilitation :** Structuree puis derangeante (First Principles) puis pragmatique (Constraints)
**Moments de percee :** #109 "le modele predit la degradation pas les accidents", #119 "la valeur est dans les surprises", #126 "miroir des compromis delegant/delegataire"
**Flux creatif :** Soutenu tout au long, reponses de plus en plus profondes a mesure que les techniques avancaient

## Idea Organization and Prioritization

### Organisation thematique (6 themes, 140 idees)

**Theme 1 : Nettoyage & Feature Engineering** (#4, #14, #25, #26, #36, #37, #38, #85, #86, #87, #88, #93, #94, #95, #101, #102, #103, #104, #105, #106, #116, #117, #118)
- Cohorte materiau-epoque > age brut
- Reparation = facteur aggravant (manchon = fragilite)
- Contagion de cohorte (poses ensemble = vieillissent ensemble)
- "Prove it or drop it" pour features incertaines (pression, terrain, diametre)
- Pipeline reproductible + rapport qualite donnees

**Theme 2 : Modelisation & Validation** (#1, #7, #19, #40, #51, #52, #53, #54, #55, #56, #57, #61, #66, #69, #70, #81, #82, #83, #84, #96, #107, #108, #109, #111, #119, #120, #130)
- Hybride Survie + ML pour interpretabilite + precision
- SHAP par troncon = CONDITION D'ADOPTION
- Validation temporelle multi-fenetres + backtesting = LIVRABLE CLE
- Modele simple d'abord comme diagnostic precoce
- Scope : prediction de degradation, pas des accidents

**Theme 3 : Moteur d'optimisation** (#21, #22, #27, #41, #42, #46, #47, #59, #62, #63, #64, #65, #121, #122, #123, #126, #127, #139, #140)
- Bi-objectif risque vs cout, plancher 1%, horizon 3 ans glissant
- Contraintes dures vs molles explicites
- What-if ingenieur avec trace et justification = BESOIN CLE
- Miroir des compromis delegant/delegataire
- Parallelisable avec le modele (scoring simple en attendant)

**Theme 4 : Interface & UX** (#6, #20, #31, #32, #33, #34, #60, #78, #79, #80, #128)
- Cockpit ingenieur (SIG, troncons, drill-down) + Tableau directeur (scenarios, KPIs)
- Slider budget interactif + export fiche elu PDF
- Architecture SIG-ready des le depart
- Integration SIG = condition de survie a terme

**Theme 5 : Strategie d'argumentation** (#8, #24, #29, #30, #35, #44, #45, #58, #89, #90, #91, #92, #132)
- Scenario "ne rien faire" = LEVIER PRINCIPAL pour debloquer budgets
- Cout curatif vs preventif, dette de renouvellement, point de bascule reglementaire
- Metriques metier parlantes (lift, pas AUC)

**Theme 6 : Livraison & perennite** (#48, #49, #50, #71, #72, #73, #74, #97, #99, #124, #125, #131, #133, #134, #135, #137, #138)
- 4 phases incrementales avec go/no-go
- Stack Python end-to-end, 3 modules independants
- V1 avec ce qu'on a, architecture pluggable
- Formation + documentation = conditions de perennite

### Prioritization Results

**Top 3 idees a plus fort impact (choix utilisateur) :**
1. **SHAP par troncon (#70)** — Sans ca, pas d'adoption. L'ingenieur doit savoir POURQUOI un troncon est a risque.
2. **Modele de prediction fiable (Theme 2)** — C'est l'argument qui debloque les budgets. Inclut backtesting comme livrable de credibilite.
3. **Livraison incrementale 4 phases (#71)** — Valeur visible rapidement, evite l'effet tunnel.

**Quick win immediat :**
- **Etat des lieux patrimonial (#72)** — Faisable en 1-2 semaines a partir des donnees brutes. Distribution ages/materiaux, evolution casses, cohortes a risque, qualite donnees. Premiere vue synthetique du reseau pour le directeur.

**V2+ (enrichissements futurs) :**
- Integration SIG (carte interactive, clustering spatial)
- Feedback loop des forcages ingenieur → features V2
- Simulation Monte Carlo (enveloppes d'incertitude)
- Donnees de couts reels (remplacement ratios standards)
- Donnees sol/voirie si disponibles
- Re-entrainement automatise annuel

### Action Planning

**Phase 1 — Etat des lieux patrimonial (1-2 semaines) :**
1. Pipeline nettoyage reproductible (dates 1900, anomalies externes, jointure)
2. Rapport : distribution ages/materiaux, cohortes, evolution casses/an, qualite donnees
3. Top troncons sinistres + identification cohortes a risque (AC 1960-70, FG pre-1960)
4. Livrable : rapport PDF pour directeur technique

**Phase 2 — Modele predictif + backtesting (gate : go/no-go phase 1) :**
1. Feature engineering : cohorte materiau-epoque, nb reparations, acceleration casses, interactions
2. "Prove it or drop it" sur features incertaines
3. Baseline simple (scoring cohorte x historique) puis ML (XGBoost / survie hybride)
4. Validation temporelle multi-fenetres
5. SHAP integre des le depart
6. Livrable : modele + rapport de confiance + backtesting + courbe lift

**Phase 3 — Moteur optimisation (gate : go/no-go phase 2) :**
1. Formulation bi-objectif risque vs cout, contraintes dures (1%, budget) vs molles
2. Plan tri-annuel glissant avec penalite de report
3. Matrice couts 2 gammes x diametres
4. What-if ingenieur (forcage + re-optimisation)
5. Scenarios budgetaires (3-5 scenarios + "ne rien faire")
6. Livrable : moteur + scenarios + argumentaire directeur

**Phase 4 — Interface (gate : go/no-go phase 3) :**
1. Cockpit ingenieur : troncons par risque, filtres, drill-down SHAP, historique
2. Tableau directeur : slider budget, scenarios compares, KPIs, export fiche elu
3. Architecture SIG-ready (nullable, plug-and-play)
4. Onboarding progressif + formation
5. Livrable : interface deployee + documentation

## Session Summary and Insights

**Realisations cles :**
- 140 idees generees en 3 techniques complementaires
- 6 themes structures couvrant l'ensemble du projet
- 3 priorites strategiques + 1 quick win identifie
- Plan d'action en 4 phases avec gates go/no-go
- Fausses contraintes eliminees (SIG, couts reels, sequencement)

**Verites fondamentales decouvertes :**
- Le materiau-epoque est la vraie variable, pas l'age
- La reparation est un mecanisme aggravant, pas juste un signal
- Le nettoyage est une hypothese testable, pas un preprocessing
- Le modele predit la degradation, pas les accidents
- La valeur est dans les surprises (divergences modele/expert)
- L'outil est un miroir des compromis, pas un oracle

**Contraintes critiques :**
- SHAP = condition d'adoption non-negociable
- Backtesting = livrable de credibilite non-negociable
- Integration SIG a terme = condition de survie
- Bus factor / maintenabilite = a traiter des le depart
- Boucle delegant/delegataire = design a double interface
