Compte Rendu de Réunion

Date : 10 avril 2026
Objet : Revue fonctionnelle – Tableau de bord & Optimiseur – HpO.ai
Participants : Mohamed, Baptiste, Lionel (principal sponsor), Valentin, JC
Type : Réunion interne


1. Tableau de Bord – Analyse du Réseau
1.1 Définition du périmètre et du scope
Réseau concerné : Eau potable et assainissement
Territoire : La définition précise des 6 661 km de réseau est un préalable indispensable à toute analyse
Typologie des canalisations à distinguer impérativement :
Transport — feeders (grand diamètre, artères principales)
Distribution — petit diamètre, desserte des habitations
Branchements — raccordements individuels aux abonnés



⚠️ Point structurant : La définition du scope conditionne l'ensemble de l'analyse. Sans cadrage précis, les résultats ne sont pas exploitables. Le périmètre retenu porte à priori sur la distribution eau de l'ensemble de la SEM.



1.2 Analyse du patrimoine
Qualifier le type de linéaire par période de pose, notamment avant/après 1950 — certains résultats peuvent être immédiatement révélateurs
Branchements : leur prise en charge par le gestionnaire est un point structurant, les coûts associés étant d'une nature très différente de ceux des canalisations
Risque principal identifié : les fuites
Donnée clé : 80 % des fuites sont localisées sur les branchements, et non sur les canalisations


1.3 Matrice de risque
Approches de risque à intégrer : hydraulique, financier, politique, etc.
La matrice de risque doit être paramétrable (pondération ajustable selon le contexte client)
La valeur ajoutée d'HpO.ai réside dans la contextualisation du risque


Exemple illustratif : Un feeder défaillant apparaîtra en rouge vif selon sa localisation, car les conséquences opérationnelles et politiques peuvent être majeures



1.4 Définition des grandeurs et paramétrage
Longueur d'une canalisation : la définition doit être clarifiée — s'agit-il d'un tronçon ? d'un segment entre deux vannes ? d'un linéaire réseau ?
→ Notion propre à Watgis, à rendre paramétrable selon chaque client
Fiche signalétique sur sélection d'un tronçon : affichage de la fiche + localisation avec calque orthophoto
Attention au type de canalisation : ex. un polyéthylène DN51 sur 50 m est vraisemblablement un branchement → non impactant pour la SEM


1.5 Aléas et facteurs de risque externes
Intégrer dans l'analyse les aléas suivants :

Proximité ou croisement avec le réseau d'assainissement
Présence de haute tension enfouie (champ magnétique)


1.6 Programmes de renouvellement
Les programmes de renouvellement doivent être chiffrés et présentés dans le tableau de bord
Gestion des exclusions : à traiter avec rigueur pour ne pas fausser les résultats


2. Optimiseur – Priorisation des Travaux
2.1 Paramètres et contraintes
Entrées principales : budget disponible et contraintes terrain
L'algorithme doit prendre en compte la zone géographique et le type de commune (le linéaire renouvelable annuellement est très variable selon les contextes)
Ordre de grandeur de référence : ~32 km pour ~32 M€ (ratio indicatif, à affiner)


2.2 Positionnement par rapport à MOSARE
MOSARE est l'outil groupe Veolia disposant de sa propre fonction d'optimisation
HpO.ai doit se positionner clairement par rapport à MOSARE, notamment en analysant les réponses aux appels d'offres de MOSARE pour identifier les points de différenciation
La richesse de la base de données MOSARE (localisation des chantiers, entreprises intervenantes, coûts de travaux) constitue néanmoins une source d'alimentation potentielle pour l'optimiseur HpO.ai


2.3 Contraintes de terrain à intégrer dans la priorisation

Contrainte               Nature

Voies pompiers      Coupure de durée strictement limitée

Tramway                 Coordination avec l'exploitant, contraintes de planning

Écoles / Hôpitaux   Sensibilité forte, à planifier hors périodes critiques
2.4 Contrôle de la pertinence de l'IA
Vérifier systématiquement que les recommandations de l'IA ne sont pas déconnantes ou hors réalité terrain
L'ossature fonctionnelle présentée est jugée pertinente pour Lionel (sponsor principal)
Horizon temporel recommandé : étendre le raisonnement à 10 ans


3. Modes de Gestion – Approches Différenciées
3.1 En Délégation de Service Public (DSP)
Le raisonnement s'articule du macro vers le micro :
# Compte Rendu de Réunion

**Date :** 10 avril 2026  
**Objet :** Revue fonctionnelle – Tableau de bord & Optimiseur – HpO.ai  
**Participants :** Mohamed, Baptiste, Lionel (principal sponsor), Valentin, JC  
**Type :** Réunion interne

---

## 1. Tableau de Bord – Analyse du Réseau

### 1.1 Définition du périmètre et du scope
- **Réseau concerné :** Eau potable et assainissement
- **Territoire :** Définition précise des 6 661 km de réseau, préalable indispensable à toute analyse
- **Typologie des canalisations à distinguer :**
    - Transport — feeders (grand diamètre, artères principales)
    - Distribution — petit diamètre, desserte des habitations
    - Branchements — raccordements individuels aux abonnés

> ⚠️ **Point structurant :** La définition du scope conditionne l'ensemble de l'analyse. Sans cadrage précis, les résultats ne sont pas exploitables. Le périmètre retenu porte à priori sur la distribution eau de l'ensemble de la SEM.

### 1.2 Analyse du patrimoine
- Qualifier le type de linéaire par période de pose (notamment avant/après 1950)
- Branchements : prise en charge par le gestionnaire = point structurant (coûts très différents)
- **Risque principal identifié :** les fuites
- **Donnée clé :** 80 % des fuites sont localisées sur les branchements, non sur les canalisations

### 1.3 Matrice de risque
- Approches de risque à intégrer : hydraulique, financier, politique, etc.
- Matrice de risque paramétrable (pondération ajustable selon le contexte client)
- **Valeur ajoutée HpO.ai :** contextualisation du risque

> *Exemple : Un feeder défaillant apparaîtra en rouge vif selon sa localisation, car les conséquences opérationnelles et politiques peuvent être majeures*

### 1.4 Définition des grandeurs et paramétrage
- **Longueur d'une canalisation :** définition à clarifier (tronçon ? segment entre deux vannes ? linéaire réseau ?)
    - Notion propre à Watgis, à rendre paramétrable selon chaque client
- Fiche signalétique sur sélection d'un tronçon : affichage de la fiche + localisation avec calque orthophoto
- Attention au type de canalisation : ex. un polyéthylène DN51 sur 50 m est vraisemblablement un branchement → non impactant pour la SEM

### 1.5 Aléas et facteurs de risque externes
- Intégrer dans l'analyse :
    - Proximité ou croisement avec le réseau d'assainissement
    - Présence de haute tension enfouie (champ magnétique)

### 1.6 Programmes de renouvellement
- Les programmes de renouvellement doivent être chiffrés et présentés dans le tableau de bord
- Gestion des exclusions : à traiter avec rigueur pour ne pas fausser les résultats

---

## 2. Optimiseur – Priorisation des Travaux

### 2.1 Paramètres et contraintes
- **Entrées principales :** budget disponible et contraintes terrain
- L'algorithme doit prendre en compte la zone géographique et le type de commune (le linéaire renouvelable annuellement est très variable selon les contextes)
- **Ordre de grandeur de référence :** ~32 km pour ~32 M€ (ratio indicatif, à affiner)

### 2.2 Positionnement par rapport à MOSARE
- MOSARE = outil groupe Veolia disposant de sa propre fonction d'optimisation
- HpO.ai doit se positionner clairement par rapport à MOSARE (analyser les réponses aux AO pour identifier les points de différenciation)
- La richesse de la base de données MOSARE (localisation des chantiers, entreprises intervenantes, coûts de travaux) = source d'alimentation potentielle pour l'optimiseur HpO.ai

### 2.3 Contraintes de terrain à intégrer dans la priorisation

| Contrainte         | Nature                                             |
|--------------------|---------------------------------------------------|
| Voies pompiers     | Coupure de durée strictement limitée              |
| Tramway            | Coordination avec l'exploitant, contraintes de planning |
| Écoles / Hôpitaux  | Sensibilité forte, à planifier hors périodes critiques |

### 2.4 Contrôle de la pertinence de l'IA
- Vérifier systématiquement que les recommandations de l'IA ne sont pas déconnantes ou hors réalité terrain
- L'ossature fonctionnelle présentée est jugée pertinente pour Lionel (sponsor principal)
- **Horizon temporel recommandé :** étendre le raisonnement à 10 ans

---

## 3. Modes de Gestion – Approches Différenciées

### 3.1 En Délégation de Service Public (DSP)
Le raisonnement s'articule du macro vers le micro :
- Long terme (10 ans)
    - Impact du plan de renouvellement
        - Analyse des rendements
            - Horizon 5 ans
                - Horizon 3 ans
                    - Plan annuel

### 3.2 En Régie
- Pilotage principalement contraint par le budget annuel
- Exemple : 2 M€/an → environ 2 km renouvelés par an

---

## 4. Intelligence Artificielle – Ambition et Positionnement
- L'IA doit être capable d'anticiper les défaillances avant qu'elles surviennent (approche prédictive)
- **Objectif :** passer d'une logique réactive "je répare quand ça casse" à une logique proactive "je renouvelle avant que ça cède"

---

## 5. Actions & Points de Suivi

| # | Action                                                      | Échéance   |
|---|-------------------------------------------------------------|------------|
| 1 | Lire et analyser les réponses aux AO de MOSARE              | À définir  |
| 2 | Préparer et cadrer la démo HpO.ai                           | À définir  |
| 3 | Définir précisément le périmètre des 6 661 km               | À définir  |
| 4 | Valider la paramétrisation de la matrice de risque          | À définir  |
| 5 | Clarifier la définition de longueur de tronçon dans Watgis  | À définir  |
